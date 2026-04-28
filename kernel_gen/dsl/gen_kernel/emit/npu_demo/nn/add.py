from __future__ import annotations

from kernel_gen.dialect.nn import NnAddOp, NnMemoryType

from ...register import emit_c_impl


@emit_c_impl(NnAddOp, target="npu_demo")
def _emit_npu_demo_nn_add(op: NnAddOp, ctx) -> str:
    from ... import emit_c_value

    if not isinstance(op.lhs.type, NnMemoryType) or not isinstance(op.rhs.type, NnMemoryType) or not isinstance(op.result.type, NnMemoryType):
        raise ctx.emit_error(op.name, "unsupported op")
    result_name = ctx.lookup_name(op.result)
    if result_name is None:
        raise ctx.emit_error(op.name, "unsupported op")
    lhs_expr = emit_c_value(op.lhs, ctx)
    rhs_expr = emit_c_value(op.rhs, ctx)
    space_expr = ctx.dispatch_attr(op.result.type)
    input_type = ctx.dispatch_type(op.lhs.type.element_type)
    output_type = ctx.dispatch_type(op.result.type.element_type)
    return (
        f"{ctx.current_indent}add<{space_expr}, {input_type}, {output_type}>"
        f"({result_name} /*out*/, {lhs_expr} /*lhs*/, {rhs_expr} /*rhs*/);"
    )
