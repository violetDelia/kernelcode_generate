#!/usr/bin/env python3
"""codex-multi-agents-task-core.py.

创建者: OpenAI
最后一次更改: OpenAI

功能说明:
- 处理 `codex-multi-agents-task.sh` 的核心数据逻辑。
- 负责解析与写回 `TODO.md`、`DONE.md`、`agents-lists.md`。
- 负责任务状态流转、计划书统计、角色权限与自动续接候选判定。

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
ALLOWED_TASK_TYPES: set[str] = {"spec", "build", "review", "merge", "other", "refactor"}


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
    if kind == "spec":
        return ["spec"]
    if kind == "build":
        return ["实现", "开发", "测试", "全能替补"]
    if kind == "review":
        return ["审查", "复审"]
    if kind == "merge":
        return ["合并"]
    if kind == "refactor":
        return ["实现", "开发", "测试", "重构", "全能替补"]
    if kind == "other":
        return []
    return []


def agent_matches_type(kind: str, duty: str) -> bool:
    if kind == "other":
        return True
    keywords = type_duty_keywords(kind)
    duty_text = duty.strip()
    return any((kw in duty_text for kw in keywords))


def is_agent_eligible_for_auto(
    name: str,
    kind: str,
    agents_rows: list[list[str]],
    agents_table: dict,
) -> int:
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
    if not agent_matches_type(kind, duty):
        return -1
    return idx


def pick_next_auto_assignee(
    row: list[str],
    agents_rows: list[list[str]],
    agents_table: dict,
    operator_name: str,
) -> tuple[str, int] | None:
    kind = normalize_task_type(row[5], RC_DATA, f"task list row {row[0].strip()}")
    operator = operator_name.strip()
    operator_idx = is_agent_eligible_for_auto(operator, kind, agents_rows, agents_table)
    if operator_idx >= 0:
        return operator, operator_idx

    for candidate_row in agents_rows:
        name = candidate_row[agents_table["name_idx"]].strip()
        if not name or name == operator:
            continue
        candidate_idx = is_agent_eligible_for_auto(name, kind, agents_rows, agents_table)
        if candidate_idx >= 0:
            return name, candidate_idx
    return None


def ensure_operator_permission(
    op: str,
    operator_name: str,
    permission_agents_file: str,
) -> None:
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

    _, permission_table = parse_agents_table(permission_agents_file)
    permission_rows = [r[:] for r in permission_table["rows"]]
    row_idx = find_agent_row_index(permission_rows, permission_table["name_idx"], caller)
    if row_idx < 0:
        fail(RC_DATA, f"operator not found in permission agents list: {caller}")

    row = permission_rows[row_idx]
    intro = ""
    duty = ""
    if "介绍" in permission_table["header"]:
        intro = row[permission_table["header"].index("介绍")].strip()
    if "职责" in permission_table["header"]:
        duty = row[permission_table["header"].index("职责")].strip()

    role_text = f"{intro} {duty}"
    admin_names = parse_csv_names(
        os.environ.get("CODEX_MULTI_AGENTS_ADMIN_USERS", "神秘人")
    )
    arch_names = parse_csv_names(
        os.environ.get("CODEX_MULTI_AGENTS_ARCH_USERS", "大闸蟹,守护最好的爱莉希雅")
    )
    is_admin = ("管理员" in role_text) or (caller in admin_names)
    is_arch = ("架构师" in role_text) or (caller in arch_names)

    if op == "new":
        if not (is_admin or is_arch):
            fail(RC_DATA, f"operation -{op} is restricted to 架构师或管理员: {caller}")
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
    active: set[str] = set()
    for row in exec_rows:
        assignee = row[8].strip()
        status = row[9].strip()
        if assignee and status == "进行中":
            active.add(assignee)
    return len(active)


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
        if agents_rows[agent_idx][agents_table["status_idx"]].strip().lower() == "busy":
            fail(RC_DATA, f"agent is busy, cannot dispatch: {assignee}")
        active_assignees = count_active_assignees(exec_rows)
        if active_assignees >= max_parallel:
            fail(RC_DATA, f"parallel assignee limit reached: {active_assignees}/{max_parallel}")
        table_type = row[5].strip()
        if type_kind and table_type and table_type != type_kind:
            fail(RC_DATA, f"task type mismatch: table={table_type} arg={type_kind}")
        task_type = table_type or type_kind
        if not task_type:
            fail(RC_DATA, f"empty task type in task list: {task_id}")
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
                task_type,
                depends_val,
                plan_doc_val,
                assignee,
                "进行中",
                "",
                record_file,
            ]
        )
        agents_rows[agent_idx][agents_table["status_idx"]] = "busy"
        message_lines.append(f"OK: dispatch {task_id} -> {assignee}")
        message_lines.append(f"OK: replace {assignee} 状态")

    elif op == "done":
        idx = find_row_index(exec_rows, task_id)
        if idx < 0:
            fail(RC_DATA, f"task not found in running list: {task_id}")

        row = exec_rows.pop(idx)
        update_plan_on_done(plan_rows, row[7].strip())
        assignee = row[8].strip()
        if assignee:
            assert agents_table is not None
            assert agents_rows is not None
            agent_idx = find_agent_row_index(agents_rows, agents_table["name_idx"], assignee)
            if agent_idx < 0:
                fail(RC_DATA, f"agent not found in agents list: {assignee}")
        done_lines, done_table = parse_done_table(done_file)
        done_rows = [r[:] for r in done_table["rows"]]
        finished_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
        done_rows.append([row[0], row[4], assignee, "已完成", finished_at, log_file, ""])
        done_lines = replace_table(done_lines, done_table, done_rows, keep_original_head=False)
        message_lines.append(f"OK: done {task_id}")
        if assignee:
            if count_doing_tasks(exec_rows, assignee) == 0:
                agents_rows[agent_idx][agents_table["status_idx"]] = "free"
                message_lines.append(f"OK: replace {assignee} 状态")
            else:
                agents_rows[agent_idx][agents_table["status_idx"]] = "busy"

    elif op == "pause":
        idx = find_row_index(exec_rows, task_id)
        if idx < 0:
            fail(RC_DATA, f"task not found in running list: {task_id}")

        assignee = exec_rows[idx][8].strip()
        if assignee:
            assert agents_table is not None
            assert agents_rows is not None
            agent_idx = find_agent_row_index(agents_rows, agents_table["name_idx"], assignee)
            if agent_idx < 0:
                fail(RC_DATA, f"agent not found in agents list: {assignee}")
        exec_rows[idx][9] = "暂停"
        message_lines.append(f"OK: pause {task_id}")
        if assignee:
            if count_doing_tasks(exec_rows, assignee) == 0:
                agents_rows[agent_idx][agents_table["status_idx"]] = "free"
                message_lines.append(f"OK: replace {assignee} 状态")
            else:
                agents_rows[agent_idx][agents_table["status_idx"]] = "busy"

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
            agent_idx = find_agent_row_index(agents_rows, agents_table["name_idx"], assignee)
            if agent_idx < 0:
                fail(RC_DATA, f"agent not found in agents list: {assignee}")

        exec_rows[idx][9] = "进行中"
        message_lines.append(f"OK: continue {task_id}")
        if assignee:
            agents_rows[agent_idx][agents_table["status_idx"]] = "busy"
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

        old_assignee = exec_rows[idx][8].strip()
        old_idx = None
        if old_assignee:
            old_idx = find_agent_row_index(agents_rows, agents_table["name_idx"], old_assignee)
            if old_idx < 0:
                fail(RC_DATA, f"agent not found in agents list: {old_assignee}")

        exec_rows[idx][8] = new_assignee
        message_lines.append(f"OK: reassign {task_id} -> {new_assignee}")

        updated: set[str] = set()

        def update_agent(name: str, row_idx: int | None) -> None:
            if not name or row_idx is None or name in updated:
                return
            status = "busy" if count_doing_tasks(exec_rows, name) > 0 else "free"
            agents_rows[row_idx][agents_table["status_idx"]] = status
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

        row = exec_rows.pop(idx)
        assignee = row[8].strip()
        next_list_row = [row[0], row[1], row[2], row[3], message.strip(), type_kind, row[6], row[7], "", row[11]]
        list_rows.append(next_list_row)
        message_lines.append(f"OK: next {task_id}")

        if assignee:
            assert agents_table is not None
            assert agents_rows is not None
            agent_idx = find_agent_row_index(agents_rows, agents_table["name_idx"], assignee)
            if agent_idx < 0:
                fail(RC_DATA, f"agent not found in agents list: {assignee}")
            if count_doing_tasks(exec_rows, assignee) == 0:
                agents_rows[agent_idx][agents_table["status_idx"]] = "free"
            else:
                agents_rows[agent_idx][agents_table["status_idx"]] = "busy"
            message_lines.append(f"OK: replace {assignee} 状态")

        if auto_flag:
            assert agents_table is not None
            assert agents_rows is not None
            next_kind = normalize_task_type(next_list_row[5], RC_DATA, f"next task {task_id}")
            if next_kind not in {"merge", "review", "build", "spec"}:
                message_lines.append("__AUTO_NEXT__=none")
            elif count_active_assignees(exec_rows) >= max_parallel:
                message_lines.append("__AUTO_NEXT__=none")
            else:
                picked = pick_next_auto_assignee(next_list_row, agents_rows, agents_table, operator_name)
                if picked is None:
                    message_lines.append("__AUTO_NEXT__=none")
                else:
                    candidate_assignee, candidate_agent_idx = picked
                    candidate_idx = find_row_index(list_rows, task_id)
                    if candidate_idx < 0:
                        fail(RC_INTERNAL, f"task not found after next append: {task_id}")
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
                    message_lines.append(f"OK: auto-dispatch {candidate_row[0]} -> {candidate_assignee}")
                    message_lines.append(f"OK: replace {candidate_assignee} 状态")
                    message_lines.append(f"__AUTO_NEXT__=dispatch|{candidate_row[0]}|{candidate_assignee}")

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
