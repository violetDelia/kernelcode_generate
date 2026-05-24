"""DMA slice operation definitions.

功能说明:
- 定义 `dma.load`、`dma.store`、`dma.slice` 与 `dma.deslice`。

API 列表:
- `class DmaLoadOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue])`
- `class DmaStoreOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue])`
- `class DmaSliceOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue])`
- `class DmaDesliceOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue], result_type: NnMemoryType)`

使用示例:
- `DmaSliceOp(target, source, offsets, sizes, strides)`

关联文件:
- spec: spec/dialect/dma.md
- test: test/dialect/dma/
- 功能实现: kernel_gen/dialect/dma/operation/slice.py
"""

from __future__ import annotations

from kernel_gen .core .error import ErrorKind ,ErrorModule ,kernel_code_error

from collections .abc import Sequence

from xdsl .dialects .builtin import ArrayAttr ,IntAttr
from xdsl .ir import Attribute ,Operation ,SSAValue
from xdsl .irdl import (
AttrSizedOperandSegments ,
IRDLOperation ,
attr_def ,
irdl_op_definition ,
operand_def ,
result_def ,
traits_def ,
var_operand_def ,
)
from xdsl .traits import NoMemoryEffect

from kernel_gen .dialect .nn import NnMemoryType
from kernel_gen .dialect .symbol import SymbolValueType

from ..effect import DmaTargetSourceEffect

from xdsl .ir import Attribute ,SSAValue

from kernel_gen .core .contracts import verify_memory_type as core_verify_memory_type

from kernel_gen .dialect .symbol import SymbolExprAttr ,SymbolIterType ,SymbolValueType

# Localized helpers from retired package-internal modules.

class _DmaSliceHelpers :
    """当前文件内本地 helper 容器。

    功能说明:
    - 承接退场 common.py 后的文件内 helper，避免形成模块级事实公开函数。

    使用示例:
    - _DmaSliceHelpers.helper(...)
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
    def verify_symbol_int_operands (
    values :Sequence [SSAValue ],field_name :str ,*,min_value :int
    )->Sequence [SSAValue ]:
        """校验 `!symbol.int<#symbol.expr<expr>>` operand 列表。


        功能说明:
        - 确保所有 operand 类型为 `!symbol.int<#symbol.expr<expr>>`。
        - 若 operand 可静态恢复为整型常量，则施加最小值约束。

        使用示例:
        - verify_symbol_int_operands(op.sizes, "sizes", min_value=1)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        for value in values :
            if not isinstance (value .type ,SymbolValueType ):
                raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,f"{field_name } entries must be !symbol.int")
            value .type .verify ()
            static_value =_DmaSliceHelpers .operand_int_value (value )
            if static_value is not None and static_value <min_value :
                raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,f"{field_name } entries must be >= {min_value }")
        return values

    @staticmethod
    def verify_symbol_index_operands (
    values :Sequence [SSAValue ],field_name :str ,*,min_value :int
    )->Sequence [SSAValue ]:
        """校验 `!symbol.int` / `!symbol.iter` operand 列表。


        功能说明:
        - 确保 operand 类型为 `!symbol.int` 或 `!symbol.iter`。
        - 若 operand 可静态恢复为整型常量，则施加最小值约束。

        使用示例:
        - verify_symbol_index_operands(op.offsets, "offsets", min_value=0)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        for value in values :
            if not isinstance (value .type ,(SymbolValueType ,SymbolIterType )):
                raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,f"{field_name } entries must be !symbol.int or !symbol.iter")
            value .type .verify ()
            static_value =_DmaSliceHelpers .operand_int_value (value )
            if static_value is not None and static_value <min_value :
                raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,f"{field_name } entries must be >= {min_value }")
        return values

    @staticmethod
    def verify_rank_match (values :Sequence [SSAValue ],rank :int ,field_name :str )->None :
        """校验标量 operand 列表长度与 rank 一致。


        功能说明:
        - 用于验证切片大小与 shape 的对应关系。

        使用示例:
        - verify_rank_match(offsets, rank, "offsets")

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if len (values )!=rank :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,f"{field_name } length must match rank")

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

        return _DmaSliceHelpers .static_int_from_expr_text (_DmaSliceHelpers .dim_expr_text (dim ))

    @staticmethod
    def verify_operands_match_layout (
    values :Sequence [SSAValue ],
    layout :ArrayAttr [Attribute ],
    message :str ,
    )->None :
        """校验 operand 列表与类型中可静态判定的布局一致。


        功能说明:
        - 若布局维度为静态 `SymbolExprAttr`，对应 operand 必须是相同值的 `!symbol.int<#symbol.expr<n>>`。
        - 若布局维度为符号表达式，则 operand 的公开表达式必须一致。
        - `?` 类型值只能匹配 `#symbol.expr<?>` 布局，不能通过 SSA 名称伪造具名维度。

        使用示例:
        - verify_operands_match_layout(op.sizes, result_type.shape, "shape must match sizes")

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        for value ,expected in zip (values ,layout .data ,strict =True ):
            expected_int =_DmaSliceHelpers .static_int_from_dim (expected )
            if expected_int is not None :
                static_value =_DmaSliceHelpers .operand_int_value (value )
                if static_value !=expected_int :
                    raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,message )
                continue
            expected_expr =_DmaSliceHelpers .dim_expr_text (expected )
            if expected_expr =="?":
                if not isinstance (value .type ,SymbolValueType )or value .type .get_value ()!="?":
                    raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,message )
                continue
            if not isinstance (value .type ,SymbolValueType )or value .type .get_value ()!=expected_expr :
                raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,message )

    @staticmethod
    def verify_unit_stride_operands (strides :Sequence [SSAValue ])->None :
        """校验 stride operand 是否全为常量 1。


        功能说明:
        - 当前阶段仅支持单位步长语义。
        - 每个 operand 都必须是值为 `1` 的 `!symbol.int<#symbol.expr<1>>`。

        使用示例:
        - verify_unit_stride_operands(op.strides)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        for value in strides :
            if _DmaSliceHelpers .operand_int_value (value )!=1 :
                raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma stride must be 1 in current implementation")












@irdl_op_definition
class DmaLoadOp (IRDLOperation ):
    """dma.load。"""

    name ="dma.load"
    traits =traits_def (DmaTargetSourceEffect ())

    target =operand_def (NnMemoryType )
    source =operand_def (NnMemoryType )
    offsets =var_operand_def (Attribute )
    sizes =var_operand_def (SymbolValueType )
    strides =var_operand_def (SymbolValueType )

    irdl_options =[AttrSizedOperandSegments (as_property =True )]

    def __init__ (
    self ,
    target :SSAValue |Operation ,
    source :SSAValue |Operation ,
    offsets :Sequence [SSAValue ],
    sizes :Sequence [SSAValue ],
    strides :Sequence [SSAValue ],
    )->None :
        """初始化 dma.load。


        功能说明:
        - 设置 target/source 与 offsets/sizes/strides。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaLoadOp(target, source, offsets, sizes, strides)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        super ().__init__ (
        operands =[target ,source ,offsets ,sizes ,strides ],
        )

    def verify_ (self )->None :
        """校验 dma.load。


        功能说明:
        - offsets/sizes/strides 长度与 source rank 一致。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。
        - target.shape == sizes 且 element_type 一致。

        使用示例:
        - DmaLoadOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        target_type =_DmaSliceHelpers .verify_memory_type (self .target .type ,"target")
        source_type =_DmaSliceHelpers .verify_memory_type (self .source .type ,"source")
        offsets =_DmaSliceHelpers .verify_symbol_index_operands (self .offsets ,"offsets",min_value =0 )
        sizes =_DmaSliceHelpers .verify_symbol_int_operands (self .sizes ,"sizes",min_value =1 )
        strides =_DmaSliceHelpers .verify_symbol_int_operands (self .strides ,"strides",min_value =1 )
        rank =len (source_type .shape .data )
        if len (target_type .shape .data )!=rank :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.load target rank must match source rank")
        _DmaSliceHelpers .verify_rank_match (offsets ,rank ,"offsets")
        _DmaSliceHelpers .verify_rank_match (sizes ,rank ,"sizes")
        _DmaSliceHelpers .verify_rank_match (strides ,rank ,"strides")
        _DmaSliceHelpers .verify_unit_stride_operands (strides )
        _DmaSliceHelpers .verify_operands_match_layout (sizes ,target_type .shape ,"target shape must match sizes")
        if source_type .element_type !=target_type .element_type :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.load element_type mismatch")


@irdl_op_definition
class DmaStoreOp (IRDLOperation ):
    """dma.store。"""

    name ="dma.store"
    traits =traits_def (DmaTargetSourceEffect ())

    target =operand_def (NnMemoryType )
    source =operand_def (NnMemoryType )
    offsets =var_operand_def (Attribute )
    sizes =var_operand_def (SymbolValueType )
    strides =var_operand_def (SymbolValueType )

    irdl_options =[AttrSizedOperandSegments (as_property =True )]

    def __init__ (
    self ,
    target :SSAValue |Operation ,
    source :SSAValue |Operation ,
    offsets :Sequence [SSAValue ],
    sizes :Sequence [SSAValue ],
    strides :Sequence [SSAValue ],
    )->None :
        """初始化 dma.store。


        功能说明:
        - 设置 target/source 与 offsets/sizes/strides。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaStoreOp(target, source, offsets, sizes, strides)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        super ().__init__ (operands =[target ,source ,offsets ,sizes ,strides ])

    def verify_ (self )->None :
        """校验 dma.store。


        功能说明:
        - source.shape 必须与 sizes 对齐。
        - offsets/sizes/strides 长度与 target rank 一致。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaStoreOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        source_type =_DmaSliceHelpers .verify_memory_type (self .source .type ,"source")
        target_type =_DmaSliceHelpers .verify_memory_type (self .target .type ,"target")
        offsets =_DmaSliceHelpers .verify_symbol_index_operands (self .offsets ,"offsets",min_value =0 )
        sizes =_DmaSliceHelpers .verify_symbol_int_operands (self .sizes ,"sizes",min_value =1 )
        strides =_DmaSliceHelpers .verify_symbol_int_operands (self .strides ,"strides",min_value =1 )
        rank =len (target_type .shape .data )
        _DmaSliceHelpers .verify_rank_match (offsets ,rank ,"offsets")
        _DmaSliceHelpers .verify_rank_match (sizes ,rank ,"sizes")
        _DmaSliceHelpers .verify_rank_match (strides ,rank ,"strides")
        _DmaSliceHelpers .verify_unit_stride_operands (strides )
        _DmaSliceHelpers .verify_operands_match_layout (sizes ,source_type .shape ,"source shape must match sizes")
        if source_type .element_type !=target_type .element_type :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.store element_type mismatch")


@irdl_op_definition
class DmaSliceOp (IRDLOperation ):
    """dma.slice。"""

    name ="dma.slice"
    traits =traits_def (DmaTargetSourceEffect ())

    target =operand_def (NnMemoryType )
    source =operand_def (NnMemoryType )
    offsets =var_operand_def (Attribute )
    sizes =var_operand_def (SymbolValueType )
    strides =var_operand_def (SymbolValueType )

    irdl_options =[AttrSizedOperandSegments (as_property =True )]

    def __init__ (
    self ,
    target :SSAValue |Operation ,
    source :SSAValue |Operation ,
    offsets :Sequence [SSAValue ],
    sizes :Sequence [SSAValue ],
    strides :Sequence [SSAValue ],
    )->None :
        """初始化 dma.slice。


        功能说明:
        - 设置 target/source 与 offsets/sizes/strides。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaSliceOp(target, source, offsets, sizes, strides)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        super ().__init__ (operands =[target ,source ,offsets ,sizes ,strides ])

    def verify_ (self )->None :
        """校验 dma.slice。


        功能说明:
        - offsets/sizes/strides 长度与 source rank 一致。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。
        - target.shape == sizes 且 target/source element_type 一致。
        - 当前阶段 stride 必须为 1。

        使用示例:
        - DmaSliceOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        target_type =_DmaSliceHelpers .verify_memory_type (self .target .type ,"target")
        source_type =_DmaSliceHelpers .verify_memory_type (self .source .type ,"source")
        offsets =_DmaSliceHelpers .verify_symbol_index_operands (self .offsets ,"offsets",min_value =0 )
        sizes =_DmaSliceHelpers .verify_symbol_int_operands (self .sizes ,"sizes",min_value =1 )
        strides =_DmaSliceHelpers .verify_symbol_int_operands (self .strides ,"strides",min_value =1 )
        rank =len (source_type .shape .data )
        if len (target_type .shape .data )!=rank :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.slice target rank must match source rank")
        _DmaSliceHelpers .verify_rank_match (offsets ,rank ,"offsets")
        _DmaSliceHelpers .verify_rank_match (sizes ,rank ,"sizes")
        _DmaSliceHelpers .verify_rank_match (strides ,rank ,"strides")
        _DmaSliceHelpers .verify_unit_stride_operands (strides )
        _DmaSliceHelpers .verify_operands_match_layout (sizes ,target_type .shape ,"shape must match sizes")
        if source_type .element_type !=target_type .element_type :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.slice element_type mismatch")


@irdl_op_definition
class DmaDesliceOp (IRDLOperation ):
    """dma.deslice。"""

    name ="dma.deslice"
    traits =traits_def (DmaTargetSourceEffect ())

    target =operand_def (NnMemoryType )
    source =operand_def (NnMemoryType )
    offsets =var_operand_def (Attribute )
    sizes =var_operand_def (SymbolValueType )
    strides =var_operand_def (SymbolValueType )
    result =result_def (NnMemoryType )

    irdl_options =[AttrSizedOperandSegments (as_property =True )]

    def __init__ (
    self ,
    target :SSAValue |Operation ,
    source :SSAValue |Operation ,
    offsets :Sequence [SSAValue ],
    sizes :Sequence [SSAValue ],
    strides :Sequence [SSAValue ],
    result_type :NnMemoryType ,
    )->None :
        """初始化 dma.deslice。


        功能说明:
        - 设置 target/source、offsets/sizes/strides 与结果类型。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaDesliceOp(target, source, offsets, sizes, strides, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        super ().__init__ (
        operands =[target ,source ,offsets ,sizes ,strides ],
        result_types =[result_type ],
        )

    def verify_ (self )->None :
        """校验 dma.deslice。


        功能说明:
        - source.shape 必须与 sizes 对齐。
        - offsets/sizes/strides 长度与 target rank 一致。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。
        - result type 必须与 target type 一致。

        使用示例:
        - DmaDesliceOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        source_type =_DmaSliceHelpers .verify_memory_type (self .source .type ,"source")
        target_type =_DmaSliceHelpers .verify_memory_type (self .target .type ,"target")
        result_type =_DmaSliceHelpers .verify_memory_type (self .result .type ,"result")
        offsets =_DmaSliceHelpers .verify_symbol_index_operands (self .offsets ,"offsets",min_value =0 )
        sizes =_DmaSliceHelpers .verify_symbol_int_operands (self .sizes ,"sizes",min_value =1 )
        strides =_DmaSliceHelpers .verify_symbol_int_operands (self .strides ,"strides",min_value =1 )
        rank =len (target_type .shape .data )
        _DmaSliceHelpers .verify_rank_match (offsets ,rank ,"offsets")
        _DmaSliceHelpers .verify_rank_match (sizes ,rank ,"sizes")
        _DmaSliceHelpers .verify_rank_match (strides ,rank ,"strides")
        _DmaSliceHelpers .verify_unit_stride_operands (strides )
        _DmaSliceHelpers .verify_operands_match_layout (sizes ,source_type .shape ,"source shape must match sizes")
        if source_type .element_type !=target_type .element_type :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.deslice element_type mismatch")
        if result_type !=target_type :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.deslice result must match target type")



__all__ =[
"DmaLoadOp",
"DmaStoreOp",
"DmaSliceOp",
"DmaDesliceOp",
]
