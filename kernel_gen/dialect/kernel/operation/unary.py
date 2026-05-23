"""kernel unary operation.

功能说明:
- 定义 kernel.exp op。

API 列表:
- `class KernelExpOp(input_value: SSAValue | Operation, out: SSAValue | Operation, space: NnMemorySpaceAttr)`

使用示例:
- `from kernel_gen.dialect.kernel.operation import ...`

关联文件:
- spec: spec/dialect/kernel.md
- test: test/dialect/kernel/
- 功能实现: kernel_gen/dialect/kernel/operation/unary.py
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
    _verify_element_type_match,
    _verify_memory_type,
    _verify_same_layout,
)

_KERNEL_ERROR_SCENE = "dialect.kernel verifier"

@irdl_op_definition
class KernelExpOp(IRDLOperation):
    """kernel.exp。"""

    name = "kernel.exp"
    traits = traits_def(_KernelUnaryMemoryEffect())

    out = operand_def(NnMemoryType)
    input = operand_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        out: SSAValue | Operation,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 exp op。

        功能说明:
        - 按 out/input operand 顺序保存指数 op 输入输出和执行 space。

        使用示例:
        - KernelExpOp(input_value, out, space)
        """

        super().__init__(operands=[out, input_value], attributes={"space": space})

    def verify_(self) -> None:
        """校验 kernel.exp operand 与输出约束。

        功能说明:
        - 要求 input/out layout 与 dtype 一致，且 element type 为浮点类型。

        使用示例:
        - KernelExpOp(input_value, out, space).verify()
        """

        input_type = _verify_memory_type(self.input.type, "input")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([input_type, out_type], self.space)
        _verify_element_type_match(
            [input_type, out_type],
            "kernel.exp element_type must match across operands",
        )
        if not isinstance(input_type.element_type, (BFloat16Type, Float16Type, Float32Type, Float64Type)):
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_KERNEL_ERROR_SCENE,
                    expected="kernel.exp element_type must be float",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )

__all__ = [
    "KernelExpOp",
]
