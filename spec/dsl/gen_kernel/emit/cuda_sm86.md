# cuda_sm86.md

## 功能简介

- 定义 `kernel_gen.dsl.gen_kernel.emit.cuda_sm86` backend 的 SourceBundle 输出合同。
- backend 只通过 `emit_c_impl(ModuleOp, target="cuda_sm86")` 接入，不新增 package 公开 API。
- 生成源码必须包含 CUDA include、`__global__` kernel marker、真实 Tensor Core `mma.sync` 或 `nvcuda::wmma` 执行路径和 `kg_execute_entry(slots, count)` C ABI。

## API 列表

- 无公开 API；模块通过 emit registry 自动加载。

## 文档信息

- `spec`：[`spec/dsl/gen_kernel/emit/cuda_sm86.md`](../../../../spec/dsl/gen_kernel/emit/cuda_sm86.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/emit/cuda_sm86/__init__.py`](../../../../kernel_gen/dsl/gen_kernel/emit/cuda_sm86/__init__.py)
- `test`：[`test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py`](../../../../test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py)

## API详细说明

本文档不新增独立公开 API。`ModuleOp` 发射入口由 [`spec/dsl/gen_kernel/emit/register.md`](register.md) 的 `emit_c_impl(..., target="cuda_sm86")` 注册合同承接。

## 依赖

- CUDA include runtime：[`spec/include/cuda_sm86/cuda_sm86.md`](../../../include/cuda_sm86/cuda_sm86.md)
- SourceBundle 格式：[`spec/dsl/gen_kernel/source_bundle.md`](../source_bundle.md)
- target registry：[`spec/target/registry.md`](../../../target/registry.md)

## 模块级补充

- SourceBundle artifact 至少包含 `kernel.cu`。
- backend 必须基于 lowered IR 中真实 `Operation.name` kernel op family 与受 spec 约束的函数类型信息选择具体 kernel family，matmul / conv2d / flash_attention 不得共享固定三合一万能 dispatcher。
- backend 不得用 entry function 名称、printed IR 字符串 token、注释或 unknown fallback 选择 kernel family；无支持 op、无 kernel family、多个不兼容 family、unknown op 或空 module 必须稳定失败。
- CUDA include 路径固定为 `include/cuda_sm86/cuda_sm86.cuh`。
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

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-CUDA-SM86-EMIT-001 | 生成/编译 | module 发射 SourceBundle。 | 设置 `set_target("cuda_sm86")`。 | 运行 `test_cuda_sm86_emit_module_returns_source_bundle`。 | 输出 `kernel.cu` 与 generated header marker，含 CUDA include / `mma.sync` / C ABI，且无 npu_demo 残留。 | `test_cuda_sm86_emit_module_returns_source_bundle` |
| TC-CUDA-SM86-EMIT-002 | dump | SourceBundle artifact 落盘。 | 设置 `dump_dir`。 | 运行 `test_cuda_sm86_gen_kernel_dump_writes_bundle_artifacts`。 | `source.cpp`、`kernel.cu`、generated header 均写出。 | `test_cuda_sm86_gen_kernel_dump_writes_bundle_artifacts` |
| TC-CUDA-SM86-EMIT-003 | IR 翻译 | 不同 lowered demo IR 发射。 | 准备 matmul / conv2d / flash_attention module。 | 运行 `test_cuda_sm86_emit_selects_different_sources_from_lowered_entry` 与 CUDA runtime source 差异测试。 | 三类 generated source 的 `kg_cuda_sm86_selected_kernel_kind`、device kernel 与源码内容不同。 | `test_cuda_sm86_emit_selects_different_sources_from_lowered_entry`、`test_cuda_sm86_demo_sources_are_lowered_ir_specific` |
| TC-CUDA-SM86-EMIT-004 | 边界/异常 | unsupported / unknown module 稳定失败。 | 准备空 module、name-only module 或仅属性文本包含 kernel token 的 module。 | 运行 `test_cuda_sm86_emit_rejects_name_only_or_unknown_module` 与 `test_cuda_sm86_emit_rejects_printed_string_tokens_without_kernel_ops`。 | backend 抛出 `unsupported kernel family`，不生成 SourceBundle。 | `test_cuda_sm86_emit_rejects_name_only_or_unknown_module`、`test_cuda_sm86_emit_rejects_printed_string_tokens_without_kernel_ops` |
