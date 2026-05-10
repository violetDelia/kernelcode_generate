"""Kernel operation elementwise helpers.


功能说明:
- 提供 `kernel` operation family 的 out-first 二元逐元素算术与比较 helper。
- helper 只做公开 `Memory` 元信息校验，返回 `None`，不创建新的 `Memory`。

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

使用示例:
- from kernel_gen.operation import kernel
- kernel.add(out, lhs, rhs)

关联文件:
- spec: spec/operation/kernel.md
- test: test/operation/kernel/test_elementwise.py
- 功能实现: kernel_gen/operation/kernel/elementwise.py
"""

from __future__ import annotations

from enum import Enum

from kernel_gen.core.error import (
    ERROR_ACTION,
    ERROR_TEMPLATE,
    ErrorKind,
    ErrorModule,
    kernel_code_error,
)
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


class KernelBinaryElewiseKind(Enum):
    """kernel binary elewise kind 枚举。"""

    ADD = "add"
    SUB = "sub"
    MUL = "mul"
    DIV = "div"
    TRUEDIV = "truediv"
    EQ = "eq"
    NE = "ne"
    LT = "lt"
    LE = "le"
    GT = "gt"
    GE = "ge"


_ARITHMETIC_KINDS = {
    KernelBinaryElewiseKind.ADD,
    KernelBinaryElewiseKind.SUB,
    KernelBinaryElewiseKind.MUL,
    KernelBinaryElewiseKind.DIV,
    KernelBinaryElewiseKind.TRUEDIV,
}
_COMPARE_KINDS = {
    KernelBinaryElewiseKind.EQ,
    KernelBinaryElewiseKind.NE,
    KernelBinaryElewiseKind.LT,
    KernelBinaryElewiseKind.LE,
    KernelBinaryElewiseKind.GT,
    KernelBinaryElewiseKind.GE,
}
_ERROR_SCENE = "kernel operation 参数校验"


def _raise_contract(expected: str, actual: str) -> None:
    """抛出 kernel operation 合同错误。

    功能说明:
    - 当前文件内统一错误构造，避免各 helper 重复拼装错误模板。

    使用示例:
    - _raise_contract("kernel operands must be Memory", "lhs=int")
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
    - out-first kernel helper 当前只接受 `Memory` operand。

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


def _same_shape(lhs: list[SymbolDim], rhs: list[SymbolDim]) -> bool:
    """比较两个 shape 是否完全一致。

    功能说明:
    - kernel operation 不做隐式 broadcast，rank 与各维表达都必须一致。

    使用示例:
    - _same_shape(lhs.get_shape(), rhs.get_shape())
    """

    if len(lhs) != len(rhs):
        return False
    return all(_same_dim(lhs_dim, rhs_dim) for lhs_dim, rhs_dim in zip(lhs, rhs, strict=True))


def _same_stride(lhs: list[int | SymbolDim], rhs: list[int | SymbolDim]) -> bool:
    """比较两个 stride 是否完全一致。

    功能说明:
    - 静态和符号 stride 都按公开值一致性比较。

    使用示例:
    - _same_stride(lhs.get_stride(), rhs.get_stride())
    """

    if len(lhs) != len(rhs):
        return False
    for lhs_dim, rhs_dim in zip(lhs, rhs, strict=True):
        if lhs_dim != rhs_dim:
            return False
    return True


def _ensure_common_layout(out: Memory, lhs: Memory, rhs: Memory) -> None:
    """校验 out/lhs/rhs shape、stride 与 space 一致。

    功能说明:
    - kernel.binary_elewise 不提供 broadcast 或 layout 转换能力。

    使用示例:
    - _ensure_common_layout(out, lhs, rhs)
    """

    if not _same_shape(out.get_shape(), lhs.get_shape()) or not _same_shape(out.get_shape(), rhs.get_shape()):
        _raise_contract("kernel.binary_elewise shape must match across operands", "shape mismatch")
    if not _same_stride(out.get_stride(), lhs.get_stride()) or not _same_stride(out.get_stride(), rhs.get_stride()):
        _raise_contract("kernel.binary_elewise stride must match across operands", "stride mismatch")
    if out.get_space() is not lhs.get_space() or out.get_space() is not rhs.get_space():
        _raise_contract("kernel.binary_elewise space must match across operands", "space mismatch")


def binary_elewise(out: Memory, lhs: Memory, rhs: Memory, *, kind: KernelBinaryElewiseKind) -> None:
    """执行 out-first binary elewise 元信息校验。

    功能说明:
    - 校验 out/lhs/rhs 均为 `Memory`。
    - 算术 kind 要求三者 dtype 一致。
    - 比较 kind 要求 out dtype 为 `NumericType.Bool`，lhs/rhs dtype 可不同。
    - 返回 `None` 表示写回由 kernel dialect op 承接。

    使用示例:
    - binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.ADD)
    """

    _ensure_memory(out, "out")
    _ensure_memory(lhs, "lhs")
    _ensure_memory(rhs, "rhs")
    if not isinstance(kind, KernelBinaryElewiseKind):
        _raise_contract("kernel.binary_elewise kind must be KernelBinaryElewiseKind", f"kind={type(kind).__name__}")
    _ensure_common_layout(out, lhs, rhs)
    if kind in _ARITHMETIC_KINDS:
        if out.get_type() is not lhs.get_type() or out.get_type() is not rhs.get_type():
            _raise_contract("kernel.binary_elewise arithmetic dtype must match across operands", "dtype mismatch")
        return None
    if kind in _COMPARE_KINDS:
        if out.get_type() is not NumericType.Bool:
            _raise_contract("kernel.binary_elewise compare output dtype must be Bool", f"out={out.get_type()}")
        return None
    _raise_contract("kernel.binary_elewise kind must be supported", f"kind={kind}")


def add(out: Memory, lhs: Memory, rhs: Memory) -> None:
    """out-first add。

    功能说明:
    - 校验 `kernel.binary_elewise(kind=ADD)` 公开合同。

    使用示例:
    - add(out, lhs, rhs)
    """

    return binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.ADD)


def sub(out: Memory, lhs: Memory, rhs: Memory) -> None:
    """out-first sub。

    功能说明:
    - 校验 `kernel.binary_elewise(kind=SUB)` 公开合同。

    使用示例:
    - sub(out, lhs, rhs)
    """

    return binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.SUB)


def mul(out: Memory, lhs: Memory, rhs: Memory) -> None:
    """out-first mul。

    功能说明:
    - 校验 `kernel.binary_elewise(kind=MUL)` 公开合同。

    使用示例:
    - mul(out, lhs, rhs)
    """

    return binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.MUL)


def div(out: Memory, lhs: Memory, rhs: Memory) -> None:
    """out-first div。

    功能说明:
    - 校验 `kernel.binary_elewise(kind=DIV)` 公开合同。

    使用示例:
    - div(out, lhs, rhs)
    """

    return binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.DIV)


def truediv(out: Memory, lhs: Memory, rhs: Memory) -> None:
    """out-first truediv。

    功能说明:
    - 校验 `kernel.binary_elewise(kind=TRUEDIV)` 公开合同。

    使用示例:
    - truediv(out, lhs, rhs)
    """

    return binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.TRUEDIV)


def eq(out: Memory, lhs: Memory, rhs: Memory) -> None:
    """out-first eq。

    功能说明:
    - 校验 `kernel.binary_elewise(kind=EQ)` compare 合同。

    使用示例:
    - eq(out, lhs, rhs)
    """

    return binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.EQ)


def ne(out: Memory, lhs: Memory, rhs: Memory) -> None:
    """out-first ne。

    功能说明:
    - 校验 `kernel.binary_elewise(kind=NE)` compare 合同。

    使用示例:
    - ne(out, lhs, rhs)
    """

    return binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.NE)


def lt(out: Memory, lhs: Memory, rhs: Memory) -> None:
    """out-first lt。

    功能说明:
    - 校验 `kernel.binary_elewise(kind=LT)` compare 合同。

    使用示例:
    - lt(out, lhs, rhs)
    """

    return binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.LT)


def le(out: Memory, lhs: Memory, rhs: Memory) -> None:
    """out-first le。

    功能说明:
    - 校验 `kernel.binary_elewise(kind=LE)` compare 合同。

    使用示例:
    - le(out, lhs, rhs)
    """

    return binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.LE)


def gt(out: Memory, lhs: Memory, rhs: Memory) -> None:
    """out-first gt。

    功能说明:
    - 校验 `kernel.binary_elewise(kind=GT)` compare 合同。

    使用示例:
    - gt(out, lhs, rhs)
    """

    return binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.GT)


def ge(out: Memory, lhs: Memory, rhs: Memory) -> None:
    """out-first ge。

    功能说明:
    - 校验 `kernel.binary_elewise(kind=GE)` compare 合同。

    使用示例:
    - ge(out, lhs, rhs)
    """

    return binary_elewise(out, lhs, rhs, kind=KernelBinaryElewiseKind.GE)
