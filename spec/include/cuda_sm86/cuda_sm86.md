# cuda_sm86.md

## 功能简介

- 定义 `include/cuda_sm86/cuda_sm86.cuh` 的 CUDA SM86 target 单入口 include 合同。
- 该 header 按 arch 第一版分层：`include/api/Arch.h` 承接跨 target 公开接口层，`include/cuda_sm86/Arch.h` 承接 CUDA 后端实现层。
- aggregate header 聚合公开接口层和后端实现层；Draft 10 A1 确认的 CUDA SM86 wrapper API 由 `include/cuda_sm86/Arch.h` 承载。
- 具体 matmul / conv2d / flash_attention kernel entry、hash entry、generated `__global__` kernel 与 generated device body 必须由 `cuda_sm86` emit SourceBundle 局部实现。
- 禁止公开 `launch_matmul_entry(...)`、禁止在 include 中定义固定 `matmul_f32_kernel(...)` 或任一具体业务 kernel API。

## API 列表

- `namespace cuda_sm86`
- `struct cuda_sm86::ArgSlot`
- `class cuda_sm86::KernelContext`
- `cuda_sm86::launch<block, thread, subthread, shared_memory_size, name>(ctx, args...)`
- `cuda_sm86::block_id()`
- `cuda_sm86::thread_id()`
- `cuda_sm86::thread_num()`
- `cuda_sm86::barrier()`
- `cuda_sm86::alloc<Space, T>(ctx, shape, stride, format = MemoryFormat::Norm)`
- `cuda_sm86::DmaRing<Space, SlotT, BackingT>`
- `template <MemorySpace Space, typename SlotT, typename BackingT> __device__ cuda_sm86::DmaRing<Space, SlotT, BackingT>::DmaRing(Memory<Space, BackingT>& backing, S_INT num, S_INT offset_bytes, const Vector& shape, const Vector& stride, MemoryFormat format)`
- `template <MemorySpace Space, typename SlotT, typename BackingT> __device__ Memory<Space, SlotT> cuda_sm86::DmaRing<Space, SlotT, BackingT>::current() const`
- `template <MemorySpace Space, typename SlotT, typename BackingT> __device__ Memory<Space, SlotT> cuda_sm86::DmaRing<Space, SlotT, BackingT>::advance()`
- `cuda_sm86::make_ring<SlotT, Space, BackingT>(backing, num, offset_bytes, shape, stride, format = MemoryFormat::Norm)`
- `cuda_sm86::fill(ctx, target, value)`
- `cuda_sm86::slice(ctx, target, source, offset, size, stride)`
- `cuda_sm86::deslice(ctx, target, source, offset, size, stride)`
- `cuda_sm86::load(ctx, target, source, offset, size, stride)`
- `cuda_sm86::store(ctx, target, source, offset, size, stride)`
- `cuda_sm86::transpose(ctx, target, source, perm)`
- `cuda_sm86::broadcast(ctx, target, source)`
- `cuda_sm86::view(source, offset, size, stride)`
- `cuda_sm86::add/sub/mul/truediv/max(ctx, out, lhs, rhs)`
- `cuda_sm86::exp(ctx, out, input)`
- `cuda_sm86::reduce_sum/reduce_max(ctx, out, input, axis)`
- `cuda_sm86::matmul(ctx, out, lhs, rhs, acc = false)`
- `cuda_sm86::img2col2d(ctx, out, input, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr)`

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
- 注意事项：该 namespace 只承接 Draft 10 A1 确认的 CUDA SM86 wrapper API 与 generated source 共享 ABI；跨 target 通用接口真源仍是 `include/api/Arch.h`。

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

### `cuda_sm86::KernelContext` 与 wrapper API

- api：`class cuda_sm86::KernelContext`、`cuda_sm86::launch(...)`、`cuda_sm86::load/store/slice/deslice/fill/broadcast/transpose/view/make_ring/current/advance/matmul/img2col2d/add/sub/mul/truediv/max/exp/reduce_sum/reduce_max(...)`
- 参数：按 `API 列表` 中 wrapper 签名接收 generated device body 的 context、memory descriptor、symbol scalar、shape、stride、offset 或 launch 参数。
- 返回值：除 descriptor / ring / arch query wrapper 外，算子 wrapper 返回 `Status`；`launch` 返回 `Status` 并保留显式 template extents。
- 注意事项：`launch` 仅按显式 `shared_memory_size` template 值设置 CUDA dynamic shared memory opt-in，不做设备能力探测、sm 推断或 target 选择。
- 使用示例：

  ```cpp
  cuda_sm86::KernelContext ctx;
  (void)cuda_sm86::load<MemorySpace::TLM1, MemorySpace::GM, float, float>(ctx, target, source, Vector{0}, Vector{16, 16}, Vector{1, 1});
  ```

- 功能说明：为 generated CUDA SM86 device body 提供 Draft 10 A1 确认的 public wrapper surface，使 final IR op/operand/shape/stride/space/symbol dataflow 直接进入 generated source。
- 注意事项：不得把 `cuda_sm86::detail::*` 加入公开 API；不得新增 fixed primitive、vendor BLAS 或其它 SM/backend fallback。

### `cuda_sm86::DmaRing<Space, SlotT, BackingT>`

- api：`template <MemorySpace Space, typename SlotT, typename BackingT> class cuda_sm86::DmaRing`、`template <MemorySpace Space, typename SlotT, typename BackingT> __device__ cuda_sm86::DmaRing<Space, SlotT, BackingT>::DmaRing(Memory<Space, BackingT>& backing, S_INT num, S_INT offset_bytes, const Vector& shape, const Vector& stride, MemoryFormat format)`、`template <MemorySpace Space, typename SlotT, typename BackingT> __device__ Memory<Space, SlotT> cuda_sm86::DmaRing<Space, SlotT, BackingT>::current() const`、`template <MemorySpace Space, typename SlotT, typename BackingT> __device__ Memory<Space, SlotT> cuda_sm86::DmaRing<Space, SlotT, BackingT>::advance()`
- 参数：`backing` 为 ring backing descriptor；`num` 为 ring slot 数量；`offset_bytes` 为 slot 字节间距；`shape`、`stride` 和 `format` 描述当前 slot layout。
- 返回值：constructor 无返回值；`current()` 与 `advance()` 返回 `Memory<Space, SlotT>` slot descriptor。
- 使用示例：

  ```cpp
  auto ring = cuda_sm86::make_ring<float>(backing, 2, 64, {16}, {1});
  Memory<MemorySpace::TLM1, float> current = ring.current();
  Memory<MemorySpace::TLM1, float> next = ring.advance();
  ```

- 功能说明：承接 generated device body 中 `dma.current_ring` 与 `dma.advance_ring` 的 public member surface；`current()` 不推进 cursor，`advance()` 推进 cursor 后返回新 slot。
- 注意事项：ring 生命周期和 advance 位置由 emitc 根据 final IR 生命周期分析生成；wrapper 本身不推断生命周期，也不新增稳定错误文本。

## 后端实现层边界

- `include/cuda_sm86/Arch.h` 是 CUDA 后端实现层；它由 `cuda_sm86.cuh` 聚合，并承载 Draft 10 A1 确认的 CUDA SM86 wrapper API。
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
- 验证 aggregate header 不直接定义固定业务 kernel entry，且公开 wrapper API 列表不包含 `cuda_sm86::detail::*`。
- 验证 generated source 通过 backend implementation layer 使用 public wrapper calls，并只在内部 descriptor glue 中使用 `cuda_sm86::detail::*`。
- 在存在 `nvcc` 与 SM89 CUDA device 的环境中验证现有 CUDA kernel demo 形态可通过 generated CUDA source 跑通。
- 环境缺失时必须记录阻塞，不能把 skip 写成 runtime 通过。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-CUDA-SM86-INCLUDE-001 | 编译 | SourceBundle 编译命令包含 CUDA include 与 SM86 flags。 | fake `nvcc` 可执行。 | 运行 `test_cuda_sm86_compile_writes_source_bundle_and_nvcc_command`。 | artifact 写出，命令含 `-arch=sm_86`、`-shared`、`-Xcompiler -fPIC`。 | `test_cuda_sm86_compile_writes_source_bundle_and_nvcc_command` |
| TC-CUDA-SM86-INCLUDE-002 | 分层 | aggregate header 与后端实现层职责拆分。 | 候选 diff 已生成。 | 运行 `test_cuda_sm86_emit_module_returns_source_bundle`。 | `cuda_sm86.cuh` 只聚合 `include/api/Arch.h` 和 `include/cuda_sm86/Arch.h`，backend helper 位于 `cuda_sm86::detail::*`。 | `test_cuda_sm86_emit_module_returns_source_bundle` |
| TC-CUDA-SM86-INCLUDE-003 | runtime | 现有 kernel demo 形态执行。 | 本机存在 `nvcc` 与 SM89 CUDA device。 | 运行 `pytest -q test/cuda/test_cuda_sm86_kernel_demos_runtime.py -m cuda`。 | matmul / conv2d / flash_attention 三类 demo 形态输出与 NumPy baseline 一致；无 SM89 device 时必须 skip 并记录环境原因。 | `test_cuda_sm86_runtime_preflight_accepts_sm89`, `test_cuda_sm86_runtime_preflight_rejects_non_sm89`, `test_cuda_sm86_*_demo_runtime_cases` |
