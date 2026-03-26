时间：2026-03-26 09:36:44 +0800
经手人：我不是牛马
任务：T-20260326-944ecd61（worktree audit）
任务目标：核对并清理 main repo 中无效或过期 worktree，确认 worktree list 输出正常后回报。
改动：
- 核对 `git worktree list`：仅保留 `/home/lfr/kernelcode_generate` 与 `/home/lfr/kernelcode_generate/wt-20260326-dialect-tune`，无无效 worktree。
- 核对仓库根目录 `wt-*` 残留：仅 `wt-20260326-dialect-tune`，与 worktree list 一致。
- `git worktree prune --dry-run` 无输出，未发现需清理的无效 worktree。
结论：未发现无效/过期 worktree，本轮无需清理；worktree list 输出正常。
