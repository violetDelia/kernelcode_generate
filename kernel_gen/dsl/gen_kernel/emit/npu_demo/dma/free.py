"""npu_demo `dma.free` EmitC 注册实现。

功能说明:
- 注册 target=`npu_demo` 的 `dma.free` EmitC 发射实现。
- 本文件不提供跨文件公开 API；调用方必须通过 emit registry 与 `emit_c_op(...)` 公开入口调度。

API 列表:
- 无公开 API。

使用示例:
- source = emit_c_op(op, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py
"""

from __future__ import annotations

from kernel_gen.dialect.dma import DmaFreeOp

from ..type import memory_element_cpp_type
from ...register import emit_c_impl


@emit_c_impl(DmaFreeOp, target="npu_demo")
def _emit_npu_demo_dma_free(op: DmaFreeOp, ctx) -> str:
    """发射 npu_demo `dma.free` C++ 语句。

    功能说明:
    - 根据 `DmaFreeOp` 的 source memory 生成 `free<...>(...)` 语句。
    - memory dtype 模板参数通过 `memory_element_cpp_type(...)` 读取 template name 或真实 dtype。

    使用示例:
    - stmt = _emit_npu_demo_dma_free(op, ctx)
    """

    from ... import emit_c_value

    source_expr = emit_c_value(op.source, ctx)
    space_expr = ctx.dispatch_attr(op.source.type)
    source_type = memory_element_cpp_type(op.source.type, ctx)
    return f"{ctx.current_indent}free<{space_expr}, {source_type}>({source_expr} /*source*/);"
