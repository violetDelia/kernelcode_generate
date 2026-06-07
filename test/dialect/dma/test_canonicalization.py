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

from xdsl.dialects import scf

from kernel_gen.dialect.kernel import KernelMatmulFusionOp, KernelMatmulOp
from kernel_gen.dialect.symbol import SymbolForOp, SymbolNeOp

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

def test_dma_fill_canonicalization_keeps_root_fill_before_partial_alias_writer_and_root_read() -> None:
    """验证 partial alias writer 不能当作 root fill 的完整覆盖。

    功能说明:
    - `fill(root) -> subview(root partial) -> fill(subview) -> read(root)` 必须保留 root fill。
    - 锁定 partial alias writer 不会跳过后续 root read。

    使用示例:
    - pytest -q test/dialect/dma/test_canonicalization.py -k partial_alias_writer
    """

    root_type = _make_memory_type(shape=_dim_array([8]), stride=_dim_array([1]), element_type=i8)
    subview_type = _make_memory_type(shape=_dim_array([4]), stride=_dim_array([1]), element_type=i8)
    root_op = _TestOp(result_types=[root_type])
    reader_op = _TestOp(result_types=[root_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c4_op = _make_symbol_value_op(4)
    subview = DmaSubviewOp(root_op.results[0], c0_op.results[0], c4_op.results[0], c1_op.results[0], subview_type)
    module = _canonicalized_module(
        [
            root_op,
            reader_op,
            c0_op,
            c1_op,
            c4_op,
            DmaFillOp(root_op.results[0], c0_op.results[0]),
            subview,
            DmaFillOp(subview.result, c1_op.results[0]),
            DmaCopyOp(reader_op.results[0], root_op.results[0]),
        ]
    )
    assert _count_ops(module, DmaFillOp) == 2
    assert _count_ops(module, DmaSubviewOp) == 1

def test_dma_fill_canonicalization_removes_zero_fill_before_static_trip_dynamic_acc_matmul() -> None:
    """验证静态正 trip count 下 dynamic acc matmul 可删除 acc zero fill。

    功能说明:
    - 覆盖 `start/end/step` 全静态且 `end > start`、`step > 0` 的正例。
    - 通过公开 `CanonicalizePass` 删除 loop 前 `dma.fill`，不依赖 `kernel-decompose`。

    使用示例:
    - pytest -q test/dialect/dma/test_canonicalization.py -k static_trip_dynamic_acc_matmul
    """

    out_type = _make_memory_type(shape=_dim_array([2, 4]), stride=_dim_array([4, 1]), space="tsm")
    lhs_type = _make_memory_type(shape=_dim_array([2, 8]), stride=_dim_array([8, 1]), space="tsm")
    rhs_type = _make_memory_type(shape=_dim_array([8, 4]), stride=_dim_array([4, 1]), space="tsm")
    out_op = _TestOp(result_types=[out_type])
    lhs_op = _TestOp(result_types=[lhs_type])
    rhs_op = _TestOp(result_types=[rhs_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c8_op = _make_symbol_value_op(8)
    static_body = Block(arg_types=[SymbolIterType.from_bounds("0", "8", "1")])
    static_acc = SymbolNeOp(static_body.args[0], c0_op.results[0])
    static_matmul = KernelMatmulOp(out_op.results[0], lhs_op.results[0], rhs_op.results[0], _make_space("tsm"), acc=static_acc.result)
    static_body.add_ops([static_acc, static_matmul])
    static_loop = SymbolForOp(c0_op.results[0], c8_op.results[0], c1_op.results[0], static_body)
    static_module = _canonicalized_module(
        [
            out_op,
            lhs_op,
            rhs_op,
            c0_op,
            c1_op,
            c8_op,
            DmaFillOp(out_op.results[0], c0_op.results[0]),
            static_loop,
        ]
    )
    assert _count_ops(static_module, DmaFillOp) == 0

def test_dma_fill_canonicalization_removes_zero_fill_with_positive_symbol_step() -> None:
    """验证 DU1-A positive runtime tile step 下删除 acc zero fill。

    功能说明:
    - 覆盖 `start/end` 静态正区间、`step = TILE_K` 的 runtime tile 参数场景。
    - 通过公开 `CanonicalizePass` 删除 loop 前 `dma.fill`，不假设 dynamic end 为正。

    使用示例:
    - pytest -q test/dialect/dma/test_canonicalization.py -k positive_symbol_step
    """

    out_type = _make_memory_type(shape=_dim_array([2, 4]), stride=_dim_array([4, 1]), space="tsm")
    lhs_type = _make_memory_type(shape=_dim_array([2, 8]), stride=_dim_array([8, 1]), space="tsm")
    rhs_type = _make_memory_type(shape=_dim_array([8, 4]), stride=_dim_array([4, 1]), space="tsm")
    out_op = _TestOp(result_types=[out_type])
    lhs_op = _TestOp(result_types=[lhs_type])
    rhs_op = _TestOp(result_types=[rhs_type])
    c0_op = _make_symbol_value_op(0)
    c8_op = _make_symbol_value_op(8)
    tile_k_op = _make_symbol_value_op("TILE_K")
    symbol_step_body = Block(arg_types=[SymbolIterType.from_bounds("0", "8", "TILE_K")])
    symbol_step_acc = SymbolNeOp(symbol_step_body.args[0], c0_op.results[0])
    symbol_step_matmul = KernelMatmulOp(
        out_op.results[0],
        lhs_op.results[0],
        rhs_op.results[0],
        _make_space("tsm"),
        acc=symbol_step_acc.result,
    )
    symbol_step_body.add_ops([symbol_step_acc, symbol_step_matmul])
    symbol_step_loop = SymbolForOp(c0_op.results[0], c8_op.results[0], tile_k_op.results[0], symbol_step_body)
    symbol_step_module = _canonicalized_module(
        [
            out_op,
            lhs_op,
            rhs_op,
            c0_op,
            c8_op,
            tile_k_op,
            DmaFillOp(out_op.results[0], c0_op.results[0]),
            symbol_step_loop,
        ]
    )
    assert _count_ops(symbol_step_module, DmaFillOp) == 0

def test_dma_fill_canonicalization_keeps_dynamic_acc_matmul_boundaries() -> None:
    """验证 dynamic acc matmul dead-fill 的保守反例边界。

    功能说明:
    - `kernel.matmul_fusion`、非零 fill、非 canonical acc、dynamic end 与 loop 前 target read 均保留 fill。
    - 这些反例锁定 canonicalization 不回退到 fusion 语义或 dynamic shape 正数假设。

    使用示例:
    - pytest -q test/dialect/dma/test_canonicalization.py -k dynamic_acc_matmul_boundaries
    """

    out_type = _make_memory_type(shape=_dim_array([2, 4]), stride=_dim_array([4, 1]), space="tsm")
    lhs_type = _make_memory_type(shape=_dim_array([2, 8]), stride=_dim_array([8, 1]), space="tsm")
    rhs_type = _make_memory_type(shape=_dim_array([8, 4]), stride=_dim_array([4, 1]), space="tsm")

    out_op = _TestOp(result_types=[out_type])
    lhs_op = _TestOp(result_types=[lhs_type])
    rhs_op = _TestOp(result_types=[rhs_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c8_op = _make_symbol_value_op(8)
    fusion_body = Block(arg_types=[SymbolIterType.from_bounds("0", "8", "1")])
    fusion_acc = SymbolNeOp(fusion_body.args[0], c0_op.results[0])
    fusion = KernelMatmulFusionOp(
        out_op.results[0],
        lhs_op.results[0],
        rhs_op.results[0],
        fusion_acc.result,
        space=_make_space("tsm"),
        fusion_list="kernel.matmul,kernel.binary_elewise.add",
    )
    fusion_body.add_ops([fusion_acc, fusion])
    fusion_loop = SymbolForOp(c0_op.results[0], c8_op.results[0], c1_op.results[0], fusion_body)
    fusion_module = _canonicalized_module(
        [out_op, lhs_op, rhs_op, c0_op, c1_op, c8_op, DmaFillOp(out_op.results[0], c0_op.results[0]), fusion_loop]
    )
    assert _count_ops(fusion_module, DmaFillOp) == 1

    out_op = _TestOp(result_types=[out_type])
    lhs_op = _TestOp(result_types=[lhs_type])
    rhs_op = _TestOp(result_types=[rhs_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c8_op = _make_symbol_value_op(8)
    nonzero_body = Block(arg_types=[SymbolIterType.from_bounds("0", "8", "1")])
    nonzero_acc = SymbolNeOp(nonzero_body.args[0], c0_op.results[0])
    nonzero_matmul = KernelMatmulOp(out_op.results[0], lhs_op.results[0], rhs_op.results[0], _make_space("tsm"), acc=nonzero_acc.result)
    nonzero_body.add_ops([nonzero_acc, nonzero_matmul])
    nonzero_loop = SymbolForOp(c0_op.results[0], c8_op.results[0], c1_op.results[0], nonzero_body)
    nonzero_module = _canonicalized_module(
        [out_op, lhs_op, rhs_op, c0_op, c1_op, c8_op, DmaFillOp(out_op.results[0], c1_op.results[0]), nonzero_loop]
    )
    assert _count_ops(nonzero_module, DmaFillOp) == 1

    out_op = _TestOp(result_types=[out_type])
    lhs_op = _TestOp(result_types=[lhs_type])
    rhs_op = _TestOp(result_types=[rhs_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c8_op = _make_symbol_value_op(8)
    dynamic_end_op = _make_symbol_value_op("K")
    dynamic_end_body = Block(arg_types=[SymbolIterType.from_bounds("0", "K", "1")])
    dynamic_end_acc = SymbolNeOp(dynamic_end_body.args[0], c0_op.results[0])
    dynamic_end_matmul = KernelMatmulOp(
        out_op.results[0],
        lhs_op.results[0],
        rhs_op.results[0],
        _make_space("tsm"),
        acc=dynamic_end_acc.result,
    )
    dynamic_end_body.add_ops([dynamic_end_acc, dynamic_end_matmul])
    dynamic_end_loop = SymbolForOp(c0_op.results[0], dynamic_end_op.results[0], c1_op.results[0], dynamic_end_body)
    dynamic_end_module = _canonicalized_module(
        [
            out_op,
            lhs_op,
            rhs_op,
            c0_op,
            c1_op,
            c8_op,
            dynamic_end_op,
            DmaFillOp(out_op.results[0], c0_op.results[0]),
            dynamic_end_loop,
        ]
    )
    assert _count_ops(dynamic_end_module, DmaFillOp) == 1

    out_op = _TestOp(result_types=[out_type])
    lhs_op = _TestOp(result_types=[lhs_type])
    rhs_op = _TestOp(result_types=[rhs_type])
    other_op = _TestOp(result_types=[out_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c8_op = _make_symbol_value_op(8)
    read_body = Block(arg_types=[SymbolIterType.from_bounds("0", "8", "1")])
    read_acc = SymbolNeOp(read_body.args[0], c0_op.results[0])
    read_matmul = KernelMatmulOp(out_op.results[0], lhs_op.results[0], rhs_op.results[0], _make_space("tsm"), acc=read_acc.result)
    read_body.add_ops([read_acc, read_matmul])
    read_loop = SymbolForOp(c0_op.results[0], c8_op.results[0], c1_op.results[0], read_body)
    read_before_loop_module = _canonicalized_module(
        [
            out_op,
            lhs_op,
            rhs_op,
            other_op,
            c0_op,
            c1_op,
            c8_op,
            DmaFillOp(out_op.results[0], c0_op.results[0]),
            DmaCopyOp(other_op.results[0], out_op.results[0]),
            read_loop,
        ]
    )
    assert _count_ops(read_before_loop_module, DmaFillOp) == 1

    out_op = _TestOp(result_types=[out_type])
    lhs_op = _TestOp(result_types=[lhs_type])
    rhs_op = _TestOp(result_types=[rhs_type])
    other_op = _TestOp(result_types=[out_type])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c8_op = _make_symbol_value_op(8)
    body_read_body = Block(arg_types=[SymbolIterType.from_bounds("0", "8", "1")])
    body_read_acc = SymbolNeOp(body_read_body.args[0], c0_op.results[0])
    body_read_matmul = KernelMatmulOp(
        out_op.results[0],
        lhs_op.results[0],
        rhs_op.results[0],
        _make_space("tsm"),
        acc=body_read_acc.result,
    )
    body_read_body.add_ops([DmaCopyOp(other_op.results[0], out_op.results[0]), body_read_acc, body_read_matmul])
    body_read_loop = SymbolForOp(c0_op.results[0], c8_op.results[0], c1_op.results[0], body_read_body)
    body_read_module = _canonicalized_module(
        [out_op, lhs_op, rhs_op, other_op, c0_op, c1_op, c8_op, DmaFillOp(out_op.results[0], c0_op.results[0]), body_read_loop]
    )
    assert _count_ops(body_read_module, DmaFillOp) == 1

def test_dma_fill_canonicalization_removes_fill_for_if_full_deslice_before_alias_read() -> None:
    """验证 local alloc safe-if 中 full deslice 支配 alias read 时删除 fill。

    功能说明:
    - fill target 由本地 `dma.alloc` 产生。
    - then 分支先 full `dma.deslice` 覆盖 target，再读取 reshape alias；else 为空。
    - if 后继续扫描到 block 结束，没有读取旧 fill 值。

    使用示例:
    - pytest -q test/dialect/dma/test_canonicalization.py -k if_full_deslice
    """

    memory_type = _make_memory_type()
    alloc = DmaAllocOp([], memory_type)
    source_op = _TestOp(result_types=[memory_type])
    other_op = _TestOp(result_types=[memory_type])
    cond_op = _TestOp(result_types=[i1])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c2_op = _make_symbol_value_op(2)
    c4_op = _make_symbol_value_op(4)
    alias = DmaReshapeOp(alloc.result, [c2_op.results[0], c4_op.results[0]], memory_type)
    if_op = scf.IfOp(
        cond_op.results[0],
        [],
        [
            DmaDesliceOp(
                alloc.result,
                source_op.results[0],
                [c0_op.results[0], c0_op.results[0]],
                [c2_op.results[0], c4_op.results[0]],
                [c1_op.results[0], c1_op.results[0]],
            ),
            DmaCopyOp(other_op.results[0], alias.result),
            scf.YieldOp(),
        ],
        None,
    )
    module = _canonicalized_module(
        [
            alloc,
            source_op,
            other_op,
            cond_op,
            c0_op,
            c1_op,
            c2_op,
            c4_op,
            DmaFillOp(alloc.result, c0_op.results[0]),
            alias,
            if_op,
        ]
    )
    assert _count_ops(module, DmaFillOp) == 0

def test_dma_fill_canonicalization_keeps_unsafe_if_dead_fill_boundaries() -> None:
    """验证 safe-if dead-fill 的反例边界。

    功能说明:
    - else 分支未覆盖即读取 alias、partial deslice、nested region、函数参数 target 均保留 fill。
    - 这些反例锁定该规则不扩展为通用 CFG DSE。

    使用示例:
    - pytest -q test/dialect/dma/test_canonicalization.py -k unsafe_if_dead_fill
    """

    memory_type = _make_memory_type()
    alloc = DmaAllocOp([], memory_type)
    source_op = _TestOp(result_types=[memory_type])
    other_op = _TestOp(result_types=[memory_type])
    cond_op = _TestOp(result_types=[i1])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c2_op = _make_symbol_value_op(2)
    c4_op = _make_symbol_value_op(4)
    alias = DmaReshapeOp(alloc.result, [c2_op.results[0], c4_op.results[0]], memory_type)
    else_read_if = scf.IfOp(
        cond_op.results[0],
        [],
        [
            DmaDesliceOp(
                alloc.result,
                source_op.results[0],
                [c0_op.results[0], c0_op.results[0]],
                [c2_op.results[0], c4_op.results[0]],
                [c1_op.results[0], c1_op.results[0]],
            ),
            scf.YieldOp(),
        ],
        [DmaCopyOp(other_op.results[0], alias.result), scf.YieldOp()],
    )
    else_read_module = _canonicalized_module(
        [
            alloc,
            source_op,
            other_op,
            cond_op,
            c0_op,
            c1_op,
            c2_op,
            c4_op,
            DmaFillOp(alloc.result, c0_op.results[0]),
            alias,
            else_read_if,
        ]
    )
    assert _count_ops(else_read_module, DmaFillOp) == 1

    alloc = DmaAllocOp([], memory_type)
    source_op = _TestOp(result_types=[_make_memory_type(shape=_dim_array([1, 4]), stride=_dim_array([4, 1]))])
    cond_op = _TestOp(result_types=[i1])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c2_op = _make_symbol_value_op(2)
    c4_op = _make_symbol_value_op(4)
    partial_if = scf.IfOp(
        cond_op.results[0],
        [],
        [
            DmaDesliceOp(
                alloc.result,
                source_op.results[0],
                [c0_op.results[0], c0_op.results[0]],
                [c1_op.results[0], c4_op.results[0]],
                [c1_op.results[0], c1_op.results[0]],
            ),
            scf.YieldOp(),
        ],
        None,
    )
    partial_module = _canonicalized_module(
        [alloc, source_op, cond_op, c0_op, c1_op, c2_op, c4_op, DmaFillOp(alloc.result, c0_op.results[0]), partial_if]
    )
    assert _count_ops(partial_module, DmaFillOp) == 1

    alloc = DmaAllocOp([], memory_type)
    cond_op = _TestOp(result_types=[i1])
    c0_op = _make_symbol_value_op(0)
    nested_if = scf.IfOp(cond_op.results[0], [], [_make_region_side_effect_op(), scf.YieldOp()], None)
    nested_module = _canonicalized_module([alloc, cond_op, c0_op, DmaFillOp(alloc.result, c0_op.results[0]), nested_if])
    assert _count_ops(nested_module, DmaFillOp) == 1

    target_op = _TestOp(result_types=[memory_type])
    source_op = _TestOp(result_types=[memory_type])
    cond_op = _TestOp(result_types=[i1])
    c0_op = _make_symbol_value_op(0)
    c1_op = _make_symbol_value_op(1)
    c2_op = _make_symbol_value_op(2)
    c4_op = _make_symbol_value_op(4)
    function_arg_if = scf.IfOp(
        cond_op.results[0],
        [],
        [
            DmaDesliceOp(
                target_op.results[0],
                source_op.results[0],
                [c0_op.results[0], c0_op.results[0]],
                [c2_op.results[0], c4_op.results[0]],
                [c1_op.results[0], c1_op.results[0]],
            ),
            scf.YieldOp(),
        ],
        None,
    )
    function_arg_module = _canonicalized_module(
        [
            target_op,
            source_op,
            cond_op,
            c0_op,
            c1_op,
            c2_op,
            c4_op,
            DmaFillOp(target_op.results[0], c0_op.results[0]),
            function_arg_if,
        ]
    )
    assert _count_ops(function_arg_module, DmaFillOp) == 1

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
