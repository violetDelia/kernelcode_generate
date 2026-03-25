"""DMA reshape expectation.
[immutable-file]
创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 dma.reshape 返回新 shape，并按连续布局生成默认 stride。
- 验证 reshape 会保留 `dtype/space/format`。
- 验证 reshape 的连续性与元素总数边界。

使用示例:
- python expectation/operation/dma/reshape.py

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

from kernel_gen.operation.dma import reshape
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import Farmat, NumericType
from expectation.utils.random import get_random_alpha_string

# 静态连续布局 reshape 后，应返回目标 shape 和默认连续 stride。
src = Memory([2, 3, 4], NumericType.Float32, space=MemorySpace.SM, format=Farmat.CLast)
dst = reshape(src, shape=[6, 4])

assert dst.get_shape() == [6, 4]
assert dst.get_stride() == [4, 1]
assert dst.get_type() is NumericType.Float32
assert dst.get_space() is MemorySpace.SM
assert dst.get_format() is Farmat.CLast

# 动态 shape 在元素总数可保持一致时，也应支持 reshape。
dyn_m = get_random_alpha_string()
dyn_n = get_random_alpha_string()
dynamic_src = Memory([SymbolDim(dyn_m), 4], NumericType.Int32, space=MemorySpace.GM, format=Farmat.Norm)
dynamic_dst = reshape(dynamic_src, shape=[2, SymbolDim(dyn_m) * SymbolDim(2)])

assert len(dynamic_dst.get_shape()) == 2
assert dynamic_dst.get_type() is NumericType.Int32
assert dynamic_dst.get_space() is MemorySpace.GM
assert dynamic_dst.get_format() is Farmat.Norm

# source 不是 Memory 时，应显式报错。
with pytest.raises(TypeError):
    reshape([2, 3, 4], shape=[6, 4])

# shape 非法时，应显式报错。
with pytest.raises(ValueError):
    reshape(src, shape="6x4")

# 元素总数可判定不一致时，应显式报错。
with pytest.raises(ValueError):
    reshape(src, shape=[5, 4])

# 非连续布局不应被接受。
non_contiguous_src = Memory([2, 3, 4], NumericType.Float32, stride=[1, 1, 1], format=Farmat.Norm)
with pytest.raises(ValueError):
    reshape(non_contiguous_src, shape=[6, 4])
