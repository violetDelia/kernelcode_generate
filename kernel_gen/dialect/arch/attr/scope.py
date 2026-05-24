"""arch scope attr.

功能说明:
- 定义 `#arch.scope` attribute。

API 列表:
- `class ArchScopeAttr(scope: StringAttr)`

使用示例:
- `from kernel_gen.dialect.arch.attr import ...`

关联文件:
- spec: spec/dialect/arch.md
- test: test/dialect/arch/
- 功能实现: kernel_gen/dialect/arch/attr/scope.py
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar

from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE
from kernel_gen.core.contracts import raise_verify_error
from xdsl.dialects.builtin import ArrayAttr, IntAttr, StringAttr, SymbolRefAttr, i8
from xdsl.ir import Attribute, Dialect, Operation, ParametrizedAttribute, SSAValue, TypeAttribute
from xdsl.irdl import (
    AttrSizedOperandSegments,
    IRDLOperation,
    attr_def,
    irdl_attr_definition,
    irdl_op_definition,
    operand_def,
    param_def,
    result_def,
    var_operand_def,
)
from xdsl.parser import AttrParser
from xdsl.printer import Printer

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr, SymbolValueType
from kernel_gen.target import registry

# Localized helpers from retired package-internal modules.

_ERROR_SCENE = "dialect.arch verifier"

_BARRIER_SCOPE_VALUES = {"block", "thread", "subthread", "global"}

@irdl_attr_definition
class ArchScopeAttr(ParametrizedAttribute):
    """表示 `arch.barrier` 的 scope 属性。"""

    name = "arch.scope"

    scope: StringAttr = param_def(StringAttr)

    @classmethod
    def parse_parameters(cls: type["ArchScopeAttr"], parser: AttrParser) -> Sequence[Attribute]:
        """解析 arch.scope 参数。


        功能说明:
        - 支持 `#arch.scope<block>` / `thread` / `subthread` / `global>` 的文本。

        使用示例:
        - ArchScopeAttr.parse_parameters(parser)

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/arch/test_arch.py
        - 功能实现: kernel_gen/dialect/arch/
        """

        parser.parse_punctuation("<", "Expected '<' for arch.scope.")
        scope_name = parser.parse_identifier("Expected arch scope name.")
        parser.parse_punctuation(">", "Expected '>' for arch.scope.")
        return (StringAttr(scope_name),)

    def print_parameters(self: "ArchScopeAttr", printer: Printer) -> None:
        """打印 arch.scope 参数。

        功能说明:
        - 输出 `#arch.scope<...>` 尖括号内的公开 scope 名称。

        使用示例:
        - ArchScopeAttr.from_name("block").print_parameters(printer)
        """

        printer.print_string("<")
        printer.print_string(self.scope.data)
        printer.print_string(">")

    def verify(self: "ArchScopeAttr") -> None:
        """校验 arch.scope 参数。

        功能说明:
        - 确认 scope 文本属于 block/thread/subthread/global。

        使用示例:
        - ArchScopeAttr.from_name("thread").verify()
        """

        if self.scope.data not in _BARRIER_SCOPE_VALUES:
            raise_verify_error(_ERROR_SCENE, "arch.scope must be block/thread/subthread/global")

    @classmethod
    def from_name(cls: type["ArchScopeAttr"], name: str) -> "ArchScopeAttr":
        """按名称构造 arch.scope 属性。


        功能说明:
        - 为测试与实现提供统一的构造入口。

        使用示例:
        - ArchScopeAttr.from_name("block")

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/arch/test_arch.py
        - 功能实现: kernel_gen/dialect/arch/
        """

        return cls(StringAttr(name))

__all__ = ["ArchScopeAttr"]
