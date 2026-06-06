"""multi-buffer pass.


功能说明:
- 提供 `multi-buffer` pass，把可证明的 matmul lhs/rhs staging buffer 改写为 DMA ring。
- 匹配同一 `symbol.for` 外的 `dma.alloc/free` 与 loop body 内的 `dma.copy + kernel.matmul` 成对生命周期。
- 对不满足公开边界的 IR 保持 no-op，不引入宽泛 alias 或跨 region 推断。

API 列表:
- `class MultiBufferPass(memory_stage: int = 3, fold: bool = True, target: str | None = None)`
- `MultiBufferPass.from_options(options: dict[str, str]) -> MultiBufferPass`
- `MultiBufferPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.multi_buffer import MultiBufferPass
- MultiBufferPass(memory_stage=3).apply(Context(), module)

关联文件:
- spec: spec/pass/multi_buffer.md
- test: test/passes/test_multi_buffer.py
- 功能实现: kernel_gen/passes/multi_buffer.py
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
from xdsl.ir import Attribute, Operation, SSAValue

from kernel_gen.dialect.dma import (
    DmaAdvanceRingOp,
    DmaAllocOp,
    DmaCopyOp,
    DmaCurrentRingOp,
    DmaFreeOp,
    DmaMakeRingOp,
    DmaRingType,
)
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.kernel import KernelMatmulOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolExprAttr, SymbolForOp
from kernel_gen.dialect.symbol import SymbolAddOp, SymbolFloorDivOp, SymbolMulOp, SymbolValueType
from kernel_gen.passes.common import ensure_builtin_module, raise_pass_contract_error
from kernel_gen.passes.pass_manager import Pass
from kernel_gen.target.registry import get_target_hardware


@dataclass(frozen=True)
class _SymbolExprValue:
    """当前文件内的 symbol value 计划片段。"""

    value: SSAValue
    expr: str
    static_value: int | None


@dataclass(frozen=True)
class _StagingCandidate:
    """单个 matmul staging buffer 的 ring 化候选。"""

    alloc_op: DmaAllocOp
    copy_op: DmaCopyOp
    free_op: DmaFreeOp
    matmul_op: KernelMatmulOp
    operand_index: int
    slot_type: NnMemoryType
    slot_bytes: int | None


@dataclass(frozen=True)
class _RingRewriteOps:
    """当前文件内的单个 ring 改写 op 计划。"""

    current: DmaCurrentRingOp
    advance: DmaAdvanceRingOp


def _parse_memory_stage_option(value: str) -> int:
    """解析 `memory-stage` pass option。

    功能说明:
    - 将 registry 传入的字符串解析成正整数 stage 数。

    使用示例:
    - stage = _parse_memory_stage_option("3")

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
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
    - changed = _rewrite_matmul_if_pair(symbol_for, matmul, 3, None)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
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
        candidates.append(
            _StagingCandidate(
                alloc_op=alloc_op,
                copy_op=copy_op,
                free_op=free_op,
                matmul_op=matmul,
                operand_index=operand_index,
                slot_type=alloc_op.result.type,
                slot_bytes=slot_bytes,
            )
        )

    if len(candidates) != 2 or candidates[0].alloc_op is candidates[1].alloc_op:
        return False
    candidate_pair = (candidates[0], candidates[1])

    pre_loop_ops: list[Operation] = []
    rewrite_ops: list[_RingRewriteOps] = []
    if all(candidate.slot_bytes is not None for candidate in candidate_pair):
        if target is None:
            nums = (memory_stage, memory_stage)
        else:
            totals: dict[str, int] = {}
            capacities: dict[str, int] = {}
            for candidate in candidate_pair:
                if candidate.slot_bytes is None:
                    return False
                space = candidate.slot_type.space.space.data
                totals[space] = totals.get(space, 0) + candidate.slot_bytes
                capacity = get_target_hardware(target, f"{space}_memory_size")
                if capacity is None or capacity <= 0:
                    return False
                capacities[space] = capacity
            computed_nums: list[int] = []
            for candidate in candidate_pair:
                space = candidate.slot_type.space.space.data
                total = totals[space]
                if total <= 0:
                    return False
                num = capacities[space] // total
                if num <= 0:
                    return False
                computed_nums.append(num)
            nums = (computed_nums[0], computed_nums[1])

        for candidate, num in zip(candidate_pair, nums, strict=True):
            slot_bytes = candidate.slot_bytes
            if slot_bytes is None:
                return False
            backing_bytes = num * slot_bytes
            backing_type = NnMemoryType(
                ArrayAttr([SymbolExprAttr.from_expr(str(backing_bytes))]),
                ArrayAttr([SymbolExprAttr.from_expr("1")]),
                i8,
                candidate.slot_type.space,
            )
            backing = DmaAllocOp([], backing_type)
            num_op = SymbolConstOp(num)
            offset = SymbolConstOp(slot_bytes)
            shape_bytes = SymbolConstOp(slot_bytes)
            make_ring = DmaMakeRingOp(
                backing.result,
                num_op.result,
                offset.result,
                shape_bytes.result,
                DmaRingType(candidate.slot_type),
            )
            current = DmaCurrentRingOp(make_ring.result)
            advance = DmaAdvanceRingOp(make_ring.result)
            pre_loop_ops.extend([backing, num_op, offset, shape_bytes, make_ring])
            rewrite_ops.append(_RingRewriteOps(current=current, advance=advance))
    else:
        element_values: list[_SymbolExprValue] = []
        element_sizes: list[int] = []
        for candidate in candidate_pair:
            if candidate.slot_bytes is not None:
                const_op = SymbolConstOp(candidate.slot_bytes)
                pre_loop_ops.append(const_op)
                element_values.append(_SymbolExprValue(const_op.result, str(candidate.slot_bytes), candidate.slot_bytes))
                element_sizes.append(1)
                continue

            element_type = candidate.slot_type.element_type
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

            dims = list(candidate.slot_type.shape.data)
            operands = list(candidate.alloc_op.dynamic_shape)
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
                    dim_values.append(_SymbolExprValue(operand, dim_expr, static_value))
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
                        dim_values.append(_SymbolExprValue(dim_const.result, str(static_dim), static_dim))
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
                    dim_values.append(_SymbolExprValue(operand, dim_expr, None))

            if not dim_values:
                return False
            elements = dim_values[0]
            for dim_value in dim_values[1:]:
                result_expr = f"{elements.expr}*{dim_value.expr}"
                if elements.static_value is not None and dim_value.static_value is not None:
                    value = elements.static_value * dim_value.static_value
                    const_op = SymbolConstOp(value)
                    pre_loop_ops.append(const_op)
                    elements = _SymbolExprValue(const_op.result, str(value), value)
                else:
                    mul_op = SymbolMulOp(elements.value, dim_value.value, SymbolValueType.from_expr(result_expr))
                    pre_loop_ops.append(mul_op)
                    elements = _SymbolExprValue(mul_op.result, result_expr, None)
            element_values.append(elements)
            element_sizes.append(element_size)

        shared_bpe: SymbolConstOp | None = None
        shared_element_size = element_sizes[0] if element_sizes[0] == element_sizes[1] else None
        if shared_element_size is not None and shared_element_size > 1:
            shared_bpe = SymbolConstOp(shared_element_size)
            pre_loop_ops.append(shared_bpe)

        shape_values: list[_SymbolExprValue] = []
        for elements, element_size in zip(element_values, element_sizes, strict=True):
            if element_size == 1:
                shape_values.append(elements)
                continue
            bpe = shared_bpe
            if bpe is None:
                bpe = SymbolConstOp(element_size)
                pre_loop_ops.append(bpe)
            bpe_value = _SymbolExprValue(bpe.result, str(element_size), element_size)
            result_expr = f"{element_size}*{elements.expr}"
            if elements.static_value is not None:
                value = elements.static_value * element_size
                const_op = SymbolConstOp(value)
                pre_loop_ops.append(const_op)
                shape_values.append(_SymbolExprValue(const_op.result, str(value), value))
            else:
                mul_op = SymbolMulOp(elements.value, bpe_value.value, SymbolValueType.from_expr(result_expr))
                pre_loop_ops.append(mul_op)
                shape_values.append(_SymbolExprValue(mul_op.result, result_expr, None))

        if target is None:
            lhs_num = SymbolConstOp(memory_stage)
            rhs_num = SymbolConstOp(memory_stage)
            pre_loop_ops.extend([lhs_num, rhs_num])
            num_values = (
                _SymbolExprValue(lhs_num.result, str(memory_stage), memory_stage),
                _SymbolExprValue(rhs_num.result, str(memory_stage), memory_stage),
            )
        else:
            num_slots: list[_SymbolExprValue | None] = [None, None]
            groups: list[list[int]] = []
            spaces: list[str] = []
            for index, candidate in enumerate(candidate_pair):
                space = candidate.slot_type.space.space.data
                if space in spaces:
                    groups[spaces.index(space)].append(index)
                    continue
                spaces.append(space)
                groups.append([index])
            for group in groups:
                capacity = get_target_hardware(target, f"{candidate_pair[group[0]].slot_type.space.space.data}_memory_size")
                if capacity is None or capacity <= 0:
                    return False
                total = shape_values[group[0]]
                for index in group[1:]:
                    addend = shape_values[index]
                    result_expr = f"{total.expr} + {addend.expr}"
                    if total.static_value is not None and addend.static_value is not None:
                        value = total.static_value + addend.static_value
                        const_op = SymbolConstOp(value)
                        pre_loop_ops.append(const_op)
                        total = _SymbolExprValue(const_op.result, str(value), value)
                    else:
                        add_op = SymbolAddOp(total.value, addend.value, SymbolValueType.from_expr(result_expr))
                        pre_loop_ops.append(add_op)
                        total = _SymbolExprValue(add_op.result, result_expr, None)
                if total.static_value is not None:
                    if total.static_value <= 0:
                        return False
                    num_value = capacity // total.static_value
                    if num_value <= 0:
                        return False
                    num_const = SymbolConstOp(num_value)
                    pre_loop_ops.append(num_const)
                    num = _SymbolExprValue(num_const.result, str(num_value), num_value)
                else:
                    capacity_const = SymbolConstOp(capacity)
                    num_expr = f"{capacity} floordiv ({total.expr})"
                    num_op = SymbolFloorDivOp(capacity_const.result, total.value, SymbolValueType.from_expr(num_expr))
                    pre_loop_ops.extend([capacity_const, num_op])
                    num = _SymbolExprValue(num_op.result, num_expr, None)
                for index in group:
                    num_slots[index] = num
            if num_slots[0] is None or num_slots[1] is None:
                return False
            num_values = (num_slots[0], num_slots[1])

        backing_values: list[_SymbolExprValue] = []
        for num_value, shape_value in zip(num_values, shape_values, strict=True):
            result_expr = f"({num_value.expr})*({shape_value.expr})"
            if num_value.static_value is not None and shape_value.static_value is not None:
                value = num_value.static_value * shape_value.static_value
                const_op = SymbolConstOp(value)
                pre_loop_ops.append(const_op)
                backing_values.append(_SymbolExprValue(const_op.result, str(value), value))
            else:
                mul_op = SymbolMulOp(num_value.value, shape_value.value, SymbolValueType.from_expr(result_expr))
                pre_loop_ops.append(mul_op)
                backing_values.append(_SymbolExprValue(mul_op.result, result_expr, None))

        for candidate, num_value, shape_value, backing_value in zip(candidate_pair, num_values, shape_values, backing_values, strict=True):
            dynamic_shape = [] if backing_value.static_value is not None else [backing_value.value]
            backing_type = NnMemoryType(
                ArrayAttr([SymbolExprAttr.from_expr(backing_value.expr)]),
                ArrayAttr([SymbolExprAttr.from_expr("1")]),
                i8,
                candidate.slot_type.space,
            )
            backing = DmaAllocOp(dynamic_shape, backing_type)
            make_ring = DmaMakeRingOp(
                backing.result,
                num_value.value,
                shape_value.value,
                shape_value.value,
                DmaRingType(candidate.slot_type),
            )
            current = DmaCurrentRingOp(make_ring.result)
            advance = DmaAdvanceRingOp(make_ring.result)
            pre_loop_ops.extend([backing, make_ring])
            rewrite_ops.append(_RingRewriteOps(current=current, advance=advance))

    parent_block.insert_ops_before(pre_loop_ops, symbol_for)
    for candidate, ops in zip(candidate_pair, rewrite_ops, strict=True):
        loop_block.insert_ops_before([ops.current], candidate.copy_op)
        for use in tuple(candidate.alloc_op.result.uses):
            if use.operation is candidate.free_op:
                continue
            use.operation.operands[use.index] = ops.current.result
    loop_block.insert_ops_after([rewrite_ops[0].advance, rewrite_ops[1].advance], matmul)
    for candidate in candidate_pair:
        free_block = candidate.free_op.parent_block()
        alloc_block = candidate.alloc_op.parent_block()
        if free_block is not None:
            free_block.erase_op(candidate.free_op)
        if alloc_block is not None:
            alloc_block.erase_op(candidate.alloc_op)
    return True


class MultiBufferPass(Pass):
    """multi-buffer pass。

    功能说明:
    - 将可证明的 matmul lhs/rhs staging buffer 成对改写为 `dma.ring`。
    - 默认 `memory_stage=3`，当 `target` 非空时优先按 target registry 容量计算 ring num。
    - 只处理同一 `symbol.for` 外 staging alloc/free、直接 body 内 copy/matmul 消费的公开模式。

    使用示例:
    - MultiBufferPass(memory_stage=3, target="npu_demo").apply(Context(), module)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    name = "multi-buffer"

    def __init__(self, memory_stage: int = 3, fold: bool = True, target: str | None = None) -> None:
        """初始化 multi-buffer pass。

        功能说明:
        - 保存 ring stage 数、通用 fold 开关和可选 target 名称。

        使用示例:
        - pass_obj = MultiBufferPass(memory_stage=3, fold=False, target="npu_demo")

        关联文件:
        - spec: spec/pass/multi_buffer.md
        - test: test/passes/test_multi_buffer.py
        - 功能实现: kernel_gen/passes/multi_buffer.py
        """

        if isinstance(memory_stage, bool) or not isinstance(memory_stage, int):
            raise_pass_contract_error("MultiBufferOptionError", "memory_stage must be integer")
        if memory_stage <= 0:
            raise_pass_contract_error("MultiBufferOptionError", "memory_stage must be positive")
        if target is not None and (not isinstance(target, str) or not target.strip()):
            raise_pass_contract_error("MultiBufferOptionError", "target must be non-empty")
        super().__init__(fold=fold)
        self.memory_stage = memory_stage
        self.target = target.strip() if isinstance(target, str) else None

    @classmethod
    def from_options(cls, options: dict[str, str]) -> "MultiBufferPass":
        """从 pass registry options 构造 multi-buffer pass。

        功能说明:
        - 接受 pass 专属 `memory-stage` 与 `target`。
        - `fold` 必须由 registry 通用选项处理，传到本方法时按未知 option 失败。

        使用示例:
        - pass_obj = MultiBufferPass.from_options({"memory-stage": "3", "target": "npu_demo"})

        关联文件:
        - spec: spec/pass/multi_buffer.md
        - test: test/passes/test_multi_buffer.py
        - 功能实现: kernel_gen/passes/multi_buffer.py
        """

        allowed = {"memory-stage", "target"}
        unknown = sorted(set(options) - allowed)
        if unknown:
            raise_pass_contract_error("MultiBufferOptionError", f"unknown option: {unknown[0]}")
        memory_stage = 3
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
        - 遍历 `symbol.for` 直接 body 中的 `kernel.matmul`，匹配 loop 外成对 lhs/rhs staging 生命周期。
        - 不满足条件的结构保持 no-op。

        使用示例:
        - MultiBufferPass().apply(Context(), module)

        关联文件:
        - spec: spec/pass/multi_buffer.md
        - test: test/passes/test_multi_buffer.py
        - 功能实现: kernel_gen/passes/multi_buffer.py
        """

        _ = ctx
        ensure_builtin_module(module)
        for symbol_for in [op for op in module.walk() if isinstance(op, SymbolForOp)]:
            loop_block = symbol_for.body.blocks[0]
            for op in list(loop_block.ops):
                if isinstance(op, KernelMatmulOp):
                    _rewrite_matmul_if_pair(symbol_for, op, self.memory_stage, self.target)


__all__ = ["MultiBufferPass"]
