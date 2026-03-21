#!/usr/bin/env bash
# codex-multi-agents-schedule-command.sh
#
# 创建者: Codex
# 最后修改人: Codex
#
# 功能说明:
# - 按固定时间间隔执行 shell 命令，默认执行 `mand`。
# - 支持限制执行次数，便于做一次性调度和自动化测试。
# - 支持将每次执行的标准输出与标准错误追加写入日志文件。
#
# 使用示例:
# - 默认执行一次 `mand`: codex-multi-agents-schedule-command.sh -interval 60 -count 1
# - 每 5 秒执行一次 `mand`，共执行 3 次: codex-multi-agents-schedule-command.sh -interval 5 -count 3
# - 每 10 秒执行一次自定义命令并写日志:
#   codex-multi-agents-schedule-command.sh -interval 10 -count 2 -command 'echo hello' -log-file ./schedule.log
#
# 对应文件:
# - spec: /home/lfr/kernelcode_generate/spec/codex-multi-agents/scripts/codex-multi-agents-schedule-command.md
# - test: /home/lfr/kernelcode_generate/test/codex-multi-agents/test_codex-multi-agents-schedule-command.py
# - 功能实现: /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-schedule-command.sh

set -u
set -o pipefail

readonly RC_OK=0
readonly RC_ARG=1
readonly RC_FILE=2
readonly RC_DATA=3
readonly RC_INTERNAL=5

COMMAND="mand"
INTERVAL=""
COUNT="0"
LOG_FILE=""
SHELL_BIN="${SHELL:-/bin/bash}"
HAS_INTERVAL=0

# trim
# 创建者: Codex
# 最后修改人: Codex
# 功能说明: 去除字符串首尾空白字符。
# 使用示例: trim "  mand  "
trim() {
  local s="${1-}"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf "%s" "$s"
}

# err
# 创建者: Codex
# 最后修改人: Codex
# 功能说明: 统一输出错误并按约定返回错误码。
# 使用示例: err "$RC_ARG" "missing value for -interval"
err() {
  local code="$1"
  shift
  printf "ERROR(%s): %s\n" "$code" "$*" >&2
  exit "$code"
}

# usage
# 创建者: Codex
# 最后修改人: Codex
# 功能说明: 输出脚本参数说明、示例和返回码约定。
# 使用示例: usage
usage() {
  cat <<'EOF'
Usage:
  codex-multi-agents-schedule-command.sh -interval <seconds> [-count <times>] [-command <cmd>] [-log-file <path>] [-shell <shell_path>]

Examples:
  codex-multi-agents-schedule-command.sh -interval 60 -count 1
  codex-multi-agents-schedule-command.sh -interval 5 -count 3 -command 'echo hello'
  codex-multi-agents-schedule-command.sh -interval 10 -count 2 -command 'mand --mode batch' -log-file ./schedule.log

Return codes:
  0 success
  1 argument error
  2 file or environment error
  3 command execution error
  5 internal error
EOF
}

# is_non_negative_integer
# 创建者: Codex
# 最后修改人: Codex
# 功能说明: 判断输入是否为非负整数。
# 使用示例: is_non_negative_integer "0"
is_non_negative_integer() {
  local value="$1"
  [[ "$value" =~ ^[0-9]+$ ]]
}

# is_positive_integer
# 创建者: Codex
# 最后修改人: Codex
# 功能说明: 判断输入是否为正整数。
# 使用示例: is_positive_integer "3"
is_positive_integer() {
  local value="$1"
  [[ "$value" =~ ^[1-9][0-9]*$ ]]
}

# parse_args
# 创建者: Codex
# 最后修改人: Codex
# 功能说明: 解析命令行参数并校验必填项。
# 使用示例: parse_args -interval 5 -count 2 -command 'echo hello'
parse_args() {
  if [[ $# -eq 0 ]]; then
    usage
    err "$RC_ARG" "missing arguments"
  fi

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -interval=*)
        INTERVAL="${1#*=}"
        HAS_INTERVAL=1
        shift
        ;;
      -interval)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -interval"
        INTERVAL="$2"
        HAS_INTERVAL=1
        shift 2
        ;;
      -count=*)
        COUNT="${1#*=}"
        shift
        ;;
      -count)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -count"
        COUNT="$2"
        shift 2
        ;;
      -command=*)
        COMMAND="${1#*=}"
        shift
        ;;
      -command)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -command"
        COMMAND="$2"
        shift 2
        ;;
      -log-file=*)
        LOG_FILE="${1#*=}"
        shift
        ;;
      -log-file)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -log-file"
        LOG_FILE="$2"
        shift 2
        ;;
      -shell=*)
        SHELL_BIN="${1#*=}"
        shift
        ;;
      -shell)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -shell"
        SHELL_BIN="$2"
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

  [[ "$HAS_INTERVAL" -eq 1 ]] || err "$RC_ARG" "missing required argument: -interval"
  INTERVAL="$(trim "$INTERVAL")"
  COUNT="$(trim "$COUNT")"
  COMMAND="$(trim "$COMMAND")"
  SHELL_BIN="$(trim "$SHELL_BIN")"
  LOG_FILE="$(trim "$LOG_FILE")"

  is_non_negative_integer "$INTERVAL" || err "$RC_ARG" "-interval must be a non-negative integer"
  is_non_negative_integer "$COUNT" || err "$RC_ARG" "-count must be a non-negative integer"
  [[ -n "$COMMAND" ]] || err "$RC_ARG" "empty value for -command"
  [[ -n "$SHELL_BIN" ]] || err "$RC_ARG" "empty value for -shell"
}

# ensure_environment
# 创建者: Codex
# 最后修改人: Codex
# 功能说明: 检查运行 shell 和日志目录是否可用。
# 使用示例: ensure_environment
ensure_environment() {
  [[ -x "$SHELL_BIN" ]] || err "$RC_FILE" "shell not found or not executable: $SHELL_BIN"

  if [[ -n "$LOG_FILE" ]]; then
    local log_dir
    log_dir="$(dirname "$LOG_FILE")"
    mkdir -p "$log_dir" || err "$RC_FILE" "cannot create log directory: $log_dir"
    touch "$LOG_FILE" || err "$RC_FILE" "cannot open log file: $LOG_FILE"
  fi
}

# run_once
# 创建者: Codex
# 最后修改人: Codex
# 功能说明: 执行一次命令，并在需要时将结果追加到日志文件。
# 使用示例: run_once 1
run_once() {
  local round="$1"
  local output

  output="$("$SHELL_BIN" -lc "$COMMAND" 2>&1)"
  local rc=$?
  local now
  now="$(date '+%Y-%m-%d %H:%M:%S')"

  if [[ -n "$LOG_FILE" ]]; then
    {
      printf "[%s] round=%s command=%s\n" "$now" "$round" "$COMMAND"
      printf "%s\n" "$output"
    } >> "$LOG_FILE"
  fi

  if [[ "$rc" -ne 0 ]]; then
    printf "%s\n" "$output" >&2
    err "$RC_DATA" "command failed on round $round with exit code $rc"
  fi

  printf "[%s] OK round=%s command=%s\n" "$now" "$round" "$COMMAND"
  if [[ -n "$output" ]]; then
    printf "%s\n" "$output"
  fi
}

# run_schedule
# 创建者: Codex
# 最后修改人: Codex
# 功能说明: 按 interval/count 控制调度循环。
# 使用示例: run_schedule
run_schedule() {
  local round=1

  if [[ "$COUNT" == "0" ]]; then
    while true; do
      run_once "$round"
      round=$((round + 1))
      sleep "$INTERVAL"
    done
  fi

  while [[ "$round" -le "$COUNT" ]]; do
    run_once "$round"
    if [[ "$round" -lt "$COUNT" ]]; then
      sleep "$INTERVAL"
    fi
    round=$((round + 1))
  done
}

main() {
  parse_args "$@"
  ensure_environment
  run_schedule
}

main "$@"
