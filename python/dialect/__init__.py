"""Dialect package entry.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 暴露 nn dialect 的 type、attr 与 op 定义，并覆盖 TSM/TLM 空间语义。

使用示例:
- from python.dialect import Nn, NnAddOp, NnBroadcastOp, NnMemoryType

关联文件:
- spec: spec/dialect/nn.md
- test: test/dialect/test_nn_dialect.py
- 功能实现: python/dialect/nn.py
"""

from .nn import (
    Nn,
    NnAddOp,
    NnBroadcastOp,
    NnEqOp,
    NnGeOp,
    NnGtOp,
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
    "NnMemorySpaceAttr",
    "NnMemoryType",
]
