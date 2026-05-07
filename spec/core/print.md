# print.md

## 功能简介

定义 `kernel_gen.core.print` 的公开 alias IR 打印入口。该入口用于诊断 dump 和合同验收，把完整 xDSL operation 打印为带顶层 alias 定义的 MLIR-like 文本；普通 `str(op)`、xDSL 原生 `Printer.print_attribute(...)` 和比较工具默认文本不因本 spec 改变。

## API 列表

- `print_operation_with_aliases(operation: Operation | ModuleOp) -> str`

## 文档信息

- `spec`：`spec/core/print.md`
- `功能实现`：`kernel_gen/core/print.py`
- `test`：`test/core/test_print.py`
- `expectation`：`expectation/core/print.py`，仅作为本计划授权合同验收资产。

## 依赖

- `xdsl.ir.Operation`：合法输入的基础 operation 类型。
- `xdsl.dialects.builtin.ModuleOp`：常见完整 module 输入类型。
- `kernel_gen.dialect.symbol.SymbolExprAttr`：`#symbol.expr<...>` alias 来源。
- `kernel_gen.dialect.symbol.SymbolIterAttr`：`#symbol.iter<...>` alias 来源。
- `kernel_gen.core.context.build_default_context()`：测试与验收使用该公开入口验证 alias IR 可重新解析。

## API详细说明

### `print_operation_with_aliases(operation: Operation | ModuleOp) -> str`

- api：`print_operation_with_aliases(operation: Operation | ModuleOp) -> str`
- 参数：
  - `operation`：待打印的 xDSL operation；类型必须是 `xdsl.ir.Operation` 或 `xdsl.dialects.builtin.ModuleOp`；调用方传入 `None`、`str`、数值或其它非 operation 对象时必须失败。
- 返回值：
  - `str`：带顶层 alias 定义的 IR 文本；返回文本以换行结尾。
- 功能说明：
  - 收集输入 operation 树中的 `#symbol.expr<...>` 与 `#symbol.iter<...>`。
  - 在 IR 顶部声明 alias，并在正文中引用 alias。
  - alias 状态只属于本次调用，不写入全局状态，也不污染 raw attr/type 打印。
- 使用示例：

  ```python
  from xdsl.parser import Parser

  from kernel_gen.core.context import build_default_context
  from kernel_gen.core.print import print_operation_with_aliases

  module = Parser(
      build_default_context(),
      "builtin.module { func.func @main(%n: !symbol.int<#symbol.expr<N>>) { func.return } }",
  ).parse_module()

  text = print_operation_with_aliases(module)
  assert "#S_N = #symbol.expr<N>" in text
  assert "!symbol.int<#S_N>" in text
  ```
- 注意事项：
  - 非 operation 输入必须抛出 `TypeError("operation must be xdsl Operation")`。
  - 常量表达式 `#symbol.expr<0>`、`#symbol.expr<7>`、`#symbol.expr<-3>` 分别声明为 `#C0`、`#C7`、`#C_NEG3`。
  - 单符号表达式 `#symbol.expr<N>` 声明为 `#S_N`。
  - unknown 表达式 `#symbol.expr<?>` 声明为 `#S_Q`。
  - 复杂表达式按首次出现顺序声明为 `#S1`、`#S2`。
  - `#symbol.iter<start = ..., end = ..., step = ...>` 按首次出现顺序声明为 `#It1`、`#It2`，其 start/end/step 必须引用本次输出中已声明的 symbol expr alias。
  - 同一表达式或同一 iter attr 多次出现时只声明一次 alias。
  - 声明顺序固定为常量、单符号、unknown、复杂表达式、iter；各组内部保持首次出现顺序。
  - 正文不得残留可 alias 化的长形态 `#symbol.expr<...>` 或 `#symbol.iter<...>`。
  - 本接口不解析 IR、不运行 pass、不修改输入 operation，不新增 `dump_ir(...)`、`format_ir(...)` 或其它公开入口。

## 测试

- 测试文件：
  - `test/core/test_print.py`
- 执行命令：
  - `pytest -q test/core/test_print.py`

### 测试目标

- 验证 `print_operation_with_aliases(...)` 的公开导入、alias 规则、非法输入错误、round-trip 可解析和 raw attr/type 不污染。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-CORE-PRINT-001 | 公开入口 | public import | 准备 `kernel_gen.core.print` 模块。 | 导入 `print_operation_with_aliases`。 | 公开函数可导入，且未要求从包根转发。 | `test_print_operation_with_aliases_public_import` |
| TC-CORE-PRINT-002 | 解析/打印 | expr alias and round trip | 准备包含常量、单符号和复杂 symbol expr 的完整 module。 | 调用 `print_operation_with_aliases(module)` 并重新解析输出。 | 输出含 `#C*`、`#S_*`、`#S1`，正文不残留长 `#symbol.expr<...>`。 | `test_print_operation_with_aliases_aliases_symbol_exprs_and_round_trips` |
| TC-CORE-PRINT-003 | 解析/打印 | iter alias | 准备含 `symbol.for` iter attr 的完整 module。 | 调用 `print_operation_with_aliases(module)`。 | 输出含 `#It1`，正文不残留长 `#symbol.iter<...>`。 | `test_print_operation_with_aliases_aliases_symbol_iter` |
| TC-CORE-PRINT-004 | 内存/DMA | memory alias | 准备含 `!nn.memory` shape/stride symbol expr 的完整 module。 | 调用 `print_operation_with_aliases(module)`。 | memory shape/stride 引用 expr alias，正文不展开长 expr。 | `test_print_operation_with_aliases_aliases_memory_shape_and_stride` |
| TC-CORE-PRINT-005 | 边界/异常 | invalid input | 传入非 xDSL operation 对象。 | 调用 `print_operation_with_aliases(...)`。 | 抛出 `TypeError("operation must be xdsl Operation")`。 | `test_print_operation_with_aliases_rejects_non_operation` |
| TC-CORE-PRINT-006 | 解析/打印 | raw attr no pollution | 准备 `SymbolValueType.from_expr("N")`。 | 先调用 alias printer，再使用 xDSL `Printer.print_attribute(...)` 打印 raw type。 | raw type 仍输出 `!symbol.int<#symbol.expr<N>>`，不出现未定义 alias。 | `test_print_operation_with_aliases_does_not_pollute_raw_attribute_printing` |
