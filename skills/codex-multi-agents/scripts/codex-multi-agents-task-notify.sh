#!/usr/bin/env bash
# codex-multi-agents-task-notify.sh
#
# 创建者: OpenAI
# 最后一次更改: 小李飞刀
#
# 功能:
# - 执行 task 脚本的通知副作用：list -init、tmux -talk、任务消息拼装、管理员摘要发送。
# - 供 codex-multi-agents-task.sh 在 -dispatch、-reassign 与 -next 成功后调用。
#
# 对应文件:
# - spec: /home/lfr/kernelcode_generate/spec/codex-multi-agents/scripts/codex-multi-agents-task.md
# - test: /home/lfr/kernelcode_generate/test/codex-multi-agents/test_codex-multi-agents-task.py
# - impl: /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-task-notify.sh
#
# 使用示例:
# - bash skills/codex-multi-agents/scripts/codex-multi-agents-task-notify.sh -dispatch-init -agents-list ./agents/codex-multi-agents/agents-lists.md -to worker-a
# - bash skills/codex-multi-agents/scripts/codex-multi-agents-task-notify.sh -next -file ./TODO.md -task_id EX-2 -type review -agents-list ./agents/codex-multi-agents/agents-lists.md -from worker-b -admin 神秘人

set -u
set -o pipefail

readonly RC_OK=0
readonly RC_ARG=1
readonly RC_FILE=2

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
LIST_SCRIPT="${SCRIPT_DIR}/codex-multi-agents-list.sh"
TMUX_SCRIPT="${SCRIPT_DIR}/codex-multi-agents-tmux.sh"

OP_DISPATCH_INIT=0
OP_DISPATCH_MESSAGE=0
OP_REASSIGN=0
OP_NEXT=0

FILE=""
TASK_ID=""
TO=""
OLD_ASSIGNEE=""
FROM=""
AGENTS_LIST=""
MESSAGE=""
TYPE_KIND=""
ADMIN_NAME=""
AUTO_TASK_ID=""
AUTO_ASSIGNEE=""

trim() {
  local s="${1-}"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf "%s" "$s"
}

err() {
  local code="$1"
  shift
  printf "ERROR(%s): %s\n" "$code" "$*" >&2
  exit "$code"
}

usage() {
  cat <<'USAGE'
Usage:
  codex-multi-agents-task-notify.sh -dispatch-init -agents-list <agents-lists.md> -to <worker>
  codex-multi-agents-task-notify.sh -dispatch-message -file <TODO.md> -task_id <id> -to <worker> -from <sender> -agents-list <agents-lists.md> [-message <text>]
  codex-multi-agents-task-notify.sh -reassign -file <TODO.md> -task_id <id> -to <worker> -old-assignee <worker> -from <sender> -agents-list <agents-lists.md>
  codex-multi-agents-task-notify.sh -next -file <TODO.md> -task_id <id> -type <spec|build|review|merge|other|refactor> -agents-list <agents-lists.md> -from <sender> -admin <admin> [-auto-task-id <id>] [-auto-assignee <name>]
USAGE
}

parse_args() {
  [[ $# -gt 0 ]] || err "$RC_ARG" "missing arguments"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -dispatch-init)
        OP_DISPATCH_INIT=1
        shift
        ;;
      -dispatch-message)
        OP_DISPATCH_MESSAGE=1
        shift
        ;;
      -reassign)
        OP_REASSIGN=1
        shift
        ;;
      -next)
        OP_NEXT=1
        shift
        ;;
      -file)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -file"
        FILE="$2"
        shift 2
        ;;
      -task_id)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -task_id"
        TASK_ID="$2"
        shift 2
        ;;
      -to)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -to"
        TO="$2"
        shift 2
        ;;
      -old-assignee)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -old-assignee"
        OLD_ASSIGNEE="$2"
        shift 2
        ;;
      -from)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -from"
        FROM="$2"
        shift 2
        ;;
      -agents-list)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -agents-list"
        AGENTS_LIST="$2"
        shift 2
        ;;
      -message)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -message"
        MESSAGE="$2"
        shift 2
        ;;
      -type)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -type"
        TYPE_KIND="$2"
        shift 2
        ;;
      -admin)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -admin"
        ADMIN_NAME="$2"
        shift 2
        ;;
      -auto-task-id)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -auto-task-id"
        AUTO_TASK_ID="$2"
        shift 2
        ;;
      -auto-assignee)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -auto-assignee"
        AUTO_ASSIGNEE="$2"
        shift 2
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

  local op_count=$((OP_DISPATCH_INIT + OP_DISPATCH_MESSAGE + OP_REASSIGN + OP_NEXT))
  [[ "$op_count" -eq 1 ]] || err "$RC_ARG" "exactly one operation is required: -dispatch-init|-dispatch-message|-reassign|-next"

  if [[ "$OP_DISPATCH_INIT" -eq 1 ]]; then
    [[ -n "$(trim "$AGENTS_LIST")" ]] || err "$RC_ARG" "-dispatch-init requires -agents-list"
    [[ -n "$(trim "$TO")" ]] || err "$RC_ARG" "-dispatch-init requires -to"
  elif [[ "$OP_DISPATCH_MESSAGE" -eq 1 ]]; then
    [[ -n "$(trim "$FILE")" ]] || err "$RC_ARG" "-dispatch-message requires -file"
    [[ -n "$(trim "$TASK_ID")" ]] || err "$RC_ARG" "-dispatch-message requires -task_id"
    [[ -n "$(trim "$TO")" ]] || err "$RC_ARG" "-dispatch-message requires -to"
    [[ -n "$(trim "$FROM")" ]] || err "$RC_ARG" "-dispatch-message requires -from"
    [[ -n "$(trim "$AGENTS_LIST")" ]] || err "$RC_ARG" "-dispatch-message requires -agents-list"
  elif [[ "$OP_REASSIGN" -eq 1 ]]; then
    [[ -n "$(trim "$FILE")" ]] || err "$RC_ARG" "-reassign requires -file"
    [[ -n "$(trim "$TASK_ID")" ]] || err "$RC_ARG" "-reassign requires -task_id"
    [[ -n "$(trim "$TO")" ]] || err "$RC_ARG" "-reassign requires -to"
    [[ -n "$(trim "$OLD_ASSIGNEE")" ]] || err "$RC_ARG" "-reassign requires -old-assignee"
    [[ -n "$(trim "$FROM")" ]] || err "$RC_ARG" "-reassign requires -from"
    [[ -n "$(trim "$AGENTS_LIST")" ]] || err "$RC_ARG" "-reassign requires -agents-list"
  elif [[ "$OP_NEXT" -eq 1 ]]; then
    [[ -n "$(trim "$FILE")" ]] || err "$RC_ARG" "-next requires -file"
    [[ -n "$(trim "$TASK_ID")" ]] || err "$RC_ARG" "-next requires -task_id"
    [[ -n "$(trim "$TYPE_KIND")" ]] || err "$RC_ARG" "-next requires -type"
    [[ -n "$(trim "$AGENTS_LIST")" ]] || err "$RC_ARG" "-next requires -agents-list"
    [[ -n "$(trim "$FROM")" ]] || err "$RC_ARG" "-next requires -from"
  fi
}

send_init_for_agent() {
  local target="$1"
  if [[ ! -f "$LIST_SCRIPT" ]]; then
    printf "WARN: list script not found, skip dispatch init: %s\n" "$LIST_SCRIPT" >&2
    return 0
  fi

  local output=""
  local rc=0
  output="$(bash "$LIST_SCRIPT" -file "$AGENTS_LIST" -init -name "$target" 2>&1)" || rc=$?
  if [[ "$rc" -ne 0 ]]; then
    printf "WARN: dispatch init failed for %s: %s\n" "$target" "$output" >&2
    return 0
  fi
}

send_talk_message() {
  local from_name="$1"
  local to_name="$2"
  local body="$3"

  if [[ ! -f "$TMUX_SCRIPT" ]]; then
    printf "WARN: skip talk, tmux script not found: %s\n" "$TMUX_SCRIPT" >&2
    return 0
  fi

  local output=""
  local rc=0
  output="$(bash "$TMUX_SCRIPT" -talk -from "$from_name" -to "$to_name" -agents-list "$AGENTS_LIST" -message "$body" 2>&1)" || rc=$?
  if [[ "$rc" -ne 0 ]]; then
    printf "WARN: talk failed from %s to %s: %s\n" "$from_name" "$to_name" "$output" >&2
    return 0
  fi

  [[ -z "$output" ]] || printf "%s\n" "$output"
}

build_task_message_for_id() {
  local todo_file="$1"
  local target_task_id="$2"

  python3 - "$todo_file" "$target_task_id" "$REPO_ROOT" <<'PY'
import sys

todo_file = sys.argv[1]
task_id = sys.argv[2]
repo_root = sys.argv[3]


def is_pipe_row(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def split_row(text: str) -> list[str]:
    stripped = text.strip()
    return [cell.strip() for cell in stripped[1:-1].split("|")]


with open(todo_file, "r", encoding="utf-8") as file_handle:
    lines = file_handle.read().splitlines()

section_start = -1
for index, line in enumerate(lines):
    if line.strip() == "## 正在执行的任务":
        section_start = index
        break

if section_start < 0:
    print(
        f"请处理任务 {task_id}。完成后按 {repo_root}/agents/standard/任务记录约定.md 记录并回报管理员；流程不清楚请询问管理员；实现/架构问题请询问架构师。"
    )
    raise SystemExit(0)

section_end = len(lines)
for index in range(section_start + 1, len(lines)):
    if lines[index].startswith("## "):
        section_end = index
        break

header_cells = None
header_idx = -1
for index in range(section_start + 1, max(section_end - 1, section_start + 1)):
    if not is_pipe_row(lines[index]):
        continue
    if not is_pipe_row(lines[index + 1]):
        continue
    header_cells = split_row(lines[index])
    header_idx = index
    break

if header_cells is None:
    print(
        f"请处理任务 {task_id}。完成后按 {repo_root}/agents/standard/任务记录约定.md 记录并回报管理员；流程不清楚请询问管理员；实现/架构问题请询问架构师。"
    )
    raise SystemExit(0)


def cell_value(row: list[str], name: str) -> str:
    if name not in header_cells:
        return ""
    cell_idx = header_cells.index(name)
    if cell_idx >= len(row):
        return ""
    value = row[cell_idx].strip()
    if value == "None":
        return ""
    return value


row_cells = None
for index in range(header_idx + 2, section_end):
    line = lines[index]
    if not is_pipe_row(line):
        continue
    cells = split_row(line)
    if cells and cells[0] == task_id:
        row_cells = cells
        break

if row_cells is None:
    print(
        f"请处理任务 {task_id}。完成后按 {repo_root}/agents/standard/任务记录约定.md 记录并回报管理员；流程不清楚请询问管理员；实现/架构问题请询问架构师。"
    )
    raise SystemExit(0)

worktree = cell_value(row_cells, "worktree")
desc = cell_value(row_cells, "描述") or task_id
plan_doc = cell_value(row_cells, "计划书")
record_file = cell_value(row_cells, "记录文件")
record_spec = f"{repo_root}/agents/standard/任务记录约定.md"

parts = []
if worktree:
    parts.append(f"worktree={worktree}")
if plan_doc:
    parts.append(f"计划书={plan_doc}")
if record_file:
    parts.append(f"记录文件={record_file}")
prefix = "；".join(parts)
if prefix:
    prefix = prefix + "；"

print(
    f"请处理任务 {task_id}（{desc}）。{prefix}完成后按 {record_spec} 记录并回报管理员；流程不清楚请询问管理员；实现/架构问题请询问架构师。"
)
PY
}

dispatch_message() {
  local body=""
  local output=""
  local rc=0

  if [[ -n "${MESSAGE-}" ]]; then
    body="$MESSAGE"
  else
    body="$(build_task_message_for_id "$FILE" "$TASK_ID")"
  fi

  if [[ ! -f "$TMUX_SCRIPT" ]]; then
    if [[ -n "${MESSAGE-}" ]]; then
      printf "ERROR(%s): tmux script not found: %s\n" "$RC_FILE" "$TMUX_SCRIPT" >&2
      return "$RC_FILE"
    fi
    printf "WARN: skip auto dispatch talk, tmux script not found: %s\n" "$TMUX_SCRIPT" >&2
    return 0
  fi

  output="$(bash "$TMUX_SCRIPT" -talk -from "$FROM" -to "$TO" -agents-list "$AGENTS_LIST" -message "$body" 2>&1)" || rc=$?
  if [[ "$rc" -ne 0 ]]; then
    if [[ -n "${MESSAGE-}" ]]; then
      printf "%s\n" "$output" >&2
      return "$rc"
    fi
    printf "WARN: auto dispatch talk failed for task %s: %s\n" "$TASK_ID" "$output" >&2
    return 0
  fi

  [[ -z "$output" ]] || printf "%s\n" "$output"
}

build_reassign_cancel_message() {
  # 功能说明:
  # - 生成旧接手人在改派后收到的默认提示文本。
  # - 固定包含任务 ID 与新接手人，提醒旧接手人停止当前处理。
  #
  # 使用示例:
  # - build_reassign_cancel_message
  #
  # 关联文件:
  # - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
  # - test: test/codex-multi-agents/test_codex-multi-agents-task.py
  # - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-notify.sh
  printf "任务 %s 已改派给 %s，请停止当前处理并等待新的安排。" "$TASK_ID" "$TO"
}

reassign_notify() {
  # 功能说明:
  # - 在改派成功后同时通知旧接手人与新接手人。
  # - 旧接手人收到取消提示，新接手人收到与分发一致的任务消息模板。
  #
  # 使用示例:
  # - reassign_notify
  #
  # 关联文件:
  # - spec: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
  # - test: test/codex-multi-agents/test_codex-multi-agents-task.py
  # - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-task-notify.sh
  send_talk_message "$FROM" "$OLD_ASSIGNEE" "$(build_reassign_cancel_message)"
  send_init_for_agent "$TO"
  dispatch_message
}

next_notify() {
  local summary_message=""
  local assignee_label=""

  if [[ -n "$(trim "$AUTO_TASK_ID")" && -n "$(trim "$AUTO_ASSIGNEE")" && "$AUTO_ASSIGNEE" != "$FROM" ]]; then
    send_init_for_agent "$AUTO_ASSIGNEE"
    send_talk_message "$FROM" "$AUTO_ASSIGNEE" "$(build_task_message_for_id "$FILE" "$AUTO_TASK_ID")"
  fi

  if [[ -n "$(trim "$ADMIN_NAME")" && "$ADMIN_NAME" != "$FROM" ]]; then
    if [[ -n "$(trim "$AUTO_TASK_ID")" && -n "$(trim "$AUTO_ASSIGNEE")" ]]; then
      assignee_label="$AUTO_ASSIGNEE"
      if [[ "$AUTO_ASSIGNEE" == "$FROM" ]]; then
        assignee_label="当前执行者"
      fi
      if [[ "$AUTO_TASK_ID" == "$TASK_ID" ]]; then
        summary_message="任务 $TASK_ID 已完成当前阶段，已回到任务列表；新任务类型=$TYPE_KIND，已经指派给-> $assignee_label。"
      else
        summary_message="任务 $TASK_ID 已完成当前阶段，已回到任务列表；已自动开始任务 $AUTO_TASK_ID -> $assignee_label。"
      fi
    else
      summary_message="任务 $TASK_ID 已完成当前阶段，已回到任务列表；新任务类型=$TYPE_KIND，请管理员推进。"
    fi
    send_talk_message "$FROM" "$ADMIN_NAME" "$summary_message"
  fi
}

main() {
  parse_args "$@"

  if [[ "$OP_DISPATCH_INIT" -eq 1 ]]; then
    send_init_for_agent "$TO"
    return 0
  fi

  if [[ "$OP_DISPATCH_MESSAGE" -eq 1 ]]; then
    dispatch_message
    return $?
  fi

  if [[ "$OP_REASSIGN" -eq 1 ]]; then
    reassign_notify
    return $?
  fi

  next_notify
}

main "$@"
