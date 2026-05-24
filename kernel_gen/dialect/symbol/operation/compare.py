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
from kernel_gen.core.contracts import raise_verify_error
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

from ..attr import SymbolExprAttr, SymbolIterAttr
from ..type import SymbolIterType, SymbolPtrType, SymbolValueType

from ..type import SymbolIterType, SymbolValueType

# Localized helpers from retired package-internal modules.

_ERROR_SCENE = "dialect.symbol"

def _format_error(expected: str, actual: str = ERROR_ACTUAL) -> str:
    """格式化 symbol dialect 统一错误文本。

    功能说明:
    - 复用核心错误模板生成 verifier、value error 与 type error 的稳定文本。

    使用示例:
    - message = _format_error("symbol value type expected")
    """

    return ERROR_TEMPLATE.format(
        scene=_ERROR_SCENE,
        expected=expected,
        actual=actual,
        action=ERROR_ACTION,
    )

def _is_symbol_arith_operand_type(attr: Attribute) -> bool:
    """判断 attribute 是否可作为 symbol 算术/比较 operand。

    功能说明:
    - symbol 算术允许 `!symbol.int` 与 loop-carried `!symbol.iter`，供 tail `min(tile, dim - idx)` 使用。

    使用示例:
    - ok = _is_symbol_arith_operand_type(SymbolValueType.from_expr("N"))
    """

    if isinstance(attr, SymbolValueType):
        return True
    if isinstance(attr, SymbolIterType):
        return True
    return False

def _parse_symbol_binary_operand_types(parser: AttrParser, op_name: str) -> tuple[Attribute, Attribute]:
    """解析 symbol 二元 op 的 operand type 列表。

    功能说明:
    - 支持当前 printer 输出的 `lhs_type, rhs_type`。
    - 兼容 MLIR 常见的 parenthesized 形式 `(lhs_type, rhs_type)`。

    使用示例:
    - lhs_type, rhs_type = _parse_symbol_binary_operand_types(parser, "symbol.eq")
    """

    if parser.parse_optional_punctuation("(") is not None:
        lhs_type = parser.parse_type()
        parser.parse_characters(",", f" in {op_name} type list")
        rhs_type = parser.parse_type()
        parser.parse_punctuation(")", f" in {op_name} type list")
        return lhs_type, rhs_type
    lhs_type = parser.parse_type()
    parser.parse_characters(",", f" in {op_name} type list")
    rhs_type = parser.parse_type()
    return lhs_type, rhs_type

def _get_concrete_symbol_int_value(attr: Attribute) -> int | None:
    """提取静态可求值的 `!symbol.int` 整数值。


    功能说明:
    - 仅当 `attr` 是静态整数 `SymbolValueType` 时返回具体整数。
    - 动态 symbol 表达返回 `None`，供 fold 逻辑保守拒绝。

    使用示例:
    - _get_concrete_symbol_int_value(SymbolValueType.from_expr("3"))

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/symbol/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol/
    """

    if not isinstance(attr, SymbolValueType):
        return None
    value = attr.get_value()
    if not isinstance(value, int):
        return None
    return value


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
                raise_verify_error(_ERROR_SCENE, f"{self.name} {field_name} must have type !symbol.int<#symbol.expr<expr>> or !symbol.iter<...>")
        if self.result.type != i1:
            raise_verify_error(_ERROR_SCENE, f"{self.name} result type must be i1")

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
