"""symbol ptr type.

功能说明:
- 定义 `!symbol.ptr` type。

API 列表:
- `class SymbolPtrType(dtype: Attribute, template_name: StringAttr | str | None = None)`

使用示例:
- `from kernel_gen.dialect.symbol.type import ...`

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/symbol/
- 功能实现: kernel_gen/dialect/symbol/type/ptr_type.py
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

from ..common import _normalize_symbol_ptr_template_name, _raise_verify_error, _verify_symbol_ptr_template_name
from .value_type import SymbolValueType

@irdl_attr_definition
class SymbolPtrType(ParametrizedAttribute, TypeAttribute):
    """符号指针类型。


    功能说明:
    - 表示 `!symbol.ptr<dtype>` 或 `!symbol.ptr<dtype, template = T>` 的指针类型承载。
    - 作为 DSL `Ptr(dtype)` 与 IR 类型的唯一桥接入口。

    使用示例:
    - SymbolPtrType(f32, template_name="T")

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/symbol/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol/
    """

    name = "symbol.ptr"

    dtype: Attribute = param_def(Attribute)
    template_name: StringAttr = param_def(StringAttr)

    def __init__(self: "SymbolPtrType", dtype: Attribute, template_name: StringAttr | str | None = None) -> None:
        """初始化 symbol.ptr 类型。

        功能说明:
        - 保存指针 element dtype 与可选 template name。
        - 默认不携带 template name，兼容 `SymbolPtrType(dtype)` 旧构造。

        使用示例:
        - SymbolPtrType(f32, "T")
        """

        super().__init__(dtype, _normalize_symbol_ptr_template_name(template_name))

    @classmethod
    def parse_parameters(cls: type["SymbolPtrType"], parser: AttrParser) -> Sequence[Attribute]:
        """解析 symbol.ptr 类型参数。


        功能说明:
        - 解析 `!symbol.ptr<dtype>` 或 `!symbol.ptr<dtype, template = T>` 中的 dtype 与 template。

        使用示例:
        - SymbolPtrType.parse_parameters(parser)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        parser.parse_punctuation("<", "Expected '<' for symbol ptr type.")
        dtype = parser.parse_type()
        template_name = StringAttr("")
        if parser.parse_optional_punctuation(",") is not None:
            keyword = parser.parse_identifier("Expected 'template' symbol.ptr option.")
            if keyword != "template":
                parser.raise_error("symbol.ptr only accepts template option")
            parser.parse_punctuation("=", "Expected '=' after symbol.ptr template option.")
            template_name = StringAttr(parser.parse_identifier("Expected symbol.ptr template name."))
        parser.parse_punctuation(">", "Expected '>' for symbol ptr type.")
        return (dtype, template_name)

    def print_parameters(self: "SymbolPtrType", printer: Printer) -> None:
        """打印 symbol.ptr 类型参数。


        功能说明:
        - 输出 `!symbol.ptr<dtype>` 的 dtype 和可选 template 部分。

        使用示例:
        - SymbolPtrType(f32).print_parameters(printer)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        printer.print_string("<")
        printer.print_attribute(self.dtype)
        template_name = self.template_name.data
        if template_name:
            printer.print_string(", template = ")
            printer.print_string(template_name)
        printer.print_string(">")

    def verify(self: "SymbolPtrType") -> None:
        """校验 symbol.ptr 的 dtype。


        功能说明:
        - 要求 dtype 为合法 TypeAttribute。
        - 明确拒绝 `!symbol.int<...>` 作为 ptr dtype。

        使用示例:
        - SymbolPtrType(f32).verify()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        if not isinstance(self.dtype, TypeAttribute):
            _raise_verify_error("symbol.ptr dtype must be type")
        if isinstance(self.dtype, SymbolValueType):
            _raise_verify_error("symbol.ptr dtype must not be symbol.int")
        _verify_symbol_ptr_template_name(self.template_name.data)

__all__ = ["SymbolPtrType"]
