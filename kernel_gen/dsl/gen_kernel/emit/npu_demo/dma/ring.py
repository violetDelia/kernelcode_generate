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

from collections.abc import Sequence

from xdsl.ir import SSAValue

from kernel_gen.dialect.dma import DmaAdvanceRingOp, DmaCurrentRingOp, DmaMakeRingOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr

from ...register import emit_c_impl


def _memory_element_cpp_type(memory_type: NnMemoryType, ctx) -> str:
    """返回当前文件发射 ring slot 所需的 C++ element type。

    功能说明:
    - 优先使用 `NnMemoryType.template_name` 作为模板 dtype。
    - 未携带 template name 时通过 `ctx.dispatch_type(...)` 发射真实 element type。

    使用示例:
    - element_type = _memory_element_cpp_type(memory_type, ctx)
    """

    memory_type.verify()
    template_name = memory_type.template_name.data
    if template_name:
        return template_name
    return ctx.dispatch_type(memory_type.element_type)


def _symbol_expr_text(attr: SymbolExprAttr, ctx, op_name: str) -> str:
    """返回可直接放入 npu_demo `Vector` 的 symbol 表达式文本。

    功能说明:
    - ring slot 发射只接受 `SymbolExprAttr` shape/stride 条目。
    - `?` 表示无法构造静态 slot view，按公开 emit 错误失败。

    使用示例:
    - dim_expr = _symbol_expr_text(dim_attr, ctx, "dma.current_ring")
    """

    attr.verify()
    expr_text = attr.expr.data
    if expr_text == "?":
        raise ctx.emit_error(op_name, "ring slot shape must be static or symbolic")
    return expr_text


def _vector_ctor_expr(values: Sequence[str]) -> str:
    """构造 npu_demo `Vector(...)` 表达式。

    功能说明:
    - 使用 `static_cast<long long>(...)` 避免整数列表触发 `Vector` 指针构造歧义。
    - 当前文件内用于 ring slot offset/shape/stride 发射，不作为公开 API。

    使用示例:
    - expr = _vector_ctor_expr(("0", "16"))
    """

    return "Vector(" + ", ".join(f"static_cast<long long>({value})" for value in values) + ")"


def _shape_vector_expr(values: Sequence[str], ctx) -> tuple[str, str]:
    """构造支持任意 rank 的 npu_demo `Vector` shape 表达式。

    功能说明:
    - rank 1..4 走公开 `Vector(...)` 构造。
    - rank >4 使用当前语句前的局部 `long long[]`，再走公开 `Vector(data, size)` 构造。

    使用示例:
    - prefix, expr = _shape_vector_expr(("m", "n"), ctx)
    """

    if len(values) <= 4:
        return "", _vector_ctor_expr(values)
    shape_buf_name = ctx.allocate_name("ring_shape_")
    prefix = f"{ctx.current_indent}long long {shape_buf_name}[{len(values)}] = {{{', '.join(values)}}};\n"
    return prefix, f"Vector({shape_buf_name}, {len(values)})"


def _num_elements_expr(shape_values: Sequence[str]) -> str:
    """构造 rank 形状对应的元素数量表达式。

    功能说明:
    - 将 ring slot 的 shape 条目相乘，用于从 1D byte backing 创建 typed flat view。
    - 只服务当前文件内 ring slot 发射，不作为公开 API。

    使用示例:
    - numel = _num_elements_expr(("72", "48"))
    """

    if not shape_values:
        return "1"
    return " * ".join(f"({value})" for value in shape_values)


def _ring_owner(value: SSAValue, ctx, op_name: str) -> DmaMakeRingOp:
    """返回 ring SSA value 的 `dma.make_ring` owner。

    功能说明:
    - npu_demo ring 发射只支持由本计划 `MultiBufferPass` 生成的 `dma.make_ring`。
    - 非 make_ring 来源不能安全还原 backing memory，按 emit 错误失败。

    使用示例:
    - make_ring = _ring_owner(op.ring, ctx, op.name)
    """

    owner = value.owner
    if not isinstance(owner, DmaMakeRingOp):
        raise ctx.emit_error(op_name, "ring source must be dma.make_ring")
    return owner


def _emit_ring_slot_view(op: DmaCurrentRingOp | DmaAdvanceRingOp, ctx) -> str:
    """发射 ring 当前 slot 的 typed view。

    功能说明:
    - 从 `dma.make_ring` backing memory 生成 offset=0 的 typed view。
    - 当前 npu_demo 后端顺序执行 tile 生命周期，slot 轮转对正确性不产生可见差异；因此 `dma.advance_ring` 也发射为同一 slot view。

    使用示例:
    - stmt = _emit_ring_slot_view(op, ctx)
    """

    from ... import emit_c_value

    make_ring = _ring_owner(op.ring, ctx, op.name)
    result_type = op.result.type
    if not isinstance(result_type, NnMemoryType):
        raise ctx.emit_error(op.name, "ring slot result must be nn.memory")
    backing_expr = emit_c_value(make_ring.memory, ctx)
    result_name = ctx.create_or_get_name(op.result)
    result_cpp_type = ctx.dispatch_type(result_type)
    element_type = _memory_element_cpp_type(result_type, ctx)
    view_accessor = "view"
    if isinstance(make_ring.memory.type, NnMemoryType) and make_ring.memory.type.template_name.data:
        view_accessor = "template view"
    rank = len(result_type.shape.data)
    shape_values = tuple(_symbol_expr_text(dim, ctx, op.name) for dim in result_type.shape.data)
    shape_prefix, shape_expr = _shape_vector_expr(
        shape_values, ctx
    )
    flat_offset_expr = _vector_ctor_expr(("0",))
    flat_size_expr = _vector_ctor_expr((_num_elements_expr(shape_values),))
    flat_stride_expr = _vector_ctor_expr(("1",))
    if rank == 1:
        return (
            f"{ctx.current_indent}{result_cpp_type} {result_name} = "
            f"{backing_expr}.{view_accessor}<{element_type}>"
            f"({flat_offset_expr} /*offset*/, {flat_size_expr} /*size*/, {flat_stride_expr} /*stride*/);"
        )
    flat_name = ctx.allocate_name("ring_slot_")
    flat_view = (
        f"{ctx.current_indent}{result_cpp_type} {flat_name} = "
        f"{backing_expr}.{view_accessor}<{element_type}>"
        f"({flat_offset_expr} /*offset*/, {flat_size_expr} /*size*/, {flat_stride_expr} /*stride*/);"
    )
    reshape = f"{ctx.current_indent}{result_cpp_type} {result_name} = {flat_name}.reshape({shape_expr} /*shape*/);"
    return f"{shape_prefix}{flat_view}\n{reshape}"


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

    return _emit_ring_slot_view(op, ctx)


@emit_c_impl(DmaAdvanceRingOp, target="npu_demo")
def _emit_npu_demo_dma_advance_ring(op: DmaAdvanceRingOp, ctx) -> str:
    """发射 npu_demo `dma.advance_ring` C++ 语句。

    功能说明:
    - 当前 npu_demo 串行执行中保留可用 slot view，避免引入未确认的 runtime ring helper。
    - 若后续公开 runtime ring API，再由计划统一收口真实轮转。

    使用示例:
    - stmt = _emit_npu_demo_dma_advance_ring(op, ctx)
    """

    return _emit_ring_slot_view(op, ctx)
