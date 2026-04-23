#!/usr/bin/env bash
# codex-multi-agents-task.sh
#
# 创建者: 榕
# 最后一次更改: 小李飞刀
#
# 功能:
# - 管理 TODO.md 任务流转: 分发、完成、暂停、继续、改派、续接、新建、删除、计划归档。
# - 支持 DONE.md 自动创建与完成记录追加。
# - 在分发、完成、暂停、继续、改派、续接时同步更新 agents-lists.md 角色状态。
# - 在 TODO.md 维护计划书进度表，支持 -status -plan-list 与 -done-plan 收口归档。
# - 通过 task-core.py 处理表格读写、状态流转、权限与自动续接判定。
# - 通过 task-notify.sh 处理 list -init、tmux -talk、任务消息、改派通知与管理员摘要。
# - 写操作统一使用 flock 文件锁。
#
# 对应文件:
# - spec: /home/lfr/kernelcode_generate/spec/codex-multi-agents/scripts/codex-multi-agents-task.md
# - test: /home/lfr/kernelcode_generate/test/codex-multi-agents/test_codex-multi-agents-task.py
# - impl: /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-task.sh

set -u
set -o pipefail

readonly RC_OK=0
readonly RC_ARG=1
readonly RC_FILE=2
readonly RC_DATA=3
readonly RC_LOCK=4
readonly RC_INTERNAL=5

# 并行执行人数上限（可通过环境变量覆盖）
# 示例：CODEX_MULTI_AGENTS_MAX_PARALLEL=10 codex-multi-agents-task.sh ...
MAX_PARALLEL_AGENTS="${CODEX_MULTI_AGENTS_MAX_PARALLEL:-8}"

OP_DISPATCH=0
OP_DONE=0
OP_PAUSE=0
OP_CONTINUE=0
OP_REASSIGN=0
OP_NEW=0
OP_NEXT=0
OP_STATUS=0
OP_DELETE=0
OP_DONE_PLAN=0

FILE=""
AGENTS_LIST=""
TASK_ID=""
TO=""
FROM=""
INFO=""
LOG_FILE=""
WORKTREE=""
MESSAGE=""
TYPE_KIND=""
DEPENDS=""
PLAN_DOC=""

HAS_FILE=0
HAS_AGENTS_LIST=0
HAS_TASK_ID=0
HAS_TO=0
HAS_FROM=0
HAS_INFO=0
HAS_LOG=0
HAS_WORKTREE=0
HAS_MESSAGE=0
HAS_TYPE=0
HAS_DEPENDS=0
HAS_PLAN=0
HAS_AUTO=0
HAS_DOING=0
HAS_TASK_LIST=0
HAS_PLAN_LIST=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
LIST_SCRIPT="${SCRIPT_DIR}/codex-multi-agents-list.sh"
TMUX_SCRIPT="${SCRIPT_DIR}/codex-multi-agents-tmux.sh"
TASK_CORE_SCRIPT="${SCRIPT_DIR}/codex-multi-agents-task-core.py"
TASK_NOTIFY_SCRIPT="${SCRIPT_DIR}/codex-multi-agents-task-notify.sh"
DEFAULT_CONFIG_FILE="${REPO_ROOT}/agents/codex-multi-agents/config/config.txt"

validate_parallel_limit() {
  if [[ ! "$MAX_PARALLEL_AGENTS" =~ ^[0-9]+$ ]]; then
    err "$RC_ARG" "invalid CODEX_MULTI_AGENTS_MAX_PARALLEL: ${MAX_PARALLEL_AGENTS}"
  fi
  if [[ "$MAX_PARALLEL_AGENTS" -le 0 ]]; then
    err "$RC_ARG" "CODEX_MULTI_AGENTS_MAX_PARALLEL must be greater than 0"
  fi
}

trim() {
  local s="${1-}"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf "%s" "$s"
}

validate_type_kind() {
  local raw="${1-}"
  local text
  text="$(trim "$raw" | tr '[:upper:]' '[:lower:]')"
  case "$text" in
    spec|build|review|merge|other|refactor)
      printf "%s" "$text"
      return 0
      ;;
    *)
      err "$RC_ARG" "invalid value for -type: ${raw}"
      ;;
  esac
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
  codex-multi-agents-task.sh -file <TODO.md> -dispatch -task_id <id> [-to <worker>] -agents-list <agents-lists.md> [-message <text>] [-type <spec|build|review|merge|other|refactor>]
  codex-multi-agents-task.sh -file <TODO.md> -done -task_id <id> -log <log_path> -agents-list <agents-lists.md>
  codex-multi-agents-task.sh -file <TODO.md> -pause -task_id <id> -agents-list <agents-lists.md>
  codex-multi-agents-task.sh -file <TODO.md> -continue -task_id <id> -agents-list <agents-lists.md>
  codex-multi-agents-task.sh -file <TODO.md> -reassign -task_id <id> -to <worker> -agents-list <agents-lists.md>
  codex-multi-agents-task.sh -file <TODO.md> -next [-to <worker>|-auto] -task_id <id> -from <sender> -type <spec|build|review|merge|other|refactor> -message <text> -agents-list <agents-lists.md>
  codex-multi-agents-task.sh -file <TODO.md> -new -info <desc> -type <spec|build|review|merge|other|refactor> -worktree <path> -depends <task_ids|None> -plan <plan_doc|None> [-to <worker>] [-from <owner>] [-log <record_path>]
  codex-multi-agents-task.sh -file <TODO.md> -status -doing
  codex-multi-agents-task.sh -file <TODO.md> -status -task-list
  codex-multi-agents-task.sh -file <TODO.md> -status -plan-list
  codex-multi-agents-task.sh -file <TODO.md> -delete -task_id <id>
  codex-multi-agents-task.sh -file <TODO.md> -done-plan -plan <plan_doc>

Notes:
  - -next without -to will try to auto-start the first ready task in 任务列表 after updating the current task.
  - -next -auto will continue auto-starting all ready tasks in 任务列表 until no ready task remains or the parallel limit is reached.
  - explicit -dispatch/-reassign/-next -to must match the target agent duty with the task type; merge only allows merge specialists.

Examples:
  codex-multi-agents-task.sh -file ./skills/codex-multi-agents/examples/TODO.md -dispatch -task_id EX-3 -to worker-a -agents-list ./agents/codex-multi-agents/agents-lists.md -message "请处理任务 EX-3"
  codex-multi-agents-task.sh -file ./skills/codex-multi-agents/examples/TODO.md -done -task_id EX-1 -log ./agents/codex-multi-agents/log/task-EX-1.log -agents-list ./agents/codex-multi-agents/agents-lists.md
  codex-multi-agents-task.sh -file ./skills/codex-multi-agents/examples/TODO.md -pause -task_id EX-2 -agents-list ./agents/codex-multi-agents/agents-lists.md
  codex-multi-agents-task.sh -file ./skills/codex-multi-agents/examples/TODO.md -continue -task_id EX-2 -agents-list ./agents/codex-multi-agents/agents-lists.md
  codex-multi-agents-task.sh -file ./skills/codex-multi-agents/examples/TODO.md -reassign -task_id EX-2 -to worker-c -agents-list ./agents/codex-multi-agents/agents-lists.md
  codex-multi-agents-task.sh -file ./skills/codex-multi-agents/examples/TODO.md -next -task_id EX-2 -from worker-b -type review -message "下一阶段：补齐边界测试" -agents-list ./agents/codex-multi-agents/agents-lists.md
  codex-multi-agents-task.sh -file ./skills/codex-multi-agents/examples/TODO.md -next -task_id EX-2 -from worker-b -to worker-c -type review -message "下一阶段：补齐边界测试" -agents-list ./agents/codex-multi-agents/agents-lists.md
  codex-multi-agents-task.sh -file ./skills/codex-multi-agents/examples/TODO.md -next -auto -task_id EX-2 -from worker-b -type review -message "下一阶段：补齐边界测试" -agents-list ./agents/codex-multi-agents/agents-lists.md
  codex-multi-agents-task.sh -file ./skills/codex-multi-agents/examples/TODO.md -new -info "补充单元测试" -type build -worktree repo-x -depends "EX-2,EX-5" -plan "ARCHITECTURE/plan/x.md" -to worker-b -from 李白 -log ./log/record.md
  codex-multi-agents-task.sh ./skills/codex-multi-agents/examples/TODO.md -file -status -doing
  codex-multi-agents-task.sh ./skills/codex-multi-agents/examples/TODO.md -file -status -task-list
  codex-multi-agents-task.sh ./skills/codex-multi-agents/examples/TODO.md -file -status -plan-list
  codex-multi-agents-task.sh -file ./skills/codex-multi-agents/examples/TODO.md -delete -task_id EX-4
  codex-multi-agents-task.sh -file ./skills/codex-multi-agents/examples/TODO.md -done-plan -plan "ARCHITECTURE/plan/x.md"

Return codes:
  0 success
  1 argument error
  2 file error
  3 data error
  4 lock error
  5 internal error
USAGE
}

parse_args() {
  if [[ $# -eq 0 ]]; then
    usage
    err "$RC_ARG" "missing arguments"
  fi

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -dispatch)
        OP_DISPATCH=1
        shift
        ;;
      -done)
        OP_DONE=1
        shift
        ;;
      -pause)
        OP_PAUSE=1
        shift
        ;;
      -continue)
        OP_CONTINUE=1
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
      -new)
        OP_NEW=1
        shift
        ;;
      -delete)
        OP_DELETE=1
        shift
        ;;
      -done-plan)
        OP_DONE_PLAN=1
        shift
        ;;
      -status)
        OP_STATUS=1
        shift
        ;;
      -file=*)
        FILE="${1#*=}"
        HAS_FILE=1
        shift
        ;;
      -file)
        if [[ $# -ge 2 && "${2-}" != -* ]]; then
          FILE="$2"
          HAS_FILE=1
          shift 2
        else
          [[ "$HAS_FILE" -eq 1 ]] || err "$RC_ARG" "missing value for -file"
          shift
        fi
        ;;
      -agents-list=*)
        AGENTS_LIST="${1#*=}"
        HAS_AGENTS_LIST=1
        shift
        ;;
      -agents-list)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -agents-list"
        AGENTS_LIST="$2"
        HAS_AGENTS_LIST=1
        shift 2
        ;;
      -task_id=*)
        TASK_ID="${1#*=}"
        HAS_TASK_ID=1
        shift
        ;;
      -task_id)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -task_id"
        TASK_ID="$2"
        HAS_TASK_ID=1
        shift 2
        ;;
      -to=*)
        TO="${1#*=}"
        HAS_TO=1
        shift
        ;;
      -to)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -to"
        TO="$2"
        HAS_TO=1
        shift 2
        ;;
      -from=*)
        FROM="${1#*=}"
        HAS_FROM=1
        shift
        ;;
      -from)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -from"
        FROM="$2"
        HAS_FROM=1
        shift 2
        ;;
      -info=*)
        INFO="${1#*=}"
        HAS_INFO=1
        shift
        ;;
      -info)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -info"
        INFO="$2"
        HAS_INFO=1
        shift 2
        ;;
      -worktree=*)
        WORKTREE="${1#*=}"
        HAS_WORKTREE=1
        shift
        ;;
      -worktree)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -worktree"
        WORKTREE="$2"
        HAS_WORKTREE=1
        shift 2
        ;;
      -message=*)
        MESSAGE="${1#*=}"
        HAS_MESSAGE=1
        shift
        ;;
      -message)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -message"
        MESSAGE="$2"
        HAS_MESSAGE=1
        shift 2
        ;;
      -type=*)
        TYPE_KIND="${1#*=}"
        HAS_TYPE=1
        shift
        ;;
      -type)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -type"
        TYPE_KIND="$2"
        HAS_TYPE=1
        shift 2
        ;;
      -depends=*)
        DEPENDS="${1#*=}"
        HAS_DEPENDS=1
        shift
        ;;
      -depends)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -depends"
        DEPENDS="$2"
        HAS_DEPENDS=1
        shift 2
        ;;
      -plan=*)
        PLAN_DOC="${1#*=}"
        HAS_PLAN=1
        shift
        ;;
      -plan)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -plan"
        PLAN_DOC="$2"
        HAS_PLAN=1
        shift 2
        ;;
      -doing)
        HAS_DOING=1
        shift
        ;;
      -task-list)
        HAS_TASK_LIST=1
        shift
        ;;
      -plan-list)
        HAS_PLAN_LIST=1
        shift
        ;;
      -auto)
        HAS_AUTO=1
        shift
        ;;
      -log=*)
        LOG_FILE="${1#*=}"
        HAS_LOG=1
        shift
        ;;
      -log)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -log"
        LOG_FILE="$2"
        HAS_LOG=1
        shift 2
        ;;
      -h|--help)
        usage
        exit "$RC_OK"
        ;;
      *)
        if [[ "$HAS_FILE" -eq 0 && "$1" != -* ]]; then
          FILE="$1"
          HAS_FILE=1
          shift
        else
          err "$RC_ARG" "unknown argument: $1"
        fi
        ;;
    esac
  done

  [[ "$HAS_FILE" -eq 1 ]] || err "$RC_ARG" "missing required argument: -file"
  [[ -n "$(trim "$FILE")" ]] || err "$RC_ARG" "empty value for -file"

  local op_count=$((OP_DISPATCH + OP_DONE + OP_PAUSE + OP_CONTINUE + OP_REASSIGN + OP_NEXT + OP_NEW + OP_STATUS))
  op_count=$((op_count + OP_DELETE + OP_DONE_PLAN))
  [[ "$op_count" -eq 1 ]] || err "$RC_ARG" "exactly one operation is required: -dispatch|-done|-pause|-continue|-reassign|-next|-new|-status|-delete|-done-plan"

  if [[ "$OP_DISPATCH" -eq 1 ]]; then
    [[ "$HAS_TASK_ID" -eq 1 ]] || err "$RC_ARG" "-dispatch requires -task_id"
    [[ "$HAS_AGENTS_LIST" -eq 1 ]] || err "$RC_ARG" "-dispatch requires -agents-list"
    [[ -n "$(trim "$TASK_ID")" ]] || err "$RC_ARG" "empty value for -task_id"
    if [[ "$HAS_TYPE" -eq 1 ]]; then
      [[ -n "$(trim "$TYPE_KIND")" ]] || err "$RC_ARG" "empty value for -type"
      TYPE_KIND="$(validate_type_kind "$TYPE_KIND")"
    fi
    if [[ "$HAS_TO" -eq 1 ]]; then
      [[ -n "$(trim "$TO")" ]] || err "$RC_ARG" "empty value for -to"
    fi
    [[ -n "$(trim "$AGENTS_LIST")" ]] || err "$RC_ARG" "empty value for -agents-list"
    if [[ "$HAS_MESSAGE" -eq 1 ]]; then
      [[ -n "$(trim "$MESSAGE")" ]] || err "$RC_ARG" "empty value for -message"
    fi
    [[ "$HAS_INFO" -eq 0 && "$HAS_LOG" -eq 0 && "$HAS_FROM" -eq 0 && "$HAS_WORKTREE" -eq 0 && "$HAS_DEPENDS" -eq 0 && "$HAS_PLAN" -eq 0 ]] || err "$RC_ARG" "-dispatch does not accept -info/-log/-from/-worktree/-depends/-plan"
  fi

  if [[ "$OP_DONE" -eq 1 ]]; then
    [[ "$HAS_TASK_ID" -eq 1 ]] || err "$RC_ARG" "-done requires -task_id"
    [[ "$HAS_LOG" -eq 1 ]] || err "$RC_ARG" "-done requires -log"
    [[ "$HAS_AGENTS_LIST" -eq 1 ]] || err "$RC_ARG" "-done requires -agents-list"
    [[ -n "$(trim "$TASK_ID")" ]] || err "$RC_ARG" "empty value for -task_id"
    [[ -n "$(trim "$LOG_FILE")" ]] || err "$RC_ARG" "empty value for -log"
    [[ -n "$(trim "$AGENTS_LIST")" ]] || err "$RC_ARG" "empty value for -agents-list"
    [[ "$HAS_TO" -eq 0 && "$HAS_INFO" -eq 0 && "$HAS_FROM" -eq 0 && "$HAS_WORKTREE" -eq 0 && "$HAS_MESSAGE" -eq 0 && "$HAS_TYPE" -eq 0 && "$HAS_DEPENDS" -eq 0 && "$HAS_PLAN" -eq 0 ]] || err "$RC_ARG" "-done does not accept -to/-info/-from/-worktree/-message/-type/-depends/-plan"
  fi

  if [[ "$OP_PAUSE" -eq 1 ]]; then
    [[ "$HAS_TASK_ID" -eq 1 ]] || err "$RC_ARG" "-pause requires -task_id"
    [[ "$HAS_AGENTS_LIST" -eq 1 ]] || err "$RC_ARG" "-pause requires -agents-list"
    [[ -n "$(trim "$TASK_ID")" ]] || err "$RC_ARG" "empty value for -task_id"
    [[ -n "$(trim "$AGENTS_LIST")" ]] || err "$RC_ARG" "empty value for -agents-list"
    [[ "$HAS_TO" -eq 0 && "$HAS_INFO" -eq 0 && "$HAS_LOG" -eq 0 && "$HAS_FROM" -eq 0 && "$HAS_WORKTREE" -eq 0 && "$HAS_MESSAGE" -eq 0 && "$HAS_TYPE" -eq 0 && "$HAS_DEPENDS" -eq 0 && "$HAS_PLAN" -eq 0 ]] || err "$RC_ARG" "-pause does not accept -to/-info/-log/-from/-worktree/-message/-type/-depends/-plan"
  fi

  if [[ "$OP_CONTINUE" -eq 1 ]]; then
    [[ "$HAS_TASK_ID" -eq 1 ]] || err "$RC_ARG" "-continue requires -task_id"
    [[ "$HAS_AGENTS_LIST" -eq 1 ]] || err "$RC_ARG" "-continue requires -agents-list"
    [[ -n "$(trim "$TASK_ID")" ]] || err "$RC_ARG" "empty value for -task_id"
    [[ -n "$(trim "$AGENTS_LIST")" ]] || err "$RC_ARG" "empty value for -agents-list"
    [[ "$HAS_TO" -eq 0 && "$HAS_INFO" -eq 0 && "$HAS_LOG" -eq 0 && "$HAS_FROM" -eq 0 && "$HAS_WORKTREE" -eq 0 && "$HAS_MESSAGE" -eq 0 && "$HAS_TYPE" -eq 0 && "$HAS_DEPENDS" -eq 0 && "$HAS_PLAN" -eq 0 ]] || err "$RC_ARG" "-continue does not accept -to/-info/-log/-from/-worktree/-message/-type/-depends/-plan"
  fi

  if [[ "$OP_REASSIGN" -eq 1 ]]; then
    [[ "$HAS_TASK_ID" -eq 1 ]] || err "$RC_ARG" "-reassign requires -task_id"
    [[ "$HAS_TO" -eq 1 ]] || err "$RC_ARG" "-reassign requires -to"
    [[ "$HAS_AGENTS_LIST" -eq 1 ]] || err "$RC_ARG" "-reassign requires -agents-list"
    [[ -n "$(trim "$TASK_ID")" ]] || err "$RC_ARG" "empty value for -task_id"
    [[ -n "$(trim "$TO")" ]] || err "$RC_ARG" "empty value for -to"
    [[ -n "$(trim "$AGENTS_LIST")" ]] || err "$RC_ARG" "empty value for -agents-list"
    [[ "$HAS_INFO" -eq 0 && "$HAS_LOG" -eq 0 && "$HAS_FROM" -eq 0 && "$HAS_WORKTREE" -eq 0 && "$HAS_MESSAGE" -eq 0 && "$HAS_TYPE" -eq 0 && "$HAS_DEPENDS" -eq 0 && "$HAS_PLAN" -eq 0 ]] || err "$RC_ARG" "-reassign does not accept -info/-log/-from/-worktree/-message/-type/-depends/-plan"
  fi

  if [[ "$OP_NEXT" -eq 1 ]]; then
    [[ "$HAS_TASK_ID" -eq 1 ]] || err "$RC_ARG" "-next requires -task_id"
    [[ "$HAS_FROM" -eq 1 ]] || err "$RC_ARG" "-next requires -from"
    [[ "$HAS_TYPE" -eq 1 ]] || err "$RC_ARG" "-next requires -type"
    [[ "$HAS_MESSAGE" -eq 1 ]] || err "$RC_ARG" "-next requires -message"
    [[ "$HAS_AGENTS_LIST" -eq 1 ]] || err "$RC_ARG" "-next requires -agents-list"
    [[ -n "$(trim "$TASK_ID")" ]] || err "$RC_ARG" "empty value for -task_id"
    [[ -n "$(trim "$FROM")" ]] || err "$RC_ARG" "empty value for -from"
    [[ -n "$(trim "$TYPE_KIND")" ]] || err "$RC_ARG" "empty value for -type"
    TYPE_KIND="$(validate_type_kind "$TYPE_KIND")"
    [[ -n "$(trim "$MESSAGE")" ]] || err "$RC_ARG" "empty value for -message"
    [[ -n "$(trim "$AGENTS_LIST")" ]] || err "$RC_ARG" "empty value for -agents-list"
    if [[ "$HAS_TO" -eq 1 ]]; then
      [[ -n "$(trim "$TO")" ]] || err "$RC_ARG" "empty value for -to"
    fi
    [[ ! ( "$HAS_TO" -eq 1 && "$HAS_AUTO" -eq 1 ) ]] || err "$RC_ARG" "-next cannot combine -to and -auto"
    [[ "$HAS_INFO" -eq 0 && "$HAS_LOG" -eq 0 && "$HAS_WORKTREE" -eq 0 && "$HAS_DOING" -eq 0 && "$HAS_TASK_LIST" -eq 0 && "$HAS_PLAN_LIST" -eq 0 && "$HAS_DEPENDS" -eq 0 && "$HAS_PLAN" -eq 0 ]] || err "$RC_ARG" "-next does not accept -info/-log/-worktree/-doing/-task-list/-plan-list/-depends/-plan"
  fi

  if [[ "$HAS_AUTO" -eq 1 && "$OP_NEXT" -eq 0 ]]; then
    err "$RC_ARG" "-auto only supports -next"
  fi

  if [[ "$OP_NEW" -eq 1 ]]; then
    [[ "$HAS_INFO" -eq 1 ]] || err "$RC_ARG" "-new requires -info"
    [[ "$HAS_TYPE" -eq 1 ]] || err "$RC_ARG" "-new requires -type"
    [[ "$HAS_WORKTREE" -eq 1 ]] || err "$RC_ARG" "-new requires -worktree"
    [[ "$HAS_DEPENDS" -eq 1 ]] || err "$RC_ARG" "-new requires -depends"
    [[ "$HAS_PLAN" -eq 1 ]] || err "$RC_ARG" "-new requires -plan"
    [[ -n "$(trim "$INFO")" ]] || err "$RC_ARG" "empty value for -info"
    [[ -n "$(trim "$TYPE_KIND")" ]] || err "$RC_ARG" "empty value for -type"
    TYPE_KIND="$(validate_type_kind "$TYPE_KIND")"
    [[ -n "$(trim "$WORKTREE")" ]] || err "$RC_ARG" "empty value for -worktree"
    [[ "$(trim "$WORKTREE" | tr '[:upper:]' '[:lower:]')" != "none" ]] || err "$RC_ARG" "-new requires non-None value for -worktree"
    if [[ "$HAS_TO" -eq 1 ]]; then
      [[ -n "$(trim "$TO")" ]] || err "$RC_ARG" "empty value for -to"
    fi
    if [[ "$HAS_FROM" -eq 1 ]]; then
      [[ -n "$(trim "$FROM")" ]] || err "$RC_ARG" "empty value for -from"
    fi
    [[ -n "$(trim "$DEPENDS")" ]] || err "$RC_ARG" "empty value for -depends"
    [[ -n "$(trim "$PLAN_DOC")" ]] || err "$RC_ARG" "empty value for -plan"
    [[ "$HAS_TASK_ID" -eq 0 ]] || err "$RC_ARG" "-new does not accept -task_id"
    [[ "$HAS_MESSAGE" -eq 0 ]] || err "$RC_ARG" "-new does not accept -message"
    [[ "$HAS_AGENTS_LIST" -eq 0 ]] || err "$RC_ARG" "-new does not accept -agents-list"
    [[ "$HAS_DOING" -eq 0 && "$HAS_TASK_LIST" -eq 0 && "$HAS_PLAN_LIST" -eq 0 ]] || err "$RC_ARG" "-new does not accept -doing/-task-list/-plan-list"
  fi

  if [[ "$OP_STATUS" -eq 1 ]]; then
    [[ "$HAS_TASK_ID" -eq 0 && "$HAS_TO" -eq 0 && "$HAS_FROM" -eq 0 && "$HAS_INFO" -eq 0 && "$HAS_LOG" -eq 0 && "$HAS_WORKTREE" -eq 0 && "$HAS_AGENTS_LIST" -eq 0 && "$HAS_MESSAGE" -eq 0 && "$HAS_TYPE" -eq 0 && "$HAS_DEPENDS" -eq 0 && "$HAS_PLAN" -eq 0 ]] || err "$RC_ARG" "-status does not accept -task_id/-to/-from/-info/-log/-worktree/-agents-list/-message/-type/-depends/-plan"
    local status_count=$((HAS_DOING + HAS_TASK_LIST + HAS_PLAN_LIST))
    [[ "$status_count" -eq 1 ]] || err "$RC_ARG" "-status requires exactly one of -doing/-task-list/-plan-list"
  fi

  if [[ "$OP_DELETE" -eq 1 ]]; then
    [[ "$HAS_TASK_ID" -eq 1 ]] || err "$RC_ARG" "-delete requires -task_id"
    [[ -n "$(trim "$TASK_ID")" ]] || err "$RC_ARG" "empty value for -task_id"
    [[ "$HAS_TO" -eq 0 && "$HAS_INFO" -eq 0 && "$HAS_LOG" -eq 0 && "$HAS_FROM" -eq 0 && "$HAS_WORKTREE" -eq 0 && "$HAS_MESSAGE" -eq 0 && "$HAS_AGENTS_LIST" -eq 0 && "$HAS_DOING" -eq 0 && "$HAS_TASK_LIST" -eq 0 && "$HAS_PLAN_LIST" -eq 0 && "$HAS_TYPE" -eq 0 && "$HAS_DEPENDS" -eq 0 && "$HAS_PLAN" -eq 0 ]] || err "$RC_ARG" "-delete does not accept -to/-info/-log/-from/-worktree/-message/-agents-list/-doing/-task-list/-plan-list/-type/-depends/-plan"
  fi

  if [[ "$OP_DONE_PLAN" -eq 1 ]]; then
    [[ "$HAS_PLAN" -eq 1 ]] || err "$RC_ARG" "-done-plan requires -plan"
    [[ -n "$(trim "$PLAN_DOC")" ]] || err "$RC_ARG" "empty value for -plan"
    [[ "$HAS_TASK_ID" -eq 0 && "$HAS_TO" -eq 0 && "$HAS_INFO" -eq 0 && "$HAS_LOG" -eq 0 && "$HAS_FROM" -eq 0 && "$HAS_WORKTREE" -eq 0 && "$HAS_MESSAGE" -eq 0 && "$HAS_AGENTS_LIST" -eq 0 && "$HAS_DOING" -eq 0 && "$HAS_TASK_LIST" -eq 0 && "$HAS_PLAN_LIST" -eq 0 && "$HAS_TYPE" -eq 0 && "$HAS_DEPENDS" -eq 0 ]] || err "$RC_ARG" "-done-plan does not accept -task_id/-to/-info/-log/-from/-worktree/-message/-agents-list/-doing/-task-list/-plan-list/-type/-depends"
  fi
}

read_config_value() {
  local config_file="$1"
  local key="$2"

  [[ -f "$config_file" ]] || return 1
  python3 - "$config_file" "$key" <<'PY'
import sys

path = sys.argv[1]
key = sys.argv[2]

with open(path, "r", encoding="utf-8") as fh:
    for raw in fh:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        lhs, rhs = line.split("=", 1)
        if lhs.strip() != key:
            continue
        print(rhs.strip())
        break
PY
}

resolve_dispatch_sender() {
  local from_name="${CODEX_MULTI_AGENTS_ROOT_NAME-}"
  if [[ -n "$(trim "$from_name")" ]]; then
    printf "%s" "$from_name"
    return 0
  fi

  from_name="$(read_config_value "${CODEX_MULTI_AGENTS_CONFIG:-$DEFAULT_CONFIG_FILE}" "ROOT_NAME" || true)"
  if [[ -n "$(trim "$from_name")" ]]; then
    printf "%s" "$from_name"
    return 0
  fi

  printf "scheduler"
}

resolve_operator_name() {
  local operator_name="${CODEX_MULTI_AGENTS_ROOT_NAME-}"
  if [[ -n "$(trim "$operator_name")" ]]; then
    printf "%s" "$operator_name"
    return 0
  fi

  operator_name="$(read_config_value "${CODEX_MULTI_AGENTS_CONFIG:-$DEFAULT_CONFIG_FILE}" "ROOT_NAME" || true)"
  printf "%s" "$operator_name"
}

resolve_default_agents_file() {
  local from_env="${CODEX_MULTI_AGENTS_AGENTS_FILE-}"
  if [[ -n "$(trim "$from_env")" ]]; then
    printf "%s" "$from_env"
    return 0
  fi

  local from_cfg=""
  from_cfg="$(read_config_value "${CODEX_MULTI_AGENTS_CONFIG:-$DEFAULT_CONFIG_FILE}" "AGENTS_FILE" || true)"
  if [[ -n "$(trim "$from_cfg")" ]]; then
    printf "%s" "$from_cfg"
    return 0
  fi

  local fallback="${REPO_ROOT}/agents/codex-multi-agents/agents-lists.md"
  if [[ -f "$fallback" ]]; then
    printf "%s" "$fallback"
    return 0
  fi

  printf ""
}

resolve_permission_agents_file() {
  local from_env="${CODEX_MULTI_AGENTS_PERMISSION_AGENTS_FILE-}"
  if [[ -n "$(trim "$from_env")" ]]; then
    printf "%s" "$from_env"
    return 0
  fi

  local from_default=""
  from_default="$(resolve_default_agents_file)"
  if [[ -n "$(trim "$from_default")" ]]; then
    printf "%s" "$from_default"
    return 0
  fi

  printf "%s" "${1-}"
}

run_task_notify() {
  [[ -f "$TASK_NOTIFY_SCRIPT" ]] || err "$RC_FILE" "notify script not found: $TASK_NOTIFY_SCRIPT"
  bash "$TASK_NOTIFY_SCRIPT" "$@"
}

resolve_admin_name() {
  local from_env="${CODEX_MULTI_AGENTS_ADMIN_USERS-}"
  if [[ -n "$(trim "$from_env")" ]]; then
    from_env="${from_env%%,*}"
    from_env="$(trim "$from_env")"
    if [[ -n "$from_env" ]]; then
      printf "%s" "$from_env"
      return 0
    fi
  fi

  python3 - "$AGENTS_LIST" <<'PY'
import sys

path = sys.argv[1]

def is_pipe_row(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("|") and stripped.endswith("|")

def split_row(text: str) -> list[str]:
    stripped = text.strip()
    return [cell.strip() for cell in stripped[1:-1].split("|")]

try:
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.read().splitlines()
except OSError:
    print("神秘人")
    raise SystemExit(0)

for index in range(len(lines) - 1):
    if not (is_pipe_row(lines[index]) and is_pipe_row(lines[index + 1])):
        continue
    header = split_row(lines[index])
    if "姓名" not in header:
        continue
    name_idx = header.index("姓名")
    intro_idx = header.index("介绍") if "介绍" in header else -1
    duty_idx = header.index("职责") if "职责" in header else -1
    row_index = index + 2
    while row_index < len(lines) and is_pipe_row(lines[row_index]):
        row = split_row(lines[row_index])
        intro = row[intro_idx] if intro_idx >= 0 and intro_idx < len(row) else ""
        duty = row[duty_idx] if duty_idx >= 0 and duty_idx < len(row) else ""
        if "管理员" in f"{intro} {duty}":
            print(row[name_idx])
            raise SystemExit(0)
        row_index += 1

print("神秘人")
PY
}

read_running_assignee() {
  local todo_file="$1"
  local target_task_id="$2"

  python3 - "$todo_file" "$target_task_id" <<'PY'
import sys

todo_file = sys.argv[1]
task_id = sys.argv[2]

def is_pipe_row(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("|") and stripped.endswith("|")

def split_row(text: str) -> list[str]:
    stripped = text.strip()
    return [cell.strip() for cell in stripped[1:-1].split("|")]

with open(todo_file, "r", encoding="utf-8") as fh:
    lines = fh.read().splitlines()

section_start = -1
for index, line in enumerate(lines):
    if line.strip() == "## 正在执行的任务":
        section_start = index
        break

if section_start < 0:
    raise SystemExit(0)

section_end = len(lines)
for index in range(section_start + 1, len(lines)):
    if lines[index].startswith("## "):
        section_end = index
        break

for index in range(section_start + 1, section_end):
    if not is_pipe_row(lines[index]):
        continue
    row = split_row(lines[index])
    if row and row[0] == task_id and len(row) >= 9:
        print(row[8])
        raise SystemExit(0)
PY
}

validate_todo_file() {
  [[ -e "$FILE" ]] || err "$RC_FILE" "file not found: $FILE"
  [[ -f "$FILE" ]] || err "$RC_FILE" "not a regular file: $FILE"
  [[ -r "$FILE" ]] || err "$RC_FILE" "file is not readable: $FILE"
}

acquire_lock_on_file() {
  local path="$1"
  local __fd_var="$2"

  [[ -e "$path" ]] || err "$RC_FILE" "file not found: $path"
  [[ -f "$path" ]] || err "$RC_FILE" "not a regular file: $path"
  [[ -r "$path" ]] || err "$RC_FILE" "file is not readable: $path"

  local fd
  exec {fd}< "$path" || err "$RC_LOCK" "cannot open file for lock: $path"
  flock -x -w 5 "$fd" || err "$RC_LOCK" "cannot acquire lock on file: $path"
  printf -v "$__fd_var" '%s' "$fd"
}

release_lock_fd() {
  local fd="${1-}"
  [[ -n "$fd" ]] || return 0
  eval "exec ${fd}<&-"
}

run_python_core() {
  local op="$1"
  local todo_file="$2"
  local task_id="$3"
  local to="$4"
  local info="$5"
  local log_file="$6"
  local from="$7"
  local worktree="$8"
  local message="$9"
  local type_kind="${10}"
  local depends="${11}"
  local plan_doc="${12}"
  local done_file="${13}"
  local agents_file="${14}"
  local operator_name="${15}"
  local permission_agents_file="${16}"
  local max_parallel_agents="${17}"
  local auto_flag="${18}"
  [[ -f "$TASK_CORE_SCRIPT" ]] || err "$RC_FILE" "task core script not found: $TASK_CORE_SCRIPT"
  python3 "$TASK_CORE_SCRIPT" \
    "$op" "$todo_file" "$task_id" "$to" "$info" "$log_file" "$from" "$worktree" "$message" \
    "$type_kind" "$depends" "$plan_doc" "$done_file" "$agents_file" "$operator_name" \
    "$permission_agents_file" "$max_parallel_agents" "$auto_flag"
}

main() {
  parse_args "$@"
  validate_todo_file
  validate_parallel_limit

  local op=""
  local done_file=""
  local done_lock_fd=""
  local agents_lock_fd=""
  local operator_name=""
  local permission_agents_file=""
  local next_sender=""
  local admin_name=""
  local auto_flag="0"
  local -a auto_next_dispatches=()
  local reassign_old_assignee=""
  local reassign_new_assignee=""
  local visible_output=""
  local core_output=""
  local rc=0

  if [[ "$OP_DISPATCH" -eq 1 ]]; then
    op="dispatch"
  elif [[ "$OP_DONE" -eq 1 ]]; then
    op="done"
  elif [[ "$OP_PAUSE" -eq 1 ]]; then
    op="pause"
  elif [[ "$OP_CONTINUE" -eq 1 ]]; then
    op="continue"
  elif [[ "$OP_REASSIGN" -eq 1 ]]; then
    op="reassign"
  elif [[ "$OP_NEXT" -eq 1 ]]; then
    op="next"
  elif [[ "$OP_NEW" -eq 1 ]]; then
    op="new"
  elif [[ "$OP_STATUS" -eq 1 ]]; then
    if [[ "$HAS_DOING" -eq 1 ]]; then
      op="status-doing"
    elif [[ "$HAS_TASK_LIST" -eq 1 ]]; then
      op="status-task-list"
    else
      op="status-plan-list"
    fi
  elif [[ "$OP_DELETE" -eq 1 ]]; then
    op="delete"
  elif [[ "$OP_DONE_PLAN" -eq 1 ]]; then
    op="done-plan"
  else
    err "$RC_INTERNAL" "unexpected operation state"
  fi

  if [[ "$HAS_AUTO" -eq 1 ]]; then
    auto_flag="1"
  fi

  if [[ "$op" == "status-doing" || "$op" == "status-task-list" || "$op" == "status-plan-list" ]]; then
    run_python_core "$op" "$FILE" "" "" "" "" "" "" "" "" "" "" "" "" "" "" "$MAX_PARALLEL_AGENTS" "0"
    rc=$?
    exit "$rc"
  fi

  if [[ "$op" == "new" || "$op" == "dispatch" || "$op" == "done" || "$op" == "done-plan" ]]; then
    operator_name="$(resolve_operator_name)"
    if [[ "$op" == "new" || "$op" == "dispatch" || "$op" == "done" || "$op" == "done-plan" ]]; then
      [[ -n "$(trim "$operator_name")" ]] || err "$RC_ARG" "cannot resolve operator identity; set CODEX_MULTI_AGENTS_ROOT_NAME or ROOT_NAME in config"
      permission_agents_file="$(resolve_permission_agents_file "$AGENTS_LIST")"
      [[ -n "$(trim "$permission_agents_file")" ]] || err "$RC_ARG" "cannot resolve permission agents list; set CODEX_MULTI_AGENTS_PERMISSION_AGENTS_FILE or AGENTS_FILE"
    fi
  fi

  if [[ "$op" == "next" ]]; then
    next_sender="$(trim "$FROM")"
    operator_name="$next_sender"
    admin_name="$(trim "$(resolve_admin_name)")"
  fi

  local todo_lock_fd=""
  acquire_lock_on_file "$FILE" todo_lock_fd

  if [[ "$op" == "done" ]]; then
    done_file="$(dirname "$FILE")/DONE.md"
    if [[ ! -e "$done_file" ]]; then
      : > "$done_file" || err "$RC_FILE" "failed to create done file: $done_file"
    fi
    acquire_lock_on_file "$done_file" done_lock_fd
  fi

  if [[ "$op" == "dispatch" || "$op" == "done" || "$op" == "pause" || "$op" == "continue" || "$op" == "reassign" || "$op" == "next" ]]; then
    acquire_lock_on_file "$AGENTS_LIST" agents_lock_fd
  fi

  if [[ "$op" == "dispatch" ]]; then
    release_lock_fd "$agents_lock_fd"
    release_lock_fd "$todo_lock_fd"
    run_task_notify -dispatch-init -agents-list "$AGENTS_LIST" -to "$TO"
    acquire_lock_on_file "$FILE" todo_lock_fd
    acquire_lock_on_file "$AGENTS_LIST" agents_lock_fd
  fi

  core_output="$(run_python_core "$op" "$FILE" "$TASK_ID" "$TO" "$INFO" "$LOG_FILE" "$FROM" "$WORKTREE" "$MESSAGE" "$TYPE_KIND" "$DEPENDS" "$PLAN_DOC" "$done_file" "$AGENTS_LIST" "$operator_name" "$permission_agents_file" "$MAX_PARALLEL_AGENTS" "$auto_flag")"
  rc=$?
  if [[ "$rc" -ne 0 ]]; then
    exit "$rc"
  fi

  if [[ "$op" == "next" ]]; then
    local -a auto_markers=()
    visible_output="$(printf "%s\n" "$core_output" | grep -v '^__AUTO_NEXT__=' || true)"
    mapfile -t auto_markers < <(printf "%s\n" "$core_output" | grep '^__AUTO_NEXT__=' || true)
    for auto_marker in "${auto_markers[@]}"; do
      [[ "$auto_marker" == "__AUTO_NEXT__=none" ]] && continue
      local auto_payload="${auto_marker#__AUTO_NEXT__=}"
      local marker_kind=""
      local marker_task_id=""
      local marker_assignee=""
      IFS='|' read -r marker_kind marker_task_id marker_assignee <<<"$auto_payload"
      [[ "$marker_kind" == "dispatch" ]] || continue
      auto_next_dispatches+=("${marker_task_id}|${marker_assignee}")
    done
  elif [[ "$op" == "reassign" ]]; then
    local reassign_marker=""
    reassign_marker="$(printf "%s\n" "$core_output" | grep '^__REASSIGN__=' || true)"
    visible_output="$(printf "%s\n" "$core_output" | grep -v '^__REASSIGN__=' || true)"
    if [[ -n "$reassign_marker" ]]; then
      local reassign_payload="${reassign_marker#__REASSIGN__=}"
      IFS='|' read -r reassign_old_assignee reassign_new_assignee <<<"$reassign_payload"
    fi
  else
    visible_output="$core_output"
  fi

  [[ -z "$visible_output" ]] || printf "%s\n" "$visible_output"

  if [[ "$op" == "dispatch" ]]; then
    release_lock_fd "$agents_lock_fd"
    release_lock_fd "$todo_lock_fd"
    local notify_args=(
      -dispatch-message
      -file "$FILE"
      -task_id "$TASK_ID"
      -to "$TO"
      -from "$(resolve_dispatch_sender)"
      -agents-list "$AGENTS_LIST"
    )
    if [[ "$HAS_MESSAGE" -eq 1 ]]; then
      notify_args+=(-message "$MESSAGE")
    fi
    run_task_notify "${notify_args[@]}"
    local talk_rc=$?
    if [[ "$talk_rc" -ne 0 ]]; then
      printf "ERROR(%s): dispatch succeeded but message delivery failed for task %s; retry codex-multi-agents-tmux.sh -talk only\n" "$talk_rc" "$TASK_ID" >&2
      exit "$talk_rc"
    fi
    return 0
  fi

  if [[ "$op" == "next" ]]; then
    release_lock_fd "$agents_lock_fd"
    release_lock_fd "$todo_lock_fd"
    local next_notify_args=(
      -next
      -file "$FILE"
      -task_id "$TASK_ID"
      -type "$TYPE_KIND"
      -agents-list "$AGENTS_LIST"
      -from "$next_sender"
      -admin "$admin_name"
    )
    for auto_dispatch in "${auto_next_dispatches[@]}"; do
      next_notify_args+=(-auto-dispatch "$auto_dispatch")
    done
    run_task_notify "${next_notify_args[@]}"
    return 0
  fi

  if [[ "$op" == "reassign" ]]; then
    release_lock_fd "$agents_lock_fd"
    release_lock_fd "$todo_lock_fd"
    run_task_notify \
      -reassign \
      -file "$FILE" \
      -task_id "$TASK_ID" \
      -to "${reassign_new_assignee:-$TO}" \
      -old-assignee "$reassign_old_assignee" \
      -from "$(resolve_dispatch_sender)" \
      -agents-list "$AGENTS_LIST"
    return 0
  fi

  release_lock_fd "$agents_lock_fd"
  release_lock_fd "$done_lock_fd"
  release_lock_fd "$todo_lock_fd"
}

main "$@"
