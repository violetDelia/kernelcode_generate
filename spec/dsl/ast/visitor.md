# visitor.md

## 功能简介

- 定义 AST 访问器，用于遍历 `FunctionAST` 并驱动节点转换。
- 访问器在遍历过程中调用 `emit_mlir` 中定义的节点发射逻辑。
- 不负责 Python 函数解析与 MLIR 文本输出。

## API 列表

- `KernelCodeError(kind, ErrorModule.AST, message, location: SourceLocation | None = None)`
- `class AstVisitor(config: dict[str, object] | None = None)`
- `AstVisitor.__init__(config: dict[str, object] | None = None) -> None`
- `AstVisitor.register(node_type: type, method_name: str) -> None`
- `AstVisitor.visit(node: object, ctx: EmitContext) -> object`
- `AstVisitor.visit_function(func_ast: FunctionAST, ctx: EmitContext) -> object`
- `AstVisitor.visit_block(block_ast: object, ctx: EmitContext) -> object`
- `AstVisitor.visit_stmt(stmt: object, ctx: EmitContext) -> object`
- `AstVisitor.visit_expr(expr: object, ctx: EmitContext) -> object`

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dsl/ast/visitor.md`](../../../spec/dsl/ast/visitor.md)
- `功能实现`：[`kernel_gen/dsl/ast/visitor.py`](../../../kernel_gen/dsl/ast/visitor.py)
- `test`：[`test/dsl/ast/test_visitor.py`](../../../test/dsl/ast/test_visitor.py)

## 依赖

- AST 节点定义与解析入口：[`spec/dsl/ast/__init__.md`](../../../spec/dsl/ast/__init__.md)
- 节点发射规范：[`spec/dsl/emit_mlir.md`](../../../spec/dsl/emit_mlir.md)

## 术语

- `AstVisitor`：AST 遍历器，负责节点分发与顺序控制。
- `EmitContext`：发射上下文结构。
- `KernelCodeError`：访问器阶段错误类型，`module()` 固定为 `ast`。

## 目标

- 以确定性顺序遍历 AST。
- 维护局部变量到已生成值的映射。
- 将节点交由 `emit_mlir` 进行 MLIR op/value 生成。

## 限制与边界

- 不解析 Python 函数源码；解析入口由 `ast.parse_function(...)` 提供。
- 不定义任何节点的 MLIR 生成细节；仅负责遍历与分发。
- 不生成 MLIR 文本，不负责 module 封装。
- 不引入 target/硬件字段或默认值；`EmitContext.config` 中的 `target`/`hardware` 由上游注入，访问器仅透传至 emit 逻辑。

## 公开接口

### `AstVisitor(config: dict[str, object] | None = None)`

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

### `AstVisitor.register(node_type: type, method_name: str) -> None`

功能说明：

- 为访问器注册额外节点分发方法。
- 允许自定义 visitor 扩展 AST 节点覆盖面。

参数说明：

- `node_type` (`type`)：要注册的 AST 节点类型。
- `method_name` (`str`)：visitor 上的方法名。

使用示例：

```python
class MyVisitor(AstVisitor):
    _registry: dict[type, str] = {}

    def visit_my_node(self, node, ctx):
        return node

MyVisitor.register(MyNode, "visit_my_node")
```

注意事项：

- 注册只影响当前 visitor class 的分发表，不自动修改其他 visitor 子类的本地覆写逻辑。

返回与限制：

- 无返回值。

### `AstVisitor.visit_function(func_ast: FunctionAST, ctx: EmitContext) -> object`

功能说明：

- 遍历 `FunctionAST`，按语句顺序生成节点对应的 MLIR op/value。
- 负责建立初始符号表（参数绑定）。

参数说明：

- `func_ast` (`FunctionAST`)：函数 AST 根节点。
- `ctx` (`EmitContext`)：发射上下文。

使用示例：

```python
ctx = EmitContext(
    builder=builder,
    symbols={},
    types=types,
    config={"target": "gpu_a", "hardware": {"thread_num": 256}},
)
result = visitor.visit_function(func_ast, ctx)
```

注意事项：

- 必须保证语句遍历顺序与 AST 一致。
- `ctx.config` 中的 `target`/`hardware` 必须保持原样传递，不得由访问器篡改或注入默认值。

返回与限制：

- 返回值包含函数返回值或已生成的 op/value（具体结构由实现约束）。

### `AstVisitor.visit_block(block_ast: object, ctx: EmitContext) -> object`

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

### `AstVisitor.visit_stmt(stmt: object, ctx: EmitContext) -> object`

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

- 不支持的语句必须抛出 `KernelCodeError`。

返回与限制：

- 语句节点通常不返回值。

### `AstVisitor.visit(node: object, ctx: EmitContext) -> object`

功能说明：

- 根据已注册的节点类型分发到对应的 visit 方法。

参数说明：

- `node` (`object`)：任意 AST 节点。
- `ctx` (`EmitContext`)：发射上下文。

使用示例：

```python
visitor = AstVisitor()
result = visitor.visit(func_ast.body, ctx)
```

注意事项：

- 未注册节点必须抛出 `KernelCodeError`。

返回与限制：

- 返回已注册 visit 方法的返回值。

### `AstVisitor.visit_expr(expr: object, ctx: EmitContext) -> object`

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

### `KernelCodeError`

功能说明：访问器阶段的统一错误类型。

参数说明：

- `message` (`str`)：错误描述。
- `location` (`SourceLocation|None`)：可选位置信息。

使用示例：

```python
raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, "Unsupported node", location=location)
```

注意事项：

- 错误必须携带可定位的诊断信息。

返回与限制：

- 抛出异常终止遍历。

## 测试

- 测试文件：[`test/dsl/ast/test_visitor.py`](../../../test/dsl/ast/test_visitor.py)
- 执行命令（visitor 单测）：`pytest -q test/dsl/ast/test_visitor.py`
- 覆盖率命令：`pytest -q --cov=kernel_gen.dsl.ast.visitor --cov-branch --cov-report=term-missing test/dsl/ast/test_visitor.py`
- 测试目标：
  - 覆盖语句块遍历与异常提示。
  - 覆盖已注册节点分发与未注册节点报错。
- 功能与用例清单：
  - AV-001：空 BlockAST 遍历返回 None。（`test_ast_visitor_empty_block_returns_none`）
  - AV-002：未知 BlockAST 抛 `KernelCodeError`。（`test_ast_visitor_rejects_unknown_block`）
  - AV-003：已注册节点正确分发。（`test_ast_visitor_dispatches_registered_node`）
  - AV-004：`register(...)` 可为自定义 visitor 注册节点分发。（`test_ast_visitor_register_dispatches_custom_node`）
  - AV-005：未注册节点抛 `KernelCodeError`。（`test_ast_visitor_rejects_unregistered_node`）
