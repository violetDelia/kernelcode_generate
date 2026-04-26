"""nn -> kernel lowering pass.

创建者: 金铲铲大作战
最后一次更改: jcc你莫辜负

功能说明:
- 将 nn dialect op 通过 pattern collection lower 为 kernel dialect op。
- 当结果无法复用已有输出时，为结果插入 dma.alloc。
- `nn.softmax` 不在本 pass 直接 lower，需先由上游完成分解。
- 文件内 helper 按 `_ensure_*`、`_normalize_*`、`_collect_*`、`_materialize_*`
  与 `_lower_*` 前缀收口，并由 `_RejectUnsupportedNnOpPattern` 兜底拒绝未知 `nn.*`；
  这些 helper 仅供当前文件内部复用。

API 列表:
- `class NnLoweringError()`
- `nn_lowering_patterns() -> list[RewritePattern]`
- `class NnLoweringPass()`
- `NnLoweringPass.apply(self: NnLoweringPass, ctx: Context, op: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
- from xdsl.context import Context
- NnLoweringPass().apply(Context(), module)

关联文件:
- spec: spec/pass/lowering/nn_lowering/spec.md
- test: test/pass/nn_lowering/test_lowering_nn_lowering.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import (
    ArrayAttr,
    IntAttr,
    IntegerAttr,
    IntegerType,
    ModuleOp,
    StringAttr,
    UnrealizedConversionCastOp,
    i32,
)
from xdsl.ir import Block, Operation, Region, SSAValue
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriteWalker,
    PatternRewriter,
    RewritePattern,
    op_type_rewrite_pattern,
)
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.dma import DmaAllocOp, DmaFillOp
from kernel_gen.dialect.kernel import (
    KernelBinaryElewiseOp,
    KernelImg2col1dOp,
    KernelImg2col2dOp,
    KernelMatmulOp,
    KernelReduceOp,
)
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolGetDimOp, SymbolValueType
from ...pass_manager import Pass


class NnLoweringError(ValueError):
    """nn -> kernel lowering 过程的显式错误。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 用于在 lowering 阶段中断执行并返回明确错误信息。

    使用示例:
    - raise NnLoweringError("Unsupported nn op")

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """


_SUPPORTED_BINARY: dict[str, str] = {
    "nn.add": "add",
    "nn.sub": "sub",
    "nn.mul": "mul",
    "nn.truediv": "div",
    "nn.eq": "eq",
    "nn.ne": "ne",
    "nn.lt": "lt",
    "nn.le": "le",
    "nn.gt": "gt",
    "nn.ge": "ge",
}


def _ensure_space_attr(op: Operation) -> NnMemorySpaceAttr:
    """获取并校验 nn op 的 space attribute。

    创建者: 金铲铲大作战
    最后一次更改: 朽木露琪亚

    功能说明:
    - 确认 op.attributes["space"] 为 NnMemorySpaceAttr。

    使用示例:
    - space = _ensure_space_attr(op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    space = op.attributes.get("space")
    if not isinstance(space, NnMemorySpaceAttr):
        raise NnLoweringError("nn op must define #nn.space attribute")
    return space


def _ensure_single_result(op: Operation) -> NnMemoryType:
    """获取并校验 op 的唯一输出类型。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 确认仅有一个结果，且结果类型为 nn.memory。

    使用示例:
    - result_type = _ensure_single_result(op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    if len(op.results) != 1:
        raise NnLoweringError("nn op must produce exactly one result")
    result_type = op.results[0].type
    if not isinstance(result_type, NnMemoryType):
        raise NnLoweringError("nn op result must be nn.memory")
    return result_type


def _ensure_operand_count(op: Operation, count: int) -> None:
    """校验 op 的 operand 数量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 确认 op.operands 数量与预期一致。

    使用示例:
    - _ensure_operand_count(op, 2)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    if len(op.operands) != count:
        raise NnLoweringError(f"{op.name} must have {count} operands")


def _ensure_int_attr(op: Operation, name: str) -> int:
    """获取并校验 op 的 int attribute。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 从 op.attributes 获取指定 name。
    - 校验为 IntegerAttr 或 IntAttr，并返回其值。

    使用示例:
    - axis = _ensure_int_attr(op, "axis")

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    attr = op.attributes.get(name)
    if isinstance(attr, IntegerAttr):
        return attr.value.data
    if isinstance(attr, IntAttr):
        return attr.data
    raise NnLoweringError(f"{op.name} {name} must be integer")


def _ensure_unary_result_matches_operand(
    op: Operation, operand_type: NnMemoryType, result_type: NnMemoryType
) -> list[int | str]:
    """校验 unary op 的结果类型与 operand 一致。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 要求 result/operand 的 shape、stride、element_type、space 完全一致。

    使用示例:
    - shape = _ensure_unary_result_matches_operand(op, operand.type, result_type)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/exp.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    operand_shape = _normalize_shape_dims(operand_type.shape.data)
    result_shape = _normalize_shape_dims(result_type.shape.data)
    if operand_shape != result_shape:
        raise NnLoweringError(f"{op.name} result shape must match operand")
    operand_stride = _normalize_shape_dims(operand_type.stride.data)
    result_stride = _normalize_shape_dims(result_type.stride.data)
    if operand_stride != result_stride:
        raise NnLoweringError(f"{op.name} result stride must match operand")
    if operand_type.element_type != result_type.element_type:
        raise NnLoweringError(f"{op.name} result element type must match operand")
    if operand_type.space != result_type.space:
        raise NnLoweringError(f"{op.name} result space must match operand")
    return result_shape


def _collect_unary_dynamic_shape(
    block: Block,
    op: Operation,
    operand: SSAValue,
    operand_shape: list[int | str],
    result_shape: list[int | str],
) -> list[SSAValue]:
    """收集 unary 结果的动态维度列表。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 对每个符号维度插入 symbol.get_dim 作为 dma.alloc 的 dynamic_shape。
    - 要求 operand/result 的符号维度一致。

    使用示例:
    - params = _collect_unary_dynamic_shape(block, op, operand, operand_shape, result_shape)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/exp.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    symbol_dims: list[SSAValue] = []
    for axis, dim in enumerate(result_shape):
        if not isinstance(dim, str):
            continue
        source_dim = operand_shape[axis]
        if not isinstance(source_dim, str):
            raise NnLoweringError(f"{op.name} operand shape must match result shape")
        if source_dim != dim:
            raise NnLoweringError(f"{op.name} operand shape must match result shape")
        symbol_op = SymbolGetDimOp(operand, IntAttr(axis))
        block.insert_op_before(symbol_op, op)
        symbol_dims.append(symbol_op.result)
    return symbol_dims


def _ensure_symbol_int(op: Operation, operand: SSAValue | Operation) -> SSAValue:
    """确保 operand 为 symbol.int 或 IntegerAttr。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 若 operand 为 int attr，则使用 arith.constant 转换为 SSAValue。
    - 若 operand 为 symbol.int，则直接返回。

    使用示例:
    - kw = _ensure_symbol_int(op, op.operands[1])

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    if isinstance(operand, Operation):
        operand = operand.results[0]
    if isinstance(operand.type, SymbolValueType):
        return operand
    if isinstance(operand, SSAValue):
        raise NnLoweringError("nn img2col parameters must be symbol.int")
    raise NnLoweringError("nn img2col parameters must be symbol.int")


def _ensure_symbol_or_int(op: Operation, operand: SSAValue | Operation) -> SSAValue:
    """确保 operand 为 symbol.int 或 IntegerAttr。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 symbol.int 或 arith.constant 整数。

    使用示例:
    - value = _ensure_symbol_or_int(op, operand)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    if isinstance(operand, Operation):
        operand = operand.results[0]
    if isinstance(operand.type, SymbolValueType):
        return operand
    if isinstance(operand.type, IntegerType):
        return operand
    raise NnLoweringError("broadcast scalar must be int or symbol")


def _ensure_reduce_axis(op_name: str, axes_attr: ArrayAttr) -> int:
    """校验 reduce 轴参数。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 确保 axes_attr 为 ArrayAttr 且仅包含一个 IntegerAttr。

    使用示例:
    - axis = _ensure_reduce_axis("nn.reduce_min", axes_attr)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    if not isinstance(axes_attr, ArrayAttr):
        raise NnLoweringError(f"{op_name} axes must be ArrayAttr")
    if len(axes_attr.data) == 0:
        raise NnLoweringError("reduce axes must be non-empty")
    if len(axes_attr.data) != 1:
        raise NnLoweringError("reduce axes must contain exactly one element")
    axis_attr = axes_attr.data[0]
    if isinstance(axis_attr, IntegerAttr):
        return axis_attr.value.data
    if isinstance(axis_attr, IntAttr):
        return axis_attr.data
    raise NnLoweringError("reduce axis must be integer")


def _ensure_reduce_keepdim(op_name: str, keepdim_attr: Attribute) -> bool:
    """校验 reduce keepdim 参数。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - keepdim 必须是 IntegerAttr 0 或 1。

    使用示例:
    - keepdim = _ensure_reduce_keepdim("nn.reduce_min", keepdim_attr)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    if isinstance(keepdim_attr, IntAttr):
        keepdim = keepdim_attr.data
    elif isinstance(keepdim_attr, IntegerAttr):
        keepdim = keepdim_attr.value.data
    else:
        raise NnLoweringError("keepdim must be integer")
    if keepdim not in (0, 1):
        raise NnLoweringError("keepdim must be 0 or 1")
    return bool(keepdim)


def _normalize_shape_dims(shape: Iterable[Attribute]) -> list[int | str]:
    """将 shape 维度规范化为 int 或 str。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - IntAttr 转换为 int。
    - StringAttr 转换为 str。
    - 其它类型抛出 NnLoweringError。

    使用示例:
    - dims = _normalize_shape_dims(mem_type.shape.data)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    dims: list[int | str] = []
    for dim in shape:
        if isinstance(dim, IntAttr):
            dims.append(dim.data)
            continue
        if isinstance(dim, IntegerAttr):
            dims.append(dim.value.data)
            continue
        if isinstance(dim, StringAttr):
            dims.append(dim.data)
            continue
        raise NnLoweringError("matmul shape must be IntAttr or StringAttr")
    return dims


def _collect_reduce_dynamic_shape(
    block: Block,
    op: Operation,
    operand: SSAValue,
    operand_shape: list[int | str],
    result_shape: list[int | str],
    axis: int,
    keepdim: bool,
) -> list[SSAValue]:
    """收集 reduce 结果的动态维度列表。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 遍历结果 shape 中的符号维度，按 axis/keepdim 映射回 operand 维度。
    - 对每个符号维度插入 symbol.get_dim 作为 dma.alloc 的 dynamic_shape。

    使用示例:
    - params = _collect_reduce_dynamic_shape(block, op, operand, operand_shape, result_shape, axis, keepdim)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/reduce_min.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    symbol_dims: list[SSAValue] = []
    for result_idx, dim in enumerate(result_shape):
        if not isinstance(dim, str):
            continue
        source_axis = result_idx if keepdim or result_idx < axis else result_idx + 1
        if source_axis < 0 or source_axis >= len(operand_shape):
            raise NnLoweringError("reduce axis out of range")
        source_dim = operand_shape[source_axis]
        if not isinstance(source_dim, str):
            raise NnLoweringError("reduce axis must be integer")
        if source_dim != dim:
            raise NnLoweringError("reduce axis symbol mismatch")
        symbol_op = SymbolGetDimOp(operand, IntAttr(source_axis))
        block.insert_op_before(symbol_op, op)
        symbol_dims.append(symbol_op.result)
    return symbol_dims


def _ensure_matmul_shape(
    lhs_type: NnMemoryType,
    rhs_type: NnMemoryType,
    out_type: NnMemoryType,
) -> None:
    """校验 nn.matmul 的 shape 合同。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 确认 lhs/rhs/out 均为 rank-2。
    - 校验 `[M, K] x [K, N] -> [M, N]` 规则。

    使用示例:
    - _ensure_matmul_shape(lhs_type, rhs_type, out_type)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    lhs_shape = _normalize_shape_dims(lhs_type.shape.data)
    rhs_shape = _normalize_shape_dims(rhs_type.shape.data)
    out_shape = _normalize_shape_dims(out_type.shape.data)
    if len(lhs_shape) != 2 or len(rhs_shape) != 2 or len(out_shape) != 2:
        raise NnLoweringError("matmul requires rank-2 memory types")
    if lhs_shape[1] != rhs_shape[0]:
        raise NnLoweringError("matmul contracting dimensions must match")
    if out_shape[0] != lhs_shape[0] or out_shape[1] != rhs_shape[1]:
        raise NnLoweringError("matmul output shape must match operands")


def _ensure_matmul_stride(mem_type: NnMemoryType) -> None:
    """校验 nn.matmul 的 stride 连续性。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 当 shape/stride 可静态求值时，要求 stride 为连续布局。

    使用示例:
    - _ensure_matmul_stride(out_type)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    shape = mem_type.shape.data
    stride = mem_type.stride.data
    if len(shape) != 2 or len(stride) != 2:
        raise NnLoweringError("matmul stride must be contiguous")
    if not all(isinstance(dim, IntAttr) for dim in shape):
        return
    if not all(isinstance(dim, IntAttr) for dim in stride):
        return
    expected_stride0 = shape[1].data
    expected_stride1 = 1
    if stride[0].data != expected_stride0 or stride[1].data != expected_stride1:
        raise NnLoweringError("matmul stride must be contiguous")

def _materialize_fill(
    block: Block,
    value: SSAValue,
    result_type: NnMemoryType,
    space: NnMemorySpaceAttr,
) -> SSAValue:
    """将标量填充为 nn.memory。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 插入 dma.alloc 与 dma.fill，将标量扩展为 memory。

    使用示例:
    - filled = _materialize_fill(block, scalar, result_type, space)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    alloc = DmaAllocOp([], result_type)
    block.add_op(alloc)
    fill = DmaFillOp(alloc, value)
    block.add_op(fill)
    return alloc.results[0]


def _materialize_fill_for_mixed(
    block: Block,
    op: Operation,
    lhs: SSAValue,
    rhs: SSAValue,
    result_type: NnMemoryType,
) -> tuple[SSAValue, SSAValue]:
    """处理 mixed symbol/nn.memory binary op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 当只有一个 operand 为 nn.memory 时，将另一个标量填充为 memory。

    使用示例:
    - lhs, rhs = _materialize_fill_for_mixed(block, op, lhs, rhs, result_type)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    space = _ensure_space_attr(op)
    if isinstance(lhs.type, NnMemoryType) and not isinstance(rhs.type, NnMemoryType):
        rhs = _materialize_fill(block, rhs, result_type, space)
    elif isinstance(rhs.type, NnMemoryType) and not isinstance(lhs.type, NnMemoryType):
        lhs = _materialize_fill(block, lhs, result_type, space)
    return lhs, rhs


def _lower_binary(block: Block, op: Operation) -> None:
    """lower binary ops。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 element binary 与 compare family。
    - 统一生成 kernel.binary_elewise op。

    使用示例:
    - _lower_binary(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    space = _ensure_space_attr(op)
    result_type = _ensure_single_result(op)
    _ensure_operand_count(op, 2)
    lhs, rhs = op.operands

    if isinstance(lhs.type, NnMemoryType) and isinstance(rhs.type, NnMemoryType):
        lhs_type = lhs.type
        rhs_type = rhs.type
        if lhs_type.shape != rhs_type.shape:
            raise NnLoweringError("nn op operands must have the same shape")
        alloc = DmaAllocOp([], result_type)
        block.insert_op_before(alloc, op)
        result = alloc.results[0]
    elif isinstance(lhs.type, NnMemoryType) or isinstance(rhs.type, NnMemoryType):
        result = DmaAllocOp([], result_type)
        block.insert_op_before(result, op)
        result = result.results[0]
        lhs, rhs = _materialize_fill_for_mixed(block, op, lhs, rhs, result_type)
    else:
        raise NnLoweringError("nn op must provide at least one nn.memory operand")

    kind = _SUPPORTED_BINARY[op.name]
    lowered = KernelBinaryElewiseOp(result, lhs, rhs, kind=kind, space=space)
    block.insert_op_before(lowered, op)
    op.results[0].replace_all_uses_with(result)
    block.erase_op(op)


def _lower_reduce(block: Block, op: Operation, *, kind: str) -> None:
    """lower reduce family。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 校验 axes / keepdim。
    - 先创建 dma.alloc，再调用 kernel.reduce(kind=...)。

    使用示例:
    - _lower_reduce(block, op, kind="min")

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    space = _ensure_space_attr(op)
    result_type = _ensure_single_result(op)
    if len(op.operands) == 2:
        _ensure_symbol_or_int(op, op.operands[1])
    elif len(op.operands) != 1:
        raise NnLoweringError(f"{op.name} must have 1 operands")
    operand = op.operands[0]
    if not isinstance(operand.type, NnMemoryType):
        raise NnLoweringError("nn.reduce operand must be nn.memory")
    axes_attr = op.attributes.get("axes")
    if axes_attr is None:
        raise NnLoweringError(f"{op.name} axes must be ArrayAttr")
    axis = _ensure_reduce_axis(op.name, axes_attr)
    keepdim_attr = op.attributes.get("keepdim")
    if keepdim_attr is None:
        raise NnLoweringError(f"{op.name} keepdim must be bool")
    keepdim = _ensure_reduce_keepdim(op.name, keepdim_attr)
    operand_rank = len(operand.type.shape.data)
    result_rank = len(result_type.shape.data)
    expected_rank = operand_rank if keepdim else operand_rank - 1
    if result_rank != expected_rank:
        raise NnLoweringError("reduce shape rank must match")
    operand_shape = _normalize_shape_dims(operand.type.shape.data)
    result_shape = _normalize_shape_dims(result_type.shape.data)
    params = _collect_reduce_dynamic_shape(
        block,
        op,
        operand,
        operand_shape,
        result_shape,
        axis,
        keepdim,
    )
    alloc = DmaAllocOp(params, result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = KernelReduceOp(result, operand, kind=kind, axis=axis, keepdim=keepdim, space=space)
    block.insert_op_before(lowered, op)
    op.results[0].replace_all_uses_with(result)
    block.erase_op(op)


def _lower_matmul(block: Block, op: Operation) -> None:
    """lower nn.matmul。

    创建者: 小李飞刀
    最后一次更改: jcc你莫辜负

    功能说明:
    - 校验 shape 与 stride。
    - 动态维度通过 symbol.get_dim 生成 dma.alloc 的 dynamic_shape。
    - 先创建 dma.alloc，再调用 kernel.matmul。

    使用示例:
    - _lower_matmul(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    space = _ensure_space_attr(op)
    result_type = _ensure_single_result(op)
    _ensure_operand_count(op, 2)
    lhs, rhs = op.operands
    if not isinstance(lhs.type, NnMemoryType) or not isinstance(rhs.type, NnMemoryType):
        raise NnLoweringError("nn.matmul operands must be nn.memory")
    _ensure_matmul_shape(lhs.type, rhs.type, result_type)
    _ensure_matmul_stride(lhs.type)
    _ensure_matmul_stride(rhs.type)
    _ensure_matmul_stride(result_type)
    lhs_shape = _normalize_shape_dims(lhs.type.shape.data)
    rhs_shape = _normalize_shape_dims(rhs.type.shape.data)
    out_shape = _normalize_shape_dims(result_type.shape.data)
    symbol_dims: list[SSAValue] = []
    if isinstance(out_shape[0], str):
        if out_shape[0] != lhs_shape[0]:
            raise NnLoweringError("matmul output shape must match operands")
        symbol_op = SymbolGetDimOp(lhs, IntAttr(0))
        block.insert_op_before(symbol_op, op)
        symbol_dims.append(symbol_op.result)
    if isinstance(out_shape[1], str):
        if out_shape[1] != rhs_shape[1]:
            raise NnLoweringError("matmul output shape must match operands")
        symbol_op = SymbolGetDimOp(rhs, IntAttr(1))
        block.insert_op_before(symbol_op, op)
        symbol_dims.append(symbol_op.result)
    alloc = DmaAllocOp(symbol_dims, result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = KernelMatmulOp(result, lhs, rhs, space)
    block.insert_op_before(lowered, op)
    op.results[0].replace_all_uses_with(result)
    block.erase_op(op)


def _ensure_img2col_params(
    op: Operation,
    operand_count: int,
    dynamic_count: int,
) -> tuple[SSAValue, list[SSAValue]]:
    """校验并提取 img2col 参数。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验参数数量，并提取 dynamic 参数列表。

    使用示例:
    - operand, params = _ensure_img2col_params(op, 6, 5)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    _ensure_operand_count(op, operand_count)
    operand = op.operands[0]
    params = [_ensure_symbol_int(op, op.operands[idx + 1]) for idx in range(dynamic_count)]
    return operand, params


def _lower_img2col1d(block: Block, op: Operation) -> None:
    """lower nn.img2col1d。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 将 img2col1d 参数转换为 symbol.int。
    - 先创建 dma.alloc，再调用 kernel.img2col1d。

    使用示例:
    - _lower_img2col1d(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    space = _ensure_space_attr(op)
    result_type = _ensure_single_result(op)
    operand, params = _ensure_img2col_params(op, 6, 5)
    alloc = DmaAllocOp(params, result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = KernelImg2col1dOp(result, operand, *params, space)
    block.insert_op_before(lowered, op)
    op.results[0].replace_all_uses_with(result)
    block.erase_op(op)


def _lower_img2col2d(block: Block, op: Operation) -> None:
    """lower nn.img2col2d。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 将 img2col2d 参数转换为 symbol.int。
    - 先创建 dma.alloc，再调用 kernel.img2col2d。

    使用示例:
    - _lower_img2col2d(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    space = _ensure_space_attr(op)
    result_type = _ensure_single_result(op)
    operand, params = _ensure_img2col_params(op, 11, 10)
    alloc = DmaAllocOp(params, result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = KernelImg2col2dOp(result, operand, *params, space)
    block.insert_op_before(lowered, op)
    op.results[0].replace_all_uses_with(result)
    block.erase_op(op)


def nn_lowering_patterns() -> list[RewritePattern]:
    """返回 lower-nn 的 rewrite pattern 集合。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 汇总 nn_lowering 各 family pattern，作为 NnLoweringPass.apply(...) 的唯一 driver 输入。
    - `_RejectUnsupportedNnOpPattern` 必须保持在最后，保证已支持 pattern 先尝试改写。

    使用示例:
    - patterns = nn_lowering_patterns()

    关联文件:
    - spec: [spec/pass/lowering/nn_lowering/spec.md](spec/pass/lowering/nn_lowering/spec.md)
    - test: [test/pass/nn_lowering/public_name.py](test/pass/nn_lowering/public_name.py)
    - 功能实现: [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
    """

    from .dma_structured_lowering import dma_structured_patterns
    from .element_binary_lowering import element_binary_patterns
    from .matmul_img2col_lowering import matmul_img2col_patterns
    from .reduce_softmax_lowering import reduce_softmax_patterns
    from .select_cast_lowering import select_cast_patterns

    return [
        *element_binary_patterns(),
        *select_cast_patterns(),
        *dma_structured_patterns(),
        *matmul_img2col_patterns(),
        *reduce_softmax_patterns(),
        _RejectUnsupportedNnOpPattern(),
    ]


class _RejectUnsupportedNnOpPattern(RewritePattern):
    """拒绝未纳入 nn_lowering family 的 nn op。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 放在所有已支持 family pattern 之后。
    - 若仍有 nn.* op 未被处理，则按现有 unknown op 合同抛出 NnLoweringError。

    使用示例:
    - pattern = _RejectUnsupportedNnOpPattern()

    关联文件:
    - spec: [spec/pass/lowering/nn_lowering/spec.md](spec/pass/lowering/nn_lowering/spec.md)
    - test: [test/pass/nn_lowering/public_name.py](test/pass/nn_lowering/public_name.py)
    - 功能实现: [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter) -> None:
        _ = rewriter
        if not op.name.startswith("nn."):
            return
        raise NnLoweringError(f"unknown op: {op.name}")


class NnLoweringPass(Pass):
    """nn -> kernel lowering pass。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 将 nn dialect op 降至 kernel / dma / symbol。
    - 通过 `PatternRewriteWalker` 驱动单个 nn op 的 rewrite。
    - 兼容旧 `run(...)` 入口，同时对外满足 `ModulePass.apply(...)` 合同。

    使用示例:
    - NnLoweringPass().apply(Context(), module)
    - NnLoweringPass().run(module)

    关联文件:
    - spec: [spec/pass/lowering/nn_lowering/spec.md](spec/pass/lowering/nn_lowering/spec.md)
    - test: [test/pass/nn_lowering/test_lowering_nn_lowering.py](test/pass/nn_lowering/test_lowering_nn_lowering.py)
    - 功能实现: [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
    """

    name = "lower-nn"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        """执行 nn lowering。

        创建者: 金铲铲大作战
        最后一次更改: jcc你莫辜负

        功能说明:
        - 通过 canonical public path 取得 `nn_lowering_patterns()` 返回的 pattern driver。
        - 使用 `PatternRewriteWalker + GreedyRewritePatternApplier` 对 module 原地改写。

        使用示例:
        - NnLoweringPass().apply(Context(), module)

        关联文件:
        - spec: [spec/pass/lowering/nn_lowering/spec.md](spec/pass/lowering/nn_lowering/spec.md)
        - test: [test/pass/nn_lowering/public_name.py](test/pass/nn_lowering/public_name.py)
        - 功能实现: [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
        """

        from kernel_gen.passes.lowering import nn_lowering as nn_lowering_pkg

        PatternRewriteWalker(
            GreedyRewritePatternApplier(
                nn_lowering_pkg.nn_lowering_patterns(),
                ctx=ctx,
                folding_enabled=True,
                dce_enabled=False,
            )
        ).rewrite_module(op)

    def run(self, module: ModuleOp) -> ModuleOp:
        """兼容旧 `run(...)` 入口。"""

        self.apply(Context(), module)
        return module


__all__ = ["NnLoweringError", "NnLoweringPass"]
