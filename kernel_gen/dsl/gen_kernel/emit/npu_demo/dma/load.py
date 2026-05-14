"""npu_demo `dma.load` EmitC 注册实现。

功能说明:
- 注册 target=`npu_demo` 的 `dma.load` EmitC 发射实现。
- 本文件不提供跨文件公开 API；调用方必须通过 emit registry 与 `emit_c_op(...)` 公开入口调度。

API 列表:
- 无公开 API。

使用示例:
- source = emit_c_op(op, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/load.py
"""

from __future__ import annotations

from xdsl.dialects.builtin import StringAttr
from xdsl.ir import Operation

from kernel_gen.dialect.dma import DmaLoadOp
from kernel_gen.dialect.symbol import SymbolConstOp

from ..type import memory_element_cpp_type
from ...register import emit_c_impl


@emit_c_impl(DmaLoadOp, target="npu_demo")
def _emit_npu_demo_dma_load(op: DmaLoadOp, ctx) -> str:
    """发射 npu_demo `dma.load` C++ 语句。

    功能说明:
    - 根据 `DmaLoadOp` 的 target、source、offset/size/stride 生成 `load<...>(...)` 语句。
    - 仅作为当前文件内注册实现使用，不作为跨文件公开 API。

    使用示例:
    - stmt = _emit_npu_demo_dma_load(op, ctx)
    """

    from ... import emit_c_value

    target_expr = emit_c_value(op.target, ctx)
    source_expr = emit_c_value(op.source, ctx)
    layout_exprs: list[str] = []
    for values in (op.offsets, op.sizes, op.strides):
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
        layout_exprs.append("{" + ", ".join(parts) + "}")
    offset_expr, size_expr, stride_expr = layout_exprs
    return (
        f"{ctx.current_indent}load<{ctx.dispatch_attr(op.target.type)}, {ctx.dispatch_attr(op.source.type)}, "
        f"{memory_element_cpp_type(op.target.type, ctx)}, {memory_element_cpp_type(op.source.type, ctx)}>"
        f"({target_expr} /*dst*/, {source_expr} /*source*/, {offset_expr} /*offset*/, "
        f"{size_expr} /*size*/, {stride_expr} /*stride*/);"
    )
