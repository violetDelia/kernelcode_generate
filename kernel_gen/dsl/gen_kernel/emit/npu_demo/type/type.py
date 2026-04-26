"""`target=npu_demo` 的 type 到 C/C++ 类型文本映射。"""

from __future__ import annotations

from xdsl.dialects.builtin import BFloat16Type, Float16Type, Float64Type, IndexType, IntegerType, Signedness

from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType

from ...register import emit_c_type_impl


def _integer_type_to_c(attr: IntegerType) -> str:
    if attr.width.data == 1:
        return "bool"
    prefix = "uint" if attr.signedness.data == Signedness.UNSIGNED else "int"
    return f"{prefix}{attr.width.data}_t"


@emit_c_type_impl(IntegerType, target="npu_demo")
def _emit_npu_demo_integer_type(attr: IntegerType, _ctx) -> str:
    return _integer_type_to_c(attr)


@emit_c_type_impl(Float16Type, target="npu_demo")
def _emit_npu_demo_float16_type(_attr: Float16Type, _ctx) -> str:
    return "half"


@emit_c_type_impl(BFloat16Type, target="npu_demo")
def _emit_npu_demo_bfloat16_type(_attr: BFloat16Type, _ctx) -> str:
    return "bfloat16_t"


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
    return f"Memory<{space_param}, {ctx.dispatch_type(attr.element_type)}>"


@emit_c_type_impl(SymbolValueType, target="npu_demo")
def _emit_npu_demo_symbol_value_type(_attr: SymbolValueType, _ctx) -> str:
    return "S_INT"
