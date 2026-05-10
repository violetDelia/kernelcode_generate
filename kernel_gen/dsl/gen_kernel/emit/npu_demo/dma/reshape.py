"""npu_demo `dma.reshape` EmitC 注册实现。

功能说明:
- 注册 target=`npu_demo` 的 `dma.reshape` EmitC 发射实现。
- 本文件不提供跨文件公开 API；调用方必须通过 emit registry 与 `emit_c_op(...)` 公开入口调度。

API 列表:
- 无公开 API。

使用示例:
- source = emit_c_op(op, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/reshape.py
"""

from __future__ import annotations

from collections.abc import Sequence

from kernel_gen.dialect.dma import DmaReshapeOp

from ...register import emit_c_impl


def _shape_vector_expr(values: Sequence[str], ctx) -> tuple[str, str]:
    """构造 `Vector` shape 表达式。

    功能说明:
    - rank 1..4 使用公开 `Vector{...}` 自有存储构造。
    - rank >4 使用当前语句前的局部 `long long[]`，再走公开 `Vector(data, size)` 构造。

    使用示例:
    - prefix, expr = _shape_vector_expr(["m", "n"], ctx)
    """

    if len(values) <= 4:
        return "", "Vector{" + ", ".join(values) + "}"
    shape_buf_name = ctx.allocate_name("reshape_shape_")
    prefix = f"{ctx.current_indent}long long {shape_buf_name}[{len(values)}] = {{{', '.join(values)}}};\n"
    return prefix, f"Vector({shape_buf_name}, {len(values)})"


@emit_c_impl(DmaReshapeOp, target="npu_demo")
def _emit_npu_demo_dma_reshape(op: DmaReshapeOp, ctx) -> str:
    """发射 npu_demo `dma.reshape` C++ 语句。

    功能说明:
    - 根据 `DmaReshapeOp` 的 source 与 shape 生成成员式 `reshape(...)` 语句。
    - rank 1..4 使用 `Vector{...}`，rank >4 使用 `long long[]` 加 `Vector(data, size)`。
    - 仅作为当前文件内注册实现使用，不作为跨文件公开 API。

    使用示例:
    - stmt = _emit_npu_demo_dma_reshape(op, ctx)
    """

    from ... import emit_c_value

    result_name = ctx.create_or_get_name(op.result)
    source_expr = emit_c_value(op.source, ctx)
    shape_values = tuple(emit_c_value(value, ctx) for value in op.shape)
    shape_prefix, shape_expr = _shape_vector_expr(shape_values, ctx)
    return (
        f"{shape_prefix}"
        f"{ctx.current_indent}{ctx.dispatch_type(op.result.type)} {result_name} = "
        f"{source_expr}.reshape({shape_expr} /*shape*/);"
    )
