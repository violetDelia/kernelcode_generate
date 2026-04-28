from __future__ import annotations

from kernel_gen.dialect.dma import DmaDesliceOp

from ...register import emit_c_impl


def _emit_brace_list(values, ctx, emit_value) -> str:
    return "{" + ", ".join(emit_value(value, ctx) for value in values) + "}"


def _emit_vector_expr(values, ctx, emit_value) -> str:
    if not 1 <= len(values) <= 4:
        raise ctx.emit_error("dma.deslice", "npu_demo Vector supports 1..4 values")
    return "Vector{" + ", ".join(emit_value(value, ctx) for value in values) + "}"


@emit_c_impl(DmaDesliceOp, target="npu_demo")
def _emit_npu_demo_dma_deslice(op: DmaDesliceOp, ctx) -> str:
    from ... import emit_c_value

    source_expr = emit_c_value(op.source, ctx)
    target_expr = emit_c_value(op.target, ctx)
    ctx.bind_name(op.result, target_expr)
    if len(op.offsets) == len(op.sizes) == len(op.strides) == 1:
        return (
            f"{ctx.current_indent}deslice({target_expr} /*target*/, {source_expr} /*source*/, "
            f"{emit_c_value(op.offsets[0], ctx)} /*offset*/, {emit_c_value(op.sizes[0], ctx)} /*size*/, "
            f"{emit_c_value(op.strides[0], ctx)} /*stride*/);"
        )
    if len(op.offsets) == len(op.sizes) == len(op.strides) == 3:
        return (
            f"{ctx.current_indent}deslice({target_expr} /*target*/, {source_expr} /*source*/, "
            f"{_emit_brace_list(op.offsets, ctx, emit_c_value)} /*offset*/, {_emit_brace_list(op.sizes, ctx, emit_c_value)} /*size*/, "
            f"{_emit_brace_list(op.strides, ctx, emit_c_value)} /*stride*/);"
        )
    offset_vec = _emit_vector_expr(op.offsets, ctx, emit_c_value)
    size_vec = _emit_vector_expr(op.sizes, ctx, emit_c_value)
    stride_vec = _emit_vector_expr(op.strides, ctx, emit_c_value)
    return (
        f"{ctx.current_indent}deslice({target_expr} /*target*/, {source_expr} /*source*/, "
        f"{offset_vec} /*offset*/, {size_vec} /*size*/, {stride_vec} /*stride*/);"
    )
