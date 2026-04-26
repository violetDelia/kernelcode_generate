"""`target=npu_demo` 的 memory space 到 C 模板参数映射。"""

from __future__ import annotations

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType

from ...register import emit_c_attr_impl

_SPACE_NAME_MAP = {
    "global": "GM",
    "shared": "SM",
    "local": "LM",
    "tsm": "TSM",
    "tlm1": "TLM1",
    "tlm2": "TLM2",
    "tlm3": "TLM3",
}


def _lookup_space_name(space_name: str) -> str:
    mapped = _SPACE_NAME_MAP.get(space_name)
    if mapped is None:
        raise ValueError(f"unsupported memory space: {space_name}")
    return mapped


@emit_c_attr_impl(NnMemorySpaceAttr, target="npu_demo")
def _emit_npu_demo_memory_space_to_c(space_attr: NnMemorySpaceAttr, _ctx) -> str:
    return _lookup_space_name(space_attr.space.data)


@emit_c_attr_impl(str, target="npu_demo")
def _emit_npu_demo_space_name_to_c(space_name: str, _ctx) -> str:
    return _lookup_space_name(space_name)


@emit_c_attr_impl(NnMemoryType, target="npu_demo")
def _emit_npu_demo_space_to_c(memory_type: NnMemoryType, ctx) -> str:
    return _emit_npu_demo_space_name_to_c(memory_type.space.space.data, ctx)
