# DSL AST 控制流节点

## 功能简介

- `kernel_gen.dsl.ast.nodes.control_flow` 定义 DSL AST 控制流节点。
- `ForAST` 负责发射 `symbol.for`，`IfAST` 负责发射 `scf.if`。
- `basic.py` 不再承载 `IfAST`，`symbol.py` 不再承载 `ForAST`；控制流节点必须从 `kernel_gen.dsl.ast.nodes.control_flow` 或包根 `kernel_gen.dsl.ast.nodes` 导入。

## API 列表

- `class ForAST(var: SymbolDimAST, start: ValueAST, end: ValueAST, body: BlockAST, step: ValueAST | None = None, location: SourceLocation | None = None)`
- `class IfAST(condition: ValueAST, true_body: BlockAST, false_body: BlockAST | None = None, location: SourceLocation | None = None)`

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：`spec/dsl/ast/nodes/control_flow.md`
- `功能实现`：`kernel_gen/dsl/ast/nodes/control_flow.py`
- `test`：`test/dsl/ast/nodes/test_control_flow.py`

## 依赖

- `spec/dsl/ast/nodes/basic.md`：提供 `StatementAST`、`ValueAST`、`BlockAST` 与 `BoolValueAST`。
- `spec/dsl/ast/nodes/symbol.md`：提供 `SymbolDimAST` 与 `ConstValueAST`。
- `spec/dsl/ast/nodes/attr.md`：提供 `SourceLocation`。
- `kernel_gen.dialect.symbol`：提供 `SymbolForOp`、`SymbolValueType` 与 `SymbolIterType`。
- `xdsl.dialects.scf`：提供 `IfAST` 发射的 `scf.if`。

## 额外补充

- `ForAST` 的 `start`、`end`、`step` 必须发射为 `!symbol.int` SSA value；`step` 省略时等价于 `ConstValueAST(1)`。
- `ForAST` 的 `step` 不能为 0；非法边界必须通过 `KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, ...)` 稳定失败。
- `ForAST` 的 body block 必须使用 loop iter argument 绑定 `var.name`，body 发射完成后不得保留临时 `name_hint`。
- `IfAST` 的 condition 必须发射为 `i1` SSA value；非 `i1` 条件必须稳定失败。
- `IfAST.false_body` 为 `None` 时不生成 else region；当前 DSL 不要求 Python `else` 必须存在。

## API详细说明

### `class ForAST(var: SymbolDimAST, start: ValueAST, end: ValueAST, body: BlockAST, step: ValueAST | None = None, location: SourceLocation | None = None)`

- api：`class ForAST(var: SymbolDimAST, start: ValueAST, end: ValueAST, body: BlockAST, step: ValueAST | None = None, location: SourceLocation | None = None)`
- 参数：
  - `var`：循环变量；类型 `SymbolDimAST`；无默认值；传入非 `SymbolDimAST` 时构造阶段归一为 `SymbolDimAST`。
  - `start`：起始边界；类型 `ValueAST`；无默认值；传入 Python 常量时归一为 `ConstValueAST`。
  - `end`：结束边界；类型 `ValueAST`；无默认值；传入 Python 常量时归一为 `ConstValueAST`。
  - `body`：循环体；类型 `BlockAST`；无默认值。
  - `step`：步长；类型 `ValueAST | None`；默认值 `None`；`None` 表示 1。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`。
- 返回值：`ForAST`。
- 使用示例：

  ```python
  from kernel_gen.dsl.ast.nodes import BlockAST, ConstValueAST, ForAST, SymbolDimAST

  loop = ForAST(SymbolDimAST("i"), ConstValueAST(0), ConstValueAST(4), BlockAST([]))
  ```
- 功能说明：表示 DSL `for` 循环，发射时生成 `symbol.for`。
- 注意事项：`ForAST` 是控制流节点，不属于 `symbol.py` 的公开 API；调用方不得从 `kernel_gen.dsl.ast.nodes.symbol` 导入该类型。

### `class IfAST(condition: ValueAST, true_body: BlockAST, false_body: BlockAST | None = None, location: SourceLocation | None = None)`

- api：`class IfAST(condition: ValueAST, true_body: BlockAST, false_body: BlockAST | None = None, location: SourceLocation | None = None)`
- 参数：
  - `condition`：条件值；类型 `ValueAST`；无默认值；传入 Python 常量时归一为 `BoolValueAST`。
  - `true_body`：then 分支；类型 `BlockAST`；无默认值。
  - `false_body`：else 分支；类型 `BlockAST | None`；默认值 `None`。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`。
- 返回值：`IfAST`。
- 使用示例：

  ```python
  from kernel_gen.dsl.ast.nodes import BlockAST, BoolValueAST, IfAST

  branch = IfAST(BoolValueAST(True), BlockAST([]))
  ```
- 功能说明：表示 DSL 条件分支，发射时生成 `scf.if`。
- 注意事项：`IfAST` 是控制流节点，不属于 `basic.py` 的公开 API；调用方不得从 `kernel_gen.dsl.ast.nodes.basic` 导入该类型。

## 测试

- 测试文件：`test/dsl/ast/nodes/test_control_flow.py`
- 执行命令：`pytest -q test/dsl/ast/nodes/test_control_flow.py`

### 测试目标

- 控制流节点模块归属、包根公开导出、构造归一与 legacy 归属退场。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-AST-NODES-CONTROL-FLOW-001 | 公开入口 | control-flow nodes live in control_flow module | 可导入 `kernel_gen.dsl.ast.nodes.control_flow`。 | 运行 `test_control_flow_nodes_live_in_control_flow_module`。 | `ForAST` / `IfAST` 在 control_flow.py，basic.py / symbol.py 不再定义对应控制流节点。 | `test_control_flow_nodes_live_in_control_flow_module` |
| TC-DSL-AST-NODES-CONTROL-FLOW-002 | 构造归一 | for ast normalizes python bounds and default step | 构造 `ForAST`。 | 运行 `test_for_ast_normalizes_bounds_and_default_step`。 | 循环变量和常量边界归一为公开 AST 节点。 | `test_for_ast_normalizes_bounds_and_default_step` |
| TC-DSL-AST-NODES-CONTROL-FLOW-003 | 构造归一 | if ast normalizes python bool condition | 构造 `IfAST`。 | 运行 `test_if_ast_normalizes_python_bool_condition`。 | Python bool 条件归一为 `BoolValueAST`。 | `test_if_ast_normalizes_python_bool_condition` |
