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

from .value_type import SymbolValueType

# Localized helpers from retired package-internal modules.

_SYMBOL_PTR_TEMPLATE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

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

def _normalize_symbol_ptr_template_name(template_name: StringAttr | str | None) -> StringAttr:
    """规整 symbol.ptr template name 参数。

    功能说明:
    - 把公开构造参数 `str | StringAttr | None` 统一为 `StringAttr`。

    使用示例:
    - attr = _normalize_symbol_ptr_template_name("T")
    """

    if template_name is None:
        return StringAttr("")
    if isinstance(template_name, StringAttr):
        return template_name
    if isinstance(template_name, str):
        return StringAttr(template_name)
    raise TypeError(
        ERROR_TEMPLATE.format(
            scene=_ERROR_SCENE,
            expected="symbol.ptr template_name must be str, StringAttr or None",
            actual=ERROR_ACTUAL,
            action=ERROR_ACTION,
        )
    )

def _verify_symbol_ptr_template_name(template_name: str) -> None:
    """校验 symbol.ptr template name 文本。

    功能说明:
    - 空字符串表示未携带 template name。
    - 非空时必须是公开 identifier 文本。

    使用示例:
    - _verify_symbol_ptr_template_name("T")
    """

    has_template = template_name != ""
    if not has_template:
        return
    is_identifier = _SYMBOL_PTR_TEMPLATE_PATTERN.fullmatch(template_name) is not None
    if not is_identifier:
        raise_verify_error(_ERROR_SCENE, "symbol.ptr template_name must be an identifier")


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
            raise_verify_error(_ERROR_SCENE, "symbol.ptr dtype must be type")
        if isinstance(self.dtype, SymbolValueType):
            raise_verify_error(_ERROR_SCENE, "symbol.ptr dtype must not be symbol.int")
        _verify_symbol_ptr_template_name(self.template_name.data)

__all__ = ["SymbolPtrType"]
