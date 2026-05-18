"""npu_demo memory dialect emitter.


功能说明:
- 注册 target=`npu_demo` 的 `memory.get_data` 源码发射实现。
- `memory.get_data` 只发射为公开 `Memory::data()` 调用，不新增 include API。

API 列表:
- 无公开 API。

使用示例:
- from kernel_gen.dsl.gen_kernel.emit import emit_c_op
- source = emit_c_op(memory_get_data_op, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/memory.py
"""

from __future__ import annotations

from kernel_gen.dialect.memory import MemoryGetDataOp
from kernel_gen.dialect.nn import NnMemoryType

from ..register import emit_c_impl, emit_c_value_impl


def _npu_demo_memory_element_cpp_type(memory_type: NnMemoryType, ctx) -> str:
    """返回 npu_demo memory element C++ 类型。

    功能说明:
    - 优先使用 memory type 的公开 template name。
    - 未携带 template 时通过公开 type dispatch 处理 element type。

    使用示例:
    - cpp_type = _npu_demo_memory_element_cpp_type(memory_type, ctx)
    """

    memory_type.verify()
    template_name = memory_type.template_name.data
    if template_name:
        return template_name
    return ctx.dispatch_type(memory_type.element_type)


@emit_c_impl(MemoryGetDataOp, target="npu_demo")
def _emit_npu_demo_memory_get_data(op: MemoryGetDataOp, ctx) -> str:
    """发射 npu_demo memory.get_data 语句。

    功能说明:
    - 生成 `<T>* ptr = <source>.data();`。
    - 指针 element type 继承 source memory 的 template 或 element dtype。

    使用示例:
    - stmt = _emit_npu_demo_memory_get_data(op, ctx)
    """

    result_name = ctx.create_or_get_name(op.result)
    source_type = op.source.type
    pointer_type = f"{_npu_demo_memory_element_cpp_type(source_type, ctx)}*"
    from .. import emit_c_value

    return f"{ctx.current_indent}{pointer_type} {result_name} = {emit_c_value(op.source, ctx)}.data();"


@emit_c_value_impl(MemoryGetDataOp, target="npu_demo")
def _emit_npu_demo_memory_get_data_value(value, ctx) -> str:
    """发射 npu_demo memory.get_data value 表达式。

    功能说明:
    - 已声明时复用绑定名称。
    - 未声明时内联为 `<source>.data()` 表达式。

    使用示例:
    - expr = _emit_npu_demo_memory_get_data_value(op.result, ctx)
    """

    bound = ctx.lookup_name(value)
    if bound is not None:
        return bound
    owner = value.owner
    from .. import emit_c_value

    return f"{emit_c_value(owner.source, ctx)}.data()"
