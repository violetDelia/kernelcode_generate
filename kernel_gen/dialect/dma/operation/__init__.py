"""DMA dialect operation package.

功能说明:
- 聚合 dma package 内部 op 定义，供 package root 构造公开 root API。

API 列表:
- `class DmaAllocOp(dynamic_shape: Sequence[SSAValue], result_type: NnMemoryType)`
- `class DmaFillOp(target: SSAValue | Operation, value: SSAValue | Operation)`
- `class DmaFreeOp(source: SSAValue | Operation)`
- `class DmaCopyOp(target: SSAValue | Operation, source: SSAValue | Operation)`
- `class DmaBroadcastOp(target: SSAValue | Operation, source: SSAValue | Operation)`
- `class DmaTransposeOp(target: SSAValue | Operation, source: SSAValue | Operation, perm: Sequence[int] | ArrayAttr)`
- `class DmaLoadOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue])`
- `class DmaStoreOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue])`
- `class DmaSliceOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue])`
- `class DmaDesliceOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue])`
- `class DmaSubviewOp(source: SSAValue | Operation, offset: SSAValue | Operation, size: SSAValue | Operation, stride: SSAValue | Operation, result_type: NnMemoryType)`
- `class DmaViewOp(source: SSAValue | Operation, offsets: Sequence[SSAValue], shape: Sequence[SSAValue], stride: Sequence[SSAValue], result_type: NnMemoryType)`
- `class DmaReshapeOp(source: SSAValue | Operation, shape: Sequence[SSAValue], result_type: NnMemoryType)`
- `class DmaReinterpretOp(source: SSAValue | Operation, offset: SSAValue | Operation, shape: Sequence[SSAValue], stride: Sequence[SSAValue], result_type: NnMemoryType)`
- `class DmaCastOp(target: SSAValue | Operation, source: SSAValue | Operation)`
- `class DmaMakeRingOp(memory: SSAValue | Operation, num: SSAValue | Operation, offset: SSAValue | Operation, result_type: DmaRingType)`
- `class DmaCurrentRingOp(ring: SSAValue | Operation, result_type: NnMemoryType | None = None)`
- `class DmaAdvanceRingOp(ring: SSAValue | Operation, result_type: NnMemoryType | None = None)`

使用示例:
- `from kernel_gen.dialect.dma.operation import DmaCopyOp`

关联文件:
- spec: spec/dialect/dma.md
- test: test/dialect/dma/
- 功能实现: kernel_gen/dialect/dma/operation/__init__.py
"""

from __future__ import annotations

from .alias import DmaReinterpretOp, DmaReshapeOp, DmaSubviewOp, DmaViewOp
from .lifecycle import DmaAllocOp, DmaFillOp, DmaFreeOp
from .ring import DmaAdvanceRingOp, DmaCurrentRingOp, DmaMakeRingOp
from .slice import DmaDesliceOp, DmaLoadOp, DmaSliceOp, DmaStoreOp
from .transfer import DmaBroadcastOp, DmaCastOp, DmaCopyOp, DmaTransposeOp

__all__ = [
    "DmaAllocOp",
    "DmaFillOp",
    "DmaFreeOp",
    "DmaCopyOp",
    "DmaBroadcastOp",
    "DmaTransposeOp",
    "DmaLoadOp",
    "DmaStoreOp",
    "DmaSliceOp",
    "DmaDesliceOp",
    "DmaSubviewOp",
    "DmaViewOp",
    "DmaReshapeOp",
    "DmaReinterpretOp",
    "DmaCastOp",
    "DmaMakeRingOp",
    "DmaCurrentRingOp",
    "DmaAdvanceRingOp",
]
