# 20260319-worktree-cleanup

## T-20260319-41eac48b

- 时间：2026-03-19 21:22:32 +0800
- 角色：`不要啊教练`
- worktree：`/home/lfr/kernelcode_generate/wt-20260319-worktree-cleanup`
- 目标：盘点并清理冗余 worktree（优先检查 operation/nn matmul/init/broadcast 链路相关 worktree）

### 已清理 worktree
- `/home/lfr/kernelcode_generate/wt-20260319-dsl-emit-mlir-mlir-gen-merge`
  - 原因：无未提交改动，分支无未合入提交，可安全移除。

### 保留的 worktree（含原因）
- `/home/lfr/kernelcode_generate/wt-20260319-operation-nn-init-doc-fix`
  - 存在未提交改动：`python/operation/__init__.py`、`agents/codex-multi-agents/log/talk.log`。
- `/home/lfr/kernelcode_generate/wt-20260319-operation-nn-matmul-review`
  - 存在未提交/未登记改动：`agents/codex-multi-agents/agents-lists.md`、`agents/codex-multi-agents/log/talk.log`、`agents/codex-multi-agents/log/task_records/2026/12/20260319-operation-nn-matmul-refactor.md`。
- `/home/lfr/kernelcode_generate/wt-20260319-operation-nn-matmul-merge`
  - 分支存在未合入提交：`ce5c30e`（"Refresh nn matmul spec mapping"）。
- `/home/lfr/kernelcode_generate/wt-20260319-operation-nn-matmul-spec-fix`
  - 存在未提交/未登记改动：`spec/operation/nn.md`、`agents/codex-multi-agents/log/talk.log`、`agents/codex-multi-agents/log/task_records/2026/12/20260319-operation-nn-matmul-refactor.md`。
- `/home/lfr/kernelcode_generate/wt-20260319-operation-nn-matmul-impl`
  - 存在未提交改动：`python/operation/__init__.py`、`python/operation/nn.py`、`test/operation/test_operation_nn.py`、`agents/codex-multi-agents/log/talk.log`。
- `/home/lfr/kernelcode_generate/wt-20260319-operation-nn-broadcast-spec-fix`
  - 存在未提交改动：`spec/operation/nn.md`。
- `/home/lfr/kernelcode_generate/wt-20260319-dsl-emit-mlir-mlir-gen-refactor`
  - 存在未提交/未登记改动：`spec/dsl/mlir_gen.md`、`spec/dsl/emit_mlir.md`、`agents/codex-multi-agents/agents-lists.md`、`agents/codex-multi-agents/log/talk.log`、`agents/codex-multi-agents/log/task_records/2026/12/20260319-dsl-emit-mlir-refactor.md`、`agents/codex-multi-agents/log/task_records/2026/12/20260319-dsl-mlir-gen-refactor.md`。

### 说明
- 本次仅移除确认无改动且无未合入提交的 worktree，其余因存在改动或未合入提交暂不清理。
