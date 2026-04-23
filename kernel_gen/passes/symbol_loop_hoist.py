"""symbol-loop-hoist pass.

创建者: 朽木露琪亚
最后一次更改: 金铲铲大作战

功能说明:
- 作为 `ModulePass` 实现 `symbol-loop-hoist` pass，仅处理 `symbol.for`；当 module 中不存在
  `symbol.for` 时保持 no-op。
- 把循环体内仅依赖循环外 SSA 的对象外提到 `symbol.for` 之前，减少 split 后循环体内重复构造的符号查询、
  形状推导与可复用 buffer/视图描述。
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

from collections.abc import Iterable

from xdsl.context import Context
from xdsl.dialects import func
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

from kernel_gen.dialect.dma import (
    DmaAllocOp,
    DmaCopyOp,
    DmaDesliceOp,
    DmaFillOp,
    DmaFreeOp,
    DmaLoadOp,
    DmaReshapeOp,
    DmaSliceOp,
    DmaStoreOp,
    DmaViewOp,
)
from kernel_gen.dialect.kernel import _BaseKernelBinaryOp
from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolConstOp,
    SymbolDivOp,
    SymbolEqOp,
    SymbolFloorDivOp,
    SymbolGeOp,
    SymbolGetDimOp,
    SymbolGetStrideOp,
    SymbolGtOp,
    SymbolLeOp,
    SymbolLtOp,
    SymbolMulOp,
    SymbolNeOp,
    SymbolSubOp,
    SymbolToFloatOp,
    SymbolToIntOp,
    SymbolForOp,
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
    - raise SymbolLoopHoistError("SymbolLoopHoistSideEffectOp: ...")

    关联文件:
    - spec: spec/pass/symbol_loop_hoist.md
    - test: test/pass/test_symbol_loop_hoist.py
    - 功能实现: kernel_gen/passes/symbol_loop_hoist.py
    """


def _raise_symbol_loop_hoist_error(keyword: str, detail: str) -> None:
    raise SymbolLoopHoistError(f"{keyword}: {detail}")


_SYMBOL_PURE_OPS: tuple[type[Operation], ...] = (
    TunerParamOp,
    SymbolConstOp,
    SymbolGetDimOp,
    SymbolGetStrideOp,
    SymbolAddOp,
    SymbolSubOp,
    SymbolMulOp,
    SymbolDivOp,
    SymbolFloorDivOp,
    SymbolEqOp,
    SymbolNeOp,
    SymbolLtOp,
    SymbolLeOp,
    SymbolGtOp,
    SymbolGeOp,
    SymbolToIntOp,
    SymbolToFloatOp,
)

_DMA_META_OPS: tuple[type[Operation], ...] = (
    DmaViewOp,
    DmaReshapeOp,
)

_DMA_FORBIDDEN_OPS: tuple[type[Operation], ...] = (
    DmaDesliceOp,
    DmaCopyOp,
    DmaStoreOp,
    DmaFillOp,
    DmaFreeOp,
)


def _parent_block(op: Operation) -> Block | None:
    return getattr(op, "parent_block", lambda: None)()


def _is_defined_in_block(value: SSAValue, block: Block) -> bool:
    if isinstance(value, BlockArgument):
        return value.owner is block
    owner = getattr(value, "owner", None)
    if owner is None:
        return False
    return _parent_block(owner) is block


def _iter_operand_values(op: Operation) -> Iterable[SSAValue]:
    for operand in op.operands:
        yield SSAValue.get(operand)


def _is_loop_invariant(op: Operation, loop_block: Block) -> bool:
    return all(not _is_defined_in_block(operand, loop_block) for operand in _iter_operand_values(op))


def _is_forbidden_side_effect_op(op: Operation) -> bool:
    return isinstance(op, _DMA_FORBIDDEN_OPS)


def _has_writing_use_in_block(value: SSAValue, block: Block, *, exclude_ops: set[Operation] | None = None) -> bool:
    exclude_ops = exclude_ops or set()
    for use in value.uses:
        user = use.operation
        if user in exclude_ops:
            continue
        if _parent_block(user) is not block:
            continue
        idx = use.index
        if isinstance(user, DmaSliceOp) and idx == 0:
            return True
        if isinstance(user, DmaDesliceOp) and idx == 1:
            return True
        if isinstance(user, DmaStoreOp) and idx == 1:
            return True
        if isinstance(user, DmaCopyOp) and idx == 1:
            return True
        if isinstance(user, DmaFillOp) and idx == 0:
            return True
        if isinstance(user, _BaseKernelBinaryOp) and idx == 2:
            return True
    return False


def _is_read_only_in_block(value: SSAValue, block: Block, *, exclude_ops: set[Operation] | None = None) -> bool:
    return not _has_writing_use_in_block(value, block, exclude_ops=exclude_ops)


def _maybe_hoist_fixed_read(
    op: Operation,
    *,
    loop_block: Block,
) -> None:
    if isinstance(op, DmaSliceOp):
        source = SSAValue.get(op.source)
        target = SSAValue.get(op.target)
        if not _is_read_only_in_block(source, loop_block):
            _raise_symbol_loop_hoist_error(
                "SymbolLoopHoistFixedReadSourceMutated",
                "fixed read requires source to remain read-only in symbol.for",
            )
        if not _is_read_only_in_block(target, loop_block, exclude_ops={op}):
            _raise_symbol_loop_hoist_error(
                "SymbolLoopHoistFixedReadResultRewritten",
                "fixed read requires slice target not to be rewritten in symbol.for",
            )
        return

    if isinstance(op, DmaLoadOp):
        source = SSAValue.get(op.source)
        result = SSAValue.get(op.result)
        if not _is_read_only_in_block(source, loop_block):
            _raise_symbol_loop_hoist_error(
                "SymbolLoopHoistFixedReadSourceMutated",
                "fixed read requires source to remain read-only in symbol.for",
            )
        if not _is_read_only_in_block(result, loop_block):
            _raise_symbol_loop_hoist_error(
                "SymbolLoopHoistFixedReadResultRewritten",
                "fixed read requires load result not to be rewritten in symbol.for",
            )
        return


def _is_free_in_loop(value: SSAValue, loop_block: Block) -> bool:
    for use in value.uses:
        user = use.operation
        if _parent_block(user) is not loop_block:
            continue
        if isinstance(user, DmaFreeOp):
            return True
    return False


def _next_hoist_candidate(symbol_for: SymbolForOp) -> Operation | None:
    """返回当前 `symbol.for` 下一条可外提候选。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 按 loop 体内当前顺序扫描候选 op。
    - 只返回一条可外提 op，供 pattern 驱动器反复应用直到稳定态。
    - 当候选违反固定失败边界时，直接抛出 `SymbolLoopHoistError`。

    使用示例:
    - candidate = _next_hoist_candidate(symbol_for)

    关联文件:
    - spec: spec/pass/symbol_loop_hoist.md
    - test: test/pass/test_symbol_loop_hoist.py
    - 功能实现: kernel_gen/passes/symbol_loop_hoist.py
    """

    blocks = list(symbol_for.body.blocks)
    if len(blocks) != 1:
        _raise_symbol_loop_hoist_error(
            "SymbolLoopHoistVerifierError",
            "symbol.for must have single-block body",
        )
    loop_block = blocks[0]
    outer_block = _parent_block(symbol_for)
    if outer_block is None:
        _raise_symbol_loop_hoist_error(
            "SymbolLoopHoistVerifierError",
            "symbol.for must be contained in a block",
        )

    for op in list(loop_block.ops):
        if isinstance(op, func.ReturnOp):
            continue
        if isinstance(op, SymbolForOp):
            continue
        if not _is_loop_invariant(op, loop_block):
            continue

        if _is_forbidden_side_effect_op(op):
            _raise_symbol_loop_hoist_error(
                "SymbolLoopHoistSideEffectOp",
                f"unsupported invariant op {op.name} inside symbol.for",
            )

        if isinstance(op, DmaAllocOp):
            result = SSAValue.get(op.result)
            if _is_free_in_loop(result, loop_block):
                _raise_symbol_loop_hoist_error(
                    "SymbolLoopHoistAllocLifetimeUnsafe",
                    "dma.alloc result is freed inside symbol.for",
                )
            return op

        if isinstance(op, _DMA_META_OPS) or isinstance(op, _SYMBOL_PURE_OPS):
            return op

        if isinstance(op, (DmaSliceOp, DmaLoadOp)):
            _maybe_hoist_fixed_read(op, loop_block=loop_block)
            return op

    return None


class _SymbolLoopHoistPattern(RewritePattern):
    """按单个 `symbol.for` 候选驱动 hoist。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 每次匹配只外提一条当前可用候选 op。
    - 依赖 `PatternRewriteWalker` 的 greedy 驱动，把同一 `symbol.for` 推进到稳定态。

    使用示例:
    - PatternRewriteWalker(
    -     GreedyRewritePatternApplier([_SymbolLoopHoistPattern()], ctx=ctx, dce_enabled=False)
    - ).rewrite_module(module)

    关联文件:
    - spec: spec/pass/symbol_loop_hoist.md
    - test: test/pass/test_symbol_loop_hoist.py
    - 功能实现: kernel_gen/passes/symbol_loop_hoist.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, symbol_for: SymbolForOp, rewriter: PatternRewriter, /) -> None:
        candidate = _next_hoist_candidate(symbol_for)
        if candidate is None:
            return
        candidate.detach()
        rewriter.insert_op(candidate, InsertPoint.before(symbol_for))
        rewriter.notify_op_modified(symbol_for)


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
                [_SymbolLoopHoistPattern()],
                ctx=ctx,
                dce_enabled=False,
            )
        ).rewrite_module(module)
        try:
            module.verify()
        except VerifyException as exc:
            _raise_symbol_loop_hoist_error("SymbolLoopHoistVerifierError", str(exc))

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


__all__ = ["SymbolLoopHoistError", "SymbolLoopHoistPass"]
