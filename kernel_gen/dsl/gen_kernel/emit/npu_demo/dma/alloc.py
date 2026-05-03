"""npu_demo `dma.alloc` EmitC 注册实现。

功能说明:
- 注册 target=`npu_demo` 的 `dma.alloc` EmitC 发射实现。
- 本文件不提供跨文件公开 API；调用方必须通过 emit registry 与 `emit_c_op(...)` 公开入口调度。

API 列表:
- 无公开 API。

使用示例:
- source = emit_c_op(op, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/alloc.py
"""

from __future__ import annotations

from xdsl.dialects.builtin import IntAttr, StringAttr

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.symbol import SymbolValueType

from ...register import emit_c_impl


@emit_c_impl(DmaAllocOp, target="npu_demo")
def _emit_npu_demo_dma_alloc(op: DmaAllocOp, ctx) -> str:
    """发射 npu_demo `dma.alloc` C++ 语句。

    功能说明:
    - 根据 `DmaAllocOp` 的 memory type、dynamic shape 与 stride 生成 `alloc<...>(...)` 语句。
    - 仅作为当前文件内注册实现使用，不作为跨文件公开 API。

    使用示例:
    - stmt = _emit_npu_demo_dma_alloc(op, ctx)
    """

    from ... import emit_c_value

    result_name = ctx.create_or_get_name(op.result)
    result_type = op.result.type
    shape_values = [emit_c_value(value, ctx) for value in op.dynamic_shape]
    if not shape_values:
        shape_values = []
        for value in result_type.shape.data:
            if isinstance(value, IntAttr):
                shape_values.append(str(value.data))
                continue
            if isinstance(value, StringAttr):
                shape_values.append(value.data)
                continue
            raise ctx.emit_error(op.name, "unsupported alloc layout value")
    symbol_bindings: dict[str, str] = {}
    for value in op.dynamic_shape:
        value_type = value.type
        if isinstance(value_type, SymbolValueType):
            value_expr = value_type.expr.expr.data
            value_name = emit_c_value(value, ctx)
            for expr_key in (value_expr, f"({value_expr})", value_expr.replace(" ", "")):
                symbol_bindings[expr_key] = value_name
            public_value = value_type.get_value()
            if isinstance(public_value, str):
                for expr_key in (public_value, f"({public_value})", public_value.replace(" ", "")):
                    symbol_bindings[expr_key] = value_name
    stride_values: list[str] = []
    for value in result_type.stride.data:
        if isinstance(value, IntAttr):
            stride_values.append(str(value.data))
            continue
        if isinstance(value, StringAttr):
            mapped = None
            layout_expr = value.data
            mapped = symbol_bindings.get(layout_expr)
            if mapped is None:
                mapped = symbol_bindings.get(layout_expr.replace(" ", ""))
            if mapped is None and layout_expr.startswith("(") and layout_expr.endswith(")"):
                unwrapped_expr = layout_expr[1:-1]
                mapped = symbol_bindings.get(unwrapped_expr) or symbol_bindings.get(unwrapped_expr.replace(" ", ""))
            stride_values.append(mapped or layout_expr)
            continue
        raise ctx.emit_error(f"{op.name} stride", "unsupported alloc layout value")
    if not hasattr(result_type, "element_type"):
        raise ctx.emit_error(op.name, "result must be nn.memory")
    space_expr = ctx.dispatch_attr(result_type)
    element_type = ctx.dispatch_type(result_type.element_type)
    shape_text = ", ".join(shape_values)
    stride_text = ", ".join(stride_values)
    return (
        f"{ctx.current_indent}Memory<{space_expr}, {element_type}> {result_name} = "
        f"alloc<{space_expr}, {element_type}>({{{shape_text}}} /*shape*/, {{{stride_text}}} /*stride*/);"
    )
