"""DSL AST control-flow node definitions.


功能说明:
- 定义 DSL AST 控制流节点。
- `ForAST` 发射为 `symbol.for`，`IfAST` 发射为 `scf.if`。
- 控制流节点独立于 `basic.py` 和 `symbol.py`，避免基础节点或 symbol 值节点文件混入控制流实现。

API 列表:
- `ForAST(var: SymbolDimAST, start: ValueAST, end: ValueAST, body: BlockAST, step: ValueAST | None = None, location: SourceLocation | None = None)`
- `IfAST(condition: ValueAST, true_body: BlockAST, false_body: BlockAST | None = None, location: SourceLocation | None = None)`

使用示例:
- from kernel_gen.dsl.ast.nodes.control_flow import ForAST, IfAST
- loop = ForAST(SymbolDimAST("i"), ConstValueAST(0), ConstValueAST(4), BlockAST([]))

关联文件:
- spec: spec/dsl/ast/nodes/control_flow.md
- test: test/dsl/ast/nodes/test_control_flow.py
- 功能实现: kernel_gen/dsl/ast/nodes/control_flow.py
"""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects import scf
from xdsl.dialects.builtin import i1
from xdsl.ir import Block, Operation, Region, SSAValue

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.symbol import SymbolForOp, SymbolIterType, SymbolValueType

from .attr import EmitMlirResult, SourceLocation
from .basic import BlockAST, BoolValueAST, StatementAST, ValueAST
from .symbol import ConstValueAST, SymbolDimAST

__all__ = [
    "ForAST",
    "IfAST",
]


@dataclass
class ForAST(StatementAST):
    """循环节点。"""

    var: SymbolDimAST
    start: ValueAST
    end: ValueAST
    body: BlockAST
    step: ValueAST | None = None
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.var, SymbolDimAST):
            self.var = SymbolDimAST(self.var, self.location)
        if not isinstance(self.start, ValueAST):
            self.start = ConstValueAST(self.start, location=self.location)
        if not isinstance(self.end, ValueAST):
            self.end = ConstValueAST(self.end, location=self.location)
        if self.step is not None and not isinstance(self.step, ValueAST):
            self.step = ConstValueAST(self.step, location=self.location)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将循环节点发射为 `symbol.for`。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 发射 start/end/step 为 `!symbol.int` SSA value。
        - 构造 `symbol.for` body block，并递归发射 `body`。

        使用示例:
        - loop.emit_mlir(ctx, block)
        """

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        start = self.start.emit_mlir(ctx, block)
        if isinstance(start, Operation):
            block.add_op(start)
            start = start.results[0]
        end = self.end.emit_mlir(ctx, block)
        if isinstance(end, Operation):
            block.add_op(end)
            end = end.results[0]
        step_source = self.step if self.step is not None else ConstValueAST(1)
        step = step_source.emit_mlir(ctx, block)
        if isinstance(step, Operation):
            block.add_op(step)
            step = step.results[0]
        if not isinstance(start, SSAValue) or not isinstance(end, SSAValue) or not isinstance(step, SSAValue):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "for bounds must lower to SSA values")
        if not isinstance(start.type, SymbolValueType) or not isinstance(end.type, SymbolValueType) or not isinstance(step.type, SymbolValueType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "for bounds must be symbol.int")
        if step.type.expr.expr.data == "0":
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "for range step must not be zero")
        iter_type = SymbolIterType.from_bounds(start.type.expr.expr.data, end.type.expr.expr.data, step.type.expr.expr.data)
        body_block = Block(arg_types=[iter_type])
        body_block.args[0].name_hint = self.var.name
        loop_op = SymbolForOp(start, end, step, body_block)
        block.add_op(loop_op)
        self.body.emit_mlir(ctx, body_block)
        body_block.args[0].name_hint = None
        return None


@dataclass
class IfAST(StatementAST):
    """条件分支节点。"""

    condition: ValueAST
    true_body: BlockAST
    false_body: BlockAST | None = None
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.condition, ValueAST):
            self.condition = BoolValueAST(bool(self.condition), self.location)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将条件节点发射为 `scf.if`。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 发射 condition 为 `i1` SSA value。
        - 构造 true region，并在存在 false_body 时构造 false region。

        使用示例:
        - branch.emit_mlir(ctx, block)
        """

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        condition = self.condition.emit_mlir(ctx, block)
        if isinstance(condition, Operation):
            block.add_op(condition)
            condition = condition.results[0]
        if not isinstance(condition, SSAValue):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "if condition must lower to SSA value")
        if condition.type != i1:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "if condition must be i1")
        true_block = Block()
        false_region: Region | None = None
        false_block: Block | None = None
        if self.false_body is not None:
            false_block = Block()
            false_region = Region(false_block)
        if_op = scf.IfOp(condition, [], Region(true_block), false_region)
        block.add_op(if_op)
        self.true_body.emit_mlir(ctx, true_block)
        if self.false_body is not None and false_block is not None:
            self.false_body.emit_mlir(ctx, false_block)
        return None
