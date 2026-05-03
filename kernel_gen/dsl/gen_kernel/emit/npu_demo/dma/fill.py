"""npu_demo dma.fill 发射实现。


功能说明:
- 发射 npu_demo target 下的 `dma.fill` helper 调用。
- 将 `inf` / `-inf` 浮点字面量转换为 C++ `std::numeric_limits<T>::infinity()`，避免生成源码依赖未定义标识符。

API 列表:
- 无公开 API；通过 emit registry 注册 `DmaFillOp` 的 npu_demo 发射器。

使用示例:
- stmt = emit_c_op(dma_fill_op, EmitCContext())

关联文件:
- spec: spec/dsl/gen_kernel/emit.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/fill.py
"""

from __future__ import annotations

from kernel_gen.dialect.dma import DmaFillOp

from ...register import emit_c_impl


@emit_c_impl(DmaFillOp, target="npu_demo")
def _emit_npu_demo_dma_fill(op: DmaFillOp, ctx) -> str:
    """发射 npu_demo `dma.fill`。


    功能说明:
    - 生成 `fill<Space, Type>(dst, value)` helper 调用。
    - 对字符串无穷字面量对应的 lowered 常量做 C++ 可编译化。

    使用示例:
    - stmt = _emit_npu_demo_dma_fill(op, ctx)
    """

    from ... import emit_c_value

    target_expr = emit_c_value(op.target, ctx)
    space_expr = ctx.dispatch_attr(op.target.type)
    target_type = ctx.dispatch_type(op.target.type.element_type)
    value_expr = emit_c_value(op.value, ctx)
    if value_expr == "inf":
        value_expr = f"std::numeric_limits<{target_type}>::infinity()"
    elif value_expr == "-inf":
        value_expr = f"-std::numeric_limits<{target_type}>::infinity()"
    return f"{ctx.current_indent}fill<{space_expr}, {target_type}>({target_expr} /*dst*/, {value_expr} /*value*/);"
