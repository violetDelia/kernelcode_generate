"""npu_demo `dma.*_ring` EmitC 注册实现。

功能说明:
- 注册 target=`npu_demo` 的 `dma.make_ring`、`dma.current_ring` 与 `dma.advance_ring` EmitC 发射实现。
- npu_demo 当前执行模型为顺序 tile 计算，ring slot 通过 backing memory 的 typed view 表达，`advance` 保持可编译的 serial no-op slot 视图。
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

from kernel_gen.dialect.dma import DmaAdvanceRingOp, DmaCurrentRingOp, DmaMakeRingOp
from kernel_gen.dialect.nn import NnMemoryType

from ...register import emit_c_impl


@emit_c_impl(DmaMakeRingOp, target="npu_demo")
def _emit_npu_demo_dma_make_ring(op: DmaMakeRingOp, ctx) -> str:
    """发射 npu_demo `dma.make_ring` C++ 语句。

    功能说明:
    - `dma.make_ring` 仅描述 backing memory 与 stage 参数，npu_demo 串行后端无需额外 runtime 对象。
    - backing memory 由后续 `dma.current_ring` / `dma.advance_ring` 发射为 typed slot view。

    使用示例:
    - stmt = _emit_npu_demo_dma_make_ring(op, ctx)
    """

    return ""


@emit_c_impl(DmaCurrentRingOp, target="npu_demo")
def _emit_npu_demo_dma_current_ring(op: DmaCurrentRingOp, ctx) -> str:
    """发射 npu_demo `dma.current_ring` C++ 语句。

    功能说明:
    - 将 ring 当前 slot 映射为 backing memory 的 typed view。
    - 不新增 include/runtime 公开 helper。

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
    backing_expr = emit_c_value(make_ring.memory, ctx)
    result_name = ctx.create_or_get_name(op.result)
    result_cpp_type = ctx.dispatch_type(result_type)
    template_name = result_type.template_name.data
    element_type = template_name if template_name else ctx.dispatch_type(result_type.element_type)
    view_accessor = "view"
    if isinstance(make_ring.memory.type, NnMemoryType) and make_ring.memory.type.template_name.data:
        view_accessor = "template view"
    rank = len(result_type.shape.data)
    shape_values: list[str] = []
    for dim in result_type.shape.data:
        dim.verify()
        dim_expr = dim.expr.data
        if dim_expr == "?":
            raise ctx.emit_error(op.name, "ring slot shape must be static or symbolic")
        shape_values.append(dim_expr)
    shape_expr = "{" + ", ".join(shape_values) + "}"
    flat_size_value = " * ".join(f"({value})" for value in shape_values) if shape_values else "1"
    if rank == 1:
        return (
            f"{ctx.current_indent}{result_cpp_type} {result_name} = "
            f"{backing_expr}.{view_accessor}<{element_type}>"
            f"({{0}} /*offset*/, {{{flat_size_value}}} /*size*/, {{1}} /*stride*/);"
        )
    flat_name = ctx.allocate_name("ring_slot_")
    flat_view = (
        f"{ctx.current_indent}{result_cpp_type} {flat_name} = "
        f"{backing_expr}.{view_accessor}<{element_type}>"
        f"({{0}} /*offset*/, {{{flat_size_value}}} /*size*/, {{1}} /*stride*/);"
    )
    reshape = f"{ctx.current_indent}{result_cpp_type} {result_name} = {flat_name}.reshape({shape_expr} /*shape*/);"
    return f"{flat_view}\n{reshape}"


@emit_c_impl(DmaAdvanceRingOp, target="npu_demo")
def _emit_npu_demo_dma_advance_ring(op: DmaAdvanceRingOp, ctx) -> str:
    """发射 npu_demo `dma.advance_ring` C++ 语句。

    功能说明:
    - 当前 npu_demo 串行执行中保留可用 slot view，避免引入未确认的 runtime ring helper。
    - 若后续公开 runtime ring API，再由计划统一收口真实轮转。

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
    backing_expr = emit_c_value(make_ring.memory, ctx)
    result_name = ctx.create_or_get_name(op.result)
    result_cpp_type = ctx.dispatch_type(result_type)
    template_name = result_type.template_name.data
    element_type = template_name if template_name else ctx.dispatch_type(result_type.element_type)
    view_accessor = "view"
    if isinstance(make_ring.memory.type, NnMemoryType) and make_ring.memory.type.template_name.data:
        view_accessor = "template view"
    rank = len(result_type.shape.data)
    shape_values: list[str] = []
    for dim in result_type.shape.data:
        dim.verify()
        dim_expr = dim.expr.data
        if dim_expr == "?":
            raise ctx.emit_error(op.name, "ring slot shape must be static or symbolic")
        shape_values.append(dim_expr)
    shape_expr = "{" + ", ".join(shape_values) + "}"
    flat_size_value = " * ".join(f"({value})" for value in shape_values) if shape_values else "1"
    if rank == 1:
        return (
            f"{ctx.current_indent}{result_cpp_type} {result_name} = "
            f"{backing_expr}.{view_accessor}<{element_type}>"
            f"({{0}} /*offset*/, {{{flat_size_value}}} /*size*/, {{1}} /*stride*/);"
        )
    flat_name = ctx.allocate_name("ring_slot_")
    flat_view = (
        f"{ctx.current_indent}{result_cpp_type} {flat_name} = "
        f"{backing_expr}.{view_accessor}<{element_type}>"
        f"({{0}} /*offset*/, {{{flat_size_value}}} /*size*/, {{1}} /*stride*/);"
    )
    reshape = f"{ctx.current_indent}{result_cpp_type} {result_name} = {flat_name}.reshape({shape_expr} /*shape*/);"
    return f"{flat_view}\n{reshape}"
