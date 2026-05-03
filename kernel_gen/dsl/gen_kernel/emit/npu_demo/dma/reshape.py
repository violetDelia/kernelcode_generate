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

from kernel_gen.dialect.dma import DmaReshapeOp

from ...register import emit_c_impl


@emit_c_impl(DmaReshapeOp, target="npu_demo")
def _emit_npu_demo_dma_reshape(op: DmaReshapeOp, ctx) -> str:
    """发射 npu_demo `dma.reshape` C++ 语句。

    功能说明:
    - 根据 `DmaReshapeOp` 的 source 与 shape 生成 memory `reshape(...)` 语句。
    - 仅作为当前文件内注册实现使用，不作为跨文件公开 API。

    使用示例:
    - stmt = _emit_npu_demo_dma_reshape(op, ctx)
    """

    from ... import emit_c_value

    result_name = ctx.create_or_get_name(op.result)
    source_expr = emit_c_value(op.source, ctx)
    shape_expr = "{" + ", ".join(emit_c_value(value, ctx) for value in op.shape) + "}"
    return (
        f"{ctx.current_indent}{ctx.dispatch_type(op.result.type)} {result_name} = "
        f"{source_expr}.reshape({shape_expr} /*shape*/);"
    )
