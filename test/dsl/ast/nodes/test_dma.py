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

import random

import pytest
from xdsl.context import Context
from xdsl.ir import Block, Operation, SSAValue

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolValueType
from kernel_gen.dsl.ast.nodes.attr import BoolTypeAttrAST, FloatTypeAttrAST, IntTypeAttrAST, MemorySpaceAttrAST
from kernel_gen.dsl.ast.nodes.basic import MemoryAST, ValueAST
from kernel_gen.dsl.ast.nodes.symbol import ConstValueAST, SymbolListAST
from kernel_gen.dsl.ast.nodes.symbol import SymbolAddAST, SymbolDimAST, SymbolFloorDivAST, SymbolMulAST, SymbolSubAST, SymbolTrueDivAST, TensorAxisAccessAST
from kernel_gen.dsl.ast.nodes.dma import (
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
)
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
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


def _block_for_memories(*nodes: MemoryAST) -> tuple[Context, Block]:
    """为公开 MemoryAST 输入构造 Context 与带命名参数的 Block。"""

    ctx = Context()
    block = Block(arg_types=[node.to_mlir_type(ctx) for node in nodes])
    for arg, node in zip(block.args, nodes, strict=True):
        arg.name_hint = node.name
    return ctx, block


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

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> SSAValue:
        """发射一个测试用 memory SSA。"""

        assert isinstance(block, Block)
        source_type = _memory("src", [8]).to_mlir_type(ctx)
        alloc = DmaAllocOp([], source_type)
        block.add_op(alloc)
        return alloc.results[0]


class RawEmitAST(ValueAST):
    """按测试输入原样返回非法 emit 结果。"""

    def __init__(self, value: int | str | None) -> None:
        self.value = value

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> int | str | None:
        """返回原始值，用于验证公开 AST 对非法 emit 结果的错误语义。"""

        _ = (ctx, block)
        return self.value


class SymbolConstEmitAST(ValueAST):
    """返回公开 SymbolConstOp，用于验证 AST 接受 Operation-return 子节点。"""

    def __init__(self, value: int) -> None:
        self.value = value

    def result_symbol(self) -> int:
        """返回解析期公开 symbol 语义。"""

        return self.value

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> Operation:
        """发射公开 `symbol.const` operation。"""

        _ = (ctx, block)
        return SymbolConstOp(self.value)


class BlockArgSymbolAST(ValueAST):
    """返回公开 block argument symbol SSA，用于测试公开类型传播。"""

    def __init__(self, index: int, symbol: int | str | SymbolDim | None = None) -> None:
        self.index = index
        self.symbol = symbol

    def result_symbol(self) -> int | SymbolDim | None:
        """返回测试显式提供的公开解析期 symbol 语义。"""

        if self.symbol is None:
            return None
        if isinstance(self.symbol, (int, SymbolDim)):
            return self.symbol
        return SymbolDim(self.symbol)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> SSAValue:
        """发射指定 block argument，不通过 SSA 名称构造表达式。"""

        _ = ctx
        assert isinstance(block, Block)
        return block.args[self.index]


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


def test_dma_result_memory_handles_parameterized_public_shapes() -> None:
    """DMA result 节点按公开 Memory 语义推导 shape、dtype 与 space。"""

    rng = random.Random(20260503)

    for index in range(8):
        rows = rng.randint(2, 8)
        cols = rng.randint(2, 8)
        source = MemoryAST.from_memory(f"src_{index}", Memory([rows, cols], NumericType.Float32))

        assert DmaAllocAST([SymbolDim("N"), cols], NumericType.Float32, MemorySpace.SM).result_memory().space is MemorySpace.SM
        assert DmaCopyAST(source, MemorySpace.SM).result_memory().shape.get_values() == [rows, cols]
        assert DmaCopyAST(source, MemorySpace.SM).result_memory().space is MemorySpace.SM
        assert DmaCastAST(source, NumericType.Float16, MemorySpace.LM).result_memory().dtype is NumericType.Float16
        assert DmaViewAST(source, [0, 0], [rows - 1, cols], [1, 1]).result_memory().shape.get_values() == [rows - 1, cols]
        assert DmaReshapeAST(source, [rows * cols]).result_memory().shape.get_values() == [rows * cols]
        assert DmaFlattenAST(source).result_memory().shape.get_values() == [rows * cols]
        assert DmaLoadAST(source, [0, 0], [rows - 1, cols], [1, 1], MemorySpace.SM).result_memory().space is MemorySpace.SM
        assert DmaSliceAST(source, [0, 0], [rows - 1, cols], [1, 1], MemorySpace.SM).result_memory().space is MemorySpace.SM

    assert DmaCopyAST(1, MemorySpace.SM).result_memory() is None
    assert DmaAllocAST([_memory("shape_unknown", [2])], NumericType.Float32).result_memory() is None
    assert DmaAllocAST([2], NumericType.Float32, stride=[_memory("stride_unknown", [2])]).result_memory() is None
    assert DmaLoadAST(_memory("stride_source", [4]), [0], [1], [_memory("stride_bad", [2])]).result_memory() is None


def test_dma_emit_mlir_accepts_public_nodes_and_reports_public_errors() -> None:
    """DMA AST 节点通过公开 emit_mlir 发射，非法公开输入按稳定错误失败。"""

    x = MemoryAST.from_memory("x", Memory([8, 4], NumericType.Float32))
    y = MemoryAST.from_memory("y", Memory([8, 4], NumericType.Float32))
    tile = MemoryAST.from_memory("tile", Memory([4, 4], NumericType.Float32))
    ctx = Context()
    block = Block(arg_types=[x.to_mlir_type(ctx), y.to_mlir_type(ctx), tile.to_mlir_type(ctx)])
    for arg, node in zip(block.args, (x, y, tile), strict=True):
        arg.name_hint = node.name

    success_nodes = (
        DmaAllocAST([8, 4], NumericType.Float32, MemorySpace.SM),
        DmaAllocAST([SymbolDimAST(4)], NumericType.Float32, MemorySpace.SM, stride=[SymbolDimAST(1)]),
        DmaCopyAST(DmaAllocAST([8, 4], NumericType.Float32, MemorySpace.GM), MemorySpace.SM),
        DmaCopyAST(x, MemorySpace.SM),
        DmaCastAST(DmaAllocAST([8, 4], NumericType.Float32, MemorySpace.GM), NumericType.Float16, MemorySpace.SM),
        DmaCastAST(x, NumericType.Float16, MemorySpace.SM),
        DmaViewAST(DmaAllocAST([8, 4], NumericType.Float32, MemorySpace.GM), [0, 0], [4, 4], [1, 1]),
        DmaViewAST(x, [0, 0], [4, 4], [1, 1]),
        DmaReshapeAST(DmaAllocAST([2, 4], NumericType.Float32, MemorySpace.GM), [8]),
        DmaReshapeAST(x, [32]),
        DmaFlattenAST(DmaAllocAST([2, 4], NumericType.Float32, MemorySpace.GM)),
        DmaFlattenAST(x),
        DmaFillAST(DmaAllocAST([2], NumericType.Float32, MemorySpace.GM), 0),
        DmaFillAST(x, "inf"),
        DmaLoadAST(DmaAllocAST([8, 4], NumericType.Float32, MemorySpace.GM), [0, 0], [4, 4], [1, 1], MemorySpace.SM),
        DmaLoadAST(x, [0, 0], [4, 4], [1, 1], MemorySpace.SM),
        DmaSliceAST(x, [0, 0], [4, 4], [1, 1], MemorySpace.SM),
        DmaStoreAST(y, DmaAllocAST([4, 4], NumericType.Float32, MemorySpace.GM), [0, 0], [4, 4], [1, 1]),
        DmaStoreAST(y, tile, [0, 0], [4, 4], [1, 1]),
        DmaDesliceAST(y, tile, [0, 0], [4, 4], [1, 1]),
    )
    for node in success_nodes:
        emitted = node.emit_mlir(ctx, block)
        assert isinstance(emitted, (Operation, type(None))) or hasattr(emitted, "type")

    DmaFreeAST(x).emit_mlir(ctx, block)
    DmaFreeAST(DmaAllocAST([2], NumericType.Float32, MemorySpace.GM)).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="copy source must lower to nn.memory"):
        DmaCopyAST(1, MemorySpace.SM).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="fill string literal"):
        DmaFillAST(x, "nan").emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="load offset must lower to symbol.int"):
        DmaLoadAST(x, [x], [4], [1]).emit_mlir(ctx, block)


def test_dma_alloc_emit_mlir_handles_parameterized_public_shape_expressions() -> None:
    """dma.alloc 公开 AST 覆盖动态 shape 表达式、dtype 分支与 stride 合同。"""

    rng = random.Random(20260504)
    shape_exprs = [
        SymbolAddAST(ConstValueAST(rng.randint(2, 4)), ConstValueAST(3)),
        SymbolSubAST(ConstValueAST(9), ConstValueAST(rng.randint(1, 3))),
        SymbolMulAST(ConstValueAST(2), ConstValueAST(rng.randint(3, 5))),
        SymbolTrueDivAST(ConstValueAST(8), ConstValueAST(2)),
        SymbolFloorDivAST(ConstValueAST(9), ConstValueAST(2)),
    ]
    ctx = Context()
    block = Block()
    emitted = DmaAllocAST(shape_exprs, NumericType.Int32, MemorySpace.SM).emit_mlir(ctx, block)
    assert isinstance(emitted, DmaAllocOp)
    assert len(emitted.dynamic_shape) == len(shape_exprs)

    symbol_block = Block(arg_types=[SymbolValueType.from_expr("M")])
    symbol_alloc = DmaAllocAST([SymbolFloorDivAST(BlockArgSymbolAST(0, "M"), ConstValueAST(2))], NumericType.Float32, MemorySpace.SM).emit_mlir(
        Context(), symbol_block
    )
    assert isinstance(symbol_alloc, DmaAllocOp)
    assert symbol_alloc.result.type.shape.data[0].expr.data == "M floordiv 2"

    bool_alloc = DmaAllocAST([2], NumericType.Bool, MemorySpace.LM).emit_mlir(Context(), Block())
    int_alloc = DmaAllocAST([2], NumericType.Uint16, MemorySpace.LM).emit_mlir(Context(), Block())
    signed_alloc = DmaAllocAST([2], IntTypeAttrAST(64, True), MemorySpace.LM).emit_mlir(Context(), Block())
    unsigned_alloc = DmaAllocAST([2], IntTypeAttrAST(32, False), MemorySpace.LM).emit_mlir(Context(), Block())
    strided = DmaAllocAST([2, 3], NumericType.Float32, MemorySpace.SM, stride=[3, 1])
    assert isinstance(bool_alloc, DmaAllocOp)
    assert isinstance(int_alloc, DmaAllocOp)
    assert isinstance(signed_alloc, DmaAllocOp)
    assert isinstance(unsigned_alloc, DmaAllocOp)
    assert strided.result_memory().stride.get_values() == [3, 1]

    with pytest.raises(KernelCodeError, match="alloc dtype must be a public dtype attr"):
        DmaAllocAST([2], "bad-dtype", MemorySpace.SM)
    shape_mem = _memory("shape_mem", [2])
    shape_ctx, shape_block = _block_for_memories(shape_mem)
    with pytest.raises(KernelCodeError, match="alloc shape must lower to symbol.int"):
        DmaAllocAST([shape_mem], NumericType.Float32, MemorySpace.SM).emit_mlir(shape_ctx, shape_block)
    stride_mem = _memory("stride_mem", [2])
    stride_ctx, stride_block = _block_for_memories(stride_mem)
    with pytest.raises(KernelCodeError, match="alloc stride must lower to symbol.int"):
        DmaAllocAST([2], NumericType.Float32, MemorySpace.SM, stride=[stride_mem]).emit_mlir(stride_ctx, stride_block)
    with pytest.raises(KernelCodeError, match="alloc shape expression must lower to SSA values"):
        DmaAllocAST([SymbolAddAST(RawEmitAST(1), ConstValueAST(3))], NumericType.Float32, MemorySpace.SM).emit_mlir(Context(), Block())
    with pytest.raises(KernelCodeError, match="dma.alloc only supports contiguous stride"):
        DmaAllocAST([2, 3], NumericType.Float32, MemorySpace.SM, stride=[1, 1]).emit_mlir(Context(), Block())


def test_dma_emit_mlir_handles_dynamic_public_memory_paths() -> None:
    """DMA copy/cast/view/reshape/flatten/load/slice 覆盖符号 shape 与默认 stride 公开路径。"""

    source = MemoryAST.from_memory("source", Memory([SymbolDim("N"), 4], NumericType.Float32))
    target = MemoryAST.from_memory("target", Memory([SymbolDim("N"), 4], NumericType.Float32))
    tile = MemoryAST.from_memory("tile", Memory([2, 4], NumericType.Float32, space=MemorySpace.SM))
    ctx, block = _block_for_memories(source, target, tile)

    for node in (
        DmaCopyAST(source, MemorySpace.SM),
        DmaCastAST(source, NumericType.Float16, MemorySpace.SM),
        DmaViewAST(source, [0, 0], [2, 4], [1, 1]),
        DmaReshapeAST(source, [2, 4]),
        DmaFlattenAST(source),
        DmaLoadAST(source, [0, 0], [2, 4], None, MemorySpace.SM),
        DmaSliceAST(source, [0, 0], [2, 4], None, MemorySpace.SM),
    ):
        emitted = node.emit_mlir(ctx, block)
        assert isinstance(emitted, (Operation, SSAValue))

    assert isinstance(DmaStoreAST(target, tile, [0, 0], [2, 4], None).emit_mlir(ctx, block), Operation)
    assert isinstance(DmaDesliceAST(target, tile, [0, 0], [2, 4], None).emit_mlir(ctx, block), Operation)
    dynamic_size = [TensorAxisAccessAST(source, "shape", 0), 4]
    assert isinstance(DmaLoadAST(source, [0, 0], dynamic_size, None, MemorySpace.SM).emit_mlir(ctx, block), SSAValue)
    assert isinstance(DmaSliceAST(source, [0, 0], dynamic_size, None, MemorySpace.SM).emit_mlir(ctx, block), SSAValue)


def test_dma_slice_uses_full_rank_dynamic_shape_for_unknown_named_result() -> None:
    """DmaSliceAST 对公开命名但 SSA 类型未知的结果使用 full-rank dynamic_shape。"""

    source = MemoryAST.from_memory("source", Memory([8, 8, 3, 3], NumericType.Float32))
    ctx = Context()
    block = Block(arg_types=[source.to_mlir_type(ctx), SymbolValueType.from_expr("?"), SymbolValueType.from_expr("?")])
    block.args[0].name_hint = "source"
    node = DmaSliceAST(
        source,
        [0, 0, 0, 0],
        [
            BlockArgSymbolAST(1, "?"),
            BlockArgSymbolAST(2, "?"),
            3,
            3,
        ],
        None,
        MemorySpace.SM,
    )

    emitted = node.emit_mlir(ctx, block)

    assert isinstance(emitted, SSAValue)
    assert isinstance(emitted.owner, DmaAllocOp)
    assert len(emitted.owner.dynamic_shape) == 4
    emitted.owner.verify()


def test_dma_reshape_uses_public_name_for_unknown_shape_operand() -> None:
    """DmaReshapeAST 对公开赋值名的 `?` shape operand 生成稳定 runtime 维度别名。"""

    source = MemoryAST.from_memory("source", Memory([SymbolDim("TOTAL")], NumericType.Float32))
    ctx = Context()
    block = Block(
        arg_types=[
            source.to_mlir_type(ctx),
            SymbolValueType.from_expr("?"),
            SymbolValueType.from_expr("?"),
        ]
    )
    block.args[0].name_hint = "source"
    block.args[1].name_hint = "k_tile"
    block.args[2].name_hint = "out_tile"

    emitted = DmaReshapeAST(
        source,
        [
            SymbolDimAST("k_tile", runtime_symbol=SymbolDim("?")),
            SymbolDimAST("out_tile", runtime_symbol=SymbolDim("?")),
        ],
    ).emit_mlir(ctx, block)

    assert isinstance(emitted, Operation)
    assert [dim.expr.data for dim in emitted.result.type.shape.data] == ["k_tile", "out_tile"]
    assert [dim.expr.data for dim in emitted.result.type.stride.data] == ["out_tile", "1"]
    assert [operand.type.get_value() for operand in emitted.shape] == ["?", "?"]
    emitted.verify()


def test_dma_alloc_lowers_public_symbol_binary_shape_to_symbol_expr_type() -> None:
    """DmaAllocAST 通过公开 symbol AST 生成结构化 shape/stride 类型。"""

    ctx = Context()
    block = Block(arg_types=[SymbolValueType.from_expr("M"), SymbolValueType.from_expr("N")])
    node = DmaAllocAST(
        [
            SymbolAddAST(BlockArgSymbolAST(0, "M"), ConstValueAST(1)),
            SymbolMulAST(ConstValueAST(2), BlockArgSymbolAST(1, "N")),
        ],
        NumericType.Float32,
        MemorySpace.SM,
    )

    emitted = node.emit_mlir(ctx, block)

    assert isinstance(emitted, DmaAllocOp)
    assert [dim.expr.data for dim in emitted.result.type.shape.data] == ["M + 1", "2*N"]
    assert [dim.expr.data for dim in emitted.result.type.stride.data] == ["2*N", "1"]
    assert len(emitted.dynamic_shape) == 2
    emitted.verify()


def test_dma_alloc_emit_mlir_covers_public_dtype_and_symbol_sub_matrix() -> None:
    """DmaAllocAST 覆盖公开 bool/int dtype 与 symbol sub shape。"""

    ctx = Context()
    block = Block(arg_types=[SymbolValueType.from_expr("M"), SymbolValueType.from_expr("N")])

    bool_alloc = DmaAllocAST(
        [SymbolSubAST(BlockArgSymbolAST(0, "M"), ConstValueAST(1))],
        BoolTypeAttrAST(),
        MemorySpace.GM,
    ).emit_mlir(ctx, block)
    int_alloc = DmaAllocAST(
        [BlockArgSymbolAST(1, "N")],
        IntTypeAttrAST(16, False),
        MemorySpace.SM,
    ).emit_mlir(ctx, block)

    assert isinstance(bool_alloc, DmaAllocOp)
    assert isinstance(int_alloc, DmaAllocOp)
    assert bool_alloc.result.type.shape.data[0].expr.data == "M - 1"
    assert int_alloc.result.type.shape.data[0].expr.data == "N"
    bool_alloc.verify()
    int_alloc.verify()


def test_dma_emit_mlir_accepts_public_operation_returning_symbol_nodes() -> None:
    """DMA 公开节点接受返回 Operation 的 symbol 子节点。"""

    target = MemoryAST.from_memory("target", Memory([4], NumericType.Float32))
    source = MemoryAST.from_memory("source", Memory([4], NumericType.Float32))
    tile = MemoryAST.from_memory("tile", Memory([2], NumericType.Float32))
    ctx, block = _block_for_memories(target, source, tile)

    alloc = DmaAllocAST(
        [SymbolConstEmitAST(4), SymbolConstEmitAST(2)],
        NumericType.Float32,
        MemorySpace.SM,
        stride=[SymbolConstEmitAST(2), SymbolConstEmitAST(1)],
    ).emit_mlir(ctx, block)
    view = DmaViewAST(
        source,
        [SymbolConstEmitAST(0)],
        [SymbolConstEmitAST(2)],
        [SymbolConstEmitAST(1)],
    ).emit_mlir(ctx, block)
    loaded = DmaLoadAST(
        source,
        [SymbolConstEmitAST(0)],
        [SymbolConstEmitAST(2)],
        [SymbolConstEmitAST(1)],
        MemorySpace.SM,
    ).emit_mlir(ctx, block)
    reshaped = DmaReshapeAST(source, [SymbolConstEmitAST(4)]).emit_mlir(ctx, block)
    store_op = DmaStoreAST(
        target,
        tile,
        [SymbolConstEmitAST(0)],
        [SymbolConstEmitAST(2)],
        [SymbolConstEmitAST(1)],
    ).emit_mlir(ctx, block)

    assert isinstance(alloc, DmaAllocOp)
    assert isinstance(view, Operation)
    assert isinstance(loaded, SSAValue)
    assert isinstance(reshaped, Operation)
    assert isinstance(store_op, Operation)
    alloc.verify()
    loaded.owner.verify()
    reshaped.verify()


def test_dma_fill_emit_mlir_handles_public_value_and_dtype_matrix() -> None:
    """dma.fill 覆盖 bool/int/float/symbol/string 公开值矩阵与稳定错误语义。"""

    bool_mem = MemoryAST.from_memory("bool_mem", Memory([2], NumericType.Bool))
    int_mem = MemoryAST.from_memory("int_mem", Memory([2], NumericType.Int32))
    float_mem = MemoryAST.from_memory("float_mem", Memory([2], NumericType.Float32))
    ctx, block = _block_for_memories(bool_mem, int_mem, float_mem)

    for node in (
        DmaFillAST(bool_mem, True),
        DmaFillAST(int_mem, 7),
        DmaFillAST(float_mem, 3),
        DmaFillAST(float_mem, 1.5),
        DmaFillAST(float_mem, "-inf"),
        DmaFillAST(float_mem, SymbolDimAST(5)),
        DmaFillAST(bool_mem, False),
        DmaFillAST(bool_mem, 1),
    ):
        assert isinstance(node.emit_mlir(ctx, block), Operation)

    with pytest.raises(KernelCodeError, match="fill string literal requires float memory"):
        DmaFillAST(int_mem, "inf").emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="fill float value requires float memory"):
        DmaFillAST(int_mem, 1.5).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="Unsupported fill value"):
        DmaFillAST(float_mem, None).emit_mlir(ctx, block)


def test_dma_emit_mlir_reports_public_error_matrix() -> None:
    """DMA 公开 AST 覆盖非法 emit 结果、非 memory 输入与写回语义错误矩阵。"""

    target = MemoryAST.from_memory("target", Memory([4, 4], NumericType.Float32))
    tile = MemoryAST.from_memory("tile", Memory([2, 4], NumericType.Float32))
    ctx, block = _block_for_memories(target, tile)

    error_cases = (
        (DmaFreeAST(ConstValueAST(1)), "value must be Memory"),
        (DmaFillAST(ConstValueAST(1), 0), "fill target must lower to nn.memory"),
        (DmaViewAST(RawEmitAST(1), [0, 0], [2, 2], [1, 1]), "view source must lower to SSA value"),
        (DmaViewAST(1, [0], [1], [1]), "view source must lower to nn.memory"),
        (DmaViewAST(target, [target], [1], [1]), "view offset must lower to symbol.int"),
        (DmaViewAST(target, [0], [target], [1]), "view size must lower to symbol.int"),
        (DmaViewAST(target, [0], [1], [target]), "view stride must lower to symbol.int"),
        (DmaReshapeAST(RawEmitAST(1), [4]), "reshape source must lower to SSA value"),
        (DmaReshapeAST(1, [4]), "reshape source must be nn.memory"),
        (DmaReshapeAST(target, [target]), "reshape shape must lower to symbol.int"),
        (DmaFlattenAST(RawEmitAST(1)), "flatten source must lower to SSA value"),
        (DmaFlattenAST(1), "flatten source must be nn.memory"),
        (DmaLoadAST(RawEmitAST(1), [0], [1], [1]), "load source must lower to SSA value"),
        (DmaLoadAST(1, [0], [1], [1]), "load source must lower to nn.memory"),
        (DmaSliceAST(RawEmitAST(1), [0], [1], [1]), "slice source must lower to SSA value"),
        (DmaAllocAST([DmaAllocAST([2], NumericType.Float32, MemorySpace.GM)], NumericType.Float32, MemorySpace.SM), "alloc shape must lower to symbol.int"),
        (DmaCopyAST(RawEmitAST(1), MemorySpace.SM), "copy source must lower to SSA value"),
        (DmaCastAST(RawEmitAST(1), NumericType.Float16), "cast source must lower to SSA value"),
        (DmaCastAST(1, NumericType.Float16), "cast source must lower to nn.memory"),
        (DmaLoadAST(target, [target], [1], [1]), "load offset must lower to symbol.int"),
        (DmaSliceAST(target, [0], [target], [1]), "slice size must lower to symbol.int"),
        (DmaSliceAST(target, [0], [1], [target]), "slice stride must lower to symbol.int"),
        (DmaStoreAST(target, ConstValueAST(1), [0, 0], [2, 4], [1, 1]), "store source must lower to nn.memory"),
        (DmaStoreAST(DmaAllocAST([4, 4], NumericType.Float32, MemorySpace.GM), tile, [0, 0], [2, 4], [1, 1]), "store target must be MemoryAST"),
        (DmaStoreAST(target, tile, [target], [2, 4], [1, 1]), "store offset must lower to symbol.int"),
        (DmaStoreAST(target, tile, [0, 0], [target], [1, 1]), "store size must lower to symbol.int"),
        (DmaStoreAST(target, tile, [0, 0], [2, 4], [target]), "store stride must lower to symbol.int"),
        (DmaStoreAST(1, tile, [0], [1], [1]), "store target must be MemoryAST"),
        (DmaDesliceAST(ConstValueAST(1), tile, [0, 0], [2, 4], [1, 1]), "deslice target must be nn.memory"),
        (DmaDesliceAST(target, tile, [target], [2, 4], [1, 1]), "deslice offset must lower to symbol.int"),
        (DmaDesliceAST(target, tile, [0, 0], [target], [1, 1]), "deslice size must lower to symbol.int"),
        (DmaDesliceAST(target, tile, [0, 0], [2, 4], [target]), "deslice stride must lower to symbol.int"),
        (DmaStoreAST(RawEmitAST(1), tile, [0], [1], [1]), "store operands must lower to SSA values"),
    )
    for node, message in error_cases:
        with pytest.raises(KernelCodeError, match=message):
            node.emit_mlir(ctx, block)

    with pytest.raises(KernelCodeError):
        DmaStoreAST(target, tile, [0, 0], [8, 4], [1, 1]).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError):
        DmaDesliceAST(target, tile, [0, 0], [8, 4], [1, 1]).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="cast dtype must be a public dtype attr"):
        DmaCastAST(target, "bad-dtype")


def test_dma_flatten_public_dynamic_and_scalar_shape_matrix() -> None:
    """dma.flatten 公开 AST 覆盖多维符号 shape 与 rank-0 输入边界。"""

    dynamic = MemoryAST.from_memory("dynamic", Memory([SymbolDim("N"), SymbolDim("M"), 4], NumericType.Float32))
    scalar = MemoryAST.from_memory("scalar", Memory([], NumericType.Float32))
    ctx, block = _block_for_memories(dynamic, scalar)

    assert isinstance(DmaFlattenAST(dynamic).emit_mlir(ctx, block), Operation)
    assert isinstance(DmaFlattenAST(scalar).emit_mlir(ctx, block), Operation)
