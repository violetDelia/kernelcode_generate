"""Kernel operation unary activation helpers.


功能说明:
- 提供 `kernel` operation family 的 out-first unary compute helper。
- helper 只做公开 `Memory` 元信息校验，返回 `None`，不创建新的 `Memory`。

API 列表:
- `exp(out: Memory, input_value: Memory) -> None`

使用示例:
- from kernel_gen.operation import kernel
- kernel.exp(out, input_value)

关联文件:
- spec: spec/operation/kernel.md
- test: test/operation/kernel/test_activation.py
- 功能实现: kernel_gen/operation/kernel/activation.py
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
from kernel_gen.symbol_variable.type import FLOAT_DTYPES

_ERROR_SCENE = "kernel operation 参数校验"


def _raise_contract(expected: str, actual: str) -> None:
    """抛出 kernel activation 合同错误。

    功能说明:
    - 当前文件内统一错误构造。

    使用示例:
    - _raise_contract("kernel.exp operands must be Memory", "input=int")
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
    - out-first kernel activation helper 当前只接受 `Memory` operand。

    使用示例:
    - _ensure_memory(out, "out")
    """

    if not isinstance(value, Memory):
        _raise_contract(f"kernel.{name} operand must be Memory", f"{name}={type(value).__name__}")


def _same_dim(lhs: SymbolDim, rhs: SymbolDim) -> bool:
    """比较两个 SymbolDim 公开等价。

    功能说明:
    - 复用 `SymbolDim.__eq__` 公开比较语义。

    使用示例:
    - _same_dim(SymbolDim("M"), SymbolDim("M"))
    """

    return lhs == rhs


def _same_symbol_list(lhs: list[int | SymbolDim], rhs: list[int | SymbolDim]) -> bool:
    """比较 shape/stride 列表是否完全一致。

    功能说明:
    - kernel.exp 不提供 broadcast 或 layout 转换能力。

    使用示例:
    - _same_symbol_list(out.get_shape(), input_value.get_shape())
    """

    if len(lhs) != len(rhs):
        return False
    for lhs_dim, rhs_dim in zip(lhs, rhs, strict=True):
        if isinstance(lhs_dim, SymbolDim) and isinstance(rhs_dim, SymbolDim):
            if not _same_dim(lhs_dim, rhs_dim):
                return False
            continue
        if lhs_dim != rhs_dim:
            return False
    return True


def exp(out: Memory, input_value: Memory) -> None:
    """out-first exponential。

    功能说明:
    - 校验 `kernel.exp(out, input_value)` 公开合同。
    - `out` 与 `input_value` 的 shape/stride/space/dtype 必须一致。
    - dtype 必须是公开浮点 NumericType。

    使用示例:
    - exp(out, input_value)
    """

    _ensure_memory(out, "out")
    _ensure_memory(input_value, "input")
    if not _same_symbol_list(out.get_shape(), input_value.get_shape()):
        _raise_contract("kernel.exp shape must match across operands", "shape mismatch")
    if not _same_symbol_list(out.get_stride(), input_value.get_stride()):
        _raise_contract("kernel.exp stride must match across operands", "stride mismatch")
    if out.get_space() is not input_value.get_space():
        _raise_contract("kernel.exp space must match across operands", "space mismatch")
    if out.get_type() is not input_value.get_type():
        _raise_contract("kernel.exp dtype must match across operands", "dtype mismatch")
    if input_value.get_type() not in FLOAT_DTYPES:
        _raise_contract("kernel.exp dtype must be float", f"dtype={input_value.get_type()}")
    return None


__all__ = ["exp"]
