"""NN operation activation family.

创建者: 守护最好的爱莉希雅
最后一次更改: 金铲铲大作战

功能说明:
- 提供 relu / leaky_relu / sigmoid / tanh / hard_sigmoid 激活函数。

使用示例:
- from kernel_gen.operation.nn.activation import relu, sigmoid, tanh

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/test_operation_nn_elementwise.py
- 功能实现: kernel_gen/operation/nn/activation.py
"""

from __future__ import annotations

from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType
from .common import _ensure_activation_scalar, _ensure_float_memory

def relu(value: object) -> Memory:
    """逐元素 ReLU 激活。

    创建者: 我不是牛马
    最后一次更改: jcc你莫辜负

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
    return memory._clone_with_dtype(memory.dtype)

def leaky_relu(value: object, alpha: int | float = 0.01) -> Memory:
    """逐元素 Leaky ReLU 激活。

    创建者: 我不是牛马
    最后一次更改: jcc你莫辜负

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
    return memory._clone_with_dtype(memory.dtype)

def sigmoid(value: object) -> Memory:
    """逐元素 Sigmoid 激活。

    创建者: 我不是牛马
    最后一次更改: jcc你莫辜负

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
    return memory._clone_with_dtype(memory.dtype)

def tanh(value: object) -> Memory:
    """逐元素 Tanh 激活。

    创建者: 我不是牛马
    最后一次更改: jcc你莫辜负

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
    return memory._clone_with_dtype(memory.dtype)

def hard_sigmoid(value: object, alpha: int | float = 0.2, beta: int | float = 0.5) -> Memory:
    """逐元素 Hard Sigmoid 激活。

    创建者: 我不是牛马
    最后一次更改: jcc你莫辜负

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
    return memory._clone_with_dtype(memory.dtype)

__all__ = [
    "relu",
    "leaky_relu",
    "sigmoid",
    "tanh",
    "hard_sigmoid",
]
