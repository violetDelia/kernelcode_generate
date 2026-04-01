#!/usr/bin/env bash
# notify-admin.sh
#
# 创建者: Codex
# 最后修改人: 榕
#
# 功能说明:
# - 按脚本顶部配置定时向管理员发送会话消息。
# - 定时频率、管理员信息、日志路径和消息内容都直接维护在本文件顶部。
# - 修改本文件后，重新启动脚本即可生效。
#
# 使用示例:
# - 使用当前配置运行: script/notify-admin.sh
#
# 对应文件:
# - spec: spec/script/notify-admin.md
# - test: test/script/test_notify_admin.py
# - 功能实现: script/notify-admin.sh

set -u
set -o pipefail

readonly RC_OK=0
readonly RC_ARG=1
readonly RC_FILE=2
readonly RC_DATA=3
readonly RC_INTERNAL=5

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TMUX_SCRIPT="$REPO_ROOT/skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh"
LIST_SCRIPT="$REPO_ROOT/skills/codex-multi-agents/scripts/codex-multi-agents-list.sh"

# -----------------------------
# 可直接修改的配置区
# -----------------------------
# 每隔多久发送一次，单位秒。
INTERVAL_SECONDS=1800

# 会话发送信息。
FROM_NAME="榕"
TO_NAME="神秘人"
AGENTS_LIST_FILE="agents/codex-multi-agents/agents-lists.md"

# 支持相对路径；相对路径基于仓库根目录。
LOG_FILE="agents/codex-multi-agents/log/talk.log"

# 多行消息直接写在 MESSAGE 变量里。
read -r -d '' MESSAGE <<'EOF' || true
询问正在执行的任务并推进，分发任务列表给合适的人。更新6个计划书状态，有序推进所有任务（含计划书），注意不要再前置任务完成前开始后置任务，最快速度完成所有任务。
EOF

MODE="loop"

err() {
  local code="$1"
  shift
  printf "ERROR(%s): %s\n" "$code" "$*" >&2
  exit "$code"
}

usage() {
  cat <<'EOF'
Usage:
  notify-admin.sh
  notify-admin.sh -init
EOF
}

log_path() {
  local input_path="$1"
  if [[ "$input_path" = /* ]]; then
    printf '%s\n' "$input_path"
    return
  fi
  printf '%s/%s\n' "$REPO_ROOT" "$input_path"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -init)
        MODE="init"
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
}

validate_common_config() {
  [[ -n "$TO_NAME" ]] || err "$RC_DATA" "TO_NAME is required"
  [[ -n "$AGENTS_LIST_FILE" ]] || err "$RC_DATA" "AGENTS_LIST_FILE is required"
  [[ -f "$(log_path "$AGENTS_LIST_FILE")" ]] || err "$RC_FILE" "agents list not found: $(log_path "$AGENTS_LIST_FILE")"
}

validate_init_config() {
  validate_common_config
  [[ -x "$LIST_SCRIPT" ]] || err "$RC_FILE" "list script is not executable: $LIST_SCRIPT"
}

validate_loop_config() {
  validate_common_config
  [[ -n "$INTERVAL_SECONDS" ]] || err "$RC_DATA" "INTERVAL_SECONDS is required"
  [[ "$INTERVAL_SECONDS" =~ ^[0-9]+$ ]] || err "$RC_DATA" "INTERVAL_SECONDS must be a positive integer"
  [[ "$INTERVAL_SECONDS" -gt 0 ]] || err "$RC_DATA" "INTERVAL_SECONDS must be greater than 0"
  [[ -n "$FROM_NAME" ]] || err "$RC_DATA" "FROM_NAME is required"
  [[ -n "$LOG_FILE" ]] || err "$RC_DATA" "LOG_FILE is required"
  [[ -n "$MESSAGE" ]] || err "$RC_DATA" "MESSAGE is required"

  [[ -x "$TMUX_SCRIPT" ]] || err "$RC_FILE" "tmux script is not executable: $TMUX_SCRIPT"

  mkdir -p "$(dirname "$(log_path "$LOG_FILE")")" || err "$RC_FILE" "failed to create log directory"
}

cleanup() {
  exit "$RC_OK"
}

send_once() {
  bash "$TMUX_SCRIPT" \
    -talk \
    -from "$FROM_NAME" \
    -to "$TO_NAME" \
    -agents-list "$(log_path "$AGENTS_LIST_FILE")" \
    -message "$MESSAGE" \
    -log "$(log_path "$LOG_FILE")"
}

run_init() {
  validate_init_config
  bash "$LIST_SCRIPT" \
    -file "$(log_path "$AGENTS_LIST_FILE")" \
    -name "$TO_NAME"
}

main_loop() {
  while true; do
    validate_loop_config
    send_once
    sleep "$INTERVAL_SECONDS" || err "$RC_INTERNAL" "sleep failed"
  done
}

main() {
  parse_args "$@"
  trap cleanup INT TERM
  if [[ "$MODE" == "init" ]]; then
    run_init
    exit "$RC_OK"
  fi
  main_loop
}

main "$@"
