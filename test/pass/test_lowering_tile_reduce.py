"""tile-reduce pass tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 `kernel_gen.passes.lowering.tile_reduce.TileReducePass` 的公开 ModulePass 合同。
- 通过 expectation 目录级黑盒锁定 `tile-reduce` 对 matmul / fc 路径的 reduction-only 收口结果。
- 通过 registry 断言 `tile-reduce` 可稳定构造为 `ModulePass`。

使用示例:
- pytest -q test/pass/test_lowering_tile_reduce.py

关联文件:
- spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
- test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
- 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
"""

from __future__ import annotations

import os
import importlib
import subprocess
import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.passes import ModulePass

REPO_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT_STR = str(REPO_ROOT)
if REPO_ROOT_STR in sys.path:
    sys.path.remove(REPO_ROOT_STR)
sys.path.insert(0, REPO_ROOT_STR)

for module_name in list(sys.modules):
    if module_name == "kernel_gen" or module_name.startswith("kernel_gen."):
        del sys.modules[module_name]

registry_module = importlib.import_module("kernel_gen.passes.registry")
build_registered_pass = registry_module.build_registered_pass
load_builtin_passes = registry_module.load_builtin_passes

tile_reduce_module = importlib.import_module("kernel_gen.passes.lowering.tile_reduce")
TileReduceError = tile_reduce_module.TileReduceError
TileReducePass = tile_reduce_module.TileReducePass

tile_reduce_matmul = importlib.import_module("expectation.pass.tile.reduce.matmul")
tile_reduce_fc = importlib.import_module("expectation.pass.tile.reduce.fc")


def _run_expectation_module(module_name: str) -> subprocess.CompletedProcess[str]:
    """以独立进程运行 expectation 目录入口。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 固定在当前 worktree 根目录启动，复现 package 级 expectation 的入口解析路径。
    - 使用 worktree-first `PYTHONPATH`，验证目录入口不会串到仓根旧合同。

    使用示例:
    - result = _run_expectation_module("expectation.pass.tile.reduce")

    关联文件:
    - spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
    - test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [expectation/pass/tile/reduce/__main__.py](expectation/pass/tile/reduce/__main__.py)
    """

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = os.pathsep.join([str(REPO_ROOT), str(REPO_ROOT.parent)])
    return subprocess.run(
        [sys.executable, "-m", module_name],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _assert_ircheck_ok(case_text: str, source_path: str, *, required_fragments: tuple[str, ...]) -> None:
    """运行 tile-reduce 黑盒并断言通过。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 使用 `run_ircheck_text` 验证 `tile-reduce` 目录级 expectation。

    使用示例:
    - _assert_ircheck_ok(CASE_TEXT_STATIC, "test/pass/test_lowering_tile_reduce.py:static", required_fragments=("tile.analysis",))

    关联文件:
    - spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
    - test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    run_ircheck_text = importlib.import_module("kernel_gen.tools.ircheck").run_ircheck_text
    result = run_ircheck_text(case_text, source_path=source_path)
    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert result.actual_ir.count("symbol.for") == 1
    assert '"tile.step_value"(' not in result.actual_ir
    assert "tile.analysis" in result.actual_ir
    assert "tile.tile_exprs" in result.actual_ir
    for fragment in required_fragments:
        assert fragment in result.actual_ir, f"actual_ir must contain {fragment!r}"


def test_tile_reduce_pass_is_module_pass_and_registry_construction() -> None:
    """验证 tile-reduce 可作为 ModulePass 由 registry 构造。"""

    load_builtin_passes()

    pass_obj = build_registered_pass("tile-reduce")

    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.name == "tile-reduce"
    assert type(pass_obj).__name__ == "TileReducePass"
    assert pass_obj.__class__.__module__ == "kernel_gen.passes.lowering.tile_reduce"


def test_tile_reduce_pass_rejects_non_module_input() -> None:
    """验证 tile-reduce 的 `apply` 仅接受 builtin.module。"""

    with pytest.raises(
        TileReduceError,
        match=r"^TileReduceRequiresLoweredKernelIR: module must be builtin\.module$",
    ):
        TileReducePass().apply(Context(), object())


def test_tile_reduce_expectation_matmul_cases() -> None:
    """验证 tile-reduce matmul 目录级 expectation。"""

    _assert_ircheck_ok(
        tile_reduce_matmul.CASE_TEXT_STATIC,
        "expectation/pass/tile/reduce/matmul.py:static",
        required_fragments=('"kernel.matmul"', '"kernel.binary_elewise"'),
    )
    _assert_ircheck_ok(
        tile_reduce_matmul.CASE_TEXT_DYNAMIC,
        "expectation/pass/tile/reduce/matmul.py:dynamic",
        required_fragments=('"kernel.matmul"', '"kernel.binary_elewise"'),
    )
    _assert_ircheck_ok(
        tile_reduce_matmul.CASE_TEXT_MIXED,
        "expectation/pass/tile/reduce/matmul.py:mixed",
        required_fragments=('"kernel.matmul"', '"kernel.binary_elewise"'),
    )


def test_tile_reduce_expectation_fc_cases() -> None:
    """验证 tile-reduce fc 目录级 expectation。"""

    _assert_ircheck_ok(
        tile_reduce_fc.CASE_TEXT_STATIC,
        "expectation/pass/tile/reduce/fc.py:static",
        required_fragments=('"dma.broadcast"', '"kernel.matmul"', '"kernel.binary_elewise"'),
    )
    _assert_ircheck_ok(
        tile_reduce_fc.CASE_TEXT_DYNAMIC,
        "expectation/pass/tile/reduce/fc.py:dynamic",
        required_fragments=('"dma.broadcast"', '"kernel.matmul"', '"kernel.binary_elewise"'),
    )
    _assert_ircheck_ok(
        tile_reduce_fc.CASE_TEXT_MIXED,
        "expectation/pass/tile/reduce/fc.py:mixed",
        required_fragments=('"dma.broadcast"', '"kernel.matmul"', '"kernel.binary_elewise"'),
    )


def test_tile_reduce_expectation_package_entry_uses_worktree_first() -> None:
    """验证 tile-reduce 包级 expectation 入口不会串到仓根旧合同。"""

    result = _run_expectation_module("expectation.pass.tile.reduce")
    assert result.returncode == 0, (
        f"expected returncode=0, got {result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r}"
    )
    assert result.stderr == "", f"expected stderr to be empty, got {result.stderr!r}"
