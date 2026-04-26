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
- `CompiledKernel.execute(args: tuple[RuntimeArg, ...] | None = None, *, request: ExecuteRequest | None = None, entry_point: str | None = None, capture_function_output: bool = False, stream: object | None = None) -> ExecuteResult`
- `CompiledKernel.close() -> None`
- `class ExecuteResult(ok: bool, status_code: int, failure_phrase: str | None, compile_stdout: str = "", compile_stderr: str = "", run_stdout: str = "", run_stderr: str = "", elapsed_ms: float = 0.0)`

## 文档信息

- 创建者：睡觉小分队
- 最后一次更改：咯咯咯（2026-04-15）
- spec：[`spec/execute_engine/execute_engine.md`](spec/execute_engine/execute_engine.md)
- 功能实现：[`kernel_gen/execute_engine/execution_engine.py`](kernel_gen/execute_engine/execution_engine.py)
- test：[`test/execute_engine/test_execute_engine_contract.py`](test/execute_engine/test_execute_engine_contract.py)

## 依赖

- `emit_c`：负责生成可编译的 C++ 源码片段（本执行引擎不改变 `emit_c` 语义）。
  - 关联 spec：[`spec/dsl/gen_kernel/emit.md`](spec/dsl/gen_kernel/emit.md)
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

## 限制与边界

- `P0` 仅支持 `target in {"cpu","npu_demo"}`；其他 target 必须失败，且 `failure_phrase == "target_header_mismatch"`。
- `P0` 不支持 `stream`；当 `ExecuteRequest.stream is not None` 必须失败，且 `failure_phrase == "stream_not_supported"`。
- `P0` 不支持函数输出回收；当 `ExecuteRequest.capture_function_output=True` 必须失败，且 `failure_phrase == "function_output_capture_not_supported"`。
- `P0` 不负责推导参数个数/顺序；调用方必须提供与 `function` 形参顺序一致的 `args`。
- 禁止 silent fallback：
  - 目标 include 缺失或不匹配时必须失败；不得自动切换到另一 target include。
  - 编译或运行失败必须显式返回失败短语；不得返回 `ok=True` 或用空字符串糊弄。

## 公开接口

### `class ExecutionEngine(target: str, compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`

- 功能说明：按 `compile -> execute` 生命周期编译并执行由 `emit_c` 生成的 C++ 源码。
- 参数说明：
  - `target(str)`: `"cpu"` 或 `"npu_demo"`。
  - `compiler(str | None)`: 可选，显式指定编译器；为 `None` 时使用默认编译器。
  - `compiler_flags(tuple[str, ...])`: 可选，编译 flags（应包含至少 `-std=c++17`）。
  - `link_flags(tuple[str, ...])`: 可选，链接 flags。
- 使用示例：

```python
engine = ExecutionEngine(target="npu_demo")
kernel = engine.compile(
    source=cpp_source,
    function="npu_demo::add",
)
result = kernel.execute(args=(lhs, rhs, out))
assert result.ok is True
```

- 注意事项：
  - `compile` 与 `execute` 必须分离；不得将运行阶段隐式塞进 `compile`。
  - `args` 仅允许 `memory/int/float` 三类；其他类型必须失败。
- 返回与限制：
  - `compile(...) -> CompiledKernel`；失败时必须返回 `ExecuteResult(ok=False, failure_phrase=...)` 或抛出等价的失败（具体承载形式见后续接口文档）。

### `ExecutionEngine.compile(source: str | None = None, function: str | None = None, *, request: CompileRequest | None = None, entry_point: str = "kg_execute_entry") -> CompiledKernel`

- 功能说明：编译 `source`，并返回可执行的 `CompiledKernel`。
- 参数说明（P0 总览级冻结）：
  - `source(str)`: C++ 源码字符串；为空或非法时必须失败，`failure_phrase == "source_empty_or_invalid"`。
  - `function(str)`: 目标函数符号（例如 `"npu_demo::add"`）；符号解析失败时必须失败，`failure_phrase == "symbol_resolve_failed"`。
  - `entry_point(str)`: 可选；未提供时默认 `"kg_execute_entry"`。
- 返回与限制：
  - 编译失败必须失败，`failure_phrase == "compile_failed"`。
  - 若编译过程使用了内部临时工作区，则在失败返回前必须先释放该工作区，避免临时文件残留。

### `CompiledKernel.execute(args: tuple[RuntimeArg, ...] | None = None, *, request: ExecuteRequest | None = None, entry_point: str | None = None, capture_function_output: bool = False, stream: object | None = None) -> ExecuteResult`

- 功能说明：以有序参数序列运行 `entry_point`，并返回 `ExecuteResult`。
- 参数说明（P0 总览级冻结）：
  - `args(tuple[RuntimeArg, ...])`: 有序参数序列；必须与目标函数形参顺序一致。
  - `entry_point(str | None)`: 可选；为 `None` 时使用 `CompiledKernel.entry_point`。
  - `stream(object | None)`: `P0` 不支持，非空必失败（`stream_not_supported`）。
  - `capture_function_output(bool)`: `P0` 不支持，为 `True` 必失败（`function_output_capture_not_supported`）。
- 返回与限制：
  - 运行时抛出/abort 必须失败，`failure_phrase == "runtime_throw_or_abort"`。
  - `entry_point` 无法解析时必须失败，`failure_phrase == "symbol_resolve_failed"`。

### `CompiledKernel.close() -> None`

- 功能说明：显式释放编译阶段创建的内部临时工作区。
- 使用示例：

```python
kernel = engine.compile(source="int main(){}", function="cpu::add")
try:
    result = kernel.execute(args=())
    assert result.ok is True
finally:
    kernel.close()
```

- 注意事项：
  - `close()` 必须是幂等的，重复调用不得再释放同一临时工作区。
  - 若编译阶段未使用内部临时工作区，`close()` 必须保持空操作语义。

### `class ExecuteResult(ok: bool, status_code: int, failure_phrase: str | None, compile_stdout: str = "", compile_stderr: str = "", run_stdout: str = "", run_stderr: str = "", elapsed_ms: float = 0.0)`

- 功能说明：承载 `compile/execute` 的可机械比较结果。
- 字段说明（P0 总览级冻结）：
  - `ok(bool)`: 成功判定；`ok=True` 时必须满足 `status_code == 0` 且 `failure_phrase is None`。
  - `status_code(int)`: `0` 表示成功；非 `0` 表示失败。
  - `failure_phrase(str | None)`: 失败短语；仅允许取以下固定值之一（成功时为 `None`）：
    - `target_header_mismatch`
    - `source_empty_or_invalid`
    - `compile_failed`
    - `symbol_resolve_failed`
    - `runtime_throw_or_abort`
    - `stream_not_supported`
    - `function_output_capture_not_supported`
- 使用示例：

```python
if not result.ok:
    assert result.failure_phrase in {
        "compile_failed",
        "runtime_throw_or_abort",
        "symbol_resolve_failed",
    }
```

## `execute_engine + npu_demo + matmul`（S1）合同说明

- 适用范围：[`test/execute_engine/test_execute_engine_compile.py`](test/execute_engine/test_execute_engine_compile.py) 与 [`test/execute_engine/test_execute_engine_invoke.py`](test/execute_engine/test_execute_engine_invoke.py) 中的 tiled matmul smoke。
- 本阶段定义合同文本与验收映射，不在本文件扩展新的运行时能力。
- `CASE-1`（raw IR）：前端 tile memory 语义必须体现 `MemorySpace.TSM -> #nn.space<tsm>`。
- `CASE-2`（lowering IR）：tiled loop 内应出现 `kernel.matmul`，且不应残留 `nn.matmul`。
- `CASE-3`（source + execute）：源码应命中 `npu_demo::matmul(`，并通过 `compile -> execute` 返回 `ok=True,status_code=0,failure_phrase=None`。

使用示例：

```python
engine = ExecutionEngine(target="npu_demo")
kernel = engine.compile(source=generated_source, function="npu_demo::matmul")
result = kernel.execute(args=(out, lhs, rhs))
assert result.ok and result.failure_phrase is None
```

验收映射：

- 合同资产：[`test/execute_engine/test_execute_engine_compile.py`](test/execute_engine/test_execute_engine_compile.py)、[`test/execute_engine/test_execute_engine_invoke.py`](test/execute_engine/test_execute_engine_invoke.py)
- 关联 spec：[`spec/dsl/gen_kernel/emit.md`](spec/dsl/gen_kernel/emit.md)、[`spec/dsl/gen_kernel/gen_kernel.md`](spec/dsl/gen_kernel/gen_kernel.md)
- 关联测试：[`test/execute_engine/test_execute_engine_compile.py`](test/execute_engine/test_execute_engine_compile.py)、[`test/execute_engine/test_execute_engine_invoke.py`](test/execute_engine/test_execute_engine_invoke.py)

## 测试

- 测试文件：[`test/execute_engine/test_execute_engine_contract.py`](test/execute_engine/test_execute_engine_contract.py)
- 执行命令：
  - `pytest -q test/execute_engine/test_execute_engine_contract.py`
- 测试目标：
  - 覆盖 `compile -> execute` 生命周期最小闭环。
  - 覆盖 `stream/output_capture` 的 `P0` 禁用失败短语。
  - 覆盖 `target` 不匹配、源码非法、符号解析失败、编译失败、运行失败的失败短语入口。
- 功能与用例清单：
  - `EE-S1-001`：`compile -> execute` 成功返回 `ok=True,status_code=0,failure_phrase=None`。
  - `EE-S1-002`：`stream != None` 触发 `stream_not_supported`。
  - `EE-S1-003`：`capture_function_output=True` 触发 `function_output_capture_not_supported`。
  - `EE-S1-004`：空/非法 `source` 触发 `source_empty_or_invalid`。
  - `EE-S1-005`：符号解析失败触发 `symbol_resolve_failed`。
  - `EE-S1-006`：编译失败触发 `compile_failed`。
  - `EE-S1-007`：运行时异常触发 `runtime_throw_or_abort`。
