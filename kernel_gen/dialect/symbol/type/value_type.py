"""symbol value type.

功能说明:
- 定义 `!symbol.int` type。

API 列表:
- `class SymbolValueType(expr: SymbolExprAttr)`

使用示例:
- `from kernel_gen.dialect.symbol.type import ...`

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/symbol/
- 功能实现: kernel_gen/dialect/symbol/type/value_type.py
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

from kernel_gen.dialect.nn import NnMemoryType

from ..attr.expr_attr import SymbolExprAttr

_UNKNOWN_SYMBOL_EXPR = "?"

@irdl_attr_definition
class SymbolValueType(ParametrizedAttribute, TypeAttribute):
    """仅表示整数符号值语义的类型。"""

    name = "symbol.int"

    expr: SymbolExprAttr = param_def(SymbolExprAttr)

    @classmethod
    def parse_parameters(cls: type["SymbolValueType"], parser: AttrParser) -> Sequence[Attribute]:
        """解析整数符号值类型参数。

        功能说明:
        - 解析 `!symbol.int<#symbol.expr<...>>` 或 alias attribute。
        - 拒绝旧 quoted string 参数。

        使用示例:
        - Parser(ctx, "!symbol.int<#symbol.expr<N>>").parse_attribute()
        """

        parser.parse_punctuation("<", "Expected '<' for symbol int type.")
        expr = parser.parse_attribute()
        parser.parse_punctuation(">", "Expected '>' for symbol int type.")
        if not isinstance(expr, SymbolExprAttr):
            parser.raise_error("symbol.int expects SymbolExprAttr parameter")
        return (expr,)

    def print_parameters(self: "SymbolValueType", printer: Printer) -> None:
        """打印整数符号值类型参数。

        功能说明:
        - 输出 `!symbol.int<#symbol.expr<...>>`。

        使用示例:
        - SymbolValueType.from_expr("N").print_parameters(printer)
        """

        printer.print_string("<")
        printer.print_attribute(self.expr)
        printer.print_string(">")

    def verify(self: "SymbolValueType") -> None:
        """校验整数符号值类型。

        功能说明:
        - 校验参数必须是合法 `SymbolExprAttr`。

        使用示例:
        - SymbolValueType.from_expr("N").verify()
        """

        self.expr.verify()

    def __str__(self: "SymbolValueType") -> str:
        """返回公开的 symbol.int 文本表示。

        功能说明:
        - 返回不带 dialect sigil 的调试文本。

        使用示例:
        - str(SymbolValueType.from_expr("N"))
        """

        return f"symbol.int<#{self.expr.name}<{self.expr.expr.data}>>"

    def get_value(self: "SymbolValueType") -> int | str:
        """返回 symbol.int 的公开值。


        功能说明:
        - 对已 canonical 的整数字面量返回 `int`。
        - 对符号表达返回存储的标准化字符串，不在读取时重复解析复杂表达式。

        使用示例:
        - SymbolValueType.from_expr("N").get_value()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        expr = self.expr.expr.data
        if expr == _UNKNOWN_SYMBOL_EXPR:
            return _UNKNOWN_SYMBOL_EXPR
        return int(expr) if expr.lstrip("-").isdigit() else expr

    def is_symbol(self: "SymbolValueType") -> bool:
        """判断当前值是否为非字面量符号表达。


        功能说明:
        - 纯数字常量返回 `False`。
        - 其他 symbol 表达返回 `True`。

        使用示例:
        - SymbolValueType.from_expr("1").is_symbol()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        expr = self.expr.expr.data
        return expr != _UNKNOWN_SYMBOL_EXPR and not expr.lstrip("-").isdigit()

    @classmethod
    def from_expr(cls: type["SymbolValueType"], expr: str) -> "SymbolValueType":
        """从字符串构造整数符号值类型。


        功能说明:
        - 统一创建只表示整数类型的 symbol value type。

        使用示例:
        - SymbolValueType.from_expr("N")

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        return cls(SymbolExprAttr.from_expr(expr))

__all__ = ["SymbolValueType"]
