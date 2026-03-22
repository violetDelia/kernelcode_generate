"""Symbol dialect definitions.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 定义仅表示整数符号值语义的 symbol dialect。
- 提供 `SymbolExprAttr` 与 `SymbolValueType`，不区分 `int8/int64` 等整型宽度。

使用示例:
- from kernel_gen.dialect.symbol import Symbol, SymbolExprAttr, SymbolValueType

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/test_symbol_dialect.py
- 功能实现: kernel_gen/dialect/symbol.py
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from xdsl.dialects.builtin import StringAttr
from xdsl.ir import Attribute, Dialect, ParametrizedAttribute, TypeAttribute
from xdsl.irdl import irdl_attr_definition, param_def
from xdsl.parser import AttrParser
from xdsl.printer import Printer
from xdsl.utils.exceptions import VerifyException

_SYMBOL_EXPR_PATTERN = re.compile(
    r"^(?:[A-Za-z_][A-Za-z0-9_]*|[0-9]+)(?:\s*[+\-*]\s*(?:[A-Za-z_][A-Za-z0-9_]*|[0-9]+))*$"
)


def _normalize_expr(expr: str) -> str:
    """标准化符号表达字符串。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 去除首尾空白，供 verifier 与打印使用。

    使用示例:
    - _normalize_expr("  N + 1  ")

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol_dialect.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    return expr.strip()


@irdl_attr_definition
class SymbolExprAttr(ParametrizedAttribute):
    """承载单个整数符号表达。"""

    name = "symbol.expr"

    expr: StringAttr = param_def(StringAttr)

    @classmethod
    def parse_parameters(cls, parser: AttrParser) -> Sequence[Attribute]:
        """解析符号表达参数。"""

        parser.parse_punctuation("<", "Expected '<' for symbol expr attribute.")
        expr = parser.parse_str_literal("Expected quoted symbol expression.")
        parser.parse_punctuation(">", "Expected '>' for symbol expr attribute.")
        return (StringAttr(expr),)

    def print_parameters(self, printer: Printer) -> None:
        """打印符号表达参数。"""

        printer.print_string("<")
        printer.print_string_literal(_normalize_expr(self.expr.data))
        printer.print_string(">")

    def verify(self) -> None:
        """校验符号表达。"""

        expr = _normalize_expr(self.expr.data)
        if not expr:
            raise VerifyException("symbol expr must not be empty")
        if not _SYMBOL_EXPR_PATTERN.fullmatch(expr):
            raise VerifyException("symbol expr must contain identifiers, integers, spaces, +, - or *")

    @classmethod
    def from_expr(cls, expr: str) -> "SymbolExprAttr":
        """从字符串构造符号表达 attribute。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 为测试与实现提供统一的构造入口。

        使用示例:
        - SymbolExprAttr.from_expr("N")

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        return cls(StringAttr(_normalize_expr(expr)))


@irdl_attr_definition
class SymbolValueType(ParametrizedAttribute, TypeAttribute):
    """仅表示整数符号值语义的类型。"""

    name = "symbol.int"

    expr: SymbolExprAttr = param_def(SymbolExprAttr)

    @classmethod
    def parse_parameters(cls, parser: AttrParser) -> Sequence[Attribute]:
        """解析整数符号值类型参数。"""

        parser.parse_punctuation("<", "Expected '<' for symbol int type.")
        expr = parser.parse_str_literal("Expected quoted symbol expression.")
        parser.parse_punctuation(">", "Expected '>' for symbol int type.")
        return (SymbolExprAttr.from_expr(expr),)

    def print_parameters(self, printer: Printer) -> None:
        """打印整数符号值类型参数。"""

        printer.print_string("<")
        printer.print_string_literal(_normalize_expr(self.expr.expr.data))
        printer.print_string(">")

    def verify(self) -> None:
        """校验整数符号值类型。"""

        self.expr.verify()

    @classmethod
    def from_expr(cls, expr: str) -> "SymbolValueType":
        """从字符串构造整数符号值类型。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 统一创建只表示整数类型的 symbol value type。

        使用示例:
        - SymbolValueType.from_expr("N")

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        return cls(SymbolExprAttr.from_expr(expr))


Symbol = Dialect(
    "symbol",
    [],
    [
        SymbolExprAttr,
        SymbolValueType,
    ],
)

__all__ = [
    "Symbol",
    "SymbolExprAttr",
    "SymbolValueType",
]
