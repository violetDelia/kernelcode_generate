"""NN operation exp helper.


功能说明:
- 提供逐元素 exp 运算。

API 列表:
- `exp(value: Memory) -> Memory`

使用示例:
- from kernel_gen.operation.nn.exp import exp

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/nn/test_elementwise.py
- 功能实现: kernel_gen/operation/nn/exp.py
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



def _ensure_float_memory(value: Memory, op_name: str) -> Memory:
    """校验 `exp` 的 `Memory` 与浮点 dtype 输入。


    功能说明:
    - 仅接受 `Memory` 输入。
    - dtype 必须属于公开浮点类型集合。

    使用示例:
    - _ensure_float_memory(Memory([1], NumericType.Float32), "exp")
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
    if value.dtype not in FLOAT_DTYPES:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene=f"nn.{op_name} 参数校验",
                expected=f"{op_name} value dtype must be float",
                actual=str(value.dtype),
                action=ERROR_ACTION,
            )
        )
    return value

def exp(value: Memory) -> Memory:
    """逐元素指数函数。


    功能说明:
    - 仅接受浮点 Memory 输入。
    - 输出继承输入的 shape/dtype/space/format/stride。

    使用示例:
    - exp(Memory(["M", "N"], NumericType.Float32))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_elementwise.py
    - 功能实现: kernel_gen/operation/nn/exp.py
    """
    memory = _ensure_float_memory(value, "exp")
    return memory.clone()

__all__ = ["exp"]
