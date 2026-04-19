"""S3 expectation entry tests.

创建者: 小李飞刀
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 `script/run-op-mlir-s3-expectation.sh` 的命令骨架与调用环境。
- 锁定当前 worktree 通过主仓 expectation 入口复测 S3 验收命令的可执行方式。

关联文件:
- 功能实现: script/run-op-mlir-s3-expectation.sh
- 计划书: ARCHITECTURE/plan/operation_mlir_gen_expectation_green_plan.md
- 测试文件: test/script/test_run_op_mlir_s3_expectation.py

使用示例:
- pytest -q test/script/test_run_op_mlir_s3_expectation.py
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_SCRIPT = REPO_ROOT / "script/run-op-mlir-s3-expectation.sh"
EXPECTATION_MODULE = "expectation.pass.lowing.nn_lowering"

pytestmark = pytest.mark.infra


def _run_script(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """执行 S3 expectation 入口脚本。"""

    runtime_env = os.environ.copy()
    if env is not None:
        runtime_env.update(env)
    return subprocess.run(
        ["/bin/bash", str(SOURCE_SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=runtime_env,
        check=False,
    )


def test_print_command_uses_worktree_and_main_repo_paths() -> None:
    """TC-S3-ENTRY-001: `--print-command` 输出应显式包含主仓与 worktree 路径。"""

    result = _run_script("--print-command")

    expected_pythonpath = str(REPO_ROOT.parent)
    expected = (
        f"cd {REPO_ROOT} && PYTHONDONTWRITEBYTECODE=1 "
        f"PYTHONPATH={expected_pythonpath} python3 -m {EXPECTATION_MODULE}"
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected


def test_script_runs_module_from_main_repo_with_prefixed_pythonpath(tmp_path: Path) -> None:
    """TC-S3-ENTRY-002: 脚本执行时应从 worktree 启动，并通过 `PYTHONPATH` 暴露主仓 expectation。"""

    state_file = tmp_path / "fake_python_state.txt"
    fake_python = tmp_path / "fake-python"
    fake_python.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f"printf 'cwd=%s\\n' \"$PWD\" > {state_file}",
                f"printf 'argv=%s\\n' \"$*\" >> {state_file}",
                "printf 'pythondontwritebytecode=%s\\n' \"${PYTHONDONTWRITEBYTECODE-}\" >> "
                f"{state_file}",
                "printf 'pythonpath=%s\\n' \"${PYTHONPATH-}\" >> "
                f"{state_file}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    result = _run_script(env={"PYTHON_BIN": str(fake_python)})

    assert result.returncode == 0, result.stderr
    content = state_file.read_text(encoding="utf-8")
    assert f"cwd={REPO_ROOT}" in content
    assert f"argv=-m {EXPECTATION_MODULE}" in content
    assert "pythondontwritebytecode=1" in content
    assert f"pythonpath={REPO_ROOT.parent}" in content


def test_script_runs_real_nn_lowering_expectation() -> None:
    """TC-S3-ENTRY-003: 真实 expectation 应在 fresh process 下以当前 worktree 实现通过。"""

    result = _run_script()

    assert result.returncode == 0, result.stderr
    assert "[CASE-broadcast-static]" in result.stdout
    assert "[CASE-transpose-dynamic]" in result.stdout
