"""codex-multi-agents-task.sh tests.

创建者: 榕
最后一次更改: jcc你莫辜负

功能说明:
- 覆盖 task 脚本的任务分发、完成、暂停、继续、改派、新建、删除、状态查询与错误返回码路径。

覆盖率信息:
- 当前覆盖率: `N/A`。该链路的功能实现为 shell 脚本 `skills/codex-multi-agents/scripts/codex-multi-agents-task.sh`，`pytest-cov` 无法直接采集脚本覆盖率，执行覆盖率命令会得到 `no-data-collected`。
- 达标判定: shell 实现按规则豁免 `95%` 覆盖率达标线。
- 当前以 `TC-001..049` 共 49 条测试用例作为覆盖基线，覆盖分发、分发前初始化、分发消息发送、完成、暂停、继续、改派、续接、新建、删除、状态查询、计划书进度、权限校验、并行上限、文件错误、结构错误与锁冲突路径。

覆盖率命令:
- `pytest -q --cov=skills/codex-multi-agents/scripts/codex-multi-agents-task.sh --cov-branch --cov-report=term-missing test/codex-multi-agents/test_codex-multi-agents-task.py`
- 功能校验命令: `pytest -q test/codex-multi-agents/test_codex-multi-agents-task.py`

关联文件:
- 功能实现: `skills/codex-multi-agents/scripts/codex-multi-agents-task.sh`
- Spec 文档: `spec/codex-multi-agents/scripts/codex-multi-agents-task.md`
- 测试文件: `test/codex-multi-agents/test_codex-multi-agents-task.py`

使用示例:
- `pytest -q test/codex-multi-agents/test_codex-multi-agents-task.py`
"""

from __future__ import annotations

import fcntl
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "skills/codex-multi-agents/scripts/codex-multi-agents-task.sh"

pytestmark = pytest.mark.infra


def run_script(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """调用待测 shell 脚本并返回执行结果。"""
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def row_running(
    task_id: str,
    owner: str,
    created_at: str,
    worktree: str,
    desc: str,
    depends: str,
    plan_doc: str,
    assignee: str,
    status: str,
    guide: str = "",
    record: str = "",
    type_kind: str = "build",
) -> str:
    return (
        f"| {task_id} | {owner} | {created_at} | {worktree} | {desc} | {type_kind} | {depends} | "
        f"{plan_doc} | {assignee} | {status} | {guide} | {record} |"
    )


def row_list(
    task_id: str,
    owner: str,
    created_at: str,
    worktree: str,
    desc: str,
    depends: str = "",
    plan_doc: str = "",
    assignee: str = "",
    record: str = "",
    type_kind: str = "build",
) -> str:
    return (
        f"| {task_id} | {owner} | {created_at} | {worktree} | {desc} | {type_kind} | {depends} | "
        f"{plan_doc} | {assignee} | {record} |"
    )


def agent_row(name: str, status: str = "free") -> str:
    return f"| {name} | {status} | {name}-session | codex | agent-{name} | 简介 | ./prompt.md | ./archive.md | 执行 |"


def write_agents_file(path: Path, rows: list[str] | None = None) -> None:
    """写入标准 agents-lists.md 测试文件。"""
    if rows is None:
        rows = [
            agent_row("worker-a", "free"),
            agent_row("worker-b", "busy"),
        ]

    text = "\n".join(
        [
            "# Agents 名单",
            "",
            "| 姓名 | 状态 | 会话 | 启动类型 | agent session | 介绍 | 提示词 | 归档文件 | 职责 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            *rows,
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")


def write_fake_tmux(bin_dir: Path, state_dir: Path, sessions: list[str] | None = None) -> Path:
    """写入 fake tmux 可执行文件，用于拦截 dispatch 内部触发的 talk。"""
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
    grep -Fxq "$target" "$sessions_file"
    ;;
  send-keys)
    [[ "${1-}" == "-t" ]] || exit 2
    target="${2-}"
    msg="${3-}"
    key="${4-}"
    echo "send:$target:$msg:$key" >> "$calls_file"
    ;;
  *)
    exit 0
    ;;
esac
""",
        encoding="utf-8",
    )
    fake_tmux.chmod(0o755)
    return calls_file


def write_todo_file(path: Path, running_rows: list[str] | None = None, list_rows: list[str] | None = None) -> None:
    """写入标准 TODO.md 测试文件。"""
    write_todo_file_current(path, running_rows=running_rows, list_rows=list_rows)


def write_todo_file_with_task_type(path: Path) -> None:
    """写入带任务类型列的标准 TODO.md 测试文件。"""
    text = "\n".join(
        [
            "## 正在执行的任务",
            "",
            "| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 任务类型 | 依赖任务 | 计划书 | 指派 | 状态 | 用户指导 | 记录文件 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            "| EX-1 | 李白 | 2026-03-08 16:10:00 +0800 | . | 创建 src | build |  |  | worker-a | 进行中 | xxx | ./log/ex1.md |",
            "| EX-2 | 杜甫 | 2026-03-08 16:20:00 +0800 | . | 创建 test | build |  |  | worker-b | 进行中 | xxx | ./log/ex2.md |",
            "",
            "## 需要用户确认的事项",
            "",
            "| 任务 ID | 创建时间 | worktree | 描述 | 用户确认状态 | 记录文件 |",
            "| --- | --- | --- | --- | --- | --- |",
            "| U-1 | 2026-03-08 16:00:00 +0800 | . | 描述 | 未确认 | ./log/u1.md |",
            "",
            "## 任务列表",
            "",
            "| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 任务类型 | 依赖任务 | 计划书 | 指派 | 记录文件 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            "| EX-3 | 苏轼 | 2026-03-08 16:30:00 +0800 |  | 删除 tmp/demo.txt | build |  |  |  | ./log/ex3.md |",
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")


def row_running_typed(
    task_id: str,
    owner: str,
    created_at: str,
    worktree: str,
    desc: str,
    type_kind: str,
    depends: str,
    plan_doc: str,
    assignee: str,
    status: str,
    guide: str = "",
    record: str = "",
) -> str:
    """渲染带任务类型列的运行中任务行。"""
    return (
        f"| {task_id} | {owner} | {created_at} | {worktree} | {desc} | {type_kind} | {depends} | "
        f"{plan_doc} | {assignee} | {status} | {guide} | {record} |"
    )


def row_list_typed(
    task_id: str,
    owner: str,
    created_at: str,
    worktree: str,
    desc: str,
    type_kind: str,
    depends: str = "",
    plan_doc: str = "",
    assignee: str = "",
    record: str = "",
) -> str:
    """渲染带任务类型列的任务列表行。"""
    return (
        f"| {task_id} | {owner} | {created_at} | {worktree} | {desc} | {type_kind} | {depends} | "
        f"{plan_doc} | {assignee} | {record} |"
    )


def write_todo_file_current(
    path: Path,
    running_rows: list[str] | None = None,
    list_rows: list[str] | None = None,
) -> None:
    """写入当前 task 脚本使用的 TODO.md 表头。"""
    if running_rows is None:
        running_rows = [
            row_running_typed(
                "EX-1",
                "李白",
                "2026-03-08 16:10:00 +0800",
                ".",
                "创建 src",
                "build",
                "",
                "",
                "worker-a",
                "进行中",
                "xxx",
                "./log/ex1.md",
            ),
            row_running_typed(
                "EX-2",
                "杜甫",
                "2026-03-08 16:20:00 +0800",
                ".",
                "创建 test",
                "build",
                "",
                "",
                "worker-b",
                "进行中",
                "xxx",
                "./log/ex2.md",
            ),
        ]
    if list_rows is None:
        list_rows = [
            row_list_typed(
                "EX-3",
                "苏轼",
                "2026-03-08 16:30:00 +0800",
                "",
                "删除 tmp/demo.txt",
                "build",
                "",
                "",
                "",
                "./log/ex3.md",
            )
        ]

    text = "\n".join(
        [
            "## 正在执行的任务",
            "",
            "| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 任务类型 | 依赖任务 | 计划书 | 指派 | 状态 | 用户指导 | 记录文件 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            *running_rows,
            "",
            "## 需要用户确认的事项",
            "",
            "| 任务 ID | 创建时间 | worktree | 描述 | 用户确认状态 | 记录文件 |",
            "| --- | --- | --- | --- | --- | --- |",
            "| U-1 | 2026-03-08 16:00:00 +0800 | . | 描述 | 未确认 | ./log/u1.md |",
            "",
            "## 任务列表",
            "",
            "| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 任务类型 | 依赖任务 | 计划书 | 指派 | 记录文件 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            *list_rows,
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")


def agent_row_with_role(name: str, status: str, duty: str, session: str | None = None, intro: str = "简介") -> str:
    """渲染带职责与会话名的角色行。"""
    resolved_session = session or f"{name}-session"
    return f"| {name} | {status} | {resolved_session} | codex | agent-{name} | {intro} | ./prompt.md | ./archive.md | {duty} |"


def parse_section_rows(text: str, heading: str) -> list[list[str]]:
    """解析指定标题下的首个 markdown 表格数据行。"""
    lines = text.splitlines()
    section_idx = -1
    for i, line in enumerate(lines):
        if line.strip() == heading:
            section_idx = i
            break
    if section_idx < 0:
        return []

    section_end = len(lines)
    for i in range(section_idx + 1, len(lines)):
        if lines[i].startswith("## "):
            section_end = i
            break

    header_idx = -1
    for i in range(section_idx + 1, max(section_end - 1, section_idx + 1)):
        s1 = lines[i].strip()
        s2 = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if s1.startswith("|") and s1.endswith("|") and s2.startswith("|") and "---" in s2:
            header_idx = i
            break
    if header_idx < 0:
        return []

    rows: list[list[str]] = []
    idx = header_idx + 2
    while idx < section_end:
        s = lines[idx].strip()
        if not (s.startswith("|") and s.endswith("|")):
            break
        rows.append([c.strip() for c in s[1:-1].split("|")])
        idx += 1

    return rows


def get_agent_status(path: Path, name: str) -> str:
    rows = parse_section_rows(path.read_text(encoding="utf-8"), "# Agents 名单")
    for row in rows:
        if row[0] == name:
            return row[1]
    raise AssertionError(f"agent not found: {name}")


# TC-001
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证 -dispatch 成功将任务从任务列表移入正在执行并写入指派/状态。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_dispatch_task_success(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file_current(todo)
    write_agents_file(agents)

    result = run_script("-file", str(todo), "-dispatch", "-task_id", "EX-3", "-to", "worker-a", "-agents-list", str(agents))
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")
    list_rows = parse_section_rows(content, "## 任务列表")

    assert result.returncode == 0
    assert "OK: dispatch EX-3 -> worker-a" in result.stdout
    assert "OK: replace worker-a 状态" in result.stdout
    assert any(
        r[0] == "EX-3"
        and r[1] == "苏轼"
        and r[8] == "worker-a"
        and r[9] == "进行中"
        and r[11] == "./log/ex3.md"
        and r[3] == ""
        and r[2] != ""
        for r in running_rows
    )
    assert not any(r[0] == "EX-3" for r in list_rows)
    assert get_agent_status(agents, "worker-a") == "busy"


# TC-001A
# 创建者: OpenAI
# 最后一次更改: OpenAI
# 测试目的: 验证 -dispatch 不要求显式提供 -type，直接使用任务记录中的任务类型。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_dispatch_does_not_require_type(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file_with_task_type(todo)
    write_agents_file(agents, [agent_row("神秘人", "free"), agent_row("worker-a", "free"), agent_row("worker-b", "free")])

    env = os.environ.copy()
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "神秘人"
    env["CODEX_MULTI_AGENTS_PERMISSION_AGENTS_FILE"] = str(agents)
    result = run_script("-file", str(todo), "-dispatch", "-task_id", "EX-3", "-to", "worker-a", "-agents-list", str(agents), env=env)

    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")

    assert result.returncode == 0
    assert any(r[0] == "EX-3" and r[5] == "build" and r[8] == "worker-a" and r[9] == "进行中" for r in running_rows)


# TC-002
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证 -dispatch 任务不存在返回 RC=3。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_dispatch_missing_task_returns_rc3(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file_current(todo)
    write_agents_file(agents)

    result = run_script("-file", str(todo), "-dispatch", "-task_id", "BAD", "-to", "worker-a", "-agents-list", str(agents))

    assert result.returncode == 3
    assert "task not found in task list: BAD" in result.stderr


# TC-003
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证 -done 成功移除任务并写入 DONE.md。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_done_task_moves_to_done_file_success(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file_current(todo)
    write_agents_file(agents, [agent_row("worker-a", "busy"), agent_row("worker-b", "busy")])
    log_path = "./agents/codex-multi-agents/log/task-EX-1.log"

    result = run_script("-file", str(todo), "-done", "-task_id", "EX-1", "-log", log_path, "-agents-list", str(agents))
    todo_text = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(todo_text, "## 正在执行的任务")

    done_file = tmp_path / "DONE.md"
    done_text = done_file.read_text(encoding="utf-8")

    assert result.returncode == 0
    assert "OK: done EX-1" in result.stdout
    assert "OK: replace worker-a 状态" in result.stdout
    assert not any(r[0] == "EX-1" for r in running_rows)

    assert done_file.exists()
    assert "| EX-1 |" in done_text
    assert "| 已完成 |" in done_text
    assert log_path in done_text
    assert re.search(r"\| EX-1 \|.*\| 已完成 \| \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+-]\d{4} \|", done_text)
    assert get_agent_status(agents, "worker-a") == "free"


# TC-003A
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-13 07:40:00 +0800
# 最近一次运行成功时间: 2026-04-13 07:40:00 +0800
# 测试目的: 验证 合并角色调用 -done 可成功完成任务。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_done_allows_merge_operator(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file_current(
        todo,
        running_rows=[
            row_running_typed(
                "EX-1",
                "李白",
                "2026-03-08 16:10:00 +0800",
                ".",
                "合并收口",
                "merge",
                "",
                "",
                "李白",
                "进行中",
                "",
                "./log/ex1.md",
            )
        ],
    )
    write_agents_file(
        agents,
        rows=[
            "| 李白 | busy | 李白 | codex | 李白 | 合并收口 | ./prompt.md | ./archive.md | 合并 |",
            agent_row("worker-a", "busy"),
            agent_row("worker-b", "busy"),
        ],
    )

    env = os.environ.copy()
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "李白"
    env["CODEX_MULTI_AGENTS_PERMISSION_AGENTS_FILE"] = str(agents)
    result = run_script(
        "-file",
        str(todo),
        "-done",
        "-task_id",
        "EX-1",
        "-log",
        "./log/record.md",
        "-agents-list",
        str(agents),
        env=env,
    )

    done_file = tmp_path / "DONE.md"
    done_text = done_file.read_text(encoding="utf-8")
    running_rows = parse_section_rows(todo.read_text(encoding="utf-8"), "## 正在执行的任务")

    assert result.returncode == 0
    assert "OK: done EX-1" in result.stdout
    assert "EX-1" in done_text
    assert not any(r[0] == "EX-1" for r in running_rows)
    assert get_agent_status(agents, "李白") == "free"


# TC-003B
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-13 07:40:00 +0800
# 最近一次运行成功时间: 2026-04-13 07:40:00 +0800
# 测试目的: 验证 合并角色不能完成非 merge 任务。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_done_rejects_merge_operator_for_non_merge_task(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file_current(
        todo,
        running_rows=[
            row_running_typed(
                "EX-1",
                "李白",
                "2026-03-08 16:10:00 +0800",
                ".",
                "执行 build",
                "build",
                "",
                "",
                "李白",
                "进行中",
                "",
                "./log/ex1.md",
            )
        ],
    )
    write_agents_file(
        agents,
        rows=[
            "| 李白 | busy | 李白 | codex | 李白 | 合并收口 | ./prompt.md | ./archive.md | 合并 |",
        ],
    )

    env = os.environ.copy()
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "李白"
    env["CODEX_MULTI_AGENTS_PERMISSION_AGENTS_FILE"] = str(agents)
    result = run_script(
        "-file",
        str(todo),
        "-done",
        "-task_id",
        "EX-1",
        "-log",
        "./log/record.md",
        "-agents-list",
        str(agents),
        env=env,
    )

    running_rows = parse_section_rows(todo.read_text(encoding="utf-8"), "## 正在执行的任务")
    assert result.returncode == 3
    assert "merge operator can only complete merge tasks: EX-1" in result.stderr
    assert any(r[0] == "EX-1" for r in running_rows)


# TC-003C
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-13 07:40:00 +0800
# 最近一次运行成功时间: 2026-04-13 07:40:00 +0800
# 测试目的: 验证 合并角色不能完成他人 merge 任务。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_done_rejects_merge_operator_for_other_assignee(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file_current(
        todo,
        running_rows=[
            row_running_typed(
                "EX-1",
                "李白",
                "2026-03-08 16:10:00 +0800",
                ".",
                "合并收口",
                "merge",
                "",
                "",
                "worker-a",
                "进行中",
                "",
                "./log/ex1.md",
            )
        ],
    )
    write_agents_file(
        agents,
        rows=[
            "| 李白 | busy | 李白 | codex | 李白 | 合并收口 | ./prompt.md | ./archive.md | 合并 |",
            agent_row("worker-a", "busy"),
        ],
    )

    env = os.environ.copy()
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "李白"
    env["CODEX_MULTI_AGENTS_PERMISSION_AGENTS_FILE"] = str(agents)
    result = run_script(
        "-file",
        str(todo),
        "-done",
        "-task_id",
        "EX-1",
        "-log",
        "./log/record.md",
        "-agents-list",
        str(agents),
        env=env,
    )

    running_rows = parse_section_rows(todo.read_text(encoding="utf-8"), "## 正在执行的任务")
    assert result.returncode == 3
    assert "merge operator can only complete own tasks: EX-1" in result.stderr
    assert any(r[0] == "EX-1" for r in running_rows)


# TC-004
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证 -done 任务不存在返回 RC=3。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_done_missing_task_returns_rc3(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file_current(todo)
    write_agents_file(agents)

    result = run_script("-file", str(todo), "-done", "-task_id", "BAD", "-log", "./log/bad.log", "-agents-list", str(agents))

    assert result.returncode == 3
    assert "task not found in running list: BAD" in result.stderr


# TC-005
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证 -pause 成功将任务状态更新为 暂停。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_pause_task_success(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file_current(todo)
    write_agents_file(agents, [agent_row("worker-a", "busy"), agent_row("worker-b", "busy")])

    result = run_script("-file", str(todo), "-pause", "-task_id", "EX-2", "-agents-list", str(agents))
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")

    assert result.returncode == 0
    assert "OK: pause EX-2" in result.stdout
    assert "OK: replace worker-b 状态" in result.stdout
    assert any(r[0] == "EX-2" and r[9] == "暂停" for r in running_rows)
    assert get_agent_status(agents, "worker-b") == "free"


# TC-006
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证 -pause 任务不存在返回 RC=3。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_pause_missing_task_returns_rc3(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file_current(todo)
    write_agents_file(agents)

    result = run_script("-file", str(todo), "-pause", "-task_id", "BAD", "-agents-list", str(agents))

    assert result.returncode == 3
    assert "task not found in running list: BAD" in result.stderr


# TC-007
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证 -new 带指派创建任务并写入任务列表。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_new_task_with_assignee_success(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file_current(todo)

    result = run_script(
        "-file",
        str(todo),
        "-new",
        "-info",
        "实现任务调度器告警",
        "-type",
        "build",
        "-to",
        "worker-b",
        "-from",
        "李白",
        "-worktree",
        "repo-x",
        "-depends",
        "EX-2 EX-3",
        "-plan",
        "ARCHITECTURE/plan/x.md",
        "-log",
        "./log/record-1.log",
    )
    content = todo.read_text(encoding="utf-8")
    list_rows = parse_section_rows(content, "## 任务列表")

    assert result.returncode == 0
    assert re.search(r"OK: new T-\d{8}-[0-9a-f]{8}", result.stdout)
    assert any(
        r[4] == "实现任务调度器告警"
        and r[5] == "build"
        and r[8] == "worker-b"
        and r[1] == "李白"
        and r[3] == "repo-x"
        and r[9] == "./log/record-1.log"
        and re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+-]\d{4}", r[2] or "")
        for r in list_rows
    )


# TC-008
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证 -new 不带指派创建任务并写入任务列表。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_new_task_without_assignee_success(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file(todo)

    result = run_script(
        "-file",
        str(todo),
        "-new",
        "-info",
        "补充单元测试",
        "-type",
        "build",
        "-worktree",
        "repo-y",
        "-depends",
        "None",
        "-plan",
        "None",
    )
    content = todo.read_text(encoding="utf-8")
    list_rows = parse_section_rows(content, "## 任务列表")

    assert result.returncode == 0
    assert re.search(r"OK: new T-\d{8}-[0-9a-f]{8}", result.stdout)
    assert any(
        r[4] == "补充单元测试"
        and r[5] == "build"
        and r[8] == ""
        and r[1] == ""
        and r[3] == "repo-y"
        and r[9] == ""
        and re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+-]\d{4}", r[2] or "")
        for r in list_rows
    )


# TC-009
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证缺少必填参数返回 RC=1。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_argument_error_returns_rc1(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file(todo)

    result = run_script("-file", str(todo), "-done", "-task_id", "EX-1")

    assert result.returncode == 1
    assert "-done requires -log" in result.stderr


# TC-010
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证 TODO 文件不存在返回 RC=2。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_file_not_found_returns_rc2(tmp_path: Path) -> None:
    missing = tmp_path / "missing.md"

    result = run_script(
        "-file",
        str(missing),
        "-new",
        "-info",
        "desc",
        "-type",
        "build",
        "-worktree",
        "repo-missing",
        "-depends",
        "None",
        "-plan",
        "None",
    )

    assert result.returncode == 2
    assert "file not found" in result.stderr


# TC-011
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证表结构不合法返回 RC=2。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_invalid_todo_structure_returns_rc2(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    todo.write_text(
        "\n".join(
            [
                "## 非法任务段落",
                "",
                "| A | B |",
                "| --- | --- |",
                "| 1 | 2 |",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_script(
        "-file",
        str(todo),
        "-new",
        "-info",
        "desc",
        "-type",
        "build",
        "-worktree",
        "repo-invalid",
        "-depends",
        "None",
        "-plan",
        "None",
    )

    assert result.returncode == 2
    assert "invalid table format" in result.stderr


# TC-012
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证锁冲突时返回 RC=4。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_lock_conflict_returns_rc4(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(todo)
    write_agents_file(agents)

    with todo.open("r", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = run_script("-file", str(todo), "-dispatch", "-task_id", "EX-3", "-to", "worker-a", "-agents-list", str(agents))

    assert result.returncode == 4
    assert "cannot acquire lock" in result.stderr


# TC-013
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证 -status -doing 输出正在执行任务表。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_status_doing_outputs_running_table(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file(todo)

    result = run_script(str(todo), "-file", "-status", "-doing")

    assert result.returncode == 0
    assert "正在执行的任务" not in result.stdout
    assert "任务列表" not in result.stdout
    assert "EX-1" in result.stdout
    assert "EX-3" not in result.stdout


# TC-014
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证 -status -task-list 输出任务列表表。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_status_task_list_outputs_list_table(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file(todo)

    result = run_script(str(todo), "-file", "-status", "-task-list")

    assert result.returncode == 0
    assert "正在执行的任务" not in result.stdout
    assert "任务列表" not in result.stdout
    assert "EX-3" in result.stdout
    assert "EX-1" not in result.stdout


# TC-015
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-25 03:41:48 +0800
# 最近一次运行成功时间: 2026-03-25 03:41:48 +0800
# 测试目的: 验证 -status 参数组合错误返回 RC=1。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_status_requires_exactly_one_mode(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file(todo)

    result = run_script(str(todo), "-file", "-status")
    assert result.returncode == 1
    assert "-status requires exactly one of -doing/-task-list/-plan-list" in result.stderr

    result = run_script(str(todo), "-file", "-status", "-doing", "-task-list")
    assert result.returncode == 1
    assert "-status requires exactly one of -doing/-task-list/-plan-list" in result.stderr


# TC-015A
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-08 06:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 06:47:00 +0800
# 测试目的: 验证 -status 在 TODO 表头不匹配时返回 RC=2（不应误返回 RC=0）。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_status_invalid_table_returns_rc2(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    todo.write_text(
        "\n".join(
            [
                "## 正在执行的任务",
                "",
                "| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 指派 | 状态 | 用户指导 | 记录文件 |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                "",
                "## 任务列表",
                "",
                "| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 指派 | 记录文件 |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_script("-file", str(todo), "-status", "-task-list")
    assert result.returncode == 2
    assert "invalid table format" in result.stderr


# TC-016
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-25 03:41:48 +0800
# 最近一次运行成功时间: 2026-03-25 03:41:48 +0800
# 测试目的: 验证 -dispatch 携带 -message 时，会先执行一次 -init，再调用 tmux 对话脚本向目标会话发消息。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_dispatch_with_message_sends_talk_success(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    config = tmp_path / "config.txt"
    talk_log = tmp_path / "log" / "talk.log"
    calls_file = write_fake_tmux(bin_dir, state_dir, sessions=["worker-a-session"])
    write_todo_file_current(todo)
    write_agents_file(agents)
    config.write_text(
        "\n".join(
            [
                "ROOT_NAME=神秘人",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["CODEX_MULTI_AGENTS_CONFIG"] = str(config)
    env["CODEX_MULTI_AGENTS_DISPATCH_INIT_ROLL"] = "0"
    result = run_script(
        "-file",
        str(todo),
        "-dispatch",
        "-task_id",
        "EX-3",
        "-to",
        "worker-a",
        "-agents-list",
        str(agents),
        "-message",
        "请处理任务 EX-3，完成后回报。",
        env=env,
    )

    assert result.returncode == 0
    assert "OK: dispatch EX-3 -> worker-a" in result.stdout
    assert "OK: talk 神秘人 -> worker-a (worker-a-session)" in result.stdout
    calls_text = calls_file.read_text(encoding="utf-8")
    assert "你的名字叫做worker-a" in calls_text
    assert calls_text.index("你的名字叫做worker-a") < calls_text.index("@神秘人向@worker-a发起会话: 请处理任务 EX-3，完成后回报。")
    assert "send:worker-a-session:@神秘人向@worker-a发起会话: 请处理任务 EX-3，完成后回报。:" in calls_text
    assert "@神秘人向@worker-a发起会话: 请处理任务 EX-3，完成后回报。" in talk_log.read_text(encoding="utf-8")


# TC-017
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:24:46 +0800
# 最近一次运行成功时间: 2026-03-22 17:24:46 +0800
# 测试目的: 验证 -dispatch 携带 -message 时，即使分发前 -init 失败，仍会保留已提交的分发结果并在消息发送失败时返回错误。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_dispatch_with_message_failure_keeps_dispatch_result(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    config = tmp_path / "config.txt"
    write_fake_tmux(bin_dir, state_dir, sessions=[])
    write_todo_file_current(todo)
    write_agents_file(agents)
    config.write_text("ROOT_NAME=神秘人\n", encoding="utf-8")

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["CODEX_MULTI_AGENTS_CONFIG"] = str(config)
    env["CODEX_MULTI_AGENTS_DISPATCH_INIT_ROLL"] = "0"
    result = run_script(
        "-file",
        str(todo),
        "-dispatch",
        "-task_id",
        "EX-3",
        "-to",
        "worker-a",
        "-agents-list",
        str(agents),
        "-message",
        "请处理任务 EX-3",
        env=env,
    )
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")
    list_rows = parse_section_rows(content, "## 任务列表")

    assert result.returncode == 3
    assert "WARN: dispatch init failed for worker-a:" in result.stderr
    assert "target session not found: worker-a-session" in result.stderr
    assert "dispatch succeeded but message delivery failed for task EX-3" in result.stderr
    assert any(r[0] == "EX-3" and r[8] == "worker-a" and r[9] == "进行中" for r in running_rows)
    assert not any(r[0] == "EX-3" for r in list_rows)
    assert get_agent_status(agents, "worker-a") == "busy"


# TC-018
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-25 03:41:48 +0800
# 最近一次运行成功时间: 2026-03-25 03:41:48 +0800
# 测试目的: 验证 -dispatch 在真正分发前会固定调用一次 list -init，并在未提供 -message 时发送默认模板消息。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_dispatch_runs_init_before_dispatch(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    calls_file = write_fake_tmux(bin_dir, state_dir, sessions=["worker-a-session"])
    write_todo_file_current(todo)
    write_agents_file(agents)

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["CODEX_MULTI_AGENTS_DISPATCH_INIT_ROLL"] = "0"
    result = run_script(
        "-file",
        str(todo),
        "-dispatch",
        "-task_id",
        "EX-3",
        "-to",
        "worker-a",
        "-agents-list",
        str(agents),
        env=env,
    )

    assert result.returncode == 0
    assert "OK: dispatch EX-3 -> worker-a" in result.stdout
    assert "OK: talk 神秘人 -> worker-a (worker-a-session)" in result.stdout
    calls_text = calls_file.read_text(encoding="utf-8")
    assert "你的名字叫做worker-a" in calls_text
    expected_message = (
        "@神秘人向@worker-a发起会话: 请处理任务 EX-3（删除 tmp/demo.txt）。"
        "记录文件=./log/ex3.md；"
        f"完成后按 {REPO_ROOT}/agents/standard/任务记录约定.md 记录并回报管理员；"
        "流程不清楚请询问管理员；实现/架构问题请询问架构师。"
    )
    assert expected_message in calls_text
    assert calls_text.index("你的名字叫做worker-a") < calls_text.index(expected_message)
    assert get_agent_status(agents, "worker-a") == "busy"


# TC-046
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-08 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-08 00:00:00 +0800
# 测试目的: 验证 -dispatch 未提供 -message 时，若默认消息发送失败仅告警且不回滚分发结果。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_dispatch_without_message_talk_failure_is_warning(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    write_fake_tmux(bin_dir, state_dir, sessions=[])
    write_todo_file_current(todo)
    write_agents_file(agents)

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["CODEX_MULTI_AGENTS_DISPATCH_INIT_ROLL"] = "0"
    result = run_script(
        "-file",
        str(todo),
        "-dispatch",
        "-task_id",
        "EX-3",
        "-to",
        "worker-a",
        "-agents-list",
        str(agents),
        env=env,
    )

    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")
    list_rows = parse_section_rows(content, "## 任务列表")
    assert result.returncode == 0
    assert "OK: dispatch EX-3 -> worker-a" in result.stdout
    assert "WARN: auto dispatch talk failed for task EX-3:" in result.stderr
    assert any(r[0] == "EX-3" and r[8] == "worker-a" and r[9] == "进行中" for r in running_rows)
    assert not any(r[0] == "EX-3" for r in list_rows)
    assert get_agent_status(agents, "worker-a") == "busy"


# TC-047
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-08 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-08 00:00:00 +0800
# 测试目的: 验证 -dispatch 未提供 -message 时，默认模板消息会按实际存在的 worktree/计划书拼接字段。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_dispatch_without_message_template_includes_worktree_and_plan(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    calls_file = write_fake_tmux(bin_dir, state_dir, sessions=["worker-a-session"])
    write_todo_file_current(
        todo,
        list_rows=[
            row_list_typed(
                "EX-3",
                "苏轼",
                "2026-03-08 16:30:00 +0800",
                "/tmp/wt-ex3",
                "删除 tmp/demo.txt",
                "build",
                "",
                "ARCHITECTURE/plan/demo.md",
                "",
                "./log/ex3.md",
            )
        ],
    )
    write_agents_file(agents)

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["CODEX_MULTI_AGENTS_DISPATCH_INIT_ROLL"] = "0"
    result = run_script(
        "-file",
        str(todo),
        "-dispatch",
        "-task_id",
        "EX-3",
        "-to",
        "worker-a",
        "-agents-list",
        str(agents),
        env=env,
    )

    assert result.returncode == 0
    assert "OK: dispatch EX-3 -> worker-a" in result.stdout
    calls_text = calls_file.read_text(encoding="utf-8")
    expected_message = (
        "@神秘人向@worker-a发起会话: 请处理任务 EX-3（删除 tmp/demo.txt）。"
        "worktree=/tmp/wt-ex3；计划书=ARCHITECTURE/plan/demo.md；记录文件=./log/ex3.md；"
        f"完成后按 {REPO_ROOT}/agents/standard/任务记录约定.md 记录并回报管理员；"
        "流程不清楚请询问管理员；实现/架构问题请询问架构师。"
    )
    assert expected_message in calls_text


# TC-019
# 创建者: 榕
# 最后一次更改: 榕
# 最近一次运行测试时间: 2026-03-26 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-26 00:00:00 +0800
# 测试目的: 验证 -continue 成功将暂停任务恢复为进行中并同步角色状态为 busy。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_continue_task_success(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(
        todo,
        running_rows=[
            row_running("EX-1", "李白", "2026-03-08 16:10:00 +0800", ".", "创建 src", "", "", "worker-a", "进行中", "xxx", "./log/ex1.md"),
            row_running("EX-2", "杜甫", "2026-03-08 16:20:00 +0800", ".", "创建 test", "", "", "worker-b", "暂停", "xxx", "./log/ex2.md"),
        ],
    )
    write_agents_file(agents, [agent_row("worker-a", "busy"), agent_row("worker-b", "free")])

    result = run_script("-file", str(todo), "-continue", "-task_id", "EX-2", "-agents-list", str(agents))
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")

    assert result.returncode == 0
    assert "OK: continue EX-2" in result.stdout
    assert "OK: replace worker-b 状态" in result.stdout
    assert any(r[0] == "EX-2" and r[9] == "进行中" for r in running_rows)
    assert get_agent_status(agents, "worker-b") == "busy"


# TC-020
# 创建者: 榕
# 最后一次更改: 榕
# 最近一次运行测试时间: 2026-03-26 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-26 00:00:00 +0800
# 测试目的: 验证 -continue 任务不存在时返回 RC=3。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_continue_missing_task_returns_rc3(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(todo)
    write_agents_file(agents)

    result = run_script("-file", str(todo), "-continue", "-task_id", "BAD", "-agents-list", str(agents))

    assert result.returncode == 3
    assert "task not found in running list: BAD" in result.stderr


# TC-021
# 创建者: 榕
# 最后一次更改: 榕
# 最近一次运行测试时间: 2026-03-26 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-26 00:00:00 +0800
# 测试目的: 验证 -continue 仅允许继续状态为暂停的任务。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_continue_requires_paused_status(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(todo)
    write_agents_file(agents)

    result = run_script("-file", str(todo), "-continue", "-task_id", "EX-2", "-agents-list", str(agents))

    assert result.returncode == 3
    assert "task status is not paused: EX-2" in result.stderr


# TC-022
# 创建者: 榕
# 最后一次更改: 榕
# 最近一次运行测试时间: 2026-03-26 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-26 00:00:00 +0800
# 测试目的: 验证 -continue 缺少 -agents-list 参数时返回 RC=1。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_continue_requires_agents_list(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file(todo)

    result = run_script("-file", str(todo), "-continue", "-task_id", "EX-2")

    assert result.returncode == 1
    assert "-continue requires -agents-list" in result.stderr


# TC-023
# 创建者: 神秘人
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-26 11:00:00 +0800
# 最近一次运行成功时间: 2026-03-26 11:00:00 +0800
# 测试目的: 验证 -reassign 成功更新任务指派并同步旧/新角色状态。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_reassign_task_success(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(
        todo,
        running_rows=[
            row_running("EX-1", "李白", "2026-03-08 16:10:00 +0800", ".", "创建 src", "", "", "worker-a", "进行中", "xxx", "./log/ex1.md"),
            row_running("EX-2", "杜甫", "2026-03-08 16:20:00 +0800", ".", "创建 test", "", "", "worker-b", "进行中", "xxx", "./log/ex2.md"),
        ],
    )
    write_agents_file(agents, [agent_row("worker-a", "busy"), agent_row("worker-b", "busy"), agent_row("worker-c", "free")])

    result = run_script("-file", str(todo), "-reassign", "-task_id", "EX-2", "-to", "worker-c", "-agents-list", str(agents))
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")

    assert result.returncode == 0
    assert "OK: reassign EX-2 -> worker-c" in result.stdout
    assert any(r[0] == "EX-2" and r[8] == "worker-c" for r in running_rows)
    assert get_agent_status(agents, "worker-a") == "busy"
    assert get_agent_status(agents, "worker-b") == "free"
    assert get_agent_status(agents, "worker-c") == "busy"


# TC-024
# 创建者: 神秘人
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-26 11:00:00 +0800
# 最近一次运行成功时间: 2026-03-26 11:00:00 +0800
# 测试目的: 验证 -reassign 任务不存在时返回 RC=3。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_reassign_missing_task_returns_rc3(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(todo)
    write_agents_file(agents)

    result = run_script("-file", str(todo), "-reassign", "-task_id", "BAD", "-to", "worker-a", "-agents-list", str(agents))

    assert result.returncode == 3
    assert "task not found in running list: BAD" in result.stderr


# TC-025
# 创建者: 神秘人
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-26 11:00:00 +0800
# 最近一次运行成功时间: 2026-03-26 11:00:00 +0800
# 测试目的: 验证 -reassign 缺少 -agents-list 参数时返回 RC=1。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_reassign_requires_agents_list(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file(todo)

    result = run_script("-file", str(todo), "-reassign", "-task_id", "EX-2", "-to", "worker-a")

    assert result.returncode == 1
    assert "-reassign requires -agents-list" in result.stderr


# TC-028A
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 测试目的: 验证 -reassign 目标角色为 busy 时返回 RC=3。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_reassign_rejects_busy_agent(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(
        todo,
        running_rows=[
            row_running("EX-1", "李白", "2026-03-08 16:10:00 +0800", ".", "创建 src", "", "", "worker-a", "进行中", "xxx", "./log/ex1.md"),
            row_running("EX-2", "杜甫", "2026-03-08 16:20:00 +0800", ".", "创建 test", "", "", "worker-b", "进行中", "xxx", "./log/ex2.md"),
        ],
    )
    write_agents_file(agents, [agent_row("worker-a", "busy"), agent_row("worker-b", "busy")])

    result = run_script("-file", str(todo), "-reassign", "-task_id", "EX-1", "-to", "worker-b", "-agents-list", str(agents))
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")

    assert result.returncode == 3
    assert "agent is busy, cannot reassign: worker-b" in result.stderr
    assert any(r[0] == "EX-1" and r[8] == "worker-a" for r in running_rows)


# TC-026
# 创建者: 神秘人
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-29 19:15:00 +0800
# 最近一次运行成功时间: 2026-03-29 19:15:00 +0800
# 测试目的: 验证 -delete 成功删除任务列表中的任务。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_delete_task_list_success(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file(todo)

    result = run_script("-file", str(todo), "-delete", "-task_id", "EX-3")
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")
    list_rows = parse_section_rows(content, "## 任务列表")

    assert result.returncode == 0
    assert "OK: delete EX-3" in result.stdout
    assert any(r[0] == "EX-1" for r in running_rows)
    assert not any(r[0] == "EX-3" for r in list_rows)


# TC-027
# 创建者: 神秘人
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-29 19:15:00 +0800
# 最近一次运行成功时间: 2026-03-29 19:15:00 +0800
# 测试目的: 验证 -delete 任务不存在返回 RC=3。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_delete_missing_task_returns_rc3(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file(todo)

    result = run_script("-file", str(todo), "-delete", "-task_id", "BAD")

    assert result.returncode == 3
    assert "task not found in task list: BAD" in result.stderr


# TC-028
# 创建者: 神秘人
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-29 19:15:00 +0800
# 最近一次运行成功时间: 2026-03-29 19:15:00 +0800
# 测试目的: 验证 -delete 任务位于正在执行列表时返回 RC=3。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_delete_running_task_returns_rc3(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file(todo)

    result = run_script("-file", str(todo), "-delete", "-task_id", "EX-1")
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")

    assert result.returncode == 3
    assert "task already exists in running list: EX-1" in result.stderr
    assert any(r[0] == "EX-1" for r in running_rows)


# TC-029
# 创建者: 神秘人
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-31 10:20:00 +0800
# 最近一次运行成功时间: 2026-03-31 10:20:00 +0800
# 测试目的: 验证 -delete 允许删除状态为暂停的正在执行任务。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_delete_paused_running_task_success(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(
        todo,
        running_rows=[
            row_running("EX-1", "李白", "2026-03-08 16:10:00 +0800", ".", "创建 src", "", "", "worker-a", "进行中", "xxx", "./log/ex1.md"),
            row_running("EX-2", "杜甫", "2026-03-08 16:20:00 +0800", ".", "创建 test", "", "", "worker-b", "暂停", "xxx", "./log/ex2.md"),
        ],
    )
    write_agents_file(agents, rows=[agent_row("worker-a", "busy"), agent_row("worker-b", "free")])

    result = run_script("-file", str(todo), "-delete", "-task_id", "EX-2")
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")
    list_rows = parse_section_rows(content, "## 任务列表")

    assert result.returncode == 0
    assert "OK: delete EX-2" in result.stdout
    assert any(r[0] == "EX-1" for r in running_rows)
    assert not any(r[0] == "EX-2" for r in running_rows)
    assert not any(r[0] == "EX-2" for r in list_rows)


# TC-030
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-08 13:40:00 +0800
# 最近一次运行成功时间: 2026-04-08 13:40:00 +0800
# 测试目的: 验证 -next 成功将运行中任务回退到任务列表并更新描述。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_next_task_moves_running_to_task_list_success(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    calls_file = write_fake_tmux(bin_dir, state_dir, sessions=["神秘人-session"])
    write_todo_file_current(todo)
    write_agents_file(
        agents,
        rows=[
            agent_row_with_role("神秘人", "free", "管理员", "神秘人-session", "管理员"),
            agent_row_with_role("worker-a", "busy", "开发"),
            agent_row_with_role("worker-b", "busy", "开发"),
        ],
    )

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["CODEX_MULTI_AGENTS_ADMIN_USERS"] = "神秘人"
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "worker-b"

    result = run_script(
        "-file",
        str(todo),
        "-next",
        "-task_id",
        "EX-2",
        "-from",
        "worker-b",
        "-type",
        "review",
        "-message",
        "下一阶段：补齐边界用例",
        "-agents-list",
        str(agents),
        env=env,
    )
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")
    list_rows = parse_section_rows(content, "## 任务列表")

    assert result.returncode == 0
    assert "OK: next EX-2" in result.stdout
    assert "OK: replace worker-b 状态" in result.stdout
    assert "OK: talk worker-b -> 神秘人 (神秘人-session)" in result.stdout
    assert not any(r[0] == "EX-2" for r in running_rows)
    assert any(
        r[0] == "EX-2"
        and r[1] == "杜甫"
        and r[3] == "."
        and r[4] == "下一阶段：补齐边界用例"
        and r[5] == "review"
        and r[8] == ""
        and r[9] == "./log/ex2.md"
        for r in list_rows
    )
    assert get_agent_status(agents, "worker-b") == "free"
    calls_text = calls_file.read_text(encoding="utf-8")
    assert (
        "send:神秘人-session:@worker-b向@神秘人发起会话: "
        "任务 EX-2 已完成当前阶段，已回到任务列表；新任务类型=review，请管理员推进。:"
    ) in calls_text


# TC-031
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-08 13:40:00 +0800
# 最近一次运行成功时间: 2026-04-08 13:40:00 +0800
# 测试目的: 验证 -next 缺少 -message 返回 RC=1。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_next_requires_message(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file_current(todo)
    write_agents_file(agents)

    result = run_script(
        "-file",
        str(todo),
        "-next",
        "-task_id",
        "EX-2",
        "-from",
        "worker-b",
        "-type",
        "review",
        "-agents-list",
        str(agents),
    )

    assert result.returncode == 1
    assert "-next requires -message" in result.stderr


# TC-031A
# 创建者: OpenAI
# 最后一次更改: OpenAI
# 测试目的: 验证 -next 必须显式提供 -type。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_next_requires_type(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file_with_task_type(todo)
    write_agents_file(agents, [agent_row("worker-a", "busy"), agent_row("worker-b", "free")])

    result = run_script(
        "-file",
        str(todo),
        "-next",
        "-task_id",
        "EX-2",
        "-from",
        "worker-b",
        "-message",
        "下一阶段：补齐边界用例",
        "-agents-list",
        str(agents),
    )

    assert result.returncode == 1
    assert "-next requires -type" in result.stderr


# TC-032
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-08 13:40:00 +0800
# 最近一次运行成功时间: 2026-04-08 13:40:00 +0800
# 测试目的: 验证 非架构师/管理员 调用 -new 被拒绝。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_new_restricted_for_non_privileged_operator(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(todo)
    write_agents_file(agents, rows=[agent_row("worker-a", "free")])

    env = os.environ.copy()
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "worker-a"
    env["CODEX_MULTI_AGENTS_PERMISSION_AGENTS_FILE"] = str(agents)
    result = run_script(
        "-file",
        str(todo),
        "-new",
        "-info",
        "补充单元测试",
        "-type",
        "build",
        "-worktree",
        "repo-auth",
        "-depends",
        "None",
        "-plan",
        "None",
        env=env,
    )

    assert result.returncode == 3
    assert "operation -new is restricted to 架构师或管理员: worker-a" in result.stderr


# TC-033
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-08 13:40:00 +0800
# 最近一次运行成功时间: 2026-04-08 13:40:00 +0800
# 测试目的: 验证 非管理员 调用 -done 被拒绝。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_done_restricted_for_non_privileged_operator(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(todo)
    write_agents_file(agents, rows=[agent_row("worker-a", "busy"), agent_row("worker-b", "busy")])

    env = os.environ.copy()
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "worker-a"
    env["CODEX_MULTI_AGENTS_PERMISSION_AGENTS_FILE"] = str(agents)
    result = run_script("-file", str(todo), "-done", "-task_id", "EX-1", "-log", "./log/record.md", "-agents-list", str(agents), env=env)

    running_rows = parse_section_rows(todo.read_text(encoding="utf-8"), "## 正在执行的任务")
    assert result.returncode == 3
    assert "operation -done is restricted to 管理员或合并: worker-a" in result.stderr
    assert any(r[0] == "EX-1" for r in running_rows)


# TC-034
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-08 14:25:00 +0800
# 最近一次运行成功时间: 2026-04-08 14:25:00 +0800
# 测试目的: 验证 -new 缺少 -worktree 返回 RC=1。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_new_requires_worktree(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file(todo)

    result = run_script("-file", str(todo), "-new", "-info", "补充单元测试", "-type", "build")

    assert result.returncode == 1
    assert "-new requires -worktree" in result.stderr

    result = run_script(
        "-file",
        str(todo),
        "-new",
        "-info",
        "补充单元测试",
        "-type",
        "build",
        "-worktree",
        "None",
        "-depends",
        "None",
        "-plan",
        "None",
    )

    assert result.returncode == 1
    assert "-new requires non-None value for -worktree" in result.stderr


# TC-035
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-08 14:25:00 +0800
# 最近一次运行成功时间: 2026-04-08 14:25:00 +0800
# 测试目的: 验证 -dispatch 在依赖任务未完成时返回 RC=3。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_dispatch_blocked_by_unresolved_dependency(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(
        todo,
        list_rows=[
            row_list("EX-3", "苏轼", "2026-03-08 16:30:00 +0800", "", "删除 tmp/demo.txt", "EX-1", "ARCHITECTURE/plan/p.md", "", "./log/ex3.md"),
        ],
    )
    write_agents_file(agents)

    result = run_script("-file", str(todo), "-dispatch", "-task_id", "EX-3", "-to", "worker-a", "-agents-list", str(agents))
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")
    list_rows = parse_section_rows(content, "## 任务列表")

    assert result.returncode == 3
    assert "task has unresolved dependency: EX-1" in result.stderr
    assert not any(r[0] == "EX-3" and r[8] == "worker-a" for r in running_rows)
    assert any(r[0] == "EX-3" for r in list_rows)

    write_todo_file(
        todo,
        list_rows=[
            row_list("EX-3", "苏轼", "2026-03-08 16:30:00 +0800", "", "删除 tmp/demo.txt", "DONE-0、EX-4", "ARCHITECTURE/plan/p.md", "", "./log/ex3.md"),
            row_list("EX-4", "辛弃疾", "2026-03-08 16:40:00 +0800", "", "补充验收", "", "", "", "./log/ex4.md"),
        ],
    )
    result = run_script("-file", str(todo), "-dispatch", "-task_id", "EX-3", "-to", "worker-a", "-agents-list", str(agents))
    assert result.returncode == 3
    assert "task has unresolved dependency: EX-4" in result.stderr


# TC-036
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-08 15:30:00 +0800
# 最近一次运行成功时间: 2026-04-08 15:30:00 +0800
# 测试目的: 验证 -dispatch 指派给 busy 角色时返回 RC=3。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_dispatch_rejects_busy_agent(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(todo)
    write_agents_file(agents, rows=[agent_row("worker-a", "free"), agent_row("worker-b", "busy")])

    result = run_script("-file", str(todo), "-dispatch", "-task_id", "EX-3", "-to", "worker-b", "-agents-list", str(agents))
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")
    list_rows = parse_section_rows(content, "## 任务列表")

    assert result.returncode == 3
    assert "agent is busy, cannot dispatch: worker-b" in result.stderr
    assert not any(r[0] == "EX-3" and r[8] == "worker-b" for r in running_rows)
    assert any(r[0] == "EX-3" for r in list_rows)


# TC-037
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-08 15:30:00 +0800
# 最近一次运行成功时间: 2026-04-08 15:30:00 +0800
# 测试目的: 验证 -next 缺少 -agents-list 返回 RC=1。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_next_requires_agents_list(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file_current(todo)

    result = run_script(
        "-file",
        str(todo),
        "-next",
        "-task_id",
        "EX-2",
        "-from",
        "worker-b",
        "-type",
        "review",
        "-message",
        "下一阶段：补齐边界用例",
    )

    assert result.returncode == 1
    assert "-next requires -agents-list" in result.stderr


# TC-037A
# 创建者: OpenAI
# 最后一次更改: OpenAI
# 测试目的: 验证 -next 缺少 -from 返回 RC=1。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_next_requires_from(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file_current(todo)
    write_agents_file(agents)

    result = run_script(
        "-file",
        str(todo),
        "-next",
        "-task_id",
        "EX-2",
        "-type",
        "review",
        "-message",
        "下一阶段：补齐边界用例",
        "-agents-list",
        str(agents),
    )

    assert result.returncode == 1
    assert "-next requires -from" in result.stderr


# TC-050
# 创建者: OpenAI
# 最后一次更改: OpenAI
# 测试目的: 验证 -next -auto 会把同一任务重新续接给当前执行者，并向管理员发送固定摘要。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_next_auto_reassigns_same_task_to_operator(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    calls_file = write_fake_tmux(bin_dir, state_dir, sessions=["神秘人-session"])
    write_todo_file_current(
        todo,
        running_rows=[
            row_running_typed(
                "EX-2",
                "杜甫",
                "2026-03-08 16:20:00 +0800",
                "/tmp/wt-ex2",
                "创建 test",
                "build",
                "",
                "ARCHITECTURE/plan/demo.md",
                "worker-b",
                "进行中",
                "xxx",
                "./log/ex2.md",
            ),
        ],
        list_rows=[],
    )
    write_agents_file(
        agents,
        rows=[
            agent_row_with_role("神秘人", "free", "管理员", "神秘人-session", "管理员"),
            agent_row_with_role("worker-b", "busy", "开发 审查"),
        ],
    )

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["CODEX_MULTI_AGENTS_ADMIN_USERS"] = "神秘人"
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "worker-b"

    result = run_script(
        "-file",
        str(todo),
        "-next",
        "-auto",
        "-task_id",
        "EX-2",
        "-from",
        "worker-b",
        "-type",
        "review",
        "-message",
        "下一阶段：补齐边界用例",
        "-agents-list",
        str(agents),
        env=env,
    )

    assert result.returncode == 0
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")
    list_rows = parse_section_rows(content, "## 任务列表")
    assert any(r[0] == "EX-2" and r[5] == "review" and r[8] == "worker-b" and r[9] == "进行中" for r in running_rows)
    assert not any(r[0] == "EX-2" for r in list_rows)
    assert get_agent_status(agents, "worker-b") == "busy"
    calls_text = calls_file.read_text(encoding="utf-8")
    assert "向@worker-b发起会话" not in calls_text
    assert (
        "send:神秘人-session:@worker-b向@神秘人发起会话: "
        "任务 EX-2 已完成当前阶段，已回到任务列表；新任务类型=review，已经指派给-> 当前执行者。:"
    ) in calls_text


# TC-051
# 创建者: OpenAI
# 最后一次更改: jcc你莫辜负
# 测试目的: 验证 -next -auto 会把同一任务续接给其他匹配角色，并输出默认任务消息模板与管理员摘要。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_next_auto_reassigns_same_task_to_other_agent(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    calls_file = write_fake_tmux(bin_dir, state_dir, sessions=["神秘人-session", "worker-c-session"])
    write_todo_file_current(
        todo,
        running_rows=[
            row_running_typed(
                "EX-2",
                "杜甫",
                "2026-03-08 16:20:00 +0800",
                "/tmp/wt-ex2",
                "创建 test",
                "build",
                "",
                "ARCHITECTURE/plan/demo.md",
                "worker-b",
                "进行中",
                "xxx",
                "./log/ex2.md",
            ),
        ],
        list_rows=[],
    )
    write_agents_file(
        agents,
        rows=[
            agent_row_with_role("神秘人", "free", "管理员", "神秘人-session", "管理员"),
            agent_row_with_role("worker-b", "busy", "开发"),
            agent_row_with_role("worker-c", "free", "审查"),
        ],
    )

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["CODEX_MULTI_AGENTS_ADMIN_USERS"] = "神秘人"
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "worker-b"

    result = run_script(
        "-file",
        str(todo),
        "-next",
        "-auto",
        "-task_id",
        "EX-2",
        "-from",
        "worker-b",
        "-type",
        "review",
        "-message",
        "下一阶段：补齐边界用例",
        "-agents-list",
        str(agents),
        env=env,
    )

    assert result.returncode == 0
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")
    list_rows = parse_section_rows(content, "## 任务列表")
    assert any(r[0] == "EX-2" and r[5] == "review" and r[8] == "worker-c" and r[9] == "进行中" for r in running_rows)
    assert not any(r[0] == "EX-2" for r in list_rows)
    assert get_agent_status(agents, "worker-b") == "free"
    assert get_agent_status(agents, "worker-c") == "busy"
    calls_text = calls_file.read_text(encoding="utf-8")
    assert "你的名字叫做worker-c" in calls_text
    expected_task_message = (
        "@worker-b向@worker-c发起会话: 请处理任务 EX-2（下一阶段：补齐边界用例）。"
        "worktree=/tmp/wt-ex2；计划书=ARCHITECTURE/plan/demo.md；记录文件=./log/ex2.md；"
        f"完成后按 {REPO_ROOT}/agents/standard/任务记录约定.md 记录并回报管理员；"
        "流程不清楚请询问管理员；实现/架构问题请询问架构师。"
    )
    assert expected_task_message in calls_text
    assert (
        "send:神秘人-session:@worker-b向@神秘人发起会话: "
        "任务 EX-2 已完成当前阶段，已回到任务列表；新任务类型=review，已经指派给-> worker-c。:"
    ) in calls_text


# TC-058
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 测试目的: 验证 spec 自动续接优先选择专职角色。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-task.py -k test_next_auto_spec_dedicated_first
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_next_auto_spec_dedicated_first(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    calls_file = write_fake_tmux(bin_dir, state_dir, sessions=["神秘人-session", "worker-c-session"])
    write_todo_file_current(
        todo,
        running_rows=[
            row_running_typed(
                "EX-2",
                "杜甫",
                "2026-03-08 16:20:00 +0800",
                "/tmp/wt-ex2",
                "创建 spec",
                "spec",
                "",
                "ARCHITECTURE/plan/demo.md",
                "worker-b",
                "进行中",
                "xxx",
                "./log/ex2.md",
            ),
        ],
        list_rows=[],
    )
    write_agents_file(
        agents,
        rows=[
            agent_row_with_role("神秘人", "free", "管理员", "神秘人-session", "管理员"),
            agent_row_with_role("worker-b", "busy", "审查"),
            agent_row_with_role("worker-c", "free", "spec 文档编写"),
            agent_row_with_role("worker-s", "free", "全能替补"),
        ],
    )

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["CODEX_MULTI_AGENTS_ADMIN_USERS"] = "神秘人"
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "worker-b"

    result = run_script(
        "-file",
        str(todo),
        "-next",
        "-auto",
        "-task_id",
        "EX-2",
        "-from",
        "worker-b",
        "-type",
        "spec",
        "-message",
        "下一阶段：补齐边界用例",
        "-agents-list",
        str(agents),
        env=env,
    )

    assert result.returncode == 0
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")
    assert any(r[0] == "EX-2" and r[5] == "spec" and r[8] == "worker-c" for r in running_rows)
    assert get_agent_status(agents, "worker-c") == "busy"
    assert get_agent_status(agents, "worker-s") == "free"
    calls_text = calls_file.read_text(encoding="utf-8")
    assert "你的名字叫做worker-c" in calls_text


# TC-059
# 创建者: jcc你莫辜负
# 最后一次更改: 朽木露琪亚
# 测试目的: 验证 build 自动续接优先分配给专职角色。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-task.py -k test_next_auto_build_dedicated_first
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_next_auto_build_dedicated_first(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    calls_file = write_fake_tmux(bin_dir, state_dir, sessions=["神秘人-session", "worker-c-session"])
    write_todo_file_current(
        todo,
        running_rows=[
            row_running_typed(
                "EX-2",
                "杜甫",
                "2026-03-08 16:20:00 +0800",
                "/tmp/wt-ex2",
                "创建 test",
                "build",
                "",
                "ARCHITECTURE/plan/demo.md",
                "worker-b",
                "进行中",
                "xxx",
                "./log/ex2.md",
            ),
        ],
        list_rows=[],
    )
    write_agents_file(
        agents,
        rows=[
            agent_row_with_role("神秘人", "free", "管理员", "神秘人-session", "管理员"),
            agent_row_with_role("worker-b", "busy", "审查"),
            agent_row_with_role("worker-c", "free", "实现 测试"),
            agent_row_with_role("worker-s", "free", "全能替补"),
        ],
    )

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["CODEX_MULTI_AGENTS_ADMIN_USERS"] = "神秘人"
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "worker-b"

    result = run_script(
        "-file",
        str(todo),
        "-next",
        "-auto",
        "-task_id",
        "EX-2",
        "-from",
        "worker-b",
        "-type",
        "build",
        "-message",
        "下一阶段：补齐边界用例",
        "-agents-list",
        str(agents),
        env=env,
    )

    assert result.returncode == 0
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")
    assert any(r[0] == "EX-2" and r[5] == "build" and r[8] == "worker-c" for r in running_rows)
    assert get_agent_status(agents, "worker-c") == "busy"
    assert get_agent_status(agents, "worker-s") == "free"
    calls_text = calls_file.read_text(encoding="utf-8")
    assert "你的名字叫做worker-c" in calls_text


# TC-060
# 创建者: jcc你莫辜负
# 最后一次更改: 朽木露琪亚
# 测试目的: 验证 build 专职不可用时自动续接回退到候补角色。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-task.py -k test_next_auto_build_falls_back_to_substitute
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_next_auto_build_falls_back_to_substitute(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    calls_file = write_fake_tmux(bin_dir, state_dir, sessions=["神秘人-session", "worker-s-session"])
    write_todo_file_current(
        todo,
        running_rows=[
            row_running_typed(
                "EX-2",
                "杜甫",
                "2026-03-08 16:20:00 +0800",
                "/tmp/wt-ex2",
                "创建 test",
                "build",
                "",
                "ARCHITECTURE/plan/demo.md",
                "worker-b",
                "进行中",
                "xxx",
                "./log/ex2.md",
            ),
        ],
        list_rows=[],
    )
    write_agents_file(
        agents,
        rows=[
            agent_row_with_role("神秘人", "free", "管理员", "神秘人-session", "管理员"),
            agent_row_with_role("worker-b", "busy", "审查"),
            agent_row_with_role("worker-c", "busy", "实现 测试"),
            agent_row_with_role("worker-s", "free", "全能替补"),
        ],
    )

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["CODEX_MULTI_AGENTS_ADMIN_USERS"] = "神秘人"
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "worker-b"

    result = run_script(
        "-file",
        str(todo),
        "-next",
        "-auto",
        "-task_id",
        "EX-2",
        "-from",
        "worker-b",
        "-type",
        "build",
        "-message",
        "下一阶段：补齐边界用例",
        "-agents-list",
        str(agents),
        env=env,
    )

    assert result.returncode == 0
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")
    assert any(r[0] == "EX-2" and r[5] == "build" and r[8] == "worker-s" for r in running_rows)
    assert get_agent_status(agents, "worker-s") == "busy"
    calls_text = calls_file.read_text(encoding="utf-8")
    assert "你的名字叫做worker-s" in calls_text


# TC-061
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 测试目的: 验证 review 自动续接优先选择专职角色。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-task.py -k test_next_auto_review_dedicated_first
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_next_auto_review_dedicated_first(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    calls_file = write_fake_tmux(bin_dir, state_dir, sessions=["神秘人-session", "worker-c-session"])
    write_todo_file_current(
        todo,
        running_rows=[
            row_running_typed(
                "EX-2",
                "杜甫",
                "2026-03-08 16:20:00 +0800",
                "/tmp/wt-ex2",
                "创建 test",
                "review",
                "",
                "ARCHITECTURE/plan/demo.md",
                "worker-b",
                "进行中",
                "xxx",
                "./log/ex2.md",
            ),
        ],
        list_rows=[],
    )
    write_agents_file(
        agents,
        rows=[
            agent_row_with_role("神秘人", "free", "管理员", "神秘人-session", "管理员"),
            agent_row_with_role("worker-b", "busy", "开发"),
            agent_row_with_role("worker-c", "free", "审查"),
            agent_row_with_role("worker-s", "free", "全能替补"),
        ],
    )

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["CODEX_MULTI_AGENTS_ADMIN_USERS"] = "神秘人"
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "worker-b"

    result = run_script(
        "-file",
        str(todo),
        "-next",
        "-auto",
        "-task_id",
        "EX-2",
        "-from",
        "worker-b",
        "-type",
        "review",
        "-message",
        "下一阶段：补齐边界用例",
        "-agents-list",
        str(agents),
        env=env,
    )

    assert result.returncode == 0
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")
    assert any(r[0] == "EX-2" and r[5] == "review" and r[8] == "worker-c" for r in running_rows)
    assert get_agent_status(agents, "worker-c") == "busy"
    assert get_agent_status(agents, "worker-s") == "free"
    calls_text = calls_file.read_text(encoding="utf-8")
    assert "你的名字叫做worker-c" in calls_text


# TC-062
# 创建者: jcc你莫辜负
# 最后一次更改: 朽木露琪亚
# 测试目的: 验证 merge 只允许专职角色，候补不可接续。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-task.py -k test_next_auto_merge_rejects_fallback
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_next_auto_merge_rejects_fallback(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    calls_file = write_fake_tmux(bin_dir, state_dir, sessions=["神秘人-session"])
    write_todo_file_current(
        todo,
        running_rows=[
            row_running_typed(
                "EX-2",
                "杜甫",
                "2026-03-08 16:20:00 +0800",
                "/tmp/wt-ex2",
                "创建 test",
                "merge",
                "",
                "ARCHITECTURE/plan/demo.md",
                "worker-b",
                "进行中",
                "xxx",
                "./log/ex2.md",
            ),
        ],
        list_rows=[],
    )
    write_agents_file(
        agents,
        rows=[
            agent_row_with_role("神秘人", "free", "管理员", "神秘人-session", "管理员"),
            agent_row_with_role("worker-b", "busy", "实现 测试"),
            agent_row_with_role("worker-s", "free", "全能替补"),
        ],
    )

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["CODEX_MULTI_AGENTS_ADMIN_USERS"] = "神秘人"
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "worker-b"

    result = run_script(
        "-file",
        str(todo),
        "-next",
        "-auto",
        "-task_id",
        "EX-2",
        "-from",
        "worker-b",
        "-type",
        "merge",
        "-message",
        "下一阶段：补齐边界用例",
        "-agents-list",
        str(agents),
        env=env,
    )

    assert result.returncode == 0
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")
    list_rows = parse_section_rows(content, "## 任务列表")
    assert not any(r[0] == "EX-2" for r in running_rows)
    assert any(r[0] == "EX-2" and r[5] == "merge" and r[8] == "" for r in list_rows)
    calls_text = calls_file.read_text(encoding="utf-8")
    assert (
        "send:神秘人-session:@worker-b向@神秘人发起会话: "
        "任务 EX-2 已完成当前阶段，已回到任务列表；新任务类型=merge，请管理员推进。:"
    ) in calls_text


# TC-056
# 创建者: OpenAI
# 最后一次更改: 睡觉小分队
# 测试目的: 验证 -next -auto 在设置随机种子时可复现自动续接结果。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-task.py -k "next_auto_random_assignment_with_seed"
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_next_auto_random_assignment_with_seed(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    calls_file = write_fake_tmux(
        bin_dir, state_dir, sessions=["神秘人-session", "worker-d-session"]
    )
    write_todo_file_current(
        todo,
        running_rows=[
            row_running_typed(
                "EX-2",
                "杜甫",
                "2026-03-08 16:20:00 +0800",
                "/tmp/wt-ex2",
                "创建 test",
                "review",
                "",
                "ARCHITECTURE/plan/demo.md",
                "worker-b",
                "进行中",
                "xxx",
                "./log/ex2.md",
            ),
        ],
        list_rows=[],
    )
    write_agents_file(
        agents,
        rows=[
            agent_row_with_role("神秘人", "free", "管理员", "神秘人-session", "管理员"),
            agent_row_with_role("worker-b", "busy", "开发"),
            agent_row_with_role("worker-c", "free", "审查"),
            agent_row_with_role("worker-d", "free", "审查"),
            agent_row_with_role("worker-e", "free", "审查"),
            agent_row_with_role("worker-s", "free", "全能替补"),
        ],
    )

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["CODEX_MULTI_AGENTS_ADMIN_USERS"] = "神秘人"
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "worker-b"
    env["CODEX_MULTI_AGENTS_AUTO_RANDOM_SEED"] = "seed-a"

    result = run_script(
        "-file",
        str(todo),
        "-next",
        "-auto",
        "-task_id",
        "EX-2",
        "-from",
        "worker-b",
        "-type",
        "review",
        "-message",
        "下一阶段：补齐边界用例",
        "-agents-list",
        str(agents),
        env=env,
    )

    assert result.returncode == 0
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")
    assert any(r[0] == "EX-2" and r[8] == "worker-d" and r[9] == "进行中" for r in running_rows)
    assert get_agent_status(agents, "worker-b") == "free"
    assert get_agent_status(agents, "worker-d") == "busy"
    assert get_agent_status(agents, "worker-s") == "free"
    calls_text = calls_file.read_text(encoding="utf-8")
    assert "你的名字叫做worker-d" in calls_text


# TC-057
# 创建者: OpenAI
# 最后一次更改: 睡觉小分队
# 测试目的: 验证更换随机种子会触发不同的自动续接结果。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-task.py -k "next_auto_random_assignment_seed_changes"
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_next_auto_random_assignment_seed_changes(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    calls_file = write_fake_tmux(
        bin_dir, state_dir, sessions=["神秘人-session", "worker-e-session"]
    )
    write_todo_file_current(
        todo,
        running_rows=[
            row_running_typed(
                "EX-2",
                "杜甫",
                "2026-03-08 16:20:00 +0800",
                "/tmp/wt-ex2",
                "创建 test",
                "review",
                "",
                "ARCHITECTURE/plan/demo.md",
                "worker-b",
                "进行中",
                "xxx",
                "./log/ex2.md",
            ),
        ],
        list_rows=[],
    )
    write_agents_file(
        agents,
        rows=[
            agent_row_with_role("神秘人", "free", "管理员", "神秘人-session", "管理员"),
            agent_row_with_role("worker-b", "busy", "开发"),
            agent_row_with_role("worker-c", "free", "审查"),
            agent_row_with_role("worker-d", "free", "审查"),
            agent_row_with_role("worker-e", "free", "审查"),
        ],
    )

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["CODEX_MULTI_AGENTS_ADMIN_USERS"] = "神秘人"
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "worker-b"
    env["CODEX_MULTI_AGENTS_AUTO_RANDOM_SEED"] = "seed-b"

    result = run_script(
        "-file",
        str(todo),
        "-next",
        "-auto",
        "-task_id",
        "EX-2",
        "-from",
        "worker-b",
        "-type",
        "review",
        "-message",
        "下一阶段：补齐边界用例",
        "-agents-list",
        str(agents),
        env=env,
    )

    assert result.returncode == 0
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")
    assert any(r[0] == "EX-2" and r[8] == "worker-e" and r[9] == "进行中" for r in running_rows)
    assert get_agent_status(agents, "worker-b") == "free"
    assert get_agent_status(agents, "worker-e") == "busy"
    calls_text = calls_file.read_text(encoding="utf-8")
    assert "你的名字叫做worker-e" in calls_text


# TC-052
# 创建者: OpenAI
# 最后一次更改: OpenAI
# 测试目的: 验证 -next -auto 无法续接时，会保留在任务列表并通知管理员推进。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_next_auto_failure_notifies_admin(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    calls_file = write_fake_tmux(bin_dir, state_dir, sessions=["神秘人-session"])
    write_todo_file_current(
        todo,
        running_rows=[
            row_running_typed(
                "EX-2",
                "杜甫",
                "2026-03-08 16:20:00 +0800",
                ".",
                "创建 test",
                "build",
                "",
                "",
                "worker-b",
                "进行中",
                "xxx",
                "./log/ex2.md",
            ),
        ],
        list_rows=[],
    )
    write_agents_file(
        agents,
        rows=[
            agent_row_with_role("神秘人", "free", "管理员", "神秘人-session", "管理员"),
            agent_row_with_role("worker-b", "busy", "开发"),
        ],
    )

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["CODEX_MULTI_AGENTS_ADMIN_USERS"] = "神秘人"
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "worker-b"

    result = run_script(
        "-file",
        str(todo),
        "-next",
        "-auto",
        "-task_id",
        "EX-2",
        "-from",
        "worker-b",
        "-type",
        "review",
        "-message",
        "下一阶段：补齐边界用例",
        "-agents-list",
        str(agents),
        env=env,
    )

    assert result.returncode == 0
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")
    list_rows = parse_section_rows(content, "## 任务列表")
    assert not any(r[0] == "EX-2" for r in running_rows)
    assert any(r[0] == "EX-2" and r[5] == "review" and r[8] == "" for r in list_rows)
    calls_text = calls_file.read_text(encoding="utf-8")
    assert (
        "send:神秘人-session:@worker-b向@神秘人发起会话: "
        "任务 EX-2 已完成当前阶段，已回到任务列表；新任务类型=review，请管理员推进。:"
    ) in calls_text


# TC-053
# 创建者: OpenAI
# 最后一次更改: OpenAI
# 测试目的: 验证 -auto 只能与 -next 组合使用。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_auto_only_supports_next(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file_current(todo)
    write_agents_file(agents, rows=[agent_row_with_role("神秘人", "free", "管理员", "神秘人-session", "管理员")])

    result = run_script("-file", str(todo), "-dispatch", "-auto", "-task_id", "EX-3", "-to", "worker-a", "-agents-list", str(agents))

    assert result.returncode == 1
    assert "-auto only supports -next" in result.stderr


# TC-038
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-08 15:30:00 +0800
# 最近一次运行成功时间: 2026-04-08 15:30:00 +0800
# 测试目的: 验证 -new 缺少 -depends 或 -plan 返回 RC=1。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_new_requires_depends_and_plan(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file(todo)

    result = run_script("-file", str(todo), "-new", "-info", "补充单元测试", "-type", "build", "-worktree", "repo-required", "-plan", "None")
    assert result.returncode == 1
    assert "-new requires -depends" in result.stderr

    result = run_script("-file", str(todo), "-new", "-info", "补充单元测试", "-type", "build", "-worktree", "repo-required", "-depends", "None")
    assert result.returncode == 1
    assert "-new requires -plan" in result.stderr


# TC-039
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-08 22:20:00 +0800
# 最近一次运行成功时间: 2026-04-08 22:20:00 +0800
# 测试目的: 验证 -status -plan-list 输出计划书进度表。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_status_plan_list_outputs_plan_table(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file(todo)

    result = run_script(str(todo), "-file", "-status", "-plan-list")

    assert result.returncode == 0
    assert "计划书" in result.stdout
    assert "完成状态" in result.stdout


# TC-040
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-08 22:20:00 +0800
# 最近一次运行成功时间: 2026-04-08 22:20:00 +0800
# 测试目的: 验证 -new 的 -depends 任务不存在时返回 RC=3。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_new_requires_existing_dependencies(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(
        todo,
        list_rows=[row_list("EX-3", "苏轼", "2026-03-08 16:30:00 +0800", "wt-ex3", "删除 tmp/demo.txt", "", "", "", "./log/ex3.md")],
    )
    write_agents_file(agents, rows=[agent_row("神秘人", "free"), agent_row("worker-a", "free")])

    env = os.environ.copy()
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "神秘人"
    env["CODEX_MULTI_AGENTS_PERMISSION_AGENTS_FILE"] = str(agents)
    result = run_script(
        "-file",
        str(todo),
        "-new",
        "-info",
        "需要依赖的任务",
        "-type",
        "build",
        "-worktree",
        "repo-dep-check",
        "-depends",
        "EX-404",
        "-plan",
        "ARCHITECTURE/plan/a.md",
        env=env,
    )

    assert result.returncode == 3
    assert "dependency task not found: EX-404" in result.stderr
    list_rows = parse_section_rows(todo.read_text(encoding="utf-8"), "## 任务列表")
    assert not any(r[4] == "需要依赖的任务" for r in list_rows)

    result = run_script(
        "-file",
        str(todo),
        "-new",
        "-info",
        "重复 worktree 校验",
        "-type",
        "build",
        "-worktree",
        "wt-ex3",
        "-depends",
        "EX-3",
        "-plan",
        "ARCHITECTURE/plan/a.md",
        env=env,
    )

    assert result.returncode == 3
    assert "duplicate worktree found: wt-ex3 (task: EX-3)" in result.stderr


# TC-041
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-08 22:20:00 +0800
# 最近一次运行成功时间: 2026-04-08 22:20:00 +0800
# 测试目的: 验证 -new 会创建并更新计划书进度表。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_new_updates_plan_progress_table(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(todo)
    write_agents_file(agents, rows=[agent_row("神秘人", "free"), agent_row("worker-a", "free")])

    env = os.environ.copy()
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "神秘人"
    env["CODEX_MULTI_AGENTS_PERMISSION_AGENTS_FILE"] = str(agents)
    result = run_script(
        "-file",
        str(todo),
        "-new",
        "-info",
        "计划任务-1",
        "-type",
        "build",
        "-worktree",
        "repo-plan-1",
        "-depends",
        "EX-3",
        "-plan",
        "ARCHITECTURE/plan/plan-a.md",
        env=env,
    )

    assert result.returncode == 0
    plan_rows = parse_section_rows(todo.read_text(encoding="utf-8"), "## 计划书")
    assert any(r[0] == "ARCHITECTURE/plan/plan-a.md" and r[1] == "1" and r[2] == "0" and r[3] == "1" and r[4] == "进行中" for r in plan_rows)


# TC-042
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-08 22:20:00 +0800
# 最近一次运行成功时间: 2026-04-08 22:20:00 +0800
# 测试目的: 验证最后一个计划任务 -done 后计划状态变为完成待检查。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_done_last_plan_task_marks_plan_waiting_review(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(
        todo,
        running_rows=[
            row_running(
                "EX-1",
                "李白",
                "2026-03-08 16:10:00 +0800",
                ".",
                "创建 src",
                "",
                "ARCHITECTURE/plan/plan-a.md",
                "worker-a",
                "进行中",
                "xxx",
                "./log/ex1.md",
            ),
        ],
        list_rows=[],
    )
    write_agents_file(agents, rows=[agent_row("神秘人", "free"), agent_row("worker-a", "busy")])

    env = os.environ.copy()
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "神秘人"
    env["CODEX_MULTI_AGENTS_PERMISSION_AGENTS_FILE"] = str(agents)
    result = run_script("-file", str(todo), "-done", "-task_id", "EX-1", "-log", "./log/done.md", "-agents-list", str(agents), env=env)

    assert result.returncode == 0
    plan_rows = parse_section_rows(todo.read_text(encoding="utf-8"), "## 计划书")
    assert any(r[0] == "ARCHITECTURE/plan/plan-a.md" and r[1] == "1" and r[2] == "1" and r[3] == "0" and r[4] == "完成待检查" for r in plan_rows)


# TC-043
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-08 22:20:00 +0800
# 最近一次运行成功时间: 2026-04-08 22:20:00 +0800
# 测试目的: 验证 -done-plan 会移除已完成待检查的计划。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_done_plan_removes_review_ready_plan(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    todo.write_text(
        "\n".join(
            [
                "## 正在执行的任务",
                "",
                "| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 任务类型 | 依赖任务 | 计划书 | 指派 | 状态 | 用户指导 | 记录文件 |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                "",
                "## 计划书",
                "",
                "| 计划书 | 总任务数 | 已完成任务 | 待完成任务 | 完成状态 |",
                "| --- | --- | --- | --- | --- |",
                "| ARCHITECTURE/plan/plan-a.md | 1 | 1 | 0 | 完成待检查 |",
                "",
                "## 任务列表",
                "",
                "| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 任务类型 | 依赖任务 | 计划书 | 指派 | 记录文件 |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_agents_file(agents, rows=[agent_row("神秘人", "free")])

    env = os.environ.copy()
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "神秘人"
    env["CODEX_MULTI_AGENTS_PERMISSION_AGENTS_FILE"] = str(agents)
    result = run_script("-file", str(todo), "-done-plan", "-plan", "ARCHITECTURE/plan/plan-a.md", env=env)

    assert result.returncode == 0
    assert "OK: done-plan ARCHITECTURE/plan/plan-a.md" in result.stdout
    plan_rows = parse_section_rows(todo.read_text(encoding="utf-8"), "## 计划书")
    assert not any(r[0] == "ARCHITECTURE/plan/plan-a.md" for r in plan_rows)


# TC-044
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-08 22:20:00 +0800
# 最近一次运行成功时间: 2026-04-08 22:20:00 +0800
# 测试目的: 验证 -done-plan 仅接受完成待检查的计划。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_done_plan_requires_review_ready_status(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    todo.write_text(
        "\n".join(
            [
                "## 正在执行的任务",
                "",
                "| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 任务类型 | 依赖任务 | 计划书 | 指派 | 状态 | 用户指导 | 记录文件 |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                "",
                "## 计划书",
                "",
                "| 计划书 | 总任务数 | 已完成任务 | 待完成任务 | 完成状态 |",
                "| --- | --- | --- | --- | --- |",
                "| ARCHITECTURE/plan/plan-a.md | 2 | 1 | 1 | 进行中 |",
                "",
                "## 任务列表",
                "",
                "| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 任务类型 | 依赖任务 | 计划书 | 指派 | 记录文件 |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                "| EX-9 | 李白 | 2026-03-08 16:30:00 +0800 | . | 未完成任务 | build |  | ARCHITECTURE/plan/plan-a.md | worker-a | ./log/ex9.md |",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_agents_file(agents, rows=[agent_row("神秘人", "free")])

    env = os.environ.copy()
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "神秘人"
    env["CODEX_MULTI_AGENTS_PERMISSION_AGENTS_FILE"] = str(agents)
    result = run_script("-file", str(todo), "-done-plan", "-plan", "ARCHITECTURE/plan/plan-a.md", env=env)

    assert result.returncode == 3
    assert "plan is not ready for done-plan: ARCHITECTURE/plan/plan-a.md" in result.stderr


# TC-045
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-08 22:20:00 +0800
# 最近一次运行成功时间: 2026-04-08 22:20:00 +0800
# 测试目的: 验证 非管理员 调用 -done-plan 被拒绝。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_done_plan_restricted_for_non_privileged_operator(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    todo.write_text(
        "\n".join(
            [
                "## 正在执行的任务",
                "",
                "| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 任务类型 | 依赖任务 | 计划书 | 指派 | 状态 | 用户指导 | 记录文件 |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                "",
                "## 计划书",
                "",
                "| 计划书 | 总任务数 | 已完成任务 | 待完成任务 | 完成状态 |",
                "| --- | --- | --- | --- | --- |",
                "| ARCHITECTURE/plan/plan-a.md | 1 | 1 | 0 | 完成待检查 |",
                "",
                "## 任务列表",
                "",
                "| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 任务类型 | 依赖任务 | 计划书 | 指派 | 记录文件 |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_agents_file(agents, rows=[agent_row("worker-a", "free")])

    env = os.environ.copy()
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "worker-a"
    env["CODEX_MULTI_AGENTS_PERMISSION_AGENTS_FILE"] = str(agents)
    result = run_script("-file", str(todo), "-done-plan", "-plan", "ARCHITECTURE/plan/plan-a.md", env=env)

    assert result.returncode == 3
    assert "operation -done-plan is restricted to 管理员: worker-a" in result.stderr


# TC-048
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-08 23:15:00 +0800
# 最近一次运行成功时间: 2026-04-08 23:15:00 +0800
# 测试目的: 验证 -dispatch 在达到并行人数上限时返回 RC=3。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_dispatch_rejects_when_parallel_limit_reached(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(
        todo,
        running_rows=[
            row_running("EX-1", "李白", "2026-03-08 16:10:00 +0800", ".", "创建 src", "", "", "worker-a", "进行中", "xxx", "./log/ex1.md"),
        ],
        list_rows=[
            row_list("EX-3", "苏轼", "2026-03-08 16:30:00 +0800", "", "删除 tmp/demo.txt", "", "", "", "./log/ex3.md"),
        ],
    )
    write_agents_file(agents, rows=[agent_row("神秘人", "free"), agent_row("worker-a", "busy"), agent_row("worker-b", "free")])

    env = os.environ.copy()
    env["CODEX_MULTI_AGENTS_MAX_PARALLEL"] = "1"
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "神秘人"
    env["CODEX_MULTI_AGENTS_PERMISSION_AGENTS_FILE"] = str(agents)
    result = run_script("-file", str(todo), "-dispatch", "-task_id", "EX-3", "-to", "worker-b", "-agents-list", str(agents), env=env)

    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")
    list_rows = parse_section_rows(content, "## 任务列表")
    assert result.returncode == 3
    assert "parallel assignee limit reached: 1/1" in result.stderr
    assert not any(r[0] == "EX-3" and r[8] == "worker-b" for r in running_rows)
    assert any(r[0] == "EX-3" for r in list_rows)


# TC-049
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-08 23:15:00 +0800
# 最近一次运行成功时间: 2026-04-08 23:15:00 +0800
# 测试目的: 验证 非管理员 调用 -dispatch 被拒绝。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_dispatch_restricted_for_non_admin_operator(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(todo)
    write_agents_file(agents, rows=[agent_row("worker-a", "free"), agent_row("worker-b", "free")])

    env = os.environ.copy()
    env["CODEX_MULTI_AGENTS_ROOT_NAME"] = "worker-a"
    env["CODEX_MULTI_AGENTS_PERMISSION_AGENTS_FILE"] = str(agents)
    result = run_script("-file", str(todo), "-dispatch", "-task_id", "EX-3", "-to", "worker-b", "-agents-list", str(agents), env=env)

    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")
    list_rows = parse_section_rows(content, "## 任务列表")
    assert result.returncode == 3
    assert "operation -dispatch is restricted to 管理员: worker-a" in result.stderr
    assert not any(r[0] == "EX-3" and r[8] == "worker-b" for r in running_rows)
    assert any(r[0] == "EX-3" for r in list_rows)
