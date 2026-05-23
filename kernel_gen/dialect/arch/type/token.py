"""arch token type.

功能说明:
- 定义 arch token type；共享 token 文本校验来自 `arch.common` 包内 API。

API 列表:
- `class ArchTokenType(token_id: StringAttr)`

使用示例:
- `from kernel_gen.dialect.arch.type import ...`

关联文件:
- spec: spec/dialect/arch.md
- test: test/dialect/arch/
- 功能实现: kernel_gen/dialect/arch/type/token.py
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

from ..common import _verify_token_id_text


@irdl_attr_definition
class ArchTokenType(ParametrizedAttribute, TypeAttribute):
    """Arch event token type。"""

    name = "arch.token"

    token_id: StringAttr = param_def(StringAttr)

    @classmethod
    def parse_parameters(cls: type["ArchTokenType"], parser: AttrParser) -> Sequence[Attribute]:
        """解析 arch.token type 参数。

        功能说明:
        - 支持 `!arch.token<event_id>` 文本。

        使用示例:
        - Parser(ctx, "!arch.token<event0>").parse_attribute()

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/arch/test_arch.py
        - 功能实现: kernel_gen/dialect/arch/
        """

        parser.parse_punctuation("<", "Expected '<' for arch.token.")
        token_id = parser.parse_identifier("Expected arch token id.")
        parser.parse_punctuation(">", "Expected '>' for arch.token.")
        return (StringAttr(token_id),)

    def print_parameters(self: "ArchTokenType", printer: Printer) -> None:
        """打印 arch.token type 参数。

        功能说明:
        - 输出 `!arch.token<...>` 尖括号内的 token id。

        使用示例:
        - ArchTokenType(StringAttr("event0")).print_parameters(printer)
        """

        printer.print_string("<")
        printer.print_string(self.token_id.data)
        printer.print_string(">")

    def verify(self: "ArchTokenType") -> None:
        """校验 arch.token type。

        功能说明:
        - token id 必须非空且为公开 identifier。

        使用示例:
        - ArchTokenType(StringAttr("event0")).verify()

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/arch/test_arch.py
        - 功能实现: kernel_gen/dialect/arch/
        """

        _verify_token_id_text(self.token_id.data)

__all__ = ["ArchTokenType"]
