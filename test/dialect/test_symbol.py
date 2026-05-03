"""symbol dialect tests.


功能说明:
- 覆盖 symbol dialect 的整数符号 attribute/type、verifier、parse/print 与错误路径。

使用示例:
- pytest -q test/dialect/test_symbol.py

覆盖率:
- 覆盖率命令: pytest -q --cov=kernel_gen.dialect.symbol --cov-report=term-missing test/dialect/test_symbol.py
- 覆盖率结果: 80%（2026-04-01 09:35:37 +0800）

关联文件:
- 功能实现: kernel_gen/dialect/symbol.py
- Spec 文档: spec/dialect/symbol.md
- 测试文件: test/dialect/test_symbol.py
"""

from __future__ import annotations

from io import StringIO
import random
import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects.arith import Arith
from xdsl.dialects.builtin import ArrayAttr, Builtin, IndexType, IntAttr, IntegerType, StringAttr, bf16, f16, f32, f64, i1, i8, i16, i32, i64
from xdsl.dialects.test import Test, TestOp as _TestOp
from xdsl.ir import Attribute, Block, Operation, Region
from xdsl.folder import Folder
from xdsl.parser import Parser
from xdsl.printer import Printer
from xdsl.utils.exceptions import ParseError, VerifyException

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.nn import Nn, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import (
    Symbol,
    SymbolAddOp,
    SymbolCastOp,
    SymbolConstOp,
    SymbolDivOp,
    SymbolDimType,
    SymbolEqOp,
    SymbolExprAttr,
    SymbolFloorDivOp,
    SymbolGeOp,
    SymbolGetDimOp,
    SymbolGetStrideOp,
    SymbolForOp,
    SymbolGtOp,
    SymbolIterAttr,
    SymbolLeOp,
    SymbolLtOp,
    SymbolMulOp,
    SymbolMinOp,
    SymbolNeOp,
    SymbolSubOp,
    SymbolIterType,
    SymbolYieldOp,
    SymbolToIntOp,
    SymbolToFloatOp,
    SymbolPtrType,
    SymbolValueType,
)
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


def _build_context() -> Context:
    """构造加载 builtin/symbol 的解析上下文。


    功能说明:
    - 为 symbol attribute/type 的 parse/print 测试提供统一 context。

    使用示例:
    - _build_context()

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    ctx = Context()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(Arith)
    ctx.load_dialect(Test)
    ctx.load_dialect(Nn)
    ctx.load_dialect(Symbol)
    return ctx


def _print_attr(value: Attribute) -> str:
    """打印 attribute 或 type 为文本。"""

    stream = StringIO()
    printer = Printer(stream=stream)
    printer.print_attribute(value)
    return stream.getvalue()


def _print_op(op: Operation) -> str:
    """打印 operation 为文本。"""

    stream = StringIO()
    printer = Printer(stream=stream)
    printer.print_op(op)
    return stream.getvalue()


def _make_space(name: str = "global") -> NnMemorySpaceAttr:
    """构造 nn space attribute。


    功能说明:
    - 为 symbol.get_dim/get_stride 测试提供统一的 `nn.space` 构造。

    使用示例:
    - _make_space()

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    return NnMemorySpaceAttr(StringAttr(name))


def _make_memory_type(shape: list[IntAttr | StringAttr], stride: list[IntAttr | StringAttr]) -> NnMemoryType:
    """构造 nn.memory type。


    功能说明:
    - 为 symbol.get_dim/get_stride 测试构造最小合法 memory type。

    使用示例:
    - _make_memory_type([IntAttr(4)], [IntAttr(1)])

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    return NnMemoryType(ArrayAttr(shape), ArrayAttr(stride), i32, _make_space())


def _make_memory_value(memory_type: NnMemoryType):
    """构造携带 nn.memory type 的测试 SSA value。


    功能说明:
    - 复用 `test.TestOp` 产出 `symbol.get_dim/get_stride` 所需 operand。

    使用示例:
    - _make_memory_value(memory_type)

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    return _TestOp(result_types=[memory_type]).results[0]


def _make_symbol_value(expr: str):
    """构造携带 symbol.int type 的测试 SSA value。


    功能说明:
    - 为 symbol.for 测试复用统一的 symbol.int 操作数构造。

    使用示例:
    - _make_symbol_value("N")

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    return _TestOp(result_types=[SymbolValueType.from_expr(expr)]).results[0]


# TC-SYM-001 / TC-SYM-002 / TC-SYM-009
# 测试目的: 验证 SymbolExprAttr 的基础表达、复合表达与 parse/print round-trip 稳定。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_expr_attr_round_trip() -> None:
    ctx = _build_context()
    for text in ['#symbol.expr<"N">', '#symbol.expr<"M + 1">', '#symbol.expr<"B*K">', '#symbol.expr<"min(T, N - i)">']:
        expr = Parser(ctx, text).parse_attribute()
        assert isinstance(expr, SymbolExprAttr)
        expr.verify()
        assert _print_attr(expr) == text


# TC-SYM-009A
# 测试目的: 验证公开 symbol 表达式只接受小写 `min(lhs, rhs)`，不接受 `Min(lhs, rhs)` 别名。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_expr_attr_rejects_uppercase_min_alias() -> None:
    with pytest.raises(VerifyException, match=r"min\(lhs, rhs\)"):
        SymbolExprAttr.from_expr("Min(T, N - i)").verify()
    with pytest.raises(VerifyException, match=r"min\(lhs, rhs\)"):
        SymbolValueType.from_expr("Min(T, N - i)").verify()


# TC-SYM-003
# 测试目的: 验证空表达式会被 verifier 拒绝。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_expr_attr_rejects_empty_expr() -> None:
    with pytest.raises(VerifyException, match="must not be empty"):
        SymbolExprAttr.from_expr("   ").verify()


# TC-SYM-004 / TC-SYM-005 / TC-SYM-006 / TC-SYM-009
# 测试目的: 验证整数 symbol type 支持具名表达与常量表达，并可稳定 parse/print。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_value_type_round_trip_for_integer_only_semantics() -> None:
    ctx = _build_context()
    for text in ['!symbol.int<"N">', '!symbol.int<"M + 1">', '!symbol.int<"3">', '!symbol.int<"min(T, N - i)">']:
        ty = Parser(ctx, text).parse_attribute()
        assert isinstance(ty, SymbolValueType)
        ty.verify()
        assert _print_attr(ty) == text


# TC-SYM-052
# 功能说明: 验证 symbol.iter 的 parse/print 与 verifier 行为。
# 使用示例: pytest -q test/dialect/test_symbol.py -k test_symbol_iter_type_round_trip
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
# 对应测试文件路径: test/dialect/test_symbol.py
def test_symbol_iter_type_round_trip() -> None:
    ctx = _build_context()
    ty = Parser(ctx, '!symbol.iter<start = "0", end = "index", step = "1">').parse_attribute()
    assert isinstance(ty, SymbolIterType)
    ty.verify()
    assert _print_attr(ty) == '!symbol.iter<start = "0", end = "index", step = "1">'


# TC-SYM-049
# 测试目的: 验证 symbol.const 生成匹配常量的 symbol.int 类型。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_const_op_verify_success() -> None:
    op = SymbolConstOp(3)
    op.verify()
    assert _print_attr(op.result.type) == '!symbol.int<"3">'


# TC-SYM-050
# 测试目的: 验证 symbol.const 的 parse/print round-trip 稳定。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_const_op_round_trip() -> None:
    ctx = _build_context()
    module = Parser(
        ctx,
        """
builtin.module {
  %c0 = symbol.const 0 : !symbol.int<"0">
  %c1 = symbol.const -4 : !symbol.int<"-4">
}
""",
    ).parse_module()

    module.verify()
    printed = _print_op(module)
    assert 'symbol.const 0 : !symbol.int<"0">' in printed
    assert 'symbol.const -4 : !symbol.int<"-4">' in printed


# TC-SYM-052 / TC-SYM-053 / TC-SYM-054 / TC-SYM-055 / TC-SYM-056
# 测试目的: 验证 symbol.add/sub/mul/div/floordiv 的静态整数 fold 会 materialize 为 symbol.const。
# 使用示例: pytest -q test/dialect/test_symbol.py -k test_symbol_binary_arith_fold_constant_operands
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
@pytest.mark.parametrize(
    ("op_factory", "lhs", "rhs", "result_type", "expected"),
    [
        (SymbolAddOp, 2, 3, "5", 5),
        (SymbolSubOp, 7, 4, "3", 3),
        (SymbolMulOp, 6, 5, "30", 30),
        (SymbolDivOp, 6, 3, "2", 2),
        (SymbolFloorDivOp, 7, 3, "2", 2),
        (SymbolMinOp, 7, 3, "3", 3),
    ],
)
def test_symbol_binary_arith_fold_constant_operands(
    op_factory: type[SymbolAddOp],
    lhs: int,
    rhs: int,
    result_type: str,
    expected: int,
) -> None:
    ctx = _build_context()
    folder = Folder(ctx)
    lhs_op = SymbolConstOp(lhs)
    rhs_op = SymbolConstOp(rhs)
    op = op_factory(lhs_op.result, rhs_op.result, SymbolValueType.from_expr(result_type))

    folded = folder.try_fold(op)

    assert folded is not None
    values, new_ops = folded
    assert len(values) == 1
    assert len(new_ops) == 1
    assert isinstance(new_op := new_ops[0], SymbolConstOp)
    assert new_op.value.data == expected
    assert new_op.result.type == SymbolValueType.from_expr(str(expected))


# TC-SYM-057
# 测试目的: 验证静态 folding 不会误折叠含动态 symbol 的二元算术表达式。
# 使用示例: pytest -q test/dialect/test_symbol.py -k test_symbol_binary_arith_fold_rejects_dynamic_operands
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_binary_arith_fold_rejects_dynamic_operands() -> None:
    ctx = _build_context()
    folder = Folder(ctx)
    lhs = _TestOp(result_types=[SymbolValueType.from_expr("N")]).results[0]
    rhs = SymbolConstOp(2).result
    op = SymbolAddOp(lhs, rhs, SymbolValueType.from_expr("N + 2"))

    assert folder.try_fold(op) is None


# TC-SYM-051
# 测试目的: 验证 symbol.const 会拒绝不匹配的结果类型。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_const_op_rejects_mismatched_type() -> None:
    with pytest.raises(VerifyException, match="result type must match value"):
        SymbolConstOp(3, SymbolValueType.from_expr("4")).verify()
    with pytest.raises(VerifyException, match="base attribute symbol.int"):
        SymbolConstOp(3, i32).verify()


# TC-SYM-013 / TC-SYM-014
# 测试目的: 验证 Memory 中的单值 shape/stride 分量进入 IR 时统一复用 symbol dialect 的整数-only 语义。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_memory_scalar_components_round_trip_through_symbol_dialect() -> None:
    mem = Memory(["M", "K", "N"], NumericType.Float32)
    stride_values = mem.stride.get_values()

    stride_expr = SymbolExprAttr.from_expr(str(stride_values[0]))
    dim_type = SymbolValueType.from_expr(str(mem.shape.get_values()[2]))
    unit_type = SymbolValueType.from_expr(str(stride_values[2]))

    stride_expr.verify()
    dim_type.verify()
    unit_type.verify()

    assert _print_attr(stride_expr) == '#symbol.expr<"K*N">'
    assert _print_attr(dim_type) == '!symbol.int<"N">'
    assert _print_attr(unit_type) == '!symbol.int<"1">'


# TC-SYM-007 / TC-SYM-008
# 测试目的: 验证 legacy 宽度整型或缺少表达式的文本不会被当前整数-only symbol type 接受。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_value_type_rejects_unsupported_legacy_text_forms() -> None:
    ctx = _build_context()
    with pytest.raises(ParseError):
        Parser(ctx, '!symbol.int64<"N">').parse_attribute()
    with pytest.raises(ParseError):
        Parser(ctx, "!symbol.int").parse_attribute()


# TC-SYM-010 / TC-SYM-011 / TC-SYM-012
# 测试目的: 验证 symbol type 相等性仅比较整数语义下的表达式内容，不再区分整型宽度。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_value_type_equality_depends_on_expr_only() -> None:
    lhs = SymbolValueType.from_expr("N")
    rhs = SymbolValueType.from_expr("N")
    other = SymbolValueType.from_expr("M")

    assert lhs == rhs
    assert lhs != other
    assert _print_attr(lhs) == '!symbol.int<"N">'


# TC-SYM-058
# 测试目的: 以确定性随机表达式矩阵验证公开 symbol.int 值语义、常量归一化与符号表达 canonical 文本。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_value_type_public_expression_matrix() -> None:
    ctx = _build_context()
    rng = random.Random(20260505)
    cases = [
        ("+4", 4, False, '!symbol.int<"4">'),
        ("-4", -4, False, '!symbol.int<"-4">'),
        ("7 - 4", 3, False, '!symbol.int<"3">'),
        ("2 + 3 * 4", 14, False, '!symbol.int<"14">'),
        ("8 / 2", 4, False, '!symbol.int<"4">'),
        ("7 // 3", 2, False, '!symbol.int<"2">'),
        ("+N", "N", True, '!symbol.int<"+N">'),
        ("N + 1", "N + 1", True, '!symbol.int<"N + 1">'),
        ("N - T", "N - T", True, '!symbol.int<"N - T">'),
        ("N * T", "N*T", True, '!symbol.int<"N * T">'),
        ("-N + M", "M - N", True, '!symbol.int<"-N + M">'),
        ("floor(7)", "7", True, '!symbol.int<"floor(7)">'),
        ("floor(7/N)", "7 // N", True, '!symbol.int<"floor(7/N)">'),
        ("floor((N + 1) / T)", "(N + 1) // T", True, '!symbol.int<"floor((N + 1) / T)">'),
        ("N // 2", "N // 2", True, '!symbol.int<"N // 2">'),
    ]

    for expr, expected_value, expected_symbol, expected_text in rng.sample(cases, k=len(cases)):
        parsed = Parser(ctx, f'!symbol.int<"{expr}">').parse_attribute()
        assert isinstance(parsed, SymbolValueType)
        parsed.verify()
        assert parsed.get_value() == expected_value
        assert parsed.is_symbol() is expected_symbol
        assert _print_attr(parsed) == expected_text


# TC-SYM-061
# 测试目的: 验证公开 symbol.int 对除零和非整除表达式保持非静态符号语义，不误归一为整数常量。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_value_type_public_non_concrete_division_edges() -> None:
    ctx = _build_context()
    cases = ["7 / 0", "7 / 2"]

    for expr in cases:
        parsed = Parser(ctx, f'!symbol.int<"{expr}">').parse_attribute()
        assert isinstance(parsed, SymbolValueType)
        parsed.verify()
        assert parsed.is_symbol()
        assert _print_attr(parsed) == f'!symbol.int<"{expr}">'


# TC-SYM-059
# 测试目的: 验证 symbol.dim 与 symbol.iter 公开构造、字符串化和 parser 兼容边界。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_dim_and_iter_public_constructor_matrix() -> None:
    ctx = _build_context()
    rng = random.Random(20260505)
    for name in rng.sample(["BLOCK_M", "tile_n", "_inner0"], k=3):
        dim_type = SymbolDimType.from_name(name)
        dim_type.verify()
        assert str(dim_type) == f"symbol.dim<{name}>"

    for name, message in [(" ", "must not be empty"), ("1bad", "must match")]:
        with pytest.raises(VerifyException, match=message):
            SymbolDimType.from_name(name)

    iter_attr = SymbolIterAttr.from_bounds("0", "N", "TILE_N")
    iter_type = SymbolIterType.from_attr(iter_attr)
    assert str(iter_type) == "symbol.iter<start=0, end=N, step=TILE_N>"

    legacy = Parser(ctx, '!symbol.iter<"index">').parse_attribute()
    assert isinstance(legacy, SymbolIterType)
    assert _print_attr(legacy) == '!symbol.iter<start = "0", end = "index", step = "1">'

    with pytest.raises(ParseError, match="Expected quoted symbol expression"):
        Parser(ctx, "!symbol.iter<start = 0, end = \"N\", step = \"1\">").parse_attribute()


# TC-SYM-060
# 测试目的: 验证公开 Folder 折叠入口对除零、非整除和结果类型不匹配的稳定拒绝。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_binary_arith_fold_public_rejection_matrix() -> None:
    ctx = _build_context()
    folder = Folder(ctx)
    cases = [
        SymbolDivOp(SymbolConstOp(7).result, SymbolConstOp(0).result, SymbolValueType.from_expr("0")),
        SymbolDivOp(SymbolConstOp(7).result, SymbolConstOp(2).result, SymbolValueType.from_expr("3")),
        SymbolFloorDivOp(SymbolConstOp(7).result, SymbolConstOp(0).result, SymbolValueType.from_expr("0")),
        SymbolAddOp(SymbolConstOp(1).result, SymbolConstOp(2).result, SymbolValueType.from_expr("4")),
        SymbolAddOp(_TestOp(result_types=[i32]).results[0], SymbolConstOp(1).result, SymbolValueType.from_expr("1")),
    ]

    for op in cases:
        assert folder.try_fold(op) is None


# TC-SYM-003 / TC-SYM-007
# 测试目的: 验证非法字符表达式在 attr/type 两条路径都会报 verifier 错误。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_verifier_rejects_illegal_expression_characters() -> None:
    with pytest.raises(VerifyException, match="must contain identifiers"):
        SymbolExprAttr.from_expr("N@2").verify()
    with pytest.raises(VerifyException, match="must contain identifiers"):
        SymbolValueType.from_expr("N@1").verify()
    with pytest.raises(VerifyException, match="must contain identifiers"):
        SymbolExprAttr.from_expr("N +").verify()
    with pytest.raises(VerifyException, match="must contain identifiers"):
        SymbolExprAttr.from_expr("[]").verify()


# TC-SYM-015
# 测试目的: 验证 symbol.add/sub/mul/div/floordiv 在 symbol.int 输入与输出下可通过 verifier。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_arith_ops_verify_success() -> None:
    add_op = SymbolAddOp(_make_symbol_value("M"), _make_symbol_value("1"), SymbolValueType.from_expr("M + 1"))
    sub_op = SymbolSubOp(_make_symbol_value("N"), _make_symbol_value("1"), SymbolValueType.from_expr("N - 1"))
    mul_op = SymbolMulOp(_make_symbol_value("M"), _make_symbol_value("N"), SymbolValueType.from_expr("M*N"))
    div_op = SymbolDivOp(_make_symbol_value("M"), _make_symbol_value("N"), SymbolValueType.from_expr("M / N"))
    floordiv_op = SymbolFloorDivOp(
        _make_symbol_value("M"),
        _make_symbol_value("N"),
        SymbolValueType.from_expr("M // N"),
    )
    min_op = SymbolMinOp(_make_symbol_value("T"), _make_symbol_value("N - i"), SymbolValueType.from_expr("min(T, N - i)"))

    add_op.verify()
    sub_op.verify()
    mul_op.verify()
    div_op.verify()
    floordiv_op.verify()
    min_op.verify()

    assert _print_attr(add_op.result.type) == '!symbol.int<"M + 1">'
    assert _print_attr(sub_op.result.type) == '!symbol.int<"N - 1">'
    assert _print_attr(mul_op.result.type) == '!symbol.int<"M*N">'
    assert _print_attr(div_op.result.type) == '!symbol.int<"M / N">'
    assert _print_attr(floordiv_op.result.type) == '!symbol.int<"M // N">'
    assert _print_attr(min_op.result.type) == '!symbol.int<"min(T, N - i)">'


# TC-SYM-015B
# 测试目的: 验证公开 SymbolDim 运算在乘法操作数含加减表达式时保留操作数边界。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_dim_arithmetic_preserves_operand_precedence() -> None:
    assert (SymbolDim("THO - 1") * SymbolDim("SH")).get_value() == "SH*(THO - 1)"
    assert (SymbolDim("KH - 1") * SymbolDim("DH")).get_value() == "DH*(KH - 1)"
    assert (SymbolDim("N + 1") // SymbolDim("T")).get_value() == "(N + 1) // T"


# TC-SYM-016
# 测试目的: 验证 symbol.add/sub/mul/div/floordiv 的 parse/print round-trip 稳定。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_arith_ops_round_trip() -> None:
    ctx = _build_context()
    module = Parser(
        ctx,
        """
builtin.module {
  %m = "test.op"() : () -> !symbol.int<"M">
  %n = "test.op"() : () -> !symbol.int<"N">
  %one = "test.op"() : () -> !symbol.int<"1">
  %sum = symbol.add %m, %one : !symbol.int<"M">, !symbol.int<"1"> -> !symbol.int<"M + 1">
  %diff = symbol.sub %n, %one : !symbol.int<"N">, !symbol.int<"1"> -> !symbol.int<"N - 1">
  %prod = symbol.mul %m, %n : !symbol.int<"M">, !symbol.int<"N"> -> !symbol.int<"M*N">
  %quot = symbol.div %m, %n : !symbol.int<"M">, !symbol.int<"N"> -> !symbol.int<"M / N">
  %floor = symbol.floordiv %m, %n : !symbol.int<"M">, !symbol.int<"N"> -> !symbol.int<"M // N">
  %tail = symbol.min %m, %n : !symbol.int<"M">, !symbol.int<"N"> -> !symbol.int<"min(M, N)">
}
""",
    ).parse_module()

    module.verify()
    printed = _print_op(module)
    assert "symbol.add %m, %one : !symbol.int<\"M\">, !symbol.int<\"1\"> -> !symbol.int<\"M + 1\">" in printed
    assert "symbol.sub %n, %one : !symbol.int<\"N\">, !symbol.int<\"1\"> -> !symbol.int<\"N - 1\">" in printed
    assert "symbol.mul %m, %n : !symbol.int<\"M\">, !symbol.int<\"N\"> -> !symbol.int<\"M*N\">" in printed
    assert "symbol.div %m, %n : !symbol.int<\"M\">, !symbol.int<\"N\"> -> !symbol.int<\"M / N\">" in printed
    assert "symbol.floordiv %m, %n : !symbol.int<\"M\">, !symbol.int<\"N\"> -> !symbol.int<\"M // N\">" in printed
    assert "symbol.min %m, %n : !symbol.int<\"M\">, !symbol.int<\"N\"> -> !symbol.int<\"min(M, N)\">" in printed


# TC-SYM-017
# 测试目的: 验证 symbol.add/sub/mul/div/floordiv 会拒绝非 symbol.int 的操作数或结果类型。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_arith_ops_reject_non_symbol_int_types() -> None:
    non_symbol_value = _TestOp(result_types=[i32]).results[0]
    symbol_value = _make_symbol_value("N")

    with pytest.raises(VerifyException, match='symbol.add lhs must have type !symbol.int<"expr">'):
        SymbolAddOp(non_symbol_value, symbol_value, SymbolValueType.from_expr("N")).verify()
    with pytest.raises(VerifyException, match='symbol.sub rhs must have type !symbol.int<"expr">'):
        SymbolSubOp(symbol_value, non_symbol_value, SymbolValueType.from_expr("N")).verify()
    with pytest.raises(VerifyException, match='symbol.mul result type must be !symbol.int<"expr">'):
        SymbolMulOp(symbol_value, symbol_value, i32).verify()
    with pytest.raises(VerifyException, match='symbol.div lhs must have type !symbol.int<"expr">'):
        SymbolDivOp(non_symbol_value, symbol_value, SymbolValueType.from_expr("N / 2")).verify()
    with pytest.raises(VerifyException, match='symbol.floordiv result type must be !symbol.int<"expr">'):
        SymbolFloorDivOp(symbol_value, symbol_value, i32).verify()


# TC-SYM-018
# 测试目的: 验证 symbol.add/sub/mul/div/floordiv 对不完整文本签名会报 parse 错误。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_arith_ops_reject_malformed_signatures() -> None:
    ctx = _build_context()

    with pytest.raises(ParseError, match="symbol.add"):
        Parser(
            ctx,
            """
builtin.module {
  %m = "test.op"() : () -> !symbol.int<"M">
  %one = "test.op"() : () -> !symbol.int<"1">
  %sum = symbol.add %m, %one : !symbol.int<"M">, !symbol.int<"1">
}
""",
        ).parse_module()
    with pytest.raises(ParseError, match="symbol.mul"):
        Parser(
            ctx,
            """
builtin.module {
  %m = "test.op"() : () -> !symbol.int<"M">
  %n = "test.op"() : () -> !symbol.int<"N">
  %prod = symbol.mul %m : !symbol.int<"M"> -> !symbol.int<"M*N">
}
""",
        ).parse_module()
    with pytest.raises(ParseError, match="symbol.floordiv"):
        Parser(
            ctx,
            """
builtin.module {
  %m = "test.op"() : () -> !symbol.int<"M">
  %n = "test.op"() : () -> !symbol.int<"N">
  %floor = symbol.floordiv %m : !symbol.int<"M"> -> !symbol.int<"M // N">
}
""",
        ).parse_module()


# TC-SYM-019
# 测试目的: 验证 symbol.add/sub/mul/div/floordiv 的错误信息包含具体 op 名称与失败原因。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_arith_ops_error_messages_include_context() -> None:
    symbol_value = _make_symbol_value("N")
    non_symbol_value = _TestOp(result_types=[i32]).results[0]
    ctx = _build_context()

    with pytest.raises(VerifyException, match='symbol.add lhs must have type !symbol.int<"expr">'):
        SymbolAddOp(non_symbol_value, symbol_value, SymbolValueType.from_expr("N + 1")).verify()
    with pytest.raises(ParseError, match="symbol.sub"):
        Parser(
            ctx,
            """
builtin.module {
  %n = "test.op"() : () -> !symbol.int<"N">
  %one = "test.op"() : () -> !symbol.int<"1">
  %diff = symbol.sub %n %one : !symbol.int<"N">, !symbol.int<"1"> -> !symbol.int<"N - 1">
}
""",
        ).parse_module()
    with pytest.raises(ParseError, match="symbol.div"):
        Parser(
            ctx,
            """
builtin.module {
  %n = "test.op"() : () -> !symbol.int<"N">
  %one = "test.op"() : () -> !symbol.int<"1">
  %quot = symbol.div %n %one : !symbol.int<"N">, !symbol.int<"1"> -> !symbol.int<"N / 1">
}
""",
        ).parse_module()


# TC-SYM-020
# 测试目的: 验证 symbol.eq/ne/lt/le/gt/ge 在 symbol.int 输入与 i1 输出下可通过 verifier。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_compare_ops_verify_success() -> None:
    symbol_value_m = _make_symbol_value("M")
    symbol_value_n = _make_symbol_value("N")

    ops = [
        SymbolEqOp(symbol_value_m, symbol_value_n, i1),
        SymbolNeOp(symbol_value_m, symbol_value_n, i1),
        SymbolLtOp(symbol_value_m, symbol_value_n, i1),
        SymbolLeOp(symbol_value_m, symbol_value_n, i1),
        SymbolGtOp(symbol_value_m, symbol_value_n, i1),
        SymbolGeOp(symbol_value_m, symbol_value_n, i1),
    ]

    for op in ops:
        op.verify()
        assert op.result.type == i1


# TC-SYM-021
# 测试目的: 验证 symbol.eq/ne/lt/le/gt/ge 的 parse/print round-trip 稳定。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_compare_ops_round_trip() -> None:
    ctx = _build_context()
    module = Parser(
        ctx,
        """
builtin.module {
  %m = "test.op"() : () -> !symbol.int<"M">
  %n = "test.op"() : () -> !symbol.int<"N">
  %eq = symbol.eq %m, %n : !symbol.int<"M">, !symbol.int<"N"> -> i1
  %ne = symbol.ne %m, %n : !symbol.int<"M">, !symbol.int<"N"> -> i1
  %lt = symbol.lt %m, %n : !symbol.int<"M">, !symbol.int<"N"> -> i1
  %le = symbol.le %m, %n : !symbol.int<"M">, !symbol.int<"N"> -> i1
  %gt = symbol.gt %m, %n : !symbol.int<"M">, !symbol.int<"N"> -> i1
  %ge = symbol.ge %m, %n : !symbol.int<"M">, !symbol.int<"N"> -> i1
}
""",
    ).parse_module()

    module.verify()
    printed = _print_op(module)
    assert 'symbol.eq %m, %n : !symbol.int<"M">, !symbol.int<"N"> -> i1' in printed
    assert 'symbol.ne %m, %n : !symbol.int<"M">, !symbol.int<"N"> -> i1' in printed
    assert 'symbol.lt %m, %n : !symbol.int<"M">, !symbol.int<"N"> -> i1' in printed
    assert 'symbol.le %m, %n : !symbol.int<"M">, !symbol.int<"N"> -> i1' in printed
    assert 'symbol.gt %m, %n : !symbol.int<"M">, !symbol.int<"N"> -> i1' in printed
    assert 'symbol.ge %m, %n : !symbol.int<"M">, !symbol.int<"N"> -> i1' in printed


# TC-SYM-022
# 测试目的: 验证 symbol.eq/ne/lt/le/gt/ge 会拒绝非 symbol.int 的输入操作数。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_compare_ops_reject_non_symbol_int_operands() -> None:
    non_symbol_value = _TestOp(result_types=[i32]).results[0]
    symbol_value = _make_symbol_value("N")

    with pytest.raises(VerifyException, match='symbol.eq lhs must have type !symbol.int<"expr">'):
        SymbolEqOp(non_symbol_value, symbol_value, i1).verify()
    with pytest.raises(VerifyException, match='symbol.ge rhs must have type !symbol.int<"expr">'):
        SymbolGeOp(symbol_value, non_symbol_value, i1).verify()


# TC-SYM-023
# 测试目的: 验证 symbol.eq/ne/lt/le/gt/ge 会拒绝非 i1 结果类型。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_compare_ops_reject_non_i1_result() -> None:
    symbol_value = _make_symbol_value("N")

    with pytest.raises(VerifyException, match="symbol.lt result type must be i1"):
        SymbolLtOp(symbol_value, symbol_value, i32).verify()
    with pytest.raises(VerifyException, match="symbol.ne result type must be i1"):
        SymbolNeOp(symbol_value, symbol_value, IndexType()).verify()


# TC-SYM-024
# 测试目的: 验证 symbol.eq/ne/lt/le/gt/ge 对不完整文本签名会报 parse 错误。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_compare_ops_reject_malformed_signatures() -> None:
    ctx = _build_context()

    with pytest.raises(ParseError, match="symbol.eq"):
        Parser(
            ctx,
            """
builtin.module {
  %m = "test.op"() : () -> !symbol.int<"M">
  %n = "test.op"() : () -> !symbol.int<"N">
  %eq = symbol.eq %m, %n : !symbol.int<"M">, !symbol.int<"N">
}
""",
        ).parse_module()
    with pytest.raises(ParseError, match="symbol.gt"):
        Parser(
            ctx,
            """
builtin.module {
  %m = "test.op"() : () -> !symbol.int<"M">
  %gt = symbol.gt %m : !symbol.int<"M"> -> i1
}
""",
        ).parse_module()


# TC-SYM-025
# 测试目的: 验证 symbol.eq/ne/lt/le/gt/ge 的错误信息包含具体 op 名称与失败原因。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_compare_ops_error_messages_include_context() -> None:
    symbol_value = _make_symbol_value("N")
    non_symbol_value = _TestOp(result_types=[i32]).results[0]
    ctx = _build_context()

    with pytest.raises(VerifyException, match='symbol.le rhs must have type !symbol.int<"expr">'):
        SymbolLeOp(symbol_value, non_symbol_value, i1).verify()
    with pytest.raises(ParseError, match="symbol.ge"):
        Parser(
            ctx,
            """
builtin.module {
  %m = "test.op"() : () -> !symbol.int<"M">
  %n = "test.op"() : () -> !symbol.int<"N">
  %ge = symbol.ge %m %n : !symbol.int<"M">, !symbol.int<"N"> -> i1
}
""",
        ).parse_module()


# TC-SYM-039
# 测试目的: 验证 symbol.to_float 在 symbol.int 输入与 f32 结果下可通过 verifier。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_to_float_verify_success() -> None:
    op = SymbolToFloatOp(_make_symbol_value("N"), f32)

    op.verify()
    assert _print_attr(op.result.type) == "f32"


# TC-SYM-040
# 测试目的: 验证 symbol.to_float 的 parse/print round-trip 稳定。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_to_float_round_trip() -> None:
    ctx = _build_context()
    module = Parser(
        ctx,
        """
builtin.module {
  %n = "test.op"() : () -> !symbol.int<"N">
  %f = symbol.to_float %n : !symbol.int<"N"> -> f32
}
""",
    ).parse_module()

    module.verify()
    printed = _print_op(module)
    assert 'symbol.to_float %n : !symbol.int<"N"> -> f32' in printed


# TC-SYM-041
# 测试目的: 验证 symbol.to_float 会拒绝非 symbol.int 输入或非浮点结果类型。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_to_float_rejects_invalid_types() -> None:
    non_symbol_value = _TestOp(result_types=[i32]).results[0]
    symbol_value = _make_symbol_value("N")

    with pytest.raises(VerifyException, match='symbol.to_float source must have type !symbol.int<"expr">'):
        SymbolToFloatOp(non_symbol_value, f32).verify()
    for result_type in (f16, bf16, f32, f64):
        SymbolToFloatOp(symbol_value, result_type).verify()
    with pytest.raises(VerifyException, match="symbol.to_float result type must be float"):
        SymbolToFloatOp(symbol_value, i32).verify()


# TC-SYM-041A
# 测试目的: 验证 symbol.cast 支持整型结果并保持 parse/print 稳定。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
def test_symbol_cast_round_trip() -> None:
    ctx = _build_context()
    module = Parser(
        ctx,
        """
builtin.module {
  %n = "test.op"() : () -> !symbol.int<"N">
  %i8 = symbol.cast %n : !symbol.int<"N"> -> i8
  %i32 = symbol.cast %n : !symbol.int<"N"> -> i32
}
""",
    ).parse_module()

    module.verify()
    printed = _print_op(module)
    assert 'symbol.cast %n : !symbol.int<"N"> -> i8' in printed
    assert 'symbol.cast %n : !symbol.int<"N"> -> i32' in printed


# TC-SYM-041B
# 测试目的: 验证 symbol.cast 会拒绝非 symbol.int 输入或非整型结果类型。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
def test_symbol_cast_rejects_invalid_types() -> None:
    non_symbol_value = _TestOp(result_types=[i32]).results[0]
    symbol_value = _make_symbol_value("N")

    with pytest.raises(VerifyException, match='symbol.cast source must have type !symbol.int<"expr">'):
        SymbolCastOp(non_symbol_value, i32).verify()
    with pytest.raises(VerifyException, match="symbol.cast result type must be integer"):
        SymbolCastOp(symbol_value, f32).verify()


# TC-SYM-042
# 测试目的: 验证 symbol.to_int 支持常见整型变体（i8/i16/i32/i64）并通过 verifier。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
@pytest.mark.parametrize(
    ("result_type", "expected_text"),
    [(i8, "i8"), (i16, "i16"), (i32, "i32"), (i64, "i64")],
)
def test_symbol_to_int_verify_success_for_integer_variants(result_type: IntegerType, expected_text: str) -> None:
    op = SymbolToIntOp(_make_symbol_value("N"), result_type)

    op.verify()
    assert _print_attr(op.result.type) == expected_text


# TC-SYM-043
# 测试目的: 验证 symbol.to_int 的 parse/print 在不同整型结果类型下 round-trip 稳定。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_to_int_round_trip() -> None:
    ctx = _build_context()
    module = Parser(
        ctx,
        """
builtin.module {
  %n = "test.op"() : () -> !symbol.int<"N">
  %i8 = symbol.to_int %n : !symbol.int<"N"> -> i8
  %i32 = symbol.to_int %n : !symbol.int<"N"> -> i32
  %i64 = symbol.to_int %n : !symbol.int<"N"> -> i64
}
""",
    ).parse_module()

    module.verify()
    printed = _print_op(module)
    assert 'symbol.to_int %n : !symbol.int<"N"> -> i8' in printed
    assert 'symbol.to_int %n : !symbol.int<"N"> -> i32' in printed
    assert 'symbol.to_int %n : !symbol.int<"N"> -> i64' in printed


# TC-SYM-044
# 测试目的: 验证 symbol.to_int 会拒绝非 symbol.int 输入或非整型结果类型。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_to_int_rejects_invalid_types() -> None:
    non_symbol_value = _TestOp(result_types=[i32]).results[0]
    symbol_value = _make_symbol_value("N")

    with pytest.raises(VerifyException, match='symbol.to_int source must have type !symbol.int<"expr">'):
        SymbolToIntOp(non_symbol_value, i32).verify()
    with pytest.raises(VerifyException, match="symbol.to_int result type must be integer"):
        SymbolToIntOp(symbol_value, f32).verify()
    with pytest.raises(VerifyException, match="symbol.to_int result type must be integer"):
        SymbolToIntOp(symbol_value, IndexType()).verify()


# TC-SYM-045
# 测试目的: 验证 `SymbolPtrType` 的基础合法路径：构造/解析 `!symbol.ptr<dtype>` 均可通过 verifier。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_ptr_type_verify_success() -> None:
    ctx = _build_context()

    ty = SymbolPtrType(f32)
    ty.verify()
    assert _print_attr(ty) == "!symbol.ptr<f32>"

    parsed = Parser(ctx, "!symbol.ptr<f32>").parse_attribute()
    assert isinstance(parsed, SymbolPtrType)
    parsed.verify()
    assert _print_attr(parsed) == "!symbol.ptr<f32>"


# TC-SYM-046
# 测试目的: 验证 `!symbol.ptr<dtype>` 文本语法的 parse/print round-trip 稳定性。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_ptr_type_round_trip() -> None:
    ctx = _build_context()
    for text in ["!symbol.ptr<f32>", "!symbol.ptr<i32>"]:
        ty = Parser(ctx, text).parse_attribute()
        assert isinstance(ty, SymbolPtrType)
        ty.verify()
        assert _print_attr(ty) == text


# TC-SYM-047
# 测试目的: 验证 `!symbol.int<\"...\">` 作为 `!symbol.ptr<dtype>` 的 dtype 必须被拒绝。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_ptr_type_rejects_symbol_value_dtype() -> None:
    with pytest.raises(VerifyException, match="symbol\\.ptr dtype must not be symbol\\.int"):
        SymbolPtrType(SymbolValueType.from_expr("N")).verify()


# TC-SYM-048
# 测试目的: 验证非 `TypeAttribute` 作为 dtype 必须被 verifier 拒绝。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_ptr_type_rejects_non_type_dtype() -> None:
    with pytest.raises(VerifyException, match="symbol\\.ptr dtype must be type"):
        SymbolPtrType(StringAttr("not_type")).verify()


# TC-SYM-026
# 测试目的: 验证 symbol.get_dim 可从 nn.memory 读取静态整数维度并返回对应 symbol value type。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_get_dim_reads_static_dim_from_memory_type() -> None:
    source = _make_memory_value(
        _make_memory_type([IntAttr(4), IntAttr(8)], [IntAttr(8), IntAttr(1)])
    )

    op = SymbolGetDimOp(source, 0)

    op.verify()
    assert _print_attr(op.result.type) == '!symbol.int<"4">'


# TC-SYM-026A
# 测试目的: 验证 symbol.get_dim 读取静态整数维度时可由 folding 折叠为常量。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_get_dim_folds_static_dim_to_const_attr() -> None:
    source = _make_memory_value(
        _make_memory_type([IntAttr(4), StringAttr("N")], [IntAttr(8), IntAttr(1)])
    )

    static_op = SymbolGetDimOp(source, 0)
    dynamic_op = SymbolGetDimOp(source, 1)

    assert static_op.fold() == (IntAttr(4),)
    assert dynamic_op.fold() is None


# TC-SYM-027
# 测试目的: 验证 symbol.get_dim 可从 nn.memory 读取符号维度并返回对应 symbol value type。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_get_dim_reads_symbolic_dim_from_memory_type() -> None:
    source = _make_memory_value(
        _make_memory_type([StringAttr("M"), StringAttr("N")], [StringAttr("N"), IntAttr(1)])
    )

    op = SymbolGetDimOp(source, 1)

    op.verify()
    assert _print_attr(op.result.type) == '!symbol.int<"N">'


# TC-SYM-028
# 测试目的: 验证 symbol.get_stride 可从 nn.memory 读取静态整数步幅并返回对应 symbol value type。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_get_stride_reads_static_stride_from_memory_type() -> None:
    source = _make_memory_value(
        _make_memory_type([IntAttr(4), IntAttr(8)], [IntAttr(8), IntAttr(1)])
    )

    op = SymbolGetStrideOp(source, 0)

    op.verify()
    assert _print_attr(op.result.type) == '!symbol.int<"8">'


# TC-SYM-028A
# 测试目的: 验证 symbol.get_stride 读取静态整数步幅时可由 folding 折叠为常量。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_get_stride_folds_static_stride_to_const_attr() -> None:
    source = _make_memory_value(
        _make_memory_type([StringAttr("M"), StringAttr("N")], [IntAttr(16), StringAttr("N")])
    )

    static_op = SymbolGetStrideOp(source, 0)
    dynamic_op = SymbolGetStrideOp(source, 1)

    assert static_op.fold() == (IntAttr(16),)
    assert dynamic_op.fold() is None


# TC-SYM-062
# 测试目的: 验证 symbol.get_dim/get_stride 的公开 fold 入口会稳定拒绝非 memory、非静态轴号、越界轴号与匿名动态条目。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_memory_query_fold_public_rejection_matrix() -> None:
    non_memory_source = _TestOp(result_types=[i32]).results[0]
    static_source = _make_memory_value(
        _make_memory_type([IntAttr(4), IntAttr(8)], [IntAttr(8), IntAttr(1)])
    )
    unknown_dim_source = _make_memory_value(
        _make_memory_type([StringAttr("?"), IntAttr(8)], [IntAttr(8), IntAttr(1)])
    )
    unknown_stride_source = _make_memory_value(
        _make_memory_type([IntAttr(4), IntAttr(8)], [StringAttr("?"), IntAttr(1)])
    )

    assert SymbolGetDimOp(non_memory_source, 0).fold() is None
    assert SymbolGetDimOp(static_source, StringAttr("axis")).fold() is None
    assert SymbolGetStrideOp(static_source, 2).fold() is None
    assert SymbolGetDimOp(unknown_dim_source, 0).fold() is None
    assert SymbolGetStrideOp(unknown_stride_source, 0).fold() is None


# TC-SYM-029
# 测试目的: 验证 symbol.get_stride 可从 nn.memory 读取符号步幅并返回对应 symbol value type。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_get_stride_reads_symbolic_stride_from_memory_type() -> None:
    source = _make_memory_value(
        _make_memory_type([StringAttr("M"), StringAttr("N")], [StringAttr("K*N"), StringAttr("N")])
    )

    op = SymbolGetStrideOp(source, 1)

    op.verify()
    assert _print_attr(op.result.type) == '!symbol.int<"N">'


# TC-SYM-030
# 测试目的: 验证 symbol.get_dim 在轴号越界、负数或非静态整数时会报 verifier 错误。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_get_dim_rejects_invalid_axis() -> None:
    source = _make_memory_value(
        _make_memory_type([IntAttr(4), IntAttr(8)], [IntAttr(8), IntAttr(1)])
    )

    with pytest.raises(VerifyException, match="axis out of range"):
        SymbolGetDimOp(source, -1).verify()
    with pytest.raises(VerifyException, match="axis out of range"):
        SymbolGetDimOp(source, 2).verify()
    with pytest.raises(VerifyException, match="axis must be a static integer"):
        SymbolGetDimOp(source, StringAttr("axis")).verify()


# TC-SYM-030
# 测试目的: 验证 symbol.get_stride 在轴号越界、负数或非静态整数时会报 verifier 错误。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_get_stride_rejects_invalid_axis() -> None:
    source = _make_memory_value(
        _make_memory_type([IntAttr(4), IntAttr(8)], [IntAttr(8), IntAttr(1)])
    )

    with pytest.raises(VerifyException, match="axis out of range"):
        SymbolGetStrideOp(source, -1).verify()
    with pytest.raises(VerifyException, match="axis out of range"):
        SymbolGetStrideOp(source, 2).verify()
    with pytest.raises(VerifyException, match="axis must be a static integer"):
        SymbolGetStrideOp(source, StringAttr("axis")).verify()


# TC-SYM-031
# 测试目的: 验证 symbol.get_dim 在 source 不是 nn.memory 或目标 dim 为匿名动态值时会报 verifier 错误。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_get_dim_rejects_non_memory_type() -> None:
    non_memory_source = _TestOp(result_types=[i32]).results[0]
    unknown_dim_source = _make_memory_value(
        _make_memory_type([StringAttr("?"), IntAttr(8)], [IntAttr(8), IntAttr(1)])
    )

    with pytest.raises(VerifyException, match="source must be nn.memory"):
        SymbolGetDimOp(non_memory_source, 0).verify()
    with pytest.raises(VerifyException, match="does not support unknown shape entry"):
        SymbolGetDimOp(unknown_dim_source, 0).verify()


# TC-SYM-031
# 测试目的: 验证 symbol.get_stride 在目标 stride 为匿名动态值时会报 verifier 错误。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_get_stride_rejects_unknown_entry() -> None:
    source = _make_memory_value(
        _make_memory_type([StringAttr("N"), IntAttr(8)], [StringAttr("?"), IntAttr(1)])
    )

    with pytest.raises(VerifyException, match="does not support unknown stride entry"):
        SymbolGetStrideOp(source, 0).verify()


# TC-SYM-032
# 测试目的: 验证 symbol.for 接受 symbol.int 类型的 start/end/step，并暴露单个 symbol.int 块参数。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_for_accepts_symbol_int_bounds_and_iter_arg() -> None:
    start = _make_symbol_value("M")
    end = _make_symbol_value("N")
    step = _make_symbol_value("1")
    body = Block(arg_types=[SymbolIterType.from_bounds("M", "N", "1")])

    op = SymbolForOp(start, end, step, body)

    op.verify()
    assert len(op.body.block.args) == 1
    assert isinstance(op.body.block.args[0].type, SymbolIterType)
    assert _print_attr(op.body.block.args[0].type) == '!symbol.iter<start = "M", end = "N", step = "1">'


# TC-SYM-033
# 测试目的: 验证 symbol.for 的 parse/print round-trip 稳定。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_for_round_trip() -> None:
    ctx = _build_context()
    module = Parser(
        ctx,
        """
builtin.module {
  %start = "test.op"() : () -> !symbol.int<"M">
  %end = "test.op"() : () -> !symbol.int<"N">
  %step = "test.op"() : () -> !symbol.int<"1">
  symbol.for %i = %start to %end step %step {iter = #symbol.iter<start = "M", end = "N", step = "1">} {
  }
}
""",
    ).parse_module()

    op = module.body.block.ops.last
    assert isinstance(op, SymbolForOp)
    assert (
        _print_op(op)
        == 'symbol.for %i = %start to %end step %step {iter = #symbol.iter<start = "M", end = "N", step = "1">} {\n}'
    )


# TC-SYM-034
# 测试目的: 验证 symbol.for 会拒绝非 symbol.int 的 start/end/step 或块参数类型，尤其 it 不能是 f32/f64/index/i32 等非 SymbolValueType。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_for_rejects_non_symbol_int_operands() -> None:
    symbol_value = _make_symbol_value("N")
    non_symbol_value = _TestOp(result_types=[i32]).results[0]
    non_symbol_it_values = [
        _TestOp(result_types=[i32]).results[0],
        _TestOp(result_types=[f32]).results[0],
        _TestOp(result_types=[f64]).results[0],
        _TestOp(result_types=[IndexType()]).results[0],
    ]

    with pytest.raises(VerifyException, match='symbol.for start must have type !symbol.int<"expr">'):
        SymbolForOp(non_symbol_value, symbol_value, symbol_value, Block(arg_types=[SymbolIterType.from_bounds("N", "N", "N")])).verify()
    for non_symbol_it in non_symbol_it_values:
        with pytest.raises(VerifyException, match="symbol.for it must have type !symbol.iter<...>"):
            SymbolForOp(symbol_value, symbol_value, symbol_value, Block(arg_types=[non_symbol_it.type])).verify()


# TC-SYM-035
# 测试目的: 验证 symbol.for 在 step 可静态判定为 0 时会报错。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_for_rejects_zero_step() -> None:
    start = _make_symbol_value("M")
    end = _make_symbol_value("N")
    step = _make_symbol_value("0")

    with pytest.raises(VerifyException, match="symbol.for step must not be zero"):
        SymbolForOp(start, end, step, Block(arg_types=[SymbolIterType.from_bounds("M", "N", "0")])).verify()


# TC-SYM-036
# 测试目的: 验证 symbol.for 会拒绝空 region、多块 region 或错误块参数结构。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_for_rejects_invalid_region_shape() -> None:
    start = _make_symbol_value("M")
    end = _make_symbol_value("N")
    step = _make_symbol_value("1")

    with pytest.raises(VerifyException, match="symbol.for.*single-block regions"):
        SymbolForOp(start, end, step, Region()).verify()
    with pytest.raises(VerifyException, match="symbol.for body must have exactly one block argument"):
        SymbolForOp(start, end, step, Block()).verify()
    with pytest.raises(VerifyException, match="symbol.for.*single-block regions"):
        SymbolForOp(
            start,
            end,
            step,
            Region(
                [
                    Block(arg_types=[SymbolIterType.from_bounds("M", "N", "1")]),
                    Block(arg_types=[SymbolIterType.from_bounds("M", "N", "1")]),
                ]
            ),
        ).verify()


# TC-SYM-037
# 测试目的: 验证 symbol.for 文本缺少关键片段或类型段不完整时 parse 会报错。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_for_parse_rejects_malformed_text() -> None:
    ctx = _build_context()

    with pytest.raises(ParseError, match="symbol.for"):
        Parser(
            ctx,
            """
builtin.module {
  %start = "test.op"() : () -> !symbol.int<"M">
  %end = "test.op"() : () -> !symbol.int<"N">
  %step = "test.op"() : () -> !symbol.int<"1">
  symbol.for %i = %start %end step %step {iter = #symbol.iter<start = "M", end = "N", step = "1">} {
  }
}
""",
        ).parse_module()
    with pytest.raises(VerifyException, match="iter attribute must be"):
        Parser(
            ctx,
            """
builtin.module {
  %start = "test.op"() : () -> !symbol.int<"0">
  %end = "test.op"() : () -> !symbol.int<"N">
  %step = "test.op"() : () -> !symbol.int<"1">
  symbol.for %i = %start to %end step %step {iter = #symbol.expr<"N">} {
  }
}
""",
        ).parse_module()
    with pytest.raises(VerifyException, match="result type requires loop-carried"):
        Parser(
            ctx,
            """
builtin.module {
  %start = "test.op"() : () -> !symbol.int<"0">
  %end = "test.op"() : () -> !symbol.int<"N">
  %step = "test.op"() : () -> !symbol.int<"1">
  symbol.for %i = %start to %end step %step {iter = #symbol.iter<start = "0", end = "N", step = "1">} -> !symbol.int<"N"> {
  }
}
""",
        ).parse_module()
    with pytest.raises(VerifyException, match="loop-carried result must be"):
        Parser(
            ctx,
            """
builtin.module {
  %start = "test.op"() : () -> !symbol.int<"0">
  %end = "test.op"() : () -> !symbol.int<"N">
  %step = "test.op"() : () -> !symbol.int<"1">
  %zero = symbol.const 0 : !symbol.int<"0">
  symbol.for %i = %start to %end step %step iter_args(%acc = %zero) {iter = #symbol.iter<start = "0", end = "N", step = "1">} -> f32 {
  }
}
""",
        ).parse_module()
    with pytest.raises(ParseError, match="symbol.for"):
        Parser(
            ctx,
            """
builtin.module {
  %start = "test.op"() : () -> !symbol.int<"M">
  %end = "test.op"() : () -> !symbol.int<"N">
  %step = "test.op"() : () -> !symbol.int<"1">
  symbol.for %i = %start to %end step %step {iter = #symbol.iter<start = "M", end = "N">} {
  }
}
""",
        ).parse_module()


# TC-SYM-038
# 测试目的: 验证 symbol.for 的 verifier 与 parse 错误信息包含 op 名称与失败原因。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_for_error_messages_include_context() -> None:
    start = _make_symbol_value("M")
    end = _make_symbol_value("N")
    step = _make_symbol_value("0")

    with pytest.raises(VerifyException, match="symbol.for step must not be zero"):
        SymbolForOp(start, end, step, Block(arg_types=[SymbolIterType.from_bounds("M", "N", "0")])).verify()

    ctx = _build_context()
    with pytest.raises(ParseError, match="symbol.for"):
        Parser(
            ctx,
            """
builtin.module {
  %start = "test.op"() : () -> !symbol.int<"M">
  %end = "test.op"() : () -> !symbol.int<"N">
  %step = "test.op"() : () -> !symbol.int<"1">
  symbol.for %i = %start to %end %step {iter = #symbol.iter<start = "M", end = "N", step = "1">} {
  }
}
""",
        ).parse_module()


# TC-SYM-063
# 测试目的: 验证 symbol.yield 公开 verifier 对父 op 与 carried value 约束保持稳定错误语义。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_yield_public_parent_and_carried_edges() -> None:
    start = _make_symbol_value("0")
    end = _make_symbol_value("N")
    step = _make_symbol_value("1")

    with pytest.raises(VerifyException, match="symbol.yield must appear inside symbol.for"):
        SymbolYieldOp(SymbolConstOp(1).result).verify()

    block = Block(arg_types=[SymbolIterType.from_bounds("0", "N", "1")])
    yield_op = SymbolYieldOp(SymbolConstOp(1).result)
    block.add_op(yield_op)
    SymbolForOp(start, end, step, block)
    with pytest.raises(VerifyException, match="symbol.yield requires symbol.for loop-carried"):
        yield_op.verify()


# TC-SYM-064
# 测试目的: 验证 symbol.for 公开 verifier 对 iter attribute 与 block argument 的一致性矩阵。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_for_rejects_iter_attr_mismatch_matrix() -> None:
    start = _make_symbol_value("0")
    end = _make_symbol_value("N")
    step = _make_symbol_value("1")

    cases = [
        (
            SymbolForOp(
                start,
                end,
                step,
                Block(arg_types=[SymbolIterType.from_bounds("1", "N", "1")]),
                iter_attr=SymbolIterAttr.from_bounds("1", "N", "1"),
            ),
            "iter.start must match start operand",
        ),
        (
            SymbolForOp(
                start,
                end,
                step,
                Block(arg_types=[SymbolIterType.from_bounds("0", "M", "1")]),
                iter_attr=SymbolIterAttr.from_bounds("0", "M", "1"),
            ),
            "iter.end must match end operand",
        ),
        (
            SymbolForOp(
                start,
                end,
                step,
                Block(arg_types=[SymbolIterType.from_bounds("0", "N", "2")]),
                iter_attr=SymbolIterAttr.from_bounds("0", "N", "2"),
            ),
            "iter.step must match step operand",
        ),
        (
            SymbolForOp(
                start,
                end,
                step,
                Block(arg_types=[SymbolIterType.from_bounds("0", "N", "2")]),
                iter_attr=SymbolIterAttr.from_bounds("0", "N", "1"),
            ),
            "it must have type symbol.iter",
        ),
        (
            SymbolForOp(
                start,
                end,
                step,
                Block(arg_types=[SymbolIterType.from_bounds("0", "N", "1")]),
                init=SymbolConstOp(0).result,
                result_type=SymbolValueType.from_expr("TOTAL"),
            ),
            "requires exactly two block arguments",
        ),
    ]

    for op, message in cases:
        with pytest.raises(VerifyException, match=message):
            op.verify()


# TC-SYM-065
# 测试目的: 验证 symbol.for 打印公开路径会对结构不完整的循环回退到稳定 default format。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_for_prints_default_format_for_invalid_body_shape() -> None:
    op = SymbolForOp(_make_symbol_value("0"), _make_symbol_value("N"), _make_symbol_value("1"), Block())

    assert _print_op(op).startswith("symbol.for(")


# TC-SYM-038A
# 测试目的: 验证 symbol.for 支持单个 loop-carried symbol.int，并保持 parse/print round-trip 稳定。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_for_loop_carried_symbol_int_round_trip() -> None:
    start = _make_symbol_value("0")
    end = _make_symbol_value("M")
    step = _make_symbol_value("TILE_M")
    init = SymbolConstOp(0).result
    iter_type = SymbolIterType.from_bounds("0", "M", "TILE_M")
    acc_type = SymbolValueType.from_expr("ACC")
    result_type = SymbolValueType.from_expr("TOTAL")
    block = Block(arg_types=[iter_type, acc_type])
    acc = block.args[1]
    local = SymbolConstOp(1)
    block.add_op(local)
    next_op = SymbolAddOp(acc, local.result, SymbolValueType.from_expr("NEXT"))
    block.add_op(next_op)
    block.add_op(SymbolYieldOp(next_op.result))

    op = SymbolForOp(start, end, step, block, init=init, result_type=result_type)
    op.verify()
    assert op.result is not None
    assert op.result.type == result_type
    assert isinstance(block.last_op, SymbolYieldOp)

    ctx = _build_context()
    module = Parser(
        ctx,
        """
builtin.module {
  %start = "test.op"() : () -> !symbol.int<"0">
  %end = "test.op"() : () -> !symbol.int<"M">
  %step = "test.op"() : () -> !symbol.int<"TILE_M">
  %zero = symbol.const 0 : !symbol.int<"0">
  %total = symbol.for %i = %start to %end step %step iter_args(%acc = %zero) {iter = #symbol.iter<start = "0", end = "M", step = "TILE_M">} -> !symbol.int<"TOTAL"> {
    %one = symbol.const 1 : !symbol.int<"1">
    %next = symbol.add %acc, %one : !symbol.int<"TOTAL">, !symbol.int<"1"> -> !symbol.int<"NEXT">
    symbol.yield %next : !symbol.int<"NEXT">
  }
}
""",
    ).parse_module()
    module.verify()
    printed = _print_op(module).rstrip()
    reparsed = Parser(ctx, printed).parse_module()
    reparsed.verify()
    assert "iter_args(%acc = %zero)" in printed
    assert 'symbol.yield %next : !symbol.int<"NEXT">' in printed
    assert ' -> !symbol.int<"TOTAL"> {' in printed
    assert printed == _print_op(reparsed).rstrip()


# TC-SYM-038B
# 测试目的: 验证 symbol.for loop-carried symbol.int 仅允许单个 symbol.int init/acc/yield/result 组合。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_for_rejects_invalid_loop_carried_symbol_int() -> None:
    start = _make_symbol_value("0")
    end = _make_symbol_value("M")
    step = _make_symbol_value("TILE_M")
    valid_init = SymbolConstOp(0).result

    with pytest.raises(VerifyException, match='symbol.for loop-carried init must have type !symbol.int<"expr">'):
        SymbolForOp(
            start,
            end,
            step,
            Block(arg_types=[SymbolIterType.from_bounds("0", "M", "TILE_M"), SymbolValueType.from_expr("ACC")]),
            init=_TestOp(result_types=[f32]).results[0],
            result_type=SymbolValueType.from_expr("TOTAL"),
        ).verify()

    with pytest.raises(VerifyException, match='symbol.for loop-carried acc must have type !symbol.int<"expr">'):
        SymbolForOp(
            start,
            end,
            step,
            Block(arg_types=[SymbolIterType.from_bounds("0", "M", "TILE_M"), i32]),
            init=valid_init,
            result_type=SymbolValueType.from_expr("TOTAL"),
        ).verify()

    with pytest.raises(VerifyException, match='symbol.for loop-carried result must have type !symbol.int<"expr">'):
        SymbolForOp(
            start,
            end,
            step,
            Block(arg_types=[SymbolIterType.from_bounds("0", "M", "TILE_M"), SymbolValueType.from_expr("ACC")]),
            init=valid_init,
            result_type=f32,
        ).verify()

    block_missing_yield = Block(arg_types=[SymbolIterType.from_bounds("0", "M", "TILE_M"), SymbolValueType.from_expr("ACC")])
    with pytest.raises(VerifyException, match="symbol.for loop-carried body must terminate with symbol.yield"):
        SymbolForOp(
            start,
            end,
            step,
            block_missing_yield,
            init=valid_init,
            result_type=SymbolValueType.from_expr("TOTAL"),
        ).verify()

    block_bad_yield = Block(arg_types=[SymbolIterType.from_bounds("0", "M", "TILE_M"), SymbolValueType.from_expr("ACC")])
    block_bad_yield.add_op(SymbolYieldOp(_TestOp(result_types=[f32]).results[0]))
    with pytest.raises(VerifyException, match='symbol.yield value must have type !symbol.int<"expr">'):
        SymbolForOp(
            start,
            end,
            step,
            block_bad_yield,
            init=valid_init,
            result_type=SymbolValueType.from_expr("TOTAL"),
        ).verify()
