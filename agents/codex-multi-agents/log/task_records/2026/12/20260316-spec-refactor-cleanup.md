
## T-20260316-63af31d2

- 时间：2026-03-16 04:06:00 +0800
- 角色：`睡觉小分队`
- 任务描述：在 `wt-20260316-spec-refactor-cleanup` 统一检查 `symbol_variable` 相关 spec 中残留的重构过程、迁移步骤等非设计文档信息，并按当前规则清理为面向单实现文件的设计文档。
- worktree：`wt-20260316-spec-refactor-cleanup`
- 产出文件：
  - `spec/symbol_variable/memory.md`
  - `spec/symbol_variable/symbol_dim.md`
  - `spec/symbol_variable/symbol_shape.md`
  - `spec/symbol_variable/type.md`
- 删除文件：
  - `spec/symbol_variable/farmat_migration.md`
- 变更摘要：
  - 清理 `memory.md`、`symbol_dim.md`、`symbol_shape.md`、`type.md` 中带有“迁移后”“本次规则”“Compat 说明”等过程性表述，改写为稳定的公开模块路径与功能边界描述。
  - 删除 `farmat_migration.md`，原因是其内容为迁移/阶段方案文档，且不满足“单实现文件对应单份设计文档”的当前规则。
  - 保留 `package_api.md` 作为 `python/symbol_variable/__init__.py` 的单文件设计文档，不扩展到实现或测试改动。
- worktree 说明：
  - 指定 worktree 初始不存在，已创建：`wt-20260316-spec-refactor-cleanup`。
- 测试说明：
  - 本任务仅修改 spec，管理员已明确“不需要额外跑测”，因此未执行测试。
