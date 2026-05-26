"""kernel matmul fusion decompose pass.

功能说明:
- 提供 `kernel-matmul-fusion-decompose` pass，把中间 `kernel.matmul_fusion` 拆回已有可 emit IR。
- `kernel.matmul_fusion.fusion_list` 只作为 metadata 保留到分解前，本 pass 不按该 attr 改变语义。

API 列表:
- `class KernelMatmulFusionDecomposePass(fold: bool = True)`
- `KernelMatmulFusionDecomposePass.from_options(options: dict[str, str]) -> KernelMatmulFusionDecomposePass`
- `KernelMatmulFusionDecomposePass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.kernel_matmul_fusion_decompose import KernelMatmulFusionDecomposePass
- KernelMatmulFusionDecomposePass().apply(Context(), module)
- KernelMatmulFusionDecomposePass.from_options({})

关联文件:
- spec: spec/pass/kernel_matmul_fusion_decompose.md
- test: test/passes/test_kernel_matmul_fusion_decompose.py
- 功能实现: kernel_gen/passes/kernel_matmul_fusion_decompose.py
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects import scf
from xdsl.dialects.builtin import IntegerAttr, ModuleOp
from xdsl.ir import Block, Region
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


def _kernel_matmul_fusion_decompose_error(message: str) -> KernelCodeError:
    """构造 kernel-matmul-fusion-decompose 错误。

    功能说明:
    - 统一 pass 内稳定错误短语前缀，便于 spec、pytest 与 expectation 机械匹配。

    使用示例:
    - raise _kernel_matmul_fusion_decompose_error("tmp type")
    """

    detail = message.strip()
    if not detail:
        detail = "unknown error"
    full_message = f"kernel-matmul-fusion-decompose {detail}"
    error = KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, full_message)
    return error


class KernelMatmulFusionDecomposePass(Pass):
    """分解 kernel.matmul_fusion 的公开 pass。

    功能说明:
    - 将每个 `kernel.matmul_fusion(out,lhs,rhs,acc)` 分解成 `scf.if %acc` 双分支。
    - `fusion_list` metadata 不参与匹配或输出。
    - true 分支执行 `kernel.matmul(..., acc=true)`。
    - false 分支执行 `kernel.matmul(..., acc=false)`。

    使用示例:
    - KernelMatmulFusionDecomposePass().apply(Context(), module)
    """

    name = "kernel-matmul-fusion-decompose"

    def __init__(self, fold: bool = True) -> None:
        """初始化 matmul fusion 分解 pass。

        功能说明:
        - 只记录通用 fold 开关；本 pass 不接受自定义 option。

        使用示例:
        - KernelMatmulFusionDecomposePass()
        """

        super().__init__(fold=fold)

    @classmethod
    def from_options(cls, options: dict[str, str]) -> "KernelMatmulFusionDecomposePass":
        """从 registry options 构造 pass。

        功能说明:
        - 第一版不接受自定义 option。
        - unknown option 稳定失败，错误短语包含 `kernel-matmul-fusion-decompose options`。

        使用示例:
        - KernelMatmulFusionDecomposePass.from_options({})
        """

        if options:
            names = ", ".join(sorted(options))
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                f"kernel-matmul-fusion-decompose options unknown: {names}",
            )
        return cls()

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 kernel.matmul_fusion 分解。

        功能说明:
        - 遍历 builtin.module 中的 fusion op。
        - 在 fusion 前插入必要 `symbol.get_dim` 与 `scf.if`，再删除原 fusion op。
        - 不读取 `fusion_list`，因此非空 metadata 不改变输出。

        使用示例:
        - KernelMatmulFusionDecomposePass().apply(Context(), module)
        """

        ensure_builtin_module(module)
        PatternRewriteWalker(
            GreedyRewritePatternApplier(
                [_KernelMatmulFusionDecomposePattern()],
                ctx=ctx,
                folding_enabled=self.fold,
                dce_enabled=False,
            ),
            apply_recursively=True,
        ).rewrite_module(module)


class _KernelMatmulFusionDecomposePattern(RewritePattern):
    """kernel.matmul_fusion 分解 pattern。

    功能说明:
    - 用单个 typed root pattern 将 fusion op 分解为 `scf.if` 双分支。
    - 忽略 `fusion_list` metadata，保持所有 fusion 输入同一分解语义。

    使用示例:
    - pattern = _KernelMatmulFusionDecomposePattern()
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, fusion: KernelMatmulFusionOp, rewriter: PatternRewriter, /) -> None:
        """把 kernel.matmul_fusion 替换为 scf.if。

        功能说明:
        - true 分支保留累加语义 `kernel.matmul(..., acc=true)`。
        - false 分支使用覆盖语义 `kernel.matmul(..., acc=false)`。
        - 不复制 `fusion_list` metadata 到输出 matmul。

        使用示例:
        - walker 运行时自动调用本方法。
        """

        then_matmul = KernelMatmulOp(fusion.out, fusion.lhs, fusion.rhs, fusion.space, acc=True)
        then_block = Block()
        then_block.add_ops([then_matmul, scf.YieldOp()])
        else_matmul = KernelMatmulOp(fusion.out, fusion.lhs, fusion.rhs, fusion.space, acc=IntegerAttr.from_bool(False))
        else_block = Block()
        else_block.add_ops([else_matmul, scf.YieldOp()])
        if_op = scf.IfOp(fusion.acc, [], Region(then_block), Region(else_block))
        try:
            verify_generated_ops([then_matmul, else_matmul, if_op])
        except KernelCodeError as exc:
            raise _kernel_matmul_fusion_decompose_error("matmul acc") from exc
        rewriter.replace_matched_op([if_op], [])


__all__ = ["KernelMatmulFusionDecomposePass"]
