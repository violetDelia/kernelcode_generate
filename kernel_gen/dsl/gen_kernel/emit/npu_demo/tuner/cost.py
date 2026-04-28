"""npu_demo tuner cost emitters.

创建者: 金铲铲大作战
最后一次更改: 大闸蟹

功能说明:
- 发射 `tuner.cost` 到 `npu_demo::cost::*` 公开 helper 调用。
- 当前文件内 helper 只服务本文件的 cost emit 细节，不作为跨文件公开 API。

API 列表:
- 无；本文件通过 `emit_c_impl(TunerCostOp, target="npu_demo")` 注册发射实现。

使用示例:
- source = emit_c(module, EmitCContext())

关联文件:
- spec: spec/dsl/gen_kernel/emit.md
- spec: spec/include/api/cost/Core.md
- spec: spec/include/api/cost/Dma.md
- spec: spec/include/api/cost/Kernel.md
- test: test/dsl/gen_kernel/emit/test_emit.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/cost.py
"""

from __future__ import annotations

from xdsl.dialects.builtin import IntegerAttr, StringAttr

from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.tuner import TunerCostOp

from ...register import emit_c_impl


def _require_tuner_cost_memory_type(value, ctx, role: str) -> NnMemoryType:
    """校验 tuner.cost 的 memory operand 类型。

    创建者: 金铲铲大作战
    最后一次更改: OpenAI Codex

    功能说明:
    - 要求给定 SSA value 的类型是 `NnMemoryType`，否则用 emit error 报出稳定错误。

    使用示例:
    - memory_type = _require_tuner_cost_memory_type(value, ctx, "target")
    """

    if not isinstance(value.type, NnMemoryType):
        raise ctx.emit_error("tuner.cost", f"{role} must be nn.memory")
    return value.type


def _emit_vector_expr(values, ctx, emit_value, op_name: str) -> str:
    """把 cost helper 的 offset/size/stride operands 发射为 `Vector{...}`。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 复用公开 `Vector` 形态承接 `cost::slice/deslice` 的向量参数。
    - 当前 npu_demo `Vector` 支持 1..4 个值，超出时显式失败。

    使用示例:
    - offset = _emit_vector_expr(offsets, ctx, emit_c_value, "dma.slice")
    """

    if not 1 <= len(values) <= 4:
        raise ctx.emit_error("tuner.cost", f"op_name={op_name} npu_demo Vector supports 1..4 values")
    return "Vector{" + ", ".join(emit_value(value, ctx) for value in values) + "}"


def _emit_symbol_operands(values: tuple[object, ...], ctx, emit_value, op_name: str) -> tuple[str, ...]:
    """发射 tuner.cost 的 symbol 标量 operands。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 保持 `img2col` 等 cost helper 的标量参数顺序。
    - 当前函数只做文本发射，不引入跨文件 helper 或私有 API。

    使用示例:
    - kh, kw = _emit_symbol_operands((kh_value, kw_value), ctx, emit_c_value, "kernel.img2col2d")
    """

    if not values:
        raise ctx.emit_error("tuner.cost", f"op_name={op_name} requires symbol operands")
    return tuple(emit_value(value, ctx) for value in values)


def _split_dma_region_operands(helper_name: str, operands: tuple[object, ...], rank: int, ctx):
    """拆分 `dma.slice/deslice` 成本 helper 的扁平 operand 列表。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - `LaunchKernelCostFuncPass` 透传原 op operands，`tuner.cost` 自身没有 segment attr。
    - 根据 memory rank 将 `target/source/offsets/sizes/strides` 从扁平列表中恢复出来。

    使用示例:
    - target, source, offsets, sizes, strides = _split_dma_region_operands("dma.slice", operands, 2, ctx)
    """

    expected = 2 + 3 * rank
    if len(operands) != expected:
        raise ctx.emit_error("tuner.cost", f"op_name={helper_name} requires target, source, offsets, sizes, strides")
    target_value = operands[0]
    source_value = operands[1]
    offsets = operands[2 : 2 + rank]
    sizes = operands[2 + rank : 2 + 2 * rank]
    strides = operands[2 + 2 * rank : 2 + 3 * rank]
    return target_value, source_value, offsets, sizes, strides


@emit_c_impl(TunerCostOp, target="npu_demo")
def _emit_npu_demo_tuner_cost(op: TunerCostOp, ctx) -> str:
    """发射 npu_demo `tuner.cost`。

    创建者: 金铲铲大作战
    最后一次更改: OpenAI Codex

    功能说明:
    - 将受支持的 `op_name` 映射到公开 `npu_demo::cost::*` helper。
    - `cost_kind` 按 IR 文本原样透传为模板实参。

    使用示例:
    - line = _emit_npu_demo_tuner_cost(op, ctx)
    """

    from ... import emit_c_value

    if not isinstance(op.cost_kind, StringAttr):
        raise ctx.emit_error("tuner.cost", "cost_kind must be string attr")
    if not isinstance(op.op_name, StringAttr):
        raise ctx.emit_error("tuner.cost", "op_name must be string attr")
    helper_kind = op.cost_kind.data
    helper_name = op.op_name.data
    result_name = ctx.create_or_get_name(op.result)
    operands = tuple(op.operands)
    if helper_name == "kernel.add":
        if len(operands) != 3:
            raise ctx.emit_error("tuner.cost", f"op_name={helper_name} requires out, lhs, rhs")
        out_value, lhs_value, rhs_value = operands
        out_type = _require_tuner_cost_memory_type(out_value, ctx, "out")
        lhs_type = _require_tuner_cost_memory_type(lhs_value, ctx, "lhs")
        rhs_type = _require_tuner_cost_memory_type(rhs_value, ctx, "rhs")
        out_space = ctx.dispatch_attr(out_type)
        if ctx.dispatch_attr(lhs_type) != out_space or ctx.dispatch_attr(rhs_type) != out_space:
            raise ctx.emit_error("tuner.cost", "kernel.add operands must share memory space")
        lhs_dtype = ctx.dispatch_type(lhs_type.element_type)
        rhs_dtype = ctx.dispatch_type(rhs_type.element_type)
        if lhs_dtype != rhs_dtype:
            raise ctx.emit_error("tuner.cost", "kernel.add lhs/rhs element type must match")
        out_dtype = ctx.dispatch_type(out_type.element_type)
        out_expr = emit_c_value(out_value, ctx)
        lhs_expr = emit_c_value(lhs_value, ctx)
        rhs_expr = emit_c_value(rhs_value, ctx)
        return (
            f"{ctx.current_indent}S_INT {result_name} = "
            f"cost::add<{out_space}, {lhs_dtype}, {out_dtype}, {helper_kind}>"
            f"({out_expr} /*out*/, {lhs_expr} /*lhs*/, {rhs_expr} /*rhs*/);"
        )
    if helper_name == "kernel.binary_elewise":
        if len(operands) != 3:
            raise ctx.emit_error("tuner.cost", f"op_name={helper_name} requires out, lhs, rhs")
        kernel_kind = op.attributes.get("kernel_kind")
        if not isinstance(kernel_kind, StringAttr):
            raise ctx.emit_error("tuner.cost", "kernel.binary_elewise requires kernel_kind string attr")
        helper_map = {
            "add": "add",
            "sub": "sub",
            "mul": "mul",
            "div": "truediv",
            "truediv": "truediv",
            "eq": "eq",
            "ne": "ne",
            "lt": "lt",
            "le": "le",
            "gt": "gt",
            "ge": "ge",
        }
        helper = helper_map.get(kernel_kind.data)
        if helper is None:
            raise ctx.emit_error("tuner.cost", f"kernel.binary_elewise unsupported kind={kernel_kind.data}")
        out_value, lhs_value, rhs_value = operands
        out_type = _require_tuner_cost_memory_type(out_value, ctx, "out")
        lhs_type = _require_tuner_cost_memory_type(lhs_value, ctx, "lhs")
        rhs_type = _require_tuner_cost_memory_type(rhs_value, ctx, "rhs")
        out_space = ctx.dispatch_attr(out_type)
        if ctx.dispatch_attr(lhs_type) != out_space or ctx.dispatch_attr(rhs_type) != out_space:
            raise ctx.emit_error("tuner.cost", "kernel.binary_elewise operands must share memory space")
        lhs_dtype = ctx.dispatch_type(lhs_type.element_type)
        rhs_dtype = ctx.dispatch_type(rhs_type.element_type)
        if lhs_dtype != rhs_dtype:
            raise ctx.emit_error("tuner.cost", "kernel.binary_elewise lhs/rhs element type must match")
        out_dtype = ctx.dispatch_type(out_type.element_type)
        out_expr = emit_c_value(out_value, ctx)
        lhs_expr = emit_c_value(lhs_value, ctx)
        rhs_expr = emit_c_value(rhs_value, ctx)
        return (
            f"{ctx.current_indent}S_INT {result_name} = "
            f"cost::{helper}<{out_space}, {lhs_dtype}, {out_dtype}, {helper_kind}>"
            f"({out_expr} /*out*/, {lhs_expr} /*lhs*/, {rhs_expr} /*rhs*/);"
        )
    if helper_name == "kernel.exp":
        if len(operands) != 2:
            raise ctx.emit_error("tuner.cost", f"op_name={helper_name} requires out, input")
        out_value, input_value = operands
        out_type = _require_tuner_cost_memory_type(out_value, ctx, "out")
        input_type = _require_tuner_cost_memory_type(input_value, ctx, "input")
        out_space = ctx.dispatch_attr(out_type)
        if ctx.dispatch_attr(input_type) != out_space:
            raise ctx.emit_error("tuner.cost", "kernel.exp operands must share memory space")
        out_expr = emit_c_value(out_value, ctx)
        input_expr = emit_c_value(input_value, ctx)
        return (
            f"{ctx.current_indent}S_INT {result_name} = "
            f"cost::exp<{out_space}, {ctx.dispatch_type(input_type.element_type)}, "
            f"{ctx.dispatch_type(out_type.element_type)}, {helper_kind}>"
            f"({out_expr} /*out*/, {input_expr} /*input*/);"
        )
    if helper_name == "kernel.select":
        if len(operands) != 4:
            raise ctx.emit_error("tuner.cost", f"op_name={helper_name} requires out, cond, lhs, rhs")
        out_value, cond_value, lhs_value, rhs_value = operands
        out_type = _require_tuner_cost_memory_type(out_value, ctx, "out")
        cond_type = _require_tuner_cost_memory_type(cond_value, ctx, "cond")
        lhs_type = _require_tuner_cost_memory_type(lhs_value, ctx, "lhs")
        rhs_type = _require_tuner_cost_memory_type(rhs_value, ctx, "rhs")
        out_space = ctx.dispatch_attr(out_type)
        if any(ctx.dispatch_attr(value_type) != out_space for value_type in (cond_type, lhs_type, rhs_type)):
            raise ctx.emit_error("tuner.cost", "kernel.select operands must share memory space")
        if ctx.dispatch_type(cond_type.element_type) != "bool":
            raise ctx.emit_error("tuner.cost", "kernel.select cond element type must be bool")
        lhs_dtype = ctx.dispatch_type(lhs_type.element_type)
        rhs_dtype = ctx.dispatch_type(rhs_type.element_type)
        if lhs_dtype != rhs_dtype:
            raise ctx.emit_error("tuner.cost", "kernel.select lhs/rhs element type must match")
        out_expr = emit_c_value(out_value, ctx)
        cond_expr = emit_c_value(cond_value, ctx)
        lhs_expr = emit_c_value(lhs_value, ctx)
        rhs_expr = emit_c_value(rhs_value, ctx)
        return (
            f"{ctx.current_indent}S_INT {result_name} = "
            f"cost::select<{out_space}, {lhs_dtype}, {ctx.dispatch_type(out_type.element_type)}, {helper_kind}>"
            f"({out_expr} /*out*/, {cond_expr} /*cond*/, {lhs_expr} /*lhs*/, {rhs_expr} /*rhs*/);"
        )
    if helper_name in ("kernel.reduce", "kernel.reduce_min"):
        if len(operands) != 2:
            raise ctx.emit_error("tuner.cost", f"op_name={helper_name} requires out, input")
        if helper_name == "kernel.reduce":
            kernel_kind = op.attributes.get("kernel_kind")
            if not isinstance(kernel_kind, StringAttr):
                raise ctx.emit_error("tuner.cost", "kernel.reduce requires kernel_kind string attr")
            helper = {
                "sum": "reduce_sum",
                "min": "reduce_min",
                "max": "reduce_max",
            }.get(kernel_kind.data)
            if helper is None:
                raise ctx.emit_error("tuner.cost", f"kernel.reduce unsupported kind={kernel_kind.data}")
        else:
            helper = "reduce_min"
        axis = op.attributes.get("axis")
        if not isinstance(axis, IntegerAttr):
            raise ctx.emit_error("tuner.cost", f"{helper_name} requires integer axis attr")
        out_value, input_value = operands
        out_type = _require_tuner_cost_memory_type(out_value, ctx, "out")
        input_type = _require_tuner_cost_memory_type(input_value, ctx, "input")
        out_space = ctx.dispatch_attr(out_type)
        if ctx.dispatch_attr(input_type) != out_space:
            raise ctx.emit_error("tuner.cost", f"{helper_name} operands must share memory space")
        out_expr = emit_c_value(out_value, ctx)
        input_expr = emit_c_value(input_value, ctx)
        return (
            f"{ctx.current_indent}S_INT {result_name} = "
            f"cost::{helper}<{out_space}, {ctx.dispatch_type(input_type.element_type)}, "
            f"{ctx.dispatch_type(out_type.element_type)}, {helper_kind}>"
            f"({out_expr} /*out*/, {input_expr} /*input*/, {axis.value.data} /*axis*/);"
        )
    if helper_name == "dma.copy":
        if len(operands) != 2:
            raise ctx.emit_error("tuner.cost", f"op_name={helper_name} requires target, source")
        target_value, source_value = operands
        target_type = _require_tuner_cost_memory_type(target_value, ctx, "target")
        source_type = _require_tuner_cost_memory_type(source_value, ctx, "source")
        target_dtype = ctx.dispatch_type(target_type.element_type)
        source_dtype = ctx.dispatch_type(source_type.element_type)
        if target_dtype != source_dtype:
            raise ctx.emit_error("tuner.cost", "dma.copy source/target element type must match")
        target_expr = emit_c_value(target_value, ctx)
        source_expr = emit_c_value(source_value, ctx)
        return (
            f"{ctx.current_indent}S_INT {result_name} = "
            f"cost::copy<{ctx.dispatch_attr(target_type)}, {ctx.dispatch_attr(source_type)}, {target_dtype}, {helper_kind}>"
            f"({target_expr} /*target*/, {source_expr} /*source*/);"
        )
    if helper_name in ("dma.slice", "dma.deslice"):
        if len(operands) < 2:
            raise ctx.emit_error("tuner.cost", f"op_name={helper_name} requires target, source, offsets, sizes, strides")
        target_type = _require_tuner_cost_memory_type(operands[0], ctx, "target")
        source_type = _require_tuner_cost_memory_type(operands[1], ctx, "source")
        rank = len(source_type.shape.data) if helper_name == "dma.slice" else len(target_type.shape.data)
        target_value, source_value, offsets, sizes, strides = _split_dma_region_operands(
            helper_name,
            operands,
            rank,
            ctx,
        )
        target_dtype = ctx.dispatch_type(target_type.element_type)
        source_dtype = ctx.dispatch_type(source_type.element_type)
        if target_dtype != source_dtype:
            raise ctx.emit_error("tuner.cost", f"{helper_name} source/target element type must match")
        helper = "slice" if helper_name == "dma.slice" else "deslice"
        target_expr = emit_c_value(target_value, ctx)
        source_expr = emit_c_value(source_value, ctx)
        offset_expr = _emit_vector_expr(offsets, ctx, emit_c_value, helper_name)
        size_expr = _emit_vector_expr(sizes, ctx, emit_c_value, helper_name)
        stride_expr = _emit_vector_expr(strides, ctx, emit_c_value, helper_name)
        return (
            f"{ctx.current_indent}S_INT {result_name} = "
            f"cost::{helper}<{ctx.dispatch_attr(target_type)}, {ctx.dispatch_attr(source_type)}, {target_dtype}, {helper_kind}>"
            f"({target_expr} /*target*/, {source_expr} /*source*/, {offset_expr} /*offset*/, "
            f"{size_expr} /*size*/, {stride_expr} /*stride*/);"
        )
    if helper_name == "kernel.matmul":
        if len(operands) != 3:
            raise ctx.emit_error("tuner.cost", f"op_name={helper_name} requires out, lhs, rhs")
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
    if helper_name == "kernel.img2col1d":
        if len(operands) != 7:
            raise ctx.emit_error("tuner.cost", f"op_name={helper_name} requires out, input, k, s, d, p_left, p_right")
        out_value, input_value, *symbol_values = operands
        out_type = _require_tuner_cost_memory_type(out_value, ctx, "out")
        input_type = _require_tuner_cost_memory_type(input_value, ctx, "input")
        out_expr = emit_c_value(out_value, ctx)
        input_expr = emit_c_value(input_value, ctx)
        k_expr, s_expr, d_expr, p_left_expr, p_right_expr = _emit_symbol_operands(
            tuple(symbol_values),
            ctx,
            emit_c_value,
            helper_name,
        )
        return (
            f"{ctx.current_indent}S_INT {result_name} = "
            f"cost::img2col1d<{ctx.dispatch_attr(input_type)}, {ctx.dispatch_attr(out_type)}, "
            f"{ctx.dispatch_type(input_type.element_type)}, {ctx.dispatch_type(out_type.element_type)}, {helper_kind}>"
            f"({out_expr} /*out*/, {input_expr} /*input*/, {k_expr} /*k*/, {s_expr} /*s*/, {d_expr} /*d*/, "
            f"{p_left_expr} /*p_left*/, {p_right_expr} /*p_right*/);"
        )
    if helper_name == "kernel.img2col2d":
        if len(operands) != 12:
            raise ctx.emit_error(
                "tuner.cost",
                f"op_name={helper_name} requires out, input, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr",
            )
        out_value, input_value, *symbol_values = operands
        out_type = _require_tuner_cost_memory_type(out_value, ctx, "out")
        input_type = _require_tuner_cost_memory_type(input_value, ctx, "input")
        out_expr = emit_c_value(out_value, ctx)
        input_expr = emit_c_value(input_value, ctx)
        (
            kh_expr,
            kw_expr,
            sh_expr,
            sw_expr,
            dh_expr,
            dw_expr,
            ph_expr,
            pw_expr,
            pl_expr,
            pr_expr,
        ) = _emit_symbol_operands(tuple(symbol_values), ctx, emit_c_value, helper_name)
        return (
            f"{ctx.current_indent}S_INT {result_name} = "
            f"cost::img2col2d<{ctx.dispatch_attr(input_type)}, {ctx.dispatch_attr(out_type)}, "
            f"{ctx.dispatch_type(input_type.element_type)}, {ctx.dispatch_type(out_type.element_type)}, {helper_kind}>"
            f"({out_expr} /*out*/, {input_expr} /*input*/, {kh_expr} /*kh*/, {kw_expr} /*kw*/, "
            f"{sh_expr} /*sh*/, {sw_expr} /*sw*/, {dh_expr} /*dh*/, {dw_expr} /*dw*/, "
            f"{ph_expr} /*ph*/, {pw_expr} /*pw*/, {pl_expr} /*pl*/, {pr_expr} /*pr*/);"
        )
    raise ctx.emit_error("tuner.cost", f"unsupported op_name={helper_name}")
