"""DMA copy expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 dma.copy 的第二个参数为目标 `space`。
- 验证 dma.copy 的返回值规则与 dma.cast 一致。
- 验证返回结果的 `space` 与参数一致，其余 spec 与 `source` 保持一致。

使用示例:
- python expectation/operation/dma/copy.py

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

from kernel_gen.operation.dma import copy
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import Farmat, NumericType
from expectation.utils.random import get_random_alpha_string, get_random_non_zero_int

# copy 的第二个参数应是目标 space。
# 返回值的 space 与参数一致，其余 spec 与 source 保持一致。
s1 = get_random_alpha_string()
s2 = get_random_alpha_string()

src = Memory(
    [s1, s2],
    NumericType.Float32,
    space=MemorySpace.GM,
    stride=[1, 1],
    format=Farmat.CLast,
)
result = copy(src, MemorySpace.SM)

assert isinstance(result, Memory)
assert result.get_shape() == src.get_shape()
assert result.get_stride() == src.get_stride()
assert result.get_type() is src.get_type()
assert result.get_format() is src.get_format()
assert result.get_space() is MemorySpace.SM

# 传入与 source 相同的目标 space 时，也应返回新的 Memory 描述。
same_space_result = copy(src, MemorySpace.GM)

assert isinstance(same_space_result, Memory)
assert same_space_result.get_shape() == src.get_shape()
assert same_space_result.get_stride() == src.get_stride()
assert same_space_result.get_type() is src.get_type()
assert same_space_result.get_format() is src.get_format()
assert same_space_result.get_space() is MemorySpace.GM

# 动态 shape/stride 场景下，返回结果也应仅覆盖目标 space。
dyn_m = get_random_alpha_string()
dyn_n = get_random_alpha_string()
dyn_stride = get_random_non_zero_int(2, 8)
dynamic_src = Memory(
    [SymbolDim(dyn_m), SymbolDim(dyn_n)],
    NumericType.Int32,
    space=MemorySpace.SM,
    stride=[SymbolDim(dyn_stride) * SymbolDim(dyn_n), 1],
    format=Farmat.Norm,
)
dynamic_result = copy(dynamic_src, MemorySpace.LM)

assert isinstance(dynamic_result, Memory)
assert dynamic_result.get_shape() == dynamic_src.get_shape()
assert dynamic_result.get_stride() == dynamic_src.get_stride()
assert dynamic_result.get_type() is dynamic_src.get_type()
assert dynamic_result.get_format() is dynamic_src.get_format()
assert dynamic_result.get_space() is MemorySpace.LM

# source 不是 Memory 时，应显式报错。
with pytest.raises(TypeError):
    copy([s1, s2], MemorySpace.SM)

# 第二个参数不是 MemorySpace 时，应显式报错。
with pytest.raises(TypeError):
    copy(src, "SM")
