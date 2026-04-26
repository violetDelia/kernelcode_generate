from __future__ import annotations

from kernel_gen.dialect.symbol import SymbolToFloatOp

from ...register import emit_c_impl, emit_c_value_impl


@emit_c_impl(SymbolToFloatOp, target="npu_demo")
def _emit_npu_demo_symbol_to_float(op: SymbolToFloatOp, ctx) -> str:
    from ... import emit_c_value

    result = op.results[0]
    result_type = ctx.dispatch_type(result.type)
    expr = emit_c_value(result, ctx)
    result_name = ctx.create_or_get_name(result)
    return f"{ctx.current_indent}{result_type} {result_name} = {expr};"


@emit_c_value_impl(SymbolToFloatOp, target="npu_demo")
def _emit_npu_demo_symbol_to_float_value(value, ctx) -> str:
    from ... import emit_c_value

    return emit_c_value(value.owner.source, ctx)
