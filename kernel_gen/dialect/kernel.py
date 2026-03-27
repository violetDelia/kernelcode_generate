"""Kernel dialect definitions.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 定义 kernel dialect 的逐元素算术、比较、选择与类型转换 op。
- 复用 nn dialect 的 NnMemoryType 与 NnMemorySpaceAttr。
- 所有结果通过 outs(...) 写回，不产生 SSA result。

使用示例:
- from kernel_gen.dialect.kernel import Kernel, KernelAddOp

关联文件:
- spec: spec/dialect/kernel.md
- test: test/dialect/test_kernel_dialect.py
- 功能实现: kernel_gen/dialect/kernel.py
"""

from __future__ import annotations

from collections.abc import Iterable

from xdsl.dialects.builtin import Float16Type, Float32Type, Float64Type, IntegerType, i1
from xdsl.ir import Attribute, Dialect, Operation, SSAValue
from xdsl.irdl import IRDLOperation, attr_def, irdl_op_definition, operand_def
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType


def _verify_memory_type(value: Attribute, field_name: str) -> NnMemoryType:
    """校验并返回 nn.memory type。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 确认类型为 nn.memory 并触发类型校验。

    使用示例:
    - _verify_memory_type(op.lhs.type, "lhs")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    if not isinstance(value, NnMemoryType):
        raise VerifyException(f"{field_name} must be nn.memory")
    value.verify()
    return value


def _verify_same_layout(types: Iterable[NnMemoryType], op_space: NnMemorySpaceAttr) -> None:
    """校验多 operand 的 shape/stride/space 一致性。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 要求 shape/stride/space 全部一致。
    - op space 属性必须匹配 operand space。

    使用示例:
    - _verify_same_layout([lhs_type, rhs_type, out_type], space)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    types = list(types)
    if not types:
        return
    op_space.verify()
    base = types[0]
    for other in types[1:]:
        if other.space.space.data != base.space.space.data:
            raise VerifyException("kernel op operands must use the same space")
        if other.shape != base.shape:
            raise VerifyException("kernel op shape must match across operands")
        if other.stride != base.stride:
            raise VerifyException("kernel op stride must match across operands")
    if base.space.space.data != op_space.space.data:
        raise VerifyException("kernel op attribute space must match operand space")


def _verify_element_type_match(types: Iterable[NnMemoryType], message: str) -> None:
    """校验 element_type 一致性。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 要求所有类型的 element_type 相同。

    使用示例:
    - _verify_element_type_match([lhs_type, rhs_type, out_type], "...")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    types = list(types)
    if not types:
        return
    base_type = types[0].element_type
    for other in types[1:]:
        if other.element_type != base_type:
            raise VerifyException(message)


def _is_cast_element_type(value: Attribute) -> bool:
    """判断元素类型是否允许用于 kernel.cast。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持整数与浮点类型，但不允许 i1。

    使用示例:
    - _is_cast_element_type(i1)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    if isinstance(value, IntegerType):
        return value.width.data != 1
    return isinstance(value, (Float16Type, Float32Type, Float64Type))


class _BaseKernelBinaryOp(IRDLOperation):
    """kernel 二元 op 基类。"""

    lhs = operand_def(NnMemoryType)
    rhs = operand_def(NnMemoryType)
    out = operand_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        out: SSAValue | Operation,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化二元 op。"""

        super().__init__(operands=[lhs, rhs, out], attributes={"space": space})


@irdl_op_definition
class KernelAddOp(_BaseKernelBinaryOp):
    """kernel.add。"""

    name = "kernel.add"

    def verify_(self) -> None:
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([lhs_type, rhs_type, out_type], self.space)
        _verify_element_type_match(
            [lhs_type, rhs_type, out_type],
            "kernel arithmetic element_type must match across operands",
        )


@irdl_op_definition
class KernelSubOp(_BaseKernelBinaryOp):
    """kernel.sub。"""

    name = "kernel.sub"

    def verify_(self) -> None:
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([lhs_type, rhs_type, out_type], self.space)
        _verify_element_type_match(
            [lhs_type, rhs_type, out_type],
            "kernel arithmetic element_type must match across operands",
        )


@irdl_op_definition
class KernelMulOp(_BaseKernelBinaryOp):
    """kernel.mul。"""

    name = "kernel.mul"

    def verify_(self) -> None:
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([lhs_type, rhs_type, out_type], self.space)
        _verify_element_type_match(
            [lhs_type, rhs_type, out_type],
            "kernel arithmetic element_type must match across operands",
        )


@irdl_op_definition
class KernelDivOp(_BaseKernelBinaryOp):
    """kernel.div。"""

    name = "kernel.div"

    def verify_(self) -> None:
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([lhs_type, rhs_type, out_type], self.space)
        _verify_element_type_match(
            [lhs_type, rhs_type, out_type],
            "kernel arithmetic element_type must match across operands",
        )


@irdl_op_definition
class KernelEqOp(_BaseKernelBinaryOp):
    """kernel.eq。"""

    name = "kernel.eq"

    def verify_(self) -> None:
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([lhs_type, rhs_type, out_type], self.space)
        if out_type.element_type != i1:
            raise VerifyException("kernel compare output element_type must be i1")


@irdl_op_definition
class KernelNeOp(_BaseKernelBinaryOp):
    """kernel.ne。"""

    name = "kernel.ne"

    def verify_(self) -> None:
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([lhs_type, rhs_type, out_type], self.space)
        if out_type.element_type != i1:
            raise VerifyException("kernel compare output element_type must be i1")


@irdl_op_definition
class KernelLtOp(_BaseKernelBinaryOp):
    """kernel.lt。"""

    name = "kernel.lt"

    def verify_(self) -> None:
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([lhs_type, rhs_type, out_type], self.space)
        if out_type.element_type != i1:
            raise VerifyException("kernel compare output element_type must be i1")


@irdl_op_definition
class KernelLeOp(_BaseKernelBinaryOp):
    """kernel.le。"""

    name = "kernel.le"

    def verify_(self) -> None:
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([lhs_type, rhs_type, out_type], self.space)
        if out_type.element_type != i1:
            raise VerifyException("kernel compare output element_type must be i1")


@irdl_op_definition
class KernelGtOp(_BaseKernelBinaryOp):
    """kernel.gt。"""

    name = "kernel.gt"

    def verify_(self) -> None:
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([lhs_type, rhs_type, out_type], self.space)
        if out_type.element_type != i1:
            raise VerifyException("kernel compare output element_type must be i1")


@irdl_op_definition
class KernelGeOp(_BaseKernelBinaryOp):
    """kernel.ge。"""

    name = "kernel.ge"

    def verify_(self) -> None:
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([lhs_type, rhs_type, out_type], self.space)
        if out_type.element_type != i1:
            raise VerifyException("kernel compare output element_type must be i1")


@irdl_op_definition
class KernelSelectOp(IRDLOperation):
    """kernel.select。"""

    name = "kernel.select"

    cond = operand_def(NnMemoryType)
    lhs = operand_def(NnMemoryType)
    rhs = operand_def(NnMemoryType)
    out = operand_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        cond: SSAValue | Operation,
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        out: SSAValue | Operation,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 select op。"""

        super().__init__(operands=[cond, lhs, rhs, out], attributes={"space": space})

    def verify_(self) -> None:
        cond_type = _verify_memory_type(self.cond.type, "cond")
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        if cond_type.element_type != i1:
            raise VerifyException("kernel.select cond element_type must be i1")
        _verify_same_layout([cond_type, lhs_type, rhs_type, out_type], self.space)
        _verify_element_type_match(
            [lhs_type, rhs_type, out_type],
            "kernel.select operand element_type must match",
        )


@irdl_op_definition
class KernelCastOp(IRDLOperation):
    """kernel.cast。"""

    name = "kernel.cast"

    input = operand_def(NnMemoryType)
    out = operand_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        out: SSAValue | Operation,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 cast op。"""

        super().__init__(operands=[input_value, out], attributes={"space": space})

    def verify_(self) -> None:
        input_type = _verify_memory_type(self.input.type, "input")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([input_type, out_type], self.space)
        if not _is_cast_element_type(input_type.element_type) or not _is_cast_element_type(
            out_type.element_type
        ):
            raise VerifyException("kernel.cast element_type must be integer or float and not i1")


Kernel = Dialect(
    "kernel",
    [
        KernelAddOp,
        KernelSubOp,
        KernelMulOp,
        KernelDivOp,
        KernelEqOp,
        KernelNeOp,
        KernelLtOp,
        KernelLeOp,
        KernelGtOp,
        KernelGeOp,
        KernelSelectOp,
        KernelCastOp,
    ],
    [],
)

__all__ = [
    "Kernel",
    "KernelAddOp",
    "KernelSubOp",
    "KernelMulOp",
    "KernelDivOp",
    "KernelEqOp",
    "KernelNeOp",
    "KernelLtOp",
    "KernelLeOp",
    "KernelGtOp",
    "KernelGeOp",
    "KernelSelectOp",
    "KernelCastOp",
]
