"""DMA flatten expectation.
[immutable-file]
创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 dma.flatten 返回一维 Memory。
- 验证 flatten 会保留 source 的 `dtype/space/format`，并将 `stride` 规整为 `[1]`。
- 验证 flatten 仅接受连续布局的 Memory。

使用示例:
- python expectation/operation/dma/flatten.py

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

from kernel_gen.operation.dma import flatten
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import Farmat, NumericType
from expectation.utils.random import get_random_alpha_string

# 静态连续布局 flatten 后，应返回一维 shape，且 stride 固定为 [1]。
static_src = Memory(
    [2, 3, 4],
    NumericType.Float32,
    space=MemorySpace.SM,
    format=Farmat.CLast,
)
static_dst = flatten(static_src)

assert static_dst.get_shape() == [24]
assert static_dst.get_stride() == [1]
assert static_dst.get_type() is NumericType.Float32
assert static_dst.get_space() is MemorySpace.SM
assert static_dst.get_format() is Farmat.CLast

# 动态连续布局 flatten 后，应返回一维动态乘积表达式，且保留 source 元信息。
dyn_m = get_random_alpha_string()
dyn_n = get_random_alpha_string()
dyn_k = get_random_alpha_string()
dynamic_src = Memory(
    [SymbolDim(dyn_m), SymbolDim(dyn_n), SymbolDim(dyn_k)],
    NumericType.Int32,
    space=MemorySpace.GM,
    format=Farmat.Norm,
)
dynamic_dst = flatten(dynamic_src)

assert len(dynamic_dst.get_shape()) == 1
assert dynamic_dst.get_shape()[0] == (SymbolDim(dyn_m) * SymbolDim(dyn_n) * SymbolDim(dyn_k)).get_value()
assert dynamic_dst.get_stride() == [1]
assert dynamic_dst.get_type() is NumericType.Int32
assert dynamic_dst.get_space() is MemorySpace.GM
assert dynamic_dst.get_format() is Farmat.Norm

# 一维连续布局 flatten 后，应保持为一维并返回自身长度。
vector_symbol = get_random_alpha_string()
vector_src = Memory([SymbolDim(vector_symbol)], NumericType.Float16, space=MemorySpace.LM, format=Farmat.Norm)
vector_dst = flatten(vector_src)

assert vector_dst.get_shape() == [vector_symbol]
assert vector_dst.get_stride() == [1]
assert vector_dst.get_type() is NumericType.Float16
assert vector_dst.get_space() is MemorySpace.LM
assert vector_dst.get_format() is Farmat.Norm

# 非连续布局不应被接受。
non_contiguous_src = Memory([2, 3, 4], NumericType.Float32, stride=[1, 1, 1], format=Farmat.Norm)
with pytest.raises(ValueError):
    flatten(non_contiguous_src)

# source 不是 Memory 时，应显式报错。
with pytest.raises(TypeError):
    flatten([2, 3, 4])
