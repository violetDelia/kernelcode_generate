"""codex-multi-agents-tmux.sh tests.

功能说明:
- 覆盖 tmux 脚本的 talk / init-env 主流程与错误返回码路径。

关联文件:
- 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh
- Spec 文档: spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md
- 测试文件: test/codex-multi-agents/test_codex-multi-agents-tmux.py
"""

from __future__ import annotations

import fcntl
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh"


def write_agents_file(path: Path, rows: list[str] | None = None) -> None:
    """写入供 -init-env 测试使用的名单文件。"""
    header = "| 姓名 | 状态 | 会话 | 启动类型 | agent session | worktree | 介绍 | 提示词 | 归档文件 | 职责 |"
    sep = "|---|---|---|---|---|---|---|---|---|---|"
    if rows is None:
        rows = [
            "| 小明 | free | xiaoming | codex | agent-xiaoming | worktrees/xiaoming | intro | prompt.md | archive/ | duty |",
            "| 李白 | free | libai | claude | agent-libai | worktrees/libai | intro | prompt.md | archive/ | duty |",
        ]
    text = "\n".join(["# Agents 名单", "", header, sep, *rows, ""])
    path.write_text(text, encoding="utf-8")


def write_fake_tmux(bin_dir: Path, state_dir: Path, sessions: list[str] | None = None) -> Path:
    """写入 fake tmux 可执行文件，用于拦截并记录 tmux 调用。"""
    sessions = sessions or []
    bin_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)

    sessions_file = state_dir / "sessions.txt"
    calls_file = state_dir / "calls.log"
    sessions_file.write_text("\n".join(sessions) + ("\n" if sessions else ""), encoding="utf-8")
    calls_file.write_text("", encoding="utf-8")

    fake_tmux = bin_dir / "tmux"
    fake_tmux.write_text(
        """#!/usr/bin/env bash
set -u
state_dir="${FAKE_TMUX_STATE_DIR:?}"
sessions_file="$state_dir/sessions.txt"
calls_file="$state_dir/calls.log"
cmd="${1-}"
[[ -n "$cmd" ]] || exit 2
shift || true

case "$cmd" in
  has-session)
    [[ "${1-}" == "-t" ]] || exit 2
    target="${2-}"
    [[ -n "$target" ]] || exit 2
    if grep -Fxq "$target" "$sessions_file" 2>/dev/null; then
      exit 0
    fi
    exit 1
    ;;
  attach)
    [[ "${1-}" == "-t" ]] || exit 2
    target="${2-}"
    echo "attach:$target" >> "$calls_file"
    exit 0
    ;;
  new)
    [[ "${1-}" == "-s" ]] || exit 2
    target="${2-}"
    echo "$target" >> "$sessions_file"
    echo "new:$target" >> "$calls_file"
    exit 0
    ;;
  new-session)
    if [[ "${1-}" == "-d" ]]; then
      shift
    fi
    [[ "${1-}" == "-s" ]] || exit 2
    target="${2-}"
    echo "$target" >> "$sessions_file"
    echo "new-session:$target" >> "$calls_file"
    exit 0
    ;;
  send-keys)
    [[ "${1-}" == "-t" ]] || exit 2
    target="${2-}"
    msg="${3-}"
    key="${4-}"
    echo "send:$target:$msg:$key" >> "$calls_file"
    exit 0
    ;;
  *)
    echo "unknown:$cmd" >> "$calls_file"
    exit 2
    ;;
esac
""",
        encoding="utf-8",
    )
    fake_tmux.chmod(0o755)
    return calls_file


def run_script(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """调用待测 shell 脚本并返回执行结果。"""
    return subprocess.run(
        ["/bin/bash", str(SCRIPT_PATH), *args],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


# TC-001
# Last Run: 2026-03-07 13:42:00 +0800
# Last Success: 2026-03-07 13:42:00 +0800
# 功能文件: skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh
# Spec 文件: spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md
def test_talk_send_and_append_log_success(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    calls_file = write_fake_tmux(bin_dir, state_dir, sessions=["worker-a"])
    log_file = tmp_path / "talk.log"

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    result = run_script(
        "-talk",
        "-from",
        "scheduler",
        "-to",
        "worker-a",
        "-session-id",
        "worker-a",
        "-message",
        "请处理任务 T1",
        "-log",
        str(log_file),
        env=env,
    )
    calls = calls_file.read_text(encoding="utf-8")
    log_text = log_file.read_text(encoding="utf-8")

    assert result.returncode == 0
    assert "OK: talk scheduler -> worker-a (worker-a)" in result.stdout
    assert calls.count("send:worker-a:@scheduler向@worker-a发起会话: 请处理任务 T1:") == 1
    assert calls.count("send:worker-a:ENTER:") == 1
    assert "@scheduler向@worker-a发起会话: 请处理任务 T1" in log_text


# TC-002
# Last Run: 2026-03-07 13:42:00 +0800
# Last Success: 2026-03-07 13:42:00 +0800
# 功能文件: skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh
# Spec 文件: spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md
def test_talk_target_session_not_found_returns_rc3(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    write_fake_tmux(bin_dir, state_dir, sessions=["worker-a"])
    log_file = tmp_path / "talk.log"

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    result = run_script(
        "-talk",
        "-from",
        "scheduler",
        "-to",
        "worker-a",
        "-session-id",
        "missing",
        "-message",
        "hello",
        "-log",
        str(log_file),
        env=env,
    )

    assert result.returncode == 3
    assert "target session not found: missing" in result.stderr


# TC-003
# Last Run: 2026-03-07 13:42:00 +0800
# Last Success: 2026-03-07 13:42:00 +0800
# 功能文件: skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh
# Spec 文件: spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md
def test_talk_missing_message_returns_rc1(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    write_fake_tmux(bin_dir, state_dir, sessions=["worker-a"])
    log_file = tmp_path / "talk.log"

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    result = run_script(
        "-talk",
        "-from",
        "scheduler",
        "-to",
        "worker-a",
        "-session-id",
        "worker-a",
        "-log",
        str(log_file),
        env=env,
    )

    assert result.returncode == 1
    assert "-talk requires -message" in result.stderr


# TC-004
# Last Run: 2026-03-07 13:42:00 +0800
# Last Success: 2026-03-07 13:42:00 +0800
# 功能文件: skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh
# Spec 文件: spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md
def test_tmux_not_found_returns_rc2(tmp_path: Path) -> None:
    empty_bin = tmp_path / "empty_bin"
    empty_bin.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PATH"] = str(empty_bin)

    result = run_script(
        "-talk",
        "-from",
        "scheduler",
        "-to",
        "worker-a",
        "-session-id",
        "worker-a",
        "-message",
        "hello",
        "-log",
        str(tmp_path / "talk.log"),
        env=env,
    )

    assert result.returncode == 2
    assert "tmux not found in PATH" in result.stderr


# TC-005
# Last Run: 2026-03-07 13:42:00 +0800
# Last Success: 2026-03-07 13:42:00 +0800
# 功能文件: skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh
# Spec 文件: spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md
def test_talk_lock_conflict_returns_rc4(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    write_fake_tmux(bin_dir, state_dir, sessions=["worker-a"])
    log_file = tmp_path / "talk.log"
    lock_path = Path(f"{log_file}.lock")
    lock_path.touch()

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    with lock_path.open("w", encoding="utf-8") as lock_fd:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = run_script(
            "-talk",
            "-from",
            "scheduler",
            "-to",
            "worker-a",
            "-session-id",
            "worker-a",
            "-message",
            "hello",
            "-log",
            str(log_file),
            env=env,
        )

    assert result.returncode == 4
    assert "cannot acquire lock" in result.stderr


# TC-006
# Last Run: 2026-03-08 12:40:00 +0800
# Last Success: 2026-03-08 12:40:00 +0800
# 功能文件: skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh
# Spec 文件: spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md
def test_init_env_codex_creates_session_and_bootstraps(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    calls_file = write_fake_tmux(bin_dir, state_dir, sessions=[])
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    result = run_script(
        "-init-env",
        "-file",
        str(agents_file),
        "-name",
        "小明",
        env=env,
    )
    calls = calls_file.read_text(encoding="utf-8")

    assert result.returncode == 0
    assert "OK: init-env 小明 (xiaoming)" in result.stdout
    assert "new-session:xiaoming" in calls
    assert calls.count("send:xiaoming:codex:") == 1
    assert calls.count("send:xiaoming:/rename agent-xiaoming:") == 1
    assert calls.count("send:xiaoming:ENTER:") == 2


# TC-007
# Last Run: 2026-03-08 12:40:00 +0800
# Last Success: 2026-03-08 12:40:00 +0800
# 功能文件: skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh
# Spec 文件: spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md
def test_init_env_missing_agent_returns_rc3(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    write_fake_tmux(bin_dir, state_dir, sessions=[])
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    result = run_script(
        "-init-env",
        "-file",
        str(agents_file),
        "-name",
        "不存在",
        env=env,
    )

    assert result.returncode == 3
    assert "failed to read field" in result.stderr
