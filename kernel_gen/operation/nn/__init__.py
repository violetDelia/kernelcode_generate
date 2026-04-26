"""NN operation API facade package.

创建者: 守护最好的爱莉希雅
最后一次更改: 金铲铲大作战

功能说明:
- 保留 `kernel_gen.operation.nn` 公开导入入口。
- 将逐元素、broadcast、structured 与 reduction family 组织到 `kernel_gen.operation.nn.*` 子模块。
- 公开实现已迁移到 `kernel_gen.operation.nn.*` 子模块。
- 旧 `_nn_*` 文件与旧 `kernel_gen.operation.nn.py` 已退场，不再作为公开或兼容合同路径。

使用示例:
- from kernel_gen.operation.nn import add, broadcast, matmul, reduce_sum
- result = add(mem, 1)

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/test_operation_nn.py
- test: test/operation/test_operation_nn_elementwise.py
- test: test/operation/test_operation_nn_broadcast.py
- test: test/operation/test_operation_nn_structured.py
- test: test/operation/test_operation_nn_reduction.py
- 功能实现: kernel_gen/operation/nn/__init__.py
- 功能实现: kernel_gen/operation/nn/common.py
- 功能实现: kernel_gen/operation/nn/broadcast.py
- 功能实现: kernel_gen/operation/nn/elementwise_binary.py
- 功能实现: kernel_gen/operation/nn/elementwise_compare.py
- 功能实现: kernel_gen/operation/nn/activation.py
- 功能实现: kernel_gen/operation/nn/exp.py
- 功能实现: kernel_gen/operation/nn/reduction.py
- 功能实现: kernel_gen/operation/nn/fc.py
- 功能实现: kernel_gen/operation/nn/matmul.py
- 功能实现: kernel_gen/operation/nn/conv.py
- 功能实现: kernel_gen/operation/nn/img2col.py
- 功能实现: kernel_gen/operation/nn/softmax.py
- 功能实现: kernel_gen/operation/nn/transpose.py
"""

from __future__ import annotations

from .activation import hard_sigmoid, leaky_relu, relu, sigmoid, tanh
from .broadcast import _broadcast_memory_pair, _infer_broadcast_shape, broadcast, broadcast_to
from .common import _AddStrideDim, _build_add_stride, _merge_broadcast_dim, _resolve_add_dtype, _resolve_scalar_dtype
from .conv import conv
from .elementwise_binary import add, floordiv, mul, sub, truediv
from .elementwise_compare import eq, ge, gt, le, lt, ne
from .exp import exp
from .fc import fc
from .img2col import img2col1d, img2col2d
from .matmul import matmul
from .reduction import reduce_max, reduce_min, reduce_sum
from .softmax import softmax
from .transpose import transpose

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
