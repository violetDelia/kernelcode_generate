"""CUDA SM86 emit package constants.

功能说明:
- 固定 CUDA SM86 package-local source artifact 名称、target 名称和 runtime entry 名称。
- 固定每个 `kernel.*` op emit 返回的 canonical marker，供单 op dispatch 路径保持可诊断输出。
- 只承载计划确认的短字符串常量，不承载 CUDA source 模板或业务逻辑。

API 列表:
- CUDA_SM86_TARGET_NAME: str
- CUDA_SM86_KERNEL_SOURCE_ARTIFACT: str
- CUDA_SM86_GENERATED_ENTRY_HEADER_ARTIFACT: str
- CUDA_SM86_RUNTIME_ENTRY_NAME: str
- CUDA_SM86_KERNEL_OP_BINARY_ELEWISE: str
- CUDA_SM86_KERNEL_OP_EXP: str
- CUDA_SM86_KERNEL_OP_IMG2COL2D: str
- CUDA_SM86_KERNEL_OP_MATMUL: str
- CUDA_SM86_KERNEL_OP_REDUCE: str

使用示例:
- artifact = CUDA_SM86_KERNEL_SOURCE_ARTIFACT

关联文件:
- spec: spec/dsl/gen_kernel/emit/cuda_sm86.md
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm86/source_bundle.py
"""

from __future__ import annotations

CUDA_SM86_TARGET_NAME: str = "cuda_sm86"
CUDA_SM86_KERNEL_SOURCE_ARTIFACT: str = "kernel.cu"
CUDA_SM86_GENERATED_ENTRY_HEADER_ARTIFACT: str = "include/cuda_sm86/generated_entry.cuh"
CUDA_SM86_RUNTIME_ENTRY_NAME: str = "kg_execute_entry"
CUDA_SM86_KERNEL_OP_BINARY_ELEWISE: str = "kernel.binary_elewise"
CUDA_SM86_KERNEL_OP_EXP: str = "kernel.exp"
CUDA_SM86_KERNEL_OP_IMG2COL2D: str = "kernel.img2col2d"
CUDA_SM86_KERNEL_OP_MATMUL: str = "kernel.matmul"
CUDA_SM86_KERNEL_OP_REDUCE: str = "kernel.reduce"
