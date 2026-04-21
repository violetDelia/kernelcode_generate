"""Package-style EmitC registry and public entry points.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 汇总 `emit_c_op` / `emit_c_value` / `emit_c` 的包内公开入口。
- 通过注册表挂接各 dialect 的节点级发射实现，并在必要时回落旧实现。
- 为 `kernel_gen.dsl.gen_kernel` 包根提供稳定的 `emit_c` 主入口。
- 函数 / module 级源码组装迁入 `function.py`，避免继续把完整源码路径藏在兼容包装层里。

使用示例:
- from kernel_gen.dsl.gen_kernel.emit_c import EmitCContext, emit_c
- source = emit_c(func_op, EmitCContext(target="cpu"))

关联文件:
- spec: [spec/dsl/emit_c.md](../../../../spec/dsl/emit_c.md)
- spec: [spec/dsl/gen_kernel.md](../../../../spec/dsl/gen_kernel.md)
- test: [test/dsl/test_emit_c.py](../../../../test/dsl/test_emit_c.py)
- test: [test/dsl/test_gen_kernel.py](../../../../test/dsl/test_gen_kernel.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit_c/](.)
"""

from __future__ import annotations

from typing import Any

from xdsl.ir import BlockArgument, Operation, SSAValue

from .._legacy import load_legacy_emit_c_module
from ..emit_context import EmitCContext, EmitCError
from . import function as _function_module
from .register import (
    dispatch_op,
    dispatch_value,
    emit_c_impl,
    emit_c_value_impl,
    registered_op_types,
    registered_value_types,
)
from .types import (
    memory_space_to_c,
    memory_space_to_c_for_target,
    space_name_to_c,
    space_to_c,
    type_to_c,
    type_to_c_for_target,
)

# 触发各 dialect 的注册副作用。
from . import arith as _arith  # noqa: F401
from . import arch as _arch  # noqa: F401
from . import dma as _dma  # noqa: F401
from . import kernel as _kernel  # noqa: F401
from . import nn as _nn  # noqa: F401
from . import scf as _scf  # noqa: F401
from . import symbol as _symbol  # noqa: F401


def _call_legacy_emit_c_op(op: Operation, ctx: EmitCContext) -> str:
    legacy_emit_c = load_legacy_emit_c_module()
    return legacy_emit_c.emit_c_op(op, ctx)


def _call_legacy_emit_c_value(value: SSAValue, ctx: EmitCContext) -> str:
    legacy_emit_c = load_legacy_emit_c_module()
    return legacy_emit_c.emit_c_value(value, ctx)


def emit_c_op(op: Operation, ctx: EmitCContext) -> str:
    """把单个 MLIR op 生成为目标后端的语句或语句块文本。"""

    stmt = dispatch_op(op, ctx)
    if stmt is not None:
        return stmt
    return _call_legacy_emit_c_op(op, ctx)


def emit_c_value(value: SSAValue, ctx: EmitCContext) -> str:
    """把 SSA value 生成为可嵌入右值位置的表达式文本。"""

    bound = ctx.lookup_name(value)
    if bound is not None:
        return bound
    if isinstance(value, BlockArgument):
        return ctx.bind_name(value, f"arg{value.index}")
    expr = dispatch_value(value, ctx)
    if expr is not None:
        return expr
    return _call_legacy_emit_c_value(value, ctx)


def emit_c(obj: object, ctx: EmitCContext) -> str:
    """统一发射 DSL 源码片段或完整函数源码。"""

    if isinstance(obj, SSAValue):
        return emit_c_value(obj, ctx)
    return _function_module.emit_c_source(obj, ctx, emit_c_op, emit_c_value)


__all__ = [
    "EmitCContext",
    "EmitCError",
    "dispatch_op",
    "dispatch_value",
    "emit_c",
    "emit_c_impl",
    "emit_c_op",
    "emit_c_value",
    "emit_c_value_impl",
    "memory_space_to_c",
    "memory_space_to_c_for_target",
    "registered_op_types",
    "registered_value_types",
    "space_name_to_c",
    "space_to_c",
    "type_to_c",
    "type_to_c_for_target",
]
