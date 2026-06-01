"""CUDA SM86 `kernel.binary_elewise` emit registration.

功能说明:
- 注册 `target="cuda_sm86"` 的 `kernel.binary_elewise` op emit。
- ModuleOp backend 通过该 op emit 识别 conv2d / flash_attention lowered IR family。

API 列表:
- 无公开 API；`_emit_cuda_sm86_kernel_binary_elewise(op: KernelBinaryElewiseOp, ctx: EmitCContext) -> str` 仅作为 emit registry 装饰器入口存在。

使用示例:
- source = emit_c(module_op, EmitCContext())

关联文件:
- spec: spec/dsl/gen_kernel/emit/cuda_sm86.md
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm86/detect.py
- test: test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py
"""

from __future__ import annotations

from kernel_gen.dialect.kernel import KernelBinaryElewiseOp
from kernel_gen.dsl.gen_kernel.emit.register import emit_c_impl
from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext

from ..constants import CUDA_SM86_KERNEL_OP_BINARY_ELEWISE, CUDA_SM86_TARGET_NAME


@emit_c_impl(KernelBinaryElewiseOp, target=CUDA_SM86_TARGET_NAME)
def _emit_cuda_sm86_kernel_binary_elewise(op: KernelBinaryElewiseOp, ctx: EmitCContext) -> str:
    """发射 CUDA SM86 `kernel.binary_elewise` op token。

    功能说明:
    - 不直接生成整段 family source，只返回当前 op 的 canonical token。
    - `module.py` 汇总每个 kernel op 的 emit 结果后再构建 SourceBundle。

    使用示例:
    - token = _emit_cuda_sm86_kernel_binary_elewise(op, EmitCContext())
    """

    expected_token = CUDA_SM86_KERNEL_OP_BINARY_ELEWISE
    op_name = op.name
    if op_name != expected_token:
        raise ctx.emit_error("cuda_sm86.kernel.binary_elewise", f"unexpected op {op_name}")
    emitted_token = expected_token
    return emitted_token
