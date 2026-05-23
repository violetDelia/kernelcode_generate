"""DMA ring operation definitions.

功能说明:
- 定义 `dma.make_ring`、`dma.current_ring` 与 `dma.advance_ring`。

API 列表:
- `class DmaMakeRingOp(memory: SSAValue | Operation, count: SSAValue | Operation, offset: SSAValue | Operation, shape_bytes: SSAValue | Operation, result_type: DmaRingType)`
- `class DmaCurrentRingOp(ring: SSAValue | Operation, result_type: NnMemoryType | None = None)`
- `class DmaAdvanceRingOp(ring: SSAValue | Operation, result_type: NnMemoryType | None = None)`

使用示例:
- `DmaMakeRingOp(memory, count, offset, shape_bytes, ring_type)`

关联文件:
- spec: spec/dialect/dma.md
- test: test/dialect/dma/
- 功能实现: kernel_gen/dialect/dma/operation/ring.py
"""

from __future__ import annotations

from xdsl.ir import Operation, SSAValue
from xdsl.irdl import IRDLOperation, irdl_op_definition, operand_def, result_def
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType

from ..common import (
    is_i8_byte_pool,
    maybe_numel,
    symbol_int_expr_text,
    verify_memory_operand,
    verify_positive_static_operand,
)
from ..type import DmaRingType

@irdl_op_definition
class DmaMakeRingOp(IRDLOperation):
    """dma.make_ring。"""

    name = "dma.make_ring"

    memory = operand_def(NnMemoryType)
    count = operand_def(SymbolValueType)
    offset = operand_def(SymbolValueType)
    shape_bytes = operand_def(SymbolValueType)
    result = result_def(DmaRingType)

    def __init__(
        self,
        memory: SSAValue | Operation,
        count: SSAValue | Operation,
        offset: SSAValue | Operation,
        shape_bytes: SSAValue | Operation,
        result_type: DmaRingType,
    ) -> None:
        """初始化 dma.make_ring。

        功能说明:
        - 创建 ring buffer 描述，result type 记录 stage offset 与 slot memory type。

        使用示例:
        - DmaMakeRingOp(storage, count, offset, shape_bytes, ring_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        super().__init__(operands=[memory, count, offset, shape_bytes], result_types=[result_type])

    def verify_(self) -> None:
        """校验 dma.make_ring。

        功能说明:
        - backing memory 必须是一维 i8 memory。
        - count/offset/shape_bytes 必须为 `!symbol.int`，静态可判定时满足正数与容量关系。
        - result ring 的 offset 和 slot space 必须与 operands/backing memory 一致。

        使用示例:
        - DmaMakeRingOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        memory_type = verify_memory_operand(self.memory, "memory")
        if not is_i8_byte_pool(memory_type):
            raise VerifyException("dma.make_ring memory must be one-dimensional i8 memory")
        ring_type = self.result.type
        if not isinstance(ring_type, DmaRingType):
            raise VerifyException("dma.make_ring result must be dma.ring")
        ring_type.verify()
        count_int = verify_positive_static_operand(self.count, "count")
        offset_int = verify_positive_static_operand(self.offset, "offset")
        shape_bytes_int = verify_positive_static_operand(self.shape_bytes, "shape_bytes")
        if offset_int is not None and shape_bytes_int is not None and shape_bytes_int >= offset_int:
            raise VerifyException("shape_bytes must be < offset")
        backing_bytes = maybe_numel(memory_type.shape)
        if backing_bytes is not None and count_int is not None and offset_int is not None:
            if backing_bytes < count_int * offset_int:
                raise VerifyException("dma.make_ring backing memory bytes must be >= count * offset")
        offset_expr = symbol_int_expr_text(self.offset, "offset")
        if ring_type.offset.expr.data != offset_expr:
            raise VerifyException("dma.make_ring result ring offset must match offset operand")
        if ring_type.memory_type.space.space.data != memory_type.space.space.data:
            raise VerifyException("dma.make_ring result ring slot space must match backing memory space")


@irdl_op_definition
class DmaCurrentRingOp(IRDLOperation):
    """dma.current_ring。"""

    name = "dma.current_ring"

    ring = operand_def(DmaRingType)
    result = result_def(NnMemoryType)

    def __init__(
        self,
        ring: SSAValue | Operation,
        result_type: NnMemoryType | None = None,
    ) -> None:
        """初始化 dma.current_ring。

        功能说明:
        - 返回 ring 当前 cursor 对应的 slot memory。

        使用示例:
        - DmaCurrentRingOp(ring_value)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        ring_type = SSAValue.get(ring).type
        if result_type is None:
            if not isinstance(ring_type, DmaRingType):
                raise TypeError("ring must have dma.ring type when result_type is omitted")
            result_type = ring_type.memory_type
        super().__init__(operands=[ring], result_types=[result_type])

    def verify_(self) -> None:
        """校验 dma.current_ring。

        功能说明:
        - operand 必须是 dma.ring，result type 必须等于 ring slot memory type。

        使用示例:
        - DmaCurrentRingOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        ring_type = self.ring.type
        if not isinstance(ring_type, DmaRingType):
            raise VerifyException("dma.current_ring ring operand must be dma.ring")
        ring_type.verify()
        if self.result.type != ring_type.memory_type:
            raise VerifyException("dma.current_ring result must match ring slot memory type")


@irdl_op_definition
class DmaAdvanceRingOp(IRDLOperation):
    """dma.advance_ring。"""

    name = "dma.advance_ring"

    ring = operand_def(DmaRingType)
    result = result_def(NnMemoryType)

    def __init__(
        self,
        ring: SSAValue | Operation,
        result_type: NnMemoryType | None = None,
    ) -> None:
        """初始化 dma.advance_ring。

        功能说明:
        - 推进 ring cursor 并返回推进后的 current slot memory。

        使用示例:
        - DmaAdvanceRingOp(ring_value)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        ring_type = SSAValue.get(ring).type
        if result_type is None:
            if not isinstance(ring_type, DmaRingType):
                raise TypeError("ring must have dma.ring type when result_type is omitted")
            result_type = ring_type.memory_type
        super().__init__(operands=[ring], result_types=[result_type])

    def verify_(self) -> None:
        """校验 dma.advance_ring。

        功能说明:
        - operand 必须是 dma.ring，result type 必须等于 ring slot memory type。
        - op 不声明 Pure trait，未使用 result 时仍应保留 cursor 推进副作用。

        使用示例:
        - DmaAdvanceRingOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        ring_type = self.ring.type
        if not isinstance(ring_type, DmaRingType):
            raise VerifyException("dma.advance_ring ring operand must be dma.ring")
        ring_type.verify()
        if self.result.type != ring_type.memory_type:
            raise VerifyException("dma.advance_ring result must match ring slot memory type")



__all__ = [
    "DmaMakeRingOp",
    "DmaCurrentRingOp",
    "DmaAdvanceRingOp",
]
