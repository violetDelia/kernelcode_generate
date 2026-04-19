"""emit_c npu_demo expectation entry tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 `script/run_emitc_npu_demo_expectation.py` 的命令骨架与实际运行。
- 锁定复跑命令会优先使用当前 worktree 的 `kernel_gen`，避免回退到仓根实现。

关联文件:
- 功能实现: [`script/run_emitc_npu_demo_expectation.py`](../../script/run_emitc_npu_demo_expectation.py)
- 计划书: [`ARCHITECTURE/plan/npu_demo_emitc_include_api_green_plan.md`](../../ARCHITECTURE/plan/npu_demo_emitc_include_api_green_plan.md)
- 测试文件: [`test/script/test_run_emitc_npu_demo_expectation.py`](test/script/test_run_emitc_npu_demo_expectation.py)

使用示例:
- `pytest -q test/script/test_run_emitc_npu_demo_expectation.py`
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_REPO_ROOT = REPO_ROOT.parent
SOURCE_SCRIPT = REPO_ROOT / "script/run_emitc_npu_demo_expectation.py"


def _run_script(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    runtime_env = os.environ.copy()
    if env is not None:
        runtime_env.update(env)
    return subprocess.run(
        [sys.executable, str(SOURCE_SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=runtime_env,
        check=False,
    )


def test_print_command_uses_worktree_and_main_repo_paths() -> None:
    result = _run_script("--print-command", env={"PYTHONPATH": ""})

    expected_pythonpath = f"{REPO_ROOT}:{MAIN_REPO_ROOT}"
    expected = (
        f"cd {REPO_ROOT} && PYTHONDONTWRITEBYTECODE=1 "
        f"PYTHONPATH={expected_pythonpath} python3 {SOURCE_SCRIPT}"
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected


def test_script_runs_expectation_from_worktree() -> None:
    result = _run_script(env={"PYTHONPATH": ""})

    assert result.returncode == 0, result.stderr
