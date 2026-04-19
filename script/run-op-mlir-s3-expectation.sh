#!/usr/bin/env bash
# run-op-mlir-s3-expectation.sh
#
# 创建者: 小李飞刀
# 最后修改人: 小李飞刀
# 最后修改日期: 2026-04-19
#
# 功能说明:
# - 为 `T-20260418-fdbc4ed2` 提供 S3 全量 `nn_lowering` expectation 的可复现入口。
# - 从当前 worktree 启动 Python，并通过主仓路径加载 `expectation.pass.lowing.nn_lowering`。
# - 依赖 `sys.path[0]` 指向当前 worktree，保证 `kernel_gen/*` 优先使用本任务实现。
# - 支持 `--print-command` 输出实际执行命令，便于计划书和任务记录复用。
#
# 使用示例:
# - 直接执行 expectation: `script/run-op-mlir-s3-expectation.sh`
# - 只打印命令骨架: `script/run-op-mlir-s3-expectation.sh --print-command`
#
# 对应文件:
# - spec: ARCHITECTURE/plan/operation_mlir_gen_expectation_green_plan.md
# - test: test/script/test_run_op_mlir_s3_expectation.py
# - 功能实现: script/run-op-mlir-s3-expectation.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKTREE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
MODULE_NAME="expectation.pass.lowing.nn_lowering"

resolve_expectation_repo_root() {
  if [[ -d "$WORKTREE_ROOT/expectation" ]]; then
    printf '%s\n' "$WORKTREE_ROOT"
    return 0
  fi

  local parent_root
  parent_root="$(cd "$WORKTREE_ROOT/.." && pwd)"
  if [[ -d "$parent_root/expectation" ]]; then
    printf '%s\n' "$parent_root"
    return 0
  fi

  printf 'expectation repo root not found from %s\n' "$WORKTREE_ROOT" >&2
  return 1
}

MAIN_REPO_ROOT="$(resolve_expectation_repo_root)"
PYTHONPATH_VALUE="$MAIN_REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

usage() {
  cat <<'EOF'
Usage:
  script/run-op-mlir-s3-expectation.sh
  script/run-op-mlir-s3-expectation.sh --print-command
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
