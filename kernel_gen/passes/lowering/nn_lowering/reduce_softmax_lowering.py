"""reduce family lowering 实现。

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 提供 nn.exp / nn.reduce_* 的 lowering 入口。
- 统一 reduce 族 op 到 kernel.reduce(kind=...)。
- `nn.softmax` 不在本层直接 lowering，需先由上游完成分解。

使用示例:
- from kernel_gen.passes.lowering.nn_lowering.reduce_softmax_lowering import lower_reduce_softmax_family
- handled = lower_reduce_softmax_family(block, op)

关联文件:
- spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
- test: test/pass/nn_lowering/reduce_sum.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
"""

from __future__ import annotations

from xdsl.dialects.builtin import ArrayAttr, IntAttr, IntegerAttr, StringAttr
from xdsl.ir import Attribute, Block, Operation, SSAValue

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.kernel import KernelExpOp, KernelReduceOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolGetDimOp
from .nn_lowering import (
    NnLoweringError,
    _ensure_operand_count,
    _ensure_single_result,
    _ensure_space_attr,
    _ensure_symbol_or_int,
)


def _ensure_int_attr(op: Operation, name: str) -> int:
    """获取并校验 op 的 int attribute。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 从 op.attributes 获取指定 name。
    - 校验为 IntegerAttr，并返回其值。

    使用示例:
    - axis = _ensure_int_attr(op, "axis")

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/softmax.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
    """

    attr = op.attributes.get(name)
    if isinstance(attr, IntegerAttr):
        return attr.value.data
    if isinstance(attr, IntAttr):
        return attr.data
    raise NnLoweringError(f"{op.name} {name} must be integer")


def _ensure_reduce_axis(op_name: str, axes_attr: ArrayAttr) -> int:
    """校验 reduce 轴参数。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 确保 axes_attr 为 ArrayAttr 且仅包含一个 IntegerAttr。

    使用示例:
    - axis = _ensure_reduce_axis("nn.reduce_min", axes_attr)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/reduce_min.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
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
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/reduce_min.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
    """

    if isinstance(keepdim_attr, IntegerAttr):
        keepdim = keepdim_attr.value.data
    elif isinstance(keepdim_attr, IntAttr):
        keepdim = keepdim_attr.data
    else:
        raise NnLoweringError("keepdim must be integer")
    if keepdim in (0, 1, -1):
        return bool(keepdim)
    raise NnLoweringError("keepdim must be 0 or 1")


def _build_alloc_dynamic_shape_from_operand(
    block: Block,
    op: Operation,
    operand: Operation,
    result_type: NnMemoryType,
    axis_map: list[int],
) -> list[SSAValue]:
    """基于 operand 构造 dma.alloc 的 dynamic_shape。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 针对 result_type 的符号维度插入 symbol.get_dim。
    - 以 axis_map 指定 result 维度与 operand 维度的映射。

    使用示例:
    - dynamic_shape = _build_alloc_dynamic_shape_from_operand(block, op, operand, result_type, axis_map)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/reduce_sum.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
    """

    if not isinstance(operand.type, NnMemoryType):
        raise NnLoweringError(f"{op.name} operand must be nn.memory")

    dynamic_shape: list[SSAValue] = []
    for result_axis, dim in enumerate(result_type.shape.data):
        if not isinstance(dim, StringAttr):
            continue
        operand_axis = axis_map[result_axis]
        symbol_op = SymbolGetDimOp(operand, IntAttr(operand_axis))
        block.insert_op_before(symbol_op, op)
        dynamic_shape.append(symbol_op.result)
    return dynamic_shape


def _lower_exp(block: Block, op: Operation) -> None:
    """lower nn.exp。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 先创建 dma.alloc，再调用 kernel.exp。

    使用示例:
    - _lower_exp(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/exp.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
    """

    space = _ensure_space_attr(op)
    result_type = _ensure_single_result(op)
    _ensure_operand_count(op, 1)
    operand = op.operands[0]
    if not isinstance(operand.type, NnMemoryType):
        raise NnLoweringError("nn.exp operand must be nn.memory")
    if operand.type.shape != result_type.shape or operand.type.stride != result_type.stride:
        raise NnLoweringError("nn.exp result shape must match operand")
    axis_map = list(range(len(result_type.shape.data)))
    dynamic_shape = _build_alloc_dynamic_shape_from_operand(block, op, operand, result_type, axis_map)
    alloc = DmaAllocOp(dynamic_shape, result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = KernelExpOp(result, operand, space)
    block.insert_op_before(lowered, op)
    op.results[0].replace_by(result)
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
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/reduce_sum.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
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
    operand_shape = operand.type.shape.data
    result_shape = result_type.shape.data
    if keepdim:
        for idx, operand_dim in enumerate(operand_shape):
            result_dim = result_shape[idx]
            if idx == axis:
                if isinstance(result_dim, StringAttr):
                    raise NnLoweringError("reduce keepdim dimension must be 1")
                if isinstance(result_dim, IntegerAttr):
                    dim_value = result_dim.value.data
                elif isinstance(result_dim, IntAttr):
                    dim_value = result_dim.data
                else:
                    raise NnLoweringError("reduce keepdim dimension must be 1")
                if dim_value != 1:
                    raise NnLoweringError("reduce keepdim dimension must be 1")
            else:
                if isinstance(result_dim, StringAttr) and isinstance(operand_dim, StringAttr):
                    if result_dim.data != operand_dim.data:
                        raise NnLoweringError("reduce shape mismatch")
                elif isinstance(result_dim, (IntegerAttr, IntAttr)) and isinstance(
                    operand_dim, (IntegerAttr, IntAttr)
                ):
                    result_value = result_dim.value.data if isinstance(result_dim, IntegerAttr) else result_dim.data
                    operand_value = (
                        operand_dim.value.data if isinstance(operand_dim, IntegerAttr) else operand_dim.data
                    )
                    if result_value != operand_value:
                        raise NnLoweringError("reduce shape mismatch")
                else:
                    raise NnLoweringError("reduce shape mismatch")
    if keepdim:
        axis_map = list(range(operand_rank))
    else:
        axis_map = []
        for result_axis in range(result_rank):
            operand_axis = result_axis if result_axis < axis else result_axis + 1
            axis_map.append(operand_axis)
        for result_axis, operand_axis in enumerate(axis_map):
            result_dim = result_shape[result_axis]
            operand_dim = operand_shape[operand_axis]
            if isinstance(result_dim, StringAttr) and isinstance(operand_dim, StringAttr):
                if result_dim.data != operand_dim.data:
                    raise NnLoweringError("reduce shape mismatch")
            elif isinstance(result_dim, (IntegerAttr, IntAttr)) and isinstance(
                operand_dim, (IntegerAttr, IntAttr)
            ):
                result_value = result_dim.value.data if isinstance(result_dim, IntegerAttr) else result_dim.data
                operand_value = operand_dim.value.data if isinstance(operand_dim, IntegerAttr) else operand_dim.data
                if result_value != operand_value:
                    raise NnLoweringError("reduce shape mismatch")
            else:
                raise NnLoweringError("reduce shape mismatch")
    dynamic_shape = _build_alloc_dynamic_shape_from_operand(block, op, operand, result_type, axis_map)
    alloc = DmaAllocOp(dynamic_shape, result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = KernelReduceOp(result, operand, kind=kind, axis=axis, keepdim=keepdim, space=space)
    lowered.attributes = {
        "axis": lowered.attributes["axis"],
        "keepdim": lowered.attributes["keepdim"],
        "kind": lowered.attributes["kind"],
        "space": lowered.attributes["space"],
    }
    block.insert_op_before(lowered, op)
    op.results[0].replace_by(result)
    block.erase_op(op)


def lower_reduce_softmax_family(block: Block, op: Operation) -> bool:
    """处理 reduce family 的 lowering。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 识别 nn.exp / nn.reduce_*。
    - 对匹配 op 执行 lowering 并返回 True。

    使用示例:
    - handled = lower_reduce_softmax_family(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/reduce_sum.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
    """

    if op.name == "nn.exp":
        _lower_exp(block, op)
        return True
    if op.name == "nn.reduce_sum":
        _lower_reduce(block, op, kind="sum")
        return True
    if op.name == "nn.reduce_min":
        _lower_reduce(block, op, kind="min")
        return True
    if op.name == "nn.reduce_max":
        _lower_reduce(block, op, kind="max")
        return True
    return False


__all__ = ["lower_reduce_softmax_family"]
