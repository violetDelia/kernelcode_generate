"""DSL for-loop expectation.

创建者: 我不是牛马
最后一次更改: 我不是牛马

功能说明:
- 验证 `build_func_op` 对 `LoopRange + slice/deslice + 无 return` 场景生成 `symbol.for`。
- 验证循环体内的 DMA lowering 使用 `dma.slice/dma.deslice`，而非顶层展开或退化为 `dma.load/dma.store`。
- 验证循环相关 lowering 不引入 `arith.index_cast`。

使用示例:
- python expectation/dsl/for_loop.py

关联文件:
- spec: spec/dsl/mlir_gen.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: kernel_gen/dsl/mlir_gen.py
"""

import random
import string
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xdsl.dialects import arith
from xdsl.dialects.func import FuncOp

from kernel_gen.dialect.dma import DmaDesliceOp, DmaLoadOp, DmaSliceOp, DmaStoreOp
from kernel_gen.dialect.symbol import NnMemoryType, SymbolForOp, SymbolValueType
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.operation.dma import deslice, slice
from kernel_gen.operation.scf import loop, LoopRange
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


def generate_random_string(length: int) -> str:
    letters = string.ascii_letters
    return "".join(random.choice(letters) for _ in range(length))


s1 = generate_random_string(random.randint(1, 8))
s2 = generate_random_string(random.randint(1, 8))
s3 = generate_random_string(random.randint(1, 8))
A = Memory([s1], NumericType.Float32)
B = Memory([s1], NumericType.Float32)
C = Memory([s1], NumericType.Float32)
start = SymbolDim(s2)
end = SymbolDim(s3)
step = SymbolDim(2)


def add(A, B, C, start, end, step):
    for index in LoopRange(start, end, step):
        slice_a = slice(A, [index], [step], [1], MemorySpace.LM)
        slice_b = slice(B, [index], [step], [1], MemorySpace.LM)
        slice_c = slice_a + slice_b
        deslice(slice_c, C, [index], [step], [1], MemorySpace.LM)


func_op = build_func_op(add, A, B, C, start, end, step)
print(func_op)
assert isinstance(func_op, FuncOp)

# arg0 = func_op.args[0].type
# assert isinstance(arg0, NnMemoryType)
# assert len(arg0.get_shape()) == 1
# assert len(arg0.get_stide()) == 1
# assert arg0.get_shape()[0] == s1
# assert arg0.get_stide()[0] == 1

# arg1 = func_op.args[1].type
# assert isinstance(arg1, NnMemoryType)
# assert len(arg1.get_shape()) == 1
# assert len(arg1.get_stide()) == 1
# assert arg1.get_shape()[0] == s1
# assert arg1.get_stide()[0] == 1


# arg2 = func_op.args[2].type
# assert isinstance(arg2, NnMemoryType)
# assert len(arg2.get_shape()) == 1
# assert len(arg2.get_stide()) == 1
# assert arg2.get_shape()[0] == s1
# assert arg2.get_stide()[0] == 1

arg3 = func_op.args[3].type

assert isinstance(arg3, SymbolValueType)
assert arg3.is_symbol()
assert arg3.get_value() == s2


arg4 = func_op.args[4].type

assert isinstance(arg4, SymbolValueType)
assert arg4.is_symbol()
assert arg4.get_value() == s3

arg5 = func_op.args[5].type

assert isinstance(arg5, SymbolValueType)
assert not arg5.is_symbol()
assert arg5.get_value() == 2

loop_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolForOp)]
assert len(loop_ops) == 1

loop_body_ops = list(loop_ops[0].body.block.ops)
slice_ops = [op for op in loop_body_ops if isinstance(op, DmaSliceOp)]
deslice_ops = [op for op in loop_body_ops if isinstance(op, DmaDesliceOp)]

assert len(slice_ops) == 2
assert len(deslice_ops) == 1
assert not any(isinstance(op, DmaLoadOp) for op in loop_body_ops)
assert not any(isinstance(op, DmaStoreOp) for op in loop_body_ops)
assert not any(isinstance(op, arith.IndexCastOp) for op in loop_body_ops)
assert list(slice_ops[0].offsets)[0] is loop_ops[0].body.block.args[0]
assert list(deslice_ops[0].offsets)[0] is loop_ops[0].body.block.args[0]
