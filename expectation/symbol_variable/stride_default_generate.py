from kernel_gen.symbol_variable.memory import LocalSpaceMeta, Memory, MemorySpace
from kernel_gen.symbol_variable.type import Farmat, NumericType
from kernel_gen.symbol_variable.symbol_dim import SymbolDim


m = SymbolDim("M")
k = SymbolDim("K")
n = SymbolDim("N")


Tenosr_A = Memory([m, k, n], NumericType.Float32)
assert (
    Tenosr_A.__str__()
    == "Memory(GM,Tensor(shape=Shape(M, K, N), dtype=NumericType.Float32, stride=Shape(K*N, N, 1), format=Farmat.Norm))"
)
