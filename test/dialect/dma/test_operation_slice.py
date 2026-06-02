"""dma dialect operation slice tests.
功能说明:
- 验证 `kernel_gen.dialect.dma` package root 公开 API 的对应行为。

使用示例:
- `pytest -q test/dialect/dma/test_operation_slice.py`

关联文件:
- spec: spec/dialect/dma.md
- 功能实现: kernel_gen/dialect/dma/
- 测试文件: test/dialect/dma/test_operation_slice.py
"""

from test.dialect.dma.helpers import *  # noqa: F401,F403

def test_dma_load_result_space_mismatch() -> None:
    source_type = _make_memory_type(space="global")
    target_type = _make_memory_type(space="shared")
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]
    offsets = _make_symbol_operands([0, 0])
    sizes = _make_symbol_operands([2, 4])
    strides = _make_symbol_operands([1, 1])
    op = DmaLoadOp(target, source, offsets, sizes, strides)
    op.verify()

    bad_target_type = _make_memory_type(shape=_dim_array([2, 3]), space="shared")
    bad_target = _TestOp(result_types=[bad_target_type]).results[0]
    op = DmaLoadOp(bad_target, source, offsets, sizes, strides)
    with pytest.raises(KernelCodeError, match="target shape must match sizes"):
        op.verify()

def test_dma_load_accepts_symbol_iter_offset() -> None:
    source_type = _make_memory_type()
    target_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]
    iter_offset = _TestOp(result_types=[SymbolIterType.from_bounds("0", "N", "1")]).results[0]
    zero_offset = _make_symbol_operands([0])[0]
    offsets = [iter_offset, zero_offset]
    sizes = _make_symbol_operands([2, 4])
    strides = _make_symbol_operands([1, 1])
    op = DmaLoadOp(target, source, offsets, sizes, strides)
    op.verify()

def test_dma_slice_rank_mismatch() -> None:
    source_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[source_type]).results[0]
    offsets = _make_symbol_operands([0])
    sizes = _make_symbol_operands([2])
    strides = _make_symbol_operands([1])
    op = DmaSliceOp(target, source, offsets, sizes, strides)
    with pytest.raises(KernelCodeError, match="length must match rank"):
        op.verify()

    offsets = _make_symbol_operands([0, 0])
    sizes = _make_symbol_operands([2, 4])
    strides = _make_symbol_operands([1, 1])
    target_type = _make_memory_type(shape=_dim_array([2, 3]))
    target = _TestOp(result_types=[target_type]).results[0]
    op = DmaSliceOp(target, source, offsets, sizes, strides)
    with pytest.raises(KernelCodeError, match="shape must match sizes"):
        op.verify()

def test_dma_slice_non_unit_stride_rejected() -> None:
    source_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[source_type]).results[0]
    offsets = _make_symbol_operands([0, 0])
    sizes = _make_symbol_operands([2, 4])
    strides = _make_symbol_operands([1, 2])
    op = DmaSliceOp(target, source, offsets, sizes, strides)
    with pytest.raises(KernelCodeError, match="dma stride must be 1 in current implementation"):
        op.verify()

def test_dma_store_size_mismatch() -> None:
    source_type = _make_memory_type(shape=_dim_array([2, 4]))
    target_type = _make_memory_type(shape=_dim_array([8, 4]))
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]
    offsets = _make_symbol_operands([0, 0])
    sizes = _make_symbol_operands([2, 2])
    strides = _make_symbol_operands([1, 1])
    op = DmaStoreOp(target, source, offsets, sizes, strides)
    with pytest.raises(KernelCodeError, match="source shape must match sizes"):
        op.verify()

def test_dma_deslice_verify_success() -> None:
    source_type = _make_memory_type(shape=_dim_array([2, 4]))
    target_type = _make_memory_type(shape=_dim_array([8, 4]))
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]
    offsets = _make_symbol_operands([0, 0])
    sizes = _make_symbol_operands([2, 4])
    strides = _make_symbol_operands([1, 1])
    op = DmaDesliceOp(target, source, offsets, sizes, strides)
    op.verify()

def test_dma_dynamic_symbol_int_operands_valid() -> None:
    source_type = _make_memory_type(
        shape=_dim_array(["TM", "TN"]),
        stride=_dim_array(["TN", 1]),
    )
    result_type = _make_memory_type(
        shape=_dim_array(["TM", "TN"]),
        stride=_dim_array(["TN", 1]),
        space="shared",
    )
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[source_type]).results[0]
    tile = _TestOp(result_types=[result_type]).results[0]
    offsets = _make_symbol_operands(["TO", "TI"])
    sizes = _make_symbol_operands(["TM", "TN"])
    strides = _make_symbol_operands([1, 1])

    DmaLoadOp(tile, source, offsets, sizes, strides).verify()
    DmaSliceOp(tile, source, offsets, sizes, strides).verify()
    DmaStoreOp(target, tile, offsets, sizes, strides).verify()
    DmaDesliceOp(target, tile, offsets, sizes, strides).verify()
