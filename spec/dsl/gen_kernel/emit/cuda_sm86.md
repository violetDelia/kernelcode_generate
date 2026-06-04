# cuda_sm86.md

## 功能简介

- 定义 `kernel_gen.dsl.gen_kernel.emit.cuda_sm86` package backend 的 SourceBundle、target include 和 per-kernel-op emit 输出合同。
- package root 聚合 `include.py`、`kernel/` 和 `module.py` 注册入口；backend 通过 `emit_c_include_impl(target="cuda_sm86")` 与 `emit_c_impl(..., target="cuda_sm86")` 接入，不新增包外 Python 公开 API。
- 生成源码必须包含 CUDA aggregate include、`__global__` kernel marker、真实 Tensor Core `mma.sync` 或 `nvcuda::wmma` 执行路径和 `kg_execute_entry(slots, count)` C ABI。

## API 列表

- 无包外公开 API；package 通过 emit registry 自动加载。
- package-local 文件级 API 仅允许 `kernel_gen/dsl/gen_kernel/emit/cuda_sm86/` 包内按依赖方向调用，不进入 `cuda_sm86.__all__` 或测试 direct import。

## 文档信息

- `spec`：[`spec/dsl/gen_kernel/emit/cuda_sm86.md`](../../../../spec/dsl/gen_kernel/emit/cuda_sm86.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/emit/cuda_sm86/__init__.py`](../../../../kernel_gen/dsl/gen_kernel/emit/cuda_sm86/__init__.py)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/emit/cuda_sm86/include.py`](../../../../kernel_gen/dsl/gen_kernel/emit/cuda_sm86/include.py)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/emit/cuda_sm86/module.py`](../../../../kernel_gen/dsl/gen_kernel/emit/cuda_sm86/module.py)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/emit/cuda_sm86/source_bundle.py`](../../../../kernel_gen/dsl/gen_kernel/emit/cuda_sm86/source_bundle.py)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/emit/cuda_sm86/runtime.py`](../../../../kernel_gen/dsl/gen_kernel/emit/cuda_sm86/runtime.py)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/`](../../../../kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/)
- `test`：[`test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py`](../../../../test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py)

## API详细说明

本文档不新增独立包外公开 API。`ModuleOp` 发射入口由 [`spec/dsl/gen_kernel/emit/register.md`](register.md) 的 `emit_c_impl(..., target="cuda_sm86")` 注册合同承接。

package-local 文件级 API exact set：
- `CUDA_SM86_TARGET_NAME: str = "cuda_sm86"`
- `CUDA_SM86_KERNEL_SOURCE_ARTIFACT: str = "kernel.cu"`
- `CUDA_SM86_GENERATED_ENTRY_HEADER_ARTIFACT: str = "include/cuda_sm86/generated_entry.cuh"`
- `CUDA_SM86_RUNTIME_ENTRY_NAME: str = "kg_execute_entry"`
- `CUDA_SM86_KERNEL_OP_BINARY_ELEWISE: str = "kernel.binary_elewise"`
- `CUDA_SM86_KERNEL_OP_EXP: str = "kernel.exp"`
- `CUDA_SM86_KERNEL_OP_IMG2COL2D: str = "kernel.img2col2d"`
- `CUDA_SM86_KERNEL_OP_MATMUL: str = "kernel.matmul"`
- `CUDA_SM86_KERNEL_OP_REDUCE: str = "kernel.reduce"`
- `class CudaSm86IrTrace(records: tuple[str, ...], markers: tuple[str, ...], source_fragments: tuple[str, ...], op_counts: dict[str, int], memory_spaces: tuple[str, ...], entry_symbol: str, implementation_entry_symbol: str, stable_hash: str, executable_trace_source: str)`
- `CudaSm86IrTrace.render_marker_source() -> str`
- `class CudaSm86SourceBuilder(module_op: ModuleOp, ctx: EmitCContext)`
- `CudaSm86SourceBuilder.build() -> dict[str, str]`
- `CudaSm86SourceBuilder.collect_trace() -> CudaSm86IrTrace`
- `CudaSm86SourceBuilder.operation_record(op: Operation) -> str`
- `CudaSm86SourceBuilder.operation_markers(op: Operation) -> list[str]`
- `CudaSm86SourceBuilder.operation_memory_spaces(op: Operation) -> tuple[str, ...]`
- `CudaSm86SourceBuilder.operation_source_fragments(op: Operation) -> tuple[tuple[str, str], ...]`
- `CudaSm86SourceBuilder.matmul_operand_spaces(op: Operation) -> tuple[str, str, str]`
- `CudaSm86SourceBuilder.matmul_writeback_visible(op: Operation) -> bool`
- `CudaSm86SourceBuilder.matmul_materialization_marker(op: Operation) -> str`
- `CudaSm86SourceBuilder.validate_supported_attrs() -> None`
- `CudaSm86SourceBuilder.select_entry_symbol(op_counts: dict[str, int]) -> str`
- `CudaSm86SourceBuilder.operation_executable_word(record: str, index: int) -> str`
- `CudaSm86SourceBuilder.render_executable_trace_source(records: tuple[str, ...], stable_hash: str, implementation_entry_symbol: str) -> str`
- `CudaSm86SourceBuilder.render_kernel_source(trace: CudaSm86IrTrace) -> str`
- `build_cuda_sm86_source_bundle(module_op: ModuleOp, ctx: EmitCContext) -> dict[str, str]`

`runtime.py` 中 `CUDA_SM86_COMMON_RUNTIME_SOURCE` 与 `CUDA_SM86_HEADER_SOURCE` 是 package-local source fragment，不进入包外 public path，不允许测试 direct import；其用途仅限 `source_bundle.py` 拼装计划确认的 SourceBundle。
`include.py` 与 `kernel/*.py` 中的 `_emit_cuda_sm86_*` 函数只作为 registry decorator entry 使用，不进入 package-local exact set，不允许包外 direct import / call。

## 依赖

- CUDA include aggregate 与后端实现层：[`spec/include/cuda_sm86/cuda_sm86.md`](../../../include/cuda_sm86/cuda_sm86.md)
- SourceBundle 格式：[`spec/dsl/gen_kernel/source_bundle.md`](../source_bundle.md)
- target registry：[`spec/target/registry.md`](../../../target/registry.md)

## 模块级补充

- SourceBundle artifact 至少包含 `kernel.cu`。
- 目标结构固定为：
  - `__init__.py`：只导入 `include.py`、`kernel/`、`module.py` 触发注册，`__all__` 为空。
  - `constants.py`：只承载 target / artifact / runtime entry / kernel op token 短字符串常量。
  - `include.py`：唯一 `@emit_c_include_impl(target="cuda_sm86")` 真源。
  - `module.py`：唯一 `@emit_c_impl(ModuleOp, target="cuda_sm86")` 真源。
  - `kernel/{binary_elewise,exp,img2col2d,matmul,reduce}.py`：分别承接对应 `kernel.*` op 的 `@emit_c_impl(..., target="cuda_sm86")`。
  - `source_bundle.py`：遍历 final IR，承接 trace/hash/marker 和 SourceBundle artifact 拼装。
  - `runtime.py`：承接 generated source 内部 common runtime / header source fragment。
- `cuda_sm86/source/` 不存在；不得新增 source 子目录把 generated source 与 kernel op emit 分离。
- `cuda_sm86/__init__.py` 不得包含 CUDA source 大字符串、final IR traversal、SourceBundle dict 拼装或 `@emit_c_impl` handler。
- `cuda_sm86/kernel/*.py` 必须保持“一个 `kernel.*` op 对应一个 emit 注册”；`kernel.conv2d`、`kernel.flash_attention` 不是 IR op，不得作为 emitter 文件存在。
- backend 必须以 `cuda-sm86-lowering` 后 final IR 的真实 op/attrs/operand SSA identity/result identity/region block 信息构造 `kg.cuda.ir.hash`、source marker、`kg.cuda.ir.source.fragment` 和 hash 专属可执行 trace wrapper；同类型 value 的 dataflow 变化必须改变 hash 与非注释 trace body，不得根据旧摘要数据结构拼接整段 kernel source。
- backend 可根据真实 final IR compute op 选择当前 9-demo 覆盖的 implementation primitive，但 `kg_execute_entry` 必须调用 hash 专属 generated entry symbol；该 entry 先执行按 final IR record 逐段生成的 host/device trace code，再调用 implementation primitive。不得用 entry function 名称、printed IR 字符串 token、注释或 unknown fallback 选择 source；无支持 compute op、unknown op 或空 module 必须以 `unsupported cuda_sm86 final IR op: <op_name|<none>>` 失败。
- CUDA include 路径固定为 `include/cuda_sm86/cuda_sm86.cuh`；该 header 只聚合 `include/api/Arch.h` 与 `include/cuda_sm86/Arch.h`。
- CUDA 后端实现层固定为 `include/cuda_sm86/Arch.h`；generated source 真实使用的 IR memory/scalar/copy/tf32 helper 必须位于 `cuda_sm86::detail::*`，不得写成 aggregate header 公共 helper。
- `cuda_sm86::detail::*` 不进入包外公开 API，测试不得直接调用；只能通过 generated source / execute_engine / CUDA runtime gate 验证。
- CUDA include 不得包含固定业务 kernel entry。
- generated source 不得包含 `include/npu_demo`、`npu_demo::` 或 `get_dynamic_memory<TLM`。
- Tensor Core 路径必须是 generated source 中可由 `nvcc` 编译并参与最终 matmul 输出的 `mma.sync` 或 `nvcuda::wmma` 执行路径，不得只用注释、marker、probe、sentinel 或 dead path 替代。

## 测试

- 测试文件：`test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py`
- 执行命令：`pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py test/dsl/gen_kernel/emit/test_package.py`

### 测试目标

- 验证 `target="cuda_sm86"` 自动加载 backend。
- 验证 SourceBundle marker、`.cu/.cuh` artifact、CUDA include、Tensor Core 指令路径和 C ABI entry。
- 验证真实 lowered demo final IR 会影响 `kg.cuda.ir.hash`、marker、memory space、entry symbol、source fragment 与非注释 executable trace body，matmul / conv2d / flash_attention source 互不相同；同 op sequence、同 operand/result type 但 SSA dataflow 不同的 ModuleOp 也必须改变 hash、trace body 和 source。
- 验证空 module、name-only module 和 printed string token spoof module 均稳定失败，不得 fallback 到任一 generated source profile。
- 验证 `gen_kernel(...)` dump 展开 aggregate 与 artifact。
- 验证 package structure：`module.py` 是唯一 handler，root / kernel package `__all__` 为空，测试不得 direct import 内部 package-local API。
- 验证 package structure：`kernel/*.py` 中每个支持的 `kernel.*` op 都有对应 `@emit_c_impl`，`include.py` 有唯一 target include 注册，且不存在 `source/` 子目录。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-CUDA-SM86-EMIT-001 | 生成/编译 | module 发射 SourceBundle。 | 设置 `set_target("cuda_sm86")`。 | 运行 `test_cuda_sm86_emit_module_returns_source_bundle`。 | 输出 `kernel.cu` 与 generated header marker，含 CUDA include / `mma.sync` / C ABI，且无 npu_demo 残留。 | `test_cuda_sm86_emit_module_returns_source_bundle` |
| TC-CUDA-SM86-EMIT-002 | dump | SourceBundle artifact 落盘。 | 设置 `dump_dir`。 | 运行 `test_cuda_sm86_gen_kernel_dump_writes_bundle_artifacts`。 | `source.cpp`、`kernel.cu`、generated header 均写出。 | `test_cuda_sm86_gen_kernel_dump_writes_bundle_artifacts` |
| TC-CUDA-SM86-EMIT-003 | IR 翻译 | 不同 lowered demo final IR 发射。 | 准备 matmul / conv2d / flash_attention module。 | 运行 `test_cuda_sm86_emit_selects_different_sources_from_lowered_entry`、`test_cuda_sm86_ir_hash_is_stable_and_op_sequence_specific`、`test_cuda_sm86_executable_trace_changes_with_same_entry_final_ir_op_sequence`、`test_cuda_sm86_executable_trace_changes_with_same_type_dataflow` 与 CUDA runtime source 差异测试。 | 三类 generated source 的 `kg.cuda.ir.hash`、entry symbol、source fragment、op marker 与源码内容不同；同 implementation entry 的 final IR op sequence 改动会改变非注释 executable trace body；同 op/type 下的 lhs/rhs SSA dataflow 交换也会改变 hash、trace body 和 source。 | `test_cuda_sm86_emit_selects_different_sources_from_lowered_entry`、`test_cuda_sm86_ir_hash_is_stable_and_op_sequence_specific`、`test_cuda_sm86_executable_trace_changes_with_same_entry_final_ir_op_sequence`、`test_cuda_sm86_executable_trace_changes_with_same_type_dataflow`、`test_cuda_sm86_demo_sources_are_lowered_ir_specific` |
| TC-CUDA-SM86-EMIT-004 | 边界/异常 | unsupported / unknown module 稳定失败。 | 准备空 module、name-only module 或仅属性文本包含 kernel token 的 module。 | 运行 `test_cuda_sm86_emit_rejects_name_only_or_unknown_module` 与 `test_cuda_sm86_emit_rejects_printed_string_tokens_without_kernel_ops`。 | backend 抛出 `unsupported cuda_sm86 final IR op: <none>` 或真实 unsupported op 文本，不生成 SourceBundle。 | `test_cuda_sm86_emit_rejects_name_only_or_unknown_module`、`test_cuda_sm86_emit_rejects_printed_string_tokens_without_kernel_ops` |
| TC-CUDA-SM86-EMIT-005 | 结构 | package 分层结构保持。 | 已完成 `cuda_sm86` package 拆分。 | 运行 `test_cuda_sm86_emit_package_structure_matches_plan`。 | root 不含大模板 / handler，handler 仅在 `module.py`，依赖方向和测试直连禁令满足计划。 | `test_cuda_sm86_emit_package_structure_matches_plan` |
