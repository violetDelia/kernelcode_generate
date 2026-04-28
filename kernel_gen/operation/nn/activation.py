"""NN operation activation family.

创建者: 守护最好的爱莉希雅
最后一次更改: 大闸蟹

功能说明:
- 提供 relu / leaky_relu / sigmoid / tanh / hard_sigmoid 激活函数。

API 列表:
- `relu(value: object) -> Memory`
- `leaky_relu(value: object, alpha: int | float = 0.01) -> Memory`
- `sigmoid(value: object) -> Memory`
- `tanh(value: object) -> Memory`
- `hard_sigmoid(value: object, alpha: int | float = 0.2, beta: int | float = 0.5) -> Memory`

使用示例:
- from kernel_gen.operation.nn.activation import relu, sigmoid, tanh

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/test_operation_nn_elementwise.py
- 功能实现: kernel_gen/operation/nn/activation.py
"""

from __future__ import annotations

import math

from kernel_gen.core.contracts import _ERROR_TEMPLATE
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import FLOAT_DTYPES

_ERROR_ACTION = "请按接口约束传参"


def _ensure_float_memory(value: object, op_name: str) -> Memory:
    """校验激活函数的 `Memory` 与浮点 dtype 输入。

    创建者: 小李飞刀
    最后一次更改: 大闸蟹

    功能说明:
    - 仅接受 `Memory` 输入。
    - dtype 必须属于公开浮点类型集合。

    使用示例:
    - _ensure_float_memory(Memory([1], NumericType.Float32), "relu")
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
    if value.dtype not in FLOAT_DTYPES:
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene=f"nn.{op_name} 参数校验",
                expected=f"{op_name} value dtype must be float",
                actual=str(value.dtype),
                action=_ERROR_ACTION,
            )
        )
    return value


def _ensure_activation_scalar(name: str, value: object) -> None:
    """校验激活函数数值参数。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅接受有限 `int/float`。
    - 拒绝 `bool`、`SymbolDim`、`NaN` 与 `Inf`。

    使用示例:
    - _ensure_activation_scalar("alpha", 0.2)
    """

    if isinstance(value, bool) or isinstance(value, SymbolDim):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.activation 参数校验",
                expected=f"{name} must be int or float",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if not isinstance(value, (int, float)):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.activation 参数校验",
                expected=f"{name} must be int or float",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if not math.isfinite(value):
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.activation 参数校验",
                expected=f"{name} must be finite",
                actual=str(value),
                action=_ERROR_ACTION,
            )
        )

def relu(value: object) -> Memory:
    """逐元素 ReLU 激活。

    创建者: 我不是牛马
    最后一次更改: 大闸蟹

    功能说明:
    - 仅接受 Memory 输入，dtype 需为浮点类型。
    - 输出继承输入的 shape/dtype/space/format/stride。

    使用示例:
    - relu(Memory(["M", "N"], NumericType.Float32))
    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/activation.py
    """
    memory = _ensure_float_memory(value, "relu")
    return memory.clone()

def leaky_relu(value: object, alpha: int | float = 0.01) -> Memory:
    """逐元素 Leaky ReLU 激活。

    创建者: 我不是牛马
    最后一次更改: 大闸蟹

    功能说明:
    - 仅接受 Memory 输入，dtype 需为浮点类型。
    - alpha 必须为有限的 int/float。
    - 输出继承输入的 shape/dtype/space/format/stride。

    使用示例:
    - leaky_relu(Memory(["M", "N"], NumericType.Float16), alpha=0.2)
    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/activation.py
    """
    memory = _ensure_float_memory(value, "leaky_relu")
    _ensure_activation_scalar("alpha", alpha)
    return memory.clone()

def sigmoid(value: object) -> Memory:
    """逐元素 Sigmoid 激活。

    创建者: 我不是牛马
    最后一次更改: 大闸蟹

    功能说明:
    - 仅接受 Memory 输入，dtype 需为浮点类型。
    - 输出继承输入的 shape/dtype/space/format/stride。

    使用示例:
    - sigmoid(Memory(["M", "N"], NumericType.Float32))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/activation.py
    """
    memory = _ensure_float_memory(value, "sigmoid")
    return memory.clone()

def tanh(value: object) -> Memory:
    """逐元素 Tanh 激活。

    创建者: 我不是牛马
    最后一次更改: 大闸蟹

    功能说明:
    - 仅接受 Memory 输入，dtype 需为浮点类型。
    - 输出继承输入的 shape/dtype/space/format/stride。

    使用示例:
    - tanh(Memory(["M", "N"], NumericType.Float32))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/activation.py
    """
    memory = _ensure_float_memory(value, "tanh")
    return memory.clone()

def hard_sigmoid(value: object, alpha: int | float = 0.2, beta: int | float = 0.5) -> Memory:
    """逐元素 Hard Sigmoid 激活。

    创建者: 我不是牛马
    最后一次更改: 大闸蟹

    功能说明:
    - 仅接受 Memory 输入，dtype 需为浮点类型。
    - alpha/beta 必须为有限的 int/float。
    - 输出继承输入的 shape/dtype/space/format/stride。

    使用示例:
    - hard_sigmoid(Memory(["M", "N"], NumericType.Float32), alpha=0.2, beta=0.5)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/activation.py
    """
    memory = _ensure_float_memory(value, "hard_sigmoid")
    _ensure_activation_scalar("alpha", alpha)
    _ensure_activation_scalar("beta", beta)
    return memory.clone()

__all__ = [
    "relu",
    "leaky_relu",
    "sigmoid",
    "tanh",
    "hard_sigmoid",
]
