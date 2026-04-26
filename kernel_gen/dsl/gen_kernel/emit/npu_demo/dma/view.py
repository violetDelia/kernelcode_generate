from __future__ import annotations

from kernel_gen.dialect.dma import DmaViewOp

from ...register import emit_c_impl


def _emit_brace_list(values, ctx, emit_value) -> str:
    return "{" + ", ".join(emit_value(value, ctx) for value in values) + "}"


@emit_c_impl(DmaViewOp, target="npu_demo")
def _emit_npu_demo_dma_view(op: DmaViewOp, ctx) -> str:
    from ... import emit_c_value

    source_expr = emit_c_value(op.source, ctx)
    result_name = ctx.create_or_get_name(op.result)
    result_type = ctx.dispatch_type(op.result.type)
    element_type = ctx.dispatch_type(op.result.type.element_type)
    offset_expr = _emit_brace_list(op.offsets, ctx, emit_c_value)
    size_expr = _emit_brace_list(op.shape, ctx, emit_c_value)
    stride_expr = _emit_brace_list(op.stride, ctx, emit_c_value)
    return (
        f"{ctx.current_indent}{result_type} {result_name} = "
        f"{source_expr}.view<{element_type}>({offset_expr} /*offset*/, {size_expr} /*size*/, {stride_expr} /*stride*/);"
    )
