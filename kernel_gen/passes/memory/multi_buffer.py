"""multi-buffer pass.


功能说明:
- 提供 `multi-buffer-analysis`、`multi-buffer-apply` 和兼容 `multi-buffer` pass。
- analysis 阶段只把可证明的 staging buffer 标记为三项 `multi_buffer.*` 临时属性。
- apply 阶段消费三项属性并把对应 typed alloc/free 生命周期改写为 DMA ring。
- 匹配同一 `symbol.for` 外或 loop-local 的 `dma.alloc/free` 与 loop body 内的
  direct alias / direct memory use 生命周期。
- 对不满足公开边界的 IR 保持 no-op，不引入宽泛 alias 或跨 region 推断。

API 列表:
- `class MultiBufferAnalysisPass(memory_stage: int = 2, fold: bool = True, target: str | None = None)`
- `MultiBufferAnalysisPass.from_options(options: dict[str, str]) -> MultiBufferAnalysisPass`
- `MultiBufferAnalysisPass.apply(ctx: Context, module: ModuleOp) -> None`
- `class MultiBufferApplyPass(fold: bool = True, target: str | None = None, alignment: int = 1024)`
- `MultiBufferApplyPass.from_options(options: dict[str, str]) -> MultiBufferApplyPass`
- `MultiBufferApplyPass.apply(ctx: Context, module: ModuleOp) -> None`
- `class MultiBufferPass(memory_stage: int = 2, fold: bool = True, target: str | None = None, alignment: int = 1024)`
- `MultiBufferPass.from_options(options: dict[str, str]) -> MultiBufferPass`
- `MultiBufferPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.memory.multi_buffer import MultiBufferAnalysisPass, MultiBufferApplyPass
- MultiBufferAnalysisPass(memory_stage=2, target="npu_demo").apply(Context(), module)
- MultiBufferApplyPass(target="npu_demo", alignment=1024).apply(Context(), module)

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
    StringAttr,
    UnregisteredOp,
    i8,
)
from xdsl.ir import Attribute, Block, Operation, SSAValue
from xdsl.traits import IsTerminator

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
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.passes.common import ensure_builtin_module, raise_pass_contract_error
from kernel_gen.passes.pass_manager import Pass
from kernel_gen.target.registry import get_target_hardware


_SymbolExprValue = tuple[SSAValue, str, int | None]
_StagingCandidate = tuple[DmaAllocOp, DmaCopyOp, DmaFreeOp, KernelMatmulOp, int, NnMemoryType, int | None]
_RingRewriteOps = tuple[DmaCurrentRingOp, DmaAdvanceRingOp]
_MultiBufferMode = str

_MULTI_BUFFER_UPDATE_POINT_ATTR = "multi_buffer.update_point"
_MULTI_BUFFER_USE_POINT_ATTR = "multi_buffer.use_point"
_MULTI_BUFFER_NUM_ATTR = "multi_buffer.num"
_MULTI_BUFFER_ANALYSIS_ATTRS = (
    _MULTI_BUFFER_UPDATE_POINT_ATTR,
    _MULTI_BUFFER_USE_POINT_ATTR,
    _MULTI_BUFFER_NUM_ATTR,
)


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
    def symbol_binary_op(op_name: str, lhs: SSAValue, rhs: SSAValue, result_expr: str) -> Operation:
        """构造 generic symbol binary op。

        功能说明:
        - 生成 xDSL generic 形式的 `"symbol.add"` / `"symbol.sub"` / `"symbol.mul"` / `"symbol.floordiv"`。
        - 保留 result type 的 `SymbolExprAttr`，让后续 DMA ring operands 仍具备公开 `!symbol.int` 类型。

        使用示例:
        - op = _MultiBufferRewriteRules.symbol_binary_op("symbol.add", lhs, rhs, "A + B")
        """

        generic_op = UnregisteredOp.with_name(op_name)
        result_type = SymbolValueType.from_expr(result_expr)
        operands = [lhs, rhs]
        result_types = [result_type]
        return generic_op.create(operands=operands, result_types=result_types)

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
        add_op = _MultiBufferRewriteRules.symbol_binary_op("symbol.add", lhs_value, rhs_value, result_expr)
        materialized_ops.append(add_op)
        return (add_op.results[0], result_expr, None)

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
        numerator_op = _MultiBufferRewriteRules.symbol_binary_op("symbol.add", value_result, mask_op.result, numerator_expr)
        alignment_op = SymbolConstOp(alignment)
        div_expr = SymbolExprAttr.from_expr(f"({numerator_expr}) floordiv ({alignment})").expr.data
        div_op = _MultiBufferRewriteRules.symbol_binary_op(
            "symbol.floordiv",
            numerator_op.results[0],
            alignment_op.result,
            div_expr,
        )
        aligned_expr = SymbolExprAttr.from_expr(f"({div_expr})*({alignment})").expr.data
        aligned_op = _MultiBufferRewriteRules.symbol_binary_op(
            "symbol.mul",
            div_op.results[0],
            alignment_op.result,
            aligned_expr,
        )
        materialized_ops.extend([mask_op, numerator_op, alignment_op, div_op, aligned_op])
        return (aligned_op.results[0], aligned_expr, None)

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
                mul_op = _MultiBufferRewriteRules.symbol_binary_op("symbol.mul", lhs_value, rhs_value, result_expr)
                materialized_ops.append(mul_op)
                elements = (mul_op.results[0], result_expr, None)
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
        mul_op = _MultiBufferRewriteRules.symbol_binary_op("symbol.mul", elements_value, bpe.result, result_expr)
        materialized_ops.extend([bpe, mul_op])
        return (mul_op.results[0], result_expr, None)

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

    @staticmethod
    def region_labels(module: ModuleOp) -> dict[SymbolForOp, str]:
        """为 module 内 `symbol.for` 分配稳定 analysis region 标签。

        功能说明:
        - 按 module walk 顺序生成 `loop1`、`loop2` 等标签。
        - analysis 与 apply 使用同一规则复核 `multi_buffer.update_point/use_point`。

        使用示例:
        - labels = _MultiBufferRewriteRules.region_labels(module)
        """

        labels: dict[SymbolForOp, str] = {}
        loop_index = 1
        for op in module.walk():
            if not isinstance(op, SymbolForOp):
                continue
            labels[op] = f"loop{loop_index}"
            loop_index += 1
        return labels

    @staticmethod
    def write_multi_buffer_attrs(alloc_op: DmaAllocOp, update_point: str, use_point: str, num: str) -> None:
        """写入 multi-buffer analysis 三项临时属性。

        功能说明:
        - 只在 `dma.alloc` 上写 `update_point`、`use_point`、`num` 三个 `StringAttr`。
        - 不插入、删除或替换任何业务 IR。

        使用示例:
        - _MultiBufferRewriteRules.write_multi_buffer_attrs(alloc_op, "loop1", "loop1", "auto")
        """

        attrs = alloc_op.attributes
        attrs[_MULTI_BUFFER_UPDATE_POINT_ATTR] = StringAttr(update_point)
        attrs[_MULTI_BUFFER_USE_POINT_ATTR] = StringAttr(use_point)
        attrs[_MULTI_BUFFER_NUM_ATTR] = StringAttr(num)
        alloc_op.attributes = attrs

    @staticmethod
    def read_multi_buffer_attrs(alloc_op: DmaAllocOp) -> tuple[str, str, str] | None:
        """读取 multi-buffer analysis 三项临时属性。

        功能说明:
        - 三项属性都存在且都是 `StringAttr` 时返回文本三元组。
        - 缺失或类型不匹配时返回 `None`，由 apply 保持 no-op。

        使用示例:
        - attrs = _MultiBufferRewriteRules.read_multi_buffer_attrs(alloc_op)
        """

        values: list[str] = []
        for attr_name in _MULTI_BUFFER_ANALYSIS_ATTRS:
            attr = alloc_op.attributes.get(attr_name)
            if not isinstance(attr, StringAttr):
                return None
            values.append(attr.data)
        return (values[0], values[1], values[2])

    @staticmethod
    def analysis_num(memory_stage: int, target: str | None, force_num_one: bool) -> str:
        """计算 analysis 写入的 `multi_buffer.num` 文本。

        功能说明:
        - loop-local 强制写 `"1"`。
        - target 非空时 same-loop staging 写 `"auto"`，否则写固定 `memory_stage`。

        使用示例:
        - num = _MultiBufferRewriteRules.analysis_num(2, "npu_demo", False)
        """

        if force_num_one:
            return "1"
        if target is not None:
            return "auto"
        return str(memory_stage)

    @staticmethod
    def parse_multi_buffer_num_attr(value: str) -> int | None | str:
        """解析 `multi_buffer.num` 临时属性。

        功能说明:
        - `"auto"` 原样返回，由 apply target 容量逻辑处理。
        - 正整数字符串返回对应整数；其它文本返回 `None` 表示候选 no-op。

        使用示例:
        - parsed = _MultiBufferRewriteRules.parse_multi_buffer_num_attr("auto")
        """

        if value == "auto":
            return "auto"
        if not value.isdecimal():
            return None
        parsed = int(value)
        if parsed <= 0:
            return None
        return parsed


def _parse_alignment_option(value: str) -> int:
    """解析 `alignment` pass option。

    功能说明:
    - 将 registry 传入的字符串解析成非负整数 alignment。
    - 非整数或负数按公开 `MultiBufferOptionError` 稳定错误文本失败。

    使用示例:
    - alignment = _parse_alignment_option("1024")
    """

    try:
        alignment = int(value.strip())
    except ValueError as exc:
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.PASS,
            "MultiBufferOptionError: alignment must be non-negative integer",
        ) from exc
    if alignment < 0:
        raise_pass_contract_error("MultiBufferOptionError", "alignment must be non-negative integer")
    return alignment


def _validate_alignment_value(alignment: int) -> int:
    """校验公开构造器传入的 alignment。

    功能说明:
    - 接受非负整数，拒绝 `bool`、非整数和负数。
    - 返回规范化后的 int 值。

    使用示例:
    - alignment = _validate_alignment_value(1024)
    """

    if isinstance(alignment, bool):
        raise_pass_contract_error("MultiBufferOptionError", "alignment must be non-negative integer")
    if not isinstance(alignment, int):
        raise_pass_contract_error("MultiBufferOptionError", "alignment must be non-negative integer")
    if alignment < 0:
        raise_pass_contract_error("MultiBufferOptionError", "alignment must be non-negative integer")
    normalized_alignment = alignment
    return normalized_alignment


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
    *,
    mode: _MultiBufferMode = "rewrite",
    alignment: int = 1024,
    region_label: str = "loop1",
) -> bool:
    """尝试把单个 matmul 的 lhs/rhs staging 成对 ring 化。

    功能说明:
    - lhs/rhs 任一缺失或失败时整对 no-op，避免 partial ring。
    - `analysis` 模式只写三项临时属性；`apply` 模式只消费已有三项属性。
    - ring offset 和 backing bytes 使用 `alignment` 后的 slot bytes。

    使用示例:
    - changed = _rewrite_matmul_if_pair(symbol_for, matmul, 2, None, mode="analysis")

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
    if any(isinstance(op, DmaCurrentRingOp) for op in loop_block.ops):
        return False
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

    if mode == "analysis":
        num = _MultiBufferRewriteRules.analysis_num(memory_stage, target, False)
        for candidate in candidate_pair:
            alloc_op, _copy_op, _free_op, _matmul_op, _operand_index, _slot_type, _slot_bytes = candidate
            _MultiBufferRewriteRules.write_multi_buffer_attrs(alloc_op, region_label, region_label, num)
        return True

    parsed_num_attrs: list[int | str] = []
    if mode == "apply":
        for candidate in candidate_pair:
            alloc_op, _copy_op, _free_op, _matmul_op, _operand_index, _slot_type, _slot_bytes = candidate
            attrs = _MultiBufferRewriteRules.read_multi_buffer_attrs(alloc_op)
            if attrs is None:
                return False
            update_point, use_point, raw_num = attrs
            if update_point != region_label or use_point != region_label:
                return False
            parsed = _MultiBufferRewriteRules.parse_multi_buffer_num_attr(raw_num)
            if parsed is None:
                return False
            parsed_num_attrs.append(parsed)
    elif target is None:
        parsed_num_attrs = [memory_stage, memory_stage]
    else:
        parsed_num_attrs = ["auto", "auto"]

    pre_loop_ops: list[Operation] = []
    rewrite_ops: list[_RingRewriteOps] = []
    slot_values: list[_SymbolExprValue] = []
    aligned_slot_values: list[_SymbolExprValue] = []
    for candidate in candidate_pair:
        alloc_op, _copy_op, _free_op, _matmul_op, _operand_index, _slot_type, _slot_bytes = candidate
        slot_value = _MultiBufferRewriteRules.alloc_slot_byte_value(alloc_op, pre_loop_ops)
        if slot_value is None:
            return False
        aligned_slot = _MultiBufferRewriteRules.align_up_symbol_value(slot_value, alignment, pre_loop_ops)
        slot_values.append(slot_value)
        aligned_slot_values.append(aligned_slot)

    num_values: list[_SymbolExprValue | None] = [None, None]
    fixed_reserved_by_space: dict[str, _SymbolExprValue] = {}
    external_fixed_slots_by_space: dict[str, list[tuple[int, _SymbolExprValue]]] = {}
    for index, (candidate, parsed_num, aligned_slot) in enumerate(
        zip(candidate_pair, parsed_num_attrs, aligned_slot_values, strict=True)
    ):
        _alloc_op, _copy_op, _free_op, _matmul_op, _operand_index, slot_type, _slot_bytes = candidate
        if isinstance(parsed_num, int):
            num_const = SymbolConstOp(parsed_num)
            pre_loop_ops.append(num_const)
            num_value: _SymbolExprValue = (num_const.result, str(parsed_num), parsed_num)
            num_values[index] = num_value
            num_result, num_expr, num_static = num_value
            aligned_result, aligned_expr, aligned_static = aligned_slot
            if num_static is not None and aligned_static is not None:
                reserved_value = num_static * aligned_static
                reserved_const = SymbolConstOp(reserved_value)
                pre_loop_ops.append(reserved_const)
                reserved: _SymbolExprValue = (reserved_const.result, str(reserved_value), reserved_value)
            else:
                reserved_expr = SymbolExprAttr.from_expr(f"({num_expr})*({aligned_expr})").expr.data
                reserved_op = _MultiBufferRewriteRules.symbol_binary_op(
                    "symbol.mul",
                    num_result,
                    aligned_result,
                    reserved_expr,
                )
                pre_loop_ops.append(reserved_op)
                reserved = (reserved_op.results[0], reserved_expr, None)
            space = slot_type.space.space.data
            fixed_reserved_by_space[space] = (
                reserved
                if space not in fixed_reserved_by_space
                else _MultiBufferRewriteRules.add_symbol_values(fixed_reserved_by_space[space], reserved, pre_loop_ops)
            )

    if any(parsed_num == "auto" for parsed_num in parsed_num_attrs):
        if target is None:
            return False
        candidate_allocs = {candidate[0] for candidate in candidate_pair}
        symbol_for_index = parent_indexes.get(symbol_for)
        if symbol_for_index is None:
            return False
        for op in tuple(parent_block.ops):
            op_index = parent_indexes.get(op)
            if op_index is None or op_index >= symbol_for_index:
                continue
            if not isinstance(op, DmaAllocOp) or op in candidate_allocs:
                continue
            attrs = _MultiBufferRewriteRules.read_multi_buffer_attrs(op)
            if attrs is None:
                continue
            _update_point, _use_point, raw_num = attrs
            parsed = _MultiBufferRewriteRules.parse_multi_buffer_num_attr(raw_num)
            if not isinstance(parsed, int):
                continue
            op_type = op.result.type
            if not isinstance(op_type, NnMemoryType):
                continue
            slot_value = _MultiBufferRewriteRules.alloc_slot_byte_value(op, pre_loop_ops)
            if slot_value is None:
                return False
            space = op_type.space.space.data
            external_fixed_slots_by_space.setdefault(space, []).append((parsed, slot_value))

    auto_groups: dict[str, list[int]] = {}
    for index, (candidate, parsed_num) in enumerate(zip(candidate_pair, parsed_num_attrs, strict=True)):
        if parsed_num != "auto":
            continue
        _alloc_op, _copy_op, _free_op, _matmul_op, _operand_index, slot_type, _slot_bytes = candidate
        auto_groups.setdefault(slot_type.space.space.data, []).append(index)

    for space, indexes in auto_groups.items():
        capacity = get_target_hardware(target, f"{space}_memory_size") if target is not None else None
        if capacity is None or capacity <= 0:
            return False
        capacity_const = SymbolConstOp(capacity)
        pre_loop_ops.append(capacity_const)
        reserved = fixed_reserved_by_space.get(space)
        for parsed, slot_value in external_fixed_slots_by_space.get(space, []):
            aligned_slot = _MultiBufferRewriteRules.align_up_symbol_value(slot_value, alignment, pre_loop_ops)
            aligned_result, aligned_expr, aligned_static = aligned_slot
            if aligned_static is not None:
                reserved_value = parsed * aligned_static
                reserved_const = SymbolConstOp(reserved_value)
                pre_loop_ops.append(reserved_const)
                external_reserved: _SymbolExprValue = (reserved_const.result, str(reserved_value), reserved_value)
            else:
                num_const = SymbolConstOp(parsed)
                reserved_expr = SymbolExprAttr.from_expr(f"({parsed})*({aligned_expr})").expr.data
                reserved_op = _MultiBufferRewriteRules.symbol_binary_op(
                    "symbol.mul",
                    num_const.result,
                    aligned_result,
                    reserved_expr,
                )
                pre_loop_ops.extend([num_const, reserved_op])
                external_reserved = (reserved_op.results[0], reserved_expr, None)
            reserved = (
                external_reserved
                if reserved is None
                else _MultiBufferRewriteRules.add_symbol_values(reserved, external_reserved, pre_loop_ops)
            )
        if reserved is None:
            capacity_value: _SymbolExprValue = (capacity_const.result, str(capacity), capacity)
        else:
            reserved_result, reserved_expr, reserved_static = reserved
            if reserved_static is not None:
                available_static = capacity - reserved_static
                if available_static <= 0:
                    return False
                capacity_const = SymbolConstOp(available_static)
                pre_loop_ops.append(capacity_const)
                capacity_value = (capacity_const.result, str(available_static), available_static)
            else:
                available_expr = SymbolExprAttr.from_expr(f"({capacity}) - ({reserved_expr})").expr.data
                available_op = _MultiBufferRewriteRules.symbol_binary_op(
                    "symbol.sub",
                    capacity_const.result,
                    reserved_result,
                    available_expr,
                )
                pre_loop_ops.append(available_op)
                capacity_value = (available_op.results[0], available_expr, None)

        for index in indexes:
            aligned_slot_values[index] = _MultiBufferRewriteRules.align_up_symbol_value(
                slot_values[index],
                alignment,
                pre_loop_ops,
            )
        group_unit = aligned_slot_values[indexes[0]]
        for index in indexes[1:]:
            group_unit = _MultiBufferRewriteRules.add_symbol_values(group_unit, aligned_slot_values[index], pre_loop_ops)
        unit_result, unit_expr, unit_static = group_unit
        capacity_result, capacity_expr, capacity_static = capacity_value
        if unit_static is not None and capacity_static is not None:
            if unit_static <= 0:
                return False
            auto_num = capacity_static // unit_static
            if auto_num <= 0:
                return False
            num_const = SymbolConstOp(auto_num)
            pre_loop_ops.append(num_const)
            num_value = (num_const.result, str(auto_num), auto_num)
        else:
            num_expr = SymbolExprAttr.from_expr(f"({capacity_expr}) floordiv ({unit_expr})").expr.data
            num_op = _MultiBufferRewriteRules.symbol_binary_op(
                "symbol.floordiv",
                capacity_result,
                unit_result,
                num_expr,
            )
            pre_loop_ops.append(num_op)
            num_value = (num_op.results[0], num_expr, None)
        for index in indexes:
            num_values[index] = num_value

    if any(num_value is None for num_value in num_values):
        return False

    for candidate, num_value, aligned_slot in zip(candidate_pair, num_values, aligned_slot_values, strict=True):
        if num_value is None:
            return False
        _alloc_op, _copy_op, _free_op, _matmul_op, _operand_index, slot_type, _slot_bytes = candidate
        num_result, num_expr, num_static = num_value
        aligned_result, aligned_expr, aligned_static = aligned_slot
        if num_static is not None and aligned_static is not None:
            backing_static = num_static * aligned_static
            backing_const = SymbolConstOp(backing_static)
            pre_loop_ops.append(backing_const)
            backing_result = backing_const.result
            backing_expr = str(backing_static)
        else:
            backing_expr = SymbolExprAttr.from_expr(f"({num_expr})*({aligned_expr})").expr.data
            backing_op = _MultiBufferRewriteRules.symbol_binary_op(
                "symbol.mul",
                num_result,
                aligned_result,
                backing_expr,
            )
            pre_loop_ops.append(backing_op)
            backing_result = backing_op.results[0]
            backing_static = None
        backing_type = NnMemoryType(
            ArrayAttr([SymbolExprAttr.from_expr(backing_expr)]),
            ArrayAttr([SymbolExprAttr.from_expr("1")]),
            i8,
            slot_type.space,
        )
        dynamic_shape = [] if backing_static is not None else [backing_result]
        backing = DmaAllocOp(dynamic_shape, backing_type)
        offset_result = aligned_result
        if aligned_static is not None:
            offset_const = SymbolConstOp(aligned_static)
            pre_loop_ops.append(offset_const)
            offset_result = offset_const.result
        make_ring = DmaMakeRingOp(backing.result, num_result, offset_result, DmaRingType(slot_type))
        current = DmaCurrentRingOp(make_ring.result)
        advance = DmaAdvanceRingOp(make_ring.result)
        pre_loop_ops.extend([backing, make_ring])
        rewrite_ops.append((current, advance))

    parent_block.insert_ops_before(pre_loop_ops, symbol_for)
    current_insert_anchor = list(loop_block.ops)[0]
    loop_block.insert_ops_before([ops[0] for ops in rewrite_ops], current_insert_anchor)
    for candidate, ops in zip(candidate_pair, rewrite_ops, strict=True):
        alloc_op, _copy_op, free_op, _matmul_op, _operand_index, _slot_type, _slot_bytes = candidate
        current_op, _advance_op = ops
        for use in tuple(alloc_op.result.uses):
            if use.operation is free_op:
                continue
            use.operation.operands[use.index] = current_op.result
    advance_ops = [rewrite_ops[0][1], rewrite_ops[1][1]]
    loop_tail = loop_block.last_op
    if loop_tail is not None and loop_tail.has_trait(IsTerminator):
        loop_block.insert_ops_before(advance_ops, loop_tail)
    else:
        loop_block.add_ops(advance_ops)
    for candidate in candidate_pair:
        alloc_op, _copy_op, free_op, _matmul_op, _operand_index, _slot_type, _slot_bytes = candidate
        free_block = free_op.parent_block()
        alloc_block = alloc_op.parent_block()
        if free_block is not None:
            free_block.erase_op(free_op)
        if alloc_block is not None:
            alloc_block.erase_op(alloc_op)
    return True


def _rewrite_loop_staging_candidates(
    module: ModuleOp,
    memory_stage: int,
    target: str | None,
    *,
    mode: _MultiBufferMode = "rewrite",
    alignment: int = 1024,
    region_labels: dict[SymbolForOp, str] | None = None,
    existing_current_block_ids: set[int] | None = None,
) -> None:
    """按 alloc 生命周期改写 direct alias / direct use staging。

    功能说明:
    - 逐个分析 `dma.alloc` 的 direct alias 与 direct memory use。
    - 仅当所有访问都落在同一个 `symbol.for` 直接 body 时 ring 化，避免 nested region 误判。
    - 旧 matmul lhs/rhs direct alloc pair 仍由 `_rewrite_matmul_if_pair` 兼容路径处理。
    - `analysis` 模式只写三项属性；`apply` 模式只消费三项属性并使用 aligned slot 物化 ring。
    - apply 物化时把 setup/current 放到 use block 第一条既有 op 前；若 dynamic setup 无法在该点被支配则 no-op。
    - `existing_current_block_ids` 只表示本次 apply 入口前已有 current，用于避免重复 ring。

    使用示例:
    - _rewrite_loop_staging_candidates(module, 2, "npu_demo", mode="apply")

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    labels = region_labels if region_labels is not None else _MultiBufferRewriteRules.region_labels(module)
    current_block_ids = existing_current_block_ids
    if current_block_ids is None:
        current_block_ids = set()
        for current_op in [op for op in module.walk() if isinstance(op, DmaCurrentRingOp)]:
            current_block = current_op.parent_block()
            if current_block is not None:
                current_block_ids.add(id(current_block))
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
        if id(target_body) in current_block_ids:
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

    if mode == "analysis":
        for candidate in candidate_items:
            region_label = labels.get(candidate.target_loop, "loop1")
            num = _MultiBufferRewriteRules.analysis_num(memory_stage, target, candidate.force_num_one)
            _MultiBufferRewriteRules.write_multi_buffer_attrs(candidate.alloc_op, region_label, region_label, num)
        return

    parsed_num_attrs: dict[DmaAllocOp, int | str] = {}
    if mode == "apply":
        filtered_candidates: list[_LoopRingCandidate] = []
        for candidate in candidate_items:
            attrs = _MultiBufferRewriteRules.read_multi_buffer_attrs(candidate.alloc_op)
            if attrs is None:
                continue
            update_point, use_point, raw_num = attrs
            region_label = labels.get(candidate.target_loop, "loop1")
            if update_point != region_label or use_point != region_label:
                continue
            parsed = _MultiBufferRewriteRules.parse_multi_buffer_num_attr(raw_num)
            if parsed is None:
                continue
            parsed_num_attrs[candidate.alloc_op] = parsed
            filtered_candidates.append(candidate)
        candidate_items = filtered_candidates
    else:
        for candidate in candidate_items:
            parsed_num_attrs[candidate.alloc_op] = _MultiBufferRewriteRules.analysis_num(
                memory_stage,
                target,
                candidate.force_num_one,
            )

    if not candidate_items:
        return

    grouped: dict[tuple[int, str, int, int], list[_LoopRingCandidate]] = {}
    for candidate in candidate_items:
        space = candidate.slot_type.space.space.data
        grouped.setdefault(
            (
                id(candidate.target_loop),
                space,
                id(candidate.insertion_block),
                id(candidate.insertion_anchor),
            ),
            [],
        ).append(candidate)

    for group in grouped.values():
        insertion_block = group[0].insertion_block
        insertion_anchor = group[0].insertion_anchor
        insertion_indexes = {op: index for index, op in enumerate(insertion_block.ops)}
        if insertion_anchor not in insertion_indexes:
            continue
        current_anchors: dict[DmaAllocOp, Operation] = {}
        invalid_group = False
        for candidate in group:
            first_block = candidate.first_use.parent_block()
            last_block = candidate.last_use.parent_block()
            if first_block is None or last_block is None or first_block is not last_block:
                invalid_group = True
                break
            first_block_ops = list(first_block.ops)
            if not first_block_ops:
                invalid_group = True
                break
            current_anchors[candidate.alloc_op] = first_block_ops[0]
        if invalid_group:
            continue
        setup_anchor = insertion_anchor
        if all(candidate.first_use.parent_block() is insertion_block for candidate in group):
            setup_anchor = current_anchors[group[0].alloc_op]
        if setup_anchor not in insertion_indexes:
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
                            available = insertion_indexes.get(owner, 10**9) < insertion_indexes[setup_anchor]
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
                    mul_op = _MultiBufferRewriteRules.symbol_binary_op("symbol.mul", lhs_value, rhs_value, result_expr)
                    pre_loop_ops.append(mul_op)
                    elements = (mul_op.results[0], result_expr, None)

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
                mul_op = _MultiBufferRewriteRules.symbol_binary_op("symbol.mul", elements_value, bpe.result, result_expr)
                pre_loop_ops.extend([bpe, mul_op])
                slot_values[candidate.alloc_op] = (mul_op.results[0], result_expr, None)
        if unavailable or any(candidate.alloc_op not in slot_values for candidate in group):
            continue

        aligned_slot_values: dict[DmaAllocOp, _SymbolExprValue] = {}
        for candidate in group:
            aligned_slot_values[candidate.alloc_op] = _MultiBufferRewriteRules.align_up_symbol_value(
                slot_values[candidate.alloc_op],
                alignment,
                pre_loop_ops,
            )

        num_values: dict[DmaAllocOp, _SymbolExprValue] = {}
        fixed_reserved: _SymbolExprValue | None = None
        auto_candidates: list[_LoopRingCandidate] = []
        failed_group = False
        for candidate in group:
            raw_num = parsed_num_attrs.get(candidate.alloc_op)
            parsed = raw_num if isinstance(raw_num, int) else _MultiBufferRewriteRules.parse_multi_buffer_num_attr(raw_num or "")
            if parsed is None:
                failed_group = True
                break
            if parsed == "auto":
                auto_candidates.append(candidate)
                continue
            num_const = SymbolConstOp(parsed)
            pre_loop_ops.append(num_const)
            num_value: _SymbolExprValue = (num_const.result, str(parsed), parsed)
            num_values[candidate.alloc_op] = num_value
            aligned_slot = aligned_slot_values[candidate.alloc_op]
            aligned_result, aligned_expr, aligned_static = aligned_slot
            if aligned_static is not None:
                reserved_value = parsed * aligned_static
                reserved_const = SymbolConstOp(reserved_value)
                pre_loop_ops.append(reserved_const)
                reserved: _SymbolExprValue = (reserved_const.result, str(reserved_value), reserved_value)
            else:
                reserved_expr = SymbolExprAttr.from_expr(f"({parsed})*({aligned_expr})").expr.data
                reserved_op = _MultiBufferRewriteRules.symbol_binary_op(
                    "symbol.mul",
                    num_const.result,
                    aligned_result,
                    reserved_expr,
                )
                pre_loop_ops.append(reserved_op)
                reserved = (reserved_op.results[0], reserved_expr, None)
            fixed_reserved = (
                reserved
                if fixed_reserved is None
                else _MultiBufferRewriteRules.add_symbol_values(fixed_reserved, reserved, pre_loop_ops)
            )
        if failed_group:
            continue

        if auto_candidates:
            if target is None:
                continue
            capacity = get_target_hardware(target, f"{group[0].slot_type.space.space.data}_memory_size")
            if capacity is None or capacity <= 0:
                continue
            reserved_from_live_allocs, reserved_ok = _MultiBufferRewriteRules.reserved_space_bytes_for_group(
                group,
                insertion_block,
                setup_anchor,
                pre_loop_ops,
                alignment,
            )
            if not reserved_ok:
                continue
            if reserved_from_live_allocs is not None:
                reserved_from_live_allocs = _MultiBufferRewriteRules.align_up_symbol_value(
                    reserved_from_live_allocs,
                    alignment,
                    pre_loop_ops,
                )
                fixed_reserved = (
                    reserved_from_live_allocs
                    if fixed_reserved is None
                    else _MultiBufferRewriteRules.add_symbol_values(
                        fixed_reserved,
                        reserved_from_live_allocs,
                        pre_loop_ops,
                    )
                )
            if fixed_reserved is None:
                capacity_const = SymbolConstOp(capacity)
                pre_loop_ops.append(capacity_const)
                capacity_value: _SymbolExprValue = (capacity_const.result, str(capacity), capacity)
            else:
                reserved_result, reserved_expr, reserved_static = fixed_reserved
                if reserved_static is not None:
                    available_static = capacity - reserved_static
                    if available_static <= 0:
                        continue
                    capacity_const = SymbolConstOp(available_static)
                    pre_loop_ops.append(capacity_const)
                    capacity_value = (capacity_const.result, str(available_static), available_static)
                else:
                    capacity_const = SymbolConstOp(capacity)
                    available_expr = SymbolExprAttr.from_expr(f"({capacity}) - ({reserved_expr})").expr.data
                    available_op = _MultiBufferRewriteRules.symbol_binary_op(
                        "symbol.sub",
                        capacity_const.result,
                        reserved_result,
                        available_expr,
                    )
                    pre_loop_ops.extend([capacity_const, available_op])
                    capacity_value = (available_op.results[0], available_expr, None)
            group_unit = aligned_slot_values[auto_candidates[0].alloc_op]
            for candidate in auto_candidates[1:]:
                group_unit = _MultiBufferRewriteRules.add_symbol_values(
                    group_unit,
                    aligned_slot_values[candidate.alloc_op],
                    pre_loop_ops,
                )
            unit_result, unit_expr, unit_static = group_unit
            capacity_result, capacity_expr, capacity_static = capacity_value
            if unit_static is not None and capacity_static is not None:
                if unit_static <= 0:
                    continue
                auto_num = capacity_static // unit_static
                if auto_num <= 0:
                    continue
                num_const = SymbolConstOp(auto_num)
                pre_loop_ops.append(num_const)
                auto_num_value: _SymbolExprValue = (num_const.result, str(auto_num), auto_num)
            else:
                num_expr = SymbolExprAttr.from_expr(f"({capacity_expr}) floordiv ({unit_expr})").expr.data
                num_op = _MultiBufferRewriteRules.symbol_binary_op(
                    "symbol.floordiv",
                    capacity_result,
                    unit_result,
                    num_expr,
                )
                pre_loop_ops.append(num_op)
                auto_num_value = (num_op.results[0], num_expr, None)
            for candidate in auto_candidates:
                num_values[candidate.alloc_op] = auto_num_value

        if any(candidate.alloc_op not in num_values for candidate in group):
            continue

        current_ops: dict[DmaAllocOp, DmaCurrentRingOp] = {}
        advance_ops: dict[DmaAllocOp, DmaAdvanceRingOp] = {}
        for candidate in group:
            num_result, num_expr, num_static = num_values[candidate.alloc_op]
            slot_result, slot_expr, slot_static = aligned_slot_values[candidate.alloc_op]
            if num_static is not None and slot_static is not None:
                backing_value = num_static * slot_static
                backing_const = SymbolConstOp(backing_value)
                pre_loop_ops.append(backing_const)
                backing_result = backing_const.result
                backing_expr = str(backing_value)
                backing_static = backing_value
            else:
                backing_expr = SymbolExprAttr.from_expr(f"({num_expr})*({slot_expr})").expr.data
                backing_mul = _MultiBufferRewriteRules.symbol_binary_op(
                    "symbol.mul",
                    num_result,
                    slot_result,
                    backing_expr,
                )
                pre_loop_ops.append(backing_mul)
                backing_result = backing_mul.results[0]
                backing_static = None
            backing_type = NnMemoryType(
                ArrayAttr([SymbolExprAttr.from_expr(backing_expr)]),
                ArrayAttr([SymbolExprAttr.from_expr("1")]),
                i8,
                candidate.slot_type.space,
            )
            backing_shape = [] if backing_static is not None else [backing_result]
            backing = DmaAllocOp(backing_shape, backing_type)
            offset_result = slot_result
            if slot_static is not None:
                offset_const = SymbolConstOp(slot_static)
                pre_loop_ops.append(offset_const)
                offset_result = offset_const.result
            make_ring = DmaMakeRingOp(backing.result, num_result, offset_result, DmaRingType(candidate.slot_type))
            current = DmaCurrentRingOp(make_ring.result)
            advance = DmaAdvanceRingOp(make_ring.result)
            pre_loop_ops.extend([backing, make_ring])
            current_ops[candidate.alloc_op] = current
            advance_ops[candidate.alloc_op] = advance

        insertion_block.insert_ops_before(pre_loop_ops, setup_anchor)
        for candidate in group:
            current = current_ops[candidate.alloc_op]
            first_block = candidate.first_use.parent_block()
            last_block = candidate.last_use.parent_block()
            if first_block is None or last_block is None or first_block is not last_block:
                continue
            current_anchor = current_anchors[candidate.alloc_op]
            first_block.insert_ops_before([current], current_anchor)
            for alias in candidate.aliases:
                alias.operands[0] = current.result
            for user, index in candidate.direct_uses:
                user.operands[index] = current.result
            advance = advance_ops[candidate.alloc_op]
            last_block_tail = last_block.last_op
            if last_block_tail is not None and last_block_tail.has_trait(IsTerminator):
                last_block.insert_ops_before([advance], last_block_tail)
            else:
                last_block.add_ops([advance])
            free_block = candidate.free_op.parent_block()
            alloc_block = candidate.alloc_op.parent_block()
            if free_block is not None:
                free_block.erase_op(candidate.free_op)
            if alloc_block is not None:
                alloc_block.erase_op(candidate.alloc_op)


@dataclass(frozen=True)
class MultiBufferAnalysisPass(Pass):
    """multi-buffer analysis pass。

    功能说明:
    - 只分析可证明的 staging alloc/free 生命周期，并在 `dma.alloc` 上写三项 `multi_buffer.*` 属性。
    - target 非空时 same-loop staging 写 `multi_buffer.num = "auto"`；否则写固定 `memory_stage`。
    - 不物化 ring、不删除 alloc/free、不替换 operand。

    使用示例:
    - MultiBufferAnalysisPass(memory_stage=2, target="npu_demo").apply(Context(), module)
    """

    name = "multi-buffer-analysis"
    memory_stage: int = 2
    fold: bool = True
    target: str | None = None

    def __init__(self, memory_stage: int = 2, fold: bool = True, target: str | None = None) -> None:
        """初始化 multi-buffer analysis pass。

        功能说明:
        - 保存 analysis 写入固定 num 所需的 `memory_stage` 和可选 target。
        - 校验公开构造参数并保留稳定错误文本。

        使用示例:
        - pass_obj = MultiBufferAnalysisPass(memory_stage=3, fold=False)
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
    def from_options(cls, options: dict[str, str]) -> "MultiBufferAnalysisPass":
        """从 pass registry options 构造 multi-buffer analysis pass。

        功能说明:
        - 接受 `memory-stage` 与 `target` pass 专属选项。
        - `fold` 由 registry 通用选项处理，直接传入时按未知 option 失败。

        使用示例:
        - pass_obj = MultiBufferAnalysisPass.from_options({"memory-stage": "2"})
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
        """执行 multi-buffer analysis。

        功能说明:
        - 遍历 `symbol.for` 内 matmul lhs/rhs staging pair 并写三项属性。
        - 遍历 direct alias / direct memory use staging 候选并写三项属性。
        - 不满足可证明生命周期的 alloc 保持无属性 no-op。

        使用示例:
        - MultiBufferAnalysisPass().apply(Context(), module)
        """

        _ = ctx
        ensure_builtin_module(module)
        labels = _MultiBufferRewriteRules.region_labels(module)
        for symbol_for in [op for op in module.walk() if isinstance(op, SymbolForOp)]:
            loop_block = symbol_for.body.blocks[0]
            region_label = labels.get(symbol_for, "loop1")
            for op in list(loop_block.ops):
                if isinstance(op, KernelMatmulOp):
                    _rewrite_matmul_if_pair(
                        symbol_for,
                        op,
                        self.memory_stage,
                        self.target,
                        mode="analysis",
                        region_label=region_label,
                    )
        _rewrite_loop_staging_candidates(
            module,
            self.memory_stage,
            self.target,
            mode="analysis",
            region_labels=labels,
        )


@dataclass(frozen=True)
class MultiBufferApplyPass(Pass):
    """multi-buffer apply pass。

    功能说明:
    - 只消费 `multi_buffer.update_point/use_point/num` 三项 analysis 属性。
    - fixed 和 auto 都按 `alignment` 计算 ring offset 与 backing bytes。
    - apply 完成后删除旧 typed alloc/free 生命周期，不残留临时属性。

    使用示例:
    - MultiBufferApplyPass(target="npu_demo", alignment=1024).apply(Context(), module)
    """

    name = "multi-buffer-apply"
    fold: bool = True
    target: str | None = None
    alignment: int = 1024

    def __init__(self, fold: bool = True, target: str | None = None, alignment: int = 1024) -> None:
        """初始化 multi-buffer apply pass。

        功能说明:
        - 保存 auto num 计算所需 target 和 fixed/auto 共用 alignment。
        - `alignment=0` 表示关闭对齐，非法值保持稳定错误文本。

        使用示例:
        - pass_obj = MultiBufferApplyPass(target="npu_demo", alignment=1024)
        """

        if target is not None and (not isinstance(target, str) or not target.strip()):
            raise_pass_contract_error("MultiBufferOptionError", "target must be non-empty")
        object.__setattr__(self, "fold", bool(fold))
        object.__setattr__(self, "target", target.strip() if isinstance(target, str) else None)
        object.__setattr__(self, "alignment", _validate_alignment_value(alignment))

    @classmethod
    def from_options(cls, options: dict[str, str]) -> "MultiBufferApplyPass":
        """从 pass registry options 构造 multi-buffer apply pass。

        功能说明:
        - 接受 `target` 与 `alignment` pass 专属选项。
        - `fold` 由 registry 通用选项处理，直接传入时按未知 option 失败。

        使用示例:
        - pass_obj = MultiBufferApplyPass.from_options({"target": "npu_demo", "alignment": "1024"})
        """

        allowed = {"target", "alignment"}
        unknown = sorted(set(options) - allowed)
        if unknown:
            raise_pass_contract_error("MultiBufferOptionError", f"unknown option: {unknown[0]}")
        target = None
        if "target" in options:
            target = options["target"].strip()
            if not target:
                raise_pass_contract_error("MultiBufferOptionError", "target must be non-empty")
        alignment = 1024
        if "alignment" in options:
            alignment = _parse_alignment_option(options["alignment"])
        return cls(target=target, alignment=alignment)

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 multi-buffer apply。

        功能说明:
        - 重新校验带三项属性的候选，消费 fixed/auto `multi_buffer.num` 并物化 ring。
        - 对 `"auto"` 候选使用 `target` 容量和同 scope fixed reserved 计算 num。
        - 删除旧 alloc/free；被删除 alloc 上的三项临时属性不会进入输出 IR。

        使用示例:
        - MultiBufferApplyPass(target="npu_demo").apply(Context(), module)
        """

        _ = ctx
        ensure_builtin_module(module)
        labels = _MultiBufferRewriteRules.region_labels(module)
        existing_current_block_ids: set[int] = set()
        for current_op in [op for op in module.walk() if isinstance(op, DmaCurrentRingOp)]:
            current_block = current_op.parent_block()
            if current_block is not None:
                existing_current_block_ids.add(id(current_block))
        for symbol_for in [op for op in module.walk() if isinstance(op, SymbolForOp)]:
            loop_block = symbol_for.body.blocks[0]
            region_label = labels.get(symbol_for, "loop1")
            for op in list(loop_block.ops):
                if isinstance(op, KernelMatmulOp):
                    _rewrite_matmul_if_pair(
                        symbol_for,
                        op,
                        2,
                        self.target,
                        mode="apply",
                        alignment=self.alignment,
                        region_label=region_label,
                    )
        _rewrite_loop_staging_candidates(
            module,
            2,
            self.target,
            mode="apply",
            alignment=self.alignment,
            region_labels=labels,
            existing_current_block_ids=existing_current_block_ids,
        )


@dataclass(frozen=True)
class MultiBufferPass(Pass):
    """multi-buffer facade pass。

    功能说明:
    - 保留旧 `multi-buffer` 公开入口，外部行为等价于 analysis 后接 apply。
    - 默认 `memory_stage=2`、`alignment=1024`；target 非空时 analysis 写 `"auto"`，apply 计算容量。
    - 执行完成后不保留三项 `multi_buffer.*` 临时属性。

    使用示例:
    - MultiBufferPass(memory_stage=2, target="npu_demo", alignment=1024).apply(Context(), module)
    """

    name = "multi-buffer"
    memory_stage: int = 2
    fold: bool = True
    target: str | None = None
    alignment: int = 1024

    def __init__(
        self,
        memory_stage: int = 2,
        fold: bool = True,
        target: str | None = None,
        alignment: int = 1024,
    ) -> None:
        """初始化 multi-buffer facade pass。

        功能说明:
        - 保存 analysis 所需 `memory_stage`、apply 所需 `alignment` 和共享 target。
        - 保留旧构造器参数并新增已确认的公开 `alignment` 参数。

        使用示例:
        - pass_obj = MultiBufferPass(memory_stage=2, fold=False, target="npu_demo", alignment=1024)
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
        object.__setattr__(self, "alignment", _validate_alignment_value(alignment))

    @classmethod
    def from_options(cls, options: dict[str, str]) -> "MultiBufferPass":
        """从 pass registry options 构造 multi-buffer facade pass。

        功能说明:
        - 接受 pass 专属 `memory-stage`、`target` 与 `alignment`。
        - `fold` 必须由 registry 通用选项处理，传到本方法时按未知 option 失败。

        使用示例:
        - pass_obj = MultiBufferPass.from_options({"memory-stage": "2", "target": "npu_demo"})
        """

        allowed = {"memory-stage", "target", "alignment"}
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
        alignment = 1024
        if "alignment" in options:
            alignment = _parse_alignment_option(options["alignment"])
        return cls(memory_stage=memory_stage, target=target, alignment=alignment)

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 multi-buffer facade rewrite。

        功能说明:
        - 先运行 `MultiBufferAnalysisPass` 写三项临时属性。
        - 再运行 `MultiBufferApplyPass` 消费属性并生成 ring。
        - 不满足条件的结构保持 no-op。

        使用示例:
        - MultiBufferPass().apply(Context(), module)
        """

        MultiBufferAnalysisPass(memory_stage=self.memory_stage, fold=self.fold, target=self.target).apply(ctx, module)
        MultiBufferApplyPass(fold=self.fold, target=self.target, alignment=self.alignment).apply(ctx, module)


__all__ = ["MultiBufferAnalysisPass", "MultiBufferApplyPass", "MultiBufferPass"]
