# execute_engine_target.md

## 功能简介

- 定义执行引擎 `P0` 的 `target` 选择、target 专属 `include` 注入、`SourceBundle` artifact 写出与 `entry shim` 合同。
- 冻结 `entry_point` 命名、`ordered_args` 绑定顺序、编译器默认值与 flags 追加策略，使 `compile -> execute` 在不同 target 下保持机械一致。
- 本文档覆盖 target include、entry shim 与 compiler 三类职责；公开入口和 `CompiledKernel` 装配由 `kernel_gen/execute_engine/compiler.py` 承接，内置 target 支持实现由 `kernel_gen/execute_engine/builtin_strategy/` package 承接。
- runtime trance kernel log 的编译期宏由 `kernel_gen.core.config.set_trance_enabled(...)` 控制；`ExecutionEngine.compile(...)` 不新增同义入参。

## API 列表

- 本文档不新增独立公开 API；target/include/entry shim 行为由 `ExecutionEngine.compile(...)` 承接。

## 文档信息

- `spec`：[`spec/execute_engine/execute_engine_target.md`](spec/execute_engine/execute_engine_target.md)
- `功能实现`：[`kernel_gen/execute_engine/compiler.py`](kernel_gen/execute_engine/compiler.py)
- `功能实现`：[`kernel_gen/execute_engine/strategy.py`](kernel_gen/execute_engine/strategy.py)
- `功能实现`：[`kernel_gen/execute_engine/builtin_strategy/__init__.py`](kernel_gen/execute_engine/builtin_strategy/__init__.py)
- `功能实现`：[`kernel_gen/execute_engine/builtin_strategy/cpu.py`](kernel_gen/execute_engine/builtin_strategy/cpu.py)
- `功能实现`：[`kernel_gen/execute_engine/builtin_strategy/npu_demo.py`](kernel_gen/execute_engine/builtin_strategy/npu_demo.py)
- `功能实现`：[`kernel_gen/execute_engine/builtin_strategy/cuda_sm86.py`](kernel_gen/execute_engine/builtin_strategy/cuda_sm86.py)
- `功能实现`：[`kernel_gen/execute_engine/runtime_args.py`](kernel_gen/execute_engine/runtime_args.py)
- `test`：[`test/execute_engine/test_compile.py`](test/execute_engine/test_compile.py)、[`test/execute_engine/test_builtin_strategy.py`](test/execute_engine/test_builtin_strategy.py)、[`test/execute_engine/test_invoke.py`](test/execute_engine/test_invoke.py)、[`test/execute_engine/test_contract.py`](test/execute_engine/test_contract.py)

## 依赖

- 执行引擎总览合同：[`spec/execute_engine/execute_engine.md`](spec/execute_engine/execute_engine.md)
- 请求/结果/参数模型：[`spec/execute_engine/execute_engine_api.md`](spec/execute_engine/execute_engine_api.md)
- `emit_c` 输出语义：[`spec/dsl/gen_kernel/emit.md`](spec/dsl/gen_kernel/emit.md)
- CUDA SM86 include runtime：[`spec/include/cuda_sm86/cuda_sm86.md`](../include/cuda_sm86/cuda_sm86.md)

## 术语

- `target include set`：某个 `target` 在编译阶段必须注入并保持一致的头文件集合。
- `entry shim`：为 C++ 符号或模板/重载函数补齐稳定 `extern "C"` 入口的适配层。
- `ordered_args`：按目标函数形参顺序排列的 内部 ABI 槽位数组。

## 目标

- 冻结 `target=cpu`、`target=npu_demo` 与 `target=cuda_sm86` 的 include 注入结果。
- 冻结 `entry_point` 默认名、`entry shim` C ABI 签名与省略条件。
- 冻结从函数形参到 `ordered_args` 的顺序绑定规则。
- 冻结编译器默认值与 flags 追加规则，避免不同 target 下的隐式回退。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- `P0` 内置 include 注入与真实执行仅支持 `target in {"cpu", "npu_demo", "cuda_sm86"}`；第三方 target 必须通过 [`spec/execute_engine/strategy.md`](strategy.md) 的 compile strategy 扩展，不得复用 CPU include 注入作为 fallback。
- `target` 选择只由 `CompileRequest.target` 驱动；不得因为源码内容自动切换到另一 target。
- `target=npu_demo` 不允许以注入 `cpu` include 或回退调用 `cpu::*` 的方式完成编译。
- `target=cuda_sm86` 不允许以注入 `cpu` / `npu_demo` include、回退调用 `cpu::*` / `npu_demo::*` 或普通 C++ compiler 替代 `nvcc` 的方式完成默认编译。
- `entry shim` 只负责统一入口与参数绑定；不改变 `function` 本身的数学语义与参数顺序。
- `target="npu_demo"` 且目标函数末尾参数为 `std::string&` cost summary sink 时，compile unit 必须生成 `<entry_point>_capture` companion；该 companion 调用目标函数并把 summary string 写入调用方提供的 UTF-8 输出 buffer。
- `ordered_args` 绑定顺序必须与目标函数形参顺序严格一致；不得重排、推断或按名称重新排序。
- 本文档只冻结 target/include/entry shim 合同；`stream`、输出回收与运行时参数类型校验沿用 [`spec/execute_engine/execute_engine.md`](spec/execute_engine/execute_engine.md) 与 [`spec/execute_engine/execute_engine_api.md`](spec/execute_engine/execute_engine_api.md)。
### 内部编译行为

- `ExecutionEngine.compile(...)` 根据 `CompileRequest.target` 选择 compile strategy；内置 `cpu` / `npu_demo` / `cuda_sm86` strategy 由 `builtin_strategy/` package 选择 target include set 并生成编译产物。
- `target="npu_demo"` 时只能注入 `#include "include/npu_demo/npu_demo.h"`。
- `target="cpu"` 时必须同时注入 `#include "include/cpu/Memory.h"` 与 `#include "include/cpu/Nn.h"`。
- `target="cuda_sm86"` 时只能注入 `#include "include/cuda_sm86/cuda_sm86.cuh"`。
- 当 `compiler is None` 时，`cpu` / `npu_demo` 编译命令使用 `g++`，`cuda_sm86` 编译命令使用 `nvcc`。
- 编译 flags 必须保留 `-std=c++17` 基线，并按调用方顺序追加 `CompileRequest.compiler_flags`。
- `cuda_sm86` 在调用方未显式提供 CUDA 必需 flags 时必须附加 `-arch=sm_86`、`-shared`、`-Xcompiler`、`-fPIC`，并输出 `.so` shared object。
- `cuda_sm86` 编译策略必须消费公开 `SourceBundle` aggregate string，把 bundle marker 展开为真实 `.cu/.cuh` artifact 后编译主 `.cu`；不得把 aggregate marker 原文直接交给 `nvcc` 作为唯一源码。
- entry shim 仅作为内部桥接逻辑：源码未提供同名 `extern "C"` 入口时，内部生成稳定 C ABI 入口；源码已提供同名入口时可省略。
- `ordered_args` 是内部 ABI 槽位，不作为 Python 公开 API；执行侧只接收 `tuple[RuntimeInput, ...]` 运行时参数。
- 内置 target 编译产物结构、include 注入、entry shim 与真实编译 helper 均为 `builtin_strategy/` package 内实现，不进入 `kernel_gen.execute_engine` 包根公开 API；调用方不得依赖这些 helper 或 `cpu` / `npu_demo` / `cuda_sm86` 子模块作为第三方扩展点。
- `target="npu_demo"` entry shim 的函数形参解析必须把 `S_INT` 视为整数标量参数槽位，与 `int` / `long` / `int64_t` 等整型形参按同一 `ordered_args` 顺序绑定。
- `target="npu_demo"` entry shim 的函数形参解析必须把末尾 `std::string&` 识别为 cost summary sink，不占用 runtime `ordered_args` 槽位；普通 `kg_execute_entry` 可保持占位或非 capture 执行语义，`kg_execute_entry_capture` 必须创建本地 `std::string`、调用目标函数、复制文本并写回 `output_size`。
- capture companion 缺失时，`CompiledKernel.execute(..., capture_function_output=True)` 必须以 `function_output_capture_not_supported` 失败；companion 返回非零或输出超过容量必须映射到 `runtime_throw_or_abort`。
- `target="npu_demo"` entry shim 解析到 `template <typename Tn>` 与 `Memory<Space, Tn>&` 形参时，内部 `_ArgSlot` 必须携带 runtime dtype code，并根据 `gen_kernel` 生成源码中的 `__kernel_gen_template_instance_seed_*` alias 或源码中 concrete `Memory<..., dtype>` 的 dtype 生成唯一 concrete `Memory<Space, dtype>` 绑定后调用 `function<dtype...>(...)`。
- 若手写 templated source 只有 `Memory<Space, Tn>&` 形参而缺少任何 concrete `Memory<..., dtype>` 实例线索，`ExecutionEngine.compile(...)` 必须以 `template_instance_required` 稳定失败；不得默认实例化为 `float`。
- 该 template shim 不新增 `TemplateBinding`、`template_bindings` 或其它公开 compile 参数；runtime dtype 必须匹配该唯一 concrete 实例，非匹配 dtype 必须由 entry shim 返回失败码，不生成全组合 dispatcher。
- 非 templated memory 参数继续按源码中的真实 dtype 绑定；template name 不得用于 memory size、shape、stride、cast 或 alignment 判定。
- 编译器启动失败、返回非零或编译命令无法生成可执行产物时，必须失败并返回 `compile_failed`。
- `entry_point` 或导出符号无法解析时，必须失败并返回 `symbol_resolve_failed`。
- `ordered_args` 数量或顺序与目标函数形参不一致导致执行失败时，必须返回 `runtime_throw_or_abort`。
- `cuda_sm86` 使用既有 `kg_execute_entry(slots, count)` C ABI；`slots` 布局由 `include/cuda_sm86/cuda_sm86.cuh` 的 `cuda_sm86::ArgSlot` 承接。
- `cuda_sm86` 当前不支持非 `None` stream；`CompiledKernel.execute(..., stream=<non-none>)` 必须以 `stream_not_supported` 稳定失败，文本包含 `cuda_sm86 does not support non-None stream`。
- `nvcc` 缺失、返回非零或未生成 `.so` 时必须以 `compile_failed` 稳定失败；文本包含 `nvcc failed` 或 `compiler not found` 摘要。
- CUDA 运行时错误必须收敛到既有 `runtime_throw_or_abort` failure phrase，detail 文本包含 `cuda_runtime_failed`，不得新增公开 failure phrase。
### runtime trance 编译行为

- `kernel_gen.core.config.get_trance_enabled() == False` 时，编译命令不得追加 `TRANCE`、`KG_TRANCE_KERNEL_NAME`、`KG_TRANCE_DIR_PATH` 或 `KG_TRANCE_FILE_PATH` 宏。
- `kernel_gen.core.config.get_trance_enabled() == True` 时，编译命令必须追加 `-DTRANCE`、`-DKG_TRANCE_KERNEL_NAME="<kernel_name>"`、`-DKG_TRANCE_DIR_PATH="<trace_dir>"` 与 `-DKG_TRANCE_FILE_PATH=""`。
- `kernel_name` 来自 `ExecutionEngine.compile(..., function=...)` 的短名，去掉 `::` 命名空间前缀后做文件名安全化；空结果回退为 `kernel`。
- `dump_dir is None` 时 `KG_TRANCE_DIR_PATH` 与 `KG_TRANCE_FILE_PATH` 必须为空字符串，运行期由 stdout sink 输出；`dump_dir` 非空时 trace 目录路径为 `dump_dir/<kernel_name>/trance`，该路径由 `kernel_gen.core.tools.dump_dir.DumpDirWriter` 派生，最终文本不得再生成旧 `dump_dir/<kernel_name>_trace.txt`。
- entry shim 在 `TRANCE` 开启且 `KG_TRANCE_DIR_PATH` 为空时负责建立 `ScopedTranceSink`，先输出 `in func: <kernel_name> template=<none>`，再输出 `args =` 和按 `ordered_args` 顺序排列的参数行；`KG_TRANCE_DIR_PATH` 非空时顶层 shim 不得输出 stdout 或旧单文件 trace，block 文件日志由 `npu_demo::launch` 承接。
- Memory 参数行必须委托 `Memory::trance_print(...)` 输出；整型与浮点参数使用 `kernelcode::trance::print_value_arg(...)` 输出。
- runtime trance 只新增诊断输出，不改变目标函数调用顺序、实参绑定、返回码或失败短语。

## API详细说明

本文档不定义独立 API 详细条目。`target`、include 注入、entry shim 与 `ordered_args` 绑定属于 `ExecutionEngine.compile(...)` 的行为约束；参数、返回值和调用示例由 [`spec/execute_engine/execute_engine.md`](spec/execute_engine/execute_engine.md) 与 [`spec/execute_engine/execute_engine_api.md`](spec/execute_engine/execute_engine_api.md) 承接。

## 测试

- 测试文件：
  - `test/execute_engine/test_compile.py`
  - `test/execute_engine/test_builtin_strategy.py`
  - `test/execute_engine/test_contract.py`
  - `test/execute_engine/test_invoke.py`
  - `test/execute_engine/test_cuda_sm86_strategy.py`
  - `test/cuda/test_cuda_sm86_kernel_demos_runtime.py`
- 执行命令：
  - `pytest -q test/execute_engine/test_compile.py test/execute_engine/test_builtin_strategy.py`
  - `pytest -q test/execute_engine/test_invoke.py`
  - `pytest -q test/execute_engine/test_contract.py`
  - `pytest -q test/execute_engine/test_cuda_sm86_strategy.py`
  - `pytest -q test/cuda/test_cuda_sm86_kernel_demos_runtime.py -m cuda`

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
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-011 | 生成/编译 | runtime trance 编译宏由 core config 注入。 | 调用 `set_trance_enabled(True)` 与 `set_dump_dir(tmp_path)` 后通过公开 `ExecutionEngine.compile(...)` 编译。 | 运行 `test_execute_engine_compile_injects_trance_macros_from_core_config`。 | 编译命令包含 `-DTRANCE`、`KG_TRANCE_KERNEL_NAME`、`KG_TRANCE_DIR_PATH` 与空 `KG_TRANCE_FILE_PATH`，关闭时不出现这些宏。 | `test_execute_engine_compile_injects_trance_macros_from_core_config` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-012 | 执行结果 | runtime trance block 目录宏在真实 npu_demo 编译执行路径可用。 | 使用 `target="npu_demo"`、调用 `launch<2, 1, 1, 0>` 的 kernel、`trance_enabled=True` 和非空 `dump_dir`。 | 运行 `test_execute_engine_compile_trance_block_sink_runs_on_npu_demo`。 | 真实执行成功，`dump_dir/<kernel>/trance/block_0000.log` 与 `block_0001.log` 包含 launch 日志，旧 `<kernel>_trace.txt` 不存在。 | `test_execute_engine_compile_trance_block_sink_runs_on_npu_demo` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-012A | 执行结果 | npu_demo cost summary capture companion。 | 使用 `target="npu_demo"` 编译末尾带 `std::string&` summary sink 的源码。 | 运行 `test_execute_engine_npu_demo_capture_function_output_returns_run_stdout`。 | 编译单元包含 `kg_execute_entry_capture`，执行 capture 返回 `run_stdout` 文本。 | `test_execute_engine_npu_demo_capture_function_output_returns_run_stdout` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-013 | 生成/编译 | `target=cuda_sm86` 编译 SourceBundle artifact。 | 使用 `ExecutionEngine(target="cuda_sm86")` 与包含 `kernel.cu` 的公开 SourceBundle aggregate。 | 运行 `test_cuda_sm86_builtin_strategy_compiles_source_bundle_with_nvcc`。 | 编译策略写出 `.cu/.cuh` artifact，默认命令包含 `nvcc`、`-arch=sm_86`、`-shared`、`-Xcompiler -fPIC` 并返回 `.so`。 | `test_cuda_sm86_builtin_strategy_compiles_source_bundle_with_nvcc` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-014 | 边界/异常 | `target=cuda_sm86` 拒绝 npu_demo / cpu header 混用。 | 准备混入 `include/npu_demo/npu_demo.h` 的 CUDA 源码。 | 运行 `test_cuda_sm86_builtin_strategy_rejects_header_mismatch`。 | 失败短语为 `target_header_mismatch`。 | `test_cuda_sm86_builtin_strategy_rejects_header_mismatch` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-015 | 执行结果 | `target=cuda_sm86` 非空 stream 失败。 | 构造公开 `CompiledKernel(target="cuda_sm86", ...)`。 | 运行 `test_cuda_sm86_execute_rejects_non_none_stream`。 | 失败短语为 `stream_not_supported`，文本包含 `cuda_sm86 does not support non-None stream`。 | `test_cuda_sm86_execute_rejects_non_none_stream` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-016 | CUDA runtime | SM86 GPU 上运行 9 个现有 kernel demo 形态。 | 本机存在 `nvcc` 与 CUDA device。 | 运行 `pytest -q test/cuda/test_cuda_sm86_kernel_demos_runtime.py -m cuda`。 | CUDA `.so` 编译并通过 generated `kg_execute_entry` 执行 matmul / conv2d / flash_attention demo 形态，输出与 NumPy baseline 一致；缺环境必须记录阻塞，不能记作通过。 | `test_cuda_sm86_matmul_demo_runtime_cases`, `test_cuda_sm86_conv2d_demo_runtime_cases`, `test_cuda_sm86_flash_attention_demo_runtime_cases` |
