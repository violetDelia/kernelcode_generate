# ast.md

用于定义 DSL AST 数据结构的规范，对应 `python/dsl/ast.py`。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- `test`：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- `功能实现`：[`python/dsl/ast.py`](../../python/dsl/ast.py)

## 范围与目标

- 描述 DSL 前端 AST 节点的数据结构与语义边界。
- 供 `ast_visitor` 与 `lowering` 共用；不定义 Lowering 规则细节。

## 节点定义

### `SourceLocation`

功能说明：

- 记录源码行列位置。

使用示例：

```python
SourceLocation(line=1, column=0)
```

字段：

- `line: int`
- `column: int`

### `Diagnostic`

功能说明：

- 记录错误消息与对应源码位置。

使用示例：

```python
Diagnostic(message="Unsupported syntax", location=SourceLocation(3, 4))
```

字段：

- `message: str`
- `location: SourceLocation | None`

### `ModuleAST`

功能说明：

- 模块级容器，聚合多个 `FunctionAST`。

使用示例：

```python
ModuleAST(functions=[FunctionAST(name="kernel", inputs=[], outputs=[], body=BlockAST([]))])
```

字段：

- `functions: list[FunctionAST]`

### `TensorAST`

功能说明：

- 表示函数签名中的张量输入。

使用示例：

```python
TensorAST(name="A", memory=memory)
```

字段：

- `name: str`
- `memory: object`
- `location: SourceLocation | None`

### `ScalarArgAST`

功能说明：

- 表示函数签名中的标量输入。

使用示例：

```python
ScalarArgAST(name="n", value_type=int)
```

字段：

- `name: str`
- `value_type: type`
- `location: SourceLocation | None`

### `VarAST`

功能说明：

- 表示循环变量或中间变量。

使用示例：

```python
VarAST(name="i")
```

字段：

- `name: str`
- `location: SourceLocation | None`

### `BlockAST`

功能说明：

- 有序语句块容器。

使用示例：

```python
BlockAST(statements=[])
```

字段：

- `statements: list[object]`
- `location: SourceLocation | None`

### `ForAST`

功能说明：

- 表示 `for` 循环结构。

使用示例：

```python
ForAST(var=VarAST("i"), start=ConstAST(0), end=ConstAST(10), body=BlockAST([]))
```

字段：

- `var: VarAST`
- `start: object`
- `end: object`
- `body: BlockAST`
- `location: SourceLocation | None`

### `StoreAST`

功能说明：

- 描述向张量写入的语义。

使用示例：

```python
StoreAST(tensor=tensor, offset=offset, stride=None, value=expr)
```

字段：

- `tensor: TensorAST`
- `offset: object`
- `stride: object | None`
- `value: object`
- `location: SourceLocation | None`

### `LoadAST`

功能说明：

- 描述从张量读取的语义。

使用示例：

```python
LoadAST(tensor=tensor, offset=offset, stride=None)
```

字段：

- `tensor: TensorAST`
- `offset: object`
- `stride: object | None`

### `BinaryExprAST`

功能说明：

- 二元算术表达式节点。

使用示例：

```python
BinaryExprAST(op="add", lhs=a, rhs=b)
```

字段：

- `op: str` (`add/sub/mul/div`)
- `lhs: object`
- `rhs: object`
- `location: SourceLocation | None`

### `CompareExprAST`

功能说明：

- 比较表达式节点。

使用示例：

```python
CompareExprAST(op="lt", lhs=a, rhs=b)
```

字段：

- `op: str` (`eq/ne/lt/le/gt/ge`)
- `lhs: object`
- `rhs: object`
- `location: SourceLocation | None`

### `ConstAST`

功能说明：

- 表示常量表达式。

使用示例：

```python
ConstAST(value=1)
```

字段：

- `value: object`
- `location: SourceLocation | None`

### `FunctionAST`

功能说明：

- 表示 DSL 函数入口。

使用示例：

```python
FunctionAST(name="kernel", inputs=[], outputs=[], body=BlockAST([]))
```

字段：

- `name: str`
- `inputs: list[TensorAST | ScalarArgAST]`
- `outputs: list[TensorAST | ScalarArgAST]`
- `body: BlockAST`
- `location: SourceLocation | None`
- `source: str | None`
- `py_ast: object | None`
- `diagnostics: list[Diagnostic]`

辅助方法：

- `iter_inputs()`：遍历 `inputs` 中的 `TensorAST` 与 `ScalarArgAST`。

## 使用约束

- 本模块只定义数据结构，不规定具体 lowering 行为。
- `ConstAST` 允许在 AST 中存在，但是否支持 lowering 由 `spec/dsl/lowering.md` 约束。
- `StoreAST`/`LoadAST`/`ForAST` 目前不被 `ast_visitor` 构建，但保留用于 DSL 扩展。
