"""symbol-loop-hoist pass.

创建者: 朽木露琪亚
最后一次更改: 金铲铲大作战

功能说明:
- 作为 `ModulePass` 实现 `symbol-loop-hoist` pass，仅处理 `symbol.for`；当 module 中不存在
  `symbol.for` 时保持 no-op。
- 把循环体内仅依赖循环外 SSA 的受支持 symbol/tuner op 外提到 `symbol.for` 之前，减少循环体内重复
  的符号常量、参数与元信息计算。
- 通过 `PatternRewriteWalker` 以单 op pattern 驱动外提到稳定态，不做通用 LICM。

使用示例:
- from xdsl.context import Context
- from xdsl.dialects.builtin import ModuleOp
- from kernel_gen.passes.symbol_loop_hoist import SymbolLoopHoistPass
- module = ModuleOp([])
- SymbolLoopHoistPass().apply(Context(), module)
- # 兼容旧调用方仍可使用 SymbolLoopHoistPass().run(module)

关联文件:
- spec: spec/pass/symbol_loop_hoist.md
- test: test/pass/test_symbol_loop_hoist.py
- 功能实现: kernel_gen/passes/symbol_loop_hoist.py
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Block, BlockArgument, Operation, SSAValue
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriteWalker,
    PatternRewriter,
    RewritePattern,
    op_type_rewrite_pattern,
)
from xdsl.rewriter import InsertPoint
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolConstOp,
    SymbolFloorDivOp,
    SymbolForOp,
    SymbolGetDimOp,
    SymbolGetStrideOp,
    SymbolMulOp,
    SymbolSubOp,
    SymbolDivOp,
)
from kernel_gen.dialect.tuner import TunerParamOp
from kernel_gen.passes.pass_manager import Pass


class SymbolLoopHoistError(ValueError):
    """symbol-loop-hoist pass 的显式错误。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 统一承载 `SymbolLoopHoist*` 关键短语错误，便于测试稳定匹配。

    使用示例:
    - raise SymbolLoopHoistError("SymbolLoopHoistVerifierError: ...")

    关联文件:
    - spec: spec/pass/symbol_loop_hoist.md
    - test: test/pass/test_symbol_loop_hoist.py
    - 功能实现: kernel_gen/passes/symbol_loop_hoist.py
    """

class SymbolConstHoistPattern(RewritePattern):
    """`symbol.const` 外提 pattern。"""

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: SymbolConstOp, rewriter: PatternRewriter, /) -> None:
        loop_block = getattr(op, "parent_block", lambda: None)()
        if loop_block is None:
            return
        symbol_for = getattr(loop_block, "parent_op", lambda: None)()
        if not isinstance(symbol_for, SymbolForOp):
            return
        for operand in op.operands:
            value = SSAValue.get(operand)
            if isinstance(value, BlockArgument):
                if value.owner is loop_block:
                    return
                continue
            owner = getattr(value, "owner", None)
            if owner is None:
                continue
            if getattr(owner, "parent_block", lambda: None)() is loop_block:
                return
        op.detach()
        rewriter.insert_op(op, InsertPoint.before(symbol_for))
        rewriter.notify_op_modified(symbol_for)


class TunerParamHoistPattern(RewritePattern):
    """`tuner.param` 外提 pattern。"""

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: TunerParamOp, rewriter: PatternRewriter, /) -> None:
        loop_block = getattr(op, "parent_block", lambda: None)()
        if loop_block is None:
            return
        symbol_for = getattr(loop_block, "parent_op", lambda: None)()
        if not isinstance(symbol_for, SymbolForOp):
            return
        for operand in op.operands:
            value = SSAValue.get(operand)
            if isinstance(value, BlockArgument):
                if value.owner is loop_block:
                    return
                continue
            owner = getattr(value, "owner", None)
            if owner is None:
                continue
            if getattr(owner, "parent_block", lambda: None)() is loop_block:
                return
        op.detach()
        rewriter.insert_op(op, InsertPoint.before(symbol_for))
        rewriter.notify_op_modified(symbol_for)


class SymbolGetDimHoistPattern(RewritePattern):
    """`symbol.get_dim` 外提 pattern。"""

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: SymbolGetDimOp, rewriter: PatternRewriter, /) -> None:
        loop_block = getattr(op, "parent_block", lambda: None)()
        if loop_block is None:
            return
        symbol_for = getattr(loop_block, "parent_op", lambda: None)()
        if not isinstance(symbol_for, SymbolForOp):
            return
        for operand in op.operands:
            value = SSAValue.get(operand)
            if isinstance(value, BlockArgument):
                if value.owner is loop_block:
                    return
                continue
            owner = getattr(value, "owner", None)
            if owner is None:
                continue
            if getattr(owner, "parent_block", lambda: None)() is loop_block:
                return
        op.detach()
        rewriter.insert_op(op, InsertPoint.before(symbol_for))
        rewriter.notify_op_modified(symbol_for)


class SymbolGetStrideHoistPattern(RewritePattern):
    """`symbol.get_stride` 外提 pattern。"""

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: SymbolGetStrideOp, rewriter: PatternRewriter, /) -> None:
        loop_block = getattr(op, "parent_block", lambda: None)()
        if loop_block is None:
            return
        symbol_for = getattr(loop_block, "parent_op", lambda: None)()
        if not isinstance(symbol_for, SymbolForOp):
            return
        for operand in op.operands:
            value = SSAValue.get(operand)
            if isinstance(value, BlockArgument):
                if value.owner is loop_block:
                    return
                continue
            owner = getattr(value, "owner", None)
            if owner is None:
                continue
            if getattr(owner, "parent_block", lambda: None)() is loop_block:
                return
        op.detach()
        rewriter.insert_op(op, InsertPoint.before(symbol_for))
        rewriter.notify_op_modified(symbol_for)


class SymbolAddHoistPattern(RewritePattern):
    """`symbol.add` 外提 pattern。"""

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: SymbolAddOp, rewriter: PatternRewriter, /) -> None:
        loop_block = getattr(op, "parent_block", lambda: None)()
        if loop_block is None:
            return
        symbol_for = getattr(loop_block, "parent_op", lambda: None)()
        if not isinstance(symbol_for, SymbolForOp):
            return
        for operand in op.operands:
            value = SSAValue.get(operand)
            if isinstance(value, BlockArgument):
                if value.owner is loop_block:
                    return
                continue
            owner = getattr(value, "owner", None)
            if owner is None:
                continue
            if getattr(owner, "parent_block", lambda: None)() is loop_block:
                return
        op.detach()
        rewriter.insert_op(op, InsertPoint.before(symbol_for))
        rewriter.notify_op_modified(symbol_for)


class SymbolSubHoistPattern(RewritePattern):
    """`symbol.sub` 外提 pattern。"""

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: SymbolSubOp, rewriter: PatternRewriter, /) -> None:
        loop_block = getattr(op, "parent_block", lambda: None)()
        if loop_block is None:
            return
        symbol_for = getattr(loop_block, "parent_op", lambda: None)()
        if not isinstance(symbol_for, SymbolForOp):
            return
        for operand in op.operands:
            value = SSAValue.get(operand)
            if isinstance(value, BlockArgument):
                if value.owner is loop_block:
                    return
                continue
            owner = getattr(value, "owner", None)
            if owner is None:
                continue
            if getattr(owner, "parent_block", lambda: None)() is loop_block:
                return
        op.detach()
        rewriter.insert_op(op, InsertPoint.before(symbol_for))
        rewriter.notify_op_modified(symbol_for)


class SymbolMulHoistPattern(RewritePattern):
    """`symbol.mul` 外提 pattern。"""

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: SymbolMulOp, rewriter: PatternRewriter, /) -> None:
        loop_block = getattr(op, "parent_block", lambda: None)()
        if loop_block is None:
            return
        symbol_for = getattr(loop_block, "parent_op", lambda: None)()
        if not isinstance(symbol_for, SymbolForOp):
            return
        for operand in op.operands:
            value = SSAValue.get(operand)
            if isinstance(value, BlockArgument):
                if value.owner is loop_block:
                    return
                continue
            owner = getattr(value, "owner", None)
            if owner is None:
                continue
            if getattr(owner, "parent_block", lambda: None)() is loop_block:
                return
        op.detach()
        rewriter.insert_op(op, InsertPoint.before(symbol_for))
        rewriter.notify_op_modified(symbol_for)


class SymbolDivHoistPattern(RewritePattern):
    """`symbol.div` 外提 pattern。"""

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: SymbolDivOp, rewriter: PatternRewriter, /) -> None:
        loop_block = getattr(op, "parent_block", lambda: None)()
        if loop_block is None:
            return
        symbol_for = getattr(loop_block, "parent_op", lambda: None)()
        if not isinstance(symbol_for, SymbolForOp):
            return
        for operand in op.operands:
            value = SSAValue.get(operand)
            if isinstance(value, BlockArgument):
                if value.owner is loop_block:
                    return
                continue
            owner = getattr(value, "owner", None)
            if owner is None:
                continue
            if getattr(owner, "parent_block", lambda: None)() is loop_block:
                return
        op.detach()
        rewriter.insert_op(op, InsertPoint.before(symbol_for))
        rewriter.notify_op_modified(symbol_for)


class SymbolFloorDivHoistPattern(RewritePattern):
    """`symbol.floordiv` 外提 pattern。"""

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: SymbolFloorDivOp, rewriter: PatternRewriter, /) -> None:
        loop_block = getattr(op, "parent_block", lambda: None)()
        if loop_block is None:
            return
        symbol_for = getattr(loop_block, "parent_op", lambda: None)()
        if not isinstance(symbol_for, SymbolForOp):
            return
        for operand in op.operands:
            value = SSAValue.get(operand)
            if isinstance(value, BlockArgument):
                if value.owner is loop_block:
                    return
                continue
            owner = getattr(value, "owner", None)
            if owner is None:
                continue
            if getattr(owner, "parent_block", lambda: None)() is loop_block:
                return
        op.detach()
        rewriter.insert_op(op, InsertPoint.before(symbol_for))
        rewriter.notify_op_modified(symbol_for)


def get_symbol_loop_hoist_patterns() -> list[RewritePattern]:
    """返回 `symbol-loop-hoist` pass 使用的公开 pattern 列表。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 以“每种受支持 op 一个 pattern”的形式公开当前 pass 的 pattern 列表。
    - 当前只覆盖 `symbol.const`、`tuner.param`、`symbol.get_dim/get_stride` 与
      `symbol.add/sub/mul/div/floordiv`。

    使用示例:
    - `patterns = get_symbol_loop_hoist_patterns()`

    关联文件:
    - spec: spec/pass/symbol_loop_hoist.md
    - test: test/pass/test_symbol_loop_hoist.py
    - 功能实现: kernel_gen/passes/symbol_loop_hoist.py
    """

    return [
        SymbolConstHoistPattern(),
        TunerParamHoistPattern(),
        SymbolGetDimHoistPattern(),
        SymbolGetStrideHoistPattern(),
        SymbolAddHoistPattern(),
        SymbolSubHoistPattern(),
        SymbolMulHoistPattern(),
        SymbolDivHoistPattern(),
        SymbolFloorDivHoistPattern(),
    ]


class SymbolLoopHoistPass(Pass, ModulePass):
    """symbol-loop-hoist pass。

    创建者: 朽木露琪亚
    最后一次更改: 金铲铲大作战

    功能说明:
    - 作为 `ModulePass` 通过 pattern 驱动遍历 module 中的 `symbol.for` 并外提循环 invariant 的对象。
    - 若 module 中不存在 `symbol.for`，则直接 no-op 并通过 `module.verify()`。
    - 在最终 `module.verify()` 失败时统一转译为 `SymbolLoopHoistVerifierError`。

    使用示例:
    - from xdsl.context import Context
    - module = ModuleOp([])
    - SymbolLoopHoistPass().apply(Context(), module)

    关联文件:
    - spec: spec/pass/symbol_loop_hoist.md
    - test: test/pass/test_symbol_loop_hoist.py
    - 功能实现: kernel_gen/passes/symbol_loop_hoist.py
    """

    name = "symbol-loop-hoist"

    def apply(self: "SymbolLoopHoistPass", ctx: Context, module: ModuleOp) -> None:
        """执行 symbol-loop-hoist ModulePass。

        创建者: 朽木露琪亚
        最后一次更改: 金铲铲大作战

        功能说明:
        - 通过 `PatternRewriteWalker` 以单 op pattern 驱动 `symbol.for` 外提。
        - 依赖 greedy walker 把链式候选推进到稳定态。
        - 在最终 `module.verify()` 失败时统一转译为 `SymbolLoopHoistVerifierError`。

        使用示例:
        - from xdsl.context import Context
        - from xdsl.dialects.builtin import ModuleOp
        - module = ModuleOp([])
        - SymbolLoopHoistPass().apply(Context(), module)

        关联文件:
        - spec: spec/pass/symbol_loop_hoist.md
        - test: test/pass/test_symbol_loop_hoist.py
        - 功能实现: kernel_gen/passes/symbol_loop_hoist.py
        """

        PatternRewriteWalker(
            GreedyRewritePatternApplier(
                get_symbol_loop_hoist_patterns(),
                ctx=ctx,
                dce_enabled=False,
            )
        ).rewrite_module(module)
        try:
            module.verify()
        except VerifyException as exc:
            raise SymbolLoopHoistError(f"SymbolLoopHoistVerifierError: {exc}") from exc

    def run(self: "SymbolLoopHoistPass", module: ModuleOp) -> ModuleOp:
        """兼容旧 Pass 接口的执行入口。

        创建者: 朽木露琪亚
        最后一次更改: 朽木露琪亚

        功能说明:
        - 保持旧 `run(module)` 调用方可继续工作。
        - 内部直接复用 `apply(Context(), module)`。

        使用示例:
- from xdsl.dialects.builtin import ModuleOp
- module = ModuleOp([])
- SymbolLoopHoistPass().run(module)

        关联文件:
        - spec: spec/pass/symbol_loop_hoist.md
        - test: test/pass/test_symbol_loop_hoist.py
        - 功能实现: kernel_gen/passes/symbol_loop_hoist.py
        """

        self.apply(Context(), module)
        return module

__all__ = [
    "SymbolLoopHoistError",
    "SymbolLoopHoistPass",
    "SymbolConstHoistPattern",
    "TunerParamHoistPattern",
    "SymbolGetDimHoistPattern",
    "SymbolGetStrideHoistPattern",
    "SymbolAddHoistPattern",
    "SymbolSubHoistPattern",
    "SymbolMulHoistPattern",
    "SymbolDivHoistPattern",
    "SymbolFloorDivHoistPattern",
    "get_symbol_loop_hoist_patterns",
]
