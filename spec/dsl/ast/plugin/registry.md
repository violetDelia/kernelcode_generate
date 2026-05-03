# registry.md

## 功能简介

- 定义 DSL builtin 注册表。
- `dsl_builtin(...)` 绑定 DSL operation 与 AST 节点。
- `external_builtin(...)` 绑定允许保留为 Python callee 的外部函数。

## API 列表

- `class BuiltinCall(source: ast.Call, dsl_name: str, ast_node: type | None, args: list[BuiltinArgument], kwargs: dict[str, BuiltinArgument], location: SourceLocation, launch_extents: list[BuiltinArgument] | None = None)`
- `class BuiltinEntry(dsl_name: str, op: BuiltinOperation, ast_node: type | None, builder: BuiltinBuilder)`
- `dsl_builtin(op: BuiltinOperation, ast_node: type[T]) -> Callable[[Callable[[BuiltinCall], T]], Callable[[BuiltinCall], T]]`
- `external_builtin(func: BuiltinOperation, name: str | None = None) -> Callable[[BuiltinBuilder], BuiltinBuilder]`
- `lookup_builtin(op: BuiltinOperation) -> BuiltinEntry | None`
- `all_builtin_names() -> set[str]`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dsl/ast/plugin/registry.md`](../../../../spec/dsl/ast/plugin/registry.md)
- `功能实现`：[`kernel_gen/dsl/ast/plugin/registry.py`](../../../../kernel_gen/dsl/ast/plugin/registry.py)
- `test`：[`test/dsl/ast/plugin/test_registry.py`](../../../../test/dsl/ast/plugin/test_registry.py)

## 依赖

- `dataclasses`：`BuiltinEntry` 数据结构。
- Python callable：builtin builder 由 `DslAstVisitor.visit_Call(...)` 调用，签名只能是 `(node: BuiltinCall) -> BuiltinResult`。

## 目标

- 用注册表替代解析阶段硬编码 operation 名称分支；具体 builtin AST 构造必须落在对应 plugin builder 中。
- 保证同一个 operation 只能绑定一个唯一 DSL AST 节点，同一个 DSL AST 节点不会绑定到多个 operation。
- `@dsl_builtin(op, AstNode)` 的 builder 返回值必须是 `AstNode` 的精确类型；返回其他 AST、普通对象或 `AstNode` 子类都按注册合同失败处理。
- `dsl_builtin(...)` 不提供手写 `name` 参数；诊断显示名只能从 operation 对象推断，注册与查询必须继续按 operation identity。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 注册失败统一抛 `KernelCodeError(ErrorModule.AST, ...)`，错误文本必须说明重复注册项。
- `BuiltinCall` 是 parser 到 plugin builder 的唯一显式数据载体；不得在 Python `ast.Call` 上动态挂载 `_kg_*` 字段。
- `lookup_builtin(...)` 只查询，不执行 builder；builder 的执行入口在 `DslAstVisitor.visit_Call(...)`。
- `BuiltinEntry.builder(...)` 内置返回类型校验；直接通过 `lookup_builtin(...)` 取出 builder 调用时也必须遵守唯一 AST 合同。
- 不公开注册表内部字典或 `_xxx` 管理 helper。
## API详细说明

### `class BuiltinCall(source: ast.Call, dsl_name: str, ast_node: type | None, args: list[BuiltinArgument], kwargs: dict[str, BuiltinArgument], location: SourceLocation, launch_extents: list[BuiltinArgument] | None = None)`

- api：`class BuiltinCall(source: ast.Call, dsl_name: str, ast_node: type | None, args: list[BuiltinArgument], kwargs: dict[str, BuiltinArgument], location: SourceLocation, launch_extents: list[BuiltinArgument] | None = None)`
- 参数：
  - `source`：源对象、源缓冲区或源文本，提供当前操作读取的数据来源；类型 `ast.Call`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `dsl_name`：公开名称或符号名；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `ast_node`：`ast_node` 输入值，参与 `BuiltinCall` 的公开处理流程；类型 `type | None`；无默认值，调用方必须显式提供；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `args`：位置参数序列，按公开调用约定传递给目标函数或工具入口；类型 `list[BuiltinArgument]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
  - `kwargs`：关键字参数映射，按公开调用约定传递给目标函数或工具入口；类型 `dict[str, BuiltinArgument]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
  - `location`：源码位置或 IR 位置，用于诊断、错误报告或生成定位信息；类型 `SourceLocation`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `launch_extents`：`launch_extents` 输入值，参与 `BuiltinCall` 的公开处理流程；类型 `list[BuiltinArgument] | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
- 返回值：`BuiltinCall` 实例。
- 使用示例：

  ```python
  builtin_call = BuiltinCall(source=source, dsl_name=dsl_name, ast_node=ast_node, args=args, kwargs=kwargs, location=location, launch_extents=None)
  ```
- 功能说明：构造 `BuiltinCall` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class BuiltinEntry(dsl_name: str, op: BuiltinOperation, ast_node: type | None, builder: BuiltinBuilder)`

- api：`class BuiltinEntry(dsl_name: str, op: BuiltinOperation, ast_node: type | None, builder: BuiltinBuilder)`
- 参数：
  - `dsl_name`：公开名称或符号名；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `op`：IR operation，作为 emit、rewrite、lowering 或校验的当前处理对象；类型 `BuiltinOperation`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `ast_node`：`ast_node` 输入值，参与 `BuiltinEntry` 的公开处理流程；类型 `type | None`；无默认值，调用方必须显式提供；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `builder`：构建器对象，用于创建 DSL、IR、AST 或源码结构；类型 `BuiltinBuilder`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`BuiltinEntry` 实例。
- 使用示例：

  ```python
  builtin_entry = BuiltinEntry(dsl_name=dsl_name, op=op, ast_node=ast_node, builder=builder)
  ```
- 功能说明：构造 `BuiltinEntry` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `dsl_builtin(op: BuiltinOperation, ast_node: type[T]) -> Callable[[Callable[[BuiltinCall], T]], Callable[[BuiltinCall], T]]`

- api：`dsl_builtin(op: BuiltinOperation, ast_node: type[T]) -> Callable[[Callable[[BuiltinCall], T]], Callable[[BuiltinCall], T]]`
- 参数：
  - `op`：IR operation，作为 emit、rewrite、lowering 或校验的当前处理对象；类型 `BuiltinOperation`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `ast_node`：`ast_node` 输入值，参与 `dsl_builtin` 的公开处理流程；类型 `type[T]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Callable[[Callable[[BuiltinCall], T]], Callable[[BuiltinCall], T]]`。
- 使用示例：

  ```python
  result = dsl_builtin(op=op, ast_node=ast_node)
  ```
- 功能说明：执行 `dsl_builtin`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `external_builtin(func: BuiltinOperation, name: str | None = None) -> Callable[[BuiltinBuilder], BuiltinBuilder]`

- api：`external_builtin(func: BuiltinOperation, name: str | None = None) -> Callable[[BuiltinBuilder], BuiltinBuilder]`
- 参数：
  - `func`：函数对象或函数级 IR，作为构建、lowering 或代码生成输入；类型 `BuiltinOperation`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `name`：公开名称、符号名或注册名，用于查找、打印、注册或生成稳定标识；类型 `str | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Callable[[BuiltinBuilder], BuiltinBuilder]`。
- 使用示例：

  ```python
  result = external_builtin(func=func, name=None)
  ```
- 功能说明：执行 `external_builtin`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `lookup_builtin(op: BuiltinOperation) -> BuiltinEntry | None`

- api：`lookup_builtin(op: BuiltinOperation) -> BuiltinEntry | None`
- 参数：
  - `op`：IR operation，作为 emit、rewrite、lowering 或校验的当前处理对象；类型 `BuiltinOperation`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`BuiltinEntry | None`。
- 使用示例：

  ```python
  result = lookup_builtin(op=op)
  ```
- 功能说明：执行 `lookup_builtin`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `all_builtin_names() -> set[str]`

- api：`all_builtin_names() -> set[str]`
- 参数：无。
- 返回值：`set[str]`。
- 使用示例：

  ```python
  result = all_builtin_names()
  ```
- 功能说明：执行 `all_builtin_names`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

## 测试

- 测试文件：`test/dsl/ast/plugin/test_registry.py`
- 执行命令：`pytest -q test/dsl/ast/plugin/test_registry.py`

### 测试目标

- 注册名可查询，重复注册稳定失败。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-AST-PLUGIN-REGISTRY-001 | 公开入口 | DSL builtin operation binds to one ast node | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_dsl_builtin_operation_binds_to_one_ast_node`。 | 公开入口在“DSL builtin operation binds to one ast node”场景下可导入、构造、注册或按名称发现。 | `test_dsl_builtin_operation_binds_to_one_ast_node` |
| TC-DSL-AST-PLUGIN-REGISTRY-002 | 边界/异常 | DSL builtin rejects manual name argument | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dsl_builtin_rejects_manual_name_argument`。 | “DSL builtin rejects manual name argument”场景按公开错误语义失败或被拒绝。 | `test_dsl_builtin_rejects_manual_name_argument` |
| TC-DSL-AST-PLUGIN-REGISTRY-003 | 公开入口 | DSL builtin ast node cannot bind multiple operations | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_dsl_builtin_ast_node_cannot_bind_multiple_operations`。 | 公开入口在“DSL builtin ast node cannot bind multiple operations”场景下可导入、构造、注册或按名称发现。 | `test_dsl_builtin_ast_node_cannot_bind_multiple_operations` |
| TC-DSL-AST-PLUGIN-REGISTRY-004 | 公开入口 | DSL builtin builder must return declared ast node | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_dsl_builtin_builder_must_return_declared_ast_node`。 | 公开入口在“DSL builtin builder must return declared ast node”场景下可导入、构造、注册或按名称发现。 | `test_dsl_builtin_builder_must_return_declared_ast_node` |
| TC-DSL-AST-PLUGIN-REGISTRY-005 | 边界/异常 | DSL builtin builder rejects declared ast subclass | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dsl_builtin_builder_rejects_declared_ast_subclass`。 | “DSL builtin builder rejects declared ast subclass”场景按公开错误语义失败或被拒绝。 | `test_dsl_builtin_builder_rejects_declared_ast_subclass` |
