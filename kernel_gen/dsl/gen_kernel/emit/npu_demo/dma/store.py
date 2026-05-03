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


@emit_c_impl(DmaStoreOp, target="npu_demo")
def _emit_npu_demo_dma_store(op: DmaStoreOp, ctx) -> str:
    """发射 npu_demo `dma.store` C++ 语句。

    功能说明:
    - 根据 `DmaStoreOp` 的 target、source、offset/size/stride 生成 `store<...>(...)` 语句。
    - rank 1..4 的 offset/size/stride 统一发射为显式 `Vector(...)` 构造，避免多维裸初始化列表触发 C++ 构造歧义。
    - 仅作为当前文件内注册实现使用，不作为跨文件公开 API。

    使用示例:
    - stmt = _emit_npu_demo_dma_store(op, ctx)
    """

    from ... import emit_c_value

    target_expr = emit_c_value(op.target, ctx)
    source_expr = emit_c_value(op.source, ctx)
    layout_exprs: list[str] = []
    for values in (op.offsets, op.sizes, op.strides):
        if not 1 <= len(values) <= 4:
            raise ctx.emit_error("dma.store", "npu_demo Vector supports 1..4 values")
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
        cast_parts = [f"static_cast<long long>({part})" for part in parts]
        layout_exprs.append("Vector(" + ", ".join(cast_parts) + ")")
    offset_expr, size_expr, stride_expr = layout_exprs
    return (
        f"{ctx.current_indent}store<{ctx.dispatch_attr(op.target.type)}, {ctx.dispatch_attr(op.source.type)}, "
        f"{ctx.dispatch_type(op.target.type.element_type)}, {ctx.dispatch_type(op.source.type.element_type)}>"
        f"({target_expr} /*dst*/, {source_expr} /*source*/, {offset_expr} /*offset*/, "
        f"{size_expr} /*size*/, {stride_expr} /*stride*/);"
    )
