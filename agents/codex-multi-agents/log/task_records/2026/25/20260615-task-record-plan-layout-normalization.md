时间：2026-06-15 00:00 +0800
经办人：神秘人
任务：task-record-plan-layout-normalization
任务目标：整理 `agents/task_records` 与 `agents/codex-multi-agents/log/task_records/done_plan` 中未按 `<YYYY>/<WW>/...` 规范落位的任务记录和归档计划，并更新标准文档、角色提示词和防回归检查。

执行前阅读记录：
- 已读根 `AGENTS.md` 中任务记录、计划流转、提示词 / 标准文档权限、`.skills` 与 `expectation/` 禁止修改面。
- 已读 `agents/codex-multi-agents/agents/神秘人/神秘人.prompt.md` 中管理员记录、归档和任务状态职责。
- 已读 `agents/standard/agents目录规则.md`、`agents/standard/任务记录约定.md`、`agents/standard/合并规范.md` 与 `agents/standard/协作执行通用规则.md` 中记录落点和合并归档规则。

改动摘要：
- 将旧落点 `agents/task_records/20260603-memory-plan-auto-pad.md` 迁移到 `agents/codex-multi-agents/log/task_records/2026/23/20260603-memory-plan-auto-pad.md`。
- 将直接落在 `agents/codex-multi-agents/log/task_records/done_plan/2026/*.md` 的 21 个归档计划迁移到 `done_plan/2026/23/` 或 `done_plan/2026/24/`，目标周目录按对应任务记录周或文件日期推断。
- 更新 `AGENTS.md`、`agents/standard/agents目录规则.md`、`任务记录约定.md`、`协作执行通用规则.md`、`合并规范.md`、`任务新建模板.md`、`计划书标准.md`，明确任务记录为 `task_records/<YYYY>/<WW>/<record>.md`，计划归档为 `done_plan/<YYYY>/<WW>/<plan>.md`。
- 更新 `神秘人`、`李白`、`榕`、`大闸蟹`、`守护最好的爱莉希雅` 提示词，去掉 `done_plan/2026/<name>.md` 旧口径，改为 `<YYYY>/<WW>` 规范归档。
- 新增 `test/repo_conformance/test_task_record_layout.py`，用 `git ls-files` 阻止 `agents/task_records/`、`task_records/<YYYY>/*.md`、`done_plan/<YYYY>/*.md` 旧落点进入 tracked 文件。

Diff 反推自测：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_task_record_layout.py`：1 passed。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py -k "current_diff"`：2 passed, 3 deselected。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile test/repo_conformance/test_task_record_layout.py`：通过。
- `git diff --check && git diff --cached --check`：通过。

布局核对：
- `find agents/task_records -type f -print`：无输出。
- `find agents/codex-multi-agents/log/task_records/done_plan -maxdepth 2 -type f -print`：无输出，说明没有文件直接落在 `done_plan/<YYYY>/`。
- `find agents/codex-multi-agents/log/task_records/2026 -maxdepth 1 -type f -print`：无输出，说明没有文件直接落在 `task_records/<YYYY>/`。
- `rg -n "done_plan/2026|/done_plan/2026" AGENTS.md agents/standard agents/codex-multi-agents/agents`：无旧字面路径残留；当前只保留 `<YYYY>/<WW>` 规范描述。

敏感范围核对：
- `git diff --cached --name-status -- .skills expectation TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：无输出。
- `git diff --name-status -- .skills expectation TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：无输出。
- 未修改 `.skills/`、`expectation/`、`TODO.md`、`DONE.md`、`agents/codex-multi-agents/agents-lists.md`。

已知未运行 / 限制：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py` 全量运行在 120 秒内超时；已补跑与当前 diff 相关的 `-k current_diff` 子集并通过。超时未作为通过证据。

既有无关现场：
- 主仓存在既有 unstaged 删除：`ARCHITECTURE/plan/cuda_sm86_emit_package_structure_refactor_green_plan.md`、`ARCHITECTURE/plan/symbol_hoist_pipeline_pass_green_plan.md`、`kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer-analysis-if-path-expected.mlir`。本任务未修改、未恢复、未暂存这些无关现场。

减法检查：
- 删除的是旧路径落点，不删除记录内容；所有迁移文件为 `R100` 重命名，内容未变。
- 移除提示词中的旧 `done_plan/2026/<name>.md` 指导，保留计划归档流程本身。
- 新增 conformance 只检查 tracked 文件路径，不改变任务脚本语义或状态文件格式。

自检：
- 任务目标可落地：已完成路径迁移、规范更新、提示词更新和防回归测试。
- 记录路径符合新规范：本记录位于 `agents/codex-multi-agents/log/task_records/2026/25/20260615-task-record-plan-layout-normalization.md`。
- 禁止修改面已核对为空 diff；未触碰业务实现、业务测试、`.skills` 或 `expectation`。
- 残余风险：历史归档正文中可能保留当时的旧路径叙述，本轮只修当前规范、角色提示词和实际 tracked 文件落点，不改历史记录正文。

结论：整理完成，可进入后续审查 / 合并；后续新建任务或计划归档必须使用 `<YYYY>/<WW>` 路径。
