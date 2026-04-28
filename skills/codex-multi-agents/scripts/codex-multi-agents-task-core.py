#!/usr/bin/env python3
"""codex-multi-agents-task-core.py.

创建者: OpenAI
最后一次更改: Codex

功能说明:
- 处理 `codex-multi-agents-task.sh` 的核心数据逻辑。
- 负责解析与写回 `TODO.md`、`DONE.md`、`agents-lists.md`。
- 负责任务状态流转、计划书统计、角色权限与自动续接候选判定。
- 仅按命令影响的角色增量维护 `busy/free`，并拒绝同一角色同时持有多条进行中任务。

API 列表:
- normalize_task_type(raw: str, code: int, context: str)
- type_duty_keywords(kind: str)
- agent_matches_type(kind: str, duty: str)
- is_assignment_allowed_for_task(kind: str, duty: str)
- ensure_assignee_matches_task_type(kind: str, assignee: str, agent_row: list[str], agents_table: dict, action: str)
- pick_next_auto_assignee(row: list[str], exec_rows: list[list[str]], agents_rows: list[list[str]], agents_table: dict, operator_name: str, rng: random.Random | None = None)
- pick_ready_task_auto_dispatch(list_rows: list[list[str]], exec_rows: list[list[str]], agents_rows: list[list[str]], agents_table: dict, operator_name: str, max_parallel: int, rng: random.Random | None = None)
- auto_dispatch_ready_tasks(list_rows: list[list[str]], exec_rows: list[list[str]], agents_rows: list[list[str]], agents_table: dict, operator_name: str, max_parallel: int, dispatch_all: bool)
- main()

使用示例:
- `python3 skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py status-plan-list ./TODO.md "" "" "" "" "" "" "" "" "" "" "" "" "" "" 8 0`

关联文件:
- spec: `spec/codex-multi-agents/scripts/codex-multi-agents-task.md`
- test: `test/codex-multi-agents/test_codex-multi-agents-task.py`
- impl: `skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py`
"""

from __future__ import annotations

import hashlib
import os
import random
import re
import sys
import time
from datetime import datetime

RC_OK = 0
RC_ARG = 1
RC_FILE = 2
RC_DATA = 3
RC_LOCK = 4
RC_INTERNAL = 5

RUN_TABLE_HEADER = ["任务 ID", "发起人", "创建时间", "worktree", "描述", "任务类型", "依赖任务", "计划书", "指派", "状态", "用户指导", "记录文件"]
LIST_TABLE_HEADER = ["任务 ID", "发起人", "创建时间", "worktree", "描述", "任务类型", "依赖任务", "计划书", "指派", "记录文件"]
PLAN_TABLE_HEADER = ["计划书", "总任务数", "已完成任务", "待完成任务", "完成状态"]
DONE_TABLE_HEADER = ["任务 ID", "描述", "指派", "完成状态", "完成时间", "日志文件", "备注"]
AGENTS_REQUIRED_COLUMNS = ["姓名", "状态"]
ALLOWED_TASK_TYPES: set[str] = {"execute", "spec", "build", "review", "merge", "other", "refactor"}
MERGE_USERS = {"李白"}
AUTO_ASSIGNABLE_TASK_TYPES: set[str] = {"execute", "spec", "build", "review", "merge", "refactor"}


class TaskError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def fail(code: int, message: str) -> None:
    print(f"ERROR({code}): {message}", file=sys.stderr)
    raise TaskError(code, message)


def is_pipe_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|")


def is_sep_row(line: str) -> bool:
    return bool(re.match(r"^\|[\s:\-\|]+\|$", line.strip()))


def split_row(line: str) -> list[str]:
    s = line.strip()
    if not is_pipe_row(s):
        fail(RC_FILE, "invalid table format: non-table row")
    return [c.strip() for c in s[1:-1].split("|")]


def render_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def render_sep(col_count: int) -> str:
    return "| " + " | ".join(["---"] * col_count) + " |"


def read_lines(path: str) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().splitlines()
    except FileNotFoundError:
        fail(RC_FILE, f"file not found: {path}")
    except PermissionError:
        fail(RC_FILE, f"file is not readable: {path}")
    except OSError as exc:
        fail(RC_FILE, f"failed to read file: {path} ({exc})")


def write_atomic(path: str, lines: list[str]) -> None:
    tmp_path = f"{path}.tmp.{os.getpid()}.{random.randint(1000, 9999)}"
    content = "\n".join(lines) + "\n"
    try:
        with open(tmp_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except OSError as exc:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        fail(RC_INTERNAL, f"failed to update file: {path} ({exc})")


def find_section_index(lines: list[str], title: str) -> int:
    for i, line in enumerate(lines):
        if line.strip() == title:
            return i
    fail(RC_FILE, f"invalid table format: section not found: {title}")


def next_h2_index(lines: list[str], start: int) -> int:
    for i in range(start, len(lines)):
        if lines[i].startswith("## "):
            return i
    return len(lines)


def parse_table_in_section(lines: list[str], section_title: str, expected_header: list[str]) -> dict:
    sec_idx = find_section_index(lines, section_title)
    sec_end = next_h2_index(lines, sec_idx + 1)

    header_idx = -1
    sep_idx = -1
    for i in range(sec_idx + 1, max(sec_end - 1, sec_idx + 1)):
        if is_pipe_row(lines[i]) and is_sep_row(lines[i + 1]):
            header_idx = i
            sep_idx = i + 1
            break

    if header_idx < 0 or sep_idx < 0:
        fail(RC_FILE, f"invalid table format: table not found in section: {section_title}")

    header = split_row(lines[header_idx])
    if header != expected_header:
        fail(
            RC_FILE,
            f"invalid table format: unexpected header in section {section_title}, expect {expected_header}",
        )

    rows: list[list[str]] = []
    data_end = sep_idx
    i = sep_idx + 1
    while i < sec_end and is_pipe_row(lines[i]):
        row = split_row(lines[i])
        if len(row) != len(expected_header):
            fail(RC_FILE, f"invalid table format: row column count mismatch in section {section_title}")
        rows.append(row)
        data_end = i
        i += 1

    return {
        "section_title": section_title,
        "header_idx": header_idx,
        "sep_idx": sep_idx,
        "data_end": data_end,
        "header": header,
        "rows": rows,
    }


def ensure_plan_table(lines: list[str]) -> tuple[list[str], dict]:
    if any((line.strip() == "## 计划书" for line in lines)):
        return lines, parse_table_in_section(lines, "## 计划书", PLAN_TABLE_HEADER)

    task_list_idx = -1
    for i, line in enumerate(lines):
        if line.strip() == "## 任务列表":
            task_list_idx = i
            break
    if task_list_idx < 0:
        fail(RC_FILE, "invalid table format: section not found: ## 任务列表")

    insert_block = [
        "## 计划书",
        "",
        render_row(PLAN_TABLE_HEADER),
        render_sep(len(PLAN_TABLE_HEADER)),
        "",
    ]
    new_lines = lines[:task_list_idx] + insert_block + lines[task_list_idx:]
    return new_lines, parse_table_in_section(new_lines, "## 计划书", PLAN_TABLE_HEADER)


def replace_table(lines: list[str], table: dict, new_rows: list[list[str]], keep_original_head: bool = True) -> list[str]:
    if keep_original_head:
        header_line = lines[table["header_idx"]]
        sep_line = lines[table["sep_idx"]]
    else:
        header_line = render_row(table["header"])
        sep_line = render_sep(len(table["header"]))

    block = [header_line, sep_line] + [render_row(r) for r in new_rows]
    return lines[: table["header_idx"]] + block + lines[table["data_end"] + 1 :]


def is_empty_row(cells: list[str]) -> bool:
    return all((c.strip() == "" for c in cells))


def validate_unique_task_ids(exec_rows: list[list[str]], list_rows: list[list[str]]) -> None:
    seen: set[str] = set()
    for row in exec_rows + list_rows:
        if is_empty_row(row):
            continue
        task_id = row[0].strip()
        if not task_id:
            fail(RC_FILE, "invalid table format: empty task id")
        if task_id in seen:
            fail(RC_DATA, f"duplicate task id found: {task_id}")
        seen.add(task_id)


def find_row_index(rows: list[list[str]], task_id: str) -> int:
    for idx, row in enumerate(rows):
        if row[0].strip() == task_id:
            return idx
    return -1


def find_plan_row_index(plan_rows: list[list[str]], plan_doc: str) -> int:
    target = plan_doc.strip()
    for idx, row in enumerate(plan_rows):
        if row[0].strip() == target:
            return idx
    return -1


def parse_plan_int(value: str, field_name: str, plan_doc: str) -> int:
    text = value.strip()
    if not text:
        return 0
    try:
        parsed = int(text)
    except ValueError:
        fail(RC_FILE, f"invalid plan table value: {plan_doc} {field_name}={value}")
    if parsed < 0:
        fail(RC_FILE, f"invalid plan table value: {plan_doc} {field_name}={value}")
    return parsed


def normalize_plan_row(plan_rows: list[list[str]], idx: int) -> None:
    row = plan_rows[idx]
    plan_doc = row[0].strip()
    if not plan_doc:
        fail(RC_FILE, "invalid plan table format: empty plan doc")
    total = parse_plan_int(row[1], "总任务数", plan_doc)
    done = parse_plan_int(row[2], "已完成任务", plan_doc)
    pending = parse_plan_int(row[3], "待完成任务", plan_doc)
    total = max(total, done + pending)
    if total == 0:
        plan_rows.pop(idx)
        return
    status = "完成待检查" if pending == 0 else "进行中"
    row[1] = str(total)
    row[2] = str(done)
    row[3] = str(pending)
    row[4] = status


def update_plan_on_new(plan_rows: list[list[str]], plan_doc: str) -> None:
    if not plan_doc.strip():
        return
    idx = find_plan_row_index(plan_rows, plan_doc)
    if idx < 0:
        plan_rows.append([plan_doc, "1", "0", "1", "进行中"])
        return
    row = plan_rows[idx]
    total = parse_plan_int(row[1], "总任务数", plan_doc) + 1
    done = parse_plan_int(row[2], "已完成任务", plan_doc)
    pending = parse_plan_int(row[3], "待完成任务", plan_doc) + 1
    row[1] = str(max(total, done + pending))
    row[2] = str(done)
    row[3] = str(pending)
    row[4] = "进行中"


def update_plan_on_done(plan_rows: list[list[str]], plan_doc: str) -> None:
    if not plan_doc.strip():
        return
    idx = find_plan_row_index(plan_rows, plan_doc)
    if idx < 0:
        plan_rows.append([plan_doc, "1", "1", "0", "完成待检查"])
        return
    row = plan_rows[idx]
    total = parse_plan_int(row[1], "总任务数", plan_doc)
    done = parse_plan_int(row[2], "已完成任务", plan_doc) + 1
    pending = parse_plan_int(row[3], "待完成任务", plan_doc)
    if pending > 0:
        pending -= 1
    total = max(total, done + pending)
    row[1] = str(total)
    row[2] = str(done)
    row[3] = str(pending)
    row[4] = "完成待检查" if pending == 0 else "进行中"


def update_plan_on_remove_not_done(plan_rows: list[list[str]], plan_doc: str) -> None:
    if not plan_doc.strip():
        return
    idx = find_plan_row_index(plan_rows, plan_doc)
    if idx < 0:
        return
    row = plan_rows[idx]
    done = parse_plan_int(row[2], "已完成任务", plan_doc)
    pending = parse_plan_int(row[3], "待完成任务", plan_doc)
    if pending > 0:
        pending -= 1
    total = done + pending
    if total == 0:
        plan_rows.pop(idx)
        return
    row[1] = str(total)
    row[2] = str(done)
    row[3] = str(pending)
    row[4] = "完成待检查" if pending == 0 else "进行中"


def parse_done_table(done_file: str) -> tuple[list[str], dict]:
    lines = read_lines(done_file)

    if len(lines) == 0 or all((x.strip() == "" for x in lines)):
        lines = [
            "## 已完成任务",
            "",
            render_row(DONE_TABLE_HEADER),
            render_sep(len(DONE_TABLE_HEADER)),
        ]

    for i in range(0, max(len(lines) - 1, 0)):
        if i + 1 >= len(lines):
            break
        if not (is_pipe_row(lines[i]) and is_sep_row(lines[i + 1])):
            continue
        header = split_row(lines[i])
        if header != DONE_TABLE_HEADER:
            continue

        rows: list[list[str]] = []
        data_end = i + 1
        j = i + 2
        while j < len(lines) and is_pipe_row(lines[j]):
            row = split_row(lines[j])
            if len(row) != len(DONE_TABLE_HEADER):
                fail(RC_FILE, "invalid done table format: row column count mismatch")
            rows.append(row)
            data_end = j
            j += 1
        return lines, {
            "header_idx": i,
            "sep_idx": i + 1,
            "data_end": data_end,
            "header": DONE_TABLE_HEADER,
            "rows": rows,
        }

    if lines and lines[-1].strip() != "":
        lines.append("")
    lines.extend([
        "## 已完成任务",
        "",
        render_row(DONE_TABLE_HEADER),
        render_sep(len(DONE_TABLE_HEADER)),
    ])

    header_idx = len(lines) - 2
    sep_idx = len(lines) - 1
    return lines, {
        "header_idx": header_idx,
        "sep_idx": sep_idx,
        "data_end": sep_idx,
        "header": DONE_TABLE_HEADER,
        "rows": [],
    }


def parse_agents_table(agents_file: str) -> tuple[list[str], dict]:
    lines = read_lines(agents_file)

    for i in range(0, max(len(lines) - 1, 0)):
        if i + 1 >= len(lines):
            break
        if not (is_pipe_row(lines[i]) and is_sep_row(lines[i + 1])):
            continue
        header = split_row(lines[i])
        if not all((col in header for col in AGENTS_REQUIRED_COLUMNS)):
            continue

        rows: list[list[str]] = []
        data_end = i + 1
        j = i + 2
        while j < len(lines) and is_pipe_row(lines[j]):
            row = split_row(lines[j])
            if len(row) != len(header):
                fail(RC_FILE, "invalid agents table format: row column count mismatch")
            rows.append(row)
            data_end = j
            j += 1

        return lines, {
            "header_idx": i,
            "sep_idx": i + 1,
            "data_end": data_end,
            "header": header,
            "rows": rows,
            "name_idx": header.index("姓名"),
            "status_idx": header.index("状态"),
        }

    fail(RC_FILE, f"invalid agents table format: required columns not found in {agents_file}")


def find_agent_row_index(rows: list[list[str]], name_idx: int, name: str) -> int:
    for idx, row in enumerate(rows):
        if row[name_idx].strip() == name:
            return idx
    return -1


def count_doing_tasks(exec_rows: list[list[str]], assignee: str) -> int:
    count = 0
    for row in exec_rows:
        if row[8].strip() == assignee and row[9].strip() == "进行中":
            count += 1
    return count


def collect_doing_task_counts(exec_rows: list[list[str]]) -> dict[str, int]:
    """汇总每个角色的进行中任务数量。

    创建者: OpenAI
    最后一次更改: Codex

    功能说明:
    - 只统计 `状态=进行中` 且 `指派` 非空的运行中任务。
    - 供角色状态重算与“一人同一时刻仅一个任务”约束复用。

    使用示例:
    - counts = collect_doing_task_counts(exec_rows)

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
    - test: test/codex-multi-agents/test_codex-multi-agents-task.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
    """
    counts: dict[str, int] = {}
    for row in exec_rows:
        assignee = row[8].strip()
        status = row[9].strip()
        if not assignee or status != "进行中":
            continue
        counts[assignee] = counts.get(assignee, 0) + 1
    return counts


def ensure_single_active_task_per_assignee(exec_rows: list[list[str]]) -> None:
    """校验运行表中每个角色同一时刻至多一条进行中任务。

    创建者: OpenAI
    最后一次更改: Codex

    功能说明:
    - 若同一角色在运行表中出现多条 `状态=进行中` 任务，则直接报错。
    - 避免脚本继续在脏状态基础上分发、改派或自动续接。

    使用示例:
    - ensure_single_active_task_per_assignee(exec_rows)

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
    - test: test/codex-multi-agents/test_codex-multi-agents-task.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
    """
    duplicated = sorted((name for name, count in collect_doing_task_counts(exec_rows).items() if count > 1))
    if duplicated:
        fail(RC_DATA, f"assignee has multiple running tasks: {', '.join(duplicated)}")


def expected_agent_status_from_exec_rows(exec_rows: list[list[str]], assignee: str) -> str:
    """根据运行表计算单个角色应有的 busy/free 状态。

    创建者: OpenAI
    最后一次更改: Codex

    功能说明:
    - 只统计 `状态=进行中` 的任务。
    - 返回单个角色在当前运行表下应呈现的 `busy/free`。

    使用示例:
    - status = expected_agent_status_from_exec_rows(exec_rows, "worker-a")

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
    - test: test/codex-multi-agents/test_codex-multi-agents-task.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
    """
    return "busy" if count_doing_tasks(exec_rows, assignee) > 0 else "free"


def ensure_agent_status_matches_exec_rows(
    exec_rows: list[list[str]],
    agents_rows: list[list[str]],
    agents_table: dict,
    assignee: str,
) -> int:
    """校验单个角色在 agents 表中的状态与运行表一致。

    创建者: OpenAI
    最后一次更改: Codex

    功能说明:
    - 只校验被当前命令直接读写的角色，不重算整张名单。
    - 若名单状态与运行表中该角色的实际占用不一致，则直接报错。

    使用示例:
    - ensure_agent_status_matches_exec_rows(exec_rows, agents_rows, agents_table, "worker-a")

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
    - test: test/codex-multi-agents/test_codex-multi-agents-task.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
    """
    ensure_single_active_task_per_assignee(exec_rows)
    assignee_idx = find_agent_row_index(agents_rows, agents_table["name_idx"], assignee)
    if assignee_idx < 0:
        fail(RC_DATA, f"agent not found in agents list: {assignee}")
    expected = expected_agent_status_from_exec_rows(exec_rows, assignee)
    actual = agents_rows[assignee_idx][agents_table["status_idx"]].strip().lower()
    if actual != expected:
        fail(RC_DATA, f"agent status mismatch: {assignee} expect {expected} but got {actual or 'empty'}")
    return assignee_idx


def update_agent_status_from_exec_rows(
    exec_rows: list[list[str]],
    agents_rows: list[list[str]],
    agents_table: dict,
    assignee: str,
) -> int:
    """仅更新单个角色的名单状态，避免整表重算。

    创建者: OpenAI
    最后一次更改: Codex

    功能说明:
    - 只更新命令直接影响到的角色。
    - `进行中` 任务存在时写为 `busy`，否则写为 `free`。

    使用示例:
    - update_agent_status_from_exec_rows(exec_rows, agents_rows, agents_table, "worker-a")

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
    - test: test/codex-multi-agents/test_codex-multi-agents-task.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
    """
    assignee_idx = find_agent_row_index(agents_rows, agents_table["name_idx"], assignee)
    if assignee_idx < 0:
        fail(RC_DATA, f"agent not found in agents list: {assignee}")
    agents_rows[assignee_idx][agents_table["status_idx"]] = expected_agent_status_from_exec_rows(exec_rows, assignee)
    return assignee_idx


def parse_dependencies(raw: str) -> list[str]:
    text = raw.strip()
    if not text or text.lower() == "none":
        return []
    items = [item.strip() for item in re.split(r"[,\s，、]+", text) if item.strip()]
    dedup: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        dedup.append(item)
    return dedup


def parse_csv_names(raw: str) -> set[str]:
    names: set[str] = set()
    for item in raw.split(","):
        value = item.strip()
        if value:
            names.add(value)
    return names


def normalize_task_type(raw: str, code: int, context: str) -> str:
    text = raw.strip().lower()
    if not text:
        fail(code, f"empty task type: {context}")
    if text not in ALLOWED_TASK_TYPES:
        fail(code, f"invalid task type: {context}={raw}")
    return text


def type_duty_keywords(kind: str) -> list[str]:
    """按任务类型返回专职关键词集合。

    创建者: OpenAI
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 为专职匹配提供关键词集合。
    - 仅描述专职关键词，不包含候补关键词。

    使用示例:
    - keywords = type_duty_keywords("execute")

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
    - test: test/codex-multi-agents/test_codex-multi-agents-task.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
    """
    if kind == "execute":
        return ["计划级 execute", "execute", "实现", "测试", "spec"]
    if kind == "spec":
        return ["spec 文档编写", "spec"]
    if kind == "build":
        return ["实现", "测试"]
    if kind == "review":
        return ["审查", "复审"]
    if kind == "merge":
        return ["合并"]
    if kind == "refactor":
        return ["实现", "开发", "测试", "重构"]
    if kind == "other":
        return []
    return []


def agent_matches_type(kind: str, duty: str) -> bool:
    """判断职责是否满足专职匹配条件。

    创建者: OpenAI
    最后一次更改: jcc你莫辜负

    功能说明:
    - 按任务类型与关键词判断专职匹配。
    - 不处理候补职责的兜底判定。

    使用示例:
    - ok = agent_matches_type("review", "审查")

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
    - test: test/codex-multi-agents/test_codex-multi-agents-task.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
    """
    if kind == "other":
        return True
    if kind == "merge":
        return is_merge_specialist_duty(duty)
    keywords = type_duty_keywords(kind)
    duty_text = duty.strip()
    return any((kw in duty_text for kw in keywords))


def is_substitute_duty(duty: str) -> bool:
    """判断是否为候补职责。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 识别职责中包含“全能替补”的候补角色。

    使用示例:
    - is_sub = is_substitute_duty("仅负责全能替补（不含合并）")

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
    - test: test/codex-multi-agents/test_codex-multi-agents-task.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
    """
    return "全能替补" in duty


def is_merge_specialist_duty(duty: str) -> bool:
    """判断是否为可承接 merge 任务的合并专职职责。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅接受职责包含“合并”且未显式声明“不含合并”的角色。
    - 排除候补职责，避免 `merge` 被候补角色接手。

    使用示例:
    - ok = is_merge_specialist_duty("合并")

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
    - test: test/codex-multi-agents/test_codex-multi-agents-task.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
    """
    duty_text = duty.strip()
    if not duty_text:
        return False
    if is_substitute_duty(duty_text):
        return False
    return ("合并" in duty_text) and ("不含合并" not in duty_text)


def get_agent_duty(
    agent_row: list[str],
    agents_table: dict,
) -> str:
    """读取角色表行中的职责文本。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 从 agents 表头中定位“职责”列。
    - 表头不存在时返回空字符串，供上层约束统一处理。

    使用示例:
    - duty = get_agent_duty(agent_row, agents_table)

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
    - test: test/codex-multi-agents/test_codex-multi-agents-task.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
    """
    header: list[str] = agents_table["header"]
    duty_idx = header.index("职责") if "职责" in header else -1
    return agent_row[duty_idx].strip() if duty_idx >= 0 else ""


def is_specialist_candidate(kind: str, duty: str) -> bool:
    """判断是否满足专职候选条件。

    创建者: jcc你莫辜负
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 使用任务类型关键词判断专职匹配。
    - 对 execute/spec/build/review 排除候补职责。

    使用示例:
    - ok = is_specialist_candidate("execute", "负责计划级 execute")

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
    - test: test/codex-multi-agents/test_codex-multi-agents-task.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
    """
    if not agent_matches_type(kind, duty):
        return False
    if kind in {"execute", "spec", "build", "review"} and is_substitute_duty(duty):
        return False
    return True


def is_assignment_allowed_for_task(kind: str, duty: str) -> bool:
    """判断职责是否允许接手该任务类型。

    创建者: OpenAI
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - `merge` 仅允许合并专职。
    - `execute/spec/build/review/refactor` 允许对应专职，必要时允许全能替补。
    - `other` 保持无职责限制。

    使用示例:
    - ok = is_assignment_allowed_for_task("execute", "负责计划级 execute")

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
    - test: test/codex-multi-agents/test_codex-multi-agents-task.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
    """
    if kind == "merge":
        return is_merge_specialist_duty(duty)
    if kind == "other":
        return True
    if is_specialist_candidate(kind, duty):
        return True
    return kind in {"execute", "spec", "build", "review", "refactor"} and is_substitute_duty(duty)


def assignment_role_label(kind: str) -> str:
    """返回任务类型对应的可分发角色标签。

    创建者: OpenAI
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 统一显式分发失败时的职责提示短语。

    使用示例:
    - label = assignment_role_label("review")

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
    - test: test/codex-multi-agents/test_codex-multi-agents-task.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
    """
    if kind == "execute":
        return "execute specialists or substitutes"
    if kind == "spec":
        return "spec specialists or substitutes"
    if kind == "build":
        return "build specialists or substitutes"
    if kind == "review":
        return "review specialists or substitutes"
    if kind == "merge":
        return "merge specialists"
    if kind == "refactor":
        return "refactor specialists or substitutes"
    return "eligible agents"


def ensure_assignee_matches_task_type(
    kind: str,
    assignee: str,
    agent_row: list[str],
    agents_table: dict,
    action: str,
) -> None:
    """校验显式分发目标角色是否满足任务类型职责约束。

    创建者: OpenAI
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - `merge` 仅允许合并专职。
    - `execute/spec/build/review/refactor` 允许对应专职，必要时允许全能替补。
    - 显式分发、改派与 `-next -to` 共用稳定错误短语。

    使用示例:
    - ensure_assignee_matches_task_type("execute", "worker-b", agent_row, agents_table, "dispatch")

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
    - test: test/codex-multi-agents/test_codex-multi-agents-task.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
    """
    duty = get_agent_duty(agent_row, agents_table)
    if is_assignment_allowed_for_task(kind, duty):
        return
    verb_map = {
        "dispatch": "dispatched",
        "reassign": "reassigned",
        "assign": "assigned",
    }
    verb = verb_map.get(action, "assigned")
    fail(
        RC_DATA,
        f"{kind} tasks can only be {verb} to {assignment_role_label(kind)}: {assignee}",
    )


def is_agent_eligible_for_auto(
    name: str,
    agents_rows: list[list[str]],
    agents_table: dict,
) -> int:
    """判断角色是否满足自动续接的基础条件。

    创建者: OpenAI
    最后一次更改: jcc你莫辜负

    功能说明:
    - 校验角色是否存在且状态为 free。
    - 排除职责包含“不承担管理员分发的任务”的角色。

    使用示例:
    - idx = is_agent_eligible_for_auto("worker-a", agents_rows, agents_table)

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
    - test: test/codex-multi-agents/test_codex-multi-agents-task.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
    """
    if not name.strip():
        return -1
    idx = find_agent_row_index(agents_rows, agents_table["name_idx"], name)
    if idx < 0:
        return -1
    row = agents_rows[idx]
    status = row[agents_table["status_idx"]].strip().lower()
    header: list[str] = agents_table["header"]
    duty_idx = header.index("职责") if "职责" in header else -1
    duty = row[duty_idx].strip() if duty_idx >= 0 else ""
    if status != "free":
        return -1
    if "不承担管理员分发的任务" in duty:
        return -1
    return idx


def resolve_auto_random_seed() -> int | None:
    """解析自动续接随机种子。

    创建者: 睡觉小分队
    最后一次更改: 睡觉小分队

    功能说明:
    - 读取 CODEX_MULTI_AGENTS_AUTO_RANDOM_SEED，并归一化为整数种子。
    - 为空或为 "None" 时返回 None。

    使用示例:
    - seed = resolve_auto_random_seed()

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
    - test: test/codex-multi-agents/test_codex-multi-agents-task.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
    """

    raw = os.getenv("CODEX_MULTI_AGENTS_AUTO_RANDOM_SEED", "").strip()
    if not raw or raw.lower() == "none":
        return None
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def build_auto_random() -> random.Random:
    """构造自动续接随机数生成器。

    创建者: 睡觉小分队
    最后一次更改: 睡觉小分队

    功能说明:
    - 若存在随机种子则构造可复现的 Random 实例。
    - 若无种子则使用默认随机源。

    使用示例:
    - rng = build_auto_random()

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
    - test: test/codex-multi-agents/test_codex-multi-agents-task.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
    """

    seed = resolve_auto_random_seed()
    if seed is None:
        return random.Random()
    return random.Random(seed)


def pick_next_auto_assignee(
    row: list[str],
    exec_rows: list[list[str]],
    agents_rows: list[list[str]],
    agents_table: dict,
    operator_name: str,
    rng: random.Random | None = None,
) -> tuple[str, int] | None:
    """在候选人集合中选择自动续接接手人。

    创建者: OpenAI
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 在专职候选集合中随机选择接手人。
    - 专职候选为空时，对 execute/spec/build/review/refactor 退到候补候选集合。
    - 候选集合顺序由 agents-lists.md 决定。

    使用示例:
    - assignee = pick_next_auto_assignee(row, exec_rows, agents_rows, agents_table, operator_name)

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
    - test: test/codex-multi-agents/test_codex-multi-agents-task.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
    """

    kind = normalize_task_type(row[5], RC_DATA, f"task list row {row[0].strip()}")
    operator = operator_name.strip()
    primary_candidates: list[tuple[str, int]] = []
    fallback_candidates: list[tuple[str, int]] = []
    header: list[str] = agents_table["header"]
    duty_idx = header.index("职责") if "职责" in header else -1
    for candidate_row in agents_rows:
        name = candidate_row[agents_table["name_idx"]].strip()
        if not name:
            continue
        if count_doing_tasks(exec_rows, name) > 0:
            continue
        candidate_idx = is_agent_eligible_for_auto(name, agents_rows, agents_table)
        if candidate_idx < 0:
            continue
        duty = candidate_row[duty_idx].strip() if duty_idx >= 0 else ""
        if is_specialist_candidate(kind, duty):
            primary_candidates.append((name, candidate_idx))
            continue
        if kind in {"execute", "spec", "build", "review", "refactor"} and is_substitute_duty(duty):
            fallback_candidates.append((name, candidate_idx))
    candidates: list[tuple[str, int]]
    if kind == "merge":
        candidates = primary_candidates
    else:
        candidates = primary_candidates or fallback_candidates
    if not candidates:
        return None
    if rng is None:
        rng = build_auto_random()
    return rng.choice(candidates)


def dependencies_resolved_for_row(
    row: list[str],
    exec_rows: list[list[str]],
    list_rows: list[list[str]],
) -> bool:
    """判断任务行的依赖是否已全部完成。

    创建者: OpenAI
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 依赖任务只要仍存在于运行表或任务列表中，即视为未完成。

    使用示例:
    - ready = dependencies_resolved_for_row(row, exec_rows, list_rows)

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
    - test: test/codex-multi-agents/test_codex-multi-agents-task.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
    """
    for dependency in parse_dependencies(row[6]):
        if find_row_index(exec_rows, dependency) >= 0 or find_row_index(list_rows, dependency) >= 0:
            return False
    return True


def pick_ready_task_auto_dispatch(
    list_rows: list[list[str]],
    exec_rows: list[list[str]],
    agents_rows: list[list[str]],
    agents_table: dict,
    operator_name: str,
    max_parallel: int,
    rng: random.Random | None = None,
) -> tuple[int, str, int] | None:
    """从任务列表中挑选首个可自动启动的任务。

    创建者: OpenAI
    最后一次更改: Codex

    功能说明:
    - 只扫描依赖已清空的任务。
    - 任务优先级按 `任务列表` 当前顺序决定。
    - 角色选择继续复用现有专职优先、候补回退与随机种子规则。
    - 仅对 execute/spec/build/review/merge/refactor 六类任务执行自动启动。

    使用示例:
    - picked = pick_ready_task_auto_dispatch(list_rows, exec_rows, agents_rows, agents_table, "worker-a", 8)

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
    - test: test/codex-multi-agents/test_codex-multi-agents-task.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
    """
    if count_active_assignees(exec_rows) >= max_parallel:
        return None
    if rng is None:
        rng = build_auto_random()
    for idx, row in enumerate(list_rows):
        kind = normalize_task_type(row[5], RC_DATA, f"task list row {row[0].strip()}")
        if kind not in AUTO_ASSIGNABLE_TASK_TYPES:
            continue
        if not dependencies_resolved_for_row(row, exec_rows, list_rows):
            continue
        picked = pick_next_auto_assignee(row, exec_rows, agents_rows, agents_table, operator_name, rng)
        if picked is None:
            continue
        assignee, agent_idx = picked
        return idx, assignee, agent_idx
    return None


def auto_dispatch_ready_tasks(
    list_rows: list[list[str]],
    exec_rows: list[list[str]],
    agents_rows: list[list[str]],
    agents_table: dict,
    operator_name: str,
    max_parallel: int,
    dispatch_all: bool,
) -> list[tuple[str, str]]:
    """按任务列表顺序自动拉起可执行任务。

    创建者: OpenAI
    最后一次更改: Codex

    功能说明:
    - 复用现有 ready 判定、候选人选择与任务类型约束。
    - `dispatch_all=False` 时只拉起首个可执行任务。
    - `dispatch_all=True` 时会持续拉起任务列表中所有当前可执行任务，直到没有 ready 任务或达到并行上限。
    - 每次拉起后立即更新 `exec_rows` 与 `agents_rows`，确保同一轮不会把同一个 free 角色分给多条任务。

    使用示例:
    - started = auto_dispatch_ready_tasks(list_rows, exec_rows, agents_rows, agents_table, "worker-a", 8, True)

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
    - test: test/codex-multi-agents/test_codex-multi-agents-task.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
    """
    started: list[tuple[str, str]] = []
    rng = build_auto_random()
    while count_active_assignees(exec_rows) < max_parallel:
        picked_ready_task = pick_ready_task_auto_dispatch(
            list_rows,
            exec_rows,
            agents_rows,
            agents_table,
            operator_name,
            max_parallel,
            rng,
        )
        if picked_ready_task is None:
            break
        candidate_idx, candidate_assignee, candidate_agent_idx = picked_ready_task
        candidate_row = list_rows.pop(candidate_idx)
        exec_rows.append(
            [
                candidate_row[0],
                candidate_row[1],
                candidate_row[2],
                candidate_row[3],
                candidate_row[4],
                candidate_row[5],
                candidate_row[6],
                candidate_row[7],
                candidate_assignee,
                "进行中",
                "",
                candidate_row[9],
            ]
        )
        agents_rows[candidate_agent_idx][agents_table["status_idx"]] = "busy"
        started.append((candidate_row[0], candidate_assignee))
        if not dispatch_all:
            break
    return started


def ensure_operator_permission(
    op: str,
    operator_name: str,
    permission_agents_file: str,
) -> None:
    """校验管理员/架构师权限并给出稳定错误短语。

    创建者: 小李飞刀
    最后修改人: 金铲铲大作战

    功能说明:
    - 对 `new/dispatch/done/done-plan` 做权限校验。
    - 优先读取权限名单中的职责/介绍字段判断管理员或架构师。
    - 当权限名单不包含操作者时，回退使用管理员/架构师姓名白名单。
    - `done` 允许合并角色执行（默认仅 `李白`）。

    使用示例:
    - ensure_operator_permission("dispatch", "神秘人", "./agents-lists.md")

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
    - test: test/codex-multi-agents/test_codex-multi-agents-task.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py
    """
    if op not in {"new", "dispatch", "done", "done-plan"}:
        return

    caller = operator_name.strip()
    if not caller:
        fail(
            RC_ARG,
            f"-{op} requires operator identity; set CODEX_MULTI_AGENTS_ROOT_NAME or ROOT_NAME in config",
        )

    if not permission_agents_file.strip():
        fail(
            RC_ARG,
            f"-{op} requires permission agents list; set CODEX_MULTI_AGENTS_PERMISSION_AGENTS_FILE or AGENTS_FILE",
        )

    admin_names = parse_csv_names(
        os.environ.get("CODEX_MULTI_AGENTS_ADMIN_USERS", "神秘人")
    )
    arch_names = parse_csv_names(
        os.environ.get("CODEX_MULTI_AGENTS_ARCH_USERS", "大闸蟹,守护最好的爱莉希雅")
    )

    _, permission_table = parse_agents_table(permission_agents_file)
    permission_rows = [r[:] for r in permission_table["rows"]]
    row_idx = find_agent_row_index(permission_rows, permission_table["name_idx"], caller)
    if row_idx < 0:
        is_admin = caller in admin_names
        is_arch = caller in arch_names
        is_merge = caller in MERGE_USERS
        if op == "new":
            if not (is_admin or is_arch):
                fail(RC_DATA, f"operation -{op} is restricted to 架构师或管理员: {caller}")
            return
        if op == "done":
            if is_merge:
                return
            if not is_admin:
                fail(RC_DATA, f"operation -{op} is restricted to 管理员或合并: {caller}")
            return
        if not is_admin:
            fail(RC_DATA, f"operation -{op} is restricted to 管理员: {caller}")
        return

    row = permission_rows[row_idx]
    intro = ""
    duty = ""
    if "介绍" in permission_table["header"]:
        intro = row[permission_table["header"].index("介绍")].strip()
    if "职责" in permission_table["header"]:
        duty = row[permission_table["header"].index("职责")].strip()

    role_text = f"{intro} {duty}".strip()
    is_admin = ("管理员" in role_text) or (caller in admin_names)
    is_arch = ("架构师" in role_text) or (caller in arch_names)
    is_merge = caller in MERGE_USERS
    if (not is_merge) and role_text and ("合并" in role_text) and ("不含合并" not in role_text):
        is_merge = True

    if op == "new":
        if not (is_admin or is_arch):
            fail(RC_DATA, f"operation -{op} is restricted to 架构师或管理员: {caller}")
        return

    if op == "done":
        if not (is_admin or is_merge):
            fail(RC_DATA, f"operation -{op} is restricted to 管理员或合并: {caller}")
        return

    if not is_admin:
        fail(RC_DATA, f"operation -{op} is restricted to 管理员: {caller}")


def parse_max_parallel(raw: str) -> int:
    text = raw.strip()
    if not text:
        fail(RC_ARG, "empty max parallel value")
    if not text.isdigit():
        fail(RC_ARG, f"invalid max parallel value: {text}")
    value = int(text)
    if value <= 0:
        fail(RC_ARG, "max parallel value must be greater than 0")
    return value


def count_active_assignees(exec_rows: list[list[str]]) -> int:
    return len(collect_doing_task_counts(exec_rows))


def generate_task_id(info: str, to: str, existing_ids: set[str]) -> str:
    date_part = datetime.now().strftime("%Y%m%d")
    for _ in range(256):
        seed = f"{date_part}|{info}|{to}|{time.time_ns()}|{random.random()}"
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8]
        task_id = f"T-{date_part}-{digest}"
        if task_id not in existing_ids:
            return task_id
    fail(RC_INTERNAL, "failed to generate unique task id")


def main() -> int:
    op = sys.argv[1]
    todo_file = sys.argv[2]
    task_id = sys.argv[3]
    to = sys.argv[4]
    info = sys.argv[5]
    log_file = sys.argv[6]
    from_user = sys.argv[7]
    worktree = sys.argv[8]
    message = sys.argv[9]
    type_kind = sys.argv[10]
    depends = sys.argv[11]
    plan_doc = sys.argv[12]
    done_file = sys.argv[13]
    agents_file = sys.argv[14]
    operator_name = sys.argv[15]
    permission_agents_file = sys.argv[16]
    max_parallel = parse_max_parallel(sys.argv[17])
    auto_flag = sys.argv[18].strip() == "1"

    ensure_operator_permission(op, operator_name, permission_agents_file)

    todo_lines = read_lines(todo_file)
    todo_lines, plan_table = ensure_plan_table(todo_lines)
    exec_table = parse_table_in_section(todo_lines, "## 正在执行的任务", RUN_TABLE_HEADER)
    list_table = parse_table_in_section(todo_lines, "## 任务列表", LIST_TABLE_HEADER)

    exec_rows = [r[:] for r in exec_table["rows"]]
    list_rows = [r[:] for r in list_table["rows"]]
    plan_rows = [r[:] for r in plan_table["rows"]]
    validate_unique_task_ids(exec_rows, list_rows)
    ensure_single_active_task_per_assignee(exec_rows)
    idx = 0
    while idx < len(plan_rows):
        before_len = len(plan_rows)
        normalize_plan_row(plan_rows, idx)
        if len(plan_rows) == before_len:
            idx += 1

    done_lines = None
    done_table = None
    agents_lines = None
    agents_table = None
    agents_rows = None
    message_lines: list[str] = []
    touched_agent_names: set[str] = set()

    if op in {"dispatch", "done", "pause", "continue", "reassign", "next"}:
        agents_lines, agents_table = parse_agents_table(agents_file)
        agents_rows = [r[:] for r in agents_table["rows"]]

    if op == "status-doing":
        print(render_row(exec_table["header"]))
        print(render_sep(len(exec_table["header"])))
        for row in exec_rows:
            print(render_row(row))
        return RC_OK

    if op == "status-task-list":
        print(render_row(list_table["header"]))
        print(render_sep(len(list_table["header"])))
        for row in list_rows:
            print(render_row(row))
        return RC_OK

    if op == "status-plan-list":
        print(render_row(plan_table["header"]))
        print(render_sep(len(plan_table["header"])))
        for row in plan_rows:
            print(render_row(row))
        return RC_OK

    if op == "dispatch":
        if find_row_index(exec_rows, task_id) >= 0:
            fail(RC_DATA, f"task already exists in running list: {task_id}")
        idx = find_row_index(list_rows, task_id)
        if idx < 0:
            fail(RC_DATA, f"task not found in task list: {task_id}")
        assert agents_table is not None
        assert agents_rows is not None
        row = list_rows[idx]
        table_assignee = row[8].strip()
        assignee = to.strip() or table_assignee
        if not assignee:
            fail(RC_ARG, "empty value for -to")
        agent_idx = find_agent_row_index(agents_rows, agents_table["name_idx"], assignee)
        if agent_idx < 0:
            fail(RC_DATA, f"agent not found in agents list: {assignee}")
        table_type = row[5].strip()
        if type_kind and table_type and table_type != type_kind:
            fail(RC_DATA, f"task type mismatch: table={table_type} arg={type_kind}")
        task_type = table_type or type_kind
        if not task_type:
            fail(RC_DATA, f"empty task type in task list: {task_id}")
        normalized_task_type = normalize_task_type(task_type, RC_DATA, f"dispatch task {task_id}")
        ensure_assignee_matches_task_type(
            normalized_task_type,
            assignee,
            agents_rows[agent_idx],
            agents_table,
            "dispatch",
        )
        if agents_rows[agent_idx][agents_table["status_idx"]].strip().lower() == "busy":
            fail(RC_DATA, f"agent is busy, cannot dispatch: {assignee}")
        if count_doing_tasks(exec_rows, assignee) > 0:
            fail(RC_DATA, f"assignee already has running task: {assignee}")
        active_assignees = count_active_assignees(exec_rows)
        if active_assignees >= max_parallel:
            fail(RC_DATA, f"parallel assignee limit reached: {active_assignees}/{max_parallel}")
        for dependency in parse_dependencies(row[6]):
            if find_row_index(exec_rows, dependency) >= 0 or find_row_index(list_rows, dependency) >= 0:
                fail(RC_DATA, f"task has unresolved dependency: {dependency}")

        row = list_rows.pop(idx)
        from_val = row[1]
        created_at = row[2]
        worktree_val = row[3]
        desc = row[4]
        depends_val = row[6]
        plan_doc_val = row[7]
        record_file = row[9]
        exec_rows.append(
            [
                row[0],
                from_val,
                created_at,
                worktree_val,
                desc,
                normalized_task_type,
                depends_val,
                plan_doc_val,
                assignee,
                "进行中",
                "",
                record_file,
            ]
        )
        update_agent_status_from_exec_rows(exec_rows, agents_rows, agents_table, assignee)
        touched_agent_names.add(assignee)
        message_lines.append(f"OK: dispatch {task_id} -> {assignee}")
        message_lines.append(f"OK: replace {assignee} 状态")

    elif op == "done":
        idx = find_row_index(exec_rows, task_id)
        if idx < 0:
            fail(RC_DATA, f"task not found in running list: {task_id}")

        caller = operator_name.strip()
        if caller:
            admin_names = parse_csv_names(
                os.environ.get("CODEX_MULTI_AGENTS_ADMIN_USERS", "神秘人")
            )
            is_admin = caller in admin_names
            is_merge = caller in MERGE_USERS
            if permission_agents_file.strip():
                _, permission_table = parse_agents_table(permission_agents_file)
                permission_rows = [r[:] for r in permission_table["rows"]]
                row_idx = find_agent_row_index(
                    permission_rows,
                    permission_table["name_idx"],
                    caller,
                )
                if row_idx >= 0:
                    row = permission_rows[row_idx]
                    intro = ""
                    duty = ""
                    if "介绍" in permission_table["header"]:
                        intro = row[permission_table["header"].index("介绍")].strip()
                    if "职责" in permission_table["header"]:
                        duty = row[permission_table["header"].index("职责")].strip()
                    role_text = f"{intro} {duty}".strip()
                    if "管理员" in role_text:
                        is_admin = True
                    if (not is_merge) and role_text and ("合并" in role_text) and ("不含合并" not in role_text):
                        is_merge = True
            if is_merge and not is_admin:
                task_type = exec_rows[idx][5].strip()
                if task_type != "merge":
                    fail(
                        RC_DATA,
                        f"merge operator can only complete merge tasks: {task_id}",
                    )
                assignee = exec_rows[idx][8].strip()
                if assignee != caller:
                    fail(
                        RC_DATA,
                        f"merge operator can only complete own tasks: {task_id}",
                    )

        row = exec_rows.pop(idx)
        update_plan_on_done(plan_rows, row[7].strip())
        assignee = row[8].strip()
        if assignee:
            assert agents_table is not None
            assert agents_rows is not None
            ensure_agent_status_matches_exec_rows(exec_rows + [row], agents_rows, agents_table, assignee)
        done_lines, done_table = parse_done_table(done_file)
        done_rows = [r[:] for r in done_table["rows"]]
        finished_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
        done_rows.append([row[0], row[4], assignee, "已完成", finished_at, log_file, ""])
        done_lines = replace_table(done_lines, done_table, done_rows, keep_original_head=False)
        if assignee:
            update_agent_status_from_exec_rows(exec_rows, agents_rows, agents_table, assignee)
            touched_agent_names.add(assignee)
        message_lines.append(f"OK: done {task_id}")
        if assignee:
            message_lines.append(f"OK: replace {assignee} 状态")

    elif op == "pause":
        idx = find_row_index(exec_rows, task_id)
        if idx < 0:
            fail(RC_DATA, f"task not found in running list: {task_id}")

        assignee = exec_rows[idx][8].strip()
        if assignee:
            assert agents_table is not None
            assert agents_rows is not None
            ensure_agent_status_matches_exec_rows(exec_rows, agents_rows, agents_table, assignee)
        exec_rows[idx][9] = "暂停"
        if assignee:
            update_agent_status_from_exec_rows(exec_rows, agents_rows, agents_table, assignee)
            touched_agent_names.add(assignee)
        message_lines.append(f"OK: pause {task_id}")
        if assignee:
            message_lines.append(f"OK: replace {assignee} 状态")

    elif op == "continue":
        idx = find_row_index(exec_rows, task_id)
        if idx < 0:
            fail(RC_DATA, f"task not found in running list: {task_id}")

        if exec_rows[idx][9].strip() != "暂停":
            fail(RC_DATA, f"task status is not paused: {task_id}")

        assignee = exec_rows[idx][8].strip()
        if assignee:
            assert agents_table is not None
            assert agents_rows is not None
            ensure_agent_status_matches_exec_rows(exec_rows, agents_rows, agents_table, assignee)
            if count_doing_tasks(exec_rows, assignee) > 0:
                fail(RC_DATA, f"assignee already has running task: {assignee}")

        exec_rows[idx][9] = "进行中"
        if assignee:
            update_agent_status_from_exec_rows(exec_rows, agents_rows, agents_table, assignee)
            touched_agent_names.add(assignee)
        message_lines.append(f"OK: continue {task_id}")
        if assignee:
            message_lines.append(f"OK: replace {assignee} 状态")

    elif op == "reassign":
        idx = find_row_index(exec_rows, task_id)
        if idx < 0:
            fail(RC_DATA, f"task not found in running list: {task_id}")

        assert agents_table is not None
        assert agents_rows is not None
        new_assignee = to.strip()
        if not new_assignee:
            fail(RC_ARG, "empty value for -to")
        new_idx = find_agent_row_index(agents_rows, agents_table["name_idx"], new_assignee)
        if new_idx < 0:
            fail(RC_DATA, f"agent not found in agents list: {new_assignee}")
        task_type = normalize_task_type(exec_rows[idx][5], RC_DATA, f"running task {task_id}")
        ensure_assignee_matches_task_type(
            task_type,
            new_assignee,
            agents_rows[new_idx],
            agents_table,
            "reassign",
        )
        if agents_rows[new_idx][agents_table["status_idx"]].strip().lower() == "busy":
            fail(RC_DATA, f"agent is busy, cannot reassign: {new_assignee}")
        if count_doing_tasks(exec_rows, new_assignee) > 0:
            fail(RC_DATA, f"assignee already has running task: {new_assignee}")

        old_assignee = exec_rows[idx][8].strip()
        old_idx = None
        if old_assignee:
            old_idx = ensure_agent_status_matches_exec_rows(exec_rows, agents_rows, agents_table, old_assignee)

        exec_rows[idx][8] = new_assignee
        if old_assignee:
            update_agent_status_from_exec_rows(exec_rows, agents_rows, agents_table, old_assignee)
            touched_agent_names.add(old_assignee)
        update_agent_status_from_exec_rows(exec_rows, agents_rows, agents_table, new_assignee)
        touched_agent_names.add(new_assignee)
        message_lines.append(f"OK: reassign {task_id} -> {new_assignee}")
        message_lines.append(f"__REASSIGN__={old_assignee}|{new_assignee}")

        updated: set[str] = set()

        def update_agent(name: str, row_idx: int | None) -> None:
            if not name or row_idx is None or name in updated:
                return
            message_lines.append(f"OK: replace {name} 状态")
            updated.add(name)

        update_agent(old_assignee, old_idx)
        update_agent(new_assignee, new_idx)

    elif op == "next":
        idx = find_row_index(exec_rows, task_id)
        if idx < 0:
            fail(RC_DATA, f"task not found in running list: {task_id}")
        if not message.strip():
            fail(RC_ARG, "empty value for -message")
        if to.strip() and auto_flag:
            fail(RC_ARG, "-next cannot combine -to and -auto")

        row = exec_rows.pop(idx)
        assignee = row[8].strip()
        next_list_row = [row[0], row[1], row[2], row[3], message.strip(), type_kind, row[6], row[7], "", row[11]]
        message_lines.append(f"OK: next {task_id}")

        assert agents_table is not None
        assert agents_rows is not None
        if assignee:
            ensure_agent_status_matches_exec_rows(exec_rows + [row], agents_rows, agents_table, assignee)
            update_agent_status_from_exec_rows(exec_rows, agents_rows, agents_table, assignee)
            touched_agent_names.add(assignee)

        manual_assignee = to.strip()
        if manual_assignee:
            next_kind = normalize_task_type(next_list_row[5], RC_DATA, f"next task {task_id}")
            candidate_agent_idx = find_agent_row_index(
                agents_rows,
                agents_table["name_idx"],
                manual_assignee,
            )
            if candidate_agent_idx < 0:
                fail(RC_DATA, f"agent not found in agents list: {manual_assignee}")
            ensure_assignee_matches_task_type(
                next_kind,
                manual_assignee,
                agents_rows[candidate_agent_idx],
                agents_table,
                "assign",
            )
            if assignee and assignee != manual_assignee:
                agent_idx = find_agent_row_index(agents_rows, agents_table["name_idx"], assignee)
                if agent_idx < 0:
                    fail(RC_DATA, f"agent not found in agents list: {assignee}")
                message_lines.append(f"OK: replace {assignee} 状态")

            if agents_rows[candidate_agent_idx][agents_table["status_idx"]].strip().lower() == "busy":
                fail(RC_DATA, f"agent is busy, cannot next to: {manual_assignee}")
            if count_doing_tasks(exec_rows, manual_assignee) > 0:
                fail(RC_DATA, f"assignee already has running task: {manual_assignee}")
            if count_active_assignees(exec_rows) >= max_parallel:
                fail(RC_DATA, f"parallel assignee limit reached: {count_active_assignees(exec_rows)}/{max_parallel}")

            exec_rows.append(
                [
                    next_list_row[0],
                    next_list_row[1],
                    next_list_row[2],
                    next_list_row[3],
                    next_list_row[4],
                    next_list_row[5],
                    next_list_row[6],
                    next_list_row[7],
                    manual_assignee,
                    "进行中",
                    "",
                    next_list_row[9],
                ]
            )
            update_agent_status_from_exec_rows(exec_rows, agents_rows, agents_table, manual_assignee)
            touched_agent_names.add(manual_assignee)
            message_lines.append(f"OK: next-dispatch {task_id} -> {manual_assignee}")
            message_lines.append(f"OK: replace {manual_assignee} 状态")
            message_lines.append(f"__AUTO_NEXT__=dispatch|{task_id}|{manual_assignee}")

        else:
            list_rows.append(next_list_row)

            if assignee:
                message_lines.append(f"OK: replace {assignee} 状态")

        if not manual_assignee:
            started_tasks = auto_dispatch_ready_tasks(
                list_rows,
                exec_rows,
                agents_rows,
                agents_table,
                operator_name,
                max_parallel,
                auto_flag,
            )
            if not started_tasks:
                message_lines.append("__AUTO_NEXT__=none")
            else:
                for started_task_id, started_assignee in started_tasks:
                    touched_agent_names.add(started_assignee)
                    message_lines.append(f"OK: auto-dispatch {started_task_id} -> {started_assignee}")
                    message_lines.append(f"OK: replace {started_assignee} 状态")
                    message_lines.append(f"__AUTO_NEXT__=dispatch|{started_task_id}|{started_assignee}")

    elif op == "new":
        existing_ids = {r[0].strip() for r in (exec_rows + list_rows) if not is_empty_row(r)}
        new_id = generate_task_id(info, to, existing_ids)
        created_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
        from_val = from_user or ""
        worktree_val = worktree.strip()
        if not worktree_val:
            fail(RC_ARG, "empty value for -worktree")
        if worktree_val.lower() == "none":
            fail(RC_ARG, "-new requires non-None value for -worktree")
        for row in (exec_rows + list_rows):
            if is_empty_row(row):
                continue
            if row[3].strip() == worktree_val:
                fail(RC_DATA, f"duplicate worktree found: {worktree_val} (task: {row[0].strip()})")
        depends_val = "" if depends.strip().lower() == "none" else depends
        plan_doc_val = "" if plan_doc.strip().lower() == "none" else plan_doc
        for dependency in parse_dependencies(depends_val):
            if find_row_index(exec_rows, dependency) < 0 and find_row_index(list_rows, dependency) < 0:
                fail(RC_DATA, f"dependency task not found: {dependency}")
        record_file = log_file or ""
        list_rows.append([new_id, from_val, created_at, worktree_val, info, type_kind, depends_val, plan_doc_val, to, record_file])
        update_plan_on_new(plan_rows, plan_doc_val)
        message_lines.append(f"OK: new {new_id}")

    elif op == "delete":
        exec_idx = find_row_index(exec_rows, task_id)
        if exec_idx >= 0:
            if exec_rows[exec_idx][9].strip() != "暂停":
                fail(RC_DATA, f"task already exists in running list: {task_id}")
            removed = exec_rows.pop(exec_idx)
            update_plan_on_remove_not_done(plan_rows, removed[7].strip())
            message_lines.append(f"OK: delete {task_id}")
        else:
            idx = find_row_index(list_rows, task_id)
            if idx < 0:
                fail(RC_DATA, f"task not found in task list: {task_id}")
            removed = list_rows.pop(idx)
            update_plan_on_remove_not_done(plan_rows, removed[7].strip())
            message_lines.append(f"OK: delete {task_id}")

    elif op == "done-plan":
        normalized_plan_doc = plan_doc.strip()
        idx = find_plan_row_index(plan_rows, normalized_plan_doc)
        if idx < 0:
            fail(RC_DATA, f"plan not found in plan table: {normalized_plan_doc}")

        row = plan_rows[idx]
        status = row[4].strip()
        pending = parse_plan_int(row[3], "待完成任务", normalized_plan_doc)
        if status != "完成待检查" or pending != 0:
            fail(RC_DATA, f"plan is not ready for done-plan: {normalized_plan_doc}")

        if any((r[7].strip() == normalized_plan_doc for r in exec_rows + list_rows)):
            fail(RC_DATA, f"plan still has pending tasks: {normalized_plan_doc}")

        plan_rows.pop(idx)
        message_lines.append(f"OK: done-plan {normalized_plan_doc}")

    else:
        fail(RC_INTERNAL, f"unsupported operation: {op}")

    if done_lines is not None:
        write_atomic(done_file, done_lines)

    if agents_lines is not None and agents_table is not None and agents_rows is not None:
        for name in sorted(touched_agent_names):
            ensure_agent_status_matches_exec_rows(exec_rows, agents_rows, agents_table, name)
        agents_lines = replace_table(agents_lines, agents_table, agents_rows, keep_original_head=True)
        write_atomic(agents_file, agents_lines)

    tables = [
        (plan_table, plan_rows),
        (exec_table, exec_rows),
        (list_table, list_rows),
    ]
    updated = todo_lines[:]
    for table, rows in sorted(tables, key=lambda x: x[0]["header_idx"], reverse=True):
        updated = replace_table(updated, table, rows, keep_original_head=True)

    write_atomic(todo_file, updated)
    for line in message_lines:
        print(line)
    return RC_OK


if __name__ == "__main__":
    try:
        rc = main()
    except TaskError as exc:
        sys.exit(exc.code)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR({RC_INTERNAL}): internal error: {exc}", file=sys.stderr)
        sys.exit(RC_INTERNAL)
    else:
        sys.exit(rc)
