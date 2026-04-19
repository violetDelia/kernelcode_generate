"""S11 npu_demo add_barrier expectation entry tests.

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 覆盖 `script/run-npu-demo-s11-add-barrier-expectation.sh` 的命令骨架与调用环境。
- 锁定 S11 `npu_demo_add_barrier` expectation 可在当前 worktree 内直接复现。

关联文件:
- 功能实现: script/run-npu-demo-s11-add-barrier-expectation.sh
- 计划书: ARCHITECTURE/plan/npu_demo_emitc_include_api_green_plan.md
- 测试文件: test/script/test_run_npu_demo_s11_add_barrier_expectation.py

使用示例:
- pytest -q test/script/test_run_npu_demo_s11_add_barrier_expectation.py
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_SCRIPT = REPO_ROOT / "script/run-npu-demo-s11-add-barrier-expectation.sh"
EXPECTATION_ENTRY = REPO_ROOT.parent / "expectation/dsl/gen_kernel/npu_demo_add_barrier"


def _run_script(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
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
    result = _run_script("--print-command")

    expected_pythonpath = f"{REPO_ROOT}:{REPO_ROOT.parent}"
    expected = (
        f"cd {REPO_ROOT} && PYTHONDONTWRITEBYTECODE=1 "
        f"PYTHONPATH={expected_pythonpath} python3 {EXPECTATION_ENTRY}"
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected


def test_script_runs_expectation_from_worktree(tmp_path: Path) -> None:
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
    assert f"argv={EXPECTATION_ENTRY}" in content
    assert "pythondontwritebytecode=1" in content
    assert f"pythonpath={REPO_ROOT}:{REPO_ROOT.parent}" in content


def test_script_runs_real_gen_kernel_expectation() -> None:
    result = _run_script()
    assert result.returncode == 0, result.stderr
