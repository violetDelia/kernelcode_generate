"""DSL AST DMA node tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast.nodes.dma` 的公开节点构造与关键字段归一。
- 测试结构对应 `spec/dsl/ast/nodes/dma.md` 与 `kernel_gen/dsl/ast/nodes/dma.py`。

使用示例:
- pytest -q test/dsl/ast/nodes/test_dma.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/nodes/dma.py
- Spec 文档: spec/dsl/ast/nodes/dma.md
- 测试文件: test/dsl/ast/nodes/test_dma.py
"""

from __future__ import annotations

import pytest
from xdsl.context import Context
from xdsl.ir import Block

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dsl.ast.nodes.attr import FloatTypeAttrAST, MemorySpaceAttrAST
from kernel_gen.dsl.ast.nodes.basic import MemoryAST, ValueAST
from kernel_gen.dsl.ast.nodes.symbol import ConstValueAST, SymbolListAST
from kernel_gen.dsl.ast.nodes.dma import (
    DmaAllocAST,
    DmaCastAST,
    DmaCopyAST,
    DmaDesliceAST,
    DmaFlattenAST,
    DmaLoadAST,
    DmaReshapeAST,
    DmaSliceAST,
    DmaStoreAST,
    DmaViewAST,
)
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.type import NumericType


def _memory(name: str, shape: list[int]) -> MemoryAST:
    """构造公开 MemoryAST 测试值。"""

    stride: list[int] = []
    running = 1
    for dim in reversed(shape):
        stride.insert(0, running)
        running *= dim
    return MemoryAST(
        name,
        SymbolListAST(shape),
        SymbolListAST(stride),
        FloatTypeAttrAST(NumericType.Float32),
        MemorySpaceAttrAST(MemorySpace.GM),
    )


def test_dma_alloc_normalizes_shape_dtype_space_and_stride_nodes() -> None:
    """DmaAllocAST 把裸 shape/dtype/space/stride 归一为对应 DSLNode。"""

    node = DmaAllocAST(
        SymbolListAST([4, 8]),
        FloatTypeAttrAST(NumericType.Float32),
        MemorySpaceAttrAST(MemorySpace.TSM),
        stride=SymbolListAST([8, 1]),
    )

    assert isinstance(node.shape, SymbolListAST)
    assert isinstance(node.dtype, FloatTypeAttrAST)
    assert isinstance(node.space, MemorySpaceAttrAST)
    assert isinstance(node.stride, SymbolListAST)
    assert node.dtype.dtype is NumericType.Float32
    assert node.space.space is MemorySpace.TSM


def test_dma_read_nodes_keep_source_first_contract() -> None:
    """DmaLoadAST / DmaSliceAST 保存 source-first 读取合同。"""

    source = _memory("src", [8])
    load = DmaLoadAST(source, SymbolListAST([0]), SymbolListAST([4]), SymbolListAST([1]))
    slice_node = DmaSliceAST(
        source,
        SymbolListAST([4]),
        SymbolListAST([4]),
        SymbolListAST([1]),
        MemorySpaceAttrAST(MemorySpace.TSM),
    )

    assert load.source is source
    assert isinstance(load.size, SymbolListAST)
    assert slice_node.source is source
    assert isinstance(slice_node.size, SymbolListAST)
    assert isinstance(slice_node.space, MemorySpaceAttrAST)


def test_dma_write_nodes_keep_target_first_contract() -> None:
    """DmaStoreAST / DmaDesliceAST 保存 target-first 写回合同。"""

    target = _memory("dst", [8])
    source = _memory("src", [4])
    store = DmaStoreAST(target, source, SymbolListAST([0]), SymbolListAST([4]), SymbolListAST([1]))
    deslice = DmaDesliceAST(target, source, SymbolListAST([4]), SymbolListAST([4]), SymbolListAST([1]))

    assert store.target is target
    assert store.source is source
    assert isinstance(store.offset.items[0], ConstValueAST)
    assert deslice.target is target
    assert deslice.source is source
    assert isinstance(deslice.size, SymbolListAST)


class SsaOnlyMemoryAST(ValueAST):
    """只发射 SSA memory，但不提供解析期 result_memory。"""

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> object:
        """发射一个测试用 memory SSA。"""

        assert isinstance(block, Block)
        source_type = _memory("src", [8]).to_mlir_type(ctx)
        alloc = DmaAllocOp([], source_type)
        block.add_op(alloc)
        return alloc.results[0]


def test_dma_result_nodes_require_ast_result_memory_for_result_type() -> None:
    """DMA result op 不再从 SSA type 反推结果 memory。"""

    source = SsaOnlyMemoryAST()

    with pytest.raises(KernelCodeError, match="load result memory must be known from AST"):
        DmaLoadAST(source, SymbolListAST([0]), SymbolListAST([4]), SymbolListAST([1])).emit_mlir(Context(), Block())

    with pytest.raises(KernelCodeError, match="slice result memory must be known from AST"):
        DmaSliceAST(source, SymbolListAST([0]), SymbolListAST([4]), SymbolListAST([1])).emit_mlir(Context(), Block())

    with pytest.raises(KernelCodeError, match="copy result memory must be known from AST"):
        DmaCopyAST(source, MemorySpaceAttrAST(MemorySpace.TSM)).emit_mlir(Context(), Block())

    with pytest.raises(KernelCodeError, match="cast result memory must be known from AST"):
        DmaCastAST(source, FloatTypeAttrAST(NumericType.Float16)).emit_mlir(Context(), Block())

    with pytest.raises(KernelCodeError, match="view result memory must be known from AST"):
        DmaViewAST(source, SymbolListAST([0]), SymbolListAST([4]), SymbolListAST([1])).emit_mlir(Context(), Block())

    with pytest.raises(KernelCodeError, match="reshape result memory must be known from AST"):
        DmaReshapeAST(source, SymbolListAST([8])).emit_mlir(Context(), Block())

    with pytest.raises(KernelCodeError, match="flatten result memory must be known from AST"):
        DmaFlattenAST(source).emit_mlir(Context(), Block())
