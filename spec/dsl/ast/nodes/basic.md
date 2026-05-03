# DSL AST 基础节点

## 功能简介

- `kernel_gen.dsl.ast.nodes.basic` 定义 DSL AST 基类、值节点、语句节点、模块、函数、绑定、调用与 memory 节点。
- `symbol` dialect 相关节点由 `spec/dsl/ast/nodes/symbol.md` 与 `kernel_gen.dsl.ast.nodes.symbol` 承载。
- 控制流节点由 `spec/dsl/ast/nodes/control_flow.md` 与 `kernel_gen.dsl.ast.nodes.control_flow` 承载。
- AST 发射固定通过节点成员递归调用 `emit_mlir(ctx, block)` 完成；`mlir_gen(...)` 的闭环是 `parse(fn, *runtime_args).emit_mlir(ctx, None)`。
- 旧 `TensorAST`、`ConstAST`、`VarAST`、`BinaryExprAST`、`CompareExprAST` 不属于公开 API。

## API 列表

- `DSLNode.emit_mlir(ctx: Context, block: Block | None = None) -> EmitMlirResult`
- `class ValueAST()`
- `ValueAST.result_memory() -> Memory | None`
- `ValueAST.result_symbol() -> int | SymbolDim | None`
- `ValueAST.result_scalar() -> int | float | bool | str | SymbolDim | None`
- `ValueAST.binding_value() -> Memory | int | float | bool | str | SymbolDim | None`
- `ValueAST.bind_target(name: str, location: SourceLocation | None = None) -> MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST | ValueAST`
- `class StatementAST()`
- `class ModuleAST(functions: list[FunctionAST], runtime_args: tuple[PythonObjectAttrAST, ...] = (), source_fn: PythonObjectAttrAST = ...)`
- `ModuleAST.emit_mlir(ctx: Context, block: Block | None = None) -> ModuleOp`
- `class FunctionAST(name: str, inputs: list[MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST], outputs: list[MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST], body: BlockAST, location: SourceLocation | None = None, source: PythonObjectAttrAST = ..., py_ast: PythonObjectAttrAST = ..., diagnostics: PythonObjectAttrAST = ..., has_explicit_return: BoolValueAST = ..., returns_none: BoolValueAST = ..., runtime_args: tuple[PythonObjectAttrAST, ...] = ())`
- `FunctionAST.input_from_runtime_arg(name: str, value: object, location: SourceLocation | None = None) -> MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST`
- `FunctionAST.input_from_bound_value(name: str, value: ValueAST, location: SourceLocation | None = None) -> MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST`
- `FunctionAST.iter_inputs() -> Iterable[MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST]`
- `class MemoryAST(name: str, shape: SymbolListAST, stride: SymbolListAST, type: IntTypeAttrAST | FloatTypeAttrAST | BoolTypeAttrAST, space: MemorySpaceAttrAST, location: SourceLocation | None = None, format: PythonObjectAttrAST = ...)`
- `MemoryAST.dtype_attr_from_numeric_type(dtype: NumericType, location: SourceLocation | None = None) -> IntTypeAttrAST | FloatTypeAttrAST | BoolTypeAttrAST`
- `MemoryAST.numeric_type_from_dtype_attr(dtype: IntTypeAttrAST | FloatTypeAttrAST | BoolTypeAttrAST) -> NumericType`
- `MemoryAST.from_memory(name: str, memory: Memory, location: SourceLocation | None = None) -> MemoryAST`
- `MemoryAST.result_memory() -> Memory | None`
- `MemoryAST.type_from_memory(ctx: Context, memory: Memory, location: SourceLocation | None = None) -> NnMemoryType`
- `MemoryAST.to_mlir_type(ctx: Context) -> NnMemoryType`
- `class BoolValueAST(value: bool, location: SourceLocation | None = None)`
- `BoolValueAST.result_scalar() -> int | float | bool | str | SymbolDim | None`
- `class BlockAST(statements: list[StatementAST | ValueAST], location: SourceLocation | None = None)`
- `BlockAST.emit_mlir(ctx: Context, block: Block | None = None) -> EmitMlirResult`
- `class BoundExprAST(name: str, target: MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST | ValueAST, value: ValueAST, location: SourceLocation | None = None)`
- `class ReturnAST(values: ValueAST | list[ValueAST] | tuple[ValueAST, ...] | None = None, location: SourceLocation | None = None)`
- `class CallAST(callee: FunctionAST, args: list[ValueAST], location: SourceLocation | None = None)`

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：`spec/dsl/ast/nodes/basic.md`
- `功能实现`：`kernel_gen/dsl/ast/nodes/basic.py`
- `test`：`test/dsl/ast/nodes/test_basic.py`

## 依赖

- `spec/dsl/ast/nodes/attr.md`：提供 `SourceLocation`、`PythonObjectAttrAST`、类型属性与 memory space 属性。
- `spec/dsl/ast/nodes/symbol.md`：提供 `SymbolDimAST`、`ConstValueAST`、`SymbolListAST` 与 symbol 运算节点。
- `spec/dsl/ast/nodes/control_flow.md`：提供 `ForAST` 与 `IfAST` 控制流节点。
- `kernel_gen.symbol_variable.memory.Memory`：`MemoryAST` 的 runtime memory 结构来源。
- `kernel_gen.symbol_variable.symbol_dim.SymbolDim`：基础值结果语义中的 symbol 维度来源。
- `xdsl.context.Context`、`xdsl.ir.Block`：`emit_mlir(...)` 的公开上下文与插入 block。

## 额外补充

- `ValueAST.result_memory()` / `result_symbol()` / `result_scalar()` 是解析期结果语义的公开入口，默认返回 `None` 或 `result_symbol()`。
- `ValueAST.binding_value()` / `bind_target(...)` 是赋值绑定公开入口；`DslAstVisitor.visit_Assign(...)` 只通过这两个入口更新后续名称绑定，不维护 visitor 侧 DMA/NN/symbol 中央推导表。
- `MemoryAST.type_from_memory(...)` 是 runtime `Memory` 到 `NnMemoryType` 的统一构造入口；DMA/NN 节点不得各自复制 dtype/space 分支表。
- `FunctionAST.input_from_runtime_arg(...)` 是 runtime 参数到函数输入 AST 的统一构造入口；visitor 不得在 `visit_FunctionDef(...)` 中复制 runtime 类型工厂。
- `FunctionAST.input_from_bound_value(...)` 是 Python callee 参数从 caller 侧 DSL 值复制输入语义的统一构造入口；只允许 memory、symbol、bool、const 这类公开输入节点。
- `basic.py` 不定义 `SymbolAddAST`、`SymbolDimAST`、`SymbolListAST` 等 symbol dialect 节点，也不定义 `ForAST` / `IfAST` 控制流节点；调用方应从对应子模块或包根 `kernel_gen.dsl.ast.nodes` 导入。

## API 详细说明

### `DSLNode.emit_mlir(ctx: Context, block: Block | None = None) -> EmitMlirResult`

- api：`DSLNode.emit_mlir(ctx: Context, block: Block | None = None) -> EmitMlirResult`
- 参数：
  - `ctx`：xDSL 上下文；类型 `Context`；无默认值；不允许 None。
  - `block`：目标 block；类型 `Block | None`；默认值 `None`。
- 返回值：`EmitMlirResult`。
- 功能说明：AST 节点统一发射入口；基类只定义合同，具体节点必须实现。
- 注意事项：不得回退到中心化 dispatcher 或 visitor 私有状态。

### `ValueAST.bind_target(name: str, location: SourceLocation | None = None) -> MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST | ValueAST`

- api：`ValueAST.bind_target(name: str, location: SourceLocation | None = None) -> MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST | ValueAST`
- 参数：
  - `name`：赋值左侧名称；类型 `str`；无默认值；不允许空字符串。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`。
- 返回值：公开 AST 节点。
- 功能说明：根据当前值节点公开结果语义构造赋值目标节点；memory 绑定为 `MemoryAST`，symbol 绑定为 `SymbolDimAST`，布尔与浮点绑定为对应常量节点，无解析期结果时返回当前值节点。
- 注意事项：该接口只负责名称绑定目标构造；不得创建额外 MLIR operation。

### `FunctionAST.input_from_runtime_arg(name: str, value: object, location: SourceLocation | None = None) -> MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST`

- api：`FunctionAST.input_from_runtime_arg(name: str, value: object, location: SourceLocation | None = None) -> MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST`
- 参数：
  - `name`：函数参数名；类型 `str`；无默认值。
  - `value`：runtime 参数；类型 `object`；无默认值。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`。
- 返回值：函数输入 AST 节点。
- 功能说明：统一 runtime 参数到 `FunctionAST.inputs` 的构造规则。
- 注意事项：当前只支持 `Memory`、`SymbolDim`、`int`、`float`、`bool`；`NnMemoryType` 与未知对象按公开错误语义拒绝。

### `FunctionAST.input_from_bound_value(name: str, value: ValueAST, location: SourceLocation | None = None) -> MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST`

- api：`FunctionAST.input_from_bound_value(name: str, value: ValueAST, location: SourceLocation | None = None) -> MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST`
- 参数：
  - `name`：callee 参数名；类型 `str`；无默认值。
  - `value`：caller 侧 DSL 值；类型 `ValueAST`；无默认值。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`。
- 返回值：函数输入 AST 节点。
- 功能说明：Python callee 参数绑定 caller 侧 DSL 节点时，通过该公开入口复制输入语义。
- 注意事项：只允许 memory、symbol、bool、const；非输入值节点直接失败，避免 callee 参数从任意表达式隐式推导。

### `MemoryAST.type_from_memory(ctx: Context, memory: Memory, location: SourceLocation | None = None) -> NnMemoryType`

- api：`MemoryAST.type_from_memory(ctx: Context, memory: Memory, location: SourceLocation | None = None) -> NnMemoryType`
- 参数：
  - `ctx`：xDSL 上下文；类型 `Context`；无默认值。
  - `memory`：runtime memory；类型 `Memory`；无默认值。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`。
- 返回值：`NnMemoryType`。
- 功能说明：统一 shape、stride、dtype、space 到 MLIR memory type 的映射。
- 注意事项：dtype 与 space 映射只能通过公开 attr 节点完成。

## 测试

- 测试文件：`test/dsl/ast/nodes/test_basic.py`
- 执行命令：`pytest -q test/dsl/ast/nodes/test_basic.py`

### 测试目标

- 基础节点构造、输入迭代、runtime 输入构造、Python callee 输入构造、`ReturnAST` 多返回、`CallAST` callee 签名、memory type 构造与旧节点退场。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-AST-NODES-BASIC-001 | 公开入口 | basic nodes construct expr block | 可导入公开基础节点和 symbol 节点。 | 运行 `test_basic_nodes_construct_expr_block`。 | Block/BoundExpr 能组合公开 ValueAST。 | `test_basic_nodes_construct_expr_block` |
| TC-DSL-AST-NODES-BASIC-002 | 公开入口 | function ast iter inputs returns declared inputs | 构造 memory 与 symbol 输入。 | 运行 `test_function_ast_iter_inputs_returns_declared_inputs`。 | `iter_inputs()` 按声明顺序返回输入。 | `test_function_ast_iter_inputs_returns_declared_inputs` |
| TC-DSL-AST-NODES-BASIC-003 | 公开入口 | function ast constructs inputs from runtime args | 准备 Memory、SymbolDim、int、float、bool。 | 运行 `test_function_ast_constructs_inputs_from_runtime_args`。 | runtime 参数被转换成对应输入 AST。 | `test_function_ast_constructs_inputs_from_runtime_args` |
| TC-DSL-AST-NODES-BASIC-004 | 公开入口 | function ast constructs inputs from bound values | 准备 caller 侧公开 ValueAST。 | 运行 `test_function_ast_constructs_inputs_from_bound_values`。 | callee 输入复制 caller 侧语义。 | `test_function_ast_constructs_inputs_from_bound_values` |
| TC-DSL-AST-NODES-BASIC-005 | 执行结果 | memory ast builds MLIR type from runtime memory | 准备 MemoryAST。 | 运行 `test_memory_ast_builds_mlir_type_from_runtime_memory`。 | 生成稳定 `NnMemoryType`。 | `test_memory_ast_builds_mlir_type_from_runtime_memory` |
| TC-DSL-AST-NODES-BASIC-006 | 边界/异常 | call ast rejects callee return value | 构造带返回值的 callee。 | 运行 `test_call_ast_rejects_callee_return_value`。 | 按公开错误拒绝返回值 callee。 | `test_call_ast_rejects_callee_return_value` |
| TC-DSL-AST-NODES-BASIC-007 | 退场边界 | basic module does not define legacy or symbol/control-flow nodes | 导入 `kernel_gen.dsl.ast.nodes.basic`。 | 运行 `test_basic_module_does_not_define_legacy_nodes`。 | 旧节点、symbol dialect 节点和控制流节点不在 basic.py 定义。 | `test_basic_module_does_not_define_legacy_nodes` |
