"""DMA ring operation definitions.

功能说明:
- 定义 `dma.make_ring`、`dma.current_ring` 与 `dma.advance_ring`。

API 列表:
- `class DmaMakeRingOp(memory: SSAValue | Operation, count: SSAValue | Operation, offset: SSAValue | Operation, shape_bytes: SSAValue | Operation, result_type: DmaRingType)`
- `class DmaCurrentRingOp(ring: SSAValue | Operation, result_type: NnMemoryType | None = None)`
- `class DmaAdvanceRingOp(ring: SSAValue | Operation, result_type: NnMemoryType | None = None)`

使用示例:
- `DmaMakeRingOp(memory, count, offset, shape_bytes, ring_type)`

关联文件:
- spec: spec/dialect/dma.md
- test: test/dialect/dma/
- 功能实现: kernel_gen/dialect/dma/operation/ring.py
"""

from __future__ import annotations

from kernel_gen .core .error import ErrorKind ,ErrorModule ,kernel_code_error

from xdsl .ir import Operation ,SSAValue
from xdsl .irdl import IRDLOperation ,irdl_op_definition ,operand_def ,result_def

from kernel_gen .dialect .nn import NnMemoryType
from kernel_gen .dialect .symbol import SymbolValueType

from ..type import DmaRingType

from xdsl .dialects .builtin import (
ArrayAttr ,
BFloat16Type ,
Float16Type ,
Float32Type ,
Float64Type ,
IntAttr ,
IntegerAttr ,
IntegerType ,
i8 ,
i32 ,
)

from kernel_gen .core .contracts import verify_memory_type as core_verify_memory_type

from kernel_gen .dialect .symbol import SymbolExprAttr ,SymbolIterType ,SymbolValueType

# Localized helpers from retired package-internal modules.

class _DmaRingHelpers :
    """当前文件内本地 helper 容器。

    功能说明:
    - 承接退场 common.py 后的文件内 helper，避免形成模块级事实公开函数。

    使用示例:
    - _DmaRingHelpers.helper(...)
    """

    @staticmethod
    def verify_memory_type (value :Attribute ,field_name :str )->NnMemoryType :
        """校验并返回 nn.memory type。


        功能说明:
        - 确认类型为 nn.memory 并触发类型校验。

        使用示例:
        - verify_memory_type(op.source.type, "source")

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        return core_verify_memory_type (value ,field_name ,scene ="dialect.dma verifier")

    @staticmethod
    def verify_memory_operand (value :SSAValue ,field_name :str )->NnMemoryType :
        """校验 SSA operand 为 nn.memory type。


        功能说明:
        - 统一处理 SSA operand 的 nn.memory 类型校验与内部验证。

        使用示例:
        - verify_memory_operand(op.source, "source")

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        return _DmaRingHelpers .verify_memory_type (value .type ,field_name )

    @staticmethod
    def operand_int_value (value :SSAValue )->int |None :
        """尝试从 `!symbol.int<#symbol.expr<expr>>` SSA operand 恢复静态整型值。


        功能说明:
        - 仅识别字面量整数表达式，例如 `!symbol.int<#symbol.expr<4>>`。
        - `!symbol.iter<start = "...", end = "...", step = "...">` 视为运行期值，不参与静态比较。

        使用示例:
        - operand_int_value(op.sizes[0])

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if isinstance (value .type ,SymbolIterType ):
            return None
        if not isinstance (value .type ,SymbolValueType ):
            return None
        expr =value .type .expr .expr .data .strip ()
        try :
            return int (expr )
        except ValueError :
            return None

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

        return _DmaRingHelpers .static_int_from_expr_text (_DmaRingHelpers .dim_expr_text (dim ))

    @staticmethod
    def is_i8_byte_pool (memory_type :NnMemoryType )->bool :
        """判断是否为 i8 一维 byte pool。


        功能说明:
        - 要求 element_type 为 i8，且 rank 为 1。

        使用示例:
        - if is_i8_byte_pool(mem_type): ...

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if len (memory_type .shape .data )!=1 :
            return False
        element_type =memory_type .element_type
        return isinstance (element_type ,IntegerType )and int (element_type .width .data )==8

    @staticmethod
    def maybe_numel (shape :ArrayAttr [Attribute ])->int |None :
        """尝试计算 shape 的元素总数。


        功能说明:
        - 仅在全部维度为静态整数 SymbolExprAttr 时返回乘积。

        使用示例:
        - maybe_numel(ArrayAttr([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("4")]))

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        numel =1
        for dim in shape .data :
            value =_DmaRingHelpers .static_int_from_dim (dim )
            if value is None :
                return None
            numel *=value
        return numel

    @staticmethod
    def symbol_int_expr_text (value :SSAValue ,field_name :str )->str :
        """读取 `!symbol.int` operand 的公开表达文本。

        功能说明:
        - 校验 operand 类型为 `SymbolValueType` 并返回其 `SymbolExprAttr` 文本。

        使用示例:
        - offset_expr = symbol_int_expr_text(op.offset, "offset")

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if not isinstance (value .type ,SymbolValueType ):
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,f"{field_name } must be !symbol.int")
        value .type .verify ()
        return value .type .expr .expr .data

    @staticmethod
    def verify_positive_static_operand (value :SSAValue ,field_name :str )->int |None :
        """校验可静态判定的 `!symbol.int` operand 为正数。

        功能说明:
        - 动态符号表达式仅校验类型，不做数值求解。

        使用示例:
        - count = verify_positive_static_operand(op.count, "count")

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        _DmaRingHelpers .symbol_int_expr_text (value ,field_name )
        static_value =_DmaRingHelpers .operand_int_value (value )
        if static_value is not None and static_value <=0 :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,f"{field_name } must be > 0")
        return static_value












@irdl_op_definition
class DmaMakeRingOp (IRDLOperation ):
    """dma.make_ring。"""

    name ="dma.make_ring"

    memory =operand_def (NnMemoryType )
    count =operand_def (SymbolValueType )
    offset =operand_def (SymbolValueType )
    shape_bytes =operand_def (SymbolValueType )
    result =result_def (DmaRingType )

    def __init__ (
    self ,
    memory :SSAValue |Operation ,
    count :SSAValue |Operation ,
    offset :SSAValue |Operation ,
    shape_bytes :SSAValue |Operation ,
    result_type :DmaRingType ,
    )->None :
        """初始化 dma.make_ring。

        功能说明:
        - 创建 ring buffer 描述，result type 记录 stage offset 与 slot memory type。

        使用示例:
        - DmaMakeRingOp(storage, count, offset, shape_bytes, ring_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        super ().__init__ (operands =[memory ,count ,offset ,shape_bytes ],result_types =[result_type ])

    def verify_ (self )->None :
        """校验 dma.make_ring。

        功能说明:
        - backing memory 必须是一维 i8 memory。
        - count/offset/shape_bytes 必须为 `!symbol.int`，静态可判定时满足正数与容量关系。
        - result ring 的 offset 和 slot space 必须与 operands/backing memory 一致。

        使用示例:
        - DmaMakeRingOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        memory_type =_DmaRingHelpers .verify_memory_operand (self .memory ,"memory")
        if not _DmaRingHelpers .is_i8_byte_pool (memory_type ):
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.make_ring memory must be one-dimensional i8 memory")
        ring_type =self .result .type
        if not isinstance (ring_type ,DmaRingType ):
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.make_ring result must be dma.ring")
        ring_type .verify ()
        count_int =_DmaRingHelpers .verify_positive_static_operand (self .count ,"count")
        offset_int =_DmaRingHelpers .verify_positive_static_operand (self .offset ,"offset")
        shape_bytes_int =_DmaRingHelpers .verify_positive_static_operand (self .shape_bytes ,"shape_bytes")
        if offset_int is not None and shape_bytes_int is not None and shape_bytes_int >=offset_int :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"shape_bytes must be < offset")
        backing_bytes =_DmaRingHelpers .maybe_numel (memory_type .shape )
        if backing_bytes is not None and count_int is not None and offset_int is not None :
            if backing_bytes <count_int *offset_int :
                raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.make_ring backing memory bytes must be >= count * offset")
        offset_expr =_DmaRingHelpers .symbol_int_expr_text (self .offset ,"offset")
        if ring_type .offset .expr .data !=offset_expr :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.make_ring result ring offset must match offset operand")
        if ring_type .memory_type .space .space .data !=memory_type .space .space .data :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.make_ring result ring slot space must match backing memory space")


@irdl_op_definition
class DmaCurrentRingOp (IRDLOperation ):
    """dma.current_ring。"""

    name ="dma.current_ring"

    ring =operand_def (DmaRingType )
    result =result_def (NnMemoryType )

    def __init__ (
    self ,
    ring :SSAValue |Operation ,
    result_type :NnMemoryType |None =None ,
    )->None :
        """初始化 dma.current_ring。

        功能说明:
        - 返回 ring 当前 cursor 对应的 slot memory。

        使用示例:
        - DmaCurrentRingOp(ring_value)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        ring_type =SSAValue .get (ring ).type
        if result_type is None :
            if not isinstance (ring_type ,DmaRingType ):
                raise TypeError ("ring must have dma.ring type when result_type is omitted")
            result_type =ring_type .memory_type
        super ().__init__ (operands =[ring ],result_types =[result_type ])

    def verify_ (self )->None :
        """校验 dma.current_ring。

        功能说明:
        - operand 必须是 dma.ring，result type 必须等于 ring slot memory type。

        使用示例:
        - DmaCurrentRingOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        ring_type =self .ring .type
        if not isinstance (ring_type ,DmaRingType ):
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.current_ring ring operand must be dma.ring")
        ring_type .verify ()
        if self .result .type !=ring_type .memory_type :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.current_ring result must match ring slot memory type")


@irdl_op_definition
class DmaAdvanceRingOp (IRDLOperation ):
    """dma.advance_ring。"""

    name ="dma.advance_ring"

    ring =operand_def (DmaRingType )
    result =result_def (NnMemoryType )

    def __init__ (
    self ,
    ring :SSAValue |Operation ,
    result_type :NnMemoryType |None =None ,
    )->None :
        """初始化 dma.advance_ring。

        功能说明:
        - 推进 ring cursor 并返回推进后的 current slot memory。

        使用示例:
        - DmaAdvanceRingOp(ring_value)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        ring_type =SSAValue .get (ring ).type
        if result_type is None :
            if not isinstance (ring_type ,DmaRingType ):
                raise TypeError ("ring must have dma.ring type when result_type is omitted")
            result_type =ring_type .memory_type
        super ().__init__ (operands =[ring ],result_types =[result_type ])

    def verify_ (self )->None :
        """校验 dma.advance_ring。

        功能说明:
        - operand 必须是 dma.ring，result type 必须等于 ring slot memory type。
        - op 不声明 Pure trait，未使用 result 时仍应保留 cursor 推进副作用。

        使用示例:
        - DmaAdvanceRingOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        ring_type =self .ring .type
        if not isinstance (ring_type ,DmaRingType ):
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.advance_ring ring operand must be dma.ring")
        ring_type .verify ()
        if self .result .type !=ring_type .memory_type :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.advance_ring result must match ring slot memory type")



__all__ =[
"DmaMakeRingOp",
"DmaCurrentRingOp",
"DmaAdvanceRingOp",
]
