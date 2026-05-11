"""`gen_kernel.emit` 公开入口。


功能说明:
- 提供 `emit_c(...)`、`emit_c_op(...)`、`emit_c_value(...)` 三个公开入口。
- 按 `target` 分发节点级 op/value 发射。
- 对 `func.func` 复用 [`kernel_gen.dsl.gen_kernel.kernel_emitter.KernelEmitter`](../kernel_emitter.py)。
- 对 `builtin.module` 优先通过现有 `emit_c_impl(ModuleOp, target=...)` registry 发射。

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
from .register import dispatch_op, dispatch_value, emit_c_impl

EmitCInput: TypeAlias = "SSAValue | Operation | func.FuncOp | ModuleOp"


def _ctx_matches_target(ctx: EmitCContext, targets: tuple[str, ...]) -> bool:
    """通过公开 `target_entry(...)` 判断上下文 target。


    功能说明:
    - 避免在 emit 主链继续扩散直接 target 名分支。
    - 仅服务本文件内保留旧错误语义与内置 ModuleOp handler 选择。

    使用示例:
    - is_builtin = _ctx_matches_target(ctx, ("cpu", "npu_demo"))
    """

    return bool(ctx.target_entry({target: True for target in targets}, default=False))


def emit_c_op(op: Operation, ctx: EmitCContext) -> str:
    """把单个 op 发射为目标相关源码语句。


    功能说明:
    - 只通过当前 target 的 emit registry 分发。
    - unknown target 不回退到 CPU；backend 未加载或未注册 handler 时按公开 gen_kernel 错误失败。

    使用示例:
    - stmt = emit_c_op(op, EmitCContext())
    """

    if isinstance(op, arith.ConstantOp):
        return ""
    dispatched = dispatch_op(op, ctx)
    if dispatched is not None:
        return dispatched
    if not _ctx_matches_target(ctx, ("cpu", "npu_demo")) and op.name in {
        "dma.alloc",
        "dma.load",
        "dma.store",
        "dma.fill",
        "dma.slice",
        "dma.deslice",
        "dma.view",
        "nn.img2col2d",
    }:
        raise ctx.emit_error(op.name, "dma ops are cpu-only")
    raise ctx.emit_error(op.name, "unsupported op")


def emit_c_value(value: SSAValue, ctx: EmitCContext) -> str:
    """把 SSA value 发射为目标相关右值表达式。


    功能说明:
    - 先按当前 target 的 value registry 分发。
    - 未注册 custom target 不回退 CPU value 逻辑。

    使用示例:
    - expr = emit_c_value(value, EmitCContext())
    """

    bound = ctx.lookup_name(value)
    if bound is not None:
        return bound
    dispatched = dispatch_value(value, ctx)
    if dispatched is not None:
        return dispatched
    if not _ctx_matches_target(ctx, ("cpu", "npu_demo")):
        raise ctx.emit_error("emit_c", "unsupported target")
    if isinstance(value, BlockArgument):
        return ctx.create_or_get_name(value)
    if _ctx_matches_target(ctx, ("npu_demo",)) and isinstance(value.type, NnMemoryType):
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


def _emit_module_with_kernel_emitter(obj: ModuleOp, ctx: EmitCContext) -> str:
    """用内置 KernelEmitter 发射 CPU/npu_demo ModuleOp。


    功能说明:
    - 将 CPU/npu_demo 既有 module 行为接入 `emit_c_impl(ModuleOp, target=...)` 注册体系。
    - 该 helper 只服务本文件中的两个内置 ModuleOp handler，不作为跨文件公开入口。

    使用示例:
    - source = _emit_module_with_kernel_emitter(module_op, ctx)
    """

    from ..kernel_emitter import KernelEmitter

    emitter = KernelEmitter(ctx, emit_op=emit_c_op)
    top_ops = list(obj.ops)
    if _ctx_matches_target(ctx, ("npu_demo",)) or any(not isinstance(top_op, func.FuncOp) for top_op in top_ops):
        source = emitter.emit(obj)
    else:
        for top_op in top_ops:
            if any(not isinstance(inner, func.ReturnOp) for inner in top_op.body.block.ops):
                raise ctx.emit_error("builtin.module is only supported for target=npu_demo", "")
        source = "\n\n".join(emitter.emit_func(top_op) for top_op in top_ops)
    include = emitter.emit_include()
    if include:
        if source:
            return include + source
        return include.rstrip()
    return source


@emit_c_impl(ModuleOp, target="cpu")
def _emit_cpu_module(obj: ModuleOp, ctx: EmitCContext) -> str:
    """发射 CPU ModuleOp。


    功能说明:
    - 通过统一 `emit_c_impl(ModuleOp, target="cpu")` handler 承接内置 CPU module 发射。
    - 不新增 `emit_c_module_impl` 平行入口。

    使用示例:
    - source = emit_c(module_op, EmitCContext())
    """

    return _emit_module_with_kernel_emitter(obj, ctx)


@emit_c_impl(ModuleOp, target="npu_demo")
def _emit_npu_demo_module(obj: ModuleOp, ctx: EmitCContext) -> str:
    """发射 npu_demo ModuleOp。


    功能说明:
    - 通过统一 `emit_c_impl(ModuleOp, target="npu_demo")` handler 承接内置 npu_demo module 发射。
    - 继续保持 launch wrapper/body 与普通单函数 module 的既有行为。

    使用示例:
    - source = emit_c(module_op, EmitCContext())
    """

    return _emit_module_with_kernel_emitter(obj, ctx)


def emit_c(obj: EmitCInput, ctx: EmitCContext) -> str:
    """统一发射节点、函数或 module 源码。

    功能说明:
    - `SSAValue` 走 value registry。
    - 普通 `Operation` 走 op registry。
    - `func.func` 继续通过 `KernelEmitter.emit_func(...)` 发射。
    - `builtin.module` 通过 `emit_c_impl(ModuleOp, target=...)` handler 发射，handler 可返回单文件或多文件源码产物。

    使用示例:
    - source = emit_c(module_op, EmitCContext())
    """

    if isinstance(obj, SSAValue):
        return emit_c_value(obj, ctx)
    if isinstance(obj, ModuleOp):
        dispatched = dispatch_op(obj, ctx)
        if dispatched is not None:
            return dispatched
        raise ctx.emit_error("emit_c", "backend_handler_not_found: type=ModuleOp")
    if isinstance(obj, Operation) and not isinstance(obj, func.FuncOp):
        return emit_c_op(obj, ctx)
    if isinstance(obj, func.FuncOp):
        from ..kernel_emitter import KernelEmitter

        emitter = KernelEmitter(ctx, emit_op=emit_c_op)
        try:
            source = emitter.emit_func(obj)
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
