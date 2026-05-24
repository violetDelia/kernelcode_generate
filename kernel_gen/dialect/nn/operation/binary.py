"""nn binary and compare operations.

功能说明:
- 承载 nn dialect package 拆分后的 nn binary and compare operations 实现。

API 列表:
- `class NnAddOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnSubOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnMulOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnDivOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnTrueDivOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnFloorDivOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnEqOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnNeOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnLtOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnLeOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnGtOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnGeOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

使用示例:
- from kernel_gen.dialect.nn import NnAddOp

关联文件:
- spec: spec/dialect/nn.md
- test: test/dialect/nn/test_operation_binary.py
- 功能实现: kernel_gen/dialect/nn/operation/binary.py
"""

from __future__ import annotations

from kernel_gen .dialect .nn .attr .space_attr import NnMemorySpaceAttr
from kernel_gen .dialect .nn .type .memory_type import NnMemoryType
from xdsl .dialects .builtin import Float16Type ,Float32Type ,IntegerType ,i1 ,i32
from xdsl .ir import Attribute ,Operation ,SSAValue
from xdsl .irdl import IRDLOperation ,attr_def ,irdl_op_definition ,operand_def ,result_def

from kernel_gen .core .error import ERROR_ACTION ,ERROR_ACTUAL ,ERROR_TEMPLATE ,ErrorKind ,ErrorModule ,kernel_code_error
from kernel_gen .core .contracts import raise_verify_error as core_raise_verify_error ,build_contiguous_stride as core_build_contiguous_stride ,verify_i64_attr as core_verify_i64_attr ,verify_memory_type as core_verify_memory_type

from xdsl .ir import Attribute ,ParametrizedAttribute ,SSAValue


# Localized helpers from retired package-internal modules.

_ERROR_SCENE ="dialect.nn verifier"

class _NnBinaryHelpers :
    """当前文件内本地 helper 容器。

    功能说明:
    - 承接退场 common.py 后的文件内 helper，避免形成模块级事实公开函数。

    使用示例:
    - _NnBinaryHelpers.helper(...)
    """

    @staticmethod
    def verify_memory_type (value :Attribute ,field_name :str )->"NnMemoryType":
        """校验并返回 memory type。

        功能说明:
        - 确认 `value` 是公开 `NnMemoryType`，并执行通用 memory type 校验。
        - `field_name` 用于在稳定错误文本中定位被校验字段。

        使用示例:
        - input_type = verify_memory_type(op.input.type, "input")
        """

        return core_verify_memory_type (value ,field_name ,scene =_ERROR_SCENE )

    @staticmethod
    def is_symbol_int_type (attr :Attribute )->bool :
        """判断 attribute 是否为 symbol.int。


        功能说明:
        - 仅通过 `name` 字段判断是否为 `symbol.int` 类型，避免 nn/symbol 循环依赖。

        使用示例:
        - is_symbol_int_type(SymbolValueType.from_expr("K"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        return isinstance (attr ,ParametrizedAttribute )and attr .name =="symbol.int"




class _NnBinaryRules :
    """当前文件内的局部 verifier 规则容器。

    功能说明:
    - 合并本文件重复使用的局部规则，避免多个 private helper 互相调用。
    - 该容器不导出，不作为跨文件公开 API。

    使用示例:
    - _NN_BINARY.verify_binary_memory_op(...)
    """

    @staticmethod
    def verify_binary_memory_op (op :"_BaseNnBinaryOp",compare_result :bool )->None :
        """统一校验 nn 二元 op。


        功能说明:
        - 检查 operand/result 类型、shape/stride、element_type 与 space 一致性。

        使用示例:
        - _NN_BINARY.verify_binary_memory_op(op, compare_result=False)

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        lhs_type =_NnBinaryHelpers .verify_memory_type (op .lhs .type ,"lhs")
        rhs_type =_NnBinaryHelpers .verify_memory_type (op .rhs .type ,"rhs")
        result_type =_NnBinaryHelpers .verify_memory_type (op .result .type ,"result")

        op .space .verify ()
        if lhs_type .space .space .data !=rhs_type .space .space .data :
            core_raise_verify_error (_ERROR_SCENE ,"nn op operands must use the same space")
        if lhs_type .space .space .data !=op .space .space .data :
            core_raise_verify_error (_ERROR_SCENE ,"nn op attribute space must match operand space")
        if result_type .space .space .data !=op .space .space .data :
            core_raise_verify_error (_ERROR_SCENE ,"nn op attribute space must match result space")

        if lhs_type .shape !=rhs_type .shape or lhs_type .shape !=result_type .shape :
            core_raise_verify_error (_ERROR_SCENE ,"nn op shape must match across operands and result")
        if lhs_type .stride !=rhs_type .stride or lhs_type .stride !=result_type .stride :
            core_raise_verify_error (_ERROR_SCENE ,"nn op stride must match across operands and result")
        if lhs_type .element_type !=rhs_type .element_type :
            core_raise_verify_error (_ERROR_SCENE ,"nn op operand element_type must match")

        if compare_result :
            if result_type .element_type !=i1 :
                core_raise_verify_error (_ERROR_SCENE ,"nn compare result element_type must be i1")
        elif result_type .element_type !=lhs_type .element_type :
            core_raise_verify_error (_ERROR_SCENE ,"nn arithmetic result element_type must match operand element_type")

    _ADD_DTYPE_ORDER ={"i32":0 ,"f16":1 ,"f32":2 }

    _ADD_DTYPE_ATTR ={"i32":i32 ,"f16":Float16Type (),"f32":Float32Type ()}

    @staticmethod
    def resolve_add_dtype_key (attr :Attribute )->str |None :
        """解析 nn.add 标量/element_type 的 promotion key。


        功能说明:
        - 支持 i32/f16/f32 三种类型；
        - `!symbol.int` 视作 i32 参与 promotion。

        使用示例:
        - _NN_BINARY.resolve_add_dtype_key(i32)
        - _NN_BINARY.resolve_add_dtype_key(SymbolValueType.from_expr("K"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        if _NnBinaryHelpers .is_symbol_int_type (attr ):
            return "i32"
        if isinstance (attr ,IntegerType )and attr .width .data ==32 :
            return "i32"
        if isinstance (attr ,Float16Type ):
            return "f16"
        if isinstance (attr ,Float32Type ):
            return "f32"
        return None

    @staticmethod
    def promote_add_dtype (lhs_type :Attribute ,rhs_type :Attribute )->Attribute |None :
        """计算 nn.add 的 dtype promotion 结果类型。


        功能说明:
        - 按 i32 < f16 < f32 顺序进行 promotion。

        使用示例:
        - _NN_BINARY.promote_add_dtype(i32, Float16Type())

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        lhs_key =_NN_BINARY .resolve_add_dtype_key (lhs_type )
        rhs_key =_NN_BINARY .resolve_add_dtype_key (rhs_type )
        if lhs_key is None or rhs_key is None :
            return None
        promoted_key =lhs_key if _ADD_DTYPE_ORDER [lhs_key ]>=_ADD_DTYPE_ORDER [rhs_key ]else rhs_key
        return _ADD_DTYPE_ATTR [promoted_key ]

_NN_BINARY =_NnBinaryRules ()
_ADD_DTYPE_ORDER =_NnBinaryRules ._ADD_DTYPE_ORDER
_ADD_DTYPE_ATTR =_NnBinaryRules ._ADD_DTYPE_ATTR

def _verify_add_op (op :"NnAddOp")->None :
    """校验 nn.add，支持 memory + scalar/symbol。


    功能说明:
    - 允许 `nn.memory + scalar`、`scalar + nn.memory`、`nn.memory + !symbol.int`；
    - 至少一侧必须为 `nn.memory`，结果的 shape/stride/space 继承 memory operand；
    - scalar dtype promotion 固定为 i32 < f16 < f32。

    使用示例:
    - _verify_add_op(op)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    lhs_value =SSAValue .get (op .lhs )
    rhs_value =SSAValue .get (op .rhs )
    lhs_type =lhs_value .type
    rhs_type =rhs_value .type
    result_type =_NnBinaryHelpers .verify_memory_type (op .result .type ,"result")

    lhs_is_memory =isinstance (lhs_type ,NnMemoryType )
    rhs_is_memory =isinstance (rhs_type ,NnMemoryType )
    if not lhs_is_memory and not rhs_is_memory :
        core_raise_verify_error (_ERROR_SCENE ,"nn.add requires at least one nn.memory operand")

    op .space .verify ()
    if lhs_is_memory and rhs_is_memory :
        _NN_BINARY .verify_binary_memory_op (op ,compare_result =False )
        return

    memory_type =_NnBinaryHelpers .verify_memory_type (lhs_type if lhs_is_memory else rhs_type ,"memory operand")
    if memory_type .space .space .data !=op .space .space .data :
        core_raise_verify_error (_ERROR_SCENE ,"nn.add attribute space must match memory operand space")
    if result_type .space .space .data !=memory_type .space .space .data :
        core_raise_verify_error (_ERROR_SCENE ,"nn.add result space must match memory operand")

    if result_type .shape !=memory_type .shape :
        core_raise_verify_error (_ERROR_SCENE ,"nn.add result shape must match memory operand")
    if result_type .stride !=memory_type .stride :
        core_raise_verify_error (_ERROR_SCENE ,"nn.add result stride must match memory operand")

    scalar_type =rhs_type if lhs_is_memory else lhs_type
    promoted_type =_NN_BINARY .promote_add_dtype (memory_type .element_type ,scalar_type )
    if promoted_type is None :
        core_raise_verify_error (_ERROR_SCENE ,"nn.add scalar element_type must be i32/f16/f32 or symbol.int")
    if result_type .element_type !=promoted_type :
        core_raise_verify_error (_ERROR_SCENE ,"nn.add result element_type must match promoted element_type")

def _verify_mixed_scalar_binary_op (op :"_BaseNnBinaryOp",op_name :str )->None :
    """校验支持 mixed memory+scalar/symbol 的 nn 二元算术 op。


    功能说明:
    - 允许 `nn.memory + scalar`、`scalar + nn.memory`、`nn.memory + !symbol.int`。
    - 结果的 shape/stride/space 继承 memory operand，dtype 按统一 promotion 规则决议。

    使用示例:
    - _verify_mixed_scalar_binary_op(op, "nn.sub")

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    lhs_value =SSAValue .get (op .lhs )
    rhs_value =SSAValue .get (op .rhs )
    lhs_type =lhs_value .type
    rhs_type =rhs_value .type
    result_type =_NnBinaryHelpers .verify_memory_type (op .result .type ,"result")

    lhs_is_memory =isinstance (lhs_type ,NnMemoryType )
    rhs_is_memory =isinstance (rhs_type ,NnMemoryType )
    if not lhs_is_memory and not rhs_is_memory :
        core_raise_verify_error (_ERROR_SCENE ,f"{op_name } requires at least one nn.memory operand")

    op .space .verify ()
    if lhs_is_memory and rhs_is_memory :
        _NN_BINARY .verify_binary_memory_op (op ,compare_result =False )
        return

    memory_type =_NnBinaryHelpers .verify_memory_type (lhs_type if lhs_is_memory else rhs_type ,"memory operand")
    if memory_type .space .space .data !=op .space .space .data :
        core_raise_verify_error (_ERROR_SCENE ,f"{op_name } attribute space must match memory operand space")
    if result_type .space .space .data !=memory_type .space .space .data :
        core_raise_verify_error (_ERROR_SCENE ,f"{op_name } result space must match memory operand")

    if result_type .shape !=memory_type .shape :
        core_raise_verify_error (_ERROR_SCENE ,f"{op_name } result shape must match memory operand")
    if result_type .stride !=memory_type .stride :
        core_raise_verify_error (_ERROR_SCENE ,f"{op_name } result stride must match memory operand")

    scalar_type =rhs_type if lhs_is_memory else lhs_type
    promoted_type =_NN_BINARY .promote_add_dtype (memory_type .element_type ,scalar_type )
    if promoted_type is None :
        core_raise_verify_error (_ERROR_SCENE ,f"{op_name } scalar element_type must be i32/f16/f32 or symbol.int")
    if result_type .element_type !=promoted_type :
        core_raise_verify_error (_ERROR_SCENE ,f"{op_name } result element_type must match promoted element_type")

class _BaseNnBinaryOp (IRDLOperation ):
    """NN 二元 op 基类。"""

    lhs =operand_def (NnMemoryType )
    rhs =operand_def (NnMemoryType )
    result =result_def (NnMemoryType )
    space =attr_def (NnMemorySpaceAttr )

    def __init__ (
    self ,
    lhs :SSAValue |Operation ,
    rhs :SSAValue |Operation ,
    result_type :NnMemoryType ,
    space :NnMemorySpaceAttr ,
    )->None :
        """初始化二元 op。

        功能说明:
        - 绑定 lhs/rhs operands、结果 memory type 和执行 space 属性。
        - 为 memory binary、mixed scalar binary 和 compare op 保持统一构造入口。

        使用示例:
        - NnAddOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
        """

        super ().__init__ (
        operands =[lhs ,rhs ],
        result_types =[result_type ],
        attributes ={"space":space },
        )

@irdl_op_definition
class NnAddOp (_BaseNnBinaryOp ):
    """nn.add。"""

    name ="nn.add"

    lhs =operand_def (Attribute )
    rhs =operand_def (Attribute )

    def verify_ (self )->None :
        """校验 nn.add 的 memory/scalar 组合。


        功能说明:
        - 支持 memory+scalar/symbol 的 verifier 校验。

        使用示例:
        - NnAddOp(lhs, rhs, result_type, space).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        _verify_add_op (self )

@irdl_op_definition
class NnSubOp (_BaseNnBinaryOp ):
    """nn.sub。"""

    name ="nn.sub"
    lhs =operand_def (Attribute )
    rhs =operand_def (Attribute )

    def verify_ (self )->None :
        """校验 nn.sub 的 memory/scalar 组合。

        功能说明:
        - 支持 memory-memory 与符合公开合同的 memory/scalar 组合。
        - 校验结果 memory type、space 和 element type 推导。

        使用示例:
        - NnSubOp(lhs, rhs, result_type, space).verify_()
        """
        _verify_mixed_scalar_binary_op (self ,"nn.sub")

@irdl_op_definition
class NnMulOp (_BaseNnBinaryOp ):
    """nn.mul。"""

    name ="nn.mul"
    lhs =operand_def (Attribute )
    rhs =operand_def (Attribute )

    def verify_ (self )->None :
        """校验 nn.mul 的 memory/scalar 组合。

        功能说明:
        - 支持 memory-memory 与符合公开合同的 memory/scalar 组合。
        - 校验结果 memory type、space 和 element type 推导。

        使用示例:
        - NnMulOp(lhs, rhs, result_type, space).verify_()
        """
        _verify_mixed_scalar_binary_op (self ,"nn.mul")

@irdl_op_definition
class NnDivOp (_BaseNnBinaryOp ):
    """nn.div。


    功能说明:
    - 定义 nn.div 方言 op 与 verifier 约束。
    - 仅支持 memory + memory 形式，不支持隐式 broadcast。

    使用示例:
    - NnDivOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    name ="nn.div"

    def verify_ (self )->None :
        """校验 nn.div 的 verifier 合同。


        功能说明:
        - 复用统一二元 memory verifier。

        使用示例:
        - NnDivOp(lhs, rhs, result_type, space).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        _NN_BINARY .verify_binary_memory_op (self ,compare_result =False )

@irdl_op_definition
class NnTrueDivOp (_BaseNnBinaryOp ):
    """nn.truediv。"""

    name ="nn.truediv"
    lhs =operand_def (Attribute )
    rhs =operand_def (Attribute )

    def verify_ (self )->None :
        """校验 nn.truediv 的 memory/scalar 组合。

        功能说明:
        - 支持 memory-memory 与符合公开合同的 memory/scalar 组合。
        - 校验 result element type 与 truediv 公开推导规则一致。

        使用示例:
        - NnTrueDivOp(lhs, rhs, result_type, space).verify_()
        """
        _verify_mixed_scalar_binary_op (self ,"nn.truediv")

@irdl_op_definition
class NnFloorDivOp (_BaseNnBinaryOp ):
    """nn.floordiv。"""

    name ="nn.floordiv"

    lhs =operand_def (Attribute )
    rhs =operand_def (Attribute )

    def verify_ (self )->None :
        """校验 nn.floordiv 的 memory/scalar 组合。

        功能说明:
        - 支持 memory-memory 与符合公开合同的 memory/scalar 组合。
        - 校验 result element type 与 floordiv 公开推导规则一致。

        使用示例:
        - NnFloorDivOp(lhs, rhs, result_type, space).verify_()
        """
        _verify_mixed_scalar_binary_op (self ,"nn.floordiv")

@irdl_op_definition
class NnEqOp (_BaseNnBinaryOp ):
    """nn.eq。"""

    name ="nn.eq"

    def verify_ (self )->None :
        """校验 nn.eq 的 compare memory 合同。

        功能说明:
        - 校验 lhs/rhs 为同形状、同 space 的 nn memory。
        - 校验 result 使用 compare result 合同而不是普通数值 element type。

        使用示例:
        - NnEqOp(lhs, rhs, result_type, space).verify_()
        """
        _NN_BINARY .verify_binary_memory_op (self ,compare_result =True )

@irdl_op_definition
class NnNeOp (_BaseNnBinaryOp ):
    """nn.ne。"""

    name ="nn.ne"

    def verify_ (self )->None :
        """校验 nn.ne 的 compare memory 合同。

        功能说明:
        - 校验 lhs/rhs 为同形状、同 space 的 nn memory。
        - 校验 result 使用 compare result 合同而不是普通数值 element type。

        使用示例:
        - NnNeOp(lhs, rhs, result_type, space).verify_()
        """
        _NN_BINARY .verify_binary_memory_op (self ,compare_result =True )

@irdl_op_definition
class NnLtOp (_BaseNnBinaryOp ):
    """nn.lt。"""

    name ="nn.lt"

    def verify_ (self )->None :
        """校验 nn.lt 的 compare memory 合同。

        功能说明:
        - 校验 lhs/rhs 为同形状、同 space 的 nn memory。
        - 校验 result 使用 compare result 合同而不是普通数值 element type。

        使用示例:
        - NnLtOp(lhs, rhs, result_type, space).verify_()
        """
        _NN_BINARY .verify_binary_memory_op (self ,compare_result =True )

@irdl_op_definition
class NnLeOp (_BaseNnBinaryOp ):
    """nn.le。"""

    name ="nn.le"

    def verify_ (self )->None :
        """校验 nn.le 的 compare memory 合同。

        功能说明:
        - 校验 lhs/rhs 为同形状、同 space 的 nn memory。
        - 校验 result 使用 compare result 合同而不是普通数值 element type。

        使用示例:
        - NnLeOp(lhs, rhs, result_type, space).verify_()
        """
        _NN_BINARY .verify_binary_memory_op (self ,compare_result =True )

@irdl_op_definition
class NnGtOp (_BaseNnBinaryOp ):
    """nn.gt。"""

    name ="nn.gt"

    def verify_ (self )->None :
        """校验 nn.gt 的 compare memory 合同。

        功能说明:
        - 校验 lhs/rhs 为同形状、同 space 的 nn memory。
        - 校验 result 使用 compare result 合同而不是普通数值 element type。

        使用示例:
        - NnGtOp(lhs, rhs, result_type, space).verify_()
        """
        _NN_BINARY .verify_binary_memory_op (self ,compare_result =True )

@irdl_op_definition
class NnGeOp (_BaseNnBinaryOp ):
    """nn.ge。"""

    name ="nn.ge"

    def verify_ (self )->None :
        """校验 nn.ge 的 compare memory 合同。

        功能说明:
        - 校验 lhs/rhs 为同形状、同 space 的 nn memory。
        - 校验 result 使用 compare result 合同而不是普通数值 element type。

        使用示例:
        - NnGeOp(lhs, rhs, result_type, space).verify_()
        """
        _NN_BINARY .verify_binary_memory_op (self ,compare_result =True )

__all__ =["NnAddOp","NnSubOp","NnMulOp","NnDivOp","NnTrueDivOp","NnFloorDivOp","NnEqOp","NnNeOp","NnLtOp","NnLeOp","NnGtOp","NnGeOp"]
