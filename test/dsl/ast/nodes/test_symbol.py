"""DSL AST symbol node tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast.nodes.symbol` 的 symbol dialect AST 节点边界。
- 测试结构对应 `spec/dsl/ast/nodes/symbol.md` 与 `kernel_gen/dsl/ast/nodes/symbol.py`。

使用示例:
- pytest -q test/dsl/ast/nodes/test_symbol.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/nodes/symbol.py
- Spec 文档: spec/dsl/ast/nodes/symbol.md
- 测试文件: test/dsl/ast/nodes/test_symbol.py
"""

from __future__ import annotations

import importlib
import random

import pytest
from xdsl.context import Context
from xdsl.dialects.builtin import i1
from xdsl.dialects.test import TestOp as _TestOp
from xdsl.ir import Attribute
from xdsl.ir import Block, Operation, SSAValue

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.symbol import SymbolIterType, SymbolValueType
from kernel_gen.dsl.ast.nodes.attr import FloatTypeAttrAST, IntTypeAttrAST, ListAST, PythonObjectAttrAST, TupleAST
from kernel_gen.dsl.ast.nodes.basic import MemoryAST, ValueAST
from kernel_gen.dsl.ast.nodes.symbol import (
    ConstValueAST,
    SymbolAddAST,
    SymbolDimAST,
    SymbolEqAST,
    SymbolFloorDivAST,
    SymbolGeAST,
    SymbolGtAST,
    SymbolLeAST,
    SymbolListAST,
    SymbolLtAST,
    SymbolMinAST,
    SymbolMulAST,
    SymbolNeAST,
    SymbolSubAST,
    SymbolToFloatAST,
    SymbolTrueDivAST,
    TensorAxisAccessAST,
)
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


class DetachedSymbolValueAST(ValueAST):
    """测试公开 ValueAST 合同时返回未挂接 symbol op 的节点。"""

    def __init__(self, value: int) -> None:
        self.value = value

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> Operation:
        """返回未挂接 symbol 常量 op，验证调用方按公开 emit 合同接入。"""

        _ = block
        emitted = ConstValueAST(self.value).emit_mlir(ctx, None)
        assert isinstance(emitted, Operation)
        return emitted


class DetachedSymbolTypedValueAST(ValueAST):
    """测试公开 ValueAST 合同时返回指定 symbol 类型 SSA 的节点。"""

    def __init__(self, result_type: Attribute) -> None:
        self.result_type = result_type

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> Operation:
        """返回指定 result type 的 xDSL 测试 op。"""

        _ = (ctx, block)
        return _TestOp(result_types=[self.result_type])


class RawEmitAST(ValueAST):
    """测试公开 ValueAST 合同时返回非法 emit 结果的节点。"""

    def __init__(self, value: int | str | None) -> None:
        self.value = value

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> int | str | None:
        """返回原始值，用于验证公开 emit 边界的错误语义。"""

        _ = (ctx, block)
        return self.value


def test_symbol_nodes_live_in_symbol_module() -> None:
    """symbol.py 承载 symbol dialect AST 节点公开定义。"""

    symbol_module = importlib.import_module("kernel_gen.dsl.ast.nodes.symbol")
    basic_module = importlib.import_module("kernel_gen.dsl.ast.nodes.basic")

    assert symbol_module.SymbolAddAST is SymbolAddAST
    assert symbol_module.SymbolMinAST is SymbolMinAST
    assert symbol_module.SymbolDimAST is SymbolDimAST
    assert not hasattr(basic_module, "SymbolAddAST")
    assert not hasattr(basic_module, "SymbolDimAST")
    assert not hasattr(symbol_module, "ForAST")


def test_symbol_binary_and_list_expose_result_symbol_semantics() -> None:
    """Symbol 节点通过 result_symbol/result_symbols 暴露解析期符号语义。"""

    runtime_symbol = SymbolDim("N")
    lhs = SymbolDimAST("n", runtime_symbol=runtime_symbol)
    rhs = ConstValueAST(2)
    expr = SymbolAddAST(lhs, rhs)
    tail = SymbolMinAST(lhs, rhs)
    shape = SymbolListAST([lhs, rhs, expr, tail])

    assert lhs.result_symbol() == runtime_symbol
    assert rhs.result_symbol() == 2
    assert expr.result_symbol() == runtime_symbol + 2
    assert str(tail.result_symbol().get_value()) == "min(2, N)"
    assert shape.result_symbols() == [runtime_symbol, 2, runtime_symbol + 2, tail.result_symbol()]


@pytest.mark.parametrize(
    ("node_type", "expected"),
    random.Random(20260503).sample(
        [
            (SymbolAddAST, SymbolDim("N") + SymbolDim(3)),
            (SymbolSubAST, SymbolDim("N") - SymbolDim(3)),
            (SymbolMulAST, SymbolDim("N") * SymbolDim(3)),
            (SymbolTrueDivAST, SymbolDim("N") / SymbolDim(3)),
            (SymbolFloorDivAST, SymbolDim("N") // SymbolDim(3)),
        ],
        5,
    ),
)
def test_symbol_binary_nodes_expose_parameterized_result_symbols(node_type: type, expected: SymbolDim) -> None:
    """确定性随机遍历公开 symbol 二元节点，锁定解析期符号语义。"""

    lhs = SymbolDimAST("N")
    rhs = ConstValueAST(3)

    result = node_type(lhs, rhs).result_symbol()

    assert result == expected


def test_symbol_scalar_and_list_boundaries_use_public_result_methods() -> None:
    """常量、列表和 memory axis 节点通过公开 result_* 方法暴露稳定语义。"""

    assert ConstValueAST(True).result_symbol() is None
    assert ConstValueAST(True).result_scalar() is True
    assert ConstValueAST(1.5).result_symbol() is None
    assert ConstValueAST("token").result_scalar() == "token"
    assert SymbolListAST([ConstValueAST(1.5)]).result_symbols() is None

    memory = Memory(["M", 8], NumericType.Float32, space=MemorySpace.SM, stride=["S", 1])
    memory_ast = MemoryAST.from_memory("x", memory)
    shape_access = TensorAxisAccessAST(memory_ast, PythonObjectAttrAST("shape"), ConstValueAST(0))
    stride_access = TensorAxisAccessAST(memory_ast, PythonObjectAttrAST("stride"), ConstValueAST(1))
    bad_axis = TensorAxisAccessAST(memory_ast, PythonObjectAttrAST("shape"), ConstValueAST(4))

    assert shape_access.result_symbol() == SymbolDim("M")
    assert stride_access.result_symbol() == 1
    assert bad_axis.result_symbol() is None


@pytest.mark.parametrize(
    "compare_type",
    random.Random(20260504).sample(
        [SymbolEqAST, SymbolNeAST, SymbolLtAST, SymbolLeAST, SymbolGtAST, SymbolGeAST],
        6,
    ),
)
def test_symbol_compare_nodes_emit_public_mlir(compare_type: type) -> None:
    """公开 symbol 比较节点可经 emit_mlir 生成 SSA 结果。"""

    ctx = Context()
    block = Block()

    result = compare_type(ConstValueAST(1), ConstValueAST(2)).emit_mlir(ctx, block)

    assert isinstance(result, SSAValue)


def test_symbol_public_emit_mlir_success_and_error_boundaries() -> None:
    """公开 emit_mlir 覆盖 int/bool/float/symbol-to-float 与稳定错误语义。"""

    ctx = Context()
    block = Block()

    assert isinstance(ConstValueAST(True).emit_mlir(ctx, block), SSAValue)
    assert isinstance(ConstValueAST(4).emit_mlir(ctx, block), SSAValue)
    assert isinstance(ConstValueAST(1.25).emit_mlir(ctx, block), SSAValue)
    assert isinstance(SymbolDimAST(7).emit_mlir(ctx, block), SSAValue)
    assert isinstance(SymbolAddAST(ConstValueAST(1), ConstValueAST(2)).emit_mlir(ctx, block), SSAValue)
    assert isinstance(SymbolToFloatAST(ConstValueAST(3)).emit_mlir(ctx, block), SSAValue)

    with pytest.raises(KernelCodeError, match="Unsupported constant type"):
        ConstValueAST("bad").emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="Unbound symbol dimension"):
        SymbolDimAST("UNBOUND").emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="SymbolListAST item must be ValueAST, int or SymbolDim"):
        SymbolListAST([1.25])
    with pytest.raises(KernelCodeError, match="symbol.to_float source must have type symbol.int"):
        SymbolToFloatAST(ConstValueAST(1.25)).emit_mlir(ctx, block)


def test_symbol_public_emit_mlir_reuses_bound_symbols_and_detached_constants() -> None:
    """公开 emit_mlir 复用已绑定 symbol SSA，并支持 detached 常量 op。"""

    ctx = Context()
    block = Block(arg_types=[SymbolValueType.from_expr("N")])
    block.args[0].name_hint = "N"

    assert SymbolDimAST("N").emit_mlir(ctx, block) is block.args[0]
    assert SymbolDimAST("N").name == "N"

    result = ConstValueAST(5).emit_mlir(ctx, block)
    assert isinstance(result, SSAValue)
    result.name_hint = "K"
    assert SymbolDimAST("K").emit_mlir(ctx, block) is result

    assert isinstance(ConstValueAST(True).emit_mlir(ctx, None), Operation)
    assert isinstance(ConstValueAST(4).emit_mlir(ctx, None), Operation)
    assert isinstance(ConstValueAST(1.25).emit_mlir(ctx, None), Operation)
    assert ConstValueAST(IntTypeAttrAST(32), 7).result_symbol() == 7
    assert ConstValueAST(FloatTypeAttrAST(NumericType.Float32), 1.5).result_scalar() == 1.5
    assert ConstValueAST(0, 6).result_symbol() == 6


def test_symbol_list_public_emit_mlir_and_normalization_edges() -> None:
    """SymbolListAST 通过公开列表/元组和值节点发射 symbol SSA 列表。"""

    ctx = Context()
    block = Block()
    list_node = SymbolListAST(ListAST([ConstValueAST(1), SymbolDimAST(2)]))
    tuple_node = SymbolListAST(TupleAST((ConstValueAST(3),)))
    detached_node = SymbolListAST([DetachedSymbolValueAST(4)])

    assert list_node.items is list_node.values
    assert len(list_node.emit_mlir(ctx, block)) == 2
    assert len(tuple_node.emit_mlir(ctx, block)) == 1
    assert len(detached_node.emit_mlir(ctx, block)) == 1

    with pytest.raises(KernelCodeError, match="symbol list item must lower to symbol value"):
        SymbolListAST([ConstValueAST(True)]).emit_mlir(ctx, Block())


def test_symbol_tensor_axis_emit_public_shape_stride_and_errors() -> None:
    """TensorAxisAccessAST 按公开 memory SSA 发射 shape/stride 查询并报告边界错误。"""

    memory = Memory(["M", 8], NumericType.Float32, space=MemorySpace.GM, stride=["S", 1])
    memory_ast = MemoryAST.from_memory("x", memory)
    ctx = Context()
    block = Block(arg_types=[memory_ast.to_mlir_type(ctx)])
    block.args[0].name_hint = "x"

    shape_result = TensorAxisAccessAST(memory_ast, "shape", 0).emit_mlir(ctx, block)
    stride_result = TensorAxisAccessAST(memory_ast, "stride", 0).emit_mlir(ctx, block)

    assert isinstance(shape_result, SSAValue)
    assert isinstance(stride_result, SSAValue)
    assert [op.name for op in block.ops] == ["symbol.get_dim", "symbol.get_stride"]
    assert TensorAxisAccessAST(memory_ast, "shape", 1.5).result_symbol() is None
    assert TensorAxisAccessAST(memory_ast, "offset", 0).result_symbol() is None

    with pytest.raises(KernelCodeError, match="tensor axis must be a static integer"):
        TensorAxisAccessAST(memory_ast, "shape", 1.5).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="tensor axis out of range"):
        TensorAxisAccessAST(memory_ast, "shape", 4).emit_mlir(ctx, block)
    with pytest.raises(KernelCodeError, match="Unsupported tensor axis access"):
        TensorAxisAccessAST(memory_ast, "offset", 0).emit_mlir(ctx, block)

    wrong_type_block = Block(arg_types=[SymbolValueType.from_expr("x")])
    wrong_type_block.args[0].name_hint = "x"
    with pytest.raises(KernelCodeError, match="tensor axis source must be nn.memory"):
        TensorAxisAccessAST(memory_ast, "shape", 0).emit_mlir(ctx, wrong_type_block)


@pytest.mark.parametrize(
    ("node_type", "expected_op"),
    [
        (SymbolAddAST, "symbol.add"),
        (SymbolSubAST, "symbol.sub"),
        (SymbolMulAST, "symbol.mul"),
        (SymbolTrueDivAST, "symbol.div"),
        (SymbolFloorDivAST, "symbol.floordiv"),
    ],
)
def test_symbol_binary_public_emit_mlir_matrix_and_errors(node_type: type, expected_op: str) -> None:
    """公开 symbol 二元节点发射对应 op，并对非法公开操作数给出稳定错误。"""

    ctx = Context()
    block = Block()

    result = node_type(DetachedSymbolValueAST(8), DetachedSymbolValueAST(2)).emit_mlir(ctx, block)

    assert isinstance(result, SSAValue)
    assert block.last_op is not None
    assert block.last_op.name == expected_op
    assert node_type(ConstValueAST(1.5), ConstValueAST(2)).result_symbol() is None

    with pytest.raises(KernelCodeError, match=r"symbol operands must have !symbol\.int or !symbol\.iter type"):
        node_type(ConstValueAST(True), ConstValueAST(2)).emit_mlir(ctx, Block())


def test_symbol_binary_public_emit_mlir_propagates_unknown_for_unknown_and_iter_operands() -> None:
    """symbol 二元 AST 对 `?` 和 `symbol.iter` operand 发射 unknown result。"""

    ctx = Context()
    block = Block()

    unknown_result = SymbolAddAST(
        DetachedSymbolTypedValueAST(SymbolValueType.from_expr("?")),
        ConstValueAST(2),
    ).emit_mlir(ctx, block)
    iter_result = SymbolSubAST(
        ConstValueAST(2),
        DetachedSymbolTypedValueAST(SymbolIterType.from_bounds("0", "N", "1")),
    ).emit_mlir(ctx, block)

    assert isinstance(unknown_result, SSAValue)
    assert isinstance(iter_result, SSAValue)
    assert unknown_result.type == SymbolValueType.from_expr("?")
    assert iter_result.type == SymbolValueType.from_expr("?")
    assert "2 - " not in str(iter_result.type)


def test_symbol_compare_public_emit_mlir_keeps_i1_for_iter_operand() -> None:
    """symbol compare AST 对 `symbol.iter` operand 仍发射 `i1` 结果。"""

    ctx = Context()
    block = Block()

    result = SymbolLtAST(
        DetachedSymbolTypedValueAST(SymbolIterType.from_bounds("0", "N", "1")),
        ConstValueAST(2),
    ).emit_mlir(ctx, block)

    assert isinstance(result, SSAValue)
    assert result.type == i1


def test_symbol_to_float_and_compare_public_emit_error_edges() -> None:
    """symbol.to_float 与比较节点只接受可发射为 SSA 的公开 ValueAST 结果。"""

    ctx = Context()
    block = Block()

    assert isinstance(SymbolToFloatAST(DetachedSymbolValueAST(3)).emit_mlir(ctx, block), SSAValue)
    assert isinstance(SymbolEqAST(DetachedSymbolValueAST(1), DetachedSymbolValueAST(2)).emit_mlir(ctx, block), SSAValue)

    with pytest.raises(KernelCodeError, match="symbol.to_float source must lower to SSA value"):
        SymbolToFloatAST(RawEmitAST("bad")).emit_mlir(ctx, Block())
    with pytest.raises(KernelCodeError, match="symbol compare operands must lower to SSA values"):
        SymbolEqAST(RawEmitAST(None), ConstValueAST(2)).emit_mlir(ctx, Block())
