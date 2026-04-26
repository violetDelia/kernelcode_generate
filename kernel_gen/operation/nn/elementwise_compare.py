"""NN operation elementwise compare family.

创建者: 守护最好的爱莉希雅
最后一次更改: 金铲铲大作战

功能说明:
- 提供逐元素比较 family。

使用示例:
- from kernel_gen.operation.nn.elementwise_compare import eq, lt, ge

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/test_operation_nn_elementwise.py
- 功能实现: kernel_gen/operation/nn/elementwise_compare.py
"""

from __future__ import annotations

from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType
from .common import (
    _ERROR_ACTION,
    _ERROR_TEMPLATE,
    _ensure_memory_operand,
    _ensure_scalar_value,
)
from .elementwise_binary import _infer_implicit_broadcast_shape

def _compare_memory_result(lhs: Memory, rhs: Memory) -> Memory:
    """逐元素比较 Memory/Memory 结果推导。

    创建者: 小李飞刀
    最后一次更改: jcc你莫辜负

    功能说明:
    - 支持隐式 broadcast 推导目标 shape。
    - 结果 dtype 固定为 Bool。

    使用示例:
    - _compare_memory_result(lhs, rhs)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_compare.py
    """
    if lhs.dtype is not rhs.dtype:
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.compare 参数校验",
                expected="Memory dtype mismatch",
                actual=f"lhs={lhs.dtype} rhs={rhs.dtype}",
                action=_ERROR_ACTION,
            )
        )
    lhs_values = lhs.shape.get_values()
    rhs_values = rhs.shape.get_values()
    if lhs_values == rhs_values:
        return lhs._clone_with_dtype(NumericType.Bool)
    target_shape = _infer_implicit_broadcast_shape(lhs, rhs)
    return Memory(target_shape, NumericType.Bool, space=lhs.space, stride=None, format=lhs.format)

def _dispatch_compare(lhs: object, rhs: object, op: str, rop: str) -> Memory:
    """二元比较调度。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 保持比较方向的调度规则。

    使用示例:
    - _dispatch_compare(mem, 1, "__lt__", "__gt__")

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_compare.py
    """
    _ensure_memory_operand(lhs, rhs)
    if isinstance(lhs, Memory) and isinstance(rhs, Memory):
        return _compare_memory_result(lhs, rhs)
    if isinstance(lhs, Memory):
        _ensure_scalar_value(rhs)
        return lhs._clone_with_dtype(NumericType.Bool)
    _ensure_scalar_value(lhs)
    return rhs._clone_with_dtype(NumericType.Bool)

def eq(lhs: object, rhs: object) -> Memory:
    """逐元素相等比较。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 支持 Memory 与 Memory/标量的相等比较。

    使用示例:
    - eq(mem, other)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_compare.py
    """
    return _dispatch_compare(lhs, rhs, "__eq__", "__eq__")

def ne(lhs: object, rhs: object) -> Memory:
    """逐元素不等比较。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 支持 Memory 与 Memory/标量的不等比较。

    使用示例:
    - ne(mem, other)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_compare.py
    """
    return _dispatch_compare(lhs, rhs, "__ne__", "__ne__")

def lt(lhs: object, rhs: object) -> Memory:
    """逐元素小于比较。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 支持 Memory 与 Memory/标量的小于比较。

    使用示例:
    - lt(mem, 0)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_compare.py
    """
    return _dispatch_compare(lhs, rhs, "__lt__", "__gt__")

def le(lhs: object, rhs: object) -> Memory:
    """逐元素小于等于比较。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 支持 Memory 与 Memory/标量的小于等于比较。

    使用示例:
    - le(mem, 0)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_compare.py
    """
    return _dispatch_compare(lhs, rhs, "__le__", "__ge__")

def gt(lhs: object, rhs: object) -> Memory:
    """逐元素大于比较。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 支持 Memory 与 Memory/标量的大于比较。

    使用示例:
    - gt(mem, other)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_compare.py
    """
    return _dispatch_compare(lhs, rhs, "__gt__", "__lt__")

def ge(lhs: object, rhs: object) -> Memory:
    """逐元素大于等于比较。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 支持 Memory 与 Memory/标量的大于等于比较。

    使用示例:
    - ge(mem, other)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_compare.py
    """
    return _dispatch_compare(lhs, rhs, "__ge__", "__le__")

__all__ = [
    "_compare_memory_result",
    "_dispatch_compare",
    "eq",
    "ne",
    "lt",
    "le",
    "gt",
    "ge",
]
