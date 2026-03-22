from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.symbol_variable.memory import LocalSpaceMeta, Memory, MemorySpace
from kernel_gen.symbol_variable.type import Farmat, NumericType
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.operation.nn import matmul
from kernel_gen.dsl.mlir_gen import build_func_op
from xdsl.dialects.func import FuncOp

A = Memory(["N", 32], NumericType.Float32, stride=["C", 1])
B = Memory(["N", 32], NumericType.Float32, stride=["C", 1])

def add(A, B):
    C = A + B
    return C

func_op = build_func_op(add)
print(func_op)
assert func_op.__str__() == '''func.func @add(%0 : !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>, %1 : !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>) -> !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>> {
  %2 = "nn.add"(%0, %1) {space = #nn.space<global>} : (!nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>, !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>) -> !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>
  func.return %2 : !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>
}'''
