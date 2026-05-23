"""memory operation package.

功能说明:
- 聚合 memory package 内公开 op。

API 列表:
- `class MemoryGetDataOp(source: SSAValue | Operation, result_type: Attribute | None = None)`

使用示例:
- `from kernel_gen.dialect.memory.operation import ...`

关联文件:
- spec: spec/dialect/memory.md
- test: test/dialect/memory/
- 功能实现: kernel_gen/dialect/memory/operation/__init__.py
"""

from __future__ import annotations

from .get_data import MemoryGetDataOp

__all__ = ["MemoryGetDataOp"]
