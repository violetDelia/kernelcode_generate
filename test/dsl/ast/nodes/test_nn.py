"""DSL AST NN node tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast.nodes.nn` 的公开节点构造与小范围字段归一。
- 测试结构对应 `spec/dsl/ast/nodes/nn.md` 与 `kernel_gen/dsl/ast/nodes/nn.py`。

使用示例:
- pytest -q test/dsl/ast/nodes/test_nn.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/nodes/nn.py
- Spec 文档: spec/dsl/ast/nodes/nn.md
- 测试文件: test/dsl/ast/nodes/test_nn.py
"""

from __future__ import annotations

import random
from dataclasses import fields

import pytest
from xdsl.context import Context
from xdsl.ir import Block, Operation

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dsl.ast.nodes.attr import FloatTypeAttrAST, MemorySpaceAttrAST
from kernel_gen.dsl.ast.nodes.basic import BoolValueAST, MemoryAST
from kernel_gen.dsl.ast.nodes.dma import DmaAllocAST
from kernel_gen.dsl.ast.nodes.symbol import ConstValueAST, SymbolAddAST, SymbolDimAST, SymbolListAST
from kernel_gen.dsl.ast.nodes.nn import (
    ConvAST,
    FCAST,
    MatmulAST,
    NnAddAST,
    NnBroadcastAST,
    NnBroadcastToAST,
    NnEqAST,
    NnExpAST,
    NnFloorDivAST,
    NnGeAST,
    NnGtAST,
    NnHardSigmoidAST,
    NnImg2Col1dAST,
    NnImg2Col2dAST,
    NnLeAST,
    NnLeakyReluAST,
    NnLtAST,
    NnMulAST,
    NnNeAST,
    NnReduceAST,
    NnReduceMaxAST,
    NnReduceMinAST,
    NnReduceSumAST,
    NnReluAST,
    NnSigmoidAST,
    NnSoftmaxAST,
    NnSubAST,
    NnTanhAST,
    NnTransposeAST,
    NnTrueDivAST,
)
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


def _block_for_memories(*nodes: MemoryAST) -> tuple[Context, Block]:
    """为公开 MemoryAST 输入构造 Context 与带命名参数的 Block。"""

    ctx = Context()
    block = Block(arg_types=[node.to_mlir_type(ctx) for node in nodes])
    for arg, node in zip(block.args, nodes, strict=True):
        arg.name_hint = node.name
    return ctx, block


def test_nn_binary_node_stores_exact_operation_kind_and_operands() -> None:
    """每个 NN 二元 op 节点保存唯一 op kind 与两个 DSLNode operand。"""

    lhs = MemoryAST("lhs", SymbolListAST([4]), SymbolListAST([1]), FloatTypeAttrAST(NumericType.Float32), MemorySpaceAttrAST(MemorySpace.GM))
    rhs = MemoryAST("rhs", SymbolListAST([4]), SymbolListAST([1]), FloatTypeAttrAST(NumericType.Float32), MemorySpaceAttrAST(MemorySpace.GM))
    node = NnAddAST(lhs, rhs)

    assert node.lhs is lhs
    assert node.rhs is rhs


def test_nn_unary_node_stores_kind_and_optional_parameters() -> None:
    """NnReluAST 继承 unary 节点字段并保留 alpha/beta 形态。"""

    value = MemoryAST("x", SymbolListAST([4]), SymbolListAST([1]), FloatTypeAttrAST(NumericType.Float32), MemorySpaceAttrAST(MemorySpace.GM))
    node = NnReluAST(value)

    assert node.value is value


def test_nn_broadcast_to_normalizes_shape_and_space_nodes() -> None:
    """broadcast_to 的 target_shape 与 space 使用公开属性节点承接。"""

    source = MemoryAST("x", SymbolListAST([1, 4]), SymbolListAST([4, 1]), FloatTypeAttrAST(NumericType.Float32), MemorySpaceAttrAST(MemorySpace.GM))
    node = NnBroadcastToAST(source, SymbolListAST([2, 4]), MemorySpace.TSM)

    assert node.source is source
    assert isinstance(node.target_shape, SymbolListAST)
    assert isinstance(node.space, MemorySpaceAttrAST)
    assert node.space.space is MemorySpace.TSM


def test_nn_matmul_and_img2col_store_structured_members() -> None:
    """matmul / img2col 节点不下沉到 Python callable 桥接结构。"""

    lhs = MemoryAST("lhs", SymbolListAST([4, 8]), SymbolListAST([8, 1]), FloatTypeAttrAST(NumericType.Float32), MemorySpaceAttrAST(MemorySpace.GM))
    rhs = MemoryAST("rhs", SymbolListAST([8, 16]), SymbolListAST([16, 1]), FloatTypeAttrAST(NumericType.Float32), MemorySpaceAttrAST(MemorySpace.GM))
    matmul = MatmulAST(lhs, rhs, MemorySpace.TSM)
    img2col = NnImg2Col1dAST(lhs, ConstValueAST(3))

    assert matmul.lhs is lhs
    assert matmul.rhs is rhs
    assert isinstance(matmul.memoryspace, MemorySpaceAttrAST)
    assert img2col.source is lhs
    assert isinstance(img2col.kw, ConstValueAST)


def test_nn_nodes_do_not_expose_legacy_dispatch_fields() -> None:
    """NN 节点字段不再使用旧 op/kind/args/kwargs 分派结构。"""

    legacy_fields = {"op", "kind", "args", "kwargs"}

    for node_type in (NnAddAST, NnEqAST, NnReluAST, NnReduceAST, NnReduceSumAST, NnImg2Col1dAST, ConvAST):
        assert legacy_fields.isdisjoint({field.name for field in fields(node_type)})


def test_nn_reduce_nodes_share_public_base_fields() -> None:
    """reduce family 共享公开 base 字段，不重复维护 axis/keepdim 结构。"""

    value = MemoryAST("x", SymbolListAST([2, 4]), SymbolListAST([4, 1]), FloatTypeAttrAST(NumericType.Float32), MemorySpaceAttrAST(MemorySpace.GM))

    for node_type in (NnReduceSumAST, NnReduceMinAST, NnReduceMaxAST):
        node = node_type(value, ConstValueAST(1), True)
        assert isinstance(node, NnReduceAST)
        assert node.value is value
        assert isinstance(node.axis, ConstValueAST)
        assert isinstance(node.keepdim, BoolValueAST)
        assert node.keepdim.value is True
        assert node.result_memory() is not None


def test_nn_result_memory_handles_parameterized_public_shapes() -> None:
    """NN 节点按公开 operation 语义推导 result_memory，覆盖静态与符号形状。"""

    rng = random.Random(20260503)

    for index in range(8):
        rows = rng.randint(2, 5)
        cols = rng.randint(2, 5)
        lhs = MemoryAST.from_memory(f"lhs_{index}", Memory([rows, cols], NumericType.Float32))
        rhs = MemoryAST.from_memory(f"rhs_{index}", Memory([cols, rows + 1], NumericType.Float32))

        assert MatmulAST(lhs, rhs).result_memory().shape.get_values() == [rows, rows + 1]
        assert NnAddAST(lhs, lhs).result_memory().shape.get_values() == [rows, cols]
        assert NnSubAST(lhs, 1).result_memory().shape.get_values() == [rows, cols]
        assert NnMulAST(2, lhs).result_memory().shape.get_values() == [rows, cols]
        assert NnTrueDivAST(lhs, lhs).result_memory().shape.get_values() == [rows, cols]
        assert NnGeAST(lhs, lhs).result_memory().dtype is NumericType.Bool
        assert NnGtAST(lhs, lhs).result_memory().dtype is NumericType.Bool
        assert NnLeAST(lhs, lhs).result_memory().dtype is NumericType.Bool
        assert NnLtAST(lhs, lhs).result_memory().dtype is NumericType.Bool
        assert NnReduceSumAST(lhs, axis=0).result_memory().shape.get_values() == [cols]
        assert NnReduceMinAST(lhs, axis=0, keepdim=True).result_memory().shape.get_values() == [1, cols]

    img1d = MemoryAST.from_memory("img1d", Memory([1, 3, SymbolDim("W")], NumericType.Float32))
    img2d = MemoryAST.from_memory("img2d", Memory([1, 3, SymbolDim("H"), SymbolDim("W")], NumericType.Float32))

    assert NnImg2Col1dAST(img1d, 3, 1, 1, 1, 1).result_memory().shape.get_values() == [1, 3, 3, SymbolDim("W")]
    assert NnImg2Col2dAST(img2d, 3, 3, 1, 1, 1, 1, 1, 1, 1, 1).result_memory().shape.get_values() == [
        1,
        3,
        3,
        3,
        SymbolDim("H"),
        SymbolDim("W"),
    ]
    assert NnReduceMaxAST(MemoryAST.from_memory("x", Memory([2, 3], NumericType.Float32)), axis=None).result_memory().shape.get_values() == [1]
    assert NnReduceSumAST(1, axis=0).result_memory() is None


def test_nn_emit_mlir_accepts_public_nodes_and_reports_public_errors() -> None:
    """NN AST 节点通过公开 emit_mlir 入口发射，非法公开输入按稳定错误失败。"""

    x = MemoryAST.from_memory("x", Memory([2, 3], NumericType.Float32))
    y = MemoryAST.from_memory("y", Memory([2, 3], NumericType.Float32))
    ctx = Context()
    block = Block(arg_types=[x.to_mlir_type(ctx), y.to_mlir_type(ctx)])
    for arg, node in zip(block.args, (x, y), strict=True):
        arg.name_hint = node.name

    success_nodes = (
        NnBroadcastAST(x, y),
        NnBroadcastToAST(x, [2, 3], MemorySpace.GM),
        NnTransposeAST(x, [1, 0]),
        NnReluAST(x),
        NnSigmoidAST(x),
        NnTanhAST(x),
        NnLeakyReluAST(x, 0.25),
        NnHardSigmoidAST(x, 0.2, 0.5),
        NnExpAST(x),
        NnReduceSumAST(x, axis=1, keepdim=True),
        NnReduceMinAST(x, axis=0),
        NnReduceMaxAST(x, axis=None),
        NnSoftmaxAST(x, axis=-1),
    )
    for node in success_nodes:
        emitted = node.emit_mlir(ctx, block)
        assert isinstance(emitted, Operation)

    with pytest.raises(KernelCodeError, match="broadcast operands must be nn.memory"):
        NnBroadcastAST(1, y).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="broadcast_to target shape item must be scalar"):
        NnBroadcastToAST(x, [y], MemorySpace.GM).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="softmax axis must be int"):
        NnSoftmaxAST(x, axis=ConstValueAST("AXIS")).emit_mlir(ctx, block)


def test_nn_emit_mlir_handles_parameterized_public_binary_and_compare_paths() -> None:
    """NN element/compare 节点覆盖 memory-symbol、symbol-memory、broadcast 与 dtype cast 公开路径。"""

    rng = random.Random(20260504)
    lhs_int = MemoryAST.from_memory("lhs_int", Memory([1, 3], NumericType.Int32))
    rhs_float = MemoryAST.from_memory("rhs_float", Memory([2, 3], NumericType.Float32))
    lhs_float = MemoryAST.from_memory("lhs_float", Memory([2, 1], NumericType.Float32))
    rhs_int = MemoryAST.from_memory("rhs_int", Memory([2, 3], NumericType.Int32))
    ctx, block = _block_for_memories(lhs_int, rhs_float, lhs_float, rhs_int)

    binary_nodes = (
        NnAddAST(rhs_float, rhs_float),
        NnSubAST(lhs_float, ConstValueAST(rng.randint(1, 5))),
        NnMulAST(ConstValueAST(rng.randint(2, 6)), lhs_float),
        NnTrueDivAST(rhs_float, rhs_float),
        NnFloorDivAST(lhs_int, ConstValueAST(2)),
    )
    for node in binary_nodes:
        assert isinstance(node.emit_mlir(ctx, block), Operation)

    compare_nodes = (
        NnEqAST(lhs_int, rhs_float),
        NnNeAST(lhs_float, rhs_int),
        NnLtAST(lhs_int, rhs_float),
        NnLeAST(lhs_float, rhs_int),
        NnGtAST(lhs_int, rhs_float),
        NnGeAST(lhs_float, rhs_int),
    )
    for node in compare_nodes:
        emitted = node.emit_mlir(ctx, block)
        assert isinstance(emitted, Operation)
        assert emitted.results[0].type.shape.data == rhs_float.to_mlir_type(ctx).shape.data

    bad = MemoryAST.from_memory("bad", Memory([4, 3], NumericType.Float32))
    bad_ctx, bad_block = _block_for_memories(lhs_float, bad)
    with pytest.raises(KernelCodeError, match="Implicit broadcast dimension mismatch"):
        NnEqAST(lhs_float, bad).emit_mlir(bad_ctx, bad_block)


def test_nn_emit_mlir_handles_symbolic_compare_and_scalar_cast_matrix() -> None:
    """NN compare/binary 公开节点覆盖符号 shape 广播、dtype cast 与 int/float 标量 cast 矩阵。"""

    lhs_uint = MemoryAST.from_memory("lhs_uint", Memory([SymbolDim("N"), 1], NumericType.Uint16))
    rhs_float = MemoryAST.from_memory("rhs_float", Memory([1, SymbolDim("M")], NumericType.Float64))
    full_int = MemoryAST.from_memory("full_int", Memory([SymbolDim("N"), SymbolDim("M")], NumericType.Int8))
    scalar_int = MemoryAST.from_memory("scalar_int", Memory([2, 2], NumericType.Int32))
    scalar_float = MemoryAST.from_memory("scalar_float", Memory([2, 2], NumericType.Float32))
    ctx, block = _block_for_memories(lhs_uint, rhs_float, full_int, scalar_int, scalar_float)

    compare_nodes = (
        NnLtAST(lhs_uint, rhs_float),
        NnGeAST(full_int, rhs_float),
        NnEqAST(rhs_float, full_int),
    )
    for node in compare_nodes:
        emitted = node.emit_mlir(ctx, block)
        assert isinstance(emitted, Operation)
        assert len(emitted.results[0].type.shape.data) == 2

    scalar_nodes = (
        NnAddAST(scalar_int, SymbolDimAST(3)),
        NnSubAST(SymbolDimAST(5), scalar_int),
        NnMulAST(scalar_float, SymbolDimAST(2)),
        NnTrueDivAST(SymbolDimAST(8), scalar_float),
        NnFloorDivAST(scalar_int, ConstValueAST(2)),
        NnFloorDivAST(scalar_int, SymbolDimAST(3)),
    )
    for node in scalar_nodes:
        assert isinstance(node.emit_mlir(ctx, block), Operation)


def test_nn_emit_mlir_rejects_memory_producing_non_argument_nodes() -> None:
    """NN 公开 AST 对“可发射 memory 但不是 tensor argument”的输入保持稳定错误语义。"""

    target = MemoryAST.from_memory("target", Memory([2, 3], NumericType.Float32))
    alloc_expr = DmaAllocAST([2, 3], NumericType.Float32, MemorySpace.GM)
    img1d = MemoryAST.from_memory("img1d", Memory([1, 3, SymbolDim("W")], NumericType.Float32))
    ctx, block = _block_for_memories(target, img1d)

    with pytest.raises(KernelCodeError, match="broadcast operands must be tensor arguments"):
        NnBroadcastAST(alloc_expr, target).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="broadcast operands must be tensor arguments"):
        NnBroadcastAST(target, DmaAllocAST([2, 3], NumericType.Float32, MemorySpace.GM)).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="broadcast operands must be nn.memory"):
        NnBroadcastAST(target, 1).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="broadcast_to source must be tensor argument"):
        NnBroadcastToAST(alloc_expr, [2, 3], MemorySpace.GM).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="broadcast_to source must be tensor argument"):
        NnBroadcastToAST(1, [2, 3], MemorySpace.GM).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="transpose value must be tensor argument"):
        NnTransposeAST(alloc_expr, [1, 0]).emit_mlir(ctx, block)
    for node_type, message in (
        (NnSigmoidAST, "sigmoid value must be tensor argument"),
        (NnTanhAST, "tanh value must be tensor argument"),
        (NnExpAST, "exp value must be tensor argument"),
    ):
        with pytest.raises(KernelCodeError, match=message):
            node_type(alloc_expr).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="leaky_relu value must be tensor argument"):
        NnLeakyReluAST(alloc_expr, 0.25).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="hard_sigmoid value must be tensor argument"):
        NnHardSigmoidAST(alloc_expr, 0.2, 0.5).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="img2col parameter must lower to symbol.int"):
        NnImg2Col1dAST(img1d, target).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="img2col source must lower to nn.memory"):
        NnImg2Col1dAST(1, 3).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="img2col source result memory is unavailable"):
        NnImg2Col1dAST(NnSoftmaxAST(DmaAllocAST([1, 3, 8], NumericType.Float32, MemorySpace.GM)), 3).emit_mlir(ctx, block)


def test_nn_reduce_base_and_img2col_public_unavailable_paths() -> None:
    """NN reduce 基类与 img2col 在公开输入缺少 memory/symbol 语义时返回稳定失败。"""

    value = MemoryAST.from_memory("value", Memory([2, 3], NumericType.Float32))
    reduce_node = NnReduceAST(value, axis=0)

    with pytest.raises(KernelCodeError, match="reduce_name must be implemented"):
        reduce_node.reduce_name()
    with pytest.raises(KernelCodeError, match="reduce_memory must be implemented"):
        reduce_node.result_memory()

    assert NnImg2Col1dAST(ConstValueAST(1), 3).result_memory() is None
    assert NnImg2Col1dAST(value, value).result_memory() is None
    assert NnImg2Col2dAST(value, 3, value).result_memory() is None


def test_nn_emit_mlir_handles_structured_public_nodes_and_dynamic_conv() -> None:
    """matmul/fc/img2col/conv 结构化节点通过公开 AST 入口覆盖静态与符号 shape。"""

    mat_lhs = MemoryAST.from_memory("mat_lhs", Memory([4, 8], NumericType.Float32))
    mat_rhs = MemoryAST.from_memory("mat_rhs", Memory([8, 5], NumericType.Float32))
    fc_weight = MemoryAST.from_memory("fc_weight", Memory([5, 8], NumericType.Float32))
    img1d = MemoryAST.from_memory("img1d", Memory([1, 3, SymbolDim("W")], NumericType.Float32))
    img2d = MemoryAST.from_memory("img2d", Memory([1, 3, SymbolDim("H"), SymbolDim("W")], NumericType.Float32))
    conv_input = MemoryAST.from_memory("conv_input", Memory([1, SymbolDim("CIN"), 8, 8], NumericType.Float32))
    conv_weight = MemoryAST.from_memory("conv_weight", Memory([SymbolDim("COUT"), SymbolDim("CIN"), 3, 3], NumericType.Float32))
    conv_symbolic_kernel_weight = MemoryAST.from_memory("conv_symbolic_kernel_weight", Memory([SymbolDim("COUT"), SymbolDim("CIN"), SymbolDim("KH"), SymbolDim("KW")], NumericType.Float32))
    conv_static_input = MemoryAST.from_memory("conv_static_input", Memory([2, 3, 9, 9], NumericType.Float32))
    conv_static_weight = MemoryAST.from_memory("conv_static_weight", Memory([4, 3, 3, 3], NumericType.Float32))
    ctx, block = _block_for_memories(mat_lhs, mat_rhs, fc_weight, img1d, img2d, conv_input, conv_weight, conv_symbolic_kernel_weight, conv_static_input, conv_static_weight)

    structured_nodes = (
        MatmulAST(mat_lhs, mat_rhs),
        FCAST(mat_lhs, fc_weight),
        NnBroadcastToAST(mat_lhs, [SymbolAddAST(ConstValueAST(2), ConstValueAST(2)), ConstValueAST(8)], MemorySpace.GM),
        NnSoftmaxAST(DmaAllocAST([2, 3], NumericType.Float32, MemorySpace.GM)),
        NnReduceSumAST(DmaAllocAST([2, 3], NumericType.Float32, MemorySpace.GM), axis=0),
        MatmulAST(DmaAllocAST([2, 3], NumericType.Float32, MemorySpace.GM), DmaAllocAST([3, 4], NumericType.Float32, MemorySpace.GM)),
        NnImg2Col1dAST(DmaAllocAST([1, 3, 8], NumericType.Float32, MemorySpace.GM), ConstValueAST(3)),
        NnImg2Col1dAST(img1d, SymbolAddAST(ConstValueAST(2), ConstValueAST(1))),
        NnImg2Col1dAST(img1d, ConstValueAST(3), ConstValueAST(1), ConstValueAST(1), ConstValueAST(1), ConstValueAST(1)),
        NnImg2Col2dAST(img2d, ConstValueAST(3), ConstValueAST(3), ConstValueAST(1), ConstValueAST(1), ConstValueAST(1), ConstValueAST(1), ConstValueAST(1), ConstValueAST(1), ConstValueAST(1), ConstValueAST(1)),
        ConvAST(conv_input, conv_weight, [ConstValueAST(1), ConstValueAST(1)], [ConstValueAST(1), ConstValueAST(1), ConstValueAST(1), ConstValueAST(1)], [ConstValueAST(1), ConstValueAST(1)]),
        ConvAST(conv_input, conv_symbolic_kernel_weight, [ConstValueAST(1), ConstValueAST(1)], [ConstValueAST(1), ConstValueAST(1), ConstValueAST(1), ConstValueAST(1)], [ConstValueAST(1), ConstValueAST(1)]),
        ConvAST(conv_static_input, conv_static_weight, [SymbolAddAST(ConstValueAST(1), ConstValueAST(0)), ConstValueAST(1)], [ConstValueAST(1), ConstValueAST(1), ConstValueAST(1), ConstValueAST(1)], [ConstValueAST(1), ConstValueAST(1)]),
    )
    for node in structured_nodes:
        assert isinstance(node.emit_mlir(ctx, block), Operation)

    with pytest.raises(KernelCodeError, match="conv stride/dilation/padding rank mismatch"):
        ConvAST(conv_input, conv_weight, [ConstValueAST(1)], [ConstValueAST(1), ConstValueAST(1), ConstValueAST(1), ConstValueAST(1)], [ConstValueAST(1), ConstValueAST(1)]).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="conv parameter must lower to symbol.int"):
        ConvAST(conv_static_input, conv_static_weight, [conv_static_input, ConstValueAST(1)], [ConstValueAST(1), ConstValueAST(1), ConstValueAST(1), ConstValueAST(1)], [ConstValueAST(1), ConstValueAST(1)]).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="matmul contracting dimension mismatch"):
        MatmulAST(mat_lhs, mat_lhs).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="conv operands must be nn.memory"):
        ConvAST(1, 2, [1, 1], [0, 0, 0, 0], [1, 1], groups=1).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="conv operands must be tensor arguments"):
        ConvAST(DmaAllocAST([1, 3, 8, 8], NumericType.Float32, MemorySpace.GM), DmaAllocAST([4, 3, 3, 3], NumericType.Float32, MemorySpace.GM), [ConstValueAST(1), ConstValueAST(1)], [ConstValueAST(0), ConstValueAST(0), ConstValueAST(0), ConstValueAST(0)], [ConstValueAST(1), ConstValueAST(1)]).emit_mlir(ctx, block)


def test_nn_matmul_rejects_unrelated_anonymous_runtime_contracting_dims() -> None:
    """matmul 不把不可证明相同的匿名运行期 contracting 维度互相匹配。"""

    lhs = MemoryAST.from_memory("lhs", Memory(["?", "?"], NumericType.Float32))
    rhs = MemoryAST.from_memory("rhs", Memory(["?", "?"], NumericType.Float32))
    ctx, block = _block_for_memories(lhs, rhs)

    with pytest.raises(KernelCodeError, match="matmul contracting dimension mismatch"):
        MatmulAST(lhs, rhs).emit_mlir(ctx, block)


def test_nn_conv_uses_shared_runtime_contracting_dim_for_matmul() -> None:
    """conv 公开 AST 在匿名运行期 shape 下生成可验证的 reshape/matmul 类型。"""

    conv_input = MemoryAST.from_memory("conv_input", Memory(["?", "?", "?", "?"], NumericType.Float32))
    conv_weight = MemoryAST.from_memory("conv_weight", Memory(["?", "?", 3, 3], NumericType.Float32))
    ctx, block = _block_for_memories(conv_input, conv_weight)

    result = ConvAST(
        conv_input,
        conv_weight,
        [ConstValueAST(1), ConstValueAST(1)],
        [ConstValueAST(1), ConstValueAST(1), ConstValueAST(1), ConstValueAST(1)],
        [ConstValueAST(1), ConstValueAST(1)],
    ).emit_mlir(ctx, block)

    matmul_ops = [op for op in block.ops if op.name == "nn.matmul"]
    assert isinstance(result, Operation)
    assert len(matmul_ops) == 1
    matmul_ops[0].verify()


def test_nn_emit_mlir_reports_public_operation_value_errors() -> None:
    """公开 NN 节点在成员节点先发射 Operation 或非法值时保持稳定错误语义。"""

    x = MemoryAST.from_memory("x", Memory([2, 3], NumericType.Float32))
    rank1 = MemoryAST.from_memory("rank1", Memory([3], NumericType.Float32))
    mat_rhs = MemoryAST.from_memory("mat_rhs", Memory([3, 4], NumericType.Float32))
    mat_rhs_i32 = MemoryAST.from_memory("mat_rhs_i32", Memory([3, 4], NumericType.Int32))
    mat_rhs_tsm = MemoryAST.from_memory("mat_rhs_tsm", Memory([3, 4], NumericType.Float32, MemorySpace.TSM))
    ctx, block = _block_for_memories(x, rank1, mat_rhs, mat_rhs_i32, mat_rhs_tsm)

    with pytest.raises(KernelCodeError, match="relu value must be tensor argument"):
        NnReluAST(DmaAllocAST([2, 3], NumericType.Float32, MemorySpace.GM)).emit_mlir(ctx, block)
    for node_type, message in (
        (NnReluAST, "relu value must lower to nn.memory"),
        (NnSigmoidAST, "sigmoid value must lower to nn.memory"),
        (NnTanhAST, "tanh value must lower to nn.memory"),
        (NnExpAST, "exp value must lower to nn.memory"),
    ):
        with pytest.raises(KernelCodeError, match=message):
            node_type(1).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="leaky_relu value must lower to nn.memory"):
        NnLeakyReluAST(1, 0.25).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="hard_sigmoid value must lower to nn.memory"):
        NnHardSigmoidAST(1, 0.2, 0.5).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="transpose value must lower to nn.memory"):
        NnTransposeAST(1, [1, 0]).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="transpose perm must be static int list"):
        NnTransposeAST(x, [ConstValueAST("bad")]).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="softmax value must lower to nn.memory"):
        NnSoftmaxAST(1).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="softmax axis out of range"):
        NnSoftmaxAST(DmaAllocAST([2, 3], NumericType.Float32, MemorySpace.GM), axis=ConstValueAST(3)).emit_mlir(ctx, block)
    for node_type, name in (
        (NnReduceSumAST, "reduce_sum"),
        (NnReduceMinAST, "reduce_min"),
        (NnReduceMaxAST, "reduce_max"),
    ):
        with pytest.raises(KernelCodeError, match=f"{name} value must lower to nn.memory"):
            node_type(ConstValueAST(1), axis=0).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="Unsupported nn.add operands"):
        NnAddAST(1, 2).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="Unsupported nn.eq operands"):
        NnEqAST(1, 2).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="Implicit broadcast dimension mismatch"):
        NnAddAST(x, mat_rhs).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="matmul operands must be nn.memory"):
        MatmulAST(1, 2).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="matmul operands must be rank-2 Memory"):
        MatmulAST(rank1, mat_rhs).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="matmul space mismatch"):
        MatmulAST(x, mat_rhs_tsm).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="matmul operand/result element_type must match"):
        MatmulAST(x, mat_rhs_i32).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="matmul result memory is unavailable"):
        MatmulAST(NnSoftmaxAST(DmaAllocAST([2, 3], NumericType.Float32, MemorySpace.GM)), DmaAllocAST([3, 4], NumericType.Float32, MemorySpace.GM)).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="fc operands must be tensor arguments"):
        FCAST(1, 2).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="fc operands must be tensor arguments"):
        FCAST(DmaAllocAST([2, 3], NumericType.Float32, MemorySpace.GM), DmaAllocAST([4, 3], NumericType.Float32, MemorySpace.GM)).emit_mlir(ctx, block)
    bad_fc_weight = MemoryAST.from_memory("bad_fc_weight", Memory([4, 5], NumericType.Float32))
    bad_ctx, bad_block = _block_for_memories(x, bad_fc_weight)
    with pytest.raises(KernelCodeError, match="matmul contracting dimension mismatch"):
        FCAST(x, bad_fc_weight).emit_mlir(bad_ctx, bad_block)
    with pytest.raises(KernelCodeError, match="reduce_sum result memory is unavailable"):
        NnReduceSumAST(NnSoftmaxAST(DmaAllocAST([2, 3], NumericType.Float32, MemorySpace.GM)), axis=0).emit_mlir(ctx, block)


def test_nn_emit_mlir_operation_operand_and_result_memory_matrix() -> None:
    """NN 公开节点覆盖 Operation operand、符号 fallback 与 compare result_memory 矩阵。"""

    ctx = Context()
    block = Block(arg_types=[])
    add_op = NnAddAST(DmaAllocAST([2, 3], NumericType.Float32, MemorySpace.GM), DmaAllocAST([2, 3], NumericType.Float32, MemorySpace.GM)).emit_mlir(ctx, block)
    eq_op = NnEqAST(DmaAllocAST([1, 3], NumericType.Int32, MemorySpace.GM), DmaAllocAST([2, 3], NumericType.Float32, MemorySpace.GM)).emit_mlir(ctx, block)

    assert isinstance(add_op, Operation)
    assert isinstance(eq_op, Operation)
    assert len(tuple(block.ops)) >= 6

    memory = MemoryAST.from_memory("memory", Memory([2, 3], NumericType.Float32))
    int_memory = MemoryAST.from_memory("int_memory", Memory([2, 3], NumericType.Int32))
    other = MemoryAST.from_memory("other", Memory([4, 5], NumericType.Int32))
    shape_mismatch = MemoryAST.from_memory("shape_mismatch", Memory([2, 4], NumericType.Float32))
    assert NnAddAST(ConstValueAST(1.5), memory).result_memory() is None
    assert NnAddAST(memory, SymbolDimAST("S")).result_memory().shape.get_values() == [2, 3]
    assert NnSubAST(SymbolDimAST("S"), memory).result_memory().shape.get_values() == [2, 3]
    with pytest.raises(KernelCodeError, match="Implicit broadcast dimension mismatch"):
        NnAddAST(memory, shape_mismatch).result_memory()
    assert NnEqAST(ConstValueAST(1.5), memory).result_memory() is None
    assert NnEqAST(memory, int_memory).result_memory().dtype is NumericType.Bool
    assert NnEqAST(memory, SymbolDimAST("S")).result_memory().dtype is NumericType.Bool
    assert NnEqAST(SymbolDimAST("S"), memory).result_memory().shape.get_values() == [2, 3]
    assert NnEqAST(memory, other).result_memory().dtype is NumericType.Bool
    with pytest.raises(KernelCodeError, match="At least one operand must be Memory"):
        NnEqAST(SymbolDimAST("S"), SymbolDimAST("T")).result_memory()
