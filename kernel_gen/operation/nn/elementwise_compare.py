"""NN operation elementwise compare family.


功能说明:
- 提供逐元素比较 family。

API 列表:
- `eq(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `ne(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `lt(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `le(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `gt(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `ge(lhs: CompareOperand, rhs: CompareOperand) -> Memory`

使用示例:
- from kernel_gen.operation.nn.elementwise_compare import eq, lt, ge

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/nn/test_elementwise.py
- 功能实现: kernel_gen/operation/nn/elementwise_compare.py
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
from kernel_gen.symbol_variable.symbol_shape import SymbolShape
from kernel_gen.symbol_variable.type import NumericType

CompareScalar = int | float | bool
CompareOperand = Memory | CompareScalar


def _merge_broadcast_dim(lhs_dim: int | str, rhs_dim: int | str) -> int | str:
    """合并两个维度为隐式 broadcast 目标维度。


    功能说明:
    - 维度相等时返回该维度。
    - 任一侧为静态 1 时返回另一侧。
    - 其他情况视为不兼容。

    使用示例:
    - _merge_broadcast_dim(1, "N")
    """

    if lhs_dim == rhs_dim:
        return lhs_dim
    if lhs_dim == 1:
        return rhs_dim
    if rhs_dim == 1:
        return lhs_dim
    raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
        ERROR_TEMPLATE.format(
            scene="nn.compare 参数校验",
            expected="Implicit broadcast dimension mismatch",
            actual=f"lhs={lhs_dim} rhs={rhs_dim}",
            action=ERROR_ACTION,
        )
    )


def _infer_implicit_broadcast_shape(lhs: Memory, rhs: Memory) -> SymbolShape:
    """推导逐元素隐式 broadcast 的共同目标 shape。


    功能说明:
    - 按尾维对齐规则合并维度。
    - 对较小 rank 的一侧视为前置维补 1。

    使用示例:
    - _infer_implicit_broadcast_shape(lhs, rhs)
    """

    lhs_values = lhs.shape.get_values()
    rhs_values = rhs.shape.get_values()
    lhs_rank = len(lhs_values)
    rhs_rank = len(rhs_values)
    max_rank = lhs_rank if lhs_rank >= rhs_rank else rhs_rank
    result_reversed: list[int | str] = []
    for idx in range(1, max_rank + 1):
        lhs_dim = lhs_values[-idx] if idx <= lhs_rank else 1
        rhs_dim = rhs_values[-idx] if idx <= rhs_rank else 1
        result_reversed.append(_merge_broadcast_dim(lhs_dim, rhs_dim))
    return SymbolShape(list(reversed(result_reversed)))


def _ensure_memory_operand(lhs: CompareOperand, rhs: CompareOperand) -> None:
    """校验至少一侧为 `Memory`。


    功能说明:
    - 仅允许 `Memory` 或与 `Memory` 组合的二元运算。

    使用示例:
    - _ensure_memory_operand(Memory([1], NumericType.Float32), 1)
    """

    if not isinstance(lhs, Memory) and not isinstance(rhs, Memory):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.compare 参数校验",
                expected="At least one operand must be Memory",
                actual=f"lhs={type(lhs).__name__} rhs={type(rhs).__name__}",
                action=ERROR_ACTION,
            )
        )


def _ensure_scalar_value(value: CompareScalar) -> None:
    """校验公开标量输入类型。


    功能说明:
    - 仅允许 `int/float/bool` 作为与 `Memory` 组合的公开标量。

    使用示例:
    - _ensure_scalar_value(1)
    """

    if isinstance(value, bool):
        return
    if not isinstance(value, (int, float)):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.compare 参数校验",
                expected="Unsupported scalar type for nn operation",
                actual=type(value).__name__,
                action=ERROR_ACTION,
            )
        )


def _compare_memory_result(lhs: Memory, rhs: Memory) -> Memory:
    """逐元素比较 Memory/Memory 结果推导。


    功能说明:
    - 支持隐式 broadcast 推导目标 shape。
    - 结果 dtype 固定为 Bool。

    使用示例:
    - _compare_memory_result(lhs, rhs)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_compare.py
    """
    if lhs.dtype is not rhs.dtype:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.compare 参数校验",
                expected="Memory dtype mismatch",
                actual=f"lhs={lhs.dtype} rhs={rhs.dtype}",
                action=ERROR_ACTION,
            )
        )
    lhs_values = lhs.shape.get_values()
    rhs_values = rhs.shape.get_values()
    if lhs_values == rhs_values:
        return lhs.clone(dtype=NumericType.Bool)
    target_shape = _infer_implicit_broadcast_shape(lhs, rhs)
    return Memory(target_shape, NumericType.Bool, space=lhs.space, stride=None, format=lhs.format)

def _dispatch_compare(lhs: CompareOperand, rhs: CompareOperand, op: str, rop: str) -> Memory:
    """二元比较调度。


    功能说明:
    - 保持比较方向的调度规则。

    使用示例:
    - _dispatch_compare(mem, 1, "__lt__", "__gt__")

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_compare.py
    """
    _ensure_memory_operand(lhs, rhs)
    if isinstance(lhs, Memory) and isinstance(rhs, Memory):
        return _compare_memory_result(lhs, rhs)
    if isinstance(lhs, Memory):
        _ensure_scalar_value(rhs)
        return lhs.clone(dtype=NumericType.Bool)
    _ensure_scalar_value(lhs)
    return rhs.clone(dtype=NumericType.Bool)

def eq(lhs: CompareOperand, rhs: CompareOperand) -> Memory:
    """逐元素相等比较。


    功能说明:
    - 支持 Memory 与 Memory/标量的相等比较。

    使用示例:
    - eq(mem, other)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_compare.py
    """
    return _dispatch_compare(lhs, rhs, "__eq__", "__eq__")

def ne(lhs: CompareOperand, rhs: CompareOperand) -> Memory:
    """逐元素不等比较。


    功能说明:
    - 支持 Memory 与 Memory/标量的不等比较。

    使用示例:
    - ne(mem, other)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_compare.py
    """
    return _dispatch_compare(lhs, rhs, "__ne__", "__ne__")

def lt(lhs: CompareOperand, rhs: CompareOperand) -> Memory:
    """逐元素小于比较。


    功能说明:
    - 支持 Memory 与 Memory/标量的小于比较。

    使用示例:
    - lt(mem, 0)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_compare.py
    """
    return _dispatch_compare(lhs, rhs, "__lt__", "__gt__")

def le(lhs: CompareOperand, rhs: CompareOperand) -> Memory:
    """逐元素小于等于比较。


    功能说明:
    - 支持 Memory 与 Memory/标量的小于等于比较。

    使用示例:
    - le(mem, 0)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_compare.py
    """
    return _dispatch_compare(lhs, rhs, "__le__", "__ge__")

def gt(lhs: CompareOperand, rhs: CompareOperand) -> Memory:
    """逐元素大于比较。


    功能说明:
    - 支持 Memory 与 Memory/标量的大于比较。

    使用示例:
    - gt(mem, other)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_compare.py
    """
    return _dispatch_compare(lhs, rhs, "__gt__", "__lt__")

def ge(lhs: CompareOperand, rhs: CompareOperand) -> Memory:
    """逐元素大于等于比较。


    功能说明:
    - 支持 Memory 与 Memory/标量的大于等于比较。

    使用示例:
    - ge(mem, other)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_compare.py
    """
    return _dispatch_compare(lhs, rhs, "__ge__", "__le__")

__all__ = ["eq", "ne", "lt", "le", "gt", "ge"]
