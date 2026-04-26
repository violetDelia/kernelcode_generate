from __future__ import annotations

from kernel_gen.dialect.kernel import KernelReduceMinOp, KernelReduceOp
from kernel_gen.dialect.nn import NnMemoryType

from ....errors import emit_c_error
from ...register import emit_c_impl


def _block_arg_index(value) -> int | None:
    return value.index if hasattr(value, "index") else None


def _normalize_out_input_operands(out_value, input_value):
    out_idx = _block_arg_index(out_value)
    input_idx = _block_arg_index(input_value)
    if out_idx is not None and input_idx is not None and input_idx < out_idx:
        return input_value, out_value
    return out_value, input_value


@emit_c_impl(KernelReduceOp, target="npu_demo")
def _emit_npu_demo_kernel_reduce(op: KernelReduceOp, ctx) -> str:
    from ... import emit_c_value

    out_value, input_value = _normalize_out_input_operands(op.out, op.input)
    if not isinstance(input_value.type, NnMemoryType) or not isinstance(out_value.type, NnMemoryType):
        raise emit_c_error(ctx, op.name, "unsupported op")
    if op.kind.data != "sum":
        raise emit_c_error(ctx, op.name, f"unsupported kind={op.kind.data}")
    return (
        f"{ctx.current_indent}reduce_sum<{ctx.dispatch_attr(out_value.type)}, {ctx.dispatch_type(input_value.type.element_type)}, "
        f"{ctx.dispatch_type(out_value.type.element_type)}>"
        f"({emit_c_value(out_value, ctx)} /*out*/, {emit_c_value(input_value, ctx)} /*input*/, {op.axis.value.data} /*axis*/);"
    )


@emit_c_impl(KernelReduceMinOp, target="npu_demo")
def _emit_npu_demo_kernel_reduce_min(op: KernelReduceMinOp, ctx) -> str:
    from ... import emit_c_value

    out_value, input_value = _normalize_out_input_operands(op.out, op.input)
    if not isinstance(input_value.type, NnMemoryType) or not isinstance(out_value.type, NnMemoryType):
        raise emit_c_error(ctx, op.name, "unsupported op")
    return (
        f"{ctx.current_indent}reduce_min<{ctx.dispatch_attr(out_value.type)}, {ctx.dispatch_type(input_value.type.element_type)}, "
        f"{ctx.dispatch_type(out_value.type.element_type)}>"
        f"({emit_c_value(out_value, ctx)} /*out*/, {emit_c_value(input_value, ctx)} /*input*/, {op.axis.value.data} /*axis*/);"
    )
