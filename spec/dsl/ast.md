# ast.md

## 功能简介

定义 DSL 前端 AST 数据结构，作为 `ast_visitor` 与 `lowering` 的共享语义载体。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- `功能实现`：[`python/dsl/ast.py`](../../python/dsl/ast.py)
- `test`：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)

## 依赖

- [`python/dsl/ast.py`](../../python/dsl/ast.py)：AST 节点数据结构的功能实现。
- [`python/dsl/ast_visitor.py`](../../python/dsl/ast_visitor.py)：构建 AST 与诊断信息的前端访问器。
- [`python/dsl/lowering.py`](../../python/dsl/lowering.py)：基于 AST 的 lowering 规则与合法性约束。

## 目标

- 统一描述 DSL AST 节点的结构、字段与用途。
- 为 `ast_visitor` 与 `lowering` 提供稳定的数据结构接口。

## 限制与边界

- 仅定义数据结构与字段语义，不描述具体 lowering 规则。
- `StoreAST`/`LoadAST`/`ForAST` 当前可能不被 `ast_visitor` 构建，但保留用于后续扩展。
- `ConstAST` 允许存在于 AST 中，是否可 lowering 由 `spec/dsl/lowering.md` 决定。

## 公开接口

### `SourceLocation`

- 功能说明：记录 AST 节点在源码中的行列位置。
- 参数说明：
  - `line: int`：行号。
  - `column: int`：列号。
- 使用示例：
  - `SourceLocation(line=1, column=0)`
- 注意事项：用于诊断信息定位，不参与运算语义。
- 返回与限制：返回不可变的数据结构实例。

### `Diagnostic`

- 功能说明：记录错误消息与对应源码位置。
- 参数说明：
  - `message: str`：诊断信息。
  - `location: SourceLocation | None`：可选源码位置。
- 使用示例：
  - `Diagnostic(message="Unsupported syntax", location=SourceLocation(3, 4))`
- 注意事项：可与 `FunctionAST.diagnostics` 配合使用。
- 返回与限制：返回不可变的数据结构实例。

### `ModuleAST`

- 功能说明：模块级 AST 容器，聚合多个 `FunctionAST`。
- 参数说明：
  - `functions: list[FunctionAST]`
- 使用示例：
  - `ModuleAST(functions=[FunctionAST(name="kernel", inputs=[], outputs=[], body=BlockAST([]))])`
- 注意事项：仅承载结构信息，不负责执行。
- 返回与限制：返回不可变的数据结构实例。

### `TensorAST`

- 功能说明：表示函数签名中的张量输入或输出。
- 参数说明：
  - `name: str`
  - `memory: object`
  - `location: SourceLocation | None`
- 使用示例：
  - `TensorAST(name="A", memory=memory)`
- 注意事项：`memory` 类型由上层语义定义。
- 返回与限制：返回不可变的数据结构实例。

### `ScalarArgAST`

- 功能说明：表示函数签名中的标量参数。
- 参数说明：
  - `name: str`
  - `value_type: type`
  - `location: SourceLocation | None`
- 使用示例：
  - `ScalarArgAST(name="n", value_type=int)`
- 注意事项：仅保存类型信息，不负责类型转换。
- 返回与限制：返回不可变的数据结构实例。

### `VarAST`

- 功能说明：表示循环变量或中间变量。
- 参数说明：
  - `name: str`
  - `location: SourceLocation | None`
- 使用示例：
  - `VarAST(name="i")`
- 注意事项：变量绑定关系由上层解析器维护。
- 返回与限制：返回不可变的数据结构实例。

### `BlockAST`

- 功能说明：有序语句块容器。
- 参数说明：
  - `statements: list[object]`
  - `location: SourceLocation | None`
- 使用示例：
  - `BlockAST(statements=[])`
- 注意事项：`statements` 可包含 AST 节点或表达式。
- 返回与限制：返回不可变的数据结构实例。

### `ForAST`

- 功能说明：表示 `for` 循环结构。
- 参数说明：
  - `var: VarAST`
  - `start: object`
  - `end: object`
  - `body: BlockAST`
  - `location: SourceLocation | None`
- 使用示例：
  - `ForAST(var=VarAST("i"), start=ConstAST(0), end=ConstAST(10), body=BlockAST([]))`
- 注意事项：循环区间语义由 `lowering` 定义。
- 返回与限制：返回不可变的数据结构实例。

### `StoreAST`

- 功能说明：描述向张量写入的语义。
- 参数说明：
  - `tensor: TensorAST`
  - `offset: object`
  - `stride: object | None`
  - `value: object`
  - `location: SourceLocation | None`
- 使用示例：
  - `StoreAST(tensor=tensor, offset=offset, stride=None, value=expr)`
- 注意事项：`stride` 允许为空，写入语义由 `lowering` 处理。
- 返回与限制：返回不可变的数据结构实例。

### `LoadAST`

- 功能说明：描述从张量读取的语义。
- 参数说明：
  - `tensor: TensorAST`
  - `offset: object`
  - `stride: object | None`
  - `location: SourceLocation | None`
- 使用示例：
  - `LoadAST(tensor=tensor, offset=offset, stride=None)`
- 注意事项：`stride` 允许为空，读取语义由 `lowering` 处理。
- 返回与限制：返回不可变的数据结构实例。

### `BinaryExprAST`

- 功能说明：二元算术表达式节点。
- 参数说明：
  - `op: str`（`add/sub/mul/div`）
  - `lhs: object`
  - `rhs: object`
  - `location: SourceLocation | None`
- 使用示例：
  - `BinaryExprAST(op="add", lhs=a, rhs=b)`
- 注意事项：操作符集合由上层解析器限制。
- 返回与限制：返回不可变的数据结构实例。

### `CompareExprAST`

- 功能说明：比较表达式节点。
- 参数说明：
  - `op: str`（`eq/ne/lt/le/gt/ge`）
  - `lhs: object`
  - `rhs: object`
  - `location: SourceLocation | None`
- 使用示例：
  - `CompareExprAST(op="lt", lhs=a, rhs=b)`
- 注意事项：比较语义由 `lowering` 解释。
- 返回与限制：返回不可变的数据结构实例。

### `ConstAST`

- 功能说明：表示常量表达式。
- 参数说明：
  - `value: object`
  - `location: SourceLocation | None`
- 使用示例：
  - `ConstAST(value=1)`
- 注意事项：常量类型由上层解析器决定。
- 返回与限制：返回不可变的数据结构实例。

### `FunctionAST`

- 功能说明：表示 DSL 函数入口。
- 参数说明：
  - `name: str`
  - `inputs: list[TensorAST | ScalarArgAST]`
  - `outputs: list[TensorAST | ScalarArgAST]`
  - `body: BlockAST`
  - `location: SourceLocation | None`
  - `source: str | None`
  - `py_ast: object | None`
  - `diagnostics: list[Diagnostic]`
- 使用示例：
  - `FunctionAST(name="kernel", inputs=[], outputs=[], body=BlockAST([]))`
- 注意事项：`diagnostics` 记录解析阶段错误；`source/py_ast` 可为空。
- 返回与限制：返回不可变的数据结构实例。

#### `FunctionAST.iter_inputs()`

- 功能说明：迭代 `inputs` 中的 `TensorAST` 与 `ScalarArgAST`。
- 参数说明：无。
- 使用示例：
  - `list(func_ast.iter_inputs())`
- 注意事项：返回迭代器视图，不拷贝列表。
- 返回与限制：返回 `Iterable[TensorAST | ScalarArgAST]`。

## 测试

- 测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令：`pytest -q test/dsl/test_ast_visitor.py`
- 测试目标：
  - 覆盖 AST 结构在 `ast_visitor` 构建与诊断流转中的核心行为。
- 功能与用例清单：
  - `AV-001`：函数解析生成 AST 与位置信息。
