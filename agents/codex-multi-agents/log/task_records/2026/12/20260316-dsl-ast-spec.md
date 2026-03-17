# 20260316-dsl-ast-spec 记录

## T-20260316-58ea8d3f

- 时间：2026-03-16 22:28:54 +0800
- 角色：规格小队
- 任务描述：补齐 `spec/dsl/ast.md`，定义 AST 节点结构、字段、位置元信息、输入节点与 IR/Lowering 关系，并为所有公开 API/节点类型补齐示例。
- worktree：`wt-20260316-dsl-ast-spec`
- 产出文件：`spec/dsl/ast.md`
- 变更摘要：
  - 重写 AST 节点定义与字段说明，补充 `SourceRange` 位置元信息约定。
  - 为每个节点类型提供示例与预期结果说明，并补充 DSL 映射示例。
  - 明确与 IR/Lowering 的关系及对应示例。
- 范围说明：
  - 本次仅修改 spec，未改动实现与测试。
