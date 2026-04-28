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
- `test`：
  - [`test/dsl/ast/test_parser.py`](../../../test/dsl/ast/test_parser.py)
  - [`test/dsl/ast/test_package.py`](../../../test/dsl/ast/test_package.py)

## 依赖

- Python `ast`/`inspect`：用于获取源码并解析语法树。
- [`spec/dsl/ast/nodes.md`](../../../spec/dsl/ast/nodes.md)：AST 节点类型与字段语义。
- [`spec/symbol_variable/memory.md`](../../../spec/symbol_variable/memory.md)：`MemorySpace` 枚举语义。
- [`spec/operation/dma.md`](../../../spec/operation/dma.md)：`fill` 等 dma helper 的公开入口与参数边界。
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
- `parse_function_with_env(...)` 只属于 parser 模块级公开入口；`kernel_gen.dsl.ast` 包根 facade、`kernel_gen.dsl.mlir_gen` 包根 facade 与工具层公开入口都不得把它当作并列主入口重新导出。
- DSL helper 识别规则以“显式 import 绑定到真实公开 helper 对象 + 调用形态”作为真源；不得依赖 helper 的 Python `inspect.signature`、参数注解、默认值或文件内私有包装函数来决定是否把某个调用当作 DSL helper。
- 对 `kernel_gen.operation.dma.fill`，当前公开解析入口只接受显式 import 绑定得到的 helper 调用；未导入的裸 `fill(...)` 与 `kernel_gen.operation.dma.fill(...)` 这类链式属性访问都不属于当前 AST 公开入口。
- 当 helper 为 `fill(...)` 时，parser 对字符串字面量只接受 `"inf"` 与 `"-inf"`；其他字符串必须在解析阶段直接拒绝，不下沉到后续 lowering 再猜测含义。
- 当 `build_func_op(...)` / `mlir_gen(...)` 提供 `runtime_args` 时，参数注解中的裸 `Memory` 与裸 `SymbolDim` 允许作为占位注解被 parser 接受；parser 不得把这两类注解直接收敛为 `Unsupported annotation`。实际 `func.func` 输入签名仍由下游 builder 基于 `runtime_args` 决定，而不是由这类占位注解直接决定。

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
- 为 parser 模块内需要显式环境控制的调用方提供稳定入口。

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
- `build_func_op(...)` / `mlir_gen(...)` 的包根公开合同不再透出 `globals` / `builtins`；若上层实现仍需要显式环境控制，只能在 parser 或 mlir_gen 目录内消费本入口，不得把它转成新的工具层公开接口。
- 文件内其他 `_...` helper 属于实现细节，不构成公开 API，也不得被跨文件实现或测试直连。
- dma/nn/arch helper 的识别规则以 import 绑定关系与 parser 自身白名单为准；不得通过改 helper 函数签名、额外包装 callable 或伪造同名对象来影响解析结果。

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
- 对 `fill(...)` 这类 dma helper，当前稳定入口是“显式 import 绑定到 `kernel_gen.operation.dma.fill` 的真实模块导出对象后再调用”；helper 的 Python 签名不是解析判定依据。

返回与限制：

- 返回 `FunctionAST`。
- 解析失败时应抛出包含位置信息的错误或返回带 `Diagnostic` 的结果（以测试为准）。

## 测试

- 测试文件：[`test/dsl/ast/test_parser.py`](../../../test/dsl/ast/test_parser.py)
- 相关 helper 绑定测试：[`test/dsl/ast/test_package.py`](../../../test/dsl/ast/test_package.py)
- 执行命令：`pytest -q test/dsl/ast/test_parser.py test/dsl/ast/test_package.py`
- 测试目标：
  - 覆盖 `parse_function(...)` 的解析入口与诊断输出。
  - 覆盖 parse 结果能够构造 `FunctionAST` 并保留源位置信息。
  - 覆盖 helper 解析的基本形态校验与错误路径。
  - 覆盖 `fill` 等 dma helper 的 import 绑定规则、字符串字面量边界与“解析不依赖 helper 签名”的合同。
- 功能与用例清单：
  - AST-P-001：解析基础赋值函数并生成 `FunctionAST`。（`test_parse_function_basic_assignment`）
  - AST-P-002：解析 `for range(...)` 语法并生成 `ForAST`。（`test_parse_function_for_loop`）
  - AST-P-003：解析 helper 调用入口并生成相应 AST。（`test_parse_function_helper_call`）
  - AST-P-004：显式环境入口允许通过 `runtime_table` 推断缺失注解。（`test_parse_function_with_env_infers_runtime_annotation`）
  - AST-P-005：缺失注解时返回带位置信息的 `AstParseError`。（`test_parse_function_reports_diagnostics`）
  - AST-P-006：解析 helper 非法参数形态并报稳定错误。（`test_parse_function_rejects_invalid_helper_arity`）
  - AST-P-007：`for range(..., step=0)` 在解析阶段直接报错。（`test_parse_function_step_zero_rejected`）
  - AST-P-008：facade 不导出 parser 私有 helper。（`test_ast_facade_does_not_export_parser_private_helpers`）
  - AST-P-009：显式 import 绑定到 `kernel_gen.operation.dma.fill` 的 helper 调用可被识别，且识别不依赖 helper Python 签名。（`test_parse_function_accepts_import_bound_fill_helper`、`test_parse_function_accepts_import_bound_fill_helper_without_signature_coupling`）
  - AST-P-010：`fill` 的字符串字面量只允许 `"inf"` 与 `"-inf"`，其他字符串在解析阶段直接拒绝。（`test_parse_function_rejects_invalid_fill_string_literal`）
  - AST-P-011：未导入的裸 `fill(...)` 与 `kernel_gen.operation.dma.fill(...)` 链式属性访问不属于当前 AST 公开入口。（`test_parse_function_rejects_unimported_dma_helpers`、`test_parse_function_rejects_fill_helper_call_via_attribute_chain`）
  - AST-P-012：当 `build_func_op(...)` / `mlir_gen(...)` 传入 `runtime_args` 时，裸 `Memory` / `SymbolDim` 参数注解必须作为占位注解被 parser 接受，不得报 `Unsupported annotation`。（下游待补测试映射：`test_parse_function_accepts_runtime_driven_memory_placeholder_annotation`、`test_parse_function_accepts_runtime_driven_symbol_placeholder_annotation`）
