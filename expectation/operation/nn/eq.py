"""NN eq expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 nn.eq 复用逐元素隐式 broadcast 规则，并返回 predicate dtype 的 Memory。

使用示例:
- python expectation/operation/nn/eq.py

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

from kernel_gen.operation.nn import eq
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType
from expectation.utils.random import get_random_alpha_string, get_random_non_zero_int

s1 = get_random_alpha_string()
s2 = get_random_alpha_string()
invalid_dim = get_random_non_zero_int(2, 8)

# 相同 shape 的比较应返回相同 shape 的谓词结果。
same_lhs = Memory([s1, s2], NumericType.Float32)
same_rhs = Memory([s1, s2], NumericType.Float32)
same_result = eq(same_lhs, same_rhs)

assert same_result.get_shape() == [s1, s2]
assert same_result.get_type() is NumericType.Bool

# 比较操作应复用隐式 broadcast，并返回谓词类型。
lhs = Memory([1, s2], NumericType.Float32)
rhs = Memory([s1, s2], NumericType.Float32)
result = eq(lhs, rhs)

assert result.get_shape() == [s1, s2]
assert result.get_type() is NumericType.Bool

# 与标量比较时，应保持 Memory 的 shape。
scalar_result = eq(rhs, 0)

assert scalar_result.get_shape() == [s1, s2]
assert scalar_result.get_type() is NumericType.Bool

# 无法 broadcast 的 shape 应显式报错。
with pytest.raises(ValueError):
    eq(rhs, Memory([invalid_dim], NumericType.Float32))
