"""NN add expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 `nn.add` 支持 `Memory/Memory` 的隐式 broadcast，并返回目标 shape 的 `Memory`。

使用示例:
- python expectation/operation/nn/add.py

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

from kernel_gen.operation.nn import add
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import Farmat, NumericType
from expectation.utils.random import get_random_alpha_string

s1 = get_random_alpha_string()
s2 = get_random_alpha_string()

# 相同 shape 的加法应保持原有的 Memory 描述。
t1 = Memory([s1, s2])
t2 = Memory([s1, s2])

t3 = add(t1, t2)
assert isinstance(t3, Memory)
assert t1 == t3

# singleton 维度应按隐式 broadcast 规则扩张到目标 shape。
t4 = Memory([1, s2])
t5 = add(t1, t4)
assert t5 == t1

t6 = Memory([1])
t7 = add(t1, t6)
assert t7 == t1

# 不同 dtype 的加法应遵循约定的类型提升规则。
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

lhs = Memory([s1, s2], NumericType.Int32)
rhs = Memory([s1, s2], NumericType.Float32)
result = add(lhs, rhs)

assert result.get_shape() == [s1, s2]
assert PROMOTION_ORDER[result.get_type()] == min(PROMOTION_ORDER[lhs.get_type()], PROMOTION_ORDER[rhs.get_type()])
assert result.get_type() is NumericType.Int32

# 当 format 或 stride 不一致时，结果应回落到默认布局元信息。
lhs_layout = Memory([s1, s2], NumericType.Int32, stride=[s2, 1], format=Farmat.CLast)
rhs_layout = Memory([s1, s2], NumericType.Int32, stride=[s2, 1], format=Farmat.Norm)
layout_result = add(lhs_layout, rhs_layout)

assert layout_result.get_shape() == [s1, s2]
assert layout_result.get_format() is Farmat.Norm
assert layout_result.get_stride()[0].get_value() == s2
assert layout_result.get_stride()[1] == 1

# 无法 broadcast 的 shape 应显式报错。
invalid_rhs = Memory([2], NumericType.Int32)
with pytest.raises(ValueError):
    add(t1, invalid_rhs)
