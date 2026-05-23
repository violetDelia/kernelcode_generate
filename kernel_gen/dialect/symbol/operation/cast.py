"""symbol cast operations.

功能说明:
- 定义 symbol cast/to_int/to_float op。

API 列表:
- `class SymbolToFloatOp(value: SSAValue, result_type: Attribute)`
- `class SymbolToIntOp(value: SSAValue, result_type: Attribute)`
- `class SymbolCastOp(value: SSAValue, result_type: Attribute)`

使用示例:
- `from kernel_gen.dialect.symbol.operation import ...`

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/symbol/
- 功能实现: kernel_gen/dialect/symbol/operation/cast.py
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

@irdl_op_definition
class SymbolToFloatOp(IRDLOperation):
    """将 symbol.int 标量转换为 f32。"""

    name = "symbol.to_float"
    traits = traits_def(Pure())

    source = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(
        self: "SymbolToFloatOp",
        source: SSAValue | Operation,
        result_type: Attribute = f32,
    ) -> None:
        """初始化 symbol.to_float。


        功能说明:
        - 设置单个 `!symbol.int<#symbol.expr<expr>>` 操作数与浮点结果类型。

        使用示例:
        - SymbolToFloatOp(source, f32)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        super().__init__(operands=[source], result_types=[result_type])

    def verify_(self: "SymbolToFloatOp") -> None:
        """校验 symbol.to_float 的类型约束。


        功能说明:
        - 校验 source 必须为 `!symbol.int<#symbol.expr<expr>>`。
        - 校验 result 必须为浮点类型。

        使用示例:
        - SymbolToFloatOp(source, f32).verify_()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        source_value = SSAValue.get(self.source)
        if not _is_symbol_int_type(source_value.type):
            _raise_verify_error(f"{self.name} source must have type !symbol.int<#symbol.expr<expr>>")
        if not isinstance(self.result.type, (Float16Type, BFloat16Type, Float32Type, Float64Type)):
            _raise_verify_error(f"{self.name} result type must be float")

    def print(self: "SymbolToFloatOp", printer: Printer) -> None:
        """打印 symbol.to_float 自定义文本语法。

        功能说明:
        - 输出 source operand、source type 与浮点 result type。

        使用示例:
        - SymbolToFloatOp(source, f32).print(printer)
        """

        printer.print_string(" ")
        printer.print_ssa_value(self.source)
        printer.print_string(" : ")
        printer.print_attribute(SSAValue.get(self.source).type)
        printer.print_string(" -> ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls: type["SymbolToFloatOp"], parser: AttrParser) -> "SymbolToFloatOp":
        """解析 symbol.to_float 自定义文本语法。

        功能说明:
        - 读取 source operand、source type 与浮点 result type 并构造 op。

        使用示例:
        - SymbolToFloatOp.parse(parser)
        """

        unresolved_source = parser.parse_unresolved_operand()
        parser.parse_characters(":", f" in {cls.name}")
        source_type = parser.parse_type()
        parser.parse_characters("->", f" in {cls.name}")
        result_type = parser.parse_type()
        source = parser.resolve_operand(unresolved_source, source_type)
        return cls(source, result_type)


@irdl_op_definition
class SymbolToIntOp(IRDLOperation):
    """将 symbol.int 标量转换为普通整型。"""

    name = "symbol.to_int"
    traits = traits_def(Pure())

    source = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(
        self: "SymbolToIntOp",
        source: SSAValue | Operation,
        result_type: Attribute = i32,
    ) -> None:
        """初始化 symbol.to_int。


        功能说明:
        - 设置单个 `!symbol.int<#symbol.expr<expr>>` 操作数与普通整型结果类型。

        使用示例:
        - SymbolToIntOp(source, i32)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        super().__init__(operands=[source], result_types=[result_type])

    def verify_(self: "SymbolToIntOp") -> None:
        """校验 symbol.to_int 的类型约束。


        功能说明:
        - 校验 source 必须为 `!symbol.int<#symbol.expr<expr>>`。
        - 校验 result 必须为 builtin 整型（`IntegerType`）。

        使用示例:
        - SymbolToIntOp(source, i32).verify_()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        source_value = SSAValue.get(self.source)
        if not _is_symbol_int_type(source_value.type):
            _raise_verify_error(f"{self.name} source must have type !symbol.int<#symbol.expr<expr>>")
        if not isinstance(self.result.type, IntegerType):
            _raise_verify_error(f"{self.name} result type must be integer")

    def print(self: "SymbolToIntOp", printer: Printer) -> None:
        """打印 symbol.to_int 自定义文本语法。

        功能说明:
        - 输出 source operand、source type 与整数 result type。

        使用示例:
        - SymbolToIntOp(source, i32).print(printer)
        """

        printer.print_string(" ")
        printer.print_ssa_value(self.source)
        printer.print_string(" : ")
        printer.print_attribute(SSAValue.get(self.source).type)
        printer.print_string(" -> ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls: type["SymbolToIntOp"], parser: AttrParser) -> "SymbolToIntOp":
        """解析 symbol.to_int 自定义文本语法。

        功能说明:
        - 读取 source operand、source type 与整数 result type 并构造 op。

        使用示例:
        - SymbolToIntOp.parse(parser)
        """

        unresolved_source = parser.parse_unresolved_operand()
        parser.parse_characters(":", f" in {cls.name}")
        source_type = parser.parse_type()
        parser.parse_characters("->", f" in {cls.name}")
        result_type = parser.parse_type()
        source = parser.resolve_operand(unresolved_source, source_type)
        return cls(source, result_type)


@irdl_op_definition
class SymbolCastOp(IRDLOperation):
    """转换 symbol.int 标量或 symbol.ptr 指针。"""

    name = "symbol.cast"
    traits = traits_def(Pure())

    source = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(
        self: "SymbolCastOp",
        source: SSAValue | Operation,
        result_type: Attribute = i32,
    ) -> None:
        """初始化 symbol.cast。


        功能说明:
        - 设置单个 `!symbol.int<#symbol.expr<expr>>` 操作数与普通整型结果类型。
        - 或设置单个 `!symbol.ptr<dtype>` 操作数与 `!symbol.int<#symbol.expr<??>>` 结果类型。
        - 供 `emit_c/npu_demo` 读取 `symbol.cast` 文本输入。

        使用示例:
        - SymbolCastOp(source, i32)

        关联文件:
        - spec: spec/dsl/gen_kernel/emit.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        super().__init__(operands=[source], result_types=[result_type])

    def verify_(self: "SymbolCastOp") -> None:
        """校验 symbol.cast 的类型约束。


        功能说明:
        - 校验 source 必须为 `!symbol.int<#symbol.expr<expr>>` 或 `!symbol.ptr<dtype>`。
        - `!symbol.int` source 的 result 必须为 builtin 整型。
        - `!symbol.ptr` source 的 result 必须为 `!symbol.int<#symbol.expr<??>>`。

        使用示例:
        - SymbolCastOp(source, i32).verify_()

        关联文件:
        - spec: spec/dsl/gen_kernel/emit.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """
        source_value = SSAValue.get(self.source)
        if isinstance(source_value.type, SymbolPtrType):
            if not _is_unknown_symbol_int_type(self.result.type):
                _raise_verify_error(f"{self.name} ptr result type must be !symbol.int<#symbol.expr<?>>")
            return
        if not _is_symbol_int_type(source_value.type):
            _raise_verify_error(f"{self.name} source must have type !symbol.int<#symbol.expr<expr>> or !symbol.ptr<dtype>")
        if not isinstance(self.result.type, IntegerType):
            _raise_verify_error(f"{self.name} result type must be integer")

    def print(self: "SymbolCastOp", printer: Printer) -> None:
        """打印 symbol.cast 自定义文本语法。

        功能说明:
        - 输出 source operand、source type 与 cast result type。

        使用示例:
        - SymbolCastOp(source, i32).print(printer)
        """

        printer.print_string(" ")
        printer.print_ssa_value(self.source)
        printer.print_string(" : ")
        printer.print_attribute(SSAValue.get(self.source).type)
        printer.print_string(" -> ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls: type["SymbolCastOp"], parser: AttrParser) -> "SymbolCastOp":
        """解析 symbol.cast 自定义文本语法。

        功能说明:
        - 读取 source operand、source type 与 cast result type 并构造 op。

        使用示例:
        - SymbolCastOp.parse(parser)
        """

        unresolved_source = parser.parse_unresolved_operand()
        parser.parse_characters(":", f" in {cls.name}")
        source_type = parser.parse_type()
        parser.parse_characters("->", f" in {cls.name}")
        result_type = parser.parse_type()
        source = parser.resolve_operand(unresolved_source, source_type)
        return cls(source, result_type)

__all__ = ["SymbolToFloatOp", "SymbolToIntOp", "SymbolCastOp"]
