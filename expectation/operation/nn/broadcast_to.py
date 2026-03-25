"""NN broadcast_to expectation.
[immutable-file]
创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 nn.broadcast_to 可按公开接口把 singleton dim 扩张到目标 shape。
- 验证 nn.broadcast_to 的返回值与目标 target 描述完全一致。

使用示例:
- python expectation/operation/nn/broadcast_to.py

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/test_operation_nn.py
- 功能实现: kernel_gen/operation/nn.py
"""

from pathlib import Path
import sys

import pytest

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) in sys.path:
    sys.path.remove(str(CURRENT_DIR))

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.operation.nn import broadcast as broadcast_to
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import Farmat, NumericType
from expectation.utils.random import get_random_alpha_string, get_random_non_zero_int

s1 = get_random_alpha_string()
s2 = get_random_alpha_string()
s3 = get_random_alpha_string()
invalid_dim = get_random_non_zero_int(2, 8)

# singleton 维度显式扩张后，返回值应与 target 的描述完全一致。
value = Memory([1, s2], NumericType.Float32, space=MemorySpace.SM, format=Farmat.CLast)
target = Memory(
    [s1, s2],
    NumericType.Float32,
    space=MemorySpace.LM,
    stride=[s2, 1],
    format=Farmat.Norm,
)
result = broadcast_to(value, target)

assert result.get_shape() == target.get_shape()
assert result.get_type() is target.get_type()
assert result.get_space() is target.get_space()
assert result.get_format() is target.get_format()
assert result.get_stride() == target.get_stride()

# 低 rank 输入应允许前置补维后再扩张，且结果与 target 完全一致。
vector = Memory([s3], NumericType.Float32, space=MemorySpace.LM, format=Farmat.Norm)
vector_target = Memory(
    [s1, s3],
    NumericType.Float32,
    space=MemorySpace.GM,
    stride=[s3, 1],
    format=Farmat.CLast,
)
vector_result = broadcast_to(vector, vector_target)

assert vector_result.get_shape() == vector_target.get_shape()
assert vector_result.get_type() is vector_target.get_type()
assert vector_result.get_space() is vector_target.get_space()
assert vector_result.get_format() is vector_target.get_format()
assert vector_result.get_stride() == vector_target.get_stride()

# 两个 singleton 维度同时扩张时，结果也应与 target 完全一致。
two_dim_value = Memory([1, 1, s3], NumericType.Float32, space=MemorySpace.SM, format=Farmat.CLast)
two_dim_target = Memory(
    [s1, s2, s3],
    NumericType.Float32,
    space=MemorySpace.TSM,
    stride=[SymbolDim(s2) * SymbolDim(s3), s3, 1],
    format=Farmat.Norm,
)
two_dim_result = broadcast_to(two_dim_value, two_dim_target)

assert two_dim_result.get_shape() == two_dim_target.get_shape()
assert two_dim_result.get_type() is two_dim_target.get_type()
assert two_dim_result.get_space() is two_dim_target.get_space()
assert two_dim_result.get_format() is two_dim_target.get_format()
assert two_dim_result.get_stride() == two_dim_target.get_stride()

# 目标 shape 与输入 shape 相同，结果仍应与 target 的完整描述一致。
same_shape = Memory([s1, s2], NumericType.Float32, space=MemorySpace.GM)
same_target = Memory(
    [s1, s2],
    NumericType.Float32,
    space=MemorySpace.SM,
    stride=[s2, 1],
    format=Farmat.CLast,
)
same_result = broadcast_to(same_shape, same_target)

assert same_result.get_shape() == same_target.get_shape()
assert same_result.get_type() is same_target.get_type()
assert same_result.get_space() is same_target.get_space()
assert same_result.get_format() is same_target.get_format()
assert same_result.get_stride() == same_target.get_stride()

# target 作为输出描述时，返回值应在 shape/stride/space/format 上完全与 target 对齐。
explicit_target = Memory(
    [s1, s2],
    NumericType.Float32,
    space=MemorySpace.TLM,
    stride=[s2, 1],
    format=Farmat.CLast,
)
explicit_result = broadcast_to(value, explicit_target)

assert explicit_result.get_shape() == explicit_target.get_shape()
assert explicit_result.get_type() is explicit_target.get_type()
assert explicit_result.get_space() is explicit_target.get_space()
assert explicit_result.get_format() is explicit_target.get_format()
assert explicit_result.get_stride() == explicit_target.get_stride()

# 目标 rank 小于输入 rank 时，应显式报错。
with pytest.raises(ValueError):
    broadcast_to(same_shape, Memory([s2], NumericType.Float32, space=MemorySpace.GM))

# 非 singleton 维度不兼容时，应显式报错。
with pytest.raises(ValueError):
    broadcast_to(
        same_shape,
        Memory([invalid_dim, s2], NumericType.Float32, space=MemorySpace.GM),
    )
