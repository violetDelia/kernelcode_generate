# 20260321-spec-include-api-memory

## T-20260321-00c933f0

- 时间：2026-03-21 11:40:20 +0800
- 角色：`咯咯咯`
- worktree：`/home/lfr/kernelcode_generate/wt-20260321-spec-include-api-memory`
- 任务描述：修正 `spec/include/api/Memory.md`，明确 API 无实现/无测试口径并按 AGENTS.md 结构收敛。
- 变更文件：
  - `spec/include/api/Memory.md`
- 测试：
  - 未执行（spec 口径修正不涉及测试）。

## T-20260321-0a1d7c2e

- 时间：2026-03-21 11:42:10 +0800
- 角色：`咯咯咯`
- worktree：`/home/lfr/kernelcode_generate/wt-20260321-spec-include-api-memory`
- 任务描述：合并 `spec/include/api/Memory.md` 并删除 `spec/include/cpu/Memory.md`。
- 提交：`f02e162`
- 变更文件：
  - `spec/include/api/Memory.md`
  - `spec/include/cpu/Memory.md`
- 风险：
  - 提交中夹带了与本任务无关的文件改动（见提交统计），需要管理员确认是否拆分或回退。
- 测试：
  - 未执行（合并任务不涉及测试）。
