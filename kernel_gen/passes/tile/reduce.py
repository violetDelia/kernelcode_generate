"""tile-reduce pass module.


功能说明:
- 承接 `tile-reduce` 的公开 pattern、getter、`ModulePass` 与当前实现逻辑。
- 对外 canonical public path 固定为 `kernel_gen.passes.tile.reduce`。
- 不再拆分额外实现文件，当前 pass 逻辑全部保留在本文件。

API 列表:
- `class TileReduceMatmulPattern(RewritePattern)`
- `get_tile_reduce_pass_patterns() -> list[RewritePattern]`
- `class TileReducePass(ModulePass)`
- `TileReducePass.__init__(fold: bool = True) -> None`
- `TileReducePass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.tile.reduce import (
-     TileReduceMatmulPattern,
-     TileReducePass,
-     get_tile_reduce_pass_patterns,
- )
- patterns = get_tile_reduce_pass_patterns()
- TileReducePass().apply(Context(), module)

关联文件:
- spec: [spec/pass/tile/reduce.md](spec/pass/tile/reduce.md)
- test: [test/passes/tile/test_reduce.py](test/passes/tile/test_reduce.py)
- test: [test/dsl/gen_kernel/test_gen_kernel.py](test/dsl/gen_kernel/test_gen_kernel.py)
- 功能实现: [kernel_gen/passes/tile/reduce.py](kernel_gen/passes/tile/reduce.py)
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, IntegerAttr, ModuleOp, StringAttr, UnregisteredOp, i32
from xdsl.ir import Attribute, Block, Operation, SSAValue
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)

from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp, DmaFillOp, DmaViewOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp, KernelMatmulOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import Symbol, SymbolExprAttr, SymbolForOp, SymbolGetDimOp, SymbolIterType, SymbolValueType
from kernel_gen.dialect.tuner import TunerParamOp
from kernel_gen.passes.common import ensure_builtin_module, raise_pass_contract_error


class TileReduceMatmulPattern(RewritePattern):
    """匹配 `kernel.matmul` 的公开 tile-reduce pattern。


    功能说明:
    - 命中顶层 `kernel.matmul` 后，就地把当前 op 改写为“只切 reduce 轴”的结构。
    - 顶层输出 memory 直接作为 reduce 累加目标，不再生成输出轴 loop 与输出轴 `tuner.param`。
    - 只改写当前顶层 tile op；已经落在 `symbol.for` 内的 rewritten op 不再重复处理。

    使用示例:
    - TileReduceMatmulPattern().match_and_rewrite(op, rewriter)

    关联文件:
    - spec: [spec/pass/tile/reduce.md](spec/pass/tile/reduce.md)
    - test: [test/passes/tile/test_reduce.py](test/passes/tile/test_reduce.py)
    - 功能实现: [kernel_gen/passes/tile/reduce.py](kernel_gen/passes/tile/reduce.py)
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: KernelMatmulOp, rewriter: PatternRewriter, /) -> None:
        if "tile.analysis" not in op.attributes:
            return
        block = op.parent_block()
        if block is None:
            return
        parent_op = block.parent_op()
        if not isinstance(parent_op, func.FuncOp):
            return

        operands = [SSAValue.get(operand) for operand in op.operands]
        if len(operands) < 3:
            return
        out, lhs, rhs = operands[0], operands[1], operands[2]
        if not (
            isinstance(out.type, NnMemoryType)
            and isinstance(lhs.type, NnMemoryType)
            and isinstance(rhs.type, NnMemoryType)
        ):
            return
        if len(out.type.shape.data) != 2 or len(lhs.type.shape.data) != 2 or len(rhs.type.shape.data) != 2:
            return

        matmul_ops = [candidate for candidate in block.ops if isinstance(candidate, KernelMatmulOp)]
        matmul_index = matmul_ops.index(op)
        tile_r_name = f"TILE_R{matmul_index}"

        analysis_attr = op.attributes.get("tile.analysis")
        if not isinstance(analysis_attr, ArrayAttr):
            raise_pass_contract_error(
                "TilePassUnsupportedOp",
                f"function {parent_op.sym_name.data} requires tile.analysis before tile-reduce",
            )

        space_attr = op.attributes.get("space")
        space = space_attr if isinstance(space_attr, NnMemorySpaceAttr) else out.type.space
        reduce_tile_exprs = ArrayAttr(
            [
                ArrayAttr([StringAttr(""), StringAttr("")]),
                ArrayAttr([StringAttr(""), StringAttr(tile_r_name)]),
                ArrayAttr([StringAttr(tile_r_name), StringAttr("")]),
            ]
        )

        shape_source = out
        top_level_consumer: KernelBinaryElewiseOp | None = None
        for use in out.uses:
            if isinstance(use.operation, KernelBinaryElewiseOp) and use.operation.parent_block() is block:
                top_level_consumer = use.operation
                shape_source = SSAValue.get(use.operation.out)
                break

        if isinstance(out.owner, DmaAllocOp) and top_level_consumer is None:
            raise_pass_contract_error(
                "TilePassUnsupportedOp",
                f"function {parent_op.sym_name.data} needs a stable output memory to derive non-reduce dims",
            )

        tile_r = TunerParamOp(SymbolValueType.from_expr(tile_r_name))
        tile_r.result.name_hint = tile_r_name.replace("TILE_", "").lower()
        zero = UnregisteredOp.with_name("symbol.const").create(
            operands=[],
            result_types=[SymbolValueType.from_expr("0")],
            properties={"value": IntegerAttr(0, 64)},
        )
        dim_m = SymbolGetDimOp(shape_source, 0)
        dim_n = SymbolGetDimOp(shape_source, 1)
        dim_k = SymbolGetDimOp(lhs, 1)

        allocs_to_rewrite: list[DmaAllocOp] = []
        if top_level_consumer is not None:
            for candidate in block.ops:
                if candidate is op:
                    break
                if isinstance(candidate, DmaBroadcastOp):
                    broadcast_target = SSAValue.get(candidate.target)
                    if isinstance(broadcast_target.owner, DmaAllocOp):
                        allocs_to_rewrite.append(broadcast_target.owner)
        if isinstance(out.owner, DmaAllocOp) and out.owner not in allocs_to_rewrite:
            allocs_to_rewrite.append(out.owner)

        if allocs_to_rewrite:
            block.insert_ops_before([dim_m, dim_n], allocs_to_rewrite[0])
            for alloc_op in allocs_to_rewrite:
                replacement = DmaAllocOp([dim_m.result, dim_n.result], alloc_op.result.type)
                block.insert_ops_before([replacement], alloc_op)
                alloc_op.result.replace_all_uses_with(replacement.result)
                if alloc_op is out.owner:
                    out = replacement.result
                block.erase_op(alloc_op)
            dead_get_dims: list[SymbolGetDimOp] = []
            for candidate in block.ops:
                if candidate is op:
                    break
                if isinstance(candidate, SymbolGetDimOp) and not candidate.result.uses:
                    dead_get_dims.append(candidate)
            for dead_get_dim in dead_get_dims:
                block.erase_op(dead_get_dim)
            block.insert_ops_before([tile_r, zero, dim_k], op)
        else:
            block.insert_ops_before([tile_r, zero, dim_m, dim_n, dim_k], op)

        if out.type.element_type == i32:
            block.insert_ops_before([DmaFillOp(out, zero.results[0])], op)
        else:
            block.insert_ops_before(
                [
                    UnregisteredOp.with_name("dma.fill").create(
                        operands=[out, zero.results[0]],
                        result_types=[],
                    )
                ],
                op,
            )

        reduce_block = Block(
            arg_types=[
                SymbolIterType.from_bounds(
                    zero.results[0].type.expr.expr.data,
                    dim_k.result.type.expr.expr.data,
                    tile_r.result.type.expr.expr.data,
                )
            ]
        )
        reduce_loop = SymbolForOp(zero.results[0], dim_k.result, tile_r.result, reduce_block)
        block.insert_ops_before([reduce_loop], op)

        const_one = UnregisteredOp.with_name("symbol.const").create(
            operands=[],
            result_types=[SymbolValueType.from_expr("1")],
            properties={"value": IntegerAttr(1, 64)},
        )
        reduce_block.add_op(const_one)

        m_expr = dim_m.result.type.expr.expr.data
        n_expr = dim_n.result.type.expr.expr.data
        m_attr = SymbolExprAttr.from_expr(m_expr)
        n_attr = SymbolExprAttr.from_expr(n_expr)
        tile_r_attr = SymbolExprAttr.from_expr(tile_r_name)

        lhs_view = DmaViewOp(
            lhs,
            [zero.results[0], reduce_block.args[0]],
            [dim_m.result, tile_r.result],
            [const_one.results[0], const_one.results[0]],
            NnMemoryType(
                ArrayAttr([m_attr, tile_r_attr]),
                ArrayAttr([SymbolExprAttr.from_expr("1"), SymbolExprAttr.from_expr("1")]),
                lhs.type.element_type,
                lhs.type.space,
            ),
        )
        rhs_view = DmaViewOp(
            rhs,
            [reduce_block.args[0], zero.results[0]],
            [tile_r.result, dim_n.result],
            [const_one.results[0], const_one.results[0]],
            NnMemoryType(
                ArrayAttr([tile_r_attr, n_attr]),
                ArrayAttr([SymbolExprAttr.from_expr("1"), SymbolExprAttr.from_expr("1")]),
                rhs.type.element_type,
                rhs.type.space,
            ),
        )
        reduce_block.add_ops([lhs_view, rhs_view])

        tmp_alloc = DmaAllocOp([dim_m.result, dim_n.result], out.type)
        reduce_block.add_op(tmp_alloc)
        if out.type.element_type == i32:
            reduce_block.add_op(DmaFillOp(tmp_alloc.result, zero.results[0]))
        else:
            reduce_block.add_op(
                UnregisteredOp.with_name("dma.fill").create(
                    operands=[tmp_alloc.result, zero.results[0]],
                    result_types=[],
                )
            )
        reduce_block.add_op((tmp_matmul := KernelMatmulOp(tmp_alloc.result, lhs_view.result, rhs_view.result, space)))
        tmp_matmul.attributes["tile.analysis"] = analysis_attr
        tmp_matmul.attributes["tile.tile_exprs"] = reduce_tile_exprs
        reduce_block.add_op(
            KernelBinaryElewiseOp(
                out,
                tmp_alloc.result,
                out,
                kind="add",
                space=space,
            )
        )

        block.erase_op(op)
        rewriter.notify_op_modified(parent_op)


def get_tile_reduce_pass_patterns() -> list[RewritePattern]:
    """返回 `tile-reduce` pass 使用的公开 pattern 列表。


    功能说明:
    - 为外部测试、组合 pass 和公开 API 提供稳定的 pattern 构造入口。
    - 当前只公开 `TileReduceMatmulPattern`。

    使用示例:
    - patterns = get_tile_reduce_pass_patterns()

    关联文件:
    - spec: [spec/pass/tile/reduce.md](spec/pass/tile/reduce.md)
    - test: [test/passes/tile/test_reduce.py](test/passes/tile/test_reduce.py)
    - 功能实现: [kernel_gen/passes/tile/reduce.py](kernel_gen/passes/tile/reduce.py)
    """

    return [TileReduceMatmulPattern()]


class TileReducePass(ModulePass):
    """`tile-reduce` 的公开 `ModulePass`。"""

    name = "tile-reduce"

    def __init__(self: "TileReducePass", fold: bool = True) -> None:
        """初始化 tile-reduce pass 公共选项。


        功能说明:
        - 记录 `fold` 开关，默认允许 pass 内 pattern walker 执行 folding。

        使用示例:
        - pass_obj = TileReducePass()
        - pass_obj = TileReducePass(fold=False)

        关联文件:
        - spec: [spec/pass/tile/reduce.md](spec/pass/tile/reduce.md)
        - test: [test/passes/tile/test_reduce.py](test/passes/tile/test_reduce.py)
        - 功能实现: [kernel_gen/passes/tile/reduce.py](kernel_gen/passes/tile/reduce.py)
        """

        self.fold = bool(fold)

    def apply(self: "TileReducePass", ctx: Context, module: ModuleOp) -> None:
        ensure_builtin_module(module)
        if ctx.get_optional_dialect(Symbol.name) is None:
            ctx.load_dialect(Symbol)
        has_matmul = False
        for op in module.walk():
            if not isinstance(op, KernelMatmulOp):
                continue
            block = op.parent_block()
            if block is None or not isinstance(block.parent_op(), func.FuncOp):
                continue
            has_matmul = True
            if "tile.analysis" not in op.attributes or "tile.tile_exprs" not in op.attributes:
                raise_pass_contract_error(
                    "TilePassUnsupportedOp",
                    f"function {block.parent_op().sym_name.data} requires tile.analysis and tile.tile_exprs before tile-reduce",
                )
        if not has_matmul:
            return
        PatternRewriteWalker(
            GreedyRewritePatternApplier(
                get_tile_reduce_pass_patterns(),
                ctx=ctx,
                folding_enabled=self.fold,
                dce_enabled=False,
            ),
            walk_regions_first=True,
        ).rewrite_module(module)


__all__ = [
    "TileReduceMatmulPattern",
    "TileReducePass",
    "get_tile_reduce_pass_patterns",
]
