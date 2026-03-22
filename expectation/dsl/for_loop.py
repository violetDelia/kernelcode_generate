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

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.symbol_variable.memory import LocalSpaceMeta, Memory, MemorySpace
from kernel_gen.symbol_variable.type import Farmat, NumericType
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.operation.nn import matmul
from kernel_gen.operation.dma import deslice, slice
from kernel_gen.operation.scf import LoopRange
from kernel_gen.dialect.dma import DmaDesliceOp, DmaLoadOp, DmaSliceOp, DmaStoreOp
from kernel_gen.dialect.symbol import SymbolForOp
from kernel_gen.dsl.mlir_gen import build_func_op
from xdsl.dialects.func import FuncOp
from xdsl.dialects import arith

A = Memory(["L"], NumericType.Float32)
B = Memory(["L"], NumericType.Float32)
C = Memory(["L"], NumericType.Float32)
start = SymbolDim("start")
end = SymbolDim("end")
step = SymbolDim("step")


def add(A, B, C, end, start, step):
    for index in LoopRange(start, end, step):
        SA = slice(A, [index], [step], [1], MemorySpace.LM)
        SB = slice(B, [index], [step], [1], MemorySpace.LM)
        SC = SA + SB
        deslice(SC, C, [index], [step], [1], MemorySpace.LM)


func_op = build_func_op(add)
print(func_op)
assert isinstance(func_op, FuncOp)
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
