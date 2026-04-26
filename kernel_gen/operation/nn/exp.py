"""NN operation exp helper.

创建者: 守护最好的爱莉希雅
最后一次更改: 金铲铲大作战

功能说明:
- 提供逐元素 exp 运算。

使用示例:
- from kernel_gen.operation.nn.exp import exp

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/test_operation_nn_elementwise.py
- 功能实现: kernel_gen/operation/nn/exp.py
"""

from __future__ import annotations

from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType
from .common import _ensure_float_memory

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
    return memory._clone_with_dtype(memory.dtype)

__all__ = ["exp"]
