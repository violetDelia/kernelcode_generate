"""dma.reinterpret operation tests.

功能说明:
- 覆盖 `DmaReinterpretOp` 的公开构造、verifier、NoMemoryEffect 与错误边界。

使用示例:
- pytest -q test/dialect/dma/test_reinterpret.py

关联文件:
- spec: spec/dialect/dma.md
- 功能实现: kernel_gen/dialect/dma/operation/alias.py
- 测试文件: test/dialect/dma/test_reinterpret.py
"""

from test.dialect.dma.helpers import *  # noqa: F401,F403


def test_dma_reinterpret_typed_source_uses_element_offset_and_no_memory_effect() -> None:
    """验证 typed source 下 `dma.reinterpret` 的 element offset 合同。

    功能说明:
    - source/result dtype 与 space 一致时允许 alias。
    - result shape/stride operand 必须与 result type 精确匹配。
    - op 不产生 memory effect。

    使用示例:
    - pytest -q test/dialect/dma/test_reinterpret.py -k typed_source
    """

    source_type = _make_memory_type(shape=_dim_array([16]), stride=_dim_array([1]), element_type=i32)
    result_type = _make_memory_type(shape=_dim_array([2, 3]), stride=_dim_array([3, 1]), element_type=i32)
    source = _TestOp(result_types=[source_type]).results[0]
    offset, two, three, one = _make_symbol_operands([4, 2, 3, 1])

    op = DmaReinterpretOp(source, offset, [two, three], [three, one], result_type)

    op.verify()
    assert op.result.type == result_type
    assert get_effects(op) == set()


def test_dma_reinterpret_byte_pool_uses_byte_offset() -> None:
    """验证 i8 byte pool source 下 `dma.reinterpret` 的 byte offset 合同。

    功能说明:
    - byte pool 可切出不同 element_type 的 result。
    - bounds 按 byte offset 加 typed result footprint 检查。

    使用示例:
    - pytest -q test/dialect/dma/test_reinterpret.py -k byte_pool
    """

    pool_type = _make_memory_type(shape=_dim_array([64]), stride=_dim_array([1]), element_type=i8, space="shared")
    result_type = _make_memory_type(shape=_dim_array([2, 4]), stride=_dim_array([4, 1]), element_type=i32, space="shared")
    source = _TestOp(result_types=[pool_type]).results[0]
    offset, two, four, one = _make_symbol_operands([8, 2, 4, 1])

    op = DmaReinterpretOp(source, offset, [two, four], [four, one], result_type)

    op.verify()


def test_dma_reinterpret_rejects_public_contract_edges() -> None:
    """验证 `dma.reinterpret` 的公开 verifier 错误文本。

    功能说明:
    - 覆盖 space、element type、shape/stride layout、bounds 与 offset 类型错误。

    使用示例:
    - pytest -q test/dialect/dma/test_reinterpret.py -k rejects
    """

    source_type = _make_memory_type(shape=_dim_array([8]), stride=_dim_array([1]), element_type=i32)
    source = _TestOp(result_types=[source_type]).results[0]
    offset, two, four, one = _make_symbol_operands([0, 2, 4, 1])
    result_type = _make_memory_type(shape=_dim_array([2, 4]), stride=_dim_array([4, 1]), element_type=i32)

    with pytest.raises(VerifyException, match="element_type mismatch"):
        DmaReinterpretOp(
            source,
            offset,
            [two, four],
            [four, one],
            _make_memory_type(shape=_dim_array([2, 4]), stride=_dim_array([4, 1]), element_type=i1),
        ).verify()

    with pytest.raises(VerifyException, match="space mismatch"):
        DmaReinterpretOp(
            source,
            offset,
            [two, four],
            [four, one],
            _make_memory_type(shape=_dim_array([2, 4]), stride=_dim_array([4, 1]), space="shared"),
        ).verify()

    with pytest.raises(VerifyException, match="shape must match result shape"):
        DmaReinterpretOp(source, offset, [four, two], [four, one], result_type).verify()

    with pytest.raises(VerifyException, match="stride must match result stride"):
        DmaReinterpretOp(source, offset, [two, four], [one, one], result_type).verify()

    with pytest.raises(VerifyException, match="offset entries must be !symbol.int or !symbol.iter"):
        DmaReinterpretOp(source, _TestOp(result_types=[IndexType()]).results[0], [two, four], [four, one], result_type).verify()

    with pytest.raises(VerifyException, match="bounds mismatch"):
        DmaReinterpretOp(source, _make_symbol_operands([1])[0], [two, four], [four, one], result_type).verify()

    pool_type = _make_memory_type(shape=_dim_array([31]), stride=_dim_array([1]), element_type=i8, space="shared")
    pool = _TestOp(result_types=[pool_type]).results[0]
    with pytest.raises(VerifyException, match="byte bounds mismatch"):
        DmaReinterpretOp(
            pool,
            _make_symbol_operands([0])[0],
            [two, four],
            [four, one],
            _make_memory_type(shape=_dim_array([2, 4]), stride=_dim_array([4, 1]), element_type=i32, space="shared"),
        ).verify()
