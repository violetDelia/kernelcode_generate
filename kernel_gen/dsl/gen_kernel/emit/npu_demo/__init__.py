"""`target=npu_demo` 的按 dialect 注册 emitter 入口。

创建者: OpenAI Codex
最后一次更改: OpenAI Codex

功能说明:
- 聚合 `arch/dma/kernel/nn/symbol/tuner/type` 各子目录注册的 emitter。
- 为根级 `emit` 分发层提供 `npu_demo` target 的内部 op/value 发射实现。

使用示例:
- `_emit_c_op(op, ctx)`
- `_emit_c_value(value, ctx)`

关联文件:
- spec: [`spec/dsl/gen_kernel/emit.md`](spec/dsl/gen_kernel/emit.md)
- test: [`test/dsl/gen_kernel/emit/test_emit.py`](test/dsl/gen_kernel/emit/test_emit.py)
- 功能实现: [`kernel_gen/dsl/gen_kernel/emit/npu_demo/__init__.py`](kernel_gen/dsl/gen_kernel/emit/npu_demo/__init__.py)
"""

from __future__ import annotations

from xdsl.dialects import arith
from xdsl.ir import BlockArgument
from xdsl.ir import Operation, SSAValue

from kernel_gen.dialect.nn import NnMemoryType

from ...emit_context import EmitCContext, EmitCError
from ..register import dispatch_op, dispatch_value
from . import arch as _arch  # noqa: F401
from . import dma as _dma  # noqa: F401
from . import include as _include  # noqa: F401
from . import kernel as _kernel  # noqa: F401
from . import name as _name  # noqa: F401
from . import nn as _nn  # noqa: F401
from . import symbol as _symbol  # noqa: F401
from . import tuner as _tuner  # noqa: F401
from . import type as _type  # noqa: F401


def _format_literal(op: arith.ConstantOp, ctx: EmitCContext) -> str:
    value = op.value
    if hasattr(value, "value") and hasattr(value.value, "data"):
        return str(value.value.data)
    if hasattr(value, "data"):
        return str(value.data)
    raise EmitCError(f"target={ctx.config['target']}: {op.name}: unsupported constant literal")


def _emit_c_op(op: Operation, ctx: EmitCContext) -> str:
    if isinstance(op, arith.ConstantOp):
        return ""
    dispatched = dispatch_op(op, ctx)
    if dispatched is not None:
        return dispatched
    raise EmitCError(f"target={ctx.config['target']}: {op.name}: unsupported op")


def _emit_c_value(value: SSAValue, ctx: EmitCContext) -> str:
    bound = ctx.lookup_name(value)
    if bound is not None:
        return bound
    if isinstance(value, BlockArgument):
        return ctx.create_or_get_name(value)
    if isinstance(value.type, NnMemoryType):
        return ctx.create_or_get_name(value)
    owner = value.owner
    if isinstance(owner, arith.ConstantOp):
        return _format_literal(owner, ctx)
    dispatched = dispatch_value(value, ctx)
    if dispatched is not None:
        return dispatched
    raise EmitCError(f"target={ctx.config['target']}: {owner.name}: invalid dependency for value {value}")


__all__: list[str] = []
