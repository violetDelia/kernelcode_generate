"""memory dialect package root.

功能说明:
- 暴露 memory dialect 稳定 root API。

API 列表:
- `Memory`
- `class MemoryGetDataOp(source: SSAValue | Operation, result_type: Attribute | None = None)`

使用示例:
- `from kernel_gen.dialect.memory import Memory, MemoryGetDataOp`

关联文件:
- spec: spec/dialect/memory.md
- test: test/dialect/memory/
- 功能实现: kernel_gen/dialect/memory/__init__.py
"""

from __future__ import annotations

from xdsl.ir import Dialect

from .operation import MemoryGetDataOp

Memory = Dialect("memory", [MemoryGetDataOp], [])

__all__ = [
    "Memory",
    "MemoryGetDataOp",
]
