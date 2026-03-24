"""memory tests.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 Memory/MemorySpace/LocalSpaceMeta 构造、表示与转换行为。

使用示例:
- pytest -q test/symbol_variable/test_memory.py

关联文件:
- 功能实现: kernel_gen/symbol_variable/memory.py
- Spec 文档: spec/symbol_variable/memory.md
- 测试文件: test/symbol_variable/test_memory.py

覆盖率:
- 覆盖率: 98% (kernel_gen/symbol_variable/memory.py)
- 覆盖率命令: pytest --cov=kernel_gen.symbol_variable.memory --cov-report=term-missing test/symbol_variable/test_memory.py test/operation/test_memory_operation.py
"""

from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.symbol_variable.memory import LocalSpaceMeta, Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.symbol_shape import SymbolShape
from kernel_gen.symbol_variable.type import Farmat, NumericType


# ME-001
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 12:05:49 +0800
# 最近一次运行成功时间: 2026-03-24 12:05:49 +0800
# 测试目的: 验证默认空间为 GM，且默认 dtype/shape/stride/format 可通过公开接口获取。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_default_space
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_default_space() -> None:
    mem = Memory([1, 2], NumericType.Float32)
    assert mem.space is MemorySpace.GM
    assert mem.stride is not None
    assert mem.stride.get_values() == [2, 1]

    default_mem = Memory([1, 2])
    assert default_mem.get_type() is NumericType.Float32
    assert default_mem.get_shape() == [1, 2]
    assert default_mem.get_stride() == [2, 1]
    assert default_mem.get_space() is MemorySpace.GM
    assert default_mem.get_format() is Farmat.Norm


# ME-002
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 12:05:49 +0800
# 最近一次运行成功时间: 2026-03-24 12:05:49 +0800
# 测试目的: 验证指定空间写入。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_custom_space
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_custom_space() -> None:
    mem = Memory([1], NumericType.Int32, space=MemorySpace.LM)
    assert mem.space is MemorySpace.LM


# ME-003
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 12:05:49 +0800
# 最近一次运行成功时间: 2026-03-24 12:05:49 +0800
# 测试目的: 验证 __repr__ 包含空间名与张量字段表达。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_repr
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_repr() -> None:
    mem = Memory([1, 2], NumericType.Float32)
    rep = repr(mem)
    assert rep.startswith("Memory(GM,")
    assert "Tensor(" in rep
    assert "shape=" in rep
    assert "dtype=" in rep
    assert "stride=" in rep
    assert "format=" in rep
    assert "stride=Shape(2, 1)" in rep


# ME-004
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 12:05:49 +0800
# 最近一次运行成功时间: 2026-03-24 12:05:49 +0800
# 测试目的: 验证 tensor-like 字段直入构造保持 shape/dtype/stride/format。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_construct_from_tensor_fields
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_construct_from_tensor_fields() -> None:
    class DummyTensor:
        def __init__(self, shape, dtype, stride, format):
            self.shape = shape
            self.dtype = dtype
            self.stride = stride
            self.format = format

    tensor = DummyTensor(["N", 4], NumericType.Float32, stride=[4, 1], format=Farmat.Norm)
    mem = Memory(
        tensor.shape,
        tensor.dtype,
        stride=tensor.stride,
        format=tensor.format,
    )
    assert isinstance(mem, Memory)
    assert mem.space is MemorySpace.GM
    assert mem.shape.get_values() == ["N", 4]
    assert mem.dtype is tensor.dtype
    assert mem.stride.get_values() == [4, 1]
    assert mem.format is tensor.format


# ME-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 12:05:49 +0800
# 最近一次运行成功时间: 2026-03-24 12:05:49 +0800
# 测试目的: 验证显式 stride 列表输入可被规整为 SymbolShape，且 rank 不匹配时抛错。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_explicit_stride_list
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_explicit_stride_list() -> None:
    mem = Memory([2, 3], NumericType.Int32, stride=[3, 1])
    assert isinstance(mem.stride, SymbolShape)
    assert mem.stride.get_values() == [3, 1]
    with pytest.raises(ValueError):
        Memory([2, 3], NumericType.Int32, stride=[3])


# ME-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 12:05:49 +0800
# 最近一次运行成功时间: 2026-03-24 12:05:49 +0800
# 测试目的: 验证动态 shape/stride 输入保持动态维度语义，并通过公开接口序列化。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_dynamic_shape_stride
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_dynamic_shape_stride() -> None:
    mem = Memory(["N", 32], NumericType.Float32, stride=["C", 1])
    assert mem.shape.get_values() == ["N", 32]
    assert mem.stride.get_values() == ["C", 1]
    assert mem.get_shape() == ["N", 32]
    assert mem.get_stride() == [SymbolDim("C"), 1]


# ME-007
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 12:05:49 +0800
# 最近一次运行成功时间: 2026-03-24 12:05:49 +0800
# 测试目的: 验证 shape/stride 可直接接收 SymbolShape。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_shape_stride_accept_symbol_shape
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_shape_stride_accept_symbol_shape() -> None:
    shape = SymbolShape([1, "N"])
    stride = SymbolShape([2, 1])
    mem = Memory(shape, NumericType.Float32, stride=stride)
    assert mem.shape is shape
    assert mem.stride is stride


# ME-008
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 12:05:49 +0800
# 最近一次运行成功时间: 2026-03-24 12:05:49 +0800
# 测试目的: 验证默认 format 与显式 format 保持可见。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_default_format
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_default_format() -> None:
    default_mem = Memory([1, 2], NumericType.Float32)
    explicit_mem = Memory([1, 2], NumericType.Float32, format=Farmat.CLast)
    assert default_mem.format is Farmat.Norm
    assert explicit_mem.format is Farmat.CLast


# ME-009
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 12:05:49 +0800
# 最近一次运行成功时间: 2026-03-24 12:05:49 +0800
# 测试目的: 验证 LocalSpaceMeta 冻结与 MemorySpace 元信息字段。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_space_meta
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_space_meta() -> None:
    meta = MemorySpace.GM.value
    assert isinstance(meta, LocalSpaceMeta)
    assert meta.name == "GM"
    assert meta.max_size is None
    assert meta.align == 1024
    with pytest.raises(FrozenInstanceError):
        meta.align = 256


# ME-017
# 创建者: OpenAI
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 12:05:49 +0800
# 最近一次运行成功时间: 2026-03-24 12:05:49 +0800
# 测试目的: 验证未显式提供 stride 时默认生成连续行主序步幅。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_default_stride_generated_row_major
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_default_stride_generated_row_major() -> None:
    mem = Memory([2, 3, 4], NumericType.Float32)
    assert mem.stride is not None
    assert mem.stride.get_values() == [12, 4, 1]


# ME-018
# 创建者: OpenAI
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 12:05:49 +0800
# 最近一次运行成功时间: 2026-03-24 12:05:49 +0800
# 测试目的: 验证符号维度默认 stride 使用无空格乘法表达式并保持字符串表示一致。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_default_stride_symbolic_expression_repr
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_default_stride_symbolic_expression_repr() -> None:
    m = SymbolDim("M")
    k = SymbolDim("K")
    n = SymbolDim("N")
    mem = Memory([m, k, n], NumericType.Float32)
    assert mem.stride is not None
    assert mem.stride.get_values() == ["K*N", "N", 1]
    assert str(mem) == (
        "Memory(GM,Tensor(shape=Shape(M, K, N), dtype=NumericType.Float32, "
        "stride=Shape(K*N, N, 1), format=Farmat.Norm))"
    )


# ME-019
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 12:05:49 +0800
# 最近一次运行成功时间: 2026-03-24 12:05:49 +0800
# 测试目的: 验证字符串形状输入时默认 stride 生成与字符串表示一致。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_default_stride_symbolic_expression_from_strings
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_default_stride_symbolic_expression_from_strings() -> None:
    mem = Memory(["M", "K", "N"], NumericType.Float32)
    assert mem.stride is not None
    assert mem.stride.get_values() == ["K*N", "N", 1]
    assert str(mem) == (
        "Memory(GM,Tensor(shape=Shape(M, K, N), dtype=NumericType.Float32, "
        "stride=Shape(K*N, N, 1), format=Farmat.Norm))"
    )


# ME-015
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 12:05:49 +0800
# 最近一次运行成功时间: 2026-03-24 12:05:49 +0800
# 测试目的: 验证混合 dtype 时结果使用更高精度类型。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_memory_mixed_dtype_promotes_to_highest_precision
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_memory_mixed_dtype_promotes_to_highest_precision() -> None:
    lhs = Memory([1], NumericType.Int32)
    rhs = Memory([1], NumericType.Float32)
    result = lhs + rhs
    assert result.dtype is NumericType.Float32


# ME-021
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 12:05:49 +0800
# 最近一次运行成功时间: 2026-03-24 12:05:49 +0800
# 测试目的: 验证浮点标量参与运算时结果提升到 Float32。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_memory_float_scalar_promotes_to_highest_precision
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_memory_float_scalar_promotes_to_highest_precision() -> None:
    mem = Memory([1], NumericType.Int32)
    result = mem + 1.5
    assert result.dtype is NumericType.Float32


# ME-022
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 12:05:49 +0800
# 最近一次运行成功时间: 2026-03-24 12:05:49 +0800
# 测试目的: 验证 / 与 // 采用相同的最高精度提升规则。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_memory_division_uses_highest_precision_dtype
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_memory_division_uses_highest_precision_dtype() -> None:
    lhs = Memory([1], NumericType.Float16)
    rhs = Memory([1], NumericType.Float32)
    truediv = lhs / rhs
    floordiv = lhs // rhs
    assert truediv.dtype is NumericType.Float32
    assert floordiv.dtype is NumericType.Float32


# ME-023
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 12:05:49 +0800
# 最近一次运行成功时间: 2026-03-24 12:05:49 +0800
# 测试目的: 验证 reflected 算术与正向运算使用相同的提升规则。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_memory_reflected_arithmetic_uses_same_promotion_rule
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_memory_reflected_arithmetic_uses_same_promotion_rule() -> None:
    mem = Memory([1], NumericType.Int8)
    results = [2 + mem, 2 - mem, 2 * mem, 2 / mem, 2 // mem]
    for result in results:
        assert result.dtype is NumericType.Int32


# ME-024
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 12:05:49 +0800
# 最近一次运行成功时间: 2026-03-24 12:05:49 +0800
# 测试目的: 验证不支持的对象操作数抛 TypeError。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_memory_invalid_operand_type_error
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_memory_invalid_operand_type_error() -> None:
    mem = Memory([1], NumericType.Float32)
    with pytest.raises(TypeError):
        _ = mem + object()
