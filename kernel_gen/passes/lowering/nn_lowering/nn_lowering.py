"""nn -> kernel lowering pass.

创建者: 金铲铲大作战
最后一次更改: 朽木露琪亚

功能说明:
- 将 nn dialect 的逐元素 op lower 为 kernel dialect op。
- 当结果无法复用已有输出时，为结果插入 dma.alloc。
- `nn.softmax` lower 为 `kernel.softmax` 并保留 `axis`。

使用示例:
- from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
- module = NnLoweringPass().run(module)

关联文件:
- spec: spec/pass/lowering/nn_lowering.md
- test: test/pass/nn_lowering/test_lowering_nn_lowering.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
"""

from __future__ import annotations

from collections.abc import Iterable

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
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp, DmaCopyOp, DmaFillOp, DmaTransposeOp
from kernel_gen.dialect.kernel import (
    KernelCastOp,
    KernelExpOp,
    KernelImg2col1dOp,
    KernelImg2col2dOp,
    KernelMatmulOp,
    KernelReduceOp,
    KernelSelectOp,
    KernelSoftmaxOp,
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
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """


_RESULT_TYPED_ALLOC_OPS = {"nn.img2col1d", "nn.img2col2d"}


def _ensure_space_attr(op: Operation) -> NnMemorySpaceAttr:
    """获取并校验 nn op 的 space attribute。

    创建者: 金铲铲大作战
    最后一次更改: 朽木露琪亚

    功能说明:
    - 确认 op.attributes["space"] 为 NnMemorySpaceAttr。

    使用示例:
    - space = _ensure_space_attr(op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
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
    - spec: spec/pass/lowering/nn_lowering.md
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
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    if len(op.operands) != count:
        raise NnLoweringError(f"{op.name} must have {count} operands")


def _ensure_int_attr(op: Operation, name: str) -> int:
    """获取并校验 op 的 int attribute。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 从 op.attributes 获取指定 name。
    - 校验为 IntegerAttr，并返回其值。

    使用示例:
    - axis = _ensure_int_attr(op, "axis")

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    attr = op.attributes.get(name)
    if not isinstance(attr, IntegerAttr):
        raise NnLoweringError(f"{op.name} {name} must be integer")
    return attr.value.data


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
    - spec: spec/pass/lowering/nn_lowering.md
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
    - spec: spec/pass/lowering/nn_lowering.md
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


def _get_symbol_dim_from_source(
    block: Block,
    op: Operation,
    axis: int,
    result_shape: list[int | str],
    operand: SSAValue,
    operand_shape: list[int | str],
) -> SymbolGetDimOp:
    """从 operand 的 symbol dim 提取维度。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 使用 SymbolGetDimOp 从 operand 上读取动态维度。

    使用示例:
    - _get_symbol_dim_from_source(block, op, idx, result_shape, operand, operand_shape)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    axis_offset = len(result_shape) - len(operand_shape)
    source_axis = axis - axis_offset
    if source_axis < 0 or source_axis >= len(operand_shape):
        raise NnLoweringError("NnLoweringBroadcastSymbolDimNotFromSource: axis out of range")
    source_dim = operand_shape[source_axis]
    if not isinstance(source_dim, str):
        raise NnLoweringError("NnLoweringBroadcastSymbolDimNotFromSource: source dim is not symbolic")
    if source_dim != result_shape[axis]:
        raise NnLoweringError("NnLoweringBroadcastSymbolDimNotFromSource: symbol mismatch")
    symbol_op = SymbolGetDimOp(operand, IntAttr(source_axis))
    block.insert_op_before(symbol_op, op)
    return symbol_op


def _ensure_broadcast_shape(
    op: Operation,
    result_type: NnMemoryType,
    operand_type: NnMemoryType,
) -> tuple[list[int | str], list[int | str]]:
    """校验 nn.broadcast 的 shape 合法性。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验 operand 与 result shape 兼容。

    使用示例:
    - result_shape, operand_shape = _ensure_broadcast_shape(op, result_type, operand_type)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    if not isinstance(result_type, NnMemoryType):
        raise NnLoweringError("nn.broadcast result must be nn.memory")
    if not isinstance(operand_type, NnMemoryType):
        raise NnLoweringError("nn.broadcast operand must be nn.memory")

    def _shape_value(dim: Attribute) -> int | str:
        if isinstance(dim, StringAttr):
            return dim.data
        if isinstance(dim, IntAttr):
            return dim.data
        if isinstance(dim, IntegerAttr):
            return dim.value.data
        raise NnLoweringError("nn.broadcast shape must be IntAttr or StringAttr")

    result_shape = [_shape_value(dim) for dim in result_type.shape.data]
    operand_shape = [_shape_value(dim) for dim in operand_type.shape.data]

    if len(result_shape) < len(operand_shape):
        raise NnLoweringError("nn.broadcast result rank must be >= operand rank")

    for dim in operand_shape:
        if isinstance(dim, str) and dim == "?":
            raise NnLoweringError("nn.broadcast operand shape must not contain '?'")

    return result_shape, operand_shape


def _ensure_broadcast_compat(result_shape: list[int | str], operand_shape: list[int | str]) -> None:
    """校验 nn.broadcast 的 shape 兼容性。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 按尾维对齐规则检查 operand/result 维度。
    - 对静态数值不匹配报错，对非法符号扩张报错。

    使用示例:
    - _ensure_broadcast_compat(result_shape, operand_shape)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    axis_offset = len(result_shape) - len(operand_shape)
    for idx in range(axis_offset):
        dim = result_shape[idx]
        if isinstance(dim, str):
            raise NnLoweringError("NnLoweringBroadcastSymbolDimNotFromSource: new symbol dim")
    for idx, operand_dim in enumerate(operand_shape):
        result_dim = result_shape[idx + axis_offset]
        if isinstance(operand_dim, int):
            if isinstance(result_dim, int):
                if operand_dim != 1 and operand_dim != result_dim:
                    raise NnLoweringError("invalid broadcast target shape")
                continue
            raise NnLoweringError("NnLoweringBroadcastSymbolDimNotFromSource: result dim not in source")
        if isinstance(result_dim, str):
            if operand_dim != result_dim:
                raise NnLoweringError("NnLoweringBroadcastSymbolDimNotFromSource: symbol mismatch")
            continue
        raise NnLoweringError("invalid broadcast target shape")


def _ensure_reduce_axis(op_name: str, axes_attr: ArrayAttr) -> int:
    """校验 reduce 轴参数。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 确保 axes_attr 为 ArrayAttr 且仅包含一个 IntegerAttr。

    使用示例:
    - axis = _ensure_reduce_axis("nn.reduce_min", axes_attr)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
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
    if not isinstance(axis_attr, IntegerAttr):
        raise NnLoweringError("reduce axis must be integer")
    return axis_attr.value.data


def _ensure_reduce_keepdim(op_name: str, keepdim_attr: Attribute) -> bool:
    """校验 reduce keepdim 参数。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - keepdim 必须是 IntegerAttr 0 或 1。

    使用示例:
    - keepdim = _ensure_reduce_keepdim("nn.reduce_min", keepdim_attr)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    if not isinstance(keepdim_attr, IntegerAttr):
        raise NnLoweringError("keepdim must be integer")
    keepdim = keepdim_attr.value.data
    if keepdim not in (0, 1):
        raise NnLoweringError("keepdim must be 0 or 1")
    return bool(keepdim)


def _ensure_softmax_axis(op: Operation) -> int:
    """校验 softmax axis。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 从 op.attributes 解析 axis，并校验范围。

    使用示例:
    - axis = _ensure_softmax_axis(op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    axis = _ensure_int_attr(op, "axis")
    result_type = _ensure_single_result(op)
    rank = len(result_type.shape.data)
    if axis < 0 or axis >= rank:
        raise NnLoweringError("softmax axis out of range")
    return axis


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
    - spec: spec/pass/lowering/nn_lowering.md
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
    - spec: spec/pass/lowering/nn_lowering.md
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
    - spec: spec/pass/lowering/nn_lowering.md
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


def _lower_select(block: Block, op: Operation) -> None:
    """lower nn.select。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 先创建 dma.alloc，再调用 kernel.select。

    使用示例:
    - _lower_select(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    space = _ensure_space_attr(op)
    result_type = _ensure_single_result(op)
    _ensure_operand_count(op, 3)
    alloc = DmaAllocOp([], result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = KernelSelectOp(op.operands[0], op.operands[1], op.operands[2], result, space)
    block.insert_op_before(lowered, op)
    op.results[0].replace_by(result)
    block.erase_op(op)


def _lower_cast(block: Block, op: Operation) -> None:
    """lower nn.cast。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 先创建 dma.alloc，再调用 dma.cast。

    使用示例:
    - _lower_cast(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    result_type = _ensure_single_result(op)
    if len(op.operands) == 2:
        _ensure_symbol_or_int(op, op.operands[1])
    elif len(op.operands) != 1:
        raise NnLoweringError(f"{op.name} must have 1 operands")
    operand = op.operands[0]
    if not isinstance(operand.type, NnMemoryType):
        raise NnLoweringError("nn.cast operand must be nn.memory")
    if operand.type.shape != result_type.shape or operand.type.stride != result_type.stride:
        raise NnLoweringError("cast result must preserve symbol dims")
    alloc = DmaAllocOp([], result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = KernelCastOp(operand, result, result_type.space)
    block.insert_op_before(lowered, op)
    op.results[0].replace_by(result)
    block.erase_op(op)


def _lower_exp(block: Block, op: Operation) -> None:
    """lower nn.exp。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 先创建 dma.alloc，再调用 kernel.exp。

    使用示例:
    - _lower_exp(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    space = _ensure_space_attr(op)
    result_type = _ensure_single_result(op)
    _ensure_operand_count(op, 1)
    alloc = DmaAllocOp([], result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = KernelExpOp(op.operands[0], result, space)
    block.insert_op_before(lowered, op)
    op.results[0].replace_by(result)
    block.erase_op(op)


def _lower_reduce(block: Block, op: Operation, *, kind: str) -> None:
    """lower reduce family。

    创建者: 金铲铲大作战
    最后一次更改: 朽木露琪亚

    功能说明:
    - 校验 axes / keepdim。
    - 先创建 dma.alloc，再调用 kernel.reduce(kind=...)。

    使用示例:
    - _lower_reduce(block, op, kind="min")

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
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
    alloc = DmaAllocOp([], result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = KernelReduceOp(operand, result, kind=kind, axis=axis, keepdim=keepdim, space=space)
    block.insert_op_before(lowered, op)
    op.results[0].replace_by(result)
    block.erase_op(op)


def _lower_softmax(block: Block, op: Operation) -> None:
    """lower nn.softmax。

    创建者: 金铲铲大作战
    最后一次更改: 朽木露琪亚

    功能说明:
    - 校验 axis。
    - 先创建 dma.alloc，再调用 kernel.softmax。

    使用示例:
    - _lower_softmax(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    space = _ensure_space_attr(op)
    result_type = _ensure_single_result(op)
    _ensure_operand_count(op, 1)
    axis = _ensure_softmax_axis(op)
    alloc = DmaAllocOp([], result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = KernelSoftmaxOp(op.operands[0], result, axis, space)
    block.insert_op_before(lowered, op)
    op.results[0].replace_by(result)
    block.erase_op(op)


def _lower_matmul(block: Block, op: Operation) -> None:
    """lower nn.matmul。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 校验 shape 与 stride。
    - 先创建 dma.alloc，再调用 kernel.matmul。

    使用示例:
    - _lower_matmul(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
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
    alloc = DmaAllocOp([], result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = KernelMatmulOp(lhs, rhs, result, space)
    block.insert_op_before(lowered, op)
    op.results[0].replace_by(result)
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
    - spec: spec/pass/lowering/nn_lowering.md
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
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    space = _ensure_space_attr(op)
    result_type = _ensure_single_result(op)
    operand, params = _ensure_img2col_params(op, 6, 5)
    alloc = DmaAllocOp(params, result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = KernelImg2col1dOp(operand, *params, result, space)
    block.insert_op_before(lowered, op)
    op.results[0].replace_by(result)
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
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    space = _ensure_space_attr(op)
    result_type = _ensure_single_result(op)
    operand, params = _ensure_img2col_params(op, 11, 10)
    alloc = DmaAllocOp(params, result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = KernelImg2col2dOp(operand, *params, result, space)
    block.insert_op_before(lowered, op)
    op.results[0].replace_by(result)
    block.erase_op(op)


def _lower_broadcast(block: Block, op: Operation) -> None:
    """lower nn.broadcast。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 允许动态 shape，并使用 symbol.get_dim。
    - 先创建 dma.alloc，再调用 dma.broadcast。

    使用示例:
    - _lower_broadcast(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    result_type = _ensure_single_result(op)
    if len(op.operands) == 2:
        _ensure_symbol_or_int(op, op.operands[1])
    elif len(op.operands) != 1:
        raise NnLoweringError(f"{op.name} must have 1 operands")
    operand = op.operands[0]
    if not isinstance(operand.type, NnMemoryType):
        raise NnLoweringError("nn.broadcast operand must be nn.memory")

    result_shape, operand_shape = _ensure_broadcast_shape(op, result_type, operand.type)
    _ensure_broadcast_compat(result_shape, operand_shape)
    if any(isinstance(dim, str) for dim in result_shape):
        symbol_dims: list[SSAValue] = []
        for idx, dim in enumerate(result_shape):
            if isinstance(dim, str):
                symbol_op = _get_symbol_dim_from_source(
                    block,
                    op,
                    idx,
                    result_shape,
                    operand,
                    operand_shape,
                )
                symbol_dims.append(symbol_op.result)
        alloc = DmaAllocOp(symbol_dims, result_type)
    else:
        alloc = DmaAllocOp([], result_type)

    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = DmaBroadcastOp(result, operand)
    block.insert_op_before(lowered, op)
    op.results[0].replace_by(result)
    block.erase_op(op)


def _lower_transpose(block: Block, op: Operation) -> None:
    """lower nn.transpose。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验 perm / shape / stride。
    - 先创建 dma.alloc，再调用 dma.transpose。

    使用示例:
    - _lower_transpose(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    result_type = _ensure_single_result(op)
    operand = op.operands[0]
    if not isinstance(operand.type, NnMemoryType):
        raise NnLoweringError("nn.transpose operand must be nn.memory")
    perm_attr = op.attributes.get("perm")
    if not isinstance(perm_attr, ArrayAttr):
        raise NnLoweringError("nn.transpose perm must be ArrayAttr")
    perm = perm_attr.data
    if len(perm) != len(result_type.shape.data):
        raise NnLoweringError("nn.transpose perm rank mismatch")
    alloc = DmaAllocOp([], result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = DmaTransposeOp(result, operand, perm_attr)
    block.insert_op_before(lowered, op)
    op.results[0].replace_by(result)
    block.erase_op(op)


def _lower_broadcast_to(block: Block, op: Operation) -> None:
    """lower nn.broadcast_to。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 先创建 dma.alloc，再调用 dma.broadcast。

    使用示例:
    - _lower_broadcast_to(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    result_type = _ensure_single_result(op)
    _ensure_operand_count(op, 2)
    operand = op.operands[0]
    if not isinstance(operand.type, NnMemoryType):
        raise NnLoweringError("nn.broadcast_to operand must be nn.memory")
    if not isinstance(op.operands[1].type, SymbolValueType):
        raise NnLoweringError("nn.broadcast_to target must be symbol.int")
    alloc = DmaAllocOp([op.operands[1]], result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = DmaBroadcastOp(result, operand)
    block.insert_op_before(lowered, op)
    op.results[0].replace_by(result)
    block.erase_op(op)


def _lower_fill(block: Block, op: Operation) -> None:
    """lower nn.fill。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 先创建 dma.alloc，再调用 dma.fill。

    使用示例:
    - _lower_fill(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    result_type = _ensure_single_result(op)
    _ensure_operand_count(op, 1)
    alloc = DmaAllocOp([], result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = DmaFillOp(result, op.operands[0])
    block.insert_op_before(lowered, op)
    op.results[0].replace_by(result)
    block.erase_op(op)


def _lower_copy(block: Block, op: Operation) -> None:
    """lower nn.copy。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 先创建 dma.alloc，再调用 dma.copy。

    使用示例:
    - _lower_copy(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    result_type = _ensure_single_result(op)
    _ensure_operand_count(op, 1)
    alloc = DmaAllocOp([], result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = DmaCopyOp(result, op.operands[0])
    block.insert_op_before(lowered, op)
    op.results[0].replace_by(result)
    block.erase_op(op)


def _lower_op(block: Block, op: Operation) -> None:
    """lower 单个 op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 根据 op.name 分发到具体 lowering。

    使用示例:
    - _lower_op(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    from .element_binary_lowering import lower_element_binary_family

    if lower_element_binary_family(block, op):
        return
    if op.name == "nn.select":
        _lower_select(block, op)
        return
    if op.name == "nn.cast":
        _lower_cast(block, op)
        return
    if op.name == "nn.exp":
        _lower_exp(block, op)
        return
    if op.name == "nn.reduce_sum":
        _lower_reduce(block, op, kind="sum")
        return
    if op.name == "nn.reduce_min":
        _lower_reduce(block, op, kind="min")
        return
    if op.name == "nn.reduce_max":
        _lower_reduce(block, op, kind="max")
        return
    if op.name == "nn.softmax":
        _lower_softmax(block, op)
        return
    if op.name == "nn.matmul":
        _lower_matmul(block, op)
        return
    if op.name == "nn.img2col1d":
        _lower_img2col1d(block, op)
        return
    if op.name == "nn.img2col2d":
        _lower_img2col2d(block, op)
        return
    if op.name == "nn.broadcast":
        _lower_broadcast(block, op)
        return
    if op.name == "nn.transpose":
        _lower_transpose(block, op)
        return
    if op.name == "nn.broadcast_to":
        _lower_broadcast_to(block, op)
        return
    if op.name == "nn.fill":
        _lower_fill(block, op)
        return
    if op.name == "nn.copy":
        _lower_copy(block, op)
        return
    raise NnLoweringError(f"unknown op: {op.name}")


def _lower_block(block: Block) -> None:
    """lower block 内的 ops。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 逐个遍历 op 执行 lowering。

    使用示例:
    - _lower_block(block)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    for op in list(block.ops):
        if isinstance(op, func.ReturnOp):
            continue
        _lower_op(block, op)


def _lower_func(func_op: func.FuncOp) -> None:
    """lower func。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 对 func 的 entry block 进行 lowering。

    使用示例:
    - _lower_func(func_op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    block = func_op.body.block
    _lower_block(block)


def _lower_module(module: ModuleOp) -> None:
    """lower module。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 遍历 module 内所有 func 并执行 lowering。

    使用示例:
    - _lower_module(module)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    for op in module.ops:
        if not isinstance(op, func.FuncOp):
            continue
        _lower_func(op)


class NnLoweringPass(Pass):
    """nn -> kernel lowering pass。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 将 nn dialect op 降至 kernel / dma / symbol。
    - 统一对 nn_lowering pass 的入口。

    使用示例:
    - NnLoweringPass().run(module)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    name = "lower-nn"

    def run(self, module: ModuleOp) -> ModuleOp:
        """执行 nn lowering。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 调用内部 lowering 对 module 进行原地变换。

        使用示例:
        - NnLoweringPass().run(module)

        关联文件:
        - spec: spec/pass/lowering/nn_lowering.md
        - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
        - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
        """

        _lower_module(module)
        return module


__all__ = ["NnLoweringError", "NnLoweringPass"]
