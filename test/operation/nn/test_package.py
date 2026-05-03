"""nn facade smoke tests.


功能说明:
- 保留 `test_operation_nn.py` 作为 facade 兼容冒烟入口。
- 具体 family 用例已拆分到 `test_operation_nn_elementwise.py`、`test_operation_nn_broadcast.py`、`test_operation_nn_structured.py`、`test_operation_nn_reduction.py`。

使用示例:
- pytest -q test/operation/nn/test_package.py

关联文件:
- 功能实现: kernel_gen/operation/nn/__init__.py
- Spec 文档: spec/operation/nn.md
- 测试文件: test/operation/nn/test_package.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import kernel_gen.operation as operation_api
import kernel_gen.operation.nn as operation_nn

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.operation.nn import add, broadcast, conv, fc, matmul, reduce_sum, softmax
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType


# OP-NN-FACADE-001
# 测试目的: 验证 nn facade 不再暴露私有 helper。
# 使用示例: pytest -q test/operation/nn/test_package.py -k test_nn_facade_hides_private_helpers
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_package.py
def test_nn_facade_hides_private_helpers() -> None:
    assert not hasattr(operation_nn, '_AddStrideDim')
    assert not hasattr(operation_nn, '_resolve_add_dtype')
    assert not hasattr(operation_nn, '_merge_broadcast_dim')
    assert not hasattr(operation_nn, '_infer_broadcast_shape')
    assert not hasattr(operation_nn, '_broadcast_memory_pair')


# OP-NN-FACADE-002
# 测试目的: 验证 nn facade 公开对象可从 package-root 直接获取。
# 使用示例: pytest -q test/operation/nn/test_package.py -k test_nn_facade_public_objects_available
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_package.py
def test_nn_facade_public_objects_available() -> None:
    assert operation_nn.add is add
    assert operation_nn.broadcast is broadcast
    assert operation_nn.reduce_sum is reduce_sum
    assert operation_nn.matmul is matmul
    assert operation_nn.fc is fc
    assert operation_nn.conv is conv
    assert operation_nn.softmax is softmax


# OP-NN-FACADE-003
# 测试目的: 验证 nn facade 公开 helper 在拆分后仍可直接调用。
# 使用示例: pytest -q test/operation/nn/test_package.py -k test_nn_facade_public_helpers_smoke
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_package.py
def test_nn_facade_public_helpers_smoke() -> None:
    lhs = Memory([2, 2], NumericType.Float32)
    rhs = Memory([2, 2], NumericType.Float32)
    assert add(lhs, rhs).get_shape() == [2, 2]
    assert broadcast(Memory([1, 2], NumericType.Float32), rhs).get_shape() == [2, 2]
    assert matmul(Memory([2, 3], NumericType.Float32), Memory([3, 4], NumericType.Float32)).get_shape() == [2, 4]
    assert reduce_sum(lhs).get_shape() == [1]
    assert operation_nn.fc is fc
    assert operation_nn.conv is conv
    assert operation_nn.softmax is softmax
    assert operation_api.add is add
