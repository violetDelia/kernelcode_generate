"""EmitC context re-export for the package-style `gen_kernel` entry.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 把旧版片段发射模块中的 `EmitCContext` / `EmitCError` 作为包内上下文模块导出。
- 为 `kernel_gen.dsl.gen_kernel` 包根提供稳定的上下文入口，方便外部按新路径导入。

使用示例:
- from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext
- ctx = EmitCContext(target="cpu")

关联文件:
- spec: [spec/dsl/emit_c.md](../../../spec/dsl/emit_c.md)
- test: [test/dsl/test_emit_c.py](../../../test/dsl/test_emit_c.py)
- 功能实现: [kernel_gen/dsl/emit_c.py](../emit_c.py)
"""

from __future__ import annotations

from ._legacy import load_legacy_emit_c_module

_legacy_emit_c = load_legacy_emit_c_module()

EmitCContext = _legacy_emit_c.EmitCContext
EmitCError = _legacy_emit_c.EmitCError

__all__ = ["EmitCContext", "EmitCError"]
