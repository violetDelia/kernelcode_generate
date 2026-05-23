"""DMA slice operation definitions.

功能说明:
- 定义 `dma.load`、`dma.store`、`dma.slice` 与 `dma.deslice`。

API 列表:
- `class DmaLoadOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue])`
- `class DmaStoreOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue])`
- `class DmaSliceOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue])`
- `class DmaDesliceOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue], result_type: NnMemoryType)`

使用示例:
- `DmaSliceOp(target, source, offsets, sizes, strides)`

关联文件:
- spec: spec/dialect/dma.md
- test: test/dialect/dma/
- 功能实现: kernel_gen/dialect/dma/operation/slice.py
"""

from __future__ import annotations

from collections.abc import Sequence

from xdsl.dialects.builtin import ArrayAttr, IntAttr
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
    verify_memory_type,
    verify_operands_match_layout,
    verify_rank_match,
    verify_symbol_index_operands,
    verify_symbol_int_operands,
    verify_unit_stride_operands,
)
from ..effect import DmaTargetSourceEffect

@irdl_op_definition
class DmaLoadOp(IRDLOperation):
    """dma.load。"""

    name = "dma.load"
    traits = traits_def(DmaTargetSourceEffect())

    target = operand_def(NnMemoryType)
    source = operand_def(NnMemoryType)
    offsets = var_operand_def(Attribute)
    sizes = var_operand_def(SymbolValueType)
    strides = var_operand_def(SymbolValueType)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        target: SSAValue | Operation,
        source: SSAValue | Operation,
        offsets: Sequence[SSAValue],
        sizes: Sequence[SSAValue],
        strides: Sequence[SSAValue],
    ) -> None:
        """初始化 dma.load。


        功能说明:
        - 设置 target/source 与 offsets/sizes/strides。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaLoadOp(target, source, offsets, sizes, strides)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        super().__init__(
            operands=[target, source, offsets, sizes, strides],
        )

    def verify_(self) -> None:
        """校验 dma.load。


        功能说明:
        - offsets/sizes/strides 长度与 source rank 一致。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。
        - target.shape == sizes 且 element_type 一致。

        使用示例:
        - DmaLoadOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        target_type = verify_memory_type(self.target.type, "target")
        source_type = verify_memory_type(self.source.type, "source")
        offsets = verify_symbol_index_operands(self.offsets, "offsets", min_value=0)
        sizes = verify_symbol_int_operands(self.sizes, "sizes", min_value=1)
        strides = verify_symbol_int_operands(self.strides, "strides", min_value=1)
        rank = len(source_type.shape.data)
        if len(target_type.shape.data) != rank:
            raise VerifyException("dma.load target rank must match source rank")
        verify_rank_match(offsets, rank, "offsets")
        verify_rank_match(sizes, rank, "sizes")
        verify_rank_match(strides, rank, "strides")
        verify_unit_stride_operands(strides)
        verify_operands_match_layout(sizes, target_type.shape, "target shape must match sizes")
        if source_type.element_type != target_type.element_type:
            raise VerifyException("dma.load element_type mismatch")


@irdl_op_definition
class DmaStoreOp(IRDLOperation):
    """dma.store。"""

    name = "dma.store"
    traits = traits_def(DmaTargetSourceEffect())

    target = operand_def(NnMemoryType)
    source = operand_def(NnMemoryType)
    offsets = var_operand_def(Attribute)
    sizes = var_operand_def(SymbolValueType)
    strides = var_operand_def(SymbolValueType)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        target: SSAValue | Operation,
        source: SSAValue | Operation,
        offsets: Sequence[SSAValue],
        sizes: Sequence[SSAValue],
        strides: Sequence[SSAValue],
    ) -> None:
        """初始化 dma.store。


        功能说明:
        - 设置 target/source 与 offsets/sizes/strides。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaStoreOp(target, source, offsets, sizes, strides)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        super().__init__(operands=[target, source, offsets, sizes, strides])

    def verify_(self) -> None:
        """校验 dma.store。


        功能说明:
        - source.shape 必须与 sizes 对齐。
        - offsets/sizes/strides 长度与 target rank 一致。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaStoreOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        source_type = verify_memory_type(self.source.type, "source")
        target_type = verify_memory_type(self.target.type, "target")
        offsets = verify_symbol_index_operands(self.offsets, "offsets", min_value=0)
        sizes = verify_symbol_int_operands(self.sizes, "sizes", min_value=1)
        strides = verify_symbol_int_operands(self.strides, "strides", min_value=1)
        rank = len(target_type.shape.data)
        verify_rank_match(offsets, rank, "offsets")
        verify_rank_match(sizes, rank, "sizes")
        verify_rank_match(strides, rank, "strides")
        verify_unit_stride_operands(strides)
        verify_operands_match_layout(sizes, source_type.shape, "source shape must match sizes")
        if source_type.element_type != target_type.element_type:
            raise VerifyException("dma.store element_type mismatch")


@irdl_op_definition
class DmaSliceOp(IRDLOperation):
    """dma.slice。"""

    name = "dma.slice"
    traits = traits_def(DmaTargetSourceEffect())

    target = operand_def(NnMemoryType)
    source = operand_def(NnMemoryType)
    offsets = var_operand_def(Attribute)
    sizes = var_operand_def(SymbolValueType)
    strides = var_operand_def(SymbolValueType)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        target: SSAValue | Operation,
        source: SSAValue | Operation,
        offsets: Sequence[SSAValue],
        sizes: Sequence[SSAValue],
        strides: Sequence[SSAValue],
    ) -> None:
        """初始化 dma.slice。


        功能说明:
        - 设置 target/source 与 offsets/sizes/strides。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaSliceOp(target, source, offsets, sizes, strides)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        super().__init__(operands=[target, source, offsets, sizes, strides])

    def verify_(self) -> None:
        """校验 dma.slice。


        功能说明:
        - offsets/sizes/strides 长度与 source rank 一致。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。
        - target.shape == sizes 且 target/source element_type 一致。
        - 当前阶段 stride 必须为 1。

        使用示例:
        - DmaSliceOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        target_type = verify_memory_type(self.target.type, "target")
        source_type = verify_memory_type(self.source.type, "source")
        offsets = verify_symbol_index_operands(self.offsets, "offsets", min_value=0)
        sizes = verify_symbol_int_operands(self.sizes, "sizes", min_value=1)
        strides = verify_symbol_int_operands(self.strides, "strides", min_value=1)
        rank = len(source_type.shape.data)
        if len(target_type.shape.data) != rank:
            raise VerifyException("dma.slice target rank must match source rank")
        verify_rank_match(offsets, rank, "offsets")
        verify_rank_match(sizes, rank, "sizes")
        verify_rank_match(strides, rank, "strides")
        verify_unit_stride_operands(strides)
        verify_operands_match_layout(sizes, target_type.shape, "shape must match sizes")
        if source_type.element_type != target_type.element_type:
            raise VerifyException("dma.slice element_type mismatch")


@irdl_op_definition
class DmaDesliceOp(IRDLOperation):
    """dma.deslice。"""

    name = "dma.deslice"
    traits = traits_def(DmaTargetSourceEffect())

    target = operand_def(NnMemoryType)
    source = operand_def(NnMemoryType)
    offsets = var_operand_def(Attribute)
    sizes = var_operand_def(SymbolValueType)
    strides = var_operand_def(SymbolValueType)
    result = result_def(NnMemoryType)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        target: SSAValue | Operation,
        source: SSAValue | Operation,
        offsets: Sequence[SSAValue],
        sizes: Sequence[SSAValue],
        strides: Sequence[SSAValue],
        result_type: NnMemoryType,
    ) -> None:
        """初始化 dma.deslice。


        功能说明:
        - 设置 target/source、offsets/sizes/strides 与结果类型。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaDesliceOp(target, source, offsets, sizes, strides, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        super().__init__(
            operands=[target, source, offsets, sizes, strides],
            result_types=[result_type],
        )

    def verify_(self) -> None:
        """校验 dma.deslice。


        功能说明:
        - source.shape 必须与 sizes 对齐。
        - offsets/sizes/strides 长度与 target rank 一致。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。
        - result type 必须与 target type 一致。

        使用示例:
        - DmaDesliceOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        source_type = verify_memory_type(self.source.type, "source")
        target_type = verify_memory_type(self.target.type, "target")
        result_type = verify_memory_type(self.result.type, "result")
        offsets = verify_symbol_index_operands(self.offsets, "offsets", min_value=0)
        sizes = verify_symbol_int_operands(self.sizes, "sizes", min_value=1)
        strides = verify_symbol_int_operands(self.strides, "strides", min_value=1)
        rank = len(target_type.shape.data)
        verify_rank_match(offsets, rank, "offsets")
        verify_rank_match(sizes, rank, "sizes")
        verify_rank_match(strides, rank, "strides")
        verify_unit_stride_operands(strides)
        verify_operands_match_layout(sizes, source_type.shape, "source shape must match sizes")
        if source_type.element_type != target_type.element_type:
            raise VerifyException("dma.deslice element_type mismatch")
        if result_type != target_type:
            raise VerifyException("dma.deslice result must match target type")



__all__ = [
    "DmaLoadOp",
    "DmaStoreOp",
    "DmaSliceOp",
    "DmaDesliceOp",
]
