"""npu_demo `dma.*_ring` EmitC 注册实现。

功能说明:
- 注册 target=`npu_demo` 的 `dma.make_ring`、`dma.current_ring` 与 `dma.advance_ring` EmitC 发射实现。
- `dma.make_ring` 发射 runtime `npu_demo::make_ring<SlotT>(...)` 对象，`current/advance` 发射成员调用。
- 本文件不提供跨文件公开 API；调用方必须通过 emit registry 与 `emit_c_op(...)` 公开入口调度。

API 列表:
- 无公开 API。

使用示例:
- source = emit_c_op(op, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md
- test: test/kernel/test_matmul_symbolic_memory_genkernel.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py
"""

from __future__ import annotations

from kernel_gen.dialect.dma import DmaAdvanceRingOp, DmaCurrentRingOp, DmaMakeRingOp, DmaRingType
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr

from ...register import emit_c_impl


@emit_c_impl(DmaMakeRingOp, target="npu_demo")
def _emit_npu_demo_dma_make_ring(op: DmaMakeRingOp, ctx) -> str:
    """发射 npu_demo `dma.make_ring` C++ 语句。

    功能说明:
    - 根据 result ring slot type 发射 `npu_demo::make_ring<SlotT>(backing, num, offset_bytes, shape, stride)`。
    - slot 字节数不作为 IR operand 或 generated source 参数出现。

    使用示例:
    - stmt = _emit_npu_demo_dma_make_ring(op, ctx)
    """

    from ... import emit_c_value

    result_type = op.result.type
    if not isinstance(result_type, DmaRingType):
        raise ctx.emit_error(op.name, "result must be dma.ring")
    slot_type = result_type.memory_type
    if not isinstance(slot_type, NnMemoryType):
        raise ctx.emit_error(op.name, "ring slot result must be nn.memory")
    slot_type.verify()
    shape_values: list[str] = []
    stride_values: list[str] = []
    for dim in slot_type.shape.data:
        if not isinstance(dim, SymbolExprAttr):
            raise ctx.emit_error(op.name, "ring slot shape must be symbolic expression")
        dim.verify()
        dim_expr = dim.expr.data
        if dim_expr == "?":
            raise ctx.emit_error(op.name, "ring slot shape must be static or symbolic")
        shape_values.append(dim_expr)
    for dim in slot_type.stride.data:
        if not isinstance(dim, SymbolExprAttr):
            raise ctx.emit_error(op.name, "ring slot stride must be symbolic expression")
        dim.verify()
        dim_expr = dim.expr.data
        if dim_expr == "?":
            raise ctx.emit_error(op.name, "ring slot stride must be static or symbolic")
        stride_values.append(dim_expr)
    result_name = ctx.create_or_get_name(op.result)
    backing_expr = emit_c_value(op.memory, ctx)
    num_expr = emit_c_value(op.num, ctx)
    offset_expr = emit_c_value(op.offset, ctx)
    template_name = slot_type.template_name.data
    element_type = template_name if template_name else ctx.dispatch_type(slot_type.element_type)
    shape_expr = "{" + ", ".join(shape_values) + "}"
    stride_expr = "{" + ", ".join(stride_values) + "}"
    return (
        f"{ctx.current_indent}auto {result_name} = npu_demo::make_ring<{element_type}>"
        f"({backing_expr} /*backing*/, {num_expr} /*num*/, {offset_expr} /*offset_bytes*/, "
        f"{shape_expr} /*shape*/, {stride_expr} /*stride*/);"
    )


@emit_c_impl(DmaCurrentRingOp, target="npu_demo")
def _emit_npu_demo_dma_current_ring(op: DmaCurrentRingOp, ctx) -> str:
    """发射 npu_demo `dma.current_ring` C++ 语句。

    功能说明:
    - 发射 runtime ring 的 `.current()` 成员调用。

    使用示例:
    - stmt = _emit_npu_demo_dma_current_ring(op, ctx)
    """

    from ... import emit_c_value

    make_ring = op.ring.owner
    if not isinstance(make_ring, DmaMakeRingOp):
        raise ctx.emit_error(op.name, "ring source must be dma.make_ring")
    result_type = op.result.type
    if not isinstance(result_type, NnMemoryType):
        raise ctx.emit_error(op.name, "ring slot result must be nn.memory")
    result_type.verify()
    ring_expr = emit_c_value(op.ring, ctx)
    result_name = ctx.create_or_get_name(op.result)
    result_cpp_type = ctx.dispatch_type(result_type)
    return f"{ctx.current_indent}{result_cpp_type} {result_name} = {ring_expr}.current();"


@emit_c_impl(DmaAdvanceRingOp, target="npu_demo")
def _emit_npu_demo_dma_advance_ring(op: DmaAdvanceRingOp, ctx) -> str:
    """发射 npu_demo `dma.advance_ring` C++ 语句。

    功能说明:
    - 发射 runtime ring 的 `.advance()` 成员调用。
    - 当 result 没有 SSA use 时仍发射调用语句，保留 cursor side effect。

    使用示例:
    - stmt = _emit_npu_demo_dma_advance_ring(op, ctx)
    """

    from ... import emit_c_value

    make_ring = op.ring.owner
    if not isinstance(make_ring, DmaMakeRingOp):
        raise ctx.emit_error(op.name, "ring source must be dma.make_ring")
    result_type = op.result.type
    if not isinstance(result_type, NnMemoryType):
        raise ctx.emit_error(op.name, "ring slot result must be nn.memory")
    result_type.verify()
    ring_expr = emit_c_value(op.ring, ctx)
    if not op.result.uses:
        return f"{ctx.current_indent}{ring_expr}.advance();"
    result_name = ctx.create_or_get_name(op.result)
    result_cpp_type = ctx.dispatch_type(result_type)
    return f"{ctx.current_indent}{result_cpp_type} {result_name} = {ring_expr}.advance();"
