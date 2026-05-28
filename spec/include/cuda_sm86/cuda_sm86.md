# cuda_sm86.md

## 功能简介

- 定义 CUDA SM86 include runtime 的最小公开 C++ API 合同。
- 该 include runtime 定位类似 target arch include：只提供 generated CUDA source 的基础 slot ABI 与 CUDA 错误检查。
- 具体 matmul / conv2d / flash_attention kernel entry、host wrapper、device kernel、slot guard、shape product、host-device copy、device allocation、typed view 与 Tensor Core helper 必须由 `cuda_sm86` emit SourceBundle 的 generated source 局部实现。
- 禁止公开 `launch_matmul_entry(...)`、禁止在 include 中定义固定 `matmul_f32_kernel(...)` 或任一具体业务 kernel API。

## API 列表

- `struct cuda_sm86::ArgSlot`
- `void cuda_sm86::check_cuda(cudaError_t status, const char *expr, const char *file, int line)`
- `KG_CUDA_CHECK(expr)`

## 文档信息

- `spec`：[`spec/include/cuda_sm86/cuda_sm86.md`](../../include/cuda_sm86/cuda_sm86.md)
- `功能实现`：[`include/cuda_sm86/cuda_sm86.cuh`](../../../include/cuda_sm86/cuda_sm86.cuh)
- `test`：[`test/execute_engine/test_cuda_sm86_strategy.py`](../../../test/execute_engine/test_cuda_sm86_strategy.py)
- `test`：[`test/cuda/test_cuda_sm86_kernel_demos_runtime.py`](../../../test/cuda/test_cuda_sm86_kernel_demos_runtime.py)

## 依赖

- CUDA runtime headers：`cuda_runtime.h`
- CUDA emit 合同：[`spec/dsl/gen_kernel/emit/cuda_sm86.md`](../../dsl/gen_kernel/emit/cuda_sm86.md)
- 执行引擎 target 合同：[`spec/execute_engine/execute_engine_target.md`](../../execute_engine/execute_engine_target.md)

## API详细说明

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
- 功能说明：描述执行引擎 slot C ABI 中一个运行时参数槽位。
- 注意事项：该结构只稳定承载 ABI 字段，不承载任何具体业务 kernel、typed view 或 Tensor Core tile 语义。

### `void cuda_sm86::check_cuda(cudaError_t status, const char *expr, const char *file, int line)`

- api：`void cuda_sm86::check_cuda(cudaError_t status, const char *expr, const char *file, int line)`
- 参数：`status` 为 CUDA runtime API 返回值；`expr/file/line` 为调用现场。
- 返回值：成功时无返回值；失败时输出 `cuda_runtime_failed` 并终止进程。
- 使用示例：

  ```cpp
  cuda_sm86::check_cuda(cudaSuccess, "cudaSuccess", __FILE__, __LINE__);
  ```
- 功能说明：统一 CUDA runtime 错误检查与稳定错误文本。
- 注意事项：generated source 的 host wrapper 可通过该函数记录 CUDA runtime API 失败，不得把业务 kernel 分发逻辑放入 include。

### `KG_CUDA_CHECK(expr)`

- api：`KG_CUDA_CHECK(expr)`
- 参数：`expr` 为返回 `cudaError_t` 的 CUDA runtime 表达式。
- 返回值：无返回值。
- 使用示例：

  ```cpp
  KG_CUDA_CHECK(cudaGetLastError());
  ```
- 功能说明：为 generated source 提供简洁 CUDA runtime 检查宏。
- 注意事项：宏只封装 `cuda_sm86::check_cuda(...)`，不得扩展为业务 kernel launch API。

## 测试

- 测试文件：`test/execute_engine/test_cuda_sm86_strategy.py`
- 测试文件：`test/cuda/test_cuda_sm86_kernel_demos_runtime.py`
- 执行命令：
  - `pytest -q test/execute_engine/test_cuda_sm86_strategy.py`
  - `pytest -q test/cuda/test_cuda_sm86_kernel_demos_runtime.py -m cuda`

### 测试目标

- 验证 include 路径、SourceBundle artifact、`nvcc` 编译命令和 C ABI 入口。
- 验证 include 中没有具体业务 kernel、host wrapper、slot guard、typed view、device copy / allocation helper 或 Tensor Core tile marker。
- 在存在 `nvcc` 与 CUDA device 的环境中验证 9 个现有 kernel demo 形态可通过 generated CUDA source 跑通。
- 环境缺失时必须记录阻塞，不能把 skip 写成 runtime 通过。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-CUDA-SM86-INCLUDE-001 | 编译 | SourceBundle 编译命令包含 CUDA include 与 SM86 flags。 | fake `nvcc` 可执行。 | 运行 `test_cuda_sm86_compile_writes_source_bundle_and_nvcc_command`。 | artifact 写出，命令含 `-arch=sm_86`、`-shared`、`-Xcompiler -fPIC`。 | `test_cuda_sm86_compile_writes_source_bundle_and_nvcc_command` |
| TC-CUDA-SM86-INCLUDE-002 | 边界 | include 只暴露最小 ABI。 | 候选 diff 已生成。 | 运行 `test_cuda_sm86_emit_module_returns_source_bundle`。 | include 只含 `ArgSlot` / `check_cuda` / `KG_CUDA_CHECK`，generated source 承载 slot guard、copy、allocation 与 demo kernels。 | `test_cuda_sm86_emit_module_returns_source_bundle` |
| TC-CUDA-SM86-INCLUDE-003 | runtime | 9 个现有 kernel demo 形态执行。 | 本机存在 `nvcc` 与 CUDA device。 | 运行 `pytest -q test/cuda/test_cuda_sm86_kernel_demos_runtime.py -m cuda`。 | matmul / conv2d / flash_attention 三类 demo 形态输出与 NumPy baseline 一致。 | `test_cuda_sm86_*_demo_runtime_cases` |
