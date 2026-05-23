"""arch operation package.

功能说明:
- 聚合 arch package 内公开 op。

API 列表:
- `class ArchGetBlockIdOp(result_type: Attribute | None = None)`
- `class ArchGetDynamicMemoryOp(memory_space: NnMemorySpaceAttr, result_type: Attribute | None = None)`
- `class ArchLaunchOp(...)`

使用示例:
- `from kernel_gen.dialect.arch.operation import ...`

关联文件:
- spec: spec/dialect/arch.md
- test: test/dialect/arch/
- 功能实现: kernel_gen/dialect/arch/operation/__init__.py
"""

from __future__ import annotations

from .barrier import ArchBarrierOp
from .index import ArchGetBlockIdOp, ArchGetBlockNumOp, ArchGetSubthreadIdOp, ArchGetSubthreadNumOp, ArchGetThreadIdOp, ArchGetThreadNumOp
from .launch import ArchLaunchKernelOp, ArchLaunchOp
from .memory import ArchGetDynamicMemoryOp
from .token import ArchSignOp, ArchTokenOp, ArchWaitOp

__all__ = ["ArchGetBlockIdOp", "ArchGetBlockNumOp", "ArchGetThreadIdOp", "ArchGetThreadNumOp", "ArchGetSubthreadIdOp", "ArchGetSubthreadNumOp", "ArchGetDynamicMemoryOp", "ArchBarrierOp", "ArchLaunchOp", "ArchLaunchKernelOp", "ArchTokenOp", "ArchSignOp", "ArchWaitOp"]
