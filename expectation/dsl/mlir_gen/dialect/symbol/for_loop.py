"""symbol.for expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 使用函数 + `build_func_op` 组织 `symbol.for` 对应的 expectation。
- 验证 `LoopRange` 会被 lowering 为 `symbol.for`，并保留循环体中的 DMA 行为。

使用示例:
- python expectation/temp/symbol/for_loop.py

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: kernel_gen/dsl/mlir_gen.py
"""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xdsl.dialects import arith
from xdsl.dialects.func import FuncOp

from expectation.utils.random import get_random_alpha_string, get_random_non_zero_int
from kernel_gen.dialect.dma import DmaDesliceOp, DmaLoadOp, DmaSliceOp, DmaStoreOp
from kernel_gen.dialect.symbol import SymbolForOp, SymbolValueType
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.operation.dma import deslice, slice
from kernel_gen.operation.scf import LoopRange
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

DIM_NAME = get_random_alpha_string().upper()
START = SymbolDim(get_random_alpha_string().upper())
END = SymbolDim(get_random_alpha_string().upper())
STEP = SymbolDim(get_random_non_zero_int(1, 4))
A = Memory([DIM_NAME], NumericType.Float32)
B = Memory([DIM_NAME], NumericType.Float32)
C = Memory([DIM_NAME], NumericType.Float32)


def add(a, b, c, start, end, step):
    for index in LoopRange(start, end, step):
        slice_a = slice(a, [index], [step], [1])
        slice_b = slice(b, [index], [step], [1])
        slice_c = slice_a + slice_b
        deslice(slice_c, c, [index], [step], [1])


func_op = build_func_op(add, A, B, C, START, END, STEP)
assert isinstance(func_op, FuncOp)

arg3 = func_op.args[3].type
arg4 = func_op.args[4].type
arg5 = func_op.args[5].type
assert isinstance(arg3, SymbolValueType)
assert isinstance(arg4, SymbolValueType)
assert isinstance(arg5, SymbolValueType)
assert arg3.get_value() == START.get_value()
assert arg4.get_value() == END.get_value()
assert arg5.get_value() == STEP.get_value()

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
