"""tile helper module tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 锁定 `kernel_gen.passes.lowering.tile` 已退回为 helper module，不再公开旧 `TilePass`。
- 覆盖 helper module 对外只保留错误类型与共享 helper 的收口口径。

使用示例:
- pytest -q test/pass/test_lowering_tile.py

关联文件:
- 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
- Spec 文档: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
- 测试文件: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from xdsl.dialects.builtin import ArrayAttr, StringAttr

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

tile_module = importlib.import_module("kernel_gen.passes.lowering.tile")


# TC-TILE-HELPER-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 tile helper module 不再公开旧 TilePass / TileAnalysisPass / bridge op。
# 使用示例: pytest -q test/pass/test_lowering_tile.py -k test_tile_helper_module_drops_legacy_public_contract
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile.py
def test_tile_helper_module_drops_legacy_public_contract() -> None:
    assert tile_module.__all__ == ["TilePassError", "_raise_tile_error"]
    assert not hasattr(tile_module, "TilePass")
    assert not hasattr(tile_module, "TileAnalysisPass")
    assert not hasattr(tile_module, "_TileStepValueOp")
    assert not hasattr(tile_module, "_TileSymbolLiteralOp")
    assert not hasattr(tile_module, "_read_kernel_split_tile_spec")
    assert not hasattr(tile_module, "_build_elementwise_loop_specs")
    assert not hasattr(tile_module, "_build_matmul_loop_specs")


# TC-TILE-HELPER-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 tile helper module 仍保留 analysis 共享 helper，供新 ModulePass 复用。
# 使用示例: pytest -q test/pass/test_lowering_tile.py -k test_tile_helper_module_keeps_shared_analysis_helpers
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile.py
def test_tile_helper_module_keeps_shared_analysis_helpers() -> None:
    roles = [["elewise", "elewise"], ["expand", "elewise"]]
    attr = tile_module._tile_analysis_attr(roles)

    expected = ArrayAttr(
        [
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("expand"), StringAttr("elewise")]),
        ]
    )

    assert attr == expected
    assert tile_module._tile_param_hint("TILE_M0") == "m0"
    assert tile_module._tile_param_hint("TILE_D0") is None
