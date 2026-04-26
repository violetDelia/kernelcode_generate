from __future__ import annotations

from xdsl.dialects.builtin import StringAttr
from xdsl.ir import Operation

from kernel_gen.dialect.dma import DmaLoadOp
from kernel_gen.dialect.symbol import SymbolConstOp

from ...register import emit_c_impl


def _emit_brace_list(values, ctx, emit_value) -> str:
    return "{" + ", ".join(emit_value(value, ctx) for value in values) + "}"


def _emit_symbol_literal_or_value(value, ctx, emit_value) -> str:
    owner = value.owner
    if isinstance(owner, SymbolConstOp):
        return str(owner.value.data)
    if (
        isinstance(owner, Operation)
        and owner.name == "builtin.unregistered"
        and isinstance(owner.attributes.get("op_name__"), StringAttr)
        and owner.attributes["op_name__"].data == "symbol.const"
        and owner.results
    ):
        return owner.results[0].type.expr.expr.data
    return emit_value(value, ctx)


@emit_c_impl(DmaLoadOp, target="npu_demo")
def _emit_npu_demo_dma_load(op: DmaLoadOp, ctx) -> str:
    from ... import emit_c_value

    target_expr = emit_c_value(op.target, ctx)
    source_expr = emit_c_value(op.source, ctx)
    offset_expr = _emit_brace_list(op.offsets, ctx, lambda value, inner_ctx: _emit_symbol_literal_or_value(value, inner_ctx, emit_c_value))
    size_expr = _emit_brace_list(op.sizes, ctx, lambda value, inner_ctx: _emit_symbol_literal_or_value(value, inner_ctx, emit_c_value))
    stride_expr = _emit_brace_list(op.strides, ctx, lambda value, inner_ctx: _emit_symbol_literal_or_value(value, inner_ctx, emit_c_value))
    return (
        f"{ctx.current_indent}load<{ctx.dispatch_attr(op.target.type)}, {ctx.dispatch_attr(op.source.type)}, "
        f"{ctx.dispatch_type(op.target.type.element_type)}, {ctx.dispatch_type(op.source.type.element_type)}>"
        f"({target_expr} /*dst*/, {source_expr} /*source*/, {offset_expr} /*offset*/, "
        f"{size_expr} /*size*/, {stride_expr} /*stride*/);"
    )
