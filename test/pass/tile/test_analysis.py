"""tile-analysis public API tests.

创建者: OpenAI Codex
最后一次更改: OpenAI Codex

功能说明:
- 覆盖 `kernel_gen.passes.tile.analysis` 的公开 pattern/getter/pass 合同。
- 锁定 `tile-analysis` 只为当前 op 补 `tile.analysis` 与 `tile.tile_exprs`，不生成 `symbol.for` 或 `dma.view`。

使用示例:
- pytest -q test/pass/tile/test_analysis.py

关联文件:
- spec: [spec/pass/tile/analysis.md](../../../spec/pass/tile/analysis.md)
- test: [test/pass/tile/test_analysis.py](../../../test/pass/tile/test_analysis.py)
- 功能实现: [kernel_gen/passes/tile/analysis.py](../../../kernel_gen/passes/tile/analysis.py)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, StringAttr
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import PatternRewriter

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

shared_module = importlib.import_module("test.pass.tile.shared")
tile_analysis_module = importlib.import_module("kernel_gen.passes.tile.analysis")
registry_module = importlib.import_module("kernel_gen.passes.registry")
package_module = importlib.import_module("kernel_gen.passes")

build_broadcast_module = shared_module.build_broadcast_module
build_elementwise_module = shared_module.build_elementwise_module
build_matmul_module = shared_module.build_matmul_module
collect_ops = shared_module.collect_ops
TileAnalysisPass = tile_analysis_module.TileAnalysisPass
TileAnalysisBinaryPattern = tile_analysis_module.TileAnalysisBinaryPattern
TileAnalysisBroadcastPattern = tile_analysis_module.TileAnalysisBroadcastPattern
TileAnalysisMatmulPattern = tile_analysis_module.TileAnalysisMatmulPattern
get_tile_analysis_pass_patterns = tile_analysis_module.get_tile_analysis_pass_patterns
build_registered_pass = registry_module.build_registered_pass
load_builtin_passes = registry_module.load_builtin_passes


def test_tile_analysis_public_api_surface_is_stable() -> None:
    """锁定 tile-analysis 的公开导出与 getter 顺序。"""

    assert package_module.TileAnalysisBinaryPattern is TileAnalysisBinaryPattern
    assert package_module.TileAnalysisBroadcastPattern is TileAnalysisBroadcastPattern
    assert package_module.TileAnalysisMatmulPattern is TileAnalysisMatmulPattern
    assert package_module.get_tile_analysis_pass_patterns is get_tile_analysis_pass_patterns
    assert [type(pattern) for pattern in get_tile_analysis_pass_patterns()] == [
        TileAnalysisBinaryPattern,
        TileAnalysisBroadcastPattern,
        TileAnalysisMatmulPattern,
    ]


def test_tile_analysis_binary_pattern_adds_only_analysis_attrs() -> None:
    """锁定 BinaryPattern 只补 analysis attrs。"""

    module = build_elementwise_module()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    kernel_op = next(op for op in func_op.body.block.ops if op.name == "kernel.binary_elewise")

    TileAnalysisBinaryPattern().match_and_rewrite(kernel_op, PatternRewriter(kernel_op))

    ops = collect_ops(module)
    assert "tile.analysis" in kernel_op.attributes
    assert "tile.tile_exprs" in kernel_op.attributes
    assert not [op for op in ops if op.name == "symbol.for"]
    assert not [op for op in ops if op.name == "dma.view"]


def test_tile_analysis_broadcast_pattern_marks_expand_roles() -> None:
    """锁定 BroadcastPattern 的角色矩阵与空 tile 表达式。"""

    module = build_broadcast_module()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    broadcast_op = next(op for op in func_op.body.block.ops if op.name == "dma.broadcast")

    TileAnalysisBroadcastPattern().match_and_rewrite(broadcast_op, PatternRewriter(broadcast_op))

    expected_roles = ArrayAttr(
        [
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("expand"), StringAttr("elewise")]),
        ]
    )
    expected_exprs = ArrayAttr(
        [
            ArrayAttr([StringAttr(""), StringAttr("")]),
            ArrayAttr([StringAttr(""), StringAttr("")]),
        ]
    )

    assert broadcast_op.attributes["tile.analysis"] == expected_roles
    assert broadcast_op.attributes["tile.tile_exprs"] == expected_exprs


def test_tile_analysis_matmul_pattern_marks_reduce_roles() -> None:
    """锁定 MatmulPattern 的角色矩阵与空 tile 表达式。"""

    module = build_matmul_module()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    matmul_op = next(op for op in func_op.body.block.ops if op.name == "kernel.matmul")

    TileAnalysisMatmulPattern().match_and_rewrite(matmul_op, PatternRewriter(matmul_op))

    expected_roles = ArrayAttr(
        [
            ArrayAttr([StringAttr("elewise"), StringAttr("reduce")]),
            ArrayAttr([StringAttr("reduce"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
        ]
    )
    expected_exprs = ArrayAttr(
        [
            ArrayAttr([StringAttr(""), StringAttr("")]),
            ArrayAttr([StringAttr(""), StringAttr("")]),
            ArrayAttr([StringAttr(""), StringAttr("")]),
        ]
    )

    assert matmul_op.attributes["tile.analysis"] == expected_roles
    assert matmul_op.attributes["tile.tile_exprs"] == expected_exprs


def test_tile_analysis_pass_is_registry_constructible_module_pass() -> None:
    """锁定 TileAnalysisPass 的 pass 合同与无 rewrite 副作用。"""

    module = build_elementwise_module()
    load_builtin_passes()
    pass_obj = build_registered_pass("tile-analysis")

    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.__class__ is TileAnalysisPass
    pass_obj.apply(Context(), module)

    ops = collect_ops(module)
    kernel_op = next(op for op in ops if op.name == "kernel.binary_elewise")
    assert "tile.analysis" in kernel_op.attributes
    assert "tile.tile_exprs" in kernel_op.attributes
    assert not [op for op in ops if op.name == "symbol.for"]
    assert not [op for op in ops if op.name == "dma.view"]
