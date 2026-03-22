"""symbol dialect tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 symbol dialect 的整数符号 attribute/type、verifier、parse/print 与错误路径。

使用示例:
- pytest -q test/dialect/test_symbol_dialect.py

覆盖率:
- 覆盖率命令: pytest -q --cov=kernel_gen.dialect.symbol --cov-report=term-missing test/dialect/test_symbol_dialect.py
- 覆盖率结果: 100%（2026-03-22 18:50:40 +0800）

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
from xdsl.dialects.builtin import Builtin
from xdsl.parser import Parser
from xdsl.printer import Printer
from xdsl.utils.exceptions import ParseError, VerifyException

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.symbol import Symbol, SymbolExprAttr, SymbolValueType


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
    ctx.load_dialect(Symbol)
    return ctx


def _print_attr(value: object) -> str:
    """打印 attribute 或 type 为文本。"""

    stream = StringIO()
    printer = Printer(stream=stream)
    printer.print_attribute(value)
    return stream.getvalue()


# TC-SYM-001 / TC-SYM-002 / TC-SYM-009
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 18:50:40 +0800
# 最近一次运行成功时间: 2026-03-22 18:50:40 +0800
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
# 最近一次运行测试时间: 2026-03-22 18:50:40 +0800
# 最近一次运行成功时间: 2026-03-22 18:50:40 +0800
# 测试目的: 验证空表达式会被 verifier 拒绝。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_expr_attr_rejects_empty_expr() -> None:
    with pytest.raises(VerifyException, match="must not be empty"):
        SymbolExprAttr.from_expr("   ").verify()


# TC-SYM-004 / TC-SYM-005 / TC-SYM-006 / TC-SYM-009
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 18:50:40 +0800
# 最近一次运行成功时间: 2026-03-22 18:50:40 +0800
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


# TC-SYM-007 / TC-SYM-008
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 18:50:40 +0800
# 最近一次运行成功时间: 2026-03-22 18:50:40 +0800
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
# 最近一次运行测试时间: 2026-03-22 18:50:40 +0800
# 最近一次运行成功时间: 2026-03-22 18:50:40 +0800
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
# 最近一次运行测试时间: 2026-03-22 18:50:40 +0800
# 最近一次运行成功时间: 2026-03-22 18:50:40 +0800
# 测试目的: 验证非法字符表达式在 attr/type 两条路径都会报 verifier 错误。
# 对应功能实现文件路径: kernel_gen/dialect/symbol.py
# 对应 spec 文件路径: spec/dialect/symbol.md
def test_symbol_verifier_rejects_illegal_expression_characters() -> None:
    with pytest.raises(VerifyException, match="must contain identifiers"):
        SymbolExprAttr.from_expr("N/2").verify()
    with pytest.raises(VerifyException, match="must contain identifiers"):
        SymbolValueType.from_expr("N@1").verify()
