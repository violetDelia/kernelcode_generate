"""NN operation softmax helper.

创建者: 守护最好的爱莉希雅
最后一次更改: 金铲铲大作战

功能说明:
- 提供 softmax 归一化运算。

API 列表:
- `softmax(value: object, axis: int = -1) -> Memory`

使用示例:
- from kernel_gen.operation.nn.softmax import softmax

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/test_operation_nn_structured.py
- 功能实现: kernel_gen/operation/nn/softmax.py
"""

from __future__ import annotations

from kernel_gen.common.errors import _ERROR_TEMPLATE
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.symbol_shape import SymbolShape
from kernel_gen.symbol_variable.type import NumericType

_ERROR_ACTION = "请按接口约束传参"


def _clone_shape(shape: SymbolShape | None) -> SymbolShape | None:
    """复制 `SymbolShape`，避免输出与输入共享符号实例。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 对 `Memory` 的 shape/stride 做逐维复制。

    使用示例:
    - _clone_shape(SymbolShape(["M", "N"]))
    """

    if shape is None:
        return None
    return SymbolShape([SymbolDim(dim.get_symbol()) for dim in shape.get_shape()])


def _clone_memory_with_dtype(value: Memory, dtype: NumericType) -> Memory:
    """按指定 dtype 复制 `Memory` 的公开元信息。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅通过公开元信息构造结果，避免跨文件依赖私有 helper。

    使用示例:
    - _clone_memory_with_dtype(Memory([1], NumericType.Float32), NumericType.Float32)
    """

    return Memory(
        _clone_shape(value.shape),
        dtype,
        space=value.space,
        stride=_clone_shape(value.stride),
        format=value.format,
    )

def softmax(value: object, axis: int = -1) -> Memory:
    """沿指定轴执行 softmax 归一化。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 仅接受 Memory 输入，并校验 dtype 与 axis。
    - 数值稳定语义约束为 exp(x - max(x)) / sum(exp(x - max(x)))。
    - 输出 shape/dtype/space/format/stride 与输入保持一致。

    使用示例:
    - softmax(Memory(["M", "N"], NumericType.Float32))
    - softmax(Memory(["B", "C", "H", "W"], NumericType.Float32), axis=1)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_structured.py
    - 功能实现: kernel_gen/operation/nn/softmax.py
    """
    if not isinstance(value, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.softmax 参数校验",
                expected="softmax value must be Memory",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if value.dtype not in (
        NumericType.Float16,
        NumericType.BFloat16,
        NumericType.Float32,
        NumericType.Float64,
    ):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.softmax 参数校验",
                expected="softmax value dtype must be float",
                actual=str(value.dtype),
                action=_ERROR_ACTION,
            )
        )
    if isinstance(axis, bool) or not isinstance(axis, int):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.softmax 参数校验",
                expected="softmax axis must be int",
                actual=type(axis).__name__,
                action=_ERROR_ACTION,
            )
        )
    rank = len(value.shape)
    if axis < -rank or axis >= rank:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.softmax 参数校验",
                expected="softmax axis out of range",
                actual=f"axis={axis} rank={rank}",
                action=_ERROR_ACTION,
            )
        )
    _ = axis + rank if axis < 0 else axis
    return _clone_memory_with_dtype(value, value.dtype)

__all__ = ["softmax"]
