#!/usr/bin/env bash
# notify-admin.sh
#
# 最后修改日期: 2026-04-12
#
# 功能说明:
# - 按脚本顶部配置定时向管理员发送会话消息。
# - 定时频率、管理员信息和消息内容都直接维护在本文件顶部。
# - 循环模式下按 `1/3` 概率补做一次管理员初始化，降低会话缺失导致的通知失败概率。
# - 每轮会先提醒管理员推进“正在执行的任务”并分发“任务列表”中可分发任务。
# - 同轮会对 `agents-lists.md` 中状态为 `busy` 的执行人逐一发送提醒（忽略管理员与架构师账号）。
# - 支持通过 `NOTIFY_ADMIN_RANDOM_ROLL` 固定初始化分支，便于测试命中/未命中行为。
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
INTERVAL_SECONDS=3600

# 会话发送信息。
FROM_NAME="榕"
TO_NAME="神秘人"
AGENTS_LIST_FILE="agents/codex-multi-agents/agents-lists.md"

# 管理员每轮提醒消息（先发送）。
read -r -d '' ADMIN_MESSAGE <<'EOF' || true
请推进“正在执行的任务”并分发“任务列表”中可分发任务。有任何问题和回复,使用脚本 -talk 对话。如果有完成的任务按照顺序一个一个询问架构师验收,验收通过后归档。
EOF

# busy 执行人提醒消息（后发送；同一轮会逐一发送）。
read -r -d '' BUSY_MESSAGE <<'EOF' || true
再次查看TODO.md, 继续你的任务，完成后使用 -next 并回报管理员,如果发现之前执行过相同的任务,说明任务又流转到你身上,查看日志,继续按照任务要求执行。有任何阻塞/疑问再次回报管理/架构师,重复用脚本询问要求对方回复,直到对方回复。
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
  [[ -n "$ADMIN_MESSAGE" ]] || err "$RC_DATA" "ADMIN_MESSAGE is required"
  [[ -n "$BUSY_MESSAGE" ]] || err "$RC_DATA" "BUSY_MESSAGE is required"

  [[ -x "$TMUX_SCRIPT" ]] || err "$RC_FILE" "tmux script is not executable: $TMUX_SCRIPT"
}

cleanup() {
  exit "$RC_OK"
}

trim() {
  local s="${1-}"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf "%s" "$s"
}

is_pipe_row() {
  local line="${1-}"
  [[ "$line" =~ ^[[:space:]]*\\|.*\\|[[:space:]]*$ ]]
}

is_sep_row() {
  local line="${1-}"
  [[ "$line" =~ ^[[:space:]]*\\|[[:space:]:-][[:space:]:|\\-]*\\|[[:space:]]*$ ]]
}

split_row() {
  local line="$1"
  local -n out_ref="$2"
  local core
  core="$(trim "$line")"
  core="${core#|}"
  core="${core%|}"

  local raw=()
  IFS='|' read -r -a raw <<< "$core"
  out_ref=()

  local i cell
  for i in "${!raw[@]}"; do
    cell="$(trim "${raw[$i]}")"
    out_ref+=("$cell")
  done
}

should_skip_busy_target() {
  local name="${1-}"
  local intro="${2-}"
  local duty="${3-}"
  [[ -z "$name" ]] && return 0
  [[ "$name" == "$TO_NAME" ]] && return 0
  [[ "$intro" == *"管理员"* ]] && return 0
  [[ "$intro" == *"架构师"* ]] && return 0
  [[ "$duty" == *"管理员"* ]] && return 0
  [[ "$duty" == *"架构"* ]] && return 0
  return 1
}

list_busy_targets() {
  local file="$1"
  local -a lines=()
  mapfile -t lines < "$file"

  local header_idx=-1
  local sep_idx=-1
  local name_col=-1
  local status_col=-1
  local intro_col=-1
  local duty_col=-1

  local i j
  for i in "${!lines[@]}"; do
    if ! is_pipe_row "${lines[$i]}"; then
      continue
    fi

    local -a header_cells=()
    split_row "${lines[$i]}" header_cells

    name_col=-1
    status_col=-1
    intro_col=-1
    duty_col=-1
    for j in "${!header_cells[@]}"; do
      if [[ "${header_cells[$j]}" == "姓名" ]]; then
        name_col="$j"
      fi
      if [[ "${header_cells[$j]}" == "状态" ]]; then
        status_col="$j"
      fi
      if [[ "${header_cells[$j]}" == "介绍" ]]; then
        intro_col="$j"
      fi
      if [[ "${header_cells[$j]}" == "职责" ]]; then
        duty_col="$j"
      fi
    done

    if (( name_col >= 0 && status_col >= 0 )); then
      if (( i + 1 < ${#lines[@]} )) && is_sep_row "${lines[$((i + 1))]}"; then
        header_idx="$i"
        sep_idx="$((i + 1))"
        break
      fi
    fi
  done

  if (( header_idx < 0 || sep_idx < 0 )); then
    return 0
  fi

  for ((i=sep_idx + 1; i<${#lines[@]}; i++)); do
    if ! is_pipe_row "${lines[$i]}"; then
      break
    fi
    local -a cells=()
    split_row "${lines[$i]}" cells

    local name status intro="" duty=""
    name="${cells[$name_col]-}"
    status="${cells[$status_col]-}"
    if (( intro_col >= 0 )); then
      intro="${cells[$intro_col]-}"
    fi
    if (( duty_col >= 0 )); then
      duty="${cells[$duty_col]-}"
    fi

    if [[ "$status" != "busy" ]]; then
      continue
    fi
    if should_skip_busy_target "$name" "$intro" "$duty"; then
      continue
    fi
    printf '%s\n' "$name"
  done
}

send_talk() {
  local from="$1"
  local to="$2"
  local message="$3"
  bash "$TMUX_SCRIPT" \
    -talk \
    -from "$from" \
    -to "$to" \
    -agents-list "$(log_path "$AGENTS_LIST_FILE")" \
    -message "$message"
}

send_round() {
  send_talk "$FROM_NAME" "$TO_NAME" "$ADMIN_MESSAGE"

  local busy_target
  while IFS= read -r busy_target; do
    [[ -n "$busy_target" ]] || continue
    send_talk "$FROM_NAME" "$busy_target" "$BUSY_MESSAGE"
  done < <(list_busy_targets "$(log_path "$AGENTS_LIST_FILE")")
}

run_init() {
  validate_init_config
  bash "$LIST_SCRIPT" \
    -file "$(log_path "$AGENTS_LIST_FILE")" \
    -init \
    -name "$TO_NAME"
}

maybe_init_admin() {
  local roll
  roll="${NOTIFY_ADMIN_RANDOM_ROLL:-$((RANDOM % 3))}"
  [[ "$roll" =~ ^[0-2]$ ]] || err "$RC_DATA" "NOTIFY_ADMIN_RANDOM_ROLL must be 0, 1, or 2"
  if [[ "$roll" -eq 0 ]]; then
    run_init
  fi
}

main_loop() {
  while true; do
    validate_loop_config
    maybe_init_admin
    send_round
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
