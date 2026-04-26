"""nn broadcast family tests.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 `kernel_gen.operation.nn` 的 family 级测试布局。

使用示例:
- pytest -q test/operation/test_operation_nn_broadcast.py

关联文件:
- 功能实现: kernel_gen/operation/nn/__init__.py
- Spec 文档: spec/operation/nn.md
- 测试文件: test/operation/test_operation_nn_broadcast.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.operation.nn import (
    add,
    broadcast,
    broadcast_to,
    eq,
)
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import Farmat, NumericType


# OP-BC-001
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 04:03:10 +0800
# 最近一次运行成功时间: 2026-03-24 04:03:10 +0800
# 测试目的: 验证 broadcast/broadcast_to 可扩张 singleton dim 且结果对齐 target。
# 使用示例: pytest -q test/operation/test_operation_nn_broadcast.py -k test_nn_broadcast_success
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn_broadcast.py
def test_nn_broadcast_success() -> None:
    value = Memory([1, "N"], NumericType.Float32)
    target = Memory(["M", "N"], NumericType.Float32, space=MemorySpace.LM, stride=["N", 1], format=Farmat.CLast)
    result = broadcast(value, target)
    alias_result = broadcast_to(value, ["M", "N"], MemorySpace.LM)
    alias_expected = Memory(["M", "N"], NumericType.Float32, space=MemorySpace.LM, format=Farmat.Norm)
    assert result.get_shape() == target.get_shape()
    assert result.get_type() is target.get_type()
    assert result.get_space() is target.get_space()
    assert result.get_format() is target.get_format()
    assert result.get_stride() == target.get_stride()
    assert alias_result.get_shape() == alias_expected.get_shape()
    assert alias_result.get_type() is alias_expected.get_type()
    assert alias_result.get_space() is alias_expected.get_space()
    assert alias_result.get_format() is alias_expected.get_format()
    assert alias_result.get_stride() == alias_expected.get_stride()


# OP-BC-002
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 04:03:10 +0800
# 最近一次运行成功时间: 2026-03-24 04:03:10 +0800
# 测试目的: 验证 broadcast 可插入前置维并对齐 target 描述。
# 使用示例: pytest -q test/operation/test_operation_nn_broadcast.py -k test_nn_broadcast_prepend_dimension
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn_broadcast.py
def test_nn_broadcast_prepend_dimension() -> None:
    value = Memory(["N"], NumericType.Int32)
    target = Memory(["M", "N"], NumericType.Int32, space=MemorySpace.SM, stride=["N", 1], format=Farmat.Norm)
    result = broadcast(value, target)
    assert result.get_shape() == target.get_shape()
    assert result.get_type() is target.get_type()
    assert result.get_space() is target.get_space()


# OP-BC-003
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 04:03:10 +0800
# 最近一次运行成功时间: 2026-03-24 04:03:10 +0800
# 测试目的: 验证非 singleton 维度不兼容时报错。
# 使用示例: pytest -q test/operation/test_operation_nn_broadcast.py -k test_nn_broadcast_dimension_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn_broadcast.py
def test_nn_broadcast_dimension_mismatch() -> None:
    value = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(ValueError):
        _ = broadcast(value, Memory(["M", "K"], NumericType.Float32))


# OP-BC-004
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 04:03:10 +0800
# 最近一次运行成功时间: 2026-03-24 04:03:10 +0800
# 测试目的: 验证目标 rank 更小时报错。
# 使用示例: pytest -q test/operation/test_operation_nn_broadcast.py -k test_nn_broadcast_rank_error
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn_broadcast.py
def test_nn_broadcast_rank_error() -> None:
    value = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(ValueError):
        _ = broadcast(value, Memory(["N"], NumericType.Float32))


# OP-BC-005
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 04:03:10 +0800
# 最近一次运行成功时间: 2026-03-24 04:03:10 +0800
# 测试目的: 验证非 Memory 输入触发 TypeError。
# 使用示例: pytest -q test/operation/test_operation_nn_broadcast.py -k test_nn_broadcast_non_memory_error
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn_broadcast.py
def test_nn_broadcast_non_memory_error() -> None:
    with pytest.raises(TypeError):
        _ = broadcast(1, Memory(["M", "N"], NumericType.Float32))


# OP-BC-006
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 04:03:10 +0800
# 最近一次运行成功时间: 2026-03-24 04:03:10 +0800
# 测试目的: 验证非 Memory target 触发 TypeError。
# 使用示例: pytest -q test/operation/test_operation_nn_broadcast.py -k test_nn_broadcast_target_type_error
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn_broadcast.py
def test_nn_broadcast_target_type_error() -> None:
    value = Memory([1, "N"], NumericType.Float32)
    with pytest.raises(TypeError):
        _ = broadcast(value, ["M", "N"])


# OP-IB-001
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:33:34 +0800
# 最近一次运行成功时间: 2026-03-22 14:33:34 +0800
# 测试目的: 验证逐元素算术支持 singleton dim 隐式 broadcast。
# 使用示例: pytest -q test/operation/test_operation_nn_broadcast.py -k test_nn_add_implicit_broadcast_singleton
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn_broadcast.py
def test_nn_add_implicit_broadcast_singleton() -> None:
    lhs = Memory([1, "B"], NumericType.Float32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    result = add(lhs, rhs)
    lhs_same = Memory(["A", "B"], NumericType.Float32)
    rhs_same = Memory(["A", "B"], NumericType.Float32)
    rhs_singleton = Memory([1, "B"], NumericType.Float32)
    result_same = add(lhs_same, rhs_same)
    result_rhs_singleton = add(lhs_same, rhs_singleton)
    assert result.shape.get_values() == ["A", "B"]
    assert result_same.shape.get_values() == ["A", "B"]
    assert result_rhs_singleton.shape.get_values() == ["A", "B"]


# OP-IB-002
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:33:34 +0800
# 最近一次运行成功时间: 2026-03-22 14:33:34 +0800
# 测试目的: 验证逐元素算术支持前置维隐式 broadcast。
# 使用示例: pytest -q test/operation/test_operation_nn_broadcast.py -k test_nn_add_implicit_broadcast_prepend_dimension
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn_broadcast.py
def test_nn_add_implicit_broadcast_prepend_dimension() -> None:
    lhs = Memory(["B"], NumericType.Float32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    result = add(lhs, rhs)
    assert result.shape.get_values() == ["A", "B"]


# OP-IB-003
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:33:34 +0800
# 最近一次运行成功时间: 2026-03-22 14:33:34 +0800
# 测试目的: 验证比较运算复用隐式 broadcast 规则。
# 使用示例: pytest -q test/operation/test_operation_nn_broadcast.py -k test_nn_compare_implicit_broadcast
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn_broadcast.py
def test_nn_compare_implicit_broadcast() -> None:
    lhs = Memory([1, "B"], NumericType.Float32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    result = eq(lhs, rhs)
    assert result.shape.get_values() == ["A", "B"]
    assert result.dtype is NumericType.Bool


# OP-IB-004
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:33:34 +0800
# 最近一次运行成功时间: 2026-03-22 14:33:34 +0800
# 测试目的: 验证不兼容维度仍报错。
# 使用示例: pytest -q test/operation/test_operation_nn_broadcast.py -k test_nn_add_implicit_broadcast_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn_broadcast.py
def test_nn_add_implicit_broadcast_mismatch() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A", "C"], NumericType.Float32)
    with pytest.raises(ValueError):
        _ = add(lhs, rhs)
