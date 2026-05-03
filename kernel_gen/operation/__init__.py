"""Operation API 入口。


功能说明:
- 暴露 nn 顶层稳定子集：逐元素算术、比较与 `matmul`。
- 暴露 dma family 的顶层稳定 helper：`alloc/free/copy/load/store/slice/deslice/view/reshape/flatten/cast`。
- 暴露 scf family 的顶层稳定 helper：`loop`。

API 列表:
- `add(lhs, rhs)`
- `sub(lhs, rhs)`
- `mul(lhs, rhs)`
- `truediv(lhs, rhs)`
- `eq(lhs, rhs)`
- `ne(lhs, rhs)`
- `lt(lhs, rhs)`
- `le(lhs, rhs)`
- `gt(lhs, rhs)`
- `ge(lhs, rhs)`
- `matmul(lhs, rhs, memoryspace=None)`
- `alloc(shape, dtype, space=MemorySpace.GM, stride=None, format=Farmat.Norm)`
- `free(value)`
- `copy(source, space)`
- `load(source, offsets, sizes, strides=None, space=None)`
- `store(target, source, offsets, sizes, strides=None)`
- `slice(source, offsets, sizes, strides=None, space=None)`
- `deslice(target, source, offsets, sizes, strides=None)`
- `view(source, offset, size, stride)`
- `reshape(source, shape)`
- `flatten(source)`
- `cast(source, dtype, memoryspace=None)`
- `loop(start, end, step, trip_count=1)`

使用示例:
- from kernel_gen.operation import add, matmul, copy

关联文件:
- spec: spec/operation/nn.md
- spec: spec/operation/dma.md
- spec: spec/operation/scf.md
- test: test/operation/nn/test_package.py
- test: test/operation/test_dma.py
- test: test/operation/test_scf.py
- test: test/operation/test_package.py
- 功能实现: kernel_gen/operation/nn/__init__.py
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
