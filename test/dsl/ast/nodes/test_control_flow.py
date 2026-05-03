"""DSL AST control-flow node tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast.nodes.control_flow` 的公开节点归属与构造归一。
- 测试结构对应 `spec/dsl/ast/nodes/control_flow.md` 与 `kernel_gen/dsl/ast/nodes/control_flow.py`。

使用示例:
- pytest -q test/dsl/ast/nodes/test_control_flow.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/nodes/control_flow.py
- Spec 文档: spec/dsl/ast/nodes/control_flow.md
- 测试文件: test/dsl/ast/nodes/test_control_flow.py
"""

from __future__ import annotations

import importlib

import pytest
from xdsl.context import Context
from xdsl.dialects import arith, scf
from xdsl.dialects.builtin import i1
from xdsl.ir import Block, Operation

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolForOp
from kernel_gen.dsl.ast.nodes.basic import BlockAST, BoolValueAST, ValueAST
from kernel_gen.dsl.ast.nodes.control_flow import ForAST, IfAST
from kernel_gen.dsl.ast.nodes.symbol import ConstValueAST, SymbolDimAST


class _DetachedSymbolConstAST(ValueAST):
    """测试公开 ValueAST 合同中返回 unattached symbol operation 的路径。"""

    def __init__(self, value: int) -> None:
        self.value = value

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> SymbolConstOp:
        return SymbolConstOp(self.value)


class _DetachedBoolAST(ValueAST):
    """测试公开 ValueAST 合同中返回 unattached bool operation 的路径。"""

    def __init__(self, value: bool) -> None:
        self.value = value

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> Operation:
        return arith.ConstantOp.from_int_and_width(1 if self.value else 0, i1)


class _NoValueAST(ValueAST):
    """测试公开 ValueAST 合同中不产生 SSA value 的失败路径。"""

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> None:
        return None


def test_control_flow_nodes_live_in_control_flow_module() -> None:
    """控制流节点只由 control_flow.py 承载，同时保持包根导出。"""

    control_flow_module = importlib.import_module("kernel_gen.dsl.ast.nodes.control_flow")
    basic_module = importlib.import_module("kernel_gen.dsl.ast.nodes.basic")
    symbol_module = importlib.import_module("kernel_gen.dsl.ast.nodes.symbol")
    nodes_module = importlib.import_module("kernel_gen.dsl.ast.nodes")

    assert control_flow_module.ForAST is ForAST
    assert control_flow_module.IfAST is IfAST
    assert nodes_module.ForAST is ForAST
    assert nodes_module.IfAST is IfAST
    assert not hasattr(basic_module, "IfAST")
    assert not hasattr(symbol_module, "ForAST")


def test_for_ast_normalizes_bounds_and_default_step() -> None:
    """ForAST 把裸循环变量和整数边界归一为公开 AST 节点。"""

    body = BlockAST([])
    loop = ForAST("i", 0, 8, body)

    assert isinstance(loop.var, SymbolDimAST)
    assert loop.var.name == "i"
    assert isinstance(loop.start, ConstValueAST)
    assert loop.start.raw_value == 0
    assert isinstance(loop.end, ConstValueAST)
    assert loop.end.raw_value == 8
    assert loop.step is None
    assert loop.body is body


def test_if_ast_normalizes_python_bool_condition() -> None:
    """IfAST 把裸 Python bool 条件归一为 BoolValueAST。"""

    true_body = BlockAST([])
    false_body = BlockAST([])
    branch = IfAST(True, true_body, false_body)

    assert isinstance(branch.condition, BoolValueAST)
    assert branch.condition.raw_value is True
    assert branch.true_body is true_body
    assert branch.false_body is false_body


def test_for_ast_emits_symbol_for_public_bounds() -> None:
    """ForAST 通过公开 emit_mlir 发射 symbol.for 并清理循环变量临时名称。"""

    ctx = Context()
    block = Block()
    loop = ForAST("i", 0, 8, BlockAST([SymbolDimAST("i")]), step=2)

    assert loop.emit_mlir(ctx, block) is None

    loop_op = tuple(block.ops)[-1]
    assert isinstance(loop_op, SymbolForOp)
    assert loop_op.iter_attr.start.expr.data == "0"
    assert loop_op.iter_attr.end.expr.data == "8"
    assert loop_op.iter_attr.step.expr.data == "2"
    body_block = loop_op.body.blocks.first
    assert body_block is not None
    assert body_block.args[0].name_hint is None


def test_for_ast_rejects_invalid_public_bounds() -> None:
    """ForAST 对公开 value 节点发射出的非法循环边界稳定失败。"""

    ctx = Context()
    with pytest.raises(KernelCodeError, match="for range step must not be zero"):
        ForAST("i", 0, 8, BlockAST([]), step=0).emit_mlir(ctx, Block())

    with pytest.raises(KernelCodeError, match="for bounds must be symbol.int"):
        ForAST("i", BoolValueAST(True), 8, BlockAST([])).emit_mlir(ctx, Block())

    with pytest.raises(KernelCodeError, match="for bounds must lower to SSA values"):
        ForAST("i", _NoValueAST(), 8, BlockAST([])).emit_mlir(ctx, Block())


def test_for_ast_accepts_value_nodes_returning_operations() -> None:
    """ForAST 接受公开 ValueAST 合同返回的 unattached operation 边界。"""

    ctx = Context()
    block = Block()
    loop = ForAST(
        "i",
        _DetachedSymbolConstAST(1),
        _DetachedSymbolConstAST(9),
        BlockAST([]),
        step=_DetachedSymbolConstAST(4),
    )

    loop.emit_mlir(ctx, block)

    loop_op = tuple(block.ops)[-1]
    assert isinstance(loop_op, SymbolForOp)
    assert loop_op.iter_attr.start.expr.data == "1"
    assert loop_op.iter_attr.end.expr.data == "9"
    assert loop_op.iter_attr.step.expr.data == "4"


def test_if_ast_emits_scf_if_public_regions() -> None:
    """IfAST 通过公开 emit_mlir 发射 then/else 与无 else 两种 scf.if。"""

    ctx = Context()
    block = Block()
    IfAST(True, BlockAST([])).emit_mlir(ctx, block)
    IfAST(False, BlockAST([]), BlockAST([])).emit_mlir(ctx, block)

    first_if, second_if = tuple(block.ops)[1], tuple(block.ops)[3]
    assert isinstance(first_if, scf.IfOp)
    assert isinstance(second_if, scf.IfOp)
    assert len(tuple(first_if.false_region.blocks)) == 0
    assert len(tuple(second_if.false_region.blocks)) == 1


def test_if_ast_rejects_non_i1_public_condition() -> None:
    """IfAST 对公开 value 节点发射出的非 i1 条件稳定失败。"""

    with pytest.raises(KernelCodeError, match="if condition must be i1"):
        IfAST(ConstValueAST(1), BlockAST([])).emit_mlir(Context(), Block())

    with pytest.raises(KernelCodeError, match="if condition must lower to SSA value"):
        IfAST(_NoValueAST(), BlockAST([])).emit_mlir(Context(), Block())


def test_if_ast_accepts_value_nodes_returning_operations() -> None:
    """IfAST 接受公开 ValueAST 合同返回的 unattached operation 条件。"""

    block = Block()
    IfAST(_DetachedBoolAST(True), BlockAST([])).emit_mlir(Context(), block)

    assert isinstance(tuple(block.ops)[-1], scf.IfOp)
