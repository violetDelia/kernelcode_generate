"""npu_demo `dma.cast` EmitC 注册实现。

功能说明:
- 注册 target=`npu_demo` 的 `dma.cast` EmitC 发射实现。
- 本文件不提供跨文件公开 API；调用方必须通过 emit registry 与 `emit_c_op(...)` 公开入口调度。

API 列表:
- 无公开 API。

使用示例:
- source = emit_c_op(op, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/cast.py
"""

from __future__ import annotations

from kernel_gen.dialect.dma import DmaCastOp
from kernel_gen.dialect.nn import NnMemoryType

from ..type import memory_element_cpp_type
from ...register import emit_c_impl


@emit_c_impl(DmaCastOp, target="npu_demo")
def _emit_npu_demo_dma_cast(op: DmaCastOp, ctx) -> str:
    """发射 npu_demo `dma.cast` C++ 语句。

    功能说明:
    - 根据 `DmaCastOp` 的 target/source memory 生成 `cast<...>(...)` 语句。
    - memory dtype 模板参数通过 `memory_element_cpp_type(...)` 读取 template name 或真实 dtype。

    使用示例:
    - stmt = _emit_npu_demo_dma_cast(op, ctx)
    """

    from ... import emit_c_value

    if len(op.operands) == 2:
        target_value = op.target
        source_value = op.source
        target_type_attr = op.target.type
    elif len(op.operands) == 1 and len(op.results) == 1:
        target_value = op.results[0]
        source_value = op.operands[0]
        target_type_attr = op.results[0].type
    else:
        raise ctx.emit_error(op.name, "unsupported op")
    if not isinstance(target_type_attr, NnMemoryType) or not isinstance(source_value.type, NnMemoryType):
        raise ctx.emit_error(op.name, "unsupported op")
    target_expr = emit_c_value(target_value, ctx)
    source_expr = emit_c_value(source_value, ctx)
    return (
        f"{ctx.current_indent}cast<{ctx.dispatch_attr(target_type_attr)}, {memory_element_cpp_type(target_type_attr, ctx)}, "
        f"{memory_element_cpp_type(source_value.type, ctx)}>"
        f"({target_expr} /*dst*/, {source_expr} /*source*/);"
    )
