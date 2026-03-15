"""memory operation tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 Memory 的逐元素算术与比较运算约束。

使用示例:
- pytest -q test/operation/test_memory_operation.py

关联文件:
- 功能实现: symbol_variable/memory.py
- Spec 文档: spec/symbol_variable/memory.md
- 测试文件: test/operation/test_memory_operation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from symbol_variable.memory import Memory, MemorySpace
from symbol_variable.type import NumericType


# ME-008
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-15 21:58:50 +0800
# 最近一次运行成功时间: 2026-03-15 21:58:50 +0800
# 功能说明: 验证 Memory + Memory 的逐元素运算。
# 使用示例: pytest -q test/operation/test_memory_operation.py -k test_memory_add_memory
# 对应功能实现文件路径: symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/operation/test_memory_operation.py
def test_memory_add_memory() -> None:
    lhs = Memory(["N", 4], NumericType.Float32, space=MemorySpace.SM)
    rhs = Memory(["N", 4], NumericType.Float32, space=MemorySpace.GM)
    result = lhs + rhs
    assert isinstance(result, Memory)
    assert result.shape.get_values() == ["N", 4]
    assert result.dtype is NumericType.Float32
    assert result.space is MemorySpace.SM


# ME-009
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-15 21:58:50 +0800
# 最近一次运行成功时间: 2026-03-15 21:58:50 +0800
# 功能说明: 验证 Memory 与标量的逐元素运算。
# 使用示例: pytest -q test/operation/test_memory_operation.py -k test_memory_add_scalar
# 对应功能实现文件路径: symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/operation/test_memory_operation.py
def test_memory_add_scalar() -> None:
    mem = Memory([2, 2], NumericType.Int32)
    left = mem + 1
    right = 1 + mem
    assert left.shape.get_values() == [2, 2]
    assert left.dtype is NumericType.Int32
    assert right.shape.get_values() == [2, 2]
    assert right.dtype is NumericType.Int32


# ME-009
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-15 21:58:50 +0800
# 最近一次运行成功时间: 2026-03-15 21:58:50 +0800
# 功能说明: 验证运算结果元数据独立性，不复用 lhs shape/stride。
# 使用示例: pytest -q test/operation/test_memory_operation.py -k test_memory_metadata_independent
# 对应功能实现文件路径: symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/operation/test_memory_operation.py
def test_memory_metadata_independent() -> None:
    mem = Memory([2, 3], NumericType.Int32, stride=[3, 1])
    result = mem + 1
    assert result.shape.get_values() == [2, 3]
    assert result.stride.get_values() == [3, 1]
    assert result.shape is not mem.shape
    assert result.stride is not mem.stride
    result.shape[0] = 5
    result.stride[0] = 9
    assert mem.shape.get_values() == [2, 3]
    assert mem.stride.get_values() == [3, 1]


# ME-010
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-15 21:58:50 +0800
# 最近一次运行成功时间: 2026-03-15 21:58:50 +0800
# 功能说明: 验证比较运算返回 predicate dtype。
# 使用示例: pytest -q test/operation/test_memory_operation.py -k test_memory_compare_predicate
# 对应功能实现文件路径: symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/operation/test_memory_operation.py
def test_memory_compare_predicate() -> None:
    lhs = Memory([1, "M"], NumericType.Float32)
    rhs = Memory([1, "M"], NumericType.Float32)
    eq_result = lhs == rhs
    lt_result = lhs < 1
    assert isinstance(eq_result, Memory)
    assert eq_result.shape.get_values() == [1, "M"]
    assert eq_result.dtype is NumericType.Int32
    assert lt_result.dtype is NumericType.Int32


# ME-008
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-15 21:58:50 +0800
# 最近一次运行成功时间: 2026-03-15 21:58:50 +0800
# 功能说明: 验证形状不一致时抛 ValueError。
# 使用示例: pytest -q test/operation/test_memory_operation.py -k test_memory_shape_mismatch
# 对应功能实现文件路径: symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/operation/test_memory_operation.py
def test_memory_shape_mismatch() -> None:
    lhs = Memory([1, 2], NumericType.Float32)
    rhs = Memory([1, 2, 3], NumericType.Float32)
    with pytest.raises(ValueError):
        _ = lhs + rhs


# ME-008
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-15 21:58:50 +0800
# 最近一次运行成功时间: 2026-03-15 21:58:50 +0800
# 功能说明: 验证 dtype 不兼容时抛 TypeError。
# 使用示例: pytest -q test/operation/test_memory_operation.py -k test_memory_dtype_mismatch
# 对应功能实现文件路径: symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/operation/test_memory_operation.py
def test_memory_dtype_mismatch() -> None:
    lhs = Memory([1, 2], NumericType.Float32)
    rhs = Memory([1, 2], NumericType.Int32)
    with pytest.raises(TypeError):
        _ = lhs + rhs


# ME-009
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-15 21:58:50 +0800
# 最近一次运行成功时间: 2026-03-15 21:58:50 +0800
# 功能说明: 验证不支持的标量类型抛 TypeError。
# 使用示例: pytest -q test/operation/test_memory_operation.py -k test_memory_scalar_type_error
# 对应功能实现文件路径: symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/operation/test_memory_operation.py
def test_memory_scalar_type_error() -> None:
    mem = Memory([1], NumericType.Int32)
    with pytest.raises(TypeError):
        _ = mem + "1"
