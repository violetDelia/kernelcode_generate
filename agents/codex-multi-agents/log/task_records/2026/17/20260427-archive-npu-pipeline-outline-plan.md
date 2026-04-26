时间：2026-04-27 03:55
经办人：李白
任务：T-20260427-e06a380b
任务目标：补录 `npu_pipeline_outline_device_kernel_contract_green_plan.md` 的归档 merge 步骤，确认 surviving `done_plan` 承载文件落位，并完成归档任务收口。
执行前阅读记录：
- 已读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 当前任务行，确认 `T-20260427-e06a380b` 的目标是将 [`ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md) 的归档链收口到 surviving `done_plan`。
- 已读归档承载文件 [`npu_demo_lowering_outline_device_kernel_green_plan.md`](/home/lfr/kernelcode_generate/wt-20260427-archive-npu-pipeline-outline-plan/agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md)，确认正文已在当前 archive worktree 现场落位，且已经包含 `R1~R5` 对齐记录与 latest-main 承接口径。
- 已核对当前 archive worktree 的 `HEAD` 不包含 tracked 路径 `ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md`；主仓虽然存在同名共享计划文件，但它不属于当前 archive worktree 的 tracked diff 面。
改动：
- 在当前 archive worktree 中补写本任务记录 [`20260427-archive-npu-pipeline-outline-plan.md`](/home/lfr/kernelcode_generate/wt-20260427-archive-npu-pipeline-outline-plan/agents/codex-multi-agents/log/task_records/2026/17/20260427-archive-npu-pipeline-outline-plan.md)。
- 归档正文 [`npu_demo_lowering_outline_device_kernel_green_plan.md`](/home/lfr/kernelcode_generate/wt-20260427-archive-npu-pipeline-outline-plan/agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md) 已在当前 worktree 存在且现场无新增正文差异，因此本轮不伪造“删除源计划书”的 tracked 改动。
- 本轮真实提交边界只包含归档任务记录；`done_plan` 正文本轮仅做落位核对，不追加无必要改写。
验证：
- `git -C /home/lfr/kernelcode_generate/wt-20260427-archive-npu-pipeline-outline-plan status --short`
- `git -C /home/lfr/kernelcode_generate/wt-20260427-archive-npu-pipeline-outline-plan ls-tree -r --name-only HEAD | rg '^ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan\\.md$|^TODO\\.md$|^expectation($|/)|^agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan\\.md$'`
- `git -C /home/lfr/kernelcode_generate/wt-20260427-archive-npu-pipeline-outline-plan diff --check`
Diff 反推自测：
- 当前实际 diff 只包含本任务记录 [`20260427-archive-npu-pipeline-outline-plan.md`](/home/lfr/kernelcode_generate/wt-20260427-archive-npu-pipeline-outline-plan/agents/codex-multi-agents/log/task_records/2026/17/20260427-archive-npu-pipeline-outline-plan.md)。
- 反推校验重点是：archive worktree 中不存在 tracked 的源计划路径；`done_plan` 正文已存在且无需额外改写；`git diff --check` 通过。
- `expectation` 不涉及本任务，也未被修改。
自检：
- 本轮只补录 archive merge 任务记录，没有改写实现、测试、共享计划正文或 `expectation`。
- 当前 surviving `done_plan` 已承接该专题后续状态，不需要在 archive worktree 中重造活动计划路径、`TODO.md` 或 `expectation` 包。
- 若主仓快进被既有本地状态挡住，只记录阻塞，不覆盖现有改动。
结论：当前归档 merge 已按真实现场补录，可在同步到最新 `origin/main` 后提交、推送并执行 `-done`；后续由管理员执行 `-done-plan`。
