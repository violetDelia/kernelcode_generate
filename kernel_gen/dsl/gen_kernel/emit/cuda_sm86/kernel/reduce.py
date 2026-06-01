"""CUDA SM86 `kernel.reduce` emit registration.

功能说明:
- 注册 `target="cuda_sm86"` 的 `kernel.reduce` op emit。
- ModuleOp backend 通过该 op emit 识别 flash_attention lowered IR family。

API 列表:
- 无公开 API；`_emit_cuda_sm86_kernel_reduce(op: KernelReduceOp, ctx: EmitCContext) -> str` 仅作为 emit registry 装饰器入口存在。
- package-local 文件级 API：`emit_flash_attention_source(summary: CudaSm86ModuleSummary) -> str`

使用示例:
- source = emit_c(module_op, EmitCContext())

关联文件:
- spec: spec/dsl/gen_kernel/emit/cuda_sm86.md
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm86/detect.py
- test: test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py
"""

from __future__ import annotations

from kernel_gen.dialect.kernel import KernelReduceOp
from kernel_gen.dsl.gen_kernel.emit.register import emit_c_impl
from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext

from ..constants import CUDA_SM86_KERNEL_OP_REDUCE, CUDA_SM86_TARGET_NAME
from ..detect import CudaSm86ModuleSummary


@emit_c_impl(KernelReduceOp, target=CUDA_SM86_TARGET_NAME)
def _emit_cuda_sm86_kernel_reduce(op: KernelReduceOp, ctx: EmitCContext) -> str:
    """发射 CUDA SM86 `kernel.reduce` op token。

    功能说明:
    - 不直接生成整段 flash_attention source，只返回当前 op 的 canonical token。
    - `module.py` 汇总每个 kernel op 的 emit 结果后再构建 SourceBundle。

    使用示例:
    - token = _emit_cuda_sm86_kernel_reduce(op, EmitCContext())
    """

    expected_token = CUDA_SM86_KERNEL_OP_REDUCE
    op_name = op.name
    if op_name != expected_token:
        raise ctx.emit_error("cuda_sm86.kernel.reduce", f"unexpected op {op_name}")
    emitted_token = expected_token
    return emitted_token


def emit_flash_attention_source(summary: CudaSm86ModuleSummary) -> str:
    """返回 flash_attention family generated CUDA source。

    功能说明:
    - 接收 lowered IR summary 以保持三类 kernel family 的统一调用签名。
    - 生成 source 中的 runtime runner 继续使用 slots 中的四维 memory 参数。

    使用示例:
    - source = emit_flash_attention_source(summary)
    """

    return r"""
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
  if (!cuda_sm86::detail::is_f32_memory(slots, count, 0, 4) || !cuda_sm86::detail::is_f32_memory(slots, count, 1, 4) ||
      !cuda_sm86::detail::is_f32_memory(slots, count, 2, 4) || !cuda_sm86::detail::is_f32_memory(slots, count, 3, 4)) {
    return -1;
  }
  if (!cuda_sm86::detail::has_memory_data(slots, count, 0) || !cuda_sm86::detail::has_memory_data(slots, count, 1) ||
      !cuda_sm86::detail::has_memory_data(slots, count, 2) || !cuda_sm86::detail::has_memory_data(slots, count, 3)) {
    return -1;
  }
  const long long batch = slots[0].shape[0];
  const long long heads = slots[0].shape[1];
  const long long seq_len = slots[0].shape[2];
  const long long dim = slots[0].shape[3];
  if (batch <= 0 || heads <= 0 || seq_len <= 0 || dim <= 0) {
    return -1;
  }
  float* device_out = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[0]));
  float* device_q = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[1]));
  float* device_k = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[2]));
  float* device_v = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[3]));
  cuda_sm86::detail::copy_host_to_device(device_q, reinterpret_cast<const float*>(slots[1].data), cuda_sm86::detail::element_count(slots[1]));
  cuda_sm86::detail::copy_host_to_device(device_k, reinterpret_cast<const float*>(slots[2].data), cuda_sm86::detail::element_count(slots[2]));
  cuda_sm86::detail::copy_host_to_device(device_v, reinterpret_cast<const float*>(slots[3].data), cuda_sm86::detail::element_count(slots[3]));
  const long long total = batch * heads * seq_len * dim;
  const int block = 256;
  const int grid = static_cast<int>((total + block - 1) / block);
  kg_cuda_sm86_flash_attention_f32_kernel<<<grid, block>>>(device_out, device_q, device_k, device_v, batch, heads, seq_len, dim);
  KG_CUDA_CHECK(cudaGetLastError());
  KG_CUDA_CHECK(cudaDeviceSynchronize());
  cuda_sm86::detail::copy_device_to_host(reinterpret_cast<float*>(slots[0].data), device_out, cuda_sm86::detail::element_count(slots[0]));
  cuda_sm86::detail::device_free(device_v);
  cuda_sm86::detail::device_free(device_k);
  cuda_sm86::detail::device_free(device_q);
  cuda_sm86::detail::device_free(device_out);
  return 0;
}

"""
