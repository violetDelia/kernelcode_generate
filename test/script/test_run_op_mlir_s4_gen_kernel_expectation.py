"""S4 gen_kernel expectation entry tests.

创建者: 金铲铲大作战
最后一次更改: 小李飞刀

功能说明:
- 覆盖 `script/run-op-mlir-s4-gen-kernel-expectation.sh` 的命令骨架与调用环境。
- 锁定 S4 `gen_kernel` expectation 只通过当前 worktree 的 `PYTHONPATH` 直接复现。

关联文件:
- 功能实现: script/run-op-mlir-s4-gen-kernel-expectation.sh
- 计划书: ARCHITECTURE/plan/operation_mlir_gen_expectation_green_plan.md
- 测试文件: test/script/test_run_op_mlir_s4_gen_kernel_expectation.py

使用示例:
- pytest -q test/script/test_run_op_mlir_s4_gen_kernel_expectation.py
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTATION_REPO_ROOT = Path("/home/lfr/kernelcode_generate")
SOURCE_SCRIPT = REPO_ROOT / "script/run-op-mlir-s4-gen-kernel-expectation.sh"
EXPECTATION_ENTRY = EXPECTATION_REPO_ROOT / "expectation/dsl/gen_kernel/npu_demo_add_barrier"


def _run_script(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """在当前 worktree 里执行 S4 expectation 入口脚本。"""

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


def test_print_command_uses_worktree_pythonpath_only() -> None:
    """TC-S4-ENTRY-001: `--print-command` 输出应只注入当前 worktree 的 `PYTHONPATH`。"""

    # 显式清空外层 PYTHONPATH，避免 exact-match 断言被调用环境污染。
    result = _run_script("--print-command", env={"PYTHONPATH": ""})

    expected_pythonpath = f"{REPO_ROOT}"
    expected = (
        f"cd {REPO_ROOT} && PYTHONDONTWRITEBYTECODE=1 "
        f"PYTHONPATH={expected_pythonpath} python3 {EXPECTATION_ENTRY}"
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected


def test_script_runs_expectation_from_worktree(tmp_path: Path) -> None:
    """TC-S4-ENTRY-002: 真正执行时应只把当前 worktree 注入到 `PYTHONPATH`。"""

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

    result = _run_script(env={"PYTHON_BIN": str(fake_python), "PYTHONPATH": ""})

    assert result.returncode == 0, result.stderr
    content = state_file.read_text(encoding="utf-8")
    assert f"cwd={REPO_ROOT}" in content
    assert f"argv={EXPECTATION_ENTRY}" in content
    assert "pythondontwritebytecode=1" in content
    assert f"pythonpath={REPO_ROOT}" in content


def test_script_runs_real_gen_kernel_expectation() -> None:
    """TC-S4-ENTRY-003: 真实 expectation 应在清洁的 worktree 环境下通过。"""

    result = _run_script(env={"PYTHONPATH": ""})
    assert result.returncode == 0, result.stderr
