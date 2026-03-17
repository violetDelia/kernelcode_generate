# ast_visitor.md

用于定义 `python/dsl/ast_visitor.py` 的单文件设计规范。该组件是 AST 前端入口，负责将受限的 Python 函数语义映射为项目 AST，并进一步产出 `nn dialect` IR 与 MLIR 文本。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
- `关联 AST`：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- `关联 Lowering`：[`spec/dsl/lowering.md`](../../spec/dsl/lowering.md)
- `关联 Dialect`：[`spec/dialect/nn.md`](../../spec/dialect/nn.md)
- `test`：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- `功能实现`：[`python/dsl/ast_visitor.py`](../../python/dsl/ast_visitor.py)

## 范围与目标

- 作为 AST 前端入口，接受受限的 Python 函数并生成项目 AST。
- 提供从 AST 到 `nn dialect` IR 的入口输出（不在本模块内实现具体 Lowering 规则）。
- 提供 `nn dialect` IR 的 MLIR 文本输出入口，供调试与测试使用。
- 仅描述与 `python/dsl/ast_visitor.py` 直接相关的 API、依赖与边界。

## 依赖边界

### AST 前端

- 依赖 Python `ast` 与 `inspect` 读取源码与语法树。
- 输出的 AST 类型与结构遵循 `spec/dsl/ast.md`。
- 不在本模块内定义新的 AST 节点或类型系统。

### Lowering

- Lowering 规则由 `spec/dsl/lowering.md` 约束并在对应实现中完成。
- 本模块只负责调用或桥接 Lowering 的入口，不实现逐节点转换逻辑。

### Dialect

- `nn dialect` 的 IR 结构与验证规则由 `spec/dialect/nn.md` 约束。
- 本模块仅输出或转交构建 `nn dialect` IR，不定义 dialect 本体。

### MLIR 文本

- MLIR 文本输出以 `nn dialect` IR 为唯一输入。
- 文本格式与打印规则应与 `nn dialect` 的 printer 行为一致。

## 功能边界

- 仅处理受限 Python 函数的解析、AST 构建与 IR 入口输出。
- 不负责优化、调度、融合或后端代码生成。
- 不支持任意 Python 语法；具体支持范围由实现与测试定义。
- 不进行联网搜索或外部资料依赖。

## 公开接口

### 输入

- Python 函数对象（带类型标注）。
- 可选的全局符号表与内建函数注册表。
- 可选配置项（如是否保留源码片段）。

#### 输入示例

```python
<<<<<<< Updated upstream
def add(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
    return x + y

globals_table = {"Tensor": Tensor}
builtins_registry = {"relu": relu}
config = {"keep_source": True}
=======
def kernel(A: SymbolMemory, B: int):
    return load(A, B, A.get_stride())
```

返回结果至少应包含：

- `source="def kernel(...): ..."`
- `signature=(A: SymbolMemory, B: int)`
- `file_path`
- `start_lineno`

### `parse_function_ast(source)`

功能说明：

- 把函数源码解析为 Python `ast.Module` / `ast.FunctionDef`。

建议行为：

- 若源码中包含多个顶层定义，只接受目标函数对应的 `FunctionDef`。
- 若源码无法解析，抛 `SyntaxError` 或包装后的 `ValueError`。

示例：

```python
source = "def kernel(A: SymbolMemory, B: int):\n    return add(A, B)\n"
module_ast, function_ast = parse_function_ast(source)
```

预期行为：

- 返回的 `module_ast` 为 `ast.Module`
- 返回的 `function_ast` 为 `ast.FunctionDef`
- `function_ast.name == "kernel"`

### `visit_function(fn)`

功能说明：

- 主入口：函数对象 -> `FunctionAST`。

建议流程：

- `load_function_source`
- `parse_function_ast`
- `visit_Module`
- `visit_FunctionDef`

示例：

```python
def kernel(A: SymbolMemory, B: int):
    return add(A, B)

func_ast = visitor.visit_function(kernel)
```

预期行为：

- 返回 `FunctionAST`
- 参数表包含 `A`/`B` 的类型标注
- `FunctionAST` 具备可用于后续 `lowering` 的节点结构

### `visit_to_nn_ir(fn)`

功能说明：

- 组合入口：函数对象 -> `nn dialect` IR。

建议流程：

- `function -> FunctionAST`
- `validate_ast`
- `build_nn_dialect`

建议返回：

- `builtin.module`
- 内含 `func.func`
- 函数体中使用 `nn.add` / `nn.sub` / `nn.mul` / `nn.truediv` / `nn.eq` / `nn.ne` / `nn.lt` / `nn.le` / `nn.gt` / `nn.ge`

示例：

```python
def kernel(A: SymbolMemory, B: int):
    return add(A, B)

module = visitor.visit_to_nn_ir(kernel)
```

预期行为：

- 返回 `builtin.module`，内部包含 `func.func`
- `func.func` 体内包含 `nn.add` 对应的 IR 节点

### `visit_to_ir(fn)`

功能说明：

- 兼容入口，语义等同于 `visit_to_nn_ir(fn)`。

示例：

```python
def kernel(A: SymbolMemory, B: int):
    return add(A, B)

module = visitor.visit_to_ir(kernel)
```

预期行为：

- 返回的 IR 结构与 `visit_to_nn_ir(fn)` 一致

### `emit_mlir(fn)` / `emit_mlir(module)`

功能说明：

- 把 `nn dialect` IR 打印为 MLIR 风格文本。

建议流程：

- `function -> nn dialect module`
- `module -> printer`
- 返回 MLIR 风格字符串

示例：

```python
def kernel(A: SymbolMemory, B: int):
    return add(A, B)

mlir_text = visitor.emit_mlir(kernel)
```

预期行为：

- 返回非空字符串
- 文本中包含 `func.func` 与 `nn.add` 的 MLIR 风格表示

## Visitor 上下文设计

### `VisitorContext`

建议至少包含以下字段：

- `source`
- `file_path`
- `start_lineno`
- `globals`
- `locals`
- `arguments`
- `symbol_table`
- `type_env`
- `diagnostics`
- `current_function`
- `loop_stack`

### 设计原则

- visitor 过程中不使用隐式全局状态。
- 函数参数、局部变量、循环变量必须进入显式符号表。
- 源码位置信息必须跟随节点流转，便于报错。

## 支持的 Python AST 节点

第一阶段建议支持以下节点。

| Python AST 节点 | 作用 | ASTVisitor 产物 |
| --- | --- | --- |
| `Module` | 模块入口 | `ModuleAST` 或单函数入口 |
| `FunctionDef` | 顶层函数 | `FunctionAST` |
| `arguments` / `arg` | 参数 | `TensorAST` / `ScalarArgAST` |
| `Assign` | 局部绑定 | 局部符号表写入 |
| `Return` | 返回语句 | 输出表达式 / return 节点 |
| `Expr` | 独立表达式语句 | statement 节点 |
| `For` | 循环 | `ForAST` |
| `Call` | DSL 内建调用 | `LoadAST` / `StoreAST` / 内建表达式 |
| `Name` | 变量引用 | `VarAST` / 参数引用 |
| `Constant` | 常量 | `ConstAST` |
| `BinOp` | 算术表达式 | `BinaryExprAST` |
| `Compare` | 比较表达式 | `CompareExprAST` |
| `Attribute` | 受控属性 / 方法调用 | 例如 `A.get_stride()` |

## 节点访问规则

### `visit_Module`

功能说明：

- 校验模块中是否存在且只存在一个目标 `FunctionDef`。

约束：

- 不支持一个入口里同时传入多个可编译函数。
- 其他非目标顶层节点默认拒绝，除非是文档字符串。

### `visit_FunctionDef`

功能说明：

- 解析函数名、参数、返回值、函数体。

约束：

- 函数名不能为空。
- 参数类型必须可映射到 DSL 输入类型。
- 当前阶段优先支持：
  - `SymbolMemory`
  - `int`
  - 后续扩展的受支持标量类型

示例：

```python
def kernel(A: SymbolMemory, B: int):
    x = load(A, B, A.get_stride())
    return x
>>>>>>> Stashed changes
```

示例约束：输入函数必须带类型标注；`globals_table`/`builtins_registry`/`config` 可选提供，用于解析注解、内建符号与源码保留策略。

### 输出

#### `visit_function(fn)` -> `FunctionAST`

示例：

```python
func_ast = visit_function(add, globals=globals_table, builtins=builtins_registry, config=config)
```

预期结果：返回 `FunctionAST`，其函数名、参数与返回类型来自输入函数的注解与语法结构。

#### `visit_to_nn_ir(fn)` -> `nn dialect` IR 模块

示例：

```python
module = visit_to_nn_ir(add, globals=globals_table, builtins=builtins_registry, config=config)
```

预期结果：返回 `nn dialect` 的 IR 模块，至少包含与 `add` 对应的函数与基本算子结构；Lowering 规则由 `spec/dsl/lowering.md` 约束。

#### `emit_mlir(fn)` 或 `emit_mlir(module)` -> MLIR 文本

示例（输入函数）：

```python
mlir_text = emit_mlir(add, globals=globals_table, builtins=builtins_registry, config=config)
```

示例（输入模块）：

```python
module = visit_to_nn_ir(add, globals=globals_table, builtins=builtins_registry, config=config)
mlir_text = emit_mlir(module)
```

预期结果：返回 MLIR 文本字符串，语义与 `nn dialect` IR 一致，适用于调试或 round-trip 比对。

#### 可选中间结果

- Python `ast.FunctionDef`
- 源码位置信息映射
- 诊断信息集合

示例：`visit_function` 的返回结果应能提供中间产物访问能力，用于定位语法错误或类型诊断（例如在诊断集合中记录不支持语法的行列信息）。

## 约束与错误

- 源码不可获取时必须抛出 `OSError`/`TypeError` 或一致的封装异常。
- 语法解析失败时应抛 `SyntaxError` 或一致的封装异常。
- AST 构建过程中遇到不支持语法或类型错误应产生可定位的诊断信息。
- Lowering 或 Dialect 构建失败应向上传递明确异常，不静默吞错。

## 测试

- 测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令：`pytest -q test/dsl/test_ast_visitor.py`

### 测试目标

- 验证函数源码解析、AST 构建与位置信息映射正确。
- 验证 `globals` / `builtins` 入口可参与注解解析，避免公开参数失效。
- 验证 `visit_to_nn_ir` 生成 `nn dialect` IR，且满足 dialect 的基本结构约束。
- 验证 `ScalarArgAST` 能进入 `func.func` 标量参数签名。
- 验证 `emit_mlir` 输出的文本与 IR 一致，且便于 round-trip 比对。
- 验证未知名称、非法返回注解、不支持语法与 lowering 失败都能产生可定位诊断。

### 测试标准

- 所有测试通过，`pytest` 返回码 0。
- 覆盖 AST 前端、Lowering 调用边界、Dialect/MLIR 文本输出的关键路径。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| AV-001 | AST 构建 | 基础函数解析 | 输入函数带张量注解 | `visit_function(add, config={"keep_source": True})` | 返回 `FunctionAST`，保留源码、返回类型与位置信息 |
| AV-002 | IR 入口 | `visit_to_nn_ir` | 输入函数为张量二元加法 | `visit_to_nn_ir(add)` | 返回包含 `func.func` 与 `nn.add` 的模块 |
| AV-003 | MLIR 文本 | 文本输出入口 | 已定义张量二元加法函数 | `emit_mlir(add)` | 输出包含 `func.func` 与 `nn.add` 的文本 |
| AV-003A | 注解解析 | globals/builtins 入口 | `TensorAlias` 通过 globals 或 builtins 提供 | `visit_function(add_global, globals=...)` / `visit_function(add_builtin, builtins=...)` | 注解解析成功，公开入口真实生效 |
| AV-003B | Lowering | 标量参数签名 | 函数包含 `int` 标量参数 | `visit_to_nn_ir(add)` | `func.func` 输入签名包含 `i32` 标量参数 |
| AV-003C | 诊断 | 未知名称 | 函数返回表达式引用未定义名称 | `visit_function(bad)` | 抛出带 `SourceLocation` 的 `AstVisitorError` |
| AV-003D | 诊断 | lowering 失败定位 | AST 构建成功但 lowering 缺少第二个张量操作数 | `visit_to_nn_ir(bad)` | 抛出带 `SourceLocation` 的 `AstVisitorError` |
| AV-003E | 诊断 | 非法返回注解 | 返回注解不属于支持范围 | `visit_function(bad_return)` | 不静默吞错，抛出带 `SourceLocation` 的 `AstVisitorError` |
| AV-003F | 诊断 | 非法 Tensor 返回注解 | 返回注解包含不支持 dtype | `visit_function(bad_return)` | 抛出带 `SourceLocation` 的 `AstVisitorError` |
| AV-004 | 诊断 | 不支持语法 | 函数体包含 `if` | `visit_function(bad)` | 抛出带 `SourceLocation` 的 `AstVisitorError` |
