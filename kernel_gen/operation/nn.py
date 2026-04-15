"""NN operation API facade.

创建者: 金铲铲大作战
最后一次更改: 小李飞刀

功能说明:
- 保留 `kernel_gen.operation.nn` 公开导入入口。
- 将逐元素、broadcast、structured 与 reduction family 实现转发到私有模块。

使用示例:
- from kernel_gen.operation.nn import add, broadcast, matmul, reduce_sum
- result = add(mem, 1)

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/test_operation_nn.py
- 功能实现: kernel_gen/operation/nn.py
- 功能实现: kernel_gen/operation/_nn_common.py
- 功能实现: kernel_gen/operation/_nn_elementwise.py
- 功能实现: kernel_gen/operation/_nn_broadcast.py
- 功能实现: kernel_gen/operation/_nn_structured.py
- 功能实现: kernel_gen/operation/_nn_reduction.py
"""

from __future__ import annotations

from ._nn_broadcast import _broadcast_memory_pair, _infer_broadcast_shape, broadcast, broadcast_to
from ._nn_common import _AddStrideDim, _build_add_stride, _merge_broadcast_dim, _resolve_add_dtype, _resolve_scalar_dtype
from ._nn_elementwise import (
    add,
    eq,
    exp,
    floordiv,
    ge,
    gt,
    hard_sigmoid,
    le,
    leaky_relu,
    lt,
    mul,
    ne,
    relu,
    sigmoid,
    sub,
    tanh,
    truediv,
)
from ._nn_reduction import reduce_max, reduce_min, reduce_sum
from ._nn_structured import conv, fc, img2col1d, img2col2d, matmul, softmax, transpose

__all__ = [
    "add",
    "sub",
    "mul",
    "truediv",
    "floordiv",
    "eq",
    "ne",
    "lt",
    "le",
    "gt",
    "ge",
    "relu",
    "leaky_relu",
    "sigmoid",
    "tanh",
    "hard_sigmoid",
    "exp",
    "reduce_sum",
    "reduce_min",
    "reduce_max",
    "matmul",
    "img2col1d",
    "img2col2d",
    "broadcast",
    "broadcast_to",
    "transpose",
]
