"""DMA dialect type package.

功能说明:
- 聚合 dma package 内部 type 定义。

API 列表:
- `class DmaRingType(memory_type: NnMemoryType)`

使用示例:
- `from kernel_gen.dialect.dma.type import DmaRingType`

关联文件:
- spec: spec/dialect/dma.md
- test: test/dialect/dma/
- 功能实现: kernel_gen/dialect/dma/type/__init__.py
"""

from __future__ import annotations

from .ring_type import DmaRingType

__all__ = ["DmaRingType"]
