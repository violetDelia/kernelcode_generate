"""npu_demo `kernel.img2col1d` EmitC 注册实现。

功能说明:
- 注册 target=`npu_demo` 的 `kernel.img2col1d` EmitC 发射实现。
- 本文件不提供跨文件公开 API；调用方必须通过 emit registry 与 `emit_c_op(...)` 公开入口调度。

API 列表:
- 无公开 API。

使用示例:
- source = emit_c_op(op, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/kernel/__init__.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/img2col1d.py
"""

from __future__ import annotations

from kernel_gen.dialect.kernel import KernelImg2col1dOp
from kernel_gen.dialect.nn import NnMemoryType

from ...register import emit_c_impl


def _memory_element_cpp_type(memory_type: NnMemoryType, ctx) -> str:
    """返回当前文件发射 kernel.img2col1d 所需的 C++ element type。

    功能说明:
    - 优先使用 `NnMemoryType.template_name` 作为模板 dtype。
    - 未携带 template name 时通过 `ctx.dispatch_type(...)` 发射真实 element type。

    使用示例:
    - element_type = _memory_element_cpp_type(memory_type, ctx)
    """

    memory_type.verify()
    template_name = memory_type.template_name.data
    if template_name:
        return template_name
    return ctx.dispatch_type(memory_type.element_type)


@emit_c_impl(KernelImg2col1dOp, target="npu_demo")
def _emit_npu_demo_kernel_img2col1d(op: KernelImg2col1dOp, ctx) -> str:
    """发射 npu_demo `kernel.img2col1d` C++ 语句。

    功能说明:
    - 根据 `KernelImg2col1dOp` 的 input/out memory 与卷积参数生成 `img2col1d<...>(...)` 语句。
    - 仅作为当前文件内注册实现使用，不作为跨文件公开 API。

    使用示例:
    - stmt = _emit_npu_demo_kernel_img2col1d(op, ctx)
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

    params = [emit_c_value(value, ctx) for value in (op.k, op.s, op.d, op.p_left, op.p_right)]
    return (
        f"{ctx.current_indent}img2col1d<{ctx.dispatch_attr(input_value.type)}, {ctx.dispatch_attr(out_value.type)}, "
        f"{_memory_element_cpp_type(input_value.type, ctx)}, {_memory_element_cpp_type(out_value.type, ctx)}>"
        f"({emit_c_value(out_value, ctx)} /*out*/, {emit_c_value(input_value, ctx)} /*input*/, "
        f"{params[0]} /*k*/, {params[1]} /*s*/, {params[2]} /*d*/, {params[3]} /*p_left*/, {params[4]} /*p_right*/);"
    )
