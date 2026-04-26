"""兼容保留的 `kernel_gen.dsl.gen_kernel` 包根入口。

创建者: 小李飞刀
最后一次更改: OpenAI Codex

功能说明:
- 以包根形式汇总 `gen_kernel` 的公开入口、上下文对象与节点级片段发射接口。
- 当前 `kernel_gen.dsl.gen_kernel` 就是 canonical 公开路径。
- 包根仅承认 `gen_kernel(...)` / `emit_c(...)` / `emit_c_op(...)` / `emit_c_value(...)` 这组稳定公开入口。

使用示例:
- from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c, gen_kernel
- source = emit_c(func_op, EmitCContext(target="cpu"))

关联文件:
- spec: [spec/dsl/gen_kernel/emit.md](../../../spec/dsl/gen_kernel/emit.md)
- spec: [spec/dsl/gen_kernel/gen_kernel.md](../../../spec/dsl/gen_kernel/gen_kernel.md)
- test: [test/dsl/gen_kernel/emit/test_emit.py](../../../test/dsl/gen_kernel/emit/test_emit.py)
- test: [test/dsl/gen_kernel/test_gen_kernel.py](../../../test/dsl/gen_kernel/test_gen_kernel.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/__init__.py](.)
"""

from __future__ import annotations

from .emit import emit_c, emit_c_op, emit_c_value
from .emit_context import EmitCContext, EmitCError
from .gen_kernel import GenKernelError, KernelEmitter, gen_kernel


def __getattr__(name: str) -> object:
    if name in {"gen_signature", "gen_body"}:
        raise AttributeError(f"{name} is no longer a public entry; use gen_kernel(...) instead")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "GenKernelError",
    "KernelEmitter",
    "gen_kernel",
    "EmitCContext",
    "EmitCError",
    "emit_c",
    "emit_c_op",
    "emit_c_value",
]
