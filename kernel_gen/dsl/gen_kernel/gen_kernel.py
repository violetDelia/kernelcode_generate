"""`gen_kernel(...)` 公开模块入口。

创建者: 小李飞刀
最后一次更改: OpenAI Codex

功能说明:
- 提供 `gen_kernel(obj, ctx)` 的稳定公开入口。
- 提供 `dsl_gen_kernel(fn, *runtime_args, ctx, config=None)` 的 callable 公开入口。
- 单个非函数 op 继续直接委托给本模块绑定的 `emit_c_op(...)`。
- 函数 / module 输入统一委托给内部 `KernelEmitter` 生成完整源码。
- 内部函数级 kernel emitter 实现位于 `kernel_emitter.py`，本文件只承载公开 API。

API 列表:
- `gen_kernel(obj: object, ctx: EmitCContext) -> str`
- `dsl_gen_kernel(fn: Callable[..., object], *runtime_args: object, ctx: EmitCContext, config: dict[str, object] | None = None) -> str`
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

from collections.abc import Callable

from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp

from kernel_gen.dsl.mlir_gen import mlir_gen

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


def _resolve_root_func(module: ModuleOp, fn_name: str) -> func.FuncOp:
    """从 `mlir_gen(...)` 结果里定位 callable 对应的根函数。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 优先按 callable 的 `__name__` 精确匹配 `func.func`。
    - 若 module 中只有一个 `func.func`，则直接把它视作根函数。
    - 若找不到公开根函数，统一抛 `GenKernelError`，避免 `dsl_gen_kernel(...)` 静默选错 callee。

    使用示例:
    - module = mlir_gen(add_scalar, 1, 2)
    - root_func = _resolve_root_func(module, "add_scalar")

    关联文件:
    - spec: [spec/dsl/gen_kernel/gen_kernel.md](../../../../spec/dsl/gen_kernel/gen_kernel.md)
    - test: [test/dsl/gen_kernel/test_gen_kernel.py](../../../../test/dsl/gen_kernel/test_gen_kernel.py)
    - 功能实现: [kernel_gen/dsl/gen_kernel/gen_kernel.py](.)
    """

    func_ops = [op for op in module.body.block.ops if isinstance(op, func.FuncOp)]
    for func_op in func_ops:
        if func_op.sym_name.data == fn_name:
            return func_op
    if len(func_ops) == 1:
        return func_ops[0]
    raise GenKernelError(f"dsl_gen_kernel({fn_name}): root func not found")


def dsl_gen_kernel(
    fn: Callable[..., object],
    *runtime_args: object,
    ctx: EmitCContext,
    config: dict[str, object] | None = None,
) -> str:
    """通过公开 `mlir_gen(...) + gen_kernel(...)` 链路生成 callable 源码。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 只接受 Python DSL callable 及其运行时参数。
    - 先通过公开 `mlir_gen(...)` 生成 `builtin.module`，再选择 callable 对应的根 `func.func` 走公开 `gen_kernel(...)`。
    - 不在本文件外额外直连 parser、module-builder 或 kernel emitter 私有 helper。

    使用示例:
    - source = dsl_gen_kernel(add_scalar, 1, 2, ctx=EmitCContext(config={"target": "cpu"}))

    关联文件:
    - spec: [spec/dsl/gen_kernel/gen_kernel.md](../../../../spec/dsl/gen_kernel/gen_kernel.md)
    - test: [test/dsl/gen_kernel/test_gen_kernel.py](../../../../test/dsl/gen_kernel/test_gen_kernel.py)
    - 功能实现: [kernel_gen/dsl/gen_kernel/gen_kernel.py](.)
    """

    module = mlir_gen(fn, *runtime_args, config=config)
    root_func = _resolve_root_func(module, getattr(fn, "__name__", "<anonymous>"))
    return gen_kernel(root_func, ctx)


def __getattr__(name: str) -> object:
    if name in {"gen_signature", "gen_body"}:
        raise AttributeError(f"{name} is no longer a public entry; use gen_kernel(...) instead")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["GenKernelError", "dsl_gen_kernel", "gen_kernel"]
