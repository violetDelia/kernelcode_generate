"""NN matmul expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 nn.matmul 返回二维矩阵乘结果。
- 验证 lhs/rhs dtype 不一致时，结果返回较低优先级的 dtype。
- 验证 matmul 的 `memoryspace=None` 时继承输入 spec。
- 验证 matmul 显式传入 `memoryspace` 时仅覆盖结果 space，且 lhs/rhs 的 space 必须相同。

使用示例:
- python expectation/operation/nn/matmul.py

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

from kernel_gen.operation.nn import matmul
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import Farmat, NumericType
from expectation.utils.random import get_random_alpha_string, get_random_non_zero_int

PROMOTION_ORDER = {
    NumericType.Int8: 0,
    NumericType.Uint8: 1,
    NumericType.Int16: 2,
    NumericType.Uint16: 3,
    NumericType.Int32: 4,
    NumericType.Uint32: 5,
    NumericType.Int64: 6,
    NumericType.Uint64: 7,
    NumericType.Float16: 8,
    NumericType.BFloat16: 9,
    NumericType.Float32: 10,
    NumericType.Float64: 11,
}

s1 = get_random_alpha_string()
s2 = get_random_alpha_string()
s3 = get_random_alpha_string()
s4 = get_random_alpha_string()
invalid_dim = get_random_non_zero_int(2, 8)

# 默认参数 memoryspace=None 时，应继承输入的 spec，且 lhs/rhs 的 space 必须相同。
# matmul 的返回 format 默认是 Norm。
lhs = Memory([s1, s2], NumericType.Float16, space=MemorySpace.GM, format=Farmat.CLast)
rhs = Memory(
    [s2, s3],
    NumericType.Float16,
    space=MemorySpace.GM,
    stride=[s3, 1],
    format=Farmat.CLast,
)
result = matmul(lhs, rhs)

assert result.get_shape() == [s1, s3]
assert result.get_type() is NumericType.Float16
assert result.get_space() is MemorySpace.GM
assert result.get_format() is Farmat.Norm
assert result.get_stride() == [s3, 1]

# 显式传入 memoryspace 时，应仅覆盖结果 space，其他 spec 仍继承输入。
space_override_result = matmul(lhs, rhs, memoryspace=MemorySpace.SM)

assert space_override_result.get_shape() == [s1, s3]
assert space_override_result.get_type() is NumericType.Float16
assert space_override_result.get_space() is MemorySpace.SM
assert space_override_result.get_format() is Farmat.Norm
assert space_override_result.get_stride() == [s3, 1]

# 不同 dtype 的矩阵乘应遵循约定的类型提升规则。
mixed_rhs = Memory([s2, s3], NumericType.Float32, space=MemorySpace.GM)
mixed_result = matmul(lhs, mixed_rhs)

assert mixed_result.get_shape() == [s1, s3]
assert PROMOTION_ORDER[mixed_result.get_type()] == min(
    PROMOTION_ORDER[lhs.get_type()],
    PROMOTION_ORDER[mixed_rhs.get_type()],
)
assert mixed_result.get_type() is NumericType.Float16
assert mixed_result.get_space() is MemorySpace.GM

# contracting dim 不一致时，应显式报错。
with pytest.raises(ValueError):
    matmul(lhs, Memory([s4, s3], NumericType.Float16, space=MemorySpace.GM))

# 非 rank-2 输入不应被接受。
with pytest.raises(ValueError):
    matmul(Memory([s1, s2, s3], NumericType.Float16), rhs)

# lhs/rhs 的 space 不一致时，应显式报错。
with pytest.raises(ValueError):
    matmul(lhs, Memory([s2, s3], NumericType.Float16, space=MemorySpace.SM))

# 失败路径也应覆盖静态维 contracting mismatch。
with pytest.raises(ValueError):
    matmul(
        Memory([invalid_dim, s2], NumericType.Float16),
        Memory([s3, s4], NumericType.Float16),
    )
