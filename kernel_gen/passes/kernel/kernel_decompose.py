"""kernel decompose pass.

功能说明:
- 提供 `kernel-decompose` pass，把中间 kernel 聚合 op 规整成下游可消费 kernel IR。
- 第一版处理 `kernel.matmul_fusion`，输出带动态 acc operand 的 `kernel.matmul`。
- 不删除 `dma.fill`；fill 删除统一交由后续 canonicalization 处理。

API 列表:
- `class KernelDecomposePass(fold: bool = True)`
- `KernelDecomposePass.from_options(options: dict[str, str]) -> KernelDecomposePass`
- `KernelDecomposePass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.kernel.kernel_decompose import KernelDecomposePass
- KernelDecomposePass().apply(Context(), module)
- KernelDecomposePass.from_options({})

关联文件:
- spec: spec/pass/kernel/kernel_decompose.md
- test: test/passes/kernel/test_kernel_decompose.py
- 功能实现: kernel_gen/passes/kernel/kernel_decompose.py
"""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.kernel import KernelMatmulFusionOp, KernelMatmulOp
from kernel_gen.passes.common import ensure_builtin_module, verify_generated_ops
from kernel_gen.passes.pass_manager import Pass


def _kernel_decompose_error(message: str) -> KernelCodeError:
    """构造 kernel-decompose 错误。

    功能说明:
    - 统一 pass 内稳定错误短语前缀，便于 spec、pytest 与 expectation 机械匹配。
    - 空白 detail 归一为 `unknown error`，避免抛出空消息。
    - 返回 KernelCodeError，由调用点决定是否链式抛出。

    使用示例:
    - raise _kernel_decompose_error("matmul acc")
    """

    detail = message.strip()
    if not detail:
        detail = "unknown error"
    prefix = "kernel-decompose"
    text = f"{prefix} {detail}"
    return KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, text)


@dataclass(frozen=True)
class KernelDecomposePass(Pass):
    """分解 kernel 中间聚合 op 的公开 pass。

    功能说明:
    - 将 `kernel.matmul_fusion(out,lhs,rhs,acc)` 规整为单条
      `kernel.matmul(out,lhs,rhs,acc)` 动态 acc op。
    - 不生成旧 `scf.if` 双分支，不复制 `fusion_list` metadata。
    - 不删除 `dma.fill`，保持 fill 规范化职责集中在 canonicalization。

    使用示例:
    - KernelDecomposePass().apply(Context(), module)
    """

    name = "kernel-decompose"
    fold: bool = True

    def __init__(self, fold: bool = True) -> None:
        """初始化 kernel-decompose pass。

        功能说明:
        - 记录通用 fold 开关。
        - 第一版不接受 pass 专属 option。

        使用示例:
        - KernelDecomposePass()
        """

        object.__setattr__(self, "fold", bool(fold))

    @classmethod
    def from_options(cls, options: dict[str, str]) -> "KernelDecomposePass":
        """从 registry options 构造 pass。

        功能说明:
        - 第一版不接受自定义 option。
        - unknown option 稳定失败，错误短语包含 `kernel-decompose options`。

        使用示例:
        - KernelDecomposePass.from_options({})
        """

        if options:
            names = ", ".join(sorted(options))
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                f"kernel-decompose options unknown: {names}",
            )
        return cls()

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 kernel 中间 op 分解。

        功能说明:
        - 遍历 builtin.module 中的 `kernel.matmul_fusion`。
        - 将 fusion 替换为动态 acc `kernel.matmul`。
        - 不删除任何 `dma.fill`。

        使用示例:
        - KernelDecomposePass().apply(Context(), module)
        """

        ensure_builtin_module(module)
        PatternRewriteWalker(
            GreedyRewritePatternApplier(
                [_KernelMatmulFusionToDynamicAccPattern()],
                ctx=ctx,
                folding_enabled=self.fold,
                dce_enabled=False,
            ),
            apply_recursively=True,
        ).rewrite_module(module)


class _KernelMatmulFusionToDynamicAccPattern(RewritePattern):
    """kernel.matmul_fusion 到动态 acc matmul 的 pattern。"""

    @op_type_rewrite_pattern
    def match_and_rewrite(self, fusion: KernelMatmulFusionOp, rewriter: PatternRewriter, /) -> None:
        """把 `kernel.matmul_fusion` 替换成动态 acc `kernel.matmul`。

        功能说明:
        - 生成单条 `KernelMatmulOp(..., acc=fusion.acc)`。
        - 先局部 verify 新 op，失败时报 `kernel-decompose matmul acc`。
        - 替换成功后保留所有现有 `dma.fill`。

        使用示例:
        - walker 运行时自动调用本方法。
        """

        matmul = KernelMatmulOp(fusion.out, fusion.lhs, fusion.rhs, fusion.space, acc=fusion.acc)
        try:
            verify_generated_ops([matmul])
        except KernelCodeError as exc:
            raise _kernel_decompose_error("matmul acc") from exc
        rewriter.replace_matched_op([matmul], [])


__all__ = ["KernelDecomposePass"]
