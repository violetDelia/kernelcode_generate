from __future__ import annotations

from kernel_gen.dialect.arch import ArchGetDynamicMemoryOp

from ....errors import emit_c_error
from ...register import emit_c_impl, emit_c_value_impl

_NPU_DYNAMIC_MEMORY_SPACES = {"TSM", "TLM1", "TLM2", "TLM3"}


@emit_c_impl(ArchGetDynamicMemoryOp, target="npu_demo")
def _emit_npu_demo_get_dynamic_memory_op(op: ArchGetDynamicMemoryOp, ctx) -> str:
    result_name = ctx.create_or_get_name(op.result)
    memory_type = ctx.dispatch_type(op.result.type)
    space_expr = ctx.dispatch_attr(op.memory_space.space.data)
    if space_expr not in _NPU_DYNAMIC_MEMORY_SPACES:
        raise emit_c_error(ctx, op.name, "unsupported dynamic memory space")
    return f"{ctx.current_indent}{memory_type} {result_name} = npu_demo::get_dynamic_memory<{space_expr}>();"


@emit_c_value_impl(ArchGetDynamicMemoryOp, target="npu_demo")
def _emit_npu_demo_get_dynamic_memory_value(value, ctx) -> str:
    op = value.owner
    space_expr = ctx.dispatch_attr(op.memory_space.space.data)
    if space_expr not in _NPU_DYNAMIC_MEMORY_SPACES:
        raise emit_c_error(ctx, op.name, "unsupported dynamic memory space")
    return f"npu_demo::get_dynamic_memory<{space_expr}>()"
