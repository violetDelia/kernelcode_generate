from __future__ import annotations

from kernel_gen.dialect.dma import DmaCopyOp

from ...register import emit_c_impl


@emit_c_impl(DmaCopyOp, target="npu_demo")
def _emit_npu_demo_dma_copy(op: DmaCopyOp, ctx) -> str:
    from ... import emit_c_value

    target_expr = emit_c_value(op.target, ctx)
    source_expr = emit_c_value(op.source, ctx)
    target_space = ctx.dispatch_attr(op.target.type)
    source_space = ctx.dispatch_attr(op.source.type)
    target_type = ctx.dispatch_type(op.target.type.element_type)
    source_type = ctx.dispatch_type(op.source.type.element_type)
    return (
        f"{ctx.current_indent}copy<{target_space}, {source_space}, {target_type}, {source_type}>"
        f"({target_expr} /*dst*/, {source_expr} /*source*/);"
    )
