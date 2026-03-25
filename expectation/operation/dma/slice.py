"""DMA slice expectation.
[immutable-file]
创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 dma.slice 返回 `shape` 等于 `sizes` 的结果块。
- 验证 slice 的结果 `space` 默认继承 `source`，显式传参时与参数一致。
- 验证 slice 的参数边界与 load 保持一致。

使用示例:
- python expectation/operation/dma/slice.py

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

from kernel_gen.operation.dma import slice
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType
from expectation.utils.random import get_random_alpha_string

# 默认不传 space 时，应继承 source 的空间。
src = Memory([64, 64], NumericType.Float32, space=MemorySpace.GM)
default_sub = slice(src, offsets=[0, 16], sizes=[8, 8], strides=[1, 1])

assert default_sub.get_shape() == [8, 8]
assert default_sub.get_type() is NumericType.Float32
assert default_sub.get_space() is MemorySpace.GM
assert default_sub.get_stride() == [8, 1]

# 显式传入 space 时，结果应切换到目标空间。
sub = slice(src, offsets=[0, 16], sizes=[8, 8], strides=[1, 1], space=MemorySpace.LM)

assert sub.get_shape() == [8, 8]
assert sub.get_type() is NumericType.Float32
assert sub.get_space() is MemorySpace.LM
assert sub.get_stride() == [8, 1]

# 动态 shape 也应正常支持。
dyn_m = get_random_alpha_string()
dyn_n = get_random_alpha_string()
off_m = get_random_alpha_string()
off_n = get_random_alpha_string()
dynamic_src = Memory([SymbolDim(dyn_m), SymbolDim(dyn_n)], NumericType.Int32, space=MemorySpace.SM)
dynamic_sub = slice(
    dynamic_src,
    offsets=[SymbolDim(off_m), SymbolDim(off_n)],
    sizes=[1, SymbolDim(dyn_n)],
    strides=[1, 1],
    space=MemorySpace.GM,
)

assert dynamic_sub.get_shape() == [1, dyn_n]
assert dynamic_sub.get_type() is NumericType.Int32
assert dynamic_sub.get_space() is MemorySpace.GM
assert dynamic_sub.get_stride() == [dyn_n, 1]

# source 不是 Memory 时，应显式报错。
with pytest.raises(TypeError):
    slice([64, 64], offsets=[0, 16], sizes=[8, 8], strides=[1, 1])

# rank 不一致时，应显式报错。
with pytest.raises(ValueError):
    slice(src, offsets=[0], sizes=[8, 8], strides=[1, 1])

# 非法 size 应显式报错。
with pytest.raises(ValueError):
    slice(src, offsets=[0, 16], sizes=[0, 8], strides=[1, 1])

# 非单位 stride 的 slice 也是合法的，返回结果仍由 sizes 决定。
strided_sub = slice(src, offsets=[0, 16], sizes=[8, 8], strides=[1, 2])

assert strided_sub.get_shape() == [8, 8]
assert strided_sub.get_type() is NumericType.Float32
assert strided_sub.get_space() is MemorySpace.GM
assert strided_sub.get_stride() == [8, 1]

# 静态 shape 下如果 stride 扩大访问跨度后越界，应显式报错。
# 这里第二维从 56 开始取 8 个元素，stride=2，最后访问位置超过 64。
with pytest.raises(ValueError):
    slice(src, offsets=[0, 56], sizes=[8, 8], strides=[1, 2])
