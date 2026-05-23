"""symbol iter type.

功能说明:
- 定义 `!symbol.iter` type。

API 列表:
- `class SymbolIterType(start: SymbolExprAttr, end: SymbolExprAttr, step: SymbolExprAttr)`

使用示例:
- `from kernel_gen.dialect.symbol.type import ...`

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/symbol/
- 功能实现: kernel_gen/dialect/symbol/type/iter_type.py
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
from ..attr import SymbolExprAttr, SymbolIterAttr

@irdl_attr_definition
class SymbolIterType(ParametrizedAttribute, TypeAttribute):
    """表示循环迭代变量的 symbol 类型。"""

    name = "symbol.iter"

    start: SymbolExprAttr = param_def(SymbolExprAttr)
    end: SymbolExprAttr = param_def(SymbolExprAttr)
    step: SymbolExprAttr = param_def(SymbolExprAttr)

    @classmethod
    def parse_parameters(cls: type["SymbolIterType"], parser: AttrParser) -> Sequence[Attribute]:
        """解析循环迭代类型参数。


        功能说明:
        - 解析 `!symbol.iter<start = #symbol.expr<...>, end = #symbol.expr<...>, step = #symbol.expr<...>>` 语法。
        - 明确拒绝旧格式 `!symbol.iter<"expr">`。

        使用示例:
        - SymbolIterType.parse_parameters(parser)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        parser.parse_punctuation("<", "Expected '<' for symbol iter type.")
        parser.parse_keyword("start", " in symbol.iter type")
        parser.parse_characters("=", " in symbol.iter type")
        start = parser.parse_attribute()
        if not isinstance(start, SymbolExprAttr):
            parser.raise_error("symbol.iter start expects SymbolExprAttr")
        parser.parse_characters(",", " in symbol.iter type")
        parser.parse_keyword("end", " in symbol.iter type")
        parser.parse_characters("=", " in symbol.iter type")
        end = parser.parse_attribute()
        if not isinstance(end, SymbolExprAttr):
            parser.raise_error("symbol.iter end expects SymbolExprAttr")
        parser.parse_characters(",", " in symbol.iter type")
        parser.parse_keyword("step", " in symbol.iter type")
        parser.parse_characters("=", " in symbol.iter type")
        step = parser.parse_attribute()
        if not isinstance(step, SymbolExprAttr):
            parser.raise_error("symbol.iter step expects SymbolExprAttr")
        parser.parse_punctuation(">", "Expected '>' for symbol iter type.")
        return (start, end, step)

    def print_parameters(self: "SymbolIterType", printer: Printer) -> None:
        """打印循环迭代类型参数。


        功能说明:
        - 输出 `!symbol.iter<start = #symbol.expr<...>, end = #symbol.expr<...>, step = #symbol.expr<...>>` 的表达式参数。

        使用示例:
        - SymbolIterType.from_bounds("0", "N", "TILE_D0").print_parameters(printer)

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

    def verify(self: "SymbolIterType") -> None:
        """校验循环迭代类型参数。


        功能说明:
        - 复用 symbol.expr 的合法性校验，确保 start/end/step 都合法。

        使用示例:
        - SymbolIterType.from_bounds("0", "N", "TILE_D0").verify()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        self.start.verify()
        self.end.verify()
        self.step.verify()

    def __str__(self: "SymbolIterType") -> str:
        """返回公开的 symbol.iter 文本表示。


        功能说明:
        - 生成 `symbol.iter<start,end,step>` 形式的字符串表示。

        使用示例:
        - str(SymbolIterType.from_bounds("0", "N", "TILE_D0"))

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        return (
            "symbol.iter<"
            f"start={_normalize_expr(self.start.expr.data)}, "
            f"end={_normalize_expr(self.end.expr.data)}, "
            f"step={_normalize_expr(self.step.expr.data)}>"
        )

    @classmethod
    def from_bounds(cls: type["SymbolIterType"], start: str, end: str, step: str) -> "SymbolIterType":
        """从 start/end/step 构造循环迭代类型。


        功能说明:
        - 统一创建 `!symbol.iter<start = #symbol.expr<...>, end = #symbol.expr<...>, step = #symbol.expr<...>>`。

        使用示例:
        - SymbolIterType.from_bounds("0", "N", "TILE_D0")

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

    @classmethod
    def from_attr(cls: type["SymbolIterType"], attr: SymbolIterAttr) -> "SymbolIterType":
        """从 symbol.iter attribute 构造循环迭代类型。


        功能说明:
        - 将 `#symbol.iter<...>` 转换为对应的 `!symbol.iter<...>` 类型。

        使用示例:
        - SymbolIterType.from_attr(SymbolIterAttr.from_bounds("0", "N", "TILE_D0"))

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        return cls(attr.start, attr.end, attr.step)

__all__ = ["SymbolIterType"]
