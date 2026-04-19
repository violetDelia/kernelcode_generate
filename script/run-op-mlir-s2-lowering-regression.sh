#!/usr/bin/env bash
# run-op-mlir-s2-lowering-regression.sh
#
# 创建者: 金铲铲大作战
# 最后修改人: 金铲铲大作战
# 最后修改日期: 2026-04-19
#
# 功能说明:
# - 为 `T-20260418-61084fbf` 提供 S2 lowering 回归的 worktree 内可执行入口。
# - 固定执行 element_binary add/sub/mul/div/truediv 五组 lowering 回归，避免 `-k` 关键词筛选不命中。
# - 支持 `--print-command` 输出实际执行命令，便于任务记录直接复用。
#
# 使用示例:
# - 直接执行 lowering 回归: `script/run-op-mlir-s2-lowering-regression.sh`
# - 只打印命令骨架: `script/run-op-mlir-s2-lowering-regression.sh --print-command`
#
# 对应文件:
# - spec: ARCHITECTURE/plan/operation_mlir_gen_expectation_green_plan.md
# - test: test/script/test_run_op_mlir_s2_lowering_regression.py
# - 功能实现: script/run-op-mlir-s2-lowering-regression.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKTREE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PYTEST_ARGS=(
  -m pytest
  -q
  test/pass/nn_lowering/element_binary_add.py
  test/pass/nn_lowering/element_binary_sub.py
  test/pass/nn_lowering/element_binary_mul.py
  test/pass/nn_lowering/element_binary_div.py
  test/pass/nn_lowering/element_binary_truediv.py
)

usage() {
  cat <<'EOF'
Usage:
  script/run-op-mlir-s2-lowering-regression.sh
  script/run-op-mlir-s2-lowering-regression.sh --print-command
EOF
}

print_command() {
  printf 'cd %s && PYTHONDONTWRITEBYTECODE=1 %s' "$WORKTREE_ROOT" "$PYTHON_BIN"
  for arg in "${PYTEST_ARGS[@]}"; do
    printf ' %s' "$arg"
  done
  printf '\n'
}

main() {
  case "${1-}" in
    "")
      cd "$WORKTREE_ROOT"
      exec env PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" "${PYTEST_ARGS[@]}"
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
