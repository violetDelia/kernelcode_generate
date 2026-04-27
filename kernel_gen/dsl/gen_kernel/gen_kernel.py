"""`gen_kernel(...)` 公开模块入口。

创建者: 小李飞刀
最后一次更改: OpenAI Codex

功能说明:
- 提供 `gen_kernel(obj, ctx)` 的稳定公开入口。
- 单个非函数 op 继续直接委托给本模块绑定的 `emit_c_op(...)`。
- 函数 / module 输入统一委托给内部 `KernelEmitter` 生成完整源码。
- 内部函数级 kernel emitter 实现位于 `kernel_emitter.py`，本文件只承载公开 API。

API 列表:
- `gen_kernel(obj: object, ctx: EmitCContext) -> str`
- `GenKernelError(message: str)`

使用示例:
- from kernel_gen.dsl.gen_kernel import EmitCContext, gen_kernel
- source = gen_kernel(func_op, EmitCContext(config={"target": "cpu"}))

关联文件:
- spec: [spec/dsl/gen_kernel/gen_kernel.md](../../../../spec/dsl/gen_kernel/gen_kernel.md)
- spec: [spec/dsl/gen_kernel/emit.md](../../../../spec/dsl/gen_kernel/emit.md)
- test: [test/dsl/gen_kernel/test_gen_kernel.py](../../../../test/dsl/gen_kernel/test_gen_kernel.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/gen_kernel.py](.)
- 功能实现: [kernel_gen/dsl/gen_kernel/kernel_emitter.py](kernel_emitter.py)
"""

from __future__ import annotations

from . import kernel_emitter as _kernel_emitter
from .emit import emit_c_op
from .emit_context import EmitCContext, EmitCError

GenKernelError = _kernel_emitter.GenKernelError


def gen_kernel(obj: object, ctx: EmitCContext) -> str:
    """生成单个 op 或完整函数/module 的目标源码。"""

    emit_ctx = ctx
    if ctx.config["target"] == "npu_demo":
        emit_config = dict(ctx.config or {})
        emit_config["indent"] = "    "
        emit_ctx = EmitCContext(config=emit_config)
    emitter = _kernel_emitter.KernelEmitter(emit_ctx, emit_op=emit_c_op)
    try:
        source = emitter.emit(obj)
    except EmitCError as exc:
        raise GenKernelError(str(exc)) from exc
    include = emitter.emit_include()
    if include:
        if source:
            return include + source
        return include.rstrip()
    return source


def __getattr__(name: str) -> object:
    if name in {"gen_signature", "gen_body"}:
        raise AttributeError(f"{name} is no longer a public entry; use gen_kernel(...) instead")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["GenKernelError", "gen_kernel"]
