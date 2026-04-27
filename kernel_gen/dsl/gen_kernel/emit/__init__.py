"""`gen_kernel.emit` 公开入口。

创建者: OpenAI Codex
最后修改人: OpenAI Codex

功能说明:
- 提供 `emit_c(...)`、`emit_c_op(...)`、`emit_c_value(...)` 三个公开入口。
- 按 `target` 分发节点级 op/value 发射。
- 对 `func.func` / `builtin.module` 复用 [`kernel_gen.dsl.gen_kernel.kernel_emitter.KernelEmitter`](../kernel_emitter.py)。

使用示例:
- from kernel_gen.dsl.gen_kernel.emit import emit_c
- source = emit_c(func_op, EmitCContext(config={"target": "cpu"}))

关联文件:
- spec: [spec/dsl/gen_kernel/emit.md](../../../../spec/dsl/gen_kernel/emit.md)
- test: [test/dsl/gen_kernel/emit/test_emit.py](../../../../test/dsl/gen_kernel/emit/test_emit.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit/__init__.py](.)
"""

from __future__ import annotations

from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Operation, SSAValue

from ..emit_context import EmitCContext, EmitCError
from . import cpu as _cpu
from . import npu_demo as _npu_demo


def _dispatch_target(target: str, *, for_value: bool = False):
    if target == "cpu":
        return _cpu
    if target == "npu_demo":
        return _npu_demo
    if not for_value:
        return _cpu
    raise EmitCError(f"target={target}: unsupported target")


def emit_c_op(op: Operation, ctx: EmitCContext) -> str:
    """把单个 op 发射为目标相关源码语句。"""

    return _dispatch_target(ctx.config["target"])._emit_c_op(op, ctx)


def emit_c_value(value: SSAValue, ctx: EmitCContext) -> str:
    """把 SSA value 发射为目标相关右值表达式。"""

    return _dispatch_target(ctx.config["target"], for_value=True)._emit_c_value(value, ctx)


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
        from ..kernel_emitter import GenKernelError, KernelEmitter
        from kernel_gen.dialect.arch import ArchLaunchOp

        emit_ctx = ctx
        if ctx.config["target"] == "npu_demo":
            emit_ctx = EmitCContext(config=dict(ctx.config))
        emitter = KernelEmitter(emit_ctx, emit_op=emit_c_op)
        try:
            if isinstance(obj, func.FuncOp):
                source = emitter.emit_func(obj)
            else:
                top_ops = list(obj.ops)
                if not top_ops or any(not isinstance(top_op, func.FuncOp) for top_op in top_ops):
                    source = emitter.emit(obj)
                elif ctx.config["target"] == "npu_demo" and any(
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
        except EmitCError as exc:
            raise GenKernelError(str(exc).replace(f"target={ctx.config['target']}: ", "")) from exc
    raise EmitCError(f"target={ctx.config['target']}: unsupported emit_c object {type(obj).__name__}")


__all__ = ["emit_c", "emit_c_op", "emit_c_value"]
