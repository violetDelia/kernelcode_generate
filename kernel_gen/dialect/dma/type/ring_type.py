"""DMA ring type definition.

功能说明:
- 定义 `!dma.ring` 类型。

API 列表:
- `class DmaRingType(offset: SymbolExprAttr, memory_type: NnMemoryType)`

使用示例:
- `DmaRingType(SymbolExprAttr.from_expr("64"), memory_type)`

关联文件:
- spec: spec/dialect/dma.md
- test: test/dialect/dma/
- 功能实现: kernel_gen/dialect/dma/type/ring_type.py
"""

from __future__ import annotations

from collections.abc import Sequence

from xdsl.ir import Attribute, ParametrizedAttribute, TypeAttribute
from xdsl.irdl import irdl_attr_definition, param_def
from xdsl.parser import AttrParser
from xdsl.printer import Printer
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr

from ..common import static_int_from_dim, verify_symbol_expr_attr

@irdl_attr_definition
class DmaRingType(ParametrizedAttribute, TypeAttribute):
    """DMA ring buffer type。"""

    name = "dma.ring"

    offset: SymbolExprAttr = param_def(SymbolExprAttr)
    memory_type: NnMemoryType = param_def(NnMemoryType)

    @classmethod
    def parse_parameters(cls, parser: AttrParser) -> Sequence[Attribute]:
        """解析 dma.ring type 参数。

        功能说明:
        - 支持 `!dma.ring<#symbol.expr<offset>, !nn.memory<...>>`。

        使用示例:
        - Parser(ctx, "!dma.ring<#symbol.expr<64>, !nn.memory<...>>").parse_attribute()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        parser.parse_punctuation("<", "Expected '<' for dma.ring.")
        offset = parser.parse_attribute()
        parser.parse_punctuation(",", "Expected ',' after dma.ring offset.")
        memory_type = parser.parse_attribute()
        parser.parse_punctuation(">", "Expected '>' for dma.ring.")
        if not isinstance(offset, SymbolExprAttr):
            parser.raise_error("dma.ring offset must be SymbolExprAttr")
        if not isinstance(memory_type, NnMemoryType):
            parser.raise_error("dma.ring memory type must be nn.memory")
        return (offset, memory_type)

    def print_parameters(self, printer: Printer) -> None:
        """打印 dma.ring type 参数。

        功能说明:
        - 按公开 assembly 形式输出 offset 与 slot memory type。

        使用示例:
        - `Printer(stream=stream).print_attribute(ring_type)`
        """

        printer.print_string("<")
        printer.print_attribute(self.offset)
        printer.print_string(", ")
        printer.print_attribute(self.memory_type)
        printer.print_string(">")

    def verify(self) -> None:
        """校验 dma.ring type。

        功能说明:
        - offset 必须是合法 SymbolExprAttr，静态可判定时必须大于 0。
        - memory_type 必须是合法 nn.memory。

        使用示例:
        - DmaRingType(SymbolExprAttr.from_expr("64"), mem_type).verify()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        offset = verify_symbol_expr_attr(self.offset, "dma.ring offset")
        static_offset = static_int_from_dim(offset)
        if static_offset is not None and static_offset <= 0:
            raise VerifyException("dma.ring offset must be > 0")
        self.memory_type.verify()



__all__ = [
    "DmaRingType",
]
