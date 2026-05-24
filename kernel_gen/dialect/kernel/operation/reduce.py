"""kernel reduce operations.

功能说明:
- 定义 kernel.reduce 与 kernel.reduce_min op。

API 列表:
- `class KernelReduceOp(out: SSAValue | Operation, input_value: SSAValue | Operation, *, kind: str | StringAttr, axis: int | IntegerAttr | IntAttr, keepdim: bool | int | IntegerAttr | IntAttr, space: NnMemorySpaceAttr)`
- `class KernelReduceMinOp(out: SSAValue | Operation, input_value: SSAValue | Operation, axis: int | IntegerAttr | IntAttr, keepdim: bool | int | IntegerAttr | IntAttr, space: NnMemorySpaceAttr)`

使用示例:
- `from kernel_gen.dialect.kernel.operation import ...`

关联文件:
- spec: spec/dialect/kernel.md
- test: test/dialect/kernel/
- 功能实现: kernel_gen/dialect/kernel/operation/reduce.py
"""

from __future__ import annotations

from collections .abc import Iterable ,Sequence

from kernel_gen .core .contracts import dims_equal ,build_contiguous_stride ,verify_i64_attr_range ,verify_memory_type
from kernel_gen .core .error import ERROR_ACTION ,ERROR_ACTUAL ,ERROR_TEMPLATE ,ErrorKind ,ErrorModule ,kernel_code_error
from xdsl .dialects .arith import ConstantOp
from xdsl .dialects .builtin import (
BFloat16Type ,
Float16Type ,
Float32Type ,
Float64Type ,
IntAttr ,
IntegerAttr ,
IntegerType ,
StringAttr ,
i1 ,
)
from xdsl .ir import Attribute ,Dialect ,Operation ,SSAValue
from xdsl .irdl import IRDLOperation ,attr_def ,irdl_op_definition ,operand_def ,traits_def
from xdsl .traits import EffectInstance ,MemoryEffect ,MemoryEffectKind

from kernel_gen .dialect .nn import NnMemorySpaceAttr ,NnMemoryType
from kernel_gen .dialect .symbol import SymbolExprAttr ,SymbolValueType

# Localized helpers from retired package-internal modules.

_ERROR_SCENE ="dialect.kernel verifier"

class _KernelUnaryMemoryEffect (MemoryEffect ):
    """一输入一输出 kernel op 的 out 写与 input 读 effect trait。"""

    @classmethod
    def get_effects (cls ,op :Operation )->set [EffectInstance ]:
        """返回一输入一输出 kernel op 的 MemoryEffect 集合。


        功能说明:
        - 使用 IRDL 命名字段绑定 effect value，避免 `KernelExpOp(input_value, out, ...)`
          等构造函数参数顺序与 op 字段顺序不一致时读写误绑。
        - `out` 产生 WRITE effect，`input` 产生 READ effect。

        使用示例:
        - effects = _KernelUnaryMemoryEffect.get_effects(op)

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        return {
        EffectInstance (MemoryEffectKind .WRITE ,SSAValue .get (op .out )),# type: ignore[attr-defined]
        EffectInstance (MemoryEffectKind .READ ,SSAValue .get (op .input )),# type: ignore[attr-defined]
        }

def _normalize_kind_attr (
kind :str |StringAttr ,
*,
op_name :str ,
field_name :str ,
allowed :set [str ],
)->StringAttr :
    """规范化并校验 kind attribute。


    功能说明:
    - 支持 str 与 StringAttr 作为 kind 输入。
    - 校验 kind 是否属于允许集合。

    使用示例:
    - kind_attr = _normalize_kind_attr("add", op_name="kernel.binary_elewise", field_name="kind", allowed=_BINARY_ELEWISE_KINDS)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    if isinstance (kind ,StringAttr ):
        kind_attr =kind
    elif isinstance (kind ,str ):
        kind_attr =StringAttr (kind )
    else :
        raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,
        ERROR_TEMPLATE .format (
        scene =_ERROR_SCENE ,
        expected =f"{op_name } {field_name } must be string",
        actual =ERROR_ACTUAL ,
        action =ERROR_ACTION ,
        )
        )
    if kind_attr .data not in allowed :
        allowed_text =", ".join (sorted (allowed ))
        raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,
        ERROR_TEMPLATE .format (
        scene =_ERROR_SCENE ,
        expected =f"{op_name } {field_name } must be one of [{allowed_text }]",
        actual =ERROR_ACTUAL ,
        action =ERROR_ACTION ,
        )
        )
    return kind_attr

def _normalize_i64_attr (value :int |IntegerAttr |IntAttr ,field_name :str )->IntegerAttr :
    """将数值规整为 i64 IntegerAttr。


    功能说明:
    - 支持传入 int/IntAttr/IntegerAttr，统一为 i64 IntegerAttr。
    - 用于 axis、tile 因子等整型属性构造入口。

    使用示例:
    - _normalize_i64_attr(1, "axis")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    if isinstance (value ,IntegerAttr ):
        attr =value
    elif isinstance (value ,IntAttr ):
        attr =IntegerAttr (value .data ,IntegerType (64 ))
    else :
        attr =IntegerAttr (int (value ),IntegerType (64 ))
    return attr

def _verify_i64_attr_range (attr :IntegerAttr ,field_name :str ,*,min_value :int ,max_value :int )->int :
    """校验 i64 属性并返回整数值。


    功能说明:
    - 校验属性类型为 i64。
    - 校验数值落在指定闭区间。

    使用示例:
    - axis = _verify_i64_attr_range(attr, "axis", min_value=-2, max_value=1)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    return verify_i64_attr_range (
    attr ,
    field_name ,
    min_value =min_value ,
    max_value =max_value ,
    scene =_ERROR_SCENE ,
    )

def _normalize_bool_attr (value :bool |int |IntegerAttr |IntAttr ,field_name :str )->IntegerAttr :
    """将布尔语义规整为 i1 IntegerAttr。


    功能说明:
    - 支持 bool/int/IntAttr/IntegerAttr 输入，统一为 i1 IntegerAttr。
    - 用于 kernel.reduce_min keepdim 等属性构造入口。

    使用示例:
    - _normalize_bool_attr(True, "keepdim")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    if isinstance (value ,IntegerAttr ):
        return value
    if isinstance (value ,IntAttr ):
        value =value .data
    if isinstance (value ,bool ):
        value =1 if value else 0
    return IntegerAttr (int (value ),IntegerType (1 ))

def _verify_bool_attr (attr :IntegerAttr ,field_name :str )->bool :
    """校验 i1 bool attr 并返回布尔值。


    功能说明:
    - 要求类型为 i1 IntegerAttr。
    - 要求取值为 0/1，接受 i1 语义下的 -1(true)。

    使用示例:
    - keepdim = _verify_bool_attr(op.keepdim, "keepdim")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    if not isinstance (attr .type ,IntegerType ):
        raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,
        ERROR_TEMPLATE .format (
        scene =_ERROR_SCENE ,
        expected =f"{field_name } must be i1",
        actual =ERROR_ACTUAL ,
        action =ERROR_ACTION ,
        )
        )
    width_attr =attr .type .width
    width_value =width_attr .data if isinstance (width_attr ,IntAttr )else width_attr
    if width_value !=1 :
        raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,
        ERROR_TEMPLATE .format (
        scene =_ERROR_SCENE ,
        expected =f"{field_name } must be i1",
        actual =ERROR_ACTUAL ,
        action =ERROR_ACTION ,
        )
        )
    value =attr .value .data
    if value ==-1 :
        return True
    if value not in (0 ,1 ):
        raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,
        ERROR_TEMPLATE .format (
        scene =_ERROR_SCENE ,
        expected =f"{field_name } must be bool",
        actual =ERROR_ACTUAL ,
        action =ERROR_ACTION ,
        )
        )
    return value ==1

class _KernelReduceHelpers :
    """当前文件内本地 helper 容器。

    功能说明:
    - 承接退场 common.py 后的文件内 helper，避免形成模块级事实公开函数。

    使用示例:
    - _KernelReduceHelpers.helper(...)
    """

    @staticmethod
    def dims_equal (lhs :Attribute ,rhs :Attribute )->bool :
        """判断两个维度是否语义一致。


        功能说明:
        - 对 `SymbolExprAttr` 比较 canonical 文本。
        - 其它 attribute 统一视为不一致，避免旧 bare layout 条目继续参与 verifier。

        使用示例:
        - dims_equal(SymbolExprAttr.from_expr("1"), SymbolExprAttr.from_expr("1"))

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        if isinstance (lhs ,SymbolExprAttr )and isinstance (rhs ,SymbolExprAttr ):
            return lhs .expr .data ==rhs .expr .data
        return False


def _build_reduce_result_shape (
input_dims :Sequence [Attribute ],
axis :int ,
keepdim :bool ,
)->list [Attribute ]:
    """构造 reduce 结果的 shape 维度列表。


    功能说明:
    - keepdim=true 时将归约轴替换为 1。
    - keepdim=false 时移除归约轴；若结果 rank 为 0 则规范为 [1]。

    使用示例:
    - _build_reduce_result_shape([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("3")], axis=0, keepdim=False)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    if keepdim :
        return [SymbolExprAttr .from_expr ("1")if index ==axis else dim for index ,dim in enumerate (input_dims )]

    result_dims =[dim for index ,dim in enumerate (input_dims )if index !=axis ]
    if not result_dims :
        return [SymbolExprAttr .from_expr ("1")]
    return result_dims

def _verify_reduce_result_shape (
result_type :NnMemoryType ,
expected_shape :Sequence [Attribute ],
op_name :str ,
)->None :
    """校验 reduce 结果 shape 合同。


    功能说明:
    - 比较结果 shape 与期望 shape 的长度与逐维一致性。

    使用示例:
    - _verify_reduce_result_shape(out_type, expected_shape, "kernel.reduce_min")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    if len (result_type .shape .data )!=len (expected_shape ):
        raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,
        ERROR_TEMPLATE .format (
        scene =_ERROR_SCENE ,
        expected =f"{op_name } out shape must match reduce contract",
        actual =ERROR_ACTUAL ,
        action =ERROR_ACTION ,
        )
        )

    for expected_dim ,actual_dim in zip (expected_shape ,result_type .shape .data ,strict =True ):
        if not _KernelReduceHelpers .dims_equal (expected_dim ,actual_dim ):
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,
            ERROR_TEMPLATE .format (
            scene =_ERROR_SCENE ,
            expected =f"{op_name } out shape must match reduce contract",
            actual =ERROR_ACTUAL ,
            action =ERROR_ACTION ,
            )
            )



_KERNEL_ERROR_SCENE ="dialect.kernel verifier"
_REDUCE_KINDS ={"sum","min","max"}

@irdl_op_definition
class KernelReduceOp (IRDLOperation ):
    """kernel.reduce。


    功能说明:
    - 定义带 kind 的 reduce op 与 verifier 约束。

    使用示例:
    - KernelReduceOp(inp, out, kind="sum", axis=1, keepdim=False, space=NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    name ="kernel.reduce"
    traits =traits_def (_KernelUnaryMemoryEffect ())

    out =operand_def (NnMemoryType )
    input =operand_def (NnMemoryType )
    axis =attr_def (IntegerAttr )
    keepdim =attr_def (IntegerAttr )
    kind =attr_def (StringAttr )
    space =attr_def (NnMemorySpaceAttr )

    def __init__ (
    self ,
    out :SSAValue |Operation ,
    input_value :SSAValue |Operation ,
    *,
    kind :str |StringAttr ,
    axis :int |IntegerAttr |IntAttr ,
    keepdim :bool |int |IntegerAttr |IntAttr ,
    space :NnMemorySpaceAttr ,
    )->None :
        """初始化 kernel.reduce op。


        功能说明:
        - 绑定输入/输出 operand。
        - axis 规整为 i64 IntegerAttr，keepdim 规整为 i1。

        使用示例:
        - KernelReduceOp(inp, out, kind="sum", axis=1, keepdim=False, space=NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        axis_attr =_normalize_i64_attr (axis ,"axis")
        keepdim_attr =_normalize_bool_attr (keepdim ,"keepdim")
        kind_attr =_normalize_kind_attr (
        kind ,op_name =self .name ,field_name ="kind",allowed =_REDUCE_KINDS
        )
        super ().__init__ (
        operands =[out ,input_value ],
        attributes ={
        "axis":axis_attr ,
        "keepdim":keepdim_attr ,
        "kind":kind_attr ,
        "space":space ,
        },
        )

    def verify_ (self )->None :
        """校验 kernel.reduce 的 verifier 合同。


        功能说明:
        - 校验 kind/axis/keepdim/out.shape 约束。
        - 校验 element_type 与 space 一致性。

        使用示例:
        - KernelReduceOp(inp, out, kind="sum", axis=1, keepdim=False, space=space).verify_()

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        input_type =verify_memory_type (self .input .type ,"input",scene =_ERROR_SCENE )
        out_type =verify_memory_type (self .out .type ,"out",scene =_ERROR_SCENE )
        _normalize_kind_attr (
        self .kind ,op_name =self .name ,field_name ="kind",allowed =_REDUCE_KINDS
        )
        axis_value =_verify_i64_attr_range (
        self .axis ,"axis",min_value =0 ,max_value =len (input_type .shape .data )-1
        )
        keepdim_value =_verify_bool_attr (self .keepdim ,"keepdim")
        if input_type .element_type !=out_type .element_type :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,
            ERROR_TEMPLATE .format (
            scene =_KERNEL_ERROR_SCENE ,
            expected ="kernel.reduce element_type must match across operands",
            actual =ERROR_ACTUAL ,
            action =ERROR_ACTION ,
            )
            )
        self .space .verify ()
        if input_type .space .space .data !=out_type .space .space .data :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,
            ERROR_TEMPLATE .format (
            scene =_KERNEL_ERROR_SCENE ,
            expected ="kernel.reduce out space must match input",
            actual =ERROR_ACTUAL ,
            action =ERROR_ACTION ,
            )
            )
        if input_type .space .space .data !=self .space .space .data :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,
            ERROR_TEMPLATE .format (
            scene =_KERNEL_ERROR_SCENE ,
            expected ="kernel.reduce attribute space must match input",
            actual =ERROR_ACTUAL ,
            action =ERROR_ACTION ,
            )
            )
        expected_shape =_build_reduce_result_shape (
        list (input_type .shape .data ),axis_value ,keepdim_value
        )
        _verify_reduce_result_shape (out_type ,expected_shape ,"kernel.reduce")


@irdl_op_definition
class KernelReduceMinOp (IRDLOperation ):
    """kernel.reduce_min。


    功能说明:
    - 定义 kernel.reduce_min op 与 verifier 约束。

    使用示例:
    - KernelReduceMinOp(out, inp, axis=1, keepdim=False, space=NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    name ="kernel.reduce_min"
    traits =traits_def (_KernelUnaryMemoryEffect ())

    out =operand_def (NnMemoryType )
    input =operand_def (NnMemoryType )
    axis =attr_def (IntegerAttr )
    keepdim =attr_def (IntegerAttr )
    space =attr_def (NnMemorySpaceAttr )

    def __init__ (
    self ,
    out :SSAValue |Operation ,
    input_value :SSAValue |Operation ,
    axis :int |IntegerAttr |IntAttr ,
    keepdim :bool |int |IntegerAttr |IntAttr ,
    space :NnMemorySpaceAttr ,
    )->None :
        """初始化 reduce_min op。


        功能说明:
        - 绑定输入/输出 operand。
        - axis 规整为 i64 IntegerAttr，keepdim 规整为 i1。

        使用示例:
        - KernelReduceMinOp(out, inp, axis=1, keepdim=False, space=NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        axis_attr =_normalize_i64_attr (axis ,"axis")
        keepdim_attr =_normalize_bool_attr (keepdim ,"keepdim")
        super ().__init__ (
        operands =[out ,input_value ],
        attributes ={"axis":axis_attr ,"keepdim":keepdim_attr ,"space":space },
        )

    def verify_ (self )->None :
        """校验 kernel.reduce_min 的 verifier 合同。


        功能说明:
        - 校验 axis/keepdim/out.shape 约束。
        - 校验 element_type 与 space 一致性。

        使用示例:
        - KernelReduceMinOp(out, inp, axis=1, keepdim=False, space=NnMemorySpaceAttr.from_name("global")).verify_()

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        input_type =verify_memory_type (self .input .type ,"input",scene =_ERROR_SCENE )
        out_type =verify_memory_type (self .out .type ,"out",scene =_ERROR_SCENE )
        axis_value =_verify_i64_attr_range (
        self .axis ,"axis",min_value =0 ,max_value =len (input_type .shape .data )-1
        )
        keepdim_value =_verify_bool_attr (self .keepdim ,"keepdim")
        if input_type .element_type !=out_type .element_type :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,
            ERROR_TEMPLATE .format (
            scene =_KERNEL_ERROR_SCENE ,
            expected ="kernel.reduce_min element_type must match across operands",
            actual =ERROR_ACTUAL ,
            action =ERROR_ACTION ,
            )
            )
        self .space .verify ()
        if input_type .space .space .data !=out_type .space .space .data :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,
            ERROR_TEMPLATE .format (
            scene =_KERNEL_ERROR_SCENE ,
            expected ="kernel.reduce_min out space must match input",
            actual =ERROR_ACTUAL ,
            action =ERROR_ACTION ,
            )
            )
        if input_type .space .space .data !=self .space .space .data :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,
            ERROR_TEMPLATE .format (
            scene =_KERNEL_ERROR_SCENE ,
            expected ="kernel.reduce_min attribute space must match input",
            actual =ERROR_ACTUAL ,
            action =ERROR_ACTION ,
            )
            )
        expected_shape =_build_reduce_result_shape (
        list (input_type .shape .data ),axis_value ,keepdim_value
        )
        _verify_reduce_result_shape (out_type ,expected_shape ,"kernel.reduce_min")

__all__ =[
"KernelReduceOp",
"KernelReduceMinOp",
]
