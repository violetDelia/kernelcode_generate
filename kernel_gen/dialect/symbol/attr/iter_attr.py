"""symbol iter attr.

功能说明:
- 定义 symbol iter attribute。

API 列表:
- `class SymbolIterAttr(start: SymbolExprAttr, end: SymbolExprAttr, step: SymbolExprAttr)`

使用示例:
- `from kernel_gen.dialect.symbol.attr import ...`

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/symbol/
- 功能实现: kernel_gen/dialect/symbol/attr/iter_attr.py
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE
from xdsl.dialects import arith
from xdsl.dialects.builtin import BFloat16Type, Float16Type, Float32Type, Float64Type, IntAttr, IntegerAttr, IntegerType, StringAttr, f32, f64, i1, i32
from xdsl.dialect_interfaces.constant_materialization import ConstantMaterializationInterface
from xdsl.ir import Attribute, Block, Dialect, Operation, ParametrizedAttribute, Region, SSAValue, TypeAttribute
from xdsl.irdl import (
    IRDLOperation,
    attr_def,
    irdl_attr_definition,
    irdl_op_definition,
    opt_operand_def,
    opt_result_def,
    operand_def,
    param_def,
    region_def,
    result_def,
    traits_def,
    var_operand_def,
)
from xdsl.interfaces import HasFolderInterface
from xdsl.parser import AttrParser
from xdsl.printer import Printer
from xdsl.traits import IsTerminator, NoTerminator, Pure
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import NnMemoryType

from ..common import _format_error
from ..expr.parser import (_SymbolExprNode, _SymbolExprToken, _SymbolExprParserBase, _SymbolExprTextParser, _SymbolExprAttrParser, _tokenize_symbol_expr, _make_symbol_expr_const, _make_symbol_expr_symbol, _make_symbol_expr_unknown, _is_symbol_expr_unknown, _contains_symbol_expr_unknown, _contains_symbol_expr_iter, _make_symbol_expr_iter, _get_symbol_expr_const, _get_concrete_symbol_expr_node_value, _linear_symbol_expr_terms, _make_symbol_expr_neg, _make_symbol_expr_add, _make_symbol_expr_sub, _make_symbol_expr_mul, _make_symbol_expr_keyword_binary, _make_symbol_expr_min, _make_symbol_expr_max, _symbol_expr_precedence, _format_symbol_expr_node, _format_symbol_expr_add, _parse_symbol_expr_from_text, _parse_symbol_expr_from_attr_parser, _normalize_expr, _evaluate_concrete_expr, _canonicalize_symbolic_expr, _is_supported_symbol_expr, _unwrap_symbol_expr_attr_text)
from .expr_attr import SymbolExprAttr

@irdl_attr_definition
class SymbolIterAttr(ParametrizedAttribute):
    """承载 `symbol.iter` 循环边界 attribute。"""

    name = "symbol.iter"

    start: SymbolExprAttr = param_def(SymbolExprAttr)
    end: SymbolExprAttr = param_def(SymbolExprAttr)
    step: SymbolExprAttr = param_def(SymbolExprAttr)

    @classmethod
    def parse_parameters(cls: type["SymbolIterAttr"], parser: AttrParser) -> Sequence[Attribute]:
        """解析 symbol.iter attribute 参数。


        功能说明:
        - 解析 `#symbol.iter<start = #symbol.expr<...>, end = #symbol.expr<...>, step = #symbol.expr<...>>` 语法。

        使用示例:
        - SymbolIterAttr.parse_parameters(parser)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        parser.parse_punctuation("<", "Expected '<' for symbol.iter attribute.")
        parser.parse_keyword("start", " in symbol.iter attribute")
        parser.parse_characters("=", " in symbol.iter attribute")
        start = parser.parse_attribute()
        if not isinstance(start, SymbolExprAttr):
            parser.raise_error("symbol.iter start expects SymbolExprAttr")
        parser.parse_characters(",", " in symbol.iter attribute")
        parser.parse_keyword("end", " in symbol.iter attribute")
        parser.parse_characters("=", " in symbol.iter attribute")
        end = parser.parse_attribute()
        if not isinstance(end, SymbolExprAttr):
            parser.raise_error("symbol.iter end expects SymbolExprAttr")
        parser.parse_characters(",", " in symbol.iter attribute")
        parser.parse_keyword("step", " in symbol.iter attribute")
        parser.parse_characters("=", " in symbol.iter attribute")
        step = parser.parse_attribute()
        if not isinstance(step, SymbolExprAttr):
            parser.raise_error("symbol.iter step expects SymbolExprAttr")
        parser.parse_punctuation(">", "Expected '>' for symbol.iter attribute.")
        return (start, end, step)

    def print_parameters(self: "SymbolIterAttr", printer: Printer) -> None:
        """打印 symbol.iter attribute 参数。


        功能说明:
        - 输出 `#symbol.iter<start = #symbol.expr<...>, end = #symbol.expr<...>, step = #symbol.expr<...>>` 语法。

        使用示例:
        - SymbolIterAttr.from_bounds("0", "N", "TILE_D0").print_parameters(printer)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        printer.print_string("<start = ")
        printer.print_attribute(self.start)
        printer.print_string(", end = ")
        printer.print_attribute(self.end)
        printer.print_string(", step = ")
        printer.print_attribute(self.step)
        printer.print_string(">")

    def verify(self: "SymbolIterAttr") -> None:
        """校验 symbol.iter attribute 参数。


        功能说明:
        - 校验 start/end/step 的 symbol 表达式合法性。

        使用示例:
        - SymbolIterAttr.from_bounds("0", "N", "TILE_D0").verify()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        self.start.verify()
        self.end.verify()
        self.step.verify()

    @classmethod
    def from_bounds(cls: type["SymbolIterAttr"], start: str, end: str, step: str) -> "SymbolIterAttr":
        """从 start/end/step 字符串构造 symbol.iter attribute。


        功能说明:
        - 统一构造 `#symbol.iter<start = #symbol.expr<...>, end = #symbol.expr<...>, step = #symbol.expr<...>>`。

        使用示例:
        - SymbolIterAttr.from_bounds("0", "N", "TILE_D0")

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        return cls(
            SymbolExprAttr.from_expr(start),
            SymbolExprAttr.from_expr(end),
            SymbolExprAttr.from_expr(step),
        )

__all__ = ["SymbolIterAttr"]
