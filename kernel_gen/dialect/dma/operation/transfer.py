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

from collections.abc import Sequence

from xdsl.dialects.builtin import ArrayAttr, IntAttr, IntegerType
from xdsl.ir import Attribute, Operation, SSAValue
from xdsl.irdl import (
    AttrSizedOperandSegments,
    IRDLOperation,
    attr_def,
    irdl_op_definition,
    operand_def,
    result_def,
    traits_def,
    var_operand_def,
)
from xdsl.traits import NoMemoryEffect
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType

from ..common import (
    verify_broadcast_compat,
    verify_memory_type,
    verify_transpose_layout,
    verify_transpose_perm,
)
from ..effect import DmaBroadcastMemoryEffect, DmaTargetSourceEffect

@irdl_op_definition
class DmaCopyOp(IRDLOperation):
    """dma.copy。"""

    name = "dma.copy"
    traits = traits_def(DmaTargetSourceEffect())

    target = operand_def(NnMemoryType)
    source = operand_def(NnMemoryType)

    def __init__(self, target: SSAValue | Operation, source: SSAValue | Operation) -> None:
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

        super().__init__(operands=[target, source])

    def verify_(self) -> None:
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

        source_type = verify_memory_type(self.source.type, "source")
        target_type = verify_memory_type(self.target.type, "target")
        if source_type.shape != target_type.shape:
            raise VerifyException("dma.copy source/target shape mismatch")
        if source_type.stride != target_type.stride:
            raise VerifyException("dma.copy source/target stride mismatch")
        if source_type.element_type != target_type.element_type:
            raise VerifyException("dma.copy source/target element_type mismatch")


@irdl_op_definition
class DmaBroadcastOp(IRDLOperation):
    """dma.broadcast。"""

    name = "dma.broadcast"
    traits = traits_def(DmaBroadcastMemoryEffect())

    target = operand_def(NnMemoryType)
    source = operand_def(Attribute)

    def __init__(self, target: SSAValue | Operation, source: SSAValue | Operation) -> None:
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

        super().__init__(operands=[target, source])

    def verify_(self) -> None:
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

        target_type = verify_memory_type(self.target.type, "target")
        source_value = SSAValue.get(self.source)
        source_type = source_value.type

        if isinstance(source_type, NnMemoryType):
            source_type = verify_memory_type(source_type, "source")
            if source_type.element_type != target_type.element_type:
                raise VerifyException("dma.broadcast element_type mismatch")
            if source_type.space.space.data != target_type.space.space.data:
                raise VerifyException("dma.broadcast space mismatch")
            verify_broadcast_compat(source_type.shape, target_type.shape)
            return

        if isinstance(source_type, SymbolValueType):
            if not isinstance(target_type.element_type, IntegerType):
                raise VerifyException("dma.broadcast symbol.int target must be integer element_type")
            return

        if source_type != target_type.element_type:
            raise VerifyException("dma.broadcast scalar type mismatch")


@irdl_op_definition
class DmaTransposeOp(IRDLOperation):
    """dma.transpose。"""

    name = "dma.transpose"
    traits = traits_def(DmaTargetSourceEffect())

    target = operand_def(NnMemoryType)
    source = operand_def(NnMemoryType)
    perm = attr_def(ArrayAttr)

    def __init__(
        self,
        target: SSAValue | Operation,
        source: SSAValue | Operation,
        perm: Sequence[int] | ArrayAttr,
    ) -> None:
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

        perm_attr = perm if isinstance(perm, ArrayAttr) else ArrayAttr([IntAttr(value) for value in perm])
        super().__init__(operands=[target, source], attributes={"perm": perm_attr})

    def verify_(self) -> None:
        """校验 dma.transpose。


        功能说明:
        - target/source 必须为 nn.memory。
        - element_type 与 space 必须一致。
        - perm 必须是 0..rank-1 的排列，target shape 为 source 的重排。
        - target stride 必须是 target shape 的默认连续 stride。

        使用示例:
        - DmaTransposeOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        target_type = verify_memory_type(self.target.type, "target")
        source_type = verify_memory_type(self.source.type, "source")
        if target_type.element_type != source_type.element_type:
            raise VerifyException("dma.transpose element_type mismatch")
        if target_type.space.space.data != source_type.space.space.data:
            raise VerifyException("dma.transpose space mismatch")
        perm_values = verify_transpose_perm(self.perm, len(source_type.shape.data))
        verify_transpose_layout(source_type, target_type, perm_values)



@irdl_op_definition
class DmaCastOp(IRDLOperation):
    """dma.cast。"""

    name = "dma.cast"
    traits = traits_def(DmaTargetSourceEffect())

    target = operand_def(NnMemoryType)
    source = operand_def(NnMemoryType)

    def __init__(self, target: SSAValue | Operation, source: SSAValue | Operation) -> None:
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

        super().__init__(operands=[target, source])

    def verify_(self) -> None:
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

        target_type = verify_memory_type(self.target.type, "target")
        source_type = verify_memory_type(self.source.type, "source")
        if source_type.shape != target_type.shape:
            raise VerifyException("dma.cast shape mismatch")
        if source_type.stride != target_type.stride:
            raise VerifyException("dma.cast stride mismatch")
        if source_type.space.space.data != target_type.space.space.data:
            raise VerifyException("dma.cast space mismatch")



__all__ = [
    "DmaCopyOp",
    "DmaBroadcastOp",
    "DmaTransposeOp",
    "DmaCastOp",
]
