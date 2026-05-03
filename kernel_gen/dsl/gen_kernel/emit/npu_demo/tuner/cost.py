"""npu_demo tuner cost emitters.


功能说明:
- 发射 `tuner.cost` 到 `npu_demo::cost::*` 公开 helper 调用。
- `dma.store` 写回成本复用公开 `cost::deslice` helper，不新增 cost namespace 公开接口。
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
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/cost.py
"""

from __future__ import annotations

from xdsl.dialects.builtin import IntegerAttr, StringAttr

from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.tuner import TunerCostOp

from ...register import emit_c_impl


@emit_c_impl(TunerCostOp, target="npu_demo")
def _emit_npu_demo_tuner_cost(op: TunerCostOp, ctx) -> str:
    """发射 npu_demo `tuner.cost`。


    功能说明:
    - 将受支持的 `op_name` 映射到公开 `npu_demo::cost::*` helper。
    - `op_name="dma.store"` 按写回方向发射为 `cost::deslice`，用于 DMA2 聚合合同。
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
        if not isinstance(out_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"out must be nn.memory")
        out_type = out_value.type
        if not isinstance(lhs_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"lhs must be nn.memory")
        lhs_type = lhs_value.type
        if not isinstance(rhs_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"rhs must be nn.memory")
        rhs_type = rhs_value.type
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
        if not isinstance(out_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"out must be nn.memory")
        out_type = out_value.type
        if not isinstance(lhs_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"lhs must be nn.memory")
        lhs_type = lhs_value.type
        if not isinstance(rhs_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"rhs must be nn.memory")
        rhs_type = rhs_value.type
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
        if not isinstance(out_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"out must be nn.memory")
        out_type = out_value.type
        if not isinstance(input_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"input must be nn.memory")
        input_type = input_value.type
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
        if not isinstance(out_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"out must be nn.memory")
        out_type = out_value.type
        if not isinstance(cond_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"cond must be nn.memory")
        cond_type = cond_value.type
        if not isinstance(lhs_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"lhs must be nn.memory")
        lhs_type = lhs_value.type
        if not isinstance(rhs_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"rhs must be nn.memory")
        rhs_type = rhs_value.type
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
        if not isinstance(out_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"out must be nn.memory")
        out_type = out_value.type
        if not isinstance(input_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"input must be nn.memory")
        input_type = input_value.type
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
        if not isinstance(target_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"target must be nn.memory")
        target_type = target_value.type
        if not isinstance(source_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"source must be nn.memory")
        source_type = source_value.type
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
    if helper_name in ("dma.slice", "dma.deslice", "dma.store"):
        if len(operands) < 2:
            raise ctx.emit_error("tuner.cost", f"op_name={helper_name} requires target, source, offsets, sizes, strides")
        if not isinstance(operands[0].type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", "target must be nn.memory")
        target_type = operands[0].type
        if not isinstance(operands[1].type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", "source must be nn.memory")
        source_type = operands[1].type
        rank = len(source_type.shape.data) if helper_name == "dma.slice" else len(target_type.shape.data)
        expected = 2 + 3 * rank
        if len(operands) != expected:
            raise ctx.emit_error("tuner.cost", f"op_name={helper_name} requires target, source, offsets, sizes, strides")
        target_value = operands[0]
        source_value = operands[1]
        offsets = operands[2 : 2 + rank]
        sizes = operands[2 + rank : 2 + 2 * rank]
        strides = operands[2 + 2 * rank : 2 + 3 * rank]
        target_dtype = ctx.dispatch_type(target_type.element_type)
        source_dtype = ctx.dispatch_type(source_type.element_type)
        if target_dtype != source_dtype:
            raise ctx.emit_error("tuner.cost", f"{helper_name} source/target element type must match")
        helper = "slice" if helper_name == "dma.slice" else "deslice"
        target_expr = emit_c_value(target_value, ctx)
        source_expr = emit_c_value(source_value, ctx)
        if not 1 <= len(offsets) <= 4 or not 1 <= len(sizes) <= 4 or not 1 <= len(strides) <= 4:
            raise ctx.emit_error("tuner.cost", f"op_name={helper_name} npu_demo Vector supports 1..4 values")
        offset_expr = "Vector{" + ", ".join(emit_c_value(value, ctx) for value in offsets) + "}"
        size_expr = "Vector{" + ", ".join(emit_c_value(value, ctx) for value in sizes) + "}"
        stride_expr = "Vector{" + ", ".join(emit_c_value(value, ctx) for value in strides) + "}"
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
        if not isinstance(out_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"out must be nn.memory")
        out_type = out_value.type
        if not isinstance(lhs_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"lhs must be nn.memory")
        lhs_type = lhs_value.type
        if not isinstance(rhs_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"rhs must be nn.memory")
        rhs_type = rhs_value.type
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
        if not isinstance(out_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"out must be nn.memory")
        out_type = out_value.type
        if not isinstance(input_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"input must be nn.memory")
        input_type = input_value.type
        out_expr = emit_c_value(out_value, ctx)
        input_expr = emit_c_value(input_value, ctx)
        k_expr, s_expr, d_expr, p_left_expr, p_right_expr = tuple(emit_c_value(value, ctx) for value in symbol_values)
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
        if not isinstance(out_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"out must be nn.memory")
        out_type = out_value.type
        if not isinstance(input_value.type, NnMemoryType):
            raise ctx.emit_error("tuner.cost", f"input must be nn.memory")
        input_type = input_value.type
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
        ) = tuple(emit_c_value(value, ctx) for value in symbol_values)
        return (
            f"{ctx.current_indent}S_INT {result_name} = "
            f"cost::img2col2d<{ctx.dispatch_attr(input_type)}, {ctx.dispatch_attr(out_type)}, "
            f"{ctx.dispatch_type(input_type.element_type)}, {ctx.dispatch_type(out_type.element_type)}, {helper_kind}>"
            f"({out_expr} /*out*/, {input_expr} /*input*/, {kh_expr} /*kh*/, {kw_expr} /*kw*/, "
            f"{sh_expr} /*sh*/, {sw_expr} /*sw*/, {dh_expr} /*dh*/, {dw_expr} /*dw*/, "
            f"{ph_expr} /*ph*/, {pw_expr} /*pw*/, {pl_expr} /*pl*/, {pr_expr} /*pr*/);"
        )
    raise ctx.emit_error("tuner.cost", f"unsupported op_name={helper_name}")
