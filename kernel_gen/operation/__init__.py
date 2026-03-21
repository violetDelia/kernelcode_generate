"""Operation API 入口。

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 暴露 nn 逐元素算术、比较与 matmul API。
- 暴露 dma 搬运 API。

使用示例:
- from kernel_gen.operation import add, matmul, copy

关联文件:
- spec: spec/operation/nn.md
- spec: spec/operation/dma.md
- test: test/operation/test_operation_nn.py
- test: test/operation/test_operation_dma.py
- 功能实现: kernel_gen/operation/nn.py
- 功能实现: kernel_gen/operation/dma.py
"""

from .dma import alloc, cast, copy, deslice, flatten, free, load, slice, store, view
from .nn import add, eq, ge, gt, le, lt, matmul, mul, ne, sub, truediv

__all__ = [
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
    "matmul",
    "alloc",
    "free",
    "copy",
    "load",
    "store",
    "slice",
    "deslice",
    "view",
    "flatten",
    "cast",
]
