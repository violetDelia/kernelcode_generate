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

class _KernelBinaryMemoryEffect(MemoryEffect):
    """二元 kernel op 的 out 写与 lhs/rhs 读 effect trait。"""

    @classmethod
    def get_effects(cls, op: Operation) -> set[EffectInstance]:
        """返回二元 kernel op 的 MemoryEffect 集合。


        功能说明:
        - 使用 IRDL 命名字段绑定 effect value，避免构造函数参数顺序变化导致读写误绑。
        - `out` 产生 WRITE effect，`lhs/rhs` 产生 READ effect。

        使用示例:
        - effects = _KernelBinaryMemoryEffect.get_effects(op)

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        return {
            EffectInstance(MemoryEffectKind.WRITE, SSAValue.get(op.out)),  # type: ignore[attr-defined]
            EffectInstance(MemoryEffectKind.READ, SSAValue.get(op.lhs)),  # type: ignore[attr-defined]
            EffectInstance(MemoryEffectKind.READ, SSAValue.get(op.rhs)),  # type: ignore[attr-defined]
        }

def _normalize_kind_attr(
    kind: str | StringAttr,
    *,
    op_name: str,
    field_name: str,
    allowed: set[str],
) -> StringAttr:
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

    if isinstance(kind, StringAttr):
        kind_attr = kind
    elif isinstance(kind, str):
        kind_attr = StringAttr(kind)
    else:
        raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{op_name} {field_name} must be string",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )
    if kind_attr.data not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{op_name} {field_name} must be one of [{allowed_text}]",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )
    return kind_attr

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

        lhs_type = verify_memory_type(self.lhs.type, "lhs", scene=_ERROR_SCENE)
        rhs_type = verify_memory_type(self.rhs.type, "rhs", scene=_ERROR_SCENE)
        out_type = verify_memory_type(self.out.type, "out", scene=_ERROR_SCENE)
        _verify_same_layout([lhs_type, rhs_type, out_type], self.space)
        kind_value = _normalize_kind_attr(
            self.kind, op_name=self.name, field_name="kind", allowed=_BINARY_ELEWISE_KINDS
        ).data
        if kind_value in _BINARY_ELEWISE_COMPARE_KINDS:
            if not out_type.element_type == i1:
                raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
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
