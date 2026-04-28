from __future__ import annotations

from xdsl.dialects.builtin import IntAttr

from kernel_gen.dialect.symbol import SymbolGetDimOp

from ...register import emit_c_impl, emit_c_value_impl


@emit_c_impl(SymbolGetDimOp, target="npu_demo")
def _emit_npu_demo_symbol_get_dim(op: SymbolGetDimOp, ctx) -> str:
    from ... import emit_c_value

    result = op.results[0]
    result_type = ctx.dispatch_type(result.type)
    expr = emit_c_value(result, ctx)
    result_name = ctx.create_or_get_name(result)
    return f"{ctx.current_indent}{result_type} {result_name} = {expr};"


@emit_c_value_impl(SymbolGetDimOp, target="npu_demo")
def _emit_npu_demo_symbol_get_dim_value(value, ctx) -> str:
    from ... import emit_c_value

    owner = value.owner
    if not isinstance(owner.axis, IntAttr):
        raise ctx.emit_error(owner.name, "axis must be IntAttr")
    source_expr = emit_c_value(owner.source, ctx)
    return f"{source_expr}.get_shape({owner.axis.data})"
