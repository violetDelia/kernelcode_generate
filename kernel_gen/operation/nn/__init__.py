"""NN operation API facade package.


功能说明:
- 保留 `kernel_gen.operation.nn` 公开导入入口。
- 将逐元素、broadcast、structured 与 reduction family 组织到 `kernel_gen.operation.nn.*` 子模块。
- 公开实现已迁移到 `kernel_gen.operation.nn.*` 子模块。
- 旧 `_nn_*` 文件与旧 `kernel_gen.operation.nn.py` 已退场，不再作为公开或兼容合同路径。

API 列表:
- `add(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`
- `sub(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`
- `mul(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`
- `truediv(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`
- `floordiv(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`
- `eq(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `ne(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `lt(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `le(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `gt(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `ge(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `relu(value: Memory) -> Memory`
- `leaky_relu(value: Memory, alpha: int | float = 0.01) -> Memory`
- `sigmoid(value: Memory) -> Memory`
- `tanh(value: Memory) -> Memory`
- `hard_sigmoid(value: Memory, alpha: int | float = 0.2, beta: int | float = 0.5) -> Memory`
- `exp(value: Memory) -> Memory`
- `reduce_sum(value: Memory, axis: AxisInput = None, keepdim: bool = False) -> Memory`
- `reduce_min(value: Memory, axis: AxisInput = None, keepdim: bool = False) -> Memory`
- `reduce_max(value: Memory, axis: AxisInput = None, keepdim: bool = False) -> Memory`
- `fc(value: Memory, weight: Memory, bias: Memory | None = None) -> Memory`
- `matmul(lhs: Memory, rhs: Memory, memoryspace: MemorySpace | None = None) -> Memory`
- `conv(value: Memory, weight: Memory, bias: Memory | None = None, sh: int | SymbolDim = 1, sw: int | SymbolDim = 1, dh: int | SymbolDim = 1, dw: int | SymbolDim = 1, ph: int | SymbolDim = 0, pw: int | SymbolDim = 0, pl: int | SymbolDim = 0, pr: int | SymbolDim = 0) -> Memory`
- `img2col1d(value: Memory, kw: int | SymbolDim, sw: int | SymbolDim = 1, dw: int | SymbolDim = 1, pl: int | SymbolDim = 0, pr: int | SymbolDim = 0) -> Memory`
- `img2col2d(value: Memory, kh: int | SymbolDim, kw: int | SymbolDim, sh: int | SymbolDim = 1, sw: int | SymbolDim = 1, dh: int | SymbolDim = 1, dw: int | SymbolDim = 1, ph: int | SymbolDim = 0, pw: int | SymbolDim = 0, pl: int | SymbolDim = 0, pr: int | SymbolDim = 0) -> Memory`
- `broadcast(value: Memory, target: Memory) -> Memory`
- `broadcast_to(source: Memory, target_shape: ShapeInput, space: MemorySpace) -> Memory`
- `transpose(value: Memory, perm: Sequence[int]) -> Memory`
- `softmax(value: Memory, axis: int = -1) -> Memory`

使用示例:
- from kernel_gen.operation.nn import add, broadcast, matmul, reduce_sum
- result = add(mem, 1)

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/nn/test_package.py
- test: test/operation/nn/test_elementwise.py
- test: test/operation/nn/test_broadcast.py
- test: test/operation/nn/test_structured.py
- test: test/operation/nn/test_reduction.py
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
