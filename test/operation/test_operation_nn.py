"""nn operation API tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 python/operation/nn.py 的逐元素算术与比较 API。

使用示例:
- pytest -q test/operation/test_operation_nn.py

关联文件:
- 功能实现: python/operation/nn.py
- Spec 文档: spec/operation/nn.md
- 测试文件: test/operation/test_operation_nn.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.operation.nn import add, eq, ge, gt, le, lt, mul, ne, sub, truediv
from python.symbol_variable.memory import Memory
from python.symbol_variable.symbol_shape import SymbolList, SymbolShape
from python.symbol_variable.type import NumericType


# OP-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 02:24:54 +0800
# 最近一次运行成功时间: 2026-03-16 02:24:54 +0800
# 功能说明: 验证 add API 可独立调用并保持形状。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_add_memory
# 对应功能实现文件路径: python/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_add_memory() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    result = add(lhs, rhs)
    assert isinstance(result, Memory)
    assert result.shape.get_values() == ["A", "B"]
    assert result.dtype is NumericType.Float32


# OP-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 02:24:54 +0800
# 最近一次运行成功时间: 2026-03-16 02:24:54 +0800
# 功能说明: 验证 Memory 与标量加法支持左右两侧。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_add_scalar
# 对应功能实现文件路径: python/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_add_scalar() -> None:
    mem = Memory([2, 2], NumericType.Int32)
    left = add(mem, 1)
    right = add(1, mem)
    assert left.shape.get_values() == [2, 2]
    assert left.dtype is NumericType.Int32
    assert right.shape.get_values() == [2, 2]
    assert right.dtype is NumericType.Int32


# OP-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 02:24:54 +0800
# 最近一次运行成功时间: 2026-03-16 02:24:54 +0800
# 功能说明: 验证链式表达式逐步检查形状与类型。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_chain_expression
# 对应功能实现文件路径: python/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_chain_expression() -> None:
    lhs = Memory(["M", "N"], NumericType.Float32)
    rhs = Memory(["M", "N"], NumericType.Float32)
    result = add(add(lhs, 3), rhs)
    assert result.shape.get_values() == ["M", "N"]
    assert result.dtype is NumericType.Float32


# OP-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 02:24:54 +0800
# 最近一次运行成功时间: 2026-03-16 02:24:54 +0800
# 功能说明: 验证 shape 不一致抛 ValueError。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_shape_mismatch
# 对应功能实现文件路径: python/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_shape_mismatch() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A", "C"], NumericType.Float32)
    with pytest.raises(ValueError):
        _ = add(lhs, rhs)


# OP-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 02:24:54 +0800
# 最近一次运行成功时间: 2026-03-16 02:24:54 +0800
# 功能说明: 验证 rank 不一致抛 ValueError。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_rank_mismatch
# 对应功能实现文件路径: python/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_rank_mismatch() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A"], NumericType.Float32)
    with pytest.raises(ValueError):
        _ = add(lhs, rhs)


# OP-008
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 02:24:54 +0800
# 最近一次运行成功时间: 2026-03-16 02:24:54 +0800
# 功能说明: 验证 dtype 不兼容抛 TypeError。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_dtype_mismatch
# 对应功能实现文件路径: python/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_dtype_mismatch() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A", "B"], NumericType.Int32)
    with pytest.raises(TypeError):
        _ = add(lhs, rhs)


# OP-007
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 02:24:54 +0800
# 最近一次运行成功时间: 2026-03-16 02:24:54 +0800
# 功能说明: 验证标量类型不合法抛 TypeError。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_scalar_type_error
# 对应功能实现文件路径: python/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_scalar_type_error() -> None:
    mem = Memory([1], NumericType.Int32)
    with pytest.raises(TypeError):
        _ = add(mem, "3")


# OP-009
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 02:24:54 +0800
# 最近一次运行成功时间: 2026-03-16 02:24:54 +0800
# 功能说明: 验证比较 API 返回 predicate dtype。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_compare_predicate
# 对应功能实现文件路径: python/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_compare_predicate() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    eq_result = eq(lhs, rhs)
    lt_result = lt(lhs, 0)
    gt_result = gt(0, lhs)
    assert eq_result.shape.get_values() == ["A", "B"]
    assert eq_result.dtype is NumericType.Int32
    assert lt_result.dtype is NumericType.Int32
    assert gt_result.dtype is NumericType.Int32


# OP-010
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 02:24:54 +0800
# 最近一次运行成功时间: 2026-03-16 02:24:54 +0800
# 功能说明: 验证比较时 shape 顺序不同抛 ValueError。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_compare_shape_order
# 对应功能实现文件路径: python/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_compare_shape_order() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["B", "A"], NumericType.Float32)
    with pytest.raises(ValueError):
        _ = eq(lhs, rhs)


# OP-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 02:24:54 +0800
# 最近一次运行成功时间: 2026-03-16 02:24:54 +0800
# 功能说明: 验证其他算术 API 保持形状。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_other_arithmetic
# 对应功能实现文件路径: python/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_other_arithmetic() -> None:
    lhs = Memory([2, 2], NumericType.Int32)
    rhs = Memory([2, 2], NumericType.Int32)
    assert sub(lhs, rhs).shape.get_values() == [2, 2]
    assert mul(lhs, 2).shape.get_values() == [2, 2]
    assert truediv(lhs, 1).shape.get_values() == [2, 2]


# OP-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 02:24:54 +0800
# 最近一次运行成功时间: 2026-03-16 02:24:54 +0800
# 功能说明: 验证纯标量输入抛 TypeError。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_scalar_only_error
# 对应功能实现文件路径: python/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_scalar_only_error() -> None:
    with pytest.raises(TypeError):
        _ = add(1, 2)


# OP-009
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 02:24:54 +0800
# 最近一次运行成功时间: 2026-03-16 02:24:54 +0800
# 功能说明: 验证比较操作对称 API 可用。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_compare_alias
# 对应功能实现文件路径: python/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_compare_alias() -> None:
    lhs = Memory([1], NumericType.Int32)
    rhs = Memory([1], NumericType.Int32)
    assert ne(lhs, rhs).dtype is NumericType.Int32
    assert le(lhs, rhs).dtype is NumericType.Int32
    assert ge(lhs, rhs).dtype is NumericType.Int32


# OP-011
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 02:24:54 +0800
# 最近一次运行成功时间: 2026-03-16 02:24:54 +0800
# 功能说明: 验证 nn 链路在迁移后不依赖已移除的 convert_from_* 入口。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_operation_does_not_require_convert_from_list
# 对应功能实现文件路径: python/symbol_variable/memory.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_operation_does_not_require_convert_from_list() -> None:
    assert not hasattr(SymbolList, "convert_from_list")
    assert not hasattr(SymbolShape, "convert_from_list")

    lhs = Memory(["N", 32], NumericType.Float32, stride=["C", 1])
    rhs = Memory(["N", 32], NumericType.Float32, stride=["C", 1])

    result = add(lhs, rhs)

    assert result.shape.get_values() == ["N", 32]
    assert result.stride is not None
    assert result.stride.get_values() == ["C", 1]
