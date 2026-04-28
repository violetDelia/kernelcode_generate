from __future__ import annotations

from kernel_gen.dialect.kernel import KernelImg2col1dOp
from kernel_gen.dialect.nn import NnMemoryType

from ...register import emit_c_impl


def _block_arg_index(value) -> int | None:
    return value.index if hasattr(value, "index") else None


def _normalize_out_input_operands(out_value, input_value):
    out_idx = _block_arg_index(out_value)
    input_idx = _block_arg_index(input_value)
    if out_idx is not None and input_idx is not None and input_idx < out_idx:
        return input_value, out_value
    return out_value, input_value


@emit_c_impl(KernelImg2col1dOp, target="npu_demo")
def _emit_npu_demo_kernel_img2col1d(op: KernelImg2col1dOp, ctx) -> str:
    out_value, input_value = _normalize_out_input_operands(op.out, op.input)
    if not isinstance(input_value.type, NnMemoryType) or not isinstance(out_value.type, NnMemoryType):
        raise ctx.emit_error(op.name, "unsupported op")
    from ... import emit_c_value

    params = [emit_c_value(value, ctx) for value in (op.k, op.s, op.d, op.p_left, op.p_right)]
    return (
        f"{ctx.current_indent}img2col1d<{ctx.dispatch_attr(input_value.type)}, {ctx.dispatch_attr(out_value.type)}, "
        f"{ctx.dispatch_type(input_value.type.element_type)}, {ctx.dispatch_type(out_value.type.element_type)}>"
        f"({emit_c_value(out_value, ctx)} /*out*/, {emit_c_value(input_value, ctx)} /*input*/, "
        f"{params[0]} /*k*/, {params[1]} /*s*/, {params[2]} /*d*/, {params[3]} /*p_left*/, {params[4]} /*p_right*/);"
    )
