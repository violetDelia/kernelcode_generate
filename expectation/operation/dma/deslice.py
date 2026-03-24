"""DMA deslice expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 dma.deslice 在 `source.shape` 与 `sizes` 一致时返回 `None`。
- 验证 `dst` 必须是有效的 Memory，且静态/动态场景都需要通过合法性校验。

使用示例:
- python expectation/operation/dma/deslice.py

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

from kernel_gen.operation.dma import deslice
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType
from expectation.utils.random import get_random_alpha_string

# 静态 dst 合法时，deslice 应返回 None。
static_src = Memory([16, 16], NumericType.Float32, space=MemorySpace.SM)
static_dst = Memory([64, 64], NumericType.Float32, space=MemorySpace.GM)
static_result = deslice(static_src, static_dst, offsets=[0, 0], sizes=[16, 16], strides=[1, 1])

assert static_result is None

# 动态 dst 合法时，deslice 也应返回 None。
tile_m = get_random_alpha_string()
tile_n = get_random_alpha_string()
dst_m = get_random_alpha_string()
dst_n = get_random_alpha_string()
off_m = get_random_alpha_string()
off_n = get_random_alpha_string()
dynamic_src = Memory([SymbolDim(tile_m), SymbolDim(tile_n)], NumericType.Float32, space=MemorySpace.SM)
dynamic_dst = Memory([SymbolDim(dst_m), SymbolDim(dst_n)], NumericType.Float32, space=MemorySpace.GM)
dynamic_result = deslice(
    dynamic_src,
    dynamic_dst,
    offsets=[SymbolDim(off_m), SymbolDim(off_n)],
    sizes=[SymbolDim(tile_m), SymbolDim(tile_n)],
    strides=[1, 1],
)

assert dynamic_result is None

# dst 不是 Memory 时，应显式报错。
with pytest.raises(TypeError):
    deslice(static_src, [64, 64], offsets=[0, 0], sizes=[16, 16], strides=[1, 1])

# dst 的 dtype 与 source 不一致时，应显式报错。
dtype_mismatch_dst = Memory([64, 64], NumericType.Int32, space=MemorySpace.GM)
with pytest.raises(TypeError):
    deslice(static_src, dtype_mismatch_dst, offsets=[0, 0], sizes=[16, 16], strides=[1, 1])

# dst 的 rank 与索引列表长度不一致时，应显式报错。
rank_mismatch_dst = Memory([64, 64, 64], NumericType.Float32, space=MemorySpace.GM)
with pytest.raises(ValueError):
    deslice(static_src, rank_mismatch_dst, offsets=[0, 0], sizes=[16, 16], strides=[1, 1])

# 动态 dst 的 rank 与索引列表长度不一致时，也应显式报错。
batch_dim = get_random_alpha_string()
dynamic_rank_mismatch_dst = Memory(
    [SymbolDim(batch_dim), SymbolDim(dst_m), SymbolDim(dst_n)],
    NumericType.Float32,
    space=MemorySpace.GM,
)
with pytest.raises(ValueError):
    deslice(
        dynamic_src,
        dynamic_rank_mismatch_dst,
        offsets=[SymbolDim(off_m), SymbolDim(off_n)],
        sizes=[SymbolDim(tile_m), SymbolDim(tile_n)],
        strides=[1, 1],
    )

# 静态 dst 上若 offsets 与 sizes 组合后越界，应显式报错。
# 这里用第二维 60 + 16 > 64 表达写回范围超出目标边界。
with pytest.raises(ValueError):
    deslice(
        static_src,
        static_dst,
        offsets=[0, 60],
        sizes=[16, 16],
        strides=[1, 1],
    )

# 静态 dst 上非单位 stride 只要不越界，就是合法的。
strided_result = deslice(
    static_src,
    static_dst,
    offsets=[0, 20],
    sizes=[16, 16],
    strides=[1, 2],
)

assert strided_result is None

# 静态 dst 上若 stride 扩大了访问跨度，导致写回范围越界，也应显式报错。
# 这里用第二维起点 40，size=16，stride=2，最后访问位置超过 64。
with pytest.raises(ValueError):
    deslice(
        static_src,
        static_dst,
        offsets=[0, 40],
        sizes=[16, 16],
        strides=[1, 2],
    )
