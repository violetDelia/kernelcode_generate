"""npu_demo `dma.store` EmitC 注册实现。

功能说明:
- 注册 target=`npu_demo` 的 `dma.store` EmitC 发射实现。
- 本文件不提供跨文件公开 API；调用方必须通过 emit registry 与 `emit_c_op(...)` 公开入口调度。

API 列表:
- 无公开 API。

使用示例:
- source = emit_c_op(op, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/store.py
"""

from __future__ import annotations

from xdsl.dialects.builtin import StringAttr
from xdsl.ir import Operation

from kernel_gen.dialect.dma import DmaStoreOp
from kernel_gen.dialect.symbol import SymbolConstOp

from ...register import emit_c_impl


def _memory_element_cpp_type(memory_type, ctx) -> str:
    """返回 memory 的 C++ element type。

    功能说明:
    - 优先使用 `NnMemoryType.template_name` 发射模板 dtype。
    - 未携带 template name 时回退到 `element_type` 的 concrete C++ 类型。

    使用示例:
    - dtype = _memory_element_cpp_type(op.target.type, ctx)
    """

    memory_type.verify()
    template_name = memory_type.template_name.data
    if template_name:
        return template_name
    return ctx.dispatch_type(memory_type.element_type)


@emit_c_impl(DmaStoreOp, target="npu_demo")
def _emit_npu_demo_dma_store(op: DmaStoreOp, ctx) -> str:
    """发射 npu_demo `dma.store` C++ 语句。

    功能说明:
    - 根据 `DmaStoreOp` 的 target、source、offset/size/stride 生成 `store<...>(ctx, ...)` 语句。
    - rank 1..8 的 offset/size/stride 发射为 `{...}`，由 include/api `Vector` 参数承接。
    - 仅作为当前文件内注册实现使用，不作为跨文件公开 API。

    使用示例:
    - stmt = _emit_npu_demo_dma_store(op, ctx)
    """

    from ... import emit_c_value

    target_expr = emit_c_value(op.target, ctx)
    source_expr = emit_c_value(op.source, ctx)
    layout_parts: list[tuple[str, list[str]]] = []
    for label, values in (("offset", op.offsets), ("size", op.sizes), ("stride", op.strides)):
        if len(values) == 0:
            raise ctx.emit_error("dma.store", "layout rank mismatch")
        parts: list[str] = []
        for value in values:
            owner = value.owner
            if isinstance(owner, SymbolConstOp):
                parts.append(str(owner.value.data))
                continue
            if (
                isinstance(owner, Operation)
                and owner.name == "builtin.unregistered"
                and isinstance(owner.attributes.get("op_name__"), StringAttr)
                and owner.attributes["op_name__"].data == "symbol.const"
                and owner.results
            ):
                parts.append(owner.results[0].type.expr.expr.data)
                continue
            parts.append(emit_c_value(value, ctx))
        layout_parts.append((label, parts))
    rank = len(layout_parts[0][1])
    if any(len(parts) != rank for _label, parts in layout_parts):
        raise ctx.emit_error("dma.store", "layout rank mismatch")
    if rank > 8:
        raise ctx.emit_error("dma.store", "layout rank exceeds Vector brace-list capacity")
    layout_exprs = ["{" + ", ".join(parts) + "}" for _label, parts in layout_parts]
    layout_lines: list[str] = []
    offset_expr, size_expr, stride_expr = layout_exprs
    op.target.type.verify()
    target_type = op.target.type.template_name.data or ctx.dispatch_type(op.target.type.element_type)
    op.source.type.verify()
    source_type = op.source.type.template_name.data or ctx.dispatch_type(op.source.type.element_type)
    return "\n".join(
        [
            *layout_lines,
            (
                f"{ctx.current_indent}store<{ctx.dispatch_attr(op.target.type)}, {ctx.dispatch_attr(op.source.type)}, "
                f"{target_type}, {source_type}>"
                f"(ctx, {target_expr} /*dst*/, {source_expr} /*source*/, {offset_expr} /*offset*/, "
                f"{size_expr} /*size*/, {stride_expr} /*stride*/);"
            ),
        ]
    )
