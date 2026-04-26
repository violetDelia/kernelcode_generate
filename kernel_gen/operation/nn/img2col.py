"""NN operation img2col family.

创建者: 守护最好的爱莉希雅
最后一次更改: 金铲铲大作战

功能说明:
- 提供 img2col1d / img2col2d 运算与共享 shape helper。

使用示例:
- from kernel_gen.operation.nn.img2col import img2col1d, img2col2d

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/test_operation_nn_structured.py
- 功能实现: kernel_gen/operation/nn/img2col.py
"""

from __future__ import annotations

from .common import (
    _ERROR_ACTION,
    _ERROR_TEMPLATE,
    _normalize_symbolic_int_param,
)
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.symbol_shape import SymbolShape
from kernel_gen.symbol_variable.type import Farmat, NumericType

def _normalize_img2col_param(name: str, value: int | SymbolDim, allow_zero: bool) -> SymbolDim:
    """规范化 img2col 参数为 SymbolDim。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅接受 int 或 SymbolDim。
    - 对静态可判定的值校验正数/非负约束。

    使用示例:
    - _normalize_img2col_param("kh", 3, allow_zero=False)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_structured.py
    - 功能实现: kernel_gen/operation/nn/img2col.py
    """
    return _normalize_symbolic_int_param(
        scene="nn.img2col 参数校验",
        owner="img2col",
        name=name,
        value=value,
        allow_zero=allow_zero,
    )

def _img2col_output_dim(
    size: SymbolDim,
    kernel: SymbolDim,
    stride: SymbolDim,
    dilation: SymbolDim,
    pad_low: SymbolDim,
    pad_high: SymbolDim,
) -> SymbolDim:
    """计算 img2col 的输出维度。

    创建者: 小李飞刀
    最后一次更改: jcc你莫辜负

    功能说明:
    - 按 floor((size + pad_low + pad_high - dilation*(kernel-1) - 1) / stride) + 1 计算。

    使用示例:
    - _img2col_output_dim(SymbolDim(5), SymbolDim(3), SymbolDim(1), SymbolDim(1), SymbolDim(1), SymbolDim(1))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_structured.py
    - 功能实现: kernel_gen/operation/nn/img2col.py
    """
    return ((size + pad_low + pad_high - dilation * (kernel - 1) - 1) // stride) + 1

def img2col1d(
    value: object,
    kw: int | SymbolDim,
    sw: int | SymbolDim = 1,
    dw: int | SymbolDim = 1,
    pl: int | SymbolDim = 0,
    pr: int | SymbolDim = 0,
) -> Memory:
    """一维窗口展开高层语义推导。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 校验输入类型与 rank。
    - 校验 kernel/stride/dilation/padding 参数。
    - 返回 img2col1d 展开后的 Memory 描述。

    使用示例:
    - img2col1d(Memory([1, 16, 32], NumericType.Float32), kw=3, sw=1, dw=1, pl=1, pr=1)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_structured.py
    - 功能实现: kernel_gen/operation/nn/img2col.py
    """
    if not isinstance(value, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.img2col1d 参数校验",
                expected="img2col1d value must be Memory",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if len(value.shape) != 3:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.img2col1d 参数校验",
                expected="img2col1d value must be rank-3 Memory",
                actual=f"rank={len(value.shape)}",
                action=_ERROR_ACTION,
            )
        )

    kw_dim = _normalize_img2col_param("kw", kw, allow_zero=False)
    sw_dim = _normalize_img2col_param("sw", sw, allow_zero=False)
    dw_dim = _normalize_img2col_param("dw", dw, allow_zero=False)
    pl_dim = _normalize_img2col_param("pl", pl, allow_zero=True)
    pr_dim = _normalize_img2col_param("pr", pr, allow_zero=True)

    if value.format is Farmat.Norm:
        n_dim, c_dim, w_dim = value.shape.get_shape()
    elif value.format is Farmat.CLast:
        n_dim, w_dim, c_dim = value.shape.get_shape()
    else:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.img2col1d 参数校验",
                expected="img2col1d value format must be Norm or CLast",
                actual=str(value.format),
                action=_ERROR_ACTION,
            )
        )
    w_out = _img2col_output_dim(w_dim, kw_dim, sw_dim, dw_dim, pl_dim, pr_dim)

    w_out_value = w_out.get_value()
    if isinstance(w_out_value, int) and w_out_value <= 0:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.img2col1d 参数校验",
                expected="img2col1d output width must be positive",
                actual=str(w_out_value),
                action=_ERROR_ACTION,
            )
        )

    if value.format is Farmat.Norm:
        out_shape = SymbolShape([n_dim, c_dim, kw_dim, w_out])
    else:
        out_shape = SymbolShape([n_dim, w_out, kw_dim, c_dim])
    return Memory(
        out_shape,
        value.dtype,
        space=value.space,
        format=Farmat.Norm,
    )

def img2col2d(
    value: object,
    kh: int | SymbolDim,
    kw: int | SymbolDim,
    sh: int | SymbolDim = 1,
    sw: int | SymbolDim = 1,
    dh: int | SymbolDim = 1,
    dw: int | SymbolDim = 1,
    ph: int | SymbolDim = 0,
    pw: int | SymbolDim = 0,
    pl: int | SymbolDim = 0,
    pr: int | SymbolDim = 0,
) -> Memory:
    """二维窗口展开高层语义推导。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 校验输入类型与 rank。
    - 校验 kernel/stride/dilation/padding 参数。
    - 返回 img2col2d 展开后的 Memory 描述。

    使用示例:
    - img2col2d(Memory([1, 3, 5, 5], NumericType.Float32), kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=1, pw=1, pl=1, pr=1)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_structured.py
    - 功能实现: kernel_gen/operation/nn/img2col.py
    """
    return _img2col(value, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr)

def _img2col(
    value: object,
    kh: int | SymbolDim,
    kw: int | SymbolDim,
    sh: int | SymbolDim,
    sw: int | SymbolDim,
    dh: int | SymbolDim,
    dw: int | SymbolDim,
    ph: int | SymbolDim,
    pw: int | SymbolDim,
    pl: int | SymbolDim,
    pr: int | SymbolDim,
) -> Memory:
    """img2col2d 的内部展开实现。

    创建者: 小李飞刀
    最后一次更改: jcc你莫辜负

    功能说明:
    - 供 img2col2d 复用的内部实现。
    - 校验输入类型与 rank、kernel/stride/dilation/padding 参数。
    - 返回展开后的 Memory 描述。

    使用示例:
    - _img2col(Memory([1, 3, 5, 5], NumericType.Float32), 3, 3, 1, 1, 1, 1, 1, 1, 1, 1)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_structured.py
    - 功能实现: kernel_gen/operation/nn/img2col.py
    """
    if not isinstance(value, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.img2col 参数校验",
                expected="img2col value must be Memory",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if len(value.shape) != 4:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.img2col 参数校验",
                expected="img2col value must be rank-4 Memory",
                actual=f"rank={len(value.shape)}",
                action=_ERROR_ACTION,
            )
        )

    kh_dim = _normalize_img2col_param("kh", kh, allow_zero=False)
    kw_dim = _normalize_img2col_param("kw", kw, allow_zero=False)
    sh_dim = _normalize_img2col_param("sh", sh, allow_zero=False)
    sw_dim = _normalize_img2col_param("sw", sw, allow_zero=False)
    dh_dim = _normalize_img2col_param("dh", dh, allow_zero=False)
    dw_dim = _normalize_img2col_param("dw", dw, allow_zero=False)
    ph_dim = _normalize_img2col_param("ph", ph, allow_zero=True)
    pw_dim = _normalize_img2col_param("pw", pw, allow_zero=True)
    pl_dim = _normalize_img2col_param("pl", pl, allow_zero=True)
    pr_dim = _normalize_img2col_param("pr", pr, allow_zero=True)

    if value.format is Farmat.Norm:
        n_dim, c_dim, h_dim, w_dim = value.shape.get_shape()
    elif value.format is Farmat.CLast:
        n_dim, h_dim, w_dim, c_dim = value.shape.get_shape()
    else:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.img2col 参数校验",
                expected="img2col value format must be Norm or CLast",
                actual=str(value.format),
                action=_ERROR_ACTION,
            )
        )
    h_out = _img2col_output_dim(h_dim, kh_dim, sh_dim, dh_dim, ph_dim, pw_dim)
    w_out = _img2col_output_dim(w_dim, kw_dim, sw_dim, dw_dim, pl_dim, pr_dim)

    h_out_value = h_out.get_value()
    if isinstance(h_out_value, int) and h_out_value <= 0:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.img2col 参数校验",
                expected="img2col output height must be positive",
                actual=str(h_out_value),
                action=_ERROR_ACTION,
            )
        )
    w_out_value = w_out.get_value()
    if isinstance(w_out_value, int) and w_out_value <= 0:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.img2col 参数校验",
                expected="img2col output width must be positive",
                actual=str(w_out_value),
                action=_ERROR_ACTION,
            )
        )

    if value.format is Farmat.Norm:
        out_shape = SymbolShape([n_dim, c_dim, kh_dim, kw_dim, h_out, w_out])
    else:
        out_shape = SymbolShape([n_dim, h_out, w_out, kh_dim, kw_dim, c_dim])
    return Memory(
        out_shape,
        value.dtype,
        space=value.space,
        format=Farmat.Norm,
    )

__all__ = [
    "_normalize_img2col_param",
    "_img2col_output_dim",
    "img2col1d",
    "img2col2d",
    "_img2col",
]
