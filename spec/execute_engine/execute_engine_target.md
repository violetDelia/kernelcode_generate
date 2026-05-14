# execute_engine_target.md

## 功能简介

- 定义执行引擎 `P0` 的 `target` 选择、target 专属 `include` 注入与 `entry shim` 合同。
- 冻结 `entry_point` 命名、`ordered_args` 绑定顺序、编译器默认值与 flags 追加策略，使 `compile -> execute` 在不同 target 下保持机械一致。
- 本文档覆盖 target include、entry shim 与 compiler 三类职责，统一由 `kernel_gen/execute_engine/compiler.py` 承接实现。
- runtime trance kernel log 的编译期宏由 `kernel_gen.core.config.set_trance_enabled(...)` 控制；`ExecutionEngine.compile(...)` 不新增同义入参。

## API 列表

- 本文档不新增独立公开 API；target/include/entry shim 行为由 `ExecutionEngine.compile(...)` 承接。

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/execute_engine/execute_engine_target.md`](spec/execute_engine/execute_engine_target.md)
- `功能实现`：[`kernel_gen/execute_engine/compiler.py`](kernel_gen/execute_engine/compiler.py)
- `test`：[`test/execute_engine/test_compile.py`](test/execute_engine/test_compile.py)、[`test/execute_engine/test_invoke.py`](test/execute_engine/test_invoke.py)、[`test/execute_engine/test_contract.py`](test/execute_engine/test_contract.py)

## 依赖

- 执行引擎总览合同：[`spec/execute_engine/execute_engine.md`](spec/execute_engine/execute_engine.md)
- 请求/结果/参数模型：[`spec/execute_engine/execute_engine_api.md`](spec/execute_engine/execute_engine_api.md)
- `emit_c` 输出语义：[`spec/dsl/gen_kernel/emit.md`](spec/dsl/gen_kernel/emit.md)

## 术语

- `target include set`：某个 `target` 在编译阶段必须注入并保持一致的头文件集合。
- `entry shim`：为 C++ 符号或模板/重载函数补齐稳定 `extern "C"` 入口的适配层。
- `ordered_args`：按目标函数形参顺序排列的 内部 ABI 槽位数组。

## 目标

- 冻结 `target=cpu` 与 `target=npu_demo` 的 include 注入结果。
- 冻结 `entry_point` 默认名、`entry shim` C ABI 签名与省略条件。
- 冻结从函数形参到 `ordered_args` 的顺序绑定规则。
- 冻结编译器默认值与 flags 追加规则，避免不同 target 下的隐式回退。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- `P0` 内置 include 注入与真实执行仅支持 `target in {"cpu", "npu_demo"}`；第三方 target 必须通过 [`spec/execute_engine/strategy.md`](strategy.md) 的 compile strategy 扩展，不得复用 CPU include 注入作为 fallback。
- `target` 选择只由 `CompileRequest.target` 驱动；不得因为源码内容自动切换到另一 target。
- `target=npu_demo` 不允许以注入 `cpu` include 或回退调用 `cpu::*` 的方式完成编译。
- `entry shim` 只负责统一入口与参数绑定；不改变 `function` 本身的数学语义与参数顺序。
- `ordered_args` 绑定顺序必须与目标函数形参顺序严格一致；不得重排、推断或按名称重新排序。
- 本文档只冻结 target/include/entry shim 合同；`stream`、输出回收与运行时参数类型校验沿用 [`spec/execute_engine/execute_engine.md`](spec/execute_engine/execute_engine.md) 与 [`spec/execute_engine/execute_engine_api.md`](spec/execute_engine/execute_engine_api.md)。
### 内部编译行为

- `ExecutionEngine.compile(...)` 根据 `CompileRequest.target` 选择 target include set。
- `target="npu_demo"` 时只能注入 `#include "include/npu_demo/npu_demo.h"`。
- `target="cpu"` 时必须同时注入 `#include "include/cpu/Memory.h"` 与 `#include "include/cpu/Nn.h"`。
- 当 `compiler is None` 时，编译命令使用 `g++`。
- 编译 flags 必须保留 `-std=c++17` 基线，并按调用方顺序追加 `CompileRequest.compiler_flags`。
- entry shim 仅作为内部桥接逻辑：源码未提供同名 `extern "C"` 入口时，内部生成稳定 C ABI 入口；源码已提供同名入口时可省略。
- `ordered_args` 是内部 ABI 槽位，不作为 Python 公开 API；执行侧只接收 `tuple[RuntimeInput, ...]` 运行时参数。
- `target="npu_demo"` entry shim 的函数形参解析必须把 `S_INT` 视为整数标量参数槽位，与 `int` / `long` / `int64_t` 等整型形参按同一 `ordered_args` 顺序绑定。
- `target="npu_demo"` entry shim 解析到 `template <typename Tn>` 与 `Memory<Space, Tn>&` 形参时，内部 `_ArgSlot` 必须携带 runtime dtype code，并根据源码中 concrete `Memory<..., dtype>` 的 dtype 生成唯一 concrete `Memory<Space, dtype>` 绑定后调用 `function<dtype...>(...)`。
- 若手写 templated source 只有 `Memory<Space, Tn>&` 形参而缺少任何 concrete `Memory<..., dtype>` 实例线索，`ExecutionEngine.compile(...)` 必须以 `template_instance_required` 稳定失败；不得默认实例化为 `float`。
- 该 template shim 不新增 `TemplateBinding`、`template_bindings` 或其它公开 compile 参数；runtime dtype 必须匹配该唯一 concrete 实例，非匹配 dtype 必须由 entry shim 返回失败码，不生成全组合 dispatcher。
- 非 templated memory 参数继续按源码中的真实 dtype 绑定；template name 不得用于 memory size、shape、stride、cast 或 alignment 判定。
- 编译器启动失败、返回非零或编译命令无法生成可执行产物时，必须失败并返回 `compile_failed`。
- `entry_point` 或导出符号无法解析时，必须失败并返回 `symbol_resolve_failed`。
- `ordered_args` 数量或顺序与目标函数形参不一致导致执行失败时，必须返回 `runtime_throw_or_abort`。
### runtime trance 编译行为

- `kernel_gen.core.config.get_trance_enabled() == False` 时，编译命令不得追加 `TRANCE`、`KG_TRANCE_KERNEL_NAME` 或 `KG_TRANCE_FILE_PATH` 宏。
- `kernel_gen.core.config.get_trance_enabled() == True` 时，编译命令必须追加 `-DTRANCE`、`-DKG_TRANCE_KERNEL_NAME="<kernel_name>"` 与 `-DKG_TRANCE_FILE_PATH="<trace_path>"`。
- `kernel_name` 来自 `ExecutionEngine.compile(..., function=...)` 的短名，去掉 `::` 命名空间前缀后做文件名安全化；空结果回退为 `kernel`。
- `dump_dir is None` 时 `KG_TRANCE_FILE_PATH` 必须为空字符串，运行期由 stdout sink 输出；`dump_dir` 非空时 trace 文件路径为 `dump_dir/<kernel_name>_trace.txt`。
- entry shim 在 `TRANCE` 开启时负责建立 `ScopedTranceSink`，先输出 `in func: <kernel_name> template=<none>`，再输出 `args =` 和按 `ordered_args` 顺序排列的参数行。
- Memory 参数行必须委托 `Memory::trance_print(...)` 输出；整型与浮点参数使用 `kernelcode::trance::print_value_arg(...)` 输出。
- runtime trance 只新增诊断输出，不改变目标函数调用顺序、实参绑定、返回码或失败短语。

## API详细说明

本文档不定义独立 API 详细条目。`target`、include 注入、entry shim 与 `ordered_args` 绑定属于 `ExecutionEngine.compile(...)` 的行为约束；参数、返回值和调用示例由 [`spec/execute_engine/execute_engine.md`](spec/execute_engine/execute_engine.md) 与 [`spec/execute_engine/execute_engine_api.md`](spec/execute_engine/execute_engine_api.md) 承接。

## 测试

- 测试文件：
  - `test/execute_engine/test_compile.py`
  - `test/execute_engine/test_contract.py`
  - `test/execute_engine/test_invoke.py`
- 执行命令：
  - `pytest -q test/execute_engine/test_compile.py`
  - `pytest -q test/execute_engine/test_invoke.py`
  - `pytest -q test/execute_engine/test_contract.py`

### 测试目标

- 验证 `spec/execute_engine/execute_engine_target.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。
- 验证 Memory/DMA 参数、布局、搬运或 verifier 行为。
- 验证 DSL、IR 或 EmitC 生成文本与编译链路符合公开合同。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-001 | 公开入口 | `target=npu_demo` 注入 `include/npu_demo/npu_demo.h`，且不回退到 `cpu` include。 | 使用固定种子矩阵准备 `npu_demo` 与 `cpu` 编译源码。 | 运行 `test_execute_engine_compile_target_include_and_entry_shim_matrix`。 | `npu_demo` 编译单元只注入 npu include，且不混入 cpu include。 | `test_execute_engine_compile_target_include_and_entry_shim_matrix` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-002 | 内存/DMA | `target=cpu` 同时注入 `include/cpu/Memory.h` 与 `include/cpu/Nn.h`。 | 使用固定种子矩阵准备缺失或已存在 include 的 `cpu` 源码。 | 运行 `test_execute_engine_compile_target_include_and_entry_shim_matrix`。 | `cpu` 编译单元补齐 Memory/Nn include，且不会重复注入同一 include。 | `test_execute_engine_compile_target_include_and_entry_shim_matrix` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-003 | 生成/编译 | `compiler=None` 时使用 `g++`，并保留 `-std=c++17` 基线。 | 准备公开 `ExecutionEngine.compile(...)` 成功路径。 | 运行 `test_execute_engine_compile_returns_kernel_with_command`。 | 编译命令使用 `g++`，包含 `-std=c++17` 与仓库 include 路径。 | `test_execute_engine_compile_returns_kernel_with_command` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-004 | 生成/编译 | 默认 `entry_point=kg_execute_entry`，且 `ExecuteRequest.entry_point=None` 使用编译产物中的入口名。 | 使用固定种子矩阵准备缺失 entry 与已有 entry 的源码。 | 运行 `test_execute_engine_compile_target_include_and_entry_shim_matrix` 与 `test_execute_engine_invoke_real_entry_runtime_arg_matrix`。 | 缺失 entry 时注入 shim；已有同名 entry 时省略 shim；执行默认入口成功。 | `test_execute_engine_compile_target_include_and_entry_shim_matrix`, `test_execute_engine_invoke_real_entry_runtime_arg_matrix` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-005 | 生成/编译 | 源码已提供同名同签名 `extern "C"` 入口时可省略 `entry shim`。 | 使用固定种子矩阵准备已提供 `kg_execute_entry` 的 `cpu`/`npu_demo` 源码。 | 运行 `test_execute_engine_compile_target_include_and_entry_shim_matrix`。 | 编译单元不再生成额外 runtime entry shim。 | `test_execute_engine_compile_target_include_and_entry_shim_matrix` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-006 | 边界/异常 | target/include family 不一致时返回 `target_header_mismatch`。 | 使用固定种子矩阵准备混合 include 与 target 不匹配源码。 | 运行 `test_execute_engine_compile_failure_phrase_matrix`。 | include family 与 target 不一致时稳定返回 `target_header_mismatch`。 | `test_execute_engine_compile_failure_phrase_matrix` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-007 | 边界/异常 | 导出入口无法解析时返回 `symbol_resolve_failed`。 | 使用固定种子矩阵准备空 entry 与公开 `CompiledKernel` 加载失败边界。 | 运行 `test_execute_engine_compile_failure_phrase_matrix` 与 `test_execute_engine_invoke_public_soname_load_failure_matrix`。 | 空 entry 返回 `symbol_resolve_failed`；非法 shared object 的入口解析失败也返回该短语。 | `test_execute_engine_compile_failure_phrase_matrix`, `test_execute_engine_invoke_public_soname_load_failure_matrix` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-008 | 生成/编译 | npu_demo entry shim 绑定 `S_INT` 标量形参。 | 准备包含 `S_INT` 形参的 npu_demo 源码和整数 runtime arg。 | 运行 `test_execute_engine_compile_unit_binds_npu_demo_s_int_arg`。 | entry shim 生成的 C ABI 入口按函数形参顺序绑定 `S_INT` 参数，编译成功。 | `test_execute_engine_compile_unit_binds_npu_demo_s_int_arg` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-009 | 生成/编译 | entry shim 按 memory/int/float/KernelContext 形参顺序生成 runtime 绑定源码。 | 通过公开 `ExecutionEngine.compile(...)` 编译含 `KernelContext`、`Memory`、整型与浮点形参的源码。 | 运行 `test_execute_engine_compile_entry_shim_public_param_matrix`。 | 生成的编译单元包含默认 `KernelContext`、runtime 参数个数校验、memory/int/float 参数转换与顺序调用。 | `test_execute_engine_compile_entry_shim_public_param_matrix` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-010 | 生成/编译 | 目标函数形参不可解析时生成稳定占位 entry shim。 | 通过公开 `ExecutionEngine.compile(...)` 编译含未支持形参类型的源码。 | 运行 `test_execute_engine_compile_entry_shim_placeholder_for_unsupported_params`。 | 编译单元包含占位 `kg_execute_entry`，并保持 `ordered_args/arg_count` 消费与 `return 0` 兼容行为。 | `test_execute_engine_compile_entry_shim_placeholder_for_unsupported_params` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-011 | 生成/编译 | runtime trance 编译宏由 core config 注入。 | 调用 `set_trance_enabled(True)` 与 `set_dump_dir(tmp_path)` 后通过公开 `ExecutionEngine.compile(...)` 编译。 | 运行 `test_execute_engine_compile_injects_trance_macros_from_core_config`。 | 编译命令包含 `-DTRANCE`、`KG_TRANCE_KERNEL_NAME` 与 `KG_TRANCE_FILE_PATH`，关闭时不出现这些宏。 | `test_execute_engine_compile_injects_trance_macros_from_core_config` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-012 | 执行结果 | runtime trance 字符串宏在真实 npu_demo 编译执行路径可用。 | 使用 `target="npu_demo"`、无参数 kernel、`trance_enabled=True` 和非空 `dump_dir`。 | 运行 `test_execute_engine_compile_trance_file_sink_runs_on_npu_demo`。 | 真实执行成功，trace 文件包含 `in func: <kernel> template=<none>` 与 `args =`。 | `test_execute_engine_compile_trance_file_sink_runs_on_npu_demo` |
