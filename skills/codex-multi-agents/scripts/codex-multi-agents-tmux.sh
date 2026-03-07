#!/usr/bin/env bash
# codex-multi-agents-tmux.sh
#
# 功能:
# - 基于 tmux 连接/创建会话。
# - 发送标准格式对话到目标会话并写入日志。
#
# 对应文件:
# - spec: spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md
# - test: test/codex-multi-agents/test_codex-multi-agents-tmux.py
# - impl: skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh

set -u
set -o pipefail

readonly RC_OK=0
readonly RC_ARG=1
readonly RC_FILE=2
readonly RC_DATA=3
readonly RC_LOCK=4
readonly RC_INTERNAL=5

FILE=""
OP_ATTACH=0
OP_TALK=0
SESSION=""
SESSION_ID=""
FROM=""
TO=""
MESSAGE=""
LOG_FILE=""
HAS_SESSION=0
HAS_SESSION_ID=0
HAS_FROM=0
HAS_TO=0
HAS_MESSAGE=0
HAS_LOG=0

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
  cat <<'EOF'
Usage:
  codex-multi-agents-tmux.sh -attach -s <session>
  codex-multi-agents-tmux.sh -talk -from <sender> -to <target_name> -session-id <target_session_id> -message <message> -log <log_path>

Examples:
  codex-multi-agents-tmux.sh -attach -s worker-a
  codex-multi-agents-tmux.sh -talk -from scheduler -to worker-a -session-id worker-a -message "请处理任务 T1" -log ./agents/codex-multi-agents/log/talk.log

Return codes:
  0 success
  1 argument error
  2 file or environment error
  3 data error
  4 lock error
  5 internal error
EOF
}

parse_args() {
  if [[ $# -eq 0 ]]; then
    usage
    err "$RC_ARG" "missing arguments"
  fi

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -attach)
        OP_ATTACH=1
        shift
        ;;
      -talk)
        OP_TALK=1
        shift
        ;;
      -s=*)
        SESSION="${1#*=}"
        HAS_SESSION=1
        shift
        ;;
      -s)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -s"
        SESSION="$2"
        HAS_SESSION=1
        shift 2
        ;;
      -from=*)
        FROM="${1#*=}"
        HAS_FROM=1
        shift
        ;;
      -session-id=*)
        SESSION_ID="${1#*=}"
        HAS_SESSION_ID=1
        shift
        ;;
      -session-id)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -session-id"
        SESSION_ID="$2"
        HAS_SESSION_ID=1
        shift 2
        ;;
      -from)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -from"
        FROM="$2"
        HAS_FROM=1
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
        err "$RC_ARG" "unknown argument: $1"
        ;;
    esac
  done

  local op_count=$((OP_ATTACH + OP_TALK))
  [[ "$op_count" -eq 1 ]] || err "$RC_ARG" "exactly one operation is required: -attach|-talk"

  if [[ "$OP_ATTACH" -eq 1 ]]; then
    [[ "$HAS_SESSION" -eq 1 ]] || err "$RC_ARG" "-attach requires -s"
    [[ -n "$(trim "$SESSION")" ]] || err "$RC_ARG" "empty value for -s"
    [[ "$HAS_FROM" -eq 0 && "$HAS_TO" -eq 0 && "$HAS_SESSION_ID" -eq 0 && "$HAS_MESSAGE" -eq 0 && "$HAS_LOG" -eq 0 ]] || err "$RC_ARG" "-attach does not accept -from/-to/-session-id/-message/-log"
  fi

  if [[ "$OP_TALK" -eq 1 ]]; then
    [[ "$HAS_FROM" -eq 1 ]] || err "$RC_ARG" "-talk requires -from"
    [[ "$HAS_TO" -eq 1 ]] || err "$RC_ARG" "-talk requires -to"
    [[ "$HAS_SESSION_ID" -eq 1 ]] || err "$RC_ARG" "-talk requires -session-id"
    [[ "$HAS_MESSAGE" -eq 1 ]] || err "$RC_ARG" "-talk requires -message"
    [[ "$HAS_LOG" -eq 1 ]] || err "$RC_ARG" "-talk requires -log"
    [[ -n "$(trim "$FROM")" ]] || err "$RC_ARG" "empty value for -from"
    [[ -n "$(trim "$TO")" ]] || err "$RC_ARG" "empty value for -to"
    [[ -n "$(trim "$SESSION_ID")" ]] || err "$RC_ARG" "empty value for -session-id"
    [[ -n "$(trim "$MESSAGE")" ]] || err "$RC_ARG" "empty value for -message"
    [[ -n "$(trim "$LOG_FILE")" ]] || err "$RC_ARG" "empty value for -log"
    [[ "$HAS_SESSION" -eq 0 ]] || err "$RC_ARG" "-talk does not accept -s"
  fi
}

ensure_tmux_available() {
  command -v tmux >/dev/null 2>&1 || err "$RC_FILE" "tmux not found in PATH"
}

tmux_has_session() {
  local target="$1"
  tmux has-session -t "$target" >/dev/null 2>&1
}

do_attach() {
  if tmux_has_session "$SESSION"; then
    tmux attach -t "$SESSION" || err "$RC_INTERNAL" "tmux attach failed: $SESSION"
    printf "OK: attach %s\n" "$SESSION"
    return
  fi

  tmux new -s "$SESSION" || err "$RC_INTERNAL" "tmux new failed: $SESSION"
  printf "OK: new %s\n" "$SESSION"
}

format_talk_message() {
  printf "@%s向@%s发起会话: %s" "$FROM" "$TO" "$MESSAGE"
}

acquire_log_lock() {
  local lock_file="${LOG_FILE}.lock"
  exec {lock_fd}> "$lock_file" || err "$RC_LOCK" "cannot open lock file: $lock_file"
  flock -x -w 5 "$lock_fd" || err "$RC_LOCK" "cannot acquire lock: $lock_file"
}

append_log_line() {
  local line="$1"
  local dir
  dir="$(dirname "$LOG_FILE")"
  mkdir -p "$dir" || err "$RC_FILE" "failed to create log directory: $dir"

  acquire_log_lock
  printf "%s\n" "$line" >> "$LOG_FILE" || err "$RC_INTERNAL" "failed to write log file: $LOG_FILE"
}

do_talk() {
  tmux_has_session "$SESSION_ID" || err "$RC_DATA" "target session not found: $SESSION_ID"

  local line
  line="$(format_talk_message)"
  tmux send-keys -t "$SESSION_ID" "$line" C-m || err "$RC_INTERNAL" "tmux send-keys failed: $SESSION_ID"
  append_log_line "$line"
  printf "OK: talk %s -> %s (%s)\n" "$FROM" "$TO" "$SESSION_ID"
}

main() {
  parse_args "$@"
  ensure_tmux_available

  if [[ "$OP_ATTACH" -eq 1 ]]; then
    do_attach
  elif [[ "$OP_TALK" -eq 1 ]]; then
    do_talk
  else
    err "$RC_INTERNAL" "unexpected operation state"
  fi
}

main "$@"
