# execute_engine_api.md

## 功能简介

- 定义执行引擎 `P0` 的请求/结果/参数模型：`CompileRequest / ExecuteRequest / CompiledKernel / ExecuteResult`。
- 冻结字段、默认值与失败短语触发条件，使调用方无需理解实现细节也能稳定调用与比对结果。

## API 列表

- `class CompileRequest(source: str, target: str, function: str, entry_point: str = "kg_execute_entry", compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`
- `class ExecuteRequest(args: tuple[RuntimeInput, ...], entry_point: str | None = None, capture_function_output: bool = False, stream: None = None)`
- `class CompiledKernel(target: str, soname_path: str, function: str, entry_point: str, compile_stdout: str = "", compile_stderr: str = "")`
- `CompiledKernel.close() -> None`
- `CompiledKernel.execute(args: tuple[RuntimeInput, ...] | None = None, *, request: ExecuteRequest | None = None, entry_point: str | None = None, capture_function_output: bool = False, stream: None = None) -> ExecuteResult`
- `class ExecuteResult(ok: bool, status_code: int, failure_phrase: str | None, compile_stdout: str = "", compile_stderr: str = "", run_stdout: str = "", run_stderr: str = "", elapsed_ms: float = 0.0)`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/execute_engine/execute_engine_api.md`](spec/execute_engine/execute_engine_api.md)
- `功能实现`：[`kernel_gen/execute_engine/compiler.py`](kernel_gen/execute_engine/compiler.py)
- `test`：[`test/execute_engine/test_contract.py`](test/execute_engine/test_contract.py)

## 依赖

- 执行引擎总览合同：[`spec/execute_engine/execute_engine.md`](spec/execute_engine/execute_engine.md)
- `emit_c` 输出语义：[`spec/dsl/gen_kernel/emit.md`](spec/dsl/gen_kernel/emit.md)

## 术语

- `failure_phrase`：执行引擎对外固定失败短语集合。

## 目标

- 统一 `CompileRequest/ExecuteRequest/ExecuteResult` 字段与默认值。
- 明确 `args` 与函数形参顺序的一一对应规则。
- 锁定 7 个失败短语与触发条件。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- `P0` 仅支持 `target in {"cpu","npu_demo"}`；其他 target 必须失败并返回 `target_header_mismatch`。
- `P0` 不支持 `stream` 与输出回收；当 `ExecuteRequest.stream is not None` 或 `capture_function_output=True` 必须失败。
- `args` 必须与 `function` 形参顺序严格一致；不做自动重排或参数推断。
- 运行时参数仅允许 memory / int / float 三类输入；其他类型必须失败。
- 失败短语只允许取 7 个固定值（见 `ExecuteResult`）；禁止同义词扩散与 silent fallback。
## API详细说明

### `class CompileRequest(source: str, target: str, function: str, entry_point: str = "kg_execute_entry", compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`

- api：`class CompileRequest(source: str, target: str, function: str, entry_point: str = "kg_execute_entry", compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`
- 参数：
  - `source`：源对象、源缓冲区或源文本，提供当前操作读取的数据来源；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `function`：Python 函数、DSL 函数或函数级对象，作为构建或执行输入；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `entry_point`：`entry_point` 输入值，参与 `CompileRequest` 的公开处理流程；类型 `str`；默认值 `"kg_execute_entry"`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `compiler`：编译器命令或编译器对象，用于把生成源码编译为可执行产物；类型 `str | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `compiler_flags`：`compiler_flags` 输入值，参与 `CompileRequest` 的公开处理流程；类型 `tuple[str, ...]`；默认值 `("-std=c++17",)`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `link_flags`：`link_flags` 输入值，参与 `CompileRequest` 的公开处理流程；类型 `tuple[str, ...]`；默认值 `()`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`CompileRequest` 实例。
- 使用示例：

  ```python
  compile_request = CompileRequest(source=source, target=target, function=function, entry_point="kg_execute_entry", compiler=None, compiler_flags=compiler_flags, link_flags=link_flags)
  ```
- 功能说明：定义 `CompileRequest` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class ExecuteRequest(args: tuple[RuntimeInput, ...], entry_point: str | None = None, capture_function_output: bool = False, stream: None = None)`

- api：`class ExecuteRequest(args: tuple[RuntimeInput, ...], entry_point: str | None = None, capture_function_output: bool = False, stream: None = None)`
- 参数：
  - `args`：位置参数序列，按公开调用约定传递给目标函数或工具入口；类型 `tuple[RuntimeInput, ...]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `entry_point`：`entry_point` 输入值，参与 `ExecuteRequest` 的公开处理流程；类型 `str | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `capture_function_output`：函数对象或函数级 IR；类型 `bool`；默认值 `False`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `stream`：输入或输出流对象，用于读取源码、写入文本或传递诊断；类型 `None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ExecuteRequest` 实例。
- 使用示例：

  ```python
  import numpy as np
  import torch

  args = (
      torch.zeros((2, 3)),
      np.zeros((2, 3), dtype=np.float32),
  )
  execute_request = ExecuteRequest(args=args, entry_point=None, capture_function_output=False, stream=None)
  ```
- 功能说明：定义 `ExecuteRequest` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class CompiledKernel(target: str, soname_path: str, function: str, entry_point: str, compile_stdout: str = "", compile_stderr: str = "")`

- api：`class CompiledKernel(target: str, soname_path: str, function: str, entry_point: str, compile_stdout: str = "", compile_stderr: str = "")`
- 参数：
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `soname_path`：公开名称或符号名；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `function`：Python 函数、DSL 函数或函数级对象，作为构建或执行输入；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `entry_point`：`entry_point` 输入值，参与 `CompiledKernel` 的公开处理流程；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `compile_stdout`：`compile_stdout` 输入值，参与 `CompiledKernel` 的公开处理流程；类型 `str`；默认值 `""`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `compile_stderr`：`compile_stderr` 输入值，参与 `CompiledKernel` 的公开处理流程；类型 `str`；默认值 `""`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`CompiledKernel` 实例。
- 使用示例：

  ```python
  compiled_kernel = CompiledKernel(target=target, soname_path=soname_path, function=function, entry_point=entry_point, compile_stdout="", compile_stderr="")
  ```
- 功能说明：定义 `CompiledKernel` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `CompiledKernel.close() -> None`

- api：`CompiledKernel.close() -> None`
- 参数：无。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  compiled_kernel = compiled_kernel
  compiled_kernel.close()
  ```
- 功能说明：执行 `close`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `CompiledKernel.execute(args: tuple[RuntimeInput, ...] | None = None, *, request: ExecuteRequest | None = None, entry_point: str | None = None, capture_function_output: bool = False, stream: None = None) -> ExecuteResult`

- api：`CompiledKernel.execute(args: tuple[RuntimeInput, ...] | None = None, *, request: ExecuteRequest | None = None, entry_point: str | None = None, capture_function_output: bool = False, stream: None = None) -> ExecuteResult`
- 参数：
  - `args`：位置参数序列，按公开调用约定传递给目标函数或工具入口；类型 `tuple[RuntimeInput, ...] | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `request`：请求对象，承载工具、执行引擎或服务入口需要处理的输入信息；类型 `ExecuteRequest | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `entry_point`：`entry_point` 输入值，参与 `execute` 的公开处理流程；类型 `str | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `capture_function_output`：函数对象或函数级 IR；类型 `bool`；默认值 `False`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `stream`：输入或输出流对象，用于读取源码、写入文本或传递诊断；类型 `None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ExecuteResult`。
- 使用示例：

  ```python
  compiled_kernel = compiled_kernel
  result = compiled_kernel.execute(args=None, request=None, entry_point=None, capture_function_output=False, stream=None)
  ```
- 功能说明：执行 `execute`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `class ExecuteResult(ok: bool, status_code: int, failure_phrase: str | None, compile_stdout: str = "", compile_stderr: str = "", run_stdout: str = "", run_stderr: str = "", elapsed_ms: float = 0.0)`

- api：`class ExecuteResult(ok: bool, status_code: int, failure_phrase: str | None, compile_stdout: str = "", compile_stderr: str = "", run_stdout: str = "", run_stderr: str = "", elapsed_ms: float = 0.0)`
- 参数：
  - `ok`：`ok` 输入值，参与 `ExecuteResult` 的公开处理流程；类型 `bool`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `status_code`：`status_code` 输入值，参与 `ExecuteResult` 的公开处理流程；类型 `int`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `failure_phrase`：`failure_phrase` 输入值，参与 `ExecuteResult` 的公开处理流程；类型 `str | None`；无默认值，调用方必须显式提供；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `compile_stdout`：`compile_stdout` 输入值，参与 `ExecuteResult` 的公开处理流程；类型 `str`；默认值 `""`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `compile_stderr`：`compile_stderr` 输入值，参与 `ExecuteResult` 的公开处理流程；类型 `str`；默认值 `""`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `run_stdout`：`run_stdout` 输入值，参与 `ExecuteResult` 的公开处理流程；类型 `str`；默认值 `""`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `run_stderr`：`run_stderr` 输入值，参与 `ExecuteResult` 的公开处理流程；类型 `str`；默认值 `""`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `elapsed_ms`：`elapsed_ms` 输入值，参与 `ExecuteResult` 的公开处理流程；类型 `float`；默认值 `0.0`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ExecuteResult` 实例。
- 使用示例：

  ```python
  execute_result = ExecuteResult(ok=ok, status_code=status_code, failure_phrase=failure_phrase, compile_stdout="", compile_stderr="", run_stdout="", run_stderr="", elapsed_ms=0.0)
  ```
- 功能说明：定义 `ExecuteResult` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

## 测试

- 测试文件：`test/execute_engine/test_contract.py`
- 执行命令：`pytest -q test/execute_engine/test_contract.py`

### 测试目标

- 验证 `spec/execute_engine/execute_engine_api.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证公开执行入口的返回值、输出或状态变化符合预期。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。
- 验证 DSL、IR 或 EmitC 生成文本与编译链路符合公开合同。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-001 | 执行结果 | execute engine contract files exist | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_execute_engine_contract_files_exist`。 | 命令返回码、输出、执行结果或状态变更体现“execute engine contract files exist”场景。 | `test_execute_engine_contract_files_exist` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-002 | 公开入口 | execute engine public API exports only runtime contract | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_execute_engine_public_api_exports_only_runtime_contract`。 | 公开入口在“execute engine public API exports only runtime contract”场景下可导入、构造、注册或按名称发现。 | `test_execute_engine_public_api_exports_only_runtime_contract` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-003 | 生成/编译 | execute engine compile execute ok | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_execute_engine_compile_execute_ok`。 | 生成源码、IR 文本或编译结果体现“execute engine compile execute ok”场景。 | `test_execute_engine_compile_execute_ok` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-004 | 执行结果 | execute engine stream not supported | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_execute_engine_stream_not_supported`。 | 命令返回码、输出、执行结果或状态变更体现“execute engine stream not supported”场景。 | `test_execute_engine_stream_not_supported` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-005 | 执行结果 | execute engine function output capture not supported | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_execute_engine_function_output_capture_not_supported`。 | 命令返回码、输出、执行结果或状态变更体现“execute engine function output capture not supported”场景。 | `test_execute_engine_function_output_capture_not_supported` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-006 | 边界/异常 | execute engine source empty or invalid | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_execute_engine_source_empty_or_invalid`。 | “execute engine source empty or invalid”场景按公开错误语义失败或被拒绝。 | `test_execute_engine_source_empty_or_invalid` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-007 | 边界/异常 | execute engine target header mismatch | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_execute_engine_target_header_mismatch`。 | “execute engine target header mismatch”场景按公开错误语义失败或被拒绝。 | `test_execute_engine_target_header_mismatch` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-008 | 边界/异常 | execute engine failure phrases frozen | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_execute_engine_failure_phrases_frozen`。 | “execute engine failure phrases frozen”场景按公开错误语义失败或被拒绝。 | `test_execute_engine_failure_phrases_frozen` |
