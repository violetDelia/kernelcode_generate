from __future__ import annotations

from xdsl.dialects.builtin import IntAttr

from kernel_gen.dialect.symbol import SymbolGetStrideOp

from ....errors import emit_c_error
from ...register import emit_c_impl, emit_c_value_impl


@emit_c_impl(SymbolGetStrideOp, target="npu_demo")
def _emit_npu_demo_symbol_get_stride(op: SymbolGetStrideOp, ctx) -> str:
    from ... import emit_c_value

    result = op.results[0]
    result_type = ctx.dispatch_type(result.type)
    expr = emit_c_value(result, ctx)
    result_name = ctx.create_or_get_name(result)
    return f"{ctx.current_indent}{result_type} {result_name} = {expr};"


@emit_c_value_impl(SymbolGetStrideOp, target="npu_demo")
def _emit_npu_demo_symbol_get_stride_value(value, ctx) -> str:
    from ... import emit_c_value

    owner = value.owner
    if not isinstance(owner.axis, IntAttr):
        raise emit_c_error(ctx, owner.name, "axis must be IntAttr")
    source_expr = emit_c_value(owner.source, ctx)
    return f"{source_expr}.get_stride({owner.axis.data})"
