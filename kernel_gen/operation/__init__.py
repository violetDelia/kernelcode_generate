"""Operation API 入口。

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 暴露 nn 逐元素算术、比较与 matmul API。
- 暴露 dma 搬运 API。
- 暴露 scf loop 范围迭代 API。

使用示例:
- from kernel_gen.operation import add, matmul, copy

关联文件:
- spec: spec/operation/nn.md
- spec: spec/operation/dma.md
- spec: spec/operation/scf.md
- test: test/operation/test_operation_nn.py
- test: test/operation/test_operation_dma.py
- test: test/operation/test_operation_scf.py
- 功能实现: kernel_gen/operation/nn.py
- 功能实现: kernel_gen/operation/dma.py
- 功能实现: kernel_gen/operation/scf.py
"""

from .dma import alloc, cast, copy, deslice, flatten, free, load, reshape, slice, store, view
from .nn import add, eq, ge, gt, le, lt, matmul, mul, ne, sub, truediv
from .scf import loop

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
    "reshape",
    "flatten",
    "cast",
    "loop",
]
