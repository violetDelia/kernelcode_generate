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
def add(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
    return x + y

globals_table = {"Tensor": Tensor}
builtins_registry = {"relu": relu}
config = {"keep_source": True}
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
