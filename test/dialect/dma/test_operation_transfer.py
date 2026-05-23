"""dma dialect operation transfer tests.
功能说明:
- 验证 `kernel_gen.dialect.dma` package root 公开 API 的对应行为。

使用示例:
- `pytest -q test/dialect/dma/test_operation_transfer.py`

关联文件:
- spec: spec/dialect/dma.md
- 功能实现: kernel_gen/dialect/dma/
- 测试文件: test/dialect/dma/test_operation_transfer.py
"""

from test.dialect.dma.helpers import *  # noqa: F401,F403

def test_dma_copy_verify_success() -> None:
    memory_type = _make_memory_type()
    source = _TestOp(result_types=[memory_type]).results[0]
    target = _TestOp(result_types=[memory_type]).results[0]
    op = DmaCopyOp(target, source)
    op.verify()

def test_dma_copy_memory_effects_target_write_source_read() -> None:
    memory_type = _make_memory_type()
    target = _TestOp(result_types=[memory_type]).results[0]
    source = _TestOp(result_types=[memory_type]).results[0]
    op = DmaCopyOp(target, source)

    assert _effect_kinds_by_value(op) == {
        (MemoryEffectKind.WRITE, target),
        (MemoryEffectKind.READ, source),
    }

def test_dma_copy_shape_mismatch() -> None:
    source_type = _make_memory_type(shape=_dim_array([2, 4]))
    target_type = _make_memory_type(shape=_dim_array([2, 8]))
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]
    op = DmaCopyOp(target, source)
    with pytest.raises(VerifyException, match="shape mismatch"):
        op.verify()

def test_dma_cast_verify_success() -> None:
    source_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]
    target_type = NnMemoryType(source_type.shape, source_type.stride, i1, source_type.space)
    target = _TestOp(result_types=[target_type]).results[0]
    op = DmaCastOp(target, source)
    op.verify()

def test_dma_cast_layout_or_space_mismatch() -> None:
    source_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]

    target_type = _make_memory_type(shape=_dim_array([2, 5]))
    op = DmaCastOp(_TestOp(result_types=[target_type]).results[0], source)
    with pytest.raises(VerifyException, match="dma.cast shape mismatch"):
        op.verify()

    target_type = _make_memory_type(stride=_dim_array([5, 1]))
    op = DmaCastOp(_TestOp(result_types=[target_type]).results[0], source)
    with pytest.raises(VerifyException, match="dma.cast stride mismatch"):
        op.verify()

    target_type = _make_memory_type(space="shared")
    op = DmaCastOp(_TestOp(result_types=[target_type]).results[0], source)
    with pytest.raises(VerifyException, match="dma.cast space mismatch"):
        op.verify()

def test_dma_copy_rejects_stride_or_element_type_mismatch() -> None:
    source_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]

    stride_mismatch = _make_memory_type(stride=_dim_array([8, 1]))
    op = DmaCopyOp(_TestOp(result_types=[stride_mismatch]).results[0], source)
    with pytest.raises(VerifyException, match="dma.copy source/target stride mismatch"):
        op.verify()

    element_type_mismatch = NnMemoryType(source_type.shape, source_type.stride, i1, source_type.space)
    op = DmaCopyOp(_TestOp(result_types=[element_type_mismatch]).results[0], source)
    with pytest.raises(VerifyException, match="dma.copy source/target element_type mismatch"):
        op.verify()

def test_dma_transfer_ops_reject_element_space_or_result_mismatch() -> None:
    source_type = _make_memory_type()
    target_type = _make_memory_type(shape=_dim_array([8, 4]))
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]
    offsets = _make_symbol_operands([0, 0])
    sizes = _make_symbol_operands([2, 4])
    strides = _make_symbol_operands([1, 1])

    bad_load_type = NnMemoryType(source_type.shape, source_type.stride, i1, source_type.space)
    bad_load_target = _TestOp(result_types=[bad_load_type]).results[0]
    op = DmaLoadOp(bad_load_target, source, offsets, sizes, strides)
    with pytest.raises(VerifyException, match="dma.load element_type mismatch"):
        op.verify()

    store_source_type = NnMemoryType(source_type.shape, source_type.stride, i1, source_type.space)
    store_source = _TestOp(result_types=[store_source_type]).results[0]
    op = DmaStoreOp(target, store_source, offsets, sizes, strides)
    with pytest.raises(VerifyException, match="dma.store element_type mismatch"):
        op.verify()

    bad_slice_type = NnMemoryType(source_type.shape, source_type.stride, i1, source_type.space)
    bad_slice_target = _TestOp(result_types=[bad_slice_type]).results[0]
    op = DmaSliceOp(bad_slice_target, source, offsets, sizes, strides)
    with pytest.raises(VerifyException, match="dma.slice element_type mismatch"):
        op.verify()

    deslice_source = _TestOp(result_types=[source_type]).results[0]
    deslice_target_type = _make_memory_type(shape=_dim_array([8, 4]))
    deslice_target = _TestOp(result_types=[deslice_target_type]).results[0]
    bad_deslice_source_type = NnMemoryType(source_type.shape, source_type.stride, i1, source_type.space)
    bad_deslice_source = _TestOp(result_types=[bad_deslice_source_type]).results[0]
    op = DmaDesliceOp(
        deslice_target,
        bad_deslice_source,
        offsets,
        sizes,
        strides,
        deslice_target_type,
    )
    with pytest.raises(VerifyException, match="dma.deslice element_type mismatch"):
        op.verify()

    bad_result_type = _make_memory_type(shape=_dim_array([8, 4]), space="shared")
    op = DmaDesliceOp(deslice_target, deslice_source, offsets, sizes, strides, bad_result_type)
    with pytest.raises(VerifyException, match="dma.deslice result must match target type"):
        op.verify()

def test_dma_broadcast_accepts_memory_source() -> None:
    source_type = _make_memory_type(
        shape=_dim_array([1, 4]),
        stride=_dim_array([4, 1]),
    )
    target_type = _make_memory_type(
        shape=_dim_array([2, 4]),
        stride=_dim_array([4, 1]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]

    DmaBroadcastOp(target, source).verify()

def test_dma_broadcast_accepts_symbol_int_scalar() -> None:
    target = _TestOp(result_types=[_make_memory_type()]).results[0]
    scalar = _make_symbol_operands(["N"])[0]

    DmaBroadcastOp(target, scalar).verify()

def test_dma_broadcast_rejects_static_shape_mismatch() -> None:
    source_type = _make_memory_type(
        shape=_dim_array([2, 4]),
        stride=_dim_array([4, 1]),
    )
    target_type = _make_memory_type(
        shape=_dim_array([3, 4]),
        stride=_dim_array([4, 1]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]

    with pytest.raises(VerifyException, match="dma.broadcast shape mismatch"):
        DmaBroadcastOp(target, source).verify()

def test_dma_broadcast_rejects_scalar_type_mismatch() -> None:
    target = _TestOp(result_types=[_make_memory_type()]).results[0]
    scalar = _TestOp(result_types=[f32]).results[0]

    with pytest.raises(VerifyException, match="dma.broadcast scalar type mismatch"):
        DmaBroadcastOp(target, scalar).verify()

def test_dma_transpose_accepts_valid_perm() -> None:
    source_type = _make_memory_type(
        shape=_dim_array([2, 3]),
        stride=_dim_array([3, 1]),
    )
    target_type = _make_memory_type(
        shape=_dim_array([3, 2]),
        stride=_dim_array([2, 1]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]

    DmaTransposeOp(target, source, perm=[1, 0]).verify()

def test_dma_transpose_accepts_unknown_outer_stride() -> None:
    source_type = _make_memory_type(
        shape=_dim_array(["A", "?", "N"]),
        stride=_dim_array(["?", "N", 1]),
    )
    target_type = _make_memory_type(
        shape=_dim_array(["A", "?", "N"]),
        stride=_dim_array(["?", "N", 1]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]

    DmaTransposeOp(target, source, perm=[0, 1, 2]).verify()

def test_dma_transpose_rejects_invalid_perm() -> None:
    source_type = _make_memory_type(
        shape=_dim_array([2, 3]),
        stride=_dim_array([3, 1]),
    )
    target_type = _make_memory_type(
        shape=_dim_array([3, 2]),
        stride=_dim_array([2, 1]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]

    with pytest.raises(VerifyException, match="dma.transpose perm"):
        DmaTransposeOp(target, source, perm=[1, 1]).verify()
