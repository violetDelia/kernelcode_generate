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
    _KernelUnaryMemoryEffect,
    _build_reduce_result_shape,
    _normalize_bool_attr,
    _normalize_i64_attr,
    _normalize_kind_attr,
    _verify_bool_attr,
    _verify_i64_attr_range,
    _verify_memory_type,
    _verify_reduce_result_shape,
)

_KERNEL_ERROR_SCENE = "dialect.kernel verifier"
_REDUCE_KINDS = {"sum", "min", "max"}

@irdl_op_definition
class KernelReduceOp(IRDLOperation):
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

    name = "kernel.reduce"
    traits = traits_def(_KernelUnaryMemoryEffect())

    out = operand_def(NnMemoryType)
    input = operand_def(NnMemoryType)
    axis = attr_def(IntegerAttr)
    keepdim = attr_def(IntegerAttr)
    kind = attr_def(StringAttr)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        out: SSAValue | Operation,
        input_value: SSAValue | Operation,
        *,
        kind: str | StringAttr,
        axis: int | IntegerAttr | IntAttr,
        keepdim: bool | int | IntegerAttr | IntAttr,
        space: NnMemorySpaceAttr,
    ) -> None:
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

        axis_attr = _normalize_i64_attr(axis, "axis")
        keepdim_attr = _normalize_bool_attr(keepdim, "keepdim")
        kind_attr = _normalize_kind_attr(
            kind, op_name=self.name, field_name="kind", allowed=_REDUCE_KINDS
        )
        super().__init__(
            operands=[out, input_value],
            attributes={
                "axis": axis_attr,
                "keepdim": keepdim_attr,
                "kind": kind_attr,
                "space": space,
            },
        )

    def verify_(self) -> None:
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

        input_type = _verify_memory_type(self.input.type, "input")
        out_type = _verify_memory_type(self.out.type, "out")
        _normalize_kind_attr(
            self.kind, op_name=self.name, field_name="kind", allowed=_REDUCE_KINDS
        )
        axis_value = _verify_i64_attr_range(
            self.axis, "axis", min_value=0, max_value=len(input_type.shape.data) - 1
        )
        keepdim_value = _verify_bool_attr(self.keepdim, "keepdim")
        if input_type.element_type != out_type.element_type:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_KERNEL_ERROR_SCENE,
                    expected="kernel.reduce element_type must match across operands",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        self.space.verify()
        if input_type.space.space.data != out_type.space.space.data:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_KERNEL_ERROR_SCENE,
                    expected="kernel.reduce out space must match input",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if input_type.space.space.data != self.space.space.data:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_KERNEL_ERROR_SCENE,
                    expected="kernel.reduce attribute space must match input",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        expected_shape = _build_reduce_result_shape(
            list(input_type.shape.data), axis_value, keepdim_value
        )
        _verify_reduce_result_shape(out_type, expected_shape, "kernel.reduce")


@irdl_op_definition
class KernelReduceMinOp(IRDLOperation):
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

    name = "kernel.reduce_min"
    traits = traits_def(_KernelUnaryMemoryEffect())

    out = operand_def(NnMemoryType)
    input = operand_def(NnMemoryType)
    axis = attr_def(IntegerAttr)
    keepdim = attr_def(IntegerAttr)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        out: SSAValue | Operation,
        input_value: SSAValue | Operation,
        axis: int | IntegerAttr | IntAttr,
        keepdim: bool | int | IntegerAttr | IntAttr,
        space: NnMemorySpaceAttr,
    ) -> None:
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

        axis_attr = _normalize_i64_attr(axis, "axis")
        keepdim_attr = _normalize_bool_attr(keepdim, "keepdim")
        super().__init__(
            operands=[out, input_value],
            attributes={"axis": axis_attr, "keepdim": keepdim_attr, "space": space},
        )

    def verify_(self) -> None:
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

        input_type = _verify_memory_type(self.input.type, "input")
        out_type = _verify_memory_type(self.out.type, "out")
        axis_value = _verify_i64_attr_range(
            self.axis, "axis", min_value=0, max_value=len(input_type.shape.data) - 1
        )
        keepdim_value = _verify_bool_attr(self.keepdim, "keepdim")
        if input_type.element_type != out_type.element_type:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_KERNEL_ERROR_SCENE,
                    expected="kernel.reduce_min element_type must match across operands",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        self.space.verify()
        if input_type.space.space.data != out_type.space.space.data:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_KERNEL_ERROR_SCENE,
                    expected="kernel.reduce_min out space must match input",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if input_type.space.space.data != self.space.space.data:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_KERNEL_ERROR_SCENE,
                    expected="kernel.reduce_min attribute space must match input",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        expected_shape = _build_reduce_result_shape(
            list(input_type.shape.data), axis_value, keepdim_value
        )
        _verify_reduce_result_shape(out_type, expected_shape, "kernel.reduce_min")

__all__ = [
    "KernelReduceOp",
    "KernelReduceMinOp",
]
