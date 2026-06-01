# cuda_sm86.md

## 功能简介

- 定义 `include/cuda_sm86/cuda_sm86.cuh` 的 CUDA SM86 target 单入口 include 合同。
- 该 header 按 arch 第一版分层：`include/api/Arch.h` 承接跨 target 公开接口层，`include/cuda_sm86/Arch.h` 承接 CUDA 后端实现层。
- aggregate header 只聚合公开接口层和后端实现层，不直接承载 memory/scalar/copy/allocation/TF32 helper 实现。
- 具体 matmul / conv2d / flash_attention kernel entry、host wrapper 与 device kernel 必须由 `cuda_sm86` emit SourceBundle 的 generated source 局部实现。
- 禁止公开 `launch_matmul_entry(...)`、禁止在 include 中定义固定 `matmul_f32_kernel(...)` 或任一具体业务 kernel API。

## API 列表

- `namespace cuda_sm86`
- `struct cuda_sm86::ArgSlot`

## 文档信息

- `spec`：[`spec/include/cuda_sm86/cuda_sm86.md`](../../include/cuda_sm86/cuda_sm86.md)
- `功能实现`：[`include/cuda_sm86/cuda_sm86.cuh`](../../../include/cuda_sm86/cuda_sm86.cuh)
- `功能实现`：[`include/cuda_sm86/Arch.h`](../../../include/cuda_sm86/Arch.h)
- `test`：[`test/execute_engine/test_cuda_sm86_strategy.py`](../../../test/execute_engine/test_cuda_sm86_strategy.py)
- `test`：[`test/cuda/test_cuda_sm86_kernel_demos_runtime.py`](../../../test/cuda/test_cuda_sm86_kernel_demos_runtime.py)

## 依赖

- 跨 target Arch 公开接口层：[`spec/include/api/Arch.md`](../api/Arch.md)
- CUDA emit 合同：[`spec/dsl/gen_kernel/emit/cuda_sm86.md`](../../dsl/gen_kernel/emit/cuda_sm86.md)
- 执行引擎 target 合同：[`spec/execute_engine/execute_engine_target.md`](../../execute_engine/execute_engine_target.md)

## API详细说明

### `namespace cuda_sm86`

- api：`namespace cuda_sm86`
- 参数：不适用。
- 返回值：不适用。
- 使用示例：

  ```cpp
  #include "include/cuda_sm86/cuda_sm86.cuh"
  ```

- 功能说明：固定 CUDA SM86 后端 namespace，用于承接 generated source 与 execute_engine 共享的 backend ABI。
- 注意事项：该 namespace 不承接跨 target `launch` / `KernelContext` 公开接口；跨 target Arch 接口真源仍是 `include/api/Arch.h`。

### `struct cuda_sm86::ArgSlot`

- api：`struct cuda_sm86::ArgSlot`
- 参数：不适用。
- 字段：`kind`、`data`、`shape`、`stride`、`rank`、`dtype_code`、`int_value`、`float_value`。
- 返回值：不适用。
- 使用示例：

  ```cpp
  extern "C" int kg_execute_entry(cuda_sm86::ArgSlot *slots, unsigned long long count) {
    return slots == nullptr && count != 0 ? -1 : 0;
  }
  ```

- 功能说明：描述 CUDA SM86 执行引擎 slot C ABI 中一个运行时参数槽位。
- 注意事项：该结构是 CUDA 后端 ABI，不是跨 target include/api 公共抽象；不得承载具体业务 kernel、typed view 或 Tensor Core tile 语义。

## 后端实现层边界

- `include/cuda_sm86/Arch.h` 是 CUDA 后端实现层；它由 `cuda_sm86.cuh` 聚合，但不扩展跨 target include/api 公开面。
- `cuda_sm86::detail::*` 只允许 generated CUDA source 使用，承接 memory/scalar guard、host-device copy、device allocation、TF32 转换与 CUDA 错误检查。
- `KG_CUDA_CHECK(expr)` 只允许 generated CUDA source 内部使用，错误文本保持 `cuda_runtime_failed`。
- 测试不得把 `cuda_sm86::detail::*` 当成公开 API 直接调用；只能通过 `emit_c(...)`、`gen_kernel(...)`、`ExecutionEngine(target="cuda_sm86")` 或 CUDA demo runtime gate 观察行为。

## 测试

- 测试文件：`test/execute_engine/test_cuda_sm86_strategy.py`
- 测试文件：`test/cuda/test_cuda_sm86_kernel_demos_runtime.py`
- 测试文件：`test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py`
- 执行命令：
  - `pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py`
  - `pytest -q test/execute_engine/test_cuda_sm86_strategy.py`
  - `pytest -q test/cuda/test_cuda_sm86_kernel_demos_runtime.py -m cuda`

### 测试目标

- 验证 aggregate header 包含 `include/api/Arch.h` 与 `include/cuda_sm86/Arch.h`。
- 验证 aggregate header 不直接定义 backend helper 或固定业务 kernel entry。
- 验证 generated source 通过 backend implementation layer 使用 `cuda_sm86::detail::*` helper。
- 在存在 `nvcc` 与 CUDA device 的环境中验证现有 CUDA kernel demo 形态可通过 generated CUDA source 跑通。
- 环境缺失时必须记录阻塞，不能把 skip 写成 runtime 通过。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-CUDA-SM86-INCLUDE-001 | 编译 | SourceBundle 编译命令包含 CUDA include 与 SM86 flags。 | fake `nvcc` 可执行。 | 运行 `test_cuda_sm86_compile_writes_source_bundle_and_nvcc_command`。 | artifact 写出，命令含 `-arch=sm_86`、`-shared`、`-Xcompiler -fPIC`。 | `test_cuda_sm86_compile_writes_source_bundle_and_nvcc_command` |
| TC-CUDA-SM86-INCLUDE-002 | 分层 | aggregate header 与后端实现层职责拆分。 | 候选 diff 已生成。 | 运行 `test_cuda_sm86_emit_module_returns_source_bundle`。 | `cuda_sm86.cuh` 只聚合 `include/api/Arch.h` 和 `include/cuda_sm86/Arch.h`，backend helper 位于 `cuda_sm86::detail::*`。 | `test_cuda_sm86_emit_module_returns_source_bundle` |
| TC-CUDA-SM86-INCLUDE-003 | runtime | 现有 kernel demo 形态执行。 | 本机存在 `nvcc` 与 CUDA device。 | 运行 `pytest -q test/cuda/test_cuda_sm86_kernel_demos_runtime.py -m cuda`。 | matmul / conv2d / flash_attention 三类 demo 形态输出与 NumPy baseline 一致。 | `test_cuda_sm86_*_demo_runtime_cases` |
