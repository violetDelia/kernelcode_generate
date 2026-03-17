# 20260316-dsl-risk-review 记录

## 审查记录 T-20260316-4b3d7357

- 时间: 2026-03-16 22:10:00 +0800
- 角色: 巡检小队
- worktree: `wt-20260316-dsl-risk-review`
- worktree 状态:
  - 任务单指定 `wt-20260316-dsl-risk-review`
  - 当前仓库未创建该 worktree，本次仅基于主工作区进行只读审查
- 审查范围:
  - `spec/dsl/ast.md`
  - `spec/dsl/ir.md`
  - `spec/dsl/lowering.md`
  - `spec/dsl/ast_visitor.md`
  - `spec/dialect/nn.md`
- 测试:
  - 本次为 spec 风险审查，不涉及代码测试；未执行测试

结论: 不通过

问题清单:
- 高: `spec/dsl/ast.md`、`spec/dsl/ir.md`、`spec/dsl/lowering.md` 在当前主工作区缺失，但 `spec/dsl/ast_visitor.md` 明确依赖并引用这些文档。ASTVisitor 后续集成缺少上游 AST/IR/Lowering 规范，导致依赖关系与 API 语义无法对齐。
- 中: `spec/dsl/ast_visitor.md` 列出了多个核心 API（如 `parse_function_ast`、`visit_function`、`visit_to_ir` 等），但缺少对应 API 级示例，未满足“spec 中 API 必须提供示例”的新规则。
- 中: `spec/dialect/nn.md` 作为 `nn dialect` 设计规范，定义了关键类型与 verifier 约束，但未提供任何 API 使用示例，不满足“spec 中 API 必须提供示例”的新规则，容易造成实现和测试歧义。

影响范围:
- ASTVisitor 集成路径（函数 -> AST -> nn dialect IR -> MLIR 文本）缺少上游规范支撑，存在明显的实现阻塞风险。
- 新规则要求 API 示例的情况下，现有 spec 审查不可通过，会影响后续实现与测试复核。

为何不通过:
- 关键依赖 spec 缺失，无法完成依赖关系与语义一致性审查。
- 多处 API 缺少示例，违反最新 spec 规则。

建议改法:
- 补齐 `spec/dsl/ast.md`、`spec/dsl/ir.md`、`spec/dsl/lowering.md`，并明确与 `ast_visitor` 的依赖关系与数据流。
- 在 `spec/dsl/ast_visitor.md` 中为所有公开 API 补充最小可执行示例（典型输入、调用方式、预期行为）。
- 在 `spec/dialect/nn.md` 中补充 `NnMemoryType`、`NnMemorySpaceAttr`、`nn.add/nn.eq` 等 API 的最小示例，覆盖 parse/print 与 verifier 约束。

是否需要新建改进任务: 是

重构/改进任务建议:
1) 新建 spec：补齐 `spec/dsl/ast.md`
   - 背景: `ast_visitor` 引用但缺失，阻塞依赖审查
   - 范围: `spec/dsl/ast.md`
   - 影响: AST 节点结构、属性、类型/位置字段规范
   - 建议: 明确 AST 节点列表、字段、示例与与 IR/Loweing 对应关系
   - 优先级: 高
2) 新建 spec：补齐 `spec/dsl/ir.md` 与 `spec/dsl/lowering.md`
   - 背景: IR 结构与 AST->IR 规则缺失
   - 范围: `spec/dsl/ir.md`、`spec/dsl/lowering.md`
   - 影响: ASTVisitor 的下游输出语义与 lowering 行为
   - 建议: 定义 IR 节点、合法性、并给出 AST->IR 示例与规则
   - 优先级: 高
3) 规范补充：为 `spec/dsl/ast_visitor.md` 与 `spec/dialect/nn.md` 添加 API 示例
   - 背景: 新规则要求所有 API 必须有示例
   - 范围: `spec/dsl/ast_visitor.md`、`spec/dialect/nn.md`
   - 影响: 统一实现/测试预期，减少接口歧义
   - 建议: 为每个 API 提供最小示例与预期行为说明
   - 优先级: 中
