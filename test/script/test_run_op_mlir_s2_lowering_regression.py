"""S2 lowering regression entry tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 `script/run-op-mlir-s2-lowering-regression.sh` 的命令骨架与调用环境。
- 锁定 S2 element_binary lowering 回归可在当前 worktree 内直接复现。

关联文件:
- 功能实现: script/run-op-mlir-s2-lowering-regression.sh
- 计划书: ARCHITECTURE/plan/operation_mlir_gen_expectation_green_plan.md
- 测试文件: test/script/test_run_op_mlir_s2_lowering_regression.py

使用示例:
- pytest -q test/script/test_run_op_mlir_s2_lowering_regression.py
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_SCRIPT = REPO_ROOT / "script/run-op-mlir-s2-lowering-regression.sh"
EXPECTED_TESTS = [
    "test/pass/nn_lowering/element_binary_add.py",
    "test/pass/nn_lowering/element_binary_sub.py",
    "test/pass/nn_lowering/element_binary_mul.py",
    "test/pass/nn_lowering/element_binary_div.py",
    "test/pass/nn_lowering/element_binary_truediv.py",
]


def _run_script(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """执行 S2 lowering 回归入口脚本。"""

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


def test_print_command_uses_explicit_lowering_cases() -> None:
    """TC-S2-LOWER-001: `--print-command` 应显式列出固定回归用例。"""

    result = _run_script("--print-command")

    expected_prefix = f"cd {REPO_ROOT} && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q"
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith(expected_prefix)
    for test_path in EXPECTED_TESTS:
        assert test_path in result.stdout


def test_script_runs_pytest_from_worktree(tmp_path: Path) -> None:
    """TC-S2-LOWER-002: 脚本执行时应从当前 worktree 启动 pytest。"""

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
    assert "argv=-m pytest -q" in content
    assert "pythondontwritebytecode=1" in content
    for test_path in EXPECTED_TESTS:
        assert test_path in content


def test_script_runs_real_lowering_regression() -> None:
    """TC-S2-LOWER-003: 真实 lowering 回归应在 fresh process 下通过。"""

    result = _run_script()

    assert result.returncode == 0, result.stderr
    assert "6 passed" in result.stdout
