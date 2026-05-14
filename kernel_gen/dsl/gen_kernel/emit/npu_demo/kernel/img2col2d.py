"""npu_demo `kernel.img2col2d` EmitC 注册实现。

功能说明:
- 注册 target=`npu_demo` 的 `kernel.img2col2d` EmitC 发射实现。
- 本文件不提供跨文件公开 API；调用方必须通过 emit registry 与 `emit_c_op(...)` 公开入口调度。

API 列表:
- 无公开 API。

使用示例:
- source = emit_c_op(op, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/kernel/__init__.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/img2col2d.py
"""

from __future__ import annotations

from kernel_gen.dialect.kernel import KernelImg2col2dOp
from kernel_gen.dialect.nn import NnMemoryType

from ..type import memory_element_cpp_type
from ...register import emit_c_impl


@emit_c_impl(KernelImg2col2dOp, target="npu_demo")
def _emit_npu_demo_kernel_img2col2d(op: KernelImg2col2dOp, ctx) -> str:
    """发射 npu_demo `kernel.img2col2d` C++ 语句。

    功能说明:
    - 根据 `KernelImg2col2dOp` 的 input/out memory 与二维卷积参数生成 `img2col2d<...>(...)` 语句。
    - 仅作为当前文件内注册实现使用，不作为跨文件公开 API。

    使用示例:
    - stmt = _emit_npu_demo_kernel_img2col2d(op, ctx)
    """

    out_value = op.out
    input_value = op.input
    out_idx = out_value.index if hasattr(out_value, "index") else None
    input_idx = input_value.index if hasattr(input_value, "index") else None
    if out_idx is not None and input_idx is not None and input_idx < out_idx:
        out_value, input_value = input_value, out_value
    if not isinstance(input_value.type, NnMemoryType) or not isinstance(out_value.type, NnMemoryType):
        raise ctx.emit_error(op.name, "unsupported op")
    from ... import emit_c_value

    params = [emit_c_value(value, ctx) for value in (op.kh, op.kw, op.sh, op.sw, op.dh, op.dw, op.ph, op.pw, op.pl, op.pr)]
    return (
        f"{ctx.current_indent}img2col2d<{ctx.dispatch_attr(input_value.type)}, {ctx.dispatch_attr(out_value.type)}, "
        f"{memory_element_cpp_type(input_value.type, ctx)}, {memory_element_cpp_type(out_value.type, ctx)}>"
        f"({emit_c_value(out_value, ctx)} /*out*/, {emit_c_value(input_value, ctx)} /*input*/, "
        f"{params[0]} /*kh*/, {params[1]} /*kw*/, {params[2]} /*sh*/, {params[3]} /*sw*/, {params[4]} /*dh*/, {params[5]} /*dw*/, "
        f"{params[6]} /*ph*/, {params[7]} /*pw*/, {params[8]} /*pl*/, {params[9]} /*pr*/);"
    )
