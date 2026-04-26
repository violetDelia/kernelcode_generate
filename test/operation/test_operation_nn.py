"""nn facade smoke tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 保留 `test_operation_nn.py` 作为 facade 兼容冒烟入口。
- 具体 family 用例已拆分到 `test_operation_nn_elementwise.py`、`test_operation_nn_broadcast.py`、`test_operation_nn_structured.py`、`test_operation_nn_reduction.py`。

使用示例:
- pytest -q test/operation/test_operation_nn.py

关联文件:
- 功能实现: kernel_gen/operation/nn/__init__.py
- Spec 文档: spec/operation/nn.md
- 测试文件: test/operation/test_operation_nn.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import kernel_gen.operation as operation_api
import kernel_gen.operation.nn as operation_nn

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.operation.nn import add, broadcast, matmul, reduce_sum
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType


# OP-NN-FACADE-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-16 01:06:00 +0800
# 最近一次运行成功时间: 2026-04-16 01:06:00 +0800
# 测试目的: 验证 nn facade 继续暴露测试依赖的私有 helper。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_facade_reexports_private_helpers
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_facade_reexports_private_helpers() -> None:
    assert hasattr(operation_nn, '_AddStrideDim')
    assert hasattr(operation_nn, '_resolve_add_dtype')
    assert hasattr(operation_nn, '_merge_broadcast_dim')
    assert hasattr(operation_nn, '_infer_broadcast_shape')
    assert hasattr(operation_nn, '_broadcast_memory_pair')


# OP-NN-FACADE-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-16 01:06:00 +0800
# 最近一次运行成功时间: 2026-04-16 01:06:00 +0800
# 测试目的: 验证 nn facade 的公开 __all__ 集合在拆分后保持不变。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_facade_public_all_stable
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_facade_public_all_stable() -> None:
    assert operation_nn.__all__ == [
        'add', 'sub', 'mul', 'truediv', 'floordiv', 'eq', 'ne', 'lt', 'le', 'gt', 'ge',
        'relu', 'leaky_relu', 'sigmoid', 'tanh', 'hard_sigmoid', 'exp',
        'reduce_sum', 'reduce_min', 'reduce_max',
        'matmul', 'img2col1d', 'img2col2d', 'broadcast', 'broadcast_to', 'transpose',
    ]


# OP-NN-FACADE-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-16 01:06:00 +0800
# 最近一次运行成功时间: 2026-04-16 01:06:00 +0800
# 测试目的: 验证 nn facade 公开 helper 在拆分后仍可直接调用。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_facade_public_helpers_smoke
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_facade_public_helpers_smoke() -> None:
    lhs = Memory([2, 2], NumericType.Float32)
    rhs = Memory([2, 2], NumericType.Float32)
    assert add(lhs, rhs).get_shape() == [2, 2]
    assert broadcast(Memory([1, 2], NumericType.Float32), rhs).get_shape() == [2, 2]
    assert matmul(Memory([2, 3], NumericType.Float32), Memory([3, 4], NumericType.Float32)).get_shape() == [2, 4]
    assert reduce_sum(lhs).get_shape() == [1]
    assert operation_api.add is add
