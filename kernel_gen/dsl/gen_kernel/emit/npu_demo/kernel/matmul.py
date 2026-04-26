from __future__ import annotations

from kernel_gen.dialect.kernel import KernelMatmulOp

from ...register import emit_c_impl


def _block_arg_index(value) -> int | None:
    return value.index if hasattr(value, "index") else None


def _normalize_matmul_operands(op: KernelMatmulOp):
    out_value = op.out
    lhs_value = op.lhs
    rhs_value = op.rhs
    out_idx = _block_arg_index(out_value)
    lhs_idx = _block_arg_index(lhs_value)
    rhs_idx = _block_arg_index(rhs_value)
    if (
        out_idx is not None
        and lhs_idx is not None
        and rhs_idx is not None
        and rhs_idx < out_idx
        and rhs_idx < lhs_idx
    ):
        return rhs_value, out_value, lhs_value
    return out_value, lhs_value, rhs_value


@emit_c_impl(KernelMatmulOp, target="npu_demo")
def _emit_npu_demo_kernel_matmul(op: KernelMatmulOp, ctx) -> str:
    from ... import emit_c_value

    out_value, lhs_value, rhs_value = _normalize_matmul_operands(op)
    out_expr = emit_c_value(out_value, ctx)
    lhs_expr = emit_c_value(lhs_value, ctx)
    rhs_expr = emit_c_value(rhs_value, ctx)
    lhs_space = ctx.dispatch_attr(lhs_value.type)
    rhs_space = ctx.dispatch_attr(rhs_value.type)
    out_space = ctx.dispatch_attr(out_value.type)
    lhs_type = ctx.dispatch_type(lhs_value.type.element_type)
    rhs_type = ctx.dispatch_type(rhs_value.type.element_type)
    out_type = ctx.dispatch_type(out_value.type.element_type)
    return (
        f"{ctx.current_indent}matmul<{lhs_space}, {rhs_space}, {out_space}, "
        f"{lhs_type}, {rhs_type}, {out_type}>({out_expr} /*out*/, {lhs_expr} /*lhs*/, {rhs_expr} /*rhs*/);"
    )
