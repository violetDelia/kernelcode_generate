
## T-20260316-74a25430

- 时间：2026-03-16 04:30:00 +0800
- 角色：`摸鱼小分队`
- 任务描述：在 `wt-20260316-dsl-ir-lowering-spec` 补齐 `spec/dsl/ir.md` 与 `spec/dsl/lowering.md`，定义 AST->IR 数据流、IR 结构、`ScalarArgAST` / `TensorAST` 到 `func.func` 签名的 lowering 规则，并为相关 API / 规则补齐示例。
- worktree：`wt-20260316-dsl-ir-lowering-spec`
- 产出文件：
  - `spec/dsl/ir.md`
  - `spec/dsl/lowering.md`
- 变更摘要：
  - 指定 worktree 初始不存在，已创建：`wt-20260316-dsl-ir-lowering-spec`。
  - 重写 `ir.md`，明确 `ModuleAST` / `FunctionAST` / `TensorAST` / `ScalarArgAST` 到 `IRModule` / `IRFunction` / `IRBuffer` / `IRScalarArg` 的数据流关系，以及 `IRBlock`、`IRFor`、`IRLoad`、`IRStore`、`IRBinary`、`IRCompare` 等 IR 结构。
  - 重写 `lowering.md`，明确 `validate_ast(ast)`、`lower_ast(ast)` 的职责，补充 `TensorAST` / `ScalarArgAST` 到 `func.func` 参数的签名规则，并定义名称解析、元信息传递与错误边界。
  - 为文档中定义的相关 API 和规则补齐实际示例，覆盖 AST 输入示例、IR 结构示例、`func.func` 签名示例与错误示例。
- 测试说明：
  - 本任务仅修改 spec，未改动实现与测试；管理员未要求跑测，因此未执行测试。

## T-20260316-74a25430

- 时间：2026-03-16 04:34:00 +0800
- 角色：`摸鱼小分队`
- 任务描述：在 `wt-20260316-dsl-ir-lowering-spec` 补齐 `spec/dsl/ir.md` 与 `spec/dsl/lowering.md`，定义 AST->IR 数据流、IR 结构、`ScalarArgAST`/`TensorAST` 到 `func.func` 签名的 lowering 规则，并为相关 API/规则补齐示例。
- worktree：`wt-20260316-dsl-ir-lowering-spec`
- 产出文件：
  - `spec/dsl/ir.md`
  - `spec/dsl/lowering.md`
- 变更摘要：
  - 指定 worktree 初始不存在，已创建：`wt-20260316-dsl-ir-lowering-spec`。
  - 重写 `ir.md`，补清 AST->IR 数据流、IR 节点结构、`IRFunction`/`IRBuffer`/`IRScalarArg` 与 `func.func` 的对应关系。
  - 重写 `lowering.md`，补清 `validate_ast`/`lower_ast` 入口、签名 lowering、节点 lowering、名称解析、错误规则以及 `TensorAST`/`ScalarArgAST` 到 `func.func` 参数的映射约束。
  - 为文档内定义的关键 API 与规则补齐实际示例，覆盖 `IRModule`、`IRFunction`、`IRBuffer`、`IRScalarArg`、`IRLoad`、`IRStore`、`IRBinary`、`IRCompare` 以及 `func.func` 签名示例。
- 测试说明：
  - 本任务仅修改 spec，未改动实现与测试；管理员未要求跑测，因此未执行测试。
