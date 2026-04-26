from __future__ import annotations

from xdsl.dialects.builtin import StringAttr

from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.tuner import TunerCostOp

from ....errors import emit_c_error
from ...register import emit_c_impl


def _require_tuner_cost_memory_type(value, ctx, role: str) -> NnMemoryType:
    if not isinstance(value.type, NnMemoryType):
        raise emit_c_error(ctx, "tuner.cost", f"{role} must be nn.memory")
    return value.type


@emit_c_impl(TunerCostOp, target="npu_demo")
def _emit_npu_demo_tuner_cost(op: TunerCostOp, ctx) -> str:
    from ... import emit_c_value

    if not isinstance(op.cost_kind, StringAttr):
        raise emit_c_error(ctx, "tuner.cost", "cost_kind must be string attr")
    if not isinstance(op.op_name, StringAttr):
        raise emit_c_error(ctx, "tuner.cost", "op_name must be string attr")
    helper_kind = op.cost_kind.data
    helper_name = op.op_name.data
    result_name = ctx.create_or_get_name(op.result)
    operands = tuple(op.operands)
    if helper_name == "kernel.add":
        if len(operands) != 3:
            raise emit_c_error(ctx, "tuner.cost", f"op_name={helper_name} requires out, lhs, rhs")
        out_value, lhs_value, rhs_value = operands
        out_type = _require_tuner_cost_memory_type(out_value, ctx, "out")
        lhs_type = _require_tuner_cost_memory_type(lhs_value, ctx, "lhs")
        rhs_type = _require_tuner_cost_memory_type(rhs_value, ctx, "rhs")
        out_space = ctx.dispatch_attr(out_type)
        if ctx.dispatch_attr(lhs_type) != out_space or ctx.dispatch_attr(rhs_type) != out_space:
            raise emit_c_error(ctx, "tuner.cost", "kernel.add operands must share memory space")
        lhs_dtype = ctx.dispatch_type(lhs_type.element_type)
        rhs_dtype = ctx.dispatch_type(rhs_type.element_type)
        if lhs_dtype != rhs_dtype:
            raise emit_c_error(ctx, "tuner.cost", "kernel.add lhs/rhs element type must match")
        out_dtype = ctx.dispatch_type(out_type.element_type)
        out_expr = emit_c_value(out_value, ctx)
        lhs_expr = emit_c_value(lhs_value, ctx)
        rhs_expr = emit_c_value(rhs_value, ctx)
        return (
            f"{ctx.current_indent}S_INT {result_name} = "
            f"cost::add<{out_space}, {lhs_dtype}, {out_dtype}, {helper_kind}>"
            f"({out_expr} /*out*/, {lhs_expr} /*lhs*/, {rhs_expr} /*rhs*/);"
        )
    if helper_name == "dma.copy":
        if len(operands) != 2:
            raise emit_c_error(ctx, "tuner.cost", f"op_name={helper_name} requires target, source")
        target_value, source_value = operands
        target_type = _require_tuner_cost_memory_type(target_value, ctx, "target")
        source_type = _require_tuner_cost_memory_type(source_value, ctx, "source")
        target_dtype = ctx.dispatch_type(target_type.element_type)
        source_dtype = ctx.dispatch_type(source_type.element_type)
        if target_dtype != source_dtype:
            raise emit_c_error(ctx, "tuner.cost", "dma.copy source/target element type must match")
        target_expr = emit_c_value(target_value, ctx)
        source_expr = emit_c_value(source_value, ctx)
        return (
            f"{ctx.current_indent}S_INT {result_name} = "
            f"cost::copy<{ctx.dispatch_attr(target_type)}, {ctx.dispatch_attr(source_type)}, {target_dtype}, {helper_kind}>"
            f"({target_expr} /*target*/, {source_expr} /*source*/);"
        )
    if helper_name == "kernel.matmul":
        if len(operands) != 3:
            raise emit_c_error(ctx, "tuner.cost", f"op_name={helper_name} requires out, lhs, rhs")
        out_value, lhs_value, rhs_value = operands
        out_type = _require_tuner_cost_memory_type(out_value, ctx, "out")
        lhs_type = _require_tuner_cost_memory_type(lhs_value, ctx, "lhs")
        rhs_type = _require_tuner_cost_memory_type(rhs_value, ctx, "rhs")
        out_expr = emit_c_value(out_value, ctx)
        lhs_expr = emit_c_value(lhs_value, ctx)
        rhs_expr = emit_c_value(rhs_value, ctx)
        return (
            f"{ctx.current_indent}S_INT {result_name} = "
            f"cost::matmul<{ctx.dispatch_attr(lhs_type)}, {ctx.dispatch_attr(rhs_type)}, {ctx.dispatch_attr(out_type)}, "
            f"{ctx.dispatch_type(lhs_type.element_type)}, {ctx.dispatch_type(rhs_type.element_type)}, {ctx.dispatch_type(out_type.element_type)}, "
            f"{helper_kind}>({out_expr} /*out*/, {lhs_expr} /*lhs*/, {rhs_expr} /*rhs*/);"
        )
    raise emit_c_error(ctx, "tuner.cost", f"unsupported op_name={helper_name}")
