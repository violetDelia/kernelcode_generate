# DSL AST Symbol 节点

## 功能简介

- `kernel_gen.dsl.ast.nodes.symbol` 定义 `symbol` dialect 相关 DSL AST 节点。
- 本文件承载符号维度、整数/浮点常量、符号列表、`symbol.to_float`、memory shape/stride 查询、符号二元运算与符号比较。
- `symbol.for` 控制流节点由 `spec/dsl/ast/nodes/control_flow.md` 与 `kernel_gen.dsl.ast.nodes.control_flow` 承载。
- `basic.py` 不再定义 symbol dialect 节点；调用方应从 `kernel_gen.dsl.ast.nodes.symbol` 或包根 `kernel_gen.dsl.ast.nodes` 导入。

## API 列表

- `class SymbolDimAST(symbol: SymbolDim | int | str, location: SourceLocation | None = None, runtime_symbol: SymbolDim | int | None = None)`
- `SymbolDimAST.result_symbol() -> int | SymbolDim | None`
- `class ConstValueAST(type: IntTypeAttrAST | FloatTypeAttrAST | int | float | str, value: int | float | str | None = None, location: SourceLocation | None = None)`
- `ConstValueAST.result_symbol() -> int | SymbolDim | None`
- `ConstValueAST.result_scalar() -> int | float | bool | str | SymbolDim | None`
- `class SymbolListAST(values: list[ValueAST | int | str | SymbolDim] | tuple[ValueAST | int | str | SymbolDim, ...] | ValueAST | int | str | SymbolDim, location: SourceLocation | None = None)`
- `SymbolListAST.result_symbols() -> list[int | SymbolDim] | None`
- `class SymbolToFloatAST(source: ValueAST, location: SourceLocation | None = None)`
- `class TensorAxisAccessAST(tensor: MemoryAST, kind: PythonObjectAttrAST, axis: ConstValueAST, location: SourceLocation | None = None)`
- `class SymbolAddAST(lhs: SymbolDimAST | ConstValueAST, rhs: SymbolDimAST | ConstValueAST, location: SourceLocation | None = None)`
- `class SymbolSubAST(lhs: SymbolDimAST | ConstValueAST, rhs: SymbolDimAST | ConstValueAST, location: SourceLocation | None = None)`
- `class SymbolMulAST(lhs: SymbolDimAST | ConstValueAST, rhs: SymbolDimAST | ConstValueAST, location: SourceLocation | None = None)`
- `class SymbolTrueDivAST(lhs: SymbolDimAST | ConstValueAST, rhs: SymbolDimAST | ConstValueAST, location: SourceLocation | None = None)`
- `class SymbolFloorDivAST(lhs: SymbolDimAST | ConstValueAST, rhs: SymbolDimAST | ConstValueAST, location: SourceLocation | None = None)`
- `SymbolBinaryAST.result_symbol() -> int | SymbolDim | None`
- `class SymbolEqAST(lhs: SymbolDimAST | ConstValueAST, rhs: SymbolDimAST | ConstValueAST, location: SourceLocation | None = None)`
- `class SymbolNeAST(lhs: SymbolDimAST | ConstValueAST, rhs: SymbolDimAST | ConstValueAST, location: SourceLocation | None = None)`
- `class SymbolLtAST(lhs: SymbolDimAST | ConstValueAST, rhs: SymbolDimAST | ConstValueAST, location: SourceLocation | None = None)`
- `class SymbolLeAST(lhs: SymbolDimAST | ConstValueAST, rhs: SymbolDimAST | ConstValueAST, location: SourceLocation | None = None)`
- `class SymbolGtAST(lhs: SymbolDimAST | ConstValueAST, rhs: SymbolDimAST | ConstValueAST, location: SourceLocation | None = None)`
- `class SymbolGeAST(lhs: SymbolDimAST | ConstValueAST, rhs: SymbolDimAST | ConstValueAST, location: SourceLocation | None = None)`

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：`spec/dsl/ast/nodes/symbol.md`
- `功能实现`：`kernel_gen/dsl/ast/nodes/symbol.py`
- `test`：`test/dsl/ast/nodes/test_symbol.py`

## 依赖

- `spec/dsl/ast/nodes/basic.md`：提供 `ValueAST`、`MemoryAST`。
- `spec/dsl/ast/nodes/attr.md`：提供 `SourceLocation`、`PythonObjectAttrAST`、`IntTypeAttrAST`、`FloatTypeAttrAST`。
- `spec/dsl/ast/nodes/control_flow.md`：提供 `symbol.for` 对应 `ForAST` 控制流节点。
- `kernel_gen.dialect.symbol`：提供 `symbol.*` MLIR op 与 `SymbolValueType`。
- `kernel_gen.symbol_variable.symbol_dim.SymbolDim`：解析期符号维度表达来源。

## 额外补充

- `SymbolDimAST.symbol` 控制 MLIR SSA 名称与绑定查找；`runtime_symbol` 控制解析期 shape/stride/result 语义。
- `ConstValueAST` 的整数发射为 `symbol.const`，浮点发射为 `arith.constant`，布尔发射为 `arith.constant i1`。
- `SymbolListAST.result_symbols()` 只返回 `int | SymbolDim` 列表；任一元素没有公开 symbol 语义时返回 `None`。
- `symbol.py` 不定义 `ForAST`；循环边界和 step 的 `!symbol.int` 合同由 `control_flow.py` 的 `ForAST` 承载。
- `TensorAxisAccessAST` 只负责 memory shape/stride 到 `symbol.get_dim` / `symbol.get_stride` 的查询。
- symbol 二元运算节点必须通过 `result_symbol()` 暴露解析期结果，并通过 `emit_mlir(...)` 生成对应 `symbol.add/sub/mul/div/floordiv`。

## API 详细说明

### `SymbolDimAST.result_symbol() -> int | SymbolDim | None`

- api：`SymbolDimAST.result_symbol() -> int | SymbolDim | None`
- 参数：无。
- 返回值：`int | SymbolDim | None`。
- 功能说明：返回当前符号维度的解析期 symbol 语义。
- 注意事项：不执行跨节点求解；优先返回 `runtime_symbol`。

### `ConstValueAST.result_symbol() -> int | SymbolDim | None`

- api：`ConstValueAST.result_symbol() -> int | SymbolDim | None`
- 参数：无。
- 返回值：`int | SymbolDim | None`。
- 功能说明：整数常量返回 `int`，其他常量返回 `None`。
- 注意事项：`bool` 不作为 symbol 整数。

### `SymbolListAST.result_symbols() -> list[int | SymbolDim] | None`

- api：`SymbolListAST.result_symbols() -> list[int | SymbolDim] | None`
- 参数：无。
- 返回值：`list[int | SymbolDim] | None`。
- 功能说明：逐项读取公开 `result_symbol()`，全部成功时返回同序列表。
- 注意事项：该接口不得接受任意 Python 对象作为列表项。

### `SymbolBinaryAST.result_symbol() -> int | SymbolDim | None`

- api：`SymbolBinaryAST.result_symbol() -> int | SymbolDim | None`
- 参数：无。
- 返回值：`int | SymbolDim | None`。
- 功能说明：对左右 symbol 语义做对应二元组合，供 shape/stride 与赋值绑定复用。
- 注意事项：只覆盖当前节点表达式，不做全局符号化简。

## 测试

- 测试文件：`test/dsl/ast/nodes/test_symbol.py`
- 执行命令：`pytest -q test/dsl/ast/nodes/test_symbol.py`

### 测试目标

- symbol dialect AST 节点的模块归属、公开导入、解析期 symbol 语义和 `SymbolListAST` 聚合语义。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-AST-NODES-SYMBOL-001 | 公开入口 | symbol nodes live in symbol module | 可导入 `kernel_gen.dsl.ast.nodes.symbol`。 | 运行 `test_symbol_nodes_live_in_symbol_module`。 | symbol 节点在 symbol.py，basic.py 不再定义 symbol 节点。 | `test_symbol_nodes_live_in_symbol_module` |
| TC-DSL-AST-NODES-SYMBOL-002 | 符号语义 | symbol binary and list expose result symbol semantics | 构造 `SymbolDimAST`、`ConstValueAST`、`SymbolAddAST`。 | 运行 `test_symbol_binary_and_list_expose_result_symbol_semantics`。 | `result_symbol()` 与 `result_symbols()` 返回稳定解析期符号语义。 | `test_symbol_binary_and_list_expose_result_symbol_semantics` |
