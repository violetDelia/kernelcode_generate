"""npu_demo `dma.deslice` EmitC 注册实现。

功能说明:
- 注册 target=`npu_demo` 的 `dma.deslice` EmitC 发射实现。
- 本文件不提供跨文件公开 API；调用方必须通过 emit registry 与 `emit_c_op(...)` 公开入口调度。

API 列表:
- 无公开 API。

使用示例:
- source = emit_c_op(op, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/deslice.py
"""

from __future__ import annotations

from kernel_gen.dialect.dma import DmaDesliceOp

from ...register import emit_c_impl


@emit_c_impl(DmaDesliceOp, target="npu_demo")
def _emit_npu_demo_dma_deslice(op: DmaDesliceOp, ctx) -> str:
    """发射 npu_demo `dma.deslice` C++ 语句。

    功能说明:
    - 根据 `DmaDesliceOp` 的 source、target 与 layout 参数生成 `deslice(...)` 语句。
    - offset/size/stride 统一发射为 brace-list，交由 include initializer-list overload 承接。
    - 仅作为当前文件内注册实现使用，不作为跨文件公开 API。

    使用示例:
    - stmt = _emit_npu_demo_dma_deslice(op, ctx)
    """

    from ... import emit_c_value

    source_expr = emit_c_value(op.source, ctx)
    target_expr = emit_c_value(op.target, ctx)
    if not len(op.offsets) == len(op.sizes) == len(op.strides) or len(op.offsets) == 0:
        raise ctx.emit_error("dma.deslice", "layout rank mismatch")
    offset_vec = "{" + ", ".join(emit_c_value(value, ctx) for value in op.offsets) + "}"
    size_vec = "{" + ", ".join(emit_c_value(value, ctx) for value in op.sizes) + "}"
    stride_vec = "{" + ", ".join(emit_c_value(value, ctx) for value in op.strides) + "}"
    return (
        f"{ctx.current_indent}deslice({target_expr} /*target*/, {source_expr} /*source*/, "
        f"{offset_vec} /*offset*/, {size_vec} /*size*/, {stride_vec} /*stride*/);"
    )
