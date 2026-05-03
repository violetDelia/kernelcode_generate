"""tile-analysis logic module.


功能说明:
- 承接 `tile-analysis` 的真实 analysis-only 主链与 `ModulePass` 落点。
- 对外公开 `Binary/Broadcast/Matmul` 三类 op-level pattern 与 getter，供测试与组合 pass 复用。
- 只写 `tile.analysis` 与 `tile.tile_exprs`，不生成 `symbol.for`、`dma.view` 或其他 tile rewrite 结构。

API 列表:
- `class TileAnalysisBinaryPattern(RewritePattern)`
- `class TileAnalysisBroadcastPattern(RewritePattern)`
- `class TileAnalysisMatmulPattern(RewritePattern)`
- `get_tile_analysis_pass_patterns() -> list[RewritePattern]`
- `class TileAnalysisPass(ModulePass)`
- `TileAnalysisPass.__init__(fold: bool = True) -> None`
- `TileAnalysisPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.tile.analysis import TileAnalysisPass, TileAnalysisBinaryPattern, get_tile_analysis_pass_patterns
- TileAnalysisPass().apply(Context(), module)
- patterns = get_tile_analysis_pass_patterns()

关联文件:
- spec: [spec/pass/tile/analysis.md](spec/pass/tile/analysis.md)
- test: [test/passes/tile/test_analysis.py](test/passes/tile/test_analysis.py)
- 功能实现: [kernel_gen/passes/tile/analysis.py](kernel_gen/passes/tile/analysis.py)
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects.builtin import ArrayAttr, IntAttr, ModuleOp, StringAttr
from xdsl.ir import Operation, SSAValue
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
from kernel_gen.dialect.symbol import Symbol, SymbolForOp, SymbolValueType
from kernel_gen.passes.common import ensure_builtin_module


def _matches_matmul_roles(
    lhs_value: SSAValue,
    rhs_value: SSAValue,
    out_value: SSAValue,
) -> bool:
    """判断三个 memory 是否满足 `lhs[M,K] * rhs[K,N] -> out[M,N]`。


    功能说明:
    - 只接受三个 `rank-2 nn.memory`。
    - 用于 `tile-analysis` 在不依赖 operand 文本顺序的前提下识别 matmul 逻辑角色。

    使用示例:
    - assert _matches_matmul_roles(lhs_value, rhs_value, out_value)

    关联文件:
    - spec: [spec/pass/tile/analysis.md](spec/pass/tile/analysis.md)
    - test: [test/passes/tile/test_analysis.py](test/passes/tile/test_analysis.py)
    - 功能实现: [kernel_gen/passes/tile/analysis.py](kernel_gen/passes/tile/analysis.py)
    """

    if not (
        isinstance(lhs_value.type, NnMemoryType)
        and isinstance(rhs_value.type, NnMemoryType)
        and isinstance(out_value.type, NnMemoryType)
    ):
        return False
    lhs_shape = list(lhs_value.type.shape.data)
    rhs_shape = list(rhs_value.type.shape.data)
    out_shape = list(out_value.type.shape.data)
    if len(lhs_shape) != 2 or len(rhs_shape) != 2 or len(out_shape) != 2:
        return False
    return (
        lhs_shape[0] == out_shape[0]
        and lhs_shape[1] == rhs_shape[0]
        and rhs_shape[1] == out_shape[1]
    )


def _collect_ancestor_loop_step_exprs(op: Operation) -> list[str]:
    """收集当前 op 外层 `symbol.for` 的 step 表达式，按外到内排序。"""

    parents: list[SymbolForOp] = []
    parent = op.parent_op()
    while parent is not None:
        if isinstance(parent, SymbolForOp):
            parents.append(parent)
        parent = parent.parent_op()
    ordered_steps: list[str] = []
    for loop_op in reversed(parents):
        step_type = SSAValue.get(loop_op.step).type
        if isinstance(step_type, SymbolValueType):
            ordered_steps.append(str(step_type.get_value()))
    return ordered_steps


def _build_tile_expr_row_from_matching_dims(
    roles: list[str],
    dim_attrs: list[IntAttr | StringAttr],
    loop_step_exprs: list[str],
) -> list[str]:
    """按 loop step 与实际 shape 维度匹配结果写回 tile 表达式。"""

    row = [""] * len(roles)
    if not loop_step_exprs:
        return row
    remaining_positions = [
        index for index, role in enumerate(roles) if role == "elewise"
    ]
    for step_expr in loop_step_exprs:
        matched_position: int | None = None
        for index in reversed(remaining_positions):
            if _dim_expr_text(dim_attrs[index]) == step_expr:
                matched_position = index
                break
        if matched_position is None:
            continue
        row[matched_position] = step_expr
        remaining_positions.remove(matched_position)
    return row


def _dim_expr_text(dim_attr: IntAttr | StringAttr) -> str:
    """返回 shape 维度 attr 的稳定字符串文本。"""

    if isinstance(dim_attr, IntAttr):
        return str(dim_attr.data)
    return dim_attr.data


class TileAnalysisBinaryPattern(RewritePattern):
    """匹配 `kernel.binary_elewise` 的公开 analysis pattern。


    功能说明:
    - 命中 `kernel.binary_elewise` 后，只为当前 op 补 `tile.analysis` 与 `tile.tile_exprs`。
    - 若当前 op 已有这两个 attr，则直接跳过。

    使用示例:
    - pattern = TileAnalysisBinaryPattern()

    关联文件:
    - spec: [spec/pass/tile/analysis.md](spec/pass/tile/analysis.md)
    - test: [test/passes/tile/test_analysis.py](test/passes/tile/test_analysis.py)
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
        tile_expr_rows = [[""] * rank for _ in memory_values]
        loop_step_exprs = _collect_ancestor_loop_step_exprs(op)
        if loop_step_exprs:
            tile_expr_rows = [
                _build_tile_expr_row_from_matching_dims(
                    ["elewise"] * rank,
                    list(value.type.shape.data),
                    loop_step_exprs,
                )
                for value in memory_values
            ]
        op.attributes["tile.analysis"] = ArrayAttr(
            [ArrayAttr([StringAttr(role) for role in row]) for row in roles]
        )
        op.attributes["tile.tile_exprs"] = ArrayAttr(
            [ArrayAttr([StringAttr(expr) for expr in row]) for row in tile_expr_rows]
        )
        rewriter.notify_op_modified(op)


class TileAnalysisBroadcastPattern(RewritePattern):
    """匹配 `dma.broadcast` 的公开 analysis pattern。


    功能说明:
    - 命中 `dma.broadcast` 后，只为当前 op 补 `tile.analysis` 与 `tile.tile_exprs`。
    - 若当前 op 已有这两个 attr，则直接跳过。

    使用示例:
    - pattern = TileAnalysisBroadcastPattern()

    关联文件:
    - spec: [spec/pass/tile/analysis.md](spec/pass/tile/analysis.md)
    - test: [test/passes/tile/test_analysis.py](test/passes/tile/test_analysis.py)
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
            aligned_source_dims = [IntAttr(1)] * len(target_dims)
        tile_expr_rows = [[""] * len(row) for row in roles]
        loop_step_exprs = _collect_ancestor_loop_step_exprs(op)
        if loop_step_exprs:
            tile_expr_rows = [
                _build_tile_expr_row_from_matching_dims(
                    ["expand" if role == "expand" else "elewise" for role in roles[1]],
                    target_dims,
                    loop_step_exprs,
                ),
                _build_tile_expr_row_from_matching_dims(
                    roles[1],
                    aligned_source_dims,
                    loop_step_exprs,
                ),
            ]
        op.attributes["tile.analysis"] = ArrayAttr(
            [ArrayAttr([StringAttr(role) for role in row]) for row in roles]
        )
        op.attributes["tile.tile_exprs"] = ArrayAttr(
            [ArrayAttr([StringAttr(expr) for expr in row]) for row in tile_expr_rows]
        )
        rewriter.notify_op_modified(op)


class TileAnalysisMatmulPattern(RewritePattern):
    """匹配 `kernel.matmul` 的公开 analysis pattern。


    功能说明:
    - 命中 `kernel.matmul` 后，只为当前 op 补 `tile.analysis` 与 `tile.tile_exprs`。
    - 若当前 op 已有这两个 attr，则直接跳过。

    使用示例:
    - pattern = TileAnalysisMatmulPattern()

    关联文件:
    - spec: [spec/pass/tile/analysis.md](spec/pass/tile/analysis.md)
    - test: [test/passes/tile/test_analysis.py](test/passes/tile/test_analysis.py)
    - 功能实现: [kernel_gen/passes/tile/analysis.py](kernel_gen/passes/tile/analysis.py)
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: KernelMatmulOp, rewriter: PatternRewriter, /) -> None:
        if "tile.analysis" in op.attributes and "tile.tile_exprs" in op.attributes:
            return
        operands = [SSAValue.get(operand) for operand in op.operands]
        if len(operands) < 3:
            return
        candidate_memories = operands[:3]
        if not all(isinstance(value.type, NnMemoryType) for value in candidate_memories):
            return
        lhs_index, rhs_index, out_index = 0, 1, 2
        lhs, rhs, out = (
            candidate_memories[lhs_index],
            candidate_memories[rhs_index],
            candidate_memories[out_index],
        )
        if not _matches_matmul_roles(lhs, rhs, out):
            matched = False
            for lhs_candidate_index in range(3):
                for rhs_candidate_index in range(3):
                    for out_candidate_index in range(3):
                        if len({lhs_candidate_index, rhs_candidate_index, out_candidate_index}) != 3:
                            continue
                        lhs_candidate = candidate_memories[lhs_candidate_index]
                        rhs_candidate = candidate_memories[rhs_candidate_index]
                        out_candidate = candidate_memories[out_candidate_index]
                        if _matches_matmul_roles(lhs_candidate, rhs_candidate, out_candidate):
                            lhs_index, rhs_index, out_index = (
                                lhs_candidate_index,
                                rhs_candidate_index,
                                out_candidate_index,
                            )
                            lhs, rhs, out = lhs_candidate, rhs_candidate, out_candidate
                            matched = True
                            break
                    if matched:
                        break
                if matched:
                    break
        if not _matches_matmul_roles(lhs, rhs, out):
            return
        roles = [
            ["elewise", "reduce"],
            ["reduce", "elewise"],
            ["elewise", "elewise"],
        ]
        tile_expr_rows = [["", ""], ["", ""], ["", ""]]
        loop_step_exprs = _collect_ancestor_loop_step_exprs(op)
        if loop_step_exprs:
            lhs_type = lhs.type
            rhs_type = rhs.type
            out_type = out.type
            assert isinstance(lhs_type, NnMemoryType)
            assert isinstance(rhs_type, NnMemoryType)
            assert isinstance(out_type, NnMemoryType)
            out_shape = list(out_type.shape.data)
            rhs_shape = list(rhs_type.shape.data)
            m_expr = _dim_expr_text(out_shape[0])
            n_expr = _dim_expr_text(out_shape[1])
            k_expr = _dim_expr_text(rhs_shape[0])
            tile_m = ""
            tile_n = ""
            for step_expr in loop_step_exprs:
                if step_expr == n_expr:
                    tile_n = step_expr
                    continue
                if step_expr == k_expr:
                    continue
                if step_expr == m_expr:
                    tile_m = step_expr
            tile_expr_rows = [
                [tile_m, ""],
                ["", tile_n],
                [tile_m, tile_n],
            ]
        op.attributes["tile.analysis"] = ArrayAttr(
            [ArrayAttr([StringAttr(role) for role in row]) for row in roles]
        )
        op.attributes["tile.tile_exprs"] = ArrayAttr(
            [ArrayAttr([StringAttr(expr) for expr in row]) for row in tile_expr_rows]
        )
        rewriter.notify_op_modified(op)


def get_tile_analysis_pass_patterns() -> list[RewritePattern]:
    """返回 `tile-analysis` pass 使用的公开 pattern 列表。


    功能说明:
    - 为外部测试、组合 pass 与公开 API 提供稳定的 op-level pattern 构造入口。
    - 保持 `Binary -> Broadcast -> Matmul` 顺序稳定，便于机械断言。

    使用示例:
    - patterns = get_tile_analysis_pass_patterns()

    关联文件:
    - spec: [spec/pass/tile/analysis.md](spec/pass/tile/analysis.md)
    - test: [test/passes/tile/test_analysis.py](test/passes/tile/test_analysis.py)
    - 功能实现: [kernel_gen/passes/tile/analysis.py](kernel_gen/passes/tile/analysis.py)
    """

    return [
        TileAnalysisBinaryPattern(),
        TileAnalysisBroadcastPattern(),
        TileAnalysisMatmulPattern(),
    ]


class TileAnalysisPass(ModulePass):
    """`tile-analysis` 的公开 `ModulePass`。


    功能说明:
    - 保持稳定公开名 `tile-analysis`。
    - 逐个对模块中的 tile 目标 op 运行公开 pattern，补齐缺失的 `tile.analysis` 与 `tile.tile_exprs`。

    使用示例:
    - TileAnalysisPass().apply(Context(), module)

    关联文件:
    - spec: [spec/pass/tile/analysis.md](spec/pass/tile/analysis.md)
    - test: [test/passes/tile/test_analysis.py](test/passes/tile/test_analysis.py)
    - 功能实现: [kernel_gen/passes/tile/analysis.py](kernel_gen/passes/tile/analysis.py)
    """

    name = "tile-analysis"

    def __init__(self: "TileAnalysisPass", fold: bool = True) -> None:
        """初始化 tile-analysis pass 公共选项。


        功能说明:
        - 记录 `fold` 开关，默认允许 pass 内 pattern walker 执行 folding。

        使用示例:
        - pass_obj = TileAnalysisPass()
        - pass_obj = TileAnalysisPass(fold=False)

        关联文件:
        - spec: [spec/pass/tile/analysis.md](spec/pass/tile/analysis.md)
        - test: [test/passes/tile/test_analysis.py](test/passes/tile/test_analysis.py)
        - 功能实现: [kernel_gen/passes/tile/analysis.py](kernel_gen/passes/tile/analysis.py)
        """

        self.fold = bool(fold)

    def apply(self: "TileAnalysisPass", ctx: Context, module: ModuleOp) -> None:
        ensure_builtin_module(module)
        if ctx.get_optional_dialect(Symbol.name) is None:
            ctx.load_dialect(Symbol)
        PatternRewriteWalker(
            GreedyRewritePatternApplier(
                get_tile_analysis_pass_patterns(),
                ctx=ctx,
                folding_enabled=self.fold,
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
