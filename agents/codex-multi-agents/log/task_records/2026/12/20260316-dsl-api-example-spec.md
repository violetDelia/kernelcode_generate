# 20260316-dsl-api-example-spec 记录

## 任务记录 T-20260316-f01f0a21

- 时间: 2026-03-16 22:25:00 +0800
- 角色: 巡检小队（临时授权处理 spec 补充）
- 任务类型: spec
- worktree: `wt-20260316-dsl-api-example-spec`
- worktree 状态:
  - 任务单指定 `wt-20260316-dsl-api-example-spec`
  - 当前仓库未创建该 worktree，本次在主工作区完成 spec 补充
- 范围:
  - `spec/dsl/ast_visitor.md`
  - `spec/dialect/nn.md`
- 产出文件:
  - `spec/dsl/ast_visitor.md`
  - `spec/dialect/nn.md`
- 变更摘要:
  - 为 `parse_function_ast` / `visit_function` / `visit_to_ir` / `visit_to_nn_ir` / `emit_mlir` 补充最小 API 示例与预期行为说明
  - 为 `NnMemorySpaceAttr` / `NnMemoryType` / `nn.add` / `nn.eq` 补充最小 API 示例与 verifier 约束说明
- 测试:
  - 本任务为 spec 补充，不涉及代码测试；未执行测试
