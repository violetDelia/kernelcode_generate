#!/usr/bin/env bash
# codex-multi-agents-dashboard.sh
#
# 创建者: 榕
# 最后一次更改: 榕
#
# 功能:
# - 聚合 agents 名单、任务列表与最近对话日志并输出终端状态总览。
# - 只读展示，不修改任何名单/任务/日志文件。
# - 支持单次输出或定时刷新输出。
#
# 对应文件:
# - spec: /home/lfr/kernelcode_generate/spec/codex-multi-agents/scripts/codex-multi-agents-dashboard.md
# - test: /home/lfr/kernelcode_generate/test/codex-multi-agents/test_codex-multi-agents-dashboard.py
# - impl: /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-dashboard.sh
#
# 使用示例:
# - codex-multi-agents-dashboard.sh -agents-file ./agents/codex-multi-agents/agents-lists.md -todo-file ./TODO.md -once
# - codex-multi-agents-dashboard.sh -agents-file ./agents/codex-multi-agents/agents-lists.md -todo-file ./TODO.md -log-file ./agents/codex-multi-agents/log/talk.log -once
# - codex-multi-agents-dashboard.sh -agents-file ./agents/codex-multi-agents/agents-lists.md -todo-file ./TODO.md -refresh 3

set -u
set -o pipefail

readonly RC_OK=0
readonly RC_ARG=1
readonly RC_FILE=2
readonly RC_DATA=3
readonly RC_INTERNAL=5

AGENTS_FILE=""
TODO_FILE=""
LOG_FILE=""
REFRESH=""
ONCE=0
NO_TALK=0
NO_SUMMARY=0

HAS_AGENTS=0
HAS_TODO=0
HAS_LOG=0
HAS_REFRESH=0

usage() {
  cat <<'USAGE'
Usage:
  codex-multi-agents-dashboard.sh -agents-file <path> -todo-file <path> [-log-file <path>] [-once]
  codex-multi-agents-dashboard.sh -agents-file <path> -todo-file <path> [-log-file <path>] -refresh <seconds>
  codex-multi-agents-dashboard.sh -agents-file <path> -todo-file <path> -no-talk -once
  codex-multi-agents-dashboard.sh -agents-file <path> -todo-file <path> -no-summary -once

Examples:
  codex-multi-agents-dashboard.sh -agents-file ./agents/codex-multi-agents/agents-lists.md -todo-file ./TODO.md -once
  codex-multi-agents-dashboard.sh -agents-file ./agents/codex-multi-agents/agents-lists.md -todo-file ./TODO.md -log-file ./agents/codex-multi-agents/log/talk.log -once
  codex-multi-agents-dashboard.sh -agents-file ./agents/codex-multi-agents/agents-lists.md -todo-file ./TODO.md -refresh 3

Return codes:
  0 success
  1 argument error
  2 file error
  3 data error
  5 internal error
USAGE
}

err() {
  local code="$1"
  shift
  printf "ERROR(%s): %s\n" "$code" "$*" >&2
  exit "$code"
}

parse_args() {
  if [[ $# -eq 0 ]]; then
    usage
    err "$RC_ARG" "missing arguments"
  fi

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -agents-file=*)
        AGENTS_FILE="${1#*=}"
        HAS_AGENTS=1
        shift
        ;;
      -agents-file)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -agents-file"
        AGENTS_FILE="$2"
        HAS_AGENTS=1
        shift 2
        ;;
      -todo-file=*)
        TODO_FILE="${1#*=}"
        HAS_TODO=1
        shift
        ;;
      -todo-file)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -todo-file"
        TODO_FILE="$2"
        HAS_TODO=1
        shift 2
        ;;
      -log-file=*)
        LOG_FILE="${1#*=}"
        HAS_LOG=1
        shift
        ;;
      -log-file)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -log-file"
        LOG_FILE="$2"
        HAS_LOG=1
        shift 2
        ;;
      -refresh=*)
        REFRESH="${1#*=}"
        HAS_REFRESH=1
        shift
        ;;
      -refresh)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -refresh"
        REFRESH="$2"
        HAS_REFRESH=1
        shift 2
        ;;
      -once)
        ONCE=1
        shift
        ;;
      -no-talk)
        NO_TALK=1
        shift
        ;;
      -no-summary)
        NO_SUMMARY=1
        shift
        ;;
      -h|--help)
        usage
        exit "$RC_OK"
        ;;
      *)
        err "$RC_ARG" "unknown argument: $1"
        ;;
    esac
  done

  [[ "$HAS_AGENTS" -eq 1 ]] || err "$RC_ARG" "missing required argument: -agents-file"
  [[ "$HAS_TODO" -eq 1 ]] || err "$RC_ARG" "missing required argument: -todo-file"

  if [[ "$ONCE" -eq 1 && "$HAS_REFRESH" -eq 1 ]]; then
    err "$RC_ARG" "-once conflicts with -refresh"
  fi

  if [[ "$HAS_REFRESH" -eq 1 ]]; then
    if ! [[ "$REFRESH" =~ ^[0-9]+$ ]] || [[ "$REFRESH" -le 0 ]]; then
      err "$RC_ARG" "refresh interval must be a positive integer"
    fi
  fi
}

run_python_core() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  local list_script="$script_dir/codex-multi-agents-list.sh"
  local task_script="$script_dir/codex-multi-agents-task.sh"

  python - "$AGENTS_FILE" "$TODO_FILE" "$LOG_FILE" "$NO_TALK" "$NO_SUMMARY" "$list_script" "$task_script" <<'PY'
import os
import subprocess
import sys
from collections import Counter

RC_OK = 0
RC_DATA = 3
RC_INTERNAL = 5

agents_file = sys.argv[1]
todo_file = sys.argv[2]
log_file = sys.argv[3]
no_talk = sys.argv[4] == "1"
no_summary = sys.argv[5] == "1"
list_script = sys.argv[6]
task_script = sys.argv[7]

MAX_COL_WIDTH = 30


def fail(code: int, message: str) -> None:
    sys.stderr.write(f"ERROR({code}): {message}\n")
    sys.exit(code)


def run_cmd(cmd: list[str]) -> str:
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip()
        if err:
            sys.stderr.write(err + "\n")
        sys.exit(result.returncode)
    return result.stdout


def is_pipe_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def split_row(line: str) -> list[str]:
    core = line.strip()
    core = core.strip("|")
    return [cell.strip() for cell in core.split("|")]


def parse_table(text: str) -> tuple[list[str], list[list[str]]]:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        fail(RC_DATA, "invalid table format: missing header")
    header_line = ""
    sep_line = ""
    start_idx = -1
    for i in range(len(lines) - 1):
        if is_pipe_row(lines[i]) and is_pipe_row(lines[i + 1]):
            header_line = lines[i]
            sep_line = lines[i + 1]
            start_idx = i + 2
            break
    if start_idx < 0:
        fail(RC_DATA, "invalid table format: header not found")
    if "---" not in sep_line:
        fail(RC_DATA, "invalid table format: missing separator row")
    header = split_row(header_line)
    rows: list[list[str]] = []
    for line in lines[start_idx:]:
        if not is_pipe_row(line):
            break
        row = split_row(line)
        rows.append(row)
    return header, rows


def truncate_cell(cell: str) -> str:
    if len(cell) <= MAX_COL_WIDTH:
        return cell
    if MAX_COL_WIDTH <= 3:
        return cell[:MAX_COL_WIDTH]
    return cell[: MAX_COL_WIDTH - 3] + "..."


def render_row(cells: list[str], widths: list[int]) -> str:
    parts = []
    for idx, cell in enumerate(cells):
        cell = cell.ljust(widths[idx])
        parts.append(f" {cell} ")
    return "|" + "|".join(parts) + "|"


def render_sep(widths: list[int]) -> str:
    parts = []
    for width in widths:
        span = max(3, width)
        parts.append(" " + ("-" * span) + " ")
    return "|" + "|".join(parts) + "|"


def render_table(header: list[str], rows: list[list[str]]) -> list[str]:
    widths = [len(h) for h in header]
    processed: list[list[str]] = []
    for row in rows:
        padded = []
        for idx, cell in enumerate(row):
            cell = truncate_cell(cell)
            widths[idx] = max(widths[idx], len(cell))
            padded.append(cell)
        processed.append(padded)
    lines = [render_row(header, widths), render_sep(widths)]
    lines.extend(render_row(row, widths) for row in processed)
    return lines


def ensure_columns(header: list[str], required: list[str], context: str) -> dict[str, int]:
    index = {name: i for i, name in enumerate(header)}
    missing = [name for name in required if name not in index]
    if missing:
        fail(RC_DATA, f"{context} missing required columns: {', '.join(missing)}")
    return index


def is_empty_row(row: list[str]) -> bool:
    return all(cell.strip() == "" for cell in row)


def load_talk_lines(path: str, max_lines: int = 10) -> list[str]:
    if not path:
        return []
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return []
    if not lines:
        return []
    return lines[-max_lines:]


try:
    agents_output = run_cmd(["bash", list_script, "-file", agents_file, "-status"])
    doing_output = run_cmd(["bash", task_script, "-file", todo_file, "-status", "-doing"])
    task_list_output = run_cmd(["bash", task_script, "-file", todo_file, "-status", "-task-list"])

    agents_header, agents_rows = parse_table(agents_output)
    doing_header, doing_rows = parse_table(doing_output)
    list_header, list_rows = parse_table(task_list_output)

    agents_index = ensure_columns(
        agents_header,
        ["姓名", "状态", "会话", "agent session", "介绍"],
        "agents table",
    )
    doing_index = ensure_columns(
        doing_header,
        ["任务 ID", "worktree", "描述", "指派"],
        "doing tasks table",
    )

    doing_rows = [row for row in doing_rows if not is_empty_row(row)]
    list_rows = [row for row in list_rows if not is_empty_row(row)]

    tasks_by_assignee: dict[str, list[tuple[str, str, str]]] = {}
    for row in doing_rows:
        task_id = row[doing_index["任务 ID"]]
        worktree = row[doing_index["worktree"]]
        desc = row[doing_index["描述"]]
        assignee = row[doing_index["指派"]]
        tasks_by_assignee.setdefault(assignee, []).append((task_id, desc, worktree))

    agent_table_header = ["姓名", "状态", "会话", "agent session", "当前任务", "工作树", "介绍"]
    agent_table_rows: list[list[str]] = []
    status_values: list[str] = []

    for row in agents_rows:
        name = row[agents_index["姓名"]]
        status = row[agents_index["状态"]]
        session = row[agents_index["会话"]]
        agent_session = row[agents_index["agent session"]]
        intro = row[agents_index["介绍"]]
        status_values.append(status)

        tasks = tasks_by_assignee.get(name, [])
        if tasks:
            task_labels = [f"{task_id}:{desc}" if desc else task_id for task_id, desc, _ in tasks]
            worktrees = [wt for _, _, wt in tasks if wt]
            current_task = ";".join(task_labels)
            current_worktree = ";".join(worktrees)
        else:
            current_task = ""
            current_worktree = ""

        agent_table_rows.append(
            [name, status, session, agent_session, current_task, current_worktree, intro]
        )

    summary_lines: list[str] = []
    if not no_summary:
        status_counter = Counter(status_values)
        status_parts = [f"{key}={status_counter[key]}" for key in sorted(status_counter.keys())]
        summary_lines = [
            "== 摘要 ==",
            f"角色总数: {len(agents_rows)}",
            f"状态分布: {', '.join(status_parts)}" if status_parts else "状态分布: -",
            f"doing 任务数: {len(doing_rows)}",
            f"task-list 任务数: {len(list_rows)}",
            "",
        ]

    output_lines: list[str] = []
    output_lines.extend(summary_lines)

    output_lines.append("== 角色状态 ==")
    output_lines.extend(render_table(agent_table_header, agent_table_rows))
    output_lines.append("")

    output_lines.append("== 正在执行的任务 ==")
    output_lines.extend(render_table(doing_header, doing_rows))
    output_lines.append("")

    output_lines.append("== 任务列表 ==")
    output_lines.extend(render_table(list_header, list_rows))
    output_lines.append("")

    if not no_talk and log_file:
        talk_lines = load_talk_lines(log_file)
        output_lines.append("== 最近对话 ==")
        if talk_lines:
            output_lines.extend(talk_lines)
        else:
            output_lines.append("（无记录）")
        output_lines.append("")

    sys.stdout.write("\n".join(output_lines))
    sys.exit(RC_OK)
except SystemExit:
    raise
except Exception as exc:  # noqa: BLE001
    sys.stderr.write(f"ERROR({RC_INTERNAL}): internal error: {exc}\n")
    sys.exit(RC_INTERNAL)
PY
}

main() {
  parse_args "$@"

  if [[ "$HAS_REFRESH" -eq 1 ]]; then
    while true; do
      printf "\033c"
      run_python_core
      sleep "$REFRESH"
    done
  else
    run_python_core
  fi
}

main "$@"
