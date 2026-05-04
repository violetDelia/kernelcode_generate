# Trance

## 功能简介

定义 runtime trance kernel log 的 include API 规范，负责在编译期 `TRANCE` 开启后记录 kernel 调用、模板信息、运行期参数摘要和成本返回值。

- `TRANCE` 是唯一编译期启用宏；关闭时 `include/api/Trance.h` 必须保持无副作用 no-op。
- `KG_TRANCE_KERNEL_NAME` 是编译链注入的 kernel 名称宏；未注入时后端实现默认使用 `"kernel"`。
- `KG_TRANCE_FILE_PATH` 是编译链注入的 trace 文件路径宏；空字符串表示输出到 stdout。
- `kernelcode::trance::ScopedTranceSink` 负责在一次运行期入口内建立当前 sink，并在析构时关闭文件 sink。
- `Memory::trance_print(...)` 的参数摘要格式由 [`spec/include/api/Memory.md`](Memory.md) 定义。

## API 列表

- `TRANCE -> macro`
- `KG_TRANCE_KERNEL_NAME -> const char* macro`
- `KG_TRANCE_FILE_PATH -> const char* macro`
- `struct kernelcode::trance::TranceSink`
- `kernelcode::trance::make_stdout_sink() -> TranceSink`
- `kernelcode::trance::make_file_sink(const char* file_path) -> TranceSink`
- `kernelcode::trance::make_default_sink() -> TranceSink`
- `kernelcode::trance::close_sink(TranceSink& sink) -> void`
- `kernelcode::trance::current_sink() -> const TranceSink&`
- `class kernelcode::trance::ScopedTranceSink`
- `kernelcode::trance::ScopedTranceSink::ScopedTranceSink()`
- `kernelcode::trance::ScopedTranceSink::~ScopedTranceSink() -> void`
- `kernelcode::trance::write_line(const TranceSink& sink, const char* text) -> void`
- `kernelcode::trance::write_log_failed_and_fallback(const char* file_path) -> void`
- `kernelcode::trance::print_func_begin(const TranceSink& sink, const char* func_name, const char* template_desc) -> void`
- `kernelcode::trance::print_return_i64(const TranceSink& sink, long long value) -> void`
- `template <typename Callable> kernelcode::trance::print_callable_arg(const TranceSink& sink, const char* name, Callable&& callable) -> void`
- `template <typename T> kernelcode::trance::print_value_arg(const TranceSink& sink, const char* name, const T& value) -> void`

## 文档信息

- `spec`：`spec/include/api/Trance.md`
- `功能实现`：`include/api/Trance.h` 提供公开声明与 no-op 占位；`include/npu_demo/Trance.h` 提供 `npu_demo` 后端实现。
- `test`：`test/include/api/test_trance.py`

## 依赖

- [`spec/core/config.md`](../../core/config.md)：定义 `set_trance_enabled(value: bool) -> None` 与 `dump_dir` 配置来源。
- [`spec/execute_engine/execute_engine_target.md`](../../execute_engine/execute_engine_target.md)：定义编译期宏注入和 entry shim 参数打印。
- [`spec/include/api/Memory.md`](Memory.md)：定义 `Memory::trance_print(...)` 输出格式。
- [`spec/include/api/Arch.md`](Arch.md)：定义 `launch<...>(callee, args...)` 公开入口。
- [`spec/include/npu_demo/npu_demo.md`](../npu_demo/npu_demo.md)：定义 `include/npu_demo/npu_demo.h` 聚合与后端 runtime 承接。

## 目标

- 为 runtime kernel log 提供单一 include 入口，避免在 `dsl_run(...)`、runner 或执行引擎上新增平行参数。
- 明确 stdout、文件输出、文件失败回退和关闭语义，使生成源码与手写 include 消费者可复现同一行为。
- 保证 `TRANCE` 未开启时不扩散标准库打印、文件管理或额外运行期副作用。

## API详细说明

### `TRANCE -> macro`

- api：`TRANCE -> macro`
- 参数：无。
- 返回值：编译期宏，不提供运行期返回值。
- 使用示例：

  ```cpp
  #ifdef TRANCE
  kernelcode::trance::write_line(kernelcode::trance::current_sink(), "enabled");
  #endif
  ```
- 功能说明：启用 runtime trance kernel log 的编译期宏。
- 注意事项：未定义 `TRANCE` 时，`include/api/Trance.h` 中公开函数必须保持 no-op；不得输出 stdout、打开文件或改变 kernel 执行结果。

### `KG_TRANCE_KERNEL_NAME -> const char* macro`

- api：`KG_TRANCE_KERNEL_NAME -> const char* macro`
- 参数：无。
- 返回值：编译期字符串宏。
- 使用示例：

  ```cpp
  kernelcode::trance::print_func_begin(
      kernelcode::trance::current_sink(),
      KG_TRANCE_KERNEL_NAME,
      "template=<none>");
  ```
- 功能说明：表示当前编译入口的 kernel 名称。
- 注意事项：编译链开启 `TRANCE` 时必须注入该宏；未注入时后端实现默认值为 `"kernel"`；该宏只用于诊断文本，不参与符号解析或入口查找。

### `KG_TRANCE_FILE_PATH -> const char* macro`

- api：`KG_TRANCE_FILE_PATH -> const char* macro`
- 参数：无。
- 返回值：编译期字符串宏。
- 使用示例：

  ```cpp
  kernelcode::trance::TranceSink sink = kernelcode::trance::make_file_sink(KG_TRANCE_FILE_PATH);
  ```
- 功能说明：表示 runtime trance 输出文件路径。
- 注意事项：空字符串表示输出到 stdout；非空路径打开失败时必须输出 `log failed: <path>` 并回退 stdout；文件 sink 使用覆盖写入语义。

### `struct kernelcode::trance::TranceSink`

- api：`struct kernelcode::trance::TranceSink`
- 参数：无。
- 返回值：sink 状态结构。
- 使用示例：

  ```cpp
  kernelcode::trance::TranceSink sink = kernelcode::trance::make_stdout_sink();
  ```
- 功能说明：承载 runtime trance 输出目标。
- 注意事项：调用方不得依赖字段布局；`TRANCE` 关闭时该结构可为空结构，仍必须可默认构造和传参。

### `kernelcode::trance::make_stdout_sink() -> TranceSink`

- api：`kernelcode::trance::make_stdout_sink() -> TranceSink`
- 参数：无。
- 返回值：`TranceSink`，表示 stdout 输出目标。
- 使用示例：

  ```cpp
  auto sink = kernelcode::trance::make_stdout_sink();
  kernelcode::trance::write_line(sink, "line");
  ```
- 功能说明：创建 stdout sink。
- 注意事项：`TRANCE` 关闭时返回 no-op sink；`TRANCE` 开启时输出必须写入 stdout 并 flush。

### `kernelcode::trance::make_file_sink(const char* file_path) -> TranceSink`

- api：`kernelcode::trance::make_file_sink(const char* file_path) -> TranceSink`
- 参数：
  - `file_path`：trace 文件路径；类型 `const char*`；必填；允许空指针或空字符串；空指针与空字符串都按 stdout sink 处理。
- 返回值：`TranceSink`，表示文件 sink 或回退后的 stdout sink。
- 使用示例：

  ```cpp
  auto sink = kernelcode::trance::make_file_sink("dump/kernel_trace.txt");
  ```
- 功能说明：创建文件输出 sink。
- 注意事项：文件必须按覆盖写入打开；打开失败时必须输出 `log failed: <path>` 并返回 stdout sink；调用方应在不再使用时调用 `close_sink(...)` 或使用 `ScopedTranceSink`。

### `kernelcode::trance::make_default_sink() -> TranceSink`

- api：`kernelcode::trance::make_default_sink() -> TranceSink`
- 参数：无。
- 返回值：`TranceSink`。
- 使用示例：

  ```cpp
  auto sink = kernelcode::trance::make_default_sink();
  ```
- 功能说明：按 `KG_TRANCE_FILE_PATH` 创建默认 sink。
- 注意事项：`KG_TRANCE_FILE_PATH` 为空时返回 stdout sink；非空路径按 `make_file_sink(...)` 的失败回退语义处理。

### `kernelcode::trance::close_sink(TranceSink& sink) -> void`

- api：`kernelcode::trance::close_sink(TranceSink& sink) -> void`
- 参数：
  - `sink`：待关闭的输出 sink；类型 `TranceSink&`；必填；调用后该 sink 不应继续用于输出。
- 返回值：无返回值。
- 使用示例：

  ```cpp
  auto sink = kernelcode::trance::make_stdout_sink();
  kernelcode::trance::close_sink(sink);
  ```
- 功能说明：关闭文件 sink 或处理 no-op/stdout sink。
- 注意事项：stdout sink 和 no-op sink 关闭时不得产生额外输出；文件 sink 关闭后不得重复关闭底层文件句柄。

### `kernelcode::trance::current_sink() -> const TranceSink&`

- api：`kernelcode::trance::current_sink() -> const TranceSink&`
- 参数：无。
- 返回值：`const TranceSink&`，表示当前作用域 sink。
- 使用示例：

  ```cpp
  kernelcode::trance::ScopedTranceSink scope;
  kernelcode::trance::write_line(kernelcode::trance::current_sink(), "line");
  ```
- 功能说明：读取当前 runtime trance sink。
- 注意事项：没有当前线程活动 `ScopedTranceSink` 时必须返回 stdout sink；活动 sink 按线程隔离，不得让未建立 scope 的其它线程继承当前线程的 sink；返回引用只在当前调用上下文内用于输出，不作为长期持有对象。

### `class kernelcode::trance::ScopedTranceSink`

- api：`class kernelcode::trance::ScopedTranceSink`
- 参数：无。
- 返回值：`ScopedTranceSink` 实例。
- 使用示例：

  ```cpp
  kernelcode::trance::ScopedTranceSink scope;
  ```
- 功能说明：在当前作用域建立默认 sink。
- 注意事项：构造时使用 `make_default_sink()`；析构时关闭当前线程的 current sink 并恢复当前线程的前一个 sink；该类型不承诺跨线程共享同一个活动 sink。

### `kernelcode::trance::ScopedTranceSink::ScopedTranceSink()`

- api：`kernelcode::trance::ScopedTranceSink::ScopedTranceSink()`
- 参数：无。
- 返回值：无返回值；构造完成后当前作用域已有可读取 sink。
- 使用示例：

  ```cpp
  kernelcode::trance::ScopedTranceSink scope;
  ```
- 功能说明：构造当前作用域 runtime trance sink。
- 注意事项：构造失败不得改变 kernel 数学结果；文件打开失败必须按 `make_file_sink(...)` 语义回退 stdout。

### `kernelcode::trance::ScopedTranceSink::~ScopedTranceSink() -> void`

- api：`kernelcode::trance::ScopedTranceSink::~ScopedTranceSink() -> void`
- 参数：无。
- 返回值：无返回值。
- 使用示例：

  ```cpp
  {
      kernelcode::trance::ScopedTranceSink scope;
      kernelcode::trance::write_line(kernelcode::trance::current_sink(), "line");
  }
  ```
- 功能说明：结束当前 sink 作用域。
- 注意事项：析构必须关闭文件 sink；析构不得抛出异常或改变 kernel 返回码。

### `kernelcode::trance::write_line(const TranceSink& sink, const char* text) -> void`

- api：`kernelcode::trance::write_line(const TranceSink& sink, const char* text) -> void`
- 参数：
  - `sink`：输出目标；类型 `const TranceSink&`；必填。
  - `text`：待输出文本；类型 `const char*`；必填；空指针按空字符串输出。
- 返回值：无返回值。
- 使用示例：

  ```cpp
  kernelcode::trance::write_line(kernelcode::trance::current_sink(), "args =");
  ```
- 功能说明：输出一行 runtime trance 文本。
- 注意事项：实现必须追加换行并 flush；`TRANCE` 关闭时必须无副作用。

### `kernelcode::trance::write_log_failed_and_fallback(const char* file_path) -> void`

- api：`kernelcode::trance::write_log_failed_and_fallback(const char* file_path) -> void`
- 参数：
  - `file_path`：打开失败的 trace 文件路径；类型 `const char*`；必填；空指针按空字符串输出。
- 返回值：无返回值。
- 使用示例：

  ```cpp
  kernelcode::trance::write_log_failed_and_fallback("dump/missing/kernel_trace.txt");
  ```
- 功能说明：输出文件 sink 打开失败提示。
- 注意事项：稳定文本前缀为 `log failed: `；该函数只报告失败并使用 stdout，不尝试创建目录。

### `kernelcode::trance::print_func_begin(const TranceSink& sink, const char* func_name, const char* template_desc) -> void`

- api：`kernelcode::trance::print_func_begin(const TranceSink& sink, const char* func_name, const char* template_desc) -> void`
- 参数：
  - `sink`：输出目标；类型 `const TranceSink&`；必填。
  - `func_name`：函数或 kernel 名称；类型 `const char*`；必填；空指针按空字符串处理。
  - `template_desc`：模板参数描述；类型 `const char*`；必填；空指针按空字符串处理。
- 返回值：无返回值。
- 使用示例：

  ```cpp
  kernelcode::trance::print_func_begin(
      kernelcode::trance::current_sink(),
      "npu_demo::launch",
      "template=<block=1, thread=2, subthread=1, shared_memory_size=0>");
  ```
- 功能说明：输出函数入口行。
- 注意事项：输出格式固定为 `in func: <func_name> <template_desc>`；`template_desc` 必须与 `in func:` 在同一行。

### `kernelcode::trance::print_return_i64(const TranceSink& sink, long long value) -> void`

- api：`kernelcode::trance::print_return_i64(const TranceSink& sink, long long value) -> void`
- 参数：
  - `sink`：输出目标；类型 `const TranceSink&`；必填。
  - `value`：待输出返回值；类型 `long long`；必填。
- 返回值：无返回值。
- 使用示例：

  ```cpp
  kernelcode::trance::print_return_i64(kernelcode::trance::current_sink(), 42);
  ```
- 功能说明：输出成本函数返回值。
- 注意事项：输出格式固定为 `return = <value>`；该输出不改变 Python 侧返回值或 C++ wrapper 写回路径。

### `template <typename Callable> kernelcode::trance::print_callable_arg(const TranceSink& sink, const char* name, Callable&& callable) -> void`

- api：`template <typename Callable> kernelcode::trance::print_callable_arg(const TranceSink& sink, const char* name, Callable&& callable) -> void`
- 参数：
  - `sink`：输出目标；类型 `const TranceSink&`；必填。
  - `name`：参数名；类型 `const char*`；必填；空指针按空字符串处理。
  - `callable`：可调用对象；类型 `Callable&&`；必填；只用于标记 callable 参数，不调用该对象。
- 返回值：无返回值。
- 使用示例：

  ```cpp
  kernelcode::trance::print_callable_arg(kernelcode::trance::current_sink(), "arg0", kernel_body);
  ```
- 功能说明：输出 callable 参数摘要。
- 注意事项：输出格式固定为 `<name> = callable[kernel_body]`；不得执行 `callable` 或依赖 callable 的内部类型名作为稳定文本。

### `template <typename T> kernelcode::trance::print_value_arg(const TranceSink& sink, const char* name, const T& value) -> void`

- api：`template <typename T> kernelcode::trance::print_value_arg(const TranceSink& sink, const char* name, const T& value) -> void`
- 参数：
  - `sink`：输出目标；类型 `const TranceSink&`；必填。
  - `name`：参数名；类型 `const char*`；必填；空指针按空字符串处理。
  - `value`：待输出的标量或 `Memory` 参数；类型 `const T&`；必填；标量通过 stream 输出，`Memory` 参数委托 `Memory::trance_print(...)`。
- 返回值：无返回值。
- 使用示例：

  ```cpp
  kernelcode::trance::print_value_arg(kernelcode::trance::current_sink(), "arg1", 7);
  ```
- 功能说明：输出运行期参数摘要。
- 注意事项：标量输出格式固定为 `<name> = <value>`；`Memory` 输出格式由 `Memory::trance_print(...)` 负责；该函数不得改变参数值或 kernel 调用顺序。

## 测试

- 测试文件：
  - `test/include/api/test_trance.py`
  - `test/include/api/test_public_namespace.py`
- 执行命令：
  - `pytest -q test/include/api/test_trance.py`
  - `pytest -q test/include/api/test_public_namespace.py`

### 测试目标

- 验证 `TRANCE` 关闭时 `include/api/Trance.h` 公开函数为 no-op。
- 验证 include/api 公开头文件组合可被调用方直接包含。
- 验证 `TRANCE` 开启时 stdout sink 输出函数入口、launch 模板信息、callable 参数摘要与 forwarded args 参数摘要。
- 验证文件 sink 打开失败时输出 `log failed: <path>` 并回退 stdout。
- 验证 `ScopedTranceSink/current_sink` 的活动 sink 按线程隔离，未建 scope 的其它线程不继承当前线程的文件 sink。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-INCLUDE-API-TRANCE-001 | 公开入口 | `TRANCE` 关闭时 no-op 公开函数可编译运行。 | 只 include `include/api/Trance.h`，不传 `-DTRANCE`。 | 运行 `test_api_trance_header_noop_without_macro`。 | 程序成功运行且 stdout 为空。 | `test_api_trance_header_noop_without_macro` |
| TC-INCLUDE-API-TRANCE-002 | 执行结果 | `TRANCE` 开启时 stdout 输出 Memory forwarded 参数和 launch 模板信息。 | include `include/npu_demo/npu_demo.h`，传 `-DTRANCE`，通过 `launch` 传入 `Memory<GM, float>` 与标量参数。 | 运行 `test_npu_demo_trance_stdout_memory_and_launch_format`。 | stdout 包含 `in func: npu_demo::launch template=<block=1, thread=2, subthread=1, shared_memory_size=0>`、`arg0 = callable[kernel_body]`、`arg1 = mem[...] [2, 3] [3, 1] f32 GM` 与 `arg2 = 7`。 | `test_npu_demo_trance_stdout_memory_and_launch_format` |
| TC-INCLUDE-API-TRANCE-003 | 边界/异常 | 文件 sink 打开失败后回退 stdout。 | 传 `-DTRANCE` 与不存在父目录的 `KG_TRANCE_FILE_PATH`。 | 运行 `test_npu_demo_trance_file_open_failure_falls_back_to_stdout`。 | stdout 包含 `log failed: <path>` 和后续输出行，目标文件不存在。 | `test_npu_demo_trance_file_open_failure_falls_back_to_stdout` |
| TC-INCLUDE-API-TRANCE-004 | 公开入口 | include/api 公开头文件组合可直接 compile-only 消费。 | include `Core.h`、`Arch.h`、`Trance.h`、`Memory.h`、`Dma.h` 与 `Kernel.h`。 | 运行 `test_include_api_public_headers_compile_together`。 | C++ compile-only 成功，调用方可读取公开类型与 no-op sink。 | `test_include_api_public_headers_compile_together` |
| TC-INCLUDE-API-TRANCE-005 | 公开入口 | `include/api/Trance.h` no-op runtime 边界可直接运行。 | 只 include `include/api/Trance.h`，不传 `-DTRANCE`。 | 运行 `test_include_api_trance_noop_public_runtime_boundary`。 | 程序成功运行且 stdout 为空。 | `test_include_api_trance_noop_public_runtime_boundary` |
| TC-INCLUDE-API-TRANCE-006 | 并发边界 | 当前线程建立文件 sink 后，未建 scope 的其它线程调用 `current_sink()`。 | include `include/npu_demo/Trance.h`，传 `-DTRANCE` 与有效 `KG_TRANCE_FILE_PATH`，用 `std::thread` 在其它线程写入。 | 运行 `test_npu_demo_scoped_sink_does_not_cross_thread`。 | owner 线程输出写入 trace 文件；observer 线程输出写入 stdout，trace 文件不包含 observer 行。 | `test_npu_demo_scoped_sink_does_not_cross_thread` |
