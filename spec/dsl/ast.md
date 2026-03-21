# ast.md

## 功能简介

- 定义 DSL AST 节点与字段语义。
- 提供解析入口，将 Python 函数解析为 AST 树。
- 不定义 MLIR 生成或文本输出。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- `功能实现`：[`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py)
- `test`：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)

## 依赖

- Python `ast`/`inspect`：用于获取源码并解析语法树。

## 术语

- `FunctionAST`：函数级 AST 根节点。
- `Diagnostic`：带源码位置的诊断信息。
- `SourceLocation`：源码行列位置。

## 目标

- 提供稳定的 AST 节点定义。
- [immutable]提供 `parse_function(...)` 将 Python 函数解析为 AST。
- 为后续遍历与发射提供结构化输入。

## 限制与边界

- 只覆盖 AST 与解析入口，不负责 MLIR 生成与输出。
- 只支持受限语法子集，具体范围以测试清单为准。
- 不做优化、融合或后端相关行为。
- [immutable]只提供ast节点定义以及将函数翻译为ast树的能力。

## 公开接口

### `parse_function(fn)`

功能说明：

- 解析 Python 函数并构建 `FunctionAST`。
- 在解析阶段生成 `Diagnostic` 以承载错误定位信息。
- [immutable]不需要不必要的参数。

参数说明：

- `fn` (`callable`)：受限 Python 函数。

使用示例：

```python
def add(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]"):
    return x + y

func_ast = parse_function(add)
```

注意事项：

- 必须能获取函数源码；否则应抛出解析错误。
- 注解解析规则以本文件与测试清单为准。

返回与限制：

- 返回 `FunctionAST`。
- 解析失败时应抛出包含位置信息的错误或返回带 `Diagnostic` 的结果（以测试为准）。

### `SourceLocation`

功能说明：记录 AST 节点的源码位置信息。

参数说明：

- `line` (`int`)：行号。
- `column` (`int`)：列号。

使用示例：

```python
SourceLocation(line=1, column=0)
```

注意事项：仅用于诊断与定位，不参与语义计算。

返回与限制：返回不可变的数据结构实例。

### `Diagnostic`

功能说明：记录错误消息与对应源码位置。

参数说明：

- `message` (`str`)：诊断信息。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
Diagnostic(message="Unsupported syntax", location=SourceLocation(3, 4))
```

注意事项：可与 `FunctionAST.diagnostics` 配合使用。

返回与限制：返回不可变的数据结构实例。

### `FunctionAST`

功能说明：表示 DSL 函数入口。

参数说明：

- `name` (`str`)：函数名。
- `inputs` (`list[TensorAST|ScalarArgAST]`)：输入参数。
- `outputs` (`list[TensorAST|ScalarArgAST]`)：输出参数。
- `body` (`BlockAST`)：函数体。
- `location` (`SourceLocation|None`)：可选源码位置。
- `source` (`str|None`)：可选源码文本。
- `py_ast` (`object|None`)：可选 Python AST。
- `diagnostics` (`list[Diagnostic]`)：诊断信息。

使用示例：

```python
FunctionAST(name="kernel", inputs=[], outputs=[], body=BlockAST([]))
```

注意事项：`diagnostics` 仅用于记录解析阶段问题。

返回与限制：返回不可变的数据结构实例。

### `FunctionAST.iter_inputs()`

功能说明：迭代 `inputs` 中的 `TensorAST` 与 `ScalarArgAST`。

参数说明：无。

使用示例：

```python
list(func_ast.iter_inputs())
```

注意事项：返回迭代器视图，不拷贝列表。

返回与限制：返回 `Iterable[TensorAST|ScalarArgAST]`。

### `BlockAST`

功能说明：有序语句块容器。

参数说明：

- `statements` (`list[object]`)：语句列表。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
BlockAST(statements=[])
```

注意事项：`statements` 可包含表达式与语句节点。

返回与限制：返回不可变的数据结构实例。

### `TensorAST`

功能说明：函数签名中的张量参数。

参数说明：

- `name` (`str`)：参数名。
- `memory` (`object`)：张量元信息载体。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
TensorAST(name="A", memory=memory)
```

注意事项：`memory` 的具体类型由上层语义决定。

返回与限制：返回不可变的数据结构实例。

### `ScalarArgAST`

功能说明：函数签名中的标量参数。

参数说明：

- `name` (`str`)：参数名。
- `value_type` (`type`)：标量类型。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
ScalarArgAST(name="n", value_type=int)
```

注意事项：仅保存类型信息，不负责类型转换。

返回与限制：返回不可变的数据结构实例。

### `VarAST`

功能说明：变量节点。

参数说明：

- `name` (`str`)：变量名。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
VarAST(name="i")
```

注意事项：绑定关系由解析器维护。

返回与限制：返回不可变的数据结构实例。

### `ForAST`

功能说明：`for` 循环结构。

参数说明：

- `var` (`VarAST`)：迭代变量。
- `start` (`object`)：起始表达式。
- `end` (`object`)：结束表达式。
- `body` (`BlockAST`)：循环体。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
ForAST(var=VarAST("i"), start=ConstAST(0), end=ConstAST(10), body=BlockAST([]))
```

注意事项：循环语义由下游生成阶段解释。

返回与限制：返回不可变的数据结构实例。

### `StoreAST`

功能说明：向张量写入的语义节点。

参数说明：

- `tensor` (`TensorAST`)：目标张量。
- `offset` (`object`)：访问偏移。
- `stride` (`object|None`)：可选步长。
- `value` (`object`)：写入值。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
StoreAST(tensor=tensor, offset=offset, stride=None, value=expr)
```

注意事项：`stride` 允许为空，具体语义由下游定义。

返回与限制：返回不可变的数据结构实例。

### `LoadAST`

功能说明：从张量读取的语义节点。

参数说明：

- `tensor` (`TensorAST`)：源张量。
- `offset` (`object`)：访问偏移。
- `stride` (`object|None`)：可选步长。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
LoadAST(tensor=tensor, offset=offset, stride=None)
```

注意事项：`stride` 允许为空，具体语义由下游定义。

返回与限制：返回不可变的数据结构实例。

### `BinaryExprAST`

功能说明：二元算术表达式。

参数说明：

- `op` (`str`)：操作符（例如 `add/sub/mul/div`）。
- `lhs` (`object`)：左操作数。
- `rhs` (`object`)：右操作数。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
BinaryExprAST(op="add", lhs=a, rhs=b)
```

注意事项：操作符集合由解析器限制。

返回与限制：返回不可变的数据结构实例。

### `CompareExprAST`

功能说明：比较表达式。

参数说明：

- `op` (`str`)：操作符（例如 `eq/ne/lt/le/gt/ge`）。
- `lhs` (`object`)：左操作数。
- `rhs` (`object`)：右操作数。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
CompareExprAST(op="lt", lhs=a, rhs=b)
```

注意事项：比较语义由下游定义。

返回与限制：返回不可变的数据结构实例。

### `ConstAST`

功能说明：常量表达式节点。

参数说明：

- `value` (`object`)：常量值。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
ConstAST(value=1)
```

注意事项：常量类型由解析器决定。

返回与限制：返回不可变的数据结构实例。

### `ModuleAST`

功能说明：模块级 AST 容器。

参数说明：

- `functions` (`list[FunctionAST]`)：函数列表。

使用示例：

```python
ModuleAST(functions=[FunctionAST(name="kernel", inputs=[], outputs=[], body=BlockAST([]))])
```

注意事项：`parse_function(...)` 的直接输出为 `FunctionAST`，`ModuleAST` 仅用于扩展场景。

返回与限制：返回不可变的数据结构实例。

## 测试

- 测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令：`pytest -q test/dsl/test_ast_visitor.py`
- 测试目标：
  - 覆盖 `parse_function(...)` 的源码解析与 AST 构建。
  - 覆盖 AST 节点字段与诊断信息的构造。
- 功能与用例清单：
  - AST-001：解析函数生成 `FunctionAST`。
  - AST-002：解析参数与返回注解，生成 `TensorAST`/`ScalarArgAST`。
  - AST-003：不支持语法时返回诊断或抛出错误。
