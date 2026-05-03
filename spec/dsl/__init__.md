# __init__.md

## 功能简介

- 固定 `kernel_gen.dsl`、`kernel_gen.dsl.ast.mlir_gen` 与 `kernel_gen.dsl.gen_kernel` 的包导出边界。
- 防止函数级 builder、显式解析环境 helper 或跨文件非公开 helper 通过包根暴露。
- 本文件只定义包级 facade 的公开导出；具体节点字段、emit 语义与 gen_kernel 语义由对应子 spec 承接。
- AST Node 类不从 `kernel_gen.dsl` 包根导出；需要节点类型时使用 `kernel_gen.dsl.ast`。

## API 列表

- `kernel_gen.dsl.parse_function(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> FunctionAST`
- `kernel_gen.dsl.ast.mlir_gen.mlir_gen(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> ModuleOp`
- `kernel_gen.dsl.gen_kernel.gen_kernel(obj: GenKernelInput, ctx: EmitCContext) -> str`
- `kernel_gen.dsl.gen_kernel.dsl_gen_kernel(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg, ctx: EmitCContext) -> str`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dsl/__init__.md`](../../spec/dsl/__init__.md)
- `功能实现`：
  - [`kernel_gen/dsl/__init__.py`](../../kernel_gen/dsl/__init__.py)
  - [`kernel_gen/dsl/ast/mlir_gen.py`](../../kernel_gen/dsl/ast/mlir_gen.py)
  - [`kernel_gen/dsl/gen_kernel/__init__.py`](../../kernel_gen/dsl/gen_kernel/__init__.py)
- `test`：[`test/dsl/test_package.py`](../../test/dsl/test_package.py)

## 依赖

- [`spec/dsl/ast/__init__.md`](../../spec/dsl/ast/__init__.md)：AST 包根导出合同。
- [`spec/dsl/ast/mlir_gen.md`](../../spec/dsl/ast/mlir_gen.md)：AST 侧 `mlir_gen(...)` 真实合同。
- [`spec/dsl/gen_kernel/gen_kernel.md`](../../spec/dsl/gen_kernel/gen_kernel.md)：源码生成入口合同。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 包根只导出本文件 `API 列表` 中列出的公开 API。
- `FunctionAST`、`ModuleAST`、`BlockAST`、`TensorAST`、`ScalarArgAST`、`VarAST`、`ConstAST`、`BinaryExprAST`、`CompareExprAST`、`Diagnostic`、`SourceLocation` 等 AST Node / 诊断类型不得从 `kernel_gen.dsl` 包根导出；统一从 `kernel_gen.dsl.ast` 使用。
- `kernel_gen.dsl.build_func_op`、`kernel_gen.dsl.build_func_op_from_ast`、`kernel_gen.dsl.ast.mlir_gen.build_func_op`、`kernel_gen.dsl.ast.mlir_gen.build_func_op_from_ast`、`kernel_gen.dsl.ast.parser.parse_function_with_env`、`kernel_gen.dsl.ast.mlir_gen.emit`、`kernel_gen.dsl.AstVisitor`、`kernel_gen.dsl.EmitContext`、`kernel_gen.dsl.emit_mlir` 均不是公开 API，包根不得重新导出。
- `kernel_gen.dsl.ast.emit_context`、`kernel_gen.dsl.ast.emit_nn` 与 `kernel_gen.dsl.ast.mlir_context` 已删除，不得作为兼容 facade 恢复。
- 下划线 helper、实现拆分函数、内部 parser 环境函数不得进入 `__all__`。
- 测试不得通过 `from module import private_name`、反射或跨文件直接调用非公开 helper 形成隐式 API。
- `kernel_gen.dsl.mlir_gen`、`kernel_gen.dsl.mlir_gen.emit`、`kernel_gen.dsl.mlir_gen.emit.core`、`kernel_gen.dsl.emit_mlir`、`kernel_gen.dsl.ast.visitor` 已删除，不得作为兼容 facade 恢复；旧深层私有导入路径也不提供兼容。
## API详细说明

### `kernel_gen.dsl.parse_function(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> FunctionAST`

- api：`kernel_gen.dsl.parse_function(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> FunctionAST`
- 参数：
  - `fn`：可调用对象，作为 DSL 构建、执行或包装入口的主体；类型 `Callable[..., DslFunctionReturn]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `runtime_args`：运行期实参序列，与 DSL 函数形参按顺序对应；类型 `DslRuntimeArg`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`FunctionAST`。
- 使用示例：

  ```python
  dsl = dsl
  result = dsl.parse_function(fn=fn, runtime_args=runtime_args)
  ```
- 功能说明：解析 `function`。
- 注意事项：输入解析、执行失败和校验失败必须通过本条目声明的返回值或公开错误文本表达。

### `kernel_gen.dsl.ast.mlir_gen.mlir_gen(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> ModuleOp`

- api：`kernel_gen.dsl.ast.mlir_gen.mlir_gen(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> ModuleOp`
- 参数：
  - `fn`：可调用对象，作为 DSL 构建、执行或包装入口的主体；类型 `Callable[..., DslFunctionReturn]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `runtime_args`：运行期实参序列，与 DSL 函数形参按顺序对应；类型 `DslRuntimeArg`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ModuleOp`。
- 使用示例：

  ```python
  mlir_gen = mlir_gen
  result = mlir_gen.mlir_gen(fn=fn, runtime_args=runtime_args)
  ```
- 功能说明：执行 `mlir_gen`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `kernel_gen.dsl.gen_kernel.gen_kernel(obj: GenKernelInput, ctx: EmitCContext) -> str`

- api：`kernel_gen.dsl.gen_kernel.gen_kernel(obj: GenKernelInput, ctx: EmitCContext) -> str`
- 参数：
  - `obj`：`obj` 输入值，参与 `gen_kernel` 的公开处理流程；类型 `GenKernelInput`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `EmitCContext`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`str`，表示生成或格式化后的文本。
- 使用示例：

  ```python
  gen_kernel = gen_kernel
  result = gen_kernel.gen_kernel(obj=obj, ctx=ctx)
  ```
- 功能说明：执行 `gen_kernel`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `kernel_gen.dsl.gen_kernel.dsl_gen_kernel(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg, ctx: EmitCContext) -> str`

- api：`kernel_gen.dsl.gen_kernel.dsl_gen_kernel(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg, ctx: EmitCContext) -> str`
- 参数：
  - `fn`：可调用对象，作为 DSL 构建、执行或包装入口的主体；类型 `Callable[..., DslFunctionReturn]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `runtime_args`：运行期实参序列，与 DSL 函数形参按顺序对应；类型 `DslRuntimeArg`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `EmitCContext`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`str`，表示生成或格式化后的文本。
- 使用示例：

  ```python
  gen_kernel = gen_kernel
  result = gen_kernel.dsl_gen_kernel(fn=fn, runtime_args=runtime_args, ctx=ctx)
  ```
- 功能说明：执行 `dsl_gen_kernel`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

## 测试

- 测试文件：`test/dsl/test_package.py`
- 执行命令：`pytest -q test/dsl/test_package.py`

### 测试目标

- 包根导出、AST `mlir_gen(...)` 导出和旧 facade / 旧深层私有导入路径拒绝边界保持稳定。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-001 | 公开入口 | DSL package public exports | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_dsl_package_public_exports`。 | 公开入口在“DSL package public exports”场景下可导入、构造、注册或按名称发现。 | `test_dsl_package_public_exports` |
| TC-DSL-002 | 边界/异常 | gen kernel package public exports and legacy rejection | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_package_public_exports_and_legacy_rejection`。 | “gen kernel package public exports and legacy rejection”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_package_public_exports_and_legacy_rejection` |
| TC-DSL-003 | 公开入口 | MLIR gen package public exports | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_mlir_gen_package_public_exports`。 | 公开入口在“MLIR gen package public exports”场景下可导入、构造、注册或按名称发现。 | `test_mlir_gen_package_public_exports` |
| TC-DSL-004 | 边界/异常 | removed legacy DSL facades reject import | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_removed_legacy_dsl_facades_reject_import`。 | “removed legacy DSL facades reject import”场景按公开错误语义失败或被拒绝。 | `test_removed_legacy_dsl_facades_reject_import` |
