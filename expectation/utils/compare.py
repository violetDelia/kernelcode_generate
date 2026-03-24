"""Expectation comparison helpers.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 为 expectation 脚本提供 `symbol.int` 结果的统一断言辅助。
- 同时支持静态整数值与动态符号表达式的断言。

使用示例:
- assert_static_symbol_int(value.type, 3)
- assert_dynamic_symbol_int(value.type, SymbolDim("N") + SymbolDim("1"))

关联文件:
- 功能实现: expectation/utils/compare.py
"""

from __future__ import annotations

from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.symbol_variable.symbol_dim import SymbolDim


def assert_static_symbol_int(value_type: object, expected_value: int | float) -> None:
    """断言 `symbol.int` 类型表示静态整数值。"""

    assert isinstance(value_type, SymbolValueType)
    normalized = int(expected_value) if isinstance(expected_value, float) and expected_value.is_integer() else expected_value
    assert not value_type.is_symbol()
    assert value_type.get_value() == normalized
    assert value_type == SymbolValueType.from_expr(str(normalized))


def assert_dynamic_symbol_int(value_type: object, expected_expr: SymbolDim | str) -> None:
    """断言 `symbol.int` 类型表示动态符号表达式。"""

    assert isinstance(value_type, SymbolValueType)
    assert value_type.is_symbol()
    expected_text = str(expected_expr.get_value()) if isinstance(expected_expr, SymbolDim) else expected_expr
    assert value_type.get_value() == expected_text
    assert value_type == SymbolValueType.from_expr(expected_text)
