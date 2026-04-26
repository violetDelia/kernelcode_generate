"""memory tests.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 Memory/MemorySpace/LocalSpaceMeta 构造、表示与转换行为。

覆盖率信息:
- 当前覆盖率: `98%`（`kernel_gen.symbol_variable.memory`；`test_memory.py` + `test_memory_operation.py`，2026-04-09 +0800）
- 达标判定: 已达到 `95%` 覆盖率达标线。

覆盖率命令:
- `pytest -q --cov=kernel_gen.symbol_variable.memory --cov-report=term-missing --cov-fail-under=95 test/symbol_variable/test_memory.py test/symbol_variable/test_memory_operation.py`

使用示例:
- pytest -q test/symbol_variable/test_memory.py

关联文件:
- 功能实现: kernel_gen/symbol_variable/memory.py
- Spec 文档: spec/symbol_variable/memory.md
- 测试文件: test/symbol_variable/test_memory.py
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import pytest
import sympy as sp

from kernel_gen.symbol_variable.memory import LocalSpaceMeta, Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.symbol_shape import SymbolShape
from kernel_gen.symbol_variable.type import Farmat, NumericType


def _make_unsimplified_division_dim() -> SymbolDim:
    """构造保持除法链文本的动态维度。"""
    a_symbol = sp.symbols("A", integer=True, real=True)
    b_symbol = sp.symbols("B", integer=True, real=True)
    return SymbolDim(
        sp.Mul(
            sp.Mul(a_symbol, b_symbol, evaluate=False),
            sp.Pow(b_symbol, -1, evaluate=False),
            evaluate=False,
        )
    )


# ME-001
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 00:52:36 +0800
# 最近一次运行成功时间: 2026-03-25 00:52:36 +0800
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
# 最近一次运行测试时间: 2026-03-25 00:52:36 +0800
# 最近一次运行成功时间: 2026-03-25 00:52:36 +0800
# 测试目的: 验证指定空间写入。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_custom_space
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_custom_space() -> None:
    mem = Memory([1], NumericType.Int32, space=MemorySpace.LM)
    assert mem.space is MemorySpace.LM


# ME-002A
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-15 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-15 00:00:00 +0800
# 测试目的: 验证公开 TLM 空间已拆分为 TLM1/TLM2/TLM3，且旧 TLM 成员不再对外暴露。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_tlm123_spaces_and_legacy_tlm_absent
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_tlm123_spaces_and_legacy_tlm_absent() -> None:
    tlm1 = Memory([1], NumericType.Float16, space=MemorySpace.TLM1)
    tlm2 = Memory([2], NumericType.Float16, space=MemorySpace.TLM2)
    tlm3 = Memory([3], NumericType.Float16, space=MemorySpace.TLM3)

    assert tlm1.space is MemorySpace.TLM1
    assert tlm2.space is MemorySpace.TLM2
    assert tlm3.space is MemorySpace.TLM3
    assert MemorySpace.TLM1.value.name == "TLM1"
    assert MemorySpace.TLM2.value.name == "TLM2"
    assert MemorySpace.TLM3.value.name == "TLM3"
    assert not hasattr(MemorySpace, "TLM")


# ME-003
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 00:52:36 +0800
# 最近一次运行成功时间: 2026-03-25 00:52:36 +0800
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
# 最近一次运行测试时间: 2026-03-25 00:52:36 +0800
# 最近一次运行成功时间: 2026-03-25 00:52:36 +0800
# 测试目的: 验证 tensor-like 字段直入构造保持 shape/dtype/stride/format。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_construct_from_tensor_fields
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_construct_from_tensor_fields() -> None:
    tensor = SimpleNamespace(
        shape=["N", 4],
        dtype=NumericType.Float32,
        stride=[4, 1],
        format=Farmat.Norm,
    )
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
# 最近一次运行测试时间: 2026-03-25 00:52:36 +0800
# 最近一次运行成功时间: 2026-03-25 00:52:36 +0800
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
# 最近一次运行测试时间: 2026-03-25 00:52:36 +0800
# 最近一次运行成功时间: 2026-03-25 00:52:36 +0800
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


# ME-006A
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-18 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-18 00:00:00 +0800
# 测试目的: 验证动态 shape 的公开序列化继承 SymbolDim.get_value()，而不是底层 sympy 结构文本。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_dynamic_shape_public_values_use_symbol_dim_get_value
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_dynamic_shape_public_values_use_symbol_dim_get_value() -> None:
    reducible = _make_unsimplified_division_dim()
    mem = Memory([reducible, 4], NumericType.Float32, stride=[reducible, 1])

    assert mem.shape.get_values() == ["A*B/B", 4]
    assert mem.get_shape() == ["A*B/B", 4]
    assert mem.get_stride()[0].get_value() == "A*B/B"


# ME-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-25 00:52:36 +0800
# 最近一次运行成功时间: 2026-03-25 00:52:36 +0800
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
# 最近一次运行测试时间: 2026-03-25 00:52:36 +0800
# 最近一次运行成功时间: 2026-03-25 00:52:36 +0800
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
# 最近一次运行测试时间: 2026-03-25 00:52:36 +0800
# 最近一次运行成功时间: 2026-03-25 00:52:36 +0800
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
# 最近一次运行测试时间: 2026-03-25 00:52:36 +0800
# 最近一次运行成功时间: 2026-03-25 00:52:36 +0800
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
# 最近一次运行测试时间: 2026-03-25 00:52:36 +0800
# 最近一次运行成功时间: 2026-03-25 00:52:36 +0800
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
# 最近一次运行测试时间: 2026-03-25 00:52:36 +0800
# 最近一次运行成功时间: 2026-03-25 00:52:36 +0800
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


# ME-020
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-06 00:19 +0800
# 最近一次运行成功时间: 2026-04-06 00:19 +0800
# 测试目的: 验证 clone 过程保留 stride 中的符号表达式结构。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_clone_with_dtype_preserves_symbolic_stride_expression
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_clone_with_dtype_preserves_symbolic_stride_expression() -> None:
    h = SymbolDim("H")
    w = SymbolDim("W")
    stride_expr = h * 5
    mem = Memory([h, w], NumericType.Float32, stride=[stride_expr, 1])
    rhs = Memory([h, w], NumericType.Int32, stride=[stride_expr, 1])
    result = mem + rhs
    assert result.stride is not None
    assert mem.stride is not None
    original_dim = mem.stride.get_shape()[0]
    result_dim = result.stride.get_shape()[0]
    assert result_dim is not original_dim
    assert result_dim == original_dim


# ME-021
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-18 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-18 00:00:00 +0800
# 测试目的: 验证 Memory 运算前的 shape 校验按符号语义比较，而不是只比较序列化文本顺序。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_memory_shape_match_uses_symbol_dim_public_values
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_memory_shape_match_uses_symbol_dim_public_values() -> None:
    n_symbol = sp.symbols("N", integer=True, real=True)
    lhs_shape_dim = SymbolDim(sp.Mul(sp.Integer(8), n_symbol, evaluate=False))
    rhs_shape_dim = SymbolDim(sp.Mul(n_symbol, sp.Integer(8), evaluate=False))
    lhs = Memory([lhs_shape_dim, 4], NumericType.Float32, stride=[4, 1], format=Farmat.CLast)
    rhs = Memory([rhs_shape_dim, 4], NumericType.Float32, stride=[8, 1], format=Farmat.Norm)

    result = lhs + rhs

    assert lhs.shape.get_values() != rhs.shape.get_values()
    assert lhs.get_shape() == ["8*N", 4]
    assert rhs.get_shape() == ["N*8", 4]
    assert result.get_shape() == ["8*N", 4]
    assert result.dtype is NumericType.Float32
    assert result.space is lhs.space
    assert result.format is lhs.format
