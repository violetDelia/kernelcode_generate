"""Python 层模块入口。

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 提供 operation 与 dialect 子模块的统一入口。

使用示例:
- from kernel_gen.operation import add
- from kernel_gen.dialect import Nn, NnAddOp

关联文件:
- spec: spec/operation/nn.md
- spec: spec/dialect/nn.md
- test: test/operation/test_operation_nn.py
- test: test/dialect/test_nn_dialect.py
- 功能实现: kernel_gen/operation/nn.py
- 功能实现: kernel_gen/dialect/nn.py
"""

from .dialect import (
    Nn,
    NnAddOp,
    NnEqOp,
    NnGeOp,
    NnGtOp,
    NnLeOp,
    NnLtOp,
    NnMemorySpaceAttr,
    NnMemoryType,
    NnMulOp,
    NnNeOp,
    NnSubOp,
    NnTrueDivOp,
)
from .operation import add, eq, ge, gt, le, lt, mul, ne, sub, truediv

__all__ = [
    "Nn",
    "NnAddOp",
    "NnSubOp",
    "NnMulOp",
    "NnTrueDivOp",
    "NnEqOp",
    "NnNeOp",
    "NnLtOp",
    "NnLeOp",
    "NnGtOp",
    "NnGeOp",
    "NnMemorySpaceAttr",
    "NnMemoryType",
    "add",
    "sub",
    "mul",
    "truediv",
    "eq",
    "ne",
    "lt",
    "le",
    "gt",
    "ge",
]
