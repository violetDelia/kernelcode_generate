"""dma family tests.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 `kernel_gen.operation.dma` 的 family 级测试布局。

使用示例:
- pytest -q test/operation/test_operation_dma_transfer_view.py

关联文件:
- 功能实现: kernel_gen/operation/dma.py
- Spec 文档: spec/operation/dma.md
- 测试文件: test/operation/test_operation_dma_transfer_view.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import kernel_gen.operation.dma as dma_api
from kernel_gen.operation.dma import deslice, load, slice, store, view
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.symbol_shape import SymbolShape
from kernel_gen.symbol_variable.type import Farmat, NumericType


# TC-OP-DMA-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 load 返回结果块并切换到目标空间。
# 使用示例: pytest -q test/operation/test_operation_dma_transfer_view.py -k test_load_result_space
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_transfer_view.py
def test_load_result_space() -> None:
    src = Memory(["M", "N"], NumericType.Float32, space=MemorySpace.GM, format=Farmat.CLast)
    tile = load(src, offsets=SymbolShape([0, 0]), sizes=SymbolShape([32, 32]), space=MemorySpace.SM)
    assert tile.shape.get_values() == [32, 32]
    assert tile.dtype is NumericType.Float32
    assert tile.space is MemorySpace.SM
    assert tile.stride is not None
    assert tile.stride.get_values() == [32, 1]
    assert tile.format is Farmat.CLast


# TC-OP-DMA-023
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 load 的 space 类型错误触发 TypeError。
# 使用示例: pytest -q test/operation/test_operation_dma_transfer_view.py -k test_load_invalid_space_type
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_transfer_view.py
def test_load_invalid_space_type() -> None:
    src = Memory(["M", "N"], NumericType.Float32, space=MemorySpace.GM)
    with pytest.raises(TypeError, match="MemorySpace"):
        load(src, offsets=[0, 0], sizes=[1, 1], strides=[1, 1], space="SM")


# TC-OP-DMA-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 slice 返回块的 shape 等于 sizes。
# 使用示例: pytest -q test/operation/test_operation_dma_transfer_view.py -k test_slice_result_shape
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_transfer_view.py
def test_slice_result_shape() -> None:
    src = Memory(["M", "N"], NumericType.Float32, format=Farmat.CLast)
    sub = slice(src, offsets=[0, 16], sizes=[8, 8], strides=[1, 1], space=MemorySpace.LM)
    assert sub.shape.get_values() == [8, 8]
    assert sub.stride is not None
    assert sub.stride.get_values() == [8, 1]
    assert sub.format is Farmat.CLast


# TC-OP-DMA-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 store 的 source.shape 与 sizes 不一致时报错。
# 使用示例: pytest -q test/operation/test_operation_dma_transfer_view.py -k test_store_size_mismatch
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_transfer_view.py
def test_store_size_mismatch() -> None:
    src = Memory([16, 16], NumericType.Float32)
    dst = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(ValueError):
        store(src, dst, offsets=[0, 0], sizes=[32, 32], strides=[1, 1])


# TC-OP-DMA-025
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 store/deslice dtype mismatch 触发 TypeError。
# 使用示例: pytest -q test/operation/test_operation_dma_transfer_view.py -k test_store_dtype_mismatch
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_transfer_view.py
def test_store_dtype_mismatch() -> None:
    src = Memory([16, 16], NumericType.Float32)
    dst = Memory(["M", "N"], NumericType.Float16)
    with pytest.raises(TypeError):
        store(src, dst, offsets=[0, 0], sizes=[16, 16], strides=[1, 1])
    with pytest.raises(TypeError):
        deslice(src, dst, offsets=[0, 0], sizes=[16, 16], strides=[1, 1])


# TC-OP-DMA-026
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 store 在匹配时返回 None。
# 使用示例: pytest -q test/operation/test_operation_dma_transfer_view.py -k test_store_success
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_transfer_view.py
def test_store_success() -> None:
    src = Memory([16, 16], NumericType.Float32)
    dst = Memory([32, 32], NumericType.Float32)
    result = store(src, dst, offsets=[0, 0], sizes=[16, 16], strides=[1, 1])
    assert result is None


# TC-OP-DMA-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 deslice 的 source.shape 与 sizes 不一致时报错。
# 使用示例: pytest -q test/operation/test_operation_dma_transfer_view.py -k test_deslice_size_mismatch
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_transfer_view.py
def test_deslice_size_mismatch() -> None:
    src = Memory([16, 16], NumericType.Float32)
    dst = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(ValueError):
        deslice(src, dst, offsets=[0, 0], sizes=[32, 32], strides=[1, 1])


# TC-OP-DMA-007
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 offsets/sizes/strides 长度与 rank 不一致时报错。
# 使用示例: pytest -q test/operation/test_operation_dma_transfer_view.py -k test_dma_index_rank_mismatch
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_transfer_view.py
def test_dma_index_rank_mismatch() -> None:
    src = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(ValueError, match="rank"):
        load(src, offsets=[0], sizes=[1, 2], strides=[1, 1])
    with pytest.raises(ValueError, match="rank"):
        load(src, offsets=[0, 0], sizes=[1, 1], strides=[1])


# TC-OP-DMA-024
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 sizes 中非正长度触发 ValueError。
# 使用示例: pytest -q test/operation/test_operation_dma_transfer_view.py -k test_dma_invalid_sizes
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_transfer_view.py
def test_dma_invalid_sizes() -> None:
    src = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(ValueError, match="size"):
        load(src, offsets=[0, 0], sizes=[0, 1], strides=[1, 1])


# TC-OP-DMA-008
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证非单位 stride 允许使用且执行边界校验。
# 使用示例: pytest -q test/operation/test_operation_dma_transfer_view.py -k test_dma_non_unit_stride_checked
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_transfer_view.py
def test_dma_non_unit_stride_checked() -> None:
    src = Memory([8, 16], NumericType.Float32)
    tile = load(src, offsets=[0, 0], sizes=[2, 4], strides=[1, 2])
    assert tile.shape.get_values() == [2, 4]
    with pytest.raises(ValueError, match="out of bounds"):
        load(src, offsets=[0, 12], sizes=[2, 4], strides=[1, 2])


# TC-OP-DMA-009
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证非 Memory 输入触发 TypeError。
# 使用示例: pytest -q test/operation/test_operation_dma_transfer_view.py -k test_dma_type_error
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_transfer_view.py
def test_dma_type_error() -> None:
    dst = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(TypeError, match="Memory"):
        load("source", offsets=[0, 0], sizes=[1, 1], strides=[1, 1])
    with pytest.raises(TypeError, match="Memory"):
        store(dst, "target", offsets=[0, 0], sizes=[1, 1], strides=[1, 1])


# TC-OP-DMA-014
# 创建者: ChatGPT
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 view(source, offset, size, stride) 返回 shape == size 且 stride 逐维组合的子视图 Memory。
# 使用示例: pytest -q test/operation/test_operation_dma_transfer_view.py -k test_view_subview_returns_memory
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_transfer_view.py
def test_view_subview_returns_memory() -> None:
    src = Memory([SymbolDim("M"), SymbolDim("K")], NumericType.Float32, space=MemorySpace.SM)
    dst = view(src, offset=[SymbolDim("M_t"), SymbolDim("K_t")], size=[2, 2], stride=[SymbolDim("stride"), 1])
    assert isinstance(dst, Memory)
    assert dst.shape.get_values() == [2, 2]
    assert dst.stride is not None
    assert dst.stride.get_values() == ["K*stride", 1]
    assert dst.dtype is NumericType.Float32
    assert dst.space is MemorySpace.SM
    assert dst.format is src.format


# TC-OP-DMA-015
# 创建者: ChatGPT
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 view 沿用 source 规格，并按 subview stride 组合返回结果 stride。
# 使用示例: pytest -q test/operation/test_operation_dma_transfer_view.py -k test_view_inherits_source_memoryspec
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_transfer_view.py
def test_view_inherits_source_memoryspec() -> None:
    src = Memory([8, 8], NumericType.Float32, space=MemorySpace.LM, stride=[32, 4], format=Farmat.CLast)
    dst = view(src, offset=[1, 2], size=[2, 2], stride=[2, 1])
    assert dst.shape.get_values() == [2, 2]
    assert dst.stride is not None
    assert dst.stride.get_values() == [64, 4]
    assert dst.dtype is NumericType.Float32
    assert dst.space is MemorySpace.LM
    assert dst.format is Farmat.CLast


# TC-OP-DMA-016
# 创建者: 我不是牛马
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 view 在静态场景下执行边界检查。
# 使用示例: pytest -q test/operation/test_operation_dma_transfer_view.py -k test_view_bounds_check
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_transfer_view.py
def test_view_bounds_check() -> None:
    src = Memory([8, 16], NumericType.Float32, space=MemorySpace.GM, format=Farmat.Norm)
    with pytest.raises(ValueError):
        view(src, offset=[0, 15], size=[2, 2], stride=[1, 1])
    with pytest.raises(ValueError):
        view(src, offset=[0, 14], size=[2, 2], stride=[1, 2])


# TC-OP-DMA-028
# 创建者: ChatGPT
# 最后一次更改: 摸鱼小分队
# 最近一次运行测试时间: 2026-03-24 19:29:54 +0800
# 最近一次运行成功时间: 2026-03-24 19:29:54 +0800
# 测试目的: 验证 view 的 offset/size/stride rank、负 offset、非正 size 与非正 stride 约束。
# 使用示例: pytest -q test/operation/test_operation_dma_transfer_view.py -k test_view_invalid_offset_size_stride
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_transfer_view.py
def test_view_invalid_offset_size_stride() -> None:
    src = Memory([2, 3], NumericType.Float32)
    with pytest.raises(ValueError):
        view(src, offset="MN", size=[2, 2], stride=[1, 1])
    with pytest.raises(ValueError):
        view(src, offset=[0], size=[2, 2], stride=[1, 1])
    with pytest.raises(ValueError):
        view(src, offset=[0, 0], size=[0, 2], stride=[1, 1])
    with pytest.raises(ValueError):
        view(src, offset=[0, 0], size=[2, 2], stride=[1])
    with pytest.raises(ValueError):
        view(src, offset=[-1, 0], size=[2, 2], stride=[1, 1])
    with pytest.raises(ValueError):
        view(src, offset=[0, 0], size=[2, 2], stride=[0, 1])


# TC-OP-DMA-029
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-16 00:49:00 +0800
# 最近一次运行成功时间: 2026-04-16 00:49:00 +0800
# 测试目的: 验证 load/store/slice/view 统一复用访问区域校验入口，而不是各自散写一轮。
# 使用示例: pytest -q test/operation/test_operation_dma_transfer_view.py -k test_dma_access_region_helpers_share_unified_validation_entry
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma_transfer_view.py
def test_dma_access_region_helpers_share_unified_validation_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    source = Memory([8, 8], NumericType.Float32)
    target = Memory([8, 8], NumericType.Float32)
    tile = Memory([2, 2], NumericType.Float32)
    calls: list[tuple[Memory, str, str, str, bool]] = []

    def fake_normalize_and_validate_access_region(
        memory: Memory,
        *,
        offsets: object,
        sizes: object,
        strides: object | None = None,
        offset_name: str = "offsets",
        size_name: str = "sizes",
        stride_name: str = "strides",
        offset_normalizer=object,
        size_normalizer=object,
        stride_normalizer=object,
    ) -> tuple[SymbolShape, SymbolShape, SymbolShape | None]:
        del offsets, sizes, offset_normalizer, size_normalizer, stride_normalizer
        calls.append((memory, offset_name, size_name, stride_name, strides is not None))
        normalized_strides = None if strides is None else SymbolShape([1, 1])
        return SymbolShape([0, 0]), SymbolShape([2, 2]), normalized_strides

    monkeypatch.setattr(dma_api, "_normalize_and_validate_access_region", fake_normalize_and_validate_access_region)

    load(source, offsets=[0, 0], sizes=[2, 2], strides=[1, 1], space=MemorySpace.SM)
    store(tile, target, offsets=[0, 0], sizes=[2, 2], strides=[1, 1])
    slice(source, offsets=[0, 0], sizes=[2, 2], strides=[1, 1], space=MemorySpace.LM)
    view(source, offset=[0, 0], size=[2, 2], stride=[1, 1])

    assert calls == [
        (source, "offsets", "sizes", "strides", True),
        (target, "offsets", "sizes", "strides", True),
        (source, "offsets", "sizes", "strides", True),
        (source, "offset", "size", "stride", True),
    ]
