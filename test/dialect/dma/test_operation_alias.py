"""dma dialect operation alias tests.
功能说明:
- 验证 `kernel_gen.dialect.dma` package root 公开 API 的对应行为。

使用示例:
- `pytest -q test/dialect/dma/test_operation_alias.py`

关联文件:
- spec: spec/dialect/dma.md
- 功能实现: kernel_gen/dialect/dma/
- 测试文件: test/dialect/dma/test_operation_alias.py
"""

from test.dialect.dma.helpers import *  # noqa: F401,F403

def test_dma_view_type_or_space_mismatch() -> None:
    source_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]
    offsets = _make_symbol_operands([0, 0])
    shape = _make_symbol_operands([2, 4])
    stride = _make_symbol_operands([1, 1])

    result_type = NnMemoryType(source_type.shape, source_type.stride, i1, source_type.space)
    op = DmaViewOp(source, offsets, shape, stride, result_type)
    with pytest.raises(VerifyException, match="element_type mismatch"):
        op.verify()

    result_type = _make_memory_type(space="shared")
    op = DmaViewOp(source, offsets, shape, stride, result_type)
    with pytest.raises(VerifyException, match="space mismatch"):
        op.verify()

def test_dma_alias_ops_have_no_memory_effect() -> None:
    memory_type = _make_memory_type()
    byte_pool_type = _make_memory_type(shape=_dim_array([64]), stride=_dim_array([1]), element_type=i8)
    source = _TestOp(result_types=[memory_type]).results[0]
    pool = _TestOp(result_types=[byte_pool_type]).results[0]
    zero, one, two, four = _make_symbol_operands([0, 1, 2, 4])

    view = DmaViewOp(source, [zero, zero], [two, four], [one, one], memory_type)
    reshape = DmaReshapeOp(source, [two, four], memory_type)
    subview = DmaSubviewOp(pool, zero, four, one, _make_memory_type(shape=_dim_array([4]), stride=_dim_array([1])))

    assert get_effects(view) == set()
    assert get_effects(reshape) == set()
    assert get_effects(subview) == set()

def test_dma_view_numel_mismatch() -> None:
    source_type = _make_memory_type(shape=_dim_array([2, 4]))
    source = _TestOp(result_types=[source_type]).results[0]
    result_type = _make_memory_type(
        shape=_dim_array([2, 5]),
        stride=_dim_array([4, 1]),
    )
    op = DmaViewOp(
        source,
        _make_symbol_operands([0, 0]),
        _make_symbol_operands([2, 5]),
        _make_symbol_operands([1, 1]),
        result_type,
    )
    with pytest.raises(VerifyException, match="numel mismatch"):
        op.verify()

def test_dma_reshape_requires_contiguous() -> None:
    source_type = _make_memory_type(
        shape=_dim_array([2, 4]),
        stride=_dim_array([5, 1]),
    )
    result_type = _make_memory_type(
        shape=_dim_array([4, 2]),
        stride=_dim_array([2, 1]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    op = DmaReshapeOp(source, _make_symbol_operands([4, 2]), result_type)
    with pytest.raises(VerifyException, match="contiguous source"):
        op.verify()

def test_dma_reshape_allows_dynamic_symbol_int_shape_operands() -> None:
    source_type = _make_memory_type(
        shape=_dim_array([2, 4]),
        stride=_dim_array([4, 1]),
    )
    result_type = _make_memory_type(
        shape=_dim_array(["M", "N"]),
        stride=_dim_array(["N", 1]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    op = DmaReshapeOp(source, _make_symbol_operands(["M", "N"]), result_type)
    op.verify()

    bad_result_type = _make_memory_type(
        shape=_dim_array(["M", "N"]),
        stride=_dim_array(["M", 1]),
    )
    op = DmaReshapeOp(source, _make_symbol_operands(["M", "N"]), bad_result_type)
    with pytest.raises(VerifyException, match="dma.reshape requires contiguous result stride"):
        op.verify()

def test_dma_reshape_rejects_named_result_from_unknown_shape_operands() -> None:
    source_type = _make_memory_type(
        shape=_dim_array(["TOTAL"]),
        stride=_dim_array([1]),
    )
    result_type = _make_memory_type(
        shape=_dim_array(["k_tile", "out_tile"]),
        stride=_dim_array(["out_tile", 1]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    shape_operands = [
        _TestOp(result_types=[SymbolValueType.from_expr("?")]).results[0],
        _TestOp(result_types=[SymbolValueType.from_expr("?")]).results[0],
    ]
    shape_operands[0].name_hint = "k_tile"
    shape_operands[1].name_hint = "out_tile"
    op = DmaReshapeOp(source, shape_operands, result_type)

    with pytest.raises(VerifyException, match="shape must match result shape"):
        op.verify()

def test_dma_reshape_accepts_equivalent_symbolic_contiguous_source_stride() -> None:
    source_type = _make_memory_type(
        shape=_dim_array(["TN", "TC", "KH", "KW", "THO", "TWO"]),
        stride=_dim_array(["KH*KW*TC*THO*TWO", "KH*KW*THO*TWO", "KW*THO*TWO", "THO*TWO", "TWO", 1]),
    )
    result_type = _make_memory_type(
        shape=_dim_array(["KH*KW*TC", "THO*TN*TWO"]),
        stride=_dim_array(["THO*TN*TWO", 1]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    op = DmaReshapeOp(source, _make_symbol_operands(["KH*KW*TC", "THO*TN*TWO"]), result_type)

    op.verify()

def test_dma_reshape_accepts_min_symbolic_contiguous_source_stride() -> None:
    source_type = _make_memory_type(
        shape=_dim_array(["min(1, 1-n0)", "min(3, 3-c0)", 3, 3, "min(4, 6-ho0)", "min(5, 6-wo0)"]),
        stride=_dim_array(
            [
                "9*min(3, 3-c0)*min(4, 6-ho0)*min(5, 6-wo0)",
                "9*min(4, 6-ho0)*min(5, 6-wo0)",
                "3*min(4, 6-ho0)*min(5, 6-wo0)",
                "min(4, 6-ho0)*min(5, 6-wo0)",
                "min(5, 6-wo0)",
                1,
            ]
        ),
    )
    result_type = _make_memory_type(
        shape=_dim_array(["9*min(3, 3-c0)", "min(1, 1-n0)*min(4, 6-ho0)*min(5, 6-wo0)"]),
        stride=_dim_array(["min(1, 1-n0)*min(4, 6-ho0)*min(5, 6-wo0)", 1]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    op = DmaReshapeOp(
        source,
        _make_symbol_operands(["9*min(3, 3-c0)", "min(1, 1-n0)*min(4, 6-ho0)*min(5, 6-wo0)"]),
        result_type,
    )

    op.verify()

def test_dma_reshape_numel_mismatch() -> None:
    source_type = _make_memory_type(
        shape=_dim_array([2, 4]),
        stride=_dim_array([4, 1]),
    )
    result_type = _make_memory_type(
        shape=_dim_array([3, 3]),
        stride=_dim_array([3, 1]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    op = DmaReshapeOp(source, _make_symbol_operands([3, 3]), result_type)
    with pytest.raises(VerifyException, match="numel mismatch"):
        op.verify()

def test_dma_view_dynamic_symbol_int_layout_operands_valid() -> None:
    source_type = _make_memory_type(
        shape=_dim_array(["M", "N"]),
        stride=_dim_array(["N", 1]),
    )
    result_type = _make_memory_type(
        shape=_dim_array(["TM", "TN"]),
        stride=_dim_array(["N", 1]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    op = DmaViewOp(
        source,
        _make_symbol_operands(["TO", "TI"]),
        _make_symbol_operands(["TM", "TN"]),
        _make_symbol_operands([1, 1]),
        result_type,
    )
    op.verify()

def test_dma_view_result_stride_uses_source_physical_stride() -> None:
    source_type = _make_memory_type(
        shape=_dim_array([2, 2]),
        stride=_dim_array([2, 1]),
    )
    result_type = _make_memory_type(
        shape=_dim_array([2, 2]),
        stride=_dim_array([2, 1]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    op = DmaViewOp(
        source,
        _make_symbol_operands([0, 0]),
        _make_symbol_operands([2, 2]),
        _make_symbol_operands([1, 1]),
        result_type,
    )
    op.verify()

    bad_stride_type = _make_memory_type(
        shape=_dim_array([2, 2]),
        stride=_dim_array([1, 1]),
    )
    bad_stride_op = DmaViewOp(
        source,
        _make_symbol_operands([0, 0]),
        _make_symbol_operands([2, 2]),
        _make_symbol_operands([1, 1]),
        bad_stride_type,
    )
    with pytest.raises(VerifyException, match="source physical stride"):
        bad_stride_op.verify()

def test_dma_view_byte_pool_typed_view() -> None:
    source_type = _make_memory_type(
        shape=_dim_array([32]),
        stride=_dim_array([1]),
        element_type=i8,
        space="global",
    )
    source = _TestOp(result_types=[source_type]).results[0]

    result_type_1d = _make_memory_type(
        shape=_dim_array([4]),
        stride=_dim_array([1]),
        element_type=i32,
        space="global",
    )
    op = DmaViewOp(
        source,
        _make_symbol_operands([2]),
        _make_symbol_operands([4]),
        _make_symbol_operands([1]),
        result_type_1d,
    )
    op.verify()

    result_type_2d = _make_memory_type(
        shape=_dim_array([2, 2]),
        stride=_dim_array([2, 1]),
        element_type=i32,
        space="global",
    )
    op = DmaViewOp(
        source,
        _make_symbol_operands([2, 0]),
        _make_symbol_operands([2, 2]),
        _make_symbol_operands([2, 1]),
        result_type_2d,
    )
    op.verify()

    out_of_bounds_type = _make_memory_type(
        shape=_dim_array([4]),
        stride=_dim_array([1]),
        element_type=i32,
        space="global",
    )
    op = DmaViewOp(
        source,
        _make_symbol_operands([6]),
        _make_symbol_operands([4]),
        _make_symbol_operands([1]),
        out_of_bounds_type,
    )
    with pytest.raises(VerifyException, match="byte bounds mismatch"):
        op.verify()

    bad_stride_type = _make_memory_type(
        shape=_dim_array([2, 2]),
        stride=_dim_array([3, 1]),
        element_type=i32,
        space="global",
    )
    op = DmaViewOp(
        source,
        _make_symbol_operands([6, 0]),
        _make_symbol_operands([2, 2]),
        _make_symbol_operands([3, 1]),
        bad_stride_type,
    )
    with pytest.raises(VerifyException, match="byte bounds mismatch"):
        op.verify()

def test_dma_subview_byte_pool_typed_result_valid() -> None:
    source_type = _make_memory_type(
        shape=_dim_array([64]),
        stride=_dim_array([1]),
        element_type=i8,
        space="shared",
    )
    source = _TestOp(result_types=[source_type]).results[0]
    result_type = _make_memory_type(
        shape=_dim_array([8]),
        stride=_dim_array([1]),
        element_type=i32,
        space="shared",
    )

    op = DmaSubviewOp(
        source,
        _make_symbol_operands([8])[0],
        _make_symbol_operands([8])[0],
        _make_symbol_operands([1])[0],
        result_type,
    )

    op.verify()
    assert op.result.type == result_type

def test_dma_subview_rejects_invalid_contract_edges() -> None:
    source_type = _make_memory_type(
        shape=_dim_array([16]),
        stride=_dim_array([1]),
        element_type=i8,
        space="shared",
    )
    source = _TestOp(result_types=[source_type]).results[0]
    result_type = _make_memory_type(
        shape=_dim_array([4]),
        stride=_dim_array([1]),
        element_type=i32,
        space="shared",
    )

    non_i8_source = _TestOp(
        result_types=[
            _make_memory_type(
                shape=_dim_array([16]),
                stride=_dim_array([1]),
                element_type=i32,
                space="shared",
            )
        ]
    ).results[0]
    with pytest.raises(VerifyException, match="source must be one-dimensional i8 memory"):
        DmaSubviewOp(
            non_i8_source,
            _make_symbol_operands([0])[0],
            _make_symbol_operands([4])[0],
            _make_symbol_operands([1])[0],
            result_type,
        ).verify()

    two_dim_result = _make_memory_type(
        shape=_dim_array([2, 2]),
        stride=_dim_array([2, 1]),
        element_type=i32,
        space="shared",
    )
    with pytest.raises(VerifyException, match="result must be one-dimensional"):
        DmaSubviewOp(
            source,
            _make_symbol_operands([0])[0],
            _make_symbol_operands([4])[0],
            _make_symbol_operands([1])[0],
            two_dim_result,
        ).verify()

    with pytest.raises(VerifyException, match="space mismatch"):
        DmaSubviewOp(
            source,
            _make_symbol_operands([0])[0],
            _make_symbol_operands([4])[0],
            _make_symbol_operands([1])[0],
            _make_memory_type(
                shape=_dim_array([4]),
                stride=_dim_array([1]),
                element_type=i32,
                space="local",
            ),
        ).verify()

    with pytest.raises(VerifyException, match="size must match result shape"):
        DmaSubviewOp(
            source,
            _make_symbol_operands([0])[0],
            _make_symbol_operands([3])[0],
            _make_symbol_operands([1])[0],
            result_type,
        ).verify()

    with pytest.raises(VerifyException, match="byte bounds mismatch"):
        DmaSubviewOp(
            source,
            _make_symbol_operands([1])[0],
            _make_symbol_operands([4])[0],
            _make_symbol_operands([1])[0],
            result_type,
        ).verify()

def test_dma_view_rejects_invalid_offsets_or_bounds() -> None:
    source_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]
    result_type = _make_memory_type(
        shape=_dim_array([2, 4]),
        stride=_dim_array([4, 1]),
    )

    with pytest.raises(VerifyException, match="offsets length must match rank"):
        DmaViewOp(
            source,
            [],
            _make_symbol_operands([2, 4]),
            _make_symbol_operands([1, 1]),
            result_type,
        ).verify()

    with pytest.raises(TypeError, match="missing 1 required positional argument"):
        DmaViewOp(
            source,
            _make_symbol_operands([0]),
            _make_symbol_operands([2, 4]),
            _make_symbol_operands([1, 1]),
        )

    with pytest.raises(VerifyException, match="offsets entries must be >= 0"):
        DmaViewOp(
            source,
            _make_symbol_operands([-1, 0]),
            _make_symbol_operands([2, 4]),
            _make_symbol_operands([1, 1]),
            result_type,
        ).verify()

    with pytest.raises(VerifyException, match="dma.view bounds mismatch"):
        DmaViewOp(
            source,
            _make_symbol_operands([1, 0]),
            _make_symbol_operands([2, 4]),
            _make_symbol_operands([1, 1]),
            result_type,
        ).verify()

def test_dma_rejects_non_symbol_int_scalar_operands() -> None:
    source_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[source_type]).results[0]
    index_operand = _TestOp(result_types=[IndexType()]).results[0]
    symbol_sizes = _make_symbol_operands([2, 4])
    symbol_strides = _make_symbol_operands([1, 1])

    with pytest.raises(VerifyException, match="offsets entries must be !symbol.int or !symbol.iter"):
        DmaLoadOp(
            target,
            source,
            [index_operand, index_operand],
            symbol_sizes,
            symbol_strides,
        ).verify()

    with pytest.raises(VerifyException, match="base attribute symbol.int"):
        DmaAllocOp([index_operand, index_operand], source_type).verify()

    with pytest.raises(VerifyException, match="offsets entries must be !symbol.int or !symbol.iter"):
        DmaViewOp(
            source,
            [index_operand, index_operand],
            _make_symbol_operands([2, 4]),
            _make_symbol_operands([4, 1]),
            source_type,
        ).verify()

    with pytest.raises(VerifyException, match="base attribute symbol.int"):
        DmaReshapeOp(
            target,
            [index_operand, index_operand],
            source_type,
        ).verify()

    with pytest.raises(VerifyException, match="value must be builtin integer, builtin float or !symbol.int"):
        DmaFillOp(target, index_operand).verify()

def test_dma_reshape_rejects_element_or_space_mismatch() -> None:
    source_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]
    shape = _make_symbol_operands([4, 2])

    bad_element_type = _make_memory_type(
        shape=_dim_array([4, 2]),
        stride=_dim_array([2, 1]),
        element_type=i1,
        space="global",
    )
    op = DmaReshapeOp(source, shape, bad_element_type)
    with pytest.raises(VerifyException, match="dma.reshape element_type mismatch"):
        op.verify()

    bad_space_type = _make_memory_type(
        shape=_dim_array([4, 2]),
        stride=_dim_array([2, 1]),
        space="shared",
    )
    op = DmaReshapeOp(source, shape, bad_space_type)
    with pytest.raises(VerifyException, match="dma.reshape space mismatch"):
        op.verify()
