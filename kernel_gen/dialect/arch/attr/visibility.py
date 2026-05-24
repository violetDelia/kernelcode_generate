"""arch visibility attr.

功能说明:
- 定义 `#arch.visibility` attribute。

API 列表:
- `class ArchVisibilityAttr(visibility: StringAttr)`

使用示例:
- `from kernel_gen.dialect.arch.attr import ...`

关联文件:
- spec: spec/dialect/arch.md
- test: test/dialect/arch/
- 功能实现: kernel_gen/dialect/arch/attr/visibility.py
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

_BARRIER_VISIBLE_SPACES = {"tsm", "tlm"}

@irdl_attr_definition
class ArchVisibilityAttr(ParametrizedAttribute):
    """表示 `arch.barrier` 的聚合可见域属性。"""

    name = "arch.visibility"

    visibility: StringAttr = param_def(StringAttr)

    @classmethod
    def parse_parameters(cls: type["ArchVisibilityAttr"], parser: AttrParser) -> Sequence[Attribute]:
        """解析 arch.visibility 参数。


        功能说明:
        - 支持 `#arch.visibility<tsm>` 与 `#arch.visibility<tlm>` 的文本。

        使用示例:
        - ArchVisibilityAttr.parse_parameters(parser)

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/arch/test_arch.py
        - 功能实现: kernel_gen/dialect/arch/
        """

        parser.parse_punctuation("<", "Expected '<' for arch.visibility.")
        visibility_name = parser.parse_identifier("Expected arch visibility name.")
        parser.parse_punctuation(">", "Expected '>' for arch.visibility.")
        return (StringAttr(visibility_name),)

    def print_parameters(self: "ArchVisibilityAttr", printer: Printer) -> None:
        """打印 arch.visibility 参数。

        功能说明:
        - 输出 `#arch.visibility<...>` 尖括号内的公开可见域名称。

        使用示例:
        - ArchVisibilityAttr.from_name("tsm").print_parameters(printer)
        """

        printer.print_string("<")
        printer.print_string(self.visibility.data)
        printer.print_string(">")

    def verify(self: "ArchVisibilityAttr") -> None:
        """校验 arch.visibility 参数。

        功能说明:
        - 确认可见域文本属于 tsm/tlm。

        使用示例:
        - ArchVisibilityAttr.from_name("tlm").verify()
        """

        if self.visibility.data not in _BARRIER_VISIBLE_SPACES:
            raise_verify_error(_ERROR_SCENE, "arch.visibility must be tsm/tlm")

    @classmethod
    def from_name(cls: type["ArchVisibilityAttr"], name: str) -> "ArchVisibilityAttr":
        """按名称构造 arch.visibility 属性。


        功能说明:
        - 为测试与实现提供统一的 barrier 可见域构造入口。

        使用示例:
        - ArchVisibilityAttr.from_name("tsm")

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/arch/test_arch.py
        - 功能实现: kernel_gen/dialect/arch/
        """

        return cls(StringAttr(name))

__all__ = ["ArchVisibilityAttr"]
