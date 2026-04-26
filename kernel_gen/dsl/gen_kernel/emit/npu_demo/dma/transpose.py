from __future__ import annotations

from xdsl.dialects.builtin import IntAttr

from kernel_gen.dialect.dma import DmaTransposeOp

from ...register import emit_c_impl


@emit_c_impl(DmaTransposeOp, target="npu_demo")
def _emit_npu_demo_dma_transpose(op: DmaTransposeOp, ctx) -> str:
    from ... import emit_c_value

    target_expr = emit_c_value(op.target, ctx)
    source_expr = emit_c_value(op.source, ctx)
    perm_values = ", ".join(
        str(value.data if isinstance(value, IntAttr) else value.value.data) for value in op.perm.data
    )
    return (
        f"{ctx.current_indent}transpose<{ctx.dispatch_attr(op.target.type)}, {ctx.dispatch_attr(op.source.type)}, "
        f"{ctx.dispatch_type(op.target.type.element_type)}, {ctx.dispatch_type(op.source.type.element_type)}>"
        f"({target_expr} /*dst*/, {source_expr} /*source*/, {{{perm_values}}} /*perm*/);"
    )
