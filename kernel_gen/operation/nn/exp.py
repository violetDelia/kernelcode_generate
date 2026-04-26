"""NN operation exp helper.

创建者: 守护最好的爱莉希雅
最后一次更改: 金铲铲大作战

功能说明:
- 提供逐元素 exp 运算。

API 列表:
- `exp(value: object) -> Memory`

使用示例:
- from kernel_gen.operation.nn.exp import exp

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/test_operation_nn_elementwise.py
- 功能实现: kernel_gen/operation/nn/exp.py
"""

from __future__ import annotations

from kernel_gen.common.errors import _ERROR_TEMPLATE
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.symbol_shape import SymbolShape
from kernel_gen.symbol_variable.type import NumericType

_ERROR_ACTION = "请按接口约束传参"
_FLOAT_DTYPES = (
    NumericType.Float16,
    NumericType.BFloat16,
    NumericType.Float32,
    NumericType.Float64,
)


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


def _ensure_float_memory(value: object, op_name: str) -> Memory:
    """校验 `exp` 的 `Memory` 与浮点 dtype 输入。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅接受 `Memory` 输入。
    - dtype 必须属于公开浮点类型集合。

    使用示例:
    - _ensure_float_memory(Memory([1], NumericType.Float32), "exp")
    """

    if not isinstance(value, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene=f"nn.{op_name} 参数校验",
                expected=f"{op_name} value must be Memory",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if value.dtype not in _FLOAT_DTYPES:
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene=f"nn.{op_name} 参数校验",
                expected=f"{op_name} value dtype must be float",
                actual=str(value.dtype),
                action=_ERROR_ACTION,
            )
        )
    return value

def exp(value: object) -> Memory:
    """逐元素指数函数。

    创建者: 朽木露琪亚
    最后一次更改: jcc你莫辜负

    功能说明:
    - 仅接受浮点 Memory 输入。
    - 输出继承输入的 shape/dtype/space/format/stride。

    使用示例:
    - exp(Memory(["M", "N"], NumericType.Float32))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/exp.py
    """
    memory = _ensure_float_memory(value, "exp")
    return _clone_memory_with_dtype(memory, memory.dtype)

__all__ = ["exp"]
