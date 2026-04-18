"""symbol_dim tests.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 SymbolDim 构造、运算、比较、动态性判断与错误分支。

使用示例:
- pytest -q test/symbol_variable/test_symbol_dim.py

关联文件:
- 功能实现: kernel_gen/symbol_variable/symbol_dim.py
- Spec 文档: spec/symbol_variable/symbol_dim.md
- 测试文件: test/symbol_variable/test_symbol_dim.py

覆盖率信息:
- 当前覆盖率: `99%`（`kernel_gen.symbol_variable.symbol_dim`，2026-04-09 +0800）
- 达标判定: 已达到 `95%` 覆盖率达标线。

覆盖率命令:
- `pytest -q --cov=kernel_gen.symbol_variable.symbol_dim --cov-report=term-missing --cov-fail-under=95 test/symbol_variable/test_symbol_dim.py`
"""

from __future__ import annotations

import sympy as sp
import pytest

from kernel_gen.symbol_variable.symbol_dim import SymbolDim


# SD-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 02:19:46 +0800
# 最近一次运行成功时间: 2026-04-06 02:19:46 +0800
# 测试目的: 验证 int 输入可构造 SymbolDim。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_init_accepts_int
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_init_accepts_int() -> None:
    dim = SymbolDim(8)
    assert dim.is_dynamic() is False
    assert isinstance(dim.get_value(), int)
    assert dim.get_value() == 8
    assert dim.get_symbol() == sp.Integer(8)
    assert repr(dim) == "8"


# SD-002
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-06 02:19:46 +0800
# 最近一次运行成功时间: 2026-04-06 02:19:46 +0800
# 测试目的: 验证非数值字面量字符串会按符号名语义构造 SymbolDim。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_init_accepts_symbol_string
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_init_accepts_symbol_string() -> None:
    dim = SymbolDim("N")
    spaced_dim = SymbolDim(" N ")
    named_dim = SymbolDim("BLOCK_M1")
    assert dim.is_dynamic() is True
    assert dim.get_symbol() == sp.symbols("N", integer=True, real=True)
    assert dim.get_value() == "N"
    assert spaced_dim.get_symbol() == sp.symbols("N", integer=True, real=True)
    assert named_dim.get_symbol() == sp.symbols("BLOCK_M1", integer=True, real=True)


# SD-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 02:19:46 +0800
# 最近一次运行成功时间: 2026-04-06 02:19:46 +0800
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
    assert expr_dim.get_symbol() == sp.symbols("K", integer=True, real=True) + 1
    assert expr_dim.get_symbol().free_symbols == {sp.symbols("K", integer=True, real=True)}


# SD-004
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-23 22:10:59 +0800
# 最近一次运行成功时间: 2026-03-23 22:10:59 +0800
# 测试目的: 验证加减乘除与整除运算返回 SymbolDim。
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
    floordiv_res = dim // 5
    sym_res = dim + sym_operand
    rev_add = 1 + dim
    rev_sub = 10 - dim
    rev_mul = 2 * dim
    rev_div = "K" / dim
    rev_floordiv = 9 // dim

    assert isinstance(add_res, SymbolDim)
    assert isinstance(sub_res, SymbolDim)
    assert isinstance(mul_res, SymbolDim)
    assert isinstance(div_res, SymbolDim)
    assert isinstance(floordiv_res, SymbolDim)
    assert isinstance(sym_res, SymbolDim)
    assert isinstance(rev_add, SymbolDim)
    assert isinstance(rev_sub, SymbolDim)
    assert isinstance(rev_mul, SymbolDim)
    assert isinstance(rev_div, SymbolDim)
    assert isinstance(rev_floordiv, SymbolDim)

    assert add_res.get_symbol() == sp.symbols("N", integer=True, real=True) + sp.Integer(2)
    assert sub_res.get_symbol() == sp.symbols("N", integer=True, real=True) - sp.symbols(
        "M", integer=True, real=True
    )
    assert mul_res.get_symbol() == sp.symbols("N", integer=True, real=True) * sp.Integer(3)
    assert div_res.get_symbol() == sp.Mul(
        sp.symbols("N", integer=True, real=True),
        sp.Pow(sp.Integer(4), -1, evaluate=False),
        evaluate=False,
    )
    assert floordiv_res.get_symbol() == sp.floor(
        sp.Mul(
            sp.symbols("N", integer=True, real=True),
            sp.Pow(sp.Integer(5), -1, evaluate=False),
            evaluate=False,
        )
    )
    assert sym_res.get_symbol() == sp.symbols("N", integer=True, real=True) + sp.symbols(
        "K", integer=True, real=True
    )
    assert rev_add.get_symbol() == sp.Integer(1) + sp.symbols("N", integer=True, real=True)
    assert rev_sub.get_symbol() == sp.Integer(10) - sp.symbols("N", integer=True, real=True)
    assert rev_mul.get_symbol() == sp.Integer(2) * sp.symbols("N", integer=True, real=True)
    assert rev_div.get_symbol() == sp.Mul(
        sp.symbols("K", integer=True, real=True),
        sp.Pow(sp.symbols("N", integer=True, real=True), -1, evaluate=False),
        evaluate=False,
    )
    assert rev_floordiv.get_symbol() == sp.floor(
        sp.Mul(
            sp.Integer(9),
            sp.Pow(sp.symbols("N", integer=True, real=True), -1, evaluate=False),
            evaluate=False,
        )
    )


# SD-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 22:10:59 +0800
# 最近一次运行成功时间: 2026-03-23 22:10:59 +0800
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
# 最近一次运行测试时间: 2026-03-23 22:10:59 +0800
# 最近一次运行成功时间: 2026-03-23 22:10:59 +0800
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
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 22:10:59 +0800
# 最近一次运行成功时间: 2026-03-23 22:10:59 +0800
# 测试目的: 验证数值字面量字符串在构造、算术操作数与比较路径上统一抛 ValueError。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_numeric_string_rejected
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_numeric_string_rejected() -> None:
    values = ["12", " 12 ", "１２", "٠١٢", "3.14", ".5", "1e3", "+1", "-2"]

    for value in values:
        with pytest.raises(ValueError):
            SymbolDim(value)

    dim = SymbolDim("N")

    for value in values:
        with pytest.raises(ValueError):
            _ = dim + value
        with pytest.raises(ValueError):
            _ = value + dim
        with pytest.raises(ValueError):
            _ = dim - value
        with pytest.raises(ValueError):
            _ = value - dim
        with pytest.raises(ValueError):
            _ = dim * value
        with pytest.raises(ValueError):
            _ = value * dim
        with pytest.raises(ValueError):
            _ = dim / value
        with pytest.raises(ValueError):
            _ = value / dim
        with pytest.raises(ValueError):
            _ = dim // value
        with pytest.raises(ValueError):
            _ = value // dim
        with pytest.raises(ValueError):
            _ = dim == value


# SD-008
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-23 22:10:59 +0800
# 最近一次运行成功时间: 2026-03-23 22:10:59 +0800
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
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 02:19:46 +0800
# 最近一次运行成功时间: 2026-04-06 02:19:46 +0800
# 测试目的: 验证非浮点非法类型输入、操作数与比较抛 TypeError。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_invalid_type_rejected
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_invalid_type_rejected() -> None:
    dim = SymbolDim(3)
    with pytest.raises(TypeError):
        SymbolDim(object())
    with pytest.raises(TypeError):
        _ = dim + object()
    with pytest.raises(TypeError):
        _ = object() - dim
    with pytest.raises(TypeError):
        _ = dim == 1.0


# SD-010
# 创建者: 我不是牛马
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 02:19:46 +0800
# 最近一次运行成功时间: 2026-04-06 02:19:46 +0800
# 测试目的: 验证静态整数之间的加减乘结果保持非动态，且 get_value 可直接与 Python 结果比较。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_static_arithmetic_get_value_semantics
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_static_arithmetic_get_value_semantics() -> None:
    add_expr = SymbolDim(3) + SymbolDim(4)
    sub_expr = SymbolDim(9) - SymbolDim(4)
    mul_expr = SymbolDim(3) * SymbolDim(5)
    div_expr = SymbolDim(9) / SymbolDim(4)
    floordiv_expr = SymbolDim(9) // SymbolDim(4)

    assert add_expr.is_dynamic() is False
    assert sub_expr.is_dynamic() is False
    assert mul_expr.is_dynamic() is False
    assert div_expr.is_dynamic() is False
    assert floordiv_expr.is_dynamic() is False
    assert add_expr.get_value() == 3 + 4
    assert sub_expr.get_value() == 9 - 4
    assert mul_expr.get_value() == 3 * 5
    assert div_expr.get_value() == 9 / 4
    assert floordiv_expr.get_value() == 9 // 4


# SD-011
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-23 22:27:41 +0800
# 最近一次运行成功时间: 2026-03-23 22:27:41 +0800
# 测试目的: 验证静态整数与动态符号混合参与加减乘时结果保持动态，且链式顺序可稳定比较。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_dynamic_mixed_add_sub_mul_semantics
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_dynamic_mixed_add_sub_mul_semantics() -> None:
    add_expr = SymbolDim(2) + SymbolDim("N")
    sub_expr = SymbolDim(4) - SymbolDim("N")
    mul_expr = SymbolDim(3) * SymbolDim("N")
    chain_expr = SymbolDim("A") - SymbolDim("B") - SymbolDim("C")

    assert add_expr.is_dynamic() is True
    assert sub_expr.is_dynamic() is True
    assert mul_expr.is_dynamic() is True
    assert add_expr.get_value() == str(sp.Integer(2) + sp.symbols("N", integer=True, real=True))
    assert sub_expr.get_value() == str(sp.Integer(4) - sp.symbols("N", integer=True, real=True))
    assert mul_expr.get_value() == str(sp.Integer(3) * sp.symbols("N", integer=True, real=True))
    assert chain_expr == SymbolDim("A") - SymbolDim("B") - SymbolDim("C")
    assert repr(chain_expr) == "A - B - C"
    assert chain_expr.get_value() == str(
        sp.symbols("A", integer=True, real=True)
        - sp.symbols("B", integer=True, real=True)
        - sp.symbols("C", integer=True, real=True)
    )


# SD-012
# 创建者: 我不是牛马
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 22:27:41 +0800
# 最近一次运行成功时间: 2026-03-23 22:27:41 +0800
# 测试目的: 验证真除法在静态与动态表达式下的 get_value 语义与链式结合顺序。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_truediv_get_value_and_order_semantics
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_truediv_get_value_and_order_semantics() -> None:
    static_expr = SymbolDim(9) / SymbolDim(4)
    dynamic_expr = SymbolDim(9) / SymbolDim("N")
    chain_expr = SymbolDim("A") / SymbolDim("B") / SymbolDim(3)
    reordered_expr = SymbolDim("A") / SymbolDim(3) / SymbolDim("B")
    same_expr = SymbolDim("A") / SymbolDim("A")
    reducible_symbol_expr = (SymbolDim("A") * SymbolDim("B")) / SymbolDim("B")
    reducible_static_factor_expr = (SymbolDim("A") * 3) / 3

    assert static_expr.is_dynamic() is False
    assert dynamic_expr.is_dynamic() is True
    assert static_expr.get_value() == 9 / 4
    assert dynamic_expr.get_value() == (SymbolDim(9) / SymbolDim("N")).get_value()
    assert chain_expr == SymbolDim("A") / SymbolDim("B") / SymbolDim(3)
    assert chain_expr != reordered_expr
    assert chain_expr.get_value() == "A/(3*B)"
    assert chain_expr.get_value() != reordered_expr.get_value()
    assert same_expr.get_symbol() == sp.Integer(1)
    assert same_expr.get_value() == 1
    assert reducible_symbol_expr.get_symbol() == sp.symbols("A", integer=True, real=True)
    assert reducible_symbol_expr.get_value() == "A"
    assert reducible_static_factor_expr.get_symbol() == sp.symbols("A", integer=True, real=True)
    assert reducible_static_factor_expr.get_value() == "A"


# SD-013
# 创建者: 我不是牛马
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 22:27:41 +0800
# 最近一次运行成功时间: 2026-03-23 22:27:41 +0800
# 测试目的: 验证整除在静态与动态表达式下的 get_value 语义与链式结合顺序。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_floordiv_get_value_and_order_semantics
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_floordiv_get_value_and_order_semantics() -> None:
    static_expr = SymbolDim(9) // SymbolDim(4)
    reverse_static_expr = 9 // SymbolDim(4)
    dynamic_expr = SymbolDim(9) // SymbolDim("N")
    chain_expr = SymbolDim("A") // SymbolDim("B") // SymbolDim(3)
    reordered_expr = SymbolDim("A") // SymbolDim(3) // SymbolDim("B")
    same_expr = SymbolDim("A") // SymbolDim("A")
    reducible_symbol_expr = (SymbolDim("A") * SymbolDim("B")) // SymbolDim("B")
    reducible_static_factor_expr = (SymbolDim("A") * 3) // 3

    assert static_expr.is_dynamic() is False
    assert reverse_static_expr.is_dynamic() is False
    assert dynamic_expr.is_dynamic() is True
    assert static_expr.get_value() == 9 // 4
    assert reverse_static_expr.get_value() == 9 // 4
    assert dynamic_expr.get_value() == (SymbolDim(9) // SymbolDim("N")).get_value()
    assert chain_expr == SymbolDim("A") // SymbolDim("B") // SymbolDim(3)
    assert chain_expr != reordered_expr
    assert chain_expr.get_value() != reordered_expr.get_value()
    assert same_expr.get_symbol() == sp.Integer(1)
    assert same_expr.get_value() == 1
    assert reducible_symbol_expr.get_symbol() == sp.symbols("A", integer=True, real=True)
    assert reducible_symbol_expr.get_value() == "A"
    assert reducible_static_factor_expr.get_symbol() == sp.symbols("A", integer=True, real=True)
    assert reducible_static_factor_expr.get_value() == "A"


# SD-014
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-23 22:27:41 +0800
# 最近一次运行成功时间: 2026-03-23 22:27:41 +0800
# 测试目的: 验证混合表达式的动态性传播与 get_value 表达式比较稳定。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_mixed_expression_get_value_semantics
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_mixed_expression_get_value_semantics() -> None:
    expr = SymbolDim(2) + SymbolDim("A") - SymbolDim(3) * SymbolDim("B") / SymbolDim(5)

    assert expr.is_dynamic() is True
    assert expr.get_value() == (
        SymbolDim(2)
        + SymbolDim("A")
        - SymbolDim(3) * SymbolDim("B") / SymbolDim(5)
    ).get_value()


# SD-015
# 创建者: 我不是牛马
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 03:02:30 +0800
# 最近一次运行成功时间: 2026-04-06 03:02:30 +0800
# 测试目的: 验证 Python float、sympy.Float 与含浮点表达式的构造输入均抛出 NotImplementedError。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_float_constructor_rejected
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_float_constructor_rejected() -> None:
    float_expr = sp.symbols("F", integer=True, real=True) + sp.Float(0.5)
    for value in [1.5, -2.25, 0.5, sp.Float(1.5), float_expr]:
        with pytest.raises(NotImplementedError):
            SymbolDim(value)


# SD-016
# 创建者: 我不是牛马
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 03:02:30 +0800
# 最近一次运行成功时间: 2026-04-06 03:02:30 +0800
# 测试目的: 验证 Python float、sympy.Float 与含浮点表达式在正向与反向加减乘除整除中均抛出 NotImplementedError。
# 使用示例: pytest -q test/symbol_variable/test_symbol_dim.py -k test_float_operands_rejected
# 对应功能实现文件路径: kernel_gen/symbol_variable/symbol_dim.py
# 对应 spec 文件路径: spec/symbol_variable/symbol_dim.md
# 对应测试文件路径: test/symbol_variable/test_symbol_dim.py
def test_float_operands_rejected() -> None:
    dim = SymbolDim(3)
    float_expr = sp.symbols("K", integer=True, real=True) + sp.Float(0.5)

    for operand in [1.5, -2.25, 0.5, sp.Float(1.5), float_expr]:
        with pytest.raises(NotImplementedError):
            _ = dim + operand
        with pytest.raises(NotImplementedError):
            _ = operand + dim
        with pytest.raises(NotImplementedError):
            _ = dim - operand
        with pytest.raises(NotImplementedError):
            _ = operand - dim
        with pytest.raises(NotImplementedError):
            _ = dim * operand
        with pytest.raises(NotImplementedError):
            _ = operand * dim
        with pytest.raises(NotImplementedError):
            _ = dim / operand
        with pytest.raises(NotImplementedError):
            _ = operand / dim
        with pytest.raises(NotImplementedError):
            _ = dim // operand
        with pytest.raises(NotImplementedError):
            _ = operand // dim
