# ast_visitor.md

## 功能简介

- 定义 `python/dsl/ast_visitor.py` 的 DSL AST 前端入口规范。
- 负责将受限的 Python 函数解析为项目 AST，并提供结构化 IR 与文本输出入口。
- 仅覆盖 AST 构建与入口封装，不定义 lowering 规则与方言语义。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
- `功能实现`：[`python/dsl/ast_visitor.py`](../../python/dsl/ast_visitor.py)
- `test`：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)

## 依赖

- Python `ast`/`inspect` 用于源码获取与语法树解析。
- AST 结构定义：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- Lowering 入口约束：[`spec/dsl/lowering.md`](../../spec/dsl/lowering.md)
- 结构化 IR 生成约束：[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- 文本输出入口规范：[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
- 目标方言：[`spec/dialect/nn.md`](../../spec/dialect/nn.md)

## 术语

- `FunctionAST`：DSL 函数的 AST 根节点。
- `Diagnostic`：带位置信息的诊断结构。
- `AstVisitorError`：AST/入口阶段的统一错误类型。
- `ModuleOp`：`nn dialect` 结构化 IR 的 module 入口类型。

## 目标

- 提供 `visit_function` 用于构建 `FunctionAST`。
- 提供 `visit_to_nn_ir` 作为 AST -> `nn dialect` IR 的入口包装。
- 提供 `emit_mlir` 作为 DSL 文本输出入口。

## 限制与边界

- 只支持受限的 Python 语法子集，具体范围以本文件与测试清单为准。
- 不负责优化、调度、融合或后端代码生成。
- 不负责方言 verifier、类型系统或打印细节。
- 不进行联网搜索或外部资料依赖。

## 公开接口

### `visit_function(fn, globals=None, builtins=None, config=None)`

功能说明：

- 解析 Python 函数并生成 `FunctionAST`。
- 支持从 `globals`/`builtins` 提供 Tensor 注解别名。

参数说明：

- `fn` (`callable`): 受限 Python 函数。
- `globals` (`dict|None`): 注解解析上下文（可选）。
- `builtins` (`dict|None`): 注解解析上下文（可选）。
- `config` (`dict|None`): 行为配置（例如 `keep_source`）。

使用示例：

```python
def add(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
    z = x + y
    return z

func_ast = visit_function(add, globals={"TensorAlias": TensorAlias}, config={"keep_source": True})
```

注意事项：

- 必须能获取函数源码；无法获取时应抛错。
- 注解必须符合本文件“额外补充”中的规则。

返回与限制：

- 返回 `FunctionAST`，包含参数/返回类型、语句与位置信息。
- 若 `config["keep_source"]` 为真，应保留源码片段。
- 可能抛出：`OSError`/`TypeError`（源码不可获取）、`SyntaxError`（语法解析失败）、`AstVisitorError`（不支持语法或注解）。

### `visit_to_nn_ir(fn, globals=None, builtins=None, config=None)`

功能说明：

- 组合入口：`FunctionAST` -> `nn dialect` IR。
- 负责调用 lowering 入口并包装错误为 `AstVisitorError`。

参数说明：

- `fn` (`callable`): 受限 Python 函数。
- `globals` (`dict|None`): 注解解析上下文（可选）。
- `builtins` (`dict|None`): 注解解析上下文（可选）。
- `config` (`dict|None`): 行为配置（可选）。

使用示例：

```python
module = visit_to_nn_ir(add)
```

注意事项：

- 仅作为入口包装，不在此处定义 lowering 规则。

返回与限制：

- 返回 `ModuleOp`，包含 `func.func` 与对应 `nn.*` op。
- Lowering 失败时必须抛出带 `Diagnostic` 的 `AstVisitorError`。

### `emit_mlir(value, globals=None, builtins=None, config=None)`

功能说明：

- 输入 Python 函数或 `nn dialect` module，输出 MLIR 风格文本。

参数说明：

- `value` (`callable|ModuleOp`): 受限 Python 函数或可打印 module。
- `globals` (`dict|None`): 仅在 `value` 为函数时使用。
- `builtins` (`dict|None`): 仅在 `value` 为函数时使用。
- `config` (`dict|None`): 仅在 `value` 为函数时使用。

使用示例：

```python
text = emit_mlir(add)
```

注意事项：

- 文本输出语义由 `emit_mlir` spec 约束，格式细节由 printer 决定。

返回与限制：

- 返回 `str`，包含 `func.func` 与对应 `nn.*` op 文本。
- 当 `value` 为函数时，错误传播规则与 `visit_to_nn_ir` 保持一致。

## 额外补充

- 支持的函数结构：仅允许单一顶层函数定义；必须包含且仅包含一个 `return`；`return` 后禁止追加语句。
- 参数与返回注解：参数必须有注解；支持 `"Tensor[dtype, dim, ...]"` 字符串、`int`/`"int"`、以及 `TensorAlias[...]` 下标注解（需在 `globals` 或 `builtins` 注册）；支持 dtype 为 `f32/float32` 与 `i32/int32`。
- 语句与表达式：仅支持 `Assign`/`Return`；表达式支持 `Name`、`Constant`、`BinOp(+ - * /)`、`Compare(== != < <= > >=)`。
- Name/局部赋值建模：`Assign` 将目标名称绑定到表达式 AST；后续 `Name` 解析直接返回该表达式对象。
- 常量边界：AST 可生成 `ConstAST`，但 lowering 当前不支持常量参与运算或直接返回，必须抛错。
- 多语句 SSA 约束：语句顺序保留；lowering 应按顺序处理并复用同一表达式对象的 SSA value。

## 测试

- 测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令：`pytest -q test/dsl/test_ast_visitor.py`

### 测试目标

- 覆盖 `visit_function` 源码解析与 AST 构建。
- 覆盖注解入口（`globals`/`builtins`）。
- 覆盖 `visit_to_nn_ir` 的 module 生成与标量签名。
- 覆盖 `emit_mlir` 文本输出入口。
- 覆盖不支持语法与诊断错误路径。

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
