"""symbol_dim tests.

创建者: 小李飞刀
最后一次更改: 咯咯咯

功能说明:
- 覆盖 SymbolDim 构造、运算、比较、动态性判断与错误分支。

使用示例:
- pytest -q test/symbol_variable/test_symbol_dim.py

关联文件:
- 功能实现: kernel_gen/symbol_variable/symbol_dim.py
- Spec 文档: spec/symbol_variable/symbol_dim.md
- 测试文件: test/symbol_variable/test_symbol_dim.py

当前覆盖率信息: 100%（2026-03-22 13:32:35 +0800）
覆盖率命令: pytest -q --cov=kernel_gen.symbol_variable.symbol_dim --cov-report=term-missing test/symbol_variable/test_symbol_dim.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import sympy as sp
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.symbol_variable.symbol_dim import SymbolDim


# SD-001
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-22 13:32:35 +0800
# 最近一次运行成功时间: 2026-03-22 13:32:35 +0800
# 测试目的: 验证 int 输入可构造 SymbolDim。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_init_accepts_int
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_init_accepts_int() -> None:
    dim = SymbolDim(8)
    assert dim.get_symbol() == sp.Integer(8)
    assert repr(dim) == "8"


# SD-002
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-22 13:32:35 +0800
# 最近一次运行成功时间: 2026-03-22 13:32:35 +0800
# 测试目的: 验证 str 符号输入可构造 SymbolDim，非纯数字字符串按符号名处理。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_init_accepts_symbol_string
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_init_accepts_symbol_string() -> None:
    dim = SymbolDim("N")
    plus_dim = SymbolDim("+1")
    float_dim = SymbolDim("3.14")
    assert dim.get_symbol() == sp.symbols("N", integer=True, real=True)
    assert plus_dim.get_symbol() == sp.symbols("+1", integer=True, real=True)
    assert float_dim.get_symbol() == sp.symbols("3.14", integer=True, real=True)


# SD-003
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-22 13:32:35 +0800
# 最近一次运行成功时间: 2026-03-22 13:32:35 +0800
# 测试目的: 验证 sympy.Basic 输入可构造 SymbolDim。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_init_accepts_sympy_basic
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_init_accepts_sympy_basic() -> None:
    sym_dim = SymbolDim(sp.symbols("M"))
    normalized = SymbolDim(sp.Symbol("P"))
    expr_dim = SymbolDim(sp.Symbol("K") + 1)
    assert sym_dim.get_symbol() == sp.symbols("M", integer=True, real=True)
    assert normalized.get_symbol() == sp.symbols("P", integer=True, real=True)
    assert expr_dim.get_symbol() == sp.Symbol("K") + 1


# SD-004
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-22 13:32:35 +0800
# 最近一次运行成功时间: 2026-03-22 13:32:35 +0800
# 测试目的: 验证加减乘除运算返回 SymbolDim。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_arithmetic_ops
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_dim.py
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
    rev_add = 1 + dim
    rev_sub = 10 - dim
    rev_mul = 2 * dim
    rev_div = "K" / dim

    assert isinstance(add_res, SymbolDim)
    assert isinstance(sub_res, SymbolDim)
    assert isinstance(mul_res, SymbolDim)
    assert isinstance(div_res, SymbolDim)
    assert isinstance(sym_res, SymbolDim)
    assert isinstance(rev_add, SymbolDim)
    assert isinstance(rev_sub, SymbolDim)
    assert isinstance(rev_mul, SymbolDim)
    assert isinstance(rev_div, SymbolDim)

    assert add_res.get_symbol() == sp.symbols("N", integer=True, real=True) + sp.Integer(2)
    assert sub_res.get_symbol() == sp.symbols("N", integer=True, real=True) - sp.symbols(
        "M", integer=True, real=True
    )
    assert mul_res.get_symbol() == sp.symbols("N", integer=True, real=True) * sp.Integer(3)
    assert div_res.get_symbol() == sp.symbols("N", integer=True, real=True) / sp.Integer(4)
    assert sym_res.get_symbol() == sp.symbols("N", integer=True, real=True) + sp.symbols(
        "K", integer=True, real=True
    )
    assert rev_add.get_symbol() == sp.Integer(1) + sp.symbols("N", integer=True, real=True)
    assert rev_sub.get_symbol() == sp.Integer(10) - sp.symbols("N", integer=True, real=True)
    assert rev_mul.get_symbol() == sp.Integer(2) * sp.symbols("N", integer=True, real=True)
    assert rev_div.get_symbol() == sp.symbols("K", integer=True, real=True) / sp.symbols(
        "N", integer=True, real=True
    )


# SD-005
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-22 13:32:35 +0800
# 最近一次运行成功时间: 2026-03-22 13:32:35 +0800
# 测试目的: 验证比较等价性返回 bool。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_equality
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_equality() -> None:
    assert SymbolDim(4) == 4
    assert SymbolDim("N") == "N"
    assert SymbolDim("N") == SymbolDim("N")
    assert SymbolDim(sp.symbols("M")) == "M"
    assert SymbolDim("N") == sp.Symbol("N")


# SD-006
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-22 13:32:35 +0800
# 最近一次运行成功时间: 2026-03-22 13:32:35 +0800
# 测试目的: 验证动态性判断。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_is_dynamic
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_is_dynamic() -> None:
    assert SymbolDim(8).is_dynamic() is False
    assert SymbolDim("N").is_dynamic() is True


# SD-007
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-22 13:32:35 +0800
# 最近一次运行成功时间: 2026-03-22 13:32:35 +0800
# 测试目的: 验证纯数字字符串输入抛 ValueError。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_numeric_string_rejected
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_numeric_string_rejected() -> None:
    for value in ["12", " 12 ", "１２", "٠١٢"]:
        with pytest.raises(ValueError):
            SymbolDim(value)
    dim = SymbolDim("N")
    for value in ["12", " 12 ", "１２", "٠١٢"]:
        with pytest.raises(ValueError):
            _ = dim + value
    with pytest.raises(ValueError):
        _ = "12" / dim
    with pytest.raises(ValueError):
        _ = dim == "12"


# SD-008
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-22 13:32:35 +0800
# 最近一次运行成功时间: 2026-03-22 13:32:35 +0800
# 测试目的: 验证空白字符串输入抛 ValueError。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_blank_string_rejected
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_blank_string_rejected() -> None:
    for value in ["", "   ", "\t"]:
        with pytest.raises(ValueError):
            SymbolDim(value)
    dim = SymbolDim("N")
    for value in [" ", "\t"]:
        with pytest.raises(ValueError):
            _ = dim + value
    with pytest.raises(ValueError):
        _ = dim == " "


# SD-009
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-22 13:32:35 +0800
# 最近一次运行成功时间: 2026-03-22 13:32:35 +0800
# 测试目的: 验证非法类型输入抛 TypeError。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_invalid_type_rejected
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_invalid_type_rejected() -> None:
    dim = SymbolDim(3)
    with pytest.raises(TypeError):
        SymbolDim(object())
    with pytest.raises(TypeError):
        _ = dim + 1.0
    with pytest.raises(TypeError):
        _ = 1.0 + dim
    with pytest.raises(TypeError):
        _ = dim == 1.0
