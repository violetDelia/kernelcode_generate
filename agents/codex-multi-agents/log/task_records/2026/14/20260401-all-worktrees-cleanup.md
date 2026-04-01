时间：2026-04-01 17:29:00 +0800
任务：T-20260401-2a495055
任务目标：清空当前空闲工作树，仅处理 `/home/lfr/kernelcode_generate` 下现存的 13 个指定 worktree，且不覆盖主仓未提交改动 `ARCHITECTURE/plan/ptr_symbol_func_input_plan.md`、`kernel_gen/dsl/emit_mlir.py`、`test/dsl/test_mlir_gen.py`。
改动：
- 核对 `git worktree list --porcelain`，确认目标 worktree 均存在：`wt-20260401-analysis-i1`、`wt-20260401-analysis-s1`、`wt-20260401-conv-p10`、`wt-20260401-conv-p11`、`wt-20260401-conv-p16`、`wt-20260401-expectation-e1`、`wt-20260401-nn-add-a1`、`wt-20260401-npu-a0`、`wt-20260401-ptr-i1`、`wt-20260401-ptr-p1`、`wt-20260401-ptr-p2`、`wt-20260401-ptr-p3`、`wt-20260401-ptr-p4`。
- 核对挂载状态：`/home/lfr/kernelcode_generate/.git` 仍为只读挂载（`mount` 显示 `type ext4 (ro,...)`）。
- 逐个检查 worktree 状态，发现仅 `wt-20260401-conv-p10`、`wt-20260401-conv-p11`、`wt-20260401-conv-p16` 为干净；其余 worktree 仍有未提交修改或未跟踪记录文件。
- 实测移除一个干净 worktree：执行 `git -C /home/lfr/kernelcode_generate worktree remove /home/lfr/kernelcode_generate/wt-20260401-conv-p10`，报错 `error: failed to delete '.git/worktrees/wt-20260401-conv-p10': Read-only file system`。
结论：任务阻塞，根因为主仓 `.git` 只读，`git worktree remove` 无法更新 `.git/worktrees/*` 元数据；当前未删除任何 worktree，也未触碰主仓未提交改动。需先恢复 `.git` 为可写后再继续清理。

时间：2026-04-01 23:48:35 +0800
任务：T-20260401-e4215fd3
任务目标：清理 `/home/lfr/kernelcode_generate` 下白名单中的 13 个现存 worktree，仅保留主仓当前未提交改动；若目标目录已不存在，则继续清理残留 worktree 元数据。
改动：
- 读取 `git worktree list --porcelain`，确认白名单中的 13 个条目仍登记在主仓 worktree 元数据中，且全部标记为 `prunable gitdir file points to non-existent location`。
- 逐个核对工作区目录，确认 `wt-20260401-analysis-i1`、`wt-20260401-analysis-s1`、`wt-20260401-conv-p10`、`wt-20260401-conv-p11`、`wt-20260401-conv-p16`、`wt-20260401-expectation-e1`、`wt-20260401-nn-add-a1`、`wt-20260401-npu-a0`、`wt-20260401-ptr-i1`、`wt-20260401-ptr-p1`、`wt-20260401-ptr-p2`、`wt-20260401-ptr-p3`、`wt-20260401-ptr-p4` 目录均已不存在。
- 核对主仓 `.git` 挂载状态，确认 `/home/lfr/kernelcode_generate/.git` 仍为只读挂载：`/dev/sdd on /home/lfr/kernelcode_generate/.git type ext4 (ro,...)`。
结论：任务阻塞。当前无需再丢弃 dirty worktree 中未提交改动，因为白名单目录已全部缺失；但残留的 worktree 元数据仍需在主仓 `.git` 可写后执行 `git worktree prune` 或等效清理。主仓未提交改动未被触碰。
