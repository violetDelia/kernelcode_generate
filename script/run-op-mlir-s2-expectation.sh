#!/usr/bin/env bash
# run-op-mlir-s2-expectation.sh
#
# 创建者: 小李飞刀
# 最后修改人: 小李飞刀
# 最后修改日期: 2026-04-19
#
# 功能说明:
# - 为 `T-20260418-61084fbf` 提供 S2 expectation 验收命令的 worktree 内可执行入口。
# - 从当前 worktree 启动 Python，并通过主仓路径加载 `expectation.pass.lowing.nn_lowering.element_binary`。
# - 依赖 `sys.path[0]` 指向当前 worktree，保证 `kernel_gen/*` 优先使用本任务实现，而不是主仓旧实现。
# - 支持 `--print-command` 输出实际执行命令，便于任务记录直接复用。
#
# 使用示例:
# - 直接执行 expectation: `script/run-op-mlir-s2-expectation.sh`
# - 只打印命令骨架: `script/run-op-mlir-s2-expectation.sh --print-command`
#
# 对应文件:
# - spec: ARCHITECTURE/plan/operation_mlir_gen_expectation_green_plan.md
# - test: test/script/test_run_op_mlir_s2_expectation.py
# - 功能实现: script/run-op-mlir-s2-expectation.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKTREE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MAIN_REPO_ROOT="$(cd "$WORKTREE_ROOT/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
MODULE_NAME="expectation.pass.lowing.nn_lowering.element_binary"
PYTHONPATH_VALUE="$MAIN_REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

usage() {
  cat <<'EOF'
Usage:
  script/run-op-mlir-s2-expectation.sh
  script/run-op-mlir-s2-expectation.sh --print-command
EOF
}

print_command() {
  printf 'cd %s && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=%s %s -m %s\n' \
    "$WORKTREE_ROOT" \
    "$PYTHONPATH_VALUE" \
    "$PYTHON_BIN" \
    "$MODULE_NAME"
}

main() {
  case "${1-}" in
    "")
      cd "$WORKTREE_ROOT"
      exec env \
        PYTHONDONTWRITEBYTECODE=1 \
        PYTHONPATH="$PYTHONPATH_VALUE" \
        "$PYTHON_BIN" -m "$MODULE_NAME"
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
