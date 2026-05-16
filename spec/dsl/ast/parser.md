# DSL AST Parser

## 功能简介

- `kernel_gen.dsl.ast.parser` 提供 Python DSL 函数到 `FunctionAST` 的公开解析入口。
- parser 不读取 Python annotation 作为 DSL 类型来源，所有输入类型由 `runtime_args` 决定。
- parser 支持 `memory.get_shape()` 的解包与索引访问；不支持 `memory.get_shape(dim)` 或 `memory.getshape(dim)`。
- parser 支持 `kernel_gen.operation.kernel` out-first helper 语句，生成 kernel AST 节点。

## API 列表

- `parse_function(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> FunctionAST`

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：`spec/dsl/ast/parser.md`
- `功能实现`：`kernel_gen/dsl/ast/parser.py`
- `test`：`test/dsl/ast/test_parser.py`

## 依赖

- `spec/dsl/ast/dsl_ast.md`：`DslAstVisitor`。
- `spec/dsl/ast/nodes/basic.md`：`ModuleAST` 与 `FunctionAST`。

## API详细说明

### `parse_function(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> FunctionAST`

- api：`parse_function(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> FunctionAST`
- 参数：
  - `fn`：Python DSL 函数；必须可调用。
  - `runtime_args`：显式运行时参数。
- 返回值：唯一 `FunctionAST`。
- 使用示例：

  ```python
  func_ast = parse_function(kernel, lhs)
  ```
- 功能说明：读取 `fn` 源码，解析为 Python AST，再用 `DslAstVisitor` 生成 DSL AST，并返回 module 中唯一函数。
- 注意事项：解析结果不是唯一函数时必须报 `parse_function expects exactly one function`。

## 测试

- 测试文件：`test/dsl/ast/test_parser.py`
- 执行命令：`pytest -q test/dsl/ast/test_parser.py`

### 测试目标

- 公开 `parse_function(...)` 入口、runtime args 类型推断、annotation 忽略、稳定错误，以及旧 `parse(...)` 删除边界。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-AST-PARSER-001 | 解析/打印 | parse function basic assignment | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_function_basic_assignment`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_function_basic_assignment` |
| TC-DSL-AST-PARSER-002 | 解析/打印 | parse function for loop | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_function_for_loop`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_function_for_loop` |
| TC-DSL-AST-PARSER-003 | 解析/打印 | parse function if else | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_function_if_else`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_function_if_else` |
| TC-DSL-AST-PARSER-004 | 解析/打印 | parse_function infers runtime annotation | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_infers_runtime_annotation`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_infers_runtime_annotation` |
| TC-DSL-AST-PARSER-005 | 解析/打印 | parse function reports diagnostics | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_function_reports_diagnostics`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_function_reports_diagnostics` |
| TC-DSL-AST-PARSER-006 | 边界/异常 | parse function step zero rejected | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_parse_function_step_zero_rejected`。 | “parse function step zero rejected”场景按公开错误语义失败或被拒绝。 | `test_parse_function_step_zero_rejected` |
| TC-DSL-AST-PARSER-007 | 解析/打印 | ast parse function uses runtime memory not annotation | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_ast_parse_function_uses_runtime_memory_not_annotation`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_ast_parse_function_uses_runtime_memory_not_annotation` |
| TC-DSL-AST-PARSER-008 | 边界/异常 | ast parse requires runtime args for parameters | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_ast_parse_requires_runtime_args_for_parameters`。 | “ast parse requires runtime args for parameters”场景按公开错误语义失败或被拒绝。 | `test_ast_parse_requires_runtime_args_for_parameters` |
| TC-DSL-AST-PARSER-009 | 边界/异常 | old parse public entry removed | 导入 `kernel_gen.dsl.ast` 与 `kernel_gen.dsl.ast.parser`。 | 运行 `test_ast_parse_public_entry_removed`。 | 旧 `parse(...)` 在包根和 parser 模块中均不可达。 | `test_ast_parse_public_entry_removed` |
| TC-DSL-AST-PARSER-010 | 解析/打印 | parse function ignores formatted tensor annotation arithmetic variants | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_function_ignores_formatted_tensor_annotation_arithmetic_variants`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_function_ignores_formatted_tensor_annotation_arithmetic_variants` |
| TC-DSL-AST-PARSER-011 | 解析/打印 | parse function ignores unsupported formatted tensor annotations | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_function_ignores_unsupported_formatted_tensor_annotations`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_function_ignores_unsupported_formatted_tensor_annotations` |
| TC-DSL-AST-PARSER-012 | 解析/打印 | parse function ignores direct tensor annotation expression element | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_function_ignores_direct_tensor_annotation_expression_element`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_function_ignores_direct_tensor_annotation_expression_element` |
| TC-DSL-AST-PARSER-013 | 解析/打印 | parse function uses runtime symboldim over union annotation | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_function_uses_runtime_symboldim_over_union_annotation`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_function_uses_runtime_symboldim_over_union_annotation` |
| TC-DSL-AST-PARSER-014 | 解析/打印 | parse function ignores unsupported union annotation | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_function_ignores_unsupported_union_annotation`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_function_ignores_unsupported_union_annotation` |
| TC-DSL-AST-PARSER-015 | 解析/打印 | parse kernel out-first helper | 准备公开 `kernel_gen.operation.kernel` helper、`Memory` 与 `SymbolDim` runtime 参数。 | 运行 `test_kernel_plugin_parse_function_builds_statement_nodes`。 | `kernel.add`、`kernel.matmul` 与 `kernel.img2col*` 解析为对应 statement AST；非 API keyword 或字符串 kind 被拒绝。 | `test_kernel_plugin_parse_function_builds_statement_nodes` |
