"""NN operation conv helper.

创建者: 守护最好的爱莉希雅
最后一次更改: 金铲铲大作战

功能说明:
- 提供二维卷积运算与参数规范化 helper。

API 列表:
- `conv(value: object, weight: object, bias: object | None = None, sh: int | SymbolDim = 1, sw: int | SymbolDim = 1, dh: int | SymbolDim = 1, dw: int | SymbolDim = 1, ph: int | SymbolDim = 0, pw: int | SymbolDim = 0, pl: int | SymbolDim = 0, pr: int | SymbolDim = 0) -> Memory`

使用示例:
- from kernel_gen.operation.nn.conv import conv

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/test_operation_nn_structured.py
- 功能实现: kernel_gen/operation/nn/conv.py
"""

from __future__ import annotations

from kernel_gen.common.errors import _ERROR_TEMPLATE
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.symbol_shape import SymbolShape
from kernel_gen.symbol_variable.type import Farmat, NumericType

_ERROR_ACTION = "请按接口约束传参"


def _normalize_symbolic_int_param(
    scene: str,
    owner: str,
    name: str,
    value: int | SymbolDim,
    allow_zero: bool,
) -> SymbolDim:
    """规范化 conv 内部整型/符号参数。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅接受 `int | SymbolDim`，拒绝 `bool` 和其他类型。
    - 对静态可判定值执行 `> 0` 或 `>= 0` 约束。

    使用示例:
    - _normalize_symbolic_int_param("nn.conv 参数校验", "conv", "sh", 1, allow_zero=False)
    """
    expected_type = f"{owner} {name} must be int or SymbolDim"
    expected_non_negative = f"{owner} {name} must be >= 0"
    expected_positive = f"{owner} {name} must be > 0"
    expected_integer = f"{owner} {name} must be integer"
    if isinstance(value, bool):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene=scene,
                expected=expected_type,
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if isinstance(value, int):
        if allow_zero and value < 0:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene=scene,
                    expected=expected_non_negative,
                    actual=str(value),
                    action=_ERROR_ACTION,
                )
            )
        if not allow_zero and value <= 0:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene=scene,
                    expected=expected_positive,
                    actual=str(value),
                    action=_ERROR_ACTION,
                )
            )
        return SymbolDim(value)
    if isinstance(value, SymbolDim):
        if not value.is_dynamic():
            resolved = value.get_value()
            if not isinstance(resolved, int):
                raise ValueError(
                    _ERROR_TEMPLATE.format(
                        scene=scene,
                        expected=expected_integer,
                        actual=str(resolved),
                        action=_ERROR_ACTION,
                    )
                )
            if allow_zero and resolved < 0:
                raise ValueError(
                    _ERROR_TEMPLATE.format(
                        scene=scene,
                        expected=expected_non_negative,
                        actual=str(resolved),
                        action=_ERROR_ACTION,
                    )
                )
            if not allow_zero and resolved <= 0:
                raise ValueError(
                    _ERROR_TEMPLATE.format(
                        scene=scene,
                        expected=expected_positive,
                        actual=str(resolved),
                        action=_ERROR_ACTION,
                    )
                )
        return value
    raise TypeError(
        _ERROR_TEMPLATE.format(
            scene=scene,
            expected=expected_type,
            actual=type(value).__name__,
            action=_ERROR_ACTION,
        )
    )


def _img2col_output_dim(
    size: SymbolDim,
    kernel: SymbolDim,
    stride: SymbolDim,
    dilation: SymbolDim,
    pad_low: SymbolDim,
    pad_high: SymbolDim,
) -> SymbolDim:
    """计算 conv 使用的单轴输出维度。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 保持 `((size + pad_low + pad_high - dilation * (kernel - 1) - 1) // stride) + 1` 的公开公式。

    使用示例:
    - _img2col_output_dim(SymbolDim(5), SymbolDim(3), SymbolDim(1), SymbolDim(1), SymbolDim(1), SymbolDim(1))
    """
    return ((size + pad_low + pad_high - dilation * (kernel - 1) - 1) // stride) + 1

def _normalize_conv_param(name: str, value: int | SymbolDim, allow_zero: bool) -> SymbolDim:
    """规范化 conv 参数为 SymbolDim。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅接受 int 或 SymbolDim。
    - 对静态可判定的值校验正数/非负约束。

    使用示例:
    - _normalize_conv_param("sh", 1, allow_zero=False)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_structured.py
    - 功能实现: kernel_gen/operation/nn/conv.py
    """
    return _normalize_symbolic_int_param(
        scene="nn.conv 参数校验",
        owner="conv",
        name=name,
        value=value,
        allow_zero=allow_zero,
    )

def conv(
    value: object,
    weight: object,
    bias: object | None = None,
    sh: int | SymbolDim = 1,
    sw: int | SymbolDim = 1,
    dh: int | SymbolDim = 1,
    dw: int | SymbolDim = 1,
    ph: int | SymbolDim = 0,
    pw: int | SymbolDim = 0,
    pl: int | SymbolDim = 0,
    pr: int | SymbolDim = 0,
) -> Memory:
    """二维卷积（NCHW）语义推导。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 校验输入类型、rank、空间与 dtype 一致性。
    - 支持可选 bias 对齐 C_out。
    - 按公式推导输出高宽并保持 Memory 元信息约束。

    使用示例:
    - conv(Memory([1, 3, 32, 32], NumericType.Float32), Memory([8, 3, 3, 3], NumericType.Float32))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_structured.py
    - 功能实现: kernel_gen/operation/nn/conv.py
    """
    if not isinstance(value, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.conv 参数校验",
                expected="conv value must be Memory",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if not isinstance(weight, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.conv 参数校验",
                expected="conv weight must be Memory",
                actual=type(weight).__name__,
                action=_ERROR_ACTION,
            )
        )
    if len(value.shape) != 4:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.conv 参数校验",
                expected="conv value must be rank-4 Memory",
                actual=f"rank={len(value.shape)}",
                action=_ERROR_ACTION,
            )
        )
    if len(weight.shape) != 4:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.conv 参数校验",
                expected="conv weight must be rank-4 Memory",
                actual=f"rank={len(weight.shape)}",
                action=_ERROR_ACTION,
            )
        )

    n_dim, c_in_dim, h_dim, w_dim = value.shape.get_shape()
    c_out_dim, c_in_weight_dim, kh_dim, kw_dim = weight.shape.get_shape()
    if c_in_dim != c_in_weight_dim:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.conv 参数校验",
                expected="conv input channel mismatch",
                actual=f"value={c_in_dim} weight={c_in_weight_dim}",
                action=_ERROR_ACTION,
            )
        )
    if value.dtype is not weight.dtype:
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.conv 参数校验",
                expected="conv dtype mismatch",
                actual=f"value={value.dtype} weight={weight.dtype}",
                action=_ERROR_ACTION,
            )
        )
    if value.space is not weight.space:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.conv 参数校验",
                expected="conv space mismatch",
                actual=f"value={value.space} weight={weight.space}",
                action=_ERROR_ACTION,
            )
        )

    if bias is not None:
        if not isinstance(bias, Memory):
            raise TypeError(
                _ERROR_TEMPLATE.format(
                    scene="nn.conv 参数校验",
                    expected="conv bias must be Memory",
                    actual=type(bias).__name__,
                    action=_ERROR_ACTION,
                )
            )
        if len(bias.shape) != 1:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene="nn.conv 参数校验",
                    expected="conv bias must be rank-1 Memory",
                    actual=f"rank={len(bias.shape)}",
                    action=_ERROR_ACTION,
                )
            )
        bias_dim = bias.shape.get_shape()[0]
        if bias_dim != c_out_dim:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene="nn.conv 参数校验",
                    expected="conv bias shape mismatch",
                    actual=f"bias={bias_dim} out={c_out_dim}",
                    action=_ERROR_ACTION,
                )
            )
        if bias.dtype is not value.dtype:
            raise TypeError(
                _ERROR_TEMPLATE.format(
                    scene="nn.conv 参数校验",
                    expected="conv bias dtype mismatch",
                    actual=f"bias={bias.dtype} value={value.dtype}",
                    action=_ERROR_ACTION,
                )
            )
        if bias.space is not value.space:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene="nn.conv 参数校验",
                    expected="conv bias space mismatch",
                    actual=f"bias={bias.space} value={value.space}",
                    action=_ERROR_ACTION,
                )
            )

    sh_dim = _normalize_conv_param("sh", sh, allow_zero=False)
    sw_dim = _normalize_conv_param("sw", sw, allow_zero=False)
    dh_dim = _normalize_conv_param("dh", dh, allow_zero=False)
    dw_dim = _normalize_conv_param("dw", dw, allow_zero=False)
    ph_dim = _normalize_conv_param("ph", ph, allow_zero=True)
    pw_dim = _normalize_conv_param("pw", pw, allow_zero=True)
    pl_dim = _normalize_conv_param("pl", pl, allow_zero=True)
    pr_dim = _normalize_conv_param("pr", pr, allow_zero=True)

    h_out = _img2col_output_dim(h_dim, kh_dim, sh_dim, dh_dim, ph_dim, pw_dim)
    w_out = _img2col_output_dim(w_dim, kw_dim, sw_dim, dw_dim, pl_dim, pr_dim)

    h_out_value = h_out.get_value()
    if isinstance(h_out_value, int) and h_out_value <= 0:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.conv 参数校验",
                expected="conv output height must be positive",
                actual=str(h_out_value),
                action=_ERROR_ACTION,
            )
        )
    w_out_value = w_out.get_value()
    if isinstance(w_out_value, int) and w_out_value <= 0:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.conv 参数校验",
                expected="conv output width must be positive",
                actual=str(w_out_value),
                action=_ERROR_ACTION,
            )
        )

    return Memory(
        SymbolShape([n_dim, c_out_dim, h_out, w_out]),
        value.dtype,
        space=value.space,
        format=Farmat.Norm,
    )

__all__ = [
    "conv",
]
