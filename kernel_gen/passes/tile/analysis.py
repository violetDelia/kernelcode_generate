"""tile-analysis logic module.

创建者: 朽木露琪亚
最后一次更改: OpenAI Codex

功能说明:
- 承接 `tile-analysis` 的真实 analysis-only 主链与 `ModulePass` 落点。
- 对外公开 `Binary/Broadcast/Matmul` 三类 op-level pattern 与 getter，供测试与组合 pass 复用。
- 只写 `tile.analysis` 与 `tile.tile_exprs`，不生成 `symbol.for`、`dma.view` 或其他 tile rewrite 结构。

使用示例:
- from kernel_gen.passes.tile.analysis import TileAnalysisPass, TileAnalysisBinaryPattern, get_tile_analysis_pass_patterns
- TileAnalysisPass().apply(Context(), module)
- patterns = get_tile_analysis_pass_patterns()

关联文件:
- spec: [spec/pass/tile/analysis.md](spec/pass/tile/analysis.md)
- test: [test/pass/tile/test_analysis.py](test/pass/tile/test_analysis.py)
- 功能实现: [kernel_gen/passes/tile/analysis.py](kernel_gen/passes/tile/analysis.py)
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects.builtin import ArrayAttr, IntAttr, ModuleOp, StringAttr
from xdsl.ir import SSAValue
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)

from kernel_gen.dialect.dma import DmaBroadcastOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp, KernelMatmulOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.passes.common import ensure_builtin_module


class TileAnalysisBinaryPattern(RewritePattern):
    """匹配 `kernel.binary_elewise` 的公开 analysis pattern。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 命中 `kernel.binary_elewise` 后，只为当前 op 补 `tile.analysis` 与 `tile.tile_exprs`。
    - 若当前 op 已有这两个 attr，则直接跳过。

    使用示例:
    - pattern = TileAnalysisBinaryPattern()

    关联文件:
    - spec: [spec/pass/tile/analysis.md](spec/pass/tile/analysis.md)
    - test: [test/pass/tile/test_analysis.py](test/pass/tile/test_analysis.py)
    - 功能实现: [kernel_gen/passes/tile/analysis.py](kernel_gen/passes/tile/analysis.py)
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: KernelBinaryElewiseOp, rewriter: PatternRewriter, /) -> None:
        if "tile.analysis" in op.attributes and "tile.tile_exprs" in op.attributes:
            return
        memory_values = [
            SSAValue.get(operand)
            for operand in op.operands
            if isinstance(SSAValue.get(operand).type, NnMemoryType)
        ]
        if not memory_values:
            return
        first_type = memory_values[0].type
        assert isinstance(first_type, NnMemoryType)
        rank = len(first_type.shape.data)
        roles = [["elewise"] * rank for _ in memory_values]
        op.attributes["tile.analysis"] = ArrayAttr(
            [ArrayAttr([StringAttr(role) for role in row]) for row in roles]
        )
        op.attributes["tile.tile_exprs"] = ArrayAttr(
            [ArrayAttr([StringAttr("") for _ in row]) for row in roles]
        )
        rewriter.notify_op_modified(op)


class TileAnalysisBroadcastPattern(RewritePattern):
    """匹配 `dma.broadcast` 的公开 analysis pattern。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 命中 `dma.broadcast` 后，只为当前 op 补 `tile.analysis` 与 `tile.tile_exprs`。
    - 若当前 op 已有这两个 attr，则直接跳过。

    使用示例:
    - pattern = TileAnalysisBroadcastPattern()

    关联文件:
    - spec: [spec/pass/tile/analysis.md](spec/pass/tile/analysis.md)
    - test: [test/pass/tile/test_analysis.py](test/pass/tile/test_analysis.py)
    - 功能实现: [kernel_gen/passes/tile/analysis.py](kernel_gen/passes/tile/analysis.py)
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: DmaBroadcastOp, rewriter: PatternRewriter, /) -> None:
        if "tile.analysis" in op.attributes and "tile.tile_exprs" in op.attributes:
            return
        target = SSAValue.get(op.operands[0])
        source = SSAValue.get(op.operands[1])
        if not isinstance(target.type, NnMemoryType):
            return
        target_dims = list(target.type.shape.data)
        target_roles = ["elewise"] * len(target_dims)
        if isinstance(source.type, NnMemoryType):
            source_dims = list(source.type.shape.data)
            aligned_source_dims = [IntAttr(1)] * max(len(target_dims) - len(source_dims), 0) + source_dims
            source_roles: list[str] = []
            for src_dim, tgt_dim in zip(aligned_source_dims, target_dims):
                same_dim = (
                    isinstance(src_dim, IntAttr)
                    and isinstance(tgt_dim, IntAttr)
                    and src_dim.data == tgt_dim.data
                ) or (
                    isinstance(src_dim, StringAttr)
                    and isinstance(tgt_dim, StringAttr)
                    and src_dim.data == tgt_dim.data
                )
                unit_dim = (
                    isinstance(src_dim, IntAttr)
                    and src_dim.data == 1
                ) or (
                    isinstance(src_dim, StringAttr)
                    and src_dim.data == "1"
                )
                if same_dim:
                    source_roles.append("elewise")
                elif unit_dim:
                    source_roles.append("expand")
                else:
                    source_roles.append("expand")
            roles = [target_roles, source_roles]
        else:
            roles = [target_roles, ["expand"] * len(target_dims)]
        op.attributes["tile.analysis"] = ArrayAttr(
            [ArrayAttr([StringAttr(role) for role in row]) for row in roles]
        )
        op.attributes["tile.tile_exprs"] = ArrayAttr(
            [ArrayAttr([StringAttr("") for _ in row]) for row in roles]
        )
        rewriter.notify_op_modified(op)


class TileAnalysisMatmulPattern(RewritePattern):
    """匹配 `kernel.matmul` 的公开 analysis pattern。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 命中 `kernel.matmul` 后，只为当前 op 补 `tile.analysis` 与 `tile.tile_exprs`。
    - 若当前 op 已有这两个 attr，则直接跳过。

    使用示例:
    - pattern = TileAnalysisMatmulPattern()

    关联文件:
    - spec: [spec/pass/tile/analysis.md](spec/pass/tile/analysis.md)
    - test: [test/pass/tile/test_analysis.py](test/pass/tile/test_analysis.py)
    - 功能实现: [kernel_gen/passes/tile/analysis.py](kernel_gen/passes/tile/analysis.py)
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: KernelMatmulOp, rewriter: PatternRewriter, /) -> None:
        if "tile.analysis" in op.attributes and "tile.tile_exprs" in op.attributes:
            return
        operands = [SSAValue.get(operand) for operand in op.operands]
        if len(operands) < 3:
            return
        out, lhs, rhs = operands[0], operands[1], operands[2]
        if not (
            isinstance(lhs.type, NnMemoryType)
            and isinstance(rhs.type, NnMemoryType)
            and isinstance(out.type, NnMemoryType)
        ):
            return
        if len(lhs.type.shape.data) != 2 or len(rhs.type.shape.data) != 2 or len(out.type.shape.data) != 2:
            return
        roles = [
            ["elewise", "reduce"],
            ["reduce", "elewise"],
            ["elewise", "elewise"],
        ]
        op.attributes["tile.analysis"] = ArrayAttr(
            [ArrayAttr([StringAttr(role) for role in row]) for row in roles]
        )
        op.attributes["tile.tile_exprs"] = ArrayAttr(
            [ArrayAttr([StringAttr("") for _ in row]) for row in roles]
        )
        rewriter.notify_op_modified(op)


def get_tile_analysis_pass_patterns() -> list[RewritePattern]:
    """返回 `tile-analysis` pass 使用的公开 pattern 列表。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 为外部测试、组合 pass 与公开 API 提供稳定的 op-level pattern 构造入口。
    - 保持 `Binary -> Broadcast -> Matmul` 顺序稳定，便于机械断言。

    使用示例:
    - patterns = get_tile_analysis_pass_patterns()

    关联文件:
    - spec: [spec/pass/tile/analysis.md](spec/pass/tile/analysis.md)
    - test: [test/pass/tile/test_analysis.py](test/pass/tile/test_analysis.py)
    - 功能实现: [kernel_gen/passes/tile/analysis.py](kernel_gen/passes/tile/analysis.py)
    """

    return [
        TileAnalysisBinaryPattern(),
        TileAnalysisBroadcastPattern(),
        TileAnalysisMatmulPattern(),
    ]


class TileAnalysisPass(ModulePass):
    """`tile-analysis` 的公开 `ModulePass`。

    创建者: 朽木露琪亚
    最后一次更改: OpenAI Codex

    功能说明:
    - 保持稳定公开名 `tile-analysis`。
    - 逐个对模块中的 tile 目标 op 运行公开 pattern，补齐缺失的 `tile.analysis` 与 `tile.tile_exprs`。

    使用示例:
    - TileAnalysisPass().apply(Context(), module)

    关联文件:
    - spec: [spec/pass/tile/analysis.md](spec/pass/tile/analysis.md)
    - test: [test/pass/tile/test_analysis.py](test/pass/tile/test_analysis.py)
    - 功能实现: [kernel_gen/passes/tile/analysis.py](kernel_gen/passes/tile/analysis.py)
    """

    name = "tile-analysis"

    def apply(self: "TileAnalysisPass", ctx: Context, module: ModuleOp) -> None:
        ensure_builtin_module(module)
        PatternRewriteWalker(
            GreedyRewritePatternApplier(
                get_tile_analysis_pass_patterns(),
                ctx=ctx,
                dce_enabled=False,
            )
        ).rewrite_module(module)


__all__ = [
    "TileAnalysisBinaryPattern",
    "TileAnalysisBroadcastPattern",
    "TileAnalysisMatmulPattern",
    "TileAnalysisPass",
    "get_tile_analysis_pass_patterns",
]
