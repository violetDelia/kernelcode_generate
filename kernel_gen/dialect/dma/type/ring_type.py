"""DMA ring type definition.

功能说明:
- 定义 `!dma.ring` 类型。

API 列表:
- `class DmaRingType(memory_type: NnMemoryType)`

使用示例:
- `DmaRingType(memory_type)`

关联文件:
- spec: spec/dialect/dma.md
- test: test/dialect/dma/
- 功能实现: kernel_gen/dialect/dma/type/ring_type.py
"""

from __future__ import annotations

from collections .abc import Sequence

from xdsl .ir import Attribute ,ParametrizedAttribute ,TypeAttribute
from xdsl .irdl import irdl_attr_definition ,param_def
from xdsl .parser import AttrParser
from xdsl .printer import Printer

from kernel_gen .dialect .nn import NnMemoryType

@irdl_attr_definition
class DmaRingType (ParametrizedAttribute ,TypeAttribute ):
    """DMA ring buffer type。"""

    name ="dma.ring"

    memory_type :NnMemoryType =param_def (NnMemoryType )

    @classmethod
    def parse_parameters (cls ,parser :AttrParser )->Sequence [Attribute ]:
        """解析 dma.ring type 参数。

        功能说明:
        - 支持 `!dma.ring<!nn.memory<...>>`。

        使用示例:
        - Parser(ctx, "!dma.ring<!nn.memory<...>>").parse_attribute()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        parser .parse_punctuation ("<","Expected '<' for dma.ring.")
        memory_type =parser .parse_attribute ()
        parser .parse_punctuation (">","Expected '>' for dma.ring.")
        if not isinstance (memory_type ,NnMemoryType ):
            parser .raise_error ("dma.ring memory type must be nn.memory")
        return (memory_type ,)

    def print_parameters (self ,printer :Printer )->None :
        """打印 dma.ring type 参数。

        功能说明:
        - 按公开 assembly 形式输出 slot memory type。

        使用示例:
        - `Printer(stream=stream).print_attribute(ring_type)`
        """

        printer .print_string ("<")
        printer .print_attribute (self .memory_type )
        printer .print_string (">")

    def verify (self )->None :
        """校验 dma.ring type。

        功能说明:
        - memory_type 必须是合法 nn.memory。

        使用示例:
        - DmaRingType(mem_type).verify()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        self .memory_type .verify ()



__all__ =[
"DmaRingType",
]
