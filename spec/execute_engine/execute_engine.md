# execute_engine.md

## 功能简介

- 本文档定义执行引擎（Execution Engine）的 `P0` 总览合同：把由 `emit_c` 产生的 C++ 源码片段，按 `compile -> execute` 两段式流程编译并执行。
- **生命周期**：`compile(request) -> CompiledKernel`，随后 `CompiledKernel.execute(exec_request) -> ExecuteResult`；当编译过程使用内部临时工作区时，`CompiledKernel.close()` 或对象析构必须释放该工作区。
- **输入**：
  - `source`：C++ 源码字符串（单个 translation unit）。
  - `target`：目标后端标识（`cpu` / `npu_demo`）。
  - `function`：要调用的目标函数符号（例如 `"npu_demo::add"`）。
  - `args`：按形参顺序排列的入参序列，元素类型仅允许：`memory` / `int` / `float`。
- **失败短语入口**：所有失败必须在 `ExecuteResult.failure_phrase` 以“固定短语”表达，禁止静默 fallback 或同义词扩散。
- **非目标（P0 不支持）**：
  - `stream` / 异步调度。
  - 函数输出回收（output capture），仅保留显式扩展位与失败短语。

## API 列表

- `class ExecutionEngine(target: str, compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`
- `ExecutionEngine.compile(source: str | None = None, function: str | None = None, *, request: CompileRequest | None = None, entry_point: str = "kg_execute_entry") -> CompiledKernel`
- `class CompiledKernel(target: str, soname_path: str, function: str, entry_point: str, compile_stdout: str = "", compile_stderr: str = "")`
- `CompiledKernel.execute(args: tuple[RuntimeInput, ...] | None = None, *, request: ExecuteRequest | None = None, entry_point: str | None = None, capture_function_output: bool = False, stream: None = None) -> ExecuteResult`
- `CompiledKernel.close() -> None`
- `class ExecuteResult(ok: bool, status_code: int, failure_phrase: str | None, compile_stdout: str = "", compile_stderr: str = "", run_stdout: str = "", run_stderr: str = "", elapsed_ms: float = 0.0)`
- `class CompileStrategy(Protocol)`
- `CompileStrategy.compile(self, request: CompileRequest) -> CompiledKernel`
- `register_compile_strategy(target: str, strategy: CompileStrategy, *, override: bool = False) -> None`
- `get_compile_strategy(target: str) -> CompileStrategy`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/execute_engine/execute_engine.md`](spec/execute_engine/execute_engine.md)
- `功能实现`：[`kernel_gen/execute_engine/compiler.py`](kernel_gen/execute_engine/compiler.py)
- `test`：[`test/execute_engine/test_contract.py`](test/execute_engine/test_contract.py)

## 依赖

- `emit_c`：负责生成可编译的 C++ 源码片段（本执行引擎不改变 `emit_c` 语义）。
  - 关联 spec：[`spec/dsl/gen_kernel/emit.md`](spec/dsl/gen_kernel/emit.md)
- `CompileStrategy`：负责第三方 target 编译扩展。
  - 关联 spec：[`spec/execute_engine/strategy.md`](strategy.md)
- `target` 相关 include 目录（由 target 映射决定）：
  - `npu_demo`：`include/npu_demo/*`
  - `cpu`：`include/cpu/*`

## 术语

- `Compile`：把 `source` 编译为可执行实体（例如 `.so`），并绑定 `target/function/entry_point`。
- `Execute`：以有序参数序列调用已编译实体的入口函数，返回 `ExecuteResult`。
- `entry_point`：执行引擎对外稳定的 C ABI 入口名；`P0` 必须可配置但允许有默认值。

## 目标

- 冻结 `ExecutionEngine.compile(...).execute(...)` 的公开入口形态，使下游可在不理解内部编译细节的前提下稳定调用。
- 冻结 `target` 与 include 的映射约束，保证 `target=npu_demo` 不会回退到 `cpu::*`。
- 冻结 `P0` 的失败短语集合与触发条件入口，保证测试可机械比较。
- 允许第三方 target 通过 compile strategy 扩展编译链路，且不得修改 `ExecutionEngine.compile(...)` 公开签名。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- `P0` 内置真实编译/执行支持 `target in {"cpu","npu_demo"}`；其他 target 必须注册 compile strategy，缺失时 `failure_phrase == "target_header_mismatch"`。
- 第三方 compile-only target 的 `CompiledKernel.execute(...)` 必须以 `failure_phrase == "execution_unsupported"` 公开失败，不得 fallback 到普通 kernel。
- `P0` 不支持 `stream`；当 `ExecuteRequest.stream is not None` 必须失败，且 `failure_phrase == "stream_not_supported"`。
- `P0` 不支持函数输出回收；当 `ExecuteRequest.capture_function_output=True` 必须失败，且 `failure_phrase == "function_output_capture_not_supported"`。
- `P0` 不负责推导参数个数/顺序；调用方必须提供与 `function` 形参顺序一致的 `args`。
- 禁止 silent fallback：
  - 目标 include 缺失或不匹配时必须失败；不得自动切换到另一 target include。
  - 编译或运行失败必须显式返回失败短语；不得返回 `ok=True` 或用空字符串糊弄。
### `execute_engine + npu_demo + matmul`（S1）合同说明

- 适用范围：[`test/execute_engine/test_compile.py`](test/execute_engine/test_compile.py) 与 [`test/execute_engine/test_invoke.py`](test/execute_engine/test_invoke.py) 中的 tiled matmul smoke。
- 本阶段定义合同文本与验收映射，不在本文件扩展新的运行时能力。
- `CASE-1`（raw IR）：前端 tile memory 语义必须体现 `MemorySpace.TSM -> #nn.space<tsm>`。
- `CASE-2`（lowering IR）：tiled loop 内应出现 `kernel.matmul`，且不应残留 `nn.matmul`。
- `CASE-3`（source + execute）：源码应命中 `npu_demo::matmul(`，并通过 `compile -> execute` 返回 `ok=True,status_code=0,failure_phrase=None`。

- 使用示例：

```python
engine = ExecutionEngine(target="npu_demo")
kernel = engine.compile(source=generated_source, function="npu_demo::matmul")
result = kernel.execute(args=(out, lhs, rhs))
assert result.ok and result.failure_phrase is None
```

验收映射：

- 合同资产：[`test/execute_engine/test_compile.py`](test/execute_engine/test_compile.py)、[`test/execute_engine/test_invoke.py`](test/execute_engine/test_invoke.py)
- 关联 spec：[`spec/dsl/gen_kernel/emit.md`](spec/dsl/gen_kernel/emit.md)、[`spec/dsl/gen_kernel/gen_kernel.md`](spec/dsl/gen_kernel/gen_kernel.md)
- 关联测试：[`test/execute_engine/test_compile.py`](test/execute_engine/test_compile.py)、[`test/execute_engine/test_invoke.py`](test/execute_engine/test_invoke.py)

## API详细说明

### `class ExecutionEngine(target: str, compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`

- api：`class ExecutionEngine(target: str, compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`
- 参数：
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `compiler`：编译器命令或编译器对象，用于把生成源码编译为可执行产物；类型 `str | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `compiler_flags`：`compiler_flags` 输入值，参与 `ExecutionEngine` 的公开处理流程；类型 `tuple[str, ...]`；默认值 `("-std=c++17",)`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `link_flags`：`link_flags` 输入值，参与 `ExecutionEngine` 的公开处理流程；类型 `tuple[str, ...]`；默认值 `()`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ExecutionEngine` 实例。
- 使用示例：

  ```python
  execution_engine = ExecutionEngine(target=target, compiler=None, compiler_flags=compiler_flags, link_flags=link_flags)
  ```
- 功能说明：定义 `ExecutionEngine` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `ExecutionEngine.compile(source: str | None = None, function: str | None = None, *, request: CompileRequest | None = None, entry_point: str = "kg_execute_entry") -> CompiledKernel`

- api：`ExecutionEngine.compile(source: str | None = None, function: str | None = None, *, request: CompileRequest | None = None, entry_point: str = "kg_execute_entry") -> CompiledKernel`
- 参数：
  - `source`：源对象、源缓冲区或源文本，提供当前操作读取的数据来源；类型 `str | None`；默认值 `None`；使用 `request` 时必须为 `None`；混用时必须以 `source_empty_or_invalid` 失败；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `function`：Python 函数、DSL 函数或函数级对象，作为构建或执行输入；类型 `str | None`；默认值 `None`；使用 `request` 时必须为 `None`；混用时必须以 `source_empty_or_invalid` 失败；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `request`：请求对象，承载工具、执行引擎或服务入口需要处理的输入信息；类型 `CompileRequest | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `entry_point`：`entry_point` 输入值，参与 `compile` 的公开处理流程；类型 `str`；默认值 `"kg_execute_entry"`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`CompiledKernel`。
- 使用示例：

  ```python
  execution_engine = execution_engine
  result = execution_engine.compile(source=None, function=None, request=None, entry_point="kg_execute_entry")
  ```
- 功能说明：执行 `compile`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态；`request` 非 `None` 时不得同时提供 `source` 或 `function`。

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

- 验证 `spec/execute_engine/execute_engine.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证非法输入、边界条件和错误语义按公开合同失败。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。
- 验证公开执行入口的返回值、输出或状态变化符合预期。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-001 | 边界/异常 | `compile -> execute` 成功返回 `ok=True,status_code=0,failure_phrase=None`。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `EE-S1-001`。 | “`compile -> execute` 成功返回 `ok=True,status_code=0,failure_phrase=None`。”场景按公开错误语义失败或被拒绝。 | `EE-S1-001` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-002 | 公开入口 | `stream != None` 触发 `stream_not_supported`。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `EE-S1-002`。 | 公开入口在“`stream != None` 触发 `stream_not_supported`。”场景下可导入、构造、注册或按名称发现。 | `EE-S1-002` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-003 | 执行结果 | `capture_function_output=True` 触发 `function_output_capture_not_supported`。 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `EE-S1-003`。 | 命令返回码、输出、执行结果或状态变更体现“`capture_function_output=True` 触发 `function_output_capture_not_supported`。”场景。 | `EE-S1-003` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-004 | 边界/异常 | 空/非法 `source` 触发 `source_empty_or_invalid`。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `EE-S1-004`。 | “空/非法 `source` 触发 `source_empty_or_invalid`。”场景按公开错误语义失败或被拒绝。 | `EE-S1-004` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-005 | 边界/异常 | 符号解析失败触发 `symbol_resolve_failed`。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `EE-S1-005`。 | “符号解析失败触发 `symbol_resolve_failed`。”场景按公开错误语义失败或被拒绝。 | `EE-S1-005` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-006 | 边界/异常 | 编译失败触发 `compile_failed`。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `EE-S1-006`。 | “编译失败触发 `compile_failed`。”场景按公开错误语义失败或被拒绝。 | `EE-S1-006` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-007 | 执行结果 | 运行时异常触发 `runtime_throw_or_abort`。 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `EE-S1-007`。 | 命令返回码、输出、执行结果或状态变更体现“运行时异常触发 `runtime_throw_or_abort`。”场景。 | `EE-S1-007` |
