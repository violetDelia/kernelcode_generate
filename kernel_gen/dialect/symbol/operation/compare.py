"""symbol compare operations.

功能说明:
- 定义 symbol compare op。

API 列表:
- `class SymbolEqOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- `class SymbolNeOp(...)`
- `class SymbolLtOp(...)`
- `class SymbolLeOp(...)`
- `class SymbolGtOp(...)`
- `class SymbolGeOp(...)`

使用示例:
- `from kernel_gen.dialect.symbol.operation import ...`

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/symbol/
- 功能实现: kernel_gen/dialect/symbol/operation/compare.py
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

from ..common import _format_error, _raise_verify_error
from ..expr.parser import (_SymbolExprNode, _SymbolExprToken, _SymbolExprParserBase, _SymbolExprTextParser, _SymbolExprAttrParser, _tokenize_symbol_expr, _make_symbol_expr_const, _make_symbol_expr_symbol, _make_symbol_expr_unknown, _is_symbol_expr_unknown, _contains_symbol_expr_unknown, _contains_symbol_expr_iter, _make_symbol_expr_iter, _get_symbol_expr_const, _get_concrete_symbol_expr_node_value, _linear_symbol_expr_terms, _make_symbol_expr_neg, _make_symbol_expr_add, _make_symbol_expr_sub, _make_symbol_expr_mul, _make_symbol_expr_keyword_binary, _make_symbol_expr_min, _make_symbol_expr_max, _symbol_expr_precedence, _format_symbol_expr_node, _format_symbol_expr_add, _parse_symbol_expr_from_text, _parse_symbol_expr_from_attr_parser, _normalize_expr, _evaluate_concrete_expr, _canonicalize_symbolic_expr, _is_supported_symbol_expr, _unwrap_symbol_expr_attr_text)
from ..attr import SymbolExprAttr, SymbolIterAttr
from ..type import SymbolIterType, SymbolPtrType, SymbolValueType
from .common import (_verify_axis, _entry_to_expr, _infer_result_type, _is_symbol_int_type, _is_symbol_arith_operand_type, _is_unknown_symbol_int_type, _parse_symbol_binary_operand_types, _symbol_iter_type_expr_node, _symbol_arith_operand_expr_node, _symbol_arith_operand_contains_unknown, _symbol_expr_bounds_are_full_tiles, _linear_distance_is_positive_multiple, _symbol_expr_full_tile_residual_step, _symbol_expr_full_tile_min_step, _symbol_min_full_tile_step_value, _requires_unknown_arith_result, _infer_symbol_arith_result_expr, _alternate_symbol_arith_result_exprs, _get_concrete_symbol_int_value)

class _BaseSymbolCompareOp(IRDLOperation, HasFolderInterface):
    """symbol 二元整数比较 op 基类。"""

    traits = traits_def(Pure())
    lhs = operand_def(Attribute)
    rhs = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(
        self: "_BaseSymbolCompareOp",
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        result_type: Attribute = i1,
    ) -> None:
        """初始化 symbol 二元整数比较 op。


        功能说明:
        - 设置两个 `!symbol.int<#symbol.expr<expr>>` 操作数与单个 `i1` 结果类型。

        使用示例:
        - SymbolEqOp(lhs, rhs, i1)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        super().__init__(operands=[lhs, rhs], result_types=[result_type])

    def verify_(self: "_BaseSymbolCompareOp") -> None:
        """校验 symbol 二元整数比较 op 的类型约束。


        功能说明:
        - 校验 `lhs` 与 `rhs` 均为 `!symbol.int<#symbol.expr<expr>>` 或循环迭代 `!symbol.iter<...>`。
        - 校验 `result` 固定为 `i1`。

        使用示例:
        - SymbolLtOp(lhs, rhs, i1).verify_()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        for field_name, field_operand in (("lhs", self.lhs), ("rhs", self.rhs)):
            operand = SSAValue.get(field_operand)
            if not _is_symbol_arith_operand_type(operand.type):
                _raise_verify_error(f"{self.name} {field_name} must have type !symbol.int<#symbol.expr<expr>> or !symbol.iter<...>")
        if self.result.type != i1:
            _raise_verify_error(f"{self.name} result type must be i1")

    def fold(self: "_BaseSymbolCompareOp") -> Sequence[SSAValue | Attribute] | None:
        """折叠静态整数 symbol 比较 op。

        功能说明:
        - 仅当 lhs/rhs 均为静态整数 `!symbol.int` 时折叠。
        - 结果固定物化为 `i1` bool 常量。
        - 动态 symbol、`?` 与 iter operand 不折叠。

        使用示例:
        - SymbolEqOp(SymbolConstOp(1).result, SymbolConstOp(1).result).fold()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        lhs_value = _get_concrete_symbol_int_value(SSAValue.get(self.lhs).type)
        rhs_value = _get_concrete_symbol_int_value(SSAValue.get(self.rhs).type)
        if lhs_value is None or rhs_value is None or self.result.type != i1:
            return None
        if self.name == "symbol.eq":
            result_value = lhs_value == rhs_value
        elif self.name == "symbol.ne":
            result_value = lhs_value != rhs_value
        elif self.name == "symbol.lt":
            result_value = lhs_value < rhs_value
        elif self.name == "symbol.le":
            result_value = lhs_value <= rhs_value
        elif self.name == "symbol.gt":
            result_value = lhs_value > rhs_value
        elif self.name == "symbol.ge":
            result_value = lhs_value >= rhs_value
        else:
            return None
        return (IntegerAttr.from_bool(result_value),)

    def print(self: "_BaseSymbolCompareOp", printer: Printer) -> None:
        """打印 symbol 二元整数比较 op 自定义文本语法。

        功能说明:
        - 输出 lhs/rhs operand、operand 类型与 i1 result type。

        使用示例:
        - SymbolEqOp(lhs, rhs).print(printer)
        """

        printer.print_string(" ")
        printer.print_ssa_value(self.lhs)
        printer.print_string(", ")
        printer.print_ssa_value(self.rhs)
        printer.print_string(" : ")
        printer.print_attribute(SSAValue.get(self.lhs).type)
        printer.print_string(", ")
        printer.print_attribute(SSAValue.get(self.rhs).type)
        printer.print_string(" -> ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls: type["_BaseSymbolCompareOp"], parser: AttrParser) -> "_BaseSymbolCompareOp":
        """解析 symbol 二元整数比较 op 自定义文本语法。

        功能说明:
        - 读取两个 operand、operand 类型与比较结果类型并构造具体比较 op。

        使用示例:
        - SymbolEqOp.parse(parser)
        """

        unresolved_lhs = parser.parse_unresolved_operand()
        parser.parse_characters(",", f" in {cls.name}")
        unresolved_rhs = parser.parse_unresolved_operand()
        parser.parse_characters(":", f" in {cls.name}")
        lhs_type, rhs_type = _parse_symbol_binary_operand_types(parser, cls.name)
        parser.parse_characters("->", f" in {cls.name}")
        result_type = parser.parse_type()

        lhs = parser.resolve_operand(unresolved_lhs, lhs_type)
        rhs = parser.resolve_operand(unresolved_rhs, rhs_type)
        return cls(lhs, rhs, result_type)

@irdl_op_definition
class SymbolEqOp(_BaseSymbolCompareOp):
    """两个 symbol.int 值的相等比较。"""

    name = "symbol.eq"


@irdl_op_definition
class SymbolNeOp(_BaseSymbolCompareOp):
    """两个 symbol.int 值的不等比较。"""

    name = "symbol.ne"


@irdl_op_definition
class SymbolLtOp(_BaseSymbolCompareOp):
    """两个 symbol.int 值的小于比较。"""

    name = "symbol.lt"


@irdl_op_definition
class SymbolLeOp(_BaseSymbolCompareOp):
    """两个 symbol.int 值的小于等于比较。"""

    name = "symbol.le"


@irdl_op_definition
class SymbolGtOp(_BaseSymbolCompareOp):
    """两个 symbol.int 值的大于比较。"""

    name = "symbol.gt"


@irdl_op_definition
class SymbolGeOp(_BaseSymbolCompareOp):
    """两个 symbol.int 值的大于等于比较。"""

    name = "symbol.ge"

__all__ = ["SymbolEqOp", "SymbolNeOp", "SymbolLtOp", "SymbolLeOp", "SymbolGtOp", "SymbolGeOp"]
