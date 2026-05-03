"""NN operation reduction family.


功能说明:
- 提供 reduce_sum/reduce_min/reduce_max family 实现

API 列表:
- `reduce_sum(value: Memory, axis: AxisInput = None, keepdim: bool = False) -> Memory`
- `reduce_min(value: Memory, axis: AxisInput = None, keepdim: bool = False) -> Memory`
- `reduce_max(value: Memory, axis: AxisInput = None, keepdim: bool = False) -> Memory`

使用示例:
- from kernel_gen.operation.nn import reduce_sum, reduce_min, reduce_max

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/nn/test_reduction.py
- 功能实现: kernel_gen/operation/nn/reduction.py
"""

from __future__ import annotations

from collections.abc import Sequence

from kernel_gen.core.contracts import default_stride as _common_default_stride
from kernel_gen.core.error import (
    ERROR_ACTION,
    ERROR_TEMPLATE,
    ErrorKind,
    ErrorModule,
    kernel_code_error,
)
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.symbol_shape import SymbolShape
from kernel_gen.symbol_variable.type import Farmat, NumericType

AxisInput = int | Sequence[int] | None


def _ensure_reduce_memory(value: Memory, op_name: str) -> Memory:
    """校验归约算子的 Memory 输入。


    功能说明:
    - 仅接受 Memory 输入。
    - 供 reduce_sum/reduce_min/reduce_max 共用。

    使用示例:
    - _ensure_reduce_memory(Memory([2, 3], NumericType.Float32), "reduce_sum")

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_reduction.py
    - 功能实现: kernel_gen/operation/nn/reduction.py
    """
    if not isinstance(value, Memory):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene=f"nn.{op_name} 参数校验",
                expected=f"{op_name} value must be Memory",
                actual=type(value).__name__,
                action=ERROR_ACTION,
            )
        )
    return value


def _normalize_reduce_axes(axis: AxisInput, rank: int, op_name: str) -> tuple[int, ...]:
    """规范化 reduce 轴列表。


    功能说明:
    - 支持 None/int/Sequence[int] 三种 axis 输入。
    - 统一处理负轴、越界、重复轴与空序列错误。

    使用示例:
    - _normalize_reduce_axes([0, -1], rank=3, op_name="reduce_sum")

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_reduction.py
    - 功能实现: kernel_gen/operation/nn/reduction.py
    """
    if axis is None:
        return tuple(range(rank))
    if isinstance(axis, bool):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene=f"nn.{op_name} 参数校验",
                expected=f"{op_name} axis must be None, int, or Sequence[int]",
                actual=type(axis).__name__,
                action=ERROR_ACTION,
            )
        )

    axis_values: list[int]
    if isinstance(axis, int):
        axis_values = [axis]
    elif isinstance(axis, Sequence) and not isinstance(axis, (str, bytes)):
        axis_values = list(axis)
        if not axis_values:
            raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
                ERROR_TEMPLATE.format(
                    scene=f"nn.{op_name} 参数校验",
                    expected=f"{op_name} axis sequence must not be empty",
                    actual="[]",
                    action=ERROR_ACTION,
                )
            )
    else:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene=f"nn.{op_name} 参数校验",
                expected=f"{op_name} axis must be None, int, or Sequence[int]",
                actual=type(axis).__name__,
                action=ERROR_ACTION,
            )
        )

    normalized: list[int] = []
    seen: set[int] = set()
    for axis_value in axis_values:
        if isinstance(axis_value, bool) or not isinstance(axis_value, int):
            raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
                ERROR_TEMPLATE.format(
                    scene=f"nn.{op_name} 参数校验",
                    expected=f"{op_name} axis elements must be int",
                    actual=type(axis_value).__name__,
                    action=ERROR_ACTION,
                )
            )
        normalized_axis = axis_value + rank if axis_value < 0 else axis_value
        if normalized_axis < 0 or normalized_axis >= rank:
            raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
                ERROR_TEMPLATE.format(
                    scene=f"nn.{op_name} 参数校验",
                    expected=f"{op_name} axis must be within [-{rank}, {rank - 1}]",
                    actual=f"axis={axis_value} rank={rank}",
                    action=ERROR_ACTION,
                )
            )
        if normalized_axis in seen:
            raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
                ERROR_TEMPLATE.format(
                    scene=f"nn.{op_name} 参数校验",
                    expected=f"{op_name} axis must be unique",
                    actual=f"axis={axis_values}",
                    action=ERROR_ACTION,
                )
            )
        seen.add(normalized_axis)
        normalized.append(normalized_axis)
    return tuple(normalized)


def _ensure_reduce_keepdim(keepdim: bool, op_name: str) -> bool:
    """校验归约 keepdim 参数。


    功能说明:
    - 仅接受 bool 作为 keepdim 输入。

    使用示例:
    - _ensure_reduce_keepdim(True, "reduce_sum")

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_reduction.py
    - 功能实现: kernel_gen/operation/nn/reduction.py
    """
    if not isinstance(keepdim, bool):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene=f"nn.{op_name} 参数校验",
                expected=f"{op_name} keepdim must be bool",
                actual=type(keepdim).__name__,
                action=ERROR_ACTION,
            )
        )
    return keepdim


def _build_reduce_result_shape(value: Memory, axes: tuple[int, ...], keepdim: bool) -> SymbolShape:
    """根据归约轴推导输出 shape。


    功能说明:
    - keepdim=True 时将被归约轴替换为 1。
    - keepdim=False 时移除被归约轴；若结果为空则回落到 [1]。

    使用示例:
    - _build_reduce_result_shape(Memory([2, 3, 4], NumericType.Float32), (1,), keepdim=True)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_reduction.py
    - 功能实现: kernel_gen/operation/nn/reduction.py
    """
    dims = value.shape.get_shape()
    if keepdim:
        result_dims = [SymbolDim(1) if index in axes else dim for index, dim in enumerate(dims)]
    else:
        result_dims = [dim for index, dim in enumerate(dims) if index not in axes]
        if not result_dims:
            result_dims = [SymbolDim(1)]
    return SymbolShape(result_dims)


def _ensure_non_empty_reduction_extent(value: Memory, axes: tuple[int, ...], op_name: str) -> None:
    """校验 reduce_min/max 的静态空归约域。


    功能说明:
    - 若被归约轴的静态维度为 0，则直接报错。
    - 动态维度保留到后续阶段处理。

    使用示例:
    - _ensure_non_empty_reduction_extent(Memory([0, 4], NumericType.Float32), (0,), "reduce_min")

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_reduction.py
    - 功能实现: kernel_gen/operation/nn/reduction.py
    """
    for axis in axes:
        dim_value = value.shape[axis].get_value()
        if isinstance(dim_value, int) and dim_value == 0:
            raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
                ERROR_TEMPLATE.format(
                    scene=f"nn.{op_name} 参数校验",
                    expected=f"{op_name} reduction extent must be non-empty",
                    actual=f"axis={axis} dim=0",
                    action=ERROR_ACTION,
                )
            )


def _reduce_memory_result(
    value: Memory,
    axis: AxisInput,
    keepdim: bool,
    op_name: str,
    *,
    reject_empty_extent: bool,
) -> Memory:
    """推导 nn.reduce_* 的结果 Memory。


    功能说明:
    - 统一执行 value/axis/keepdim 校验。
    - 按 keepdim 规则推导 shape，并固定输出为默认布局。

    使用示例:
    - _reduce_memory_result(mem, axis=[1], keepdim=False, op_name="reduce_sum", reject_empty_extent=False)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_reduction.py
    - 功能实现: kernel_gen/operation/nn/reduction.py
    """
    memory = _ensure_reduce_memory(value, op_name)
    keepdim_flag = _ensure_reduce_keepdim(keepdim, op_name)
    axes = _normalize_reduce_axes(axis, len(memory.shape), op_name)
    if reject_empty_extent:
        _ensure_non_empty_reduction_extent(memory, axes, op_name)
    result_shape = _build_reduce_result_shape(memory, axes, keepdim_flag)
    return Memory(
        result_shape,
        memory.dtype,
        space=memory.space,
        stride=_common_default_stride(result_shape),
        format=Farmat.Norm,
    )


def reduce_sum(value: Memory, axis: AxisInput = None, keepdim: bool = False) -> Memory:
    """按指定轴执行求和归约。


    功能说明:
    - 支持 axis=None/int/Sequence[int] 三种归约写法。
    - keepdim=False 且全部轴归约时，输出回落到 [1] 标量形状。

    使用示例:
    - reduce_sum(Memory([2, 3, 4], NumericType.Float32))
    - reduce_sum(Memory([2, 3, 4], NumericType.Float32), axis=1, keepdim=True)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_reduction.py
    - 功能实现: kernel_gen/operation/nn/reduction.py
    """
    return _reduce_memory_result(
        value,
        axis,
        keepdim,
        "reduce_sum",
        reject_empty_extent=False,
    )


def reduce_min(value: Memory, axis: AxisInput = None, keepdim: bool = False) -> Memory:
    """按指定轴执行最小值归约。


    功能说明:
    - 统一执行 axis/keepdim 校验与 shape 推导。
    - 对静态可判定的空归约域直接报 KernelCodeError。

    使用示例:
    - reduce_min(Memory([2, 3, 4], NumericType.Float32), axis=[2])

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_reduction.py
    - 功能实现: kernel_gen/operation/nn/reduction.py
    """
    return _reduce_memory_result(
        value,
        axis,
        keepdim,
        "reduce_min",
        reject_empty_extent=True,
    )


def reduce_max(value: Memory, axis: AxisInput = None, keepdim: bool = False) -> Memory:
    """按指定轴执行最大值归约。


    功能说明:
    - 统一执行 axis/keepdim 校验与 shape 推导。
    - 对静态可判定的空归约域直接报 KernelCodeError。

    使用示例:
    - reduce_max(Memory([2, 3, 4], NumericType.Float32), axis=0, keepdim=True)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_reduction.py
    - 功能实现: kernel_gen/operation/nn/reduction.py
    """
    return _reduce_memory_result(
        value,
        axis,
        keepdim,
        "reduce_max",
        reject_empty_extent=True,
    )

__all__ = [
    "reduce_sum",
    "reduce_min",
    "reduce_max",
]
