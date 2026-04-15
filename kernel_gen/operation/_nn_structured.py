"""NN operation structured family.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 提供 softmax/fc/matmul/conv/img2col/transpose family 实现

使用示例:
- from kernel_gen.operation.nn import add, broadcast, reduce_sum

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/test_operation_nn.py
- 功能实现: kernel_gen/operation/_nn_structured.py
"""

from __future__ import annotations

from ._nn_common import *


def softmax(value: object, axis: int = -1) -> Memory:
    """沿指定轴执行 softmax 归一化。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅接受 Memory 输入，并校验 dtype 与 axis。
    - 数值稳定语义约束为 exp(x - max(x)) / sum(exp(x - max(x)))。
    - 输出 shape/dtype/space/format/stride 与输入保持一致。

    使用示例:
    - softmax(Memory(["M", "N"], NumericType.Float32))
    - softmax(Memory(["B", "C", "H", "W"], NumericType.Float32), axis=1)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/_nn_structured.py
    """
    if not isinstance(value, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.softmax 参数校验",
                expected="softmax value must be Memory",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if value.dtype not in (
        NumericType.Float16,
        NumericType.BFloat16,
        NumericType.Float32,
        NumericType.Float64,
    ):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.softmax 参数校验",
                expected="softmax value dtype must be float",
                actual=str(value.dtype),
                action=_ERROR_ACTION,
            )
        )
    if isinstance(axis, bool) or not isinstance(axis, int):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.softmax 参数校验",
                expected="softmax axis must be int",
                actual=type(axis).__name__,
                action=_ERROR_ACTION,
            )
        )
    rank = len(value.shape)
    if axis < -rank or axis >= rank:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.softmax 参数校验",
                expected="softmax axis out of range",
                actual=f"axis={axis} rank={rank}",
                action=_ERROR_ACTION,
            )
        )
    _ = axis + rank if axis < 0 else axis
    return value._clone_with_dtype(value.dtype)


def fc(value: object, weight: object, bias: object | None = None) -> Memory:
    """全连接（fully connected）运算。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 Memory 的末维与权重输入特征维线性变换。
    - bias 可选，提供时需与输出特征维对齐。

    使用示例:
    - fc(Memory(["B", "K"], NumericType.Float32), Memory(["N", "K"], NumericType.Float32))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/_nn_structured.py
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
    if bias is not None and _resolve_add_dtype(result_dtype, bias.dtype) is not result_dtype:
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


def matmul(lhs: object, rhs: object, memoryspace: MemorySpace | None = None) -> Memory:
    """二维矩阵乘。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅接受二维 Memory x Memory。
    - 校验 contracting dim 与 space 一致性。
    - dtype 按固定优先级决议。

    使用示例:
    - matmul(Memory(["M", "K"], NumericType.Float32), Memory(["K", "N"], NumericType.Float32))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/_nn_structured.py
    """
    if not isinstance(lhs, Memory) or not isinstance(rhs, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.matmul 参数校验",
                expected="matmul operands must be Memory",
                actual=f"lhs={type(lhs).__name__} rhs={type(rhs).__name__}",
                action=_ERROR_ACTION,
            )
        )
    lhs_values = lhs.shape.get_values()
    rhs_values = rhs.shape.get_values()
    if len(lhs_values) != 2 or len(rhs_values) != 2:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.matmul 参数校验",
                expected="matmul operands must be rank-2 Memory",
                actual=f"lhs_rank={len(lhs_values)} rhs_rank={len(rhs_values)}",
                action=_ERROR_ACTION,
            )
        )
    if lhs_values[1] != rhs_values[0]:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.matmul 参数校验",
                expected="matmul contracting dimension mismatch",
                actual=f"lhs_k={lhs_values[1]} rhs_k={rhs_values[0]}",
                action=_ERROR_ACTION,
            )
        )
    if lhs.space is not rhs.space:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.matmul 参数校验",
                expected="matmul space mismatch",
                actual=f"lhs={lhs.space} rhs={rhs.space}",
                action=_ERROR_ACTION,
            )
        )
    result_dtype = _resolve_add_dtype(lhs.dtype, rhs.dtype)
    result_space = lhs.space if memoryspace is None else memoryspace
    return Memory(
        [lhs_values[0], rhs_values[1]],
        result_dtype,
        space=result_space,
        stride=_build_add_stride(SymbolShape([lhs_values[0], rhs_values[1]])),
        format=Farmat.Norm,
    )


def _normalize_img2col_param(name: str, value: int | SymbolDim, allow_zero: bool) -> SymbolDim:
    """规范化 img2col 参数为 SymbolDim。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅接受 int 或 SymbolDim。
    - 对静态可判定的值校验正数/非负约束。

    使用示例:
    - _normalize_img2col_param("kh", 3, allow_zero=False)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/_nn_structured.py
    """
    if isinstance(value, bool):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.img2col 参数校验",
                expected=f"img2col {name} must be int or SymbolDim",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if isinstance(value, int):
        if allow_zero and value < 0:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene="nn.img2col 参数校验",
                    expected=f"img2col {name} must be >= 0",
                    actual=str(value),
                    action=_ERROR_ACTION,
                )
            )
        if not allow_zero and value <= 0:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene="nn.img2col 参数校验",
                    expected=f"img2col {name} must be > 0",
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
                        scene="nn.img2col 参数校验",
                        expected=f"img2col {name} must be integer",
                        actual=str(resolved),
                        action=_ERROR_ACTION,
                    )
                )
            if allow_zero and resolved < 0:
                raise ValueError(
                    _ERROR_TEMPLATE.format(
                        scene="nn.img2col 参数校验",
                        expected=f"img2col {name} must be >= 0",
                        actual=str(resolved),
                        action=_ERROR_ACTION,
                    )
                )
            if not allow_zero and resolved <= 0:
                raise ValueError(
                    _ERROR_TEMPLATE.format(
                        scene="nn.img2col 参数校验",
                        expected=f"img2col {name} must be > 0",
                        actual=str(resolved),
                        action=_ERROR_ACTION,
                    )
                )
        return value
    raise TypeError(
        _ERROR_TEMPLATE.format(
            scene="nn.img2col 参数校验",
            expected=f"img2col {name} must be int or SymbolDim",
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
    """计算 img2col 的输出维度。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 按 floor((size + pad_low + pad_high - dilation*(kernel-1) - 1) / stride) + 1 计算。

    使用示例:
    - _img2col_output_dim(SymbolDim(5), SymbolDim(3), SymbolDim(1), SymbolDim(1), SymbolDim(1), SymbolDim(1))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/_nn_structured.py
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
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/_nn_structured.py
    """
    if isinstance(value, bool):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.conv 参数校验",
                expected=f"conv {name} must be int or SymbolDim",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if isinstance(value, int):
        if allow_zero and value < 0:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene="nn.conv 参数校验",
                    expected=f"conv {name} must be >= 0",
                    actual=str(value),
                    action=_ERROR_ACTION,
                )
            )
        if not allow_zero and value <= 0:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene="nn.conv 参数校验",
                    expected=f"conv {name} must be > 0",
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
                        scene="nn.conv 参数校验",
                        expected=f"conv {name} must be integer",
                        actual=str(resolved),
                        action=_ERROR_ACTION,
                    )
                )
            if allow_zero and resolved < 0:
                raise ValueError(
                    _ERROR_TEMPLATE.format(
                        scene="nn.conv 参数校验",
                        expected=f"conv {name} must be >= 0",
                        actual=str(resolved),
                        action=_ERROR_ACTION,
                    )
                )
            if not allow_zero and resolved <= 0:
                raise ValueError(
                    _ERROR_TEMPLATE.format(
                        scene="nn.conv 参数校验",
                        expected=f"conv {name} must be > 0",
                        actual=str(resolved),
                        action=_ERROR_ACTION,
                    )
                )
        return value
    raise TypeError(
        _ERROR_TEMPLATE.format(
            scene="nn.conv 参数校验",
            expected=f"conv {name} must be int or SymbolDim",
            actual=type(value).__name__,
            action=_ERROR_ACTION,
        )
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
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验输入类型、rank、空间与 dtype 一致性。
    - 支持可选 bias 对齐 C_out。
    - 按公式推导输出高宽并保持 Memory 元信息约束。

    使用示例:
    - conv(Memory([1, 3, 32, 32], NumericType.Float32), Memory([8, 3, 3, 3], NumericType.Float32))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/_nn_structured.py
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
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验输入类型与 rank。
    - 校验 kernel/stride/dilation/padding 参数。
    - 返回 img2col1d 展开后的 Memory 描述。

    使用示例:
    - img2col1d(Memory([1, 16, 32], NumericType.Float32), kw=3, sw=1, dw=1, pl=1, pr=1)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/_nn_structured.py
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
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验输入类型与 rank。
    - 校验 kernel/stride/dilation/padding 参数。
    - 返回 img2col2d 展开后的 Memory 描述。

    使用示例:
    - img2col2d(Memory([1, 3, 5, 5], NumericType.Float32), kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=1, pw=1, pl=1, pr=1)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/_nn_structured.py
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
    最后一次更改: 金铲铲大作战

    功能说明:
    - 供 img2col2d 复用的内部实现。
    - 校验输入类型与 rank、kernel/stride/dilation/padding 参数。
    - 返回展开后的 Memory 描述。

    使用示例:
    - _img2col(Memory([1, 3, 5, 5], NumericType.Float32), 3, 3, 1, 1, 1, 1, 1, 1, 1, 1)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/_nn_structured.py
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


def _normalize_transpose_perm(perm: object, rank: int) -> list[int]:
    """规范化 transpose 的 perm 参数。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 要求 perm 为非字符串序列，且元素必须是 int 但不能是 bool。
    - 要求 perm 长度与输入 rank 一致，并且是 `0..rank-1` 的排列。

    使用示例:
    - _normalize_transpose_perm([1, 0], rank=2)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/_nn_structured.py
    """
    if isinstance(perm, (str, bytes)) or not isinstance(perm, Sequence):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.transpose 参数校验",
                expected="transpose perm must be a sequence of int",
                actual=type(perm).__name__,
                action=_ERROR_ACTION,
            )
        )

    normalized_perm = list(perm)
    if len(normalized_perm) != rank:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.transpose 参数校验",
                expected="transpose perm length must equal input rank",
                actual=f"perm_len={len(normalized_perm)} rank={rank}",
                action=_ERROR_ACTION,
            )
        )

    for index, axis in enumerate(normalized_perm):
        if isinstance(axis, bool) or not isinstance(axis, int):
            raise TypeError(
                _ERROR_TEMPLATE.format(
                    scene="nn.transpose 参数校验",
                    expected="transpose perm element must be int",
                    actual=f"index={index} type={type(axis).__name__}",
                    action=_ERROR_ACTION,
                )
            )

    if sorted(normalized_perm) != list(range(rank)):
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.transpose 参数校验",
                expected="transpose perm must be a permutation of input axes",
                actual=f"perm={normalized_perm} rank={rank}",
                action=_ERROR_ACTION,
            )
        )

    return normalized_perm


def transpose(value: object, perm: object) -> Memory:
    """按指定 perm 重排 Memory 的轴顺序。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅接受 Memory 输入，输出保留输入的 dtype/space/format。
    - 按 perm 同步重排 shape 与 stride。
    - 对非法 perm 长度、元素类型或非排列情形直接报错。

    使用示例:
    - transpose(Memory([2, 3], NumericType.Float32), perm=[1, 0])

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/_nn_structured.py
    """
    if not isinstance(value, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.transpose 参数校验",
                expected="transpose value must be Memory",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )

    perm_values = _normalize_transpose_perm(perm, rank=len(value.shape))
    shape_dims = value.shape.get_shape()
    stride_dims = value.stride.get_shape()
    transposed_shape = SymbolShape([shape_dims[index] for index in perm_values])
    transposed_stride = SymbolShape([stride_dims[index] for index in perm_values])
    return Memory(
        transposed_shape,
        value.dtype,
        space=value.space,
        stride=transposed_stride,
        format=value.format,
    )

__all__ = [
    "softmax",
    "fc",
    "matmul",
    "_normalize_img2col_param",
    "_img2col_output_dim",
    "_normalize_conv_param",
    "conv",
    "img2col1d",
    "img2col2d",
    "_img2col",
    "_normalize_transpose_perm",
    "transpose",
]
