"""DMA dialect package root.

功能说明:
- 暴露 dma dialect 的稳定 root API，聚合 alloc/fill/free/copy/load/store/slice/deslice/subview/view/reshape/reinterpret/cast/broadcast/ring op 与 `Dma` dialect。
- 内部 type/operation/common/effect/canonicalization 子模块只服务 package 实现，不作为外部稳定 API。

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
- `class DmaRingType(memory_type: NnMemoryType)`
- `class DmaMakeRingOp(memory: SSAValue | Operation, num: SSAValue | Operation, offset: SSAValue | Operation, shape_bytes: SSAValue | Operation, result_type: DmaRingType)`
- `class DmaCurrentRingOp(ring: SSAValue | Operation, result_type: NnMemoryType | None = None)`
- `class DmaAdvanceRingOp(ring: SSAValue | Operation, result_type: NnMemoryType | None = None)`
- `Dma`

使用示例:
- `from kernel_gen.dialect.dma import Dma, DmaCopyOp`

关联文件:
- spec: spec/dialect/dma.md
- test: test/dialect/dma/
- 功能实现: kernel_gen/dialect/dma/__init__.py
"""

from __future__ import annotations

from xdsl.ir import Dialect

from .operation import (
    DmaAdvanceRingOp,
    DmaAllocOp,
    DmaBroadcastOp,
    DmaCastOp,
    DmaCopyOp,
    DmaCurrentRingOp,
    DmaDesliceOp,
    DmaFillOp,
    DmaFreeOp,
    DmaLoadOp,
    DmaMakeRingOp,
    DmaReinterpretOp,
    DmaReshapeOp,
    DmaSliceOp,
    DmaStoreOp,
    DmaSubviewOp,
    DmaTransposeOp,
    DmaViewOp,
)
from .type import DmaRingType


class Dma(Dialect):
    """DMA dialect 入口。

    功能说明:
    - 注册 dma dialect 的 op 与 type 定义。

    使用示例:
    - `ctx.load_dialect(Dma)`
    """

    name = "dma"
    operations = [
        DmaAllocOp,
        DmaFillOp,
        DmaFreeOp,
        DmaCopyOp,
        DmaBroadcastOp,
        DmaTransposeOp,
        DmaLoadOp,
        DmaStoreOp,
        DmaSliceOp,
        DmaDesliceOp,
        DmaSubviewOp,
        DmaViewOp,
        DmaReshapeOp,
        DmaReinterpretOp,
        DmaCastOp,
        DmaMakeRingOp,
        DmaCurrentRingOp,
        DmaAdvanceRingOp,
    ]
    attributes = [DmaRingType]


__all__ = [
    "Dma",
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
    "DmaRingType",
    "DmaMakeRingOp",
    "DmaCurrentRingOp",
    "DmaAdvanceRingOp",
]
