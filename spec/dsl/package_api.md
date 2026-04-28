# package_api.md

## 功能简介

- 定义 `kernel_gen.dsl` package-root 的公开 facade 合同。
- 只回答三件事：包根稳定导出哪些名字、这些名字分别落到哪些 sibling spec、以及哪些子模块入口不能从包根假定可达。
- 为 `build_func_op(...)` 这类经由包根导入的 DSL 消费者提供单一真源，避免后续实现、测试和只读合同资产各自维护第二份导出列表。

## API 列表

- `AstVisitor(config: dict[str, object] | None = None)`
- `AstVisitorError(message: str, location: SourceLocation | None = None)`
- `BinaryExprAST(op: str, lhs: object, rhs: object, location: SourceLocation | None = None)`
- `BlockAST(statements: list[object], location: SourceLocation | None = None)`
- `CompareExprAST(op: str, lhs: object, rhs: object, location: SourceLocation | None = None)`
- `ConstAST(value: object, location: SourceLocation | None = None)`
- `Diagnostic(message: str, location: SourceLocation | None = None)`
- `EmitContext(builder: Block, symbols: dict[str, object], types: dict[int, object], config: dict[str, object] | None = None)`
- `FunctionAST(name: str, inputs: list[TensorAST | ScalarArgAST | PtrArgAST], outputs: list[TensorAST | ScalarArgAST], body: BlockAST, location: SourceLocation | None = None, source: str | None = None, py_ast: object | None = None, diagnostics: list[Diagnostic] = ..., has_explicit_return: bool = False, has_return_annotation: bool = False, returns_none: bool = False)`
- `ModuleAST(functions: list[FunctionAST])`
- `ScalarArgAST(name: str, value_type: type, is_symbolic: bool = False, location: SourceLocation | None = None)`
- `SourceLocation(line: int, column: int)`
- `TensorAST(name: str, memory: object, location: SourceLocation | None = None)`
- `VarAST(name: str, location: SourceLocation | None = None)`
- `parse_function(fn: Callable[..., object]) -> FunctionAST`
- `emit_mlir(node: object, ctx: EmitContext) -> object`
- `build_func_op(fn: Callable[..., object], *runtime_args: object, globals: dict[str, object] | None = None, builtins: dict[str, object] | object | None = None) -> func.FuncOp`
- `build_func_op_from_ast(func_ast: FunctionAST, runtime_args: tuple[object, ...] | list[object] | None = None, config: dict[str, object] | None = None) -> func.FuncOp`

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/dsl/package_api.md`](../../spec/dsl/package_api.md)
- `功能实现`：[`kernel_gen/dsl/__init__.py`](../../kernel_gen/dsl/__init__.py)
- `test`：
  - [`test/dsl/test_package_api.py`](../../test/dsl/test_package_api.py)
  - [`test/dsl/ast/test_package.py`](../../test/dsl/ast/test_package.py)

## 依赖

- [`spec/dsl/ast/__init__.md`](../../spec/dsl/ast/__init__.md)：AST facade 的公开入口与导出边界。
- [`spec/dsl/ast/visitor.md`](../../spec/dsl/ast/visitor.md)：`AstVisitor` / `AstVisitorError` 合同。
- [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)：`EmitContext` / `emit_mlir(...)` 合同。
- [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)：`build_func_op(...)` / `build_func_op_from_ast(...)` 合同。

## 目标

- 为 `kernel_gen.dsl` 包根提供稳定导入集合，避免上层实现和测试散落子模块路径假设。
- 明确 `build_func_op(...)` / `build_func_op_from_ast(...)` 经由包根公开，而 `mlir_gen(...)` 继续只保留在 `kernel_gen.dsl.mlir_gen` 子模块。
- 明确 AST facade、visitor facade 与 MLIR builder facade 在包根的拼装顺序，避免包根继续膨胀为第二层工具入口。

## 限制与边界

- `kernel_gen.dsl` 包根只承认本文件 `API 列表` 中列出的公开名字；未列出的类、函数、模块别名、helper、环境控制入口和 sibling package 能力都不是包根公开 API。
- `kernel_gen.dsl` 包根不公开：
  - `mlir_gen(...)`
  - `EmitCContext` / `EmitCError`
  - `emit_c(...)` / `emit_c_op(...)` / `emit_c_value(...)`
  - `gen_kernel(...)`
  - `parse_function_with_env(...)`
  - `kernel_gen.dsl.ast.visitor` / `kernel_gen.dsl.mlir_gen.emit` / `kernel_gen.dsl.gen_kernel` 的任何文件级 helper
- `build_func_op(...)` 与 `build_func_op_from_ast(...)` 在包根公开，`mlir_gen(...)` 不在包根公开；需要 module 级 IR 入口的调用方必须显式走 `kernel_gen.dsl.mlir_gen.mlir_gen(...)`。
- `kernel_gen.dsl` 包根只做 facade 重导出，不维护第二份 AST / visitor / emit / builder 逻辑，也不替 sibling spec 重写异常、边界或参数规则。
- 其他模块与测试只允许通过本文件列出的包根入口消费 `kernel_gen.dsl`；不得跨文件直连包根未列出的同目录实现 helper，再把它们当成稳定合同。

## 公开导出矩阵

| 包根名字 | 真源 spec | 说明 |
| --- | --- | --- |
| `AstVisitor` / `AstVisitorError` | [`spec/dsl/ast/visitor.md`](../../spec/dsl/ast/visitor.md) | visitor facade |
| `BinaryExprAST` / `BlockAST` / `CompareExprAST` / `ConstAST` / `Diagnostic` / `FunctionAST` / `ModuleAST` / `ScalarArgAST` / `SourceLocation` / `TensorAST` / `VarAST` / `parse_function(...)` | [`spec/dsl/ast/__init__.md`](../../spec/dsl/ast/__init__.md) | AST facade |
| `EmitContext` / `emit_mlir(...)` | [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md) | emit facade |
| `build_func_op(...)` / `build_func_op_from_ast(...)` | [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) | `func.func` builder facade |

## 测试

- 测试文件：
  - [`test/dsl/test_package_api.py`](../../test/dsl/test_package_api.py)
  - [`test/dsl/ast/test_package.py`](../../test/dsl/ast/test_package.py)
- 执行命令：`pytest -q test/dsl/test_package_api.py test/dsl/ast/test_package.py`
- 测试目标：
  - `kernel_gen.dsl` 包根导出集合与 `__all__` 保持稳定
  - `build_func_op(...)` / `build_func_op_from_ast(...)` 可经由包根导入
  - `mlir_gen(...)`、`EmitCContext`、`gen_kernel(...)`、`parse_function_with_env(...)` 等非包根入口不会被错误暴露到 `kernel_gen.dsl`
  - 测试只通过包根公开导入验收，不直连包根未列出的非公开 helper
