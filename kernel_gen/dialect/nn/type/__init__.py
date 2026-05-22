"""nn type package.

功能说明:
- 承载 nn dialect package 拆分后的 nn type package 实现。

API 列表:
- `class NnMemoryType(shape: ArrayAttr[SymbolExprAttr], stride: ArrayAttr[SymbolExprAttr], element_type: Attribute, space: NnMemorySpaceAttr, template_name: StringAttr | str | None = None)`
- `copy_memory_type(memory_type: NnMemoryType, *, shape: ArrayAttr[SymbolExprAttr] | None = None, stride: ArrayAttr[SymbolExprAttr] | None = None, element_type: Attribute | None = None, space: NnMemorySpaceAttr | None = None) -> NnMemoryType`
- `copy_memory_type_with_template_name(memory_type: NnMemoryType, template_name: str | StringAttr, *, shape: ArrayAttr[SymbolExprAttr] | None = None, stride: ArrayAttr[SymbolExprAttr] | None = None, element_type: Attribute | None = None, space: NnMemorySpaceAttr | None = None) -> NnMemoryType`

使用示例:
- from kernel_gen.dialect.nn.type import NnMemoryType

关联文件:
- spec: spec/dialect/nn.md
- test: test/dialect/nn/
- 功能实现: kernel_gen/dialect/nn/type/__init__.py
"""

from __future__ import annotations

from kernel_gen.dialect.nn.type.memory_type import (
    NnMemoryType,
    copy_memory_type,
    copy_memory_type_with_template_name,
)

__all__ = ["NnMemoryType", "copy_memory_type", "copy_memory_type_with_template_name"]
