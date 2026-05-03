"""CPU target emitter entry.


功能说明:
- 注册 CPU target 的 emit op / value / attr / name handler。
- 承载 CPU 侧片段源码生成与命名规则。

API 列表:
- 无（仅 target 私有注册实现）

使用示例:
- from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c_op
- stmt = emit_c_op(op, EmitCContext())

关联文件:
- spec: [spec/dsl/gen_kernel/emit.md](../../../../../spec/dsl/gen_kernel/emit.md)
- spec: [spec/dsl/gen_kernel/emit/register.md](../../../../../spec/dsl/gen_kernel/emit/register.md)
- test: [test/dsl/gen_kernel/emit/test_package.py](../../../../../test/dsl/gen_kernel/emit/test_package.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit/cpu/__init__.py](.)
"""

from __future__ import annotations

from typing import Any

from xdsl.dialects import arith, func, scf
from xdsl.dialects.builtin import (
    BFloat16Type,
    Float16Type,
    Float32Type,
    Float64Type,
    FloatAttr,
    IndexType,
    IntAttr,
    IntegerAttr,
    IntegerType,
    Signedness,
    StringAttr,
)
from xdsl.ir import BlockArgument, Operation, SSAValue

from kernel_gen.dialect.dma import (
    DmaAllocOp,
    DmaBroadcastOp,
    DmaDesliceOp,
    DmaFillOp,
    DmaLoadOp,
    DmaSliceOp,
    DmaStoreOp,
    DmaViewOp,
)
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp
from kernel_gen.dialect.nn import NnAddOp, NnImg2col2dOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import (
    SymbolCastOp,
    SymbolConstOp,
    SymbolForOp,
    SymbolGetDimOp,
    SymbolGetStrideOp,
    SymbolToFloatOp,
    SymbolToIntOp,
    SymbolValueType,
)

from ...emit_context import EmitCContext
from ..register import emit_c_attr_impl, emit_c_impl, emit_c_name_impl, emit_c_type_impl, emit_c_value_impl

_BINARY_SIGILS = {
    "arith.addi": "+",
    "arith.addf": "+",
    "arith.subi": "-",
    "arith.subf": "-",
    "arith.muli": "*",
    "arith.mulf": "*",
    "arith.divf": "/",
    "symbol.add": "+",
    "symbol.sub": "-",
    "symbol.mul": "*",
    "symbol.div": "/",
    "symbol.floordiv": "/",
}
_SYMBOL_COMPARE_SIGILS = {
    "symbol.eq": "==",
    "symbol.ne": "!=",
    "symbol.lt": "<",
    "symbol.le": "<=",
    "symbol.gt": ">",
    "symbol.ge": ">=",
}
_CMPI_SIGILS = {0: "==", 1: "!=", 2: "<", 3: "<=", 4: ">", 5: ">="}
_SPACE_NAME_MAP = {
    "global": "GM",
    "shared": "SM",
    "local": "LM",
    "tsm": "TSM",
    "tlm1": "TLM1",
    "tlm2": "TLM2",
    "tlm3": "TLM3",
}


def _block_arg_index(value: SSAValue | BlockArgument) -> int | None:
    if isinstance(value, BlockArgument):
        return value.index
    return None


def _normalize_binary_elewise_operands(op: KernelBinaryElewiseOp) -> tuple[SSAValue, SSAValue, SSAValue]:
    out_value = SSAValue.get(op.out)
    lhs_value = SSAValue.get(op.lhs)
    rhs_value = SSAValue.get(op.rhs)
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


def _cpu_space_name(space_name: str) -> str:
    mapped = _SPACE_NAME_MAP.get(space_name)
    if mapped is None:
        raise ValueError(f"unsupported memory space: {space_name}")
    return mapped


@emit_c_type_impl(IntegerType, target="cpu")
def _emit_cpu_integer_type(attr: IntegerType, _ctx) -> str:
    """发射 CPU 整数类型文本。


    功能说明:
    - 将 xDSL 整数类型映射为 CPU C/C++ 标量类型文本。

    使用示例:
    - c_type = ctx.dispatch_type(i32)
    """

    if attr.width.data == 1:
        return "bool"
    prefix = "uint" if attr.signedness.data == Signedness.UNSIGNED else "int"
    return f"{prefix}{attr.width.data}_t"


@emit_c_type_impl(Float16Type, target="cpu")
def _emit_cpu_float16_type(_attr: Float16Type, _ctx) -> str:
    """发射 CPU half 类型文本。


    功能说明:
    - 将 xDSL f16 类型映射为 CPU C/C++ half 类型文本。

    使用示例:
    - c_type = ctx.dispatch_type(Float16Type())
    """

    return "half"


@emit_c_type_impl(BFloat16Type, target="cpu")
def _emit_cpu_bfloat16_type(_attr: BFloat16Type, _ctx) -> str:
    """发射 CPU bfloat16 类型文本。


    功能说明:
    - 将 xDSL bf16 类型映射为 CPU C/C++ bfloat16 类型文本。

    使用示例:
    - c_type = ctx.dispatch_type(BFloat16Type())
    """

    return "bfloat16_t"


@emit_c_type_impl(Float32Type, target="cpu")
def _emit_cpu_float32_type(_attr: Float32Type, _ctx) -> str:
    """发射 CPU float 类型文本。


    功能说明:
    - 将 xDSL f32 类型映射为 CPU C/C++ float 类型文本。

    使用示例:
    - c_type = ctx.dispatch_type(f32)
    """

    return "float"


@emit_c_type_impl(Float64Type, target="cpu")
def _emit_cpu_float64_type(_attr: Float64Type, _ctx) -> str:
    """发射 CPU double 类型文本。


    功能说明:
    - 将 xDSL f64 类型映射为 CPU C/C++ double 类型文本。

    使用示例:
    - c_type = ctx.dispatch_type(f64)
    """

    return "double"


@emit_c_type_impl(IndexType, target="cpu")
def _emit_cpu_index_type(_attr: IndexType, _ctx) -> str:
    """发射 CPU index 类型文本。


    功能说明:
    - 将 xDSL index 类型映射为 CPU C/C++ long long 类型文本。

    使用示例:
    - c_type = ctx.dispatch_type(IndexType())
    """

    return "long long"


@emit_c_type_impl(NnMemoryType, target="cpu")
def _emit_cpu_memory_type(attr: NnMemoryType, ctx) -> str:
    """发射 CPU nn.memory 类型文本。


    功能说明:
    - 将 `nn.memory` 映射为 CPU `Memory<MemorySpace::..., element>` 类型文本。

    使用示例:
    - c_type = ctx.dispatch_type(memory_type)
    """

    space_param = ctx.dispatch_attr(attr)
    if space_param is None:
        raise ValueError(f"unsupported cpu memory type space: {attr.space.space.data}")
    return f"Memory<MemorySpace::{space_param}, {ctx.dispatch_type(attr.element_type)}>"


@emit_c_type_impl(SymbolValueType, target="cpu")
def _emit_cpu_symbol_value_type(_attr: SymbolValueType, _ctx) -> str:
    """发射 CPU symbol 标量类型文本。


    功能说明:
    - 将 `!symbol.int` 映射为 CPU C/C++ long long 类型文本。

    使用示例:
    - c_type = ctx.dispatch_type(SymbolValueType.from_expr("N"))
    """

    return "long long"


@emit_c_attr_impl(str, target="cpu")
def _emit_cpu_space_name(space_name: str, _ctx) -> str:
    return _cpu_space_name(space_name)


@emit_c_attr_impl(NnMemorySpaceAttr, target="cpu")
def _emit_cpu_memory_space(space_attr: NnMemorySpaceAttr, _ctx) -> str:
    return _cpu_space_name(space_attr.space.data)


@emit_c_attr_impl(NnMemoryType, target="cpu")
def _emit_cpu_space(memory_type: NnMemoryType, _ctx) -> str:
    return _cpu_space_name(memory_type.space.space.data)


@emit_c_name_impl(BlockArgument, target="cpu")
def _emit_cpu_block_arg_name(value: SSAValue, ctx) -> str:
    parent_op = value.owner.parent_op()
    if value.index == 0 and isinstance(parent_op, (scf.ForOp, SymbolForOp)):
        return ctx.allocate_name("i")
    return f"arg{value.index}"


@emit_c_name_impl(SymbolConstOp, target="cpu")
def _emit_cpu_symbol_const_name(value: SSAValue, _ctx) -> str:
    owner = value.owner
    if not isinstance(owner, SymbolConstOp):
        raise ValueError("symbol.const name handler only supports SymbolConstOp")
    return f"c_{owner.value.data}".replace("-", "neg_")


def _format_literal(op: arith.ConstantOp, ctx: EmitCContext) -> str:
    value = op.value
    if isinstance(value, IntegerAttr):
        return str(value.value.data)
    if isinstance(value, FloatAttr):
        return str(value.value.data)
    raise ctx.emit_error(op.name, "unsupported constant literal")


def _format_indices(indices: tuple[SSAValue, ...], ctx: EmitCContext) -> str:
    return "".join(f"[{_emit_c_value(index, ctx)}]" for index in indices)


def _format_static_layout(values: Any, ctx: EmitCContext, subject: str) -> list[str]:
    formatted: list[str] = []
    for value in values:
        if not isinstance(value, IntAttr):
            raise ctx.emit_error(subject, "only static memory layout is supported")
        formatted.append(str(value.data))
    return formatted


def _emit_long_long_buffer(name: str, values: list[str], ctx: EmitCContext) -> str:
    return f"{ctx.current_indent}long long {name}[{len(values)}] = {{{', '.join(values)}}};"


def _maybe_static_numel(shape: Any) -> int | None:
    numel = 1
    for dim in shape:
        if not isinstance(dim, IntAttr):
            return None
        numel *= dim.data
    return numel


def _shape_product_expr(shape_values: list[str]) -> str:
    if not shape_values:
        return "1"
    return " * ".join(f"({value})" for value in shape_values)


def _emit_backing_storage_decl(
    name: str,
    element_type: str,
    shape_values: list[str],
    memory_type: NnMemoryType,
    ctx: EmitCContext,
) -> tuple[list[str], str]:
    buffer_name = f"{name}_buffer"
    static_numel = _maybe_static_numel(memory_type.shape.data)
    if static_numel is None:
        raise ctx.emit_error(f"memory {name}", "dynamic shape backing is unsupported")
    return [f"{ctx.current_indent}{element_type} {buffer_name}[{static_numel}] = {{}};"], buffer_name


def _emit_memory_decl(
    name: str,
    memory_type: NnMemoryType,
    ctx: EmitCContext,
    *,
    shape_values: list[str] | None = None,
    stride_values: list[str] | None = None,
    data_expr: str | None = None,
    format_expr: str | None = None,
    space_expr: str | None = None,
    with_backing_storage: bool = False,
) -> str:
    if not (ctx.is_target("cpu") or ctx.is_target("npu_demo")):
        raise ctx.emit_error(f"memory {name}", "unsupported target")
    element_type = ctx.dispatch_type(memory_type.element_type)
    if shape_values is None:
        shape_values = _format_static_layout(memory_type.shape.data, ctx, f"memory {name}")
    if stride_values is None:
        stride_values = _format_static_layout(memory_type.stride.data, ctx, f"memory {name}")
    if with_backing_storage:
        storage_lines, data_expr = _emit_backing_storage_decl(name, element_type, shape_values, memory_type, ctx)
    else:
        storage_lines = []
    if data_expr is None:
        data_expr = f"static_cast<{element_type}*>(nullptr)"
    if format_expr is None:
        format_expr = "MemoryFormat::Norm"
    if space_expr is None:
        space_expr = ctx.dispatch_attr(memory_type)
    if ctx.is_target("npu_demo"):
        ctor_args = f"{data_expr}, {name}_shape, {name}_stride, {len(shape_values)}, {format_expr}"
    else:
        ctor_args = f"{data_expr}, {len(shape_values)}, {name}_shape, {name}_stride, {format_expr}"
    lines = [
        _emit_long_long_buffer(f"{name}_shape", shape_values, ctx),
        _emit_long_long_buffer(f"{name}_stride", stride_values, ctx),
        *storage_lines,
        f"{ctx.current_indent}Memory<{space_expr}, {element_type}> {name}({ctor_args});",
    ]
    return "\n".join(lines)


def _is_unit_tile(memory_type: NnMemoryType) -> bool:
    if len(memory_type.shape.data) == 0:
        return False
    return all(isinstance(dim, IntAttr) and dim.data == 1 for dim in memory_type.shape.data)


def _emit_dma_copy_loop_nest(
    *,
    source_expr: str,
    target_expr: str,
    offsets: tuple[SSAValue, ...],
    sizes: tuple[SSAValue, ...],
    strides: tuple[SSAValue, ...],
    ctx: EmitCContext,
    target_has_offsets: bool,
) -> str:
    if not ctx.is_target("cpu"):
        raise ctx.emit_error("dma.copy", "dma ops are cpu-only")
    base_name = ctx.allocate_name("dma")
    source_indices_name = f"{base_name}_src_indices"
    target_indices_name = f"{base_name}_dst_indices"
    rank = len(sizes)
    lines = [
        _emit_long_long_buffer(source_indices_name, ["0"] * rank, ctx),
        _emit_long_long_buffer(target_indices_name, ["0"] * rank, ctx),
    ]
    loop_names: list[str] = []
    for index, size in enumerate(sizes):
        loop_name = f"{base_name}_i{index}"
        lines.append(
            f"{ctx.current_indent}for (long long {loop_name} = 0; {loop_name} < {_emit_c_value(size, ctx)}; ++{loop_name}) {{"
        )
        ctx.push_indent()
        loop_names.append(loop_name)
    for index, loop_name in enumerate(loop_names):
        offset_expr = _emit_c_value(offsets[index], ctx)
        stride_expr = _emit_c_value(strides[index], ctx)
        if target_has_offsets:
            lines.append(f"{ctx.current_indent}{source_indices_name}[{index}] = {loop_name};")
            lines.append(
                f"{ctx.current_indent}{target_indices_name}[{index}] = {offset_expr} + ({loop_name} * {stride_expr});"
            )
        else:
            lines.append(
                f"{ctx.current_indent}{source_indices_name}[{index}] = {offset_expr} + ({loop_name} * {stride_expr});"
            )
            lines.append(f"{ctx.current_indent}{target_indices_name}[{index}] = {loop_name};")
    lines.append(
        f"{ctx.current_indent}{target_expr}.at({target_indices_name}) = {source_expr}.at({source_indices_name});"
    )
    for _ in reversed(loop_names):
        ctx.pop_indent()
        lines.append(f"{ctx.current_indent}}}")
    return "\n".join(lines)


def _emit_dma_load_stmt(op: DmaLoadOp, ctx: EmitCContext) -> str:
    if not ctx.is_target("cpu"):
        raise ctx.emit_error(op.name, "dma ops are cpu-only")
    if not isinstance(op.source.type, NnMemoryType):
        raise ctx.emit_error(op.name, "source must be nn.memory")
    if not isinstance(op.target.type, NnMemoryType):
        raise ctx.emit_error(op.name, "target must be nn.memory")
    return _emit_dma_copy_loop_nest(
        source_expr=_emit_c_value(op.source, ctx),
        target_expr=_emit_c_value(op.target, ctx),
        offsets=op.offsets,
        sizes=op.sizes,
        strides=op.strides,
        ctx=ctx,
        target_has_offsets=False,
    )


def _emit_dma_store_stmt(op: DmaStoreOp, ctx: EmitCContext) -> str:
    if not ctx.is_target("cpu"):
        raise ctx.emit_error(op.name, "dma ops are cpu-only")
    source_type = op.source.type
    if not isinstance(source_type, NnMemoryType) or not _is_unit_tile(source_type):
        raise ctx.emit_error(op.name, "only unit-tile dma.store source is supported")
    return (
        f"{ctx.current_indent}{_emit_c_value(op.target, ctx)}{_format_indices(op.offsets, ctx)} = "
        f"{_emit_c_value(op.source, ctx)};"
    )


def _emit_dma_alloc_stmt(op: DmaAllocOp, ctx: EmitCContext) -> str:
    if not ctx.is_target("cpu"):
        raise ctx.emit_error(op.name, "dma ops are cpu-only")
    result_name = ctx.create_or_get_name(op.result)
    result_type = op.result.type
    if not isinstance(result_type, NnMemoryType):
        raise ctx.emit_error(op.name, "result must be nn.memory")
    shape_values = [_emit_c_value(value, ctx) for value in op.dynamic_shape]
    if not shape_values:
        shape_values = _format_static_layout(result_type.shape.data, ctx, op.name)
    stride_values = _format_static_layout(result_type.stride.data, ctx, f"{op.name} stride")
    return _emit_memory_decl(
        result_name,
        result_type,
        ctx,
        shape_values=shape_values,
        stride_values=stride_values,
        with_backing_storage=True,
    )


def _emit_dma_fill_stmt(op: DmaFillOp, ctx: EmitCContext) -> str:
    if not ctx.is_target("cpu"):
        raise ctx.emit_error(op.name, "dma ops are cpu-only")
    target_expr = _emit_c_value(op.target, ctx)
    value_expr = _emit_c_value(op.value, ctx)
    loop_name = f"{ctx.allocate_name('fill')}_i"
    lines = [f"{ctx.current_indent}for (long long {loop_name} = 0; {loop_name} < {target_expr}.element_count(); ++{loop_name}) {{"]
    ctx.push_indent()
    lines.append(f"{ctx.current_indent}{target_expr}.data()[{loop_name}] = {value_expr};")
    ctx.pop_indent()
    lines.append(f"{ctx.current_indent}}}")
    return "\n".join(lines)


def _emit_dma_view_stmt(op: DmaViewOp, ctx: EmitCContext) -> str:
    if not ctx.is_target("cpu"):
        raise ctx.emit_error(op.name, "dma ops are cpu-only")
    source_expr = _emit_c_value(op.source, ctx)
    result_name = ctx.create_or_get_name(op.result)
    result_type = op.result.type
    if not isinstance(result_type, NnMemoryType):
        raise ctx.emit_error(op.name, "result must be nn.memory")
    shape_values = [_emit_c_value(value, ctx) for value in op.shape]
    stride_values = [_emit_c_value(value, ctx) for value in op.stride]
    base_offset_name = ctx.allocate_name("view_offset")
    offset_terms = [f"({_emit_c_value(value, ctx)} * {source_expr}.stride()[{index}])" for index, value in enumerate(op.offsets)]
    base_offset_expr = " + ".join(offset_terms) if offset_terms else "0"
    decl = _emit_memory_decl(
        result_name,
        result_type,
        ctx,
        shape_values=shape_values,
        stride_values=stride_values,
        data_expr=f"const_cast<{ctx.dispatch_type(result_type.element_type)}*>({source_expr}.data()) + {base_offset_name}",
        format_expr=f"{source_expr}.format()",
    )
    return f"{ctx.current_indent}long long {base_offset_name} = {base_offset_expr};\n{decl}"


def _emit_dma_slice_stmt(op: DmaSliceOp, ctx: EmitCContext) -> str:
    if not ctx.is_target("cpu"):
        raise ctx.emit_error(op.name, "dma ops are cpu-only")
    return _emit_dma_copy_loop_nest(
        source_expr=_emit_c_value(op.source, ctx),
        target_expr=_emit_c_value(op.target, ctx),
        offsets=op.offsets,
        sizes=op.sizes,
        strides=op.strides,
        ctx=ctx,
        target_has_offsets=False,
    )


def _emit_dma_deslice_stmt(op: DmaDesliceOp, ctx: EmitCContext) -> str:
    if not ctx.is_target("cpu"):
        raise ctx.emit_error(op.name, "dma ops are cpu-only")
    source_expr = _emit_c_value(op.source, ctx)
    target_expr = _emit_c_value(op.target, ctx)
    ctx.bind_name(op.result, target_expr)
    return _emit_dma_copy_loop_nest(
        source_expr=source_expr,
        target_expr=target_expr,
        offsets=op.offsets,
        sizes=op.sizes,
        strides=op.strides,
        ctx=ctx,
        target_has_offsets=True,
    )


def _emit_img2col2d_stmt(op: NnImg2col2dOp, ctx: EmitCContext) -> str:
    if not ctx.is_target("cpu"):
        raise ctx.emit_error(op.name, "nn ops are cpu-only")
    input_expr = _emit_c_value(op.input, ctx)
    result_expr = ctx.create_or_get_name(op.result)
    result_type = op.result.type
    if not isinstance(result_type, NnMemoryType):
        raise ctx.emit_error(op.name, "result must be nn.memory")
    decl = _emit_memory_decl(result_expr, result_type, ctx, with_backing_storage=True)
    param_values = [
        _emit_c_value(op.kh, ctx),
        _emit_c_value(op.kw, ctx),
        _emit_c_value(op.sh, ctx),
        _emit_c_value(op.sw, ctx),
        _emit_c_value(op.dh, ctx),
        _emit_c_value(op.dw, ctx),
        _emit_c_value(op.ph, ctx),
        _emit_c_value(op.pw, ctx),
        _emit_c_value(op.pl, ctx),
        _emit_c_value(op.pr, ctx),
    ]
    return f"{decl}\n{ctx.current_indent}cpu::img2col2d({', '.join([input_expr, result_expr, *param_values])});"


def _emit_nn_add_stmt(op: NnAddOp, ctx: EmitCContext) -> str:
    if not ctx.is_target("cpu"):
        raise ctx.emit_error(op.name, "unsupported op")
    result_name = ctx.lookup_name(op.result)
    if result_name is None or not isinstance(op.result.type, NnMemoryType):
        raise ctx.emit_error(op.name, "unsupported op")
    lhs_is_memory = isinstance(op.lhs.type, NnMemoryType)
    rhs_is_memory = isinstance(op.rhs.type, NnMemoryType)
    if lhs_is_memory and rhs_is_memory:
        return (
            f"{ctx.current_indent}cpu::add({_emit_c_value(op.lhs, ctx)}, {_emit_c_value(op.rhs, ctx)}, {result_name});"
        )
    if not lhs_is_memory or rhs_is_memory:
        raise ctx.emit_error(op.name, "unsupported op")
    scalar_type = op.rhs.type
    is_i32_scalar = isinstance(scalar_type, IntegerType) and scalar_type.width.data == 32
    if not (is_i32_scalar or isinstance(scalar_type, SymbolValueType)):
        raise ctx.emit_error(op.name, "unsupported op")
    return f"{ctx.current_indent}cpu::add({_emit_c_value(op.lhs, ctx)}, {_emit_c_value(op.rhs, ctx)}, {result_name});"


def _emit_kernel_binary_elewise_stmt(op: KernelBinaryElewiseOp, ctx: EmitCContext) -> str:
    out_value, lhs_value, rhs_value = _normalize_binary_elewise_operands(op)
    helper_map = {
        "add": "add",
        "sub": "sub",
        "mul": "mul",
        "div": "div",
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
    return (
        f"{ctx.current_indent}cpu::{helper_name}({_emit_c_value(lhs_value, ctx)}, "
        f"{_emit_c_value(rhs_value, ctx)}, {_emit_c_value(out_value, ctx)});"
    )


def _emit_dma_broadcast_stmt(op: DmaBroadcastOp, ctx: EmitCContext) -> str:
    if not ctx.is_target("cpu"):
        raise ctx.emit_error(op.name, "unsupported op")
    if not isinstance(op.target.type, NnMemoryType) or not isinstance(op.source.type, NnMemoryType):
        raise ctx.emit_error(op.name, "unsupported op")
    return (
        f"{ctx.current_indent}cpu::broadcast({_emit_c_value(op.source, ctx)}, {_emit_c_value(op.target, ctx)});"
    )


def _emit_assignment(op: Operation, ctx: EmitCContext) -> str:
    result = op.results[0]
    expr = _emit_c_value(result, ctx)
    result_name = ctx.create_or_get_name(result)
    return f"{ctx.current_indent}{ctx.dispatch_type(result.type)} {result_name} = {expr};"


def _emit_loop_region(
    lower: SSAValue,
    upper: SSAValue,
    step: SSAValue,
    block: Any,
    ctx: EmitCContext,
    iv_type: str = "long long",
) -> str:
    iv_name = ctx.create_or_get_name(block.args[0])
    lines = [
        f"{ctx.current_indent}for ({iv_type} {iv_name} = {_emit_c_value(lower, ctx)}; {iv_name} < {_emit_c_value(upper, ctx)}; {iv_name} += {_emit_c_value(step, ctx)}) {{"
    ]
    ctx.push_indent()
    for body_op in block.ops:
        if isinstance(body_op, scf.YieldOp):
            continue
        stmt = _emit_c_op(body_op, ctx)
        if stmt:
            lines.append(stmt)
    ctx.pop_indent()
    lines.append(f"{ctx.current_indent}}}")
    return "\n".join(lines)


def _emit_loop(op: scf.ForOp, ctx: EmitCContext) -> str:
    return _emit_loop_region(op.lb, op.ub, op.step, op.body.block, ctx)


def _emit_symbol_loop(op: SymbolForOp, ctx: EmitCContext) -> str:
    return _emit_loop_region(op.start, op.end, op.step, op.body.block, ctx)


def _emit_symbol_const_stmt(op: Operation, ctx: EmitCContext) -> str:
    if isinstance(op, SymbolConstOp):
        value_text = str(op.value.data)
        result = op.result
    else:
        if not op.results or not isinstance(op.results[0].type, SymbolValueType):
            raise ctx.emit_error(op.name, "symbol.const result must be !symbol.int")
        value_text = op.results[0].type.expr.expr.data
        result = op.results[0]
    if all(isinstance(use.operation, DmaLoadOp) for use in result.uses):
        return ""
    name = ctx.create_or_get_name(result)
    return f"{ctx.current_indent}S_INT {name} = {value_text};"


@emit_c_value_impl(Operation, BlockArgument, target="cpu")
def _emit_c_value(value: SSAValue, ctx: EmitCContext) -> str:
    bound = ctx.lookup_name(value)
    if bound is not None:
        return bound
    if isinstance(value, BlockArgument):
        return ctx.create_or_get_name(value)
    owner = value.owner
    if isinstance(value.type, NnMemoryType) and isinstance(owner, (DmaAllocOp, DmaViewOp, DmaLoadOp, DmaSliceOp, NnImg2col2dOp)):
        return ctx.create_or_get_name(value)
    if isinstance(value.type, NnMemoryType):
        raise ctx.emit_error(owner.name, f"invalid dependency for value {value}")
    if isinstance(owner, arith.ConstantOp):
        return _format_literal(owner, ctx)
    op_name_attr = owner.attributes.get("op_name__") if isinstance(owner, Operation) else None
    if isinstance(owner, SymbolConstOp) or (
        isinstance(owner, Operation)
        and owner.name == "builtin.unregistered"
        and isinstance(op_name_attr, StringAttr)
        and op_name_attr.data == "symbol.const"
    ):
        if isinstance(owner, SymbolConstOp):
            return str(owner.value.data)
        if owner.results and isinstance(owner.results[0].type, SymbolValueType):
            return owner.results[0].type.expr.expr.data
        raise ctx.emit_error(owner.name, "symbol.const result must be !symbol.int")
    if owner.name in _BINARY_SIGILS:
        return f"({_emit_c_value(owner.operands[0], ctx)} {_BINARY_SIGILS[owner.name]} {_emit_c_value(owner.operands[1], ctx)})"
    if owner.name in _SYMBOL_COMPARE_SIGILS:
        return f"({_emit_c_value(owner.operands[0], ctx)} {_SYMBOL_COMPARE_SIGILS[owner.name]} {_emit_c_value(owner.operands[1], ctx)})"
    if isinstance(owner, arith.CmpiOp):
        predicate = owner.predicate.value.data
        if predicate not in _CMPI_SIGILS:
            raise ctx.emit_error(owner.name, "unsupported comparison predicate")
        return f"({_emit_c_value(owner.lhs, ctx)} {_CMPI_SIGILS[predicate]} {_emit_c_value(owner.rhs, ctx)})"
    if isinstance(owner, (SymbolToIntOp, SymbolCastOp, SymbolToFloatOp)):
        return _emit_c_value(owner.source, ctx)
    if isinstance(owner, SymbolGetDimOp):
        if not isinstance(owner.axis, IntAttr):
            raise ctx.emit_error(owner.name, "axis must be IntAttr")
        return f"{_emit_c_value(owner.source, ctx)}.shape()[{owner.axis.data}]"
    if isinstance(owner, SymbolGetStrideOp):
        if not isinstance(owner.axis, IntAttr):
            raise ctx.emit_error(owner.name, "axis must be IntAttr")
        return f"{_emit_c_value(owner.source, ctx)}.stride()[{owner.axis.data}]"
    raise ctx.emit_error(owner.name, f"invalid dependency for value {value}")


@emit_c_impl(Operation, target="cpu")
def _emit_c_op(op: Operation, ctx: EmitCContext) -> str:
    if op.name in _BINARY_SIGILS or op.name in _SYMBOL_COMPARE_SIGILS or isinstance(op, arith.CmpiOp):
        return _emit_assignment(op, ctx)
    if isinstance(op, arith.ConstantOp):
        return ""
    op_name_attr = op.attributes.get("op_name__") if isinstance(op, Operation) else None
    if isinstance(op, SymbolConstOp) or (
        isinstance(op, Operation)
        and op.name == "builtin.unregistered"
        and isinstance(op_name_attr, StringAttr)
        and op_name_attr.data == "symbol.const"
    ):
        return ""
    if isinstance(op, (SymbolToIntOp, SymbolCastOp, SymbolToFloatOp, SymbolGetDimOp, SymbolGetStrideOp)):
        return ""
    if isinstance(op, DmaAllocOp):
        return _emit_dma_alloc_stmt(op, ctx)
    if isinstance(op, DmaFillOp):
        return _emit_dma_fill_stmt(op, ctx)
    if isinstance(op, DmaLoadOp):
        return _emit_dma_load_stmt(op, ctx)
    if isinstance(op, DmaStoreOp):
        return _emit_dma_store_stmt(op, ctx)
    if isinstance(op, DmaSliceOp):
        return _emit_dma_slice_stmt(op, ctx)
    if isinstance(op, DmaDesliceOp):
        return _emit_dma_deslice_stmt(op, ctx)
    if isinstance(op, DmaViewOp):
        return _emit_dma_view_stmt(op, ctx)
    if isinstance(op, DmaBroadcastOp):
        return _emit_dma_broadcast_stmt(op, ctx)
    if isinstance(op, KernelBinaryElewiseOp):
        return _emit_kernel_binary_elewise_stmt(op, ctx)
    if isinstance(op, NnAddOp):
        return _emit_nn_add_stmt(op, ctx)
    if isinstance(op, scf.ForOp):
        return _emit_loop(op, ctx)
    if isinstance(op, SymbolForOp):
        return _emit_symbol_loop(op, ctx)
    if isinstance(op, NnImg2col2dOp):
        return _emit_img2col2d_stmt(op, ctx)
    if isinstance(op, func.ReturnOp):
        if not op.arguments:
            return ""
        if len(op.arguments) != 1:
            raise ctx.emit_error(op.name, "unsupported return arity")
        return f"{ctx.current_indent}return {_emit_c_value(op.arguments[0], ctx)};"
    raise ctx.emit_error(op.name, "unsupported op")


__all__: list[str] = []
