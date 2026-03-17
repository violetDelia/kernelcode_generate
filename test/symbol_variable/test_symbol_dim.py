"""symbol_dim tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 SymbolDim 构造、运算、比较、动态性判断与错误分支。

使用示例:
- pytest -q test/symbol_variable/test_symbol_dim.py

关联文件:
- 功能实现: python/symbol_variable/symbol_dim.py
- Spec 文档: spec/symbol_variable/symbol_dim.md
- 测试文件: test/symbol_variable/test_symbol_dim.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import sympy as sp
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.symbol_variable.symbol_dim import SymbolDim


# SD-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 02:22:19 +0800
# 最近一次运行成功时间: 2026-03-18 02:22:19 +0800
# 功能说明: 验证 SymbolDim 构造支持 int/str/sympy.Basic。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_init_accepts_int_str_sympy
# 对应功能实现文件路径: python/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_init_accepts_int_str_sympy() -> None:
    int_dim = SymbolDim(8)
    str_dim = SymbolDim("N")
    sym_dim = SymbolDim(sp.symbols("M"))
    expr_dim = SymbolDim(sp.Symbol("K") + 1)

    assert int_dim.get_symbol() == sp.Integer(8)
    assert str_dim.get_symbol() == sp.symbols("N", integer=True, real=True)
    assert sym_dim.get_symbol() == sp.symbols("M", integer=True, real=True)
    assert expr_dim.get_symbol() == sp.Symbol("K") + 1


# SD-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 01:43:13 +0800
# 最近一次运行成功时间: 2026-03-16 01:43:13 +0800
# 功能说明: 验证纯数字字符串构造触发 ValueError。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_init_rejects_numeric_string
# 对应功能实现文件路径: python/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_init_rejects_numeric_string() -> None:
    for value in ["12", " 12 ", "１２", "٠١٢"]:
        with pytest.raises(ValueError):
            SymbolDim(value)


# SD-017
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 01:43:13 +0800
# 最近一次运行成功时间: 2026-03-16 01:43:13 +0800
# 功能说明: 验证空白字符串构造触发 ValueError。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_init_rejects_blank_string
# 对应功能实现文件路径: python/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_init_rejects_blank_string() -> None:
    for value in ["", "   ", "\t"]:
        with pytest.raises(ValueError):
            SymbolDim(value)


# SD-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 01:43:13 +0800
# 最近一次运行成功时间: 2026-03-16 01:43:13 +0800
# 功能说明: 验证算术运算返回 SymbolDim 且表达式正确。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_arithmetic_ops
# 对应功能实现文件路径: python/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_arithmetic_ops() -> None:
    dim = SymbolDim("N")
    sym_operand = sp.Symbol("K")

    add_res = dim + 2
    sub_res = dim - "M"
    mul_res = dim * 3
    div_res = dim / 4
    sym_res = dim + sym_operand

    assert isinstance(add_res, SymbolDim)
    assert isinstance(sub_res, SymbolDim)
    assert isinstance(mul_res, SymbolDim)
    assert isinstance(div_res, SymbolDim)

    assert add_res.get_symbol() == sp.symbols("N", integer=True, real=True) + sp.Integer(2)
    assert sub_res.get_symbol() == sp.symbols("N", integer=True, real=True) - sp.symbols(
        "M", integer=True, real=True
    )
    assert mul_res.get_symbol() == sp.symbols("N", integer=True, real=True) * sp.Integer(3)
    assert div_res.get_symbol() == sp.symbols("N", integer=True, real=True) / sp.Integer(4)
    assert sym_res.get_symbol() == sp.symbols("N", integer=True, real=True) + sp.symbols(
        "K", integer=True, real=True
    )


# SD-012
# 创建者: 小李飞刀
# 最后一次更改: 摸鱼小分队
# 最近一次运行测试时间: 2026-03-16 01:43:13 +0800
# 最近一次运行成功时间: 2026-03-16 01:43:13 +0800
# 功能说明: 验证运算入口拒绝纯数字/空白字符串。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_arithmetic_rejects_numeric_string
# 对应功能实现文件路径: python/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_arithmetic_rejects_numeric_string() -> None:
    dim = SymbolDim("N")
    for value in ["12", " 12 ", "１２", " ", "\t"]:
        with pytest.raises(ValueError):
            _ = dim + value
    with pytest.raises(ValueError):
        _ = "12" / dim


# SD-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 01:43:13 +0800
# 最近一次运行成功时间: 2026-03-16 01:43:13 +0800
# 功能说明: 验证反向算术运算返回 SymbolDim 且表达式正确。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_reverse_arithmetic_ops
# 对应功能实现文件路径: python/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_reverse_arithmetic_ops() -> None:
    dim = SymbolDim("N")
    sym_left = sp.Symbol("P")

    add_res = 1 + dim
    sub_res = 10 - dim
    mul_res = 2 * dim
    div_res = "K" / dim
    sym_div = sym_left / dim

    assert add_res.get_symbol() == sp.Integer(1) + sp.symbols("N", integer=True, real=True)
    assert sub_res.get_symbol() == sp.Integer(10) - sp.symbols("N", integer=True, real=True)
    assert mul_res.get_symbol() == sp.Integer(2) * sp.symbols("N", integer=True, real=True)
    assert div_res.get_symbol() == sp.symbols("K", integer=True, real=True) / sp.symbols(
        "N", integer=True, real=True
    )
    assert sym_div.get_symbol() == sp.symbols("P", integer=True, real=True) / sp.symbols(
        "N", integer=True, real=True
    )


# SD-005
# 创建者: 小李飞刀
# 最后一次更改: 摸鱼小分队
# 最近一次运行测试时间: 2026-03-16 01:43:13 +0800
# 最近一次运行成功时间: 2026-03-16 01:43:13 +0800
# 功能说明: 验证动态性判断与构造入口行为。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_dynamic_and_construct
# 对应功能实现文件路径: python/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_dynamic_and_construct() -> None:
    assert SymbolDim(8).is_dynamic() is False
    assert SymbolDim("N").is_dynamic() is True

    constructed = SymbolDim(32)
    assert isinstance(constructed, SymbolDim)
    assert constructed.get_symbol() == sp.Integer(32)


# SD-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 01:43:13 +0800
# 最近一次运行成功时间: 2026-03-16 01:43:13 +0800
# 功能说明: 验证相等比较支持 int/str/SymbolDim。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_equality
# 对应功能实现文件路径: python/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_equality() -> None:
    assert SymbolDim(4) == 4
    assert SymbolDim("N") == "N"
    assert SymbolDim("N") == SymbolDim("N")
    assert SymbolDim(sp.symbols("M")) == "M"
    assert SymbolDim("N") == sp.Symbol("N")


# SD-013
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 02:22:19 +0800
# 最近一次运行成功时间: 2026-03-18 02:22:19 +0800
# 功能说明: 验证比较入口拒绝纯数字/空白字符串。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_compare_rejects_numeric_string
# 对应功能实现文件路径: python/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_compare_rejects_numeric_string() -> None:
    dim = SymbolDim("N")
    for value in ["12", " 12 ", "１２", "٠١٢", " ", "\t"]:
        with pytest.raises(ValueError):
            _ = dim == value


# SD-018
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 02:22:19 +0800
# 最近一次运行成功时间: 2026-03-18 02:22:19 +0800
# 功能说明: 验证 sympy.Basic 表达式可用于算术与比较入口。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_sympy_basic_expression_operands
# 对应功能实现文件路径: python/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_sympy_basic_expression_operands() -> None:
    expr = sp.Symbol("K") + 1
    dim = SymbolDim("N")
    result = dim + expr
    assert result.get_symbol() == sp.symbols("N", integer=True, real=True) + expr
    compare = dim == expr
    assert isinstance(compare, bool)


# SD-009
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 01:43:13 +0800
# 最近一次运行成功时间: 2026-03-16 01:43:13 +0800
# 功能说明: 验证 str 操作数符号假设统一后的运算结果。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_string_operand_unification
# 对应功能实现文件路径: python/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_string_operand_unification() -> None:
    dim = SymbolDim("N")
    result = dim + "N"
    expected = sp.symbols("N", integer=True, real=True) + sp.symbols("N", integer=True, real=True)
    assert result.get_symbol() == expected


# SD-015
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 01:43:13 +0800
# 最近一次运行成功时间: 2026-03-16 01:43:13 +0800
# 功能说明: 验证非纯数字字符串继续按符号名处理。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_non_numeric_string_allowed
# 对应功能实现文件路径: python/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_non_numeric_string_allowed() -> None:
    plus_dim = SymbolDim("+1")
    assert plus_dim.get_symbol() == sp.symbols("+1", integer=True, real=True)
    expr = SymbolDim("N") + "3.14"
    expected = sp.symbols("N", integer=True, real=True) + sp.symbols("3.14", integer=True, real=True)
    assert expr.get_symbol() == expected


# SD-010
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 01:43:13 +0800
# 最近一次运行成功时间: 2026-03-16 01:43:13 +0800
# 功能说明: 验证 sympy.Symbol 无显式假设时被规范化。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_symbol_without_assumption_normalized
# 对应功能实现文件路径: python/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_symbol_without_assumption_normalized() -> None:
    sym = sp.Symbol("P")
    dim = SymbolDim(sym)
    assert dim.get_symbol() == sp.symbols("P", integer=True, real=True)


# SD-011
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 01:43:13 +0800
# 最近一次运行成功时间: 2026-03-16 01:43:13 +0800
# 功能说明: 验证 sympy.Symbol 带显式假设时保持原样。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_symbol_with_assumption_kept
# 对应功能实现文件路径: python/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_symbol_with_assumption_kept() -> None:
    sym = sp.symbols("Q", integer=False)
    dim = SymbolDim(sym)
    assert dim.get_symbol() is sym
    assert dim.get_symbol().is_integer is False


# SD-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 01:43:13 +0800
# 最近一次运行成功时间: 2026-03-16 01:43:13 +0800
# 功能说明: 验证算术与比较的非法类型触发 TypeError。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_invalid_types_raise
# 对应功能实现文件路径: python/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_invalid_types_raise() -> None:
    dim = SymbolDim(3)
    with pytest.raises(TypeError):
        _ = dim + 1.0
    with pytest.raises(TypeError):
        _ = 1.0 + dim
    with pytest.raises(TypeError):
        _ = dim == 1.0


# SD-008
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 01:43:13 +0800
# 最近一次运行成功时间: 2026-03-16 01:43:13 +0800
# 功能说明: 验证 get_symbol 与 repr 的一致性。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_get_symbol_and_repr
# 对应功能实现文件路径: python/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_get_symbol_and_repr() -> None:
    dim = SymbolDim("N")
    assert repr(dim) == str(dim.get_symbol())
