"""Kernel operation public API.


功能说明:
- 暴露 out-first `kernel` operation family。
- 本子模块对齐 `kernel` dialect，所有 helper 返回 `None`，不创建新 `Memory`。

API 列表:
- `class KernelBinaryElewiseKind(Enum)`
- `binary_elewise(out: Memory, lhs: Memory, rhs: Memory, *, kind: KernelBinaryElewiseKind) -> None`
- `add(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `sub(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `mul(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `div(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `truediv(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `eq(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `ne(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `lt(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `le(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `gt(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `ge(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `exp(out: Memory, input_value: Memory) -> None`
- `class KernelReduceKind(Enum)`
- `reduce(out: Memory, input_value: Memory, *, kind: KernelReduceKind, axis: int, keepdim: bool = False) -> None`
- `matmul(out: Memory, lhs: Memory, rhs: Memory) -> None`
- `img2col1d(out: Memory, input_value: Memory, k: int | SymbolDim, s: int | SymbolDim = 1, d: int | SymbolDim = 1, p_left: int | SymbolDim = 0, p_right: int | SymbolDim = 0) -> None`
- `img2col2d(out: Memory, input_value: Memory, kh: int | SymbolDim, kw: int | SymbolDim, sh: int | SymbolDim = 1, sw: int | SymbolDim = 1, dh: int | SymbolDim = 1, dw: int | SymbolDim = 1, ph: int | SymbolDim = 0, pw: int | SymbolDim = 0, pl: int | SymbolDim = 0, pr: int | SymbolDim = 0) -> None`

使用示例:
- from kernel_gen.operation import kernel
- kernel.matmul(out, lhs, rhs)

关联文件:
- spec: spec/operation/kernel.md
- test: test/operation/kernel/test_elementwise.py
- test: test/operation/kernel/test_activation.py
- test: test/operation/kernel/test_reduction.py
- test: test/operation/kernel/test_structured.py
- 功能实现: kernel_gen/operation/kernel/elementwise.py
- 功能实现: kernel_gen/operation/kernel/activation.py
- 功能实现: kernel_gen/operation/kernel/reduction.py
- 功能实现: kernel_gen/operation/kernel/structured.py
"""

from __future__ import annotations

from .elementwise import (
    KernelBinaryElewiseKind,
    add,
    binary_elewise,
    div,
    eq,
    ge,
    gt,
    le,
    lt,
    mul,
    ne,
    sub,
    truediv,
)
from .activation import exp
from .reduction import KernelReduceKind, reduce
from .structured import img2col1d, img2col2d, matmul

__all__ = [
    "KernelBinaryElewiseKind",
    "binary_elewise",
    "add",
    "sub",
    "mul",
    "div",
    "truediv",
    "eq",
    "ne",
    "lt",
    "le",
    "gt",
    "ge",
    "exp",
    "KernelReduceKind",
    "reduce",
    "matmul",
    "img2col1d",
    "img2col2d",
]
