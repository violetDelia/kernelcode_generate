"""DMA store expectation.
[immutable-file]
创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 dma.store 在 `source.shape` 与 `sizes` 一致时返回 `None`。
- 验证 store 的 `target`、rank、dtype、size、stride 等边界。

使用示例:
- python expectation/operation/dma/store.py

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

from kernel_gen.operation.dma import store
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType
from expectation.utils.random import get_random_alpha_string

# 静态场景下，source.shape 与 sizes 一致时应返回 None。
src = Memory([16, 16], NumericType.Float32, space=MemorySpace.SM)
dst = Memory([64, 64], NumericType.Float32, space=MemorySpace.GM)
result = store(src, dst, offsets=[0, 0], sizes=[16, 16], strides=[1, 1])

assert result is None

# 动态场景下，source.shape 与 sizes 一致时也应返回 None。
tile_m = get_random_alpha_string()
tile_n = get_random_alpha_string()
off_m = get_random_alpha_string()
off_n = get_random_alpha_string()
dynamic_src = Memory([SymbolDim(tile_m), SymbolDim(tile_n)], NumericType.Int32, space=MemorySpace.SM)
dynamic_dst = Memory([SymbolDim(get_random_alpha_string()), SymbolDim(get_random_alpha_string())], NumericType.Int32, space=MemorySpace.GM)
dynamic_result = store(
    dynamic_src,
    dynamic_dst,
    offsets=[SymbolDim(off_m), SymbolDim(off_n)],
    sizes=[SymbolDim(tile_m), SymbolDim(tile_n)],
    strides=[1, 1],
)

assert dynamic_result is None

# source 不是 Memory 时，应显式报错。
with pytest.raises(TypeError):
    store([16, 16], dst, offsets=[0, 0], sizes=[16, 16], strides=[1, 1])

# target 不是 Memory 时，应显式报错。
with pytest.raises(TypeError):
    store(src, [64, 64], offsets=[0, 0], sizes=[16, 16], strides=[1, 1])

# dtype 不一致时，应显式报错。
dtype_mismatch_dst = Memory([64, 64], NumericType.Int32, space=MemorySpace.GM)
with pytest.raises(TypeError):
    store(src, dtype_mismatch_dst, offsets=[0, 0], sizes=[16, 16], strides=[1, 1])

# target 的 rank 与索引列表长度不一致时，应显式报错。
rank_mismatch_dst = Memory([64, 64, 64], NumericType.Float32, space=MemorySpace.GM)
with pytest.raises(ValueError):
    store(src, rank_mismatch_dst, offsets=[0, 0], sizes=[16, 16], strides=[1, 1])

# size 与 source.shape 不一致时，应显式报错。
with pytest.raises(ValueError):
    store(src, dst, offsets=[0, 0], sizes=[8, 16], strides=[1, 1])

# 非法 size 应显式报错。
with pytest.raises(ValueError):
    store(src, dst, offsets=[0, 0], sizes=[0, 16], strides=[1, 1])

# 非单位 stride 只要不越界，就是合法的。
strided_result = store(src, dst, offsets=[0, 20], sizes=[16, 16], strides=[1, 2])

assert strided_result is None

# 静态目标上若 stride 扩大了访问跨度，导致写回范围越界，也应显式报错。
# 这里第二维起点 40，size=16，stride=2，最后访问位置超过 64。
with pytest.raises(ValueError):
    store(src, dst, offsets=[0, 40], sizes=[16, 16], strides=[1, 2])
