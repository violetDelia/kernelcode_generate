from __future__ import annotations

from kernel_gen.dialect.arch import ArchGetThreadNumOp

from ...register import emit_c_impl, emit_c_value_impl


@emit_c_impl(ArchGetThreadNumOp, target="npu_demo")
def _emit_npu_demo_get_thread_num_op(op: ArchGetThreadNumOp, ctx) -> str:
    result_name = ctx.create_or_get_name(op.result)
    result_type = ctx.dispatch_type(op.result.type)
    return f"{ctx.current_indent}{result_type} {result_name} = npu_demo::thread_num();"


@emit_c_value_impl(ArchGetThreadNumOp, target="npu_demo")
def _emit_npu_demo_get_thread_num_value(value, ctx) -> str:
    bound = ctx.lookup_name(value)
    if bound is not None:
        return bound
    return "npu_demo::thread_num()"
