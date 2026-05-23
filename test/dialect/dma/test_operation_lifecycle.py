"""dma dialect operation lifecycle tests.
功能说明:
- 验证 `kernel_gen.dialect.dma` package root 公开 API 的对应行为。

使用示例:
- `pytest -q test/dialect/dma/test_operation_lifecycle.py`

关联文件:
- spec: spec/dialect/dma.md
- 功能实现: kernel_gen/dialect/dma/
- 测试文件: test/dialect/dma/test_operation_lifecycle.py
"""

from test.dialect.dma.helpers import *  # noqa: F401,F403

def test_dma_alloc_verify_success() -> None:
    result_type = _make_memory_type()
    op = DmaAllocOp(_make_symbol_operands([2, 4]), result_type)
    op.verify()

    assert _effect_kinds_by_value(op) == {(MemoryEffectKind.ALLOC, op.result)}

def test_dma_free_requires_nn_memory_type() -> None:
    memory_type = _make_memory_type()
    source = _TestOp(result_types=[memory_type]).results[0]
    op = DmaFreeOp(source)
    op.verify()
    assert _effect_kinds_by_value(op) == {(MemoryEffectKind.FREE, source)}

    bad_source = _TestOp(result_types=[i32]).results[0]
    op = DmaFreeOp(bad_source)
    with pytest.raises(VerifyException, match="nn.memory"):
        op.verify()

def test_dma_alloc_dynamic_symbol_int_shape_operands_valid() -> None:
    result_type = _make_memory_type(
        shape=_dim_array(["M", "N"]),
        stride=_dim_array(["N", 1]),
    )
    op = DmaAllocOp(_make_symbol_operands(["M", "N"]), result_type)
    op.verify()

    non_contiguous_result_type = _make_memory_type(
        shape=_dim_array(["M", "N"]),
        stride=_dim_array([1, "M"]),
    )
    op = DmaAllocOp(_make_symbol_operands(["M", "N"]), non_contiguous_result_type)
    op.verify()

    mixed_result_type = _make_memory_type(
        shape=_dim_array(["M", 4]),
        stride=_dim_array([4, 1]),
    )
    op = DmaAllocOp(_make_symbol_operands(["M"]), mixed_result_type)
    op.verify()

    unknown_mixed_result_type = _make_memory_type(
        shape=_dim_array(["?", 4]),
        stride=_dim_array([4, 1]),
    )
    op = DmaAllocOp(_make_symbol_operands(["?"]), unknown_mixed_result_type)
    op.verify()

def test_dma_alloc_unknown_placeholder_rejects_named_symbol_operands() -> None:
    result_type = _make_memory_type(
        shape=_dim_array(["?", "?"]),
        stride=_dim_array(["?", 1]),
    )
    op = DmaAllocOp(_make_symbol_operands(["cur_n", "cur_c"]), result_type)
    with pytest.raises(VerifyException, match="dynamic_shape must match result shape"):
        op.verify()

def test_dma_alloc_named_result_shape_rejects_unknown_symbol_operands() -> None:
    result_type = _make_memory_type(
        shape=_dim_array(["cur_n", "cur_c"]),
        stride=_dim_array(["cur_c", 1]),
    )
    unknown_operands = [
        _TestOp(result_types=[SymbolValueType.from_expr("?")]).results[0],
        _TestOp(result_types=[SymbolValueType.from_expr("?")]).results[0],
    ]
    op = DmaAllocOp(unknown_operands, result_type)
    with pytest.raises(VerifyException, match="dynamic_shape must match result shape"):
        op.verify()

def test_dma_fill_accepts_builtin_i32_scalar_operand() -> None:
    target = _TestOp(result_types=[_make_memory_type()]).results[0]
    value = _TestOp(result_types=[i32]).results[0]

    DmaFillOp(target, value).verify()

def test_dma_fill_accepts_builtin_float_scalar_operand() -> None:
    target_type = _make_memory_type(element_type=f32)
    target = _TestOp(result_types=[target_type]).results[0]
    value = _TestOp(result_types=[f32]).results[0]

    DmaFillOp(target, value).verify()

def test_dma_fill_accepts_symbol_int_scalar_operand() -> None:
    target = _TestOp(result_types=[_make_memory_type()]).results[0]
    value = _make_symbol_operands(["N"])[0]

    DmaFillOp(target, value).verify()

def test_dma_fill_rejects_bool_or_unsupported_scalar() -> None:
    bad_target_type = _make_memory_type(
        shape=_dim_array([2, 4]),
        stride=_dim_array([4, 1]),
        element_type=i1,
        space="global",
    )
    bad_target = _TestOp(result_types=[bad_target_type]).results[0]
    value = _TestOp(result_types=[i32]).results[0]

    with pytest.raises(VerifyException, match="dma.fill target element_type must be numeric and not bool"):
        DmaFillOp(bad_target, value).verify()

    target = _TestOp(result_types=[_make_memory_type()]).results[0]
    bool_value = _TestOp(result_types=[i1]).results[0]
    float_value = _TestOp(result_types=[f32]).results[0]

    with pytest.raises(VerifyException, match="value must be builtin integer, builtin float or !symbol.int"):
        DmaFillOp(target, bool_value).verify()
    with pytest.raises(VerifyException, match="dma.fill value type must match target element_type"):
        DmaFillOp(target, float_value).verify()
