"""Emit registry helpers for `gen_kernel.emit`.


功能说明:
- 定义 `emit` 层公开注册器与 dispatch 合同。
- 统一 target-specific op / value / type / attr / include / name 分发入口。

API 列表:
- `emit_c_impl(*types: type[Any], target: str | None = None) -> Callable[[OpHandler], OpHandler]`
- `emit_c_value_impl(*types: type[Any], target: str | None = None) -> Callable[[ValueHandler], ValueHandler]`
- `emit_c_type_impl(*types: type[Any], target: str) -> Callable[[TypeHandler], TypeHandler]`
- `emit_c_attr_impl(*types: type[Any], target: str) -> Callable[[AttrHandler], AttrHandler]`
- `emit_c_include_impl(target: str) -> Callable[[IncludeHandler], IncludeHandler]`
- `emit_c_name_impl(*types: type[Any], target: str) -> Callable[[NameHandler], NameHandler]`
- `dispatch_op(op: Operation, ctx: EmitCContext) -> str | None`
- `dispatch_op_for_target(op: Operation, ctx: EmitCContext, target: str) -> str | None`
- `dispatch_value(value: SSAValue, ctx: EmitCContext) -> str | None`
- `dispatch_type(attr: Any, ctx: EmitCContext) -> str | None`
- `dispatch_attr(attr: Any, ctx: EmitCContext) -> str | None`
- `dispatch_include(ctx: EmitCContext) -> str`
- `dispatch_name(value: SSAValue, ctx: EmitCContext) -> str | None`

使用示例:
- from kernel_gen.dsl.gen_kernel.emit.register import dispatch_op
- stmt = dispatch_op(op, ctx)

关联文件:
- spec: [spec/dsl/gen_kernel/emit/register.md](../../../../spec/dsl/gen_kernel/emit/register.md)
- test: [test/dsl/gen_kernel/emit/test_package.py](../../../../test/dsl/gen_kernel/emit/test_package.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit/register.py](.)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xdsl.ir import BlockArgument
from xdsl.ir import Operation, SSAValue

from ..emit_context import EmitCContext

OpHandler = Callable[[Operation, EmitCContext], str]
ValueHandler = Callable[[SSAValue, EmitCContext], str]
TypeHandler = Callable[[Any, EmitCContext], str]
AttrHandler = Callable[[Any, EmitCContext], str]
IncludeHandler = Callable[[EmitCContext], str]
NameHandler = Callable[[SSAValue, EmitCContext], str | None]

_OP_REGISTRY: dict[type[Any], OpHandler] = {}
_VALUE_REGISTRY: dict[type[Any], ValueHandler] = {}
_TARGET_OP_REGISTRY: dict[str, dict[type[Any], OpHandler]] = {}
_TARGET_VALUE_REGISTRY: dict[str, dict[type[Any], ValueHandler]] = {}
_TARGET_TYPE_REGISTRY: dict[str, dict[type[Any], TypeHandler]] = {}
_TARGET_ATTR_REGISTRY: dict[str, dict[type[Any], AttrHandler]] = {}
_TARGET_INCLUDE_REGISTRY: dict[str, IncludeHandler] = {}
_TARGET_NAME_REGISTRY: dict[str, dict[type[Any], NameHandler]] = {}


def emit_c_impl(*types: type[Any], target: str | None = None) -> Callable[[OpHandler], OpHandler]:
    def decorator(func: OpHandler) -> OpHandler:
        if target is None:
            for typ in types:
                _OP_REGISTRY[typ] = func
        else:
            scoped = _TARGET_OP_REGISTRY.setdefault(target, {})
            for typ in types:
                scoped[typ] = func
        return func

    return decorator


def emit_c_value_impl(*types: type[Any], target: str | None = None) -> Callable[[ValueHandler], ValueHandler]:
    def decorator(func: ValueHandler) -> ValueHandler:
        if target is None:
            for typ in types:
                _VALUE_REGISTRY[typ] = func
        else:
            scoped = _TARGET_VALUE_REGISTRY.setdefault(target, {})
            for typ in types:
                scoped[typ] = func
        return func

    return decorator


def emit_c_type_impl(*types: type[Any], target: str) -> Callable[[TypeHandler], TypeHandler]:
    def decorator(func: TypeHandler) -> TypeHandler:
        scoped = _TARGET_TYPE_REGISTRY.setdefault(target, {})
        for typ in types:
            scoped[typ] = func
        return func

    return decorator


def emit_c_attr_impl(*types: type[Any], target: str) -> Callable[[AttrHandler], AttrHandler]:
    def decorator(func: AttrHandler) -> AttrHandler:
        scoped = _TARGET_ATTR_REGISTRY.setdefault(target, {})
        for typ in types:
            scoped[typ] = func
        return func

    return decorator


def emit_c_include_impl(*, target: str) -> Callable[[IncludeHandler], IncludeHandler]:
    def decorator(func: IncludeHandler) -> IncludeHandler:
        _TARGET_INCLUDE_REGISTRY[target] = func
        return func

    return decorator


def emit_c_name_impl(*types: type[Any], target: str) -> Callable[[NameHandler], NameHandler]:
    def decorator(func: NameHandler) -> NameHandler:
        scoped = _TARGET_NAME_REGISTRY.setdefault(target, {})
        for typ in types:
            scoped[typ] = func
        return func

    return decorator


def dispatch_op(op: Operation, ctx: EmitCContext) -> str | None:
    target_registry = ctx.target_entry(_TARGET_OP_REGISTRY, {})
    return _dispatch_op_with_registry(op, ctx, target_registry)


def dispatch_op_for_target(op: Operation, ctx: EmitCContext, target: str) -> str | None:
    """按显式 target 名称分发 op。


    功能说明:
    - 供根级 emit 入口保留历史 unknown target -> cpu 诊断路径。
    - 不暴露 target 实现模块中的私有 helper。

    使用示例:
    - dispatch_op_for_target(op, ctx, "cpu")

    关联文件:
    - spec: spec/dsl/gen_kernel/emit/register.md
    - test: test/dsl/gen_kernel/emit/test_package.py
    - 功能实现: kernel_gen/dsl/gen_kernel/emit/register.py
    """

    return _dispatch_op_with_registry(op, ctx, _TARGET_OP_REGISTRY.get(target, {}))


def _dispatch_op_with_registry(
    op: Operation,
    ctx: EmitCContext,
    target_registry: dict[type[Any], OpHandler],
) -> str | None:
    for cls in type(op).__mro__:
        handler = target_registry.get(cls)
        if handler is not None:
            return handler(op, ctx)
        handler = _OP_REGISTRY.get(cls)
        if handler is not None:
            return handler(op, ctx)
    return None


def dispatch_value(value: SSAValue, ctx: EmitCContext) -> str | None:
    target_registry = ctx.target_entry(_TARGET_VALUE_REGISTRY, {})
    if isinstance(value, BlockArgument):
        for cls in type(value).__mro__:
            handler = target_registry.get(cls)
            if handler is not None:
                return handler(value, ctx)
            handler = _VALUE_REGISTRY.get(cls)
            if handler is not None:
                return handler(value, ctx)
        return None
    owner = value.owner
    for cls in type(owner).__mro__:
        handler = target_registry.get(cls)
        if handler is not None:
            return handler(value, ctx)
        handler = _VALUE_REGISTRY.get(cls)
        if handler is not None:
            return handler(value, ctx)
    return None


def dispatch_type(attr: Any, ctx: EmitCContext) -> str | None:
    target_registry = ctx.target_entry(_TARGET_TYPE_REGISTRY, {})
    for cls in type(attr).__mro__:
        handler = target_registry.get(cls)
        if handler is not None:
            return handler(attr, ctx)
    return None


def dispatch_attr(attr: Any, ctx: EmitCContext) -> str | None:
    target_registry = ctx.target_entry(_TARGET_ATTR_REGISTRY, {})
    for cls in type(attr).__mro__:
        handler = target_registry.get(cls)
        if handler is not None:
            return handler(attr, ctx)
    return None


def dispatch_include(ctx: EmitCContext) -> str:
    handler = ctx.target_entry(_TARGET_INCLUDE_REGISTRY)
    if handler is None:
        return ""
    return handler(ctx)


def dispatch_name(value: SSAValue, ctx: EmitCContext) -> str | None:
    target_registry = ctx.target_entry(_TARGET_NAME_REGISTRY, {})
    if isinstance(value, BlockArgument):
        for cls in type(value).__mro__:
            handler = target_registry.get(cls)
            if handler is not None:
                return handler(value, ctx)
        return None
    owner = value.owner
    for cls in type(owner).__mro__:
        handler = target_registry.get(cls)
        if handler is not None:
            return handler(value, ctx)
    return None

__all__ = [
    "dispatch_attr",
    "dispatch_include",
    "dispatch_name",
    "dispatch_op",
    "dispatch_op_for_target",
    "dispatch_type",
    "dispatch_value",
    "emit_c_attr_impl",
    "emit_c_include_impl",
    "emit_c_name_impl",
    "emit_c_impl",
    "emit_c_value_impl",
    "emit_c_type_impl",
]
