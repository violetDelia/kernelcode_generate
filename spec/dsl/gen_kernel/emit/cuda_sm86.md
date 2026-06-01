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
- `功能实现`：[`kernel_gen/dsl/gen_kernel/emit/cuda_sm86/detect.py`](../../../../kernel_gen/dsl/gen_kernel/emit/cuda_sm86/detect.py)
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
- `class CudaSm86KernelFamily(str, Enum)`
- `class CudaSm86ModuleSummary(family: CudaSm86KernelFamily, matmul_count: int, img2col_count: int, exp_count: int, reduce_count: int, binary_count: int, launch_count: int, memory_rank_patterns: frozenset[tuple[int, ...]])`
- `detect_cuda_sm86_kernel_family(module_op: ModuleOp, ctx: EmitCContext) -> CudaSm86KernelFamily`
- `summarize_cuda_sm86_module(module_op: ModuleOp, ctx: EmitCContext) -> CudaSm86ModuleSummary`
- `build_cuda_sm86_source_bundle(summary: CudaSm86ModuleSummary) -> dict[str, str]`
- `emit_matmul_source(summary: CudaSm86ModuleSummary) -> str`
- `emit_conv2d_source(summary: CudaSm86ModuleSummary) -> str`
- `emit_flash_attention_source(summary: CudaSm86ModuleSummary) -> str`

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
  - `detect.py`：通过每个真实 `kernel.*` op emit 结果承接 lowered IR family detection 和 stable failure。
  - `source_bundle.py`：承接 SourceBundle artifact 拼装。
  - `runtime.py`：承接 generated source 内部 common runtime / header source fragment。
- `cuda_sm86/source/` 不存在；不得新增 source 子目录把 generated source 与 kernel op emit 分离。
- `cuda_sm86/__init__.py` 不得包含 CUDA source 大字符串、family detection、SourceBundle dict 拼装或 `@emit_c_impl` handler。
- `cuda_sm86/kernel/*.py` 必须保持“一个 `kernel.*` op 对应一个 emit 注册”；`kernel.conv2d`、`kernel.flash_attention` 不是 IR op，不得作为 emitter 文件存在。
- backend 必须基于 lowered IR 中真实 `Operation.name` kernel op family 与受 spec 约束的函数类型信息选择具体 kernel family，matmul / conv2d / flash_attention 不得共享固定三合一万能 dispatcher。
- backend 不得用 entry function 名称、printed IR 字符串 token、注释或 unknown fallback 选择 kernel family；无支持 op、无 kernel family、多个不兼容 family、unknown op 或空 module 必须稳定失败。
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
- 验证真实 lowered demo IR 会影响 generated SourceBundle，matmul / conv2d / flash_attention source 互不相同。
- 验证空 module、name-only module 和 printed string token spoof module 均稳定失败，不得 fallback 到 matmul / conv2d / flash_attention。
- 验证 `gen_kernel(...)` dump 展开 aggregate 与 artifact。
- 验证 package structure：`module.py` 是唯一 handler，root / kernel package `__all__` 为空，测试不得 direct import 内部 package-local API。
- 验证 package structure：`kernel/*.py` 中每个支持的 `kernel.*` op 都有对应 `@emit_c_impl`，`include.py` 有唯一 target include 注册，且不存在 `source/` 子目录。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-CUDA-SM86-EMIT-001 | 生成/编译 | module 发射 SourceBundle。 | 设置 `set_target("cuda_sm86")`。 | 运行 `test_cuda_sm86_emit_module_returns_source_bundle`。 | 输出 `kernel.cu` 与 generated header marker，含 CUDA include / `mma.sync` / C ABI，且无 npu_demo 残留。 | `test_cuda_sm86_emit_module_returns_source_bundle` |
| TC-CUDA-SM86-EMIT-002 | dump | SourceBundle artifact 落盘。 | 设置 `dump_dir`。 | 运行 `test_cuda_sm86_gen_kernel_dump_writes_bundle_artifacts`。 | `source.cpp`、`kernel.cu`、generated header 均写出。 | `test_cuda_sm86_gen_kernel_dump_writes_bundle_artifacts` |
| TC-CUDA-SM86-EMIT-003 | IR 翻译 | 不同 lowered demo IR 发射。 | 准备 matmul / conv2d / flash_attention module。 | 运行 `test_cuda_sm86_emit_selects_different_sources_from_lowered_entry` 与 CUDA runtime source 差异测试。 | 三类 generated source 的 `kg_cuda_sm86_selected_kernel_kind`、device kernel 与源码内容不同。 | `test_cuda_sm86_emit_selects_different_sources_from_lowered_entry`、`test_cuda_sm86_demo_sources_are_lowered_ir_specific` |
| TC-CUDA-SM86-EMIT-004 | 边界/异常 | unsupported / unknown module 稳定失败。 | 准备空 module、name-only module 或仅属性文本包含 kernel token 的 module。 | 运行 `test_cuda_sm86_emit_rejects_name_only_or_unknown_module` 与 `test_cuda_sm86_emit_rejects_printed_string_tokens_without_kernel_ops`。 | backend 抛出 `unsupported kernel family`，不生成 SourceBundle。 | `test_cuda_sm86_emit_rejects_name_only_or_unknown_module`、`test_cuda_sm86_emit_rejects_printed_string_tokens_without_kernel_ops` |
| TC-CUDA-SM86-EMIT-005 | 结构 | package 分层结构保持。 | 已完成 `cuda_sm86` package 拆分。 | 运行 `test_cuda_sm86_emit_package_structure_matches_plan`。 | root 不含大模板 / handler，handler 仅在 `module.py`，依赖方向和测试直连禁令满足计划。 | `test_cuda_sm86_emit_package_structure_matches_plan` |
