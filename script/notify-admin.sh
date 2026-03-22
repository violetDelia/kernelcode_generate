#!/usr/bin/env bash
# notify-admin.sh
#
# 创建者: Codex
# 最后修改人: 榕
#
# 功能说明:
# - 按脚本顶部配置定时向管理员发送会话消息。
# - 定时频率、管理员信息、日志路径和消息内容都可直接在本文件顶部修改。
# - 修改本文件后，重新启动脚本即可生效。
#
# 使用示例:
# - 使用当前配置运行: script/notify-admin.sh
#
# 对应文件:
# - spec: /home/lfr/kernelcode_generate/spec/script/notify-admin.md
# - test: /home/lfr/kernelcode_generate/test/script/test_notify_admin.py
# - 功能实现: /home/lfr/kernelcode_generate/script/notify-admin.sh

set -u
set -o pipefail

readonly RC_OK=0
readonly RC_ARG=1
readonly RC_FILE=2
readonly RC_DATA=3
readonly RC_INTERNAL=5

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMUX_SCRIPT="$SCRIPT_DIR/../skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh"

# -----------------------------
# 可直接修改的配置区
# -----------------------------
INTERVAL_SECONDS=1800
FROM_NAME="榕"
TO_NAME="神秘人"
SESSION_ID="神秘人"
LOG_FILE="./agents/codex-multi-agents/log/talk.log"

# 多行消息直接写在 MESSAGE 变量里。
read -r -d '' MESSAGE <<'EOF' || true
推进任务，直到任务全部完成。
EOF

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
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
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

validate_config() {
  [[ -n "$INTERVAL_SECONDS" ]] || err "$RC_DATA" "INTERVAL_SECONDS is required"
  [[ "$INTERVAL_SECONDS" =~ ^[0-9]+$ ]] || err "$RC_DATA" "INTERVAL_SECONDS must be a positive integer"
  [[ "$INTERVAL_SECONDS" -gt 0 ]] || err "$RC_DATA" "INTERVAL_SECONDS must be greater than 0"
  [[ -n "$FROM_NAME" ]] || err "$RC_DATA" "FROM_NAME is required"
  [[ -n "$TO_NAME" ]] || err "$RC_DATA" "TO_NAME is required"
  [[ -n "$SESSION_ID" ]] || err "$RC_DATA" "SESSION_ID is required"
  [[ -n "$LOG_FILE" ]] || err "$RC_DATA" "LOG_FILE is required"
  [[ -n "$MESSAGE" ]] || err "$RC_DATA" "MESSAGE is required"

  [[ -x "$TMUX_SCRIPT" ]] || err "$RC_FILE" "tmux script is not executable: $TMUX_SCRIPT"
}

send_once() {
  bash "$TMUX_SCRIPT" \
    -talk \
    -from "$FROM_NAME" \
    -to "$TO_NAME" \
    -session-id "$SESSION_ID" \
    -message "$MESSAGE" \
    -log "$LOG_FILE"
}

main_loop() {
  while true; do
    validate_config
    send_once
    sleep "$INTERVAL_SECONDS" || err "$RC_INTERNAL" "sleep failed"
  done
}

main() {
  parse_args "$@"
  main_loop
}

main "$@"
