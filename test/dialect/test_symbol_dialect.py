"""symbol dialect tests.

创建者: 金铲铲大作战
最后一次更改: 我不是牛马

功能说明:
- 覆盖 symbol dialect 的整数符号 attribute/type、verifier、parse/print 与错误路径。

使用示例:
- pytest -q test/dialect/test_symbol_dialect.py

覆盖率:
- 覆盖率命令: pytest -q --cov=kernel_gen.dialect.symbol --cov-report=term-missing test/dialect/test_symbol_dialect.py
- 覆盖率结果: 96%（2026-03-22 22:26:51 +0800）

关联文件:
- 功能实现: kernel_gen/dialect/symbol.py
- Spec 文档: spec/dialect/symbol.md
- 测试文件: test/dialect/test_symbol_dialect.py
"""

from __future__ import annotations

from io import StringIO
import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects.builtin import ArrayAttr, Builtin, IndexType, IntAttr, StringAttr, f32, f64, i32
from xdsl.dialects.test import Test, TestOp as _TestOp
from xdsl.ir import Block, Region
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
    SymbolExprAttr,
    SymbolGetDimOp,
    SymbolGetStrideOp,
    SymbolForOp,
    SymbolMulOp,
    SymbolSubOp,
    SymbolValueType,
)
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType


def _build_context() -> Context:
    """构造加载 builtin/symbol 的解析上下文。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 为 symbol attribute/type 的 parse/print 测试提供统一 context。

    使用示例:
    - _build_context()

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol_dialect.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    ctx = Context()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(Test)
    ctx.load_dialect(Nn)
    ctx.load_dialect(Symbol)
    return ctx


def _print_attr(value: object) -> str:
    """打印 attribute 或 type 为文本。"""

    stream = StringIO()
    printer = Printer(stream=stream)
    printer.print_attribute(value)
    return stream.getvalue()


def _print_op(op: object) -> str:
    """打印 operation 为文本。"""

    stream = StringIO()
    printer = Printer(stream=stream)
    printer.print_op(op)
    return stream.getvalue()


def _make_space(name: str = "global") -> NnMemorySpaceAttr:
    """构造 nn space attribute。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 为 symbol.get_dim/get_stride 测试提供统一的 `nn.space` 构造。

    使用示例:
    - _make_space()

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol_dialect.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    return NnMemorySpaceAttr(StringAttr(name))


def _make_memory_type(shape: list[IntAttr | StringAttr], stride: list[IntAttr | StringAttr]) -> NnMemoryType:
    """构造 nn.memory type。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 为 symbol.get_dim/get_stride 测试构造最小合法 memory type。

    使用示例:
    - _make_memory_type([IntAttr(4)], [IntAttr(1)])

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol_dialect.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    return NnMemoryType(ArrayAttr(shape), ArrayAttr(stride), i32, _make_space())


def _make_memory_value(memory_type: NnMemoryType):
    """构造携带 nn.memory type 的测试 SSA value。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 复用 `test.TestOp` 产出 `symbol.get_dim/get_stride` 所需 operand。

    使用示例:
    - _make_memory_value(memory_type)

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol_dialect.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    return _TestOp(result_types=[memory_type]).results[0]


def _make_symbol_value(expr: str):
    """构造携带 symbol.int type 的测试 SSA value。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 为 symbol.for 测试复用统一的 symbol.int 操作数构造。

    使用示例:
    - _make_symbol_value("N")

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol_dialect.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    return _TestOp(result_types=[SymbolValueType.from_expr(expr)]).results[0]


# TC-SYM-001 / TC-SYM-002 / TC-SYM-009
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 19:39:28 +0800
# 最近一次运行成功时间: 2026-03-22 19:39:28 +0800
# 测试目的: 验证 SymbolExprAttr 的基础表达、复合表达与 parse/print round-trip 稳定。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_expr_attr_round_trip() -> None:
    ctx = _build_context()
    for text in ['#symbol.expr<"N">', '#symbol.expr<"M + 1">', '#symbol.expr<"B*K">']:
        expr = Parser(ctx, text).parse_attribute()
        assert isinstance(expr, SymbolExprAttr)
        expr.verify()
        assert _print_attr(expr) == text


# TC-SYM-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 19:39:28 +0800
# 最近一次运行成功时间: 2026-03-22 19:39:28 +0800
# 测试目的: 验证空表达式会被 verifier 拒绝。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_expr_attr_rejects_empty_expr() -> None:
    with pytest.raises(VerifyException, match="must not be empty"):
        SymbolExprAttr.from_expr("   ").verify()


# TC-SYM-004 / TC-SYM-005 / TC-SYM-006 / TC-SYM-009
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 19:39:28 +0800
# 最近一次运行成功时间: 2026-03-22 19:39:28 +0800
# 测试目的: 验证整数 symbol type 支持具名表达与常量表达，并可稳定 parse/print。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_value_type_round_trip_for_integer_only_semantics() -> None:
    ctx = _build_context()
    for text in ['!symbol.int<"N">', '!symbol.int<"M + 1">', '!symbol.int<"3">']:
        ty = Parser(ctx, text).parse_attribute()
        assert isinstance(ty, SymbolValueType)
        ty.verify()
        assert _print_attr(ty) == text


# TC-SYM-013 / TC-SYM-014
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 19:39:28 +0800
# 最近一次运行成功时间: 2026-03-22 19:39:28 +0800
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
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 19:39:28 +0800
# 最近一次运行成功时间: 2026-03-22 19:39:28 +0800
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
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 19:39:28 +0800
# 最近一次运行成功时间: 2026-03-22 19:39:28 +0800
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


# TC-SYM-003 / TC-SYM-007
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 19:39:28 +0800
# 最近一次运行成功时间: 2026-03-22 19:39:28 +0800
# 测试目的: 验证非法字符表达式在 attr/type 两条路径都会报 verifier 错误。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_verifier_rejects_illegal_expression_characters() -> None:
    with pytest.raises(VerifyException, match="must contain identifiers"):
        SymbolExprAttr.from_expr("N/2").verify()
    with pytest.raises(VerifyException, match="must contain identifiers"):
        SymbolValueType.from_expr("N@1").verify()


# TC-SYM-015
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 22:26:51 +0800
# 最近一次运行成功时间: 2026-03-22 22:26:51 +0800
# 测试目的: 验证 symbol.add/sub/mul 在 symbol.int 输入与输出下可通过 verifier。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_arith_ops_verify_success() -> None:
    add_op = SymbolAddOp(_make_symbol_value("M"), _make_symbol_value("1"), SymbolValueType.from_expr("M + 1"))
    sub_op = SymbolSubOp(_make_symbol_value("N"), _make_symbol_value("1"), SymbolValueType.from_expr("N - 1"))
    mul_op = SymbolMulOp(_make_symbol_value("M"), _make_symbol_value("N"), SymbolValueType.from_expr("M*N"))

    add_op.verify()
    sub_op.verify()
    mul_op.verify()

    assert _print_attr(add_op.result.type) == '!symbol.int<"M + 1">'
    assert _print_attr(sub_op.result.type) == '!symbol.int<"N - 1">'
    assert _print_attr(mul_op.result.type) == '!symbol.int<"M*N">'


# TC-SYM-016
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 22:26:51 +0800
# 最近一次运行成功时间: 2026-03-22 22:26:51 +0800
# 测试目的: 验证 symbol.add/sub/mul 的 parse/print round-trip 稳定。
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
}
""",
    ).parse_module()

    module.verify()
    printed = _print_op(module)
    assert "symbol.add %m, %one : !symbol.int<\"M\">, !symbol.int<\"1\"> -> !symbol.int<\"M + 1\">" in printed
    assert "symbol.sub %n, %one : !symbol.int<\"N\">, !symbol.int<\"1\"> -> !symbol.int<\"N - 1\">" in printed
    assert "symbol.mul %m, %n : !symbol.int<\"M\">, !symbol.int<\"N\"> -> !symbol.int<\"M*N\">" in printed


# TC-SYM-017
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 22:26:51 +0800
# 最近一次运行成功时间: 2026-03-22 22:26:51 +0800
# 测试目的: 验证 symbol.add/sub/mul 会拒绝非 symbol.int 的操作数或结果类型。
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


# TC-SYM-018
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 22:26:51 +0800
# 最近一次运行成功时间: 2026-03-22 22:26:51 +0800
# 测试目的: 验证 symbol.add/sub/mul 对不完整文本签名会报 parse 错误。
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


# TC-SYM-019
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 22:26:51 +0800
# 最近一次运行成功时间: 2026-03-22 22:26:51 +0800
# 测试目的: 验证 symbol.add/sub/mul 的错误信息包含具体 op 名称与失败原因。
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


# TC-SYM-020
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 20:14:51 +0800
# 最近一次运行成功时间: 2026-03-22 20:14:51 +0800
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


# TC-SYM-021
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 20:14:51 +0800
# 最近一次运行成功时间: 2026-03-22 20:14:51 +0800
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


# TC-SYM-022
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 20:14:51 +0800
# 最近一次运行成功时间: 2026-03-22 20:14:51 +0800
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


# TC-SYM-023
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 20:14:51 +0800
# 最近一次运行成功时间: 2026-03-22 20:14:51 +0800
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


# TC-SYM-024
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 20:14:51 +0800
# 最近一次运行成功时间: 2026-03-22 20:14:51 +0800
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


# TC-SYM-024
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 20:14:51 +0800
# 最近一次运行成功时间: 2026-03-22 20:14:51 +0800
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


# TC-SYM-025
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 20:14:51 +0800
# 最近一次运行成功时间: 2026-03-22 20:14:51 +0800
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


# TC-SYM-025
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 20:14:51 +0800
# 最近一次运行成功时间: 2026-03-22 20:14:51 +0800
# 测试目的: 验证 symbol.get_stride 在目标 stride 为匿名动态值时会报 verifier 错误。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_get_stride_rejects_unknown_entry() -> None:
    source = _make_memory_value(
        _make_memory_type([StringAttr("N"), IntAttr(8)], [StringAttr("?"), IntAttr(1)])
    )

    with pytest.raises(VerifyException, match="does not support unknown stride entry"):
        SymbolGetStrideOp(source, 0).verify()


# TC-SYM-026
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 21:30:49 +0800
# 最近一次运行成功时间: 2026-03-22 21:30:49 +0800
# 测试目的: 验证 symbol.for 接受 symbol.int 类型的 start/end/step，并暴露单个 symbol.int 块参数。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_for_accepts_symbol_int_bounds_and_iter_arg() -> None:
    start = _make_symbol_value("M")
    end = _make_symbol_value("N")
    step = _make_symbol_value("1")
    body = Block(arg_types=[SymbolValueType.from_expr("M")])

    op = SymbolForOp(start, end, step, body)

    op.verify()
    assert len(op.body.block.args) == 1
    assert isinstance(op.body.block.args[0].type, SymbolValueType)
    assert _print_attr(op.body.block.args[0].type) == '!symbol.int<"M">'


# TC-SYM-027
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 21:30:49 +0800
# 最近一次运行成功时间: 2026-03-22 21:30:49 +0800
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
  symbol.for %i = %start to %end step %step : !symbol.int<"M">, !symbol.int<"N">, !symbol.int<"1"> {
  }
}
""",
    ).parse_module()

    op = module.body.block.ops.last
    assert isinstance(op, SymbolForOp)
    assert _print_op(op) == 'symbol.for %i = %start to %end step %step : !symbol.int<"M">, !symbol.int<"N">, !symbol.int<"1"> {\n}'


# TC-SYM-028
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-23 01:25:04 +0800
# 最近一次运行成功时间: 2026-03-23 01:25:04 +0800
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
        SymbolForOp(non_symbol_value, symbol_value, symbol_value, Block(arg_types=[SymbolValueType.from_expr("N")])).verify()
    for non_symbol_it in non_symbol_it_values:
        with pytest.raises(VerifyException, match='symbol.for it must have type !symbol.int<"expr">'):
            SymbolForOp(symbol_value, symbol_value, symbol_value, Block(arg_types=[non_symbol_it.type])).verify()


# TC-SYM-029
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 21:30:49 +0800
# 最近一次运行成功时间: 2026-03-22 21:30:49 +0800
# 测试目的: 验证 symbol.for 在 step 可静态判定为 0 时会报错。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_for_rejects_zero_step() -> None:
    start = _make_symbol_value("M")
    end = _make_symbol_value("N")
    step = _make_symbol_value("0")

    with pytest.raises(VerifyException, match="symbol.for step must not be zero"):
        SymbolForOp(start, end, step, Block(arg_types=[SymbolValueType.from_expr("M")])).verify()


# TC-SYM-030
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 21:30:49 +0800
# 最近一次运行成功时间: 2026-03-22 21:30:49 +0800
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
            Region([Block(arg_types=[SymbolValueType.from_expr("M")]), Block(arg_types=[SymbolValueType.from_expr("M")])]),
        ).verify()


# TC-SYM-031
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 21:30:49 +0800
# 最近一次运行成功时间: 2026-03-22 21:30:49 +0800
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
  symbol.for %i = %start %end step %step : !symbol.int<"M">, !symbol.int<"N">, !symbol.int<"1"> {
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
  symbol.for %i = %start to %end step %step : !symbol.int<"M">, !symbol.int<"N"> {
  }
}
""",
        ).parse_module()


# TC-SYM-032
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 21:30:49 +0800
# 最近一次运行成功时间: 2026-03-22 21:30:49 +0800
# 测试目的: 验证 symbol.for 的 verifier 与 parse 错误信息包含 op 名称与失败原因。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_for_error_messages_include_context() -> None:
    start = _make_symbol_value("M")
    end = _make_symbol_value("N")
    step = _make_symbol_value("0")

    with pytest.raises(VerifyException, match="symbol.for step must not be zero"):
        SymbolForOp(start, end, step, Block(arg_types=[SymbolValueType.from_expr("M")])).verify()

    ctx = _build_context()
    with pytest.raises(ParseError, match="symbol.for"):
        Parser(
            ctx,
            """
builtin.module {
  %start = "test.op"() : () -> !symbol.int<"M">
  %end = "test.op"() : () -> !symbol.int<"N">
  %step = "test.op"() : () -> !symbol.int<"1">
  symbol.for %i = %start to %end %step : !symbol.int<"M">, !symbol.int<"N">, !symbol.int<"1"> {
  }
}
""",
        ).parse_module()
