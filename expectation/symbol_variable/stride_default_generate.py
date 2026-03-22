"""Stride default generate expectation.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 验证 Memory 默认 stride 生成与字符串表示。

使用示例:
- python expectation/symbol_variable/stride_default_generate.py

关联文件:
- spec: spec/symbol_variable/memory.md
- test: test/symbol_variable/test_memory.py
- 功能实现: kernel_gen/symbol_variable/memory.py
"""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


m = SymbolDim("M")
k = SymbolDim("K")
n = SymbolDim("N")


tensor_a = Memory([m, k, n], NumericType.Float32)
assert (
    str(tensor_a)
    == "Memory(GM,Tensor(shape=Shape(M, K, N), dtype=NumericType.Float32, stride=Shape(K*N, N, 1), format=Farmat.Norm))"
)
