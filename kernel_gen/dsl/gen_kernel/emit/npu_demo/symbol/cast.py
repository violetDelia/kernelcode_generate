from __future__ import annotations

from xdsl.dialects.builtin import StringAttr
from xdsl.ir import Operation

from kernel_gen.dialect.symbol import SymbolConstOp
from kernel_gen.dialect.symbol import SymbolCastOp, SymbolToIntOp

from ...register import emit_c_impl, emit_c_value_impl


def _is_symbol_const_like(op: object) -> bool:
    if isinstance(op, SymbolConstOp):
        return True
    if not isinstance(op, Operation):
        return False
    op_name_attr = op.attributes.get("op_name__")
    return (
        op.name == "builtin.unregistered"
        and isinstance(op_name_attr, StringAttr)
        and op_name_attr.data == "symbol.const"
    )


@emit_c_impl(SymbolToIntOp, SymbolCastOp, target="npu_demo")
def _emit_npu_demo_symbol_cast(op, ctx) -> str:
    result_name = ctx.lookup_name(op.result)
    if result_name is None:
        source_owner = op.source.owner
        if _is_symbol_const_like(source_owner):
            source_name = _emit_npu_demo_symbol_cast_value(op.source, ctx)
            result_name = ctx.create_or_get_name(
                op.result,
                preferred=f"{source_name}_cast_{ctx.dispatch_type(op.result.type)}",
            )
        else:
            result_name = ctx.create_or_get_name(
                op.result,
                preferred=f"value_cast_{ctx.dispatch_type(op.result.type)}",
            )
    return f"{ctx.current_indent}{ctx.dispatch_type(op.result.type)} {result_name} = {_emit_npu_demo_symbol_cast_value(op.source, ctx)};"


@emit_c_value_impl(SymbolToIntOp, SymbolCastOp, target="npu_demo")
def _emit_npu_demo_symbol_cast_value(value, ctx) -> str:
    bound = ctx.lookup_name(value)
    if bound is not None:
        return bound
    from ... import emit_c_value

    return emit_c_value(value.owner.source, ctx)
