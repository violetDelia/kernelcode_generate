"""DMA transfer operation definitions.

功能说明:
- 定义整块搬运、广播、转置和元素类型转换 op。

API 列表:
- `class DmaCopyOp(target: SSAValue | Operation, source: SSAValue | Operation)`
- `class DmaBroadcastOp(target: SSAValue | Operation, source: SSAValue | Operation)`
- `class DmaTransposeOp(target: SSAValue | Operation, source: SSAValue | Operation, perm: Sequence[int] | ArrayAttr)`
- `class DmaCastOp(target: SSAValue | Operation, source: SSAValue | Operation)`

使用示例:
- `DmaCopyOp(target, source)`

关联文件:
- spec: spec/dialect/dma.md
- test: test/dialect/dma/
- 功能实现: kernel_gen/dialect/dma/operation/transfer.py
"""

from __future__ import annotations

from kernel_gen .core .error import ErrorKind ,ErrorModule ,kernel_code_error

from collections .abc import Sequence

from xdsl .dialects .builtin import ArrayAttr ,IntAttr ,IntegerType
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

from ..effect import DmaBroadcastMemoryEffect ,DmaTargetSourceEffect

import re

import sympy as sp

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

class _DmaTransferHelpers :
    """当前文件内本地 helper 容器。

    功能说明:
    - 承接退场 common.py 后的文件内 helper，避免形成模块级事实公开函数。

    使用示例:
    - _DmaTransferHelpers.helper(...)
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
    def symbol_expr_attr_from_expr (expr :str )->SymbolExprAttr :
        """构造公开 SymbolExprAttr。

        功能说明:
        - 统一 dma dialect 内部 shape/stride 推导的结构化表达构造。

        使用示例:
        - symbol_expr_attr_from_expr("N")

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        return SymbolExprAttr .from_expr (expr )

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

        return _DmaTransferHelpers .static_int_from_expr_text (_DmaTransferHelpers .dim_expr_text (dim ))

    @staticmethod
    def parse_symbolic_expr_text (text :str )->sp .Basic |None :
        """解析符号整数表达式文本。


        功能说明:
        - 将整数、符号乘法、`floor(...)` 与 `min(...)` 文本解析为 sympy 表达式。
        - 无法解析或未知动态维度时返回 `None`，由调用方决定是否跳过静态比较。

        使用示例:
        - parse_symbolic_expr_text("TILE_H*4")

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        stripped =text .strip ().replace (" floordiv "," // ")
        if stripped =="?":
            return None
        names =set (re .findall (r"[A-Za-z_][A-Za-z0-9_]*",stripped ))
        function_names ={"floor","min"}
        local_dict ={name :sp .Symbol (name ,integer =True ,real =True )for name in names if name not in function_names }
        local_dict .update ({"floor":sp .floor ,"min":sp .Min })
        try :
            return sp .sympify (stripped ,locals =local_dict )
        except (TypeError ,ValueError ,SyntaxError ,sp .SympifyError ):
            return None

    @staticmethod
    def verify_broadcast_compat (
    source_shape :ArrayAttr [Attribute ],
    target_shape :ArrayAttr [Attribute ],
    )->None :
        """校验 dma.broadcast 的 shape 兼容性。


        功能说明:
        - 按尾维对齐规则检查 source/target shape。
        - 仅在静态整数维度冲突时失败，符号维度不做数值求解。

        使用示例:
        - verify_broadcast_compat(source_type.shape, target_type.shape)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        source_dims =source_shape .data
        target_dims =target_shape .data
        if len (source_dims )>len (target_dims ):
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.broadcast source rank must be <= target rank")

        for offset in range (1 ,len (target_dims )+1 ):
            target_dim =target_dims [-offset ]
            source_dim =source_dims [-offset ]if offset <=len (source_dims )else _DmaTransferHelpers .symbol_expr_attr_from_expr ("1")
            source_value =_DmaTransferHelpers .static_int_from_dim (source_dim )
            target_value =_DmaTransferHelpers .static_int_from_dim (target_dim )
            if source_value is not None and target_value is not None :
                if source_value !=target_value and source_value !=1 and target_value !=1 :
                    raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.broadcast shape mismatch")

    @staticmethod
    def dims_equal (lhs :Attribute ,rhs :Attribute )->bool :
        """判断 shape/stride 维度是否一致。


        功能说明:
        - 支持 SymbolExprAttr 的 canonical 文本一致性判断。

        使用示例:
        - dims_equal(SymbolExprAttr.from_expr("N"), SymbolExprAttr.from_expr("N"))

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if isinstance (lhs ,SymbolExprAttr )and isinstance (rhs ,SymbolExprAttr ):
            return lhs .expr .data ==rhs .expr .data
        return False

    @staticmethod
    def verify_transpose_perm (perm :ArrayAttr ,rank :int )->list [int ]:
        """校验 dma.transpose 的 perm 合法性并返回序列。


        功能说明:
        - 校验 perm 长度与 rank 一致。
        - 校验 perm 为 0..rank-1 的排列。

        使用示例:
        - verify_transpose_perm(ArrayAttr([IntAttr(1), IntAttr(0)]), rank=2)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if len (perm .data )!=rank :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.transpose perm must match source rank")
        perm_values :list [int ]=[]
        for entry in perm .data :
            if isinstance (entry ,IntAttr ):
                perm_values .append (entry .data )
                continue
            if isinstance (entry ,IntegerAttr )and isinstance (entry .value ,IntAttr ):
                perm_values .append (entry .value .data )
                continue
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.transpose perm must be a permutation of 0..rank-1")
        if sorted (perm_values )!=list (range (rank )):
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.transpose perm must be a permutation of 0..rank-1")
        return perm_values

    @staticmethod
    def verify_transpose_layout (
    source_type :NnMemoryType ,
    target_type :NnMemoryType ,
    perm_values :Sequence [int ],
    )->None :
        """校验 dma.transpose 的目标 shape 与连续 stride。


        功能说明:
        - 按 perm 重排 source shape，并与 target shape 对齐校验。
        - target stride 必须是 target shape 的默认连续 stride；匿名动态 shape 的高维 stride 可保留调用点动态语义表达。

        使用示例:
        - verify_transpose_layout(source_type, target_type, [1, 0])

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if len (target_type .shape .data )!=len (perm_values ):
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.transpose target rank mismatch")
        expected_shape =[source_type .shape .data [index ]for index in perm_values ]
        for expected_dim ,actual_dim in zip (expected_shape ,target_type .shape .data ,strict =True ):
            if not _DmaTransferHelpers .dims_equal (expected_dim ,actual_dim ):
                raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.transpose target shape mismatch")

        expected_stride =_DmaTransferHelpers .default_contiguous_stride (target_type .shape )
        for expected_dim ,actual_dim in zip (expected_stride ,target_type .stride .data ,strict =True ):
            if not _DmaTransferHelpers .stride_attrs_equal (expected_dim ,actual_dim ):
                if _DmaTransferHelpers .dim_expr_text (expected_dim )=="?"and _DmaTransferHelpers .static_int_from_dim (actual_dim )is None :
                    continue
                raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.transpose target stride mismatch")

    @staticmethod
    def parenthesize_symbol_expr (expr :str )->str :
        """为乘法组合准备符号表达式文本。

        功能说明:
        - 简单标识符和整数保持原文。
        - 复合表达式加括号，避免 `floordiv`、加减法参与 stride 乘积时改变语义。

        使用示例:
        - text = parenthesize_symbol_expr("M + 1")

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if expr =="?"or expr .replace ("_","").isalnum ()or expr .lstrip ("-").isdigit ():
            return expr
        return f"({expr })"

    @staticmethod
    def symbol_expr_product (lhs :str ,rhs :str )->str :
        """组合两个 symbol 表达式乘积。

        功能说明:
        - 消除乘以 1 的冗余文本。
        - 对复合表达式加括号，保持默认连续 stride 的符号计算语义。

        使用示例:
        - expr = symbol_expr_product("M + 1", "N")

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if lhs =="1":
            return rhs
        if rhs =="1":
            return lhs
        return f"{_DmaTransferHelpers .parenthesize_symbol_expr (lhs )}*{_DmaTransferHelpers .parenthesize_symbol_expr (rhs )}"

    @staticmethod
    def default_contiguous_stride (shape :ArrayAttr [Attribute ])->list [Attribute ]:
        """按默认连续布局生成行主序 stride。


        功能说明:
        - 静态维度返回 `#symbol.expr<整数>`。
        - 符号维度返回 canonical `#symbol.expr<乘积>`。
        - `#symbol.expr<?>` 维度会把更高维 stride 退化为 `#symbol.expr<?>`。

        使用示例:
        - default_contiguous_stride(ArrayAttr([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("4")]))

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        stride :list [Attribute ]=[]
        running :str |None ="1"
        for dim in reversed (shape .data ):
            if running is None :
                stride .append (_DmaTransferHelpers .symbol_expr_attr_from_expr ("?"))
            else :
                stride .append (_DmaTransferHelpers .symbol_expr_attr_from_expr (running ))
            if running is None :
                continue
            dim_expr =_DmaTransferHelpers .dim_expr_text (dim )
            if dim_expr =="?":
                running =None
            elif dim_expr =="1":
                continue
            elif running =="1":
                running =dim_expr
            else :
                running =_DmaTransferHelpers .dim_expr_text (_DmaTransferHelpers .symbol_expr_attr_from_expr (_DmaTransferHelpers .symbol_expr_product (dim_expr ,running )))
        stride .reverse ()
        return stride

    @staticmethod
    def parse_symbolic_dim_attr (value :Attribute )->sp .Basic |None :
        """解析 stride 维度 attribute 为 sympy 表达式。


        功能说明:
        - `SymbolExprAttr` 解析为符号表达式，并为所有标识符创建同名整数符号。
        - `min(...)` 按 `sympy.Min` 解析，用于判定动态尾块连续 stride。
        - 无法解析或未知动态维度时返回 `None`。

        使用示例:
        - parse_symbolic_dim_attr(SymbolExprAttr.from_expr("KH*KW*TC"))

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if not isinstance (value ,SymbolExprAttr ):
            return None
        return _DmaTransferHelpers .parse_symbolic_expr_text (value .expr .data )

    @staticmethod
    def stride_attrs_equal (lhs :Attribute ,rhs :Attribute )->bool :
        """判断两个 stride 维度是否等价。


        功能说明:
        - 优先复用公共维度比较。
        - 当文本不同但表达式等价时，使用 sympy 简化差值判断。

        使用示例:
        - stride_attrs_equal(SymbolExprAttr.from_expr("TC*KH*KW"), SymbolExprAttr.from_expr("KH*KW*TC"))

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if _DmaTransferHelpers .dims_equal (lhs ,rhs ):
            return True
        lhs_expr =_DmaTransferHelpers .parse_symbolic_dim_attr (lhs )
        rhs_expr =_DmaTransferHelpers .parse_symbolic_dim_attr (rhs )
        if lhs_expr is None or rhs_expr is None :
            return False
        return sp .simplify (lhs_expr -rhs_expr )==0

















@irdl_op_definition
class DmaCopyOp (IRDLOperation ):
    """dma.copy。"""

    name ="dma.copy"
    traits =traits_def (DmaTargetSourceEffect ())

    target =operand_def (NnMemoryType )
    source =operand_def (NnMemoryType )

    def __init__ (self ,target :SSAValue |Operation ,source :SSAValue |Operation )->None :
        """初始化 dma.copy。


        功能说明:
        - 设置 target 与 source operand。

        使用示例:
        - DmaCopyOp(target, source)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        super ().__init__ (operands =[target ,source ])

    def verify_ (self )->None :
        """校验 dma.copy。


        功能说明:
        - source/target 的 shape/stride/element_type 必须一致。

        使用示例:
        - DmaCopyOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        source_type =_DmaTransferHelpers .verify_memory_type (self .source .type ,"source")
        target_type =_DmaTransferHelpers .verify_memory_type (self .target .type ,"target")
        if source_type .shape !=target_type .shape :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.copy source/target shape mismatch")
        if source_type .stride !=target_type .stride :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.copy source/target stride mismatch")
        if source_type .element_type !=target_type .element_type :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.copy source/target element_type mismatch")


@irdl_op_definition
class DmaBroadcastOp (IRDLOperation ):
    """dma.broadcast。"""

    name ="dma.broadcast"
    traits =traits_def (DmaBroadcastMemoryEffect ())

    target =operand_def (NnMemoryType )
    source =operand_def (Attribute )

    def __init__ (self ,target :SSAValue |Operation ,source :SSAValue |Operation )->None :
        """初始化 dma.broadcast。


        功能说明:
        - 设置 target 与 source operand。

        使用示例:
        - DmaBroadcastOp(target, source)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        super ().__init__ (operands =[target ,source ])

    def verify_ (self )->None :
        """校验 dma.broadcast。


        功能说明:
        - target 必须为 nn.memory。
        - memory source 需满足 element_type/space 与 broadcast 规则。
        - scalar source 必须与 target.element_type 类型一致，或为整数场景的 symbol.int。

        使用示例:
        - DmaBroadcastOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        target_type =_DmaTransferHelpers .verify_memory_type (self .target .type ,"target")
        source_value =SSAValue .get (self .source )
        source_type =source_value .type

        if isinstance (source_type ,NnMemoryType ):
            source_type =_DmaTransferHelpers .verify_memory_type (source_type ,"source")
            if source_type .element_type !=target_type .element_type :
                raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.broadcast element_type mismatch")
            if source_type .space .space .data !=target_type .space .space .data :
                raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.broadcast space mismatch")
            _DmaTransferHelpers .verify_broadcast_compat (source_type .shape ,target_type .shape )
            return

        if isinstance (source_type ,SymbolValueType ):
            if not isinstance (target_type .element_type ,IntegerType ):
                raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.broadcast symbol.int target must be integer element_type")
            return

        if source_type !=target_type .element_type :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.broadcast scalar type mismatch")


@irdl_op_definition
class DmaTransposeOp (IRDLOperation ):
    """dma.transpose。"""

    name ="dma.transpose"
    traits =traits_def (DmaTargetSourceEffect ())

    target =operand_def (NnMemoryType )
    source =operand_def (NnMemoryType )
    perm =attr_def (ArrayAttr )

    def __init__ (
    self ,
    target :SSAValue |Operation ,
    source :SSAValue |Operation ,
    perm :Sequence [int ]|ArrayAttr ,
    )->None :
        """初始化 dma.transpose。


        功能说明:
        - 设置 target/source operand 与 perm 属性。

        使用示例:
        - DmaTransposeOp(target, source, perm=[1, 0])

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        perm_attr =perm if isinstance (perm ,ArrayAttr )else ArrayAttr ([IntAttr (value )for value in perm ])
        super ().__init__ (operands =[target ,source ],attributes ={"perm":perm_attr })

    def verify_ (self )->None :
        """校验 dma.transpose。


        功能说明:
        - target/source 必须为 nn.memory。
        - element_type 必须一致，space 允许不同，用于跨层级物化转置。
        - perm 必须是 0..rank-1 的排列，target shape 为 source 的重排。
        - target stride 必须是 target shape 的默认连续 stride。

        使用示例:
        - DmaTransposeOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        target_type =_DmaTransferHelpers .verify_memory_type (self .target .type ,"target")
        source_type =_DmaTransferHelpers .verify_memory_type (self .source .type ,"source")
        if target_type .element_type !=source_type .element_type :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.transpose element_type mismatch")
        perm_values =_DmaTransferHelpers .verify_transpose_perm (self .perm ,len (source_type .shape .data ))
        _DmaTransferHelpers .verify_transpose_layout (source_type ,target_type ,perm_values )



@irdl_op_definition
class DmaCastOp (IRDLOperation ):
    """dma.cast。"""

    name ="dma.cast"
    traits =traits_def (DmaTargetSourceEffect ())

    target =operand_def (NnMemoryType )
    source =operand_def (NnMemoryType )

    def __init__ (self ,target :SSAValue |Operation ,source :SSAValue |Operation )->None :
        """初始化 dma.cast。


        功能说明:
        - 设置 target 与 source。

        使用示例:
        - DmaCastOp(target, source)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        super ().__init__ (operands =[target ,source ])

    def verify_ (self )->None :
        """校验 dma.cast。


        功能说明:
        - target/source 的 shape/stride/space 必须一致，仅 element_type 可变化。

        使用示例:
        - DmaCastOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        target_type =_DmaTransferHelpers .verify_memory_type (self .target .type ,"target")
        source_type =_DmaTransferHelpers .verify_memory_type (self .source .type ,"source")
        if source_type .shape !=target_type .shape :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.cast shape mismatch")
        if source_type .stride !=target_type .stride :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.cast stride mismatch")
        if source_type .space .space .data !=target_type .space .space .data :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.cast space mismatch")



__all__ =[
"DmaCopyOp",
"DmaBroadcastOp",
"DmaTransposeOp",
"DmaCastOp",
]
