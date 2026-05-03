"""DSL AST DMA plugin tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast.plugin.dma` 注册后的 DMA helper 解析行为。
- 测试结构对应 `spec/dsl/ast/plugin/dma.md` 与 `kernel_gen/dsl/ast/plugin/dma.py`。

使用示例:
- pytest -q test/dsl/ast/plugin/test_dma.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/plugin/dma.py
- Spec 文档: spec/dsl/ast/plugin/dma.md
- 测试文件: test/dsl/ast/plugin/test_dma.py
"""

from __future__ import annotations

import random

import pytest

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dsl.ast import (
    BoundExprAST,
    DmaAllocAST,
    DmaCastAST,
    DmaCopyAST,
    DmaDesliceAST,
    DmaFillAST,
    DmaFlattenAST,
    DmaFreeAST,
    DmaLoadAST,
    DmaReshapeAST,
    DmaSliceAST,
    DmaStoreAST,
    DmaViewAST,
    ReturnAST,
    SymbolListAST,
    parse_function,
)
from kernel_gen.operation.dma import alloc, cast, copy, deslice, fill, flatten, free, load, reshape, slice, store, view
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.type import NumericType


def _dma_alloc_kernel(x):
    return alloc([6, 4], NumericType.Float32, space=MemorySpace.SM, stride=[4, 1])


def _dma_copy_kernel(x):
    return copy(x, MemorySpace.LM)


def _dma_cast_kernel(x):
    return cast(x, NumericType.Float16, memoryspace=MemorySpace.TSM)


def _dma_view_kernel(x):
    return view(x, [1, 0], [2, 3], [3, 1])


def _dma_reshape_kernel(x):
    return reshape(x, [2, 12])


def _dma_flatten_kernel(x):
    return flatten(x)


def _dma_free_kernel(dst, src):
    free(dst)


def _dma_load_with_space_kernel(x):
    return load(x, [0, 1], [2, 3], [3, 1], MemorySpace.SM)


def _dma_slice_with_space_kernel(x):
    return slice(x, [1, 0], [2, 3], [3, 1], MemorySpace.LM)


def _dma_store_parameterized_kernel(dst, src):
    store(dst, src, [0, 1], [2, 3], [3, 1])


def _dma_deslice_parameterized_kernel(dst, src):
    deslice(dst, src, [1, 0], [2, 3], [3, 1])


def _dma_bad_alloc_dtype_kernel(x):
    return alloc([4], "float32")


def _dma_bad_alloc_arity_kernel(x):
    return alloc([4])


def _dma_bad_alloc_space_kernel(x):
    return alloc([4], NumericType.Float32, "SM")


def _dma_bad_cast_arity_kernel(x):
    return cast(x)


def _dma_bad_cast_dtype_kernel(x):
    return cast(x, "float16")


def _dma_bad_cast_space_kernel(x):
    return cast(x, NumericType.Float16, memoryspace="SM")


def _dma_bad_cast_duplicate_space_kernel(x):
    return cast(x, NumericType.Float16, MemorySpace.SM, memoryspace=MemorySpace.LM)


def _dma_bad_copy_space_kernel(x):
    return copy(x, "sm")


def _dma_bad_copy_arity_kernel(x):
    return copy()


def _dma_bad_fill_arity_kernel(x):
    fill(x)


def _dma_bad_fill_string_kernel(x):
    fill(x, "zero")


def _dma_bad_load_source_kernel(x):
    return load(1, [0], [1], [1])


def _dma_bad_load_arity_kernel(x):
    return load(x, [0])


def _dma_bad_load_space_kernel(x):
    return load(x, [0], [1], [1], "SM")


def _dma_bad_slice_arity_kernel(x):
    return slice(x, [0])


def _dma_bad_slice_source_kernel(x):
    return slice(1, [0], [1], [1])


def _dma_bad_slice_space_kernel(x):
    return slice(x, [0], [1], [1], "SM")


def _dma_bad_store_arity_kernel(x):
    return store(x, x, [0])


def _dma_bad_store_target_kernel(x):
    store(1, x, [0], [1])


def _dma_bad_store_space_kernel(x):
    store(x, x, [0], [1], [1], "SM")


def _dma_bad_deslice_arity_kernel(x):
    return deslice(x, x, [0])


def _dma_bad_deslice_target_kernel(x):
    deslice(1, x, [0], [1])


def _dma_bad_deslice_space_kernel(x):
    deslice(x, x, [0], [1], [1], "SM")


_DMA_INVALID_CASES = tuple(
    random.Random(20260505).sample(
        [
            (_dma_bad_alloc_dtype_kernel, "alloc dtype must be NumericType"),
            (_dma_bad_alloc_arity_kernel, "Unsupported alloc arity"),
            (_dma_bad_alloc_space_kernel, "alloc space must be MemorySpace"),
            (_dma_bad_cast_arity_kernel, "Unsupported cast arity"),
            (_dma_bad_cast_dtype_kernel, "cast dtype must be NumericType"),
            (_dma_bad_cast_space_kernel, "cast memoryspace must be MemorySpace"),
            (_dma_bad_cast_duplicate_space_kernel, "Unsupported cast arity"),
            (_dma_bad_copy_space_kernel, "copy space must be MemorySpace"),
            (_dma_bad_copy_arity_kernel, "Unsupported copy arity"),
            (_dma_bad_fill_arity_kernel, "Unsupported fill arity"),
            (_dma_bad_fill_string_kernel, 'fill string literal must be "inf" or "-inf"'),
            (_dma_bad_load_source_kernel, "load source must be MemoryAST"),
            (_dma_bad_load_arity_kernel, "Unsupported load arity"),
            (_dma_bad_load_space_kernel, "load space must be MemorySpace"),
            (_dma_bad_slice_arity_kernel, "Unsupported slice arity"),
            (_dma_bad_slice_source_kernel, "slice source must be MemoryAST"),
            (_dma_bad_slice_space_kernel, "slice space must be MemorySpace"),
            (_dma_bad_store_arity_kernel, "Unsupported store arity"),
            (_dma_bad_store_target_kernel, "store target must be MemoryAST"),
            (_dma_bad_store_space_kernel, "store space must be MemorySpace"),
            (_dma_bad_deslice_arity_kernel, "Unsupported deslice arity"),
            (_dma_bad_deslice_target_kernel, "deslice target must be MemoryAST"),
            (_dma_bad_deslice_space_kernel, "deslice space must be MemorySpace"),
        ],
        23,
    )
)


_DMA_RETURN_CASES = tuple(
    random.Random(20260503).sample(
        [
            (_dma_alloc_kernel, DmaAllocAST),
            (_dma_copy_kernel, DmaCopyAST),
            (_dma_cast_kernel, DmaCastAST),
            (_dma_view_kernel, DmaViewAST),
            (_dma_reshape_kernel, DmaReshapeAST),
            (_dma_flatten_kernel, DmaFlattenAST),
            (_dma_load_with_space_kernel, DmaLoadAST),
            (_dma_slice_with_space_kernel, DmaSliceAST),
        ],
        8,
    )
)


def _return_values(kernel, *runtime_args):
    """通过公开 parse_function 读取返回节点值。"""

    func_ast = parse_function(kernel, *runtime_args)
    return_nodes = [node for node in func_ast.body.statements if isinstance(node, ReturnAST)]
    assert len(return_nodes) == 1
    return return_nodes[0].values


def test_dma_fill_parses_to_specific_node() -> None:
    """`fill(...)` 解析为 `DmaFillAST`，不再通过中间 StoreAST 表达。"""

    memory = Memory([4], NumericType.Float32)

    def kernel(x):
        fill(x, "-inf")

    func_ast = parse_function(kernel, memory)

    fill_nodes = [node for node in func_ast.body.statements if isinstance(node, DmaFillAST)]
    assert len(fill_nodes) == 1
    assert fill_nodes[0].target == func_ast.inputs[0]


def test_dma_load_slice_parse_to_specific_nodes() -> None:
    """source-first `load` / `slice` helper 解析为具体读取节点。"""

    memory = Memory([8], NumericType.Float32)

    def kernel(x):
        a = load(x, [0], [4], [1])
        b = slice(x, [4], [4], [1])
        return b

    func_ast = parse_function(kernel, memory)
    bound_values = [node.value for node in func_ast.body.statements if isinstance(node, BoundExprAST)]

    assert any(isinstance(node, DmaLoadAST) for node in bound_values)
    assert any(isinstance(node, DmaSliceAST) for node in bound_values)
    assert all(isinstance(node.size, SymbolListAST) for node in bound_values if isinstance(node, (DmaLoadAST, DmaSliceAST)))


def test_dma_store_deslice_parse_to_specific_nodes() -> None:
    """target-first `store` / `deslice` helper 解析为具体写回节点。"""

    target = Memory([8], NumericType.Float32)
    source = Memory([4], NumericType.Float32)

    def kernel(dst, src):
        store(dst, src, [0], [4], [1])
        deslice(dst, src, [4], [4], [1])

    func_ast = parse_function(kernel, target, source)

    assert any(isinstance(node, DmaStoreAST) for node in func_ast.body.statements)
    assert any(isinstance(node, DmaDesliceAST) for node in func_ast.body.statements)
    assert all(isinstance(node.size, SymbolListAST) for node in func_ast.body.statements if isinstance(node, (DmaStoreAST, DmaDesliceAST)))


@pytest.mark.parametrize(("kernel", "expected_type"), _DMA_RETURN_CASES)
def test_dma_public_helpers_parse_parameterized_return_nodes(kernel, expected_type: type) -> None:
    """确定性随机遍历 DMA 返回型 helper，验证公开 helper 到 AST 的映射。"""

    memory = Memory([6, 4], NumericType.Float32)

    values = _return_values(kernel, memory)

    assert any(isinstance(value, expected_type) for value in values)


@pytest.mark.parametrize(
    ("kernel", "expected_type"),
    [
        (_dma_free_kernel, DmaFreeAST),
        (_dma_store_parameterized_kernel, DmaStoreAST),
        (_dma_deslice_parameterized_kernel, DmaDesliceAST),
    ],
)
def test_dma_public_statement_helpers_parse_parameterized_nodes(kernel, expected_type: type) -> None:
    """free/store/deslice 语句型公开 helper 保持具体 AST 节点语义。"""

    target = Memory([6, 4], NumericType.Float32)
    source = Memory([2, 3], NumericType.Float32)

    func_ast = parse_function(kernel, target, source)

    assert any(isinstance(node, expected_type) for node in func_ast.body.statements)


@pytest.mark.parametrize(("kernel", "match"), _DMA_INVALID_CASES)
def test_dma_public_helpers_reject_invalid_contracts(kernel, match: str) -> None:
    """DMA plugin 对公开 helper 参数矩阵保持稳定 KernelCodeError。"""

    memory = Memory([4], NumericType.Float32)

    with pytest.raises(KernelCodeError, match=match):
        parse_function(kernel, memory)
