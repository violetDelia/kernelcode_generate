from __future__ import annotations

from kernel_gen.dialect.kernel import KernelSelectOp
from kernel_gen.dialect.nn import NnMemoryType

from ...register import emit_c_impl


def _block_arg_index(value) -> int | None:
    return value.index if hasattr(value, "index") else None


def _normalize_select_operands(op: KernelSelectOp):
    out_value = op.out
    cond_value = op.cond
    lhs_value = op.lhs
    rhs_value = op.rhs
    out_idx = _block_arg_index(out_value)
    cond_idx = _block_arg_index(cond_value)
    lhs_idx = _block_arg_index(lhs_value)
    rhs_idx = _block_arg_index(rhs_value)
    if (
        out_idx is not None
        and cond_idx is not None
        and lhs_idx is not None
        and rhs_idx is not None
        and rhs_idx < out_idx
        and rhs_idx < cond_idx
        and rhs_idx < lhs_idx
    ):
        return rhs_value, out_value, cond_value, lhs_value
    return out_value, cond_value, lhs_value, rhs_value


@emit_c_impl(KernelSelectOp, target="npu_demo")
def _emit_npu_demo_kernel_select(op: KernelSelectOp, ctx) -> str:
    from ... import emit_c_value

    out_value, cond_value, lhs_value, rhs_value = _normalize_select_operands(op)
    if not all(
        isinstance(value.type, NnMemoryType)
        for value in (out_value, cond_value, lhs_value, rhs_value)
    ):
        raise ctx.emit_error(op.name, "unsupported op")
    return (
        f"{ctx.current_indent}select<{ctx.dispatch_attr(out_value.type)}, {ctx.dispatch_type(lhs_value.type.element_type)}, "
        f"{ctx.dispatch_type(out_value.type.element_type)}>"
        f"({emit_c_value(out_value, ctx)} /*out*/, {emit_c_value(cond_value, ctx)} /*cond*/, "
        f"{emit_c_value(lhs_value, ctx)} /*lhs*/, {emit_c_value(rhs_value, ctx)} /*rhs*/);"
    )
