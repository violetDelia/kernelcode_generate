# execute_engine_api.md

## 功能简介

- 定义执行引擎 `P0` 的请求/结果/参数模型：`CompileRequest / ExecuteRequest / CompiledKernel / ExecuteResult / ArgSpec`。
- 冻结字段、默认值与失败短语触发条件，使调用方无需理解实现细节也能稳定调用与比对结果。

## 文档信息

- 创建者：咯咯咯
- 最后一次更改：咯咯咯
- spec：[`spec/execute_engine/execute_engine_api.md`](spec/execute_engine/execute_engine_api.md)
- 功能实现：[`kernel_gen/execute_engine/execution_engine.py`](kernel_gen/execute_engine/execution_engine.py)
- test：[`test/execute_engine/test_execute_engine_contract.py`](test/execute_engine/test_execute_engine_contract.py)

## 依赖

- 执行引擎总览合同：[`spec/execute_engine/execute_engine.md`](spec/execute_engine/execute_engine.md)
- `emit_c` 输出语义：[`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)

## 术语

- `ArgSpec`：参数模型的统一抽象，取值为 `MemoryArg/IntArg/FloatArg` 之一。
- `failure_phrase`：执行引擎对外固定失败短语集合。

## 目标

- 统一 `CompileRequest/ExecuteRequest/ArgSpec/ExecuteResult` 字段与默认值。
- 明确 `args` 与函数形参顺序的一一对应规则。
- 锁定 7 个失败短语与触发条件。

## 限制与边界

- `P0` 仅支持 `target in {"cpu","npu_demo"}`；其他 target 必须失败并返回 `target_header_mismatch`。
- `P0` 不支持 `stream` 与输出回收；当 `ExecuteRequest.stream is not None` 或 `capture_function_output=True` 必须失败。
- `args` 必须与 `function` 形参顺序严格一致；不做自动重排或参数推断。
- `ArgSpec` 仅允许 `MemoryArg/IntArg/FloatArg` 三类；其他类型必须失败。
- 失败短语只允许取 7 个固定值（见 `ExecuteResult`）；禁止同义词扩散与 silent fallback。

## 公开接口

### `CompileRequest`

功能说明：

- 编译请求模型，描述 `source/target/function` 及编译选项。

参数说明：

- `source(str)`: C++ 源码字符串；为空或非法时必须失败（`source_empty_or_invalid`）。
- `target(str)`: `"cpu"` 或 `"npu_demo"`；不支持的 target 必须失败（`target_header_mismatch`）。
- `function(str)`: 目标函数符号；允许命名空间形式（例如 `"npu_demo::add"`）；解析失败必须失败（`symbol_resolve_failed`）。
- `entry_point(str)`: 入口名；默认 `"kg_execute_entry"`。
- `compiler(str | None)`: 显式编译器；默认 `None`（使用系统默认编译器）。
- `compiler_flags(tuple[str, ...])`: 编译 flags；默认 `("-std=c++17",)`。
- `link_flags(tuple[str, ...])`: 链接 flags；默认 `()`。

使用示例：

```python
req = CompileRequest(
    source=cpp_source,
    target="npu_demo",
    function="npu_demo::add",
)
```

注意事项：

- `function` 必须可被编译产物解析；若符号缺失，视为 `symbol_resolve_failed`。

返回与限制：

- 编译失败必须返回 `compile_failed`。

### `ExecuteRequest`

功能说明：

- 执行请求模型，描述参数序列与运行期控制选项。

参数说明：

- `args(tuple[ArgSpec, ...])`: 有序参数序列，必须与 `function` 形参顺序一致。
- `entry_point(str | None)`: 指定入口；默认 `None`（使用 `CompiledKernel.entry_point`）。
- `capture_function_output(bool)`: 是否回收函数输出；默认 `False`（`P0` 必须失败）。
- `stream(object | None)`: 运行 stream；默认 `None`（`P0` 必须失败）。

使用示例：

```python
exec_req = ExecuteRequest(
    args=(memory_arg0, int_arg1),
    capture_function_output=False,
    stream=None,
)
```

注意事项：

- `args` 的顺序与数量必须与函数形参严格一致；不一致时必须失败并返回 `runtime_throw_or_abort`。
- `entry_point` 非空但无法解析时必须失败并返回 `symbol_resolve_failed`。

返回与限制：

- `stream is not None` 时必须失败（`stream_not_supported`）。
- `capture_function_output=True` 时必须失败（`function_output_capture_not_supported`）。

### `CompiledKernel`

功能说明：

- 编译产物的只读描述，用于后续执行；当编译阶段使用内部临时工作区时，提供 `close()` 用于显式释放该工作区。

参数说明：

- `target(str)`: 编译目标。
- `soname_path(str)`: 产物共享库路径。
- `function(str)`: 目标函数符号。
- `entry_point(str)`: 实际入口名（默认来自 `CompileRequest.entry_point`）。
- `compile_stdout(str)`: 编译 stdout；默认空字符串。
- `compile_stderr(str)`: 编译 stderr；默认空字符串。

使用示例：

```python
kernel = engine.compile(req)
assert kernel.entry_point == "kg_execute_entry"
kernel.close()
```

注意事项：

- `entry_point` 若与产物符号不匹配，执行阶段必须返回 `symbol_resolve_failed`。
- `close()` 必须是幂等的；若编译使用了内部临时工作区，则 `close()` 会释放该工作区，析构时也应兜底释放。
- 若编译过程在返回前已经判定失败，内部临时工作区也必须在抛出/返回失败之前释放。

返回与限制：

- 仅承载编译结果，不负责执行。

### `ExecuteResult`

功能说明：

- 承载 `compile/execute` 的结果与失败短语。

参数说明：

- `ok(bool)`: 成功判定；`ok=True` 时必须满足 `status_code == 0` 且 `failure_phrase is None`。
- `status_code(int)`: `0` 表示成功，非 `0` 表示失败。
- `failure_phrase(str | None)`: 失败短语；成功时为 `None`。
- `compile_stdout(str)`: 编译 stdout；默认空字符串。
- `compile_stderr(str)`: 编译 stderr；默认空字符串。
- `run_stdout(str)`: 运行 stdout；默认空字符串。
- `run_stderr(str)`: 运行 stderr；默认空字符串。
- `elapsed_ms(float)`: 运行耗时；默认 `0.0`。

使用示例：

```python
if not result.ok:
    assert result.failure_phrase in {
        "compile_failed",
        "runtime_throw_or_abort",
        "symbol_resolve_failed",
    }
```

注意事项：

- 失败短语与触发条件必须固定为以下 7 组（仅允许取其一）：
  - `target_header_mismatch`：`target` 不支持或 include 不匹配。
  - `source_empty_or_invalid`：`source` 为空或非法。
  - `compile_failed`：编译器返回非零或编译阶段失败。
  - `symbol_resolve_failed`：`function` / `entry_point` 无法解析。
  - `runtime_throw_or_abort`：执行阶段抛异常、abort、参数不匹配或类型不合法。
  - `stream_not_supported`：`ExecuteRequest.stream is not None`。
  - `function_output_capture_not_supported`：`capture_function_output=True`。

返回与限制：

- `ok=False` 时必须包含非空 `failure_phrase`，且属于固定集合。

### `ArgSpec`

功能说明：

- 统一参数模型的抽象类型。

参数说明：

- `ArgSpec = MemoryArg | IntArg | FloatArg`。

使用示例：

```python
arg0: ArgSpec = MemoryArg(...)
arg1: ArgSpec = IntArg(...)
```

注意事项：

- `args` 序列顺序必须与函数形参严格一致。

返回与限制：

- 仅用于参数描述，不承载执行结果。

### `MemoryArg`

功能说明：

- 内存参数模型，用于传递张量/数组。

参数说明：

- `position(int)`: 形参序号（从 `0` 开始）。
- `param_name(str | None)`: 可选；形参名称（未知时为 `None`）。
- `space(str)`: 内存空间标识（例如 `"global"`/`"shared"`/`"local"`）。
- `dtype(str)`: 数据类型字符串（必须与 `value` 一致）。
- `shape(tuple[int, ...])`: 形状。
- `stride(tuple[int, ...] | None)`: 可选 stride；`None` 表示紧致布局。
- `value(object)`: `torch.Tensor` 或 `numpy.ndarray`。

使用示例：

```python
memory_arg0 = MemoryArg(
    position=0,
    param_name="lhs",
    space="global",
    dtype="float32",
    shape=(2, 3),
    stride=(3, 1),
    value=torch.zeros((2, 3)),
)
```

注意事项：

- `dtype/shape/stride` 必须与 `value` 一致；不一致时必须失败并返回 `runtime_throw_or_abort`。

返回与限制：

- 仅描述参数，不执行数据搬运或拷贝。

### `IntArg`

功能说明：

- 整数参数模型。

参数说明：

- `position(int)`: 形参序号（从 `0` 开始）。
- `param_name(str | None)`: 可选；形参名称（未知时为 `None`）。
- `dtype(str)`: 整数类型字符串。
- `value(int)`: 实际整数值。

使用示例：

```python
int_arg1 = IntArg(position=1, param_name="rhs", dtype="int32", value=1)
```

注意事项：

- `dtype` 必须与目标函数形参一致；不一致时必须失败并返回 `runtime_throw_or_abort`。

返回与限制：

- 仅描述参数，不包含执行结果。

### `FloatArg`

功能说明：

- 浮点参数模型。

参数说明：

- `position(int)`: 形参序号（从 `0` 开始）。
- `param_name(str | None)`: 可选；形参名称（未知时为 `None`）。
- `dtype(str)`: 浮点类型字符串。
- `value(float)`: 实际浮点值。

使用示例：

```python
float_arg2 = FloatArg(position=2, param_name="alpha", dtype="float32", value=1.0)
```

注意事项：

- `dtype` 必须与目标函数形参一致；不一致时必须失败并返回 `runtime_throw_or_abort`。

返回与限制：

- 仅描述参数，不包含执行结果。

## 测试

- 测试文件：[`test/execute_engine/test_execute_engine_contract.py`](test/execute_engine/test_execute_engine_contract.py)
- 执行命令：`pytest -q test/execute_engine/test_execute_engine_contract.py`
- 测试目标：
  - 覆盖 `CompileRequest/ExecuteRequest/ArgSpec/ExecuteResult` 的字段与默认值。
  - 覆盖 `args` 与函数形参顺序的一一对应规则。
  - 覆盖 7 个失败短语与触发条件的最小复现。
- 覆盖 `MemoryArg.value` 支持 `torch.Tensor` / `numpy.ndarray`。
- 覆盖 `stream` 与 `capture_function_output` 的 `P0` 禁用路径。
