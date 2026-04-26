"""memory operation tests.

创建者: 金铲铲大作战
最后一次更改: OpenAI Codex

功能说明:
- 覆盖 Memory 的逐元素算术、比较和 helper 边界。

使用示例:
- pytest -q test/symbol_variable/test_memory_operation.py

关联文件:
- 功能实现: kernel_gen/symbol_variable/memory.py
- Spec 文档: spec/symbol_variable/memory.md
- 测试文件: test/symbol_variable/test_memory_operation.py
"""

from __future__ import annotations

import operator

import pytest

from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import Farmat, NumericType


def _assert_memory_metadata(
    mem: Memory,
    *,
    shape: list[int | str],
    dtype: NumericType,
    stride: list[int | str],
    format: Farmat,
    space: MemorySpace | None = None,
) -> None:
    """校验 Memory 的公开元信息。"""
    assert mem.shape.get_values() == shape
    assert mem.dtype is dtype
    assert mem.stride.get_values() == stride
    assert mem.format is format
    if space is not None:
        assert mem.space is space


@pytest.mark.parametrize(
    "op",
    [
        operator.add,
        operator.sub,
        operator.mul,
        operator.truediv,
        operator.floordiv,
    ],
)
def test_memory_binary_arithmetic_preserves_lhs_metadata(op) -> None:
    lhs = Memory(["N", 4], NumericType.Int32, space=MemorySpace.SM, stride=[4, 1], format=Farmat.CLast)
    rhs = Memory(["N", 4], NumericType.Float32, space=MemorySpace.GM, stride=[8, 1], format=Farmat.Norm)
    result = op(lhs, rhs)

    assert isinstance(result, Memory)
    _assert_memory_metadata(
        result,
        shape=["N", 4],
        dtype=NumericType.Float32,
        stride=[4, 1],
        format=Farmat.CLast,
        space=MemorySpace.SM,
    )


def test_memory_repr_and_str_share_same_text() -> None:
    mem = Memory(["N", 4], NumericType.Int32, space=MemorySpace.SM, stride=[4, 1], format=Farmat.CLast)
    rep = repr(mem)

    assert rep.startswith("Memory(")
    assert str(mem) == rep


@pytest.mark.parametrize(
    "op",
    [
        lambda mem: mem + 1,
        lambda mem: 1 + mem,
        lambda mem: mem - 1,
        lambda mem: 1 - mem,
        lambda mem: mem * 2,
        lambda mem: 2 * mem,
        lambda mem: mem / 2,
        lambda mem: 2 / mem,
        lambda mem: mem // 2,
        lambda mem: 2 // mem,
        lambda mem: mem + True,
        lambda mem: mem - True,
        lambda mem: True + mem,
        lambda mem: True - mem,
        lambda mem: mem * True,
        lambda mem: True * mem,
        lambda mem: mem / True,
        lambda mem: True / mem,
        lambda mem: mem // True,
        lambda mem: True // mem,
    ],
)
def test_memory_scalar_arithmetic_promotes_to_int32(op) -> None:
    mem = Memory([2, 2], NumericType.Int8, stride=[2, 1], format=Farmat.CLast)
    result = op(mem)

    _assert_memory_metadata(
        result,
        shape=[2, 2],
        dtype=NumericType.Int32,
        stride=[2, 1],
        format=Farmat.CLast,
    )


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


@pytest.mark.parametrize(
    "result",
    [
        lambda lhs, rhs: lhs == rhs,
        lambda lhs, rhs: lhs < 1,
        lambda lhs, rhs: lhs != rhs,
        lambda lhs, rhs: lhs <= 1,
        lambda lhs, rhs: lhs > 0,
        lambda lhs, rhs: lhs >= rhs,
    ],
)
def test_memory_compare_returns_bool_dtype(result) -> None:
    lhs = Memory([1, "M"], NumericType.Float32)
    rhs = Memory([1, "M"], NumericType.Float32)
    mem = result(lhs, rhs)

    assert isinstance(mem, Memory)
    assert mem.shape.get_values() == [1, "M"]
    assert mem.dtype is NumericType.Bool


def test_memory_shape_mismatch() -> None:
    lhs = Memory([1, 2], NumericType.Float32)
    rhs = Memory([1, 2, 3], NumericType.Float32)

    with pytest.raises(ValueError):
        _ = lhs + rhs


def test_memory_dtype_mismatch() -> None:
    lhs = Memory([1, 2], NumericType.Bool)
    rhs = Memory([1, 2], NumericType.Int32)

    with pytest.raises(TypeError):
        _ = lhs + rhs


def test_memory_scalar_type_error_and_supported_int64() -> None:
    mem = Memory([1], NumericType.Int32)
    mem_bool = Memory([1], NumericType.Bool)
    mem64 = Memory([1], NumericType.Int64)

    with pytest.raises(TypeError):
        _ = mem + "1"
    with pytest.raises(TypeError):
        _ = mem_bool + 1

    result = mem64 + 1
    assert result.dtype is NumericType.Int64


def test_memory_operation_preserves_tlm123_space() -> None:
    lhs = Memory([4], NumericType.Float16, space=MemorySpace.TLM2, stride=[1], format=Farmat.Norm)
    rhs = Memory([4], NumericType.Float16, space=MemorySpace.TLM3, stride=[1], format=Farmat.CLast)

    assert (lhs + rhs).space is MemorySpace.TLM2
    assert (lhs + 1).space is MemorySpace.TLM2
