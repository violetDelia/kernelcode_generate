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
from kernel_gen.dsl.mlir_gen import build_func_op
from xdsl.dialects.func import FuncOp

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

assert isinstance(func_op, FuncOp)
