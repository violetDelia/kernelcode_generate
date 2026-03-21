"""codex-multi-agents-dashboard.sh tests.

创建者: 榕
最后一次更改: 榕

功能说明:
- 覆盖 dashboard 脚本的参数校验、输出区域、数据关联与对齐规则。

关联文件:
- 功能实现: /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-dashboard.sh
- Spec 文档: /home/lfr/kernelcode_generate/spec/codex-multi-agents/scripts/codex-multi-agents-dashboard.md
- 测试文件: /home/lfr/kernelcode_generate/test/codex-multi-agents/test_codex-multi-agents-dashboard.py

使用示例:
- pytest -q test/codex-multi-agents/test_codex-multi-agents-dashboard.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "skills/codex-multi-agents/scripts/codex-multi-agents-dashboard.sh"

AGENTS_HEADER = "| 姓名 | 状态 | 会话 | 启动类型 | agent session | 介绍 | 提示词 | 归档文件 | 职责 |"
AGENTS_SEP = "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    """调用待测 shell 脚本并返回执行结果。"""
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def make_agent_row(
    name: str,
    status: str = "free",
    session: str = "",
    startup_type: str = "codex",
    agent_session: str = "",
    intro: str = "",
    prompt: str = "./prompt.md",
    archive: str = "./log/",
    duty: str = "",
) -> str:
    return (
        f"| {name} | {status} | {session} | {startup_type} | {agent_session} | "
        f"{intro} | {prompt} | {archive} | {duty} |"
    )


def write_agents_file(path: Path, rows: list[str]) -> None:
    text = "\n".join(["# Agents", "", AGENTS_HEADER, AGENTS_SEP, *rows, ""])
    path.write_text(text, encoding="utf-8")


def write_todo_file(path: Path, running_rows: list[str], list_rows: list[str]) -> None:
    text = "\n".join(
        [
            "## 正在执行的任务",
            "",
            "| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 指派 | 状态 | 用户指导 | 记录文件 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            *running_rows,
            "",
            "## 需要用户确认的事项",
            "",
            "| 任务 ID | 创建时间 | worktree | 描述 | 用户确认状态 | 记录文件 |",
            "| --- | --- | --- | --- | --- | --- |",
            "",
            "## 任务列表",
            "",
            "| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 指派 | 记录文件 |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            *list_rows,
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")


def extract_table_lines(output: str, heading: str) -> list[str]:
    lines = output.splitlines()
    start = -1
    for idx, line in enumerate(lines):
        if line.strip() == heading:
            start = idx + 1
            break
    if start < 0:
        return []
    table_lines: list[str] = []
    for line in lines[start:]:
        if line.strip().startswith("== "):
            break
        if line.strip() == "":
            if table_lines:
                break
            continue
        table_lines.append(line)
    return table_lines


# TC-001
# 创建者: 榕
# 最后一次更改: 榕
# 最近一次运行测试时间: 2026-03-21 12:30:00 +0800
# 最近一次运行成功时间: 2026-03-21 12:30:00 +0800
# 功能说明: 验证 dashboard 单次输出包含摘要、角色状态、任务区和最近对话区。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-dashboard.py -k test_dashboard_once
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-dashboard.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-dashboard.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-dashboard.py
def test_dashboard_once(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents.md"
    todo_file = tmp_path / "TODO.md"
    log_file = tmp_path / "talk.log"

    write_agents_file(
        agents_file,
        [
            make_agent_row("小明", "free", "xiaoming", "codex", "agent-x", "擅长分发任务"),
            make_agent_row("李白", "doing", "libai", "codex", "agent-y", "合入 include/api"),
        ],
    )
    running_rows = [
        "| T-1 | 神秘人 | 2026-03-21 10:00:00 +0800 | ./wt-1 | 修复 A | 李白 | 进行中 |  | ./log/a.md |",
    ]
    list_rows = [
        "| T-2 | 神秘人 | 2026-03-21 10:10:00 +0800 | ./wt-2 | 修复 B | 小明 | ./log/b.md |",
    ]
    write_todo_file(todo_file, running_rows, list_rows)
    log_file.write_text("line-1\nline-2\n", encoding="utf-8")

    result = run_script(
        "-agents-file",
        str(agents_file),
        "-todo-file",
        str(todo_file),
        "-log-file",
        str(log_file),
        "-once",
    )
    assert result.returncode == 0
    assert "== 摘要 ==" in result.stdout
    assert "== 角色状态 ==" in result.stdout
    assert "== 正在执行的任务 ==" in result.stdout
    assert "== 任务列表 ==" in result.stdout
    assert "== 最近对话 ==" in result.stdout


# TC-002
# 创建者: 榕
# 最后一次更改: 榕
# 最近一次运行测试时间: 2026-03-21 12:30:00 +0800
# 最近一次运行成功时间: 2026-03-21 12:30:00 +0800
# 功能说明: 缺少 agents-file 时返回参数错误。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-dashboard.py -k test_dashboard_missing_agents
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-dashboard.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-dashboard.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-dashboard.py
def test_dashboard_missing_agents(tmp_path: Path) -> None:
    todo_file = tmp_path / "TODO.md"
    write_todo_file(todo_file, [], [])
    result = run_script("-todo-file", str(todo_file), "-once")
    assert result.returncode == 1
    assert "-agents-file" in result.stderr


# TC-003
# 创建者: 榕
# 最后一次更改: 榕
# 最近一次运行测试时间: 2026-03-21 12:30:00 +0800
# 最近一次运行成功时间: 2026-03-21 12:30:00 +0800
# 功能说明: 缺少 todo-file 时返回参数错误。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-dashboard.py -k test_dashboard_missing_todo
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-dashboard.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-dashboard.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-dashboard.py
def test_dashboard_missing_todo(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents.md"
    write_agents_file(agents_file, [make_agent_row("小明")])
    result = run_script("-agents-file", str(agents_file), "-once")
    assert result.returncode == 1
    assert "-todo-file" in result.stderr


# TC-004
# 创建者: 榕
# 最后一次更改: 榕
# 最近一次运行测试时间: 2026-03-21 12:30:00 +0800
# 最近一次运行成功时间: 2026-03-21 12:30:00 +0800
# 功能说明: -once 与 -refresh 同时提供应报错。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-dashboard.py -k test_dashboard_once_refresh_conflict
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-dashboard.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-dashboard.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-dashboard.py
def test_dashboard_once_refresh_conflict(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents.md"
    todo_file = tmp_path / "TODO.md"
    write_agents_file(agents_file, [make_agent_row("小明")])
    write_todo_file(todo_file, [], [])
    result = run_script(
        "-agents-file",
        str(agents_file),
        "-todo-file",
        str(todo_file),
        "-once",
        "-refresh",
        "3",
    )
    assert result.returncode == 1
    assert "-once" in result.stderr


# TC-005
# 创建者: 榕
# 最后一次更改: 榕
# 最近一次运行测试时间: 2026-03-21 12:30:00 +0800
# 最近一次运行成功时间: 2026-03-21 12:30:00 +0800
# 功能说明: -refresh 非正整数应报错。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-dashboard.py -k test_dashboard_invalid_refresh
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-dashboard.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-dashboard.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-dashboard.py
def test_dashboard_invalid_refresh(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents.md"
    todo_file = tmp_path / "TODO.md"
    write_agents_file(agents_file, [make_agent_row("小明")])
    write_todo_file(todo_file, [], [])
    result = run_script(
        "-agents-file",
        str(agents_file),
        "-todo-file",
        str(todo_file),
        "-refresh",
        "0",
    )
    assert result.returncode == 1
    assert "refresh" in result.stderr


# TC-006
# 创建者: 榕
# 最后一次更改: 榕
# 最近一次运行测试时间: 2026-03-21 12:30:00 +0800
# 最近一次运行成功时间: 2026-03-21 12:30:00 +0800
# 功能说明: agents 文件不存在应返回文件错误。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-dashboard.py -k test_dashboard_missing_agents_file
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-dashboard.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-dashboard.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-dashboard.py
def test_dashboard_missing_agents_file(tmp_path: Path) -> None:
    todo_file = tmp_path / "TODO.md"
    write_todo_file(todo_file, [], [])
    result = run_script(
        "-agents-file",
        str(tmp_path / "missing.md"),
        "-todo-file",
        str(todo_file),
        "-once",
    )
    assert result.returncode == 2
    assert "file not found" in result.stderr


# TC-007
# 创建者: 榕
# 最后一次更改: 榕
# 最近一次运行测试时间: 2026-03-21 12:30:00 +0800
# 最近一次运行成功时间: 2026-03-21 12:30:00 +0800
# 功能说明: todo 文件不存在应返回文件错误。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-dashboard.py -k test_dashboard_missing_todo_file
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-dashboard.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-dashboard.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-dashboard.py
def test_dashboard_missing_todo_file(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents.md"
    write_agents_file(agents_file, [make_agent_row("小明")])
    result = run_script(
        "-agents-file",
        str(agents_file),
        "-todo-file",
        str(tmp_path / "missing.md"),
        "-once",
    )
    assert result.returncode == 2
    assert "file not found" in result.stderr


# TC-008
# 创建者: 榕
# 最后一次更改: 榕
# 最近一次运行测试时间: 2026-03-21 12:30:00 +0800
# 最近一次运行成功时间: 2026-03-21 12:30:00 +0800
# 功能说明: -no-talk 隐藏最近对话区域。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-dashboard.py -k test_dashboard_no_talk
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-dashboard.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-dashboard.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-dashboard.py
def test_dashboard_no_talk(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents.md"
    todo_file = tmp_path / "TODO.md"
    log_file = tmp_path / "talk.log"
    write_agents_file(agents_file, [make_agent_row("小明")])
    write_todo_file(todo_file, [], [])
    log_file.write_text("line-1\n", encoding="utf-8")

    result = run_script(
        "-agents-file",
        str(agents_file),
        "-todo-file",
        str(todo_file),
        "-log-file",
        str(log_file),
        "-no-talk",
        "-once",
    )
    assert result.returncode == 0
    assert "最近对话" not in result.stdout


# TC-009
# 创建者: 榕
# 最后一次更改: 榕
# 最近一次运行测试时间: 2026-03-21 12:30:00 +0800
# 最近一次运行成功时间: 2026-03-21 12:30:00 +0800
# 功能说明: -no-summary 隐藏摘要区域。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-dashboard.py -k test_dashboard_no_summary
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-dashboard.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-dashboard.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-dashboard.py
def test_dashboard_no_summary(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents.md"
    todo_file = tmp_path / "TODO.md"
    write_agents_file(agents_file, [make_agent_row("小明")])
    write_todo_file(todo_file, [], [])
    result = run_script(
        "-agents-file",
        str(agents_file),
        "-todo-file",
        str(todo_file),
        "-no-summary",
        "-once",
    )
    assert result.returncode == 0
    assert "== 摘要 ==" not in result.stdout
    assert "== 角色状态 ==" in result.stdout


# TC-010
# 创建者: 榕
# 最后一次更改: 榕
# 最近一次运行测试时间: 2026-03-21 12:30:00 +0800
# 最近一次运行成功时间: 2026-03-21 12:30:00 +0800
# 功能说明: 日志文件缺失时最近对话区域显示为空状态。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-dashboard.py -k test_dashboard_missing_log_file
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-dashboard.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-dashboard.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-dashboard.py
def test_dashboard_missing_log_file(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents.md"
    todo_file = tmp_path / "TODO.md"
    write_agents_file(agents_file, [make_agent_row("小明")])
    write_todo_file(todo_file, [], [])
    result = run_script(
        "-agents-file",
        str(agents_file),
        "-todo-file",
        str(todo_file),
        "-log-file",
        str(tmp_path / "missing.log"),
        "-once",
    )
    assert result.returncode == 0
    assert "== 最近对话 ==" in result.stdout
    assert "（无记录）" in result.stdout


# TC-011
# 创建者: 榕
# 最后一次更改: 榕
# 最近一次运行测试时间: 2026-03-21 12:30:00 +0800
# 最近一次运行成功时间: 2026-03-21 12:30:00 +0800
# 功能说明: 角色与正在执行任务正确关联。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-dashboard.py -k test_dashboard_task_mapping
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-dashboard.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-dashboard.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-dashboard.py
def test_dashboard_task_mapping(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents.md"
    todo_file = tmp_path / "TODO.md"
    write_agents_file(
        agents_file,
        [
            make_agent_row("李白", "doing", "libai", "codex", "agent-libai", "合入 include/api"),
        ],
    )
    running_rows = [
        "| T-99 | 神秘人 | 2026-03-21 10:00:00 +0800 | ./wt-99 | 修复广播 | 李白 | 进行中 |  | ./log/99.md |",
    ]
    write_todo_file(todo_file, running_rows, [])

    result = run_script(
        "-agents-file",
        str(agents_file),
        "-todo-file",
        str(todo_file),
        "-once",
    )
    assert result.returncode == 0
    table_lines = extract_table_lines(result.stdout, "== 角色状态 ==")
    assert any("T-99" in line for line in table_lines)
    assert any("./wt-99" in line for line in table_lines)


# TC-012
# 创建者: 榕
# 最后一次更改: 榕
# 最近一次运行测试时间: 2026-03-21 12:30:00 +0800
# 最近一次运行成功时间: 2026-03-21 12:30:00 +0800
# 功能说明: 表格列宽对齐且超长字段可截断。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-dashboard.py -k test_dashboard_alignment_and_truncate
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-dashboard.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-dashboard.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-dashboard.py
def test_dashboard_alignment_and_truncate(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents.md"
    todo_file = tmp_path / "TODO.md"
    long_intro = "超长介绍" * 10
    write_agents_file(
        agents_file,
        [
            make_agent_row("小明", "free", "session", "codex", "agent-x", long_intro),
            make_agent_row("李白", "ready", "session2", "codex", "agent-y", "短介绍"),
        ],
    )
    write_todo_file(todo_file, [], [])

    result = run_script(
        "-agents-file",
        str(agents_file),
        "-todo-file",
        str(todo_file),
        "-once",
    )
    assert result.returncode == 0
    table_lines = extract_table_lines(result.stdout, "== 角色状态 ==")
    assert table_lines
    header = table_lines[0]
    data_line = table_lines[2]

    header_cells = header.strip().strip("|").split("|")
    data_cells = data_line.strip().strip("|").split("|")
    assert len(header_cells) == len(data_cells)

    widths = [len(cell) for cell in header_cells]
    for idx, cell in enumerate(data_cells):
        assert len(cell) == widths[idx]

    assert "..." in data_line
