"""DMA free expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 dma.free 接受合法的 Memory 并返回 `None`。
- 验证 dma.free 只校验输入是否为 Memory，不依赖具体的 `shape/dtype/space/format`。

使用示例:
- python expectation/operation/dma/free.py

关联文件:
- spec: spec/operation/dma.md
- test: test/operation/test_operation_dma.py
- 功能实现: kernel_gen/operation/dma.py
"""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
# 直接执行 expectation 脚本时，先移除脚本所在目录，避免同目录文件名污染导入链。
sys.path = [
    search_path
    for search_path in sys.path
    if Path(search_path or ".").resolve() != SCRIPT_DIR
]

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest

from kernel_gen.operation.dma import free
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import Farmat, NumericType
from expectation.utils.random import get_random_alpha_string

# 静态 Memory 应可被正常释放，并返回 None。
static_buf = Memory([32, 32], NumericType.Float32, space=MemorySpace.GM, format=Farmat.Norm)
static_result = free(static_buf)

assert static_result is None

# 动态 Memory 也应可被正常释放，并返回 None。
dyn_m = get_random_alpha_string()
dyn_n = get_random_alpha_string()
dynamic_buf = Memory(
    [SymbolDim(dyn_m), SymbolDim(dyn_n)],
    NumericType.Int32,
    space=MemorySpace.SM,
    format=Farmat.CLast,
)
dynamic_result = free(dynamic_buf)

assert dynamic_result is None

# 不同 space/format 的 Memory 也应被接受。
local_buf = Memory([16], NumericType.Float16, space=MemorySpace.LM, format=Farmat.Norm)
local_result = free(local_buf)

assert local_result is None

# 输入不是 Memory 时，应显式报错。
with pytest.raises(TypeError):
    free([32, 32])

with pytest.raises(TypeError):
    free("buffer")

with pytest.raises(TypeError):
    free(None)
