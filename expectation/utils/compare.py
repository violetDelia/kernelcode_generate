"""Expectation comparison helpers.

创建者: 朽木露琪亚
最后一次更改: 榕

功能说明:
- 为 expectation 脚本提供 `symbol.int` 结果的统一断言辅助。
- 同时支持静态整数值与动态符号表达式的断言。
- 支持 `Memory` 与 IR `nn.memory` 类型的一致性断言。

使用示例:
- assert_static_symbol_int(value.type, 3)
- assert_dynamic_symbol_int(value.type, SymbolDim("N") + SymbolDim("1"))
- assert_memory(value.type, memory)

关联文件:
- 功能实现: expectation/utils/compare.py
"""

from __future__ import annotations

from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dsl.emit_mlir import _memory_to_nn_type
from kernel_gen.symbol_variable.memory import Memory
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


def assert_memory(value_type: object, expected_memory: Memory) -> None:
    """断言 IR `nn.memory` 类型与 Memory 描述一致。

    参数:
    - value_type: IR 中的类型对象，应为 ``NnMemoryType``。
    - expected_memory: 期望的 ``Memory`` 描述对象。
    """

    assert isinstance(expected_memory, Memory)
    assert isinstance(value_type, NnMemoryType)
    expected_type = _memory_to_nn_type(expected_memory)
    assert value_type == expected_type
