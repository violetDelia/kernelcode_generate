"""DMA alias operation definitions.

功能说明:
- 定义 `dma.view`、`dma.subview`、`dma.reshape` 与 `dma.reinterpret`。

API 列表:
- `class DmaSubviewOp(source: SSAValue | Operation, offset: SSAValue | Operation, size: SSAValue | Operation, stride: SSAValue | Operation, result_type: NnMemoryType)`
- `class DmaViewOp(source: SSAValue | Operation, offsets: Sequence[SSAValue], shape: Sequence[SSAValue], stride: Sequence[SSAValue], result_type: NnMemoryType)`
- `class DmaReshapeOp(source: SSAValue | Operation, shape: Sequence[SSAValue], result_type: NnMemoryType)`
- `class DmaReinterpretOp(source: SSAValue | Operation, offset: SSAValue | Operation, shape: Sequence[SSAValue], stride: Sequence[SSAValue], result_type: NnMemoryType)`

使用示例:
- `DmaViewOp(source, offsets, shape, stride, result_type)`

关联文件:
- spec: spec/dialect/dma.md
- test: test/dialect/dma/
- 功能实现: kernel_gen/dialect/dma/operation/alias.py
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

from ..canonicalization import DmaReshapeCanonicalizationTrait ,DmaViewCanonicalizationTrait

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

class _DmaAliasHelpers :
    """当前文件内本地 helper 容器。

    功能说明:
    - 承接退场 common.py 后的文件内 helper，避免形成模块级事实公开函数。

    使用示例:
    - _DmaAliasHelpers.helper(...)
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
            static_value =_DmaAliasHelpers .operand_int_value (value )
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
            static_value =_DmaAliasHelpers .operand_int_value (value )
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

        return _DmaAliasHelpers .static_int_from_expr_text (_DmaAliasHelpers .dim_expr_text (dim ))

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
            expected_int =_DmaAliasHelpers .static_int_from_dim (expected )
            if expected_int is not None :
                static_value =_DmaAliasHelpers .operand_int_value (value )
                if static_value !=expected_int :
                    raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,message )
                continue
            expected_expr =_DmaAliasHelpers .dim_expr_text (expected )
            if expected_expr =="?":
                if not isinstance (value .type ,SymbolValueType )or value .type .get_value ()!="?":
                    raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,message )
                continue
            if not isinstance (value .type ,SymbolValueType )or value .type .get_value ()!=expected_expr :
                raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,message )

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
    def element_byte_size (element_type :Attribute )->int |None :
        """解析 element_type 的字节大小。


        功能说明:
        - 支持 i1/i8/i16/i32/i64 与 f16/bf16/f32/f64。

        使用示例:
        - size = element_byte_size(Float32Type())

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if isinstance (element_type ,IntegerType ):
            width =int (element_type .width .data )
            if width in {1 ,8 }:
                return 1
            if width ==16 :
                return 2
            if width ==32 :
                return 4
            if width ==64 :
                return 8
            return None
        if isinstance (element_type ,(Float16Type ,BFloat16Type )):
            return 2
        if isinstance (element_type ,Float32Type ):
            return 4
        if isinstance (element_type ,Float64Type ):
            return 8
        return None

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
    def linear_max_index (
    offsets :Sequence [SSAValue ],
    shape :Sequence [SSAValue ],
    stride :Sequence [SSAValue ],
    )->int |None :
        """计算 view 的静态最大线性索引（元素单位）。


        功能说明:
        - 当 offsets/shape/stride 都可静态还原时，返回最大线性索引。
        - 任一值无法静态还原则返回 None。

        使用示例:
        - max_index = linear_max_index(op.offsets, op.shape, op.stride)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        total =0
        for offset_value ,size_value ,stride_value in zip (offsets ,shape ,stride ,strict =True ):
            offset_int =_DmaAliasHelpers .operand_int_value (offset_value )
            size_int =_DmaAliasHelpers .operand_int_value (size_value )
            stride_int =_DmaAliasHelpers .operand_int_value (stride_value )
            if offset_int is None or size_int is None or stride_int is None :
                return None
            total +=offset_int +(size_int -1 )*stride_int
        return total

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
            value =_DmaAliasHelpers .static_int_from_dim (dim )
            if value is None :
                return None
            numel *=value
        return numel

    @staticmethod
    def verify_static_view_bounds (
    source_shape :ArrayAttr [Attribute ],
    source_stride :ArrayAttr [Attribute ],
    offsets :Sequence [SSAValue ],
    shape :Sequence [SSAValue ],
    stride :Sequence [SSAValue ],
    )->None :
        """校验 dma.view 可静态判定的边界约束。


        功能说明:
        - 当 `source.shape/source.stride` 与 `offsets/shape/stride` 都可静态恢复时，
          以源内存线性起点和结果线性覆盖范围执行静态边界检查。

        使用示例:
        - verify_static_view_bounds(source_type.shape, source_type.stride, op.offsets, op.shape, op.stride)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        source_numel =_DmaAliasHelpers .maybe_numel (source_shape )
        if source_numel is None :
            return
        linear_start =0
        linear_extent =0
        for source_step_attr ,offset_value ,size_value ,stride_value in zip (
        source_stride .data ,offsets ,shape ,stride ,strict =True
        ):
            source_step =_DmaAliasHelpers .static_int_from_dim (source_step_attr )
            if source_step is None :
                return
            offset_int =_DmaAliasHelpers .operand_int_value (offset_value )
            size_int =_DmaAliasHelpers .operand_int_value (size_value )
            stride_int =_DmaAliasHelpers .operand_int_value (stride_value )
            if offset_int is None or size_int is None or stride_int is None :
                return
            linear_start +=offset_int *source_step
            linear_extent +=(size_int -1 )*stride_int *source_step
        if linear_start +linear_extent >=source_numel :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.view bounds mismatch")

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
        return f"{_DmaAliasHelpers .parenthesize_symbol_expr (lhs )}*{_DmaAliasHelpers .parenthesize_symbol_expr (rhs )}"

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
                stride .append (_DmaAliasHelpers .symbol_expr_attr_from_expr ("?"))
            else :
                stride .append (_DmaAliasHelpers .symbol_expr_attr_from_expr (running ))
            if running is None :
                continue
            dim_expr =_DmaAliasHelpers .dim_expr_text (dim )
            if dim_expr =="?":
                running =None
            elif dim_expr =="1":
                continue
            elif running =="1":
                running =dim_expr
            else :
                running =_DmaAliasHelpers .dim_expr_text (_DmaAliasHelpers .symbol_expr_attr_from_expr (_DmaAliasHelpers .symbol_expr_product (dim_expr ,running )))
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
        return _DmaAliasHelpers .parse_symbolic_expr_text (value .expr .data )

    @staticmethod
    def parse_symbol_value_expr (value :SSAValue )->sp .Basic |None :
        """解析 `!symbol.int<#symbol.expr<expr>>` operand 为 sympy 表达式。


        功能说明:
        - 仅解析 `SymbolValueType` 的公开表达式文本。
        - 无法解析或未知动态值时返回 `None`，由调用方跳过静态比较。

        使用示例:
        - parse_symbol_value_expr(op.stride[0])

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if not isinstance (value .type ,SymbolValueType ):
            return None
        return _DmaAliasHelpers .parse_symbolic_expr_text (value .type .expr .expr .data )

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

        if _DmaAliasHelpers .dims_equal (lhs ,rhs ):
            return True
        lhs_expr =_DmaAliasHelpers .parse_symbolic_dim_attr (lhs )
        rhs_expr =_DmaAliasHelpers .parse_symbolic_dim_attr (rhs )
        if lhs_expr is None or rhs_expr is None :
            return False
        return sp .simplify (lhs_expr -rhs_expr )==0

    @staticmethod
    def verify_view_result_stride (
    source_stride :ArrayAttr [Attribute ],
    stride :Sequence [SSAValue ],
    result_stride :ArrayAttr [Attribute ],
    )->None :
        """校验 dma.view 结果 stride 来自源物理 stride 与逻辑 stride 的乘积。


        功能说明:
        - 对可解析维度执行 `result_stride == source_stride * stride_operand` 比较。
        - 含未知 `?` 或不可解析符号时跳过该维静态比较，保留动态 IR 表达能力。

        使用示例:
        - verify_view_result_stride(source_type.stride, op.stride, result_type.stride)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        for source_attr ,stride_value ,result_attr in zip (source_stride .data ,stride ,result_stride .data ,strict =True ):
            source_expr =_DmaAliasHelpers .parse_symbolic_dim_attr (source_attr )
            stride_expr =_DmaAliasHelpers .parse_symbol_value_expr (stride_value )
            result_expr =_DmaAliasHelpers .parse_symbolic_dim_attr (result_attr )
            if source_expr is None or stride_expr is None or result_expr is None :
                continue
            if sp .simplify (result_expr -(source_expr *stride_expr ))!=0 :
                raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"stride must match source physical stride * view stride")

    @staticmethod
    def is_contiguous (memory_type :NnMemoryType )->bool :
        """检查 memory type 是否连续行主序。


        功能说明:
        - 静态 stride 直接比较整数。
        - 符号 stride 使用表达式等价判断，允许乘法因子顺序不同。
        - 由匿名动态 shape 推导出的未知高维 stride 接受动态语义表达，保留调用点变量名。

        使用示例:
        - is_contiguous(memory_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        expected =_DmaAliasHelpers .default_contiguous_stride (memory_type .shape )
        if len (expected )!=len (memory_type .stride .data ):
            return False
        for expected_dim ,stride_dim in zip (expected ,memory_type .stride .data ,strict =True ):
            if not _DmaAliasHelpers .stride_attrs_equal (expected_dim ,stride_dim ):
                if _DmaAliasHelpers .dim_expr_text (expected_dim )=="?"and _DmaAliasHelpers .static_int_from_dim (stride_dim )is None :
                    continue
                return False
        return True

    @staticmethod
    def verify_default_contiguous_stride (memory_type :NnMemoryType ,message :str )->None :
        """校验 memory type 的 stride 是否匹配默认连续布局。


        功能说明:
        - 根据 `shape` 生成默认连续布局。
        - 要求 `stride` 与默认布局完全一致。

        使用示例:
        - verify_default_contiguous_stride(result_type, "dma.alloc requires contiguous result stride")

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if not _DmaAliasHelpers .is_contiguous (memory_type ):
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,message )





























def _linear_extent_index (shape :Sequence [SSAValue ],stride :Sequence [SSAValue ])->int |None :
    """计算 shape/stride 的静态最大线性相对索引。

    功能说明:
    - `dma.reinterpret` 的 offset 是独立 operand，本 helper 只计算从 result 起点到最后一个元素的线性距离。
    - 任一 shape/stride 无法静态恢复时返回 None，让 verifier 跳过静态 bounds 判断。

    使用示例:
    - extent = _linear_extent_index(op.shape, op.stride)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    total =0
    for size_value ,stride_value in zip (shape ,stride ,strict =True ):
        size_int =_DmaAliasHelpers .operand_int_value (size_value )
        stride_int =_DmaAliasHelpers .operand_int_value (stride_value )
        if size_int is None or stride_int is None :
            return None
        total +=(size_int -1 )*stride_int
    return total


@irdl_op_definition
class DmaViewOp (IRDLOperation ):
    """dma.view。"""

    name ="dma.view"
    traits =traits_def (NoMemoryEffect (),DmaViewCanonicalizationTrait ())

    source =operand_def (NnMemoryType )
    offsets =var_operand_def (Attribute )
    shape =var_operand_def (SymbolValueType )
    stride =var_operand_def (SymbolValueType )
    result =result_def (NnMemoryType )

    irdl_options =[AttrSizedOperandSegments (as_property =True )]

    def __init__ (
    self ,
    source :SSAValue |Operation ,
    offsets :Sequence [SSAValue ],
    shape :Sequence [SSAValue ],
    stride :Sequence [SSAValue ],
    result_type :NnMemoryType ,
    )->None :
        """初始化 dma.view。


        功能说明:
        - 设置 source、动态 offsets/shape/stride operand 与结果类型。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaViewOp(source, offsets, shape, stride, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if not isinstance (result_type ,NnMemoryType ):
            raise TypeError ("result_type must be nn.memory")

        super ().__init__ (operands =[source ,offsets ,shape ,stride ],result_types =[result_type ])

    def verify_ (self )->None :
        """校验 dma.view。


        功能说明:
        - `space` 必须一致；`element_type` 必须一致（i8 byte pool 允许不同 element_type）。
        - 非 byte pool 场景下 source/result rank 必须一致；byte pool 允许 rank 不一致。
        - `offsets` 允许 `!symbol.int` 与 `!symbol.iter`，`shape`/`stride` 仍需 `!symbol.int`。
        - `offsets`/`shape`/`stride` 长度与结果 rank 一致。
        - 非 byte pool 场景下，结果 stride 必须等于 source physical stride 与 view logical stride 的逐维乘积。
        - 当边界可静态判定时，必须满足 `offset + (size - 1) * stride < dim`。
        - 非 byte pool 场景下可判定 numel 不一致必须报错；byte pool 需满足 typed 子区间字节边界可达。

        使用示例:
        - DmaViewOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        source_type =_DmaAliasHelpers .verify_memory_type (self .source .type ,"source")
        result_type =_DmaAliasHelpers .verify_memory_type (self .result .type ,"result")
        offsets =_DmaAliasHelpers .verify_symbol_index_operands (self .offsets ,"offsets",min_value =0 )
        shape =_DmaAliasHelpers .verify_symbol_int_operands (self .shape ,"shape",min_value =1 )
        stride =_DmaAliasHelpers .verify_symbol_int_operands (self .stride ,"stride",min_value =1 )
        rank =len (result_type .shape .data )
        if len (source_type .shape .data )!=rank and not _DmaAliasHelpers .is_i8_byte_pool (source_type ):
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.view source/result rank mismatch")
        _DmaAliasHelpers .verify_rank_match (offsets ,rank ,"offsets")
        _DmaAliasHelpers .verify_rank_match (shape ,rank ,"shape")
        _DmaAliasHelpers .verify_rank_match (stride ,rank ,"stride")
        _DmaAliasHelpers .verify_operands_match_layout (shape ,result_type .shape ,"shape must match result shape")
        if source_type .space .space .data !=result_type .space .space .data :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.view space mismatch")

        source_numel =_DmaAliasHelpers .maybe_numel (source_type .shape )
        result_numel =_DmaAliasHelpers .maybe_numel (result_type .shape )
        if _DmaAliasHelpers .is_i8_byte_pool (source_type ):
            _DmaAliasHelpers .verify_operands_match_layout (stride ,result_type .stride ,"stride must match result stride")
            result_elem_size =_DmaAliasHelpers .element_byte_size (result_type .element_type )
            if result_elem_size is None :
                raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.view element_type unsupported for byte pool")
            max_index =_DmaAliasHelpers .linear_max_index (offsets ,shape ,stride )
            if max_index is not None and source_numel is not None :
                byte_end =(max_index +1 )*result_elem_size
                if byte_end >source_numel :
                    raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.view byte bounds mismatch")
        else :
            _DmaAliasHelpers .verify_view_result_stride (source_type .stride ,stride ,result_type .stride )
            if source_type .element_type !=result_type .element_type :
                raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.view element_type mismatch")
            if source_numel is not None and result_numel is not None and source_numel !=result_numel :
                raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.view numel mismatch")
            _DmaAliasHelpers .verify_static_view_bounds (source_type .shape ,source_type .stride ,offsets ,shape ,stride )


@irdl_op_definition
class DmaSubviewOp (IRDLOperation ):
    """dma.subview。"""

    name ="dma.subview"
    traits =traits_def (NoMemoryEffect ())

    source =var_operand_def (NnMemoryType )
    offset =var_operand_def (SymbolValueType )
    size =var_operand_def (SymbolValueType )
    stride =var_operand_def (SymbolValueType )
    result =result_def (NnMemoryType )

    irdl_options =(AttrSizedOperandSegments (as_property =True ),)

    def __init__ (
    self ,
    source :SSAValue |Operation ,
    offset :SSAValue |Operation ,
    size :SSAValue |Operation ,
    stride :SSAValue |Operation ,
    result_type :NnMemoryType ,
    )->None :
        """初始化 dma.subview。


        功能说明:
        - 设置一维 i8 backing memory、元素单位 offset/size/stride 与一维 typed result。
        - `offset/size/stride` 均为单个 `!symbol.int<#symbol.expr<expr>>` operand。

        使用示例:
        - DmaSubviewOp(pool, offset, size, stride, flat_result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if not isinstance (result_type ,NnMemoryType ):
            raise TypeError ("result_type must be nn.memory")

        super ().__init__ (
        operands =[[source ],[offset ],[size ],[stride ]],
        result_types =[result_type ],
        )

    def verify_ (self )->None :
        """校验 dma.subview。


        功能说明:
        - source 必须是一维 i8 backing memory。
        - result 必须是一维 contiguous typed memory，且 space 与 source 一致。
        - offset/size/stride 都必须是单个 `!symbol.int<#symbol.expr<expr>>`；size 必须匹配 result flat shape。

        使用示例:
        - DmaSubviewOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if len (self .source )!=1 or len (self .offset )!=1 or len (self .size )!=1 or len (self .stride )!=1 :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.subview requires one source, offset, size and stride")

        source_type =_DmaAliasHelpers .verify_memory_type (self .source [0 ].type ,"source")
        result_type =_DmaAliasHelpers .verify_memory_type (self .result .type ,"result")
        offset =_DmaAliasHelpers .verify_symbol_int_operands (self .offset ,"offset",min_value =0 )[0 ]
        size =_DmaAliasHelpers .verify_symbol_int_operands (self .size ,"size",min_value =1 )[0 ]
        stride =_DmaAliasHelpers .verify_symbol_int_operands (self .stride ,"stride",min_value =1 )[0 ]

        if not _DmaAliasHelpers .is_i8_byte_pool (source_type ):
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.subview source must be one-dimensional i8 memory")
        if len (result_type .shape .data )!=1 :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.subview result must be one-dimensional")
        if len (result_type .stride .data )!=1 :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.subview result stride rank must be one")
        if source_type .space .space .data !=result_type .space .space .data :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.subview space mismatch")

        _DmaAliasHelpers .verify_default_contiguous_stride (result_type ,"dma.subview result must be contiguous")
        _DmaAliasHelpers .verify_operands_match_layout ([size ],result_type .shape ,"dma.subview size must match result shape")

        source_numel =_DmaAliasHelpers .maybe_numel (source_type .shape )
        result_numel =_DmaAliasHelpers .maybe_numel (result_type .shape )
        result_elem_size =_DmaAliasHelpers .element_byte_size (result_type .element_type )
        if result_elem_size is None :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.subview result element_type unsupported")
        offset_int =_DmaAliasHelpers .operand_int_value (offset )
        size_int =_DmaAliasHelpers .operand_int_value (size )
        stride_int =_DmaAliasHelpers .operand_int_value (stride )
        if (
        source_numel is not None
        and result_numel is not None
        and offset_int is not None
        and size_int is not None
        and stride_int is not None
        ):
            byte_end =(offset_int +(size_int -1 )*stride_int +1 )*result_elem_size
            if byte_end >source_numel :
                raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.subview byte bounds mismatch")


@irdl_op_definition
class DmaReshapeOp (IRDLOperation ):
    """dma.reshape。"""

    name ="dma.reshape"
    traits =traits_def (NoMemoryEffect (),DmaReshapeCanonicalizationTrait ())

    source =operand_def (NnMemoryType )
    shape =var_operand_def (SymbolValueType )
    result =result_def (NnMemoryType )

    irdl_options =[AttrSizedOperandSegments (as_property =True )]

    def __init__ (
    self ,
    source :SSAValue |Operation ,
    shape :Sequence [SSAValue ],
    result_type :NnMemoryType ,
    )->None :
        """初始化 dma.reshape。


        功能说明:
        - 设置 source、动态 shape operand 与结果类型。

        使用示例:
        - DmaReshapeOp(source, shape, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        super ().__init__ (operands =[source ,shape ],result_types =[result_type ])

    def verify_ (self )->None :
        """校验 dma.reshape。


        功能说明:
        - element_type/space 必须一致。
        - source 必须连续，result.stride 必须为连续行主序。
        - 可判定 numel 不一致必须报错。

        使用示例:
        - DmaReshapeOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        source_type =_DmaAliasHelpers .verify_memory_type (self .source .type ,"source")
        result_type =_DmaAliasHelpers .verify_memory_type (self .result .type ,"result")
        shape =_DmaAliasHelpers .verify_symbol_int_operands (self .shape ,"shape",min_value =1 )
        _DmaAliasHelpers .verify_rank_match (shape ,len (result_type .shape .data ),"shape")
        _DmaAliasHelpers .verify_operands_match_layout (shape ,result_type .shape ,"shape must match result shape")
        if source_type .element_type !=result_type .element_type :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.reshape element_type mismatch")
        if source_type .space .space .data !=result_type .space .space .data :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.reshape space mismatch")

        source_numel =_DmaAliasHelpers .maybe_numel (source_type .shape )
        result_numel =_DmaAliasHelpers .maybe_numel (result_type .shape )
        if source_numel is not None and result_numel is not None and source_numel !=result_numel :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.reshape numel mismatch")

        if not _DmaAliasHelpers .is_contiguous (source_type ):
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.reshape requires contiguous source")

        _DmaAliasHelpers .verify_default_contiguous_stride (result_type ,"dma.reshape requires contiguous result stride")


@irdl_op_definition
class DmaReinterpretOp (IRDLOperation ):
    """dma.reinterpret。"""

    name ="dma.reinterpret"
    traits =traits_def (NoMemoryEffect ())

    source =operand_def (NnMemoryType )
    offset =operand_def (Attribute )
    shape =var_operand_def (SymbolValueType )
    stride =var_operand_def (SymbolValueType )
    result =result_def (NnMemoryType )

    irdl_options =[AttrSizedOperandSegments (as_property =True )]

    def __init__ (
    self ,
    source :SSAValue |Operation ,
    offset :SSAValue |Operation ,
    shape :Sequence [SSAValue ],
    stride :Sequence [SSAValue ],
    result_type :NnMemoryType ,
    )->None :
        """初始化 dma.reinterpret。


        功能说明:
        - 设置 source、线性 offset、result shape/stride operand 与结果类型。
        - source 是一维 i8 byte pool 时，offset 单位为 byte；其它 source 使用 source element 单位。

        使用示例:
        - DmaReinterpretOp(source, offset, shape, stride, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if not isinstance (result_type ,NnMemoryType ):
            raise TypeError ("result_type must be nn.memory")

        super ().__init__ (operands =[source ,offset ,shape ,stride ],result_types =[result_type ])

    def verify_ (self )->None :
        """校验 dma.reinterpret。


        功能说明:
        - source/result 均为 `!nn.memory` 且 memory space 必须一致。
        - 非 byte pool source 要求 source/result element_type 一致；byte pool source 允许 result 使用 typed element。
        - offset 必须是 `!symbol.int` 或 `!symbol.iter`；shape/stride 必须是 `!symbol.int`。
        - shape/stride operand 必须与 result type 的 shape/stride exact 匹配。
        - 静态可判定时按 offset 单位执行 bounds 检查。

        使用示例:
        - DmaReinterpretOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        source_type =_DmaAliasHelpers .verify_memory_type (self .source .type ,"source")
        result_type =_DmaAliasHelpers .verify_memory_type (self .result .type ,"result")
        offset =_DmaAliasHelpers .verify_symbol_index_operands ([self .offset ],"offset",min_value =0 )[0 ]
        shape =_DmaAliasHelpers .verify_symbol_int_operands (self .shape ,"shape",min_value =1 )
        stride =_DmaAliasHelpers .verify_symbol_int_operands (self .stride ,"stride",min_value =1 )
        rank =len (result_type .shape .data )
        _DmaAliasHelpers .verify_rank_match (shape ,rank ,"shape")
        _DmaAliasHelpers .verify_rank_match (stride ,rank ,"stride")
        _DmaAliasHelpers .verify_operands_match_layout (shape ,result_type .shape ,"dma.reinterpret shape must match result shape")
        _DmaAliasHelpers .verify_operands_match_layout (stride ,result_type .stride ,"dma.reinterpret stride must match result stride")
        if source_type .space .space .data !=result_type .space .space .data :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.reinterpret space mismatch")

        source_numel =_DmaAliasHelpers .maybe_numel (source_type .shape )
        extent =_linear_extent_index (shape ,stride )
        offset_int =_DmaAliasHelpers .operand_int_value (offset )
        if _DmaAliasHelpers .is_i8_byte_pool (source_type ):
            result_elem_size =_DmaAliasHelpers .element_byte_size (result_type .element_type )
            if result_elem_size is None :
                raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.reinterpret result element_type unsupported for byte pool")
            if source_numel is not None and offset_int is not None and extent is not None :
                byte_end =offset_int +(extent +1 )*result_elem_size
                if byte_end >source_numel :
                    raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.reinterpret byte bounds mismatch")
            return

        if source_type .element_type !=result_type .element_type :
            raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.reinterpret element_type mismatch")
        if source_numel is not None and offset_int is not None and extent is not None :
            if offset_int +extent >=source_numel :
                raise kernel_code_error (ErrorKind .VERIFY ,ErrorModule .DIALECT ,"dma.reinterpret bounds mismatch")


__all__ =[
"DmaViewOp",
"DmaSubviewOp",
"DmaReshapeOp",
"DmaReinterpretOp",
]
