from __future__ import annotations

from kernel_gen.dialect.dma import DmaCastOp
from kernel_gen.dialect.nn import NnMemoryType

from ...register import emit_c_impl


@emit_c_impl(DmaCastOp, target="npu_demo")
def _emit_npu_demo_dma_cast(op: DmaCastOp, ctx) -> str:
    from ... import emit_c_value

    if len(op.operands) == 2:
        target_value = op.target
        source_value = op.source
        target_type_attr = op.target.type
    elif len(op.operands) == 1 and len(op.results) == 1:
        target_value = op.results[0]
        source_value = op.operands[0]
        target_type_attr = op.results[0].type
    else:
        raise ctx.emit_error(op.name, "unsupported op")
    if not isinstance(target_type_attr, NnMemoryType) or not isinstance(source_value.type, NnMemoryType):
        raise ctx.emit_error(op.name, "unsupported op")
    target_expr = emit_c_value(target_value, ctx)
    source_expr = emit_c_value(source_value, ctx)
    return (
        f"{ctx.current_indent}cast<{ctx.dispatch_attr(target_type_attr)}, {ctx.dispatch_type(target_type_attr.element_type)}, "
        f"{ctx.dispatch_type(source_value.type.element_type)}>"
        f"({target_expr} /*dst*/, {source_expr} /*source*/);"
    )
