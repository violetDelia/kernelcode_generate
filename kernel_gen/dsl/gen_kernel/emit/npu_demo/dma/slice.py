"""npu_demo `dma.slice` EmitC 注册实现。

功能说明:
- 注册 target=`npu_demo` 的 `dma.slice` EmitC 发射实现。
- 本文件不提供跨文件公开 API；调用方必须通过 emit registry 与 `emit_c_op(...)` 公开入口调度。

API 列表:
- 无公开 API。

使用示例:
- source = emit_c_op(op, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/slice.py
"""

from __future__ import annotations

from kernel_gen.dialect.dma import DmaSliceOp

from ...register import emit_c_impl


@emit_c_impl(DmaSliceOp, target="npu_demo")
def _emit_npu_demo_dma_slice(op: DmaSliceOp, ctx) -> str:
    """发射 npu_demo `dma.slice` C++ 语句。

    功能说明:
    - 根据 `DmaSliceOp` 的 source、target 与 layout 参数生成 `slice(...)` 语句。
    - 仅作为当前文件内注册实现使用，不作为跨文件公开 API。

    使用示例:
    - stmt = _emit_npu_demo_dma_slice(op, ctx)
    """

    from ... import emit_c_value

    target_expr = emit_c_value(op.target, ctx)
    source_expr = emit_c_value(op.source, ctx)
    if len(op.offsets) == len(op.sizes) == len(op.strides) == 1:
        return (
            f"{ctx.current_indent}slice({target_expr} /*dst*/, {source_expr} /*source*/, "
            f"{emit_c_value(op.offsets[0], ctx)} /*offset*/, {emit_c_value(op.sizes[0], ctx)} /*size*/, {emit_c_value(op.strides[0], ctx)} /*stride*/);"
        )
    if len(op.offsets) == len(op.sizes) == len(op.strides) == 3:
        offset_expr = "{" + ", ".join(emit_c_value(value, ctx) for value in op.offsets) + "}"
        size_expr = "{" + ", ".join(emit_c_value(value, ctx) for value in op.sizes) + "}"
        stride_expr = "{" + ", ".join(emit_c_value(value, ctx) for value in op.strides) + "}"
        return (
            f"{ctx.current_indent}slice({target_expr} /*dst*/, {source_expr} /*source*/, "
            f"{offset_expr} /*offset*/, {size_expr} /*size*/, "
            f"{stride_expr} /*stride*/);"
        )
    if not 1 <= len(op.offsets) <= 4 or not 1 <= len(op.sizes) <= 4 or not 1 <= len(op.strides) <= 4:
        raise ctx.emit_error("dma.slice", "npu_demo Vector supports 1..4 values")
    offset_vec = "Vector{" + ", ".join(emit_c_value(value, ctx) for value in op.offsets) + "}"
    size_vec = "Vector{" + ", ".join(emit_c_value(value, ctx) for value in op.sizes) + "}"
    stride_vec = "Vector{" + ", ".join(emit_c_value(value, ctx) for value in op.strides) + "}"
    return (
        f"{ctx.current_indent}slice({target_expr} /*dst*/, {source_expr} /*source*/, "
        f"{offset_vec} /*offset*/, {size_vec} /*size*/, {stride_vec} /*stride*/);"
    )
