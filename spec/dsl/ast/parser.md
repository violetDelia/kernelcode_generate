# parser.md

## 功能简介

- 提供解析入口，将 Python 函数解析为 `FunctionAST`。
- 生成 `Diagnostic` 以承载解析阶段的错误定位信息。

## API 列表

- `class AstParseError(message: str, diagnostics: list[Diagnostic])`
- `AstParseError.__init__(message: str, diagnostics: list[Diagnostic]) -> None`
- `AstParseError.__str__() -> str`
- `parse_function_with_env(fn: object, globals_table: dict[str, object] | None = None, builtins_table: dict[str, object] | None = None, runtime_table: dict[str, object] | None = None, config: dict[str, object] | None = None) -> FunctionAST`
- `parse_function(fn: object) -> FunctionAST`

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/dsl/ast/parser.md`](../../../spec/dsl/ast/parser.md)
- `功能实现`：[`kernel_gen/dsl/ast/parser.py`](../../../kernel_gen/dsl/ast/parser.py)
- `test`：[`test/dsl/ast/test_parser.py`](../../../test/dsl/ast/test_parser.py)

## 依赖

- Python `ast`/`inspect`：用于获取源码并解析语法树。
- [`spec/dsl/ast/nodes.md`](../../../spec/dsl/ast/nodes.md)：AST 节点类型与字段语义。
- [`spec/symbol_variable/memory.md`](../../../spec/symbol_variable/memory.md)：`MemorySpace` 枚举语义。
- [`spec/include/api/Arch.md`](../../../spec/include/api/Arch.md)：`BarrierScope` 枚举名与 arch helper 入口形态。
- [`spec/dsl/ast/__init__.md`](../../../spec/dsl/ast/__init__.md)：解析入口与诊断口径的完整合同。

## 术语

- `Parser`：解析入口 `parse_function(...)`。
- `Diagnostic`：解析阶段产生的错误与定位信息。

## 目标

- 将受限 Python 函数解析为 `FunctionAST`。
- 生成稳定的诊断信息，供下游定位错误。

## 限制与边界

- 仅覆盖受限语法子集，不负责 MLIR 生成或后端行为。
- 解析入口只做语法与基本形态校验；数值归一化与后续语义由下游处理。
- 解析规则与诊断口径以 `spec/dsl/ast/__init__.md` 为准。

## 公开接口

### `AstParseError(message: str, diagnostics: list[Diagnostic])`

功能说明：

- AST 解析阶段统一错误类型。
- 通过 `diagnostics` 暴露稳定诊断集合。

参数说明：

- `message` (`str`)：错误主消息。
- `diagnostics` (`list[Diagnostic]`)：诊断列表。

使用示例：

```python
raise AstParseError("Missing annotation", [Diagnostic("Missing annotation", None)])
```

注意事项：

- 对外错误类型固定为 `AstParseError`；调用方不应依赖 parser 文件内私有异常。

返回与限制：

- 抛出异常终止解析。

### `parse_function_with_env(fn: object, globals_table: dict[str, object] | None = None, builtins_table: dict[str, object] | None = None, runtime_table: dict[str, object] | None = None, config: dict[str, object] | None = None)`

功能说明：

- 在显式 `globals` / `builtins` / `runtime` 环境下解析 Python 函数。
- 为 `mlir_gen`、集成 builder 与需要注解推断的调用方提供稳定公共入口。

参数说明：

- `fn` (`object`)：待解析 Python 函数对象。
- `globals_table` (`dict[str, object] | None`)：显式全局名字表。
- `builtins_table` (`dict[str, object] | None`)：显式 builtins 名字表。
- `runtime_table` (`dict[str, object] | None`)：运行时实参推断表。
- `config` (`dict[str, object] | None`)：解析配置。

使用示例：

```python
func_ast = parse_function_with_env(
    fn,
    globals_table={},
    builtins_table={},
    runtime_table=None,
    config=None,
)
```

注意事项：

- `runtime_table` 仅用于补充缺失注解推断与局部解析环境，不改变 AST 节点语义。
- `config` 的公开键由实现与集成测试约束；当前已使用的键包括 `reject_external_values` 与 `allow_python_callee_calls`。
- 文件内其他 `_...` helper 属于实现细节，不构成公开 API，也不得被跨文件实现或测试直连。

返回与限制：

- 返回 `FunctionAST`。
- 失败时抛 `AstParseError`。

### `parse_function(fn: object)`

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
- 注解解析规则、helper 入口与诊断口径以 `spec/dsl/ast/__init__.md` 为准。
- 解析结果中的节点类型来自 `kernel_gen/dsl/ast/nodes.py`，并通过 `kernel_gen.dsl.ast` 对外导出。
- `parse_function(...)` 是 facade 级最小解析入口；需要显式环境控制时应改用 `parse_function_with_env(...)`。

返回与限制：

- 返回 `FunctionAST`。
- 解析失败时应抛出包含位置信息的错误或返回带 `Diagnostic` 的结果（以测试为准）。

## 测试

- 测试文件：[`test/dsl/ast/test_parser.py`](../../../test/dsl/ast/test_parser.py)
- 执行命令：`pytest -q test/dsl/ast/test_parser.py`
- 测试目标：
  - 覆盖 `parse_function(...)` 的解析入口与诊断输出。
  - 覆盖 parse 结果能够构造 `FunctionAST` 并保留源位置信息。
  - 覆盖 helper 解析的基本形态校验与错误路径。
- 功能与用例清单：
  - AST-P-001：解析基础赋值函数并生成 `FunctionAST`。（`test_parse_function_basic_assignment`）
  - AST-P-002：解析 `for range(...)` 语法并生成 `ForAST`。（`test_parse_function_for_loop`）
  - AST-P-003：解析 helper 调用入口并生成相应 AST。（`test_parse_function_helper_call`）
  - AST-P-004：显式环境入口允许通过 `runtime_table` 推断缺失注解。（`test_parse_function_with_env_infers_runtime_annotation`）
  - AST-P-005：缺失注解时返回带位置信息的 `AstParseError`。（`test_parse_function_reports_diagnostics`）
  - AST-P-006：解析 helper 非法参数形态并报稳定错误。（`test_parse_function_rejects_invalid_helper_arity`）
  - AST-P-007：`for range(..., step=0)` 在解析阶段直接报错。（`test_parse_function_step_zero_rejected`）
  - AST-P-008：facade 不导出 parser 私有 helper。（`test_ast_facade_does_not_export_parser_private_helpers`）
