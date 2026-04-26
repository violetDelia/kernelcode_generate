from __future__ import annotations

from kernel_gen.dialect.dma import DmaFreeOp

from ...register import emit_c_impl


@emit_c_impl(DmaFreeOp, target="npu_demo")
def _emit_npu_demo_dma_free(op: DmaFreeOp, ctx) -> str:
    from ... import emit_c_value

    source_expr = emit_c_value(op.source, ctx)
    space_expr = ctx.dispatch_attr(op.source.type)
    source_type = ctx.dispatch_type(op.source.type.element_type)
    return f"{ctx.current_indent}free<{space_expr}, {source_type}>({source_expr} /*source*/);"
