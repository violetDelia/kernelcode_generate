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

from kernel_gen .core .error import ErrorKind ,ErrorModule ,kernel_code_error

from collections .abc import Sequence

from xdsl .ir import Attribute ,ParametrizedAttribute ,TypeAttribute
from xdsl .irdl import irdl_attr_definition ,param_def
from xdsl .parser import AttrParser
from xdsl .printer import Printer

from kernel_gen .dialect .nn import NnMemoryType
from kernel_gen .dialect .symbol import SymbolExprAttr

from kernel_gen .dialect .symbol import SymbolExprAttr ,SymbolIterType ,SymbolValueType

# Localized helpers from retired package-internal modules.

class _DmaRingTypeHelpers :
    """当前文件内本地 helper 容器。

    功能说明:
    - 承接退场 common.py 后的文件内 helper，避免形成模块级事实公开函数。

    使用示例:
    - _DmaRingTypeHelpers.helper(...)
    """

    @staticmethod
    def verify_symbol_expr_attr (value :Attribute ,field_name :str )->SymbolExprAttr :
        """校验属性为公开 SymbolExprAttr。

        功能说明:
        - 用于 dma ring type 的 offset 参数校验。

        使用示例:
        - offset = verify_symbol_expr_attr(attr, "offset")

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if not isinstance (value ,SymbolExprAttr ):
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,f"{field_name } must be SymbolExprAttr")
        value .verify ()
        return value

    @staticmethod
    def dim_expr_text (dim :Attribute )->str :
        """读取 memory shape/stride 的 SymbolExprAttr 文本。

        功能说明:
        - 拒绝旧 IntAttr/StringAttr shape/stride 入口。

        使用示例:
        - dim_expr_text(SymbolExprAttr.from_expr("N"))

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if not isinstance (dim ,SymbolExprAttr ):
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"memory layout entries must be SymbolExprAttr")
        dim .verify ()
        return dim .expr .data

    @staticmethod
    def static_int_from_expr_text (expr :str )->int |None :
        """尝试从 SymbolExprAttr 文本提取静态整数。

        功能说明:
        - 仅识别十进制整数字面量；动态表达式返回 None。

        使用示例:
        - static_int_from_expr_text("4")

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        signless =expr [1 :]if expr .startswith ("-")else expr
        if signless .isdecimal ():
            return int (expr )
        return None

    @staticmethod
    def static_int_from_dim (dim :Attribute )->int |None :
        """尝试从 SymbolExprAttr 维度提取静态整数。

        功能说明:
        - 对 `#symbol.expr<4>` 返回 4；动态维度返回 None。

        使用示例:
        - static_int_from_dim(SymbolExprAttr.from_expr("4"))

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        return _DmaRingTypeHelpers .static_int_from_expr_text (_DmaRingTypeHelpers .dim_expr_text (dim ))







@irdl_attr_definition
class DmaRingType (ParametrizedAttribute ,TypeAttribute ):
    """DMA ring buffer type。"""

    name ="dma.ring"

    offset :SymbolExprAttr =param_def (SymbolExprAttr )
    memory_type :NnMemoryType =param_def (NnMemoryType )

    @classmethod
    def parse_parameters (cls ,parser :AttrParser )->Sequence [Attribute ]:
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

        parser .parse_punctuation ("<","Expected '<' for dma.ring.")
        offset =parser .parse_attribute ()
        parser .parse_punctuation (",","Expected ',' after dma.ring offset.")
        memory_type =parser .parse_attribute ()
        parser .parse_punctuation (">","Expected '>' for dma.ring.")
        if not isinstance (offset ,SymbolExprAttr ):
            parser .raise_error ("dma.ring offset must be SymbolExprAttr")
        if not isinstance (memory_type ,NnMemoryType ):
            parser .raise_error ("dma.ring memory type must be nn.memory")
        return (offset ,memory_type )

    def print_parameters (self ,printer :Printer )->None :
        """打印 dma.ring type 参数。

        功能说明:
        - 按公开 assembly 形式输出 offset 与 slot memory type。

        使用示例:
        - `Printer(stream=stream).print_attribute(ring_type)`
        """

        printer .print_string ("<")
        printer .print_attribute (self .offset )
        printer .print_string (", ")
        printer .print_attribute (self .memory_type )
        printer .print_string (">")

    def verify (self )->None :
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

        offset =_DmaRingTypeHelpers .verify_symbol_expr_attr (self .offset ,"dma.ring offset")
        static_offset =_DmaRingTypeHelpers .static_int_from_dim (offset )
        if static_offset is not None and static_offset <=0 :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.ring offset must be > 0")
        self .memory_type .verify ()



__all__ =[
"DmaRingType",
]
