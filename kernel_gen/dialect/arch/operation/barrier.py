"""arch barrier operation.

功能说明:
- 定义 arch.barrier op。

API 列表:
- `class ArchBarrierOp(scope: ArchScopeAttr, visibility: ArrayAttr[Attribute])`

使用示例:
- `from kernel_gen.dialect.arch.operation import ...`

关联文件:
- spec: spec/dialect/arch.md
- test: test/dialect/arch/
- 功能实现: kernel_gen/dialect/arch/operation/barrier.py
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar

from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE
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
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr, SymbolValueType
from kernel_gen.target import registry

from ..attr import ArchScopeAttr
from ..common import _raise_verify_error, _verify_barrier_visibility_attr, _verify_target_registry_support

@irdl_op_definition
class ArchBarrierOp(IRDLOperation):
    """描述一次 block 级 barrier。"""

    name = "arch.barrier"

    scope = attr_def(ArchScopeAttr)
    visibility = attr_def(ArrayAttr)

    def __init__(
        self: "ArchBarrierOp",
        scope: ArchScopeAttr,
        visibility: ArrayAttr[Attribute],
    ) -> None:
        """初始化 arch.barrier。


        功能说明:
        - 记录 barrier 的 scope 与 visibility。

        使用示例:
        - ArchBarrierOp(ArchScopeAttr.from_name("block"), ArrayAttr([...]))

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/arch/test_arch.py
        - 功能实现: kernel_gen/dialect/arch/
        """

        super().__init__(attributes={"scope": scope, "visibility": visibility})

    def verify_(self: "ArchBarrierOp") -> None:
        """校验 arch.barrier 输入约束。


        功能说明:
        - 校验 scope 必须是公开 `#arch.scope<...>` 成员之一。
        - 校验 visibility 为唯一且完整的 `[tsm, tlm]` 聚合可见域。

        使用示例:
        - ArchBarrierOp(...).verify()

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/arch/test_arch.py
        - 功能实现: kernel_gen/dialect/arch/
        """

        _verify_target_registry_support(self.name)
        self.scope.verify()
        _verify_barrier_visibility_attr(self.visibility)

    def print(self: "ArchBarrierOp", printer: Printer) -> None:
        """打印 arch.barrier 自定义文本语法。

        功能说明:
        - 按 `{scope = ..., visibility = ...}` 格式输出 barrier 属性。

        使用示例:
        - ArchBarrierOp(scope, visibility).print(printer)
        """

        printer.print_string(" {scope = ")
        printer.print_attribute(self.scope)
        printer.print_string(", visibility = ")
        printer.print_attribute(self.visibility)
        printer.print_string("}")

    @classmethod
    def parse(cls: type["ArchBarrierOp"], parser: AttrParser) -> "ArchBarrierOp":
        """解析 arch.barrier 自定义文本语法。

        功能说明:
        - 读取 `scope` 与 `visibility` 属性并构造 `ArchBarrierOp`。

        使用示例:
        - ArchBarrierOp.parse(parser)
        """

        parser.parse_punctuation("{", "Expected '{' in arch.barrier.")
        if parser.parse_identifier("Expected `scope` in arch.barrier.") != "scope":
            _raise_verify_error("arch.barrier must print scope before visibility")
        parser.parse_punctuation("=", "Expected '=' after scope.")
        scope = parser.parse_attribute()
        parser.parse_punctuation(",", "Expected ',' between scope and visibility.")
        if parser.parse_identifier("Expected `visibility` in arch.barrier.") != "visibility":
            _raise_verify_error("arch.barrier must contain visibility attribute")
        parser.parse_punctuation("=", "Expected '=' after visibility.")
        visibility = parser.parse_attribute()
        parser.parse_punctuation("}", "Expected '}' at end of arch.barrier.")
        return cls(scope, visibility)

__all__ = ["ArchBarrierOp"]
