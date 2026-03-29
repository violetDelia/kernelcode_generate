"""Dialect package entry.

创建者: 小李飞刀
最后一次更改: 朽木露琪亚

功能说明:
- 暴露 nn 与 arch dialect 的 type、attr 与 op 定义，供包级导入复用。

使用示例:
- from kernel_gen.dialect import Arch, ArchLaunchKernelOp, Nn, NnAddOp, NnMemoryType

关联文件:
- spec: spec/dialect/arch.md
- test: test/dialect/test_arch_dialect.py
- 功能实现: kernel_gen/dialect/__init__.py
"""

from .arch import (
    Arch,
    ArchGetBlockIdOp,
    ArchGetBlockNumOp,
    ArchGetDynamicMemoryOp,
    ArchGetSubthreadIdOp,
    ArchGetSubthreadNumOp,
    ArchGetThreadIdOp,
    ArchGetThreadNumOp,
    ArchLaunchKernelOp,
)
from .nn import (
    Nn,
    NnAddOp,
    NnBroadcastOp,
    NnEqOp,
    NnGeOp,
    NnGtOp,
    NnImg2col1dOp,
    NnImg2col2dOp,
    NnLeOp,
    NnLtOp,
    NnMatmulOp,
    NnMemorySpaceAttr,
    NnMemoryType,
    NnMulOp,
    NnNeOp,
    NnSubOp,
    NnTrueDivOp,
)

__all__ = [
    "Arch",
    "ArchGetBlockIdOp",
    "ArchGetBlockNumOp",
    "ArchGetThreadIdOp",
    "ArchGetThreadNumOp",
    "ArchGetSubthreadIdOp",
    "ArchGetSubthreadNumOp",
    "ArchGetDynamicMemoryOp",
    "ArchLaunchKernelOp",
    "Nn",
    "NnAddOp",
    "NnBroadcastOp",
    "NnSubOp",
    "NnMulOp",
    "NnTrueDivOp",
    "NnEqOp",
    "NnNeOp",
    "NnLtOp",
    "NnLeOp",
    "NnGtOp",
    "NnGeOp",
    "NnMatmulOp",
    "NnImg2col1dOp",
    "NnImg2col2dOp",
    "NnMemorySpaceAttr",
    "NnMemoryType",
]
