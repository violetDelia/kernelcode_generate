"""nn operation API tests.

创建者: 金铲铲大作战
最后一次更改: 我不是牛马

功能说明:
- 覆盖 kernel_gen/operation/nn.py 的逐元素算术、比较与激活 API。

使用示例:
- pytest -q test/operation/test_operation_nn.py

当前覆盖率信息: 100%（kernel_gen/operation/nn.py，2026-03-24 04:03:10 +0800）
覆盖率命令: pytest --cov=kernel_gen.operation.nn --cov-report=term-missing -q test/operation/test_operation_nn.py

关联文件:
- 功能实现: kernel_gen/operation/nn.py
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

from kernel_gen.operation.nn import (
    _AddStrideDim,
    _broadcast_memory_pair,
    _infer_broadcast_shape,
    _merge_broadcast_dim,
    _resolve_add_dtype,
    add,
    broadcast,
    broadcast_to,
    conv,
    eq,
    fc,
    floordiv,
    ge,
    gt,
    hard_sigmoid,
    img2col1d,
    img2col2d,
    leaky_relu,
    le,
    lt,
    matmul,
    mul,
    ne,
    relu,
    sigmoid,
    softmax,
    sub,
    tanh,
    truediv,
)
import kernel_gen.operation.nn as nn_module
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.symbol_shape import SymbolList, SymbolShape
from kernel_gen.symbol_variable.type import Farmat, NumericType


# OP-001
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:33:34 +0800
# 最近一次运行成功时间: 2026-03-22 14:33:34 +0800
# 测试目的: 验证 add API 可独立调用并保持形状。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_add_memory
# 对应功能实现文件路径: kernel_gen/operation/nn.py
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
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:33:34 +0800
# 最近一次运行成功时间: 2026-03-22 14:33:34 +0800
# 测试目的: 验证 Memory 与标量加法支持左右两侧。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_add_scalar
# 对应功能实现文件路径: kernel_gen/operation/nn.py
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
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:33:34 +0800
# 最近一次运行成功时间: 2026-03-22 14:33:34 +0800
# 测试目的: 验证链式表达式逐步检查形状与类型。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_chain_expression
# 对应功能实现文件路径: kernel_gen/operation/nn.py
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
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:33:34 +0800
# 最近一次运行成功时间: 2026-03-22 14:33:34 +0800
# 测试目的: 验证 shape 不一致抛 ValueError。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_shape_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_shape_mismatch() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A", "C"], NumericType.Float32)
    with pytest.raises(ValueError):
        _ = add(lhs, rhs)


# OP-004
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:33:34 +0800
# 最近一次运行成功时间: 2026-03-22 14:33:34 +0800
# 测试目的: 验证 rank 不一致抛 ValueError。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_rank_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_rank_mismatch() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A"], NumericType.Float32)
    with pytest.raises(ValueError):
        _ = add(lhs, rhs)


# OP-014
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-24 01:43:10 +0800
# 最近一次运行成功时间: 2026-03-24 01:43:10 +0800
# 测试目的: 验证 nn.add 的 dtype 按固定优先级决议。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_dtype_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py

def test_nn_dtype_mismatch() -> None:
    lhs = Memory(["A", "B"], NumericType.Int32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    result = add(lhs, rhs)
    assert result.shape.get_values() == ["A", "B"]
    assert result.dtype is NumericType.Float32
    scalar_result = add(Memory(["A"], NumericType.Int8), 1)
    assert scalar_result.dtype is NumericType.Int32


# OP-008
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 04:03:10 +0800
# 最近一次运行成功时间: 2026-03-24 04:03:10 +0800
# 测试目的: 验证不支持的 dtype 触发 TypeError。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_dtype_invalid_error
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_dtype_invalid_error() -> None:
    with pytest.raises(TypeError):
        _ = _resolve_add_dtype(NumericType.Bool, NumericType.Int32)


# OP-005A
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 04:03:10 +0800
# 最近一次运行成功时间: 2026-03-24 04:03:10 +0800
# 测试目的: 验证 bool 标量可被接受。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_add_bool_scalar
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_add_bool_scalar() -> None:
    lhs = Memory(["A", "B"], NumericType.Int32)
    result = add(lhs, True)
    assert result.shape.get_values() == ["A", "B"]
    assert result.dtype is NumericType.Int32


# OP-007
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:33:34 +0800
# 最近一次运行成功时间: 2026-03-22 14:33:34 +0800
# 测试目的: 验证标量类型不合法抛 TypeError。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_scalar_type_error
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_scalar_type_error() -> None:
    mem = Memory([1], NumericType.Int32)
    with pytest.raises(TypeError):
        _ = add(mem, "3")


# OP-009
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:33:34 +0800
# 最近一次运行成功时间: 2026-03-22 14:33:34 +0800
# 测试目的: 验证比较 API 返回 predicate dtype。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_compare_predicate
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_compare_predicate() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    eq_result = eq(lhs, rhs)
    lt_result = lt(lhs, 0)
    gt_result = gt(0, lhs)
    with pytest.raises(TypeError):
        _ = eq(Memory(["A", "B"], NumericType.Float32), Memory(["A", "B"], NumericType.Int32))
    assert eq_result.shape.get_values() == ["A", "B"]
    assert eq_result.dtype is NumericType.Bool
    assert lt_result.dtype is NumericType.Bool
    assert gt_result.dtype is NumericType.Bool


# OP-010
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:33:34 +0800
# 最近一次运行成功时间: 2026-03-22 14:33:34 +0800
# 测试目的: 验证比较时 shape 顺序不同抛 ValueError。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_compare_shape_order
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_compare_shape_order() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["B", "A"], NumericType.Float32)
    with pytest.raises(ValueError):
        _ = eq(lhs, rhs)


# OP-002A
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:33:34 +0800
# 最近一次运行成功时间: 2026-03-22 14:33:34 +0800
# 测试目的: 验证其他算术 API 保持形状。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_other_arithmetic
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_other_arithmetic() -> None:
    lhs = Memory([2, 2], NumericType.Int32)
    rhs = Memory([2, 2], NumericType.Int32)
    assert sub(lhs, rhs).shape.get_values() == [2, 2]
    assert mul(lhs, 2).shape.get_values() == [2, 2]
    assert truediv(lhs, 1).shape.get_values() == [2, 2]


# OP-002B
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 04:03:10 +0800
# 最近一次运行成功时间: 2026-03-24 04:03:10 +0800
# 测试目的: 验证 sub 的 dtype 规则与标量反向调用。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_sub_reverse_and_dtype_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_sub_reverse_and_dtype_mismatch() -> None:
    lhs = Memory(["A", "B"], NumericType.Int32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    result = sub(lhs, rhs)
    assert result.shape.get_values() == ["A", "B"]
    assert result.dtype is NumericType.Float32
    reverse = sub(1, lhs)
    assert reverse.shape.get_values() == ["A", "B"]


# OP-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 04:03:10 +0800
# 最近一次运行成功时间: 2026-03-24 04:03:10 +0800
# 测试目的: 验证 sub 在 format/stride 不一致时回落默认布局。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_sub_format_fallback
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_sub_format_fallback() -> None:
    lhs = Memory(["M", "N"], NumericType.Int32, stride=["N", 1], format=Farmat.CLast)
    rhs = Memory(["M", "N"], NumericType.Int32, stride=["N", 2], format=Farmat.Norm)
    result = sub(lhs, rhs)
    assert result.get_format() is Farmat.Norm
    assert result.get_stride()[1] == 1


# OP-017
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 04:03:10 +0800
# 最近一次运行成功时间: 2026-03-24 04:03:10 +0800
# 测试目的: 验证 floordiv 复用算术规则、支持标量并覆盖错误路径。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_floordiv_rules
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_floordiv_rules() -> None:
    lhs = Memory(["M", "N"], NumericType.Int32)
    rhs = Memory([1, "N"], NumericType.Float32, format=Farmat.CLast)
    result = floordiv(lhs, rhs)
    assert result.shape.get_values() == ["M", "N"]
    assert result.dtype is NumericType.Float32
    assert result.format is Farmat.Norm
    assert result.get_stride()[1] == 1
    scalar_result = floordiv(lhs, 2)
    assert scalar_result.shape.get_values() == ["M", "N"]
    assert scalar_result.dtype is NumericType.Int32
    reverse_result = floordiv(2, lhs)
    assert reverse_result.shape.get_values() == ["M", "N"]
    assert reverse_result.dtype is NumericType.Int32
    with pytest.raises(ValueError):
        _ = floordiv(lhs, Memory(["K"], NumericType.Int32))


# OP-011
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:33:34 +0800
# 最近一次运行成功时间: 2026-03-22 14:33:34 +0800
# 测试目的: 验证逐元素算术包装在纯标量输入下复用 Python/SymbolDim 算术语义，并保持非法标量类型报错。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_scalar_only_error
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_scalar_only_error() -> None:
    symbol = SymbolDim("N")

    assert add(1, 2) == 3
    assert sub(5, 2) == 3
    assert truediv(6, 3) == 2.0
    assert floordiv(7, 3) == 2
    assert add(1, symbol).get_value() == "N + 1"
    assert sub(5, symbol).get_value() == "5 - N"
    assert mul(2, symbol).get_value() == "2*N"
    assert floordiv(7, symbol).get_value() == "floor(7/N)"

    with pytest.raises(TypeError):
        _ = add("lhs", "rhs")


# OP-012
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:33:34 +0800
# 最近一次运行成功时间: 2026-03-22 14:33:34 +0800
# 测试目的: 验证比较操作对称 API 可用。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_compare_alias
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_compare_alias() -> None:
    lhs = Memory([1], NumericType.Int32)
    rhs = Memory([1], NumericType.Int32)
    assert ne(lhs, rhs).dtype is NumericType.Bool
    assert le(lhs, rhs).dtype is NumericType.Bool
    assert ge(lhs, rhs).dtype is NumericType.Bool


# OP-013
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-24 00:32:00 +0800
# 最近一次运行成功时间: 2026-03-24 00:32:00 +0800
# 测试目的: 验证 nn 链路在迁移后不依赖已移除的 convert_from_* 入口。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_operation_does_not_require_convert_from_list
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
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


# OP-015
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-24 01:43:10 +0800
# 最近一次运行成功时间: 2026-03-24 01:43:10 +0800
# 测试目的: 验证 format 不一致时回落默认布局。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_add_format_fallback
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py

def test_nn_add_format_fallback() -> None:
    lhs = Memory(["M", "N"], NumericType.Int32, stride=["N", 1], format=Farmat.CLast)
    rhs = Memory(["M", "N"], NumericType.Int32, stride=["N", 1], format=Farmat.Norm)
    result = add(lhs, rhs)
    assert result.get_format() is Farmat.Norm
    assert result.get_stride()[1] == 1


# OP-016A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-24 01:43:10 +0800
# 最近一次运行成功时间: 2026-03-24 01:43:10 +0800
# 测试目的: 验证 stride 不一致时回落默认布局。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_add_stride_fallback
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py

def test_nn_add_stride_fallback() -> None:
    lhs = Memory(["M", "N"], NumericType.Int32, stride=["N", 1])
    rhs = Memory(["M", "N"], NumericType.Int32, stride=["N", 2])
    result = add(lhs, rhs)
    assert result.get_format() is Farmat.Norm
    assert result.get_stride()[1] == 1


# OP-016
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 04:03:10 +0800
# 最近一次运行成功时间: 2026-03-24 04:03:10 +0800
# 测试目的: 验证 stride 序列化维度的符号与常量路径。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_add_stride_dim_serialization
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_add_stride_dim_serialization() -> None:
    symbolic = _AddStrideDim(SymbolDim("N").get_symbol())
    constant = _AddStrideDim(SymbolDim(3).get_symbol())
    assert symbolic.get_value() == "N"
    assert constant.get_value() == 3


# OP-BC-001
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 04:03:10 +0800
# 最近一次运行成功时间: 2026-03-24 04:03:10 +0800
# 测试目的: 验证 broadcast/broadcast_to 可扩张 singleton dim 且结果对齐 target。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_broadcast_success
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_broadcast_success() -> None:
    value = Memory([1, "N"], NumericType.Float32)
    target = Memory(["M", "N"], NumericType.Float32, space=MemorySpace.LM, stride=["N", 1], format=Farmat.CLast)
    result = broadcast(value, target)
    alias_result = broadcast_to(value, target)
    assert result.get_shape() == target.get_shape()
    assert result.get_type() is target.get_type()
    assert result.get_space() is target.get_space()
    assert result.get_format() is target.get_format()
    assert result.get_stride() == target.get_stride()
    assert alias_result.get_shape() == target.get_shape()
    assert alias_result.get_type() is target.get_type()


# OP-BC-002
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 04:03:10 +0800
# 最近一次运行成功时间: 2026-03-24 04:03:10 +0800
# 测试目的: 验证 broadcast 可插入前置维并对齐 target 描述。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_broadcast_prepend_dimension
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
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
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_broadcast_dimension_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
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
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_broadcast_rank_error
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
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
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_broadcast_non_memory_error
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_broadcast_non_memory_error() -> None:
    with pytest.raises(TypeError):
        _ = broadcast(1, Memory(["M", "N"], NumericType.Float32))


# OP-BC-006
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 04:03:10 +0800
# 最近一次运行成功时间: 2026-03-24 04:03:10 +0800
# 测试目的: 验证非 Memory target 触发 TypeError。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_broadcast_target_type_error
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
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
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_add_implicit_broadcast_singleton
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_add_implicit_broadcast_singleton() -> None:
    lhs = Memory([1, "B"], NumericType.Float32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    result = add(lhs, rhs)
    lhs_same = Memory(["A", "B"], NumericType.Float32)
    rhs_same = Memory(["A", "B"], NumericType.Float32)
    lhs_b, rhs_b = _broadcast_memory_pair(lhs_same, rhs_same)
    lhs_b2, rhs_b2 = _broadcast_memory_pair(lhs, rhs)
    inferred_rhs_short = _infer_broadcast_shape(SymbolShape(["A", "B"]), SymbolShape(["B"]))
    inferred_lhs_one = _infer_broadcast_shape(SymbolShape([1, "B"]), SymbolShape(["A", "B"]))
    inferred_rhs_one = _infer_broadcast_shape(SymbolShape(["A", "B"]), SymbolShape([1, "B"]))
    rhs_singleton = Memory([1, "B"], NumericType.Float32)
    lhs_b3, rhs_b3 = _broadcast_memory_pair(lhs_same, rhs_singleton)
    assert _merge_broadcast_dim("N", 1) == "N"
    assert _merge_broadcast_dim("?", "?") == "?"
    with pytest.raises(ValueError):
        _merge_broadcast_dim("?", "N")
    assert result.shape.get_values() == ["A", "B"]
    assert lhs_b is lhs_same
    assert rhs_b is rhs_same
    assert lhs_b2.shape.get_values() == ["A", "B"]
    assert rhs_b2.shape.get_values() == ["A", "B"]
    assert inferred_rhs_short.get_values() == ["A", "B"]
    assert inferred_lhs_one.get_values() == ["A", "B"]
    assert inferred_rhs_one.get_values() == ["A", "B"]
    assert lhs_b3 is lhs_same
    assert rhs_b3.shape.get_values() == ["A", "B"]


# OP-IB-002
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:33:34 +0800
# 最近一次运行成功时间: 2026-03-22 14:33:34 +0800
# 测试目的: 验证逐元素算术支持前置维隐式 broadcast。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_add_implicit_broadcast_prepend_dimension
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_add_implicit_broadcast_prepend_dimension() -> None:
    lhs = Memory(["B"], NumericType.Float32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    result = add(lhs, rhs)
    inferred = _infer_broadcast_shape(SymbolShape(["B"]), SymbolShape(["A", "B"]))
    assert result.shape.get_values() == ["A", "B"]
    assert inferred.get_values() == ["A", "B"]


# OP-IB-003
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:33:34 +0800
# 最近一次运行成功时间: 2026-03-22 14:33:34 +0800
# 测试目的: 验证比较运算复用隐式 broadcast 规则。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_compare_implicit_broadcast
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
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
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_add_implicit_broadcast_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_add_implicit_broadcast_mismatch() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A", "C"], NumericType.Float32)
    with pytest.raises(ValueError):
        _ = add(lhs, rhs)
    with pytest.raises(ValueError):
        _infer_broadcast_shape(SymbolShape(["A", "B"]), SymbolShape(["A", "C"]))


# OP-FC-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-27 09:39:01 +0800
# 最近一次运行成功时间: 2026-03-27 09:39:01 +0800
# 测试目的: 验证 fc 在无 bias 场景下保留批维并输出默认布局。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_fc_without_bias
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_fc_without_bias() -> None:
    value = Memory([2, 3, 4], NumericType.Float32, space=MemorySpace.GM, format=Farmat.CLast)
    weight = Memory([5, 4], NumericType.Float32, space=MemorySpace.GM, format=Farmat.CLast)
    result = fc(value, weight)
    assert result.shape.get_values() == [2, 3, 5]
    assert result.dtype is NumericType.Float32
    assert result.space is MemorySpace.GM
    assert result.format is Farmat.Norm
    assert result.get_stride() == [15, 5, 1]


# OP-FC-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-27 09:39:01 +0800
# 最近一次运行成功时间: 2026-03-27 09:39:01 +0800
# 测试目的: 验证 fc 支持可选 bias 且与输出特征维对齐。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_fc_with_optional_bias
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_fc_with_optional_bias() -> None:
    value = Memory(["B", "K"], NumericType.Float32, space=MemorySpace.GM)
    weight = Memory(["N", "K"], NumericType.Float32, space=MemorySpace.GM)
    bias = Memory(["N"], NumericType.Float32, space=MemorySpace.GM)
    result = fc(value, weight, bias=bias)
    assert result.shape.get_values() == ["B", "N"]
    assert result.dtype is NumericType.Float32
    assert result.space is MemorySpace.GM


# OP-FC-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-27 09:39:01 +0800
# 最近一次运行成功时间: 2026-03-27 09:39:01 +0800
# 测试目的: 验证 fc 对非法类型输入报 TypeError。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_fc_type_error
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_fc_type_error() -> None:
    value = Memory([2, 3], NumericType.Float32)
    weight = Memory([4, 3], NumericType.Float32)
    with pytest.raises(TypeError):
        _ = fc("bad", weight)
    with pytest.raises(TypeError):
        _ = fc(value, "bad")
    with pytest.raises(TypeError):
        _ = fc(value, weight, bias=1.0)


# OP-FC-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-27 09:39:01 +0800
# 最近一次运行成功时间: 2026-03-27 09:39:01 +0800
# 测试目的: 验证 fc 的 value/weight rank 约束报错。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_fc_rank_error
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_fc_rank_error() -> None:
    value = Memory([4], NumericType.Float32)
    weight = Memory([5, 4], NumericType.Float32)
    with pytest.raises(ValueError):
        _ = fc(value, weight)
    value_ok = Memory([2, 4], NumericType.Float32)
    weight_bad = Memory([2, 4, 6], NumericType.Float32)
    with pytest.raises(ValueError):
        _ = fc(value_ok, weight_bad)


# OP-FC-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-27 09:39:01 +0800
# 最近一次运行成功时间: 2026-03-27 09:39:01 +0800
# 测试目的: 验证 fc 输入特征维不一致报错。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_fc_feature_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_fc_feature_mismatch() -> None:
    value = Memory([2, 3, 4], NumericType.Float32)
    weight = Memory([5, 6], NumericType.Float32)
    with pytest.raises(ValueError):
        _ = fc(value, weight)


# OP-FC-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-27 09:39:01 +0800
# 最近一次运行成功时间: 2026-03-27 09:39:01 +0800
# 测试目的: 验证 fc bias 维度不对齐报错。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_fc_bias_shape_error
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_fc_bias_shape_error() -> None:
    value = Memory([2, 3, 4], NumericType.Float32)
    weight = Memory([5, 4], NumericType.Float32)
    bias_rank = Memory([1, 5], NumericType.Float32)
    bias_mismatch = Memory([4], NumericType.Float32)
    with pytest.raises(ValueError):
        _ = fc(value, weight, bias=bias_rank)
    with pytest.raises(ValueError):
        _ = fc(value, weight, bias=bias_mismatch)


# OP-FC-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-27 09:39:01 +0800
# 最近一次运行成功时间: 2026-03-27 09:39:01 +0800
# 测试目的: 验证 fc space 不一致报错。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_fc_space_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_fc_space_mismatch() -> None:
    value = Memory([2, 3], NumericType.Float32, space=MemorySpace.GM)
    weight = Memory([4, 3], NumericType.Float32, space=MemorySpace.SM)
    with pytest.raises(ValueError):
        _ = fc(value, weight)
    bias = Memory([4], NumericType.Float32, space=MemorySpace.SM)
    weight_ok = Memory([4, 3], NumericType.Float32, space=MemorySpace.GM)
    with pytest.raises(ValueError):
        _ = fc(value, weight_ok, bias=bias)


# OP-FC-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-27 09:39:01 +0800
# 最近一次运行成功时间: 2026-03-27 09:39:01 +0800
# 测试目的: 验证 fc 输出可继续参与 nn 算术链路。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_fc_chain_compatibility
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_fc_chain_compatibility() -> None:
    value = Memory([2, 3], NumericType.Float32)
    weight = Memory([4, 3], NumericType.Float32)
    result = fc(value, weight)
    combined = add(result, Memory([2, 4], NumericType.Float32))
    assert combined.shape.get_values() == [2, 4]
    assert combined.dtype is NumericType.Float32


# OP-MM-001
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:33:34 +0800
# 最近一次运行成功时间: 2026-03-22 14:33:34 +0800
# 测试目的: 验证 matmul 基础二维矩阵乘输出 shape/dtype/space。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_matmul_success
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_matmul_success() -> None:
    lhs = Memory(["M", "K"], NumericType.Float32, format=Farmat.CLast)
    rhs = Memory(["K", "N"], NumericType.Float32, stride=["N", 1], format=Farmat.CLast)
    result = matmul(lhs, rhs)
    assert isinstance(result, Memory)
    assert result.shape.get_values() == ["M", "N"]
    assert result.dtype is NumericType.Float32
    assert result.space is lhs.space
    assert result.format is Farmat.Norm
    assert result.get_stride() == ["N", 1]


# OP-MM-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 04:03:10 +0800
# 最近一次运行成功时间: 2026-03-24 04:03:10 +0800
# 测试目的: 验证 matmul 显式 memoryspace 仅覆盖结果 space。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_matmul_space_override
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_matmul_space_override() -> None:
    lhs = Memory(["M", "K"], NumericType.Float32, space=MemorySpace.GM, format=Farmat.CLast)
    rhs = Memory(["K", "N"], NumericType.Float32, space=MemorySpace.GM, format=Farmat.CLast)
    result = matmul(lhs, rhs, memoryspace=MemorySpace.SM)
    assert result.shape.get_values() == ["M", "N"]
    assert result.dtype is NumericType.Float32
    assert result.space is MemorySpace.SM
    assert result.format is Farmat.Norm


# OP-MM-003
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:33:34 +0800
# 最近一次运行成功时间: 2026-03-22 14:33:34 +0800
# 测试目的: 验证 matmul contracting dim 不一致报错。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_matmul_contracting_dim_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_matmul_contracting_dim_mismatch() -> None:
    lhs = Memory(["M", "K"], NumericType.Float32)
    rhs = Memory(["Q", "N"], NumericType.Float32)
    with pytest.raises(ValueError):
        _ = matmul(lhs, rhs)


# OP-MM-004
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:33:34 +0800
# 最近一次运行成功时间: 2026-03-22 14:33:34 +0800
# 测试目的: 验证 matmul 非二维输入报错。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_matmul_rank_error
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_matmul_rank_error() -> None:
    lhs = Memory(["B", "M", "K"], NumericType.Float32)
    rhs = Memory(["K", "N"], NumericType.Float32)
    with pytest.raises(ValueError):
        _ = matmul(lhs, rhs)


# OP-MM-005
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:33:34 +0800
# 最近一次运行成功时间: 2026-03-22 14:33:34 +0800
# 测试目的: 验证 matmul 标量输入非法。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_matmul_scalar_operand_error
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_matmul_scalar_operand_error() -> None:
    lhs = Memory(["M", "K"], NumericType.Float32)
    with pytest.raises(TypeError):
        _ = matmul(lhs, 1)


# OP-MM-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 04:03:10 +0800
# 最近一次运行成功时间: 2026-03-24 04:03:10 +0800
# 测试目的: 验证 matmul dtype 按固定优先级决议。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_matmul_dtype_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_matmul_dtype_mismatch() -> None:
    lhs = Memory(["M", "K"], NumericType.Float32)
    rhs = Memory(["K", "N"], NumericType.Int32)
    result = matmul(lhs, rhs)
    assert result.shape.get_values() == ["M", "N"]
    assert result.dtype is NumericType.Float32


# OP-MM-007
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:33:34 +0800
# 最近一次运行成功时间: 2026-03-22 14:33:34 +0800
# 测试目的: 验证 matmul space 不一致报错。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_matmul_space_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_matmul_space_mismatch() -> None:
    lhs = Memory(["M", "K"], NumericType.Float32, space=MemorySpace.GM)
    rhs = Memory(["K", "N"], NumericType.Float32, space=MemorySpace.SM)
    with pytest.raises(ValueError):
        _ = matmul(lhs, rhs)


# OP-IMG2COL-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-29 17:50:04 +0800
# 最近一次运行成功时间: 2026-03-29 17:50:04 +0800
# 测试目的: 验证 img2col1d 输出形状、format/stride 与参数校验规则。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_img2col1d_contract
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_img2col1d_contract() -> None:
    value = Memory([1, 3, 5], NumericType.Float32, space=MemorySpace.GM)
    result = img2col1d(value, kw=3, sw=1, dw=1, pl=1, pr=1)
    assert result.shape.get_values() == [1, 9, 5]
    assert result.dtype is NumericType.Float32
    assert result.space is MemorySpace.GM
    assert result.format is Farmat.Norm
    assert result.get_stride() == [45, 5, 1]

    with pytest.raises(TypeError):
        _ = img2col1d("bad", kw=3, sw=1, dw=1, pl=0, pr=0)

    with pytest.raises(ValueError):
        _ = img2col1d(Memory([1, 3, 5, 5], NumericType.Float32), kw=3, sw=1, dw=1, pl=0, pr=0)

    with pytest.raises(TypeError):
        _ = img2col1d(value, kw="3", sw=1, dw=1, pl=0, pr=0)

    with pytest.raises(ValueError):
        _ = img2col1d(value, kw=0, sw=1, dw=1, pl=0, pr=0)

    with pytest.raises(ValueError):
        _ = img2col1d(value, kw=3, sw=1, dw=1, pl=-1, pr=0)

    with pytest.raises(TypeError):
        _ = img2col1d(value, kw=True, sw=1, dw=1, pl=0, pr=0)

    with pytest.raises(ValueError):
        _ = img2col1d(Memory([1, 3, 2], NumericType.Float32), kw=3, sw=1, dw=1, pl=0, pr=0)


# OP-IMG2COL-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-29 17:50:04 +0800
# 最近一次运行成功时间: 2026-03-29 17:50:04 +0800
# 测试目的: 验证 img2col2d 输出形状、format/stride 与参数校验规则。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_img2col2d_contract
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_img2col2d_contract() -> None:
    value = Memory([1, 3, 5, 5], NumericType.Float32, space=MemorySpace.GM)
    result = img2col2d(value, kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=1, pw=1, pl=1, pr=1)
    assert result.shape.get_values() == [1, 27, 25]
    assert result.dtype is NumericType.Float32
    assert result.space is MemorySpace.GM
    assert result.format is Farmat.Norm
    assert result.get_stride() == [675, 25, 1]

    with pytest.raises(TypeError):
        _ = img2col2d("bad", kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)

    with pytest.raises(ValueError):
        _ = img2col2d(Memory([1, 3, 5], NumericType.Float32), kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)

    with pytest.raises(TypeError):
        _ = img2col2d(value, kh="3", kw=3, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)

    with pytest.raises(ValueError):
        _ = img2col2d(value, kh=0, kw=3, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)

    with pytest.raises(ValueError):
        _ = img2col2d(value, kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=-1, pw=0, pl=0, pr=0)

    with pytest.raises(TypeError):
        _ = img2col2d(value, kh=True, kw=3, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)

    with pytest.raises(ValueError):
        _ = img2col2d(value, kh=7, kw=7, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)


# OP-IMG2COL-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-29 17:50:04 +0800
# 最近一次运行成功时间: 2026-03-29 17:50:04 +0800
# 测试目的: 验证 img2col 为 forbidden public name，调用需报错且不依赖成功路径。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_img2col_forbidden_public_name
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_img2col_forbidden_public_name() -> None:
    value = Memory([1, 3, 5, 5], NumericType.Float32, space=MemorySpace.GM)
    assert "img2col" not in nn_module.__all__
    with pytest.raises(ValueError):
        _ = nn_module.img2col(value, kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)


# OP-SM-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-27 09:34:06 +0800
# 最近一次运行成功时间: 2026-03-27 09:34:06 +0800
# 测试目的: 验证 softmax 默认 axis=-1 且结果保持输入元信息。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_softmax_default_axis
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_softmax_default_axis() -> None:
    value = Memory([2, 3], NumericType.Float32, space=MemorySpace.LM, stride=SymbolShape([3, 1]))
    result = softmax(value)
    assert result.shape.get_values() == [2, 3]
    assert result.dtype is NumericType.Float32
    assert result.space is MemorySpace.LM
    assert result.format is Farmat.Norm
    assert result.get_stride() == [3, 1]


# OP-SM-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-27 09:34:06 +0800
# 最近一次运行成功时间: 2026-03-27 09:34:06 +0800
# 测试目的: 验证 softmax 负轴归一化路径。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_softmax_negative_axis
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_softmax_negative_axis() -> None:
    value = Memory(["B", "C", "H"], NumericType.Float16)
    result = softmax(value, axis=-2)
    assert result.shape.get_values() == ["B", "C", "H"]
    assert result.dtype is NumericType.Float16


# OP-SM-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-27 09:34:06 +0800
# 最近一次运行成功时间: 2026-03-27 09:34:06 +0800
# 测试目的: 验证 softmax axis 非整数或为 bool 时抛 TypeError。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_softmax_axis_type_error
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_softmax_axis_type_error() -> None:
    value = Memory([2, 3], NumericType.Float32)
    with pytest.raises(TypeError):
        _ = softmax(value, axis=True)
    with pytest.raises(TypeError):
        _ = softmax(value, axis=1.5)


# OP-SM-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-27 09:34:06 +0800
# 最近一次运行成功时间: 2026-03-27 09:34:06 +0800
# 测试目的: 验证 softmax axis 越界抛 ValueError。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_softmax_axis_out_of_range
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_softmax_axis_out_of_range() -> None:
    value = Memory([2, 3], NumericType.Float32)
    with pytest.raises(ValueError):
        _ = softmax(value, axis=2)
    with pytest.raises(ValueError):
        _ = softmax(value, axis=-3)


# OP-SM-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-27 09:34:06 +0800
# 最近一次运行成功时间: 2026-03-27 09:34:06 +0800
# 测试目的: 验证 softmax 非浮点 dtype 抛 TypeError。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_softmax_dtype_error
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_softmax_dtype_error() -> None:
    value = Memory([2, 3], NumericType.Int32)
    with pytest.raises(TypeError):
        _ = softmax(value)


# OP-SM-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-27 09:34:06 +0800
# 最近一次运行成功时间: 2026-03-27 09:34:06 +0800
# 测试目的: 验证 softmax 数值稳定性语义约束存在。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_softmax_numerical_stability_contract
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_softmax_numerical_stability_contract() -> None:
    doc = softmax.__doc__ or ""
    assert "exp(x - max(x)) / sum(exp(x - max(x)))" in doc
# OP-CONV-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-27 09:41:12 +0800
# 最近一次运行成功时间: 2026-03-27 09:41:12 +0800
# 测试目的: 验证 conv 基础路径、输出形状与参数校验规则（含 bias 对齐）。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_conv_basic
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_conv_basic() -> None:
    value = Memory([1, 3, 5, 5], NumericType.Float32, space=MemorySpace.GM)
    weight = Memory([8, 3, 3, 3], NumericType.Float32, space=MemorySpace.GM)
    result = conv(value, weight, sh=1, sw=1, dh=1, dw=1, ph=1, pw=1, pl=1, pr=1)
    assert result.shape.get_values() == [1, 8, 5, 5]
    assert result.dtype is NumericType.Float32
    assert result.space is MemorySpace.GM
    assert result.format is Farmat.Norm
    assert result.get_stride() == [200, 25, 5, 1]

    bias = Memory([8], NumericType.Float32, space=MemorySpace.GM)
    _ = conv(value, weight, bias=bias, sh=2, sw=2, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)

    with pytest.raises(TypeError):
        _ = conv("bad", weight)
    with pytest.raises(TypeError):
        _ = conv(value, "bad")
    with pytest.raises(ValueError):
        _ = conv(Memory([1, 3, 5], NumericType.Float32), weight)
    with pytest.raises(ValueError):
        _ = conv(value, Memory([8, 3, 3], NumericType.Float32))
    with pytest.raises(ValueError):
        _ = conv(Memory([1, 4, 5, 5], NumericType.Float32), weight)
    with pytest.raises(TypeError):
        _ = conv(Memory([1, 3, 5, 5], NumericType.Int32), weight)
    with pytest.raises(ValueError):
        _ = conv(Memory([1, 3, 5, 5], NumericType.Float32, space=MemorySpace.SM), weight)

    with pytest.raises(TypeError):
        _ = conv(value, weight, bias="bad")
    with pytest.raises(ValueError):
        _ = conv(value, weight, bias=Memory([1, 8], NumericType.Float32))
    with pytest.raises(ValueError):
        _ = conv(value, weight, bias=Memory([4], NumericType.Float32))
    with pytest.raises(TypeError):
        _ = conv(value, weight, bias=Memory([8], NumericType.Int32))
    with pytest.raises(ValueError):
        _ = conv(value, weight, bias=Memory([8], NumericType.Float32, space=MemorySpace.SM))

    with pytest.raises(ValueError):
        _ = conv(value, weight, sh=0, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)
    with pytest.raises(ValueError):
        _ = conv(value, weight, sh=1, sw=1, dh=0, dw=1, ph=0, pw=0, pl=0, pr=0)
    with pytest.raises(ValueError):
        _ = conv(value, weight, sh=1, sw=1, dh=1, dw=1, ph=-1, pw=0, pl=0, pr=0)
    with pytest.raises(TypeError):
        _ = conv(value, weight, sh=True, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)
    with pytest.raises(ValueError):
        _ = conv(
            value,
            Memory([8, 3, 7, 7], NumericType.Float32, space=MemorySpace.GM),
            sh=1,
            sw=1,
            dh=1,
            dw=1,
            ph=0,
            pw=0,
            pl=0,
            pr=0,
        )
# OP-ACT-001
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-27 09:44:59 +0800
# 最近一次运行成功时间: 2026-03-27 09:44:59 +0800
# 测试目的: 验证 relu/sigmoid/tanh/hard_sigmoid 输出继承输入描述。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_activation_basic
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_activation_basic() -> None:
    value = Memory([2, 3], NumericType.Float32, space=MemorySpace.SM, stride=[3, 1], format=Farmat.CLast)
    for func in (relu, sigmoid, tanh):
        result = func(value)
        assert result.shape.get_values() == value.shape.get_values()
        assert result.dtype is value.dtype
        assert result.space is value.space
        assert result.format is value.format
        assert result.get_stride() == value.get_stride()

    hard_result = hard_sigmoid(value, alpha=0.2, beta=0.5)
    assert hard_result.shape.get_values() == value.shape.get_values()
    assert hard_result.dtype is value.dtype
    assert hard_result.space is value.space
    assert hard_result.format is value.format
    assert hard_result.get_stride() == value.get_stride()


# OP-ACT-002
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-27 09:44:59 +0800
# 最近一次运行成功时间: 2026-03-27 09:44:59 +0800
# 测试目的: 验证 leaky_relu alpha 参数接受有限数值并继承输入描述。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_activation_leaky_relu_alpha
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_activation_leaky_relu_alpha() -> None:
    value = Memory([4, 1], NumericType.Float16, space=MemorySpace.GM, stride=[1, 1], format=Farmat.Norm)
    for alpha in (0.01, 0, -0.5, 2):
        result = leaky_relu(value, alpha=alpha)
        assert result.shape.get_values() == value.shape.get_values()
        assert result.dtype is value.dtype
        assert result.space is value.space
        assert result.format is value.format
        assert result.get_stride() == value.get_stride()


# OP-ACT-003
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-27 09:44:59 +0800
# 最近一次运行成功时间: 2026-03-27 09:44:59 +0800
# 测试目的: 验证激活函数对非法输入、dtype 与参数报错。
# 使用示例: pytest -q test/operation/test_operation_nn.py -k test_nn_activation_invalid_input
# 对应功能实现文件路径: kernel_gen/operation/nn.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_nn.py
def test_nn_activation_invalid_input() -> None:
    value = Memory([2, 2], NumericType.Float32)

    with pytest.raises(TypeError):
        _ = relu("bad")

    with pytest.raises(TypeError):
        _ = sigmoid(Memory([2, 2], NumericType.Int32))

    with pytest.raises(TypeError):
        _ = tanh(Memory([2, 2], NumericType.Bool))

    with pytest.raises(TypeError):
        _ = leaky_relu(value, alpha=True)

    with pytest.raises(TypeError):
        _ = leaky_relu(value, alpha=SymbolDim("N"))

    with pytest.raises(ValueError):
        _ = leaky_relu(value, alpha=float("nan"))

    with pytest.raises(ValueError):
        _ = leaky_relu(value, alpha=float("inf"))

    with pytest.raises(TypeError):
        _ = hard_sigmoid(value, alpha=True, beta=0.5)

    with pytest.raises(TypeError):
        _ = hard_sigmoid(value, alpha=0.2, beta=SymbolDim("B"))

    with pytest.raises(ValueError):
        _ = hard_sigmoid(value, alpha=0.2, beta=float("-inf"))
