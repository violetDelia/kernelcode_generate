"""dma dialect type tests.
功能说明:
- 验证 `kernel_gen.dialect.dma` package root 公开 API 的对应行为。

使用示例:
- `pytest -q test/dialect/dma/test_type.py`

关联文件:
- spec: spec/dialect/dma.md
- 功能实现: kernel_gen/dialect/dma/
- 测试文件: test/dialect/dma/test_type.py
"""

from test.dialect.dma.helpers import *  # noqa: F401,F403

def test_dma_requires_nn_memory_type() -> None:
    source = _TestOp(result_types=[i32]).results[0]
    target = _TestOp(result_types=[_make_memory_type()]).results[0]
    op = DmaCopyOp(target, source)
    with pytest.raises((KernelCodeError, VerifyException), match="nn.memory"):
        op.verify()

def test_dma_nn_memory_type_verifier_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    memory_type = _make_memory_type()
    source = _TestOp(result_types=[memory_type]).results[0]
    target = _TestOp(result_types=[memory_type]).results[0]
    op = DmaCopyOp(target, source)

    monkeypatch.setattr(NnMemoryType, "verify", _raise_memory_verify_rank_mismatch)
    with pytest.raises(KernelCodeError, match="nn memory shape and stride rank must match"):
        op.verify()

def test_dma_dynamic_symbol_int_parse_print_round_trip() -> None:
    ctx = _build_context()
    c0 = _TestOp(result_types=[SymbolValueType.from_expr("2")])
    c1 = _TestOp(result_types=[SymbolValueType.from_expr("4")])
    c2 = _TestOp(result_types=[SymbolValueType.from_expr("0")])
    c3 = _TestOp(result_types=[SymbolValueType.from_expr("1")])

    alloc_type = _make_memory_type()
    view_type = _make_memory_type(
        shape=_dim_array([2, 4]),
        stride=_dim_array([4, 1]),
    )
    reshape_type = _make_memory_type(
        shape=_dim_array([4, 2]),
        stride=_dim_array([2, 1]),
    )
    load_type = _make_memory_type(space="shared")

    alloc = DmaAllocOp([c0.results[0], c1.results[0]], alloc_type)
    fill = DmaFillOp(alloc.result, c0.results[0])
    view = DmaViewOp(
        alloc.result,
        [c2.results[0], c2.results[0]],
        [c0.results[0], c1.results[0]],
        [c3.results[0], c3.results[0]],
        view_type,
    )
    load_target_op = _TestOp(result_types=[load_type])
    load_target = load_target_op.results[0]
    load = DmaLoadOp(
        load_target,
        alloc.result,
        [c2.results[0], c2.results[0]],
        [c0.results[0], c1.results[0]],
        [c3.results[0], c3.results[0]],
    )
    store = DmaStoreOp(
        alloc.result,
        load_target,
        [c2.results[0], c2.results[0]],
        [c0.results[0], c1.results[0]],
        [c3.results[0], c3.results[0]],
    )
    slice_op = DmaSliceOp(
        alloc.result,
        alloc.result,
        [c2.results[0], c2.results[0]],
        [c0.results[0], c1.results[0]],
        [c3.results[0], c3.results[0]],
    )
    deslice = DmaDesliceOp(
        alloc.result,
        load_target,
        [c2.results[0], c2.results[0]],
        [c0.results[0], c1.results[0]],
        [c3.results[0], c3.results[0]],
        alloc_type,
    )
    reshape = DmaReshapeOp(alloc.result, [c1.results[0], c0.results[0]], reshape_type)
    cast_target_op = _TestOp(
        result_types=[NnMemoryType(alloc_type.shape, alloc_type.stride, i1, alloc_type.space)]
    )
    cast_target = cast_target_op.results[0]
    cast = DmaCastOp(cast_target, alloc.result)

    module = ModuleOp(
        [c0, c1, c2, c3, alloc, fill, view, load_target_op, load, store, slice_op, deslice, reshape, cast_target_op, cast]
    )
    printed = _print_ir(module).rstrip()
    reparsed = Parser(ctx, printed).parse_module()
    reparsed.verify()
    assert _print_ir(reparsed).rstrip() == printed

def test_dma_public_verifier_boundary_matrix() -> None:
    DmaAllocOp(
        _make_symbol_operands(["?"]),
        _make_memory_type(
            shape=_dim_array(["?", 4]),
            stride=_dim_array([4, 1]),
        ),
    ).verify()

    with pytest.raises(KernelCodeError, match="dynamic_shape symbol must match result shape"):
        DmaAllocOp(
            _make_symbol_operands(["N"]),
            _make_memory_type(
                shape=_dim_array(["?", 4]),
                stride=_dim_array([4, 1]),
            ),
        ).verify()

    with pytest.raises(KernelCodeError, match="dynamic_shape length must match symbol rank"):
        DmaAllocOp(
            _make_symbol_operands(["N"]),
            _make_memory_type(
                shape=_dim_array(["N", "M"]),
                stride=_dim_array(["M", 1]),
            ),
        ).verify()

    with pytest.raises(KernelCodeError, match="dynamic_shape symbol must match result shape"):
        DmaAllocOp(
            _make_symbol_operands(["M"]),
            _make_memory_type(
                shape=_dim_array(["N", 4]),
                stride=_dim_array([4, 1]),
            ),
        ).verify()

    source_type = _make_memory_type(
        shape=_dim_array([2, 3, 4]),
        stride=_dim_array([12, 4, 1]),
    )
    target_type = _make_memory_type(
        shape=_dim_array([3, 4]),
        stride=_dim_array([4, 1]),
    )
    with pytest.raises(KernelCodeError, match="dma.broadcast source rank must be <= target rank"):
        DmaBroadcastOp(
            _TestOp(result_types=[target_type]).results[0],
            _TestOp(result_types=[source_type]).results[0],
        ).verify()

    target = _TestOp(result_types=[_make_memory_type()]).results[0]
    with pytest.raises(KernelCodeError, match="dma.broadcast element_type mismatch"):
        DmaBroadcastOp(
            target,
            _TestOp(
                result_types=[_make_memory_type(shape=_dim_array([2, 4]), element_type=i1)]
            ).results[0],
        ).verify()
    with pytest.raises(KernelCodeError, match="dma.broadcast space mismatch"):
        DmaBroadcastOp(
            target,
            _TestOp(
                result_types=[_make_memory_type(shape=_dim_array([2, 4]), space="shared")]
            ).results[0],
        ).verify()
    with pytest.raises(KernelCodeError, match="dma.broadcast symbol.int target must be integer element_type"):
        DmaBroadcastOp(
            _TestOp(result_types=[_make_memory_type(element_type=f32)]).results[0],
            _make_symbol_operands(["N"])[0],
        ).verify()

    transpose_source_type = _make_memory_type(
        shape=_dim_array([2, 3]),
        stride=_dim_array([3, 1]),
    )
    transpose_source = _TestOp(result_types=[transpose_source_type]).results[0]
    transpose_target = _TestOp(
        result_types=[
            _make_memory_type(
                shape=_dim_array([3, 2]),
                stride=_dim_array([2, 1]),
            )
        ]
    ).results[0]
    DmaTransposeOp(
        transpose_target,
        transpose_source,
        perm=ArrayAttr([IntegerAttr(1, IntegerType(64)), IntegerAttr(0, IntegerType(64))]),
    ).verify()
    for target_type_case, perm, message in [
        (
            _make_memory_type(shape=_dim_array([3]), stride=_dim_array([1])),
            [1, 0],
            "dma.transpose target rank mismatch",
        ),
        (
            _make_memory_type(shape=_dim_array([4, 2]), stride=_dim_array([2, 1])),
            [1, 0],
            "dma.transpose target shape mismatch",
        ),
        (
            _make_memory_type(shape=_dim_array([3, 2]), stride=_dim_array([3, 1])),
            [1, 0],
            "dma.transpose target stride mismatch",
        ),
        (
            _make_memory_type(shape=_dim_array([3, 2]), stride=_dim_array([2, 1])),
            [1],
            "dma.transpose perm must match source rank",
        ),
        (
            _make_memory_type(
                shape=_dim_array([3, 2]),
                stride=_dim_array([2, 1]),
                element_type=i1,
            ),
            [1, 0],
            "dma.transpose element_type mismatch",
        ),
        (
            _make_memory_type(
                shape=_dim_array([3, 2]),
                stride=_dim_array([2, 1]),
                space="shared",
            ),
            [1, 0],
            "dma.transpose space mismatch",
        ),
    ]:
        with pytest.raises(KernelCodeError, match=message):
            DmaTransposeOp(
                _TestOp(result_types=[target_type_case]).results[0],
                transpose_source,
                perm=perm,
            ).verify()
    with pytest.raises(KernelCodeError, match="dma.transpose perm must be a permutation"):
        DmaTransposeOp(
            transpose_target,
            transpose_source,
            perm=ArrayAttr([StringAttr("bad"), IntAttr(0)]),
        ).verify()

    load_source = _TestOp(result_types=[_make_memory_type()]).results[0]
    with pytest.raises(KernelCodeError, match="dma.load target rank must match source rank"):
        DmaLoadOp(
            _TestOp(result_types=[_make_memory_type(shape=_dim_array([8]), stride=_dim_array([1]))]).results[0],
            load_source,
            _make_symbol_operands([0, 0]),
            _make_symbol_operands([2, 4]),
            _make_symbol_operands([1, 1]),
        ).verify()
    with pytest.raises(KernelCodeError, match="sizes entries must be >= 1"):
        DmaLoadOp(
            _TestOp(result_types=[_make_memory_type()]).results[0],
            load_source,
            _make_symbol_operands([0, 0]),
            _make_symbol_operands([0, 4]),
            _make_symbol_operands([1, 1]),
        ).verify()
    with pytest.raises(KernelCodeError, match="dma.slice target rank must match source rank"):
        DmaSliceOp(
            _TestOp(result_types=[_make_memory_type(shape=_dim_array([8]), stride=_dim_array([1]))]).results[0],
            load_source,
            _make_symbol_operands([0, 0]),
            _make_symbol_operands([2, 4]),
            _make_symbol_operands([1, 1]),
        ).verify()

    with pytest.raises(TypeError, match="result_type must be nn.memory"):
        DmaViewOp(
            load_source,
            _make_symbol_operands([0, 0]),
            _make_symbol_operands([2, 4]),
            _make_symbol_operands([4, 1]),
            i32,
        )
    with pytest.raises(KernelCodeError, match="dma.view source/result rank mismatch"):
        DmaViewOp(
            load_source,
            _make_symbol_operands([0]),
            _make_symbol_operands([8]),
            _make_symbol_operands([1]),
            _make_memory_type(shape=_dim_array([8]), stride=_dim_array([1])),
        ).verify()

    byte_sizes = [
        (i1, 1),
        (i8, 1),
        (IntegerType(16), 2),
        (IntegerType(64), 8),
        (f16, 2),
        (f32, 4),
        (f64, 8),
    ]
    for element_type, element_size in byte_sizes:
        byte_source_type = _make_memory_type(
            shape=_dim_array([2 * element_size]),
            stride=_dim_array([1]),
            element_type=i8,
        )
        result_type = _make_memory_type(
            shape=_dim_array([2]),
            stride=_dim_array([1]),
            element_type=element_type,
        )
        DmaViewOp(
            _TestOp(result_types=[byte_source_type]).results[0],
            _make_symbol_operands([0]),
            _make_symbol_operands([2]),
            _make_symbol_operands([1]),
            result_type,
        ).verify()

    byte_source_type = _make_memory_type(
        shape=_dim_array([16]),
        stride=_dim_array([1]),
        element_type=i8,
    )
    with pytest.raises(KernelCodeError, match="dma.view element_type unsupported for byte pool"):
        DmaViewOp(
            _TestOp(result_types=[byte_source_type]).results[0],
            _make_symbol_operands([0]),
            _make_symbol_operands([2]),
            _make_symbol_operands([1]),
            _make_memory_type(shape=_dim_array([2]), stride=_dim_array([1]), element_type=IndexType()),
        ).verify()
    DmaViewOp(
        _TestOp(result_types=[byte_source_type]).results[0],
        _make_symbol_operands(["O"]),
        _make_symbol_operands([16]),
        _make_symbol_operands([1]),
        _make_memory_type(shape=_dim_array([16]), stride=_dim_array([1]), element_type=i8),
    ).verify()
