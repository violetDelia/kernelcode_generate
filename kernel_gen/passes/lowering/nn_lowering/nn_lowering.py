"""nn -> kernel lowering pass.


功能说明:
- 提供 `lower-nn` 的公开 pass 与 parent pattern driver。
- parent driver 只组合 family child 模块公开的 `*_patterns()`，不再保留旧
  `lower_*_family` 或 op 级 lowering helper。
- `_RejectUnsupportedNnOpPattern` 固定放在最后，用于拒绝未被 child pattern
  消费的 `nn.*` op。

API 列表:
- `nn_lowering_patterns() -> list[RewritePattern]`
- `class NnLoweringPass()`
- `NnLoweringPass.apply(self: NnLoweringPass, ctx: Context, op: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
- from xdsl.context import Context
- NnLoweringPass().apply(Context(), module)

关联文件:
- spec: spec/pass/lowering/nn_lowering/spec.md
- test: test/passes/lowering/nn_lowering/test_public_name.py
- test: test/passes/lowering/nn_lowering/test_nn_lowering.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Operation
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriteWalker,
    PatternRewriter,
    RewritePattern,
    op_type_rewrite_pattern,
)

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.symbol import Symbol
from ...pass_manager import Pass


def nn_lowering_patterns() -> list[RewritePattern]:
    """返回 lower-nn 的 rewrite pattern 集合。


    功能说明:
    - 汇总 nn_lowering 各 family pattern，作为 NnLoweringPass.apply(...) 的唯一 driver 输入。
    - `_RejectUnsupportedNnOpPattern` 必须保持在最后，保证已支持 pattern 先尝试改写。

    使用示例:
    - patterns = nn_lowering_patterns()

    关联文件:
    - spec: [spec/pass/lowering/nn_lowering/spec.md](spec/pass/lowering/nn_lowering/spec.md)
    - test: [test/passes/lowering/nn_lowering/test_public_name.py](test/passes/lowering/nn_lowering/test_public_name.py)
    - 功能实现: [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
    """

    from .dma_structured_lowering import dma_structured_patterns
    from .element_binary_lowering import element_binary_patterns
    from .matmul_img2col_lowering import matmul_img2col_patterns
    from .reduce_softmax_lowering import reduce_softmax_patterns
    from .select_cast_lowering import select_cast_patterns

    return [
        *element_binary_patterns(),
        *select_cast_patterns(),
        *dma_structured_patterns(),
        *matmul_img2col_patterns(),
        *reduce_softmax_patterns(),
        _RejectUnsupportedNnOpPattern(),
    ]


class _RejectUnsupportedNnOpPattern(RewritePattern):
    """拒绝未纳入 nn_lowering family 的 nn op。


    功能说明:
    - 放在所有已支持 family pattern 之后。
    - 若仍有 nn.* op 未被处理，则按 unknown op 合同抛出 KernelCodeError。

    使用示例:
    - pattern = _RejectUnsupportedNnOpPattern()

    关联文件:
    - spec: [spec/pass/lowering/nn_lowering/spec.md](spec/pass/lowering/nn_lowering/spec.md)
    - test: [test/passes/lowering/nn_lowering/test_public_name.py](test/passes/lowering/nn_lowering/test_public_name.py)
    - 功能实现: [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter) -> None:
        _ = rewriter
        if not op.name.startswith("nn."):
            return
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"unknown op: {op.name}")


class NnLoweringPass(Pass):
    """nn -> kernel lowering pass。


    功能说明:
    - 将 nn dialect op 降至 kernel / dma / symbol。
    - 通过 `PatternRewriteWalker` 驱动单个 nn op 的 rewrite。
    - 公开执行入口固定为 xdsl `ModulePass.apply(ctx, module)`，不提供单 pass
      `run(...)` 兼容入口。

    使用示例:
    - NnLoweringPass().apply(Context(), module)

    关联文件:
    - spec: [spec/pass/lowering/nn_lowering/spec.md](spec/pass/lowering/nn_lowering/spec.md)
    - test: [test/passes/lowering/nn_lowering/test_nn_lowering.py](test/passes/lowering/nn_lowering/test_nn_lowering.py)
    - 功能实现: [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
    """

    name = "lower-nn"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        """执行 nn lowering。


        功能说明:
        - 通过 canonical public path 取得 `nn_lowering_patterns()` 返回的 pattern driver。
        - 使用 `PatternRewriteWalker + GreedyRewritePatternApplier` 对 module 原地改写。
        - 显式加载 `Symbol` dialect，保证 folding 物化 `symbol.*` 常量时可从 context 取得 materialization interface。

        使用示例:
        - NnLoweringPass().apply(Context(), module)

        关联文件:
        - spec: [spec/pass/lowering/nn_lowering/spec.md](spec/pass/lowering/nn_lowering/spec.md)
        - test: [test/passes/lowering/nn_lowering/test_public_name.py](test/passes/lowering/nn_lowering/test_public_name.py)
        - 功能实现: [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
        """

        from kernel_gen.passes.lowering import nn_lowering as nn_lowering_pkg

        if ctx.get_optional_dialect(Symbol.name) is None:
            ctx.load_dialect(Symbol)
        PatternRewriteWalker(
            GreedyRewritePatternApplier(
                nn_lowering_pkg.nn_lowering_patterns(),
                ctx=ctx,
                folding_enabled=self.fold,
                dce_enabled=False,
            )
        ).rewrite_module(op)


__all__ = ["NnLoweringPass", "nn_lowering_patterns"]
