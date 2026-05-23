"""kernel structured operations.

功能说明:
- 定义 kernel.matmul、kernel.img2col1d 与 kernel.img2col2d op。

API 列表:
- `class KernelMatmulOp(out: SSAValue | Operation, lhs: SSAValue | Operation, rhs: SSAValue | Operation, space: NnMemorySpaceAttr)`
- `class KernelImg2col1dOp(...)`
- `class KernelImg2col2dOp(...)`

使用示例:
- `from kernel_gen.dialect.kernel.operation import ...`

关联文件:
- spec: spec/dialect/kernel.md
- test: test/dialect/kernel/
- 功能实现: kernel_gen/dialect/kernel/operation/structured.py
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from kernel_gen.core.contracts import build_contiguous_stride, verify_i64_attr_range, verify_memory_type
from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE
from xdsl.dialects.arith import ConstantOp
from xdsl.dialects.builtin import (
    BFloat16Type,
    Float16Type,
    Float32Type,
    Float64Type,
    IntAttr,
    IntegerAttr,
    IntegerType,
    StringAttr,
    i1,
)
from xdsl.ir import Attribute, Dialect, Operation, SSAValue
from xdsl.irdl import IRDLOperation, attr_def, irdl_op_definition, operand_def, traits_def
from xdsl.traits import EffectInstance, MemoryEffect, MemoryEffectKind
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr, SymbolValueType

from ..common import (
    _BaseKernelBinaryOp,
    _KernelBinaryMemoryEffect,
    _KernelUnaryMemoryEffect,
    _build_contiguous_stride,
    _collect_int_dims,
    _img2col_output_dim,
    _static_int_from_dim,
    _verify_element_type_match,
    _verify_img2col_param_operands,
    _verify_matmul_shape,
    _verify_memory_type,
)

_ERROR_SCENE = "dialect.kernel verifier"

@irdl_op_definition
class KernelMatmulOp(_BaseKernelBinaryOp):
    """kernel.matmul。


    功能说明:
    - 结构化矩阵乘 op，输入输出均为 nn.memory。
    - verifier 强制二维输入、shape 机械一致及 element_type 对齐。
    - 允许 out/lhs/rhs 使用不同合法 memory space，`space` attribute 只校验自身合法性。

    使用示例:
    - KernelMatmulOp(out, lhs, rhs, _make_space("global"))

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    name = "kernel.matmul"
    traits = traits_def(_KernelBinaryMemoryEffect())

    def verify_(self) -> None:
        """校验 kernel.matmul operand 与输出约束。

        功能说明:
        - 校验矩阵乘法 shape 合同、element type 一致性与 space 属性合法性。

        使用示例:
        - KernelMatmulOp(out, lhs, rhs, space).verify()
        """

        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        self.space.verify()
        _verify_matmul_shape(lhs_type.shape.data, rhs_type.shape.data, out_type.shape.data)
        _verify_element_type_match(
            [lhs_type, rhs_type, out_type],
            "kernel.matmul element_type must match across operands",
        )


@irdl_op_definition
class KernelImg2col1dOp(IRDLOperation):
    """kernel.img2col1d。


    功能说明:
    - 定义一维 img2col 的 kernel 目标 op。
    - verifier 校验输入输出 rank、窗口参数 operand、结构化结果 shape/stride 与空间一致性。

    使用示例:
    - KernelImg2col1dOp(inp, out, k_value, s_value, d_value, p_left_value, p_right_value, space=_make_space("global"))

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    name = "kernel.img2col1d"
    traits = traits_def(_KernelUnaryMemoryEffect())

    out = operand_def(NnMemoryType)
    input = operand_def(NnMemoryType)
    k = operand_def(Attribute)
    s = operand_def(Attribute)
    d = operand_def(Attribute)
    p_left = operand_def(Attribute)
    p_right = operand_def(Attribute)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        out: SSAValue | Operation,
        input_value: SSAValue | Operation,
        k: SSAValue | Operation,
        s: SSAValue | Operation,
        d: SSAValue | Operation,
        p_left: SSAValue | Operation,
        p_right: SSAValue | Operation,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 img2col1d op。


        功能说明:
        - 绑定输入/输出 operand 与窗口参数 operand。

        使用示例:
        - KernelImg2col1dOp(inp, out, k_value, s_value, d_value, p_left_value, p_right_value, _make_space("global"))

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        super().__init__(
            operands=[out, input_value, k, s, d, p_left, p_right],
            attributes={"space": space},
        )

    def verify_(self) -> None:
        """校验 kernel.img2col1d 合同。


        功能说明:
        - 校验输入输出 rank、元素类型、空间、窗口参数 operand 与结构化结果布局。

        使用示例:
        - KernelImg2col1dOp(...).verify_()

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        input_type = _verify_memory_type(self.input.type, "input")
        out_type = _verify_memory_type(self.out.type, "out")
        self.space.verify()

        if len(input_type.shape.data) != 3:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col1d requires rank-3 input",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if len(out_type.shape.data) != 4:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col1d requires rank-4 result",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if input_type.space.space.data != self.space.space.data:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col1d attribute space must match input space",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if out_type.space.space.data != self.space.space.data:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col1d attribute space must match result space",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if out_type.element_type != input_type.element_type:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col1d result element_type must match input",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )

        k_value, s_value, d_value = _verify_img2col_param_operands(
            [self.k, self.s, self.d],
            allow_zero=False,
            type_error_phrase="kernel.img2col1d k/s/d must be integer or symbol",
            value_error_phrase="kernel.img2col1d k/s/d must be positive",
        )
        p_left_value, p_right_value = _verify_img2col_param_operands(
            [self.p_left, self.p_right],
            allow_zero=True,
            type_error_phrase="kernel.img2col1d p_left/p_right must be integer or symbol",
            value_error_phrase="kernel.img2col1d p_left/p_right must be non-negative",
        )

        input_shape = list(input_type.shape.data)
        out_shape = list(out_type.shape.data)
        if k_value is not None:
            if _static_int_from_dim(out_shape[2]) != k_value:
                raise VerifyException(
                    ERROR_TEMPLATE.format(
                        scene=_ERROR_SCENE,
                        expected="kernel.img2col1d result shape/stride must match img2col1d contract",
                        actual=ERROR_ACTUAL,
                        action=ERROR_ACTION,
                    )
                )

        input_dims = _collect_int_dims(input_shape)
        input_strides = _collect_int_dims(input_type.stride.data)
        if input_dims is not None and input_strides is not None:
            if input_strides != _build_contiguous_stride(input_dims):
                raise VerifyException(
                    ERROR_TEMPLATE.format(
                        scene=_ERROR_SCENE,
                        expected="kernel.img2col1d input layout must be contiguous",
                        actual=ERROR_ACTUAL,
                        action=ERROR_ACTION,
                    )
                )

        out_dims = _collect_int_dims(out_shape)
        out_strides = _collect_int_dims(out_type.stride.data)
        if input_dims is None or out_dims is None or out_strides is None:
            return
        if any(value is None for value in (k_value, s_value, d_value, p_left_value, p_right_value)):
            return

        n_dim, c_dim, w_dim = input_dims
        w_out_dim = _img2col_output_dim(w_dim, k_value, s_value, d_value, p_left_value, p_right_value)
        expected_shape = [n_dim, c_dim, k_value, w_out_dim]
        expected_stride = _build_contiguous_stride(expected_shape)
        if w_out_dim < 1 or out_dims != expected_shape or out_strides != expected_stride:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col1d result shape/stride must match img2col1d contract",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )


@irdl_op_definition
class KernelImg2col2dOp(IRDLOperation):
    """kernel.img2col2d。


    功能说明:
    - 定义二维 img2col 的 kernel 目标 op。
    - verifier 校验输入输出 rank、窗口参数 operand、结构化结果 shape/stride 与空间一致性。

    使用示例:
    - KernelImg2col2dOp(inp, out, kh_value, kw_value, sh_value, sw_value, dh_value, dw_value, ph_value, pw_value, pl_value, pr_value, space=_make_space("global"))

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    name = "kernel.img2col2d"
    traits = traits_def(_KernelUnaryMemoryEffect())

    out = operand_def(NnMemoryType)
    input = operand_def(NnMemoryType)
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
        out: SSAValue | Operation,
        input_value: SSAValue | Operation,
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
        - 绑定输入/输出 operand 与窗口参数 operand。

        使用示例:
        - KernelImg2col2dOp(inp, out, kh_value, kw_value, sh_value, sw_value, dh_value, dw_value, ph_value, pw_value, pl_value, pr_value, _make_space("global"))

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        super().__init__(
            operands=[out, input_value, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr],
            attributes={"space": space},
        )

    def verify_(self) -> None:
        """校验 kernel.img2col2d 合同。


        功能说明:
        - 校验输入输出 rank、元素类型、空间、窗口参数 operand 与结构化结果布局。

        使用示例:
        - KernelImg2col2dOp(...).verify_()

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        input_type = _verify_memory_type(self.input.type, "input")
        out_type = _verify_memory_type(self.out.type, "out")
        self.space.verify()

        if len(input_type.shape.data) != 4:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col2d requires rank-4 input",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if len(out_type.shape.data) != 6:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col2d requires rank-6 result",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if input_type.space.space.data != self.space.space.data:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col2d attribute space must match input space",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if out_type.space.space.data != self.space.space.data:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col2d attribute space must match result space",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if out_type.element_type != input_type.element_type:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col2d result element_type must match input",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )

        kh_value, kw_value, sh_value, sw_value, dh_value, dw_value = _verify_img2col_param_operands(
            [self.kh, self.kw, self.sh, self.sw, self.dh, self.dw],
            allow_zero=False,
            type_error_phrase="kernel.img2col2d kh/kw/sh/sw/dh/dw must be integer or symbol",
            value_error_phrase="kernel.img2col2d kh/kw/sh/sw/dh/dw must be positive",
        )
        ph_value, pw_value, pl_value, pr_value = _verify_img2col_param_operands(
            [self.ph, self.pw, self.pl, self.pr],
            allow_zero=True,
            type_error_phrase="kernel.img2col2d ph/pw/pl/pr must be integer or symbol",
            value_error_phrase="kernel.img2col2d ph/pw/pl/pr must be non-negative",
        )

        input_shape = list(input_type.shape.data)
        out_shape = list(out_type.shape.data)
        if kh_value is not None:
            if _static_int_from_dim(out_shape[2]) != kh_value:
                raise VerifyException(
                    ERROR_TEMPLATE.format(
                        scene=_ERROR_SCENE,
                        expected="kernel.img2col2d result shape/stride must match img2col2d contract",
                        actual=ERROR_ACTUAL,
                        action=ERROR_ACTION,
                    )
                )
        if kw_value is not None:
            if _static_int_from_dim(out_shape[3]) != kw_value:
                raise VerifyException(
                    ERROR_TEMPLATE.format(
                        scene=_ERROR_SCENE,
                        expected="kernel.img2col2d result shape/stride must match img2col2d contract",
                        actual=ERROR_ACTUAL,
                        action=ERROR_ACTION,
                    )
                )

        input_dims = _collect_int_dims(input_shape)
        input_strides = _collect_int_dims(input_type.stride.data)
        if input_dims is not None and input_strides is not None:
            if input_strides != _build_contiguous_stride(input_dims):
                raise VerifyException(
                    ERROR_TEMPLATE.format(
                        scene=_ERROR_SCENE,
                        expected="kernel.img2col2d input layout must be contiguous",
                        actual=ERROR_ACTUAL,
                        action=ERROR_ACTION,
                    )
                )

        out_dims = _collect_int_dims(out_shape)
        out_strides = _collect_int_dims(out_type.stride.data)
        if input_dims is None or out_dims is None or out_strides is None:
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
        oh_dim = _img2col_output_dim(h_dim, kh_value, sh_value, dh_value, ph_value, pw_value)
        ow_dim = _img2col_output_dim(w_dim, kw_value, sw_value, dw_value, pl_value, pr_value)
        expected_shape = [n_dim, c_dim, kh_value, kw_value, oh_dim, ow_dim]
        expected_stride = _build_contiguous_stride(expected_shape)
        if oh_dim < 1 or ow_dim < 1 or out_dims != expected_shape or out_strides != expected_stride:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col2d result shape/stride must match img2col2d contract",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )

__all__ = [
    "KernelMatmulOp",
    "KernelImg2col1dOp",
    "KernelImg2col2dOp",
]
