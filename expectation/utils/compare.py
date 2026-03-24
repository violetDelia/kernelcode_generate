"""Expectation compare helpers.

创建者: 榕
最后一次更改: 榕

功能说明:
- 提供 expectation 场景中复用的类型断言工具。
- 当前包含 `SymbolValueType` 静态值和动态符号值的比较逻辑。

使用示例:
- from expectation.utils.compare import assert_dynamic_symbol_int, assert_static_symbol_int

关联文件:
- spec: spec/dsl/mlir_gen.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: expectation/utils/compare.py
"""

from __future__ import annotations

from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.symbol_variable.symbol_dim import SymbolDim


def assert_static_symbol_int(value_type: SymbolValueType, expected_value: int) -> None:
    """断言类型是静态整型符号值。

    使用示例:
    - assert_static_symbol_int(func_op.args[0].type, 4)
    """
    assert isinstance(value_type, SymbolValueType)
    assert value_type.is_symbol() is False
    assert value_type.get_value() == expected_value
    assert str(value_type) == "symbol.int<{}>".format(str(expected_value))


def assert_dynamic_symbol_int(value_type: SymbolValueType, expected_expr: SymbolDim) -> None:
    """断言类型是动态整型符号值。

    使用示例:
    - assert_dynamic_symbol_int(func_op.args[0].type, SymbolDim("M") + SymbolDim("N"))
    """
    assert isinstance(value_type, SymbolValueType)
    assert value_type.is_symbol() is True
    assert value_type.get_value() == expected_expr.get_value()
    assert str(value_type) == "symbol.int<{}>".format(expected_expr)


__all__ = [
    "assert_dynamic_symbol_int",
    "assert_static_symbol_int",
]
