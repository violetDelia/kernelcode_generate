from __future__ import annotations

from kernel_gen.dialect.dma import DmaFillOp

from ...register import emit_c_impl
@emit_c_impl(DmaFillOp, target="npu_demo")
def _emit_npu_demo_dma_fill(op: DmaFillOp, ctx) -> str:
    from ... import emit_c_value

    target_expr = emit_c_value(op.target, ctx)
    space_expr = ctx.dispatch_attr(op.target.type)
    target_type = ctx.dispatch_type(op.target.type.element_type)
    value_expr = emit_c_value(op.value, ctx)
    return f"{ctx.current_indent}fill<{space_expr}, {target_type}>({target_expr} /*dst*/, {value_expr} /*value*/);"
