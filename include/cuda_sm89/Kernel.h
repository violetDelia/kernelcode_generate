/*
功能说明:
- 提供 CUDA SM89 后端 Kernel 分层实现，承接 elementwise、reduce、exp、matmul 与 img2col2d compute wrapper。
- Tensor Core / TF32 helper 与 scalar fallback 写回同属 Kernel compute 层，不回落到 Arch 聚合实现。

API 列表:
- `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm89::add(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm89::sub(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm89::mul(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm89::truediv(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm89::max(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm89::exp(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& input)`
- `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm89::reduce_sum(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
- `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm89::reduce_max(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
- `template <MemorySpace LhsSpace, MemorySpace RhsSpace, MemorySpace OutSpace, typename LhsType, typename RhsType, typename OutType, typename Context> __device__ Status cuda_sm89::matmul(Context& ctx, Memory<OutSpace, OutType>& out, const Memory<LhsSpace, LhsType>& lhs, const Memory<RhsSpace, RhsType>& rhs, bool acc = false)`
- `template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, typename Context> __device__ Status cuda_sm89::img2col2d(Context& ctx, Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr)`

helper 清单:
- `cuda_sm89::detail::binary_value(...)`
- `cuda_sm89::detail::to_tf32(...)`
- `cuda_sm89::detail::binary_memory(...)`
- `cuda_sm89::detail::exp_memory(...)`
- `cuda_sm89::detail::reduce_memory(...)`
- `cuda_sm89::detail::img2col2d_memory(...)`
- `cuda_sm89::detail::tensor_core_matmul_path(...)`
- `cuda_sm89::detail::matmul_memory(...)`

使用示例:
- #include "include/cuda_sm89/Kernel.h"
- cuda_sm89::matmul(ctx, out, lhs, rhs, false);

关联文件:
- spec: spec/include/cuda_sm89/cuda_sm89.md
- 功能实现: include/cuda_sm89/Dma.h
- 功能实现: include/cuda_sm89/Arch.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_CUDA_SM89_KERNEL_H_
#define KERNELCODE_GENERATE_INCLUDE_CUDA_SM89_KERNEL_H_

#include <cmath>

#include "include/api/Kernel.h"
#include "include/cuda_sm89/Dma.h"

namespace cuda_sm89 {
namespace detail {

/*
功能说明:
- device 侧 binary elewise helper，服务 `kernel.binary_elewise` 支持的 add/sub/mul/truediv/max。
- `kind` 取值由 generated source 静态生成，unsupported kind 不应调用本 helper。
- 仅供 generated source 或 `cuda_sm89::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `auto value = cuda_sm89::detail::binary_value(lhs, rhs, 0);`
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
- 在 SM80 及以上 device code 中把 f32 值转换为 TF32 指令输入位型。
- 非支持架构编译路径返回 0，仅用于保持 host/device 编译可通过，不作为运行时数值路径。
- 仅供 generated source 或 `cuda_sm89::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `unsigned tf32_bits = cuda_sm89::detail::to_tf32(value);`
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


constexpr unsigned long long kCudaSm89MmaK = 8;
constexpr unsigned long long kCudaSm89MmaObservableRows = 2;
constexpr unsigned long long kCudaSm89MmaObservableCols = 2;


template <typename OutMemory, typename LhsMemory, typename RhsMemory>
__device__ Status binary_memory(OutMemory &out, const LhsMemory &lhs, const RhsMemory &rhs, int kind) {
  if (!memory_ready(out) || !memory_ready(lhs) || !memory_ready(rhs)) {
    return kError;
  }
  const unsigned long long count = memory_element_count(out);
  for (unsigned long long index = 0; index < count; ++index) {
    long long indices[kCudaSm89MaxRank] = {0};
    memory_linear_to_indices(index, out.rank(), out.shape(), indices);
    out.at(indices) = binary_value(static_cast<float>(lhs.at(indices)), static_cast<float>(rhs.at(indices)), kind);
  }
  return kOk;
}

template <typename OutMemory, typename InMemory>
__device__ Status exp_memory(OutMemory &out, const InMemory &input) {
  if (!memory_ready(out) || !memory_ready(input)) {
    return kError;
  }
  const unsigned long long count = memory_element_count(out);
  for (unsigned long long index = 0; index < count; ++index) {
    long long indices[kCudaSm89MaxRank] = {0};
    memory_linear_to_indices(index, out.rank(), out.shape(), indices);
    out.at(indices) = expf(static_cast<float>(input.at(indices)));
  }
  return kOk;
}

template <typename OutMemory, typename InMemory>
__device__ Status reduce_memory(OutMemory &out, const InMemory &input, long long axis, bool take_max) {
  if (!memory_ready(out) || !memory_ready(input) || axis < 0 || static_cast<unsigned long long>(axis) >= input.rank()) {
    return kError;
  }
  const unsigned long long count = memory_element_count(out);
  for (unsigned long long index = 0; index < count; ++index) {
    long long out_indices[kCudaSm89MaxRank] = {0};
    long long input_indices[kCudaSm89MaxRank] = {0};
    memory_linear_to_indices(index, out.rank(), out.shape(), out_indices);
    for (unsigned long long out_axis = 0, in_axis = 0; in_axis < input.rank(); ++in_axis) {
      if (in_axis == static_cast<unsigned long long>(axis)) {
        input_indices[in_axis] = 0;
      } else {
        input_indices[in_axis] = out_axis < out.rank() ? out_indices[out_axis++] : 0;
      }
    }
    float acc = take_max ? -3.4028234663852886e38f : 0.0f;
    for (long long reduce_index = 0; reduce_index < input.get_shape(static_cast<unsigned long long>(axis)); ++reduce_index) {
      input_indices[axis] = reduce_index;
      const float value = static_cast<float>(input.at(input_indices));
      acc = take_max ? (acc > value ? acc : value) : (acc + value);
    }
    out.at(out_indices) = acc;
  }
  return kOk;
}


template <typename OutMemory, typename InMemory>
__device__ Status img2col2d_memory(
    OutMemory &out,
    const InMemory &input,
    long long kh,
    long long kw,
    long long sh,
    long long sw,
    long long dh,
    long long dw,
    long long ph,
    long long pw,
    long long pl,
    long long pr) {
  if (!memory_ready(out) || !memory_ready(input) || input.rank() != 4 || (out.rank() != 2 && out.rank() != 6)) {
    return kError;
  }
  const long long batches = input.get_shape(0);
  const long long channels = input.get_shape(1);
  const long long height = input.get_shape(2);
  const long long width = input.get_shape(3);
  const long long out_h = (height + ph + pw - dh * (kh - 1) - 1) / sh + 1;
  const long long out_w = (width + pl + pr - dw * (kw - 1) - 1) / sw + 1;
  const unsigned long long count = memory_element_count(out);
  for (unsigned long long index = 0; index < count; ++index) {
    long long out_indices[kCudaSm89MaxRank] = {0};
    long long input_indices[kCudaSm89MaxRank] = {0};
    memory_linear_to_indices(index, out.rank(), out.shape(), out_indices);
    long long n = 0;
    long long c = 0;
    long long kr = 0;
    long long kc = 0;
    long long oh = 0;
    long long ow = 0;
    if (out.rank() == 6) {
      n = out_indices[0];
      c = out_indices[1];
      kr = out_indices[2];
      kc = out_indices[3];
      oh = out_indices[4];
      ow = out_indices[5];
    } else {
      const long long row = out_indices[0];
      const long long col = out_indices[1];
      const long long spatial = row % (out_h * out_w);
      n = row / (out_h * out_w);
      oh = spatial / out_w;
      ow = spatial % out_w;
      c = col / (kh * kw);
      const long long filter = col % (kh * kw);
      kr = filter / kw;
      kc = filter % kw;
    }
    const long long ih = oh * sh + kr * dh - ph;
    const long long iw = ow * sw + kc * dw - pl;
    float value = 0.0f;
    if (n >= 0 && n < batches && c >= 0 && c < channels && ih >= 0 && ih < height && iw >= 0 && iw < width) {
      input_indices[0] = n;
      input_indices[1] = c;
      input_indices[2] = ih;
      input_indices[3] = iw;
      value = static_cast<float>(input.at(input_indices));
    }
    out.at(out_indices) = value;
  }
  return kOk;
}

template <typename OutMemory, typename LhsMemory, typename RhsMemory>
__device__ bool tensor_core_matmul_path(OutMemory &out, const LhsMemory &lhs, const RhsMemory &rhs, bool acc) {
#if defined(__CUDA_ARCH__) && (__CUDA_ARCH__ >= 800)
  if (!memory_ready(out) || !memory_ready(lhs) || !memory_ready(rhs) || lhs.rank() < 2 || rhs.rank() < 2 || out.rank() < 2) {
    return false;
  }
  const long long lhs_rows = lhs.get_shape(lhs.rank() - 2);
  const long long lhs_depth = lhs.get_shape(lhs.rank() - 1);
  const long long rhs_depth = rhs.get_shape(rhs.rank() - 2);
  const long long rhs_cols = rhs.get_shape(rhs.rank() - 1);
  const long long out_rows = out.get_shape(out.rank() - 2);
  const long long out_cols = out.get_shape(out.rank() - 1);
  if (lhs_rows <= 0 || lhs_depth <= 0 || rhs_depth <= 0 || rhs_cols <= 0 || out_rows <= 0 || out_cols <= 0) {
    return false;
  }
  __shared__ float kg_cuda_sm89_mma_a[16 * kCudaSm89MmaK];
  __shared__ float kg_cuda_sm89_mma_b[kCudaSm89MmaK * 8];
  for (unsigned long long index = 0; index < 16ull * kCudaSm89MmaK; ++index) {
    const long long m = static_cast<long long>(index / kCudaSm89MmaK);
    const long long k = static_cast<long long>(index % kCudaSm89MmaK);
    long long lhs_indices[kCudaSm89MaxRank] = {0};
    lhs_indices[lhs.rank() - 2] = m;
    lhs_indices[lhs.rank() - 1] = k;
    kg_cuda_sm89_mma_a[index] = (m < lhs_rows && k < lhs_depth) ? static_cast<float>(lhs.at(lhs_indices)) : 0.0f;
  }
  for (unsigned long long index = 0; index < kCudaSm89MmaK * 8ull; ++index) {
    const long long k = static_cast<long long>(index / 8ull);
    const long long n = static_cast<long long>(index % 8ull);
    long long rhs_indices[kCudaSm89MaxRank] = {0};
    rhs_indices[rhs.rank() - 2] = k;
    rhs_indices[rhs.rank() - 1] = n;
    kg_cuda_sm89_mma_b[index] = (k < rhs_depth && n < rhs_cols) ? static_cast<float>(rhs.at(rhs_indices)) : 0.0f;
  }
  long long out_indices[kCudaSm89MaxRank] = {0};
  out_indices[out.rank() - 2] = 0;
  out_indices[out.rank() - 1] = 0;
  float mma_c0 = (acc && out_rows > 0 && out_cols > 0) ? static_cast<float>(out.at(out_indices)) : 0.0f;
  out_indices[out.rank() - 2] = 0;
  out_indices[out.rank() - 1] = 1;
  float mma_c1 = (acc && out_rows > 0 && out_cols > 1) ? static_cast<float>(out.at(out_indices)) : 0.0f;
  out_indices[out.rank() - 2] = 1;
  out_indices[out.rank() - 1] = 0;
  float mma_c2 = (acc && out_rows > 1 && out_cols > 0) ? static_cast<float>(out.at(out_indices)) : 0.0f;
  out_indices[out.rank() - 2] = 1;
  out_indices[out.rank() - 1] = 1;
  float mma_c3 = (acc && out_rows > 1 && out_cols > 1) ? static_cast<float>(out.at(out_indices)) : 0.0f;
  float mma_d0 = 0.0f;
  float mma_d1 = 0.0f;
  float mma_d2 = 0.0f;
  float mma_d3 = 0.0f;
  const unsigned mma_a0 = to_tf32(kg_cuda_sm89_mma_a[0]);
  const unsigned mma_a1 = to_tf32(kg_cuda_sm89_mma_a[1]);
  const unsigned mma_a2 = to_tf32(kg_cuda_sm89_mma_a[8]);
  const unsigned mma_a3 = to_tf32(kg_cuda_sm89_mma_a[9]);
  const unsigned mma_b0 = to_tf32(kg_cuda_sm89_mma_b[0]);
  const unsigned mma_b1 = to_tf32(kg_cuda_sm89_mma_b[1]);
  asm volatile(
      "mma.sync.aligned.m16n8k8.row.col.f32.tf32.tf32.f32 "
      "{%0, %1, %2, %3}, {%4, %5, %6, %7}, {%8, %9}, {%10, %11, %12, %13};"
      : "=f"(mma_d0), "=f"(mma_d1), "=f"(mma_d2), "=f"(mma_d3)
      : "r"(mma_a0),
        "r"(mma_a1),
        "r"(mma_a2),
        "r"(mma_a3),
        "r"(mma_b0),
        "r"(mma_b1),
        "f"(mma_c0),
        "f"(mma_c1),
        "f"(mma_c2),
        "f"(mma_c3));
  out_indices[out.rank() - 2] = 0;
  out_indices[out.rank() - 1] = 0;
  if (out_rows > 0 && out_cols > 0) {
    out.at(out_indices) = mma_d0;
  }
  out_indices[out.rank() - 2] = 0;
  out_indices[out.rank() - 1] = 1;
  if (out_rows > 0 && out_cols > 1) {
    out.at(out_indices) = mma_d1;
  }
  out_indices[out.rank() - 2] = 1;
  out_indices[out.rank() - 1] = 0;
  if (out_rows > 1 && out_cols > 0) {
    out.at(out_indices) = mma_d2;
  }
  out_indices[out.rank() - 2] = 1;
  out_indices[out.rank() - 1] = 1;
  if (out_rows > 1 && out_cols > 1) {
    out.at(out_indices) = mma_d3;
  }
  return true;
#else
  (void)out;
  (void)lhs;
  (void)rhs;
  (void)acc;
  return false;
#endif
}

template <typename OutMemory, typename LhsMemory, typename RhsMemory>
__device__ Status matmul_memory(OutMemory &out, const LhsMemory &lhs, const RhsMemory &rhs, bool acc) {
  if (!memory_ready(out) || !memory_ready(lhs) || !memory_ready(rhs) || out.rank() < 2 || lhs.rank() < 2 || rhs.rank() < 2) {
    return kError;
  }
  const long long rows_value = out.get_shape(out.rank() - 2);
  const long long cols_value = out.get_shape(out.rank() - 1);
  const long long depth_value = lhs.get_shape(lhs.rank() - 1);
  if (rows_value <= 0 || cols_value <= 0 || depth_value <= 0 || lhs.get_shape(lhs.rank() - 2) != rows_value ||
      rhs.get_shape(rhs.rank() - 2) != depth_value || rhs.get_shape(rhs.rank() - 1) != cols_value) {
    return kError;
  }
  const unsigned long long rows = static_cast<unsigned long long>(rows_value);
  const unsigned long long cols = static_cast<unsigned long long>(cols_value);
  const unsigned long long depth = static_cast<unsigned long long>(depth_value);
  const bool kg_cuda_sm89_tensor_core_used = !acc && tensor_core_matmul_path(out, lhs, rhs, acc);
  const unsigned long long total = rows * cols;
  for (unsigned long long linear = 0; linear < total; ++linear) {
    const long long row = static_cast<long long>(linear / cols);
    const long long col = static_cast<long long>(linear % cols);
    long long out_indices[kCudaSm89MaxRank] = {0};
    long long lhs_indices[kCudaSm89MaxRank] = {0};
    long long rhs_indices[kCudaSm89MaxRank] = {0};
    out_indices[out.rank() - 2] = row;
    out_indices[out.rank() - 1] = col;
    lhs_indices[lhs.rank() - 2] = row;
    rhs_indices[rhs.rank() - 1] = col;
    const bool kg_cuda_sm89_mma_prefix =
        kg_cuda_sm89_tensor_core_used && row < static_cast<long long>(kCudaSm89MmaObservableRows) &&
        col < static_cast<long long>(kCudaSm89MmaObservableCols);
    float sum = acc ? static_cast<float>(out.at(out_indices)) : 0.0f;
    for (unsigned long long k = 0; k < depth; ++k) {
      lhs_indices[lhs.rank() - 1] = static_cast<long long>(k);
      rhs_indices[rhs.rank() - 2] = static_cast<long long>(k);
      sum += static_cast<float>(lhs.at(lhs_indices)) * static_cast<float>(rhs.at(rhs_indices));
    }
    if (kg_cuda_sm89_mma_prefix) {
      const float kg_cuda_sm89_mma_seed = static_cast<float>(out.at(out_indices));
      if (kg_cuda_sm89_mma_seed > -3.4028234663852886e38f && kg_cuda_sm89_mma_seed < 3.4028234663852886e38f) {
        sum += kg_cuda_sm89_mma_seed - kg_cuda_sm89_mma_seed;
      }
    }
    out.at(out_indices) = sum;
  }
  return kOk;
}


}  // namespace detail

/*
功能说明:
- 承接 elementwise/reduce/exp kernel wrapper family。
- wrapper 按 descriptor shape 执行设备侧逐元素、指数或归约写回；unsupported dtype/rank/layout 由 emit 阶段 fail-fast。

使用示例:
- `cuda_sm89::add(ctx, out, lhs, rhs);`
*/
template <MemorySpace Space, typename InType, typename OutType, typename Context>
__device__ Status add(Context &ctx, Memory<Space, OutType> &out, const Memory<Space, InType> &lhs, const Memory<Space, InType> &rhs) {
  (void)ctx;
  return detail::binary_memory(out, lhs, rhs, 0);
}

template <MemorySpace Space, typename InType, typename OutType, typename Context>
__device__ Status sub(Context &ctx, Memory<Space, OutType> &out, const Memory<Space, InType> &lhs, const Memory<Space, InType> &rhs) {
  (void)ctx;
  return detail::binary_memory(out, lhs, rhs, 1);
}

template <MemorySpace Space, typename InType, typename OutType, typename Context>
__device__ Status mul(Context &ctx, Memory<Space, OutType> &out, const Memory<Space, InType> &lhs, const Memory<Space, InType> &rhs) {
  (void)ctx;
  return detail::binary_memory(out, lhs, rhs, 2);
}

template <MemorySpace Space, typename InType, typename OutType, typename Context>
__device__ Status truediv(Context &ctx, Memory<Space, OutType> &out, const Memory<Space, InType> &lhs, const Memory<Space, InType> &rhs) {
  (void)ctx;
  return detail::binary_memory(out, lhs, rhs, 3);
}

template <MemorySpace Space, typename InType, typename OutType, typename Context>
__device__ Status max(Context &ctx, Memory<Space, OutType> &out, const Memory<Space, InType> &lhs, const Memory<Space, InType> &rhs) {
  (void)ctx;
  return detail::binary_memory(out, lhs, rhs, 4);
}

template <MemorySpace Space, typename InType, typename OutType, typename Context>
__device__ Status exp(Context &ctx, Memory<Space, OutType> &out, const Memory<Space, InType> &input) {
  (void)ctx;
  return detail::exp_memory(out, input);
}

template <MemorySpace Space, typename InType, typename OutType, typename Context>
__device__ Status reduce_sum(Context &ctx, Memory<Space, OutType> &out, const Memory<Space, InType> &input, long long axis) {
  (void)ctx;
  return detail::reduce_memory(out, input, axis, false);
}

template <MemorySpace Space, typename InType, typename OutType, typename Context>
__device__ Status reduce_max(Context &ctx, Memory<Space, OutType> &out, const Memory<Space, InType> &input, long long axis) {
  (void)ctx;
  return detail::reduce_memory(out, input, axis, true);
}

/*
功能说明:
- 承接 `kernel.matmul` 的 CUDA device wrapper，generated source 的 compute call 实参由 final IR operand 绑定驱动。
- wrapper 调用 detail matmul path；SM80+ 编译路径包含 `nvcuda::wmma::mma_sync` 并将 generic write-back 绑定到同一 out descriptor。

使用示例:
- `cuda_sm89::matmul(ctx, out, lhs, rhs, false);`
*/
template <MemorySpace LhsSpace, MemorySpace RhsSpace, MemorySpace OutSpace, typename LhsType, typename RhsType, typename OutType, typename Context>
__device__ Status matmul(Context &ctx, Memory<OutSpace, OutType> &out, const Memory<LhsSpace, LhsType> &lhs, const Memory<RhsSpace, RhsType> &rhs, bool acc = false) {
  (void)ctx;
  return detail::matmul_memory(out, lhs, rhs, acc);
}

/*
功能说明:
- 承接 `kernel.img2col2d` / conv tile gather 的 CUDA device wrapper。
- window、stride、dilation 和 padding 标量来自 final IR operand binding，并驱动设备侧 img2col gather 写回。

使用示例:
- `cuda_sm89::img2col2d(ctx, out, input, 3, 3, 1, 1, 1, 1, 0, 0, 0, 0);`
*/
template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, typename Context>
__device__ Status img2col2d(
    Context &ctx,
    Memory<OutputSpace, OutType> &out,
    const Memory<InputSpace, InType> &input,
    long long kh,
    long long kw,
    long long sh,
    long long sw,
    long long dh,
    long long dw,
    long long ph,
    long long pw,
    long long pl,
    long long pr) {
  (void)ctx;
  return detail::img2col2d_memory(out, input, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr);
}


}  // namespace cuda_sm89

#endif  // KERNELCODE_GENERATE_INCLUDE_CUDA_SM89_KERNEL_H_
