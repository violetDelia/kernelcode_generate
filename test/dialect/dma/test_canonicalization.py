"""dma dialect canonicalization tests.
功能说明:
- 验证 `kernel_gen.dialect.dma` package root 公开 API 的对应行为。

使用示例:
- `pytest -q test/dialect/dma/test_canonicalization.py`

关联文件:
- spec: spec/dialect/dma.md
- 功能实现: kernel_gen/dialect/dma/
- 测试文件: test/dialect/dma/test_canonicalization.py
"""

from test.dialect.dma.helpers import *  # noqa: F401,F403

def test_dma_fill_canonicalization_removes_safe_full_overwrites() -> None:
    memory_type = _make_memory_type()

    target_op = _TestOp(result_types=[memory_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    fill_module = _canonicalized_module(
        [
            target_op,
            c0_op,
            c1_op,
            DmaFillOp(target_op.results[0], c0_op.results[0]),
            DmaFillOp(target_op.results[0], c1_op.results[0]),
        ]
    )
    assert _count_ops(fill_module, DmaFillOp) == 1

    target_op = _TestOp(result_types=[memory_type])
    source_op = _TestOp(result_types=[memory_type])
    c0_op = _make_symbol_value_op(0)
    copy_module = _canonicalized_module(
        [
            target_op,
            source_op,
            c0_op,
            DmaFillOp(target_op.results[0], c0_op.results[0]),
            DmaCopyOp(target_op.results[0], source_op.results[0]),
        ]
    )
    assert _count_ops(copy_module, DmaFillOp) == 0

    target_op = _TestOp(result_types=[memory_type])
    c0_op = _make_symbol_value_op(0)
    c7_op = _make_symbol_value_op(7)
    broadcast_module = _canonicalized_module(
        [
            target_op,
            c0_op,
            c7_op,
            DmaFillOp(target_op.results[0], c0_op.results[0]),
            DmaBroadcastOp(target_op.results[0], c7_op.results[0]),
        ]
    )
    assert _count_ops(broadcast_module, DmaFillOp) == 0

    part_type = _make_memory_type(shape=_dim_array([1, 4]), stride=_dim_array([4, 1]))
    target_op = _TestOp(result_types=[memory_type])
    part_op = _TestOp(result_types=[part_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c4_op = _make_symbol_value_op(4)
    deslice_module = _canonicalized_module(
        [
            target_op,
            part_op,
            c0_op,
            c1_op,
            c4_op,
            DmaFillOp(target_op.results[0], c0_op.results[0]),
            DmaDesliceOp(
                target_op.results[0],
                part_op.results[0],
                [c0_op.results[0], c0_op.results[0]],
                [c1_op.results[0], c4_op.results[0]],
                [c1_op.results[0], c1_op.results[0]],
            ),
        ]
    )
    assert _count_ops(deslice_module, DmaFillOp) == 0

    dynamic_type = _make_memory_type(shape=_dim_array(["M", "N", "K"]), stride=_dim_array(["N*K", "K", 1]))
    target_op = _TestOp(result_types=[dynamic_type])
    source_op = _TestOp(result_types=[dynamic_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    m_op = _make_symbol_value_op("M")
    n_op = _make_symbol_value_op("N")
    k_op = _make_symbol_value_op("K")
    dynamic_deslice_module = _canonicalized_module(
        [
            target_op,
            source_op,
            c0_op,
            c1_op,
            m_op,
            n_op,
            k_op,
            DmaFillOp(target_op.results[0], c0_op.results[0]),
            DmaDesliceOp(
                target_op.results[0],
                source_op.results[0],
                [c0_op.results[0], c0_op.results[0], c0_op.results[0]],
                [m_op.results[0], n_op.results[0], k_op.results[0]],
                [c1_op.results[0], c1_op.results[0], c1_op.results[0]],
            ),
        ]
    )
    assert _count_ops(dynamic_deslice_module, DmaFillOp) == 0

    target_op = _TestOp(result_types=[memory_type])
    source_op = _TestOp(result_types=[memory_type])
    other_op = _TestOp(result_types=[memory_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c2_op = _make_symbol_value_op(2)
    c4_op = _make_symbol_value_op(4)
    alias = DmaReshapeOp(target_op.results[0], [c2_op.results[0], c4_op.results[0]], memory_type)
    full_deslice_then_alias_read = _canonicalized_module(
        [
            target_op,
            source_op,
            other_op,
            c0_op,
            c1_op,
            c2_op,
            c4_op,
            alias,
            DmaFillOp(target_op.results[0], c0_op.results[0]),
            DmaDesliceOp(
                target_op.results[0],
                source_op.results[0],
                [c0_op.results[0], c0_op.results[0]],
                [c2_op.results[0], c4_op.results[0]],
                [c1_op.results[0], c1_op.results[0]],
            ),
            DmaCopyOp(other_op.results[0], alias.result),
        ]
    )
    assert _count_ops(full_deslice_then_alias_read, DmaFillOp) == 0

def test_dma_fill_canonicalization_keeps_reads_and_aliases() -> None:
    memory_type = _make_memory_type()

    target_op = _TestOp(result_types=[memory_type])
    source_op = _TestOp(result_types=[memory_type])
    other_op = _TestOp(result_types=[memory_type])
    c0_op = _make_symbol_value_op(0)
    read_before_copy = _canonicalized_module(
        [
            target_op,
            source_op,
            other_op,
            c0_op,
            DmaFillOp(target_op.results[0], c0_op.results[0]),
            DmaCopyOp(other_op.results[0], target_op.results[0]),
            DmaCopyOp(target_op.results[0], source_op.results[0]),
        ]
    )
    assert _count_ops(read_before_copy, DmaFillOp) == 1

    part_type = _make_memory_type(shape=_dim_array([1, 4]), stride=_dim_array([4, 1]))
    target_op = _TestOp(result_types=[memory_type])
    part_op = _TestOp(result_types=[part_type])
    other_op = _TestOp(result_types=[memory_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c4_op = _make_symbol_value_op(4)
    read_before_deslice = _canonicalized_module(
        [
            target_op,
            part_op,
            other_op,
            c0_op,
            c1_op,
            c4_op,
            DmaFillOp(target_op.results[0], c0_op.results[0]),
            DmaCopyOp(other_op.results[0], target_op.results[0]),
            DmaDesliceOp(
                target_op.results[0],
                part_op.results[0],
                [c0_op.results[0], c0_op.results[0]],
                [c1_op.results[0], c4_op.results[0]],
                [c1_op.results[0], c1_op.results[0]],
            ),
        ]
    )
    assert _count_ops(read_before_deslice, DmaFillOp) == 1

    target_op = _TestOp(result_types=[memory_type])
    part_op = _TestOp(result_types=[part_type])
    other_op = _TestOp(result_types=[memory_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c4_op = _make_symbol_value_op(4)
    read_after_deslice = _canonicalized_module(
        [
            target_op,
            part_op,
            other_op,
            c0_op,
            c1_op,
            c4_op,
            DmaFillOp(target_op.results[0], c0_op.results[0]),
            DmaDesliceOp(
                target_op.results[0],
                part_op.results[0],
                [c0_op.results[0], c0_op.results[0]],
                [c1_op.results[0], c4_op.results[0]],
                [c1_op.results[0], c1_op.results[0]],
            ),
            DmaCopyOp(other_op.results[0], target_op.results[0]),
        ]
    )
    assert _count_ops(read_after_deslice, DmaFillOp) == 1

    target_op = _TestOp(result_types=[memory_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c2_op = _make_symbol_value_op(2)
    c4_op = _make_symbol_value_op(4)
    view = DmaViewOp(
        target_op.results[0],
        [c0_op.results[0], c0_op.results[0]],
        [c2_op.results[0], c4_op.results[0]],
        [c1_op.results[0], c1_op.results[0]],
        memory_type,
    )
    alias_reader = _canonicalized_module(
        [
            target_op,
            c0_op,
            c1_op,
            c2_op,
            c4_op,
            DmaFillOp(target_op.results[0], c0_op.results[0]),
            view,
            DmaCopyOp(target_op.results[0], view.result),
        ]
    )
    assert _count_ops(alias_reader, DmaFillOp) == 1
    assert _count_ops(alias_reader, DmaViewOp) == 1

    target_op = _TestOp(result_types=[memory_type])
    c0_op = _make_symbol_value_op(0)
    c2_op = _make_symbol_value_op(2)
    c4_op = _make_symbol_value_op(4)
    reshape = DmaReshapeOp(target_op.results[0], [c2_op.results[0], c4_op.results[0]], memory_type)
    reshape_alias_reader = _canonicalized_module(
        [
            target_op,
            c0_op,
            c2_op,
            c4_op,
            DmaFillOp(target_op.results[0], c0_op.results[0]),
            reshape,
            DmaCopyOp(target_op.results[0], reshape.result),
        ]
    )
    assert _count_ops(reshape_alias_reader, DmaFillOp) == 1
    assert _count_ops(reshape_alias_reader, DmaReshapeOp) == 1

def test_dma_fill_canonicalization_keeps_self_read_write_and_side_effect_boundaries() -> None:
    memory_type = _make_memory_type()

    target_op = _TestOp(result_types=[memory_type])
    c0_op = _make_symbol_value_op(0)
    self_copy = _canonicalized_module(
        [
            target_op,
            c0_op,
            DmaFillOp(target_op.results[0], c0_op.results[0]),
            DmaCopyOp(target_op.results[0], target_op.results[0]),
        ]
    )
    assert _count_ops(self_copy, DmaFillOp) == 1

    target_op = _TestOp(result_types=[memory_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c2_op = _make_symbol_value_op(2)
    c4_op = _make_symbol_value_op(4)
    self_store = _canonicalized_module(
        [
            target_op,
            c0_op,
            c1_op,
            c2_op,
            c4_op,
            DmaFillOp(target_op.results[0], c0_op.results[0]),
            DmaStoreOp(
                target_op.results[0],
                target_op.results[0],
                [c0_op.results[0], c0_op.results[0]],
                [c2_op.results[0], c4_op.results[0]],
                [c1_op.results[0], c1_op.results[0]],
            ),
        ]
    )
    assert _count_ops(self_store, DmaFillOp) == 1

    part_type = _make_memory_type(shape=_dim_array([1, 4]), stride=_dim_array([4, 1]))
    target_op = _TestOp(result_types=[memory_type])
    part_op = _TestOp(result_types=[part_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c4_op = _make_symbol_value_op(4)
    partial_store = _canonicalized_module(
        [
            target_op,
            part_op,
            c0_op,
            c1_op,
            c4_op,
            DmaFillOp(target_op.results[0], c0_op.results[0]),
            DmaStoreOp(
                target_op.results[0],
                part_op.results[0],
                [c0_op.results[0], c0_op.results[0]],
                [c1_op.results[0], c4_op.results[0]],
                [c1_op.results[0], c1_op.results[0]],
            ),
        ]
    )
    assert _count_ops(partial_store, DmaFillOp) == 1

    target_op = _TestOp(result_types=[memory_type])
    source_op = _TestOp(result_types=[memory_type])
    c0_op = _make_symbol_value_op(0)
    region_boundary = _canonicalized_module(
        [
            target_op,
            source_op,
            c0_op,
            DmaFillOp(target_op.results[0], c0_op.results[0]),
            _make_region_side_effect_op(),
            DmaCopyOp(target_op.results[0], source_op.results[0]),
        ]
    )
    assert _count_ops(region_boundary, DmaFillOp) == 1

    target_op = _TestOp(result_types=[memory_type])
    source_op = _TestOp(result_types=[memory_type])
    c0_op = _make_symbol_value_op(0)
    unknown_boundary = _canonicalized_module(
        [
            target_op,
            source_op,
            c0_op,
            DmaFillOp(target_op.results[0], c0_op.results[0]),
            _make_unknown_side_effect_op(),
            DmaCopyOp(target_op.results[0], source_op.results[0]),
        ]
    )
    assert _count_ops(unknown_boundary, DmaFillOp) == 1

def test_dma_fill_canonicalization_keeps_subview_and_memory_broadcast_aliases() -> None:
    memory_type = _make_memory_type()
    byte_pool_type = _make_memory_type(shape=_dim_array([4]), stride=_dim_array([1]), element_type=i8)

    target_op = _TestOp(result_types=[byte_pool_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c4_op = _make_symbol_value_op(4)
    subview = DmaSubviewOp(target_op.results[0], c0_op.results[0], c4_op.results[0], c1_op.results[0], byte_pool_type)
    subview_copy_alias = _canonicalized_module(
        [
            target_op,
            c0_op,
            c1_op,
            c4_op,
            DmaFillOp(target_op.results[0], c0_op.results[0]),
            subview,
            DmaCopyOp(target_op.results[0], subview.result),
        ]
    )
    assert _count_ops(subview_copy_alias, DmaFillOp) == 1
    assert _count_ops(subview_copy_alias, DmaSubviewOp) == 1

    target_op = _TestOp(result_types=[memory_type])
    c0_op = _make_symbol_value_op(0)
    broadcast_target = _canonicalized_module(
        [
            target_op,
            c0_op,
            DmaFillOp(target_op.results[0], c0_op.results[0]),
            DmaBroadcastOp(target_op.results[0], target_op.results[0]),
        ]
    )
    assert _count_ops(broadcast_target, DmaFillOp) == 1

    target_op = _TestOp(result_types=[memory_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c2_op = _make_symbol_value_op(2)
    c4_op = _make_symbol_value_op(4)
    view = DmaViewOp(
        target_op.results[0],
        [c0_op.results[0], c0_op.results[0]],
        [c2_op.results[0], c4_op.results[0]],
        [c1_op.results[0], c1_op.results[0]],
        memory_type,
    )
    broadcast_view_alias = _canonicalized_module(
        [
            target_op,
            c0_op,
            c1_op,
            c2_op,
            c4_op,
            DmaFillOp(target_op.results[0], c0_op.results[0]),
            view,
            DmaBroadcastOp(target_op.results[0], view.result),
        ]
    )
    assert _count_ops(broadcast_view_alias, DmaFillOp) == 1
    assert _count_ops(broadcast_view_alias, DmaViewOp) == 1

    target_op = _TestOp(result_types=[byte_pool_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c4_op = _make_symbol_value_op(4)
    subview = DmaSubviewOp(target_op.results[0], c0_op.results[0], c4_op.results[0], c1_op.results[0], byte_pool_type)
    broadcast_subview_alias = _canonicalized_module(
        [
            target_op,
            c0_op,
            c1_op,
            c4_op,
            DmaFillOp(target_op.results[0], c0_op.results[0]),
            subview,
            DmaBroadcastOp(target_op.results[0], subview.result),
        ]
    )
    assert _count_ops(broadcast_subview_alias, DmaFillOp) == 1
    assert _count_ops(broadcast_subview_alias, DmaSubviewOp) == 1

def test_dma_view_reshape_canonicalization_only_removes_identity_aliases() -> None:
    memory_type = _make_memory_type()

    source_op = _TestOp(result_types=[memory_type])
    target_op = _TestOp(result_types=[memory_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c2_op = _make_symbol_value_op(2)
    c4_op = _make_symbol_value_op(4)
    identity_view = DmaViewOp(
        source_op.results[0],
        [c0_op.results[0], c0_op.results[0]],
        [c2_op.results[0], c4_op.results[0]],
        [c1_op.results[0], c1_op.results[0]],
        memory_type,
    )
    view_module = _canonicalized_module(
        [
            source_op,
            target_op,
            c0_op,
            c1_op,
            c2_op,
            c4_op,
            identity_view,
            DmaCopyOp(target_op.results[0], identity_view.result),
        ]
    )
    assert _count_ops(view_module, DmaViewOp) == 0

    source_op = _TestOp(result_types=[memory_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c2_op = _make_symbol_value_op(2)
    c4_op = _make_symbol_value_op(4)
    target_derived_view = DmaViewOp(
        source_op.results[0],
        [c0_op.results[0], c0_op.results[0]],
        [c2_op.results[0], c4_op.results[0]],
        [c1_op.results[0], c1_op.results[0]],
        memory_type,
    )
    target_derived_view_module = _canonicalized_module(
        [
            source_op,
            c0_op,
            c1_op,
            c2_op,
            c4_op,
            target_derived_view,
            DmaCopyOp(source_op.results[0], target_derived_view.result),
        ]
    )
    assert _count_ops(target_derived_view_module, DmaViewOp) == 1

    source_op = _TestOp(result_types=[memory_type])
    target_op = _TestOp(result_types=[memory_type])
    c2_op = _make_symbol_value_op(2)
    c4_op = _make_symbol_value_op(4)
    identity_reshape = DmaReshapeOp(source_op.results[0], [c2_op.results[0], c4_op.results[0]], memory_type)
    reshape_module = _canonicalized_module(
        [
            source_op,
            target_op,
            c2_op,
            c4_op,
            identity_reshape,
            DmaCopyOp(target_op.results[0], identity_reshape.result),
        ]
    )
    assert _count_ops(reshape_module, DmaReshapeOp) == 0

    source_op = _TestOp(result_types=[memory_type])
    c2_op = _make_symbol_value_op(2)
    c4_op = _make_symbol_value_op(4)
    target_derived_reshape = DmaReshapeOp(source_op.results[0], [c2_op.results[0], c4_op.results[0]], memory_type)
    target_derived_reshape_module = _canonicalized_module(
        [
            source_op,
            c2_op,
            c4_op,
            target_derived_reshape,
            DmaCopyOp(source_op.results[0], target_derived_reshape.result),
        ]
    )
    assert _count_ops(target_derived_reshape_module, DmaReshapeOp) == 1

    byte_pool_type = _make_memory_type(shape=_dim_array([16]), stride=_dim_array([1]), element_type=i8)
    typed_result_type = _make_memory_type(shape=_dim_array([4]), stride=_dim_array([1]))
    pool_op = _TestOp(result_types=[byte_pool_type])
    target_op = _TestOp(result_types=[typed_result_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c4_op = _make_symbol_value_op(4)
    typed_view = DmaViewOp(
        pool_op.results[0],
        [c0_op.results[0]],
        [c4_op.results[0]],
        [c1_op.results[0]],
        typed_result_type,
    )
    typed_view_module = _canonicalized_module(
        [
            pool_op,
            target_op,
            c0_op,
            c1_op,
            c4_op,
            typed_view,
            DmaCopyOp(target_op.results[0], typed_view.result),
        ]
    )
    assert _count_ops(typed_view_module, DmaViewOp) == 1

    source_type = _make_memory_type(shape=_dim_array([2, 2]), stride=_dim_array([2, 1]))
    changed_type = _make_memory_type(shape=_dim_array([1, 4]), stride=_dim_array([4, 1]))
    source_op = _TestOp(result_types=[source_type])
    target_op = _TestOp(result_types=[changed_type])
    c1_op = _make_symbol_value_op(1)
    c4_op = _make_symbol_value_op(4)
    changed_reshape = DmaReshapeOp(source_op.results[0], [c1_op.results[0], c4_op.results[0]], changed_type)
    changed_reshape_module = _canonicalized_module(
        [
            source_op,
            target_op,
            c1_op,
            c4_op,
            changed_reshape,
            DmaCopyOp(target_op.results[0], changed_reshape.result),
        ]
    )
    assert _count_ops(changed_reshape_module, DmaReshapeOp) == 1

def test_dma_reshape_canonicalization_composes_one_hop_reshape() -> None:
    flat_type = _make_memory_type(shape=_dim_array([4]), stride=_dim_array([1]))
    mid_type = _make_memory_type(shape=_dim_array([2, 2]), stride=_dim_array([2, 1]))
    final_type = _make_memory_type(shape=_dim_array([1, 4]), stride=_dim_array([4, 1]))
    source_op = _TestOp(result_types=[flat_type])
    target_op = _TestOp(result_types=[final_type])
    c1_op = _make_symbol_value_op(1)
    c2_op = _make_symbol_value_op(2)
    c4_op = _make_symbol_value_op(4)
    mid_reshape = DmaReshapeOp(source_op.results[0], [c2_op.results[0], c2_op.results[0]], mid_type)
    final_reshape = DmaReshapeOp(mid_reshape.result, [c1_op.results[0], c4_op.results[0]], final_type)
    composed_module = _canonicalized_module(
        [
            source_op,
            target_op,
            c1_op,
            c2_op,
            c4_op,
            mid_reshape,
            final_reshape,
            DmaCopyOp(target_op.results[0], final_reshape.result),
        ]
    )
    assert _count_ops(composed_module, DmaReshapeOp) == 1

    dynamic_source_type = _make_memory_type(shape=_dim_array(["M", "N"]), stride=_dim_array(["N", 1]))
    dynamic_mid_type = _make_memory_type(shape=_dim_array(["N", "M"]), stride=_dim_array(["M", 1]))
    dynamic_final_type = _make_memory_type(shape=_dim_array(["P", "Q"]), stride=_dim_array(["Q", 1]))
    source_op = _TestOp(result_types=[dynamic_source_type])
    target_op = _TestOp(result_types=[dynamic_final_type])
    n_op = _make_symbol_value_op("N")
    m_op = _make_symbol_value_op("M")
    p_op = _make_symbol_value_op("P")
    q_op = _make_symbol_value_op("Q")
    mid_reshape = DmaReshapeOp(source_op.results[0], [n_op.results[0], m_op.results[0]], dynamic_mid_type)
    final_reshape = DmaReshapeOp(mid_reshape.result, [p_op.results[0], q_op.results[0]], dynamic_final_type)
    dynamic_composed_module = _canonicalized_module(
        [
            source_op,
            target_op,
            n_op,
            m_op,
            p_op,
            q_op,
            mid_reshape,
            final_reshape,
            DmaCopyOp(target_op.results[0], final_reshape.result),
        ]
    )
    assert _count_ops(dynamic_composed_module, DmaReshapeOp) == 1

    source_op = _TestOp(result_types=[flat_type])
    mid_target_op = _TestOp(result_types=[mid_type])
    final_target_op = _TestOp(result_types=[final_type])
    c1_op = _make_symbol_value_op(1)
    c2_op = _make_symbol_value_op(2)
    c4_op = _make_symbol_value_op(4)
    mid_reshape = DmaReshapeOp(source_op.results[0], [c2_op.results[0], c2_op.results[0]], mid_type)
    final_reshape = DmaReshapeOp(mid_reshape.result, [c1_op.results[0], c4_op.results[0]], final_type)
    extra_use_module = _canonicalized_module(
        [
            source_op,
            mid_target_op,
            final_target_op,
            c1_op,
            c2_op,
            c4_op,
            mid_reshape,
            DmaCopyOp(mid_target_op.results[0], mid_reshape.result),
            final_reshape,
            DmaCopyOp(final_target_op.results[0], final_reshape.result),
        ]
    )
    assert _count_ops(extra_use_module, DmaReshapeOp) == 2

def test_dma_view_reshape_canonicalization_keeps_non_identity_boundaries() -> None:
    byte_pool_type = _make_memory_type(shape=_dim_array([32]), stride=_dim_array([1]), element_type=i8)
    typed_result_type = _make_memory_type(shape=_dim_array([4]), stride=_dim_array([1]))
    pool_op = _TestOp(result_types=[byte_pool_type])
    target_op = _TestOp(result_types=[typed_result_type])
    c1_op = _make_symbol_value_op(1)
    c4_op = _make_symbol_value_op(4)
    nonzero_offset_view = DmaViewOp(
        pool_op.results[0],
        [c1_op.results[0]],
        [c4_op.results[0]],
        [c1_op.results[0]],
        typed_result_type,
    )
    nonzero_offset_module = _canonicalized_module(
        [
            pool_op,
            target_op,
            c1_op,
            c4_op,
            nonzero_offset_view,
            DmaCopyOp(target_op.results[0], nonzero_offset_view.result),
        ]
    )
    assert _count_ops(nonzero_offset_module, DmaViewOp) == 1

    source_type = _make_memory_type(shape=_dim_array([2, 2]), stride=_dim_array([2, 1]))
    changed_type = _make_memory_type(shape=_dim_array([1, 4]), stride=_dim_array([4, 1]))
    source_op = _TestOp(result_types=[source_type])
    target_op = _TestOp(result_types=[changed_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c2_op = _make_symbol_value_op(2)
    c4_op = _make_symbol_value_op(4)
    shape_stride_change_view = DmaViewOp(
        source_op.results[0],
        [c0_op.results[0], c0_op.results[0]],
        [c1_op.results[0], c4_op.results[0]],
        [c2_op.results[0], c1_op.results[0]],
        changed_type,
    )
    shape_stride_change_module = _canonicalized_module(
        [
            source_op,
            target_op,
            c0_op,
            c1_op,
            c2_op,
            c4_op,
            shape_stride_change_view,
            DmaCopyOp(target_op.results[0], shape_stride_change_view.result),
        ]
    )
    assert _count_ops(shape_stride_change_module, DmaViewOp) == 1

    flat_type = _make_memory_type(shape=_dim_array([4]), stride=_dim_array([1]))
    rank_changed_type = _make_memory_type(shape=_dim_array([2, 2]), stride=_dim_array([2, 1]))
    source_op = _TestOp(result_types=[flat_type])
    target_op = _TestOp(result_types=[rank_changed_type])
    c2_op = _make_symbol_value_op(2)
    rank_change_reshape = DmaReshapeOp(source_op.results[0], [c2_op.results[0], c2_op.results[0]], rank_changed_type)
    rank_change_module = _canonicalized_module(
        [
            source_op,
            target_op,
            c2_op,
            rank_change_reshape,
            DmaCopyOp(target_op.results[0], rank_change_reshape.result),
        ]
    )
    assert _count_ops(rank_change_module, DmaReshapeOp) == 1

    dynamic_source_type = _make_memory_type(shape=_dim_array(["M", "N"]), stride=_dim_array(["N", 1]))
    dynamic_changed_type = _make_memory_type(shape=_dim_array(["N", "M"]), stride=_dim_array(["M", 1]))
    source_op = _TestOp(result_types=[dynamic_source_type])
    target_op = _TestOp(result_types=[dynamic_changed_type])
    n_op = _make_symbol_value_op("N")
    m_op = _make_symbol_value_op("M")
    dynamic_unproven_reshape = DmaReshapeOp(
        source_op.results[0],
        [n_op.results[0], m_op.results[0]],
        dynamic_changed_type,
    )
    dynamic_unproven_module = _canonicalized_module(
        [
            source_op,
            target_op,
            n_op,
            m_op,
            dynamic_unproven_reshape,
            DmaCopyOp(target_op.results[0], dynamic_unproven_reshape.result),
        ]
    )
    assert _count_ops(dynamic_unproven_module, DmaReshapeOp) == 1
