"""tile package public contract tests.

创建者: OpenAI Codex
最后一次更改: OpenAI Codex

功能说明:
- 锁定 `kernel_gen.passes.tile` package 的公开模块集合与 registry 入口。
- 锁定 `kernel_gen.passes.lowering.tile` 只剩兼容 helper `_raise_tile_error`，不再暴露 tile family 的 pass/pattern API。

使用示例:
- pytest -q test/pass/tile/test_package.py

关联文件:
- spec: [spec/pass/tile/README.md](../../../spec/pass/tile/README.md)
- test: [test/pass/tile/test_package.py](../../../test/pass/tile/test_package.py)
- 功能实现: [kernel_gen/passes/tile/__init__.py](../../../kernel_gen/passes/tile/__init__.py)
- 功能实现: [kernel_gen/passes/lowering/tile.py](../../../kernel_gen/passes/lowering/tile.py)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from xdsl.passes import ModulePass

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

passes_common_module = importlib.import_module("kernel_gen.passes.common")
tile_package = importlib.import_module("kernel_gen.passes.tile")
tile_analysis_module = importlib.import_module("kernel_gen.passes.tile.analysis")
tile_elewise_module = importlib.import_module("kernel_gen.passes.tile.elewise")
tile_reduce_module = importlib.import_module("kernel_gen.passes.tile.reduce")
legacy_tile_module = importlib.import_module("kernel_gen.passes.lowering.tile")
registry_module = importlib.import_module("kernel_gen.passes.registry")

TileAnalysisPass = tile_analysis_module.TileAnalysisPass
TileElewisePass = tile_elewise_module.TileElewisePass
TileReducePass = tile_reduce_module.TileReducePass
build_registered_pass = registry_module.build_registered_pass
load_builtin_passes = registry_module.load_builtin_passes


def test_tile_package_exports_only_public_modules() -> None:
    """锁定 tile package 只公开 analysis/elewise/reduce 模块。"""

    assert tile_package.__all__ == ["analysis", "elewise", "reduce"]
    assert tile_package.analysis is tile_analysis_module
    assert tile_package.elewise is tile_elewise_module
    assert tile_package.reduce is tile_reduce_module
    assert not hasattr(tile_package, "contract")
    assert not hasattr(tile_package, "rewrite")


def test_tile_registered_passes_use_public_modules() -> None:
    """锁定 registry 返回 tile family 的 3 个公开 pass。"""

    load_builtin_passes()
    analysis_pass = build_registered_pass("tile-analysis")
    elewise_pass = build_registered_pass("tile-elewise")
    reduce_pass = build_registered_pass("tile-reduce")

    assert isinstance(analysis_pass, ModulePass)
    assert isinstance(elewise_pass, ModulePass)
    assert isinstance(reduce_pass, ModulePass)
    assert analysis_pass.__class__ is TileAnalysisPass
    assert elewise_pass.__class__ is TileElewisePass
    assert reduce_pass.__class__ is TileReducePass


def test_legacy_tile_module_keeps_only_compat_error_helper() -> None:
    """锁定 lowering.tile 只保留兼容错误 helper。"""

    assert legacy_tile_module.__all__ == ["_raise_tile_error"]
    assert legacy_tile_module._raise_tile_error is passes_common_module.raise_pass_contract_error
    assert not hasattr(legacy_tile_module, "TileAnalysisPass")
    assert not hasattr(legacy_tile_module, "TileElewisePass")
    assert not hasattr(legacy_tile_module, "TileReducePass")

