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

_UNKNOWN_SYMBOL_EXPR = "?"


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
        if not isinstance(source_value.type, SymbolValueType):
            raise_verify_error(_ERROR_SCENE, f"{self.name} source must have type !symbol.int<#symbol.expr<expr>>")
        if not isinstance(self.result.type, (Float16Type, BFloat16Type, Float32Type, Float64Type)):
            raise_verify_error(_ERROR_SCENE, f"{self.name} result type must be float")

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
        if not isinstance(source_value.type, SymbolValueType):
            raise_verify_error(_ERROR_SCENE, f"{self.name} source must have type !symbol.int<#symbol.expr<expr>>")
        if not isinstance(self.result.type, IntegerType):
            raise_verify_error(_ERROR_SCENE, f"{self.name} result type must be integer")

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
            if not isinstance(self.result.type, SymbolValueType) or self.result.type.get_value() != _UNKNOWN_SYMBOL_EXPR:
                raise_verify_error(_ERROR_SCENE, f"{self.name} ptr result type must be !symbol.int<#symbol.expr<?>>")
            return
        if not isinstance(source_value.type, SymbolValueType):
            raise_verify_error(_ERROR_SCENE, f"{self.name} source must have type !symbol.int<#symbol.expr<expr>> or !symbol.ptr<dtype>")
        if not isinstance(self.result.type, IntegerType):
            raise_verify_error(_ERROR_SCENE, f"{self.name} result type must be integer")

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
