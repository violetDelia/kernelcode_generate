"""CUDA SM89 target include registration.

功能说明:
- 注册 `target="cuda_sm89"` 的 include prelude。
- include 发射只承接 CUDA SM89 public runtime/header 入口，不生成业务 kernel source。

API 列表:
- 无公开 API；`_emit_cuda_sm89_include(ctx: EmitCContext) -> str` 仅作为 emit registry 装饰器入口存在。

使用示例:
- source = emit_c(func_op, EmitCContext())

关联文件:
- spec: spec/dsl/gen_kernel/emit/cuda_sm89.md
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm89/__init__.py
- test: test/dsl/gen_kernel/emit/test_cuda_sm89_emit.py
"""

from __future__ import annotations

from kernel_gen.dsl.gen_kernel.emit.register import emit_c_include_impl
from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext

from .constants import CUDA_SM89_TARGET_NAME


@emit_c_include_impl(target=CUDA_SM89_TARGET_NAME)
def _emit_cuda_sm89_include(ctx: EmitCContext) -> str:
    """发射 CUDA SM89 include prelude。

    功能说明:
    - 为非 SourceBundle 的公开 emit 路径提供 target include 文本。
    - SourceBundle `kernel.cu` 仍由 runtime source 自带 includes，避免重复拼入 aggregate marker 前。

    使用示例:
    - include = _emit_cuda_sm89_include(EmitCContext())
    """

    if not ctx.is_target(CUDA_SM89_TARGET_NAME):
        raise ctx.emit_error("cuda_sm89.include", "target mismatch")
    runtime_header = '#include "include/cuda_sm89/cuda_sm89.cuh"'
    generated_header = '#include "include/cuda_sm89/generated_entry.cuh"'
    include_text = f"{runtime_header}\n{generated_header}\n\n"
    return include_text
