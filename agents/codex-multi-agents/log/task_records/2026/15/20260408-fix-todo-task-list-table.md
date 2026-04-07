时间：2026-04-08 04:10:00 +0800
经办人：李白
任务：T-20260408-c5eec1dd（repo维护：修复 TODO.md 任务列表表格）

## 任务目标
- 修复 `TODO.md` 中 `## 任务列表` 表格的格式损坏（`T-20260408-b6c3b12e` 被拆成多行，导致脚本无法解析任务行）。
- 验收：`./skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file TODO.md -status -task-list` 能输出任务行（不止表头）。

## 问题定位
- 现象：执行 `-status -task-list` 仅输出表头与分隔线，不输出任何任务行。
- 原因：`TODO.md` 的 `## 任务列表` 中存在非表格行（多行 bullet/说明），使该 section 的表格解析结果为空。

## 修复说明
- 将 `T-20260408-b6c3b12e` 的多行残留内容收敛为单行表格行（仅保留 7 列：任务 ID/发起人/创建时间/worktree/描述/指派/记录文件），移除多余的非 pipe 行。

## 复核命令与摘要
- 复核命令：
  - `./skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file TODO.md -status -task-list`
- 预期：
  - 输出除表头外至少 1 行任务数据（以 `| T-... |` 开头的表格行）。
- 实际输出摘要：
  - 成功输出 1 行任务数据（`T-20260408-b6c3b12e`）。
- 实际输出：
  ```text
  | 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 指派 | 记录文件 |
  | --- | --- | --- | --- | --- | --- | --- |
  | T-20260408-b6c3b12e | 神秘人 | 2026-04-08 01:07:07 +0800 | wt-20260408-nn-mlir-lowering-s3b5 | 收口任务：nn_mlir_gen_lowering_expectation_green_plan S3B-5(gt)，nn.gt -> kernel.gt | 李白 | agents/codex-multi-agents/log/task_records/2026/15/20260408-nn-mlir-lowering-s3b5.md |
  ```

## 改动文件
- `TODO.md`
- `agents/codex-multi-agents/log/task_records/2026/15/20260408-fix-todo-task-list-table.md`
