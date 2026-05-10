"""Kernel operation structured helpers.


功能说明:
- 提供 `kernel` operation family 的 out-first matmul/img2col helper。
- helper 只校验公开 `Memory` 元信息并返回 `None`。

API 列表:
- `matmul(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `img2col1d(out: Memory, input_value: Memory, k: int | SymbolDim, s: int | SymbolDim = 1, d: int | SymbolDim = 1, p_left: int | SymbolDim = 0, p_right: int | SymbolDim = 0) -> None`
- `img2col2d(out: Memory, input_value: Memory, kh: int | SymbolDim, kw: int | SymbolDim, sh: int | SymbolDim = 1, sw: int | SymbolDim = 1, dh: int | SymbolDim = 1, dw: int | SymbolDim = 1, ph: int | SymbolDim = 0, pw: int | SymbolDim = 0, pl: int | SymbolDim = 0, pr: int | SymbolDim = 0) -> None`

使用示例:
- from kernel_gen.operation import kernel
- kernel.matmul(out, lhs, rhs)

关联文件:
- spec: spec/operation/kernel.md
- test: test/operation/kernel/test_structured.py
- 功能实现: kernel_gen/operation/kernel/structured.py
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
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import Farmat

_ERROR_SCENE = "kernel operation 参数校验"


def _raise_contract(expected: str, actual: str) -> None:
    """抛出 kernel structured 合同错误。

    功能说明:
    - 当前文件内统一错误构造。

    使用示例:
    - _raise_contract("kernel.matmul operands must be Memory", "lhs=int")
    """

    raise kernel_code_error(
        ErrorKind.CONTRACT,
        ErrorModule.OPERATION,
        ERROR_TEMPLATE.format(
            scene=_ERROR_SCENE,
            expected=expected,
            actual=actual,
            action=ERROR_ACTION,
        ),
    )


def _ensure_memory(value: Memory, name: str) -> None:
    """校验参数为 Memory。

    功能说明:
    - structured kernel helper 当前只接受 `Memory` operand。

    使用示例:
    - _ensure_memory(out, "out")
    """

    if not isinstance(value, Memory):
        _raise_contract(f"kernel.{name} operand must be Memory", f"{name}={type(value).__name__}")


def _same_dim(lhs: SymbolDim, rhs: SymbolDim) -> bool:
    """比较 SymbolDim 公开等价。

    功能说明:
    - 复用 `SymbolDim.__eq__` 公开比较语义。

    使用示例:
    - _same_dim(SymbolDim("K"), SymbolDim("K"))
    """

    return lhs == rhs


def _same_symbol_list(lhs: list[int | SymbolDim], rhs: list[int | SymbolDim]) -> bool:
    """比较 shape/stride 列表。

    功能说明:
    - 支持 `Memory.get_shape()` 返回的 SymbolDim 列表和 `get_stride()` 的 int/SymbolDim 列表。

    使用示例:
    - _same_symbol_list(out.get_stride(), expected.get_stride())
    """

    if len(lhs) != len(rhs):
        return False
    for lhs_dim, rhs_dim in zip(lhs, rhs, strict=True):
        if lhs_dim != rhs_dim:
            return False
    return True


def _dim(value: int | SymbolDim) -> SymbolDim:
    """把公开窗口参数规整为 SymbolDim。

    功能说明:
    - `bool` 不属于 kernel structured 参数合法输入。

    使用示例:
    - _dim(3)
    """

    if isinstance(value, bool):
        _raise_contract("kernel parameter must be int or SymbolDim", f"value={type(value).__name__}")
    if isinstance(value, int):
        return SymbolDim(value)
    if isinstance(value, SymbolDim):
        return value
    _raise_contract("kernel parameter must be int or SymbolDim", f"value={type(value).__name__}")


def _normalize_param(name: str, value: int | SymbolDim, *, allow_zero: bool) -> SymbolDim:
    """校验并规整 img2col 参数。

    功能说明:
    - `k/s/d/kh/kw/sh/sw/dh/dw` 必须为正。
    - padding 参数必须非负。

    使用示例:
    - _normalize_param("kw", 3, allow_zero=False)
    """

    dim = _dim(value)
    public_value = dim.get_value()
    if isinstance(public_value, int):
        if allow_zero and public_value < 0:
            _raise_contract(f"kernel.img2col {name} must be >= 0", str(public_value))
        if not allow_zero and public_value <= 0:
            _raise_contract(f"kernel.img2col {name} must be > 0", str(public_value))
    return dim


def _out_dim(
    size_value: SymbolDim,
    kernel_value: SymbolDim,
    stride_value: SymbolDim,
    dilation_value: SymbolDim,
    pad_low: SymbolDim,
    pad_high: SymbolDim,
) -> SymbolDim:
    """计算 img2col 输出维度。

    功能说明:
    - 按 floor((size + pad_low + pad_high - dilation*(kernel-1) - 1) / stride) + 1 计算。

    使用示例:
    - _out_dim(SymbolDim(32), SymbolDim(3), SymbolDim(1), SymbolDim(1), SymbolDim(1), SymbolDim(1))
    """

    return ((size_value + pad_low + pad_high - dilation_value * (kernel_value - 1) - 1) // stride_value) + 1


def _ensure_expected_memory(actual: Memory, expected: Memory, context: str) -> None:
    """校验 actual Memory 与 expected 元信息一致。

    功能说明:
    - 比较 shape、stride、dtype、space 与 format。

    使用示例:
    - _ensure_expected_memory(out, expected, "kernel.img2col2d")
    """

    if not _same_symbol_list(actual.get_shape(), expected.get_shape()):
        _raise_contract(f"{context} out shape must match contract", "shape mismatch")
    if not _same_symbol_list(actual.get_stride(), expected.get_stride()):
        _raise_contract(f"{context} out stride must match contract", "stride mismatch")
    if actual.get_type() is not expected.get_type():
        _raise_contract(f"{context} out dtype must match contract", "dtype mismatch")
    if actual.get_space() is not expected.get_space():
        _raise_contract(f"{context} out space must match contract", "space mismatch")
    if actual.get_format() is not expected.get_format():
        _raise_contract(f"{context} out format must match contract", "format mismatch")


def matmul(out: Memory, lhs: Memory, rhs: Memory) -> None:
    """out-first rank-2 matmul。

    功能说明:
    - 校验 `lhs[M,K] * rhs[K,N] -> out[M,N]`。
    - 允许 out/lhs/rhs 位于不同 memory space。
    - 返回 `None` 表示写回由 kernel dialect op 承接。

    使用示例:
    - matmul(out, lhs, rhs)
    """

    _ensure_memory(out, "out")
    _ensure_memory(lhs, "lhs")
    _ensure_memory(rhs, "rhs")
    out_shape = out.get_shape()
    lhs_shape = lhs.get_shape()
    rhs_shape = rhs.get_shape()
    if len(out_shape) != 2 or len(lhs_shape) != 2 or len(rhs_shape) != 2:
        _raise_contract("kernel.matmul operands must be rank-2 Memory", f"out={len(out_shape)} lhs={len(lhs_shape)} rhs={len(rhs_shape)}")
    if not _same_dim(lhs_shape[1], rhs_shape[0]):
        _raise_contract("kernel.matmul contracting dimension mismatch", f"lhs_k={lhs_shape[1]} rhs_k={rhs_shape[0]}")
    if not _same_dim(out_shape[0], lhs_shape[0]) or not _same_dim(out_shape[1], rhs_shape[1]):
        _raise_contract("kernel.matmul out shape must be [lhs.M, rhs.N]", "out shape mismatch")
    if out.get_type() is not lhs.get_type() or out.get_type() is not rhs.get_type():
        _raise_contract("kernel.matmul dtype must match across operands", "dtype mismatch")
    return None


def img2col1d(
    out: Memory,
    input_value: Memory,
    k: int | SymbolDim,
    s: int | SymbolDim = 1,
    d: int | SymbolDim = 1,
    p_left: int | SymbolDim = 0,
    p_right: int | SymbolDim = 0,
) -> None:
    """out-first 一维 img2col。

    功能说明:
    - 输入必须为 Norm rank-3 `[N,C,W]`。
    - 输出必须为 `[N,C,k,W_out]` 且元信息匹配。

    使用示例:
    - img2col1d(out, input_value, 3, s=1, d=1, p_left=1, p_right=1)
    """

    _ensure_memory(out, "out")
    _ensure_memory(input_value, "input")
    if input_value.get_format() is not Farmat.Norm:
        _raise_contract("kernel.img2col1d input format must be Norm", str(input_value.get_format()))
    input_shape = input_value.get_shape()
    if len(input_shape) != 3:
        _raise_contract("kernel.img2col1d input must be rank-3 Memory", f"rank={len(input_shape)}")
    k_dim = _normalize_param("k", k, allow_zero=False)
    s_dim = _normalize_param("s", s, allow_zero=False)
    d_dim = _normalize_param("d", d, allow_zero=False)
    p_left_dim = _normalize_param("p_left", p_left, allow_zero=True)
    p_right_dim = _normalize_param("p_right", p_right, allow_zero=True)
    n_dim, c_dim, w_dim = input_shape
    w_out = _out_dim(w_dim, k_dim, s_dim, d_dim, p_left_dim, p_right_dim)
    expected = Memory([n_dim, c_dim, k_dim, w_out], input_value.get_type(), space=input_value.get_space(), format=Farmat.Norm)
    _ensure_expected_memory(out, expected, "kernel.img2col1d")
    return None


def img2col2d(
    out: Memory,
    input_value: Memory,
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
) -> None:
    """out-first 二维 img2col。

    功能说明:
    - 输入必须为 Norm rank-4 `[N,C,H,W]`。
    - 输出必须为 `[N,C,kh,kw,H_out,W_out]` 且元信息匹配。

    使用示例:
    - img2col2d(out, input_value, 3, 3, sh=1, sw=1)
    """

    _ensure_memory(out, "out")
    _ensure_memory(input_value, "input")
    if input_value.get_format() is not Farmat.Norm:
        _raise_contract("kernel.img2col2d input format must be Norm", str(input_value.get_format()))
    input_shape = input_value.get_shape()
    if len(input_shape) != 4:
        _raise_contract("kernel.img2col2d input must be rank-4 Memory", f"rank={len(input_shape)}")
    kh_dim = _normalize_param("kh", kh, allow_zero=False)
    kw_dim = _normalize_param("kw", kw, allow_zero=False)
    sh_dim = _normalize_param("sh", sh, allow_zero=False)
    sw_dim = _normalize_param("sw", sw, allow_zero=False)
    dh_dim = _normalize_param("dh", dh, allow_zero=False)
    dw_dim = _normalize_param("dw", dw, allow_zero=False)
    ph_dim = _normalize_param("ph", ph, allow_zero=True)
    pw_dim = _normalize_param("pw", pw, allow_zero=True)
    pl_dim = _normalize_param("pl", pl, allow_zero=True)
    pr_dim = _normalize_param("pr", pr, allow_zero=True)
    n_dim, c_dim, h_dim, w_dim = input_shape
    h_out = _out_dim(h_dim, kh_dim, sh_dim, dh_dim, ph_dim, pw_dim)
    w_out = _out_dim(w_dim, kw_dim, sw_dim, dw_dim, pl_dim, pr_dim)
    expected = Memory([n_dim, c_dim, kh_dim, kw_dim, h_out, w_out], input_value.get_type(), space=input_value.get_space(), format=Farmat.Norm)
    _ensure_expected_memory(out, expected, "kernel.img2col2d")
    return None
