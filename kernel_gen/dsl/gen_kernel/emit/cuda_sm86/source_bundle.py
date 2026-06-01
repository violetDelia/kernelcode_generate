"""CUDA SM86 SourceBundle assembly.

功能说明:
- 组合 lowered IR summary、runtime source、kernel family source 和 generated entry source。
- 保持 SourceBundle artifact key、selected kind marker 和 lowered op count marker 不变。

API 列表:
- `build_cuda_sm86_source_bundle(summary: CudaSm86ModuleSummary) -> dict[str, str]`

使用示例:
- bundle = build_cuda_sm86_source_bundle(summary)

关联文件:
- spec: spec/dsl/gen_kernel/emit/cuda_sm86.md
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm86/module.py
- test: test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py
"""

from __future__ import annotations

from .constants import CUDA_SM86_GENERATED_ENTRY_HEADER_ARTIFACT, CUDA_SM86_KERNEL_SOURCE_ARTIFACT, CUDA_SM86_RUNTIME_ENTRY_NAME
from .detect import CudaSm86ModuleSummary
from .runtime import CUDA_SM86_COMMON_RUNTIME_SOURCE, CUDA_SM86_HEADER_SOURCE
from .kernel.img2col2d import emit_conv2d_source
from .kernel.matmul import emit_matmul_source
from .kernel.reduce import emit_flash_attention_source


def build_cuda_sm86_source_bundle(summary: CudaSm86ModuleSummary) -> dict[str, str]:
    """构建 CUDA SM86 SourceBundle artifacts。

    功能说明:
    - 按 summary family 选择单一业务 kernel source，不回退到三合一 dispatcher。
    - 返回 `kernel.cu` 与 generated entry header 两个既有 artifact key。

    使用示例:
    - source_bundle = build_cuda_sm86_source_bundle(summary)
    """

    operation_sources = {
        "matmul": emit_matmul_source,
        "conv2d": emit_conv2d_source,
        "flash_attention": emit_flash_attention_source,
    }
    kernel_kind = summary.family.value
    operation_source = operation_sources[kernel_kind](summary)
    source_header = f"""// kg.allow_absent_memory_args: 3:float:1
// cuda_sm86 generated from lowered IR
static constexpr const char* kg_cuda_sm86_selected_kernel_kind = "{kernel_kind}";
static constexpr int kg_cuda_sm86_lowered_kernel_matmul_count = {summary.matmul_count};
static constexpr int kg_cuda_sm86_lowered_kernel_exp_count = {summary.exp_count};
static constexpr int kg_cuda_sm86_lowered_kernel_binary_count = {summary.binary_count};
static constexpr int kg_cuda_sm86_lowered_arch_launch_count = {summary.launch_count};
"""
    entry_source = f"""
extern "C" int {CUDA_SM86_RUNTIME_ENTRY_NAME}(cuda_sm86::ArgSlot* slots, unsigned long long count) {{
  return kg_cuda_sm86_run_{kernel_kind}(slots, count);
}}
"""
    kernel_source = source_header + CUDA_SM86_COMMON_RUNTIME_SOURCE + operation_source + "\n}  // namespace\n" + entry_source
    return {
        CUDA_SM86_KERNEL_SOURCE_ARTIFACT: kernel_source,
        CUDA_SM86_GENERATED_ENTRY_HEADER_ARTIFACT: CUDA_SM86_HEADER_SOURCE,
    }
