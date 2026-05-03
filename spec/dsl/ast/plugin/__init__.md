# __init__.md

## 功能简介

- 定义 `kernel_gen.dsl.ast.plugin` 包导出合同。
- 导入 `nn.py`、`dma.py`、`arch.py` 以触发默认 builtin 注册。
- emit lowering 已迁出 plugin 包；plugin 只负责 parser builtin 注册。

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
- `spec`：[`spec/dsl/ast/plugin/__init__.md`](../../../../spec/dsl/ast/plugin/__init__.md)
- `功能实现`：[`kernel_gen/dsl/ast/plugin/__init__.py`](../../../../kernel_gen/dsl/ast/plugin/__init__.py)
- `test`：[`test/dsl/ast/plugin/test_package.py`](../../../../test/dsl/ast/plugin/test_package.py)

## 依赖

- [`spec/dsl/ast/plugin/registry.md`](../../../../spec/dsl/ast/plugin/registry.md)
- [`spec/dsl/ast/plugin/nn.md`](../../../../spec/dsl/ast/plugin/nn.md)
- [`spec/dsl/ast/plugin/dma.md`](../../../../spec/dsl/ast/plugin/dma.md)
- [`spec/dsl/ast/plugin/arch.md`](../../../../spec/dsl/ast/plugin/arch.md)

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 包根只导出 registry 公开 API。
- `nn` / `dma` / `arch` 子模块只允许提供注册副作用，不提供额外公开函数。
- `emit_*.py` 不得在 plugin 包内恢复；AST emit 由 `DSLNode.emit_mlir(...)` 递归链路承接。
- `@dsl_builtin(op, AstNode)` 必须建立 operation 到唯一 AST 类型的一一绑定；builder 只能返回声明的精确 `AstNode` 类型。
- `dsl_builtin(...)` 不允许传入手写 `name`。
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

- 测试文件：`test/dsl/ast/plugin/test_package.py`
- 执行命令：`pytest -q test/dsl/ast/plugin/test_package.py`

### 测试目标

- 默认 builtin 被加载并可查询。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-AST-PLUGIN-001 | 公开入口 | plugin package exports registry API and loads builtin modules | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_plugin_package_exports_registry_api_and_loads_builtin_modules`。 | 公开入口在“plugin package exports registry API and loads builtin modules”场景下可导入、构造、注册或按名称发现。 | `test_plugin_package_exports_registry_api_and_loads_builtin_modules` |
