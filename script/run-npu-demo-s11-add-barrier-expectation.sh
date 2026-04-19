#!/usr/bin/env bash
# run-npu-demo-s11-add-barrier-expectation.sh
#
# 创建者: jcc你莫辜负
# 最后修改人: jcc你莫辜负
# 最后修改日期: 2026-04-20
#
# 功能说明:
# - 为 `T-20260419-a10007f4` 提供 S11 `npu_demo_add_barrier` expectation 的 worktree 内可执行入口。
# - 从当前 worktree 启动 Python，并通过主仓路径加载 `expectation/dsl/gen_kernel/npu_demo_add_barrier`。
# - 支持 `--print-command` 输出实际执行命令，便于任务记录与复审直接复用。
#
# 使用示例:
# - 直接执行 expectation: `script/run-npu-demo-s11-add-barrier-expectation.sh`
# - 只打印命令骨架: `script/run-npu-demo-s11-add-barrier-expectation.sh --print-command`
#
# 对应文件:
# - spec: ARCHITECTURE/plan/npu_demo_emitc_include_api_green_plan.md
# - test: test/script/test_run_npu_demo_s11_add_barrier_expectation.py
# - 功能实现: script/run-npu-demo-s11-add-barrier-expectation.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKTREE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MAIN_REPO_ROOT="$(cd "$WORKTREE_ROOT/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
EXPECTATION_ENTRY="$MAIN_REPO_ROOT/expectation/dsl/gen_kernel/npu_demo_add_barrier"
PYTHONPATH_VALUE="$WORKTREE_ROOT:$MAIN_REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

usage() {
  cat <<'EOF'
Usage:
  script/run-npu-demo-s11-add-barrier-expectation.sh
  script/run-npu-demo-s11-add-barrier-expectation.sh --print-command
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
