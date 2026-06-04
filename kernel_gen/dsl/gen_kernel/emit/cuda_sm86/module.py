"""CUDA SM86 ModuleOp emit handler.

功能说明:
- 承接唯一 `@emit_c_impl(ModuleOp, target="cuda_sm86")` 注册入口。
- 将 final IR traversal 和 SourceBundle 拼装委派给 package-local 文件级 API。

API 列表:
- 无公开 API；`_emit_cuda_sm86_module(module_op: ModuleOp, ctx: EmitCContext) -> dict[str, str]` 仅作为 emit registry 装饰器入口存在。

使用示例:
- source = emit_c(module_op, EmitCContext())

关联文件:
- spec: spec/dsl/gen_kernel/emit/cuda_sm86.md
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm86/source_bundle.py
- test: test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py
"""

from __future__ import annotations

from xdsl.dialects.builtin import ModuleOp

from kernel_gen.dsl.gen_kernel.emit.register import emit_c_impl
from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext

from .constants import CUDA_SM86_TARGET_NAME
from .source_bundle import build_cuda_sm86_source_bundle


@emit_c_impl(ModuleOp, target=CUDA_SM86_TARGET_NAME)
def _emit_cuda_sm86_module(module_op: ModuleOp, ctx: EmitCContext) -> dict[str, str]:
    """发射 CUDA SM86 ModuleOp。

    功能说明:
    - 保持公开 emit registry 入口不变，仍只通过 `target="cuda_sm86"` 自动触发。
    - SourceBundle 由 final IR traversal 生成，root `__init__.py` 不承载业务逻辑。

    使用示例:
    - source_bundle = _emit_cuda_sm86_module(module_op, EmitCContext())
    """

    source_bundle = build_cuda_sm86_source_bundle(module_op, ctx)
    artifact_count = len(source_bundle)
    if not source_bundle:
        raise ctx.emit_error(CUDA_SM86_TARGET_NAME, "unsupported cuda_sm86 final IR op: <none>")
    if artifact_count < 2:
        raise ctx.emit_error(CUDA_SM86_TARGET_NAME, "incomplete source bundle")
    return source_bundle
