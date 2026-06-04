/*
功能说明:
- 提供 cuda_sm86 后端 Arch 第一版实现层，承接 generated CUDA source 需要的 slot ABI 与 runtime helper。
- 该文件由 `include/cuda_sm86/cuda_sm86.cuh` 聚合引入；跨 target 公开接口仍以 `include/api/Arch.h` 为真源。

API 列表:
- `struct cuda_sm86::ArgSlot`

helper 清单:
- `cuda_sm86::detail::*`：generated CUDA source 专用的 memory descriptor、alias/view、copy/fill/broadcast、math kernel helper、slot/scalar guard、host-device copy、device allocation、TF32 转换与 CUDA 错误检查。
- `KG_CUDA_CHECK(expr)`：generated CUDA source 内部使用的 CUDA runtime 检查宏。

使用示例:
- #include "include/cuda_sm86/cuda_sm86.cuh"
- extern "C" int kg_execute_entry(cuda_sm86::ArgSlot* slots, unsigned long long count);

关联文件:
- spec: spec/include/cuda_sm86/cuda_sm86.md
- 功能实现: include/cuda_sm86/cuda_sm86.cuh
- test: test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_CUDA_SM86_ARCH_H_
#define KERNELCODE_GENERATE_INCLUDE_CUDA_SM86_ARCH_H_

#include <cuda_runtime.h>

#include <cstddef>
#include <cstdio>
#include <cstdlib>

namespace cuda_sm86 {

struct ArgSlot {
  int kind;
  void *data;
  long long *shape;
  long long *stride;
  unsigned long long rank;
  int dtype_code;
  long long int_value;
  double float_value;
};

namespace detail {

struct MemoryDescriptor {
  void *data;
  const long long *shape;
  const long long *stride;
  unsigned long long rank;
  int dtype_code;
};

/*
功能说明:
- 将 CUDA runtime API 返回值统一转换为 generated source 的稳定失败语义。
- 成功时直接返回；失败时输出 `cuda_runtime_failed`、CUDA 错误文本、调用位置和表达式后终止进程。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `cuda_sm86::detail::check_cuda(cudaGetLastError(), "cudaGetLastError()", __FILE__, __LINE__);`
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
- 宏只转发到 `cuda_sm86::detail::check_cuda`，不承载业务 kernel launch 或公开 API 语义。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `KG_CUDA_CHECK(cudaGetLastError());`
*/
#define KG_CUDA_CHECK(expr) ::cuda_sm86::detail::check_cuda((expr), #expr, __FILE__, __LINE__)

/*
功能说明:
- 判断指定 slot 是否是 rank 匹配的 f32 memory 参数。
- generated source 用它在读取 memory slot 前校验 kind、dtype、rank、shape 和 stride 指针。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `if (!cuda_sm86::detail::is_f32_memory(slots, count, 0, 2)) { return -1; }`
*/
inline bool is_f32_memory(const ArgSlot *slots, unsigned long long count, unsigned long long index, unsigned long long rank) {
  return slots != nullptr && index < count && slots[index].kind == 1 && slots[index].dtype_code == 1 && slots[index].rank == rank &&
         slots[index].shape != nullptr && slots[index].stride != nullptr;
}

/*
功能说明:
- 判断指定 slot 是否是带非空 data 指针的 memory 参数。
- generated source 用它区分可拷贝 memory 与缺失或非 memory slot。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `if (!cuda_sm86::detail::has_memory_data(slots, count, 1)) { return -1; }`
*/
inline bool has_memory_data(const ArgSlot *slots, unsigned long long count, unsigned long long index) {
  return slots != nullptr && index < count && slots[index].kind == 1 && slots[index].data != nullptr;
}

/*
功能说明:
- 判断指定 slot 是否是整数标量参数。
- generated source 用它读取 runtime shape、stride 或 tile 相关整数参数前做 slot kind 校验。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `if (!cuda_sm86::detail::has_int_arg(slots, count, 3)) { return -1; }`
*/
inline bool has_int_arg(const ArgSlot *slots, unsigned long long count, unsigned long long index) {
  return slots != nullptr && index < count && slots[index].kind == 2;
}

/*
功能说明:
- 读取整数标量 slot；slot 缺失或 kind 不匹配时返回调用方给定默认值。
- generated source 用它处理可选 runtime 参数，避免把缺省值逻辑散落在各 kernel wrapper 中。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `long long stride = cuda_sm86::detail::int_arg_or(slots, count, 4, 1);`
*/
inline long long int_arg_or(const ArgSlot *slots, unsigned long long count, unsigned long long index, long long default_value) {
  if (!has_int_arg(slots, count, index)) {
    return default_value;
  }
  return slots[index].int_value;
}

/*
功能说明:
- 根据 memory slot 的 shape 计算元素总数；rank 为 0、shape 为空或任一维非正时返回 0。
- generated source 用它确定 device allocation 和 host/device copy 的元素数量。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `unsigned long long elems = cuda_sm86::detail::element_count(slots[0]);`
*/
inline unsigned long long element_count(const ArgSlot &slot) {
  if (slot.shape == nullptr || slot.rank == 0) {
    return 0;
  }
  unsigned long long result = 1;
  for (unsigned long long idx = 0; idx < slot.rank; ++idx) {
    if (slot.shape[idx] <= 0) {
      return 0;
    }
    result *= static_cast<unsigned long long>(slot.shape[idx]);
  }
  return result;
}

/*
功能说明:
- 将 public `ArgSlot` 转成 generated source 内部 memory descriptor。
- descriptor 只保存指针和元数据引用，不拥有底层内存。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `auto desc = cuda_sm86::detail::descriptor_from_slot(slots[0]);`
*/
inline MemoryDescriptor descriptor_from_slot(const ArgSlot &slot) {
  return MemoryDescriptor{slot.data, slot.shape, slot.stride, slot.rank, slot.dtype_code};
}

/*
功能说明:
- 构造 alias descriptor，用于 view / reinterpret / reshape 这类不复制数据的 final IR op。
- 调用方负责传入已计算好的 data 指针、shape、stride 和 rank。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `auto alias = cuda_sm86::detail::alias_descriptor(base.data, shape, stride, 2, base.dtype_code);`
*/
inline MemoryDescriptor alias_descriptor(void *data, const long long *shape, const long long *stride, unsigned long long rank, int dtype_code) {
  return MemoryDescriptor{data, shape, stride, rank, dtype_code};
}

/*
功能说明:
- 按 descriptor shape 计算元素数量。
- rank 为 0、shape 为空或任一维非正时返回 0。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `auto elems = cuda_sm86::detail::descriptor_element_count(desc);`
*/
inline unsigned long long descriptor_element_count(const MemoryDescriptor &desc) {
  if (desc.shape == nullptr || desc.rank == 0) {
    return 0;
  }
  unsigned long long result = 1;
  for (unsigned long long idx = 0; idx < desc.rank; ++idx) {
    if (desc.shape[idx] <= 0) {
      return 0;
    }
    result *= static_cast<unsigned long long>(desc.shape[idx]);
  }
  return result;
}

/*
功能说明:
- device 侧连续 copy helper，服务 `dma.copy` materialization。
- 调用方负责保证 source/target 至少包含 `element_count` 个元素。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `cuda_sm86::detail::copy_contiguous(dst, src, count);`
*/
template <typename T>
__device__ void copy_contiguous(T *target, const T *source, unsigned long long element_count) {
  for (unsigned long long index = static_cast<unsigned long long>(threadIdx.x); index < element_count; index += blockDim.x) {
    target[index] = source[index];
  }
}

/*
功能说明:
- device 侧连续 fill helper，服务 `dma.fill` materialization。
- 调用方负责保证 target 至少包含 `element_count` 个元素。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `cuda_sm86::detail::fill_contiguous(dst, 0.0f, count);`
*/
template <typename T>
__device__ void fill_contiguous(T *target, T value, unsigned long long element_count) {
  for (unsigned long long index = static_cast<unsigned long long>(threadIdx.x); index < element_count; index += blockDim.x) {
    target[index] = value;
  }
}

/*
功能说明:
- device 侧 row-vector broadcast helper，服务 9 demo 中的 `dma.broadcast` materialization。
- `cols` 表示 source row 长度，target 按 row-major `[rows, cols]` 写入。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `cuda_sm86::detail::broadcast_row_vector(dst, src, rows, cols);`
*/
template <typename T>
__device__ void broadcast_row_vector(T *target, const T *source, unsigned long long rows, unsigned long long cols) {
  const unsigned long long total = rows * cols;
  for (unsigned long long index = static_cast<unsigned long long>(threadIdx.x); index < total; index += blockDim.x) {
    target[index] = source[index % cols];
  }
}

/*
功能说明:
- device 侧 binary elewise helper，服务 `kernel.binary_elewise` 支持的 add/sub/mul/truediv/max。
- `kind` 取值由 generated source 静态生成，unsupported kind 不应调用本 helper。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `auto value = cuda_sm86::detail::binary_value(lhs, rhs, 0);`
*/
__device__ __forceinline__ float binary_value(float lhs, float rhs, int kind) {
  if (kind == 0) {
    return lhs + rhs;
  }
  if (kind == 1) {
    return lhs - rhs;
  }
  if (kind == 2) {
    return lhs * rhs;
  }
  if (kind == 3) {
    return lhs / rhs;
  }
  return lhs > rhs ? lhs : rhs;
}

/*
功能说明:
- 为 generated source 按元素数量分配 CUDA device buffer。
- 元素数量为 0 时返回 `nullptr`；CUDA runtime 失败时通过 `KG_CUDA_CHECK` 终止。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `float *device = cuda_sm86::detail::device_alloc<float>(element_count);`
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
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `cuda_sm86::detail::copy_host_to_device(device_ptr, host_ptr, element_count);`
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
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `cuda_sm86::detail::copy_device_to_host(host_ptr, device_ptr, element_count);`
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
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `cuda_sm86::detail::device_free(device_ptr);`
*/
template <typename T>
void device_free(T *device_ptr) {
  if (device_ptr != nullptr) {
    KG_CUDA_CHECK(cudaFree(device_ptr));
  }
}

/*
功能说明:
- 在 SM80 及以上 device code 中把 f32 值转换为 TF32 指令输入位型。
- 非支持架构编译路径返回 0，仅用于保持 host/device 编译可通过，不作为运行时数值路径。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `unsigned tf32_bits = cuda_sm86::detail::to_tf32(value);`
*/
__device__ __forceinline__ unsigned to_tf32(float value) {
  unsigned out;
#if defined(__CUDA_ARCH__) && (__CUDA_ARCH__ >= 800)
  asm volatile("cvt.rna.tf32.f32 %0, %1;" : "=r"(out) : "f"(value));
#else
  out = 0;
#endif
  return out;
}

}  // namespace detail
}  // namespace cuda_sm86

#endif  // KERNELCODE_GENERATE_INCLUDE_CUDA_SM86_ARCH_H_
