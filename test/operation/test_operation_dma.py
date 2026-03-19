"""dma operation API tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 python/operation/dma.py 的搬运 API。

使用示例:
- pytest -q test/operation/test_operation_dma.py

关联文件:
- 功能实现: python/operation/dma.py
- Spec 文档: spec/operation/dma.md
- 测试文件: test/operation/test_operation_dma.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.operation.dma import alloc, copy, deslice, free, load, slice, store
from python.symbol_variable.memory import Memory, MemorySpace
from python.symbol_variable.type import NumericType


# TC-OP-DMA-AF-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 04:07:24 +0800
# 最近一次运行成功时间: 2026-03-19 04:07:24 +0800
# 功能说明: 验证 alloc 返回指定 shape/dtype/space 的 Memory。
# 使用示例: pytest -q test/operation/test_operation_dma.py -k test_alloc_returns_memory
# 对应功能实现文件路径: python/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma.py
def test_alloc_returns_memory() -> None:
    buf = alloc(["M", "N"], NumericType.Float32, space=MemorySpace.SM)
    assert isinstance(buf, Memory)
    assert buf.shape.get_values() == ["M", "N"]
    assert buf.dtype is NumericType.Float32
    assert buf.space is MemorySpace.SM


# TC-OP-DMA-AF-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 04:07:24 +0800
# 最近一次运行成功时间: 2026-03-19 04:07:24 +0800
# 功能说明: 验证 alloc 显式 stride 被保留。
# 使用示例: pytest -q test/operation/test_operation_dma.py -k test_alloc_preserves_explicit_stride
# 对应功能实现文件路径: python/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma.py
def test_alloc_preserves_explicit_stride() -> None:
    buf = alloc(["M", "N"], NumericType.Float32, stride=[1, 1])
    assert buf.stride is not None
    assert buf.stride.get_values() == [1, 1]


# TC-OP-DMA-AF-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 04:07:24 +0800
# 最近一次运行成功时间: 2026-03-19 04:07:24 +0800
# 功能说明: 验证 alloc 非法 shape/stride 抛 ValueError。
# 使用示例: pytest -q test/operation/test_operation_dma.py -k test_alloc_invalid_shape_or_stride
# 对应功能实现文件路径: python/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma.py
def test_alloc_invalid_shape_or_stride() -> None:
    with pytest.raises(ValueError):
        alloc("MN", NumericType.Float32)
    with pytest.raises(ValueError):
        alloc([1, 2], NumericType.Float32, stride=[1])


# TC-OP-DMA-AF-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 04:07:24 +0800
# 最近一次运行成功时间: 2026-03-19 04:07:24 +0800
# 功能说明: 验证 free 接受 Memory 并返回 None。
# 使用示例: pytest -q test/operation/test_operation_dma.py -k test_free_returns_none
# 对应功能实现文件路径: python/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma.py
def test_free_returns_none() -> None:
    buf = Memory([32, 32], NumericType.Float32)
    result = free(buf)
    assert result is None


# TC-OP-DMA-AF-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 04:07:24 +0800
# 最近一次运行成功时间: 2026-03-19 04:07:24 +0800
# 功能说明: 验证 free 非 Memory 输入抛 TypeError。
# 使用示例: pytest -q test/operation/test_operation_dma.py -k test_free_type_error
# 对应功能实现文件路径: python/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma.py
def test_free_type_error() -> None:
    with pytest.raises(TypeError):
        free("buf")


# TC-OP-DMA-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-18 21:24:29 +0800
# 最近一次运行成功时间: 2026-03-18 21:24:29 +0800
# 功能说明: 验证 copy 在完全匹配时通过。
# 使用示例: pytest -q test/operation/test_operation_dma.py -k test_copy_success
# 对应功能实现文件路径: python/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma.py
def test_copy_success() -> None:
    src = Memory(["M", "N"], NumericType.Float32, space=MemorySpace.GM, stride=[1, 1])
    dst = Memory(["M", "N"], NumericType.Float32, space=MemorySpace.SM, stride=[1, 1])
    result = copy(src, dst)
    assert result is None


# TC-OP-DMA-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-18 21:24:29 +0800
# 最近一次运行成功时间: 2026-03-18 21:24:29 +0800
# 功能说明: 验证 copy shape mismatch 抛 ValueError。
# 使用示例: pytest -q test/operation/test_operation_dma.py -k test_copy_shape_mismatch
# 对应功能实现文件路径: python/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma.py
def test_copy_shape_mismatch() -> None:
    src = Memory(["M", "N"], NumericType.Float32)
    dst = Memory(["M", "K"], NumericType.Float32)
    with pytest.raises(ValueError):
        copy(src, dst)


# TC-OP-DMA-010
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 08:37:32 +0800
# 最近一次运行成功时间: 2026-03-19 08:37:32 +0800
# 功能说明: 验证 copy stride mismatch 抛 ValueError。
# 使用示例: pytest -q test/operation/test_operation_dma.py -k test_copy_stride_mismatch
# 对应功能实现文件路径: python/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma.py
def test_copy_stride_mismatch() -> None:
    src = Memory(["M", "N"], NumericType.Float32, stride=[1, 1])
    dst = Memory(["M", "N"], NumericType.Float32, stride=[1, 2])
    with pytest.raises(ValueError):
        copy(src, dst)


# TC-OP-DMA-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-18 21:24:29 +0800
# 最近一次运行成功时间: 2026-03-18 21:24:29 +0800
# 功能说明: 验证 load 返回结果块并切换到目标空间。
# 使用示例: pytest -q test/operation/test_operation_dma.py -k test_load_result_space
# 对应功能实现文件路径: python/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma.py
def test_load_result_space() -> None:
    src = Memory(["M", "N"], NumericType.Float32, space=MemorySpace.GM)
    tile = load(src, offsets=[0, 0], sizes=[32, 32], strides=[1, 1], space=MemorySpace.SM)
    assert tile.shape.get_values() == [32, 32]
    assert tile.dtype is NumericType.Float32
    assert tile.space is MemorySpace.SM
    assert tile.stride is None


# TC-OP-DMA-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-18 21:24:29 +0800
# 最近一次运行成功时间: 2026-03-18 21:24:29 +0800
# 功能说明: 验证 slice 返回块的 shape 等于 sizes。
# 使用示例: pytest -q test/operation/test_operation_dma.py -k test_slice_result_shape
# 对应功能实现文件路径: python/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma.py
def test_slice_result_shape() -> None:
    src = Memory(["M", "N"], NumericType.Float32)
    sub = slice(src, offsets=[0, 16], sizes=[8, 8], strides=[1, 1], space=MemorySpace.LM)
    assert sub.shape.get_values() == [8, 8]
    assert sub.stride is None


# TC-OP-DMA-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-18 21:24:29 +0800
# 最近一次运行成功时间: 2026-03-18 21:24:29 +0800
# 功能说明: 验证 store 的 source.shape 与 sizes 不一致时报错。
# 使用示例: pytest -q test/operation/test_operation_dma.py -k test_store_size_mismatch
# 对应功能实现文件路径: python/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma.py
def test_store_size_mismatch() -> None:
    src = Memory([16, 16], NumericType.Float32)
    dst = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(ValueError):
        store(src, dst, offsets=[0, 0], sizes=[32, 32], strides=[1, 1])


# TC-OP-DMA-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-18 21:24:29 +0800
# 最近一次运行成功时间: 2026-03-18 21:24:29 +0800
# 功能说明: 验证 deslice 的 source.shape 与 sizes 不一致时报错。
# 使用示例: pytest -q test/operation/test_operation_dma.py -k test_deslice_size_mismatch
# 对应功能实现文件路径: python/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma.py
def test_deslice_size_mismatch() -> None:
    src = Memory([16, 16], NumericType.Float32)
    dst = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(ValueError):
        deslice(src, dst, offsets=[0, 0], sizes=[32, 32], strides=[1, 1])


# TC-OP-DMA-007
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-18 21:24:29 +0800
# 最近一次运行成功时间: 2026-03-18 21:24:29 +0800
# 功能说明: 验证 offsets/sizes/strides 长度与 rank 不一致时报错。
# 使用示例: pytest -q test/operation/test_operation_dma.py -k test_dma_index_rank_mismatch
# 对应功能实现文件路径: python/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma.py
def test_dma_index_rank_mismatch() -> None:
    src = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(ValueError):
        load(src, offsets=[0], sizes=[1, 2], strides=[1, 1])


# TC-OP-DMA-008
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-18 21:24:29 +0800
# 最近一次运行成功时间: 2026-03-18 21:24:29 +0800
# 功能说明: 验证非 1 stride 明确报错。
# 使用示例: pytest -q test/operation/test_operation_dma.py -k test_dma_non_unit_stride_rejected
# 对应功能实现文件路径: python/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma.py
def test_dma_non_unit_stride_rejected() -> None:
    src = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(NotImplementedError):
        load(src, offsets=[0, 0], sizes=[1, 1], strides=[1, 2])


# TC-OP-DMA-009
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-18 21:24:29 +0800
# 最近一次运行成功时间: 2026-03-18 21:24:29 +0800
# 功能说明: 验证非 Memory 输入触发 TypeError。
# 使用示例: pytest -q test/operation/test_operation_dma.py -k test_dma_type_error
# 对应功能实现文件路径: python/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma.py
def test_dma_type_error() -> None:
    dst = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(TypeError):
        copy("source", dst)
