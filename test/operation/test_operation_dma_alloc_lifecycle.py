"""dma family tests.

创建者: 小李飞刀
最后一次更改: jcc你莫辜负

功能说明:
- 覆盖 `kernel_gen.operation.dma` 的 family 级测试布局。

使用示例:
- pytest -q test/operation/test_operation_dma_alloc_lifecycle.py

关联文件:
- 功能实现: kernel_gen/operation/dma.py
- Spec 文档: spec/operation/dma.md
- 测试文件: test/operation/test_operation_dma_alloc_lifecycle.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import kernel_gen.operation.dma as dma_api
from kernel_gen.operation.dma import alloc, cast, copy, deslice, flatten, free, load, reshape, slice, store, view
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.symbol_shape import SymbolShape
from kernel_gen.symbol_variable.type import Farmat, NumericType


# TC-OP-DMA-AF-001
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 alloc 返回指定 shape/dtype/space 的 Memory。
# 使用示例: pytest -q test/operation/test_operation_dma_alloc_lifecycle.py -k test_alloc_returns_memory
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_alloc_lifecycle.py
def test_alloc_returns_memory() -> None:
    buf = alloc(["M", "N"], NumericType.Float32, space=MemorySpace.SM)
    assert isinstance(buf, Memory)
    assert buf.shape.get_values() == ["M", "N"]
    assert buf.dtype is NumericType.Float32
    assert buf.space is MemorySpace.SM


# TC-OP-DMA-AF-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-25 02:32:27 +0800
# 最近一次运行成功时间: 2026-03-25 02:32:27 +0800
# 测试目的: 验证 alloc 默认 stride 按连续布局生成，且默认 space 为 GM。
# 使用示例: pytest -q test/operation/test_operation_dma_alloc_lifecycle.py -k test_alloc_default_stride_for_symbolic_shape
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_alloc_lifecycle.py
def test_alloc_default_stride_for_symbolic_shape() -> None:
    buf = alloc(["M", "N"], NumericType.Float32)

    assert buf.space is MemorySpace.GM
    assert buf.get_stride()[0].get_value() == "N"
    assert buf.get_stride()[1] == 1
    assert buf.get_shape() == ["M", "N"]

    static_buf = alloc([2, 4], NumericType.Int32)
    assert static_buf.get_stride() == [4, 1]


# TC-OP-DMA-AF-008
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
# 测试目的: 验证 alloc 支持显式 format 并保留默认值。
# 使用示例: pytest -q test/operation/test_operation_dma_alloc_lifecycle.py -k test_alloc_preserves_format
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_alloc_lifecycle.py
def test_alloc_preserves_format() -> None:
    buf = alloc([2, 2], NumericType.Float32, format=Farmat.CLast)
    assert buf.format is Farmat.CLast
    default_buf = alloc([2, 2], NumericType.Float32)
    assert default_buf.format is Farmat.Norm


# TC-OP-DMA-AF-002
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 alloc 显式 stride 被保留。
# 使用示例: pytest -q test/operation/test_operation_dma_alloc_lifecycle.py -k test_alloc_preserves_explicit_stride
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_alloc_lifecycle.py
def test_alloc_preserves_explicit_stride() -> None:
    buf = alloc(["M", "N"], NumericType.Float32, stride=[1, 1])
    assert buf.stride is not None
    assert buf.stride.get_values() == [1, 1]


# TC-OP-DMA-AF-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 alloc 非法 shape/stride 抛 ValueError。
# 使用示例: pytest -q test/operation/test_operation_dma_alloc_lifecycle.py -k test_alloc_invalid_shape_or_stride
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_alloc_lifecycle.py
def test_alloc_invalid_shape_or_stride() -> None:
    with pytest.raises(ValueError):
        alloc("MN", NumericType.Float32)
    with pytest.raises(ValueError):
        alloc([object()], NumericType.Float32)
    with pytest.raises(ValueError):
        alloc([1, 2], NumericType.Float32, stride=[1])


# TC-OP-DMA-AF-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 alloc 的 dtype/space/format 类型错误。
# 使用示例: pytest -q test/operation/test_operation_dma_alloc_lifecycle.py -k test_alloc_invalid_dtype_or_space
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_alloc_lifecycle.py
def test_alloc_invalid_dtype_or_space() -> None:
    with pytest.raises(TypeError):
        alloc([1, 2], "float32")
    with pytest.raises(TypeError):
        alloc([1, 2], NumericType.Float32, space="GM")
    with pytest.raises(TypeError):
        alloc([1, 2], NumericType.Float32, format="Norm")


# TC-OP-DMA-AF-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 free 接受 Memory 并返回 None。
# 使用示例: pytest -q test/operation/test_operation_dma_alloc_lifecycle.py -k test_free_returns_none
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_alloc_lifecycle.py
def test_free_returns_none() -> None:
    buf = Memory([32, 32], NumericType.Float32)
    result = free(buf)
    assert result is None


# TC-OP-DMA-AF-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 free 非 Memory 输入抛 TypeError。
# 使用示例: pytest -q test/operation/test_operation_dma_alloc_lifecycle.py -k test_free_type_error
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_alloc_lifecycle.py
def test_free_type_error() -> None:
    with pytest.raises(TypeError):
        free("buf")


# TC-OP-DMA-001
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 copy 返回新 Memory，仅覆盖目标 space。
# 使用示例: pytest -q test/operation/test_operation_dma_alloc_lifecycle.py -k test_copy_success
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_alloc_lifecycle.py
def test_copy_success() -> None:
    src = Memory(["M", "N"], NumericType.Float32, space=MemorySpace.GM, stride=[1, 1], format=Farmat.CLast)
    result = copy(src, MemorySpace.SM)
    assert isinstance(result, Memory)
    assert result.shape.get_values() == ["M", "N"]
    assert result.stride is not None
    assert result.stride.get_values() == [1, 1]
    assert result.dtype is NumericType.Float32
    assert result.space is MemorySpace.SM
    assert result.format is Farmat.CLast


# TC-OP-DMA-002
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 copy 输入类型错误触发 TypeError。
# 使用示例: pytest -q test/operation/test_operation_dma_alloc_lifecycle.py -k test_copy_type_error
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_alloc_lifecycle.py
def test_copy_type_error() -> None:
    src = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(TypeError, match="Memory"):
        copy("source", MemorySpace.SM)
    with pytest.raises(TypeError, match="MemorySpace"):
        copy(src, "SM")


# TC-OP-DMA-010
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 copy 继承 source 的 shape/stride/format 规格。
# 使用示例: pytest -q test/operation/test_operation_dma_alloc_lifecycle.py -k test_copy_preserves_spec
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_alloc_lifecycle.py
def test_copy_preserves_spec() -> None:
    src = Memory(["M", "N"], NumericType.Float32, space=MemorySpace.GM, stride=[SymbolDim("S") * SymbolDim("N"), 1])
    result = copy(src, MemorySpace.GM)
    assert result.shape.get_values() == src.shape.get_values()
    assert result.stride is not None
    assert result.stride.get_values() == src.stride.get_values()
    assert result.format is src.format


# TC-OP-DMA-011
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 cast 返回相同 shape/stride/space 的新 Memory 且 dtype 发生变化。
# 使用示例: pytest -q test/operation/test_operation_dma_alloc_lifecycle.py -k test_cast_changes_dtype
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_alloc_lifecycle.py
def test_cast_changes_dtype() -> None:
    src = Memory(["M", "N"], NumericType.Float32, space=MemorySpace.SM, stride=[1, 1])
    dst = cast(src, NumericType.Float16)
    assert dst.shape.get_values() == ["M", "N"]
    assert dst.stride is not None
    assert dst.stride.get_values() == [1, 1]
    assert dst.space is MemorySpace.SM
    assert dst.dtype is NumericType.Float16


# TC-OP-DMA-022
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 cast 显式覆盖 memoryspace。
# 使用示例: pytest -q test/operation/test_operation_dma_alloc_lifecycle.py -k test_cast_overrides_space
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_alloc_lifecycle.py
def test_cast_overrides_space() -> None:
    src = Memory(["M", "N"], NumericType.Int32, space=MemorySpace.SM, stride=[1, 1], format=Farmat.CLast)
    dst = cast(src, NumericType.Int64, memoryspace=MemorySpace.GM)
    assert dst.shape.get_values() == ["M", "N"]
    assert dst.stride is not None
    assert dst.stride.get_values() == [1, 1]
    assert dst.space is MemorySpace.GM
    assert dst.format is Farmat.CLast
    assert dst.dtype is NumericType.Int64


# TC-OP-DMA-012
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 cast 非法 dtype 或 memoryspace 触发 TypeError。
# 使用示例: pytest -q test/operation/test_operation_dma_alloc_lifecycle.py -k test_cast_invalid_dtype
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_alloc_lifecycle.py
def test_cast_invalid_dtype() -> None:
    src = Memory([1, 2], NumericType.Float32)
    with pytest.raises(TypeError):
        cast(src, "float32")
    with pytest.raises(TypeError):
        cast(src, NumericType.Float32, memoryspace="GM")


# TC-OP-DMA-013
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 cast 不支持的转换路径显式报错。
# 使用示例: pytest -q test/operation/test_operation_dma_alloc_lifecycle.py -k test_cast_unsupported_conversion
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_alloc_lifecycle.py
def test_cast_unsupported_conversion() -> None:
    src = Memory([1, 2], NumericType.Float32)
    with pytest.raises(NotImplementedError):
        cast(src, NumericType.Int32)


# TC-OP-DMA-027
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 cast 支持同 dtype 与整数类型之间的转换。
# 使用示例: pytest -q test/operation/test_operation_dma_alloc_lifecycle.py -k test_cast_supported_conversions
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_alloc_lifecycle.py
def test_cast_supported_conversions() -> None:
    src = Memory([1, 2], NumericType.Int32, space=MemorySpace.LM)
    same = cast(src, NumericType.Int32)
    assert same.dtype is NumericType.Int32
    assert same.shape.get_values() == [1, 2]
    assert same.space is MemorySpace.LM
    upgraded = cast(src, NumericType.Int64)
    assert upgraded.dtype is NumericType.Int64
    assert upgraded.shape.get_values() == [1, 2]


# TC-OP-DMA-019
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 reshape 返回新 Memory 且继承 dtype/space/format。
# 使用示例: pytest -q test/operation/test_operation_dma_alloc_lifecycle.py -k test_reshape_returns_memory
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_alloc_lifecycle.py
def test_reshape_returns_memory() -> None:
    src = Memory([2, 3, 4], NumericType.Float32, space=MemorySpace.SM)
    dst = reshape(src, shape=[6, 4])
    assert isinstance(dst, Memory)
    assert dst.shape.get_values() == [6, 4]
    assert dst.dtype is NumericType.Float32
    assert dst.space is MemorySpace.SM
    assert dst.format is src.format


# TC-OP-DMA-020
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 reshape 在连续布局下生成默认 stride。
# 使用示例: pytest -q test/operation/test_operation_dma_alloc_lifecycle.py -k test_reshape_default_stride_contiguous
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_alloc_lifecycle.py
def test_reshape_default_stride_contiguous() -> None:
    src = Memory([2, 3, 4], NumericType.Float32)
    dst = reshape(src, shape=[6, 4])
    assert dst.stride is not None
    assert dst.stride.get_values() == [4, 1]


# TC-OP-DMA-021
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 reshape 非法 shape 或非连续布局触发错误。
# 使用示例: pytest -q test/operation/test_operation_dma_alloc_lifecycle.py -k test_reshape_invalid_shape_or_stride
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_alloc_lifecycle.py
def test_reshape_invalid_shape_or_stride() -> None:
    src = Memory([2, 3, 4], NumericType.Float32)
    with pytest.raises(ValueError, match="shape"):
        reshape(src, shape="24")
    with pytest.raises(ValueError, match="numel"):
        reshape(src, shape=[5, 5])
    non_contiguous = Memory([2, 3, 4], NumericType.Float32, stride=[100, 4, 1])
    with pytest.raises(ValueError, match="contiguous"):
        reshape(non_contiguous, shape=[6, 4])


# TC-OP-DMA-017
# 创建者: ChatGPT
# 最后一次更改: ChatGPT
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 flatten 在连续布局下返回一维 shape 与 stride=[1]。
# 使用示例: pytest -q test/operation/test_operation_dma_alloc_lifecycle.py -k test_flatten_contiguous
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_alloc_lifecycle.py
def test_flatten_contiguous() -> None:
    src = Memory(["M", "K", "N"], NumericType.Float32, space=MemorySpace.LM)
    dst = flatten(src)
    assert dst.shape.get_values() == ["K*M*N"]
    assert dst.stride is not None
    assert dst.stride.get_values() == [1]
    assert dst.dtype is NumericType.Float32
    assert dst.space is MemorySpace.LM
    assert dst.format is src.format


# TC-OP-DMA-018
# 创建者: ChatGPT
# 最后一次更改: ChatGPT
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 flatten 对非连续布局显式报错。
# 使用示例: pytest -q test/operation/test_operation_dma_alloc_lifecycle.py -k test_flatten_non_contiguous_rejected
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_alloc_lifecycle.py
def test_flatten_non_contiguous_rejected() -> None:
    src = Memory([2, 3, 4], NumericType.Float32, stride=[100, 4, 1])
    with pytest.raises(ValueError, match="contiguous"):
        flatten(src)
