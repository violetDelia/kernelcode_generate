"""DMA lifecycle operation definitions.

功能说明:
- 定义 `dma.alloc`、`dma.fill` 与 `dma.free`。

API 列表:
- `class DmaAllocOp(dynamic_shape: Sequence[SSAValue], result_type: NnMemoryType)`
- `class DmaFillOp(target: SSAValue | Operation, value: SSAValue | Operation)`
- `class DmaFreeOp(source: SSAValue | Operation)`

使用示例:
- `DmaAllocOp(dynamic_shape, result_type)`

关联文件:
- spec: spec/dialect/dma.md
- test: test/dialect/dma/
- 功能实现: kernel_gen/dialect/dma/operation/lifecycle.py
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

from ..canonicalization import DmaFillCanonicalizationTrait
from ..effect import DmaAllocMemoryEffect ,DmaFreeMemoryEffect ,DmaTargetWriteEffect

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

from xdsl .ir import Attribute ,SSAValue

from kernel_gen .core .contracts import verify_memory_type as core_verify_memory_type

from kernel_gen .dialect .symbol import SymbolExprAttr ,SymbolIterType ,SymbolValueType

# Localized helpers from retired package-internal modules.

class _DmaLifecycleHelpers :
    """当前文件内本地 helper 容器。

    功能说明:
    - 承接退场 common.py 后的文件内 helper，避免形成模块级事实公开函数。

    使用示例:
    - _DmaLifecycleHelpers.helper(...)
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

        return _DmaLifecycleHelpers .verify_memory_type (value .type ,field_name )

    @staticmethod
    def verify_fill_value_operand (value :SSAValue ,field_name :str )->SSAValue :
        """校验 `dma.fill` 的数值标量 operand。


        功能说明:
        - 当前接受 builtin 整型、builtin 浮点或 `!symbol.int<#symbol.expr<expr>>`。
        - builtin `i1` 视为 bool，不属于 `dma.fill` 数值标量。
        - 若为 `!symbol.int<#symbol.expr<expr>>`，同步触发其类型校验。

        使用示例:
        - verify_fill_value_operand(op.value, "value")

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if isinstance (value .type ,IntegerType )and int (value .type .width .data )!=1 :
            return value
        if isinstance (value .type ,(Float16Type ,BFloat16Type ,Float32Type ,Float64Type )):
            return value
        if isinstance (value .type ,SymbolValueType ):
            value .type .verify ()
            return value
        raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,f"{field_name } must be builtin integer, builtin float or !symbol.int")

    @staticmethod
    def verify_fill_target_element_type (element_type :Attribute )->None :
        """校验 `dma.fill` 目标 memory element type。


        功能说明:
        - 允许公开数值 memory dtype，拒绝 bool 与非数值类型。

        使用示例:
        - verify_fill_target_element_type(target_type.element_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if isinstance (element_type ,IntegerType ):
            if int (element_type .width .data )==1 :
                raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.fill target element_type must be numeric and not bool")
            return
        if isinstance (element_type ,(Float16Type ,BFloat16Type ,Float32Type ,Float64Type )):
            return
        raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.fill target element_type must be numeric and not bool")

    @staticmethod
    def verify_fill_value_matches_target (value_type :Attribute ,target_element_type :Attribute )->None :
        """校验 `dma.fill` value 与 target dtype 的公开兼容性。


        功能说明:
        - `!symbol.int` 可填充非 bool 数值 memory。
        - builtin 整数只能填充整数 memory，builtin 浮点只能填充浮点 memory。

        使用示例:
        - verify_fill_value_matches_target(op.value.type, target_type.element_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if isinstance (value_type ,SymbolValueType ):
            return
        if isinstance (value_type ,IntegerType )and isinstance (target_element_type ,IntegerType ):
            return
        if isinstance (value_type ,(Float16Type ,BFloat16Type ,Float32Type ,Float64Type ))and isinstance (
        target_element_type ,
        (Float16Type ,BFloat16Type ,Float32Type ,Float64Type ),
        ):
            return
        raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.fill value type must match target element_type")

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
            static_value =_DmaLifecycleHelpers .operand_int_value (value )
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

        return _DmaLifecycleHelpers .static_int_from_expr_text (_DmaLifecycleHelpers .dim_expr_text (dim ))

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
            expected_int =_DmaLifecycleHelpers .static_int_from_dim (expected )
            if expected_int is not None :
                static_value =_DmaLifecycleHelpers .operand_int_value (value )
                if static_value !=expected_int :
                    raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,message )
                continue
            expected_expr =_DmaLifecycleHelpers .dim_expr_text (expected )
            if expected_expr =="?":
                if not isinstance (value .type ,SymbolValueType )or value .type .get_value ()!="?":
                    raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,message )
                continue
            if not isinstance (value .type ,SymbolValueType )or value .type .get_value ()!=expected_expr :
                raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,message )

    @staticmethod
    def verify_dynamic_shape_matches_result (
    values :Sequence [SSAValue ],
    result_shape :ArrayAttr [Attribute ],
    field_name :str ,
    )->None :
        """校验 dma.alloc 的 dynamic_shape 与结果 shape 的一致性。


        功能说明:
        - 支持两种形态：
          1) dynamic_shape 与结果 rank 等长，逐维对齐；
          2) dynamic_shape 仅包含非静态维度，按出现顺序对齐。
        - 匿名维度 `?` 必须由 `!symbol.int<?>` 承接，不能与具名维互相伪装。

        使用示例:
        - verify_dynamic_shape_matches_result(dynamic_shape, result_type.shape, "dynamic_shape")

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        rank =len (result_shape .data )
        if len (values )==rank :
            _DmaLifecycleHelpers .verify_rank_match (values ,rank ,field_name )
            _DmaLifecycleHelpers .verify_operands_match_layout (values ,result_shape ,f"{field_name } must match result shape")
            return

        dynamic_dims :list [Attribute ]=[]
        for dim in result_shape .data :
            if _DmaLifecycleHelpers .static_int_from_dim (dim )is not None :
                continue
            dynamic_dims .append (dim )

        if len (values )!=len (dynamic_dims ):
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,f"{field_name } length must match symbol rank")

        _DmaLifecycleHelpers .verify_operands_match_layout (
        values ,
        ArrayAttr (dynamic_dims ),
        f"{field_name } symbol must match result shape",
        )















@irdl_op_definition
class DmaAllocOp (IRDLOperation ):
    """dma.alloc。"""

    name ="dma.alloc"
    traits =traits_def (DmaAllocMemoryEffect ())

    dynamic_shape =var_operand_def (SymbolValueType )
    result =result_def (NnMemoryType )

    irdl_options =[AttrSizedOperandSegments (as_property =True )]

    def __init__ (
    self ,
    dynamic_shape :Sequence [SSAValue ],
    result_type :NnMemoryType ,
    )->None :
        """初始化 dma.alloc。


        功能说明:
        - 设置动态 shape operand 与结果类型。

        使用示例:
        - DmaAllocOp(dynamic_shape, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        super ().__init__ (operands =[dynamic_shape ],result_types =[result_type ])

    def verify_ (self )->None :
        """校验 dma.alloc。


        功能说明:
        - 结果类型必须为 nn.memory。
        - dynamic_shape 支持空列表（全静态 shape）、全量 rank 列表或仅符号维度列表。
        - stride 按结果类型显式指定，不再额外限制布局。

        使用示例:
        - DmaAllocOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        result_type =_DmaLifecycleHelpers .verify_memory_type (self .result .type ,"result")
        dynamic_shape =_DmaLifecycleHelpers .verify_symbol_int_operands (self .dynamic_shape ,"dynamic_shape",min_value =0 )
        _DmaLifecycleHelpers .verify_dynamic_shape_matches_result (dynamic_shape ,result_type .shape ,"dynamic_shape")


@irdl_op_definition
class DmaFillOp (IRDLOperation ):
    """dma.fill。"""

    name ="dma.fill"
    traits =traits_def (DmaTargetWriteEffect (),DmaFillCanonicalizationTrait ())

    target =operand_def (NnMemoryType )
    value =operand_def (Attribute )

    def __init__ (self ,target :SSAValue |Operation ,value :SSAValue |Operation )->None :
        """初始化 dma.fill。


        功能说明:
        - 设置被写入的 `target` memory 与标量 `value` operand。

        使用示例:
        - DmaFillOp(target, value)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        super ().__init__ (operands =[target ,value ])

    def verify_ (self )->None :
        """校验 dma.fill。


        功能说明:
        - `target` 必须为非 bool 数值 `!nn.memory<...>`。
        - `value` 允许 builtin 整数、builtin 浮点或 `!symbol.int<#symbol.expr<expr>>`。

        使用示例:
        - DmaFillOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        target_type =_DmaLifecycleHelpers .verify_memory_operand (self .target ,"target")
        _DmaLifecycleHelpers .verify_fill_target_element_type (target_type .element_type )
        value =_DmaLifecycleHelpers .verify_fill_value_operand (self .value ,"value")
        _DmaLifecycleHelpers .verify_fill_value_matches_target (value .type ,target_type .element_type )


@irdl_op_definition
class DmaFreeOp (IRDLOperation ):
    """dma.free。"""

    name ="dma.free"
    traits =traits_def (DmaFreeMemoryEffect ())

    source =operand_def (NnMemoryType )

    def __init__ (self ,source :SSAValue |Operation )->None :
        """初始化 dma.free。


        功能说明:
        - 设置待释放的 source operand。

        使用示例:
        - DmaFreeOp(source)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        super ().__init__ (operands =[source ])

    def verify_ (self )->None :
        """校验 dma.free。


        功能说明:
        - source 必须为 nn.memory。

        使用示例:
        - DmaFreeOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        _DmaLifecycleHelpers .verify_memory_operand (self .source ,"source")



__all__ =[
"DmaAllocOp",
"DmaFillOp",
"DmaFreeOp",
]
