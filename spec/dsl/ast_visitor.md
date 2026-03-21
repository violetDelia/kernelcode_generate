# ast_visitor.md

## 功能简介

- 定义 AST 访问器，用于遍历 `FunctionAST` 并驱动节点转换。
- 访问器在遍历过程中调用 `emit_mlir` 中定义的节点发射逻辑。
- 不负责 Python 函数解析与 MLIR 文本输出。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
- `功能实现`：[`kernel_gen/dsl/ast_visitor.py`](../../kernel_gen/dsl/ast_visitor.py)
- `test`：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)

## 依赖

- AST 节点定义与解析入口：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- 节点发射规范：[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)

## 术语

- `AstVisitor`：AST 遍历器，负责节点分发与顺序控制。
- `EmitContext`：发射上下文结构。
- `AstVisitorError`：访问器阶段错误类型。

## 目标

- 以确定性顺序遍历 AST。
- 维护局部变量到已生成值的映射。
- 将节点交由 `emit_mlir` 进行 MLIR op/value 生成。

## 限制与边界

- 不解析 Python 函数源码；解析入口由 `ast.parse_function(...)` 提供。
- 不定义任何节点的 MLIR 生成细节；仅负责遍历与分发。
- 不生成 MLIR 文本，不负责 module 封装。

## 公开接口

### `AstVisitor(config=None)`

功能说明：

- 创建 AST 遍历器实例。
- `config` 用于控制遍历行为（例如是否保留源位置信息）。

参数说明：

- `config` (`dict|None`)：可选配置。

使用示例：

```python
visitor = AstVisitor(config={"keep_location": True})
```

注意事项：

- 配置项的语义由实现与测试清单约束。

返回与限制：

- 返回 `AstVisitor` 实例。

### `AstVisitor.visit_function(func_ast, ctx)`

功能说明：

- 遍历 `FunctionAST`，按语句顺序生成节点对应的 MLIR op/value。
- 负责建立初始符号表（参数绑定）。

参数说明：

- `func_ast` (`FunctionAST`)：函数 AST 根节点。
- `ctx` (`EmitContext`)：发射上下文。

使用示例：

```python
result = visitor.visit_function(func_ast, ctx)
```

注意事项：

- 必须保证语句遍历顺序与 AST 一致。

返回与限制：

- 返回值包含函数返回值或已生成的 op/value（具体结构由实现约束）。

### `AstVisitor.visit_block(block_ast, ctx)`

功能说明：

- 依次遍历 `BlockAST.statements` 并发射对应 op/value。

参数说明：

- `block_ast` (`BlockAST`)：语句块。
- `ctx` (`EmitContext`)：发射上下文。

使用示例：

```python
visitor.visit_block(func_ast.body, ctx)
```

注意事项：

- 语句块内的名字解析必须复用已有映射。

返回与限制：

- 无显式返回值或返回最后一条语句的结果（以实现为准）。

### `AstVisitor.visit_stmt(stmt, ctx)`

功能说明：

- 访问语句节点并分发到对应的 `emit_mlir` 逻辑。

参数说明：

- `stmt` (`object`)：语句节点。
- `ctx` (`EmitContext`)：发射上下文。

使用示例：

```python
visitor.visit_stmt(stmt_ast, ctx)
```

注意事项：

- 不支持的语句必须抛出 `AstVisitorError`。

返回与限制：

- 语句节点通常不返回值。

### `AstVisitor.visit_expr(expr, ctx)`

功能说明：

- 访问表达式节点并返回对应的 MLIR value。

参数说明：

- `expr` (`object`)：表达式节点。
- `ctx` (`EmitContext`)：发射上下文。

使用示例：

```python
value = visitor.visit_expr(expr_ast, ctx)
```

注意事项：

- 必须保证同一表达式被复用时返回相同 value。

返回与限制：

- 返回 MLIR value 对象。

### `AstVisitorError`

功能说明：访问器阶段的统一错误类型。

参数说明：

- `message` (`str`)：错误描述。
- `location` (`SourceLocation|None`)：可选位置信息。

使用示例：

```python
raise AstVisitorError("Unsupported node", location)
```

注意事项：

- 错误必须携带可定位的诊断信息。

返回与限制：

- 抛出异常终止遍历。

## 测试

- 测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令：`pytest -q test/dsl/test_ast_visitor.py`
- 测试目标：
  - 覆盖遍历顺序与节点分发。
  - 覆盖变量绑定复用与错误传播。
- 功能与用例清单：
  - AV-001：遍历函数体并生成稳定顺序。（`test_ast_visitor_visit_block_preserves_order`）
  - AV-002：同一表达式复用同一 value。（`test_ast_visitor_reuses_expression_value`）
  - AV-003：不支持语句/表达式时抛出 `AstVisitorError`。（`test_lowering_failure_reports_diagnostics`）
