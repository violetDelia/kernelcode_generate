"""CUDA SM89 `kernel.exp` emit registration.

功能说明:
- 注册 `target="cuda_sm89"` 的 `kernel.exp` op emit。
- 单 op emit 返回 canonical diagnostic token；ModuleOp SourceBundle 由 final IR traversal 统一生成 wrapper calls。

API 列表:
- 无公开 API；`_emit_cuda_sm89_kernel_exp(op: KernelExpOp, ctx: EmitCContext) -> str` 仅作为 emit registry 装饰器入口存在。

使用示例:
- source = emit_c(module_op, EmitCContext())

关联文件:
- spec: spec/dsl/gen_kernel/emit/cuda_sm89.md
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm89/source_bundle.py
- test: test/dsl/gen_kernel/emit/test_cuda_sm89_emit.py
"""

from __future__ import annotations

from kernel_gen.dialect.kernel import KernelExpOp
from kernel_gen.dsl.gen_kernel.emit.register import emit_c_impl
from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext

from ..constants import CUDA_SM89_KERNEL_OP_EXP, CUDA_SM89_TARGET_NAME


@emit_c_impl(KernelExpOp, target=CUDA_SM89_TARGET_NAME)
def _emit_cuda_sm89_kernel_exp(op: KernelExpOp, ctx: EmitCContext) -> str:
    """发射 CUDA SM89 `kernel.exp` diagnostic token。

    功能说明:
    - 校验 registry 传入 op 与 expected op name 一致。
    - 返回 canonical token，供公开单 op dispatch 路径保持可诊断输出；ModuleOp source 不依赖此返回值选择整段源码。

    使用示例:
    - token = _emit_cuda_sm89_kernel_exp(op, EmitCContext())
    """

    expected_token = CUDA_SM89_KERNEL_OP_EXP
    op_name = op.name
    if op_name != expected_token:
        raise ctx.emit_error("cuda_sm89.kernel.exp", f"unexpected op {op_name}")
    return expected_token
