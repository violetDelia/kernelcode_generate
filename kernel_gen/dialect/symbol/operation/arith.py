"""symbol arith operations.

功能说明:
- 定义 symbol 二元算术 op。

API 列表:
- `class SymbolAddOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- `class SymbolSubOp(...)`
- `class SymbolMulOp(...)`
- `class SymbolDivOp(...)`
- `class SymbolFloorDivOp(...)`
- `class SymbolMinOp(...)`
- `class SymbolMaxOp(...)`

使用示例:
- `from kernel_gen.dialect.symbol.operation import ...`

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/symbol/
- 功能实现: kernel_gen/dialect/symbol/operation/arith.py
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

_UNKNOWN_SYMBOL_EXPR = "?"

class _BaseSymbolBinaryArithOp(IRDLOperation, HasFolderInterface):
    """symbol 二元整数算术 op 基类。"""

    traits = traits_def(Pure())
    lhs = operand_def(Attribute)
    rhs = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(
        self: "_BaseSymbolBinaryArithOp",
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        result_type: Attribute,
    ) -> None:
        """初始化 symbol 二元整数算术 op。


        功能说明:
        - 设置两个 `!symbol.int<#symbol.expr<expr>>` 操作数与单个 `!symbol.int<#symbol.expr<expr>>` 结果类型。

        使用示例:
        - SymbolAddOp(lhs, rhs, SymbolValueType.from_expr("M + 1"))

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        super().__init__(operands=[lhs, rhs], result_types=[result_type])

    def verify_(self: "_BaseSymbolBinaryArithOp") -> None:
        """校验 symbol 二元整数算术 op 的类型约束。


        功能说明:
        - 校验 `lhs`、`rhs` 为 `!symbol.int<#symbol.expr<expr>>` 或循环迭代 `!symbol.iter<...>`。
        - 校验 `result` 为 `!symbol.int<#symbol.expr<expr>>`。

        使用示例:
        - SymbolMulOp(lhs, rhs, SymbolValueType.from_expr("M*N")).verify_()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        for field_name, field_operand in (("lhs", self.lhs), ("rhs", self.rhs)):
            operand = SSAValue.get(field_operand)
            if not _is_symbol_arith_operand_type(operand.type):
                _raise_verify_error(f"{self.name} {field_name} must have type !symbol.int<#symbol.expr<expr>> or !symbol.iter<...>")
        if not _is_symbol_int_type(self.result.type):
            _raise_verify_error(f"{self.name} result type must be !symbol.int<#symbol.expr<expr>>")
        lhs_type = SSAValue.get(self.lhs).type
        rhs_type = SSAValue.get(self.rhs).type
        result_type = SSAValue.get(self.result).type
        if _requires_unknown_arith_result(lhs_type, rhs_type) and not _is_unknown_symbol_int_type(result_type):
            _raise_verify_error(f"{self.name} result type must be !symbol.int<#symbol.expr<?>> when operand value contains ?")
        if not _requires_unknown_arith_result(lhs_type, rhs_type) and isinstance(result_type, SymbolValueType):
            inferred_expr = _infer_symbol_arith_result_expr(self.name, lhs_type, rhs_type)
            if inferred_expr is not None and result_type.get_value() == _UNKNOWN_SYMBOL_EXPR:
                lhs_expr = _symbol_arith_operand_expr_node(lhs_type)
                rhs_expr = _symbol_arith_operand_expr_node(rhs_type)
                if (
                    lhs_expr is not None
                    and rhs_expr is not None
                    and (_contains_symbol_expr_iter(lhs_expr) or _contains_symbol_expr_iter(rhs_expr))
                ):
                    _raise_verify_error(f"{self.name} result type must match canonical symbol expression")
            if inferred_expr is not None and result_type.get_value() != _UNKNOWN_SYMBOL_EXPR:
                accepted_exprs = (inferred_expr, *_alternate_symbol_arith_result_exprs(self.name, lhs_type, rhs_type))
                expected_types = tuple(SymbolValueType.from_expr(expr) for expr in accepted_exprs)
                if result_type not in expected_types:
                    _raise_verify_error(f"{self.name} result type must match canonical symbol expression")

    def fold(self: "_BaseSymbolBinaryArithOp") -> Sequence[SSAValue | Attribute] | None:
        """折叠静态整数 symbol 二元算术 op。


        功能说明:
        - 仅当 lhs/rhs 都是静态整数 `!symbol.int` 时折叠。
        - result 为 `!symbol.int<#symbol.expr<??>>` 时仍可物化确定 `symbol.const`。
        - 动态 symbol、`?` 与 iter 表达一律保守返回 `None`，避免误折叠。

        使用示例:
        - SymbolAddOp(SymbolConstOp(1).result, SymbolConstOp(2).result, SymbolValueType.from_expr("3")).fold()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        lhs_ssa = SSAValue.get(self.lhs)
        rhs_ssa = SSAValue.get(self.rhs)
        result_type = SSAValue.get(self.result).type
        if self.name == "symbol.min" and isinstance(result_type, SymbolValueType):
            step_value = _symbol_min_full_tile_step_value(lhs_ssa, rhs_ssa)
            if step_value is not None:
                step_static = _get_concrete_symbol_int_value(step_value.type)
                result_expr = result_type.get_value()
                if step_static is not None:
                    inferred_expr = _infer_symbol_arith_result_expr(self.name, lhs_ssa.type, rhs_ssa.type)
                    accepted_exprs: tuple[int | str, ...] = (
                        _UNKNOWN_SYMBOL_EXPR,
                        step_static,
                        *((inferred_expr,) if inferred_expr is not None else ()),
                    )
                    if result_expr in accepted_exprs:
                        if step_value.type != result_type:
                            return (step_value,)
                        return (IntAttr(step_static),)
                    return None
                if step_value.type == result_type:
                    return (step_value,)
                return None

        lhs_value = _get_concrete_symbol_int_value(lhs_ssa.type)
        rhs_value = _get_concrete_symbol_int_value(rhs_ssa.type)
        if lhs_value is None or rhs_value is None or not isinstance(result_type, SymbolValueType):
            return None

        if self.name == "symbol.add":
            result_value = lhs_value + rhs_value
        elif self.name == "symbol.sub":
            result_value = lhs_value - rhs_value
        elif self.name == "symbol.mul":
            result_value = lhs_value * rhs_value
        elif self.name == "symbol.div":
            if rhs_value == 0 or lhs_value % rhs_value != 0:
                return None
            result_value = lhs_value // rhs_value
        elif self.name == "symbol.floordiv":
            if rhs_value == 0:
                return None
            result_value = lhs_value // rhs_value
        elif self.name == "symbol.min":
            result_value = min(lhs_value, rhs_value)
        elif self.name == "symbol.max":
            result_value = max(lhs_value, rhs_value)
        else:
            return None

        result_expr = result_type.get_value()
        if result_expr != _UNKNOWN_SYMBOL_EXPR and result_expr != result_value:
            return None
        return (IntAttr(result_value),)

    def print(self: "_BaseSymbolBinaryArithOp", printer: Printer) -> None:
        """打印 symbol 二元整数算术 op 自定义文本语法。

        功能说明:
        - 输出 lhs/rhs operand、operand 类型与 result type。

        使用示例:
        - SymbolAddOp(lhs, rhs, result_type).print(printer)
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
    def parse(cls: type["_BaseSymbolBinaryArithOp"], parser: AttrParser) -> "_BaseSymbolBinaryArithOp":
        """解析 symbol 二元整数算术 op 自定义文本语法。

        功能说明:
        - 读取两个 operand、operand 类型与 result type 并构造具体算术 op。

        使用示例:
        - SymbolAddOp.parse(parser)
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
class SymbolAddOp(_BaseSymbolBinaryArithOp):
    """两个 symbol.int 值的整数加法。"""

    name = "symbol.add"


@irdl_op_definition
class SymbolSubOp(_BaseSymbolBinaryArithOp):
    """两个 symbol.int 值的整数减法。"""

    name = "symbol.sub"


@irdl_op_definition
class SymbolMulOp(_BaseSymbolBinaryArithOp):
    """两个 symbol.int 值的整数乘法。"""

    name = "symbol.mul"


@irdl_op_definition
class SymbolDivOp(_BaseSymbolBinaryArithOp):
    """两个 symbol.int 值的符号除法。"""

    name = "symbol.div"


@irdl_op_definition
class SymbolFloorDivOp(_BaseSymbolBinaryArithOp):
    """两个 symbol.int 值的符号整除。"""

    name = "symbol.floordiv"


@irdl_op_definition
class SymbolMinOp(_BaseSymbolBinaryArithOp):
    """两个 symbol.int 值的整数最小值。"""

    name = "symbol.min"


@irdl_op_definition
class SymbolMaxOp(_BaseSymbolBinaryArithOp):
    """两个 symbol.int 值的整数最大值。"""

    name = "symbol.max"

__all__ = ["SymbolAddOp", "SymbolSubOp", "SymbolMulOp", "SymbolDivOp", "SymbolFloorDivOp", "SymbolMinOp", "SymbolMaxOp"]
