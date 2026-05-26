"""npu_demo `dma.reinterpret` EmitC 注册实现。

功能说明:
- 注册 target=`npu_demo` 的 `dma.reinterpret` EmitC 发射实现。
- 生成共享 source backing data 的 `Memory<...>` 构造语句，不复制内存。
- 本文件不提供跨文件公开 API；调用方必须通过 emit registry 与 `emit_c_op(...)` 公开入口调度。

API 列表:
- 无公开 API。

使用示例:
- source = emit_c_op(op, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/reinterpret.py
"""

from __future__ import annotations

from xdsl.dialects.builtin import i8

from kernel_gen.dialect.dma import DmaReinterpretOp
from kernel_gen.dialect.nn import NnMemoryType

from ...register import emit_c_impl


def _memory_element_cpp_type(memory_type: NnMemoryType, ctx) -> str:
    """返回当前文件发射 dma.reinterpret 所需的 C++ element type。

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


def _is_i8_byte_pool(memory_type: NnMemoryType) -> bool:
    """判断 memory type 是否为一维 i8 byte pool。

    功能说明:
    - byte pool source 的 `dma.reinterpret.offset` 以 byte 为单位。
    - typed source 的 offset 保持 source element 单位。

    使用示例:
    - if _is_i8_byte_pool(memory_type): ...
    """

    return len(memory_type.shape.data) == 1 and memory_type.element_type == i8


def _reinterpret_data_expr(
    source_expr: str,
    source_type: NnMemoryType,
    result_type: NnMemoryType,
    offset_expr: str,
    ctx,
) -> str:
    """生成 `dma.reinterpret` 的底层 data 指针表达式。

    功能说明:
    - byte pool source 先按 byte 加 offset，再 cast 到 result element pointer。
    - typed source 按 source/result element 单位加 offset。

    使用示例:
    - expr = _reinterpret_data_expr("src", source_type, result_type, "offset", ctx)
    """

    result_element_type = _memory_element_cpp_type(result_type, ctx)
    if _is_i8_byte_pool(source_type):
        source_element_type = _memory_element_cpp_type(source_type, ctx)
        return (
            f"reinterpret_cast<{result_element_type}*>"
            f"(const_cast<{source_element_type}*>({source_expr}.data()) + {offset_expr})"
        )
    return f"const_cast<{result_element_type}*>({source_expr}.data()) + {offset_expr}"


@emit_c_impl(DmaReinterpretOp, target="npu_demo")
def _emit_npu_demo_dma_reinterpret(op: DmaReinterpretOp, ctx) -> str:
    """发射 npu_demo `dma.reinterpret` C++ 语句。

    功能说明:
    - 用 source data、result shape/stride brace-list 与 source format 构造新的 `Memory<...>`。
    - 不调用 view/reshape helper，保持 `dma.reinterpret` 的无副作用 alias 语义。
    - generated source 不生成 `long long *_shape[]` / `*_stride[]` 局部 layout buffer。

    使用示例:
    - stmt = _emit_npu_demo_dma_reinterpret(op, ctx)
    """

    from ... import emit_c_value

    source_expr = emit_c_value(op.source, ctx)
    source_type = op.source.type
    result_name = ctx.create_or_get_name(op.result)
    result_type = op.result.type
    if not isinstance(source_type, NnMemoryType):
        raise ctx.emit_error(op.name, "source must be nn.memory")
    if not isinstance(result_type, NnMemoryType):
        raise ctx.emit_error(op.name, "result must be nn.memory")
    shape_values = tuple(emit_c_value(value, ctx) for value in op.shape)
    stride_values = tuple(emit_c_value(value, ctx) for value in op.stride)
    offset_expr = emit_c_value(op.offset, ctx)
    data_expr = _reinterpret_data_expr(source_expr, source_type, result_type, offset_expr, ctx)
    shape_expr = "{" + ", ".join(shape_values) + "}"
    stride_expr = "{" + ", ".join(stride_values) + "}"
    return (
        f"{ctx.current_indent}{ctx.dispatch_type(result_type)} {result_name}"
        f"({data_expr}, {shape_expr} /*shape*/, {stride_expr} /*stride*/, {source_expr}.format());"
    )
