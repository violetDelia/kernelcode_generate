"""symbol_dim tests.

创建者: 小李飞刀
最后一次更改: OpenAI Codex

功能说明:
- 覆盖 SymbolDim 的构造、公开值格式化、算术、比较和异常分支。

使用示例:
- pytest -q test/symbol_variable/test_symbol_dim.py

关联文件:
- 功能实现: kernel_gen/symbol_variable/symbol_dim.py
- Spec 文档: spec/symbol_variable/symbol_dim.md
- 测试文件: test/symbol_variable/test_symbol_dim.py
"""

from __future__ import annotations

import sympy as sp
import pytest

from kernel_gen.symbol_variable.symbol_dim import SymbolDim


def _sym(name: str) -> sp.Symbol:
    """构造测试中复用的标准符号。"""
    return sp.symbols(name, integer=True, real=True)


def test_init_accepts_supported_inputs() -> None:
    int_dim = SymbolDim(8)
    str_dim = SymbolDim(" N ")
    named_dim = SymbolDim("BLOCK_M1")
    sym_dim = SymbolDim(sp.Symbol("M"))
    expr_dim = SymbolDim(sp.Symbol("K") + 1)

    assert int_dim.is_dynamic() is False
    assert int_dim.get_value() == 8
    assert int_dim.get_symbol() == sp.Integer(8)
    assert repr(int_dim) == "8"

    assert str_dim.is_dynamic() is True
    assert str_dim.get_symbol() == _sym("N")
    assert str_dim.get_value() == "N"
    assert named_dim.get_symbol() == _sym("BLOCK_M1")
    assert sym_dim.get_symbol() == _sym("M")
    assert expr_dim.get_symbol() == _sym("K") + 1
    assert expr_dim.get_symbol().free_symbols == {_sym("K")}


@pytest.mark.parametrize("value", ["12", " 12 ", "１２", "٠١٢", "3.14", ".5", "1e3", "+1", "-2"])
def test_numeric_string_rejected(value: str) -> None:
    dim = SymbolDim("N")
    ops = [
        lambda operand: dim + operand,
        lambda operand: operand + dim,
        lambda operand: dim - operand,
        lambda operand: operand - dim,
        lambda operand: dim * operand,
        lambda operand: operand * dim,
        lambda operand: dim / operand,
        lambda operand: operand / dim,
        lambda operand: dim // operand,
        lambda operand: operand // dim,
        lambda operand: dim == operand,
    ]

    with pytest.raises(ValueError):
        SymbolDim(value)

    for op in ops:
        with pytest.raises(ValueError):
            op(value)


@pytest.mark.parametrize("value", ["", "   ", "\t"])
def test_blank_string_rejected_on_constructor(value: str) -> None:
    with pytest.raises(ValueError):
        SymbolDim(value)


def test_blank_string_rejected_on_operands_and_compare() -> None:
    dim = SymbolDim("N")

    for value in [" ", "\t"]:
        with pytest.raises(ValueError):
            _ = dim + value

    with pytest.raises(ValueError):
        _ = dim == " "


def test_invalid_type_and_float_constructor_rejected() -> None:
    float_expr = _sym("F") + sp.Float(0.5)

    with pytest.raises(TypeError):
        SymbolDim(object())

    for value in [1.5, -2.25, 0.5, sp.Float(1.5), float_expr]:
        with pytest.raises(NotImplementedError):
            SymbolDim(value)


def test_invalid_type_and_float_operands_rejected() -> None:
    dim = SymbolDim(3)
    float_expr = _sym("K") + sp.Float(0.5)
    float_operands = [1.5, -2.25, 0.5, sp.Float(1.5), float_expr]
    invalid_ops = [
        lambda operand: dim + operand,
        lambda operand: operand + dim,
        lambda operand: dim - operand,
        lambda operand: operand - dim,
        lambda operand: dim * operand,
        lambda operand: operand * dim,
        lambda operand: dim / operand,
        lambda operand: operand / dim,
        lambda operand: dim // operand,
        lambda operand: operand // dim,
    ]

    with pytest.raises(TypeError):
        _ = dim + object()
    with pytest.raises(TypeError):
        _ = object() - dim
    with pytest.raises(TypeError):
        _ = dim == 1.0

    for operand in float_operands:
        for op in invalid_ops:
            with pytest.raises(NotImplementedError):
                op(operand)


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        (lambda dim: dim + 2, _sym("N") + sp.Integer(2)),
        (lambda dim: dim - "M", _sym("N") - _sym("M")),
        (lambda dim: dim * 3, _sym("N") * sp.Integer(3)),
        (
            lambda dim: dim / 4,
            sp.Mul(_sym("N"), sp.Pow(sp.Integer(4), -1, evaluate=False), evaluate=False),
        ),
        (
            lambda dim: dim // 5,
            sp.floor(sp.Mul(_sym("N"), sp.Pow(sp.Integer(5), -1, evaluate=False), evaluate=False)),
        ),
        (lambda dim: dim + sp.Symbol("K"), _sym("N") + _sym("K")),
        (lambda dim: 1 + dim, sp.Integer(1) + _sym("N")),
        (lambda dim: 10 - dim, sp.Integer(10) - _sym("N")),
        (lambda dim: 2 * dim, sp.Integer(2) * _sym("N")),
        (
            lambda dim: "K" / dim,
            sp.Mul(_sym("K"), sp.Pow(_sym("N"), -1, evaluate=False), evaluate=False),
        ),
        (
            lambda dim: 9 // dim,
            sp.floor(sp.Mul(sp.Integer(9), sp.Pow(_sym("N"), -1, evaluate=False), evaluate=False)),
        ),
    ],
)
def test_arithmetic_ops_return_expected_symbols(expr, expected: sp.Basic) -> None:
    result = expr(SymbolDim("N"))
    assert isinstance(result, SymbolDim)
    assert result.get_symbol() == expected


def test_equality_and_dynamic_detection() -> None:
    assert SymbolDim(4) == 4
    assert SymbolDim("N") == "N"
    assert SymbolDim("N") == SymbolDim("N")
    assert SymbolDim(sp.symbols("M")) == "M"
    assert SymbolDim("N") == sp.Symbol("N")
    assert SymbolDim(8).is_dynamic() is False
    assert SymbolDim("N").is_dynamic() is True


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
    assert add_expr.get_value() == 7
    assert sub_expr.get_value() == 5
    assert mul_expr.get_value() == 15
    assert div_expr.get_value() == 9 / 4
    assert floordiv_expr.get_value() == 9 // 4


def test_dynamic_mixed_add_sub_mul_semantics() -> None:
    add_expr = SymbolDim(2) + SymbolDim("N")
    sub_expr = SymbolDim(4) - SymbolDim("N")
    mul_expr = SymbolDim(3) * SymbolDim("N")
    chain_expr = SymbolDim("A") - SymbolDim("B") - SymbolDim("C")

    assert add_expr.is_dynamic() is True
    assert sub_expr.is_dynamic() is True
    assert mul_expr.is_dynamic() is True
    assert add_expr.get_value() == "N + 2"
    assert sub_expr.get_value() == "4 - N"
    assert mul_expr.get_value() == "3*N"
    assert chain_expr == SymbolDim("A") - SymbolDim("B") - SymbolDim("C")
    assert repr(chain_expr) == "A - B - C"
    assert chain_expr.get_value() == "A - B - C"


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
    assert dynamic_expr.get_value() == "9/N"
    assert chain_expr == SymbolDim("A") / SymbolDim("B") / SymbolDim(3)
    assert chain_expr != reordered_expr
    assert repr(chain_expr) == "(A/B)/3"
    assert repr(reordered_expr) == "(A/3)/B"
    assert str(chain_expr.get_symbol()) == "(A/B)/3"
    assert str(reordered_expr.get_symbol()) == "(A/3)/B"
    assert chain_expr.get_value() == "A/(3*B)"
    assert reordered_expr.get_value() == "A/(B*3)"
    assert repr(chain_expr) != chain_expr.get_value()
    assert chain_expr.get_value() != reordered_expr.get_value()
    assert same_expr.get_symbol() == sp.Integer(1)
    assert same_expr.get_value() == 1
    assert reducible_symbol_expr.get_symbol() == _sym("A")
    assert reducible_symbol_expr.get_value() == "A"
    assert reducible_static_factor_expr.get_symbol() == _sym("A")
    assert reducible_static_factor_expr.get_value() == "A"


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
    assert dynamic_expr.get_value() == "9 // N"
    assert chain_expr == SymbolDim("A") // SymbolDim("B") // SymbolDim(3)
    assert chain_expr != reordered_expr
    assert repr(chain_expr) == "floor(floor(A/B)/3)"
    assert repr(reordered_expr) == "floor(floor(A/3)/B)"
    assert str(chain_expr.get_symbol()) == "floor(floor(A/B)/3)"
    assert str(reordered_expr.get_symbol()) == "floor(floor(A/3)/B)"
    assert chain_expr.get_value() == "(A // B) // 3"
    assert reordered_expr.get_value() == "(A // 3) // B"
    assert chain_expr.get_value() != reordered_expr.get_value()
    assert same_expr.get_symbol() == sp.Integer(1)
    assert same_expr.get_value() == 1
    assert reducible_symbol_expr.get_symbol() == _sym("A")
    assert reducible_symbol_expr.get_value() == "A"
    assert reducible_static_factor_expr.get_symbol() == _sym("A")
    assert reducible_static_factor_expr.get_value() == "A"


def test_public_text_keeps_slashslash_semantics() -> None:
    expr = (SymbolDim("N") // SymbolDim("S")) + 1
    mul_expr = SymbolDim("A") * expr

    assert str(expr) == "N // S + 1"
    assert mul_expr.get_value() == "A*(N // S + 1)"


def test_mixed_expression_get_value_semantics() -> None:
    expr = SymbolDim(2) + SymbolDim("A") - SymbolDim(3) * SymbolDim("B") / SymbolDim(5)

    assert expr.is_dynamic() is True
    assert expr.get_value() == (
        SymbolDim(2) + SymbolDim("A") - SymbolDim(3) * SymbolDim("B") / SymbolDim(5)
    ).get_value()
