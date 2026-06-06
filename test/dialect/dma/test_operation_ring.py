"""dma dialect operation ring tests.
功能说明:
- 验证 `kernel_gen.dialect.dma` package root 公开 API 的对应行为。

使用示例:
- `pytest -q test/dialect/dma/test_operation_ring.py`

关联文件:
- spec: spec/dialect/dma.md
- 功能实现: kernel_gen/dialect/dma/
- 测试文件: test/dialect/dma/test_operation_ring.py
"""

from test.dialect.dma.helpers import *  # noqa: F401,F403

def test_dma_ring_type_and_ops_verify_success() -> None:
    backing_type = _make_memory_type(shape=_dim_array([768]), stride=_dim_array([1]), space="tsm", element_type=i8)
    slot_type = _make_memory_type(shape=_dim_array([4, 8]), stride=_dim_array([8, 1]), space="tsm")
    ring_type = DmaRingType(slot_type)
    storage = _TestOp(result_types=[backing_type]).results[0]
    num, offset, shape_bytes = _make_symbol_operands([3, 256, 128])

    DmaMakeRingOp(storage, num, offset, shape_bytes, ring_type).verify()
    DmaCurrentRingOp(_TestOp(result_types=[ring_type]).results[0]).verify()
    DmaAdvanceRingOp(_TestOp(result_types=[ring_type]).results[0]).verify()

    ctx = _build_context()
    parsed = Parser(ctx, "!dma.ring<!nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>>").parse_attribute()
    assert isinstance(parsed, DmaRingType)
    parsed.verify()
    assert _print_ir(parsed) == "!dma.ring<!nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>>"
    with pytest.raises(Exception, match="dma.ring|Expected"):
        Parser(ctx, "!dma.ring<#symbol.expr<256>, !nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>>").parse_attribute()

def test_dma_make_ring_verifier_edges() -> None:
    backing_type = _make_memory_type(shape=_dim_array([16]), stride=_dim_array([1]), space="tsm", element_type=i8)
    slot_type = _make_memory_type(shape=_dim_array([2, 2]), stride=_dim_array([2, 1]), space="tsm")
    ring_type = DmaRingType(slot_type)
    storage = _TestOp(result_types=[backing_type]).results[0]
    num, offset, shape_bytes = _make_symbol_operands([2, 8, 8])
    DmaMakeRingOp(storage, num, offset, shape_bytes, ring_type).verify()

    with pytest.raises(KernelCodeError, match="count must be > 0") as count_error:
        DmaMakeRingOp(storage, _make_symbol_operands([0])[0], offset, shape_bytes, ring_type).verify()
    assert count_error.value.kind() == "verify"
    assert count_error.value.module() == "dialect"
    with pytest.raises(KernelCodeError, match="offset must be > 0"):
        DmaMakeRingOp(storage, num, _make_symbol_operands([0])[0], shape_bytes, ring_type).verify()
    with pytest.raises(KernelCodeError, match="shape_bytes must be > 0"):
        DmaMakeRingOp(storage, num, offset, _make_symbol_operands([0])[0], ring_type).verify()
    with pytest.raises(KernelCodeError, match="shape_bytes.*offset"):
        DmaMakeRingOp(storage, num, offset, _make_symbol_operands([9])[0], ring_type).verify()
    with pytest.raises(KernelCodeError, match="backing memory bytes"):
        DmaMakeRingOp(
            _TestOp(result_types=[_make_memory_type(shape=_dim_array([15]), stride=_dim_array([1]), space="tsm", element_type=i8)]).results[0],
            num,
            offset,
            shape_bytes,
            ring_type,
        ).verify()
    with pytest.raises(KernelCodeError, match="space"):
        other_space_slot_type = _make_memory_type(shape=_dim_array([2, 2]), stride=_dim_array([2, 1]), space="tlm1")
        DmaMakeRingOp(
            storage,
            num,
            offset,
            shape_bytes,
            DmaRingType(other_space_slot_type),
        ).verify()
    with pytest.raises(KernelCodeError, match="one-dimensional i8"):
        DmaMakeRingOp(
            _TestOp(result_types=[_make_memory_type(shape=_dim_array([16]), stride=_dim_array([1]), space="tsm")]).results[0],
            num,
            offset,
            shape_bytes,
            ring_type,
        ).verify()

def test_dma_ring_slot_result_type_must_match() -> None:
    slot_type = _make_memory_type(shape=_dim_array([4, 8]), stride=_dim_array([8, 1]), space="tsm")
    ring = _TestOp(result_types=[DmaRingType(slot_type)]).results[0]
    wrong_slot_type = _make_memory_type(shape=_dim_array([4, 4]), stride=_dim_array([4, 1]), space="tsm")

    with pytest.raises(KernelCodeError, match="result.*ring") as current_error:
        DmaCurrentRingOp(ring, wrong_slot_type).verify()
    assert current_error.value.kind() == "verify"
    assert current_error.value.module() == "dialect"
    with pytest.raises(KernelCodeError, match="result.*ring"):
        DmaAdvanceRingOp(ring, wrong_slot_type).verify()
    with pytest.raises(TypeError, match="dma.ring"):
        DmaCurrentRingOp(_TestOp(result_types=[i32]).results[0])
    with pytest.raises(TypeError, match="dma.ring"):
        DmaAdvanceRingOp(_TestOp(result_types=[i32]).results[0])

def test_dma_advance_ring_survives_public_dce() -> None:
    slot_type = _make_memory_type(shape=_dim_array([4, 8]), stride=_dim_array([8, 1]), space="tsm")
    ring_producer = _TestOp(result_types=[DmaRingType(slot_type)])
    advance = DmaAdvanceRingOp(ring_producer.results[0])
    module = ModuleOp([ring_producer, advance])
    pm = PassManager(name="dma-ring-dce")
    pm.add_pass(_NoopPass())

    pm.run(module)

    assert any(isinstance(op, DmaAdvanceRingOp) for op in module.walk())
