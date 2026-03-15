# farmat-migration-refactor-20260315 记录

## 任务记录 T-20260315-c6ba9bd1

- 时间: 2026-03-15 23:10:00 +0800
- 角色: 巡检小队（临时授权承担 spec 规划）
- 任务类型: spec
- worktree: `wt-20260315-farmat-migration-refactor`
- worktree 状态:
  - 任务单指定了 `wt-20260315-farmat-migration-refactor`
  - 当前仓库中未创建该 worktree，`git worktree list` 未发现对应项
  - 本次 spec 产出在主工作区完成，未修改实现代码
- 范围:
  - `symbol_variable/type.py`
  - `spec/symbol_variable/memory.md`
- 产出文件:
  - `spec/symbol_variable/farmat_migration.md`
- 变更摘要:
  - 新增 `Farmat` 命名债务兼容迁移规范
  - 明确规范新名 `Format` 与旧兼容名 `Farmat`
  - 定义兼容期、移除期、异常规则与测试要求
  - 明确本方案不覆盖包根导出策略，避免与并行任务冲突
