"""DMA view expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 dma.view 返回 `shape` 等于 `size` 的子视图。
- 验证默认情况下继承 `source` 的 `dtype/space/stride/format`。
- 验证 view 没有 `space` 参数，结果 `space` 与 `source` 一致。
- 验证 view 的 rank 与 size 边界。

使用示例:
- python expectation/operation/dma/view.py

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

from kernel_gen.operation.dma import view
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import Farmat, NumericType
from expectation.utils.random import get_random_alpha_string

# view 只接收 source、offset、size、stride 四类参数；
# 结果应继承 source 的规格，仅将 shape 改为 size。
s1 = get_random_alpha_string()
s2 = get_random_alpha_string()
o1 = get_random_alpha_string()
o2 = get_random_alpha_string()
src = Memory([SymbolDim(s1), SymbolDim(s2)], NumericType.Float32, space=MemorySpace.GM, format=Farmat.CLast)
dst = view(src, offset=[SymbolDim(o1), SymbolDim(o2)], size=[2, 2], stride=[1, 1])

assert dst.get_shape() == [2, 2]
assert dst.get_type() is NumericType.Float32
assert dst.get_space() is MemorySpace.GM
assert dst.get_format() is Farmat.CLast
assert dst.get_stride() == src.get_stride()

# 动态 size 也应正常支持。
tile_m = get_random_alpha_string()
dynamic_dst = view(
    src,
    offset=[SymbolDim(o1), SymbolDim(o2)],
    size=[SymbolDim(tile_m), 1],
    stride=[1, 1],
)

assert dynamic_dst.get_shape() == [tile_m, 1]
assert dynamic_dst.get_type() is NumericType.Float32
assert dynamic_dst.get_space() is MemorySpace.GM

# source 不是 Memory 时，应显式报错。
with pytest.raises(TypeError):
    view([s1, s2], offset=[0, 0], size=[2, 2], stride=[1, 1])

# offset/size/stride 的 rank 不一致时，应显式报错。
with pytest.raises(ValueError):
    view(src, offset=[0], size=[2, 2], stride=[1, 1])

with pytest.raises(ValueError):
    view(src, offset=[0, 0], size=[2], stride=[1, 1])

with pytest.raises(ValueError):
    view(src, offset=[0, 0], size=[2, 2], stride=[1])

# size 中存在非正静态值时，应显式报错。
with pytest.raises(ValueError):
    view(src, offset=[0, 0], size=[0, 2], stride=[1, 1])

# 静态 shape 下若 offset 与 size 组合后越界，应显式报错。
# 这里第二维从 15 开始取 2 个元素，最后访问位置超过静态上界。
static_src = Memory([8, 16], NumericType.Float32, space=MemorySpace.GM, format=Farmat.Norm)
with pytest.raises(ValueError):
    view(static_src, offset=[0, 15], size=[2, 2], stride=[1, 1])

# 静态 shape 下若 stride 扩大访问跨度后越界，也应显式报错。
# 这里第二维从 14 开始取 2 个元素，stride=2，最后访问位置超过 16。
with pytest.raises(ValueError):
    view(static_src, offset=[0, 14], size=[2, 2], stride=[1, 2])
