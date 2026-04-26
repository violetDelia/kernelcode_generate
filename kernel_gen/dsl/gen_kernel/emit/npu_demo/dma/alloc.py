from __future__ import annotations

from xdsl.dialects.builtin import IntAttr, StringAttr

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.symbol import SymbolValueType

from ....errors import emit_c_error
from ...register import emit_c_impl


def _format_alloc_layout(ctx, values, subject: str, *, symbol_bindings: dict[str, str] | None = None) -> list[str]:
    formatted: list[str] = []
    for value in values:
        if isinstance(value, IntAttr):
            formatted.append(str(value.data))
            continue
        if isinstance(value, StringAttr):
            mapped = None
            layout_expr = value.data
            if symbol_bindings is not None:
                mapped = symbol_bindings.get(layout_expr)
                if mapped is None:
                    mapped = symbol_bindings.get(layout_expr.replace(" ", ""))
                if mapped is None and layout_expr.startswith("(") and layout_expr.endswith(")"):
                    unwrapped_expr = layout_expr[1:-1]
                    mapped = symbol_bindings.get(unwrapped_expr) or symbol_bindings.get(unwrapped_expr.replace(" ", ""))
            formatted.append(mapped or layout_expr)
            continue
        raise emit_c_error(ctx, subject, "unsupported alloc layout value")
    return formatted


@emit_c_impl(DmaAllocOp, target="npu_demo")
def _emit_npu_demo_dma_alloc(op: DmaAllocOp, ctx) -> str:
    from ... import emit_c_value

    result_name = ctx.create_or_get_name(op.result)
    result_type = op.result.type
    shape_values = [emit_c_value(value, ctx) for value in op.dynamic_shape]
    if not shape_values:
        shape_values = _format_alloc_layout(ctx, result_type.shape.data, op.name)
    symbol_bindings: dict[str, str] = {}
    for value in op.dynamic_shape:
        value_type = value.type
        if isinstance(value_type, SymbolValueType):
            value_expr = value_type.expr.expr.data
            value_name = emit_c_value(value, ctx)
            for expr_key in (value_expr, f"({value_expr})", value_expr.replace(" ", "")):
                symbol_bindings[expr_key] = value_name
            public_value = value_type.get_value()
            if isinstance(public_value, str):
                for expr_key in (public_value, f"({public_value})", public_value.replace(" ", "")):
                    symbol_bindings[expr_key] = value_name
    stride_values = _format_alloc_layout(ctx, result_type.stride.data, f"{op.name} stride", symbol_bindings=symbol_bindings)
    if not hasattr(result_type, "element_type"):
        raise emit_c_error(ctx, op.name, "result must be nn.memory")
    space_expr = ctx.dispatch_attr(result_type)
    element_type = ctx.dispatch_type(result_type.element_type)
    shape_text = ", ".join(shape_values)
    stride_text = ", ".join(stride_values)
    return (
        f"{ctx.current_indent}Memory<{space_expr}, {element_type}> {result_name} = "
        f"alloc<{space_expr}, {element_type}>({{{shape_text}}} /*shape*/, {{{stride_text}}} /*stride*/);"
    )
