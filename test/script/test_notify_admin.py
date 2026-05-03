"""notify-admin.sh tests.


功能说明:
- 覆盖 `script/notify-admin.sh` 的默认循环配置、`1/3` 概率初始化分支、确定性随机钩子与 `-init` 入口。

关联文件:
- 功能实现: script/notify-admin.sh
- Spec 文档: spec/script/notify-admin.md
- 测试文件: test/script/test_notify_admin.py

使用示例:
- pytest -q test/script/test_notify_admin.py

覆盖率信息:
- `script/notify-admin.sh` 为 `sh` 实现，按 `AGENTS.md` 可豁免 `95%` 覆盖率达标线。

覆盖率命令:
- 豁免：`script/notify-admin.sh` 为 `sh` 实现，不适用 Python 模块覆盖率统计。
- 功能校验命令：`pytest -q test/script/test_notify_admin.py`
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_SCRIPT = REPO_ROOT / "script/notify-admin.sh"
DEFAULT_ADMIN_MESSAGE = "请推进“正在执行的任务”并分发“任务列表”中可分发任务。有任何问题和回复,使用脚本 -talk 对话。如果有完成的任务按照顺序一个一个询问架构师验收,验收通过后归档。"
DEFAULT_BUSY_MESSAGE = "再次查看TODO.md, 继续你的任务，完成后使用 -next 并回报管理员,如果发现之前执行过相同的任务,说明任务又流转到你身上,查看日志,继续按照任务要求执行。有任何阻塞/疑问再次回报管理/架构师,重复用脚本询问要求对方回复,直到对方回复。"

pytestmark = pytest.mark.infra


def write_executable(path: Path, content: str) -> None:
    """写入测试所需的可执行脚本。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def build_fake_repo(tmp_path: Path) -> tuple[Path, Path]:
    """构造最小仓库副本，复用真实 `notify-admin.sh` 测试默认配置。"""
    repo_root = tmp_path / "repo"
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    script_path = repo_root / "script/notify-admin.sh"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(SOURCE_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    script_path.chmod(0o755)

    (repo_root / "agents/codex-multi-agents/log").mkdir(parents=True, exist_ok=True)
    (repo_root / "agents/codex-multi-agents/agents-lists.md").write_text(
        "\n".join(
            [
                "# agents",
                "",
                "| 姓名 | 状态 | 介绍 | 职责 |",
                "| --- | --- | --- | --- |",
                "| 神秘人 | busy | 管理员 | 负责分发与协调 |",
                "| 大闸蟹 | busy | 架构师：推进/拆解/标准边界 | 负责项目推进、架构拆解与标准边界；不承担管理员分发的任务 |",
                "| 小李飞刀 | busy | 擅长脚本调整 | 仅负责实现与测试 |",
                "| 小明 | ready | 跟进实现 | 仅负责实现与测试 |",
                "",
            ]
        ),
        encoding="utf-8",
    )

    write_executable(
        repo_root / "skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh",
        """#!/usr/bin/env bash
set -euo pipefail
state_dir="${FAKE_NOTIFY_STATE_DIR:?}"
count_file="$state_dir/tmux_count.txt"
count=0
if [[ -f "$count_file" ]]; then
  count="$(cat "$count_file")"
fi
count="$((count + 1))"
printf '%s' "$count" > "$count_file"
printf '%s\\0' "$@" > "$state_dir/tmux_args_${count}.bin"
exit 0
""",
    )
    write_executable(
        repo_root / "skills/codex-multi-agents/scripts/codex-multi-agents-list.sh",
        """#!/usr/bin/env bash
set -euo pipefail
state_dir="${FAKE_NOTIFY_STATE_DIR:?}"
printf '%s\\0' "$@" > "$state_dir/list_args.bin"
exit 0
""",
    )
    write_executable(
        repo_root / "bin/sleep",
        """#!/usr/bin/env bash
set -euo pipefail
state_dir="${FAKE_NOTIFY_STATE_DIR:?}"
printf '%s\\n' "${1-}" > "$state_dir/sleep_arg.txt"
exit 1
""",
    )
    return repo_root, state_dir


def read_null_separated_args(path: Path) -> list[str]:
    """读取 fake 脚本写入的 `NUL` 分隔参数列表。"""
    data = path.read_bytes()
    if not data:
        return []
    return data.decode("utf-8").split("\0")[:-1]


def read_tmux_calls(state_dir: Path) -> list[list[str]]:
    """按调用顺序读取 fake tmux 脚本记录的参数。"""
    count_path = state_dir / "tmux_count.txt"
    if not count_path.exists():
        return []
    count = int(count_path.read_text(encoding="utf-8").strip())
    calls: list[list[str]] = []
    for idx in range(1, count + 1):
        calls.append(read_null_separated_args(state_dir / f"tmux_args_{idx}.bin"))
    return calls


def run_script(repo_root: Path, *args: str, random_roll: str | None = None) -> subprocess.CompletedProcess[str]:
    """在最小仓库副本里执行 `notify-admin.sh`。"""
    env = os.environ.copy()
    env["FAKE_NOTIFY_STATE_DIR"] = str(repo_root.parent / "state")
    env["PATH"] = f"{repo_root / 'bin'}:{env.get('PATH', '')}"
    if random_roll is not None:
        env["NOTIFY_ADMIN_RANDOM_ROLL"] = random_roll
    return subprocess.run(
        ["/bin/bash", str(repo_root / "script/notify-admin.sh"), *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


# TC-NA-001
# 测试目的: 验证循环模式默认使用 3600 秒间隔，先提醒管理员推进任务，再逐个提醒 busy 执行人。
# 对应功能实现文件路径: script/notify-admin.sh
# 对应 spec 文件路径: spec/script/notify-admin.md
def test_notify_admin_loop_uses_default_interval_and_message(tmp_path: Path) -> None:
    repo_root, state_dir = build_fake_repo(tmp_path)

    result = run_script(repo_root, random_roll="1")
    tmux_calls = read_tmux_calls(state_dir)

    assert result.returncode == 5
    assert "sleep failed" in result.stderr
    assert (state_dir / "sleep_arg.txt").read_text(encoding="utf-8").strip() == "3600"
    assert len(tmux_calls) == 2
    assert tmux_calls[0] == [
        "-talk",
        "-from",
        "榕",
        "-to",
        "神秘人",
        "-agents-list",
        str(repo_root / "agents/codex-multi-agents/agents-lists.md"),
        "-message",
        DEFAULT_ADMIN_MESSAGE,
    ]
    assert tmux_calls[1] == [
        "-talk",
        "-from",
        "榕",
        "-to",
        "小李飞刀",
        "-agents-list",
        str(repo_root / "agents/codex-multi-agents/agents-lists.md"),
        "-message",
        DEFAULT_BUSY_MESSAGE,
    ]
    assert not (state_dir / "list_args.bin").exists()


# TC-NA-002
# 测试目的: 验证循环模式命中 `1/3` 分支时会先执行一次管理员初始化。
# 对应功能实现文件路径: script/notify-admin.sh
# 对应 spec 文件路径: spec/script/notify-admin.md
def test_notify_admin_loop_may_trigger_admin_init(tmp_path: Path) -> None:
    repo_root, state_dir = build_fake_repo(tmp_path)

    result = run_script(repo_root, random_roll="0")
    list_args = read_null_separated_args(state_dir / "list_args.bin")
    tmux_calls = read_tmux_calls(state_dir)

    assert result.returncode == 5
    assert list_args == [
        "-file",
        str(repo_root / "agents/codex-multi-agents/agents-lists.md"),
        "-init",
        "-name",
        "神秘人",
    ]
    assert tmux_calls
    assert tmux_calls[0][0:2] == ["-talk", "-from"]


# TC-NA-003
# 测试目的: 验证循环模式未命中 `1/3` 分支时不会执行管理员初始化。
# 对应功能实现文件路径: script/notify-admin.sh
# 对应 spec 文件路径: spec/script/notify-admin.md
def test_notify_admin_loop_skips_admin_init_when_roll_misses(tmp_path: Path) -> None:
    repo_root, state_dir = build_fake_repo(tmp_path)

    result = run_script(repo_root, random_roll="2")
    tmux_calls = read_tmux_calls(state_dir)

    assert result.returncode == 5
    assert not (state_dir / "list_args.bin").exists()
    assert len(tmux_calls) == 2
    assert tmux_calls[0][-2:] == ["-message", DEFAULT_ADMIN_MESSAGE]
    assert tmux_calls[1][-2:] == ["-message", DEFAULT_BUSY_MESSAGE]


# TC-NA-004
# 测试目的: 验证 `-init` 模式直接调用管理员初始化脚本并成功退出。
# 对应功能实现文件路径: script/notify-admin.sh
# 对应 spec 文件路径: spec/script/notify-admin.md
def test_notify_admin_init_mode_calls_list_script(tmp_path: Path) -> None:
    repo_root, state_dir = build_fake_repo(tmp_path)

    result = run_script(repo_root, "-init")
    list_args = read_null_separated_args(state_dir / "list_args.bin")

    assert result.returncode == 0
    assert list_args == [
        "-file",
        str(repo_root / "agents/codex-multi-agents/agents-lists.md"),
        "-init",
        "-name",
        "神秘人",
    ]


# TC-NA-005
# 测试目的: 验证 `NOTIFY_ADMIN_RANDOM_ROLL` 超出 `0|1|2` 时脚本会 fail-fast 并给出稳定错误短语。
# 对应功能实现文件路径: script/notify-admin.sh
# 对应 spec 文件路径: spec/script/notify-admin.md
def test_notify_admin_rejects_invalid_random_roll(tmp_path: Path) -> None:
    repo_root, state_dir = build_fake_repo(tmp_path)

    result = run_script(repo_root, random_roll="7")

    assert result.returncode == 3
    assert "NOTIFY_ADMIN_RANDOM_ROLL must be 0, 1, or 2" in result.stderr
    assert not (state_dir / "list_args.bin").exists()
    assert not (state_dir / "tmux_count.txt").exists()


# TC-NA-006
# 测试目的: 验证 `NOTIFY_ADMIN_RANDOM_ROLL` 非数字时脚本同样 fail-fast，不会误发消息或初始化。
# 对应功能实现文件路径: script/notify-admin.sh
# 对应 spec 文件路径: spec/script/notify-admin.md
def test_notify_admin_rejects_non_numeric_random_roll(tmp_path: Path) -> None:
    repo_root, state_dir = build_fake_repo(tmp_path)

    result = run_script(repo_root, random_roll="abc")

    assert result.returncode == 3
    assert "NOTIFY_ADMIN_RANDOM_ROLL must be 0, 1, or 2" in result.stderr
    assert not (state_dir / "list_args.bin").exists()
    assert not (state_dir / "tmux_count.txt").exists()


# TC-NA-007
# 测试目的: 验证脚本在仓库内保持可通过 `bash -n` 的语法检查。
# 对应功能实现文件路径: script/notify-admin.sh
# 对应 spec 文件路径: spec/script/notify-admin.md
def test_notify_admin_shell_syntax_is_valid() -> None:
    result = subprocess.run(
        ["/bin/bash", "-n", str(SOURCE_SCRIPT)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
