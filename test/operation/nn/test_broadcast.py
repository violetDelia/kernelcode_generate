"""nn broadcast family tests.


功能说明:
- 覆盖 `kernel_gen.operation.nn` 的 family 级测试布局。

使用示例:
- pytest -q test/operation/nn/test_broadcast.py

关联文件:
- 功能实现: kernel_gen/operation/nn/__init__.py
- Spec 文档: spec/operation/nn.md
- 测试文件: test/operation/nn/test_broadcast.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.operation.nn import (
    add,
    broadcast,
    broadcast_to,
    eq,
)
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.symbol_shape import SymbolShape
from kernel_gen.symbol_variable.type import Farmat, NumericType


# OP-BC-001
# 测试目的: 验证 broadcast/broadcast_to 可扩张 singleton dim 且结果对齐 target。
# 使用示例: pytest -q test/operation/nn/test_broadcast.py -k test_nn_broadcast_success
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_broadcast.py
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
# 测试目的: 验证 broadcast 可插入前置维并对齐 target 描述。
# 使用示例: pytest -q test/operation/nn/test_broadcast.py -k test_nn_broadcast_prepend_dimension
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_broadcast.py
def test_nn_broadcast_prepend_dimension() -> None:
    value = Memory(["N"], NumericType.Int32)
    target = Memory(["M", "N"], NumericType.Int32, space=MemorySpace.SM, stride=["N", 1], format=Farmat.Norm)
    result = broadcast(value, target)
    assert result.get_shape() == target.get_shape()
    assert result.get_type() is target.get_type()
    assert result.get_space() is target.get_space()


# OP-BC-003
# 测试目的: 验证非 singleton 维度不兼容时报错。
# 使用示例: pytest -q test/operation/nn/test_broadcast.py -k test_nn_broadcast_dimension_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_broadcast.py
def test_nn_broadcast_dimension_mismatch() -> None:
    value = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(KernelCodeError):
        _ = broadcast(value, Memory(["M", "K"], NumericType.Float32))


# OP-BC-004
# 测试目的: 验证目标 rank 更小时报错。
# 使用示例: pytest -q test/operation/nn/test_broadcast.py -k test_nn_broadcast_rank_error
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_broadcast.py
def test_nn_broadcast_rank_error() -> None:
    value = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(KernelCodeError):
        _ = broadcast(value, Memory(["N"], NumericType.Float32))


# OP-BC-005
# 测试目的: 验证非 Memory 输入触发 KernelCodeError。
# 使用示例: pytest -q test/operation/nn/test_broadcast.py -k test_nn_broadcast_non_memory_error
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_broadcast.py
def test_nn_broadcast_non_memory_error() -> None:
    with pytest.raises(KernelCodeError):
        _ = broadcast(1, Memory(["M", "N"], NumericType.Float32))


# OP-BC-006
# 测试目的: 验证非 Memory target 触发 KernelCodeError。
# 使用示例: pytest -q test/operation/nn/test_broadcast.py -k test_nn_broadcast_target_type_error
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_broadcast.py
def test_nn_broadcast_target_type_error() -> None:
    value = Memory([1, "N"], NumericType.Float32)
    with pytest.raises(KernelCodeError):
        _ = broadcast(value, ["M", "N"])


# OP-IB-001
# 测试目的: 验证逐元素算术支持 singleton dim 隐式 broadcast。
# 使用示例: pytest -q test/operation/nn/test_broadcast.py -k test_nn_add_implicit_broadcast_singleton
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_broadcast.py
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
# 测试目的: 验证逐元素算术支持前置维隐式 broadcast。
# 使用示例: pytest -q test/operation/nn/test_broadcast.py -k test_nn_add_implicit_broadcast_prepend_dimension
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_broadcast.py
def test_nn_add_implicit_broadcast_prepend_dimension() -> None:
    lhs = Memory(["B"], NumericType.Float32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    result = add(lhs, rhs)
    assert result.shape.get_values() == ["A", "B"]


# OP-IB-003
# 测试目的: 验证比较运算复用隐式 broadcast 规则。
# 使用示例: pytest -q test/operation/nn/test_broadcast.py -k test_nn_compare_implicit_broadcast
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_broadcast.py
def test_nn_compare_implicit_broadcast() -> None:
    lhs = Memory([1, "B"], NumericType.Float32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    result = eq(lhs, rhs)
    assert result.shape.get_values() == ["A", "B"]
    assert result.dtype is NumericType.Bool


# OP-IB-004
# 测试目的: 验证不兼容维度仍报错。
# 使用示例: pytest -q test/operation/nn/test_broadcast.py -k test_nn_add_implicit_broadcast_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_broadcast.py
def test_nn_add_implicit_broadcast_mismatch() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A", "C"], NumericType.Float32)
    with pytest.raises(KernelCodeError):
        _ = add(lhs, rhs)


# OP-BC-007
# 测试目的: 以确定性随机矩阵验证显式/隐式 broadcast 的 rank、singleton、SymbolShape 与错误语义。
# 使用示例: pytest -q test/operation/nn/test_broadcast.py -k test_nn_broadcast_parameterized_public_shape_matrix
# 对应功能实现文件路径: kernel_gen/operation/nn/broadcast.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_broadcast.py
def test_nn_broadcast_parameterized_public_shape_matrix() -> None:
    rng = random.Random(20260505)
    batch = SymbolDim("B")
    cols = rng.choice([4, "N", SymbolDim("N")])
    cases = [
        (Memory([1, cols], NumericType.Float32), Memory([batch, cols], NumericType.Float32)),
        (Memory([batch, 1], NumericType.Float32), Memory([batch, cols], NumericType.Float32)),
        (Memory([cols], NumericType.Float32), Memory([batch, cols], NumericType.Float32)),
        (Memory([batch, cols], NumericType.Float32), Memory([batch, cols], NumericType.Float32)),
    ]

    for source, target in rng.sample(cases, k=len(cases)):
        result = broadcast(source, target)
        assert result.shape.get_values() == target.shape.get_values()
        assert result.dtype is target.dtype
        assert result.space is target.space

    shape_result = broadcast_to(
        Memory([1, "N"], NumericType.Int32),
        SymbolShape([SymbolDim("M"), "N"]),
        MemorySpace.SM,
    )
    assert shape_result.shape.get_values() == [SymbolDim("M"), "N"]
    assert shape_result.dtype is NumericType.Int32
    assert shape_result.space is MemorySpace.SM

    lhs = Memory([1, "N"], NumericType.Int32)
    rhs = Memory(["M", "N"], NumericType.Int32)
    assert add(lhs, rhs).shape.get_values() == ["M", "N"]
    assert eq(rhs, lhs).shape.get_values() == ["M", "N"]

    with pytest.raises(KernelCodeError, match="broadcast dtype must match target dtype"):
        broadcast(Memory([1], NumericType.Float32), Memory([2], NumericType.Int32))
    with pytest.raises(KernelCodeError, match="broadcast_to source must be Memory"):
        broadcast_to(1, [1], MemorySpace.GM)
    with pytest.raises(KernelCodeError, match="broadcast_to space must be MemorySpace"):
        broadcast_to(Memory([1], NumericType.Float32), [2], "global")
    with pytest.raises(KernelCodeError, match="broadcast_to target_shape must be iterable shape"):
        broadcast_to(Memory([1], NumericType.Float32), 2, MemorySpace.GM)
    with pytest.raises(KernelCodeError, match="broadcast_to target rank must be >= input rank"):
        broadcast_to(Memory([2, 3], NumericType.Float32), [3], MemorySpace.GM)
    with pytest.raises(KernelCodeError, match="broadcast_to dimension mismatch"):
        broadcast_to(Memory([2, 3], NumericType.Float32), [2, 4], MemorySpace.GM)
