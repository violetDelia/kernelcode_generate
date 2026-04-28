"""symbol-buffer-hoist pass.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 定义 `symbol-buffer-hoist` 的公开 pass、公开 pattern 与公开 pattern getter。
- 只在 `symbol.for` 单 block 循环体内识别 `dma.alloc`，并在 shape 明确不依赖 loop 内 SSA、
  且直接 use 仅属于输入 staging / output scratch 两类安全形态时，将其外提到所属
  `symbol.for` 之前。
- 失败边界统一复用 `KernelCodeError(module="pass")`；不新增专题专属错误类型，也不承诺额外 compat path。

API 列表:
- `class DmaAllocInSymbolForHoistPattern()`
- `DmaAllocInSymbolForHoistPattern.match_and_rewrite(op: DmaAllocOp, rewriter: PatternRewriter) -> None`
- `get_symbol_buffer_hoist_patterns() -> list[RewritePattern]`
- `class SymbolBufferHoistPass()`
- `SymbolBufferHoistPass.apply(ctx: Context, module: ModuleOp) -> None`
- `SymbolBufferHoistPass.run(module: ModuleOp) -> ModuleOp`

使用示例:
- from xdsl.context import Context
- from xdsl.dialects.builtin import ModuleOp
- from kernel_gen.passes.symbol_buffer_hoist import SymbolBufferHoistPass
- module = ModuleOp([])
- SymbolBufferHoistPass().apply(Context(), module)

关联文件:
- spec: spec/pass/symbol_buffer_hoist.md
- test: test/pass/test_symbol_buffer_hoist.py
- test: test/pass/test_pass_registry.py
- 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
"""

from __future__ import annotations
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

from collections.abc import Iterable

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Block, BlockArgument, SSAValue, Use
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)
from xdsl.rewriter import InsertPoint
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.dma import DmaAllocOp, DmaDesliceOp, DmaSliceOp
from kernel_gen.dialect.symbol import Symbol, SymbolForOp
from kernel_gen.passes.common import ensure_builtin_module
from kernel_gen.passes.pass_manager import Pass


def _is_loop_invariant_value(value: SSAValue, loop_block: Block) -> bool:
    """判断 SSA 值是否定义在当前 loop body 之外。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 当前专题只接受 shape operand 直接来自 loop 外 SSA。
    - 当前 loop body 的块参数和当前 loop body 内定义的 op 结果都视为非 invariant。

    使用示例:
    - _is_loop_invariant_value(symbol_dim, loop_block)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/pass/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    if isinstance(value, BlockArgument):
        return value.owner is not loop_block
    owner = getattr(value, "owner", None)
    if owner is None:
        return True
    return getattr(owner, "parent_block", lambda: None)() is not loop_block


def _shape_is_loop_invariant(op: DmaAllocOp, loop_block: Block) -> bool:
    """判断 `dma.alloc` 的 dynamic_shape 是否全部来自 loop 外。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 空 `dynamic_shape` 视为满足 invariant。
    - 只要任一 shape operand 来自当前 loop body 或 loop-carried block argument，就保持 no-op。

    使用示例:
    - _shape_is_loop_invariant(alloc_op, loop_block)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/pass/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    return all(_is_loop_invariant_value(SSAValue.get(value), loop_block) for value in op.dynamic_shape)


def _is_supported_direct_use(use: Use) -> bool:
    """判断 `dma.alloc` 的单个直接 use 是否属于当前公开白名单。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 输入 staging buffer：仅接受 `dma.slice` 的 `target` operand。
    - output scratch buffer：仅接受 `dma.deslice` 的 `source` operand。
    - 其他 direct use 一律视为未承接的逃逸形态。

    使用示例:
    - all(_is_supported_direct_use(use) for use in alloc_op.result.uses)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/pass/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    user = use.operation
    return (isinstance(user, DmaSliceOp) and use.index == 0) or (
        isinstance(user, DmaDesliceOp) and use.index == 1
    )


def _collect_direct_uses(result: SSAValue) -> tuple[Use, ...]:
    """收集 alloc 结果的直接 use 列表。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 把 xdsl use 链转成稳定 tuple，便于重复遍历与空 use 判定。

    使用示例:
    - uses = _collect_direct_uses(alloc_op.result)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/pass/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    return tuple(cast_use for cast_use in result.uses)


def _uses_are_hoist_safe(uses: Iterable[Use]) -> bool:
    """判断 alloc 结果的直接 use 集合是否满足当前公开外提条件。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 当前公开语义要求 alloc 至少存在一个 direct use。
    - 只要 direct use 中存在未承接形态，就保持 no-op。

    使用示例:
    - if _uses_are_hoist_safe(_collect_direct_uses(alloc_op.result)): ...

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/pass/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    collected_uses = tuple(uses)
    return bool(collected_uses) and all(_is_supported_direct_use(use) for use in collected_uses)


class DmaAllocInSymbolForHoistPattern(RewritePattern):
    """`symbol.for` 内 `dma.alloc` 外提 pattern。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 只匹配当前 `symbol.for` body block 顶层的 `dma.alloc`。
    - 满足 shape invariant 与 direct use 白名单时，把 alloc 外提到所属 `symbol.for` 之前。

    使用示例:
    - pattern = DmaAllocInSymbolForHoistPattern()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/pass/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: DmaAllocOp, rewriter: PatternRewriter, /) -> None:
        """对满足公开条件的 loop 内 `dma.alloc` 执行外提。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 仅当 alloc 位于 `symbol.for` 直接 body block 内时继续。
        - shape 或 direct use 任一条件不满足时保持 no-op。
        - 外提后复用原 op/result，不新建等价 alloc。

        使用示例:
        - DmaAllocInSymbolForHoistPattern().match_and_rewrite(op, rewriter)

        关联文件:
        - spec: spec/pass/symbol_buffer_hoist.md
        - test: test/pass/test_symbol_buffer_hoist.py
        - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
        """

        loop_block = getattr(op, "parent_block", lambda: None)()
        if loop_block is None:
            return
        symbol_for = getattr(loop_block, "parent_op", lambda: None)()
        if not isinstance(symbol_for, SymbolForOp):
            return
        if not _shape_is_loop_invariant(op, loop_block):
            return
        if not _uses_are_hoist_safe(_collect_direct_uses(op.result)):
            return
        op.detach()
        rewriter.insert_op(op, InsertPoint.before(symbol_for))
        rewriter.notify_op_modified(symbol_for)


def get_symbol_buffer_hoist_patterns() -> list[RewritePattern]:
    """返回 `symbol-buffer-hoist` 公开 pattern 列表。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 当前专题只公开一个 `dma.alloc` 外提 pattern。
    - 返回值顺序固定，便于公开测试做机械匹配。

    使用示例:
    - patterns = get_symbol_buffer_hoist_patterns()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/pass/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    return [DmaAllocInSymbolForHoistPattern()]


class SymbolBufferHoistPass(Pass):
    """`symbol-buffer-hoist` pass。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 通过 pattern walker 处理 module 中满足公开条件的 `dma.alloc` 外提。
    - 非 `builtin.module` 输入直接复用共享 `KernelCodeError("module must be builtin.module")`。
    - 最终 verifier 失败统一转成 `KernelCodeError("SymbolBufferHoistVerifierError: ...")`。

    使用示例:
    - from xdsl.context import Context
    - from xdsl.dialects.builtin import ModuleOp
    - module = ModuleOp([])
    - SymbolBufferHoistPass().apply(Context(), module)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/pass/test_symbol_buffer_hoist.py
    - test: test/pass/test_pass_registry.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    name = "symbol-buffer-hoist"

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 `symbol-buffer-hoist` ModulePass。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 只处理 `builtin.module`。
        - 用 greedy pattern walker 把 `symbol.for` 内可安全外提的 alloc 推进到稳定态。
        - 最终统一做一次 `module.verify()`，保持公开失败前缀稳定。

        使用示例:
        - SymbolBufferHoistPass().apply(Context(), module)

        关联文件:
        - spec: spec/pass/symbol_buffer_hoist.md
        - test: test/pass/test_symbol_buffer_hoist.py
        - test: test/pass/test_pass_registry.py
        - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
        """

        module = ensure_builtin_module(module)
        if ctx.get_optional_dialect(Symbol.name) is None:
            ctx.load_dialect(Symbol)
        PatternRewriteWalker(
            GreedyRewritePatternApplier(
                get_symbol_buffer_hoist_patterns(),
                ctx=ctx,
                folding_enabled=self.fold,
                dce_enabled=False,
            )
        ).rewrite_module(module)
        try:
            module.verify()
        except VerifyException as exc:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"SymbolBufferHoistVerifierError: {exc}") from exc

    def run(self, module: ModuleOp) -> ModuleOp:
        """兼容旧 `Pass.run(module)` 入口。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 复用 `apply(Context(), module)` 执行 pass。
        - 返回原 `module`，保持既有 `PassManager.run(...)` 兼容语义。

        使用示例:
        - result = SymbolBufferHoistPass().run(module)

        关联文件:
        - spec: spec/pass/symbol_buffer_hoist.md
        - test: test/pass/test_symbol_buffer_hoist.py
        - test: test/pass/test_pass_registry.py
        - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
        """

        self.apply(Context(), module)
        return module


__all__ = [
    "DmaAllocInSymbolForHoistPattern",
    "get_symbol_buffer_hoist_patterns",
    "SymbolBufferHoistPass",
]
