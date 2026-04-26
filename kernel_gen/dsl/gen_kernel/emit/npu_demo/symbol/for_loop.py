from __future__ import annotations

from kernel_gen.dialect.symbol import SymbolForOp
from xdsl.dialects import scf

from ...register import emit_c_impl


@emit_c_impl(SymbolForOp, target="npu_demo")
def _emit_npu_demo_symbol_for(op: SymbolForOp, ctx) -> str:
    from ... import emit_c_op, emit_c_value

    block = op.body.block
    iv_name = ctx.create_or_get_name(block.args[0], prefix="i")
    lower_expr = emit_c_value(op.start, ctx)
    upper_expr = emit_c_value(op.end, ctx)
    step_expr = emit_c_value(op.step, ctx)
    lines = [
        f"{ctx.current_indent}for (S_INT {iv_name} = {lower_expr}; {iv_name} < {upper_expr}; {iv_name} += {step_expr}) {{"
    ]
    ctx.push_indent()
    for body_op in block.ops:
        if isinstance(body_op, scf.YieldOp):
            continue
        stmt = emit_c_op(body_op, ctx)
        if stmt:
            lines.append(stmt)
    ctx.pop_indent()
    lines.append(f"{ctx.current_indent}}}")
    return "\n".join(lines)
