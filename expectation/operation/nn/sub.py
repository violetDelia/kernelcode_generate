"""NN sub expectation.
[immutable-file]
创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 nn.sub 保持目标 shape。
- 验证 lhs/rhs dtype 不一致时，结果返回较低优先级的 dtype。

使用示例:
- python expectation/operation/nn/sub.py

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

from kernel_gen.operation.nn import sub
from kernel_gen.symbol_variable.memory import Memory
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
invalid_dim = get_random_non_zero_int(2, 8)

# 相同 shape 的减法应保持原有的 Memory 描述。
same_lhs = Memory([s1, s2], NumericType.Int16)
same_rhs = Memory([s1, s2], NumericType.Int16)
same_result = sub(same_lhs, same_rhs)

assert isinstance(same_result, Memory)
assert same_result == same_lhs

# singleton 维度应按隐式 broadcast 规则扩张到目标 shape。
broadcast_rhs = Memory([1, s2], NumericType.Int16)
broadcast_result = sub(same_lhs, broadcast_rhs)

assert broadcast_result.get_shape() == [s1, s2]
assert broadcast_result.get_type() is NumericType.Int16

# 与标量相减时，应保持原 shape 与 dtype。
scalar_result = sub(same_lhs, 3)

assert scalar_result.get_shape() == [s1, s2]
assert scalar_result.get_type() is NumericType.Int16

# 不同 dtype 的减法应遵循约定的类型提升规则。
lhs = Memory([s1, s2], NumericType.Int16)
rhs = Memory([s1, s2], NumericType.Int32)
result = sub(lhs, rhs)

assert result.get_shape() == [s1, s2]
assert PROMOTION_ORDER[result.get_type()] == min(
    PROMOTION_ORDER[lhs.get_type()],
    PROMOTION_ORDER[rhs.get_type()],
)
assert result.get_type() is NumericType.Int16

# 当 format 或 stride 不一致时，结果应回落到默认布局元信息。
lhs_layout = Memory([s1, s2], NumericType.Int16, stride=[1, 1], format=Farmat.CLast)
rhs_layout = Memory([s1, s2], NumericType.Int16, stride=[2, 1], format=Farmat.Norm)
layout_result = sub(lhs_layout, rhs_layout)

assert layout_result.get_shape() == [s1, s2]
assert layout_result.get_format() is Farmat.Norm
assert layout_result.get_stride()[0].get_value() == s2
assert layout_result.get_stride()[1] == 1

# 无法 broadcast 的 shape 应显式报错。
with pytest.raises(ValueError):
    sub(same_lhs, Memory([invalid_dim], NumericType.Int16))
