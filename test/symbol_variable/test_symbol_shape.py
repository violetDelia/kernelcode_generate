"""symbol_shape tests.

创建者: 小李飞刀
最后一次更改: 大闸蟹

功能说明:
- 覆盖 SymbolShape 构造、访问、序列化与异常分支。

使用示例:
- pytest -q test/symbol_variable/test_symbol_shape.py

覆盖率信息:
- 当前覆盖率: `100%`（2026-03-22 13:41:04 +0800）。
- 达标判定: 已达到 `95%` 覆盖率达标线。
- 覆盖范围: `kernel_gen/symbol_variable/symbol_shape.py` 当前行覆盖率为 `100%`。

覆盖率命令:
- pytest -q --cov=kernel_gen.symbol_variable.symbol_shape --cov-report=term-missing test/symbol_variable/test_symbol_shape.py

关联文件:
- 功能实现: kernel_gen/symbol_variable/symbol_shape.py
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

from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.symbol_shape import SymbolList, SymbolShape


# SS-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 13:41:04 +0800
# 最近一次运行成功时间: 2026-03-22 13:41:04 +0800
# 功能说明: 验证构造支持 SymbolDim 与 int 输入。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_init_accepts_symbol_dim_and_int
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_shape.py
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
# 最近一次运行测试时间: 2026-03-22 13:41:04 +0800
# 最近一次运行成功时间: 2026-03-22 13:41:04 +0800
# 功能说明: 验证序列化输出动态为 str、静态为 int。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_get_values
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_get_values() -> None:
    shape = SymbolShape(["N", 32])
    values = shape.get_values()
    assert values == ["N", 32]


# SS-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 13:41:04 +0800
# 最近一次运行成功时间: 2026-03-22 13:41:04 +0800
# 功能说明: 验证索引越界抛 IndexError 且信息一致。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_getitem_out_of_range
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_getitem_out_of_range() -> None:
    shape = SymbolShape([1, 2])
    with pytest.raises(IndexError, match="下标超出范围"):
        _ = shape[99]


# SS-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 13:41:04 +0800
# 最近一次运行成功时间: 2026-03-22 13:41:04 +0800
# 功能说明: 验证 slice 返回 List[SymbolDim]。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_getitem_slice
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_getitem_slice() -> None:
    shape = SymbolShape([1, "N", 3])
    subset = shape[1:]
    assert isinstance(subset, list)
    assert len(subset) == 2
    assert all(isinstance(item, SymbolDim) for item in subset)


# SS-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 13:41:04 +0800
# 最近一次运行成功时间: 2026-03-22 13:41:04 +0800
# 功能说明: 验证 slice 赋值会逐项转换为 SymbolDim。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_setitem_slice_converts
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_setitem_slice_converts() -> None:
    shape = SymbolShape([1, 2, 3])
    shape[0:2] = [1, "N"]
    assert all(isinstance(item, SymbolDim) for item in shape.get_shape())
    assert shape.get_values()[:2] == [1, "N"]


# SS-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 13:41:04 +0800
# 最近一次运行成功时间: 2026-03-22 13:41:04 +0800
# 功能说明: 验证 get_shape 返回拷贝，外部修改不影响内部。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_get_shape_copy
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_get_shape_copy() -> None:
    shape = SymbolShape([1, 2])
    external = shape.get_shape()
    external[0] = SymbolDim(99)
    assert shape.get_values()[0] == 1


# SS-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 13:41:04 +0800
# 最近一次运行成功时间: 2026-03-22 13:41:04 +0800
# 功能说明: 验证非 int/slice 索引抛 TypeError。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_invalid_index_type
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_invalid_index_type() -> None:
    shape = SymbolShape([1, 2])
    with pytest.raises(TypeError):
        _ = shape["0"]
    with pytest.raises(TypeError):
        shape["0"] = 1


# SS-008
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 13:41:04 +0800
# 最近一次运行成功时间: 2026-03-22 13:41:04 +0800
# 功能说明: 验证 slice 赋值非可迭代对象触发明确异常。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_slice_assign_non_iterable
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_slice_assign_non_iterable() -> None:
    shape = SymbolShape([1, 2, 3])
    with pytest.raises(TypeError, match="切片赋值必须为可迭代对象"):
        shape[0:1] = 1


# SS-009
# 创建者: 小李飞刀
# 最后一次更改: 大闸蟹
# 最近一次运行测试时间: 2026-03-22 13:41:04 +0800
# 最近一次运行成功时间: 2026-03-22 13:41:04 +0800
# 功能说明: 验证 slice 赋值元素不可转换触发明确异常。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_slice_assign_invalid_item
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_slice_assign_invalid_item() -> None:
    shape = SymbolShape([1, 2, 3])
    with pytest.raises(TypeError, match="切片赋值元素无法转换为 SymbolDim"):
        shape[0:2] = [1, object()]


# SS-018
# 创建者: 大闸蟹
# 最后一次更改: 大闸蟹
# 功能说明: 验证 slice 赋值中的浮点元素沿用 SymbolDim 的浮点输入失败边界。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_slice_assign_float_item_reuses_symbol_dim_error
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_slice_assign_float_item_reuses_symbol_dim_error() -> None:
    shape = SymbolShape([1, 2, 3])
    with pytest.raises(NotImplementedError, match="Float input is not supported"):
        shape[0:1] = [1.0]


# SS-010
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 13:41:04 +0800
# 最近一次运行成功时间: 2026-03-22 13:41:04 +0800
# 功能说明: 验证切片赋值时纯数字字符串可转换为静态维度。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_slice_assign_digit_string
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_slice_assign_digit_string() -> None:
    shape = SymbolShape([1, 2, 3])
    shape[0:1] = ["123"]
    assert shape[0].get_symbol() == SymbolDim(123).get_symbol()


# SS-011
# 创建者: 摸鱼小分队
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 13:41:04 +0800
# 最近一次运行成功时间: 2026-03-22 13:41:04 +0800
# 功能说明: 验证 SymbolList.to_symbols 复用 get_values 序列化规则，并保留动态/静态维度序列化口径。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_to_symbols
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_to_symbols() -> None:
    values = SymbolList(["N", "32", SymbolDim("K")]).to_symbols()
    assert values == ["N", 32, "K"]


# SS-012
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 13:41:04 +0800
# 最近一次运行成功时间: 2026-03-22 13:41:04 +0800
# 功能说明: 验证 int 索引赋值会转换为 SymbolDim。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_setitem_converts
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_setitem_converts() -> None:
    shape = SymbolShape([1, 2])
    shape[0] = 64
    assert isinstance(shape[0], SymbolDim)
    assert shape[0].get_symbol() == SymbolDim(64).get_symbol()


# SS-013
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 13:41:04 +0800
# 最近一次运行成功时间: 2026-03-22 13:41:04 +0800
# 功能说明: 验证 repr 输出格式。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_repr
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_repr() -> None:
    shape = SymbolShape([1, 2])
    assert repr(shape) == "Shape(1, 2)"


# SS-014
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 13:41:04 +0800
# 最近一次运行成功时间: 2026-03-22 13:41:04 +0800
# 功能说明: 验证 List 形式 repr 输出格式。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_list_repr
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_list_repr() -> None:
    list_shape = SymbolList([1, 2])
    assert repr(list_shape) == "List(1, 2)"


# SS-015
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 13:41:04 +0800
# 最近一次运行成功时间: 2026-03-22 13:41:04 +0800
# 功能说明: 验证可由已有 SymbolShape 构造等价新对象。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_construct_from_existing_shape
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_construct_from_existing_shape() -> None:
    original = SymbolShape([1, "N"])
    cloned = SymbolShape(original)
    assert isinstance(cloned, SymbolShape)
    assert cloned is not original
    assert cloned.get_values() == original.get_values()


# SS-016
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 13:41:04 +0800
# 最近一次运行成功时间: 2026-03-22 13:41:04 +0800
# 功能说明: 验证 len/iter/reversed 行为。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_iteration
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_iteration() -> None:
    shape = SymbolShape([1, 2, 3])
    assert len(shape) == 3
    assert [dim.get_symbol() for dim in shape] == [SymbolDim(1).get_symbol(), SymbolDim(2).get_symbol(), SymbolDim(3).get_symbol()]
    assert [dim.get_symbol() for dim in reversed(shape)] == [SymbolDim(3).get_symbol(), SymbolDim(2).get_symbol(), SymbolDim(1).get_symbol()]


# SS-017
# 创建者: 摸鱼小分队
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 13:41:04 +0800
# 最近一次运行成功时间: 2026-03-22 13:41:04 +0800
# 功能说明: 验证 int 索引赋值正向与负向越界均抛 IndexError 且信息一致。
# 使用示例: pytest -q test/symbol_variable/test_symbol_shape.py -k test_setitem_out_of_range
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_shape.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_shape.md
# 对应测试文件路径: test/symbol_variable/test_symbol_shape.py
def test_setitem_out_of_range() -> None:
    shape = SymbolShape([1, 2])
    with pytest.raises(IndexError, match="下标超出范围"):
        shape[99] = 1
    with pytest.raises(IndexError, match="下标超出范围"):
        shape[-3] = 1
