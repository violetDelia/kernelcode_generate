"""DMA cast expectation.
[immutable-file]
创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 dma.cast 在 `memoryspace=None` 时继承输入 spec，仅替换 dtype。
- 验证 dma.cast 显式传入 `memoryspace` 时，结果 `space` 与参数一致，其余 spec 与 `source` 保持一致。

使用示例:
- python expectation/operation/dma/cast.py

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

from kernel_gen.operation.dma import cast
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import Farmat, NumericType
from expectation.utils.random import get_random_alpha_string, get_random_non_zero_int

# 默认参数 memoryspace=None 时，应继承输入的 spec，仅替换 dtype。
s1 = get_random_alpha_string()
s2 = get_random_alpha_string()

src = Memory(
    [s1, s2],
    NumericType.Int32,
    space=MemorySpace.SM,
    stride=[1, 1],
    format=Farmat.CLast,
)
dst = cast(src, NumericType.Int64)

assert dst.get_shape() == [s1, s2]
assert dst.get_stride() == [1, 1]
assert dst.get_space() is MemorySpace.SM
assert dst.get_format() is Farmat.CLast
assert dst.get_type() is NumericType.Int64

# 显式传入 memoryspace 时，结果的 space 应与参数一致，其他 spec 与 source 保持一致。
override_dst = cast(src, NumericType.Int64, memoryspace=MemorySpace.GM)

assert override_dst.get_shape() == [s1, s2]
assert override_dst.get_stride() == [1, 1]
assert override_dst.get_space() is MemorySpace.GM
assert override_dst.get_format() is Farmat.CLast
assert override_dst.get_type() is NumericType.Int64
assert override_dst.get_shape() == src.get_shape()
assert override_dst.get_stride() == src.get_stride()
assert override_dst.get_format() is src.get_format()

# 动态 shape/stride 场景下，也应保持 source 的元信息，仅替换 dtype。
dyn_m = get_random_alpha_string()
dyn_n = get_random_alpha_string()
dyn_stride = get_random_non_zero_int(2, 8)
dynamic_src = Memory(
    [SymbolDim(dyn_m), SymbolDim(dyn_n)],
    NumericType.Float32,
    space=MemorySpace.LM,
    stride=[SymbolDim(dyn_stride) * SymbolDim(dyn_n), 1],
    format=Farmat.Norm,
)
dynamic_dst = cast(dynamic_src, NumericType.Float16)

assert dynamic_dst.get_shape() == dynamic_src.get_shape()
assert dynamic_dst.get_stride() == dynamic_src.get_stride()
assert dynamic_dst.get_space() is dynamic_src.get_space()
assert dynamic_dst.get_format() is dynamic_src.get_format()
assert dynamic_dst.get_type() is NumericType.Float16

# 显式覆盖 memoryspace 时，动态元信息也应保持不变，仅 space 按参数覆盖。
dynamic_override_dst = cast(dynamic_src, NumericType.Float16, memoryspace=MemorySpace.GM)

assert dynamic_override_dst.get_shape() == dynamic_src.get_shape()
assert dynamic_override_dst.get_stride() == dynamic_src.get_stride()
assert dynamic_override_dst.get_space() is MemorySpace.GM
assert dynamic_override_dst.get_format() is dynamic_src.get_format()
assert dynamic_override_dst.get_type() is NumericType.Float16

# source 不是 Memory 时，应显式报错。
with pytest.raises(TypeError):
    cast([s1, s2], NumericType.Int64)

# dtype 不是 NumericType 时，应显式报错。
with pytest.raises(TypeError):
    cast(src, "int64")
