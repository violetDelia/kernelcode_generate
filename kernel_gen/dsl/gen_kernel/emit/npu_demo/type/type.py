"""`target=npu_demo` 的 type 到 C/C++ 类型文本映射。


功能说明:
- 注册 `npu_demo` target 的 xDSL / 仓库类型到 C/C++ 类型文本映射。

API 列表:
- 无公开 API。

使用示例:
- from kernel_gen.dsl.gen_kernel import EmitCContext
- c_type = EmitCContext().dispatch_type(memory_type)

关联文件:
- spec: spec/dsl/gen_kernel/emit.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/type/type.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from xdsl.dialects.builtin import (
    BFloat16Type,
    Float16Type,
    Float32Type,
    Float64Type,
    IndexType,
    IntegerType,
    Signedness,
)

from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType

from ...register import emit_c_type_impl

if TYPE_CHECKING:
    from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext


def _memory_element_cpp_type(memory_type: NnMemoryType, ctx: EmitCContext) -> str:
    """返回 npu_demo memory 的 C++ element 类型文本。

    功能说明:
    - 若 `memory_type` 携带 template name，返回该 template name。
    - 未携带 template name 时回退 `ctx.dispatch_type(memory_type.element_type)`。

    使用示例:
    - element_type = _memory_element_cpp_type(memory_type, ctx)

    关联文件:
    - spec: spec/dsl/gen_kernel/emit.md
    - test: test/dsl/gen_kernel/emit/test_package.py
    - 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/type/type.py
    """

    memory_type.verify()
    template_name = memory_type.template_name.data
    if template_name:
        return template_name
    return ctx.dispatch_type(memory_type.element_type)


@emit_c_type_impl(IntegerType, target="npu_demo")
def _emit_npu_demo_integer_type(attr: IntegerType, _ctx) -> str:
    if attr.width.data == 1:
        return "bool"
    prefix = "uint" if attr.signedness.data == Signedness.UNSIGNED else "int"
    return f"{prefix}{attr.width.data}_t"


@emit_c_type_impl(Float16Type, target="npu_demo")
def _emit_npu_demo_float16_type(_attr: Float16Type, _ctx) -> str:
    return "half"


@emit_c_type_impl(BFloat16Type, target="npu_demo")
def _emit_npu_demo_bfloat16_type(_attr: BFloat16Type, _ctx) -> str:
    return "bfloat16_t"


@emit_c_type_impl(Float32Type, target="npu_demo")
def _emit_npu_demo_float32_type(_attr: Float32Type, _ctx) -> str:
    """发射 npu_demo float 类型文本。


    功能说明:
    - 将 xDSL f32 类型映射为 npu_demo C/C++ float 类型文本。

    使用示例:
    - c_type = ctx.dispatch_type(f32)
    """

    return "float"


@emit_c_type_impl(Float64Type, target="npu_demo")
def _emit_npu_demo_float64_type(_attr: Float64Type, _ctx) -> str:
    return "double"


@emit_c_type_impl(IndexType, target="npu_demo")
def _emit_npu_demo_index_type(_attr: IndexType, _ctx) -> str:
    return "long long"


@emit_c_type_impl(NnMemoryType, target="npu_demo")
def _emit_npu_demo_memory_type(attr: NnMemoryType, ctx) -> str:
    space_param = ctx.dispatch_attr(attr)
    if space_param is None:
        raise ValueError(f"unsupported npu_demo memory type space: {attr.space.space.data}")
    return f"Memory<{space_param}, {_memory_element_cpp_type(attr, ctx)}>"


@emit_c_type_impl(SymbolValueType, target="npu_demo")
def _emit_npu_demo_symbol_value_type(_attr: SymbolValueType, _ctx) -> str:
    return "S_INT"
