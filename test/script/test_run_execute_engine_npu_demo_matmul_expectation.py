"""execute_engine npu_demo matmul expectation entry tests.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 `script/run_execute_engine_npu_demo_matmul_expectation.py` 的命令骨架与实际运行。
- 锁定 execute_engine npu_demo matmul 可通过 worktree 内入口直接复现真实编译/真实执行链路。

关联文件:
- 功能实现: [`script/run_execute_engine_npu_demo_matmul_expectation.py`](../../script/run_execute_engine_npu_demo_matmul_expectation.py)
- 计划书: [`ARCHITECTURE/plan/npu_demo_emitc_include_api_green_plan.md`](../../ARCHITECTURE/plan/npu_demo_emitc_include_api_green_plan.md)
- 测试文件: [`test/script/test_run_execute_engine_npu_demo_matmul_expectation.py`](test/script/test_run_execute_engine_npu_demo_matmul_expectation.py)

使用示例:
- `pytest -q test/script/test_run_execute_engine_npu_demo_matmul_expectation.py`
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_SCRIPT = REPO_ROOT / "script/run_execute_engine_npu_demo_matmul_expectation.py"


def _resolve_expectation_entry() -> Path:
    local_entry = REPO_ROOT / "expectation/execute_engine/npu_demo/matmul.py"
    if local_entry.exists():
        return local_entry
    return REPO_ROOT.parent / "expectation/execute_engine/npu_demo/matmul.py"


EXPECTATION_ENTRY = _resolve_expectation_entry()


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


def test_print_command_uses_worktree_pythonpath_only() -> None:
    """TC-EXEC-ENTRY-001: `--print-command` 输出应只注入当前 worktree 的 `PYTHONPATH`。"""

    result = _run_script("--print-command", env={"PYTHONPATH": ""})

    expected = (
        f"cd {REPO_ROOT} && PYTHONDONTWRITEBYTECODE=1 "
        f"PYTHONPATH={REPO_ROOT} python3 {SOURCE_SCRIPT}"
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected


def test_script_runs_real_execute_engine_matmul_expectation() -> None:
    """TC-EXEC-ENTRY-002: 真实 expectation 应在清洁的 worktree 环境下通过。"""

    assert EXPECTATION_ENTRY.exists()
    result = _run_script(env={"PYTHONPATH": ""})
    assert result.returncode == 0, result.stderr
