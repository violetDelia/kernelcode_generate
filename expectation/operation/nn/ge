"""NN ge expectation.
[immutable-file]
创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 nn.ge 返回 predicate dtype 的 Memory。

使用示例:
- python expectation/operation/nn/ge.py

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

from kernel_gen.operation.nn import ge
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType
from expectation.utils.random import get_random_alpha_string, get_random_non_zero_int

s1 = get_random_alpha_string()
s2 = get_random_alpha_string()
invalid_dim = get_random_non_zero_int(2, 8)

# 相同 shape 的比较应保持输入 shape，并返回谓词类型。
lhs = Memory([s1, s2], NumericType.Float32)
rhs = Memory([s1, s2], NumericType.Float32)
result = ge(lhs, rhs)

assert result.get_shape() == [s1, s2]
assert result.get_type() is NumericType.Bool

# singleton 维度应按隐式 broadcast 规则扩张。
broadcast_lhs = Memory([1, s2], NumericType.Float32)
broadcast_result = ge(broadcast_lhs, rhs)

assert broadcast_result.get_shape() == [s1, s2]
assert broadcast_result.get_type() is NumericType.Bool

# 与标量比较时，应保持 Memory 的 shape。
scalar_result = ge(lhs, 0)

assert scalar_result.get_shape() == [s1, s2]
assert scalar_result.get_type() is NumericType.Bool

# 无法 broadcast 的 shape 应显式报错。
with pytest.raises(ValueError):
    ge(lhs, Memory([invalid_dim], NumericType.Float32))
