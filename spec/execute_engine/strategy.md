# strategy.md

## 功能简介

- 定义 `ExecutionEngine.compile(...)` 的 compile strategy 扩展合同。
- 内置 `cpu` / `npu_demo` strategy 保持既有真实编译行为。
- 第三方 target 可通过公开 registry 注册 compile strategy；缺失时公开失败，不得 fallback 到 CPU。

## API 列表

- `class CompileStrategy(Protocol)`
- `CompileStrategy.compile(self, request: CompileRequest) -> CompiledKernel`
- `register_compile_strategy(target: str, strategy: CompileStrategy, *, override: bool = False) -> None`
- `get_compile_strategy(target: str) -> CompileStrategy`
- `ExecutionEngine.compile(source: str | None = None, function: str | None = None, *, request: CompileRequest | None = None, entry_point: str = "kg_execute_entry") -> CompiledKernel`
- `CompiledKernel.execute(args: tuple[RuntimeInput, ...] | None = None, *, request: ExecuteRequest | None = None, entry_point: str | None = None, capture_function_output: bool = False, stream: None = None) -> ExecuteResult`

## 文档信息

- `spec`：`spec/execute_engine/strategy.md`
- `功能实现`：`kernel_gen/execute_engine/compiler.py`
- `功能实现`：`kernel_gen/execute_engine/__init__.py`
- `test`：`test/execute_engine/test_compile_strategy.py`
- `test`：`test/execute_engine/test_contract.py`

## 依赖

- [`spec/execute_engine/execute_engine.md`](execute_engine.md)
- [`spec/target/registry.md`](../target/registry.md)
- [`spec/dsl/gen_kernel/source_bundle.md`](../dsl/gen_kernel/source_bundle.md)

## 目标

- 保持 `ExecutionEngine.compile(...)` 公开签名不变。
- 让 compile behavior 通过 target strategy 扩展。
- 给 compile-only backend 提供稳定运行失败短语 `execution_unsupported`。

## 模块边界

- `target` 必须已通过公开 target registry 注册。
- `strategy` 必须实现 `compile(request: CompileRequest) -> CompiledKernel`。
- `override=False` 时重复注册同一 target 必须失败，错误文本包含 `duplicate compile strategy`。
- `get_compile_strategy(target)` 找不到 strategy 时必须以 `target_header_mismatch` 失败，错误文本包含 `missing compile strategy`。
- `ExecutionEngine.compile(request=...)` 与 `source` 或 `function` 混用时必须以 `source_empty_or_invalid` 失败，错误文本包含 `request cannot be combined with source or function`。
- `CompiledKernel.execute(...)` 对 `target` 不在 `cpu` / `npu_demo` 的 compile-only kernel 必须以 `execution_unsupported` 失败。
- SourceBundle decode/write helper 不公开；strategy 可自行消费 aggregate string，但不得新增公开 helper。

## API详细说明

### `class CompileStrategy(Protocol)`

- 参数：无构造参数合同。
- 返回值：实现 `compile(...)` 的 strategy 对象。
- 功能说明：定义 compile strategy 的公开协议。
- 使用示例：

  ```python
  from kernel_gen.execute_engine import CompileRequest, CompiledKernel, CompileStrategy

  class DummyStrategy:
      def compile(self, request: CompileRequest) -> CompiledKernel:
          return CompiledKernel(request.target, "/tmp/dummy.so", request.function, request.entry_point)
  ```
- 注意事项：协议只定义 `compile(...)` 方法；strategy 内部 workspace、缓存和 helper 不公开。

### `CompileStrategy.compile(self, request: CompileRequest) -> CompiledKernel`

- 参数：
  - `request`：公开 compile 请求，包含 target、source、function、entry_point、compiler 配置和 dump_dir。
- 返回值：`CompiledKernel`。
- 功能说明：把 `CompileRequest` 转换为可执行或 compile-only 的 kernel 产物。
- 使用示例：

  ```python
  kernel = strategy.compile(request)
  ```
- 注意事项：strategy 必须返回 `CompiledKernel`；非法输入按 `KernelCodeError` 公开错误处理。

### `register_compile_strategy(target: str, strategy: CompileStrategy, *, override: bool = False) -> None`

- 参数：
  - `target`：target 名称；必须已通过 target registry 注册。
  - `strategy`：实现 `CompileStrategy` 协议的对象。
  - `override`：是否覆盖已有 strategy；默认 `False`。
- 返回值：无。
- 功能说明：注册 target 对应 compile strategy。
- 使用示例：

  ```python
  from kernel_gen.execute_engine import register_compile_strategy

  register_compile_strategy("dummy_generic", DummyStrategy())
  ```
- 注意事项：重复注册默认失败；`override=True` 才允许覆盖。

### `get_compile_strategy(target: str) -> CompileStrategy`

- 参数：
  - `target`：target 名称；必须已通过 target registry 注册。
- 返回值：已注册 compile strategy。
- 功能说明：查询 target 对应 compile strategy。
- 使用示例：

  ```python
  from kernel_gen.execute_engine import get_compile_strategy

  strategy = get_compile_strategy("dummy_generic")
  ```
- 注意事项：未注册 target 或缺失 strategy 不得 fallback 到 CPU。

### `ExecutionEngine.compile(source: str | None = None, function: str | None = None, *, request: CompileRequest | None = None, entry_point: str = "kg_execute_entry") -> CompiledKernel`

- 参数：
  - `source`：源码字符串；使用 `request` 时必须为 `None`；混用时必须以 `source_empty_or_invalid` 失败。
  - `function`：函数名；使用 `request` 时必须为 `None`；混用时必须以 `source_empty_or_invalid` 失败。
  - `request`：完整 compile 请求；为 `None` 时由 `source`、`function` 和 engine 配置构造。
  - `entry_point`：C ABI 入口名；默认 `"kg_execute_entry"`。
- 返回值：`CompiledKernel`。
- 功能说明：归一化 compile 请求后交给当前 target 的 compile strategy。
- 使用示例：

  ```python
  from kernel_gen.execute_engine import ExecutionEngine

  kernel = ExecutionEngine(target="dummy_generic").compile(source="void dummy() {}\\n", function="dummy")
  ```
- 注意事项：公开签名保持不变；strategy 缺失必须失败，不得 fallback；`request` 非 `None` 时不得同时提供 `source` 或 `function`。

### `CompiledKernel.execute(args: tuple[RuntimeInput, ...] | None = None, *, request: ExecuteRequest | None = None, entry_point: str | None = None, capture_function_output: bool = False, stream: None = None) -> ExecuteResult`

- 参数：
  - `args`：运行时实参序列。
  - `request`：完整 execute 请求；为 `None` 时由其它参数构造。
  - `entry_point`：覆盖 kernel 默认入口名。
  - `capture_function_output`：是否捕获函数返回值。
  - `stream`：流对象；本阶段不支持。
- 返回值：`ExecuteResult`。
- 功能说明：执行已编译 kernel；compile-only target 返回稳定失败。
- 使用示例：

  ```python
  result = kernel.execute(args=())
  ```
- 注意事项：`target` 不在 `cpu` / `npu_demo` 时必须抛出 `KernelCodeError`，`failure_phrase == "execution_unsupported"`。

## 测试

- 测试文件：`test/execute_engine/test_compile_strategy.py`
- 测试文件：`test/execute_engine/test_contract.py`
- 执行命令：`pytest -q test/execute_engine/test_compile_strategy.py test/execute_engine/test_contract.py`

### 测试目标

- 验证 compile strategy 注册、重复注册、查询和缺失错误。
- 验证 `ExecutionEngine.compile(...)` 分发到 target strategy。
- 验证 compile-only target 的 execute 失败短语。
- 验证 execute_engine 包根公开 API 列表包含 strategy API。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TG-STRATEGY-001 | 注册边界 | 重复注册默认失败。 | target 已注册且已有 strategy。 | 再次注册同一 target。 | 抛出 `duplicate compile strategy`。 | `test_compile_strategy_registry_duplicate_requires_override` |
| TG-STRATEGY-002 | 错误语义 | target 缺失 strategy。 | target 已注册但没有 strategy。 | 调用 `ExecutionEngine(target).compile(...)`。 | 失败短语为 `target_header_mismatch`，文本包含 `missing compile strategy`。 | `test_compile_strategy_missing_target_does_not_fallback_to_cpu` |
| TG-STRATEGY-003 | compile-only | dummy backend 单文件源码。 | dummy backend 已加载。 | 编译并执行。 | 编译成功；执行失败短语为 `execution_unsupported`。 | `test_dummy_compile_strategy_writes_single_source_and_is_compile_only` |
| TG-STRATEGY-004 | SourceBundle | dummy backend 多文件源码。 | dummy backend 已加载，设置 `dump_dir`。 | 编译 SourceBundle。 | 写出 aggregate 与 artifact 文件。 | `test_dummy_compile_strategy_writes_source_bundle_artifacts` |
| TG-STRATEGY-005 | 错误语义 | `request` 与 `source` 或 `function` 混用。 | target 已注册且 strategy 已注册；准备完整 `CompileRequest`。 | 调用 `ExecutionEngine(target).compile(source=..., request=...)` 或 `compile(function=..., request=...)`。 | 抛出 `KernelCodeError`，`failure_phrase == "source_empty_or_invalid"`，文本包含 `request cannot be combined with source or function`。 | `test_compile_request_rejects_source_or_function_mix` |
