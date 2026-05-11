"""Kernel operation reduction helpers.


功能说明:
- 提供 `kernel` operation family 的 out-first reduction helper。
- helper 只做公开 `Memory` 元信息校验，返回 `None`，不创建新的 `Memory`。

API 列表:
- `class KernelReduceKind(Enum)`
- `reduce(out: Memory, input_value: Memory, *, kind: KernelReduceKind, axis: int, keepdim: bool = False) -> None`

使用示例:
- from kernel_gen.operation import kernel
- kernel.reduce(out, input_value, kind=kernel.KernelReduceKind.SUM, axis=1, keepdim=True)

关联文件:
- spec: spec/operation/kernel.md
- test: test/operation/kernel/test_reduction.py
- 功能实现: kernel_gen/operation/kernel/reduction.py
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

_ERROR_SCENE = "kernel operation 参数校验"


class KernelReduceKind(Enum):
    """kernel reduce kind 枚举。

    功能说明:
    - 定义 `kernel.reduce(...)` 公开支持的归约 kind。

    使用示例:
    - kind = KernelReduceKind.SUM
    """

    SUM = "sum"
    MIN = "min"
    MAX = "max"


def _raise_contract(expected: str, actual: str) -> None:
    """抛出 kernel reduction 合同错误。

    功能说明:
    - 当前文件内统一错误构造。

    使用示例:
    - _raise_contract("kernel.reduce axis out of range", "axis=4")
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
    - out-first kernel reduction helper 当前只接受 `Memory` operand。

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
    - kernel.reduce 的 out shape 必须机械匹配 reduce 公式。

    使用示例:
    - _same_shape(out.get_shape(), expected)
    """

    if len(lhs) != len(rhs):
        return False
    return all(_same_dim(lhs_dim, rhs_dim) for lhs_dim, rhs_dim in zip(lhs, rhs, strict=True))


def _normalize_axis(axis: int, rank: int) -> int:
    """校验并返回合法 axis。

    功能说明:
    - kernel.reduce dialect 公开 axis 为非负维度下标。
    - bool 不属于合法 axis。

    使用示例:
    - axis = _normalize_axis(1, rank=3)
    """

    if isinstance(axis, bool) or not isinstance(axis, int):
        _raise_contract("kernel.reduce axis must be int", f"axis={type(axis).__name__}")
    if axis < 0 or axis >= rank:
        _raise_contract("kernel.reduce axis out of range", f"axis={axis} rank={rank}")
    return axis


def _expected_reduce_shape(input_shape: list[SymbolDim], axis: int, keepdim: bool) -> list[SymbolDim]:
    """构造 reduce 输出 shape。

    功能说明:
    - keepdim=True 时对应轴替换为 1。
    - keepdim=False 时移除对应轴。

    使用示例:
    - shape = _expected_reduce_shape(input_shape, axis=1, keepdim=True)
    """

    if keepdim:
        return [SymbolDim(1) if index == axis else dim for index, dim in enumerate(input_shape)]
    return [dim for index, dim in enumerate(input_shape) if index != axis]


def reduce(
    out: Memory,
    input_value: Memory,
    *,
    kind: KernelReduceKind,
    axis: int,
    keepdim: bool = False,
) -> None:
    """out-first reduction。

    功能说明:
    - 校验 `kernel.reduce(out, input_value, kind=..., axis=..., keepdim=...)` 公开合同。
    - `out` 与 `input_value` 的 dtype/space 必须一致。
    - `out.shape` 必须匹配 `axis/keepdim` 推导出的 reduce 结果。

    使用示例:
    - reduce(out, input_value, kind=KernelReduceKind.MAX, axis=1, keepdim=True)
    """

    _ensure_memory(out, "out")
    _ensure_memory(input_value, "input")
    if not isinstance(kind, KernelReduceKind):
        _raise_contract("kernel.reduce kind must be KernelReduceKind", f"kind={type(kind).__name__}")
    if not isinstance(keepdim, bool):
        _raise_contract("kernel.reduce keepdim must be bool", f"keepdim={type(keepdim).__name__}")
    input_shape = input_value.get_shape()
    axis_value = _normalize_axis(axis, len(input_shape))
    if out.get_type() is not input_value.get_type():
        _raise_contract("kernel.reduce dtype must match across operands", "dtype mismatch")
    if out.get_space() is not input_value.get_space():
        _raise_contract("kernel.reduce space must match across operands", "space mismatch")
    expected_shape = _expected_reduce_shape(input_shape, axis_value, keepdim)
    if not _same_shape(out.get_shape(), expected_shape):
        _raise_contract("kernel.reduce out shape must match reduce contract", "shape mismatch")
    return None


__all__ = ["KernelReduceKind", "reduce"]
