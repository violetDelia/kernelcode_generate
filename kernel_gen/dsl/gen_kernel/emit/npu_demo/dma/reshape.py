from __future__ import annotations

from kernel_gen.dialect.dma import DmaReshapeOp

from ...register import emit_c_impl


def _emit_brace_list(values, ctx, emit_value) -> str:
    return "{" + ", ".join(emit_value(value, ctx) for value in values) + "}"


@emit_c_impl(DmaReshapeOp, target="npu_demo")
def _emit_npu_demo_dma_reshape(op: DmaReshapeOp, ctx) -> str:
    from ... import emit_c_value

    result_name = ctx.create_or_get_name(op.result)
    source_expr = emit_c_value(op.source, ctx)
    shape_expr = _emit_brace_list(op.shape, ctx, emit_c_value)
    return (
        f"{ctx.current_indent}{ctx.dispatch_type(op.result.type)} {result_name} = "
        f"{source_expr}.reshape({shape_expr} /*shape*/);"
    )
