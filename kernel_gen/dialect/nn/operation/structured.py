"""nn structured operations.

功能说明:
- 承载 nn dialect package 拆分后的 nn structured operations 实现。

API 列表:
- `class NnImg2col1dOp(input_value: SSAValue, result_type: NnMemoryType, kw: SSAValue, sw: SSAValue, dw: SSAValue, pl: SSAValue, pr: SSAValue, space: NnMemorySpaceAttr)`
- `class NnImg2col2dOp(input_value: SSAValue, result_type: NnMemoryType, kh: SSAValue, kw: SSAValue, sh: SSAValue, sw: SSAValue, dh: SSAValue, dw: SSAValue, ph: SSAValue, pw: SSAValue, pl: SSAValue, pr: SSAValue, space: NnMemorySpaceAttr)`
- `class NnMatmulOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

使用示例:
- from kernel_gen.dialect.nn import NnMatmulOp

关联文件:
- spec: spec/dialect/nn.md
- test: test/dialect/nn/test_operation_structured.py
- 功能实现: kernel_gen/dialect/nn/operation/structured.py
"""

from __future__ import annotations

from collections.abc import Sequence

from kernel_gen.dialect.nn.attr.space_attr import NnMemorySpaceAttr
from kernel_gen.dialect.nn.common import (
    build_contiguous_stride,
    is_int_or_symbol_type,
    raise_verify_error,
    static_int_from_operand,
    verify_memory_type,
)
from kernel_gen.dialect.nn.type.memory_type import NnMemoryType
from xdsl.ir import Attribute, Operation, SSAValue
from xdsl.irdl import IRDLOperation, attr_def, irdl_op_definition, operand_def, result_def

def _is_symbol_expr_attr(attr: Attribute) -> bool:
    """判断属性是否是公开 SymbolExprAttr。

    功能说明:
    - 通过延迟导入的公开 class 判断 memory shape/stride 条目。

    使用示例:
    - _is_symbol_expr_attr(SymbolExprAttr.from_expr("N"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/test_operation_structured.py
    - 功能实现: kernel_gen/dialect/nn/operation/structured.py
    """

    from kernel_gen.dialect.symbol import SymbolExprAttr

    return isinstance(attr, SymbolExprAttr)


def _dim_expr_text(dim: Attribute) -> str:
    """读取 SymbolExprAttr 的 canonical 表达式文本。

    功能说明:
    - 用于结构化 op 的静态 shape 校验。

    使用示例:
    - _dim_expr_text(SymbolExprAttr.from_expr("4"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/test_operation_structured.py
    - 功能实现: kernel_gen/dialect/nn/operation/structured.py
    """

    if not _is_symbol_expr_attr(dim):
        raise_verify_error("dimension entries must be SymbolExprAttr")
    dim.verify()
    return dim.expr.data


def _static_int_from_expr_text(expr: str) -> int | None:
    """尝试从规范表达式文本提取静态整数。

    功能说明:
    - 仅识别十进制整数字面量，动态表达式返回 None。

    使用示例:
    - _static_int_from_expr_text("4")

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    signless = expr[1:] if expr.startswith("-") else expr
    if signless.isdecimal():
        return int(expr)
    return None

def _static_int_from_dim(dim: Attribute) -> int | None:
    """尝试从 SymbolExprAttr 维度提取静态整数。

    功能说明:
    - 对 `#symbol.expr<4>` 返回 4；动态维度返回 None。

    使用示例:
    - _static_int_from_dim(SymbolExprAttr.from_expr("4"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    return _static_int_from_expr_text(_dim_expr_text(dim))

def _collect_int_dims(dims: Sequence[Attribute]) -> list[int] | None:
    """提取维度中的整数值列表。


    功能说明:
    - 仅当所有维度均为静态整数 SymbolExprAttr 时返回整数列表。
    - 任何动态 SymbolExprAttr 维度返回 None，表示无法进行数值合同校验。

    使用示例:
    - _collect_int_dims([SymbolExprAttr.from_expr("1"), SymbolExprAttr.from_expr("2")])

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    values: list[int] = []
    for dim in dims:
        value = _static_int_from_dim(dim)
        if value is None:
            return None
        values.append(value)
    return values

def _verify_img2col_param_operands(
    operands: Sequence[SSAValue],
    *,
    allow_zero: bool,
    type_error_phrase: str,
    value_error_phrase: str,
) -> list[int | None]:
    """校验 img2col 参数 operand 类型并提取静态值。


    功能说明:
    - 要求每个 operand 为 IntegerType 或 symbol.int。
    - 若可解析出静态整数值，则校验正数/非负数约束。
    - 解析失败则返回 None，供上层决定是否跳过形状合同校验。

    使用示例:
    - kw, sw = _verify_img2col_param_operands([op.kw, op.sw], allow_zero=False, type_error_phrase="kw-sw-must-be-int-or-symbol", value_error_phrase="kw-sw-must-be-positive")

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    values: list[int | None] = []
    for operand in operands:
        if not is_int_or_symbol_type(operand.type):
            raise_verify_error(type_error_phrase)
        static_value = static_int_from_operand(operand)
        if static_value is not None:
            if allow_zero:
                if static_value < 0:
                    raise_verify_error(value_error_phrase)
            elif static_value <= 0:
                raise_verify_error(value_error_phrase)
        values.append(static_value)
    return values

def _verify_matmul_shape(
    lhs_shape: Sequence[Attribute],
    rhs_shape: Sequence[Attribute],
    result_shape: Sequence[Attribute],
) -> None:
    """校验 matmul 的形状约束。


    功能说明:
    - 校验 matmul 的 rank=2 以及 contracting/result 维度约束。

    使用示例:
    - _verify_matmul_shape(lhs.shape.data, rhs.shape.data, result.shape.data)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    if len(lhs_shape) != 2 or len(rhs_shape) != 2 or len(result_shape) != 2:
        raise_verify_error("nn.matmul requires rank-2 memory types")

    if lhs_shape[1] != rhs_shape[0]:
        raise_verify_error("nn.matmul contracting dimensions must match")

    if result_shape[0] != lhs_shape[0] or result_shape[1] != rhs_shape[1]:
        raise_verify_error("nn.matmul result shape must match lhs/rhs")

def _img2col_output_dim(
    input_dim: int,
    kernel: int,
    stride: int,
    dilation: int,
    pad_before: int,
    pad_after: int,
) -> int:
    """计算 img2col 输出维度。


    功能说明:
    - 复用卷积输出维度公式并返回整数结果。

    使用示例:
    - _img2col_output_dim(8, 3, 1, 1, 1, 1)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    numerator = input_dim + pad_before + pad_after - dilation * (kernel - 1) - 1
    return numerator // stride + 1

@irdl_op_definition
class NnImg2col1dOp(IRDLOperation):
    """nn.img2col1d。


    功能说明:
    - 定义一维 img2col 方言 op 与 verifier 约束。

    使用示例:
    - NnImg2col1dOp(inp, result_type, kw_value, sw_value, dw_value, pl_value, pr_value, space=NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    name = "nn.img2col1d"

    input = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    kw = operand_def(Attribute)
    sw = operand_def(Attribute)
    dw = operand_def(Attribute)
    pl = operand_def(Attribute)
    pr = operand_def(Attribute)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        result_type: NnMemoryType,
        kw: SSAValue | Operation,
        sw: SSAValue | Operation,
        dw: SSAValue | Operation,
        pl: SSAValue | Operation,
        pr: SSAValue | Operation,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 img2col1d op。


        功能说明:
        - 绑定输入 operand、结果类型、窗口参数 operand 与 space 属性。

        使用示例:
        - NnImg2col1dOp(inp, result_type, kw_value, sw_value, dw_value, pl_value, pr_value, space=NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        super().__init__(
            operands=[input_value, kw, sw, dw, pl, pr],
            result_types=[result_type],
            attributes={"space": space},
        )

    def verify_(self) -> None:
        """校验 nn.img2col1d。


        功能说明:
        - 校验 operand rank、窗口参数 operand 合法性、result rank/type/space 与合同约束。

        使用示例:
        - NnImg2col1dOp(...).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        input_type = self.input.type
        result_type = self.result.type
        if not isinstance(input_type, NnMemoryType):
            raise_verify_error("operand-must-be-rank-3-nn-memory")
        if not isinstance(result_type, NnMemoryType):
            raise_verify_error("result-rank-must-be-4")
        input_type.verify()
        result_type.verify()

        if len(input_type.shape.data) != 3:
            raise_verify_error("operand-must-be-rank-3-nn-memory")
        if len(result_type.shape.data) != 4:
            raise_verify_error("result-rank-must-be-4")

        kw_value, sw_value, dw_value = _verify_img2col_param_operands(
            [self.kw, self.sw, self.dw],
            allow_zero=False,
            type_error_phrase="kw-sw-dw-must-be-int-or-symbol",
            value_error_phrase="kw-sw-dw-must-be-positive",
        )
        pl_value, pr_value = _verify_img2col_param_operands(
            [self.pl, self.pr],
            allow_zero=True,
            type_error_phrase="pl-pr-must-be-int-or-symbol",
            value_error_phrase="pl-pr-must-be-non-negative",
        )

        self.space.verify()
        if input_type.space.space.data != self.space.space.data:
            raise_verify_error("result-space-matches-input")
        if result_type.space.space.data != input_type.space.space.data:
            raise_verify_error("result-space-matches-input")
        if result_type.element_type != input_type.element_type:
            raise_verify_error("result-element-type-matches-input")

        input_dims = _collect_int_dims(input_type.shape.data)
        if input_dims is None:
            return
        if any(value is None for value in (kw_value, sw_value, dw_value, pl_value, pr_value)):
            return

        n_dim, c_dim, w_dim = input_dims
        w_out = _img2col_output_dim(w_dim, kw_value, sw_value, dw_value, pl_value, pr_value)
        if w_out <= 0:
            raise_verify_error("result-shape-stride-must-match-img2col1d-contract")

        expected_shape = [n_dim, c_dim, kw_value, w_out]
        for actual_dim, expected_dim in zip(result_type.shape.data, expected_shape, strict=True):
            if _static_int_from_dim(actual_dim) != expected_dim:
                raise_verify_error("result-shape-stride-must-match-img2col1d-contract")

        result_strides = _collect_int_dims(result_type.stride.data)
        if result_strides is None:
            raise_verify_error("result-shape-stride-must-match-img2col1d-contract")
        expected_stride = build_contiguous_stride(expected_shape)
        if result_strides != expected_stride:
            raise_verify_error("result-shape-stride-must-match-img2col1d-contract")

@irdl_op_definition
class NnImg2col2dOp(IRDLOperation):
    """nn.img2col2d。


    功能说明:
    - 定义二维 img2col 方言 op 与 verifier 约束。

    使用示例:
    - NnImg2col2dOp(inp, result_type, kh_value, kw_value, sh_value, sw_value, dh_value, dw_value, ph_value, pw_value, pl_value, pr_value, space=NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    name = "nn.img2col2d"

    input = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    kh = operand_def(Attribute)
    kw = operand_def(Attribute)
    sh = operand_def(Attribute)
    sw = operand_def(Attribute)
    dh = operand_def(Attribute)
    dw = operand_def(Attribute)
    ph = operand_def(Attribute)
    pw = operand_def(Attribute)
    pl = operand_def(Attribute)
    pr = operand_def(Attribute)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        result_type: NnMemoryType,
        kh: SSAValue | Operation,
        kw: SSAValue | Operation,
        sh: SSAValue | Operation,
        sw: SSAValue | Operation,
        dh: SSAValue | Operation,
        dw: SSAValue | Operation,
        ph: SSAValue | Operation,
        pw: SSAValue | Operation,
        pl: SSAValue | Operation,
        pr: SSAValue | Operation,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 img2col2d op。


        功能说明:
        - 绑定输入 operand、结果类型、窗口参数 operand 与 space 属性。

        使用示例:
        - NnImg2col2dOp(inp, result_type, kh_value, kw_value, sh_value, sw_value, dh_value, dw_value, ph_value, pw_value, pl_value, pr_value, space=NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        super().__init__(
            operands=[input_value, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr],
            result_types=[result_type],
            attributes={"space": space},
        )

    def verify_(self) -> None:
        """校验 nn.img2col2d。


        功能说明:
        - 校验 operand rank、窗口参数 operand 合法性、result rank/type/space 与合同约束。

        使用示例:
        - NnImg2col2dOp(...).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        input_type = self.input.type
        result_type = self.result.type
        if not isinstance(input_type, NnMemoryType):
            raise_verify_error("operand-must-be-rank-4-nn-memory")
        if not isinstance(result_type, NnMemoryType):
            raise_verify_error("result-rank-must-be-6")
        input_type.verify()
        result_type.verify()

        if len(input_type.shape.data) != 4:
            raise_verify_error("operand-must-be-rank-4-nn-memory")
        if len(result_type.shape.data) != 6:
            raise_verify_error("result-rank-must-be-6")

        kh_value, kw_value, sh_value, sw_value, dh_value, dw_value = _verify_img2col_param_operands(
            [self.kh, self.kw, self.sh, self.sw, self.dh, self.dw],
            allow_zero=False,
            type_error_phrase="kh-kw-sh-sw-dh-dw-must-be-int-or-symbol",
            value_error_phrase="kh-kw-sh-sw-dh-dw-must-be-positive",
        )
        ph_value, pw_value, pl_value, pr_value = _verify_img2col_param_operands(
            [self.ph, self.pw, self.pl, self.pr],
            allow_zero=True,
            type_error_phrase="ph-pw-pl-pr-must-be-int-or-symbol",
            value_error_phrase="ph-pw-pl-pr-must-be-non-negative",
        )

        self.space.verify()
        if input_type.space.space.data != self.space.space.data:
            raise_verify_error("result-space-matches-input")
        if result_type.space.space.data != input_type.space.space.data:
            raise_verify_error("result-space-matches-input")
        if result_type.element_type != input_type.element_type:
            raise_verify_error("result-element-type-matches-input")

        input_dims = _collect_int_dims(input_type.shape.data)
        if input_dims is None:
            return
        if any(
            value is None
            for value in (
                kh_value,
                kw_value,
                sh_value,
                sw_value,
                dh_value,
                dw_value,
                ph_value,
                pw_value,
                pl_value,
                pr_value,
            )
        ):
            return

        n_dim, c_dim, h_dim, w_dim = input_dims
        h_out = _img2col_output_dim(h_dim, kh_value, sh_value, dh_value, ph_value, pw_value)
        w_out = _img2col_output_dim(w_dim, kw_value, sw_value, dw_value, pl_value, pr_value)
        if h_out <= 0:
            raise_verify_error("result-shape-stride-must-match-img2col2d-contract")
        if w_out <= 0:
            raise_verify_error("result-shape-stride-must-match-img2col2d-contract")

        expected_shape = [n_dim, c_dim, kh_value, kw_value, h_out, w_out]
        for actual_dim, expected_dim in zip(result_type.shape.data, expected_shape, strict=True):
            if _static_int_from_dim(actual_dim) != expected_dim:
                raise_verify_error("result-shape-stride-must-match-img2col2d-contract")

        result_strides = _collect_int_dims(result_type.stride.data)
        if result_strides is None:
            raise_verify_error("result-shape-stride-must-match-img2col2d-contract")
        expected_stride = build_contiguous_stride(expected_shape)
        if result_strides != expected_stride:
            raise_verify_error("result-shape-stride-must-match-img2col2d-contract")

@irdl_op_definition
class NnMatmulOp(IRDLOperation):
    """nn.matmul。


    功能说明:
    - 定义 nn.matmul 方言 op 与 verifier 约束。

    使用示例:
    - NnMatmulOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    name = "nn.matmul"

    lhs = operand_def(NnMemoryType)
    rhs = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 matmul op。


        功能说明:
        - 构造 nn.matmul op 并绑定 operands/attributes。

        使用示例:
        - NnMatmulOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        super().__init__(
            operands=[lhs, rhs],
            result_types=[result_type],
            attributes={"space": space},
        )

    def verify_(self) -> None:
        """校验 nn.matmul 的 shape、space 与 dtype 合同。

        功能说明:
        - 校验 lhs/rhs/result 均为 `NnMemoryType` 且使用一致 memory space。
        - 校验 matmul 维度关系和 operand/result element_type 一致。

        使用示例:
        - NnMatmulOp(lhs, rhs, result_type, space).verify_()
        """
        lhs_type = verify_memory_type(self.lhs.type, "lhs")
        rhs_type = verify_memory_type(self.rhs.type, "rhs")
        result_type = verify_memory_type(self.result.type, "result")

        self.space.verify()
        if lhs_type.space.space.data != rhs_type.space.space.data:
            raise_verify_error("nn.matmul operands must use the same space")
        if lhs_type.space.space.data != self.space.space.data:
            raise_verify_error("nn.matmul attribute space must match operand space")
        if result_type.space.space.data != self.space.space.data:
            raise_verify_error("nn.matmul attribute space must match result space")

        _verify_matmul_shape(lhs_type.shape.data, rhs_type.shape.data, result_type.shape.data)

        if lhs_type.element_type != rhs_type.element_type or lhs_type.element_type != result_type.element_type:
            raise_verify_error("nn.matmul operand/result element_type must match")

__all__ = ["NnImg2col1dOp", "NnImg2col2dOp", "NnMatmulOp"]
