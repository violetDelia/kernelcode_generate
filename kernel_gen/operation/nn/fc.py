"""NN operation fc helper.

创建者: 守护最好的爱莉希雅
最后一次更改: 金铲铲大作战

功能说明:
- 提供全连接运算。

使用示例:
- from kernel_gen.operation.nn.fc import fc

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/test_operation_nn_structured.py
- 功能实现: kernel_gen/operation/nn/fc.py
"""

from __future__ import annotations

from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_shape import SymbolShape
from kernel_gen.symbol_variable.type import Farmat, NumericType
from .common import _ERROR_ACTION, _ERROR_TEMPLATE, _build_add_stride, _resolve_add_dtype

def fc(value: object, weight: object, bias: object | None = None) -> Memory:
    """全连接（fully connected）运算。

    创建者: 小李飞刀
    最后一次更改: jcc你莫辜负

    功能说明:
    - 支持 Memory 的末维与权重输入特征维线性变换。
    - bias 可选，提供时需与输出特征维对齐。

    使用示例:
    - fc(Memory(["B", "K"], NumericType.Float32), Memory(["N", "K"], NumericType.Float32))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_structured.py
    - 功能实现: kernel_gen/operation/nn/fc.py
    """
    if not isinstance(value, Memory) or not isinstance(weight, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.fc 参数校验",
                expected="fc operands must be Memory",
                actual=f"value={type(value).__name__} weight={type(weight).__name__}",
                action=_ERROR_ACTION,
            )
        )
    if bias is not None and not isinstance(bias, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.fc 参数校验",
                expected="fc bias must be Memory or None",
                actual=type(bias).__name__,
                action=_ERROR_ACTION,
            )
        )
    value_values = value.shape.get_values()
    weight_values = weight.shape.get_values()
    if len(value_values) < 2:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.fc 参数校验",
                expected="fc value rank must be >= 2",
                actual=f"rank={len(value_values)}",
                action=_ERROR_ACTION,
            )
        )
    if len(weight_values) != 2:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.fc 参数校验",
                expected="fc weight must be rank-2 Memory",
                actual=f"rank={len(weight_values)}",
                action=_ERROR_ACTION,
            )
        )
    if value_values[-1] != weight_values[1]:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.fc 参数校验",
                expected="fc input feature mismatch",
                actual=f"value={value_values[-1]} weight={weight_values[1]}",
                action=_ERROR_ACTION,
            )
        )
    if value.space is not weight.space:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.fc 参数校验",
                expected="fc space mismatch",
                actual=f"value={value.space} weight={weight.space}",
                action=_ERROR_ACTION,
            )
        )
    if bias is not None:
        bias_values = bias.shape.get_values()
        if len(bias_values) != 1 or bias_values[0] != weight_values[0]:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene="nn.fc 参数校验",
                    expected="fc bias shape mismatch",
                    actual=f"bias={bias_values} weight_out={weight_values[0]}",
                    action=_ERROR_ACTION,
                )
            )
        if bias.space is not value.space:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene="nn.fc 参数校验",
                    expected="fc space mismatch",
                    actual=f"bias={bias.space} value={value.space}",
                    action=_ERROR_ACTION,
                )
            )
    result_dtype = _resolve_add_dtype(value.dtype, weight.dtype)
    if bias is not None and bias.dtype is not result_dtype:
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.fc 参数校验",
                expected="fc bias dtype mismatch",
                actual=f"result={result_dtype} bias={bias.dtype}",
                action=_ERROR_ACTION,
            )
        )
    output_shape = [*value_values[:-1], weight_values[0]]
    return Memory(
        output_shape,
        result_dtype,
        space=value.space,
        stride=_build_add_stride(SymbolShape(output_shape)),
        format=Farmat.Norm,
    )

__all__ = ["fc"]
