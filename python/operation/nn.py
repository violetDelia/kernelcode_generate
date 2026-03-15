"""NN operation API.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 提供 Memory 的逐元素算术与比较运算 API。

使用示例:
- from python.operation.nn import add, eq
- result = add(mem, 1)

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/test_operation_nn.py
- 功能实现: python/operation/nn.py
"""

from __future__ import annotations

from symbol_variable.memory import Memory


def _ensure_memory_operand(lhs: object, rhs: object) -> None:
    """校验至少一侧为 Memory。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅允许 Memory 或与 Memory 组合的二元运算。

    使用示例:
    - _ensure_memory_operand(mem, 1)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: python/operation/nn.py
    """
    if not isinstance(lhs, Memory) and not isinstance(rhs, Memory):
        raise TypeError("At least one operand must be Memory")


def _dispatch_binary(lhs: object, rhs: object, op: str, rop: str) -> Memory:
    """二元算术调度。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 根据 Memory 所在侧选择正向或反向运算。

    使用示例:
    - _dispatch_binary(mem, 1, "__add__", "__radd__")

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: python/operation/nn.py
    """
    _ensure_memory_operand(lhs, rhs)
    if isinstance(lhs, Memory):
        return getattr(lhs, op)(rhs)
    return getattr(rhs, rop)(lhs)


def _dispatch_compare(lhs: object, rhs: object, op: str, rop: str) -> Memory:
    """二元比较调度。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 保持比较方向的调度规则。

    使用示例:
    - _dispatch_compare(mem, 1, "__lt__", "__gt__")

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: python/operation/nn.py
    """
    _ensure_memory_operand(lhs, rhs)
    if isinstance(lhs, Memory):
        return getattr(lhs, op)(rhs)
    return getattr(rhs, rop)(lhs)


def add(lhs: object, rhs: object) -> Memory:
    """逐元素加法。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 Memory 与 Memory/标量的加法。

    使用示例:
    - add(mem, 1)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: python/operation/nn.py
    """
    return _dispatch_binary(lhs, rhs, "__add__", "__radd__")


def sub(lhs: object, rhs: object) -> Memory:
    """逐元素减法。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 Memory 与 Memory/标量的减法。

    使用示例:
    - sub(mem, 1)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: python/operation/nn.py
    """
    return _dispatch_binary(lhs, rhs, "__sub__", "__rsub__")


def mul(lhs: object, rhs: object) -> Memory:
    """逐元素乘法。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 Memory 与 Memory/标量的乘法。

    使用示例:
    - mul(mem, 2)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: python/operation/nn.py
    """
    return _dispatch_binary(lhs, rhs, "__mul__", "__rmul__")


def truediv(lhs: object, rhs: object) -> Memory:
    """逐元素除法。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 Memory 与 Memory/标量的除法。

    使用示例:
    - truediv(mem, 2)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: python/operation/nn.py
    """
    return _dispatch_binary(lhs, rhs, "__truediv__", "__rtruediv__")


def eq(lhs: object, rhs: object) -> Memory:
    """逐元素相等比较。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 Memory 与 Memory/标量的相等比较。

    使用示例:
    - eq(mem, other)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: python/operation/nn.py
    """
    return _dispatch_compare(lhs, rhs, "__eq__", "__eq__")


def ne(lhs: object, rhs: object) -> Memory:
    """逐元素不等比较。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 Memory 与 Memory/标量的不等比较。

    使用示例:
    - ne(mem, other)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: python/operation/nn.py
    """
    return _dispatch_compare(lhs, rhs, "__ne__", "__ne__")


def lt(lhs: object, rhs: object) -> Memory:
    """逐元素小于比较。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 Memory 与 Memory/标量的小于比较。

    使用示例:
    - lt(mem, 0)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: python/operation/nn.py
    """
    return _dispatch_compare(lhs, rhs, "__lt__", "__gt__")


def le(lhs: object, rhs: object) -> Memory:
    """逐元素小于等于比较。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 Memory 与 Memory/标量的小于等于比较。

    使用示例:
    - le(mem, 0)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: python/operation/nn.py
    """
    return _dispatch_compare(lhs, rhs, "__le__", "__ge__")


def gt(lhs: object, rhs: object) -> Memory:
    """逐元素大于比较。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 Memory 与 Memory/标量的大于比较。

    使用示例:
    - gt(mem, other)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: python/operation/nn.py
    """
    return _dispatch_compare(lhs, rhs, "__gt__", "__lt__")


def ge(lhs: object, rhs: object) -> Memory:
    """逐元素大于等于比较。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 Memory 与 Memory/标量的大于等于比较。

    使用示例:
    - ge(mem, other)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: python/operation/nn.py
    """
    return _dispatch_compare(lhs, rhs, "__ge__", "__le__")


__all__ = [
    "add",
    "sub",
    "mul",
    "truediv",
    "eq",
    "ne",
    "lt",
    "le",
    "gt",
    "ge",
]
