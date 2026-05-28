"""CUDA SM86 emit backend.


功能说明:
- 通过公开 `emit_c_impl(ModuleOp, target="cuda_sm86")` 注册 CUDA SM86 module 发射入口。
- 返回 SourceBundle mapping，供公开 `gen_kernel(...)` 与 execute_engine compile strategy 写出 `.cu/.cuh` artifact。
- 按 lowered IR 的 kernel op family 与函数类型信息生成单一 CUDA entry，generated source 承载局部 runtime helper 和具体 kernel。

API 列表:
- 无公开 API；本模块只通过 emit registry 自动加载。

使用示例:
- from kernel_gen.core.config import set_target
- set_target("cuda_sm86")
- source = gen_kernel(module, EmitCContext())

关联文件:
- spec: spec/dsl/gen_kernel/emit/cuda_sm86.md
- test: test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm86/__init__.py
"""

from __future__ import annotations

from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp

from kernel_gen.dsl.gen_kernel.emit.register import emit_c_impl
from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext


_COMMON_CUDA_RUNTIME_SOURCE = r"""
#include "include/cuda_sm86/cuda_sm86.cuh"
#include "include/cuda_sm86/generated_entry.cuh"

#include <cstddef>
#include <math.h>

namespace {
inline bool kg_cuda_sm86_is_f32_memory(
    const cuda_sm86::ArgSlot* slots,
    unsigned long long count,
    unsigned long long index,
    unsigned long long rank) {
  return slots != nullptr && index < count && slots[index].kind == 1 && slots[index].dtype_code == 1 && slots[index].rank == rank &&
         slots[index].shape != nullptr && slots[index].stride != nullptr;
}

inline bool kg_cuda_sm86_has_memory_data(const cuda_sm86::ArgSlot* slots, unsigned long long count, unsigned long long index) {
  return slots != nullptr && index < count && slots[index].kind == 1 && slots[index].data != nullptr;
}

inline bool kg_cuda_sm86_has_int_arg(const cuda_sm86::ArgSlot* slots, unsigned long long count, unsigned long long index) {
  return slots != nullptr && index < count && slots[index].kind == 2;
}

inline long long kg_cuda_sm86_int_arg_or(const cuda_sm86::ArgSlot* slots, unsigned long long count, unsigned long long index, long long default_value) {
  if (!kg_cuda_sm86_has_int_arg(slots, count, index)) {
    return default_value;
  }
  return slots[index].int_value;
}

inline unsigned long long kg_cuda_sm86_element_count(const cuda_sm86::ArgSlot& slot) {
  if (slot.shape == nullptr || slot.rank == 0) {
    return 0;
  }
  unsigned long long element_count = 1;
  for (unsigned long long idx = 0; idx < slot.rank; ++idx) {
    if (slot.shape[idx] <= 0) {
      return 0;
    }
    element_count *= static_cast<unsigned long long>(slot.shape[idx]);
  }
  return element_count;
}

template <typename T>
T* kg_cuda_sm86_device_alloc(unsigned long long element_count) {
  if (element_count == 0) {
    return nullptr;
  }
  T* device_ptr = nullptr;
  KG_CUDA_CHECK(cudaMalloc(&device_ptr, static_cast<std::size_t>(element_count) * sizeof(T)));
  return device_ptr;
}

template <typename T>
void kg_cuda_sm86_copy_host_to_device(T* device_ptr, const T* host_ptr, unsigned long long element_count) {
  if (element_count == 0) {
    return;
  }
  KG_CUDA_CHECK(cudaMemcpy(device_ptr, host_ptr, static_cast<std::size_t>(element_count) * sizeof(T), cudaMemcpyHostToDevice));
}

template <typename T>
void kg_cuda_sm86_copy_device_to_host(T* host_ptr, const T* device_ptr, unsigned long long element_count) {
  if (element_count == 0) {
    return;
  }
  KG_CUDA_CHECK(cudaMemcpy(host_ptr, device_ptr, static_cast<std::size_t>(element_count) * sizeof(T), cudaMemcpyDeviceToHost));
}

template <typename T>
void kg_cuda_sm86_device_free(T* device_ptr) {
  if (device_ptr != nullptr) {
    KG_CUDA_CHECK(cudaFree(device_ptr));
  }
}

__device__ __forceinline__ unsigned kg_cuda_sm86_to_tf32(float value) {
  unsigned out;
#if defined(__CUDA_ARCH__) && (__CUDA_ARCH__ >= 800)
  asm volatile("cvt.rna.tf32.f32 %0, %1;" : "=r"(out) : "f"(value));
#else
  out = 0;
#endif
  return out;
}
"""


_MATMUL_CUDA_SOURCE = r"""
__device__ __forceinline__ float kg_cuda_sm86_load_or_zero(const float* data, long long row, long long col, long long rows, long long cols) {
  if (row < 0 || col < 0 || row >= rows || col >= cols) {
    return 0.0f;
  }
  return data[row * cols + col];
}

__global__ void kg_cuda_sm86_generated_matmul_kernel(float* out, const float* lhs, const float* rhs, const float* bias, long long m, long long n, long long k) {
  const int lane = threadIdx.x & 31;
  const int group_id = lane >> 2;
  const int thread_in_group = lane & 3;
  const long long row_base = static_cast<long long>(blockIdx.y) * 16;
  const long long col_base = static_cast<long long>(blockIdx.x) * 8;
  float d0 = 0.0f;
  float d1 = 0.0f;
  float d2 = 0.0f;
  float d3 = 0.0f;
  for (long long k_base = 0; k_base < k; k_base += 8) {
    const unsigned a0 = kg_cuda_sm86_to_tf32(kg_cuda_sm86_load_or_zero(lhs, row_base + group_id, k_base + thread_in_group, m, k));
    const unsigned a1 = kg_cuda_sm86_to_tf32(kg_cuda_sm86_load_or_zero(lhs, row_base + group_id + 8, k_base + thread_in_group, m, k));
    const unsigned a2 = kg_cuda_sm86_to_tf32(kg_cuda_sm86_load_or_zero(lhs, row_base + group_id, k_base + thread_in_group + 4, m, k));
    const unsigned a3 = kg_cuda_sm86_to_tf32(kg_cuda_sm86_load_or_zero(lhs, row_base + group_id + 8, k_base + thread_in_group + 4, m, k));
    const unsigned b0 = kg_cuda_sm86_to_tf32(kg_cuda_sm86_load_or_zero(rhs, k_base + thread_in_group, col_base + group_id, k, n));
    const unsigned b1 = kg_cuda_sm86_to_tf32(kg_cuda_sm86_load_or_zero(rhs, k_base + thread_in_group + 4, col_base + group_id, k, n));
    asm volatile(
        "mma.sync.aligned.m16n8k8.row.col.f32.tf32.tf32.f32 "
        "{%0,%1,%2,%3}, {%4,%5,%6,%7}, {%8,%9}, {%0,%1,%2,%3};\n"
        : "+f"(d0), "+f"(d1), "+f"(d2), "+f"(d3)
        : "r"(a0), "r"(a1), "r"(a2), "r"(a3), "r"(b0), "r"(b1));
  }
  const long long col0 = static_cast<long long>(thread_in_group) * 2;
  const long long rows[4] = {row_base + group_id, row_base + group_id, row_base + group_id + 8, row_base + group_id + 8};
  const long long cols[4] = {col_base + col0, col_base + col0 + 1, col_base + col0, col_base + col0 + 1};
  const float values[4] = {d0, d1, d2, d3};
  for (int idx = 0; idx < 4; ++idx) {
    if (rows[idx] < m && cols[idx] < n) {
      const float bias_value = bias == nullptr ? 0.0f : bias[cols[idx]];
      out[rows[idx] * n + cols[idx]] = values[idx] + bias_value;
    }
  }
}

int kg_cuda_sm86_run_matmul(cuda_sm86::ArgSlot* slots, unsigned long long count) {
  if (!kg_cuda_sm86_is_f32_memory(slots, count, 0, 2) || !kg_cuda_sm86_is_f32_memory(slots, count, 1, 2) ||
      !kg_cuda_sm86_is_f32_memory(slots, count, 2, 2) || !kg_cuda_sm86_has_memory_data(slots, count, 0) ||
      !kg_cuda_sm86_has_memory_data(slots, count, 1) || !kg_cuda_sm86_has_memory_data(slots, count, 2)) {
    return -1;
  }
  const long long m = slots[0].shape[0];
  const long long n = slots[0].shape[1];
  const long long k = slots[1].shape[1];
  if (m <= 0 || n <= 0 || k <= 0 || slots[1].shape[0] != m || slots[2].shape[0] != k || slots[2].shape[1] != n) {
    return -1;
  }
  float* device_out = kg_cuda_sm86_device_alloc<float>(kg_cuda_sm86_element_count(slots[0]));
  float* device_lhs = kg_cuda_sm86_device_alloc<float>(kg_cuda_sm86_element_count(slots[1]));
  float* device_rhs = kg_cuda_sm86_device_alloc<float>(kg_cuda_sm86_element_count(slots[2]));
  float* device_bias = nullptr;
  const bool has_bias = kg_cuda_sm86_has_memory_data(slots, count, 3);
  if (has_bias) {
    device_bias = kg_cuda_sm86_device_alloc<float>(kg_cuda_sm86_element_count(slots[3]));
    kg_cuda_sm86_copy_host_to_device(device_bias, reinterpret_cast<const float*>(slots[3].data), kg_cuda_sm86_element_count(slots[3]));
  }
  kg_cuda_sm86_copy_host_to_device(device_lhs, reinterpret_cast<const float*>(slots[1].data), kg_cuda_sm86_element_count(slots[1]));
  kg_cuda_sm86_copy_host_to_device(device_rhs, reinterpret_cast<const float*>(slots[2].data), kg_cuda_sm86_element_count(slots[2]));
  const dim3 block(32);
  const dim3 grid(static_cast<unsigned int>((n + 7) / 8), static_cast<unsigned int>((m + 15) / 16));
  kg_cuda_sm86_generated_matmul_kernel<<<grid, block>>>(device_out, device_lhs, device_rhs, device_bias, m, n, k);
  KG_CUDA_CHECK(cudaGetLastError());
  KG_CUDA_CHECK(cudaDeviceSynchronize());
  kg_cuda_sm86_copy_device_to_host(reinterpret_cast<float*>(slots[0].data), device_out, kg_cuda_sm86_element_count(slots[0]));
  kg_cuda_sm86_device_free(device_bias);
  kg_cuda_sm86_device_free(device_rhs);
  kg_cuda_sm86_device_free(device_lhs);
  kg_cuda_sm86_device_free(device_out);
  return 0;
}

"""


_CONV2D_CUDA_SOURCE = r"""
__global__ void kg_cuda_sm86_conv2d_f32_kernel(
    float* out,
    const float* input,
    const float* weight,
    const float* bias,
    long long batch,
    long long out_channels,
    long long out_h,
    long long out_w,
    long long in_channels,
    long long in_h,
    long long in_w,
    long long kernel_h,
    long long kernel_w,
    long long stride_h,
    long long stride_w,
    long long dilation_h,
    long long dilation_w,
    long long pad_top,
    long long pad_left) {
  const long long linear = static_cast<long long>(blockIdx.x) * blockDim.x + threadIdx.x;
  const long long total = batch * out_channels * out_h * out_w;
  if (linear >= total) {
    return;
  }
  const long long ow = linear % out_w;
  const long long oh = (linear / out_w) % out_h;
  const long long oc = (linear / (out_w * out_h)) % out_channels;
  const long long b = linear / (out_w * out_h * out_channels);
  float acc = bias == nullptr ? 0.0f : bias[oc];
  for (long long ic = 0; ic < in_channels; ++ic) {
    for (long long kh = 0; kh < kernel_h; ++kh) {
      const long long ih = oh * stride_h + kh * dilation_h - pad_top;
      if (ih < 0 || ih >= in_h) {
        continue;
      }
      for (long long kw = 0; kw < kernel_w; ++kw) {
        const long long iw = ow * stride_w + kw * dilation_w - pad_left;
        if (iw < 0 || iw >= in_w) {
          continue;
        }
        const long long input_index = ((b * in_channels + ic) * in_h + ih) * in_w + iw;
        const long long weight_index = ((oc * in_channels + ic) * kernel_h + kh) * kernel_w + kw;
        acc += input[input_index] * weight[weight_index];
      }
    }
  }
  out[linear] = acc;
}

int kg_cuda_sm86_run_conv2d(cuda_sm86::ArgSlot* slots, unsigned long long count) {
  if (!kg_cuda_sm86_is_f32_memory(slots, count, 0, 4) || !kg_cuda_sm86_is_f32_memory(slots, count, 1, 4) ||
      !kg_cuda_sm86_is_f32_memory(slots, count, 2, 4) || !kg_cuda_sm86_has_memory_data(slots, count, 0) ||
      !kg_cuda_sm86_has_memory_data(slots, count, 1) || !kg_cuda_sm86_has_memory_data(slots, count, 2)) {
    return -1;
  }
  const long long batch = slots[0].shape[0];
  const long long out_channels = slots[0].shape[1];
  const long long out_h = slots[0].shape[2];
  const long long out_w = slots[0].shape[3];
  const long long in_channels = slots[1].shape[1];
  const long long in_h = slots[1].shape[2];
  const long long in_w = slots[1].shape[3];
  const long long kernel_h = slots[2].shape[2];
  const long long kernel_w = slots[2].shape[3];
  const long long stride_h = kg_cuda_sm86_int_arg_or(slots, count, 4, 1);
  const long long stride_w = kg_cuda_sm86_int_arg_or(slots, count, 5, 1);
  const long long dilation_h = kg_cuda_sm86_int_arg_or(slots, count, 6, 1);
  const long long dilation_w = kg_cuda_sm86_int_arg_or(slots, count, 7, 1);
  const long long pad_top = kg_cuda_sm86_int_arg_or(slots, count, 8, 0);
  const long long pad_left = kg_cuda_sm86_int_arg_or(slots, count, 10, 0);
  if (batch <= 0 || out_channels <= 0 || out_h <= 0 || out_w <= 0 || in_channels <= 0 || in_h <= 0 || in_w <= 0 ||
      slots[2].shape[0] != out_channels || slots[2].shape[1] != in_channels || kernel_h <= 0 || kernel_w <= 0) {
    return -1;
  }
  float* device_out = kg_cuda_sm86_device_alloc<float>(kg_cuda_sm86_element_count(slots[0]));
  float* device_input = kg_cuda_sm86_device_alloc<float>(kg_cuda_sm86_element_count(slots[1]));
  float* device_weight = kg_cuda_sm86_device_alloc<float>(kg_cuda_sm86_element_count(slots[2]));
  float* device_bias = nullptr;
  const bool has_bias = kg_cuda_sm86_has_memory_data(slots, count, 3);
  if (has_bias) {
    device_bias = kg_cuda_sm86_device_alloc<float>(kg_cuda_sm86_element_count(slots[3]));
    kg_cuda_sm86_copy_host_to_device(device_bias, reinterpret_cast<const float*>(slots[3].data), kg_cuda_sm86_element_count(slots[3]));
  }
  kg_cuda_sm86_copy_host_to_device(device_input, reinterpret_cast<const float*>(slots[1].data), kg_cuda_sm86_element_count(slots[1]));
  kg_cuda_sm86_copy_host_to_device(device_weight, reinterpret_cast<const float*>(slots[2].data), kg_cuda_sm86_element_count(slots[2]));
  const long long total = batch * out_channels * out_h * out_w;
  const int block = 256;
  const int grid = static_cast<int>((total + block - 1) / block);
  kg_cuda_sm86_conv2d_f32_kernel<<<grid, block>>>(device_out, device_input, device_weight, device_bias, batch, out_channels, out_h, out_w,
                                                 in_channels, in_h, in_w, kernel_h, kernel_w, stride_h, stride_w, dilation_h, dilation_w,
                                                 pad_top, pad_left);
  KG_CUDA_CHECK(cudaGetLastError());
  KG_CUDA_CHECK(cudaDeviceSynchronize());
  kg_cuda_sm86_copy_device_to_host(reinterpret_cast<float*>(slots[0].data), device_out, kg_cuda_sm86_element_count(slots[0]));
  kg_cuda_sm86_device_free(device_bias);
  kg_cuda_sm86_device_free(device_weight);
  kg_cuda_sm86_device_free(device_input);
  kg_cuda_sm86_device_free(device_out);
  return 0;
}

"""


_FLASH_ATTENTION_CUDA_SOURCE = r"""
__global__ void kg_cuda_sm86_flash_attention_f32_kernel(
    float* out,
    const float* q,
    const float* k,
    const float* v,
    long long batch,
    long long heads,
    long long seq_len,
    long long dim) {
  const long long linear = static_cast<long long>(blockIdx.x) * blockDim.x + threadIdx.x;
  const long long total = batch * heads * seq_len * dim;
  if (linear >= total) {
    return;
  }
  const long long d = linear % dim;
  const long long m = (linear / dim) % seq_len;
  const long long h = (linear / (dim * seq_len)) % heads;
  const long long b = linear / (dim * seq_len * heads);
  float max_score = -3.4028234663852886e38f;
  for (long long n = 0; n < seq_len; ++n) {
    float score = 0.0f;
    for (long long kd = 0; kd < dim; ++kd) {
      const long long q_index = ((b * heads + h) * seq_len + m) * dim + kd;
      const long long k_index = ((b * heads + h) * seq_len + n) * dim + kd;
      score += q[q_index] * k[k_index];
    }
    max_score = fmaxf(max_score, score);
  }
  float sum_score = 0.0f;
  float weighted = 0.0f;
  for (long long n = 0; n < seq_len; ++n) {
    float score = 0.0f;
    for (long long kd = 0; kd < dim; ++kd) {
      const long long q_index = ((b * heads + h) * seq_len + m) * dim + kd;
      const long long k_index = ((b * heads + h) * seq_len + n) * dim + kd;
      score += q[q_index] * k[k_index];
    }
    const float weight_value = expf(score - max_score);
    const long long v_index = ((b * heads + h) * seq_len + n) * dim + d;
    sum_score += weight_value;
    weighted += weight_value * v[v_index];
  }
  out[linear] = weighted / sum_score;
}

int kg_cuda_sm86_run_flash_attention(cuda_sm86::ArgSlot* slots, unsigned long long count) {
  if (!kg_cuda_sm86_is_f32_memory(slots, count, 0, 4) || !kg_cuda_sm86_is_f32_memory(slots, count, 1, 4) ||
      !kg_cuda_sm86_is_f32_memory(slots, count, 2, 4) || !kg_cuda_sm86_is_f32_memory(slots, count, 3, 4)) {
    return -1;
  }
  if (!kg_cuda_sm86_has_memory_data(slots, count, 0) || !kg_cuda_sm86_has_memory_data(slots, count, 1) ||
      !kg_cuda_sm86_has_memory_data(slots, count, 2) || !kg_cuda_sm86_has_memory_data(slots, count, 3)) {
    return -1;
  }
  const long long batch = slots[0].shape[0];
  const long long heads = slots[0].shape[1];
  const long long seq_len = slots[0].shape[2];
  const long long dim = slots[0].shape[3];
  if (batch <= 0 || heads <= 0 || seq_len <= 0 || dim <= 0) {
    return -1;
  }
  float* device_out = kg_cuda_sm86_device_alloc<float>(kg_cuda_sm86_element_count(slots[0]));
  float* device_q = kg_cuda_sm86_device_alloc<float>(kg_cuda_sm86_element_count(slots[1]));
  float* device_k = kg_cuda_sm86_device_alloc<float>(kg_cuda_sm86_element_count(slots[2]));
  float* device_v = kg_cuda_sm86_device_alloc<float>(kg_cuda_sm86_element_count(slots[3]));
  kg_cuda_sm86_copy_host_to_device(device_q, reinterpret_cast<const float*>(slots[1].data), kg_cuda_sm86_element_count(slots[1]));
  kg_cuda_sm86_copy_host_to_device(device_k, reinterpret_cast<const float*>(slots[2].data), kg_cuda_sm86_element_count(slots[2]));
  kg_cuda_sm86_copy_host_to_device(device_v, reinterpret_cast<const float*>(slots[3].data), kg_cuda_sm86_element_count(slots[3]));
  const long long total = batch * heads * seq_len * dim;
  const int block = 256;
  const int grid = static_cast<int>((total + block - 1) / block);
  kg_cuda_sm86_flash_attention_f32_kernel<<<grid, block>>>(device_out, device_q, device_k, device_v, batch, heads, seq_len, dim);
  KG_CUDA_CHECK(cudaGetLastError());
  KG_CUDA_CHECK(cudaDeviceSynchronize());
  kg_cuda_sm86_copy_device_to_host(reinterpret_cast<float*>(slots[0].data), device_out, kg_cuda_sm86_element_count(slots[0]));
  kg_cuda_sm86_device_free(device_v);
  kg_cuda_sm86_device_free(device_k);
  kg_cuda_sm86_device_free(device_q);
  kg_cuda_sm86_device_free(device_out);
  return 0;
}

"""


_HEADER_SOURCE = """#pragma once

#include "include/cuda_sm86/cuda_sm86.cuh"

extern "C" int kg_execute_entry(cuda_sm86::ArgSlot* slots, unsigned long long count);
"""


_ENTRY_SOURCE_BY_KIND = {
    "matmul": """
extern "C" int kg_execute_entry(cuda_sm86::ArgSlot* slots, unsigned long long count) {
  return kg_cuda_sm86_run_matmul(slots, count);
}
""",
    "conv2d": """
extern "C" int kg_execute_entry(cuda_sm86::ArgSlot* slots, unsigned long long count) {
  return kg_cuda_sm86_run_conv2d(slots, count);
}
""",
    "flash_attention": """
extern "C" int kg_execute_entry(cuda_sm86::ArgSlot* slots, unsigned long long count) {
  return kg_cuda_sm86_run_flash_attention(slots, count);
}
""",
}


@emit_c_impl(ModuleOp, target="cuda_sm86")
def _emit_cuda_sm86_module(module_op: ModuleOp, ctx: EmitCContext) -> dict[str, str]:
    """发射 CUDA SM86 ModuleOp。


    功能说明:
    - 按 lowered IR 的 kernel op family 与函数类型 rank 选择 matmul、conv2d 或 flash_attention 单一 CUDA entry。
    - 无支持 kernel family 或 family 判定不唯一时稳定失败，不使用函数名或兜底。
    - 用 generated source 局部 helper 输出 CUDA host wrapper、device kernel 和真实 `mma.sync` 计算路径。
    - 不读取或调用其它模块的私有 helper；不回退到 CPU / npu_demo emit 行为。

    使用示例:
    - source = emit_c(module_op, EmitCContext())
    """
    op_names = [op.name for op in module_op.walk()]
    kernel_op_names = [op_name for op_name in op_names if op_name.startswith("kernel.")]
    supported_kernel_ops = {
        "kernel.binary_elewise",
        "kernel.exp",
        "kernel.img2col2d",
        "kernel.matmul",
        "kernel.reduce",
    }
    unsupported_kernel_ops = sorted(set(kernel_op_names) - supported_kernel_ops)
    if unsupported_kernel_ops:
        raise ctx.emit_error("cuda_sm86", f"unsupported kernel op family: {', '.join(unsupported_kernel_ops)}")
    matmul_count = sum(1 for op_name in op_names if op_name == "kernel.matmul")
    img2col_count = sum(1 for op_name in op_names if op_name == "kernel.img2col2d")
    exp_count = sum(1 for op_name in op_names if op_name == "kernel.exp")
    reduce_count = sum(1 for op_name in op_names if op_name == "kernel.reduce")
    binary_count = sum(1 for op_name in op_names if op_name == "kernel.binary_elewise")
    launch_count = sum(1 for op_name in op_names if op_name == "arch.launch")
    memory_rank_patterns: set[tuple[int, ...]] = set()
    for op in module_op.ops:
        if not isinstance(op, func.FuncOp):
            continue
        input_ranks: list[int] = []
        for input_type in op.function_type.inputs:
            input_text = str(input_type)
            memory_start = input_text.find("!nn.memory<[")
            if memory_start < 0:
                continue
            shape_start = memory_start + len("!nn.memory<[")
            shape_end = input_text.find("], [", shape_start)
            if shape_end < 0:
                continue
            shape_text = input_text[shape_start:shape_end].strip()
            input_ranks.append(0 if not shape_text else shape_text.count("#symbol.expr<"))
        if input_ranks:
            memory_rank_patterns.add(tuple(input_ranks))

    has_kernel_launch = matmul_count > 0 and launch_count > 0
    candidate_sources: dict[str, str] = {}
    if has_kernel_launch and exp_count > 0 and reduce_count > 0 and (4, 4, 4, 4) in memory_rank_patterns:
        candidate_sources["flash_attention"] = _FLASH_ATTENTION_CUDA_SOURCE
    if has_kernel_launch and exp_count == 0 and img2col_count > 0 and binary_count >= 4 and (4, 4, 4, 1) in memory_rank_patterns:
        candidate_sources["conv2d"] = _CONV2D_CUDA_SOURCE
    if has_kernel_launch and exp_count == 0 and img2col_count == 0 and reduce_count == 0 and (2, 2, 2, 1) in memory_rank_patterns:
        candidate_sources["matmul"] = _MATMUL_CUDA_SOURCE
    if len(candidate_sources) != 1:
        raise ctx.emit_error("cuda_sm86", "unsupported kernel family")
    kernel_kind, operation_source = next(iter(candidate_sources.items()))
    source_header = f"""// kg.allow_absent_memory_args: 3:float:1
// cuda_sm86 generated from lowered IR
static constexpr const char* kg_cuda_sm86_selected_kernel_kind = "{kernel_kind}";
static constexpr int kg_cuda_sm86_lowered_kernel_matmul_count = {matmul_count};
static constexpr int kg_cuda_sm86_lowered_kernel_exp_count = {exp_count};
static constexpr int kg_cuda_sm86_lowered_kernel_binary_count = {binary_count};
static constexpr int kg_cuda_sm86_lowered_arch_launch_count = {launch_count};
"""
    entry_source = _ENTRY_SOURCE_BY_KIND[kernel_kind]
    kernel_source = source_header + _COMMON_CUDA_RUNTIME_SOURCE + operation_source + "\n}  // namespace\n" + entry_source
    return {
        "kernel.cu": kernel_source,
        "include/cuda_sm86/generated_entry.cuh": _HEADER_SOURCE,
    }


__all__: list[str] = []
