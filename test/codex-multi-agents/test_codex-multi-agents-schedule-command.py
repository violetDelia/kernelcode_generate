"""codex-multi-agents-schedule-command.sh tests.

创建者: Codex
最后一次更改: Codex

功能说明:
- 覆盖定时执行脚本的默认命令、自定义命令、日志写入和错误返回码路径。

关联文件:
- 功能实现: [skills/codex-multi-agents/scripts/codex-multi-agents-schedule-command.sh](../../skills/codex-multi-agents/scripts/codex-multi-agents-schedule-command.sh)
- Spec 文档: [spec/codex-multi-agents/scripts/codex-multi-agents-schedule-command.md](../../spec/codex-multi-agents/scripts/codex-multi-agents-schedule-command.md)
- 测试文件: [test/codex-multi-agents/test_codex-multi-agents-schedule-command.py](../../test/codex-multi-agents/test_codex-multi-agents-schedule-command.py)

覆盖率:
- 覆盖率: sh 脚本覆盖率统计豁免
- 覆盖率命令: N/A（实现为 shell 脚本，按 AGENTS.md 豁免）

使用示例:
- pytest -q test/codex-multi-agents/test_codex-multi-agents-schedule-command.py
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "skills/codex-multi-agents/scripts/codex-multi-agents-schedule-command.sh"


def run_script(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """调用待测 shell 脚本并返回执行结果。

    创建者: Codex
    最后一次更改: 小李飞刀

    功能说明:
    - 统一执行待测脚本并收集 stdout/stderr 与返回码。

    使用示例:
    - run_script(\"-interval\", \"0\", \"-count\", \"1\")

    关联文件:
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-schedule-command.sh
    - Spec 文档: spec/codex-multi-agents/scripts/codex-multi-agents-schedule-command.md
    - 测试文件: test/codex-multi-agents/test_codex-multi-agents-schedule-command.py
    """
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def write_fake_command(bin_dir: Path, name: str, body: str) -> Path:
    """写入测试专用可执行命令。

    创建者: Codex
    最后一次更改: 小李飞刀

    功能说明:
    - 生成可执行脚本文件，便于构造测试命令。

    使用示例:
    - write_fake_command(tmp_path / \"bin\", \"mand\", \"#!/usr/bin/env bash\\n\")\n
    关联文件:
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-schedule-command.sh
    - Spec 文档: spec/codex-multi-agents/scripts/codex-multi-agents-schedule-command.md
    - 测试文件: test/codex-multi-agents/test_codex-multi-agents-schedule-command.py
    """
    bin_dir.mkdir(parents=True, exist_ok=True)
    command_path = bin_dir / name
    command_path.write_text(body, encoding="utf-8")
    command_path.chmod(0o755)
    return command_path


# TC-001
# 创建者: Codex
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 13:19:12 +0800
# 最近一次运行成功时间: 2026-03-22 13:19:12 +0800
# 测试目的: 验证自定义命令按次数执行并写入日志。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-schedule-command.py -k test_custom_command_runs_expected_count_and_writes_log
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-schedule-command.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-schedule-command.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-schedule-command.py
def test_custom_command_runs_expected_count_and_writes_log(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    counter_file = tmp_path / "counter.txt"
    log_file = tmp_path / "schedule.log"

    write_fake_command(
        bin_dir,
        "record-once",
        f"""#!/usr/bin/env bash
set -eu
counter_file="{counter_file}"
count=0
if [[ -f "$counter_file" ]]; then
  count="$(cat "$counter_file")"
fi
count=$((count + 1))
printf "%s" "$count" > "$counter_file"
printf "run-%s\\n" "$count"
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    result = run_script(
        "-interval",
        "0",
        "-count",
        "2",
        "-command",
        "record-once",
        "-log-file",
        str(log_file),
        env=env,
    )

    assert result.returncode == 0
    assert counter_file.read_text(encoding="utf-8") == "2"
    assert "OK round=1 command=record-once" in result.stdout
    assert "OK round=2 command=record-once" in result.stdout
    log_text = log_file.read_text(encoding="utf-8")
    assert "round=1 command=record-once" in log_text
    assert "run-1" in log_text
    assert "round=2 command=record-once" in log_text
    assert "run-2" in log_text


# TC-002
# 创建者: Codex
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 13:19:12 +0800
# 最近一次运行成功时间: 2026-03-22 13:19:12 +0800
# 测试目的: 验证默认命令 mand 可从 PATH 执行。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-schedule-command.py -k test_default_mand_command_can_run_from_path
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-schedule-command.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-schedule-command.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-schedule-command.py
def test_default_mand_command_can_run_from_path(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"

    write_fake_command(
        bin_dir,
        "mand",
        """#!/usr/bin/env bash
set -eu
printf "mand-ok\\n"
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    result = run_script("-interval=0", "-count=1", env=env)

    assert result.returncode == 0
    assert "OK round=1 command=mand" in result.stdout
    assert "mand-ok" in result.stdout


# TC-003
# 创建者: Codex
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 13:19:12 +0800
# 最近一次运行成功时间: 2026-03-22 13:19:12 +0800
# 测试目的: 验证命令失败时返回 rc=3 并停止后续执行。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-schedule-command.py -k test_command_failure_returns_rc3_and_stops_follow_up_runs
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-schedule-command.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-schedule-command.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-schedule-command.py
def test_command_failure_returns_rc3_and_stops_follow_up_runs(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    marker_file = tmp_path / "failed.txt"

    write_fake_command(
        bin_dir,
        "always-fail",
        f"""#!/usr/bin/env bash
set -eu
printf "failed-once" > "{marker_file}"
printf "boom\\n" >&2
exit 7
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    result = run_script("-interval", "0", "-count", "3", "-command", "always-fail", env=env)

    assert result.returncode == 3
    assert marker_file.read_text(encoding="utf-8") == "failed-once"
    assert "boom" in result.stderr
    assert "round 1" in result.stderr


# TC-004
# 创建者: Codex
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 13:19:12 +0800
# 最近一次运行成功时间: 2026-03-22 13:19:12 +0800
# 测试目的: 验证缺失 interval 参数时返回 rc=1。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-schedule-command.py -k test_missing_interval_returns_rc1
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-schedule-command.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-schedule-command.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-schedule-command.py
def test_missing_interval_returns_rc1(tmp_path: Path) -> None:
    result = run_script("-count", "1")

    assert result.returncode == 1
    assert "missing required argument: -interval" in result.stderr


# TC-005
# 创建者: Codex
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 13:19:12 +0800
# 最近一次运行成功时间: 2026-03-22 13:19:12 +0800
# 测试目的: 验证 shell 路径缺失时返回 rc=2。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-schedule-command.py -k test_missing_shell_returns_rc2
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-schedule-command.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-schedule-command.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-schedule-command.py
def test_missing_shell_returns_rc2(tmp_path: Path) -> None:
    result = run_script("-interval", "0", "-count", "1", "-shell", str(tmp_path / "missing-shell"))

    assert result.returncode == 2
    assert "shell not found or not executable" in result.stderr
