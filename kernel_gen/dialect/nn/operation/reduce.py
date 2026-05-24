"""nn reduce operations.

功能说明:
- 承载 nn dialect package 拆分后的 nn reduce operations 实现。

API 列表:
- `class NnReduceSumOp(input_value: SSAValue, result_type: NnMemoryType, axes: Sequence[int] | ArrayAttr[IntegerAttr], keepdim: bool | IntegerAttr, space: NnMemorySpaceAttr)`
- `class NnReduceMinOp(input_value: SSAValue, result_type: NnMemoryType, axes: Sequence[int] | ArrayAttr[IntegerAttr], keepdim: bool | IntegerAttr, space: NnMemorySpaceAttr)`
- `class NnReduceMaxOp(input_value: SSAValue, result_type: NnMemoryType, axes: Sequence[int] | ArrayAttr[IntegerAttr], keepdim: bool | IntegerAttr, space: NnMemorySpaceAttr)`

使用示例:
- from kernel_gen.dialect.nn import NnReduceSumOp

关联文件:
- spec: spec/dialect/nn.md
- test: test/dialect/nn/test_operation_reduce.py
- 功能实现: kernel_gen/dialect/nn/operation/reduce.py
"""

from __future__ import annotations

from collections .abc import Sequence

from kernel_gen .dialect .nn .attr .space_attr import NnMemorySpaceAttr
from kernel_gen .dialect .nn .type .memory_type import NnMemoryType
from xdsl .dialects .builtin import ArrayAttr ,IntAttr ,IntegerAttr
from xdsl .ir import Attribute ,Operation ,SSAValue
from xdsl .irdl import IRDLOperation ,attr_def ,irdl_op_definition ,operand_def ,result_def

from kernel_gen .core .error import ERROR_ACTION ,ERROR_ACTUAL ,ERROR_TEMPLATE ,ErrorKind ,ErrorModule ,kernel_code_error
from kernel_gen .core .contracts import raise_verify_error as core_raise_verify_error ,build_contiguous_stride as core_build_contiguous_stride ,verify_i64_attr as core_verify_i64_attr ,verify_memory_type as core_verify_memory_type

from xdsl .dialects .builtin import (
ArrayAttr ,
BFloat16Type ,
Float16Type ,
Float32Type ,
Float64Type ,
IntAttr ,
IntegerAttr ,
IntegerType ,
)


# Localized helpers from retired package-internal modules.

_ERROR_SCENE ="dialect.nn verifier"

class _NnReduceRules :
    """当前文件内的局部 verifier 规则容器。

    功能说明:
    - 合并本文件重复使用的局部规则，避免多个 private helper 互相调用。
    - 该容器不导出，不作为跨文件公开 API。

    使用示例:
    - _NN_REDUCE.symbol_expr_attr_from_expr(...)
    """

    @staticmethod
    def is_symbol_expr_attr (attr :Attribute )->bool :
        """判断属性是否是公开 SymbolExprAttr。

        功能说明:
        - 通过延迟导入的公开 class 判断 memory shape/stride 条目。

        使用示例:
        - _NN_REDUCE.is_symbol_expr_attr(SymbolExprAttr.from_expr("N"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        from kernel_gen .dialect .symbol import SymbolExprAttr

        return isinstance (attr ,SymbolExprAttr )

    @staticmethod
    def dim_expr_text (dim :Attribute )->str :
        """读取 SymbolExprAttr 的规范表达式文本。

        功能说明:
        - 统一 shape/stride 的比较、静态求值和 stride 推导入口。

        使用示例:
        - _NN_REDUCE.dim_expr_text(SymbolExprAttr.from_expr("N + 1"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        if not _NN_REDUCE .is_symbol_expr_attr (dim ):
            core_raise_verify_error (_ERROR_SCENE ,"dimension entries must be SymbolExprAttr")
        dim .verify ()
        return dim .expr .data

    def normalize_axes_attr (axes :Sequence [int ]|ArrayAttr )->ArrayAttr :
        """将归约 axes 规范化为 i64 ArrayAttr。


        功能说明:
        - 支持传入轴序列或 ArrayAttr。
        - 统一输出元素为 i64 IntegerAttr 的 ArrayAttr。

        使用示例:
        - normalize_axes_attr([0, 2])

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        if isinstance (axes ,ArrayAttr ):
            return axes
        return ArrayAttr ([IntegerAttr (int (axis ),IntegerType (64 ))for axis in axes ])

    def normalize_bool_attr (value :bool |int |IntegerAttr |IntAttr ,field_name :str )->IntegerAttr :
        """将布尔语义规范化为 i1 IntegerAttr。


        功能说明:
        - 支持 bool/int/IntAttr/IntegerAttr 输入，统一为 i1 IntegerAttr。
        - 具体合法性由 verifier 进一步校验。

        使用示例:
        - normalize_bool_attr(True, "keepdim")

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        if isinstance (value ,IntegerAttr ):
            return value
        if isinstance (value ,IntAttr ):
            value =value .data
        if isinstance (value ,bool ):
            value =1 if value else 0
        if not isinstance (value ,int ):
            raise TypeError (
            ERROR_TEMPLATE .format (
            scene ="dialect.nn 参数校验",
            expected =f"{field_name } must be bool/int or i1 attr",
            actual =type (value ).__name__ ,
            action =ERROR_ACTION ,
            )
            )
        return IntegerAttr (int (value ),IntegerType (1 ))

    def dims_equal (lhs :Attribute ,rhs :Attribute )->bool :
        """判断两个维度是否语义一致。


        功能说明:
        - SymbolExprAttr 按 canonical 表达式文本比较。

        使用示例:
        - dims_equal(SymbolExprAttr.from_expr("N + 1"), SymbolExprAttr.from_expr("1 + N"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """
        if _NN_REDUCE .is_symbol_expr_attr (lhs )and _NN_REDUCE .is_symbol_expr_attr (rhs ):
            return _NN_REDUCE .dim_expr_text (lhs )==_NN_REDUCE .dim_expr_text (rhs )
        return False

    def build_contiguous_stride (shape :Sequence [int ])->list [int ]:
        """按连续行主序构建 stride 列表。


        功能说明:
        - 以最后一维 stride=1 计算前序 stride。

        使用示例:
        - build_contiguous_stride([1, 4, 8])

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        return core_build_contiguous_stride (shape )


    @staticmethod
    def symbol_expr_attr_from_expr (expr :str )->Attribute :
        """构造公开 SymbolExprAttr。

        功能说明:
        - 延迟导入 `SymbolExprAttr`，避免 nn/symbol 模块初始化互相依赖。

        使用示例:
        - _NN_REDUCE.symbol_expr_attr_from_expr("N")

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        from kernel_gen .dialect .symbol import SymbolExprAttr

        return SymbolExprAttr .from_expr (expr )

    @staticmethod
    def is_symbol_expr_attr (attr :Attribute )->bool :
        """判断属性是否是公开 SymbolExprAttr。

        功能说明:
        - 通过延迟导入的公开 class 判断 memory shape/stride 条目。

        使用示例:
        - _NN_REDUCE.is_symbol_expr_attr(SymbolExprAttr.from_expr("N"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        from kernel_gen .dialect .symbol import SymbolExprAttr

        return isinstance (attr ,SymbolExprAttr )

    @staticmethod
    def dim_expr_text (dim :Attribute )->str :
        """读取 SymbolExprAttr 的规范表达式文本。

        功能说明:
        - 统一 shape/stride 的比较、静态求值和 stride 推导入口。

        使用示例:
        - _NN_REDUCE.dim_expr_text(SymbolExprAttr.from_expr("N + 1"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        if not _NN_REDUCE .is_symbol_expr_attr (dim ):
            core_raise_verify_error (_ERROR_SCENE ,"dimension entries must be SymbolExprAttr")
        dim .verify ()
        return dim .expr .data

    @staticmethod
    def static_int_from_expr_text (expr :str )->int |None :
        """尝试从规范表达式文本提取静态整数。

        功能说明:
        - 仅识别十进制整数字面量，动态表达式返回 None。

        使用示例:
        - _NN_REDUCE.static_int_from_expr_text("4")

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
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
        - _NN_REDUCE.static_int_from_dim(SymbolExprAttr.from_expr("4"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        return _NN_REDUCE .static_int_from_expr_text (_NN_REDUCE .dim_expr_text (dim ))

    @staticmethod
    def collect_int_dims (dims :Sequence [Attribute ])->list [int ]|None :
        """提取维度中的整数值列表。


        功能说明:
        - 仅当所有维度均为静态整数 SymbolExprAttr 时返回整数列表。
        - 任何动态 SymbolExprAttr 维度返回 None，表示无法进行数值合同校验。

        使用示例:
        - _NN_REDUCE.collect_int_dims([SymbolExprAttr.from_expr("1"), SymbolExprAttr.from_expr("2")])

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        values :list [int ]=[]
        for dim in dims :
            value =_NN_REDUCE .static_int_from_dim (dim )
            if value is None :
                return None
            values .append (value )
        return values

    @staticmethod
    def verify_reduce_axes (axes :ArrayAttr ,rank :int )->list [int ]:
        """校验归约 axes 并返回整数列表。


        功能说明:
        - 校验 axes 非空、元素唯一且在合法范围内。
        - 仅接受 i64 IntegerAttr 轴值。

        使用示例:
        - axes = _NN_REDUCE.verify_reduce_axes(ArrayAttr([IntegerAttr(1, IntegerType(64))]), rank=3)

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        if len (axes .data )==0 :
            core_raise_verify_error (_ERROR_SCENE ,"axes-must-be-non-empty-unique-and-in-range")

        values :list [int ]=[]
        for entry in axes .data :
            if not isinstance (entry ,IntegerAttr ):
                core_raise_verify_error (_ERROR_SCENE ,"axes-must-be-non-empty-unique-and-in-range")
            width_attr =entry .type .width
            width_value =width_attr .data if isinstance (width_attr ,IntAttr )else width_attr
            if width_value !=64 :
                core_raise_verify_error (_ERROR_SCENE ,"axes-must-be-non-empty-unique-and-in-range")
            axis_value =entry .value .data
            if axis_value <0 or axis_value >=rank :
                core_raise_verify_error (_ERROR_SCENE ,"axes-must-be-non-empty-unique-and-in-range")
            values .append (axis_value )

        if len (set (values ))!=len (values ):
            core_raise_verify_error (_ERROR_SCENE ,"axes-must-be-non-empty-unique-and-in-range")

        return values

    @staticmethod
    def verify_keepdim_attr (keepdim :IntegerAttr )->bool :
        """校验 keepdim 的 i1 布尔属性并返回布尔值。


        功能说明:
        - 仅接受 i1 IntegerAttr，且值必须为 0/1/-1（i1 真值可能以 -1 表示）。

        使用示例:
        - keep = _NN_REDUCE.verify_keepdim_attr(IntegerAttr(1, IntegerType(1)))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        if not isinstance (keepdim ,IntegerAttr ):
            core_raise_verify_error (_ERROR_SCENE ,"keepdim-must-be-i1-bool-attr")
        width_attr =keepdim .type .width
        width_value =width_attr .data if isinstance (width_attr ,IntAttr )else width_attr
        if width_value !=1 :
            core_raise_verify_error (_ERROR_SCENE ,"keepdim-must-be-i1-bool-attr")
        value =keepdim .value .data
        if value not in (0 ,1 ,-1 ):
            core_raise_verify_error (_ERROR_SCENE ,"keepdim-must-be-i1-bool-attr")
        return value !=0

    @staticmethod
    def build_reduce_result_shape (
    input_dims :Sequence [Attribute ],
    axes :set [int ],
    keepdim :bool ,
    )->list [Attribute ]:
        """构造归约结果的 shape 属性列表。


        功能说明:
        - keepdim=true 时将归约轴替换为 1。
        - keepdim=false 时移除归约轴；若结果 rank 为 0 则规范为 [1]。

        使用示例:
        - _NN_REDUCE.build_reduce_result_shape([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("3")], {0}, keepdim=False)

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        if keepdim :
            one =_NN_REDUCE .symbol_expr_attr_from_expr ("1")
            return [one if index in axes else dim for index ,dim in enumerate (input_dims )]

        result_dims =[dim for index ,dim in enumerate (input_dims )if index not in axes ]
        if not result_dims :
            return [_NN_REDUCE .symbol_expr_attr_from_expr ("1")]
        return result_dims

    @staticmethod
    def verify_reduce_result_shape (result_type :NnMemoryType ,expected_shape :Sequence [Attribute ])->None :
        """校验归约结果 shape 合同。


        功能说明:
        - 比较结果 shape 与期望 shape 的长度与逐维一致性。

        使用示例:
        - _NN_REDUCE.verify_reduce_result_shape(result_type, expected_shape)

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        if len (result_type .shape .data )!=len (expected_shape ):
            core_raise_verify_error (_ERROR_SCENE ,"result-shape-must-match-reduce-contract")

        for expected_dim ,actual_dim in zip (expected_shape ,result_type .shape .data ,strict =True ):
            if not _NnReduceHelpers .dims_equal (expected_dim ,actual_dim ):
                core_raise_verify_error (_ERROR_SCENE ,"result-shape-must-match-reduce-contract")

    @staticmethod
    def verify_reduce_result_stride (result_type :NnMemoryType ,expected_shape :Sequence [Attribute ])->None :
        """校验归约结果 stride 必须为连续布局。


        功能说明:
        - 仅在结果 shape 静态可判定时校验 stride 等于连续布局。

        使用示例:
        - _NN_REDUCE.verify_reduce_result_stride(result_type, expected_shape)

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        expected_dims =_NN_REDUCE .collect_int_dims (expected_shape )
        if expected_dims is None :
            return

        result_strides =_NN_REDUCE .collect_int_dims (result_type .stride .data )
        if result_strides is None :
            core_raise_verify_error (_ERROR_SCENE ,"result-stride-must-be-contiguous-for-result-shape")

        expected_stride =_NnReduceHelpers .build_contiguous_stride (expected_dims )
        if result_strides !=expected_stride :
            core_raise_verify_error (_ERROR_SCENE ,"result-stride-must-be-contiguous-for-result-shape")

    @staticmethod
    def verify_non_empty_reduction_extent (input_dims :Sequence [Attribute ],axes :Sequence [int ])->None :
        """校验静态归约轴的维度不为空。


        功能说明:
        - 对静态维度为 0 的归约轴直接报错。

        使用示例:
        - _NN_REDUCE.verify_non_empty_reduction_extent([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("0")], [1])

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        for axis in axes :
            dim =input_dims [axis ]
            if _NN_REDUCE .static_int_from_dim (dim )==0 :
                core_raise_verify_error (_ERROR_SCENE ,"empty-reduction-extent-must-be-rejected-when-static")

_NN_REDUCE =_NnReduceRules ()

class _NnReduceHelpers :
    """当前文件内本地 helper 容器。

    功能说明:
    - 承接退场 common.py 后的文件内 helper，避免形成模块级事实公开函数。

    使用示例:
    - _NnReduceHelpers.helper(...)
    """

    @staticmethod
    def normalize_axes_attr (axes :Sequence [int ]|ArrayAttr )->ArrayAttr :
        """将归约 axes 规范化为 i64 ArrayAttr。

        功能说明:
        - 支持传入轴序列或 ArrayAttr。

        使用示例:
        - normalize_axes_attr([0, 2])
        """

        if isinstance (axes ,ArrayAttr ):
            return axes
        return ArrayAttr ([IntegerAttr (int (axis ),IntegerType (64 ))for axis in axes ])

    @staticmethod
    def normalize_bool_attr (value :bool |int |IntegerAttr |IntAttr ,field_name :str )->IntegerAttr :
        """将布尔语义规范化为 i1 IntegerAttr。

        功能说明:
        - 支持 bool/int/IntAttr/IntegerAttr 输入，统一为 i1 IntegerAttr。

        使用示例:
        - normalize_bool_attr(True, "keepdim")
        """

        if isinstance (value ,IntegerAttr ):
            return value
        if isinstance (value ,IntAttr ):
            value =value .data
        if isinstance (value ,bool ):
            value =1 if value else 0
        if not isinstance (value ,int ):
            raise TypeError (
            ERROR_TEMPLATE .format (
            scene ="dialect.nn 参数校验",
            expected =f"{field_name } must be bool/int or i1 attr",
            actual =type (value ).__name__ ,
            action =ERROR_ACTION ,
            )
            )
        return IntegerAttr (int (value ),IntegerType (1 ))

    @staticmethod
    def dims_equal (lhs :Attribute ,rhs :Attribute )->bool :
        """判断两个维度是否语义一致。

        功能说明:
        - SymbolExprAttr 按 canonical 表达式文本比较。

        使用示例:
        - dims_equal(SymbolExprAttr.from_expr("N + 1"), SymbolExprAttr.from_expr("1 + N"))
        """

        if _NN_REDUCE .is_symbol_expr_attr (lhs )and _NN_REDUCE .is_symbol_expr_attr (rhs ):
            return _NN_REDUCE .dim_expr_text (lhs )==_NN_REDUCE .dim_expr_text (rhs )
        return False

    @staticmethod
    def build_contiguous_stride (shape :Sequence [int ])->list [int ]:
        """按连续行主序构建 stride 列表。

        功能说明:
        - 以最后一维 stride=1 计算前序 stride。

        使用示例:
        - build_contiguous_stride([1, 4, 8])
        """

        return core_build_contiguous_stride (shape )





def _verify_reduce_op (op :"NnReduceSumOp | NnReduceMinOp | NnReduceMaxOp",*,require_non_empty :bool )->None :
    """统一校验 nn.reduce_* 的结构化合同。


    功能说明:
    - 校验 input/result 类型、axes/keepdim、shape/stride 与空间一致性。
    - 按需检查静态空归约域错误路径。

    使用示例:
    - _verify_reduce_op(op, require_non_empty=True)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    input_type =op .input .type
    result_type =op .result .type
    if not isinstance (input_type ,NnMemoryType )or not isinstance (result_type ,NnMemoryType ):
        core_raise_verify_error (_ERROR_SCENE ,"operand-must-be-nn-memory")
    input_type .verify ()
    result_type .verify ()

    axes =_NN_REDUCE .verify_reduce_axes (op .axes ,len (input_type .shape .data ))
    keepdim =_NN_REDUCE .verify_keepdim_attr (op .keepdim )

    if require_non_empty :
        _NN_REDUCE .verify_non_empty_reduction_extent (input_type .shape .data ,axes )

    if result_type .element_type !=input_type .element_type :
        core_raise_verify_error (_ERROR_SCENE ,"result-element-type-must-match-input")

    op .space .verify ()
    if input_type .space .space .data !=result_type .space .space .data :
        core_raise_verify_error (_ERROR_SCENE ,"result-space-must-match-input-and-attr")
    if input_type .space .space .data !=op .space .space .data :
        core_raise_verify_error (_ERROR_SCENE ,"result-space-must-match-input-and-attr")

    expected_shape =_NN_REDUCE .build_reduce_result_shape (input_type .shape .data ,set (axes ),keepdim )
    _NN_REDUCE .verify_reduce_result_shape (result_type ,expected_shape )
    _NN_REDUCE .verify_reduce_result_stride (result_type ,expected_shape )

@irdl_op_definition
class NnReduceSumOp (IRDLOperation ):
    """nn.reduce_sum。


    功能说明:
    - 定义 nn.reduce_sum 方言 op 与 verifier 约束。

    使用示例:
    - NnReduceSumOp(inp, result_type, axes=[1], keepdim=True, space=NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    name ="nn.reduce_sum"

    input =operand_def (NnMemoryType )
    result =result_def (NnMemoryType )
    axes =attr_def (ArrayAttr )
    keepdim =attr_def (IntegerAttr )
    space =attr_def (NnMemorySpaceAttr )

    def __init__ (
    self ,
    input_value :SSAValue |Operation ,
    result_type :NnMemoryType ,
    axes :Sequence [int ]|ArrayAttr ,
    keepdim :bool |int |IntegerAttr |IntAttr ,
    space :NnMemorySpaceAttr ,
    )->None :
        """初始化 reduce_sum op。


        功能说明:
        - 绑定输入、结果类型、axes/keepdim 与 space 属性。

        使用示例:
        - NnReduceSumOp(inp, result_type, axes=[1], keepdim=True, space=NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """
        axes_attr =_NnReduceHelpers .normalize_axes_attr (axes )
        keepdim_attr =_NnReduceHelpers .normalize_bool_attr (keepdim ,"keepdim")
        super ().__init__ (
        operands =[input_value ],
        result_types =[result_type ],
        attributes ={
        "axes":axes_attr ,
        "keepdim":keepdim_attr ,
        "space":space ,
        },
        )

    def verify_ (self )->None :
        """校验 nn.reduce_sum verifier 合同。


        功能说明:
        - 调用统一的归约合同校验逻辑。

        使用示例:
        - NnReduceSumOp(inp, result_type, axes=[1], keepdim=True, space=NnMemorySpaceAttr.from_name("global")).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """
        _verify_reduce_op (self ,require_non_empty =False )

@irdl_op_definition
class NnReduceMinOp (IRDLOperation ):
    """nn.reduce_min。


    功能说明:
    - 定义 nn.reduce_min 方言 op 与 verifier 约束。

    使用示例:
    - NnReduceMinOp(inp, result_type, axes=[1], keepdim=False, space=NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    name ="nn.reduce_min"

    input =operand_def (NnMemoryType )
    result =result_def (NnMemoryType )
    axes =attr_def (ArrayAttr )
    keepdim =attr_def (IntegerAttr )
    space =attr_def (NnMemorySpaceAttr )

    def __init__ (
    self ,
    input_value :SSAValue |Operation ,
    result_type :NnMemoryType ,
    axes :Sequence [int ]|ArrayAttr ,
    keepdim :bool |int |IntegerAttr |IntAttr ,
    space :NnMemorySpaceAttr ,
    )->None :
        """初始化 reduce_min op。


        功能说明:
        - 绑定输入、结果类型、axes/keepdim 与 space 属性。

        使用示例:
        - NnReduceMinOp(inp, result_type, axes=[1], keepdim=False, space=NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """
        axes_attr =_NnReduceHelpers .normalize_axes_attr (axes )
        keepdim_attr =_NnReduceHelpers .normalize_bool_attr (keepdim ,"keepdim")
        super ().__init__ (
        operands =[input_value ],
        result_types =[result_type ],
        attributes ={
        "axes":axes_attr ,
        "keepdim":keepdim_attr ,
        "space":space ,
        },
        )

    def verify_ (self )->None :
        """校验 nn.reduce_min verifier 合同。


        功能说明:
        - 调用归约合同校验逻辑，并拒绝静态空归约域。

        使用示例:
        - NnReduceMinOp(inp, result_type, axes=[1], keepdim=False, space=NnMemorySpaceAttr.from_name("global")).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """
        _verify_reduce_op (self ,require_non_empty =True )

@irdl_op_definition
class NnReduceMaxOp (IRDLOperation ):
    """nn.reduce_max。


    功能说明:
    - 定义 nn.reduce_max 方言 op 与 verifier 约束。

    使用示例:
    - NnReduceMaxOp(inp, result_type, axes=[1], keepdim=False, space=NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    name ="nn.reduce_max"

    input =operand_def (NnMemoryType )
    result =result_def (NnMemoryType )
    axes =attr_def (ArrayAttr )
    keepdim =attr_def (IntegerAttr )
    space =attr_def (NnMemorySpaceAttr )

    def __init__ (
    self ,
    input_value :SSAValue |Operation ,
    result_type :NnMemoryType ,
    axes :Sequence [int ]|ArrayAttr ,
    keepdim :bool |int |IntegerAttr |IntAttr ,
    space :NnMemorySpaceAttr ,
    )->None :
        """初始化 reduce_max op。


        功能说明:
        - 绑定输入、结果类型、axes/keepdim 与 space 属性。

        使用示例:
        - NnReduceMaxOp(inp, result_type, axes=[1], keepdim=False, space=NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """
        axes_attr =_NnReduceHelpers .normalize_axes_attr (axes )
        keepdim_attr =_NnReduceHelpers .normalize_bool_attr (keepdim ,"keepdim")
        super ().__init__ (
        operands =[input_value ],
        result_types =[result_type ],
        attributes ={
        "axes":axes_attr ,
        "keepdim":keepdim_attr ,
        "space":space ,
        },
        )

    def verify_ (self )->None :
        """校验 nn.reduce_max verifier 合同。


        功能说明:
        - 调用归约合同校验逻辑，并拒绝静态空归约域。

        使用示例:
        - NnReduceMaxOp(inp, result_type, axes=[1], keepdim=False, space=NnMemorySpaceAttr.from_name("global")).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """
        _verify_reduce_op (self ,require_non_empty =True )

__all__ =["NnReduceSumOp","NnReduceMinOp","NnReduceMaxOp"]
