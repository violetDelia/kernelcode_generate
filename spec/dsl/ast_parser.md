# ast_parser.md

## 功能简介

- 提供解析入口，将 Python 函数解析为 `FunctionAST`。
- 生成 `Diagnostic` 以承载解析阶段的错误定位信息。

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/dsl/ast_parser.md`](../../spec/dsl/ast_parser.md)
- `功能实现`：[`kernel_gen/dsl/ast/parser.py`](../../kernel_gen/dsl/ast/parser.py)
- `test`：[`test/dsl/test_ast_parser.py`](../../test/dsl/test_ast_parser.py)

## 依赖

- Python `ast`/`inspect`：用于获取源码并解析语法树。
- [`spec/dsl/ast_nodes.md`](../../spec/dsl/ast_nodes.md)：AST 节点类型与字段语义。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：`MemorySpace` 枚举语义。
- [`spec/include/api/Arch.md`](../../spec/include/api/Arch.md)：`BarrierScope` 枚举名与 arch helper 入口形态。
- [`spec/dsl/ast.md`](../../spec/dsl/ast.md)：解析入口与诊断口径的完整合同。

## 术语

- `Parser`：解析入口 `parse_function(...)`。
- `Diagnostic`：解析阶段产生的错误与定位信息。

## 目标

- 将受限 Python 函数解析为 `FunctionAST`。
- 生成稳定的诊断信息，供下游定位错误。

## 限制与边界

- 仅覆盖受限语法子集，不负责 MLIR 生成或后端行为。
- 解析入口只做语法与基本形态校验；数值归一化与后续语义由下游处理。
- 解析规则与诊断口径以 `spec/dsl/ast.md` 为准。

## 公开接口

### `parse_function(fn)`

功能说明：

- 解析 Python 函数并构建 `FunctionAST`。
- 在解析阶段生成 `Diagnostic` 以承载错误定位信息。

参数说明：

- `fn` (`callable`)：受限 Python 函数。

使用示例：

```python
def add(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]"):
    return x + y

func_ast = parse_function(add)
```

注意事项：

- 必须能获取函数源码；否则应抛出解析错误。
- 注解解析规则、helper 入口与诊断口径以 `spec/dsl/ast.md` 为准。
- 解析结果中的节点类型来自 `kernel_gen/dsl/ast/nodes.py`，并通过 `kernel_gen.dsl.ast` 对外导出。

返回与限制：

- 返回 `FunctionAST`。
- 解析失败时应抛出包含位置信息的错误或返回带 `Diagnostic` 的结果（以测试为准）。

## 测试

- 测试文件：[`test/dsl/test_ast_parser.py`](../../test/dsl/test_ast_parser.py)
- 执行命令：`pytest -q test/dsl/test_ast_parser.py`
- 测试目标：
  - 覆盖 `parse_function(...)` 的解析入口与诊断输出。
  - 覆盖 parse 结果能够构造 `FunctionAST` 并保留源位置信息。
  - 覆盖 helper 解析的基本形态校验与错误路径。
- 功能与用例清单：
  - AST-P-001：解析函数生成 `FunctionAST`。（`test_ast_parser_builds_function_ast`）
  - AST-P-002：解析失败时返回带位置信息的诊断。（`test_ast_parser_reports_diagnostics`）
  - AST-P-003：解析 helper 的非法参数路径。（`test_ast_parser_rejects_invalid_helper_arity`）
