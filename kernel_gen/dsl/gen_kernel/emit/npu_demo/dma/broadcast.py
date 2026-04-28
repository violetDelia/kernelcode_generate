"""npu_demo dma.broadcast 发射实现。

创建者: 小李飞刀
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 发射 npu_demo 目标下的 `dma.broadcast`。
- memory source 发射为 `broadcast<...>(dst, source)`。
- scalar source 发射为 `fill<...>(dst, value)`，保持 `dma.broadcast` 标量语义。

API 列表:
- 无公开 API；通过 emit registry 注册 `DmaBroadcastOp` 的 npu_demo 发射器。

使用示例:
- stmt = emit_c_op(dma_broadcast_op, EmitCContext())

关联文件:
- spec: spec/dsl/gen_kernel/emit.md
- test: test/dsl/gen_kernel/emit/test_emit.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/broadcast.py
"""

from __future__ import annotations

from kernel_gen.dialect.dma import DmaBroadcastOp
from kernel_gen.dialect.nn import NnMemoryType

from ...register import emit_c_impl


@emit_c_impl(DmaBroadcastOp, target="npu_demo")
def _emit_npu_demo_dma_broadcast(op: DmaBroadcastOp, ctx) -> str:
    """发射 npu_demo `dma.broadcast`。

    创建者: 小李飞刀
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 对 memory source 生成 npu_demo broadcast helper 调用。
    - 对 scalar source 生成 npu_demo fill helper 调用。

    使用示例:
    - stmt = _emit_npu_demo_dma_broadcast(op, ctx)

    关联文件:
    - spec: spec/dsl/gen_kernel/emit.md
    - test: test/dsl/gen_kernel/emit/test_emit.py
    - 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/broadcast.py
    """

    from ... import emit_c_value

    if not isinstance(op.target.type, NnMemoryType):
        raise ctx.emit_error(op.name, "unsupported op")
    dst_expr = emit_c_value(op.target, ctx)
    if not isinstance(op.source.type, NnMemoryType):
        value_expr = emit_c_value(op.source, ctx)
        return (
            f"{ctx.current_indent}fill<{ctx.dispatch_attr(op.target.type)}, "
            f"{ctx.dispatch_type(op.target.type.element_type)}>"
            f"({dst_expr} /*dst*/, {value_expr} /*value*/);"
        )
    src_expr = emit_c_value(op.source, ctx)
    return (
        f"{ctx.current_indent}broadcast<{ctx.dispatch_attr(op.target.type)}, {ctx.dispatch_attr(op.source.type)}, "
        f"{ctx.dispatch_type(op.target.type.element_type)}, {ctx.dispatch_type(op.source.type.element_type)}>"
        f"({dst_expr} /*dst*/, {src_expr} /*source*/);"
    )
