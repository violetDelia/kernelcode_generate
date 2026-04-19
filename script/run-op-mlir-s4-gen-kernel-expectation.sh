#!/usr/bin/env bash
# run-op-mlir-s4-gen-kernel-expectation.sh
#
# 创建者: 金铲铲大作战
# 最后修改人: 金铲铲大作战
# 最后修改日期: 2026-04-19
#
# 功能说明:
# - 为 `T-20260418-20ddd3cf` 提供 S4 `gen_kernel` expectation 的 worktree 内可执行入口。
# - 从当前 worktree 启动 Python，并通过主仓路径加载 `expectation/dsl/gen_kernel/npu_demo_add_barrier`。
# - 支持 `--print-command` 输出实际执行命令，便于任务记录与计划书直接复用。
#
# 使用示例:
# - 直接执行 expectation: `script/run-op-mlir-s4-gen-kernel-expectation.sh`
# - 只打印命令骨架: `script/run-op-mlir-s4-gen-kernel-expectation.sh --print-command`
#
# 对应文件:
# - spec: ARCHITECTURE/plan/operation_mlir_gen_expectation_green_plan.md
# - test: test/script/test_run_op_mlir_s4_gen_kernel_expectation.py
# - 功能实现: script/run-op-mlir-s4-gen-kernel-expectation.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKTREE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

resolve_expectation_repo_root() {
  if [[ -f "$WORKTREE_ROOT/expectation/dsl/gen_kernel/npu_demo_add_barrier" ]]; then
    printf '%s\n' "$WORKTREE_ROOT"
    return 0
  fi

  local parent_root
  parent_root="$(cd "$WORKTREE_ROOT/.." && pwd)"
  if [[ -f "$parent_root/expectation/dsl/gen_kernel/npu_demo_add_barrier" ]]; then
    printf '%s\n' "$parent_root"
    return 0
  fi

  printf 'expectation entry not found from %s\n' "$WORKTREE_ROOT" >&2
  return 1
}

MAIN_REPO_ROOT="$(resolve_expectation_repo_root)"
EXPECTATION_ENTRY="$MAIN_REPO_ROOT/expectation/dsl/gen_kernel/npu_demo_add_barrier"
if [[ "$MAIN_REPO_ROOT" == "$WORKTREE_ROOT" ]]; then
  PYTHONPATH_VALUE="$WORKTREE_ROOT${PYTHONPATH:+:$PYTHONPATH}"
else
  PYTHONPATH_VALUE="$WORKTREE_ROOT:$MAIN_REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
fi

usage() {
  cat <<'EOF'
Usage:
  script/run-op-mlir-s4-gen-kernel-expectation.sh
  script/run-op-mlir-s4-gen-kernel-expectation.sh --print-command
EOF
}

print_command() {
  printf 'cd %s && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=%s %s %s\n' \
    "$WORKTREE_ROOT" \
    "$PYTHONPATH_VALUE" \
    "$PYTHON_BIN" \
    "$EXPECTATION_ENTRY"
}

main() {
  case "${1-}" in
    "")
      cd "$WORKTREE_ROOT"
      exec env \
        PYTHONDONTWRITEBYTECODE=1 \
        PYTHONPATH="$PYTHONPATH_VALUE" \
        "$PYTHON_BIN" "$EXPECTATION_ENTRY"
      ;;
    --print-command)
      print_command
      ;;
    -h|--help)
      usage
      ;;
    *)
      printf 'unknown argument: %s\n' "$1" >&2
      exit 1
      ;;
  esac
}

main "$@"
