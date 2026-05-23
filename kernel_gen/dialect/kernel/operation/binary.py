"""kernel binary operation.

功能说明:
- 定义 kernel.binary_elewise op。

API 列表:
- `class KernelBinaryElewiseOp(out: SSAValue | Operation, lhs: SSAValue | Operation, rhs: SSAValue | Operation, *, kind: str | StringAttr, space: NnMemorySpaceAttr)`

使用示例:
- `from kernel_gen.dialect.kernel.operation import ...`

关联文件:
- spec: spec/dialect/kernel.md
- test: test/dialect/kernel/
- 功能实现: kernel_gen/dialect/kernel/operation/binary.py
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
    _KernelBinaryMemoryEffect,
    _is_compare_output_element_type,
    _normalize_kind_attr,
    _verify_element_type_match,
    _verify_memory_type,
    _verify_same_layout,
)

_KERNEL_ERROR_SCENE = "dialect.kernel verifier"
_BINARY_ELEWISE_ARITH_KINDS = {"add", "sub", "mul", "div", "truediv"}
_BINARY_ELEWISE_COMPARE_KINDS = {"eq", "ne", "lt", "le", "gt", "ge"}
_BINARY_ELEWISE_KINDS = _BINARY_ELEWISE_ARITH_KINDS | _BINARY_ELEWISE_COMPARE_KINDS

@irdl_op_definition
class KernelBinaryElewiseOp(IRDLOperation):
    """kernel.binary_elewise。


    功能说明:
    - 定义统一的二元逐元素算术/比较 op。
    - 通过 kind 属性区分 add/sub/eq 等语义。

    使用示例:
    - KernelBinaryElewiseOp(out, lhs, rhs, kind="add", space=NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    name = "kernel.binary_elewise"
    traits = traits_def(_KernelBinaryMemoryEffect())

    out = operand_def(NnMemoryType)
    lhs = operand_def(NnMemoryType)
    rhs = operand_def(NnMemoryType)
    kind = attr_def(StringAttr)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        out: SSAValue | Operation,
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        *,
        kind: str | StringAttr,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 kernel.binary_elewise op。


        功能说明:
        - 绑定输入、输出与 kind/space 属性。

        使用示例:
        - KernelBinaryElewiseOp(out, lhs, rhs, kind="add", space=NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        kind_attr = _normalize_kind_attr(
            kind, op_name=self.name, field_name="kind", allowed=_BINARY_ELEWISE_KINDS
        )
        super().__init__(
            operands=[out, lhs, rhs],
            attributes={"kind": kind_attr, "space": space},
        )

    def verify_(self) -> None:
        """校验 kernel.binary_elewise 的 verifier 合同。


        功能说明:
        - 校验 layout/space 约束。
        - 根据 kind 决定 element_type 校验规则。

        使用示例:
        - KernelBinaryElewiseOp(out, lhs, rhs, kind="add", space=space).verify_()

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([lhs_type, rhs_type, out_type], self.space)
        kind_value = _normalize_kind_attr(
            self.kind, op_name=self.name, field_name="kind", allowed=_BINARY_ELEWISE_KINDS
        ).data
        if kind_value in _BINARY_ELEWISE_COMPARE_KINDS:
            if not _is_compare_output_element_type(out_type.element_type):
                raise VerifyException(
                    ERROR_TEMPLATE.format(
                        scene=_KERNEL_ERROR_SCENE,
                        expected="kernel.binary_elewise compare output element_type must be i1",
                        actual=ERROR_ACTUAL,
                        action=ERROR_ACTION,
                    )
                )
            return
        _verify_element_type_match(
            [lhs_type, rhs_type, out_type],
            "kernel.binary_elewise element_type must match across operands",
        )

__all__ = [
    "KernelBinaryElewiseOp",
]
