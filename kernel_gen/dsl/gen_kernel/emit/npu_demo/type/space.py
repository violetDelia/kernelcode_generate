"""`target=npu_demo` 的 memory space 到 C 模板参数映射。

功能说明:
- 注册 `NnMemorySpaceAttr`、memory space 文本与 `NnMemoryType` 到 npu_demo C 模板参数的映射。
- 本文件不提供跨文件公开 API；调用方必须通过 emit registry 与 `dispatch_attr(...)` 公开入口调度。

API 列表:
- 无公开 API。

使用示例:
- space = ctx.dispatch_attr(memory_type)

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/type/__init__.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/type/space.py
"""

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


@emit_c_attr_impl(NnMemorySpaceAttr, target="npu_demo")
def _emit_npu_demo_memory_space_to_c(space_attr: NnMemorySpaceAttr, _ctx) -> str:
    """发射 npu_demo memory space attribute 模板参数。

    功能说明:
    - 将 `NnMemorySpaceAttr` 映射为 `GM/SM/LM/TSM/TLM*` 这类 npu_demo C 模板参数。
    - 仅作为当前文件内注册实现使用，不作为跨文件公开 API。

    使用示例:
    - text = _emit_npu_demo_memory_space_to_c(space_attr, ctx)
    """

    mapped = _SPACE_NAME_MAP.get(space_attr.space.data)
    if mapped is None:
        raise ValueError(f"unsupported memory space: {space_attr.space.data}")
    return mapped


@emit_c_attr_impl(str, target="npu_demo")
def _emit_npu_demo_space_name_to_c(space_name: str, _ctx) -> str:
    """发射 npu_demo memory space 文本模板参数。

    功能说明:
    - 将 memory space 字符串映射为 npu_demo C 模板参数。
    - 仅作为当前文件内注册实现使用，不作为跨文件公开 API。

    使用示例:
    - text = _emit_npu_demo_space_name_to_c("global", ctx)
    """

    mapped = _SPACE_NAME_MAP.get(space_name)
    if mapped is None:
        raise ValueError(f"unsupported memory space: {space_name}")
    return mapped


@emit_c_attr_impl(NnMemoryType, target="npu_demo")
def _emit_npu_demo_space_to_c(memory_type: NnMemoryType, ctx) -> str:
    """发射 npu_demo memory type 的 space 模板参数。

    功能说明:
    - 从 `NnMemoryType.space` 提取 memory space 并映射为 npu_demo C 模板参数。
    - 仅作为当前文件内注册实现使用，不作为跨文件公开 API。

    使用示例:
    - text = _emit_npu_demo_space_to_c(memory_type, ctx)
    """

    space_name = memory_type.space.space.data
    mapped = _SPACE_NAME_MAP.get(space_name)
    if mapped is None:
        raise ValueError(f"unsupported memory space: {space_name}")
    return mapped
