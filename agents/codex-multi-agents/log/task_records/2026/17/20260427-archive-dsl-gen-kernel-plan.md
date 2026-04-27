时间：2026-04-27 22:05
经办人：李白
任务：T-20260427-19d0d998
任务目标：补录 `dsl_gen_kernel_mlir_gen_public_api_green_plan.md` 的归档 merge 步骤，生成 surviving `done_plan` 承接文件，并完成归档任务收口。
执行前阅读记录：
- 已读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 当前任务行，确认 `T-20260427-19d0d998` 的目标是将 [`ARCHITECTURE/plan/dsl_gen_kernel_mlir_gen_public_api_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/dsl_gen_kernel_mlir_gen_public_api_green_plan.md) 的归档链收口到 surviving `done_plan`。
- 已读共享计划正文 [`dsl_gen_kernel_mlir_gen_public_api_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/dsl_gen_kernel_mlir_gen_public_api_green_plan.md)，确认当前通过口径已经包含 `S1/S2/R1`、最新复验结论与公开 API / pytest 承接边界。
- 已核对当前 archive worktree 的 `HEAD` 不包含 tracked 路径 `ARCHITECTURE/plan/dsl_gen_kernel_mlir_gen_public_api_green_plan.md`，也不存在现成的 `done_plan` 承接文件；因此这次不是“只补记录”，而是需要在 archive worktree 中新增 surviving `done_plan` 正文。
改动：
- 在当前 archive worktree 中新建归档正文 [`dsl_gen_kernel_mlir_gen_public_api_green_plan.md`](/home/lfr/kernelcode_generate/wt-20260427-archive-dsl-gen-kernel-plan/agents/codex-multi-agents/log/task_records/done_plan/2026/17/dsl_gen_kernel_mlir_gen_public_api_green_plan.md)。
- 归档正文基于共享计划正文生成，并做了两类最小调整：
  - 顶部补入“当前主线 tracked 面不再通过活动计划路径承接该主题”的归档说明。
  - 将 Markdown 相对链接统一改到 `done_plan/2026/17` 层级，保证进入主线后的链接可直接打开。
- 在当前 archive worktree 中补写本任务记录 [`20260427-archive-dsl-gen-kernel-plan.md`](/home/lfr/kernelcode_generate/wt-20260427-archive-dsl-gen-kernel-plan/agents/codex-multi-agents/log/task_records/2026/17/20260427-archive-dsl-gen-kernel-plan.md)。
- 源计划 [`ARCHITECTURE/plan/dsl_gen_kernel_mlir_gen_public_api_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/dsl_gen_kernel_mlir_gen_public_api_green_plan.md) 虽然在主仓现场存在，但不属于当前 archive worktree 的 tracked diff 面，因此本轮不伪造“删除源计划书”的 tracked 改动。
验证：
- `git -C /home/lfr/kernelcode_generate/wt-20260427-archive-dsl-gen-kernel-plan status --short`
- `git -C /home/lfr/kernelcode_generate/wt-20260427-archive-dsl-gen-kernel-plan ls-tree -r --name-only HEAD | rg '^ARCHITECTURE/plan/dsl_gen_kernel_mlir_gen_public_api_green_plan\\.md$|^agents/codex-multi-agents/log/task_records/done_plan/2026/17/dsl_gen_kernel_mlir_gen_public_api_green_plan\\.md$|^TODO\\.md$|^expectation($|/)'`
- `python3 - <<'PY' ... markdown link check for dsl_gen_kernel_mlir_gen_public_api_green_plan.md ... PY`
- `git -C /home/lfr/kernelcode_generate/wt-20260427-archive-dsl-gen-kernel-plan diff --check`
Diff 反推自测：
- 当前实际 diff 只包含：
  - [`dsl_gen_kernel_mlir_gen_public_api_green_plan.md`](/home/lfr/kernelcode_generate/wt-20260427-archive-dsl-gen-kernel-plan/agents/codex-multi-agents/log/task_records/done_plan/2026/17/dsl_gen_kernel_mlir_gen_public_api_green_plan.md)
  - [`20260427-archive-dsl-gen-kernel-plan.md`](/home/lfr/kernelcode_generate/wt-20260427-archive-dsl-gen-kernel-plan/agents/codex-multi-agents/log/task_records/2026/17/20260427-archive-dsl-gen-kernel-plan.md)
- 反推校验重点是：
  - archive worktree 中不存在 tracked 的源计划路径；
  - surviving `done_plan` 正文已按当前通过口径落位；
  - 正文链接进入主线后可直接打开；
  - `git diff --check` 通过。
- `expectation` 不涉及本任务，也未被修改。
自检：
- 本轮只处理归档正文与归档任务记录，没有改写实现、测试、共享规则文件或 `expectation`。
- 归档正文采用当前共享计划正文作为唯一来源，没有擅自补造新的完成结论或复验结果。
- 若主仓快进被既有本地状态挡住，只记录阻塞，不覆盖现有改动。
结论：当前归档 merge 已按真实现场补录；同步到最新 `origin/main` 后，可提交、推送并执行 `-done`，后续由管理员执行 `-done-plan`。
