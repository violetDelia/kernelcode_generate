"""memory operation tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 Memory 的逐元素算术与比较运算约束。

使用示例:
- pytest -q test/operation/test_memory_operation.py

关联文件:
- 功能实现: kernel_gen/symbol_variable/memory.py
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

from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import Farmat, NumericType


# ME-010
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 01:12:46 +0800
# 最近一次运行成功时间: 2026-03-25 01:12:46 +0800
# 测试目的: 验证 Memory + Memory 逐元素运算的 dtype 提升与 format/stride/space 继承。
# 使用示例: pytest -q test/operation/test_memory_operation.py -k test_memory_add_memory
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/operation/test_memory_operation.py
def test_memory_add_memory() -> None:
    lhs = Memory(["N", 4], NumericType.Int32, space=MemorySpace.SM, stride=[4, 1], format=Farmat.CLast)
    rhs = Memory(["N", 4], NumericType.Float32, space=MemorySpace.GM, stride=[8, 1], format=Farmat.Norm)
    result = lhs + rhs
    result_sub = lhs - rhs
    result_mul = lhs * rhs
    result_div = lhs / rhs
    result_floor = lhs // rhs
    rep = repr(lhs)
    assert isinstance(result, Memory)
    assert result.shape.get_values() == ["N", 4]
    assert result.dtype is NumericType.Float32
    assert result.space is MemorySpace.SM
    assert result.format is Farmat.CLast
    assert result.stride.get_values() == [4, 1]
    assert result_sub.shape.get_values() == ["N", 4]
    assert result_sub.dtype is NumericType.Float32
    assert result_sub.space is MemorySpace.SM
    assert result_sub.format is Farmat.CLast
    assert result_sub.stride.get_values() == [4, 1]
    assert result_mul.shape.get_values() == ["N", 4]
    assert result_mul.dtype is NumericType.Float32
    assert result_mul.space is MemorySpace.SM
    assert result_mul.format is Farmat.CLast
    assert result_mul.stride.get_values() == [4, 1]
    assert result_div.shape.get_values() == ["N", 4]
    assert result_div.dtype is NumericType.Float32
    assert result_div.space is MemorySpace.SM
    assert result_div.format is Farmat.CLast
    assert result_div.stride.get_values() == [4, 1]
    assert result_floor.shape.get_values() == ["N", 4]
    assert result_floor.dtype is NumericType.Float32
    assert result_floor.space is MemorySpace.SM
    assert result_floor.format is Farmat.CLast
    assert result_floor.stride.get_values() == [4, 1]
    assert rep.startswith("Memory(")
    assert str(lhs) == rep


# ME-011
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 01:12:46 +0800
# 最近一次运行成功时间: 2026-03-25 01:12:46 +0800
# 测试目的: 验证 Memory 与标量逐元素运算的 dtype 提升规则与 bool 标量归一。
# 使用示例: pytest -q test/operation/test_memory_operation.py -k test_memory_add_scalar
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/operation/test_memory_operation.py
def test_memory_add_scalar() -> None:
    mem = Memory([2, 2], NumericType.Int8, stride=[2, 1], format=Farmat.CLast)
    left = mem + 1
    right = 1 + mem
    sub_left = mem - 1
    sub_right = 1 - mem
    mul_left = mem * 2
    mul_right = 2 * mem
    div_left = mem / 2
    div_right = 2 / mem
    floor_left = mem // 2
    floor_right = 2 // mem
    bool_add = mem + True
    bool_sub = mem - True
    bool_radd = True + mem
    bool_rsub = True - mem
    bool_mul = mem * True
    bool_rmul = True * mem
    bool_div = mem / True
    bool_rdiv = True / mem
    bool_floor = mem // True
    bool_rfloor = True // mem
    assert left.shape.get_values() == [2, 2]
    assert left.dtype is NumericType.Int32
    assert right.shape.get_values() == [2, 2]
    assert right.dtype is NumericType.Int32
    assert sub_left.shape.get_values() == [2, 2]
    assert sub_left.dtype is NumericType.Int32
    assert sub_right.shape.get_values() == [2, 2]
    assert sub_right.dtype is NumericType.Int32
    assert mul_left.shape.get_values() == [2, 2]
    assert mul_left.dtype is NumericType.Int32
    assert mul_right.shape.get_values() == [2, 2]
    assert mul_right.dtype is NumericType.Int32
    assert div_left.shape.get_values() == [2, 2]
    assert div_left.dtype is NumericType.Int32
    assert div_right.shape.get_values() == [2, 2]
    assert div_right.dtype is NumericType.Int32
    assert floor_left.shape.get_values() == [2, 2]
    assert floor_left.dtype is NumericType.Int32
    assert floor_right.shape.get_values() == [2, 2]
    assert floor_right.dtype is NumericType.Int32
    assert bool_add.shape.get_values() == [2, 2]
    assert bool_add.dtype is NumericType.Int32
    assert bool_sub.shape.get_values() == [2, 2]
    assert bool_sub.dtype is NumericType.Int32
    assert bool_radd.shape.get_values() == [2, 2]
    assert bool_radd.dtype is NumericType.Int32
    assert bool_rsub.shape.get_values() == [2, 2]
    assert bool_rsub.dtype is NumericType.Int32
    assert bool_mul.shape.get_values() == [2, 2]
    assert bool_mul.dtype is NumericType.Int32
    assert bool_rmul.shape.get_values() == [2, 2]
    assert bool_rmul.dtype is NumericType.Int32
    assert bool_div.shape.get_values() == [2, 2]
    assert bool_div.dtype is NumericType.Int32
    assert bool_rdiv.shape.get_values() == [2, 2]
    assert bool_rdiv.dtype is NumericType.Int32
    assert bool_floor.shape.get_values() == [2, 2]
    assert bool_floor.dtype is NumericType.Int32
    assert bool_rfloor.shape.get_values() == [2, 2]
    assert bool_rfloor.dtype is NumericType.Int32
    assert left.format is Farmat.CLast
    assert left.stride.get_values() == [2, 1]
    assert right.format is Farmat.CLast
    assert right.stride.get_values() == [2, 1]
    assert sub_left.format is Farmat.CLast
    assert sub_left.stride.get_values() == [2, 1]
    assert sub_right.format is Farmat.CLast
    assert sub_right.stride.get_values() == [2, 1]
    assert mul_left.format is Farmat.CLast
    assert mul_left.stride.get_values() == [2, 1]
    assert mul_right.format is Farmat.CLast
    assert mul_right.stride.get_values() == [2, 1]
    assert div_left.format is Farmat.CLast
    assert div_left.stride.get_values() == [2, 1]
    assert div_right.format is Farmat.CLast
    assert div_right.stride.get_values() == [2, 1]
    assert floor_left.format is Farmat.CLast
    assert floor_left.stride.get_values() == [2, 1]
    assert floor_right.format is Farmat.CLast
    assert floor_right.stride.get_values() == [2, 1]
    assert bool_add.format is Farmat.CLast
    assert bool_add.stride.get_values() == [2, 1]
    assert bool_sub.format is Farmat.CLast
    assert bool_sub.stride.get_values() == [2, 1]
    assert bool_radd.format is Farmat.CLast
    assert bool_radd.stride.get_values() == [2, 1]
    assert bool_rsub.format is Farmat.CLast
    assert bool_rsub.stride.get_values() == [2, 1]
    assert bool_mul.format is Farmat.CLast
    assert bool_mul.stride.get_values() == [2, 1]
    assert bool_rmul.format is Farmat.CLast
    assert bool_rmul.stride.get_values() == [2, 1]
    assert bool_div.format is Farmat.CLast
    assert bool_div.stride.get_values() == [2, 1]
    assert bool_rdiv.format is Farmat.CLast
    assert bool_rdiv.stride.get_values() == [2, 1]
    assert bool_floor.format is Farmat.CLast
    assert bool_floor.stride.get_values() == [2, 1]
    assert bool_rfloor.format is Farmat.CLast
    assert bool_rfloor.stride.get_values() == [2, 1]


# ME-012
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 01:12:46 +0800
# 最近一次运行成功时间: 2026-03-25 01:12:46 +0800
# 测试目的: 验证运算结果元数据独立性，不复用 lhs shape/stride。
# 使用示例: pytest -q test/operation/test_memory_operation.py -k test_memory_metadata_independent
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
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


# ME-013
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 01:12:46 +0800
# 最近一次运行成功时间: 2026-03-25 01:12:46 +0800
# 测试目的: 验证比较运算返回 predicate dtype。
# 使用示例: pytest -q test/operation/test_memory_operation.py -k test_memory_compare_predicate
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/operation/test_memory_operation.py
def test_memory_compare_predicate() -> None:
    lhs = Memory([1, "M"], NumericType.Float32)
    rhs = Memory([1, "M"], NumericType.Float32)
    eq_result = lhs == rhs
    lt_result = lhs < 1
    ne_result = lhs != rhs
    le_result = lhs <= 1
    gt_result = lhs > 0
    ge_result = lhs >= rhs
    assert isinstance(eq_result, Memory)
    assert eq_result.shape.get_values() == [1, "M"]
    assert eq_result.dtype is NumericType.Int32
    assert lt_result.dtype is NumericType.Int32
    assert ne_result.dtype is NumericType.Int32
    assert le_result.dtype is NumericType.Int32
    assert gt_result.dtype is NumericType.Int32
    assert ge_result.dtype is NumericType.Int32


# ME-014
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 01:12:46 +0800
# 最近一次运行成功时间: 2026-03-25 01:12:46 +0800
# 测试目的: 验证形状不一致时抛 ValueError。
# 使用示例: pytest -q test/operation/test_memory_operation.py -k test_memory_shape_mismatch
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/operation/test_memory_operation.py
def test_memory_shape_mismatch() -> None:
    lhs = Memory([1, 2], NumericType.Float32)
    rhs = Memory([1, 2, 3], NumericType.Float32)
    with pytest.raises(ValueError):
        _ = lhs + rhs


# ME-015
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 01:12:46 +0800
# 最近一次运行成功时间: 2026-03-25 01:12:46 +0800
# 测试目的: 验证 dtype 不支持参与算术运算时抛 TypeError。
# 使用示例: pytest -q test/operation/test_memory_operation.py -k test_memory_dtype_mismatch
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/operation/test_memory_operation.py
def test_memory_dtype_mismatch() -> None:
    lhs = Memory([1, 2], NumericType.Bool)
    rhs = Memory([1, 2], NumericType.Int32)
    with pytest.raises(TypeError):
        _ = lhs + rhs


# ME-016
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 01:12:46 +0800
# 最近一次运行成功时间: 2026-03-25 01:12:46 +0800
# 测试目的: 验证不支持的标量类型或 dtype 抛 TypeError。
# 使用示例: pytest -q test/operation/test_memory_operation.py -k test_memory_scalar_type_error
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/operation/test_memory_operation.py
def test_memory_scalar_type_error() -> None:
    mem = Memory([1], NumericType.Int32)
    with pytest.raises(TypeError):
        _ = mem + "1"
    mem_bool = Memory([1], NumericType.Bool)
    with pytest.raises(TypeError):
        _ = mem_bool + 1
    mem64 = Memory([1], NumericType.Int64)
    result = mem64 + 1
    assert result.dtype is NumericType.Int64
