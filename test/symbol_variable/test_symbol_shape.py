"""symbol_shape tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 SymbolShape 构造、访问、序列化与异常分支。

使用示例:
- pytest -q test/symbol_variable/test_symbol_shape.py

关联文件:
- 功能实现: symbol_variable/symbol_shape.py
- Spec 文档: spec/symbol_variable/symbol_shape.md
- 测试文件: test/symbol_variable/test_symbol_shape.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from symbol_variable.symbol_dim import SymbolDim
from symbol_variable.symbol_shape import SymbolList, SymbolShape


# SS-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-15 15:31:30 +0800
# 最近一次运行成功时间: 2026-03-15 15:31:30 +0800
# 功能说明: 验证构造支持 SymbolDim 与 int 输入。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_init_accepts_symbol_dim_and_int
# 对应功能实现文件路径: symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_init_accepts_symbol_dim_and_int() -> None:
    shape = SymbolShape([SymbolDim("N"), 32])
    assert isinstance(shape[0], SymbolDim)
    assert shape[0].get_symbol() == SymbolDim("N").get_symbol()
    assert shape[1].get_symbol() == SymbolDim(32).get_symbol()


# SS-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-15 15:31:30 +0800
# 最近一次运行成功时间: 2026-03-15 15:31:30 +0800
# 功能说明: 验证序列化输出动态为 str、静态为 int。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_get_values
# 对应功能实现文件路径: symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_get_values() -> None:
    shape = SymbolShape(["N", 32])
    values = shape.get_values()
    assert values == ["N", 32]


# SS-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-15 15:31:30 +0800
# 最近一次运行成功时间: 2026-03-15 15:31:30 +0800
# 功能说明: 验证索引越界抛 IndexError 且信息一致。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_getitem_out_of_range
# 对应功能实现文件路径: symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_getitem_out_of_range() -> None:
    shape = SymbolShape([1, 2])
    with pytest.raises(IndexError, match="下标超出范围"):
        _ = shape[99]


# SS-009
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-15 15:31:30 +0800
# 最近一次运行成功时间: 2026-03-15 15:31:30 +0800
# 功能说明: 验证 slice 返回 List[SymbolDim]。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_getitem_slice
# 对应功能实现文件路径: symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_getitem_slice() -> None:
    shape = SymbolShape([1, "N", 3])
    subset = shape[1:]
    assert isinstance(subset, list)
    assert len(subset) == 2
    assert all(isinstance(item, SymbolDim) for item in subset)


# SS-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-15 15:31:30 +0800
# 最近一次运行成功时间: 2026-03-15 15:31:30 +0800
# 功能说明: 验证 int 索引赋值会转换为 SymbolDim。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_setitem_converts
# 对应功能实现文件路径: symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_setitem_converts() -> None:
    shape = SymbolShape([1, 2])
    shape[0] = 64
    assert isinstance(shape[0], SymbolDim)
    assert shape[0].get_symbol() == SymbolDim(64).get_symbol()


# SS-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-15 15:31:30 +0800
# 最近一次运行成功时间: 2026-03-15 15:31:30 +0800
# 功能说明: 验证 convert_from_list 对 SymbolShape 返回自身。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_convert_from_list
# 对应功能实现文件路径: symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_convert_from_list() -> None:
    shape = SymbolShape([1, 2])
    assert SymbolList.convert_from_list(shape) is shape


# SS-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-15 15:31:30 +0800
# 最近一次运行成功时间: 2026-03-15 15:31:30 +0800
# 功能说明: 验证 repr 输出格式。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_repr
# 对应功能实现文件路径: symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_repr() -> None:
    shape = SymbolShape([1, 2])
    assert repr(shape) == "Shape(1, 2)"


# SS-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-15 15:31:30 +0800
# 最近一次运行成功时间: 2026-03-15 15:31:30 +0800
# 功能说明: 验证 List 形式 repr 输出格式。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_list_repr
# 对应功能实现文件路径: symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_list_repr() -> None:
    list_shape = SymbolList([1, 2])
    assert repr(list_shape) == "List(1, 2)"


# SS-008
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-15 15:31:30 +0800
# 最近一次运行成功时间: 2026-03-15 15:31:30 +0800
# 功能说明: 验证 len/iter/reversed 行为。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_iteration
# 对应功能实现文件路径: symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_iteration() -> None:
    shape = SymbolShape([1, 2, 3])
    assert len(shape) == 3
    assert [dim.get_symbol() for dim in shape] == [SymbolDim(1).get_symbol(), SymbolDim(2).get_symbol(), SymbolDim(3).get_symbol()]
    assert [dim.get_symbol() for dim in reversed(shape)] == [SymbolDim(3).get_symbol(), SymbolDim(2).get_symbol(), SymbolDim(1).get_symbol()]
