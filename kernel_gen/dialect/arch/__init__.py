"""arch dialect package root.

功能说明:
- 暴露 arch dialect 稳定 root API，内部 attr/type/operation/common 子模块不作为外部稳定 API。

API 列表:
- `Arch`
- `class ArchScopeAttr(scope: StringAttr)`
- `class ArchVisibilityAttr(visibility: StringAttr)`
- `class ArchGetBlockIdOp(result_type: Attribute | None = None)`
- `class ArchGetBlockNumOp(result_type: Attribute | None = None)`
- `class ArchGetThreadIdOp(result_type: Attribute | None = None)`
- `class ArchGetThreadNumOp(result_type: Attribute | None = None)`
- `class ArchGetSubthreadIdOp(result_type: Attribute | None = None)`
- `class ArchGetSubthreadNumOp(result_type: Attribute | None = None)`
- `class ArchGetDynamicMemoryOp(memory_space: NnMemorySpaceAttr, result_type: Attribute | None = None)`
- `class ArchBarrierOp(scope: ArchScopeAttr, visibility: ArrayAttr[Attribute])`
- `class ArchLaunchOp(callee: str | Attribute, block: SSAValue | Operation, thread: SSAValue | Operation, subthread: SSAValue | Operation, shared_memory_size: SSAValue | Operation, args: Sequence[SSAValue | Operation] = ())`
- `class ArchLaunchKernelOp(callee: str | Attribute, block: SSAValue | Operation, thread: SSAValue | Operation, subthread: SSAValue | Operation, shared_memory_size: SSAValue | Operation, args: Sequence[SSAValue | Operation] = ())`
- `class ArchTokenType(token_id: StringAttr)`
- `class ArchTokenOp(token_id: str | StringAttr, count: SSAValue | Operation)`
- `class ArchSignOp(event: SSAValue | Operation, count: SSAValue | Operation)`
- `class ArchWaitOp(event: SSAValue | Operation)`

使用示例:
- `from kernel_gen.dialect.arch import Arch, ArchLaunchKernelOp, ArchTokenType`

关联文件:
- spec: spec/dialect/arch.md
- test: test/dialect/arch/
- 功能实现: kernel_gen/dialect/arch/__init__.py
"""

from __future__ import annotations

from xdsl.ir import Dialect

from .attr import ArchScopeAttr, ArchVisibilityAttr
from .operation import (
    ArchBarrierOp, ArchGetBlockIdOp, ArchGetBlockNumOp, ArchGetDynamicMemoryOp, ArchGetSubthreadIdOp, ArchGetSubthreadNumOp, ArchGetThreadIdOp, ArchGetThreadNumOp, ArchLaunchKernelOp, ArchLaunchOp, ArchSignOp, ArchTokenOp, ArchWaitOp,
)
from .type import ArchTokenType

Arch = Dialect("arch", [ArchGetBlockIdOp, ArchGetBlockNumOp, ArchGetThreadIdOp, ArchGetThreadNumOp, ArchGetSubthreadIdOp, ArchGetSubthreadNumOp, ArchGetDynamicMemoryOp, ArchBarrierOp, ArchLaunchOp, ArchTokenOp, ArchSignOp, ArchWaitOp], [ArchScopeAttr, ArchVisibilityAttr, ArchTokenType])

__all__ = [
    "Arch",
    "ArchScopeAttr",
    "ArchVisibilityAttr",
    "ArchGetBlockIdOp",
    "ArchGetBlockNumOp",
    "ArchGetThreadIdOp",
    "ArchGetThreadNumOp",
    "ArchGetSubthreadIdOp",
    "ArchGetSubthreadNumOp",
    "ArchGetDynamicMemoryOp",
    "ArchBarrierOp",
    "ArchLaunchOp",
    "ArchLaunchKernelOp",
    "ArchTokenType",
    "ArchTokenOp",
    "ArchSignOp",
    "ArchWaitOp",
]
