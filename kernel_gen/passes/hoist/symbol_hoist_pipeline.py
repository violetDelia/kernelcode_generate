"""symbol-hoist-pipeline pass.

功能说明:
- 提供 `symbol-hoist-pipeline` pass，在一个 pass 内组合 alias 归一、symbol loop hoist 与 dma alias hoist pattern。
- pattern 顺序固定为 alias-to-reinterpret 先独立收敛，随后 symbol-loop-hoist、symbol-buffer-hoist 与 dma-alias-hoist 共同收敛。
- pass 成功验证后才替换原 module，验证失败时保持输入 module 不被部分改写。

API 列表:
- `class SymbolHoistPipelinePass(fold: bool = True)`
- `SymbolHoistPipelinePass.name: str`
- `SymbolHoistPipelinePass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.hoist.symbol_hoist_pipeline import SymbolHoistPipelinePass
- SymbolHoistPipelinePass().apply(ctx, module)

关联文件:
- spec: spec/pass/symbol_hoist_pipeline.md
- test: test/passes/test_symbol_hoist_pipeline.py
- 功能实现: kernel_gen/passes/hoist/symbol_hoist_pipeline.py
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.pattern_rewriter import GreedyRewritePatternApplier, PatternRewriteWalker
from xdsl.utils.exceptions import VerifyException

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.symbol import Symbol
from kernel_gen.passes.common import ensure_builtin_module
from kernel_gen.passes.hoist.dma_alias_ops import get_hoist_dma_alias_ops_pass_patterns
from kernel_gen.passes.hoist.dma_alias_to_reinterpret import get_dma_alias_to_reinterpret_patterns
from kernel_gen.passes.hoist.symbol_buffer_hoist import get_symbol_buffer_hoist_patterns
from kernel_gen.passes.hoist.symbol_loop_hoist import get_symbol_loop_hoist_patterns
from kernel_gen.passes.pass_manager import Pass


class SymbolHoistPipelinePass(Pass):
    """组合 hoist pattern 的公开 pass。

    功能说明:
    - 固定公开 pass name 为 `symbol-hoist-pipeline`。
    - 不调用旧 `dma-alias-to-reinterpret` / `symbol-loop-hoist` / `hoist-dma-alias-ops` pass 的 `apply(...)`。
    - 在 clone 上先运行 alias 归一，再运行 symbol-loop-hoist、symbol-buffer-hoist 与 dma-alias-hoist
      的固定点组合，验证成功后替换原 module。

    使用示例:
    - SymbolHoistPipelinePass(fold=False).apply(ctx, module)
    """

    name = "symbol-hoist-pipeline"

    def apply(self: "SymbolHoistPipelinePass", ctx: Context, module: ModuleOp) -> None:
        """执行 `symbol-hoist-pipeline` ModulePass。

        功能说明:
        - 确保 `Symbol` dialect 可用，供 alias 归一过程生成 `symbol.const/add/mul`。
        - 在 clone 上分两阶段运行 pattern，保证 verifier 失败时原 module 保持不变。
        - 第一阶段仅 alias-to-reinterpret；第二阶段顺序为 symbol-loop-hoist、symbol-buffer-hoist、hoist-dma-alias-ops。

        使用示例:
        - SymbolHoistPipelinePass().apply(ctx, module)
        """

        target = ensure_builtin_module(module)
        if ctx.get_optional_dialect(Symbol.name) is None:
            ctx.load_dialect(Symbol)
        rewritten = target.clone()
        try:
            PatternRewriteWalker(
                GreedyRewritePatternApplier(
                    get_dma_alias_to_reinterpret_patterns(),
                    ctx=ctx,
                    folding_enabled=self.fold,
                    dce_enabled=False,
                ),
                apply_recursively=True,
            ).rewrite_module(rewritten)
            PatternRewriteWalker(
                GreedyRewritePatternApplier(
                    [
                        *get_symbol_loop_hoist_patterns(),
                        *get_symbol_buffer_hoist_patterns(),
                        *get_hoist_dma_alias_ops_pass_patterns(rewritten),
                    ],
                    ctx=ctx,
                    folding_enabled=self.fold,
                    dce_enabled=False,
                ),
                apply_recursively=True,
            ).rewrite_module(rewritten)
            rewritten.verify()
        except VerifyException as exc:
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                f"SymbolHoistPipelineVerifierError: {exc}",
            ) from exc
        except KernelCodeError as exc:
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                f"SymbolHoistPipelineVerifierError: {exc}",
            ) from exc
        for block in list(target.body.blocks):
            target.body.erase_block(block, safe_erase=False)
        rewritten.body.move_blocks(target.body)


__all__ = ["SymbolHoistPipelinePass"]
