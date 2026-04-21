"""EmitC registry helpers for the package-style public entry.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 维护 `emit_c_op` / `emit_c_value` 的注册表与装饰器。
- 允许 dialect 模块按 op/value 类型挂接片段发射实现，再由包根统一调度。
- 先做注册分发，再允许回落到旧版实现，保证 S2 阶段输出与历史行为一致。

使用示例:
- from kernel_gen.dsl.gen_kernel.emit_c.register import emit_c_impl, dispatch_op
- @emit_c_impl(SomeOp)
- def _emit_some_op(op, ctx): ...

关联文件:
- spec: [spec/dsl/emit_c.md](../../../../spec/dsl/emit_c.md)
- spec: [spec/dsl/gen_kernel.md](../../../../spec/dsl/gen_kernel.md)
- test: [test/dsl/test_emit_c.py](../../../../test/dsl/test_emit_c.py)
- test: [test/dsl/test_gen_kernel.py](../../../../test/dsl/test_gen_kernel.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit_c/](.)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xdsl.ir import Operation, SSAValue

from ..emit_context import EmitCContext

OpHandler = Callable[[Operation, EmitCContext], str]
ValueHandler = Callable[[SSAValue, EmitCContext], str]

_OP_REGISTRY: dict[type[Any], OpHandler] = {}
_VALUE_REGISTRY: dict[type[Any], ValueHandler] = {}


def _register(registry: dict[type[Any], Callable[..., str]], *types: type[Any]) -> Callable[[Callable[..., str]], Callable[..., str]]:
    """把处理函数登记到注册表中。"""

    def decorator(func: Callable[..., str]) -> Callable[..., str]:
        for typ in types:
            registry[typ] = func
        return func

    return decorator


def emit_c_impl(*types: type[Any]) -> Callable[[OpHandler], OpHandler]:
    """注册一个 `emit_c_op` 处理函数。"""

    return _register(_OP_REGISTRY, *types)


def emit_c_value_impl(*types: type[Any]) -> Callable[[ValueHandler], ValueHandler]:
    """注册一个 `emit_c_value` 处理函数。"""

    return _register(_VALUE_REGISTRY, *types)


def dispatch_op(op: Operation, ctx: EmitCContext) -> str | None:
    """按 op 类层级查找已注册的发射函数。"""

    for cls in type(op).__mro__:
        handler = _OP_REGISTRY.get(cls)
        if handler is not None:
            return handler(op, ctx)
    return None


def dispatch_value(value: SSAValue, ctx: EmitCContext) -> str | None:
    """按 value owner 类层级查找已注册的发射函数。"""

    owner = value.owner
    for cls in type(owner).__mro__:
        handler = _VALUE_REGISTRY.get(cls)
        if handler is not None:
            return handler(value, ctx)
    return None


def registered_op_types() -> tuple[type[Any], ...]:
    """返回当前已注册的 op 类型快照。"""

    return tuple(_OP_REGISTRY)


def registered_value_types() -> tuple[type[Any], ...]:
    """返回当前已注册的 value owner 类型快照。"""

    return tuple(_VALUE_REGISTRY)


__all__ = [
    "dispatch_op",
    "dispatch_value",
    "emit_c_impl",
    "emit_c_value_impl",
    "registered_op_types",
    "registered_value_types",
]
