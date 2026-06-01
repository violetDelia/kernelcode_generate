"""CUDA SM86 `kernel.matmul` emit registration.

功能说明:
- 注册 `target="cuda_sm86"` 的 `kernel.matmul` op emit。
- ModuleOp backend 通过该 op emit 收集真实 lowered IR kernel op token，再选择 generated source。

API 列表:
- 无公开 API；`_emit_cuda_sm86_kernel_matmul(op: KernelMatmulOp, ctx: EmitCContext) -> str` 仅作为 emit registry 装饰器入口存在。
- package-local 文件级 API：`emit_matmul_source(summary: CudaSm86ModuleSummary) -> str`

使用示例:
- source = emit_c(module_op, EmitCContext())

关联文件:
- spec: spec/dsl/gen_kernel/emit/cuda_sm86.md
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm86/detect.py
- test: test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py
"""

from __future__ import annotations

from kernel_gen.dialect.kernel import KernelMatmulOp
from kernel_gen.dsl.gen_kernel.emit.register import emit_c_impl
from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext

from ..constants import CUDA_SM86_KERNEL_OP_MATMUL, CUDA_SM86_TARGET_NAME
from ..detect import CudaSm86ModuleSummary


@emit_c_impl(KernelMatmulOp, target=CUDA_SM86_TARGET_NAME)
def _emit_cuda_sm86_kernel_matmul(op: KernelMatmulOp, ctx: EmitCContext) -> str:
    """发射 CUDA SM86 `kernel.matmul` op token。

    功能说明:
    - 不直接生成整段 family source，只返回当前 op 的 canonical token。
    - `module.py` 汇总每个 kernel op 的 emit 结果后再构建 SourceBundle。

    使用示例:
    - token = _emit_cuda_sm86_kernel_matmul(op, EmitCContext())
    """

    expected_token = CUDA_SM86_KERNEL_OP_MATMUL
    op_name = op.name
    if op_name != expected_token:
        raise ctx.emit_error("cuda_sm86.kernel.matmul", f"unexpected op {op_name}")
    emitted_token = expected_token
    return emitted_token


def emit_matmul_source(summary: CudaSm86ModuleSummary) -> str:
    """返回 matmul family generated CUDA source。

    功能说明:
    - 接收 lowered IR summary 以保持三类 kernel family 的统一调用签名。
    - 当前 matmul source 不需要读取 summary 字段，source marker 由 `source_bundle.py` 统一写入。

    使用示例:
    - source = emit_matmul_source(summary)
    """

    return r"""
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
    const unsigned a0 = cuda_sm86::detail::to_tf32(kg_cuda_sm86_load_or_zero(lhs, row_base + group_id, k_base + thread_in_group, m, k));
    const unsigned a1 = cuda_sm86::detail::to_tf32(kg_cuda_sm86_load_or_zero(lhs, row_base + group_id + 8, k_base + thread_in_group, m, k));
    const unsigned a2 = cuda_sm86::detail::to_tf32(kg_cuda_sm86_load_or_zero(lhs, row_base + group_id, k_base + thread_in_group + 4, m, k));
    const unsigned a3 = cuda_sm86::detail::to_tf32(kg_cuda_sm86_load_or_zero(lhs, row_base + group_id + 8, k_base + thread_in_group + 4, m, k));
    const unsigned b0 = cuda_sm86::detail::to_tf32(kg_cuda_sm86_load_or_zero(rhs, k_base + thread_in_group, col_base + group_id, k, n));
    const unsigned b1 = cuda_sm86::detail::to_tf32(kg_cuda_sm86_load_or_zero(rhs, k_base + thread_in_group + 4, col_base + group_id, k, n));
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
  if (!cuda_sm86::detail::is_f32_memory(slots, count, 0, 2) || !cuda_sm86::detail::is_f32_memory(slots, count, 1, 2) ||
      !cuda_sm86::detail::is_f32_memory(slots, count, 2, 2) || !cuda_sm86::detail::has_memory_data(slots, count, 0) ||
      !cuda_sm86::detail::has_memory_data(slots, count, 1) || !cuda_sm86::detail::has_memory_data(slots, count, 2)) {
    return -1;
  }
  const long long m = slots[0].shape[0];
  const long long n = slots[0].shape[1];
  const long long k = slots[1].shape[1];
  if (m <= 0 || n <= 0 || k <= 0 || slots[1].shape[0] != m || slots[2].shape[0] != k || slots[2].shape[1] != n) {
    return -1;
  }
  float* device_out = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[0]));
  float* device_lhs = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[1]));
  float* device_rhs = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[2]));
  float* device_bias = nullptr;
  const bool has_bias = cuda_sm86::detail::has_memory_data(slots, count, 3);
  if (has_bias) {
    device_bias = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[3]));
    cuda_sm86::detail::copy_host_to_device(device_bias, reinterpret_cast<const float*>(slots[3].data), cuda_sm86::detail::element_count(slots[3]));
  }
  cuda_sm86::detail::copy_host_to_device(device_lhs, reinterpret_cast<const float*>(slots[1].data), cuda_sm86::detail::element_count(slots[1]));
  cuda_sm86::detail::copy_host_to_device(device_rhs, reinterpret_cast<const float*>(slots[2].data), cuda_sm86::detail::element_count(slots[2]));
  const dim3 block(32);
  const dim3 grid(static_cast<unsigned int>((n + 7) / 8), static_cast<unsigned int>((m + 15) / 16));
  kg_cuda_sm86_generated_matmul_kernel<<<grid, block>>>(device_out, device_lhs, device_rhs, device_bias, m, n, k);
  KG_CUDA_CHECK(cudaGetLastError());
  KG_CUDA_CHECK(cudaDeviceSynchronize());
  cuda_sm86::detail::copy_device_to_host(reinterpret_cast<float*>(slots[0].data), device_out, cuda_sm86::detail::element_count(slots[0]));
  cuda_sm86::detail::device_free(device_bias);
  cuda_sm86::detail::device_free(device_rhs);
  cuda_sm86::detail::device_free(device_lhs);
  cuda_sm86::detail::device_free(device_out);
  return 0;
}

"""
