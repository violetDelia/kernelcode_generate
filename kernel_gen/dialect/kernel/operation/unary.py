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
from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE, ErrorKind, ErrorModule, kernel_code_error
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

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr, SymbolValueType

# Localized helpers from retired package-internal modules.

_ERROR_SCENE = "dialect.kernel verifier"

class _KernelUnaryMemoryEffect(MemoryEffect):
    """一输入一输出 kernel op 的 out 写与 input 读 effect trait。"""

    @classmethod
    def get_effects(cls, op: Operation) -> set[EffectInstance]:
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
            EffectInstance(MemoryEffectKind.WRITE, SSAValue.get(op.out)),  # type: ignore[attr-defined]
            EffectInstance(MemoryEffectKind.READ, SSAValue.get(op.input)),  # type: ignore[attr-defined]
        }

def _verify_same_layout(types: Iterable[NnMemoryType], op_space: NnMemorySpaceAttr) -> None:
    """校验多 operand 的 shape/stride/space 一致性。


    功能说明:
    - 要求 shape/stride/space 全部一致。
    - op space 属性必须匹配 operand space。

    使用示例:
    - _verify_same_layout([lhs_type, rhs_type, out_type], space)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    types = list(types)
    if not types:
        return
    op_space.verify()
    base = types[0]
    for other in types[1:]:
        if other.space.space.data != base.space.space.data:
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel op operands must use the same space",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if other.shape != base.shape:
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel op shape must match across operands",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if other.stride != base.stride:
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel op stride must match across operands",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
    if base.space.space.data != op_space.space.data:
        raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected="kernel op attribute space must match operand space",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )

def _verify_element_type_match(types: Iterable[NnMemoryType], message: str) -> None:
    """校验 element_type 一致性。


    功能说明:
    - 要求所有类型的 element_type 相同。

    使用示例:
    - _verify_element_type_match([lhs_type, rhs_type, out_type], "...")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    types = list(types)
    if not types:
        return
    base_type = types[0].element_type
    for other in types[1:]:
        if other.element_type != base_type:
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected=message,
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
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

        input_type = verify_memory_type(self.input.type, "input", scene=_ERROR_SCENE)
        out_type = verify_memory_type(self.out.type, "out", scene=_ERROR_SCENE)
        _verify_same_layout([input_type, out_type], self.space)
        _verify_element_type_match(
            [input_type, out_type],
            "kernel.exp element_type must match across operands",
        )
        if not isinstance(input_type.element_type, (BFloat16Type, Float16Type, Float32Type, Float64Type)):
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
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
