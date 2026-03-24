"""DMA load expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 dma.load 返回指定 `sizes` 的块，并继承 `source` 的 `dtype/format`。
- 验证 dma.load 的结果 `space` 在默认情况下继承 `source`，显式传参时与参数一致。
- 验证 load 的 rank、size、stride 与参数类型边界。

使用示例:
- python expectation/operation/dma/load.py

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

from kernel_gen.operation.dma import load
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import Farmat, NumericType
from expectation.utils.random import get_random_alpha_string

# 默认不传 space 时，应继承 source 的空间，并返回由 sizes 决定的块。
src = Memory([8, 16], NumericType.Float32, space=MemorySpace.GM, format=Farmat.CLast)
default_tile = load(src, offsets=[0, 0], sizes=[2, 4], strides=[1, 1])

assert default_tile.get_shape() == [2, 4]
assert default_tile.get_type() is NumericType.Float32
assert default_tile.get_space() is MemorySpace.GM
assert default_tile.get_format() is Farmat.CLast
assert default_tile.get_stride() == [4, 1]

# 显式传入 space 时，结果 space 应与参数一致，其余元信息继承 source。
space_tile = load(src, offsets=[0, 0], sizes=[2, 4], strides=[1, 1], space=MemorySpace.SM)

assert space_tile.get_shape() == [2, 4]
assert space_tile.get_type() is NumericType.Float32
assert space_tile.get_space() is MemorySpace.SM
assert space_tile.get_format() is Farmat.CLast
assert space_tile.get_stride() == [4, 1]

# 动态 shape 的 load 也应正常返回，并使用随机 symbol。
dyn_m = get_random_alpha_string()
dyn_n = get_random_alpha_string()
off_m = get_random_alpha_string()
off_n = get_random_alpha_string()
dynamic_src = Memory([SymbolDim(dyn_m), SymbolDim(dyn_n)], NumericType.Int32, space=MemorySpace.GM)
dynamic_tile = load(
    dynamic_src,
    offsets=[SymbolDim(off_m), SymbolDim(off_n)],
    sizes=[SymbolDim(dyn_m), 1],
    strides=[1, 1],
    space=MemorySpace.LM,
)

assert dynamic_tile.get_shape() == [dyn_m, 1]
assert dynamic_tile.get_type() is NumericType.Int32
assert dynamic_tile.get_space() is MemorySpace.LM
assert dynamic_tile.get_stride() == [1, 1]

# source 不是 Memory 时，应显式报错。
with pytest.raises(TypeError):
    load([8, 16], offsets=[0, 0], sizes=[2, 4], strides=[1, 1])

# space 不是 MemorySpace 时，应显式报错。
with pytest.raises(TypeError):
    load(src, offsets=[0, 0], sizes=[2, 4], strides=[1, 1], space="SM")

# offsets/sizes/strides 的 rank 与 source 不一致时，应显式报错。
with pytest.raises(ValueError):
    load(src, offsets=[0], sizes=[2, 4], strides=[1, 1])

with pytest.raises(ValueError):
    load(src, offsets=[0, 0], sizes=[2], strides=[1, 1])

with pytest.raises(ValueError):
    load(src, offsets=[0, 0], sizes=[2, 4], strides=[1])

# size 中存在非正静态值时，应显式报错。
with pytest.raises(ValueError):
    load(src, offsets=[0, 0], sizes=[0, 4], strides=[1, 1])

# 非单位 stride 的 load 也是合法的，返回结果仍由 sizes 决定。
strided_tile = load(src, offsets=[0, 0], sizes=[2, 4], strides=[1, 2])

assert strided_tile.get_shape() == [2, 4]
assert strided_tile.get_type() is NumericType.Float32
assert strided_tile.get_space() is MemorySpace.GM
assert strided_tile.get_format() is Farmat.CLast
assert strided_tile.get_stride() == [4, 1]

# 静态 shape 下如果 stride 扩大访问跨度后越界，应显式报错。
# 这里第二维从 12 开始取 4 个元素，stride=2，最后访问位置超过 16。
with pytest.raises(ValueError):
    load(src, offsets=[0, 12], sizes=[2, 4], strides=[1, 2])
