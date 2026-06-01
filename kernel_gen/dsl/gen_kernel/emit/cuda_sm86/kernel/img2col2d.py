"""CUDA SM86 `kernel.img2col2d` emit registration.

功能说明:
- 注册 `target="cuda_sm86"` 的 `kernel.img2col2d` op emit。
- ModuleOp backend 通过该 op emit 识别 conv2d lowered IR family。

API 列表:
- 无公开 API；`_emit_cuda_sm86_kernel_img2col2d(op: KernelImg2col2dOp, ctx: EmitCContext) -> str` 仅作为 emit registry 装饰器入口存在。
- package-local 文件级 API：`emit_conv2d_source(summary: CudaSm86ModuleSummary) -> str`

使用示例:
- source = emit_c(module_op, EmitCContext())

关联文件:
- spec: spec/dsl/gen_kernel/emit/cuda_sm86.md
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm86/detect.py
- test: test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py
"""

from __future__ import annotations

from kernel_gen.dialect.kernel import KernelImg2col2dOp
from kernel_gen.dsl.gen_kernel.emit.register import emit_c_impl
from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext

from ..constants import CUDA_SM86_KERNEL_OP_IMG2COL2D, CUDA_SM86_TARGET_NAME
from ..detect import CudaSm86ModuleSummary


@emit_c_impl(KernelImg2col2dOp, target=CUDA_SM86_TARGET_NAME)
def _emit_cuda_sm86_kernel_img2col2d(op: KernelImg2col2dOp, ctx: EmitCContext) -> str:
    """发射 CUDA SM86 `kernel.img2col2d` op token。

    功能说明:
    - 不直接生成整段 conv2d source，只返回当前 op 的 canonical token。
    - `module.py` 汇总每个 kernel op 的 emit 结果后再构建 SourceBundle。

    使用示例:
    - token = _emit_cuda_sm86_kernel_img2col2d(op, EmitCContext())
    """

    expected_token = CUDA_SM86_KERNEL_OP_IMG2COL2D
    op_name = op.name
    if op_name != expected_token:
        raise ctx.emit_error("cuda_sm86.kernel.img2col2d", f"unexpected op {op_name}")
    emitted_token = expected_token
    return emitted_token


def emit_conv2d_source(summary: CudaSm86ModuleSummary) -> str:
    """返回 conv2d family generated CUDA source。

    功能说明:
    - 接收 lowered IR summary 以保持三类 kernel family 的统一调用签名。
    - 当前 conv2d source 的 runtime shape / scalar 校验保持原有公开行为。

    使用示例:
    - source = emit_conv2d_source(summary)
    """

    return r"""
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
  if (!cuda_sm86::detail::is_f32_memory(slots, count, 0, 4) || !cuda_sm86::detail::is_f32_memory(slots, count, 1, 4) ||
      !cuda_sm86::detail::is_f32_memory(slots, count, 2, 4) || !cuda_sm86::detail::has_memory_data(slots, count, 0) ||
      !cuda_sm86::detail::has_memory_data(slots, count, 1) || !cuda_sm86::detail::has_memory_data(slots, count, 2)) {
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
  const long long stride_h = cuda_sm86::detail::int_arg_or(slots, count, 4, 1);
  const long long stride_w = cuda_sm86::detail::int_arg_or(slots, count, 5, 1);
  const long long dilation_h = cuda_sm86::detail::int_arg_or(slots, count, 6, 1);
  const long long dilation_w = cuda_sm86::detail::int_arg_or(slots, count, 7, 1);
  const long long pad_top = cuda_sm86::detail::int_arg_or(slots, count, 8, 0);
  const long long pad_left = cuda_sm86::detail::int_arg_or(slots, count, 10, 0);
  if (batch <= 0 || out_channels <= 0 || out_h <= 0 || out_w <= 0 || in_channels <= 0 || in_h <= 0 || in_w <= 0 ||
      slots[2].shape[0] != out_channels || slots[2].shape[1] != in_channels || kernel_h <= 0 || kernel_w <= 0) {
    return -1;
  }
  float* device_out = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[0]));
  float* device_input = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[1]));
  float* device_weight = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[2]));
  float* device_bias = nullptr;
  const bool has_bias = cuda_sm86::detail::has_memory_data(slots, count, 3);
  if (has_bias) {
    device_bias = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[3]));
    cuda_sm86::detail::copy_host_to_device(device_bias, reinterpret_cast<const float*>(slots[3].data), cuda_sm86::detail::element_count(slots[3]));
  }
  cuda_sm86::detail::copy_host_to_device(device_input, reinterpret_cast<const float*>(slots[1].data), cuda_sm86::detail::element_count(slots[1]));
  cuda_sm86::detail::copy_host_to_device(device_weight, reinterpret_cast<const float*>(slots[2].data), cuda_sm86::detail::element_count(slots[2]));
  const long long total = batch * out_channels * out_h * out_w;
  const int block = 256;
  const int grid = static_cast<int>((total + block - 1) / block);
  kg_cuda_sm86_conv2d_f32_kernel<<<grid, block>>>(device_out, device_input, device_weight, device_bias, batch, out_channels, out_h, out_w,
                                                 in_channels, in_h, in_w, kernel_h, kernel_w, stride_h, stride_w, dilation_h, dilation_w,
                                                 pad_top, pad_left);
  KG_CUDA_CHECK(cudaGetLastError());
  KG_CUDA_CHECK(cudaDeviceSynchronize());
  cuda_sm86::detail::copy_device_to_host(reinterpret_cast<float*>(slots[0].data), device_out, cuda_sm86::detail::element_count(slots[0]));
  cuda_sm86::detail::device_free(device_bias);
  cuda_sm86::detail::device_free(device_weight);
  cuda_sm86::detail::device_free(device_input);
  cuda_sm86::detail::device_free(device_out);
  return 0;
}

"""
