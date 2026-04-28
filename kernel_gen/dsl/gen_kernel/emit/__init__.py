"""`gen_kernel.emit` 公开入口。

创建者: OpenAI Codex
最后修改人: 守护最好的爱莉希雅

功能说明:
- 提供 `emit_c(...)`、`emit_c_op(...)`、`emit_c_value(...)` 三个公开入口。
- 按 `target` 分发节点级 op/value 发射。
- 对 `func.func` / `builtin.module` 复用 [`kernel_gen.dsl.gen_kernel.kernel_emitter.KernelEmitter`](../kernel_emitter.py)。

使用示例:
- from kernel_gen.dsl.gen_kernel.emit import emit_c
- source = emit_c(func_op, EmitCContext())

关联文件:
- spec: [spec/dsl/gen_kernel/emit.md](../../../../spec/dsl/gen_kernel/emit.md)
- test: [test/dsl/gen_kernel/emit/test_emit.py](../../../../test/dsl/gen_kernel/emit/test_emit.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit/__init__.py](.)
"""

from __future__ import annotations
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Operation, SSAValue

from ..emit_context import EmitCContext
from . import cpu as _cpu
from . import npu_demo as _npu_demo

_TARGET_MODULES = {"cpu": _cpu, "npu_demo": _npu_demo}


def _dispatch_target(ctx: EmitCContext, *, for_value: bool = False):
    target_impl = ctx.target_entry(_TARGET_MODULES)
    if target_impl is not None:
        return target_impl
    if not for_value:
        return _cpu
    raise ctx.emit_error("emit_c", "unsupported target")


def emit_c_op(op: Operation, ctx: EmitCContext) -> str:
    """把单个 op 发射为目标相关源码语句。"""

    return _dispatch_target(ctx)._emit_c_op(op, ctx)


def emit_c_value(value: SSAValue, ctx: EmitCContext) -> str:
    """把 SSA value 发射为目标相关右值表达式。"""

    return _dispatch_target(ctx, for_value=True)._emit_c_value(value, ctx)


def emit_c(obj: object, ctx: EmitCContext) -> str:
    """统一发射节点、函数或 module 源码。

    说明:
    - `emit_c(...)` 对 `func.func` / `builtin.module` 返回完整 target 源码，包含必要 include。
    - `gen_kernel(...)` 继续复用同一套 `KernelEmitter.emit_include()` 合同。
    """

    if isinstance(obj, SSAValue):
        return emit_c_value(obj, ctx)
    if isinstance(obj, Operation) and not isinstance(obj, (func.FuncOp, ModuleOp)):
        return emit_c_op(obj, ctx)
    if isinstance(obj, (func.FuncOp, ModuleOp)):
        from ..kernel_emitter import KernelEmitter
        from kernel_gen.dialect.arch import ArchLaunchOp

        emitter = KernelEmitter(ctx, emit_op=emit_c_op)
        try:
            if isinstance(obj, func.FuncOp):
                source = emitter.emit_func(obj)
            else:
                top_ops = list(obj.ops)
                if not top_ops or any(not isinstance(top_op, func.FuncOp) for top_op in top_ops):
                    source = emitter.emit(obj)
                elif ctx.is_target("npu_demo") and any(
                    any(isinstance(inner, ArchLaunchOp) for inner in top_op.body.block.ops)
                    for top_op in top_ops
                ):
                    source = emitter.emit_module(obj)
                else:
                    source = "\n\n".join(emitter.emit_func(top_op) for top_op in top_ops)
            include = emitter.emit_include()
            if include:
                if source:
                    return include + source
                return include.rstrip()
            return source
        except KernelCodeError as exc:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.GEN_KERNEL, str(exc)) from exc
    raise ctx.emit_error("emit_c", f"unsupported emit_c object {type(obj).__name__}")


__all__ = ["emit_c", "emit_c_op", "emit_c_value"]
