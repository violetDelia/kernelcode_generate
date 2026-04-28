时间：2026-04-28 21:01:42 +0800
经办人：李白
任务：T-20260428-91e0fd54
任务目标：以现存 surviving `done_plan` 承接资产完成 `symbol_buffer_hoist_green_plan` 的归档 merge，补齐归档任务记录，并保持 `expectation` 只作为历史 / 本地只读合同来源说明
执行前阅读记录：
- 已读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 当前任务行，确认本任务为 `merge`，目标是收口 [`symbol_buffer_hoist_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/symbol_buffer_hoist_green_plan.md) 的归档链。
- 已读现存 surviving 归档正文 [`symbol_buffer_hoist_green_plan.md`](/home/lfr/kernelcode_generate/wt-20260428-archive-symbol-buffer-hoist-plan/agents/codex-multi-agents/log/task_records/done_plan/2026/17/symbol_buffer_hoist_green_plan.md)，确认正文已经写明 latest `main` 不再承接活动计划路径与 `expectation` 包，且 direct asset 口径收口到 surviving `done_plan` 与 [`20260427-symbol-buffer-hoist-plan-align-s2.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/17/20260427-symbol-buffer-hoist-plan-align-s2.md)。
- 已核对当前 archive worktree 的 tracked 现场：不存在 [`ARCHITECTURE/plan/symbol_buffer_hoist_green_plan.md`](/home/lfr/kernelcode_generate/wt-20260428-archive-symbol-buffer-hoist-plan/ARCHITECTURE/plan/symbol_buffer_hoist_green_plan.md)；也不存在 `expectation/` 目录；因此本轮按真实现场只补录归档 merge 记录，不伪造源计划删除 diff，也不写入任何 `expectation` 资产。
最小功能闭环：
- 保持当前 surviving `done_plan` 正文不回退。
- 在 archive worktree 中补齐本次归档 merge 记录。
- 将这份记录与现存 surviving `done_plan` 一起进入主线。
改动：
- 新增当前任务记录 [`20260428-archive-symbol-buffer-hoist-plan.md`](/home/lfr/kernelcode_generate/wt-20260428-archive-symbol-buffer-hoist-plan/agents/codex-multi-agents/log/task_records/2026/17/20260428-archive-symbol-buffer-hoist-plan.md)。
- 本轮未修改 [`symbol_buffer_hoist_green_plan.md`](/home/lfr/kernelcode_generate/wt-20260428-archive-symbol-buffer-hoist-plan/agents/codex-multi-agents/log/task_records/done_plan/2026/17/symbol_buffer_hoist_green_plan.md) 正文；它已作为现存 surviving 承接资产直接复用。
- 源计划 [`symbol_buffer_hoist_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/symbol_buffer_hoist_green_plan.md) 在主仓共享现场可见，但不在当前 archive worktree 的 tracked 面中，因此本轮不构造“删除源计划”的提交内容。
验证：
- `timeout 60 git -C /home/lfr/kernelcode_generate/wt-20260428-archive-symbol-buffer-hoist-plan fetch origin` -> 通过；当前 `HEAD == origin/main == merge-base == 4f441342ba046d46ac0974a64cb4cdaa55192ba8`
- `test ! -f /home/lfr/kernelcode_generate/wt-20260428-archive-symbol-buffer-hoist-plan/ARCHITECTURE/plan/symbol_buffer_hoist_green_plan.md` -> `NO_PLAN`
- `test ! -e /home/lfr/kernelcode_generate/wt-20260428-archive-symbol-buffer-hoist-plan/expectation` -> `NO_EXPECTATION`
- `git -C /home/lfr/kernelcode_generate/wt-20260428-archive-symbol-buffer-hoist-plan diff --check` -> 通过
Diff 反推自测：
- 当前实际 diff 只包含：
  - [`20260428-archive-symbol-buffer-hoist-plan.md`](/home/lfr/kernelcode_generate/wt-20260428-archive-symbol-buffer-hoist-plan/agents/codex-multi-agents/log/task_records/2026/17/20260428-archive-symbol-buffer-hoist-plan.md)
- 反推校验重点是：
  - surviving `done_plan` 已在 archive worktree 现场存在；
  - 当前 archive worktree 不包含 tracked 的活动计划路径；
  - `expectation` 只保留为归档正文中的历史 / 本地只读来源说明，未写入实际 diff；
  - `git diff --check` 通过。
合同验收（如适用）：未执行。本任务是归档 merge，且用户口径要求 `expectation` 只作为历史 / 本地只读合同来源说明；本轮未修改、移动、重命名或新建任何 `expectation` 文件。
自检：
- 本轮只补录归档任务记录，没有修改实现、测试、共享规则文件或 `expectation`。
- 归档承接正文直接复用现存 surviving `done_plan`，没有擅自重写 latest `main` 结论。
- 若主仓同步阶段被本地状态挡住，只记录阻塞，不覆盖现有改动。
结论：当前 archive merge 已按真实现场补录完成；提交时只包含本任务记录，并与现存 surviving `done_plan` 一并作为归档链 direct asset 进入主线。完成主线推送后执行 `-done`，后续由管理员按流程执行 `-done-plan`。
