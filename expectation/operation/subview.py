"""DMA subview expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 构造 subview 相关的符号维度与内存对象，作为 DMA `view` 场景的期望输入。

使用示例:
- python expectation/operation/subview.py

关联文件:
- spec: spec/operation/dma.md
- test: test/operation/test_dma.py
- 功能实现: kernel_gen/operation/dma.py
"""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.operation.dma import view
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

m = SymbolDim("M")
k = SymbolDim("K")
n = SymbolDim("N")
m_tile = SymbolDim("M_t")
k_tile = SymbolDim("K_t")
stride = SymbolDim("stride")

src = Memory([m, k], NumericType.Float32)
sub = view(src, [m_tile, k_tile], [2, 2], [stride, 1])

assert sub == Memory([2, 2], NumericType.Float32)
