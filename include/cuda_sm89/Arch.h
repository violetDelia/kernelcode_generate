/*
功能说明:
- 提供 CUDA SM89 后端 Arch 分层实现，承接 CUDA runtime 检查、host/device buffer glue、launch 与 block/thread/barrier wrapper。
- Core、Memory、Dma 与 Kernel 主体实现分别位于同名 backend header；本文件不再作为 monolithic implementation closure。

API 列表:
- `template <long long block, long long thread, long long subthread, long long shared_memory_size, auto name, typename Context, typename... Args> Status cuda_sm89::launch(Context& ctx, Args&&... args)`
- `__device__ S_INT cuda_sm89::block_id()`
- `__device__ S_INT cuda_sm89::thread_id()`
- `__device__ S_INT cuda_sm89::thread_num()`
- `__device__ void cuda_sm89::barrier()`

helper 清单:
- `cuda_sm89::detail::check_cuda(...)`
- `KG_CUDA_CHECK(expr)`
- `cuda_sm89::detail::device_alloc(...)`
- `cuda_sm89::detail::copy_host_to_device(...)`
- `cuda_sm89::detail::copy_device_to_host(...)`
- `cuda_sm89::detail::device_free(...)`

使用示例:
- #include "include/cuda_sm89/Arch.h"
- cuda_sm89::launch<1, 256, 1, 0, kernel>(ctx, slots, count);

关联文件:
- spec: spec/include/cuda_sm89/cuda_sm89.md
- 功能实现: include/cuda_sm89/cuda_sm89.cuh
- 功能实现: include/cuda_sm89/Kernel.h
- test: test/dsl/gen_kernel/emit/test_cuda_sm89_emit.py
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_CUDA_SM89_ARCH_H_
#define KERNELCODE_GENERATE_INCLUDE_CUDA_SM89_ARCH_H_

#include <cstdio>
#include <cstdlib>
#include <utility>

#include "include/api/Arch.h"
#include "include/cuda_sm89/Kernel.h"

namespace cuda_sm89 {
namespace detail {

/*
功能说明:
- 将 CUDA runtime API 返回值统一转换为 generated source 的稳定失败语义。
- 成功时直接返回；失败时输出 `cuda_runtime_failed`、CUDA 错误文本、调用位置和表达式后终止进程。
- 仅供 generated source 或 `cuda_sm89::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `cuda_sm89::detail::check_cuda(cudaGetLastError(), "cudaGetLastError()", __FILE__, __LINE__);`
*/
inline void check_cuda(cudaError_t status, const char *expr, const char *file, int line) {
  if (status == cudaSuccess) {
    return;
  }
  std::fprintf(stderr, "cuda_runtime_failed: %s at %s:%d for %s\n", cudaGetErrorString(status), file, line, expr);
  std::abort();
}

/*
功能说明:
- 为 generated source 内部调用 CUDA runtime API 提供简短检查入口。
- 宏只转发到 `cuda_sm89::detail::check_cuda`，不承载业务 kernel launch 或公开 API 语义。
- 仅供 generated source 或 `cuda_sm89::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `KG_CUDA_CHECK(cudaGetLastError());`
*/
#define KG_CUDA_CHECK(expr) ::cuda_sm89::detail::check_cuda((expr), #expr, __FILE__, __LINE__)


/*
功能说明:
- 为 generated source 按元素数量分配 CUDA device buffer。
- 元素数量为 0 时返回 `nullptr`；CUDA runtime 失败时通过 `KG_CUDA_CHECK` 终止。
- 仅供 generated source 或 `cuda_sm89::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `float *device = cuda_sm89::detail::device_alloc<float>(element_count);`
*/
template <typename T>
T *device_alloc(unsigned long long element_count) {
  if (element_count == 0) {
    return nullptr;
  }
  T *device_ptr = nullptr;
  KG_CUDA_CHECK(cudaMalloc(&device_ptr, static_cast<std::size_t>(element_count) * sizeof(T)));
  return device_ptr;
}

/*
功能说明:
- 将 host buffer 拷贝到 CUDA device buffer。
- 元素数量为 0 时不调用 CUDA runtime；否则按 `sizeof(T)` 计算字节数并检查 copy 结果。
- 仅供 generated source 或 `cuda_sm89::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `cuda_sm89::detail::copy_host_to_device(device_ptr, host_ptr, element_count);`
*/
template <typename T>
void copy_host_to_device(T *device_ptr, const T *host_ptr, unsigned long long element_count) {
  if (element_count == 0) {
    return;
  }
  KG_CUDA_CHECK(cudaMemcpy(device_ptr, host_ptr, static_cast<std::size_t>(element_count) * sizeof(T), cudaMemcpyHostToDevice));
}

/*
功能说明:
- 将 CUDA device buffer 拷贝回 host buffer。
- 元素数量为 0 时不调用 CUDA runtime；否则按 `sizeof(T)` 计算字节数并检查 copy 结果。
- 仅供 generated source 或 `cuda_sm89::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `cuda_sm89::detail::copy_device_to_host(host_ptr, device_ptr, element_count);`
*/
template <typename T>
void copy_device_to_host(T *host_ptr, const T *device_ptr, unsigned long long element_count) {
  if (element_count == 0) {
    return;
  }
  KG_CUDA_CHECK(cudaMemcpy(host_ptr, device_ptr, static_cast<std::size_t>(element_count) * sizeof(T), cudaMemcpyDeviceToHost));
}

/*
功能说明:
- 释放 generated source 内部持有的 CUDA device buffer。
- 指针为空时不调用 CUDA runtime；非空时通过 `KG_CUDA_CHECK` 检查释放结果。
- 仅供 generated source 或 `cuda_sm89::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `cuda_sm89::detail::device_free(device_ptr);`
*/
template <typename T>
void device_free(T *device_ptr) {
  if (device_ptr != nullptr) {
    KG_CUDA_CHECK(cudaFree(device_ptr));
  }
}


}  // namespace detail

/*
功能说明:
- 发起 hash 专属 generated CUDA kernel launch，承接 Draft 10 A1 public `cuda_sm89::launch` wrapper。
- wrapper 只使用显式 template extent，不查询设备能力、不推断 SM、不切换 target、不提供 fallback。
- `shared_memory_size` 非零时只按显式 template 值设置 CUDA dynamic shared memory opt-in，不修改 launch target。

使用示例:
- `cuda_sm89::launch<1, 256, 1, 49152, kernel>(ctx, slots, count);`
*/
template <long long block, long long thread, long long subthread, long long shared_memory_size, auto name, typename Context, typename... Args>
Status launch(Context &ctx, Args &&...args) {
  (void)ctx;
  if constexpr (block <= 0 || thread <= 0 || subthread != 1 || shared_memory_size < 0) {
    return kError;
  } else {
    dim3 grid(static_cast<unsigned int>(block));
    dim3 threads(static_cast<unsigned int>(thread));
    if constexpr (shared_memory_size > 0) {
      KG_CUDA_CHECK(cudaFuncSetAttribute(name, cudaFuncAttributeMaxDynamicSharedMemorySize, static_cast<int>(shared_memory_size)));
    }
    name<<<grid, threads, static_cast<unsigned int>(shared_memory_size)>>>(std::forward<Args>(args)...);
    KG_CUDA_CHECK(cudaGetLastError());
    KG_CUDA_CHECK(cudaDeviceSynchronize());
    return kOk;
  }
}

/*
功能说明:
- 返回当前 CUDA block x 轴索引，供 `arch.get_block_id` lowering 正向调用。
- 该 helper 是 device-side public wrapper，不做 runtime target selection。

使用示例:
- `S_INT bid = cuda_sm89::block_id();`
*/
__device__ inline S_INT block_id() {
  return static_cast<S_INT>(blockIdx.x);
}

/*
功能说明:
- 返回当前 CUDA thread x 轴索引，供 `arch.get_thread_id` lowering 正向调用。
- 该 helper 是 device-side public wrapper，不做 runtime target selection。

使用示例:
- `S_INT tid = cuda_sm89::thread_id();`
*/
__device__ inline S_INT thread_id() {
  return static_cast<S_INT>(threadIdx.x);
}

/*
功能说明:
- 返回当前 CUDA block 内 x 轴线程数，供 `arch.get_thread_num` lowering 正向调用。
- 该 helper 是 device-side public wrapper，不做 runtime target selection。

使用示例:
- `S_INT threads = cuda_sm89::thread_num();`
*/
__device__ inline S_INT thread_num() {
  return static_cast<S_INT>(blockDim.x);
}

/*
功能说明:
- 承接 CUDA block 内同步，供 generated device body 表达 barrier 语义。
- 当前 wrapper 只映射 `__syncthreads()`，不新增 scope/visibility public 参数。

使用示例:
- `cuda_sm89::barrier();`
*/
__device__ inline void barrier() {
  __syncthreads();
}


}  // namespace cuda_sm89

#endif  // KERNELCODE_GENERATE_INCLUDE_CUDA_SM89_ARCH_H_
