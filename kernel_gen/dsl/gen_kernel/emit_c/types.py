"""Type / space helpers for the package-style EmitC registry.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 把 `Memory` / `nn.space` / `!symbol.int` 的文本翻译收口到包内辅助模块。
- S2 阶段先保留与旧实现一致的文本输出，再由 `emit_c` 注册结构逐步接管调用点。

使用示例:
- from kernel_gen.dsl.gen_kernel.emit_c.types import type_to_c
- c_type = type_to_c(memory_type, EmitCContext(target="cpu"))

关联文件:
- spec: [spec/dsl/emit_c.md](../../../../spec/dsl/emit_c.md)
- spec: [spec/dsl/gen_kernel.md](../../../../spec/dsl/gen_kernel.md)
- test: [test/dsl/test_emit_c.py](../../../../test/dsl/test_emit_c.py)
- test: [test/dsl/test_gen_kernel.py](../../../../test/dsl/test_gen_kernel.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit_c/](.)
"""

from __future__ import annotations

from typing import Any

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType

from ..emit_context import EmitCContext, EmitCError
from .._legacy import load_legacy_emit_c_module

_legacy_emit_c = load_legacy_emit_c_module()


def memory_space_to_c(space_attr: NnMemorySpaceAttr) -> str:
    """把 `NnMemorySpaceAttr` 映射为 C 侧 `MemorySpace::...` 文本。"""

    return _legacy_emit_c._memory_space_to_c(space_attr)


def memory_space_to_c_for_target(space_attr: NnMemorySpaceAttr, target: str) -> str:
    """把 `NnMemorySpaceAttr` 映射为目标相关的 memory space 文本。"""

    return _legacy_emit_c._memory_space_to_c_for_target(space_attr, target)


def space_to_c(memory_type: NnMemoryType, ctx: EmitCContext) -> str:
    """把 `nn.memory` 的 space 映射为模板参数文本。"""

    return _legacy_emit_c._space_to_c(memory_type, ctx)


def space_name_to_c(space_name: str, ctx: EmitCContext) -> str:
    """把 space 名称映射为目标相关的模板参数文本。"""

    return _legacy_emit_c._space_name_to_c(space_name, ctx)


def type_to_c(attr: Any, ctx: EmitCContext) -> str:
    """把 xdsl / DSL 类型映射为 C 侧类型文本。"""

    return _legacy_emit_c._type_to_c(attr, ctx)


def type_to_c_for_target(attr: Any, target: str) -> str:
    """把类型映射为目标相关的 C 侧类型文本。"""

    return _legacy_emit_c._type_to_c_for_target(attr, target)


__all__ = [
    "memory_space_to_c",
    "memory_space_to_c_for_target",
    "space_name_to_c",
    "space_to_c",
    "type_to_c",
    "type_to_c_for_target",
]
