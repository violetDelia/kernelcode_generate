"""npu_demo `dma.copy` EmitC 注册实现。

功能说明:
- 注册 target=`npu_demo` 的 `dma.copy` EmitC 发射实现。
- `include/api/Dma.h` 不公开 `copy` helper，因此整块 copy 发射为公开 `slice(...)` 调用。
- 本文件不提供跨文件公开 API；调用方必须通过 emit registry 与 `emit_c_op(...)` 公开入口调度。

API 列表:
- 无公开 API。

使用示例:
- source = emit_c_op(op, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/copy.py
"""

from __future__ import annotations

from kernel_gen.dialect.dma import DmaCopyOp
from kernel_gen.dialect.nn import NnMemoryType

from ...register import emit_c_impl


@emit_c_impl(DmaCopyOp, target="npu_demo")
def _emit_npu_demo_dma_copy(op: DmaCopyOp, ctx) -> str:
    """发射 npu_demo `dma.copy` C++ 语句。

    功能说明:
    - 将 `dma.copy(target, source)` 映射为公开 `slice(target, source, zero, target.shape, one)`。
    - 避免生成 `include/api/Dma.h` 未公开的 `copy<...>(...)` helper。
    - offset/size/stride 统一发射为 brace-list，交由 include initializer-list overload 承接。

    使用示例:
    - stmt = _emit_npu_demo_dma_copy(op, ctx)
    """

    from ... import emit_c_value

    target_expr = emit_c_value(op.target, ctx)
    source_expr = emit_c_value(op.source, ctx)
    target_type = op.target.type
    if not isinstance(target_type, NnMemoryType):
        raise ctx.emit_error("dma.copy", "target must be nn.memory")
    rank = len(target_type.shape.data)
    if rank == 0:
        raise ctx.emit_error("dma.copy", "layout rank mismatch")
    offset_expr = "{" + ", ".join("0" for _ in range(rank)) + "}"
    size_expr = "{" + ", ".join(f"{target_expr}.get_shape({axis})" for axis in range(rank)) + "}"
    stride_expr = "{" + ", ".join("1" for _ in range(rank)) + "}"
    return (
        f"{ctx.current_indent}slice({target_expr} /*dst*/, {source_expr} /*source*/, "
        f"{offset_expr} /*offset*/, {size_expr} /*size*/, {stride_expr} /*stride*/);"
    )
