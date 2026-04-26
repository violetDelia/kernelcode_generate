from __future__ import annotations

from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolDivOp,
    SymbolEqOp,
    SymbolFloorDivOp,
    SymbolGeOp,
    SymbolGtOp,
    SymbolLeOp,
    SymbolLtOp,
    SymbolMulOp,
    SymbolNeOp,
    SymbolSubOp,
)

from ....errors import emit_c_error
from ...register import emit_c_impl, emit_c_value_impl

_BINARY_SIGILS = {
    SymbolAddOp: "+",
    SymbolSubOp: "-",
    SymbolMulOp: "*",
    SymbolDivOp: "/",
    SymbolFloorDivOp: "/",
}

_COMPARE_SIGILS = {
    SymbolEqOp: "==",
    SymbolNeOp: "!=",
    SymbolLtOp: "<",
    SymbolLeOp: "<=",
    SymbolGtOp: ">",
    SymbolGeOp: ">=",
}


@emit_c_impl(
    SymbolAddOp,
    SymbolSubOp,
    SymbolMulOp,
    SymbolDivOp,
    SymbolFloorDivOp,
    SymbolEqOp,
    SymbolNeOp,
    SymbolLtOp,
    SymbolLeOp,
    SymbolGtOp,
    SymbolGeOp,
    target="npu_demo",
)
def _emit_npu_demo_symbol_binary_or_compare(op, ctx) -> str:
    from ... import emit_c_value

    result = op.results[0]
    result_type = ctx.dispatch_type(result.type)
    expr = emit_c_value(result, ctx)
    result_name = ctx.create_or_get_name(result)
    return f"{ctx.current_indent}{result_type} {result_name} = {expr};"


@emit_c_value_impl(
    SymbolAddOp,
    SymbolSubOp,
    SymbolMulOp,
    SymbolDivOp,
    SymbolFloorDivOp,
    SymbolEqOp,
    SymbolNeOp,
    SymbolLtOp,
    SymbolLeOp,
    SymbolGtOp,
    SymbolGeOp,
    target="npu_demo",
)
def _emit_npu_demo_symbol_binary_or_compare_value(value, ctx) -> str:
    owner = value.owner
    from ... import emit_c_value

    lhs = emit_c_value(owner.operands[0], ctx)
    rhs = emit_c_value(owner.operands[1], ctx)
    sigil = _BINARY_SIGILS.get(type(owner)) or _COMPARE_SIGILS.get(type(owner))
    if sigil is None:
        raise emit_c_error(ctx, owner.name, "unsupported target")
    return f"({lhs} {sigil} {rhs})"
