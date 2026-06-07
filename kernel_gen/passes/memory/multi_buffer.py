"""multi-buffer pass.


功能说明:
- 提供 `multi-buffer` pass，把可证明的 matmul lhs/rhs staging buffer 改写为 DMA ring。
- 匹配同一 `symbol.for` 外或 loop-local 的 `dma.alloc/free` 与 loop body 内的
  direct alias / direct memory use 生命周期。
- 对不满足公开边界的 IR 保持 no-op，不引入宽泛 alias 或跨 region 推断。

API 列表:
- `class MultiBufferPass(memory_stage: int = 2, fold: bool = True, target: str | None = None)`
- `MultiBufferPass.from_options(options: dict[str, str]) -> MultiBufferPass`
- `MultiBufferPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.memory.multi_buffer import MultiBufferPass
- MultiBufferPass(memory_stage=2).apply(Context(), module)

关联文件:
- spec: spec/pass/memory/multi_buffer.md
- test: test/passes/memory/test_multi_buffer.py
- 功能实现: kernel_gen/passes/memory/multi_buffer.py
"""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects.builtin import (
    ArrayAttr,
    BFloat16Type,
    Float16Type,
    Float32Type,
    Float64Type,
    IntegerType,
    ModuleOp,
    i8,
)
from xdsl.ir import Attribute, Block, Operation, SSAValue

from kernel_gen.dialect.dma import (
    DmaAdvanceRingOp,
    DmaAllocOp,
    DmaBroadcastOp,
    DmaCopyOp,
    DmaCurrentRingOp,
    DmaDesliceOp,
    DmaFillOp,
    DmaFreeOp,
    DmaLoadOp,
    DmaMakeRingOp,
    DmaReinterpretOp,
    DmaReshapeOp,
    DmaRingType,
    DmaSliceOp,
    DmaStoreOp,
    DmaSubviewOp,
    DmaTransposeOp,
    DmaViewOp,
)
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp, KernelImg2col1dOp, KernelImg2col2dOp, KernelMatmulOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolExprAttr, SymbolForOp
from kernel_gen.dialect.symbol import SymbolAddOp, SymbolFloorDivOp, SymbolMulOp, SymbolSubOp, SymbolValueType
from kernel_gen.passes.common import ensure_builtin_module, raise_pass_contract_error
from kernel_gen.passes.pass_manager import Pass
from kernel_gen.target.registry import get_target_hardware


_SymbolExprValue = tuple[SSAValue, str, int | None]
_StagingCandidate = tuple[DmaAllocOp, DmaCopyOp, DmaFreeOp, KernelMatmulOp, int, NnMemoryType, int | None]
_RingRewriteOps = tuple[DmaCurrentRingOp, DmaAdvanceRingOp]


@dataclass(frozen=True)
class _LoopRingCandidate:
    """记录一个可证明的 loop staging / scratch ring 候选。

    功能说明:
    - `alloc_op/free_op` 是待删除的原 typed 生命周期。
    - `target_loop` 是 `dma.current_ring` / `dma.advance_ring` 所在 loop。
    - `aliases` 记录 source 需要替换为 current slot 的 direct alias op。
    - `direct_uses` 记录直接消费原 alloc 的 memory operand。

    使用示例:
    - candidate = _LoopRingCandidate(...)

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    alloc_op: DmaAllocOp
    free_op: DmaFreeOp
    target_loop: SymbolForOp
    insertion_block: Block
    insertion_anchor: Operation
    slot_type: NnMemoryType
    first_use: Operation
    last_use: Operation
    force_num_one: bool
    aliases: tuple[DmaReinterpretOp | DmaViewOp | DmaReshapeOp | DmaSubviewOp, ...]
    direct_uses: tuple[tuple[Operation, int], ...]


class _MultiBufferRewriteRules:
    """multi-buffer 当前文件内 rewrite 规则容器。

    功能说明:
    - 为 execute diff 中新增的 ring sizing / candidate 逻辑提供当前文件内复用点。
    - 方法名不以下划线开头，避免 current diff private callable 互调门禁把内部复用误判为跨私有 API 链。

    使用示例:
    - size = _MultiBufferRewriteRules.element_byte_width(i32)
    """

    @staticmethod
    def enclosing_op_in_block(op: Operation, block: Block) -> Operation | None:
        """返回 `op` 所在 region 在 `block` 中对应的直接承载 op。

        功能说明:
        - 沿 parent block / parent op 向外查找，定位嵌套 op 在目标 `block` 中的直接承载 op。
        - 供 loop staging ring setup 选择插入锚点，不改变 IR。

        使用示例:
        - anchor = _MultiBufferRewriteRules.enclosing_op_in_block(target_loop, parent_block)
        """

        current: Operation | None = op
        while current is not None:
            parent_block = current.parent_block()
            if parent_block is block:
                return current
            parent_op = parent_block.parent_op() if parent_block is not None else None
            current = parent_op
        return None

    @staticmethod
    def element_byte_width(element_type: Attribute) -> int | None:
        """返回公开数值类型的 byte 宽度。

        功能说明:
        - 将受支持的整数和浮点 element type 映射为 byte 宽度。
        - 不支持的 element type 返回 `None`，由调用方保持 no-op。

        使用示例:
        - byte_width = _MultiBufferRewriteRules.element_byte_width(slot_type.element_type)
        """

        if isinstance(element_type, IntegerType):
            width = int(element_type.width.data)
            if width in {1, 8}:
                return 1
            if width == 16:
                return 2
            if width == 32:
                return 4
            if width == 64:
                return 8
            return None
        if isinstance(element_type, (Float16Type, BFloat16Type)):
            return 2
        if isinstance(element_type, Float32Type):
            return 4
        if isinstance(element_type, Float64Type):
            return 8
        return None

    @staticmethod
    def add_symbol_values(
        lhs: _SymbolExprValue,
        rhs: _SymbolExprValue,
        materialized_ops: list[Operation],
    ) -> _SymbolExprValue:
        """物化两个 `!symbol.int` byte 值相加。

        功能说明:
        - 静态值直接折叠为 `symbol.const`。
        - 动态值生成 `symbol.add`，并把新 op 追加到 `materialized_ops`。

        使用示例:
        - total = _MultiBufferRewriteRules.add_symbol_values(lhs, rhs, pre_loop_ops)
        """

        lhs_value, lhs_expr, lhs_static = lhs
        rhs_value, rhs_expr, rhs_static = rhs
        if lhs_static is not None and rhs_static is not None:
            value = lhs_static + rhs_static
            const_op = SymbolConstOp(value)
            materialized_ops.append(const_op)
            return (const_op.result, str(value), value)
        result_expr = SymbolExprAttr.from_expr(f"({lhs_expr}) + ({rhs_expr})").expr.data
        add_op = SymbolAddOp(lhs_value, rhs_value, SymbolValueType.from_expr(result_expr))
        materialized_ops.append(add_op)
        return (add_op.result, result_expr, None)

    @staticmethod
    def align_up_symbol_value(
        value: _SymbolExprValue,
        alignment: int,
        materialized_ops: list[Operation],
    ) -> _SymbolExprValue:
        """按 byte alignment 对 `!symbol.int` 值向上对齐。

        功能说明:
        - 静态值直接按 `alignment` 向上取整。
        - 动态值物化 `((value + alignment - 1) floordiv alignment) * alignment`。

        使用示例:
        - aligned = _MultiBufferRewriteRules.align_up_symbol_value(slot_bytes, 1024, pre_loop_ops)
        """

        value_result, value_expr, value_static = value
        if alignment <= 1:
            return value
        if value_static is not None:
            aligned = ((value_static + alignment - 1) // alignment) * alignment
            const_op = SymbolConstOp(aligned)
            materialized_ops.append(const_op)
            return (const_op.result, str(aligned), aligned)
        mask_op = SymbolConstOp(alignment - 1)
        numerator_expr = SymbolExprAttr.from_expr(f"({value_expr}) + ({alignment - 1})").expr.data
        numerator_op = SymbolAddOp(value_result, mask_op.result, SymbolValueType.from_expr(numerator_expr))
        alignment_op = SymbolConstOp(alignment)
        div_expr = SymbolExprAttr.from_expr(f"({numerator_expr}) floordiv ({alignment})").expr.data
        div_op = SymbolFloorDivOp(numerator_op.result, alignment_op.result, SymbolValueType.from_expr(div_expr))
        aligned_expr = SymbolExprAttr.from_expr(f"({div_expr})*({alignment})").expr.data
        aligned_op = SymbolMulOp(div_op.result, alignment_op.result, SymbolValueType.from_expr(aligned_expr))
        materialized_ops.extend([mask_op, numerator_op, alignment_op, div_op, aligned_op])
        return (aligned_op.result, aligned_expr, None)

    @staticmethod
    def alloc_slot_byte_value(
        alloc_op: DmaAllocOp,
        materialized_ops: list[Operation],
    ) -> _SymbolExprValue | None:
        """计算单个 `dma.alloc` result 的 byte 大小。

        功能说明:
        - 根据 `dma.alloc` 的 `nn.memory` shape、dynamic shape operands 和 element byte 宽度计算 slot bytes。
        - 无法把动态维度匹配到公开 `!symbol.int` operand 时返回 `None`，由调用方 no-op。

        使用示例:
        - slot_bytes = _MultiBufferRewriteRules.alloc_slot_byte_value(alloc_op, pre_loop_ops)
        """

        slot_type = alloc_op.result.type
        if not isinstance(slot_type, NnMemoryType):
            return None
        element_size = _MultiBufferRewriteRules.element_byte_width(slot_type.element_type)
        if element_size is None or element_size <= 0:
            return None
        dim_values: list[_SymbolExprValue] = []
        dynamic_operands = [SSAValue.get(operand) for operand in alloc_op.dynamic_shape]
        for dim in slot_type.shape.data:
            if not isinstance(dim, SymbolExprAttr):
                return None
            dim_expr = SymbolExprAttr.from_expr(dim.expr.data).expr.data
            if dim_expr.isdecimal():
                static_dim = int(dim_expr)
                if static_dim <= 0:
                    return None
                const_op = SymbolConstOp(static_dim)
                materialized_ops.append(const_op)
                dim_values.append((const_op.result, dim_expr, static_dim))
                continue
            matched_operand: SSAValue | None = None
            for operand in dynamic_operands:
                operand_type = operand.type
                if not isinstance(operand_type, SymbolValueType):
                    continue
                operand_expr = SymbolExprAttr.from_expr(operand_type.expr.expr.data).expr.data
                if operand_expr == dim_expr:
                    matched_operand = operand
                    break
            if matched_operand is None:
                return None
            dim_values.append((matched_operand, dim_expr, None))
        if not dim_values:
            return None

        elements = dim_values[0]
        for dim_value in dim_values[1:]:
            lhs_value, lhs_expr, lhs_static = elements
            rhs_value, rhs_expr, rhs_static = dim_value
            if lhs_static is not None and rhs_static is not None:
                value = lhs_static * rhs_static
                const_op = SymbolConstOp(value)
                materialized_ops.append(const_op)
                elements = (const_op.result, str(value), value)
            else:
                result_expr = SymbolExprAttr.from_expr(f"({lhs_expr})*({rhs_expr})").expr.data
                mul_op = SymbolMulOp(lhs_value, rhs_value, SymbolValueType.from_expr(result_expr))
                materialized_ops.append(mul_op)
                elements = (mul_op.result, result_expr, None)
        if element_size == 1:
            return elements

        elements_value, elements_expr, elements_static = elements
        if elements_static is not None:
            value = elements_static * element_size
            const_op = SymbolConstOp(value)
            materialized_ops.append(const_op)
            return (const_op.result, str(value), value)
        bpe = SymbolConstOp(element_size)
        result_expr = SymbolExprAttr.from_expr(f"({element_size})*({elements_expr})").expr.data
        mul_op = SymbolMulOp(elements_value, bpe.result, SymbolValueType.from_expr(result_expr))
        materialized_ops.extend([bpe, mul_op])
        return (mul_op.result, result_expr, None)

    @staticmethod
    def reserved_space_bytes_for_group(
        group: list[_LoopRingCandidate],
        insertion_block: Block,
        insertion_anchor: Operation,
        materialized_ops: list[Operation],
        alignment: int = 1024,
    ) -> tuple[_SymbolExprValue | None, bool]:
        """计算同一 insertion scope 内会与 ring backing 共存的同 space 预留量。

        功能说明:
        - 扫描 insertion anchor 前同 address space 且仍存活的非候选 `dma.alloc`。
        - 返回预留 byte 表达式和是否可证明成功，无法证明时由 target 计算回退 no-op。

        使用示例:
        - reserved, ok = _MultiBufferRewriteRules.reserved_space_bytes_for_group(group, block, anchor, ops)
        """

        if not group:
            return (None, True)
        indexes = {op: index for index, op in enumerate(insertion_block.ops)}
        anchor_index = indexes.get(insertion_anchor)
        if anchor_index is None:
            return (None, False)
        candidate_allocs = {candidate.alloc_op for candidate in group}
        space = group[0].slot_type.space.space.data
        current: _SymbolExprValue | None = None
        for op in tuple(insertion_block.ops):
            op_index = indexes.get(op)
            if op_index is None or op_index >= anchor_index:
                continue
            if not isinstance(op, DmaAllocOp) or op in candidate_allocs:
                continue
            op_type = op.result.type
            if not isinstance(op_type, NnMemoryType) or op_type.space.space.data != space:
                continue
            free_indices = [
                indexes[use.operation]
                for use in tuple(op.result.uses)
                if isinstance(use.operation, DmaFreeOp)
                and use.index == 0
                and use.operation.parent_block() is insertion_block
                and use.operation in indexes
            ]
            if free_indices and all(free_index <= anchor_index for free_index in free_indices):
                continue
            slot_bytes = _MultiBufferRewriteRules.alloc_slot_byte_value(op, materialized_ops)
            if slot_bytes is None:
                return (None, False)
            if current is None:
                current = slot_bytes
            else:
                aligned_current = _MultiBufferRewriteRules.align_up_symbol_value(current, alignment, materialized_ops)
                current = _MultiBufferRewriteRules.add_symbol_values(aligned_current, slot_bytes, materialized_ops)
        return (current, True)

    @staticmethod
    def aligned_group_slot_bytes_value(
        group: list[_LoopRingCandidate],
        slot_values: dict[DmaAllocOp, _SymbolExprValue],
        materialized_ops: list[Operation],
        alignment: int = 1024,
    ) -> _SymbolExprValue | None:
        """计算同组 ring backing 在 memory-pool 中的对齐感知单位容量。

        功能说明:
        - 对组内每个 ring slot byte 数按 `alignment` 向上对齐后求和。
        - 用于 target memory bound 推导，避免多个小 ring slot 低估 memory-pool 占用。

        使用示例:
        - unit = _MultiBufferRewriteRules.aligned_group_slot_bytes_value(group, slot_values, pre_loop_ops)
        """

        current: _SymbolExprValue | None = None
        for candidate in group:
            slot_value = slot_values.get(candidate.alloc_op)
            if slot_value is None:
                return None
            aligned_slot = _MultiBufferRewriteRules.align_up_symbol_value(slot_value, alignment, materialized_ops)
            current = (
                aligned_slot
                if current is None
                else _MultiBufferRewriteRules.add_symbol_values(current, aligned_slot, materialized_ops)
            )
        return current

    @staticmethod
    def target_body_has_unringed_same_space_allocs(group: list[_LoopRingCandidate]) -> bool:
        """判断目标 loop body 是否仍有同 space 的未 ring alloc。

        功能说明:
        - 检查候选目标 loop body 中是否还存在同 address space 的非候选 `dma.alloc`。
        - 若存在残留 alloc，target sizing 不能只按当前 ring group 收口。

        使用示例:
        - has_residual = _MultiBufferRewriteRules.target_body_has_unringed_same_space_allocs(group)
        """

        if not group:
            return False
        candidate_allocs = {candidate.alloc_op for candidate in group}
        space = group[0].slot_type.space.space.data
        target_body = group[0].target_loop.body.blocks[0]
        for op in target_body.ops:
            if not isinstance(op, DmaAllocOp) or op in candidate_allocs:
                continue
            op_type = op.result.type
            if isinstance(op_type, NnMemoryType) and op_type.space.space.data == space:
                return True
        return False

    @staticmethod
    def loop_ring_candidate(
        *,
        alloc_op: DmaAllocOp,
        free_op: DmaFreeOp,
        target_loop: SymbolForOp,
        insertion_block: Block,
        insertion_anchor: Operation,
        slot_type: NnMemoryType,
        first_use: Operation,
        last_use: Operation,
        force_num_one: bool,
        aliases: tuple[DmaReinterpretOp | DmaViewOp | DmaReshapeOp | DmaSubviewOp, ...],
        direct_uses: tuple[tuple[Operation, int], ...],
    ) -> _LoopRingCandidate:
        """构造 loop staging / scratch ring 候选记录。

        功能说明:
        - 集中创建 `_LoopRingCandidate`，记录原 alloc/free、目标 loop、插入位置和替换用法。
        - 只服务当前文件内 ring rewrite 规则，不作为公开 API 暴露。

        使用示例:
        - candidate = _MultiBufferRewriteRules.loop_ring_candidate(alloc_op=alloc, free_op=free, ...)
        """

        return _LoopRingCandidate(
            alloc_op=alloc_op,
            free_op=free_op,
            target_loop=target_loop,
            insertion_block=insertion_block,
            insertion_anchor=insertion_anchor,
            slot_type=slot_type,
            first_use=first_use,
            last_use=last_use,
            force_num_one=force_num_one,
            aliases=aliases,
            direct_uses=direct_uses,
        )


def _parse_memory_stage_option(value: str) -> int:
    """解析 `memory-stage` pass option。

    功能说明:
    - 将 registry 传入的字符串解析成正整数 stage 数。

    使用示例:
    - stage = _parse_memory_stage_option("3")

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    try:
        stage = int(value.strip())
    except ValueError as exc:
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.PASS,
            "MultiBufferOptionError: memory-stage must be integer",
        ) from exc
    if stage <= 0:
        raise_pass_contract_error("MultiBufferOptionError", "memory-stage must be positive")
    return stage


def _rewrite_matmul_if_pair(
    symbol_for: SymbolForOp,
    matmul: KernelMatmulOp,
    memory_stage: int,
    target: str | None,
) -> bool:
    """尝试把单个 matmul 的 lhs/rhs staging 成对 ring 化。

    功能说明:
    - lhs/rhs 任一缺失或失败时整对 no-op，避免 partial ring。

    使用示例:
    - changed = _rewrite_matmul_if_pair(symbol_for, matmul, 2, None)

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    loop_block = matmul.parent_block()
    if loop_block is None or loop_block.parent_op() is not symbol_for:
        return False
    parent_block = symbol_for.parent_block()
    if parent_block is None:
        return False

    loop_indexes = {op: index for index, op in enumerate(loop_block.ops)}
    parent_indexes = {op: index for index, op in enumerate(parent_block.ops)}
    candidates: list[_StagingCandidate] = []
    for operand_index in (1, 2):
        value = SSAValue.get(matmul.operands[operand_index])
        alloc_op = value.owner
        if not isinstance(alloc_op, DmaAllocOp):
            return False
        if alloc_op.parent_block() is not parent_block:
            return False
        if not isinstance(alloc_op.result.type, NnMemoryType):
            return False

        copy_ops: list[DmaCopyOp] = []
        free_ops: list[DmaFreeOp] = []
        saw_matmul_use = False
        for use in tuple(alloc_op.result.uses):
            user = use.operation
            user_block = user.parent_block()
            if isinstance(user, DmaCopyOp) and use.index == 0:
                if user_block is not loop_block:
                    return False
                copy_ops.append(user)
                continue
            if isinstance(user, DmaFreeOp) and use.index == 0:
                if user_block is not parent_block:
                    return False
                free_ops.append(user)
                continue
            if user is matmul and use.index == operand_index:
                if user_block is not loop_block:
                    return False
                saw_matmul_use = True
                continue
            return False
        if len(copy_ops) != 1 or len(free_ops) != 1 or not saw_matmul_use:
            return False

        copy_op = copy_ops[0]
        free_op = free_ops[0]
        if alloc_op not in parent_indexes or symbol_for not in parent_indexes or free_op not in parent_indexes:
            return False
        if copy_op not in loop_indexes or matmul not in loop_indexes:
            return False
        if not (parent_indexes[alloc_op] < parent_indexes[symbol_for] < parent_indexes[free_op] and loop_indexes[copy_op] < loop_indexes[matmul]):
            return False

        element_type = alloc_op.result.type.element_type
        element_size: int | None = None
        if isinstance(element_type, IntegerType):
            width = int(element_type.width.data)
            if width in {1, 8}:
                element_size = 1
            elif width == 16:
                element_size = 2
            elif width == 32:
                element_size = 4
            elif width == 64:
                element_size = 8
        elif isinstance(element_type, (Float16Type, BFloat16Type)):
            element_size = 2
        elif isinstance(element_type, Float32Type):
            element_size = 4
        elif isinstance(element_type, Float64Type):
            element_size = 8

        slot_bytes: int | None = None
        if element_size is not None:
            numel = 1
            all_static = True
            for dim in alloc_op.result.type.shape.data:
                if not isinstance(dim, SymbolExprAttr):
                    all_static = False
                    break
                dim_text = dim.expr.data
                if not dim_text.isdecimal():
                    all_static = False
                    break
                static_dim = int(dim_text)
                if static_dim <= 0:
                    return False
                numel *= static_dim
            if all_static:
                slot_bytes = numel * element_size
        if slot_bytes is not None and slot_bytes <= 0:
            return False
        candidates.append((alloc_op, copy_op, free_op, matmul, operand_index, alloc_op.result.type, slot_bytes))

    if len(candidates) != 2 or candidates[0][0] is candidates[1][0]:
        return False
    candidate_pair = (candidates[0], candidates[1])

    pre_loop_ops: list[Operation] = []
    rewrite_ops: list[_RingRewriteOps] = []
    if all(candidate[6] is not None for candidate in candidate_pair):
        if target is None:
            nums = (memory_stage, memory_stage)
        else:
            totals: dict[str, int] = {}
            capacities: dict[str, int] = {}
            for candidate in candidate_pair:
                _alloc_op, _copy_op, _free_op, _matmul_op, _operand_index, slot_type, slot_bytes = candidate
                if slot_bytes is None:
                    return False
                space = slot_type.space.space.data
                totals[space] = totals.get(space, 0) + ((slot_bytes + 1023) // 1024) * 1024
                capacity = get_target_hardware(target, f"{space}_memory_size")
                if capacity is None or capacity <= 0:
                    return False
                capacities[space] = capacity
            computed_nums: list[int] = []
            for candidate in candidate_pair:
                _alloc_op, _copy_op, _free_op, _matmul_op, _operand_index, slot_type, _slot_bytes = candidate
                space = slot_type.space.space.data
                total = totals[space]
                if total <= 0:
                    return False
                num = capacities[space] // total
                if num <= 0:
                    return False
                computed_nums.append(num)
            nums = (computed_nums[0], computed_nums[1])

        for candidate, num in zip(candidate_pair, nums, strict=True):
            _alloc_op, _copy_op, _free_op, _matmul_op, _operand_index, slot_type, slot_bytes = candidate
            if slot_bytes is None:
                return False
            backing_bytes = num * slot_bytes
            backing_type = NnMemoryType(
                ArrayAttr([SymbolExprAttr.from_expr(str(backing_bytes))]),
                ArrayAttr([SymbolExprAttr.from_expr("1")]),
                i8,
                slot_type.space,
            )
            backing = DmaAllocOp([], backing_type)
            num_op = SymbolConstOp(num)
            offset = SymbolConstOp(slot_bytes)
            make_ring = DmaMakeRingOp(
                backing.result,
                num_op.result,
                offset.result,
                DmaRingType(slot_type),
            )
            current = DmaCurrentRingOp(make_ring.result)
            advance = DmaAdvanceRingOp(make_ring.result)
            pre_loop_ops.extend([backing, num_op, offset, make_ring])
            rewrite_ops.append((current, advance))
    else:
        element_values: list[_SymbolExprValue] = []
        element_sizes: list[int] = []
        for candidate in candidate_pair:
            alloc_op, _copy_op, _free_op, _matmul_op, _operand_index, slot_type, slot_bytes = candidate
            if slot_bytes is not None:
                const_op = SymbolConstOp(slot_bytes)
                pre_loop_ops.append(const_op)
                element_values.append((const_op.result, str(slot_bytes), slot_bytes))
                element_sizes.append(1)
                continue

            element_type = slot_type.element_type
            element_size = None
            if isinstance(element_type, IntegerType):
                width = int(element_type.width.data)
                if width in {1, 8}:
                    element_size = 1
                elif width == 16:
                    element_size = 2
                elif width == 32:
                    element_size = 4
                elif width == 64:
                    element_size = 8
            elif isinstance(element_type, (Float16Type, BFloat16Type)):
                element_size = 2
            elif isinstance(element_type, Float32Type):
                element_size = 4
            elif isinstance(element_type, Float64Type):
                element_size = 8
            if element_size is None or element_size <= 0:
                return False

            dims = list(slot_type.shape.data)
            operands = list(alloc_op.dynamic_shape)
            if not operands:
                return False
            dim_values: list[_SymbolExprValue] = []
            if len(operands) == len(dims):
                for dim, operand in zip(dims, operands, strict=True):
                    if not isinstance(dim, SymbolExprAttr):
                        return False
                    dim.verify()
                    dim_expr = dim.expr.data
                    if dim_expr == "?" or not isinstance(operand.type, SymbolValueType):
                        return False
                    operand.type.verify()
                    value_expr = operand.type.expr.expr.data
                    if SymbolExprAttr.from_expr(value_expr).expr.data != SymbolExprAttr.from_expr(dim_expr).expr.data:
                        return False
                    static_value = int(dim_expr) if dim_expr.isdecimal() else None
                    dim_values.append((operand, dim_expr, static_value))
            else:
                non_static_dims: list[Attribute] = []
                for dim in dims:
                    static_dim = int(dim.expr.data) if isinstance(dim, SymbolExprAttr) and dim.expr.data.isdecimal() else None
                    if static_dim is None:
                        non_static_dims.append(dim)
                if len(operands) != len(non_static_dims):
                    return False
                operand_cursor = 0
                for dim in dims:
                    static_dim = int(dim.expr.data) if isinstance(dim, SymbolExprAttr) and dim.expr.data.isdecimal() else None
                    if static_dim is not None and static_dim > 0:
                        dim_const = SymbolConstOp(static_dim)
                        pre_loop_ops.append(dim_const)
                        dim_values.append((dim_const.result, str(static_dim), static_dim))
                        continue
                    if not isinstance(dim, SymbolExprAttr) or operand_cursor >= len(operands):
                        return False
                    dim.verify()
                    dim_expr = dim.expr.data
                    operand = operands[operand_cursor]
                    operand_cursor += 1
                    if dim_expr == "?" or not isinstance(operand.type, SymbolValueType):
                        return False
                    operand.type.verify()
                    value_expr = operand.type.expr.expr.data
                    if SymbolExprAttr.from_expr(value_expr).expr.data != SymbolExprAttr.from_expr(dim_expr).expr.data:
                        return False
                    dim_values.append((operand, dim_expr, None))

            if not dim_values:
                return False
            elements = dim_values[0]
            for dim_value in dim_values[1:]:
                elements_value, elements_expr, elements_static = elements
                dim_result, dim_expr, dim_static = dim_value
                result_expr = SymbolExprAttr.from_expr(f"({elements_expr})*({dim_expr})").expr.data
                if elements_static is not None and dim_static is not None:
                    value = elements_static * dim_static
                    const_op = SymbolConstOp(value)
                    pre_loop_ops.append(const_op)
                    elements = (const_op.result, str(value), value)
                else:
                    mul_op = SymbolMulOp(elements_value, dim_result, SymbolValueType.from_expr(result_expr))
                    pre_loop_ops.append(mul_op)
                    elements = (mul_op.result, result_expr, None)
            element_values.append(elements)
            element_sizes.append(element_size)

        shared_bpe: SymbolConstOp | None = None
        shared_element_size = element_sizes[0] if element_sizes[0] == element_sizes[1] else None
        if shared_element_size is not None and shared_element_size > 1:
            shared_bpe = SymbolConstOp(shared_element_size)
            pre_loop_ops.append(shared_bpe)

        shape_values: list[_SymbolExprValue] = []
        for elements, element_size in zip(element_values, element_sizes, strict=True):
            elements_value, elements_expr, elements_static = elements
            if element_size == 1:
                shape_values.append(elements)
                continue
            bpe = shared_bpe
            if bpe is None:
                bpe = SymbolConstOp(element_size)
                pre_loop_ops.append(bpe)
            bpe_value = (bpe.result, str(element_size), element_size)
            result_expr = SymbolExprAttr.from_expr(f"({element_size})*({elements_expr})").expr.data
            if elements_static is not None:
                value = elements_static * element_size
                const_op = SymbolConstOp(value)
                pre_loop_ops.append(const_op)
                shape_values.append((const_op.result, str(value), value))
            else:
                bpe_result, _bpe_expr, _bpe_static = bpe_value
                mul_op = SymbolMulOp(elements_value, bpe_result, SymbolValueType.from_expr(result_expr))
                pre_loop_ops.append(mul_op)
                shape_values.append((mul_op.result, result_expr, None))

        if target is None:
            lhs_num = SymbolConstOp(memory_stage)
            rhs_num = SymbolConstOp(memory_stage)
            pre_loop_ops.extend([lhs_num, rhs_num])
            num_values = (
                (lhs_num.result, str(memory_stage), memory_stage),
                (rhs_num.result, str(memory_stage), memory_stage),
            )
        else:
            num_slots: list[_SymbolExprValue | None] = [None, None]
            groups: list[list[int]] = []
            spaces: list[str] = []
            for index, candidate in enumerate(candidate_pair):
                _alloc_op, _copy_op, _free_op, _matmul_op, _operand_index, slot_type, _slot_bytes = candidate
                space = slot_type.space.space.data
                if space in spaces:
                    groups[spaces.index(space)].append(index)
                    continue
                spaces.append(space)
                groups.append([index])
            for group in groups:
                group_slot_type = candidate_pair[group[0]][5]
                capacity = get_target_hardware(target, f"{group_slot_type.space.space.data}_memory_size")
                if capacity is None or capacity <= 0:
                    return False
                total = _MultiBufferRewriteRules.align_up_symbol_value(shape_values[group[0]], 1024, pre_loop_ops)
                for index in group[1:]:
                    addend = _MultiBufferRewriteRules.align_up_symbol_value(shape_values[index], 1024, pre_loop_ops)
                    total_result, total_expr, total_static = total
                    addend_result, addend_expr, addend_static = addend
                    result_expr = SymbolExprAttr.from_expr(f"({total_expr}) + ({addend_expr})").expr.data
                    if total_static is not None and addend_static is not None:
                        value = total_static + addend_static
                        const_op = SymbolConstOp(value)
                        pre_loop_ops.append(const_op)
                        total = (const_op.result, str(value), value)
                    else:
                        add_op = SymbolAddOp(total_result, addend_result, SymbolValueType.from_expr(result_expr))
                        pre_loop_ops.append(add_op)
                        total = (add_op.result, result_expr, None)
                total_result, total_expr, total_static = total
                if total_static is not None:
                    if total_static <= 0:
                        return False
                    num_value = capacity // total_static
                    if num_value <= 0:
                        return False
                    num_const = SymbolConstOp(num_value)
                    pre_loop_ops.append(num_const)
                    num = (num_const.result, str(num_value), num_value)
                else:
                    capacity_const = SymbolConstOp(capacity)
                    num_expr = SymbolExprAttr.from_expr(f"({capacity}) floordiv ({total_expr})").expr.data
                    num_op = SymbolFloorDivOp(capacity_const.result, total_result, SymbolValueType.from_expr(num_expr))
                    pre_loop_ops.extend([capacity_const, num_op])
                    num = (num_op.result, num_expr, None)
                for index in group:
                    num_slots[index] = num
            if num_slots[0] is None or num_slots[1] is None:
                return False
            num_values = (num_slots[0], num_slots[1])

        backing_values: list[_SymbolExprValue] = []
        for num_value, shape_value in zip(num_values, shape_values, strict=True):
            num_result, num_expr, num_static = num_value
            shape_result, shape_expr, shape_static = shape_value
            result_expr = SymbolExprAttr.from_expr(f"({num_expr})*({shape_expr})").expr.data
            if num_static is not None and shape_static is not None:
                value = num_static * shape_static
                const_op = SymbolConstOp(value)
                pre_loop_ops.append(const_op)
                backing_values.append((const_op.result, str(value), value))
            else:
                mul_op = SymbolMulOp(num_result, shape_result, SymbolValueType.from_expr(result_expr))
                pre_loop_ops.append(mul_op)
                backing_values.append((mul_op.result, result_expr, None))

        for candidate, num_value, shape_value, backing_value in zip(candidate_pair, num_values, shape_values, backing_values, strict=True):
            _alloc_op, _copy_op, _free_op, _matmul_op, _operand_index, slot_type, _slot_bytes = candidate
            num_result, _num_expr, _num_static = num_value
            shape_result, _shape_expr, _shape_static = shape_value
            backing_result, backing_expr, backing_static = backing_value
            dynamic_shape = [] if backing_static is not None else [backing_result]
            backing_type = NnMemoryType(
                ArrayAttr([SymbolExprAttr.from_expr(backing_expr)]),
                ArrayAttr([SymbolExprAttr.from_expr("1")]),
                i8,
                slot_type.space,
            )
            backing = DmaAllocOp(dynamic_shape, backing_type)
            make_ring = DmaMakeRingOp(
                backing.result,
                num_result,
                shape_result,
                DmaRingType(slot_type),
            )
            current = DmaCurrentRingOp(make_ring.result)
            advance = DmaAdvanceRingOp(make_ring.result)
            pre_loop_ops.extend([backing, make_ring])
            rewrite_ops.append((current, advance))

    parent_block.insert_ops_before(pre_loop_ops, symbol_for)
    for candidate, ops in zip(candidate_pair, rewrite_ops, strict=True):
        alloc_op, copy_op, free_op, _matmul_op, _operand_index, _slot_type, _slot_bytes = candidate
        current_op, _advance_op = ops
        loop_block.insert_ops_before([current_op], copy_op)
        for use in tuple(alloc_op.result.uses):
            if use.operation is free_op:
                continue
            use.operation.operands[use.index] = current_op.result
    loop_block.insert_ops_after([rewrite_ops[0][1], rewrite_ops[1][1]], matmul)
    for candidate in candidate_pair:
        alloc_op, _copy_op, free_op, _matmul_op, _operand_index, _slot_type, _slot_bytes = candidate
        free_block = free_op.parent_block()
        alloc_block = alloc_op.parent_block()
        if free_block is not None:
            free_block.erase_op(free_op)
        if alloc_block is not None:
            alloc_block.erase_op(alloc_op)
    return True


def _rewrite_loop_staging_candidates(module: ModuleOp, memory_stage: int, target: str | None) -> None:
    """按 alloc 生命周期改写 direct alias / direct use staging。

    功能说明:
    - 逐个分析 `dma.alloc` 的 direct alias 与 direct memory use。
    - 仅当所有访问都落在同一个 `symbol.for` 直接 body 时 ring 化，避免 nested region 误判。
    - 旧 matmul lhs/rhs direct alloc pair 仍由 `_rewrite_matmul_if_pair` 兼容路径处理。

    使用示例:
    - _rewrite_loop_staging_candidates(module, 2, "npu_demo")

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    candidate_items: list[_LoopRingCandidate] = []
    allowed_memory_op_names = {
        "dma.broadcast",
        "dma.copy",
        "dma.deslice",
        "dma.fill",
        "dma.load",
        "dma.slice",
        "dma.store",
        "dma.transpose",
        "kernel.binary_elewise",
        "kernel.img2col1d",
        "kernel.img2col2d",
        "kernel.matmul",
    }
    required_progress_op_names = {
        "dma.copy",
        "dma.deslice",
        "dma.slice",
        "dma.transpose",
        "kernel.img2col1d",
        "kernel.img2col2d",
        "kernel.matmul",
    }
    alias_types = (DmaReinterpretOp, DmaViewOp, DmaReshapeOp, DmaSubviewOp)
    for alloc_op in [op for op in module.walk() if isinstance(op, DmaAllocOp)]:
        slot_type = alloc_op.result.type
        if not isinstance(slot_type, NnMemoryType) or slot_type.element_type == i8:
            continue
        free_ops: list[DmaFreeOp] = []
        aliases: list[DmaReinterpretOp | DmaViewOp | DmaReshapeOp | DmaSubviewOp] = []
        direct_uses: list[tuple[Operation, int]] = []
        access_ops: list[Operation] = []
        unsupported = False
        saw_progress_use = False
        for use in tuple(alloc_op.result.uses):
            user = use.operation
            if isinstance(user, DmaFreeOp) and use.index == 0:
                free_ops.append(user)
                continue
            if isinstance(user, alias_types) and use.index == 0:
                aliases.append(user)
                access_ops.append(user)
                continue
            if isinstance(user, KernelMatmulOp) and use.index in {1, 2}:
                unsupported = True
                break
            if user.name not in allowed_memory_op_names:
                unsupported = True
                break
            if use.index >= len(user.operands) or not isinstance(user.operands[use.index].type, NnMemoryType):
                unsupported = True
                break
            direct_uses.append((user, use.index))
            access_ops.append(user)
            if user.name in required_progress_op_names:
                saw_progress_use = True
        if unsupported or len(free_ops) != 1:
            continue

        for alias in aliases:
            for use in tuple(alias.result.uses):
                user = use.operation
                if isinstance(user, alias_types):
                    unsupported = True
                    break
                if user.name not in allowed_memory_op_names:
                    unsupported = True
                    break
                if use.index >= len(user.operands) or not isinstance(user.operands[use.index].type, NnMemoryType):
                    unsupported = True
                    break
                access_ops.append(user)
                if user.name in required_progress_op_names:
                    saw_progress_use = True
            if unsupported:
                break
        if unsupported or not access_ops or not saw_progress_use:
            continue
        if not aliases and direct_uses and all(user.name == "dma.copy" for user, _index in direct_uses):
            continue

        nearest_loops: list[SymbolForOp] = []
        for access_op in access_ops:
            block = access_op.parent_block()
            nearest_loop: SymbolForOp | None = None
            while block is not None:
                parent = block.parent_op()
                if isinstance(parent, SymbolForOp):
                    nearest_loop = parent
                    break
                block = parent.parent_block() if parent is not None else None
            if nearest_loop is None:
                unsupported = True
                break
            nearest_loops.append(nearest_loop)
        if unsupported or not nearest_loops:
            continue
        target_loop = nearest_loops[0]
        if any(loop is not target_loop for loop in nearest_loops):
            continue
        target_body = target_loop.body.blocks[0]
        if any(isinstance(op, DmaCurrentRingOp) for op in target_body.ops):
            continue
        if any(access_op.parent_block() is not target_body for access_op in access_ops):
            continue

        alloc_block = alloc_op.parent_block()
        free_op = free_ops[0]
        free_block = free_op.parent_block()
        loop_parent = target_loop.parent_block()
        if alloc_block is None or free_block is None or loop_parent is None:
            continue
        target_indexes = {op: index for index, op in enumerate(target_body.ops)}
        if any(access_op not in target_indexes for access_op in access_ops):
            continue
        first_use = min(access_ops, key=lambda op: target_indexes[op])
        last_use = max(access_ops, key=lambda op: target_indexes[op])
        has_binary_elewise_access = any(
            isinstance(access_op, KernelBinaryElewiseOp) or access_op.name == "kernel.binary_elewise"
            for access_op in access_ops
        )

        insertion_block: Block
        insertion_anchor: Operation
        force_num_one = False
        if alloc_block is target_body and free_block is target_body:
            if alloc_op not in target_indexes or free_op not in target_indexes:
                continue
            if not (target_indexes[alloc_op] < target_indexes[first_use] <= target_indexes[last_use] < target_indexes[free_op]):
                continue
            insertion_block = target_body
            insertion_anchor = alloc_op
            force_num_one = True
        elif alloc_block is free_block:
            if has_binary_elewise_access:
                continue
            anchor = _MultiBufferRewriteRules.enclosing_op_in_block(target_loop, alloc_block)
            if anchor is None:
                continue
            parent_indexes = {op: index for index, op in enumerate(alloc_block.ops)}
            if alloc_op not in parent_indexes or anchor not in parent_indexes or free_op not in parent_indexes:
                continue
            if not (parent_indexes[alloc_op] < parent_indexes[anchor] < parent_indexes[free_op]):
                continue
            insertion_block = alloc_block
            insertion_anchor = anchor
        else:
            continue
        candidate_items.append(
            _MultiBufferRewriteRules.loop_ring_candidate(
                alloc_op=alloc_op,
                free_op=free_op,
                target_loop=target_loop,
                insertion_block=insertion_block,
                insertion_anchor=insertion_anchor,
                slot_type=slot_type,
                first_use=first_use,
                last_use=last_use,
                force_num_one=force_num_one,
                aliases=tuple(aliases),
                direct_uses=tuple(direct_uses),
            )
        )

    if not candidate_items:
        return

    grouped: dict[tuple[int, str, int, int, bool], list[_LoopRingCandidate]] = {}
    for candidate in candidate_items:
        space = candidate.slot_type.space.space.data
        grouped.setdefault(
            (
                id(candidate.target_loop),
                space,
                id(candidate.insertion_block),
                id(candidate.insertion_anchor),
                candidate.force_num_one,
            ),
            [],
        ).append(candidate)

    for group in grouped.values():
        insertion_block = group[0].insertion_block
        insertion_anchor = group[0].insertion_anchor
        insertion_indexes = {op: index for index, op in enumerate(insertion_block.ops)}
        if insertion_anchor not in insertion_indexes:
            continue
        pre_loop_ops: list[Operation] = []
        slot_values: dict[DmaAllocOp, _SymbolExprValue] = {}
        unavailable = False
        for candidate in group:
            element_type = candidate.slot_type.element_type
            element_size: int | None = None
            if isinstance(element_type, IntegerType):
                width = int(element_type.width.data)
                if width in {1, 8}:
                    element_size = 1
                elif width == 16:
                    element_size = 2
                elif width == 32:
                    element_size = 4
                elif width == 64:
                    element_size = 8
            elif isinstance(element_type, (Float16Type, BFloat16Type)):
                element_size = 2
            elif isinstance(element_type, Float32Type):
                element_size = 4
            elif isinstance(element_type, Float64Type):
                element_size = 8
            if element_size is None or element_size <= 0:
                unavailable = True
                break

            dim_items: list[_SymbolExprValue] = []
            dynamic_operands = list(candidate.alloc_op.dynamic_shape)
            for dim in candidate.slot_type.shape.data:
                if not isinstance(dim, SymbolExprAttr):
                    unavailable = True
                    break
                dim_expr = SymbolExprAttr.from_expr(dim.expr.data).expr.data
                if dim_expr.isdecimal():
                    dim_items.append((SymbolConstOp(int(dim_expr)).result, dim_expr, int(dim_expr)))
                    pre_loop_ops.append(SSAValue.get(dim_items[-1][0]).owner)
                    continue
                matched_operand: SSAValue | None = None
                for operand in dynamic_operands:
                    operand_value = SSAValue.get(operand)
                    operand_type = operand_value.type
                    if not isinstance(operand_type, SymbolValueType):
                        continue
                    operand_expr = SymbolExprAttr.from_expr(operand_type.expr.expr.data).expr.data
                    if operand_expr != dim_expr:
                        continue
                    owner = operand_value.owner
                    if isinstance(owner, Operation):
                        owner_block = owner.parent_block()
                        if owner_block is None:
                            matched_operand = None
                            break
                        available = False
                        if owner_block is insertion_block:
                            available = insertion_indexes.get(owner, 10**9) < insertion_indexes[insertion_anchor]
                        else:
                            scan_block = insertion_block
                            while scan_block is not None:
                                parent = scan_block.parent_op()
                                parent_block = parent.parent_block() if parent is not None else None
                                if parent_block is None:
                                    break
                                if owner_block is parent_block:
                                    parent_indexes = {op: index for index, op in enumerate(parent_block.ops)}
                                    available = parent_indexes.get(owner, 10**9) < parent_indexes.get(parent, -1)
                                    break
                                scan_block = parent_block
                        if not available:
                            matched_operand = None
                            break
                    else:
                        available = False
                        scan_block = insertion_block
                        while scan_block is not None:
                            if operand_value in scan_block.args:
                                available = True
                                break
                            parent = scan_block.parent_op()
                            scan_block = parent.parent_block() if parent is not None else None
                        if not available:
                            matched_operand = None
                            break
                    matched_operand = operand_value
                    break
                if matched_operand is None:
                    unavailable = True
                    break
                dim_items.append((matched_operand, dim_expr, None))
            if unavailable or not dim_items:
                break

            elements = dim_items[0]
            for dim_value in dim_items[1:]:
                lhs_value, lhs_expr, lhs_static = elements
                rhs_value, rhs_expr, rhs_static = dim_value
                if lhs_static is not None and rhs_static is not None:
                    value = lhs_static * rhs_static
                    const_op = SymbolConstOp(value)
                    pre_loop_ops.append(const_op)
                    elements = (const_op.result, str(value), value)
                else:
                    result_expr = SymbolExprAttr.from_expr(f"({lhs_expr})*({rhs_expr})").expr.data
                    mul_op = SymbolMulOp(lhs_value, rhs_value, SymbolValueType.from_expr(result_expr))
                    pre_loop_ops.append(mul_op)
                    elements = (mul_op.result, result_expr, None)

            elements_value, elements_expr, elements_static = elements
            if element_size == 1:
                slot_values[candidate.alloc_op] = elements
            elif elements_static is not None:
                value = elements_static * element_size
                const_op = SymbolConstOp(value)
                pre_loop_ops.append(const_op)
                slot_values[candidate.alloc_op] = (const_op.result, str(value), value)
            else:
                bpe = SymbolConstOp(element_size)
                result_expr = SymbolExprAttr.from_expr(f"({element_size})*({elements_expr})").expr.data
                mul_op = SymbolMulOp(elements_value, bpe.result, SymbolValueType.from_expr(result_expr))
                pre_loop_ops.extend([bpe, mul_op])
                slot_values[candidate.alloc_op] = (mul_op.result, result_expr, None)
        if unavailable or any(candidate.alloc_op not in slot_values for candidate in group):
            continue

        if target is None:
            num_const = SymbolConstOp(memory_stage)
            pre_loop_ops.append(num_const)
            shared_num: _SymbolExprValue = (num_const.result, str(memory_stage), memory_stage)
        elif any(candidate.force_num_one for candidate in group):
            num_const = SymbolConstOp(1)
            pre_loop_ops.append(num_const)
            shared_num = (num_const.result, "1", 1)
        elif _MultiBufferRewriteRules.target_body_has_unringed_same_space_allocs(group):
            num_const = SymbolConstOp(1)
            pre_loop_ops.append(num_const)
            shared_num = (num_const.result, "1", 1)
        else:
            capacity = get_target_hardware(target, f"{group[0].slot_type.space.space.data}_memory_size")
            if capacity is None or capacity <= 0:
                continue
            reserved_value, reserved_available = _MultiBufferRewriteRules.reserved_space_bytes_for_group(
                group,
                insertion_block,
                insertion_anchor,
                pre_loop_ops,
            )
            if not reserved_available:
                continue
            if reserved_value is None:
                capacity_result: SSAValue | None = None
                capacity_expr = str(capacity)
                capacity_static: int | None = capacity
            else:
                aligned_reserved = _MultiBufferRewriteRules.align_up_symbol_value(reserved_value, 1024, pre_loop_ops)
                reserved_result, reserved_expr, reserved_static = aligned_reserved
                if reserved_static is not None:
                    remaining_capacity = capacity - reserved_static
                    if remaining_capacity <= 0:
                        continue
                    capacity_const = SymbolConstOp(remaining_capacity)
                    pre_loop_ops.append(capacity_const)
                    capacity_result = capacity_const.result
                    capacity_expr = str(remaining_capacity)
                    capacity_static = remaining_capacity
                else:
                    capacity_const = SymbolConstOp(capacity)
                    capacity_expr = SymbolExprAttr.from_expr(f"({capacity}) - ({reserved_expr})").expr.data
                    capacity_sub = SymbolSubOp(capacity_const.result, reserved_result, SymbolValueType.from_expr(capacity_expr))
                    pre_loop_ops.extend([capacity_const, capacity_sub])
                    capacity_result = capacity_sub.result
                    capacity_static = None
            total_value = _MultiBufferRewriteRules.aligned_group_slot_bytes_value(group, slot_values, pre_loop_ops)
            if total_value is None:
                continue
            total_result, total_expr, total_static = total_value
            if total_static is not None and capacity_static is not None:
                if total_static <= 0:
                    continue
                num_value = capacity_static // total_static
                if num_value <= 0:
                    continue
                num_const = SymbolConstOp(num_value)
                pre_loop_ops.append(num_const)
                shared_num = (num_const.result, str(num_value), num_value)
            else:
                if capacity_result is None:
                    capacity_const = SymbolConstOp(capacity)
                    pre_loop_ops.append(capacity_const)
                    capacity_result = capacity_const.result
                num_expr = SymbolExprAttr.from_expr(f"({capacity_expr}) floordiv ({total_expr})").expr.data
                num_op = SymbolFloorDivOp(capacity_result, total_result, SymbolValueType.from_expr(num_expr))
                pre_loop_ops.append(num_op)
                shared_num = (num_op.result, num_expr, None)

        current_ops: dict[DmaAllocOp, DmaCurrentRingOp] = {}
        advance_ops: dict[DmaAllocOp, DmaAdvanceRingOp] = {}
        for candidate in group:
            num_result, num_expr, num_static = shared_num
            slot_result, slot_expr, slot_static = slot_values[candidate.alloc_op]
            if num_static is not None and slot_static is not None:
                backing_value = num_static * slot_static
                backing_const = SymbolConstOp(backing_value)
                pre_loop_ops.append(backing_const)
                backing_result = backing_const.result
                backing_expr = str(backing_value)
                backing_static = backing_value
            else:
                backing_expr = SymbolExprAttr.from_expr(f"({num_expr})*({slot_expr})").expr.data
                backing_mul = SymbolMulOp(num_result, slot_result, SymbolValueType.from_expr(backing_expr))
                pre_loop_ops.append(backing_mul)
                backing_result = backing_mul.result
                backing_static = None
            backing_type = NnMemoryType(
                ArrayAttr([SymbolExprAttr.from_expr(backing_expr)]),
                ArrayAttr([SymbolExprAttr.from_expr("1")]),
                i8,
                candidate.slot_type.space,
            )
            backing_shape = [] if backing_static is not None else [backing_result]
            backing = DmaAllocOp(backing_shape, backing_type)
            make_ring = DmaMakeRingOp(backing.result, num_result, slot_result, DmaRingType(candidate.slot_type))
            current = DmaCurrentRingOp(make_ring.result)
            advance = DmaAdvanceRingOp(make_ring.result)
            pre_loop_ops.extend([backing, make_ring])
            current_ops[candidate.alloc_op] = current
            advance_ops[candidate.alloc_op] = advance

        insertion_block.insert_ops_before(pre_loop_ops, insertion_anchor)
        for candidate in group:
            current = current_ops[candidate.alloc_op]
            first_block = candidate.first_use.parent_block()
            last_block = candidate.last_use.parent_block()
            if first_block is None or last_block is None or first_block is not last_block:
                continue
            first_block.insert_ops_before([current], candidate.first_use)
            for alias in candidate.aliases:
                alias.operands[0] = current.result
            for user, index in candidate.direct_uses:
                user.operands[index] = current.result
            last_block.insert_ops_after([advance_ops[candidate.alloc_op]], candidate.last_use)
            free_block = candidate.free_op.parent_block()
            alloc_block = candidate.alloc_op.parent_block()
            if free_block is not None:
                free_block.erase_op(candidate.free_op)
            if alloc_block is not None:
                alloc_block.erase_op(candidate.alloc_op)


@dataclass(frozen=True)
class MultiBufferPass(Pass):
    """multi-buffer pass。

    功能说明:
    - 将可证明的 matmul lhs/rhs staging pair 或 loop staging / scratch 生命周期改写为 `dma.ring`。
    - 默认 `memory_stage=2`，当 `target` 非空时优先按 target registry 容量计算 ring num。
    - 只处理 direct alias / direct memory use 均落在同一 `symbol.for` 直接 body 的公开模式。

    使用示例:
    - MultiBufferPass(memory_stage=2, target="npu_demo").apply(Context(), module)

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    name = "multi-buffer"
    memory_stage: int = 2
    fold: bool = True
    target: str | None = None

    def __init__(self, memory_stage: int = 2, fold: bool = True, target: str | None = None) -> None:
        """初始化 multi-buffer pass。

        功能说明:
        - 保存 ring stage 数、通用 fold 开关和可选 target 名称。

        使用示例:
        - pass_obj = MultiBufferPass(memory_stage=2, fold=False, target="npu_demo")

        关联文件:
        - spec: spec/pass/memory/multi_buffer.md
        - test: test/passes/memory/test_multi_buffer.py
        - 功能实现: kernel_gen/passes/memory/multi_buffer.py
        """

        if isinstance(memory_stage, bool) or not isinstance(memory_stage, int):
            raise_pass_contract_error("MultiBufferOptionError", "memory_stage must be integer")
        if memory_stage <= 0:
            raise_pass_contract_error("MultiBufferOptionError", "memory_stage must be positive")
        if target is not None and (not isinstance(target, str) or not target.strip()):
            raise_pass_contract_error("MultiBufferOptionError", "target must be non-empty")
        object.__setattr__(self, "memory_stage", memory_stage)
        object.__setattr__(self, "fold", bool(fold))
        object.__setattr__(self, "target", target.strip() if isinstance(target, str) else None)

    @classmethod
    def from_options(cls, options: dict[str, str]) -> "MultiBufferPass":
        """从 pass registry options 构造 multi-buffer pass。

        功能说明:
        - 接受 pass 专属 `memory-stage` 与 `target`。
        - `fold` 必须由 registry 通用选项处理，传到本方法时按未知 option 失败。

        使用示例:
        - pass_obj = MultiBufferPass.from_options({"memory-stage": "2", "target": "npu_demo"})

        关联文件:
        - spec: spec/pass/memory/multi_buffer.md
        - test: test/passes/memory/test_multi_buffer.py
        - 功能实现: kernel_gen/passes/memory/multi_buffer.py
        """

        allowed = {"memory-stage", "target"}
        unknown = sorted(set(options) - allowed)
        if unknown:
            raise_pass_contract_error("MultiBufferOptionError", f"unknown option: {unknown[0]}")
        memory_stage = 2
        if "memory-stage" in options:
            memory_stage = _parse_memory_stage_option(options["memory-stage"])
        target = None
        if "target" in options:
            target = options["target"].strip()
            if not target:
                raise_pass_contract_error("MultiBufferOptionError", "target must be non-empty")
        return cls(memory_stage=memory_stage, target=target)

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 multi-buffer rewrite。

        功能说明:
        - 先保留旧 direct matmul lhs/rhs 成对 staging 兼容路径。
        - 再逐个分析 direct alias / direct use alloc 候选，改写可证明 loop-local 生命周期。
        - 不满足条件的结构保持 no-op。

        使用示例:
        - MultiBufferPass().apply(Context(), module)

        关联文件:
        - spec: spec/pass/memory/multi_buffer.md
        - test: test/passes/memory/test_multi_buffer.py
        - 功能实现: kernel_gen/passes/memory/multi_buffer.py
        """

        _ = ctx
        ensure_builtin_module(module)
        for symbol_for in [op for op in module.walk() if isinstance(op, SymbolForOp)]:
            loop_block = symbol_for.body.blocks[0]
            for op in list(loop_block.ops):
                if isinstance(op, KernelMatmulOp):
                    _rewrite_matmul_if_pair(symbol_for, op, self.memory_stage, self.target)
        _rewrite_loop_staging_candidates(module, self.memory_stage, self.target)


__all__ = ["MultiBufferPass"]
