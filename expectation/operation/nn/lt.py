"""NN lt expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 nn.lt 支持 Memory 与标量比较。

使用示例:
- python expectation/operation/nn/lt.py

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

from kernel_gen.operation.nn import lt
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType
from expectation.utils.random import get_random_alpha_string, get_random_non_zero_int

s1 = get_random_alpha_string()
s2 = get_random_alpha_string()
invalid_dim = get_random_non_zero_int(2, 8)

# Memory 与标量比较应返回原 shape 的谓词结果。
lhs = Memory([s1, s2], NumericType.Float32)
result = lt(lhs, 0)

assert result.get_shape() == [s1, s2]
assert result.get_type() is NumericType.Bool

# 相同 shape 的比较应保持输入 shape。
same_rhs = Memory([s1, s2], NumericType.Float32)
same_result = lt(lhs, same_rhs)

assert same_result.get_shape() == [s1, s2]
assert same_result.get_type() is NumericType.Bool

# singleton 维度应按隐式 broadcast 规则扩张。
broadcast_rhs = Memory([1, s2], NumericType.Float32)
broadcast_result = lt(lhs, broadcast_rhs)

assert broadcast_result.get_shape() == [s1, s2]
assert broadcast_result.get_type() is NumericType.Bool

# 无法 broadcast 的 shape 应显式报错。
with pytest.raises(ValueError):
    lt(lhs, Memory([invalid_dim], NumericType.Float32))
