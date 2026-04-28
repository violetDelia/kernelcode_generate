from __future__ import annotations

from kernel_gen.dialect.kernel import KernelBinaryElewiseOp
from kernel_gen.dialect.nn import NnMemoryType

from ...register import emit_c_impl


def _block_arg_index(value) -> int | None:
    return value.index if hasattr(value, "index") else None


def _normalize_binary_elewise_operands(op: KernelBinaryElewiseOp):
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


@emit_c_impl(KernelBinaryElewiseOp, target="npu_demo")
def _emit_npu_demo_kernel_binary_elewise(op: KernelBinaryElewiseOp, ctx) -> str:
    from ... import emit_c_value

    out_value, lhs_value, rhs_value = _normalize_binary_elewise_operands(op)
    if not all(isinstance(value.type, NnMemoryType) for value in (out_value, lhs_value, rhs_value)):
        raise ctx.emit_error(op.name, "unsupported op")
    helper_map = {
        "add": "add",
        "sub": "sub",
        "mul": "mul",
        "div": "truediv",
        "eq": "eq",
        "ne": "ne",
        "lt": "lt",
        "le": "le",
        "gt": "gt",
        "ge": "ge",
    }
    helper_name = helper_map.get(op.kind.data)
    if helper_name is None:
        raise ctx.emit_error(op.name, f"unsupported kind={op.kind.data}")
    out_expr = emit_c_value(out_value, ctx)
    lhs_expr = emit_c_value(lhs_value, ctx)
    rhs_expr = emit_c_value(rhs_value, ctx)
    space_expr = ctx.dispatch_attr(out_value.type)
    input_type = ctx.dispatch_type(lhs_value.type.element_type)
    output_type = ctx.dispatch_type(out_value.type.element_type)
    return (
        f"{ctx.current_indent}{helper_name}<{space_expr}, {input_type}, {output_type}>"
        f"({out_expr} /*out*/, {lhs_expr} /*lhs*/, {rhs_expr} /*rhs*/);"
    )
