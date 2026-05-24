"""nn select cast broadcast transpose operations.

功能说明:
- 承载 nn dialect package 拆分后的 nn select cast broadcast transpose operations 实现。

API 列表:
- `class NnSelectOp(pred: SSAValue, on_true: SSAValue, on_false: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnCastOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnBroadcastOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnTransposeOp(input_value: SSAValue, result_type: NnMemoryType, perm: Sequence[int] | ArrayAttr[IntegerAttr], space: NnMemorySpaceAttr)`

使用示例:
- from kernel_gen.dialect.nn import NnBroadcastOp

关联文件:
- spec: spec/dialect/nn.md
- test: test/dialect/nn/test_operation_elewise.py
- 功能实现: kernel_gen/dialect/nn/operation/elewise.py
"""

from __future__ import annotations

from collections .abc import Sequence

from kernel_gen .dialect .nn .attr .space_attr import NnMemorySpaceAttr
from kernel_gen .dialect .nn .type .memory_type import NnMemoryType
from xdsl .dialects .builtin import ArrayAttr ,IntAttr ,IntegerAttr ,i1
from xdsl .ir import Attribute ,Operation ,SSAValue
from xdsl .irdl import IRDLOperation ,attr_def ,irdl_op_definition ,operand_def ,result_def

from kernel_gen .core .error import ERROR_ACTION ,ERROR_ACTUAL ,ERROR_TEMPLATE ,ErrorKind ,ErrorModule ,kernel_code_error
from kernel_gen .core .contracts import raise_verify_error as core_raise_verify_error ,build_contiguous_stride as core_build_contiguous_stride ,verify_i64_attr as core_verify_i64_attr ,verify_memory_type as core_verify_memory_type


# Localized helpers from retired package-internal modules.

_ERROR_SCENE ="dialect.nn verifier"

class _NnElewiseRules :
    """当前文件内的局部 verifier 规则容器。

    功能说明:
    - 合并本文件重复使用的局部规则，避免多个 private helper 互相调用。
    - 该容器不导出，不作为跨文件公开 API。

    使用示例:
    - _NN_ELEWISE.symbol_expr_attr_from_expr(...)
    """

    @staticmethod
    def is_symbol_expr_attr (attr :Attribute )->bool :
        """判断属性是否是公开 SymbolExprAttr。

        功能说明:
        - 通过延迟导入的公开 class 判断 memory shape/stride 条目。

        使用示例:
        - _NN_ELEWISE.is_symbol_expr_attr(SymbolExprAttr.from_expr("N"))

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
        - _NN_ELEWISE.dim_expr_text(SymbolExprAttr.from_expr("N + 1"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        if not _NN_ELEWISE .is_symbol_expr_attr (dim ):
            core_raise_verify_error (_ERROR_SCENE ,"dimension entries must be SymbolExprAttr")
        dim .verify ()
        return dim .expr .data

    def verify_memory_type (value :Attribute ,field_name :str )->"NnMemoryType":
        """校验并返回 memory type。

        功能说明:
        - 确认 `value` 是公开 `NnMemoryType`，并执行通用 memory type 校验。
        - `field_name` 用于在稳定错误文本中定位被校验字段。

        使用示例:
        - input_type = verify_memory_type(op.input.type, "input")
        """

        return core_verify_memory_type (value ,field_name ,scene =_ERROR_SCENE )

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
        if _NN_ELEWISE .is_symbol_expr_attr (lhs )and _NN_ELEWISE .is_symbol_expr_attr (rhs ):
            return _NN_ELEWISE .dim_expr_text (lhs )==_NN_ELEWISE .dim_expr_text (rhs )
        return False


    @staticmethod
    def symbol_expr_attr_from_expr (expr :str )->Attribute :
        """构造公开 SymbolExprAttr。

        功能说明:
        - 延迟导入 `SymbolExprAttr`，避免 nn/symbol 模块初始化互相依赖。

        使用示例:
        - _NN_ELEWISE.symbol_expr_attr_from_expr("N")

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
        - _NN_ELEWISE.is_symbol_expr_attr(SymbolExprAttr.from_expr("N"))

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
        - _NN_ELEWISE.dim_expr_text(SymbolExprAttr.from_expr("N + 1"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        if not _NN_ELEWISE .is_symbol_expr_attr (dim ):
            core_raise_verify_error (_ERROR_SCENE ,"dimension entries must be SymbolExprAttr")
        dim .verify ()
        return dim .expr .data

    @staticmethod
    def static_int_from_expr_text (expr :str )->int |None :
        """尝试从规范表达式文本提取静态整数。

        功能说明:
        - 仅识别十进制整数字面量，动态表达式返回 None。

        使用示例:
        - _NN_ELEWISE.static_int_from_expr_text("4")

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
        - _NN_ELEWISE.static_int_from_dim(SymbolExprAttr.from_expr("4"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        return _NN_ELEWISE .static_int_from_expr_text (_NN_ELEWISE .dim_expr_text (dim ))

    @staticmethod
    def verify_broadcast_compat (input_type :NnMemoryType ,result_type :NnMemoryType )->None :
        """校验 nn.broadcast 的 shape 兼容性。


        功能说明:
        - 按尾维对齐规则检查输入与输出 shape。
        - 仅允许 input 维为 1 时向任意目标维扩张。

        使用示例:
        - _NN_ELEWISE.verify_broadcast_compat(input_type, result_type)

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """
        input_dims =input_type .shape .data
        result_dims =result_type .shape .data
        if len (result_dims )<len (input_dims ):
            core_raise_verify_error (_ERROR_SCENE ,"result-rank-must-be-greater-or-equal-to-input")

        for input_dim ,result_dim in zip (reversed (input_dims ),reversed (result_dims ),strict =False ):
            if _NnElewiseHelpers .dims_equal (input_dim ,result_dim ):
                continue
            if _NN_ELEWISE .static_int_from_dim (input_dim )==1 :
                continue
            core_raise_verify_error (_ERROR_SCENE ,"result-shape-must-match-broadcast-contract")

    @staticmethod
    def verify_transpose_perm (perm :ArrayAttr ,rank :int )->list [int ]:
        """校验 nn.transpose 的 perm 合法性并返回序列。


        功能说明:
        - 校验 perm 长度与 rank 一致。
        - 校验 perm 为 0..rank-1 的排列。

        使用示例:
        - _NN_ELEWISE.verify_transpose_perm(ArrayAttr([IntAttr(1), IntAttr(0)]), rank=2)

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """
        if len (perm .data )!=rank :
            core_raise_verify_error (_ERROR_SCENE ,"nn.transpose perm must match input rank")
        perm_values :list [int ]=[]
        for entry in perm .data :
            if isinstance (entry ,IntAttr ):
                perm_values .append (entry .data )
                continue
            if isinstance (entry ,IntegerAttr )and isinstance (entry .value ,IntAttr ):
                perm_values .append (entry .value .data )
                continue
            core_raise_verify_error (_ERROR_SCENE ,"nn.transpose perm must be a permutation of 0..rank-1")
        if sorted (perm_values )!=list (range (rank )):
            core_raise_verify_error (_ERROR_SCENE ,"nn.transpose perm must be a permutation of 0..rank-1")
        return perm_values

    @staticmethod
    def verify_transpose_layout (
    input_type :NnMemoryType ,
    result_type :NnMemoryType ,
    perm_values :Sequence [int ],
    )->None :
        """校验 nn.transpose 的 shape 与物化结果 stride。


        功能说明:
        - 按 perm 重排 input shape，并与 result shape 对齐校验。
        - result stride 必须是 result shape 的默认连续 stride。

        使用示例:
        - _NN_ELEWISE.verify_transpose_layout(input_type, result_type, [1, 0])

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """
        expected_shape =[input_type .shape .data [index ]for index in perm_values ]
        for expected_dim ,actual_dim in zip (expected_shape ,result_type .shape .data ,strict =True ):
            if not _NnElewiseHelpers .dims_equal (expected_dim ,actual_dim ):
                core_raise_verify_error (_ERROR_SCENE ,"nn.transpose result shape must match permuted input")

        expected_stride =_NN_ELEWISE .default_contiguous_stride (result_type .shape )
        for expected_dim ,actual_dim in zip (expected_stride ,result_type .stride .data ,strict =True ):
            if not _NnElewiseHelpers .dims_equal (expected_dim ,actual_dim ):
                core_raise_verify_error (_ERROR_SCENE ,"nn.transpose result stride must be contiguous")

    @staticmethod
    def default_contiguous_stride (shape :ArrayAttr [Attribute ])->list [Attribute ]:
        """按默认连续布局生成行主序 stride。


        功能说明:
        - 静态维度返回 `#symbol.expr<整数>`。
        - 符号维度返回 canonical `#symbol.expr<乘积>`。
        - `#symbol.expr<?>` 维度会把更高维 stride 退化为 `#symbol.expr<?>`。

        使用示例:
        - _NN_ELEWISE.default_contiguous_stride(ArrayAttr([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("4")]))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        stride :list [Attribute ]=[]
        running :str |None ="1"
        for dim in reversed (shape .data ):
            if running is None :
                stride .append (_NN_ELEWISE .symbol_expr_attr_from_expr ("?"))
            else :
                stride .append (_NN_ELEWISE .symbol_expr_attr_from_expr (running ))
            if running is None :
                continue
            dim_expr =_NN_ELEWISE .dim_expr_text (dim )
            if dim_expr =="?":
                running =None
            elif dim_expr =="1":
                continue
            elif running =="1":
                running =dim_expr
            else :
                running =_NN_ELEWISE .dim_expr_text (_NN_ELEWISE .symbol_expr_attr_from_expr (f"{dim_expr }*{running }"))
        stride .reverse ()
        return stride

_NN_ELEWISE =_NnElewiseRules ()

class _NnElewiseHelpers :
    """当前文件内本地 helper 容器。

    功能说明:
    - 承接退场 common.py 后的文件内 helper，避免形成模块级事实公开函数。

    使用示例:
    - _NnElewiseHelpers.helper(...)
    """

    @staticmethod
    def verify_memory_type (value :Attribute ,field_name :str )->"NnMemoryType":
        """校验并返回 memory type。

        功能说明:
        - 确认 `value` 是公开 `NnMemoryType`，并执行通用 memory type 校验。

        使用示例:
        - input_type = verify_memory_type(op.input.type, "input")
        """

        return core_verify_memory_type (value ,field_name ,scene =_ERROR_SCENE )

    @staticmethod
    def dims_equal (lhs :Attribute ,rhs :Attribute )->bool :
        """判断两个维度是否语义一致。

        功能说明:
        - SymbolExprAttr 按 canonical 表达式文本比较。

        使用示例:
        - dims_equal(SymbolExprAttr.from_expr("N + 1"), SymbolExprAttr.from_expr("1 + N"))
        """

        if _NN_ELEWISE .is_symbol_expr_attr (lhs )and _NN_ELEWISE .is_symbol_expr_attr (rhs ):
            return _NN_ELEWISE .dim_expr_text (lhs )==_NN_ELEWISE .dim_expr_text (rhs )
        return False



def _verify_select_op (op :"NnSelectOp")->None :
    """校验 nn.select 的结构化合同。


    功能说明:
    - 校验 cond/lhs/rhs/result 均为 nn.memory。
    - cond element_type 必须为 i1。
    - lhs/rhs/result 的 shape/stride/space 必须一致。

    使用示例:
    - _verify_select_op(op)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    cond_type =_NnElewiseHelpers .verify_memory_type (op .cond .type ,"cond")
    lhs_type =_NnElewiseHelpers .verify_memory_type (op .lhs .type ,"lhs")
    rhs_type =_NnElewiseHelpers .verify_memory_type (op .rhs .type ,"rhs")
    result_type =_NnElewiseHelpers .verify_memory_type (op .result .type ,"result")

    if cond_type .element_type !=i1 :
        core_raise_verify_error (_ERROR_SCENE ,"nn.select cond element_type must be i1")

    op .space .verify ()
    if lhs_type .space .space .data !=rhs_type .space .space .data :
        core_raise_verify_error (_ERROR_SCENE ,"nn.select operands must use the same space")
    if lhs_type .space .space .data !=op .space .space .data :
        core_raise_verify_error (_ERROR_SCENE ,"nn.select attribute space must match operand space")
    if result_type .space .space .data !=op .space .space .data :
        core_raise_verify_error (_ERROR_SCENE ,"nn.select attribute space must match result space")

    if lhs_type .shape !=rhs_type .shape or lhs_type .shape !=result_type .shape :
        core_raise_verify_error (_ERROR_SCENE ,"nn.select shape must match across operands and result")
    if lhs_type .stride !=rhs_type .stride or lhs_type .stride !=result_type .stride :
        core_raise_verify_error (_ERROR_SCENE ,"nn.select stride must match across operands and result")
    if lhs_type .element_type !=rhs_type .element_type :
        core_raise_verify_error (_ERROR_SCENE ,"nn.select operand element_type must match")
    if result_type .element_type !=lhs_type .element_type :
        core_raise_verify_error (_ERROR_SCENE ,"nn.select result element_type must match operand element_type")

@irdl_op_definition
class NnSelectOp (IRDLOperation ):
    """nn.select。


    功能说明:
    - 定义 nn.select 方言 op 与 verifier 约束。

    使用示例:
    - NnSelectOp(cond, lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    name ="nn.select"

    cond =operand_def (NnMemoryType )
    lhs =operand_def (NnMemoryType )
    rhs =operand_def (NnMemoryType )
    result =result_def (NnMemoryType )
    space =attr_def (NnMemorySpaceAttr )

    def __init__ (
    self ,
    cond :SSAValue |Operation ,
    lhs :SSAValue |Operation ,
    rhs :SSAValue |Operation ,
    result_type :NnMemoryType ,
    space :NnMemorySpaceAttr ,
    )->None :
        """初始化 nn.select op。


        功能说明:
        - 绑定 cond/lhs/rhs、结果类型与 space。

        使用示例:
        - NnSelectOp(cond, lhs, rhs, result_type, space)

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        super ().__init__ (
        operands =[cond ,lhs ,rhs ],
        result_types =[result_type ],
        attributes ={"space":space },
        )

    def verify_ (self )->None :
        """校验 nn.select 的 verifier 合同。


        功能说明:
        - 调用统一 select 校验逻辑。

        使用示例:
        - NnSelectOp(...).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        _verify_select_op (self )

def _verify_cast_op (op :"NnCastOp")->None :
    """校验 nn.cast 的结构化合同。


    功能说明:
    - 校验 input/result 必须为 nn.memory。
    - shape/stride/space 必须一致，element_type 允许变化。

    使用示例:
    - _verify_cast_op(op)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    input_type =_NnElewiseHelpers .verify_memory_type (op .input .type ,"input")
    result_type =_NnElewiseHelpers .verify_memory_type (op .result .type ,"result")

    op .space .verify ()
    if input_type .space .space .data !=op .space .space .data :
        core_raise_verify_error (_ERROR_SCENE ,"nn.cast attribute space must match operand space")
    if result_type .space .space .data !=op .space .space .data :
        core_raise_verify_error (_ERROR_SCENE ,"nn.cast attribute space must match result space")

    if input_type .shape !=result_type .shape :
        core_raise_verify_error (_ERROR_SCENE ,"nn.cast shape must match input")
    if input_type .stride !=result_type .stride :
        core_raise_verify_error (_ERROR_SCENE ,"nn.cast stride must match input")

@irdl_op_definition
class NnCastOp (IRDLOperation ):
    """nn.cast。


    功能说明:
    - 定义 nn.cast 方言 op 与 verifier 约束。

    使用示例:
    - NnCastOp(input_value, result_type, NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    name ="nn.cast"

    input =operand_def (NnMemoryType )
    result =result_def (NnMemoryType )
    space =attr_def (NnMemorySpaceAttr )

    def __init__ (
    self ,
    input_value :SSAValue |Operation ,
    result_type :NnMemoryType ,
    space :NnMemorySpaceAttr ,
    )->None :
        """初始化 nn.cast op。


        功能说明:
        - 绑定输入、结果类型与 space。

        使用示例:
        - NnCastOp(input_value, result_type, space)

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        super ().__init__ (
        operands =[input_value ],
        result_types =[result_type ],
        attributes ={"space":space },
        )

    def verify_ (self )->None :
        """校验 nn.cast 的 verifier 合同。


        功能说明:
        - 调用统一 cast 校验逻辑。

        使用示例:
        - NnCastOp(...).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        _verify_cast_op (self )

@irdl_op_definition
class NnBroadcastOp (IRDLOperation ):
    """nn.broadcast。


    功能说明:
    - 表达 nn dialect 的显式 broadcast。
    - 按尾维对齐规则校验 shape 与 space/element_type 一致性。

    使用示例:
    - NnBroadcastOp(inp, result_type, NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    name ="nn.broadcast"

    input =operand_def (NnMemoryType )
    result =result_def (NnMemoryType )
    space =attr_def (NnMemorySpaceAttr )

    def __init__ (
    self ,
    input_value :SSAValue |Operation ,
    result_type :NnMemoryType ,
    space :NnMemorySpaceAttr ,
    )->None :
        """初始化 broadcast op。


        功能说明:
        - 绑定输入 operand、结果类型与 space 属性。

        使用示例:
        - NnBroadcastOp(inp, result_type, NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """
        super ().__init__ (
        operands =[input_value ],
        result_types =[result_type ],
        attributes ={"space":space },
        )

    def verify_ (self )->None :
        """校验 nn.broadcast 的 memory 与 broadcast 合同。

        功能说明:
        - 校验 input/result 均为 `NnMemoryType` 且 space/element_type 与 attr 一致。
        - 校验 result shape/stride 满足公开 broadcast 兼容规则。

        使用示例:
        - NnBroadcastOp(inp, result_type, space).verify_()
        """
        input_type =self .input .type
        result_type =self .result .type
        if not isinstance (input_type ,NnMemoryType )or not isinstance (result_type ,NnMemoryType ):
            core_raise_verify_error (_ERROR_SCENE ,"operand-must-be-nn-memory")
        input_type .verify ()
        result_type .verify ()

        self .space .verify ()
        if input_type .space .space .data !=result_type .space .space .data :
            core_raise_verify_error (_ERROR_SCENE ,"result-space-must-match-input-and-attr")
        if input_type .space .space .data !=self .space .space .data :
            core_raise_verify_error (_ERROR_SCENE ,"result-space-must-match-input-and-attr")
        if input_type .element_type !=result_type .element_type :
            core_raise_verify_error (_ERROR_SCENE ,"result-element-type-must-match-input")

        _NN_ELEWISE .verify_broadcast_compat (input_type ,result_type )

@irdl_op_definition
class NnTransposeOp (IRDLOperation ):
    """nn.transpose。


    功能说明:
    - 定义 nn.transpose 方言 op 与 verifier 约束。

    使用示例:
    - NnTransposeOp(inp, result_type, perm=[1, 0], space=NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    name ="nn.transpose"

    input =operand_def (NnMemoryType )
    result =result_def (NnMemoryType )
    perm =attr_def (ArrayAttr )
    space =attr_def (NnMemorySpaceAttr )

    def __init__ (
    self ,
    input_value :SSAValue |Operation ,
    result_type :NnMemoryType ,
    perm :Sequence [int ]|ArrayAttr ,
    space :NnMemorySpaceAttr ,
    )->None :
        """初始化 transpose op。


        功能说明:
        - 绑定输入、结果类型、perm 与 space 属性。

        使用示例:
        - NnTransposeOp(inp, result_type, perm=[1, 0], space=NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """
        perm_attr =perm if isinstance (perm ,ArrayAttr )else ArrayAttr ([IntAttr (value )for value in perm ])
        super ().__init__ (
        operands =[input_value ],
        result_types =[result_type ],
        attributes ={"perm":perm_attr ,"space":space },
        )

    def verify_ (self )->None :
        """校验 nn.transpose 的 perm 与 layout 合同。

        功能说明:
        - 校验 input/result memory type、space 和 element_type 保持一致。
        - 校验 perm 是合法排列，并检查 result shape/stride 与 transpose layout 匹配。

        使用示例:
        - NnTransposeOp(inp, result_type, perm=[1, 0], space=space).verify_()
        """
        input_type =_NnElewiseHelpers .verify_memory_type (self .input .type ,"input")
        result_type =_NnElewiseHelpers .verify_memory_type (self .result .type ,"result")

        self .space .verify ()
        if input_type .space .space .data !=result_type .space .space .data :
            core_raise_verify_error (_ERROR_SCENE ,"nn.transpose input/result must use the same space")
        if input_type .space .space .data !=self .space .space .data :
            core_raise_verify_error (_ERROR_SCENE ,"nn.transpose attribute space must match type space")

        if input_type .element_type !=result_type .element_type :
            core_raise_verify_error (_ERROR_SCENE ,"nn.transpose element_type must match")

        perm_values =_NN_ELEWISE .verify_transpose_perm (self .perm ,len (input_type .shape .data ))
        _NN_ELEWISE .verify_transpose_layout (input_type ,result_type ,perm_values )

__all__ =["NnSelectOp","NnCastOp","NnBroadcastOp","NnTransposeOp"]
