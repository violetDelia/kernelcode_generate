"""`gen_kernel.emit` 公开入口。


功能说明:
- 提供 `emit_c(...)`、`emit_c_op(...)`、`emit_c_value(...)` 三个公开入口。
- 按 `target` 分发节点级 op/value 发射。
- 对 `func.func` / `builtin.module` 复用 [`kernel_gen.dsl.gen_kernel.kernel_emitter.KernelEmitter`](../kernel_emitter.py)。

API 列表:
- `emit_c_op(op: Operation, ctx: EmitCContext) -> str`
- `emit_c_value(value: SSAValue, ctx: EmitCContext) -> str`
- `emit_c(obj: EmitCInput, ctx: EmitCContext) -> str`

使用示例:
- from kernel_gen.dsl.gen_kernel.emit import emit_c
- source = emit_c(func_op, EmitCContext())

关联文件:
- spec: [spec/dsl/gen_kernel/emit.md](../../../../spec/dsl/gen_kernel/emit.md)
- test: [test/dsl/gen_kernel/emit/test_package.py](../../../../test/dsl/gen_kernel/emit/test_package.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit/__init__.py](.)
"""

from __future__ import annotations
from typing import TypeAlias

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

from xdsl.dialects import arith, func
from xdsl.dialects.builtin import FloatAttr, IntAttr, IntegerAttr, ModuleOp
from xdsl.ir import BlockArgument, Operation, SSAValue

from kernel_gen.dialect.nn import NnMemoryType
from ..emit_context import EmitCContext
from . import cpu as _cpu  # noqa: F401
from . import npu_demo as _npu_demo  # noqa: F401
from .register import dispatch_op, dispatch_op_for_target, dispatch_value

EmitCInput: TypeAlias = "SSAValue | Operation | func.FuncOp | ModuleOp"


def emit_c_op(op: Operation, ctx: EmitCContext) -> str:
    """把单个 op 发射为目标相关源码语句。"""

    if isinstance(op, arith.ConstantOp):
        return ""
    if ctx.is_target("cpu") or ctx.is_target("npu_demo"):
        dispatched = dispatch_op(op, ctx)
    else:
        dispatched = dispatch_op_for_target(op, ctx, "cpu")
    if dispatched is not None:
        return dispatched
    raise ctx.emit_error(op.name, "unsupported op")


def emit_c_value(value: SSAValue, ctx: EmitCContext) -> str:
    """把 SSA value 发射为目标相关右值表达式。"""

    bound = ctx.lookup_name(value)
    if bound is not None:
        return bound
    if not ctx.is_target("cpu") and not ctx.is_target("npu_demo"):
        raise ctx.emit_error("emit_c", "unsupported target")
    dispatched = dispatch_value(value, ctx)
    if dispatched is not None:
        return dispatched
    if isinstance(value, BlockArgument):
        return ctx.create_or_get_name(value)
    if ctx.is_target("npu_demo") and isinstance(value.type, NnMemoryType):
        return ctx.create_or_get_name(value)
    owner = value.owner
    if isinstance(owner, arith.ConstantOp):
        literal_value = owner.value
        if isinstance(literal_value, IntegerAttr):
            return str(literal_value.value.data)
        if isinstance(literal_value, IntAttr):
            return str(literal_value.data)
        if isinstance(literal_value, FloatAttr):
            return str(literal_value.value.data)
        raise ctx.emit_error(owner.name, "unsupported constant literal")
    raise ctx.emit_error(owner.name, f"invalid dependency for value {value}")


def emit_c(obj: EmitCInput, ctx: EmitCContext) -> str:
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
