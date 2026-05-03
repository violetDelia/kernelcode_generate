"""NN operation fc helper.


功能说明:
- 提供全连接运算。

API 列表:
- `fc(value: Memory, weight: Memory, bias: Memory | None = None) -> Memory`

使用示例:
- from kernel_gen.operation.nn.fc import fc

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/nn/test_structured.py
- 功能实现: kernel_gen/operation/nn/fc.py
"""

from __future__ import annotations

from kernel_gen.core.contracts import default_stride
from kernel_gen.core.error import (
    ERROR_ACTION,
    ERROR_TEMPLATE,
    ErrorKind,
    ErrorModule,
    kernel_code_error,
)
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_shape import SymbolShape
from kernel_gen.symbol_variable.type import Farmat, NumericType



def _resolve_add_dtype(lhs: NumericType, rhs: NumericType) -> NumericType:
    """按公开 `Memory` 算术语义推导 nn 结构化算子的结果 dtype。


    功能说明:
    - 复用 `Memory` 的公开加法路径推导 dtype。
    - 当 dtype 组合不受支持时，转为 `nn.fc` 的稳定错误消息。

    使用示例:
    - _resolve_add_dtype(NumericType.Int32, NumericType.Float32)
    """

    try:
        return (Memory([1], lhs) + Memory([1], rhs)).get_type()
    except TypeError as exc:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.fc 参数校验",
                expected="Unsupported dtype for nn.fc",
                actual=f"lhs={lhs} rhs={rhs}",
                action=ERROR_ACTION,
            )
        ) from exc

def fc(value: Memory, weight: Memory, bias: Memory | None = None) -> Memory:
    """全连接（fully connected）运算。


    功能说明:
    - 支持 Memory 的末维与权重输入特征维线性变换。
    - bias 可选，提供时需与输出特征维对齐。

    使用示例:
    - fc(Memory(["B", "K"], NumericType.Float32), Memory(["N", "K"], NumericType.Float32))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_structured.py
    - 功能实现: kernel_gen/operation/nn/fc.py
    """
    if not isinstance(value, Memory) or not isinstance(weight, Memory):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.fc 参数校验",
                expected="fc operands must be Memory",
                actual=f"value={type(value).__name__} weight={type(weight).__name__}",
                action=ERROR_ACTION,
            )
        )
    if bias is not None and not isinstance(bias, Memory):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.fc 参数校验",
                expected="fc bias must be Memory or None",
                actual=type(bias).__name__,
                action=ERROR_ACTION,
            )
        )
    value_values = value.shape.get_values()
    weight_values = weight.shape.get_values()
    if len(value_values) < 2:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.fc 参数校验",
                expected="fc value rank must be >= 2",
                actual=f"rank={len(value_values)}",
                action=ERROR_ACTION,
            )
        )
    if len(weight_values) != 2:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.fc 参数校验",
                expected="fc weight must be rank-2 Memory",
                actual=f"rank={len(weight_values)}",
                action=ERROR_ACTION,
            )
        )
    if value_values[-1] != weight_values[1]:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.fc 参数校验",
                expected="fc input feature mismatch",
                actual=f"value={value_values[-1]} weight={weight_values[1]}",
                action=ERROR_ACTION,
            )
        )
    if value.space is not weight.space:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.fc 参数校验",
                expected="fc space mismatch",
                actual=f"value={value.space} weight={weight.space}",
                action=ERROR_ACTION,
            )
        )
    if bias is not None:
        bias_values = bias.shape.get_values()
        if len(bias_values) != 1 or bias_values[0] != weight_values[0]:
            raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
                ERROR_TEMPLATE.format(
                    scene="nn.fc 参数校验",
                    expected="fc bias shape mismatch",
                    actual=f"bias={bias_values} weight_out={weight_values[0]}",
                    action=ERROR_ACTION,
                )
            )
        if bias.space is not value.space:
            raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
                ERROR_TEMPLATE.format(
                    scene="nn.fc 参数校验",
                    expected="fc space mismatch",
                    actual=f"bias={bias.space} value={value.space}",
                    action=ERROR_ACTION,
                )
            )
    result_dtype = _resolve_add_dtype(value.dtype, weight.dtype)
    if bias is not None and bias.dtype is not result_dtype:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.fc 参数校验",
                expected="fc bias dtype mismatch",
                actual=f"result={result_dtype} bias={bias.dtype}",
                action=ERROR_ACTION,
            )
        )
    output_shape = [*value_values[:-1], weight_values[0]]
    return Memory(
        output_shape,
        result_dtype,
        space=value.space,
        stride=default_stride(SymbolShape(output_shape)),
        format=Farmat.Norm,
    )

__all__ = ["fc"]
