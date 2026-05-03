# DSL AST Visitor

## 功能简介

- `kernel_gen.dsl.ast.dsl_ast` 定义 `DslAstVisitor`，负责把 Python `ast` 树解析为 DSL AST 节点。
- visitor 的非空 `visit_*` 返回值必须是 `DSLNode`；import 与 docstring 允许返回 `None`，空 return 生成 `ReturnAST`。
- 解析阶段必须通过 `ValueAST.result_symbol()` / `result_scalar()` 区分 symbol 运算、NN 运算与布尔条件，不再生成旧 `BinaryExprAST(op=...)` / `CompareExprAST(op=...)`。
- 赋值绑定只读取右侧 `ValueAST.binding_value()` / `bind_target(...)`，不得在 visitor 内维护跨 DMA/NN/symbol 节点的中央推导逻辑。
- 函数输入构造必须委托 `FunctionAST.input_from_runtime_arg(...)` / `FunctionAST.input_from_bound_value(...)`，不得在 `visit_FunctionDef(...)` 中复制 runtime 类型工厂。
- Python callee 解析通过公开 visitor API `runtime_arg_key(...)`、`parse_python_callee(...)`、`build_python_callee_call(...)` 承接；不再把 callee 解析藏在 `_xxx` 私有方法中。

## API 列表

- `class DslAstVisitor(fn: DslCallable, runtime_args: tuple[DslRuntimeArg, ...] = ())`
- `DslAstVisitor.runtime_arg_key(value: DslVisitValue) -> RuntimeArgKey`
- `DslAstVisitor.parse_python_callee(callee: DslCallable, args: tuple[DSLNode, ...], location: SourceLocation | None) -> FunctionAST`
- `DslAstVisitor.build_python_callee_call(callee: DslCallable, args: list[DSLNode], kwargs: dict[str, DSLNode], location: SourceLocation | None) -> CallAST`
- `DslAstVisitor.visit(node: ast.AST) -> DSLNode | None`
- `DslAstVisitor.visit_Module(node: ast.Module) -> ModuleAST`
- `DslAstVisitor.visit_FunctionDef(node: ast.FunctionDef) -> FunctionAST`
- `DslAstVisitor.visit_Import(node: ast.Import) -> None`
- `DslAstVisitor.visit_ImportFrom(node: ast.ImportFrom) -> None`
- `DslAstVisitor.visit_Assign(node: ast.Assign) -> DSLNode | None`
- `DslAstVisitor.visit_AugAssign(node: ast.AugAssign) -> DSLNode | None`
- `DslAstVisitor.visit_For(node: ast.For) -> ForAST | None`
- `DslAstVisitor.visit_If(node: ast.If) -> IfAST`
- `DslAstVisitor.visit_Return(node: ast.Return) -> ReturnAST`
- `DslAstVisitor.visit_Expr(node: ast.Expr) -> DSLNode | None`
- `DslAstVisitor.visit_BinOp(node: ast.BinOp) -> ValueAST`
- `DslAstVisitor.visit_Compare(node: ast.Compare) -> ValueAST`
- `DslAstVisitor.visit_Call(node: ast.Call) -> DSLNode`
- `DslAstVisitor.visit_List(node: ast.List) -> SymbolListAST | TupleAST`
- `DslAstVisitor.visit_Tuple(node: ast.Tuple) -> TupleAST`
- `DslAstVisitor.visit_keyword(node: ast.keyword) -> TupleAST`
- `DslAstVisitor.visit_Name(node: ast.Name) -> DSLNode`
- `DslAstVisitor.visit_Constant(node: ast.Constant) -> ConstValueAST | BoolValueAST`
- `DslAstVisitor.visit_Subscript(node: ast.Subscript) -> DSLNode`
- `DslAstVisitor.visit_UnaryOp(node: ast.UnaryOp) -> ConstValueAST`
- `DslAstVisitor.visit_Attribute(node: ast.Attribute) -> DSLNode`

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：`spec/dsl/ast/dsl_ast.md`
- `功能实现`：`kernel_gen/dsl/ast/dsl_ast.py`
- `test`：`test/dsl/ast/test_dsl_ast.py`、`test/dsl/ast/test_parser.py`

## 依赖

- `spec/dsl/ast/nodes/basic.md`：基础节点、函数、block 与 memory 节点。
- `spec/dsl/ast/nodes/symbol.md`：symbol 表达式与 symbol 列表。
- `spec/dsl/ast/nodes/control_flow.md`：`ForAST` / `IfAST` 控制流节点。
- `spec/dsl/ast/plugin/registry.md`：DSL builtin 注册表。
- `kernel_gen.operation.dma`、`kernel_gen.operation.nn`、`kernel_gen.operation.arch`：可注册 DSL helper 的 operation 函数对象。

## API详细说明

### `class DslAstVisitor(fn: DslCallable, runtime_args: tuple[DslRuntimeArg, ...] = ())`

- api：`class DslAstVisitor(fn: DslCallable, runtime_args: tuple[DslRuntimeArg, ...] = ())`
- 参数：
  - `fn`：DSL Python 函数；类型 `DslCallable`；无默认值；不允许 None；函数源码必须可被公开 parser 读取。
  - `runtime_args`：运行时参数序列；类型 `tuple[DslRuntimeArg, ...]`；默认值 `()`；默认值为空 tuple；每个参数必须是公开 DSL runtime 支持的类型。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel, runtime_args=(lhs, rhs))
    ```
- 功能说明：构造 Python AST 到 DSL AST 的 visitor，绑定 DSL 函数与运行时参数。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点。

### `DslAstVisitor.runtime_arg_key(value: DslVisitValue) -> RuntimeArgKey`

- api：`DslAstVisitor.runtime_arg_key(value: DslVisitValue) -> RuntimeArgKey`
- 参数：
  - `value`：runtime 参数或 caller 侧 DSL 值；类型 `DslVisitValue`；无默认值；用于 Python callee 签名去重。
- 返回值：`RuntimeArgKey`；由类型名和稳定字段组成的签名 key。
- 使用示例：

  ```python
  key = visitor.runtime_arg_key(value)
  ```
- 功能说明：为 Python callee 调用生成稳定签名 key，用于拒绝同一 callee 的多签名调用。
- 注意事项：该 API 只用于解析期签名管理，不得作为 runtime 类型推断或 emit 依据。

### `DslAstVisitor.parse_python_callee(callee: DslCallable, args: tuple[DSLNode, ...], location: SourceLocation | None) -> FunctionAST`

- api：`DslAstVisitor.parse_python_callee(callee: DslCallable, args: tuple[DSLNode, ...], location: SourceLocation | None) -> FunctionAST`
- 参数：
  - `callee`：Python helper 函数；类型 `DslCallable`；无默认值；源码必须可由 `inspect.getsource(...)` 读取。
  - `args`：caller 侧 DSL 实参；类型 `tuple[DSLNode, ...]`；无默认值；必须与 callee 形参数量一致。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：`FunctionAST`；解析后的 callee 函数 AST。
- 使用示例：

  ```python
  callee_ast = visitor.parse_python_callee(helper, (memory_ast,), location)
  ```
- 功能说明：即时解析合法 Python callee，完成源码读取、递归检测、签名去重和 `FunctionAST` 构造。
- 注意事项：递归 callee、源码不可读、同一 callee 多签名调用必须稳定失败。

### `DslAstVisitor.build_python_callee_call(callee: DslCallable, args: list[DSLNode], kwargs: dict[str, DSLNode], location: SourceLocation | None) -> CallAST`

- api：`DslAstVisitor.build_python_callee_call(callee: DslCallable, args: list[DSLNode], kwargs: dict[str, DSLNode], location: SourceLocation | None) -> CallAST`
- 参数：
  - `callee`：Python helper 函数；类型 `DslCallable`；无默认值；必须是可解析函数。
  - `args`：caller 侧 DSL 实参；类型 `list[DSLNode]`；无默认值；每一项必须是 `ValueAST`。
  - `kwargs`：关键字实参；类型 `dict[str, DSLNode]`；无默认值；当前必须为空。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：`CallAST`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
  call_ast = visitor.build_python_callee_call(helper, args, {}, location)
  ```
- 功能说明：构造 Python callee 语句调用 AST；只支持无返回值 callee 下沉为 `func.call`。
- 注意事项：Python callee 不支持 keyword，不支持作为值表达式使用，不支持有返回值。

### `DslAstVisitor.visit(node: ast.AST) -> DSLNode | None`

- api：`DslAstVisitor.visit(node: ast.AST) -> DSLNode | None`
- 参数：
  - `node`：Python AST 节点；类型 `ast.AST`；无默认值；不允许 None；必须来自标准库 ast 解析结果。
- 返回值：`DSLNode | None`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel)
    result = visitor.visit(node=node)
    ```
- 功能说明：访问标准库 `visit` AST 节点并返回对应 DSL AST 公开节点。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点。

### `DslAstVisitor.visit_Module(node: ast.Module) -> ModuleAST`

- api：`DslAstVisitor.visit_Module(node: ast.Module) -> ModuleAST`
- 参数：
  - `node`：Python AST 节点；类型 `ast.Module`；无默认值；不允许 None；必须来自标准库 ast 解析结果。
- 返回值：`ModuleAST`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel)
    result = visitor.visit_Module(node=node)
    ```
- 功能说明：访问标准库 `Module` AST 节点并返回对应 DSL AST 公开节点。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点。

### `DslAstVisitor.visit_FunctionDef(node: ast.FunctionDef) -> FunctionAST`

- api：`DslAstVisitor.visit_FunctionDef(node: ast.FunctionDef) -> FunctionAST`
- 参数：
  - `node`：Python AST 节点；类型 `ast.FunctionDef`；无默认值；不允许 None；必须来自标准库 ast 解析结果。
- 返回值：`FunctionAST`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel)
    result = visitor.visit_FunctionDef(node=node)
    ```
- 功能说明：访问标准库 `FunctionDef` AST 节点并返回对应 DSL AST 公开节点。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点。

### `DslAstVisitor.visit_Import(node: ast.Import) -> None`

- api：`DslAstVisitor.visit_Import(node: ast.Import) -> None`
- 参数：
  - `node`：Python AST 节点；类型 `ast.Import`；无默认值；不允许 None；必须来自标准库 ast 解析结果。
- 返回值：无返回值；调用成功表示对应 AST、IR 或 runtime 动作已完成。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel)
    result = visitor.visit_Import(node=node)
    ```
- 功能说明：访问标准库 `Import` AST 节点并返回对应 DSL AST 公开节点。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点。

### `DslAstVisitor.visit_ImportFrom(node: ast.ImportFrom) -> None`

- api：`DslAstVisitor.visit_ImportFrom(node: ast.ImportFrom) -> None`
- 参数：
  - `node`：Python AST 节点；类型 `ast.ImportFrom`；无默认值；不允许 None；必须来自标准库 ast 解析结果。
- 返回值：无返回值；调用成功表示对应 AST、IR 或 runtime 动作已完成。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel)
    result = visitor.visit_ImportFrom(node=node)
    ```
- 功能说明：访问标准库 `ImportFrom` AST 节点并返回对应 DSL AST 公开节点。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点。

### `DslAstVisitor.visit_Assign(node: ast.Assign) -> DSLNode | None`

- api：`DslAstVisitor.visit_Assign(node: ast.Assign) -> DSLNode | None`
- 参数：
  - `node`：Python AST 节点；类型 `ast.Assign`；无默认值；不允许 None；必须来自标准库 ast 解析结果。
- 返回值：`DSLNode | None`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel)
    result = visitor.visit_Assign(node=node)
    ```
- 功能说明：访问标准库 `Assign` AST 节点并返回对应 DSL AST 公开节点；名称绑定必须委托右侧 `ValueAST.binding_value()` / `bind_target(...)`。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点。

### `DslAstVisitor.visit_AugAssign(node: ast.AugAssign) -> DSLNode | None`

- api：`DslAstVisitor.visit_AugAssign(node: ast.AugAssign) -> DSLNode | None`
- 参数：
  - `node`：Python AST 节点；类型 `ast.AugAssign`；无默认值；不允许 None；必须来自标准库 ast 解析结果。
- 返回值：`DSLNode | None`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel)
    result = visitor.visit_AugAssign(node=node)
    ```
- 功能说明：访问标准库 `AugAssign` AST 节点并返回对应 DSL AST 公开节点。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点。

### `DslAstVisitor.visit_For(node: ast.For) -> ForAST | None`

- api：`DslAstVisitor.visit_For(node: ast.For) -> ForAST | None`
- 参数：
  - `node`：Python AST 节点；类型 `ast.For`；无默认值；不允许 None；必须来自标准库 ast 解析结果。
- 返回值：`ForAST | None`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel)
    result = visitor.visit_For(node=node)
    ```
- 功能说明：访问标准库 `For` AST 节点并返回对应 DSL AST 公开节点。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点。

### `DslAstVisitor.visit_If(node: ast.If) -> IfAST`

- api：`DslAstVisitor.visit_If(node: ast.If) -> IfAST`
- 参数：
  - `node`：Python AST 节点；类型 `ast.If`；无默认值；不允许 None；必须来自标准库 ast 解析结果。
- 返回值：`IfAST`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel)
    result = visitor.visit_If(node=node)
    ```
- 功能说明：访问标准库 `If` AST 节点并返回对应 DSL AST 公开节点。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点。

### `DslAstVisitor.visit_Return(node: ast.Return) -> ReturnAST`

- api：`DslAstVisitor.visit_Return(node: ast.Return) -> ReturnAST`
- 参数：
  - `node`：Python AST 节点；类型 `ast.Return`；无默认值；不允许 None；必须来自标准库 ast 解析结果。
- 返回值：`ReturnAST`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel)
    result = visitor.visit_Return(node=node)
    ```
- 功能说明：访问标准库 `Return` AST 节点并返回对应 DSL AST 公开节点。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点。

### `DslAstVisitor.visit_Expr(node: ast.Expr) -> DSLNode | None`

- api：`DslAstVisitor.visit_Expr(node: ast.Expr) -> DSLNode | None`
- 参数：
  - `node`：Python AST 节点；类型 `ast.Expr`；无默认值；不允许 None；必须来自标准库 ast 解析结果。
- 返回值：`DSLNode | None`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel)
    result = visitor.visit_Expr(node=node)
    ```
- 功能说明：访问标准库 `Expr` AST 节点并返回对应 DSL AST 公开节点。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点。

### `DslAstVisitor.visit_BinOp(node: ast.BinOp) -> ValueAST`

- api：`DslAstVisitor.visit_BinOp(node: ast.BinOp) -> ValueAST`
- 参数：
  - `node`：Python AST 节点；类型 `ast.BinOp`；无默认值；不允许 None；必须来自标准库 ast 解析结果。
- 返回值：`ValueAST`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel)
    result = visitor.visit_BinOp(node=node)
    ```
- 功能说明：访问标准库 `BinOp` AST 节点并返回对应 DSL AST 公开节点。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点。

### `DslAstVisitor.visit_Compare(node: ast.Compare) -> ValueAST`

- api：`DslAstVisitor.visit_Compare(node: ast.Compare) -> ValueAST`
- 参数：
  - `node`：Python AST 节点；类型 `ast.Compare`；无默认值；不允许 None；必须来自标准库 ast 解析结果。
- 返回值：`ValueAST`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel)
    result = visitor.visit_Compare(node=node)
    ```
- 功能说明：访问标准库 `Compare` AST 节点并返回对应 DSL AST 公开节点。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点。

### `DslAstVisitor.visit_Call(node: ast.Call) -> DSLNode`

- api：`DslAstVisitor.visit_Call(node: ast.Call) -> DSLNode`
- 参数：
  - `node`：Python AST 节点；类型 `ast.Call`；无默认值；不允许 None；必须来自标准库 ast 解析结果。
- 返回值：`DSLNode`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel)
    result = visitor.visit_Call(node=node)
    ```
- 功能说明：访问标准库 `Call` AST 节点并返回对应 DSL AST 公开节点；当 callee 是内置名称 `min` 且恰有两个位置参数时，返回 `SymbolMinAST`。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点；`min(...)` 不接受关键字参数、多参数或非符号 DSL 值扩展。

### `DslAstVisitor.visit_List(node: ast.List) -> SymbolListAST | TupleAST`

- api：`DslAstVisitor.visit_List(node: ast.List) -> SymbolListAST | TupleAST`
- 参数：
  - `node`：Python AST 节点；类型 `ast.List`；无默认值；不允许 None；必须来自标准库 ast 解析结果。
- 返回值：`SymbolListAST | TupleAST`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel)
    result = visitor.visit_List(node=node)
    ```
- 功能说明：访问标准库 `List` AST 节点并返回对应 DSL AST 公开节点。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点。

### `DslAstVisitor.visit_Tuple(node: ast.Tuple) -> TupleAST`

- api：`DslAstVisitor.visit_Tuple(node: ast.Tuple) -> TupleAST`
- 参数：
  - `node`：Python AST 节点；类型 `ast.Tuple`；无默认值；不允许 None；必须来自标准库 ast 解析结果。
- 返回值：`TupleAST`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel)
    result = visitor.visit_Tuple(node=node)
    ```
- 功能说明：访问标准库 `Tuple` AST 节点并返回对应 DSL AST 公开节点。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点。

### `DslAstVisitor.visit_keyword(node: ast.keyword) -> TupleAST`

- api：`DslAstVisitor.visit_keyword(node: ast.keyword) -> TupleAST`
- 参数：
  - `node`：Python AST 节点；类型 `ast.keyword`；无默认值；不允许 None；必须来自标准库 ast 解析结果。
- 返回值：`TupleAST`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel)
    result = visitor.visit_keyword(node=node)
    ```
- 功能说明：访问标准库 `keyword` AST 节点并返回对应 DSL AST 公开节点。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点。

### `DslAstVisitor.visit_Name(node: ast.Name) -> DSLNode`

- api：`DslAstVisitor.visit_Name(node: ast.Name) -> DSLNode`
- 参数：
  - `node`：Python AST 节点；类型 `ast.Name`；无默认值；不允许 None；必须来自标准库 ast 解析结果。
- 返回值：`DSLNode`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel)
    result = visitor.visit_Name(node=node)
    ```
- 功能说明：访问标准库 `Name` AST 节点并返回对应 DSL AST 公开节点。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点。

### `DslAstVisitor.visit_Constant(node: ast.Constant) -> ConstValueAST | BoolValueAST`

- api：`DslAstVisitor.visit_Constant(node: ast.Constant) -> ConstValueAST | BoolValueAST`
- 参数：
  - `node`：Python AST 节点；类型 `ast.Constant`；无默认值；不允许 None；必须来自标准库 ast 解析结果。
- 返回值：`ConstValueAST | BoolValueAST`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel)
    result = visitor.visit_Constant(node=node)
    ```
- 功能说明：访问标准库 `Constant` AST 节点并返回对应 DSL AST 公开节点。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点。

### `DslAstVisitor.visit_Subscript(node: ast.Subscript) -> DSLNode`

- api：`DslAstVisitor.visit_Subscript(node: ast.Subscript) -> DSLNode`
- 参数：
  - `node`：Python AST 节点；类型 `ast.Subscript`；无默认值；不允许 None；必须来自标准库 ast 解析结果。
- 返回值：`DSLNode`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel)
    result = visitor.visit_Subscript(node=node)
    ```
- 功能说明：访问标准库 `Subscript` AST 节点并返回对应 DSL AST 公开节点。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点。

### `DslAstVisitor.visit_UnaryOp(node: ast.UnaryOp) -> ConstValueAST`

- api：`DslAstVisitor.visit_UnaryOp(node: ast.UnaryOp) -> ConstValueAST`
- 参数：
  - `node`：Python AST 节点；类型 `ast.UnaryOp`；无默认值；不允许 None；必须来自标准库 ast 解析结果。
- 返回值：`ConstValueAST`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel)
    result = visitor.visit_UnaryOp(node=node)
    ```
- 功能说明：访问标准库 `UnaryOp` AST 节点并返回对应 DSL AST 公开节点。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点。

### `DslAstVisitor.visit_Attribute(node: ast.Attribute) -> DSLNode`

- api：`DslAstVisitor.visit_Attribute(node: ast.Attribute) -> DSLNode`
- 参数：
  - `node`：Python AST 节点；类型 `ast.Attribute`；无默认值；不允许 None；必须来自标准库 ast 解析结果。
- 返回值：`DSLNode`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor

    visitor = DslAstVisitor(kernel)
    result = visitor.visit_Attribute(node=node)
    ```
- 功能说明：访问标准库 `Attribute` AST 节点并返回对应 DSL AST 公开节点。
- 注意事项：输入必须来自标准库 `ast` 与公开 DSL runtime 类型；不支持的语法必须通过公开 `KernelCodeError` 失败，不得静默生成内部占位节点。

## 测试

- 测试文件：
  - `test/dsl/ast/test_dsl_ast.py`
  - `test/dsl/ast/test_parser.py`
- 执行命令：`pytest -q test/dsl/ast/test_dsl_ast.py test/dsl/ast/test_parser.py`

### 测试目标

- visitor 标准入口、runtime arg 解析、symbol/NN 表达式分流、稳定错误。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-AST-DSL-AST-001 | 公开入口 | DSL ast visitor exposes standard node visitor methods | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_dsl_ast_visitor_exposes_standard_node_visitor_methods`。 | 公开入口在“DSL ast visitor exposes standard node visitor methods”场景下可导入、构造、注册或按名称发现。 | `test_dsl_ast_visitor_exposes_standard_node_visitor_methods` |
| TC-DSL-AST-DSL-AST-002 | 公开入口 | DSL ast unknown attribute base reports unknown name | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_dsl_ast_unknown_attribute_base_reports_unknown_name`。 | 公开入口在“DSL ast unknown attribute base reports unknown name”场景下可导入、构造、注册或按名称发现。 | `test_dsl_ast_unknown_attribute_base_reports_unknown_name` |
| TC-DSL-AST-DSL-AST-003 | 解析/打印 | parse function basic assignment | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_function_basic_assignment`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_function_basic_assignment` |
| TC-DSL-AST-DSL-AST-004 | 解析/打印 | parse function for loop | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_function_for_loop`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_function_for_loop` |
| TC-DSL-AST-DSL-AST-005 | 解析/打印 | parse function if else | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_function_if_else`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_function_if_else` |
| TC-DSL-AST-DSL-AST-006 | 解析/打印 | parse infers runtime annotation | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_infers_runtime_annotation`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_infers_runtime_annotation` |
| TC-DSL-AST-DSL-AST-007 | 解析/打印 | parse function reports diagnostics | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_function_reports_diagnostics`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_function_reports_diagnostics` |
| TC-DSL-AST-DSL-AST-008 | 边界/异常 | parse function step zero rejected | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_parse_function_step_zero_rejected`。 | “parse function step zero rejected”场景按公开错误语义失败或被拒绝。 | `test_parse_function_step_zero_rejected` |
| TC-DSL-AST-DSL-AST-009 | 解析/打印 | ast parse function uses runtime memory not annotation | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_ast_parse_function_uses_runtime_memory_not_annotation`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_ast_parse_function_uses_runtime_memory_not_annotation` |
| TC-DSL-AST-DSL-AST-010 | 边界/异常 | ast parse requires runtime args for parameters | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_ast_parse_requires_runtime_args_for_parameters`。 | “ast parse requires runtime args for parameters”场景按公开错误语义失败或被拒绝。 | `test_ast_parse_requires_runtime_args_for_parameters` |
| TC-DSL-AST-DSL-AST-011 | 解析/打印 | ast parse module entry returns module ast | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_ast_parse_module_entry_returns_module_ast`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_ast_parse_module_entry_returns_module_ast` |
| TC-DSL-AST-DSL-AST-012 | 解析/打印 | parse function ignores formatted tensor annotation arithmetic variants | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_function_ignores_formatted_tensor_annotation_arithmetic_variants`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_function_ignores_formatted_tensor_annotation_arithmetic_variants` |
| TC-DSL-AST-DSL-AST-013 | 解析/打印 | parse function ignores unsupported formatted tensor annotations | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_function_ignores_unsupported_formatted_tensor_annotations`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_function_ignores_unsupported_formatted_tensor_annotations` |
| TC-DSL-AST-DSL-AST-014 | 解析/打印 | parse function ignores direct tensor annotation expression element | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_function_ignores_direct_tensor_annotation_expression_element`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_function_ignores_direct_tensor_annotation_expression_element` |
| TC-DSL-AST-DSL-AST-015 | 解析/打印 | parse function uses runtime symboldim over union annotation | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_function_uses_runtime_symboldim_over_union_annotation`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_function_uses_runtime_symboldim_over_union_annotation` |
| TC-DSL-AST-DSL-AST-016 | 解析/打印 | parse function ignores unsupported union annotation | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_function_ignores_unsupported_union_annotation`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_function_ignores_unsupported_union_annotation` |
| TC-DSL-AST-DSL-AST-017 | 符号语义 | visit call lowers DSL min to SymbolMinAST | 准备包含 `min(tile, extent - i)` 的 DSL kernel。 | 运行 `test_mlir_gen_lowers_symbol_min_and_iter_arithmetic`。 | parser/visitor 生成 `SymbolMinAST` 并最终 lowered 为 `symbol.min`。 | `test_mlir_gen_lowers_symbol_min_and_iter_arithmetic` |
