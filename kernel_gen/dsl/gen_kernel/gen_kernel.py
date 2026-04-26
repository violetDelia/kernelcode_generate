"""`gen_kernel(...)` 公开模块入口。

创建者: 小李飞刀
最后一次更改: OpenAI Codex

功能说明:
- 提供 `gen_kernel(obj, ctx)` 的稳定公开入口。
- 提供 `dsl_gen_kernel(fn, *runtime_args, ctx, config=None)` 的 callable DSL 公开入口。
- 单个非函数 op 继续直接委托给本模块绑定的 `emit_c_op(...)`。
- 函数 / module 输入统一委托给内部 `KernelEmitter` 生成完整源码。
- 内部函数级 kernel emitter 实现位于 `kernel_emitter.py`，本文件只承载公开 API。

API 列表:
- `gen_kernel(obj: object, ctx: EmitCContext) -> str`
- `dsl_gen_kernel(fn: Callable[..., object], *runtime_args: object, ctx: EmitCContext, config: dict[str, object] | None = None) -> str`
- `GenKernelError(message: str)`

使用示例:
- from kernel_gen.dsl.gen_kernel import EmitCContext, dsl_gen_kernel, gen_kernel
- source = gen_kernel(func_op, EmitCContext(target="cpu"))
- source = dsl_gen_kernel(add_kernel, 3, 4, ctx=EmitCContext(target="cpu"))

关联文件:
- spec: [spec/dsl/gen_kernel/gen_kernel.md](../../../../spec/dsl/gen_kernel/gen_kernel.md)
- spec: [spec/dsl/gen_kernel/emit.md](../../../../spec/dsl/gen_kernel/emit.md)
- test: [test/dsl/gen_kernel/test_gen_kernel.py](../../../../test/dsl/gen_kernel/test_gen_kernel.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/gen_kernel.py](.)
- 功能实现: [kernel_gen/dsl/gen_kernel/kernel_emitter.py](kernel_emitter.py)
"""

from __future__ import annotations

from collections.abc import Callable

from xdsl.dialects import func

from kernel_gen.dsl.mlir_gen import mlir_gen

from . import kernel_emitter as _kernel_emitter
from .emit import emit_c_op
from .emit_context import EmitCContext, EmitCError

GenKernelError = _kernel_emitter.GenKernelError


def gen_kernel(obj: object, ctx: EmitCContext) -> str:
    """生成单个 op 或完整函数/module 的目标源码。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 维持 `op` / `func.func` / 受控 `builtin.module` 的稳定公开源码生成入口。
    - 普通 op 继续走当前文件绑定的 `emit_c_op(...)`。
    - 函数 / module 继续复用 `KernelEmitter` 的既有组装逻辑，不复制第二套 emitter。

    使用示例:
    - source = gen_kernel(func_op, EmitCContext(target="cpu"))

    关联文件:
    - spec: [spec/dsl/gen_kernel/gen_kernel.md](../../../../spec/dsl/gen_kernel/gen_kernel.md)
    - test: [test/dsl/gen_kernel/test_gen_kernel.py](../../../../test/dsl/gen_kernel/test_gen_kernel.py)
    - 功能实现: [kernel_gen/dsl/gen_kernel/gen_kernel.py](.)
    """

    emit_ctx = ctx
    if ctx.target == "npu_demo":
        emit_ctx = EmitCContext(
            target=ctx.target,
            indent="    ",
            naming=ctx.naming,
            type_converter=ctx.type_converter,
            config=dict(ctx.config or {}),
        )
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


def dsl_gen_kernel(
    fn: Callable[..., object],
    *runtime_args: object,
    ctx: EmitCContext,
    config: dict[str, object] | None = None,
) -> str:
    """从 DSL callable 直接生成目标源码。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 只承接 Python DSL callable 公开入口，不接管既有 IR 级消费者。
    - 固定复用公开 `mlir_gen(...) + gen_kernel(...)` 链路，避免复制 parser / emitter 逻辑。
    - `config` 原样传给公开 `mlir_gen(...)`，其余源码生成行为继续由 `gen_kernel(...)` 统一承接。
    - `target="npu_demo"` 继续把完整 `builtin.module` 交给既有 module 路径；其余 target 则只消费 `mlir_gen(...)` 产物中的根 `func.func`。

    使用示例:
    - source = dsl_gen_kernel(add_kernel, 3, 4, ctx=EmitCContext(target="cpu"))

    关联文件:
    - spec: [spec/dsl/gen_kernel/gen_kernel.md](../../../../spec/dsl/gen_kernel/gen_kernel.md)
    - test: [test/dsl/gen_kernel/test_gen_kernel.py](../../../../test/dsl/gen_kernel/test_gen_kernel.py)
    - 功能实现: [kernel_gen/dsl/gen_kernel/gen_kernel.py](.)
    """

    module = mlir_gen(fn, *runtime_args, config=config)
    emit_input: object = module
    if ctx.target != "npu_demo":
        root_func = next((op for op in module.body.block.ops if isinstance(op, func.FuncOp)), None)
        if root_func is not None:
            emit_input = root_func
    return gen_kernel(emit_input, ctx)


def __getattr__(name: str) -> object:
    if name in {"gen_signature", "gen_body"}:
        raise AttributeError(f"{name} is no longer a public entry; use gen_kernel(...) instead")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["GenKernelError", "gen_kernel", "dsl_gen_kernel"]
