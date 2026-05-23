"""symbol const operation.

功能说明:
- 定义 symbol.const 与 constant materialization。

API 列表:
- `class SymbolConstOp(value: int | IntAttr, result_type: SymbolValueType | None = None)`

使用示例:
- `from kernel_gen.dialect.symbol.operation import ...`

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/symbol/
- 功能实现: kernel_gen/dialect/symbol/operation/const.py
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

@irdl_op_definition
class SymbolConstOp(IRDLOperation):
    """创建 symbol.int 常量。"""

    name = "symbol.const"
    traits = traits_def(Pure())

    value = attr_def(IntAttr)
    result = result_def(SymbolValueType)

    def __init__(
        self: "SymbolConstOp",
        value: int | IntAttr,
        result_type: SymbolValueType | None = None,
    ) -> None:
        """初始化 symbol.const。


        功能说明:
        - 记录整数常量 attribute，并生成对应的 `!symbol.int<#symbol.expr<...>>` 结果类型。
        - 公开构造只接受 Python `int` 或 `IntAttr`；`IntegerAttr` 属于 arith/builtin 常量属性，不作为 `symbol.const` 输入。
        - `bool` 与 `IntAttr(data=True/False)` 不是 symbol 整数常量输入；布尔比较 fold 由 `arith.constant i1` 承接。

        使用示例:
        - SymbolConstOp(3)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        if isinstance(value, IntAttr):
            if isinstance(value.data, bool):
                raise TypeError("SymbolConstOp value must be non-bool int or IntAttr with non-bool data")
            value_attr = value
        elif isinstance(value, int):
            if isinstance(value, bool):
                raise TypeError("SymbolConstOp value must be non-bool int or IntAttr with non-bool data")
            value_attr = IntAttr(value)
        else:
            raise TypeError("SymbolConstOp value must be non-bool int or IntAttr with non-bool data")
        inferred_type = result_type or SymbolValueType.from_expr(str(value_attr.data))
        super().__init__(result_types=[inferred_type], attributes={"value": value_attr})

    def verify_(self: "SymbolConstOp") -> None:
        """校验 symbol.const 的类型约束。


        功能说明:
        - 校验 value 必须为整型 attribute。
        - 校验 result 必须是 `!symbol.int<#symbol.expr<...>>`，且表达式与常量值一致。

        使用示例:
        - SymbolConstOp(3).verify_()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        if not isinstance(self.value, IntAttr):
            _raise_verify_error(f"{self.name} value must be integer attribute")
        if not isinstance(self.result.type, SymbolValueType):
            _raise_verify_error(f"{self.name} result type must be !symbol.int<#symbol.expr<expr>>")
        expected_expr = _normalize_expr(str(self.value.data))
        actual_expr = _normalize_expr(self.result.type.expr.expr.data)
        if actual_expr != expected_expr:
            _raise_verify_error(f"{self.name} result type must match value")

    def print(self: "SymbolConstOp", printer: Printer) -> None:
        """打印 symbol.const 自定义文本语法。


        功能说明:
        - 输出 `symbol.const <value> : !symbol.int<#symbol.expr<...>>` 的文本形式。

        使用示例:
        - SymbolConstOp(3)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        printer.print_string(" ")
        printer.print_string(str(self.value.data))
        printer.print_string(" : ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls: type["SymbolConstOp"], parser: AttrParser) -> "SymbolConstOp":
        """解析 symbol.const 自定义文本语法。


        功能说明:
        - 解析整数常量与 `!symbol.int<#symbol.expr<...>>` 结果类型。

        使用示例:
        - SymbolConstOp.parse(parser)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        value = parser.parse_integer(allow_boolean=False, allow_negative=True, context_msg=f" in {cls.name}")
        parser.parse_characters(":", f" in {cls.name}")
        result_type = parser.parse_type()
        return cls(value, result_type)

class SymbolConstantMaterializationInterface(ConstantMaterializationInterface):
    """将 folded 常量 materialize 为对应公开 IR operation。


    功能说明:
    - 为 xdsl folding 提供 symbol dialect 常量物化入口，不新增独立 cleanup pass。
    - `IntegerAttr + i1` 对应 symbol compare fold，物化为 `arith.constant`。
    - `IntAttr + SymbolValueType` 对应 symbol arithmetic fold，物化为 `symbol.const`。
    - `!symbol.int<#symbol.expr<??>>` result 接收确定 `IntAttr` 并物化为确定 `SymbolConstOp`。
    - 其它 value/type 组合返回 `None`，由 folding 框架保守保留原 op。

    使用示例:
    - SymbolConstantMaterializationInterface().materialize_constant(IntAttr(3), SymbolValueType.from_expr("3"))
    - SymbolConstantMaterializationInterface().materialize_constant(IntAttr(3), SymbolValueType.from_expr("?"))
    - SymbolConstantMaterializationInterface().materialize_constant(IntegerAttr.from_bool(True), i1)

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/symbol/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol/
    """

    def materialize_constant(self, value: Attribute, type: Attribute) -> Operation | None:
        """把 folded 常量 materialize 为公开 IR operation。

        功能说明:
        - `IntegerAttr + i1` 对应 symbol compare fold，物化为 `arith.constant`。
        - `IntAttr + SymbolValueType` 对应 symbol arithmetic fold，物化为 `symbol.const`。
        - `!symbol.int<#symbol.expr<??>>` 结果类型接收确定 `IntAttr` 并返回确定 `SymbolConstOp`。
        - 其它 value/type 组合返回 `None`，交由 folding 框架保守保留原 op。

        使用示例:
        - SymbolConstantMaterializationInterface().materialize_constant(IntAttr(3), SymbolValueType.from_expr("?"))
        - SymbolConstantMaterializationInterface().materialize_constant(IntegerAttr.from_bool(True), i1)
        """

        if isinstance(value, IntegerAttr) and type == i1:
            return arith.ConstantOp(value)
        if not isinstance(value, IntAttr):
            return None
        if not isinstance(type, SymbolValueType):
            return None
        type_value = type.get_value()
        if type_value == _UNKNOWN_SYMBOL_EXPR:
            return SymbolConstOp(value)
        if type_value != value.data:
            return None
        return SymbolConstOp(value, type)

__all__ = ["SymbolConstOp", "SymbolConstantMaterializationInterface"]
