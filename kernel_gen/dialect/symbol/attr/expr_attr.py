"""symbol expr attr.

功能说明:
- 定义 `#symbol.expr` attribute。

API 列表:
- `class SymbolExprAttr(expr: StringAttr)`

使用示例:
- `from kernel_gen.dialect.symbol.attr import ...`

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/symbol/
- 功能实现: kernel_gen/dialect/symbol/attr/expr_attr.py
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

@irdl_attr_definition
class SymbolExprAttr(ParametrizedAttribute):
    """承载单个整数符号表达。"""

    name = "symbol.expr"

    expr: StringAttr = param_def(StringAttr)

    def __init__(self: "SymbolExprAttr", expr: StringAttr) -> None:
        """规范化构造期表达式。

        功能说明:
        - 公开构造 `SymbolExprAttr(StringAttr(...))` 与 `from_expr(...)` 使用同一 canonical 规则。
        - 拒绝 quoted string、裸 `/`、`//` 与非法表达式。

        使用示例:
        - SymbolExprAttr(StringAttr("1 + N"))
        """

        super().__init__(StringAttr(_normalize_expr(expr.data)))

    @classmethod
    def parse_parameters(cls: type["SymbolExprAttr"], parser: AttrParser) -> Sequence[Attribute]:
        """解析符号表达参数。

        功能说明:
        - 解析 `#symbol.expr<N + 1>` 形式的非 quoted 公开语法。
        - 只使用 xDSL 公开 parser token 接口。

        使用示例:
        - Parser(ctx, "#symbol.expr<N>").parse_attribute()
        """

        parser.parse_punctuation("<", "Expected '<' for symbol expr attribute.")
        expr = _parse_symbol_expr_from_attr_parser(parser)
        parser.parse_punctuation(">", "Expected '>' for symbol expr attribute.")
        return (StringAttr(_format_symbol_expr_node(expr)),)

    def print_parameters(self: "SymbolExprAttr", printer: Printer) -> None:
        """打印符号表达参数。

        功能说明:
        - 输出 `#symbol.expr<...>` 非 quoted 公开语法。
        - 表达式在构造与 parse 阶段已经完成 canonicalize，打印阶段直接使用存储文本，
          避免复杂动态表达式在 dump 时重复重解析。

        使用示例:
        - SymbolExprAttr.from_expr("N").print_parameters(printer)
        """

        printer.print_string("<")
        printer.print_string(self.expr.data)
        printer.print_string(">")

    def verify(self: "SymbolExprAttr") -> None:
        """校验符号表达。

        功能说明:
        - 确认内部表达不为空且不含构造入口会拒绝的 legacy 除法 / quoted 文本。
        - 公开语法的完整解析校验已经在构造与 parse 阶段完成；verify 阶段不重复
          解析复杂表达式，避免大规模 dump / memory verifier 反复触发 parser。

        使用示例:
        - SymbolExprAttr.from_expr("N floordiv 2").verify()
        """

        expr = self.expr.data
        if not expr:
            _raise_verify_error("symbol expr must not be empty")
        if '"' in expr or "'" in expr or "/" in expr:
            _raise_verify_error("symbol expr must contain identifiers, ?, integers, +, -, *, floordiv, ceildiv, mod, min(lhs, rhs) or max(lhs, rhs)")

    @classmethod
    def from_expr(cls: type["SymbolExprAttr"], expr: str) -> "SymbolExprAttr":
        """从字符串构造符号表达 attribute。


        功能说明:
        - 为测试与实现提供统一的构造入口。

        使用示例:
        - SymbolExprAttr.from_expr("N")

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        return cls(StringAttr(_normalize_expr(expr)))

__all__ = ["SymbolExprAttr"]
