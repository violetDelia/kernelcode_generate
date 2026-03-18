# ast_visitor.md

用于定义 `python/dsl/ast_visitor.py` 的单文件设计规范。该组件是 AST 前端入口，负责将受限的 Python 函数语义映射为项目 AST，并提供 nn dialect IR 与 MLIR 文本入口。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
- `关联 AST`：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- `关联 Lowering`：[`spec/dsl/lowering.md`](../../spec/dsl/lowering.md)
- `关联 MLIR`：[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- `关联 Dialect`：[`spec/dialect/nn.md`](../../spec/dialect/nn.md)
- `test`：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- `功能实现`：[`python/dsl/ast_visitor.py`](../../python/dsl/ast_visitor.py)

## 范围与目标

- 作为 AST 前端入口，接受受限的 Python 函数并生成项目 AST（见 `spec/dsl/ast.md`）。
- 提供从 AST 到 `nn dialect` IR 的入口输出（具体 lowering 规则由 `spec/dsl/lowering.md` 约束）。
- 提供 MLIR 文本输出入口（见 `spec/dsl/mlir_gen.md`）。
- 仅描述与 `python/dsl/ast_visitor.py` 直接相关的 API、依赖与边界。

## 依赖边界

- 依赖 Python `ast` 与 `inspect` 读取源码与语法树。
- AST 节点类型与结构遵循 `spec/dsl/ast.md`。
- Lowering 规则由 `spec/dsl/lowering.md` 约束并在对应实现中完成；本模块只负责调用入口。
- `nn dialect` 的 IR 结构与验证规则由 `spec/dialect/nn.md` 约束。

## 功能边界

- 仅处理受限 Python 函数的解析、AST 构建与 IR/MLIR 入口输出。
- 不负责优化、调度、融合或后端代码生成。
- 不支持任意 Python 语法；支持范围以本 spec 与测试清单为准。
- 不进行联网搜索或外部资料依赖。

## 公开接口

### `visit_function(fn, globals=None, builtins=None, config=None)`

功能说明：

- 解析 Python 函数并生成 `FunctionAST`。
- 支持从 `globals`/`builtins` 提供 Tensor 注解别名。

使用示例：

```python
def add(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
    z = x + y
    return z

func_ast = visit_function(add, globals={"TensorAlias": TensorAlias}, config={"keep_source": True})
```

约束与返回：

- 必须能获取函数源码；失败抛 `OSError` 或 `TypeError`。
- 语法解析失败抛 `SyntaxError`。
- 返回 `FunctionAST`，包含输入/输出类型、语句块与源码位置信息；当 `config["keep_source"]` 为真时保留源码。

### `visit_to_nn_ir(fn, globals=None, builtins=None, config=None)`

功能说明：

- 组合入口：`FunctionAST` -> `nn dialect` IR。
- 发生 lowering 失败时抛 `AstVisitorError`，并携带 `Diagnostic` 位置信息。

使用示例：

```python
module = visit_to_nn_ir(add)
```

返回约束：

- 返回 `xdsl.dialects.builtin.ModuleOp`。
- Module 内包含 `func.func` 与相应 `nn.*` op。

### `emit_mlir(value, globals=None, builtins=None, config=None)`

功能说明：

- 输入 Python 函数或 `nn dialect` 模块，返回 MLIR 风格文本。

使用示例：

```python
text = emit_mlir(add)
```

返回约束：

- 返回非空字符串，包含 `func.func` 与对应的 `nn.*` 操作符文本。
- 具体文本格式由 `xdsl.printer.Printer` 决定。

## AST 构建规则

### 支持的函数结构

- 仅允许单一顶层函数定义。
- 必须包含且仅包含一个 `return` 语句。
- `return` 语句必须返回表达式；不支持 `return` 空值。
- `return` 之后禁止追加语句。

### 参数与返回注解

- 必须为所有参数提供注解。
- 支持的注解：
  - `"Tensor[dtype, dim, ...]"` 字符串字面量。
  - `int` 或 `"int"` 作为标量注解。
  - 形如 `TensorAlias[dtype, dim, ...]` 的下标注解；`TensorAlias` 必须在 `globals` 或 `builtins` 中注册。
- 支持的 dtype：`f32/float32` 与 `i32/int32`。
- 返回注解可省略；若提供，则必须符合上述类型规则。

### 语句与表达式

- 仅支持以下语句：
  - `Assign`：目标必须是单个 `Name`。
  - `Return`：必须带表达式。
- 表达式支持：
  - `Name`：引用函数参数或已绑定的局部名称。
  - `Constant`：生成 `ConstAST`。
  - `BinOp`：`+ - * /` 映射为 `BinaryExprAST(op=add/sub/mul/div)`。
  - `Compare`：`== != < <= > >=` 映射为 `CompareExprAST`。

### Name/局部赋值建模

- `Assign` 将目标名称绑定到表达式 AST；后续 `Name` 解析直接返回该表达式对象。
- 不创建显式的本地变量节点用于 SSA；AST 通过共享表达式对象实现引用复用。

### 多语句 SSA 约束

- 函数体语句序列保留顺序；`return` 表达式必须为最后一条语句。
- lowering 会按顺序处理语句，并对同一表达式对象进行 SSA value 复用（见 `spec/dsl/lowering.md`）。

### Constant 能力边界

- AST 支持 `ConstAST`，用于表达式中携带 Python 常量。
- lowering 当前不支持常量参与运算或返回，遇到 `ConstAST` 必须抛错（见 `spec/dsl/lowering.md`）。

## 约束与错误

- 源码不可获取时抛 `OSError`/`TypeError`。
- 语法解析失败抛 `SyntaxError`。
- AST 构建阶段遇到不支持语法/类型必须抛 `AstVisitorError` 并携带 `Diagnostic` 位置信息。
- lowering 失败需转为 `AstVisitorError`，诊断位置应来自 `LoweringError.location`。

## 测试

- 测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令：`pytest -q test/dsl/test_ast_visitor.py`

### 测试目标

- 覆盖 `visit_function` 源码解析、AST 构建与位置信息。
- 覆盖 `globals`/`builtins` 注解入口解析。
- 覆盖 `visit_to_nn_ir` 生成 nn dialect 模块。
- 覆盖标量参数 lowering 至 `func.func` 签名。
- 覆盖 `emit_mlir` 文本输出。
- 覆盖未知名称、非法返回注解、lowering 失败、不支持语法的诊断输出。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| AV-001 | AST 构建 | 基础函数解析 | 输入函数带张量注解 | `visit_function(add, config={"keep_source": True})` | 返回 `FunctionAST`，保留源码与位置信息 |
| AV-002 | IR 入口 | `visit_to_nn_ir` | 输入函数为张量二元加法 | `visit_to_nn_ir(add)` | 返回包含 `func.func` 与 `nn.add` 的模块 |
| AV-003 | MLIR 文本 | 文本输出入口 | 已定义张量二元加法函数 | `emit_mlir(add)` | 输出包含 `func.func` 与 `nn.add` 的文本 |
| AV-003A | 注解解析 | globals/builtins 入口 | Tensor 注解别名由 `globals`/`builtins` 提供 | `visit_function(add_global, globals=...)` | 注解解析成功 |
| AV-003B | Lowering | 标量参数签名 | 函数包含 `int` 标量参数 | `visit_to_nn_ir(add)` | `func.func` 输入签名包含 `i32` |
| AV-003C | 诊断 | 未知名称 | 函数返回表达式引用未定义名称 | `visit_function(bad)` | 抛出带 `Diagnostic` 的 `AstVisitorError` |
| AV-003D | 诊断 | lowering 失败定位 | AST 构建成功但 lowering 不支持混合操作数 | `visit_to_nn_ir(bad)` | 抛出带 `Diagnostic` 的 `AstVisitorError` |
| AV-003E | 诊断 | 非法返回注解 | 返回注解不属于支持范围 | `visit_function(bad_return)` | 抛出带 `Diagnostic` 的 `AstVisitorError` |
| AV-003F | 诊断 | 非法 Tensor 返回注解 | 返回注解包含不支持 dtype | `visit_function(bad_return)` | 抛出带 `Diagnostic` 的 `AstVisitorError` |
| AV-003G | 诊断 | 常量 lowering 失败 | 函数返回常量表达式 | `visit_to_nn_ir(bad)` | 抛出带 `Diagnostic` 的 `AstVisitorError` |
| AV-003H | 诊断 | 缺失 return | 函数体没有 return | `visit_function(bad)` | 抛出带 `Diagnostic` 的 `AstVisitorError` |
| AV-003I | 诊断 | 返回类型不匹配 | 比较表达式返回但标注为 Tensor | `visit_to_nn_ir(bad)` | 抛出带 `Diagnostic` 的 `AstVisitorError` |
| AV-003J | 诊断 | Tensor 注解缺失维度 | `Tensor[f32]` / `TensorAlias[f32]` | `visit_function(bad)` | 抛出带 `Diagnostic` 的 `AstVisitorError` |
| AV-003K | SSA | 多语句 SSA | 赋值后复用表达式 | `visit_to_nn_ir(add)` | SSA 顺序正确且复用同一结果 |
| AV-004 | 诊断 | 不支持语法 | 函数体包含 `if` | `visit_function(bad)` | 抛出带 `Diagnostic` 的 `AstVisitorError` |
