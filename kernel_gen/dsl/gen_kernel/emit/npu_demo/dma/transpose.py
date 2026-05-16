"""npu_demo `dma.transpose` EmitC 注册实现。

功能说明:
- 注册 target=`npu_demo` 的 `dma.transpose` EmitC 发射实现。
- 本文件不提供跨文件公开 API；调用方必须通过 emit registry 与 `emit_c_op(...)` 公开入口调度。

API 列表:
- 无公开 API。

使用示例:
- source = emit_c_op(op, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/transpose.py
"""

from __future__ import annotations

from xdsl.dialects.builtin import IntAttr

from kernel_gen.dialect.dma import DmaTransposeOp
from kernel_gen.dialect.nn import NnMemoryType

from ...register import emit_c_impl


def _memory_element_cpp_type(memory_type: NnMemoryType, ctx) -> str:
    """返回当前文件发射 dma.transpose 所需的 C++ element type。

    功能说明:
    - 优先使用 `NnMemoryType.template_name` 作为模板 dtype。
    - 未携带 template name 时通过 `ctx.dispatch_type(...)` 发射真实 element type。

    使用示例:
    - element_type = _memory_element_cpp_type(memory_type, ctx)
    """

    memory_type.verify()
    template_name = memory_type.template_name.data
    if template_name:
        return template_name
    return ctx.dispatch_type(memory_type.element_type)


@emit_c_impl(DmaTransposeOp, target="npu_demo")
def _emit_npu_demo_dma_transpose(op: DmaTransposeOp, ctx) -> str:
    """发射 npu_demo `dma.transpose` C++ 语句。

    功能说明:
    - 根据 `DmaTransposeOp` 的 target/source/perm 生成 `transpose<...>(...)` 语句。
    - memory dtype 模板参数由当前文件内 helper 读取 template name 或真实 dtype。

    使用示例:
    - stmt = _emit_npu_demo_dma_transpose(op, ctx)
    """

    from ... import emit_c_value

    target_expr = emit_c_value(op.target, ctx)
    source_expr = emit_c_value(op.source, ctx)
    perm_values = ", ".join(
        str(value.data if isinstance(value, IntAttr) else value.value.data) for value in op.perm.data
    )
    return (
        f"{ctx.current_indent}transpose<{ctx.dispatch_attr(op.target.type)}, {ctx.dispatch_attr(op.source.type)}, "
        f"{_memory_element_cpp_type(op.target.type, ctx)}, {_memory_element_cpp_type(op.source.type, ctx)}>"
        f"({target_expr} /*dst*/, {source_expr} /*source*/, {{{perm_values}}} /*perm*/);"
    )
