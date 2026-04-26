"""NN operation API facade package.

创建者: 守护最好的爱莉希雅
最后一次更改: jcc你莫辜负

功能说明:
- 保留 `kernel_gen.operation.nn` 公开导入入口。
- 将逐元素、broadcast、structured 与 reduction family 组织到 `kernel_gen.operation.nn.*` 子模块。
- 公开实现已迁移到 `kernel_gen.operation.nn.*` 子模块。
- 旧 `_nn_*` 文件与旧 `kernel_gen.operation.nn.py` 已退场，不再作为公开或兼容合同路径。

API 列表:
- `add(lhs: object, rhs: object) -> ArithmeticResult`
- `sub(lhs: object, rhs: object) -> ArithmeticResult`
- `mul(lhs: object, rhs: object) -> ArithmeticResult`
- `truediv(lhs: object, rhs: object) -> ArithmeticResult`
- `floordiv(lhs: object, rhs: object) -> ArithmeticResult`
- `eq(lhs: object, rhs: object) -> Memory`
- `ne(lhs: object, rhs: object) -> Memory`
- `lt(lhs: object, rhs: object) -> Memory`
- `le(lhs: object, rhs: object) -> Memory`
- `gt(lhs: object, rhs: object) -> Memory`
- `ge(lhs: object, rhs: object) -> Memory`
- `relu(value: object) -> Memory`
- `leaky_relu(value: object, alpha: int | float = 0.01) -> Memory`
- `sigmoid(value: object) -> Memory`
- `tanh(value: object) -> Memory`
- `hard_sigmoid(value: object, alpha: int | float = 0.2, beta: int | float = 0.5) -> Memory`
- `exp(value: object) -> Memory`
- `reduce_sum(value: object, axis: object = None, keepdim: object = False) -> Memory`
- `reduce_min(value: object, axis: object = None, keepdim: object = False) -> Memory`
- `reduce_max(value: object, axis: object = None, keepdim: object = False) -> Memory`
- `fc(value: object, weight: object, bias: object | None = None) -> Memory`
- `matmul(lhs: object, rhs: object, memoryspace: MemorySpace | None = None) -> Memory`
- `conv(value: object, weight: object, bias: object | None = None, sh: int | SymbolDim = 1, sw: int | SymbolDim = 1, dh: int | SymbolDim = 1, dw: int | SymbolDim = 1, ph: int | SymbolDim = 0, pw: int | SymbolDim = 0, pl: int | SymbolDim = 0, pr: int | SymbolDim = 0) -> Memory`
- `img2col1d(value: object, kw: object, sw: object = 1, pw: object = 0, dw: object = 1) -> Memory`
- `img2col2d(value: object, kh: object, kw: object, sh: object = 1, sw: object = 1, ph: object = 0, pw: object = 0, dh: object = 1, dw: object = 1) -> Memory`
- `broadcast(value: object, target: object) -> Memory`
- `broadcast_to(source: object, target_shape: object, space: object) -> Memory`
- `transpose(value: object, perm: object) -> Memory`
- `softmax(value: object, axis: int = -1) -> Memory`

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
from .broadcast import broadcast, broadcast_to
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
    "fc",
    "matmul",
    "conv",
    "img2col1d",
    "img2col2d",
    "broadcast",
    "broadcast_to",
    "transpose",
    "softmax",
]
