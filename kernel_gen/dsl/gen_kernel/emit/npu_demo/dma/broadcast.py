from __future__ import annotations

from kernel_gen.dialect.dma import DmaBroadcastOp
from kernel_gen.dialect.nn import NnMemoryType

from ....errors import emit_c_error
from ...register import emit_c_impl


@emit_c_impl(DmaBroadcastOp, target="npu_demo")
def _emit_npu_demo_dma_broadcast(op: DmaBroadcastOp, ctx) -> str:
    from ... import emit_c_value

    if not isinstance(op.target.type, NnMemoryType) or not isinstance(op.source.type, NnMemoryType):
        raise emit_c_error(ctx, op.name, "unsupported op")
    dst_expr = emit_c_value(op.target, ctx)
    src_expr = emit_c_value(op.source, ctx)
    return (
        f"{ctx.current_indent}broadcast<{ctx.dispatch_attr(op.target.type)}, {ctx.dispatch_attr(op.source.type)}, "
        f"{ctx.dispatch_type(op.target.type.element_type)}, {ctx.dispatch_type(op.source.type.element_type)}>"
        f"({dst_expr} /*dst*/, {src_expr} /*source*/);"
    )
