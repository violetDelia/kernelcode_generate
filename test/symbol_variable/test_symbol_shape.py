"""symbol_shape tests.

创建者: 小李飞刀
最后一次更改: OpenAI Codex

功能说明:
- 覆盖 SymbolShape / SymbolList 的构造、访问、序列化与异常路径。

使用示例:
- pytest -q test/symbol_variable/test_symbol_shape.py

关联文件:
- 功能实现: kernel_gen/symbol_variable/symbol_shape.py
- Spec 文档: spec/symbol_variable/symbol_shape.md
- 测试文件: test/symbol_variable/test_symbol_shape.py
"""

from __future__ import annotations

import pytest

from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.symbol_shape import SymbolList, SymbolShape


def _symbols(values: list[SymbolDim]) -> list[object]:
    """提取测试中的底层符号列表。"""
    return [value.get_symbol() for value in values]


def test_init_accepts_symbol_dim_and_int() -> None:
    shape = SymbolShape([SymbolDim("N"), 32])

    assert isinstance(shape[0], SymbolDim)
    assert shape[0].get_symbol() == SymbolDim("N").get_symbol()
    assert shape[1].get_symbol() == SymbolDim(32).get_symbol()


def test_public_serialization_paths() -> None:
    shape = SymbolShape(["N", 32])
    floordiv_shape = SymbolShape([(SymbolDim("N") // SymbolDim("S")) + 1, 32])
    values = SymbolList(["N", "32", SymbolDim("K")]).to_symbols()

    assert shape.get_values() == ["N", 32]
    assert floordiv_shape.get_values() == ["N // S + 1", 32]
    assert values == ["N", 32, "K"]


def test_repr_variants() -> None:
    assert repr(SymbolShape([1, 2])) == "Shape(1, 2)"
    assert repr(SymbolList([1, 2])) == "List(1, 2)"


def test_construct_from_existing_shape_returns_equivalent_copy() -> None:
    original = SymbolShape([1, "N"])
    cloned = SymbolShape(original)

    assert isinstance(cloned, SymbolShape)
    assert cloned is not original
    assert cloned.get_values() == original.get_values()


def test_get_shape_returns_copy() -> None:
    shape = SymbolShape([1, 2])
    external = shape.get_shape()
    external[0] = SymbolDim(99)

    assert shape.get_values()[0] == 1


def test_iteration_protocol() -> None:
    shape = SymbolShape([1, 2, 3])

    assert len(shape) == 3
    assert _symbols(list(shape)) == _symbols([SymbolDim(1), SymbolDim(2), SymbolDim(3)])
    assert _symbols(list(reversed(shape))) == _symbols([SymbolDim(3), SymbolDim(2), SymbolDim(1)])


def test_getitem_errors_and_slice_access() -> None:
    shape = SymbolShape([1, "N", 3])

    with pytest.raises(IndexError, match="下标超出范围"):
        _ = shape[99]
    with pytest.raises(TypeError, match="索引类型错误"):
        _ = shape["0"]

    subset = shape[1:]
    assert isinstance(subset, list)
    assert len(subset) == 2
    assert all(isinstance(item, SymbolDim) for item in subset)


def test_int_setitem_converts_and_checks_range() -> None:
    shape = SymbolShape([1, 2])
    shape[0] = 64

    assert isinstance(shape[0], SymbolDim)
    assert shape[0].get_symbol() == SymbolDim(64).get_symbol()

    with pytest.raises(IndexError, match="下标超出范围"):
        shape[99] = 1
    with pytest.raises(IndexError, match="下标超出范围"):
        shape[-3] = 1
    with pytest.raises(TypeError, match="索引类型错误"):
        shape["0"] = 1


def test_slice_setitem_converts_values() -> None:
    shape = SymbolShape([1, 2, 3])
    shape[0:2] = [1, "N"]

    assert all(isinstance(item, SymbolDim) for item in shape.get_shape())
    assert shape.get_values()[:2] == [1, "N"]

    shape[0:1] = ["123"]
    assert shape[0].get_symbol() == SymbolDim(123).get_symbol()


def test_slice_setitem_rejects_invalid_inputs() -> None:
    shape = SymbolShape([1, 2, 3])

    with pytest.raises(TypeError, match="切片赋值必须为可迭代对象"):
        shape[0:1] = 1
    with pytest.raises(TypeError, match="切片赋值元素无法转换为 SymbolDim"):
        shape[0:2] = [1, object()]
    with pytest.raises(NotImplementedError, match="Float input is not supported"):
        shape[0:1] = [1.0]
