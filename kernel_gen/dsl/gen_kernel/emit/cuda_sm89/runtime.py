"""CUDA SM89 generated runtime source blocks.

功能说明:
- 承载 generated `kernel.cu` 内部 common runtime helper source 和 generated entry header source。
- `include/cuda_sm89/cuda_sm89.cuh` 聚合 include/api Arch 声明与 CUDA 后端 Arch 实现；这里仅打开 generated source 局部 namespace。

API 列表:
- CUDA_SM89_COMMON_RUNTIME_SOURCE: str
- CUDA_SM89_HEADER_SOURCE: str

使用示例:
- source = CUDA_SM89_COMMON_RUNTIME_SOURCE

关联文件:
- spec: spec/dsl/gen_kernel/emit/cuda_sm89.md
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm89/source_bundle.py
"""

from __future__ import annotations

from .constants import CUDA_SM89_RUNTIME_ENTRY_NAME

CUDA_SM89_COMMON_RUNTIME_SOURCE = r"""
#include "include/cuda_sm89/cuda_sm89.cuh"
#include "include/cuda_sm89/generated_entry.cuh"

#include <math.h>

namespace {
"""

CUDA_SM89_HEADER_SOURCE = f"""#pragma once

#include "include/cuda_sm89/cuda_sm89.cuh"

extern "C" int {CUDA_SM89_RUNTIME_ENTRY_NAME}(cuda_sm89::ArgSlot* slots, unsigned long long count);
"""
