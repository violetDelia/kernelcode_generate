# mlir_gen_compare.md

## 功能简介

- `mlir_gen_compare` 用来比较 `mlir_gen(...)` 产出的 `builtin.module` 与预期 `.mlir` 文件是否一致。
- 比较口径默认固定为“两边都先解析，再统一打印后比较字符串”。
- 若实际或预期文本包含 `!nn.memory<...>` 中的 `//` 符号表达式，则走工具内文本兜底：保留字符串内容，移除字符串外空白后比较。原因是 xdsl/MLIR 词法层把 `//` 识别为注释，不能可靠 parse 这类由 `SymbolDim.__floordiv__` 生成的 memory 类型文本。
- expected 文件头部或普通行注释中的 `//` 不属于 memory 表达式，不得触发文本兜底比较。
- 只返回 `bool`；不执行 pass、不做 lowering、不输出 diff。
- 工具层只依赖公开 `mlir_gen(fn, *runtime_args)`；若当前文件保留延迟加载或文本归一化 helper，它们都不是公开 API。
- expected 文本与实际 module 的解析 Context 必须复用 `kernel_gen.core.context.build_default_context()`；不得在本工具内维护第二套 dialect 注册列表。默认 Context 必须覆盖 `scf.if` 这类 mlir_gen 公开可能产出的控制流 op。

## API 列表

- `mlir_gen_compare(fn: Callable[..., DslFunctionReturn], runtime_args: tuple[DslRuntimeArg, ...] | list[DslRuntimeArg] | None, mlir_file: str) -> bool`
- `mlir_gen_compare_text(fn: Callable[..., DslFunctionReturn], runtime_args: tuple[DslRuntimeArg, ...] | list[DslRuntimeArg] | None, mlir_text: str) -> bool`
- `compare_mlir_file(fn: Callable[..., DslFunctionReturn], runtime_args: tuple[DslRuntimeArg, ...] | list[DslRuntimeArg] | None, mlir_file: str) -> bool`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/tools/mlir_gen_compare.md`](../../spec/tools/mlir_gen_compare.md)
- `功能实现`：[`kernel_gen/tools/mlir_gen_compare.py`](../../kernel_gen/tools/mlir_gen_compare.py)
- `test`：[`test/tools/test_mlir_gen_compare.py`](../../test/tools/test_mlir_gen_compare.py)

## 依赖

- `mlir_gen(...)`：[`spec/dsl/ast/mlir_gen.md`](../../spec/dsl/ast/mlir_gen.md)

## 额外补充

- `_mlir_gen_compare_expected_text(...)`、`_build_compare_context(...)` 与 `_normalize_module_text(...)` 只允许作为当前文件内 helper 存在；实现、工具与测试不得跨文件把这些 helper 当成公开 API。
- expected 文本与实际 module 的解析 Context 必须复用 `kernel_gen.core.context.build_default_context()`；不得在本工具内维护第二套 dialect 注册列表。

## API详细说明

### `mlir_gen_compare(fn: Callable[..., DslFunctionReturn], runtime_args: tuple[DslRuntimeArg, ...] | list[DslRuntimeArg] | None, mlir_file: str) -> bool`

- api：`mlir_gen_compare(fn: Callable[..., DslFunctionReturn], runtime_args: tuple[DslRuntimeArg, ...] | list[DslRuntimeArg] | None, mlir_file: str) -> bool`
- 参数：
  - `fn`：可调用对象，作为 DSL 构建、执行或包装入口的主体；类型 `Callable[..., DslFunctionReturn]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `runtime_args`：运行期实参序列，与 DSL 函数形参按顺序对应；类型 `tuple[DslRuntimeArg, ...] | list[DslRuntimeArg] | None`；无默认值，调用方必须显式提供；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
  - `mlir_file`：`mlir_file` 输入值，参与 `mlir_gen_compare` 的公开处理流程；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`bool`，表示判断结果。
- 使用示例：

  ```python
  from kernel_gen.tools.mlir_gen_compare import mlir_gen_compare

  ok = mlir_gen_compare(
      fn=add,
      runtime_args=[lhs, rhs],
      mlir_file="expected/add.mlir",
  )
  assert ok is True
  ```
- 功能说明：用 `mlir_gen(...)` 生成实际 module，读取并解析 `mlir_file`，对两边执行同一套归一化比较。
- 注意事项：
  - `mlir_gen(...)` 返回值不是 `builtin.module` 时返回 `False`。
  - expected 文件读取失败或非 UTF-8 时返回 `False`。
  - expected 文本解析失败或解析结果不是 `builtin.module` 时返回 `False`。
  - expected 文本含 `!nn.memory<...>` 尖括号正文内的 `//` 表达式时，不要求 parser 成功，改按字符串外空白归一化文本比较；普通注释中的 `//` 仍走 parser + printer 归一化。
  - 归一化失败或归一化文本不一致时返回 `False`。
  - `mlir_gen(...)` 自身抛错时不重新包裹，直接向上传播。
  - 调用方不得依赖实现内部状态。

### `mlir_gen_compare_text(fn: Callable[..., DslFunctionReturn], runtime_args: tuple[DslRuntimeArg, ...] | list[DslRuntimeArg] | None, mlir_text: str) -> bool`

- api：`mlir_gen_compare_text(fn: Callable[..., DslFunctionReturn], runtime_args: tuple[DslRuntimeArg, ...] | list[DslRuntimeArg] | None, mlir_text: str) -> bool`
- 参数：
  - `fn`：可调用对象，作为 DSL 构建、执行或包装入口的主体；类型 `Callable[..., DslFunctionReturn]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `runtime_args`：运行期实参序列，与 DSL 函数形参按顺序对应；类型 `tuple[DslRuntimeArg, ...] | list[DslRuntimeArg] | None`；无默认值，调用方必须显式提供；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
  - `mlir_text`：`mlir_text` 输入值，参与 `mlir_gen_compare_text` 的公开处理流程；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`bool`，表示判断结果。
- 使用示例：

  ```python
  result = mlir_gen_compare_text(fn=fn, runtime_args=runtime_args, mlir_text=mlir_text)
  ```
- 功能说明：执行 `mlir_gen_compare_text`。
- 注意事项：
  - 语义与 `mlir_gen_compare(...)` 一致，区别只在 expected 来源是内存字符串，不是磁盘文件。
  - expected 文本解析失败、归一化失败或文本不一致时返回 `False`。
  - expected 文本含 `!nn.memory<...>` 尖括号正文内的 `//` 表达式时，按字符串外空白归一化文本比较。
  - `mlir_gen(...)` 自身抛错时不重新包裹，直接向上传播。
  - 调用方不得依赖实现内部状态。

### `compare_mlir_file(fn: Callable[..., DslFunctionReturn], runtime_args: tuple[DslRuntimeArg, ...] | list[DslRuntimeArg] | None, mlir_file: str) -> bool`

- api：`compare_mlir_file(fn: Callable[..., DslFunctionReturn], runtime_args: tuple[DslRuntimeArg, ...] | list[DslRuntimeArg] | None, mlir_file: str) -> bool`
- 参数：
  - `fn`：可调用对象，作为 DSL 构建、执行或包装入口的主体；类型 `Callable[..., DslFunctionReturn]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `runtime_args`：运行期实参序列，与 DSL 函数形参按顺序对应；类型 `tuple[DslRuntimeArg, ...] | list[DslRuntimeArg] | None`；无默认值，调用方必须显式提供；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
  - `mlir_file`：`mlir_file` 输入值，参与 `compare_mlir_file` 的公开处理流程；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`bool`，表示判断结果。
- 使用示例：

  ```python
  result = compare_mlir_file(fn=fn, runtime_args=runtime_args, mlir_file=mlir_file)
  ```
- 功能说明：执行 `compare_mlir_file`。
- 注意事项：
  - 这是旧兼容入口，行为等价于 `mlir_gen_compare(...)`。
  - 文件读取、解析、归一化、文本比较和 `mlir_gen(...)` 抛错语义必须与 `mlir_gen_compare(...)` 保持一致。
  - 调用方不得依赖实现内部状态。

## 测试

- 测试文件：`test/tools/test_mlir_gen_compare.py`
- 执行命令：`pytest -q test/tools/test_mlir_gen_compare.py`

### 测试目标

- 验证 `tools/mlir_gen_compare` 的公开 API、边界与错误语义。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-TOOLS-MLIR-GEN-COMPARE-001 | 解析/打印 | build default context parses scf if | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_build_default_context_parses_scf_if`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_build_default_context_parses_scf_if` |
| TC-TOOLS-MLIR-GEN-COMPARE-002 | 公开入口 | MLIR gen compare true | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_mlir_gen_compare_true`。 | 公开入口在“MLIR gen compare true”场景下可导入、构造、注册或按名称发现。 | `test_mlir_gen_compare_true` |
| TC-TOOLS-MLIR-GEN-COMPARE-003 | 公开入口 | compare MLIR file alias true | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_compare_mlir_file_alias_true`。 | 公开入口在“compare MLIR file alias true”场景下可导入、构造、注册或按名称发现。 | `test_compare_mlir_file_alias_true` |
| TC-TOOLS-MLIR-GEN-COMPARE-004 | 边界/异常 | MLIR gen compare returns false on mismatch | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_mlir_gen_compare_returns_false_on_mismatch`。 | “MLIR gen compare returns false on mismatch”场景按公开错误语义失败或被拒绝。 | `test_mlir_gen_compare_returns_false_on_mismatch` |
| TC-TOOLS-MLIR-GEN-COMPARE-005 | 边界/异常 | MLIR gen compare returns false on invalid text | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_mlir_gen_compare_returns_false_on_invalid_text`。 | “MLIR gen compare returns false on invalid text”场景按公开错误语义失败或被拒绝。 | `test_mlir_gen_compare_returns_false_on_invalid_text` |
| TC-TOOLS-MLIR-GEN-COMPARE-006 | 解析/打印 | MLIR gen compare returns false on non utf8 text | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_mlir_gen_compare_returns_false_on_non_utf8_text`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_mlir_gen_compare_returns_false_on_non_utf8_text` |
| TC-TOOLS-MLIR-GEN-COMPARE-007 | 公开入口 | MLIR gen compare true with arith | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_mlir_gen_compare_true_with_arith`。 | 公开入口在“MLIR gen compare true with arith”场景下可导入、构造、注册或按名称发现。 | `test_mlir_gen_compare_true_with_arith` |
| TC-TOOLS-MLIR-GEN-COMPARE-008 | 边界/异常 | MLIR gen compare returns false on normalize parse error | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_mlir_gen_compare_returns_false_on_normalize_parse_error`。 | “MLIR gen compare returns false on normalize parse error”场景按公开错误语义失败或被拒绝。 | `test_mlir_gen_compare_returns_false_on_normalize_parse_error` |
| TC-TOOLS-MLIR-GEN-COMPARE-009 | 解析/打印 | default context loads required dialects | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_default_context_loads_required_dialects`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_default_context_loads_required_dialects` |
| TC-TOOLS-MLIR-GEN-COMPARE-010 | 公开入口 | MLIR gen compare returns false when actual not module | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_mlir_gen_compare_returns_false_when_actual_not_module`。 | 公开入口在“MLIR gen compare returns false when actual not module”场景下可导入、构造、注册或按名称发现。 | `test_mlir_gen_compare_returns_false_when_actual_not_module` |
| TC-TOOLS-MLIR-GEN-COMPARE-011 | 执行结果 | MLIR gen compare does not repair legacy DMA view result dtype | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_mlir_gen_compare_does_not_repair_legacy_dma_view_result_dtype`。 | 命令返回码、输出、执行结果或状态变更体现“MLIR gen compare does not repair legacy DMA view result dtype”场景。 | `test_mlir_gen_compare_does_not_repair_legacy_dma_view_result_dtype` |
| TC-TOOLS-MLIR-GEN-COMPARE-012 | 内存/DMA | MLIR gen compare text handles memory floor div expr | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_mlir_gen_compare_text_handles_memory_floor_div_expr`。 | 内存类型、布局、搬运结果或 verifier 行为体现“MLIR gen compare text handles memory floor div expr”场景。 | `test_mlir_gen_compare_text_handles_memory_floor_div_expr` |
| TC-TOOLS-MLIR-GEN-COMPARE-013 | 边界/异常 | MLIR gen compare text rejects memory floor div mismatch | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_mlir_gen_compare_text_rejects_memory_floor_div_mismatch`。 | “MLIR gen compare text rejects memory floor div mismatch”场景按公开错误语义失败或被拒绝。 | `test_mlir_gen_compare_text_rejects_memory_floor_div_mismatch` |
| TC-TOOLS-MLIR-GEN-COMPARE-014 | 解析/打印 | MLIR gen compare text true | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_mlir_gen_compare_text_true`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_mlir_gen_compare_text_true` |
| TC-TOOLS-MLIR-GEN-COMPARE-015 | 内存/DMA | MLIR gen compare text ignores line comment slashes for memory types | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_mlir_gen_compare_text_ignores_line_comment_slashes_for_memory_types`。 | 内存类型、布局、搬运结果或 verifier 行为体现“MLIR gen compare text ignores line comment slashes for memory types”场景。 | `test_mlir_gen_compare_text_ignores_line_comment_slashes_for_memory_types` |
| TC-TOOLS-MLIR-GEN-COMPARE-016 | 边界/异常 | MLIR gen compare text returns false on invalid text | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_mlir_gen_compare_text_returns_false_on_invalid_text`。 | “MLIR gen compare text returns false on invalid text”场景按公开错误语义失败或被拒绝。 | `test_mlir_gen_compare_text_returns_false_on_invalid_text` |
