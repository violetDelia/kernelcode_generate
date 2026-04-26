"""tile-reduce public API tests.

创建者: OpenAI Codex
最后一次更改: OpenAI Codex

功能说明:
- 覆盖 `kernel_gen.passes.tile.reduce` 的公开 pattern/getter/pass 合同。
- 锁定 `tile-reduce` 会在 `tile-analysis` 之后写出“只切 reduce 轴”的 `symbol.for + dma.view + dma.fill` 结构。

使用示例:
- pytest -q test/pass/tile/test_reduce.py

关联文件:
- spec: [spec/pass/tile/reduce.md](../../../spec/pass/tile/reduce.md)
- test: [test/pass/tile/test_reduce.py](../../../test/pass/tile/test_reduce.py)
- 功能实现: [kernel_gen/passes/tile/reduce.py](../../../kernel_gen/passes/tile/reduce.py)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
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
tile_reduce_module = importlib.import_module("kernel_gen.passes.tile.reduce")
passes_common_module = importlib.import_module("kernel_gen.passes.common")
registry_module = importlib.import_module("kernel_gen.passes.registry")
package_module = importlib.import_module("kernel_gen.passes")

build_fc_chain_module = shared_module.build_fc_chain_module
build_matmul_module = shared_module.build_matmul_module
collect_ops = shared_module.collect_ops
TileAnalysisPass = tile_analysis_module.TileAnalysisPass
TileReduceMatmulPattern = tile_reduce_module.TileReduceMatmulPattern
TileReducePass = tile_reduce_module.TileReducePass
get_tile_reduce_pass_patterns = tile_reduce_module.get_tile_reduce_pass_patterns
PassContractError = passes_common_module.PassContractError
build_registered_pass = registry_module.build_registered_pass
load_builtin_passes = registry_module.load_builtin_passes

from kernel_gen.dialect.kernel import KernelMatmulOp


def tuner_param_names(module) -> list[str]:
    """提取 `module` 中 `tuner.param` 的名字。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 读取当前 `tile-reduce` 产出的 `symbol.int` 参数名。
    - 用于锁定 fc 链路只保留 `matmul` reduce 计划相关的 `tuner.param`。

    使用示例:
    - names = tuner_param_names(module)

    关联文件:
    - spec: [spec/pass/tile/reduce.md](../../../spec/pass/tile/reduce.md)
    - test: [test/pass/tile/test_reduce.py](../../../test/pass/tile/test_reduce.py)
    - 功能实现: [test/pass/tile/test_reduce.py](../../../test/pass/tile/test_reduce.py)
    """

    names: list[str] = []
    for op in collect_ops(module):
        if op.name != "tuner.param":
            continue
        names.append(str(op.result.type.get_value()))
    return names


def test_tile_reduce_public_api_surface_is_stable() -> None:
    """锁定 tile-reduce 的公开导出与 getter 顺序。"""

    assert package_module.TileReduceMatmulPattern is TileReduceMatmulPattern
    assert package_module.get_tile_reduce_pass_patterns is get_tile_reduce_pass_patterns
    assert [type(pattern) for pattern in get_tile_reduce_pass_patterns()] == [TileReduceMatmulPattern]


def test_tile_reduce_matmul_pattern_rewrites_single_matmul_op() -> None:
    """锁定 MatmulPattern 会为 matmul 写出 reduce 结构。"""

    module = build_matmul_module()
    TileAnalysisPass().apply(Context(), module)
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    matmul_op = next(op for op in func_op.body.block.ops if isinstance(op, KernelMatmulOp))

    TileReduceMatmulPattern().match_and_rewrite(matmul_op, PatternRewriter(matmul_op))

    ops = collect_ops(module)
    rewritten = [op for op in ops if op.name == "kernel.matmul"]
    assert len([op for op in ops if op.name == "symbol.for"]) == 1
    assert len([op for op in ops if op.name == "dma.view"]) == 2
    assert len([op for op in ops if op.name == "dma.fill"]) == 2
    assert len(rewritten) == 1
    assert rewritten[0].attributes["tile.tile_exprs"] == ArrayAttr(
        [
            ArrayAttr([StringAttr(""), StringAttr("")]),
            ArrayAttr([StringAttr(""), StringAttr("TILE_R0")]),
            ArrayAttr([StringAttr("TILE_R0"), StringAttr("")]),
        ]
    )


def test_tile_reduce_pass_requires_precomputed_analysis_attrs() -> None:
    """锁定 TileReducePass 对缺少 analysis attrs 的 matmul fail-fast。"""

    module = build_matmul_module()
    with pytest.raises(PassContractError, match="requires tile.analysis and tile.tile_exprs before tile-reduce"):
        TileReducePass().apply(Context(), module)


def test_tile_reduce_pass_rewrites_matmul_and_preserves_contract() -> None:
    """锁定 TileReducePass 会写出 reduce loop/view/fill 结构。"""

    module = build_matmul_module()
    TileAnalysisPass().apply(Context(), module)
    load_builtin_passes()
    pass_obj = build_registered_pass("tile-reduce")

    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.__class__ is TileReducePass
    pass_obj.apply(Context(), module)

    ops = collect_ops(module)
    rewritten = [op for op in ops if op.name == "kernel.matmul"]
    assert len([op for op in ops if op.name == "symbol.for"]) == 1
    assert len([op for op in ops if op.name == "dma.view"]) == 2
    assert len([op for op in ops if op.name == "dma.fill"]) == 2
    assert len(rewritten) == 1


def test_tile_reduce_fc_chain_only_keeps_matmul_reduce_params() -> None:
    """锁定 fc 链路只为 matmul reduce 计划建参。"""

    module = build_fc_chain_module()
    TileAnalysisPass().apply(Context(), module)
    TileReducePass().apply(Context(), module)

    assert tuner_param_names(module) == ["TILE_R0"]
