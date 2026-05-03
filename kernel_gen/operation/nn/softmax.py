"""NN operation softmax helper.


功能说明:
- 提供 softmax 归一化运算。

API 列表:
- `softmax(value: Memory, axis: int = -1) -> Memory`

使用示例:
- from kernel_gen.operation.nn.softmax import softmax

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/nn/test_structured.py
- 功能实现: kernel_gen/operation/nn/softmax.py
"""

from __future__ import annotations

from kernel_gen.core.error import (
    ERROR_ACTION,
    ERROR_TEMPLATE,
    ErrorKind,
    ErrorModule,
    kernel_code_error,
)
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import FLOAT_DTYPES


def softmax(value: Memory, axis: int = -1) -> Memory:
    """沿指定轴执行 softmax 归一化。


    功能说明:
    - 仅接受 Memory 输入，并校验 dtype 与 axis。
    - 数值稳定语义约束为 exp(x - max(x)) / sum(exp(x - max(x)))。
    - 输出 shape/dtype/space/format/stride 与输入保持一致。

    使用示例:
    - softmax(Memory(["M", "N"], NumericType.Float32))
    - softmax(Memory(["B", "C", "H", "W"], NumericType.Float32), axis=1)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_structured.py
    - 功能实现: kernel_gen/operation/nn/softmax.py
    """
    if not isinstance(value, Memory):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.softmax 参数校验",
                expected="softmax value must be Memory",
                actual=type(value).__name__,
                action=ERROR_ACTION,
            )
        )
    if value.dtype not in FLOAT_DTYPES:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.softmax 参数校验",
                expected="softmax value dtype must be float",
                actual=str(value.dtype),
                action=ERROR_ACTION,
            )
        )
    if isinstance(axis, bool) or not isinstance(axis, int):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.softmax 参数校验",
                expected="softmax axis must be int",
                actual=type(axis).__name__,
                action=ERROR_ACTION,
            )
        )
    rank = len(value.shape)
    if axis < -rank or axis >= rank:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.softmax 参数校验",
                expected="softmax axis out of range",
                actual=f"axis={axis} rank={rank}",
                action=ERROR_ACTION,
            )
        )
    _ = axis + rank if axis < 0 else axis
    return value.clone()

__all__ = ["softmax"]
