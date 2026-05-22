"""nn attr package.

功能说明:
- 承载 nn dialect package 拆分后的 nn attr package 实现。

API 列表:
- `class NnMemorySpaceAttr(space: StringAttr)`

使用示例:
- from kernel_gen.dialect.nn.attr import NnMemorySpaceAttr

关联文件:
- spec: spec/dialect/nn.md
- test: test/dialect/nn/
- 功能实现: kernel_gen/dialect/nn/attr/__init__.py
"""

from __future__ import annotations

from kernel_gen.dialect.nn.attr.space_attr import NnMemorySpaceAttr

__all__ = ["NnMemorySpaceAttr"]
