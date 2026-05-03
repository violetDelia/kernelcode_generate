"""tile-elewise public API tests.


功能说明:
- 覆盖 `kernel_gen.passes.tile.elewise` 的公开 pattern/getter/pass 合同。
- 锁定 `tile-elewise` 在 `tile-analysis` 之后会写出显式 `symbol.for + dma.view` 结构。

使用示例:
- pytest -q test/passes/tile/test_elewise.py

关联文件:
- spec: [spec/pass/tile/elewise.md](../../../spec/pass/tile/elewise.md)
- test: [test/passes/tile/test_elewise.py](../../../test/passes/tile/test_elewise.py)
- 功能实现: [kernel_gen/passes/tile/elewise.py](../../../kernel_gen/passes/tile/elewise.py)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, StringAttr, i1, i32
from xdsl.ir import Block, Region
from xdsl.parser import Parser
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import PatternRewriter

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

shared_module = importlib.import_module("test.passes.tile.test_shared")
tile_analysis_module = importlib.import_module("kernel_gen.passes.tile.analysis")
tile_elewise_module = importlib.import_module("kernel_gen.passes.tile.elewise")
registry_module = importlib.import_module("kernel_gen.passes.registry")
package_module = importlib.import_module("kernel_gen.passes")

build_broadcast_module = shared_module.build_broadcast_module
build_elementwise_module = shared_module.build_elementwise_module
build_fc_chain_module = shared_module.build_fc_chain_module
build_matmul_module = shared_module.build_matmul_module
collect_ops = shared_module.collect_ops
make_memory_type = shared_module.make_memory_type
TileAnalysisPass = tile_analysis_module.TileAnalysisPass
TileElewiseBinaryPattern = tile_elewise_module.TileElewiseBinaryPattern
TileElewiseBroadcastPattern = tile_elewise_module.TileElewiseBroadcastPattern
TileElewiseMatmulPattern = tile_elewise_module.TileElewiseMatmulPattern
TileElewisePass = tile_elewise_module.TileElewisePass
get_tile_elewise_pass_patterns = tile_elewise_module.get_tile_elewise_pass_patterns
build_registered_pass = registry_module.build_registered_pass
load_builtin_passes = registry_module.load_builtin_passes

from kernel_gen.dialect.dma import DmaBroadcastOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp, KernelMatmulOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.core.context import build_default_context


def test_tile_elewise_public_api_surface_is_stable() -> None:
    """锁定 tile-elewise 的公开导出与 getter 顺序。"""

    assert package_module.TileElewiseBinaryPattern is TileElewiseBinaryPattern
    assert package_module.TileElewiseBroadcastPattern is TileElewiseBroadcastPattern
    assert package_module.TileElewiseMatmulPattern is TileElewiseMatmulPattern
    assert package_module.get_tile_elewise_pass_patterns is get_tile_elewise_pass_patterns
    assert [type(pattern) for pattern in get_tile_elewise_pass_patterns()] == [
        TileElewiseBinaryPattern,
        TileElewiseBroadcastPattern,
        TileElewiseMatmulPattern,
    ]


def test_tile_elewise_binary_pattern_rewrites_single_add_op() -> None:
    """锁定 BinaryPattern 会为 elementwise 写出 loop/view 结构。"""

    module = build_elementwise_module()
    TileAnalysisPass().apply(Context(), module)
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    kernel_op = next(op for op in func_op.body.block.ops if op.name == "kernel.binary_elewise")

    TileElewiseBinaryPattern().match_and_rewrite(kernel_op, PatternRewriter(kernel_op))

    ops = collect_ops(module)
    rewritten = [op for op in ops if op.name == "kernel.binary_elewise"]
    assert len([op for op in ops if op.name == "symbol.for"]) == 2
    assert len([op for op in ops if op.name == "dma.view"]) == 3
    assert len(rewritten) == 1
    assert rewritten[0].attributes["tile.tile_exprs"] == ArrayAttr(
        [
            ArrayAttr([StringAttr("TILE_D0"), StringAttr("TILE_D1")]),
            ArrayAttr([StringAttr("TILE_D0"), StringAttr("TILE_D1")]),
            ArrayAttr([StringAttr("TILE_D0"), StringAttr("TILE_D1")]),
        ]
    )


def test_tile_elewise_binary_pattern_public_compare_and_boundary_matrix() -> None:
    """锁定 binary pattern 的 compare rewrite、no-op 与公开错误边界。"""

    mem_type = make_memory_type(["M", "N"])
    bool_mem_type = NnMemoryType(mem_type.shape, mem_type.stride, i1, NnMemorySpaceAttr.from_name("global"))
    block = Block(arg_types=[mem_type, mem_type, bool_mem_type])
    space = NnMemorySpaceAttr.from_name("global")
    compare_op = KernelBinaryElewiseOp(block.args[2], block.args[0], block.args[1], kind="eq", space=space)
    compare_op.attributes["tile.analysis"] = ArrayAttr(
        [
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
        ]
    )
    block.add_ops([compare_op, func.ReturnOp()])
    module = ModuleOp(
        [
            func.FuncOp(
                "tile_compare",
                FunctionType.from_lists([mem_type, mem_type, bool_mem_type], []),
                Region(block),
            )
        ]
    )

    TileElewiseBinaryPattern().match_and_rewrite(compare_op, PatternRewriter(compare_op))

    rewritten = next(op for op in collect_ops(module) if op.name == "kernel.binary_elewise")
    assert len([op for op in collect_ops(module) if op.name == "dma.view"]) == 3
    assert [operand.type.element_type for operand in rewritten.operands] == [i1, i32, i32]

    rank1_mem_type = make_memory_type(["M"])
    rank1_block = Block(arg_types=[rank1_mem_type, rank1_mem_type, rank1_mem_type])
    rank1_op = KernelBinaryElewiseOp(rank1_block.args[2], rank1_block.args[0], rank1_block.args[1], kind="add", space=space)
    rank1_op.attributes["tile.analysis"] = ArrayAttr(
        [ArrayAttr([StringAttr("elewise")]), ArrayAttr([StringAttr("elewise")]), ArrayAttr([StringAttr("elewise")])]
    )
    rank1_block.add_ops([rank1_op, func.ReturnOp()])
    rank1_module = ModuleOp(
        [
            func.FuncOp(
                "tile_rank1_binary",
                FunctionType.from_lists([rank1_mem_type, rank1_mem_type, rank1_mem_type], []),
                Region(rank1_block),
            )
        ]
    )
    TileElewiseBinaryPattern().match_and_rewrite(rank1_op, PatternRewriter(rank1_op))
    assert [op.name for op in collect_ops(rank1_module)].count("symbol.for") == 1
    assert [op.name for op in collect_ops(rank1_module)].count("dma.view") == 3

    rank3_mem_type = make_memory_type(["B", "M", "N"])
    rank3_block = Block(arg_types=[rank3_mem_type, rank3_mem_type, rank3_mem_type])
    rank3_op = KernelBinaryElewiseOp(rank3_block.args[2], rank3_block.args[0], rank3_block.args[1], kind="mul", space=space)
    rank3_op.attributes["tile.analysis"] = ArrayAttr(
        [
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise"), StringAttr("elewise")]),
        ]
    )
    rank3_block.add_ops([rank3_op, func.ReturnOp()])
    rank3_module = ModuleOp(
        [
            func.FuncOp(
                "tile_rank3_binary",
                FunctionType.from_lists([rank3_mem_type, rank3_mem_type, rank3_mem_type], []),
                Region(rank3_block),
            )
        ]
    )
    TileElewiseBinaryPattern().match_and_rewrite(rank3_op, PatternRewriter(rank3_op))
    rank3_views = [op for op in collect_ops(rank3_module) if op.name == "dma.view"]
    assert [op.name for op in collect_ops(rank3_module)].count("symbol.for") == 3
    assert all(view.result.type.shape.data == ArrayAttr(
        [StringAttr("TILE_D0"), StringAttr("TILE_D1"), StringAttr("TILE_D2")]
    ).data for view in rank3_views)

    no_analysis_module = build_elementwise_module()
    no_analysis_op = next(op for op in collect_ops(no_analysis_module) if op.name == "kernel.binary_elewise")
    TileElewiseBinaryPattern().match_and_rewrite(no_analysis_op, PatternRewriter(no_analysis_op))
    assert [op.name for op in collect_ops(no_analysis_module)].count("symbol.for") == 0

    scalar_mem_type = NnMemoryType(ArrayAttr([]), ArrayAttr([]), i32, space)
    scalar_block = Block(arg_types=[scalar_mem_type, scalar_mem_type, scalar_mem_type])
    scalar_op = KernelBinaryElewiseOp(scalar_block.args[2], scalar_block.args[0], scalar_block.args[1], kind="add", space=space)
    scalar_op.attributes["tile.analysis"] = ArrayAttr([ArrayAttr([]), ArrayAttr([]), ArrayAttr([])])
    scalar_block.add_ops([scalar_op, func.ReturnOp()])
    scalar_module = ModuleOp(
        [
            func.FuncOp(
                "tile_scalar_noop",
                FunctionType.from_lists([scalar_mem_type, scalar_mem_type, scalar_mem_type], []),
                Region(scalar_block),
            )
        ]
    )
    TileElewiseBinaryPattern().match_and_rewrite(scalar_op, PatternRewriter(scalar_op))
    assert [op.name for op in collect_ops(scalar_module)].count("symbol.for") == 0

    bad_attr_block = Block(arg_types=[mem_type, mem_type, mem_type])
    bad_attr_op = KernelBinaryElewiseOp(bad_attr_block.args[2], bad_attr_block.args[0], bad_attr_block.args[1], kind="add", space=space)
    bad_attr_op.attributes["tile.analysis"] = StringAttr("bad")
    bad_attr_block.add_ops([bad_attr_op, func.ReturnOp()])
    ModuleOp(
        [
            func.FuncOp(
                "tile_bad_analysis_attr",
                FunctionType.from_lists([mem_type, mem_type, mem_type], []),
                Region(bad_attr_block),
            )
        ]
    )
    with pytest.raises(Exception, match="TilePassUnsupportedOp"):
        TileElewiseBinaryPattern().match_and_rewrite(bad_attr_op, PatternRewriter(bad_attr_op))

    bad_row_block = Block(arg_types=[mem_type, mem_type, mem_type])
    bad_row_op = KernelBinaryElewiseOp(bad_row_block.args[2], bad_row_block.args[0], bad_row_block.args[1], kind="add", space=space)
    bad_row_op.attributes["tile.analysis"] = ArrayAttr([StringAttr("bad")])
    bad_row_block.add_ops([bad_row_op, func.ReturnOp()])
    ModuleOp(
        [
            func.FuncOp(
                "tile_bad_analysis_row",
                FunctionType.from_lists([mem_type, mem_type, mem_type], []),
                Region(bad_row_block),
            )
        ]
    )
    with pytest.raises(Exception, match="TilePassUnsupportedOp"):
        TileElewiseBinaryPattern().match_and_rewrite(bad_row_op, PatternRewriter(bad_row_op))

    mismatch_block = Block(arg_types=[mem_type, rank1_mem_type, mem_type])
    mismatch_op = KernelBinaryElewiseOp(
        mismatch_block.args[2],
        mismatch_block.args[0],
        mismatch_block.args[1],
        kind="add",
        space=space,
    )
    mismatch_op.attributes["tile.analysis"] = ArrayAttr(
        [
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("elewise")]),
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
        ]
    )
    mismatch_block.add_ops([mismatch_op, func.ReturnOp()])
    ModuleOp(
        [
            func.FuncOp(
                "tile_rank_mismatch",
                FunctionType.from_lists([mem_type, rank1_mem_type, mem_type], []),
                Region(mismatch_block),
            )
        ]
    )
    with pytest.raises(Exception, match="TilePassRankMismatch"):
        TileElewiseBinaryPattern().match_and_rewrite(mismatch_op, PatternRewriter(mismatch_op))


def test_tile_elewise_broadcast_pattern_rewrites_single_broadcast_op() -> None:
    """锁定 BroadcastPattern 会为 broadcast 写出 loop/view 结构。"""

    module = build_broadcast_module()
    TileAnalysisPass().apply(Context(), module)
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    broadcast_op = next(op for op in func_op.body.block.ops if op.name == "dma.broadcast")

    TileElewiseBroadcastPattern().match_and_rewrite(broadcast_op, PatternRewriter(broadcast_op))

    ops = collect_ops(module)
    rewritten = [op for op in ops if op.name == "dma.broadcast"]
    assert len([op for op in ops if op.name == "symbol.for"]) == 1
    assert len([op for op in ops if op.name == "dma.view"]) == 2
    assert len(rewritten) == 1
    assert rewritten[0].attributes["tile.tile_exprs"] == ArrayAttr(
        [
            ArrayAttr([StringAttr(""), StringAttr("TILE_D0")]),
            ArrayAttr([StringAttr(""), StringAttr("TILE_D0")]),
        ]
    )


def test_tile_elewise_broadcast_pattern_public_boundary_matrix() -> None:
    """锁定 broadcast pattern 的 no-op、expand 与公开 analysis 错误边界。"""

    no_analysis_module = build_broadcast_module()
    no_analysis_op = next(op for op in collect_ops(no_analysis_module) if op.name == "dma.broadcast")
    TileElewiseBroadcastPattern().match_and_rewrite(no_analysis_op, PatternRewriter(no_analysis_op))
    assert [op.name for op in collect_ops(no_analysis_module)].count("symbol.for") == 0

    space = NnMemorySpaceAttr.from_name("global")
    scalar_mem_type = NnMemoryType(ArrayAttr([]), ArrayAttr([]), i32, space)
    scalar_block = Block(arg_types=[scalar_mem_type, scalar_mem_type])
    scalar_op = DmaBroadcastOp(scalar_block.args[0], scalar_block.args[1])
    scalar_op.attributes["tile.analysis"] = ArrayAttr([ArrayAttr([]), ArrayAttr([])])
    scalar_block.add_ops([scalar_op, func.ReturnOp()])
    scalar_module = ModuleOp(
        [
            func.FuncOp(
                "tile_scalar_broadcast_noop",
                FunctionType.from_lists([scalar_mem_type, scalar_mem_type], []),
                Region(scalar_block),
            )
        ]
    )
    TileElewiseBroadcastPattern().match_and_rewrite(scalar_op, PatternRewriter(scalar_op))
    assert [op.name for op in collect_ops(scalar_module)].count("symbol.for") == 0

    all_expand_mem_type = make_memory_type(["M"])
    all_expand_block = Block(arg_types=[all_expand_mem_type, all_expand_mem_type])
    all_expand_op = DmaBroadcastOp(all_expand_block.args[0], all_expand_block.args[1])
    all_expand_op.attributes["tile.analysis"] = ArrayAttr(
        [ArrayAttr([StringAttr("expand")]), ArrayAttr([StringAttr("expand")])]
    )
    all_expand_block.add_ops([all_expand_op, func.ReturnOp()])
    all_expand_module = ModuleOp(
        [
            func.FuncOp(
                "tile_all_expand_broadcast",
                FunctionType.from_lists([all_expand_mem_type, all_expand_mem_type], []),
                Region(all_expand_block),
            )
        ]
    )
    TileElewiseBroadcastPattern().match_and_rewrite(all_expand_op, PatternRewriter(all_expand_op))
    assert [op.name for op in collect_ops(all_expand_module)].count("symbol.for") == 0
    assert all_expand_op.attributes["tile.tile_exprs"] == ArrayAttr(
        [ArrayAttr([StringAttr("")]), ArrayAttr([StringAttr("")])]
    )

    target_type = make_memory_type(["B", "M", "N"])
    source_type = make_memory_type(["M", "N"])
    expand_block = Block(arg_types=[target_type, source_type])
    expand_op = DmaBroadcastOp(expand_block.args[0], expand_block.args[1])
    expand_op.attributes["tile.analysis"] = ArrayAttr(
        [
            ArrayAttr([StringAttr("expand"), StringAttr("elewise"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("expand"), StringAttr("elewise"), StringAttr("elewise")]),
        ]
    )
    expand_block.add_ops([expand_op, func.ReturnOp()])
    expand_module = ModuleOp(
        [
            func.FuncOp(
                "tile_expand_broadcast",
                FunctionType.from_lists([target_type, source_type], []),
                Region(expand_block),
            )
        ]
    )
    TileElewiseBroadcastPattern().match_and_rewrite(expand_op, PatternRewriter(expand_op))
    views = [op for op in collect_ops(expand_module) if op.name == "dma.view"]
    assert len([op for op in collect_ops(expand_module) if op.name == "symbol.for"]) == 2
    assert len(views) == 2
    assert views[0].result.type.shape.data == ArrayAttr(
        [IntAttr(1), StringAttr("TILE_D0"), StringAttr("TILE_D1")]
    ).data
    assert views[1].result.type.shape.data == ArrayAttr([StringAttr("TILE_D0"), StringAttr("TILE_D1")]).data

    partial_target_type = make_memory_type(["M", "N"])
    partial_source_type = make_memory_type(["M", "N"])
    partial_block = Block(arg_types=[partial_target_type, partial_source_type])
    partial_op = DmaBroadcastOp(partial_block.args[0], partial_block.args[1])
    partial_op.attributes["tile.analysis"] = ArrayAttr(
        [
            ArrayAttr([StringAttr("expand"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
        ]
    )
    partial_block.add_ops([partial_op, func.ReturnOp()])
    partial_module = ModuleOp(
        [
            func.FuncOp(
                "tile_partial_expand_broadcast",
                FunctionType.from_lists([partial_target_type, partial_source_type], []),
                Region(partial_block),
            )
        ]
    )
    TileElewiseBroadcastPattern().match_and_rewrite(partial_op, PatternRewriter(partial_op))
    partial_views = [op for op in collect_ops(partial_module) if op.name == "dma.view"]
    assert len([op for op in collect_ops(partial_module) if op.name == "symbol.for"]) == 1
    assert partial_views[0].result.type.shape.data == ArrayAttr([IntAttr(1), StringAttr("TILE_D0")]).data
    assert partial_views[1].result.type.shape.data == ArrayAttr([StringAttr("M"), StringAttr("TILE_D0")]).data

    bad_len_block = Block(arg_types=[target_type, source_type])
    bad_len_op = DmaBroadcastOp(bad_len_block.args[0], bad_len_block.args[1])
    bad_len_op.attributes["tile.analysis"] = ArrayAttr([ArrayAttr([StringAttr("elewise")])])
    bad_len_block.add_ops([bad_len_op, func.ReturnOp()])
    ModuleOp(
        [
            func.FuncOp(
                "tile_broadcast_bad_len",
                FunctionType.from_lists([target_type, source_type], []),
                Region(bad_len_block),
            )
        ]
    )
    with pytest.raises(Exception, match="TilePassUnsupportedOp"):
        TileElewiseBroadcastPattern().match_and_rewrite(bad_len_op, PatternRewriter(bad_len_op))

    bad_row_block = Block(arg_types=[target_type, source_type])
    bad_row_op = DmaBroadcastOp(bad_row_block.args[0], bad_row_block.args[1])
    bad_row_op.attributes["tile.analysis"] = ArrayAttr([StringAttr("bad"), StringAttr("bad")])
    bad_row_block.add_ops([bad_row_op, func.ReturnOp()])
    ModuleOp(
        [
            func.FuncOp(
                "tile_broadcast_bad_row",
                FunctionType.from_lists([target_type, source_type], []),
                Region(bad_row_block),
            )
        ]
    )
    with pytest.raises(Exception, match="TilePassUnsupportedOp"):
        TileElewiseBroadcastPattern().match_and_rewrite(bad_row_op, PatternRewriter(bad_row_op))


def test_tile_elewise_matmul_pattern_rewrites_single_matmul_op() -> None:
    """锁定 MatmulPattern 会为 matmul 写出 loop/view 结构。"""

    module = build_matmul_module()
    TileAnalysisPass().apply(Context(), module)
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    matmul_op = next(op for op in func_op.body.block.ops if op.name == "kernel.matmul")

    TileElewiseMatmulPattern().match_and_rewrite(matmul_op, PatternRewriter(matmul_op))

    ops = collect_ops(module)
    rewritten = [op for op in ops if op.name == "kernel.matmul"]
    views = [op for op in ops if op.name == "dma.view"]
    assert len([op for op in ops if op.name == "symbol.for"]) == 2
    assert len(views) == 3
    assert len(rewritten) == 1
    assert rewritten[0].attributes["tile.tile_exprs"] == ArrayAttr(
        [
            ArrayAttr([StringAttr("TILE_D0"), StringAttr("")]),
            ArrayAttr([StringAttr(""), StringAttr("TILE_D1")]),
            ArrayAttr([StringAttr("TILE_D0"), StringAttr("TILE_D1")]),
        ]
    )
    lhs_view_type = views[0].results[0].type
    rhs_view_type = views[1].results[0].type
    out_view_type = views[2].results[0].type
    assert isinstance(lhs_view_type, NnMemoryType)
    assert isinstance(rhs_view_type, NnMemoryType)
    assert isinstance(out_view_type, NnMemoryType)
    assert lhs_view_type.shape.data == ArrayAttr([StringAttr("TILE_D0"), StringAttr("K")]).data
    assert lhs_view_type.stride.data == ArrayAttr([IntAttr(1), IntAttr(1)]).data
    assert rhs_view_type.shape.data == ArrayAttr([StringAttr("K"), StringAttr("TILE_D1")]).data
    assert rhs_view_type.stride.data == ArrayAttr([IntAttr(1), IntAttr(1)]).data
    assert out_view_type.shape.data == ArrayAttr([StringAttr("TILE_D0"), StringAttr("TILE_D1")]).data
    assert out_view_type.stride.data == ArrayAttr([IntAttr(1), IntAttr(1)]).data


def test_tile_elewise_pass_rewrites_multiple_top_level_plans() -> None:
    """锁定 TileElewisePass 会处理同一函数中的多个顶层 plan。"""

    mem_type = make_memory_type(["M", "N"])
    block = Block(arg_types=[mem_type, mem_type, mem_type, mem_type])
    space = NnMemorySpaceAttr.from_name("global")
    block.add_ops(
        [
            KernelBinaryElewiseOp(block.args[2], block.args[0], block.args[1], kind="add", space=space),
            KernelBinaryElewiseOp(block.args[3], block.args[1], block.args[0], kind="mul", space=space),
            func.ReturnOp(),
        ]
    )
    func_op = func.FuncOp(
        "tile_elewise_multi_plan",
        FunctionType.from_lists([mem_type, mem_type, mem_type, mem_type], []),
        Region(block),
    )
    module = ModuleOp([func_op])
    TileAnalysisPass().apply(Context(), module)

    load_builtin_passes()
    pass_obj = build_registered_pass("tile-elewise")
    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.__class__ is TileElewisePass
    pass_obj.apply(Context(), module)

    ops = collect_ops(module)
    assert len([op for op in ops if op.name == "kernel.binary_elewise"]) == 2
    assert len([op for op in ops if op.name == "symbol.for"]) == 4
    assert len([op for op in ops if op.name == "dma.view"]) == 6


def test_tile_elewise_pass_fc_chain_keeps_reduce_axis_until_tile_reduce() -> None:
    """锁定 fc 链里的 matmul 只 tile `M/N`，不为 reduce 维写 elewise tile。"""

    module = build_fc_chain_module()
    TileAnalysisPass().apply(Context(), module)
    TileElewisePass().apply(Context(), module)

    ops = collect_ops(module)
    matmul_ops = [op for op in ops if op.name == "kernel.matmul"]
    assert len([op for op in ops if op.name == "symbol.for"]) == 5
    assert len(matmul_ops) == 1
    assert matmul_ops[0].attributes["tile.tile_exprs"] == ArrayAttr(
        [
            ArrayAttr([StringAttr("TILE_D0"), StringAttr("")]),
            ArrayAttr([StringAttr(""), StringAttr("TILE_D1")]),
            ArrayAttr([StringAttr("TILE_D0"), StringAttr("TILE_D1")]),
        ]
    )


def test_tile_elewise_matmul_pattern_accepts_legacy_operand_order_without_reordering() -> None:
    """锁定 legacy `lhs/rhs/out` 文本输入可直接重写，并保持原 operand 位置。"""

    ctx = build_default_context()
    module = Parser(
        ctx,
        """
builtin.module {
  func.func @tile_matmul_legacy(
      %lhs : !nn.memory<[4, 8], [8, 1], i32, #nn.space<global>>,
      %rhs : !nn.memory<[8, 16], [16, 1], i32, #nn.space<global>>,
      %out : !nn.memory<[4, 16], [16, 1], i32, #nn.space<global>>) {
    "kernel.matmul"(%lhs, %rhs, %out) {space = #nn.space<global>, tile.analysis = [["elewise", "reduce"], ["reduce", "elewise"], ["elewise", "elewise"]], tile.tile_exprs = [["", ""], ["", ""], ["", ""]]} : (!nn.memory<[4, 8], [8, 1], i32, #nn.space<global>>, !nn.memory<[8, 16], [16, 1], i32, #nn.space<global>>, !nn.memory<[4, 16], [16, 1], i32, #nn.space<global>>) -> ()
    func.return
  }
}
""",
    ).parse_module()

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    matmul_op = next(op for op in func_op.body.block.ops if op.name == "kernel.matmul")
    TileElewiseMatmulPattern().match_and_rewrite(matmul_op, PatternRewriter(matmul_op))

    rewritten = next(op for op in collect_ops(module) if op.name == "kernel.matmul")
    lhs_type = rewritten.operands[0].type
    rhs_type = rewritten.operands[1].type
    out_type = rewritten.operands[2].type
    assert isinstance(lhs_type, NnMemoryType)
    assert isinstance(rhs_type, NnMemoryType)
    assert isinstance(out_type, NnMemoryType)
    assert lhs_type.shape.data == ArrayAttr([StringAttr("TILE_D0"), IntAttr(8)]).data
    assert rhs_type.shape.data == ArrayAttr([IntAttr(8), StringAttr("TILE_D1")]).data
    assert out_type.shape.data == ArrayAttr([StringAttr("TILE_D0"), StringAttr("TILE_D1")]).data


def test_tile_elewise_matmul_pattern_public_noop_shape_boundaries() -> None:
    """锁定 matmul pattern 对缺失 analysis 与不匹配 shape 的公开 no-op 边界。"""

    no_analysis_module = build_matmul_module()
    no_analysis_op = next(op for op in collect_ops(no_analysis_module) if op.name == "kernel.matmul")
    TileElewiseMatmulPattern().match_and_rewrite(no_analysis_op, PatternRewriter(no_analysis_op))
    assert [op.name for op in collect_ops(no_analysis_module)].count("symbol.for") == 0

    space = NnMemorySpaceAttr.from_name("global")
    out_type = make_memory_type(["M", "N"])
    lhs_type = make_memory_type(["X", "K"])
    rhs_type = make_memory_type(["K", "Y"])
    mismatch_block = Block(arg_types=[out_type, lhs_type, rhs_type])
    mismatch_op = KernelMatmulOp(mismatch_block.args[0], mismatch_block.args[1], mismatch_block.args[2], space)
    mismatch_op.attributes["tile.analysis"] = ArrayAttr(
        [
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("elewise"), StringAttr("reduce")]),
            ArrayAttr([StringAttr("reduce"), StringAttr("elewise")]),
        ]
    )
    mismatch_block.add_ops([mismatch_op, func.ReturnOp()])
    mismatch_module = ModuleOp(
        [
            func.FuncOp(
                "tile_matmul_shape_mismatch",
                FunctionType.from_lists([out_type, lhs_type, rhs_type], []),
                Region(mismatch_block),
            )
        ]
    )
    TileElewiseMatmulPattern().match_and_rewrite(mismatch_op, PatternRewriter(mismatch_op))
    assert [op.name for op in collect_ops(mismatch_module)].count("symbol.for") == 0

    rank1_type = make_memory_type(["M"])
    rank1_block = Block(arg_types=[rank1_type, rank1_type, rank1_type])
    rank1_op = KernelMatmulOp(rank1_block.args[0], rank1_block.args[1], rank1_block.args[2], space)
    rank1_op.attributes["tile.analysis"] = ArrayAttr(
        [
            ArrayAttr([StringAttr("elewise")]),
            ArrayAttr([StringAttr("elewise")]),
            ArrayAttr([StringAttr("elewise")]),
        ]
    )
    rank1_block.add_ops([rank1_op, func.ReturnOp()])
    rank1_module = ModuleOp(
        [
            func.FuncOp(
                "tile_matmul_rank_mismatch",
                FunctionType.from_lists([rank1_type, rank1_type, rank1_type], []),
                Region(rank1_block),
            )
        ]
    )
    TileElewiseMatmulPattern().match_and_rewrite(rank1_op, PatternRewriter(rank1_op))
    assert [op.name for op in collect_ops(rank1_module)].count("symbol.for") == 0
