"""Emit registry helpers for `gen_kernel.emit`.


功能说明:
- 定义 `emit` 层公开注册器与 dispatch 合同。
- 统一 target-specific op / value / type / attr / include / name 分发入口。
- 按 target registry 自动加载 `kernel_gen.dsl.gen_kernel.emit.<target>` backend 模块。

API 列表:
- `emit_c_impl(*types: type[Any], target: str | None = None, override: bool = False) -> Callable[[OpHandler], OpHandler]`
- `emit_c_value_impl(*types: type[Any], target: str | None = None, override: bool = False) -> Callable[[ValueHandler], ValueHandler]`
- `emit_c_type_impl(*types: type[Any], target: str, override: bool = False) -> Callable[[TypeHandler], TypeHandler]`
- `emit_c_attr_impl(*types: type[Any], target: str, override: bool = False) -> Callable[[AttrHandler], AttrHandler]`
- `emit_c_include_impl(*, target: str, override: bool = False) -> Callable[[IncludeHandler], IncludeHandler]`
- `emit_c_name_impl(*types: type[Any], target: str, override: bool = False) -> Callable[[NameHandler], NameHandler]`
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

from collections.abc import Mapping
from collections.abc import Callable
import importlib
import re
from typing import Any

from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import BlockArgument
from xdsl.ir import Operation, SSAValue

from kernel_gen.core.config import get_target
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.target import registry as target_registry
from ..emit_context import EmitCContext

SourceProduct = str | Mapping[str, str]
OpHandler = Callable[[Operation, EmitCContext], SourceProduct]
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
_LOADED_BACKENDS: set[str] = {"cpu", "npu_demo"}
_TARGET_NAME_PATTERN = re.compile(r"^[a-z0-9_]+$")
_BUNDLE_MARKER_PREFIX = "// __KG_BUNDLE_FILE__:"


def _emit_registry_error(message: str) -> KernelCodeError:
    """构造 emit registry 的稳定合同错误。


    功能说明:
    - 将 backend loader、重复注册与 source product 错误统一归入 gen_kernel 合同错误。
    - 仅供本文件内部注册和 dispatch 逻辑使用。

    使用示例:
    - raise _emit_registry_error("backend_not_found: target=custom")
    """

    return KernelCodeError(ErrorKind.CONTRACT, ErrorModule.GEN_KERNEL, message)


def _validate_target_name(target: str) -> None:
    """校验 backend target 名称。


    功能说明:
    - 约束 target 名称只能由小写字母、数字和下划线组成。
    - 拒绝路径、大小写变体、空值和带分隔符名称。

    使用示例:
    - _validate_target_name("dummy_generic")
    """

    if not isinstance(target, str) or not _TARGET_NAME_PATTERN.fullmatch(target):
        raise _emit_registry_error("invalid target name")


def _ensure_registered_target(target: str) -> None:
    """确认 target 已通过公开 target registry 注册。


    功能说明:
    - 只通过 `target_registry.get_target_hardware(...)` 公开入口确认 target 存在。
    - 不读取 target registry 的内部字典。

    使用示例:
    - _ensure_registered_target("cpu")
    """

    try:
        target_registry.get_target_hardware(target, "__backend_probe__")
    except ValueError as exc:
        raise _emit_registry_error(f"backend_not_found: target not registered: {target}") from exc


def _is_registered_target(target: str) -> bool:
    """判断 target 是否已通过公开 target registry 注册。


    功能说明:
    - 仅用于 backend auto-load 的分支选择。
    - 不抛出 backend contract 错误；未注册时返回 `False`。

    使用示例:
    - registered = _is_registered_target("dummy_generic")
    """

    try:
        target_registry.get_target_hardware(target, "__backend_probe__")
    except ValueError:
        return False
    return True


def _target_candidates() -> dict[str, str]:
    """返回可由公开 `EmitCContext.target_entry(...)` 识别的 target 候选。


    功能说明:
    - 汇总已加载 backend 与已注册 handler 的 target 名称。
    - 追加当前 core config target，覆盖普通调用中新建 context 的 target。

    使用示例:
    - target = ctx.target_entry(_target_candidates())
    """

    candidates: set[str] = set(_LOADED_BACKENDS)
    candidates.update(_TARGET_OP_REGISTRY)
    candidates.update(_TARGET_VALUE_REGISTRY)
    candidates.update(_TARGET_TYPE_REGISTRY)
    candidates.update(_TARGET_ATTR_REGISTRY)
    candidates.update(_TARGET_INCLUDE_REGISTRY)
    candidates.update(_TARGET_NAME_REGISTRY)
    current = get_target()
    if isinstance(current, str) and current:
        candidates.add(current)
    return {target: target for target in candidates}


def _current_target(ctx: EmitCContext) -> str:
    """读取当前公开 target 配置。


    功能说明:
    - 优先通过 `EmitCContext.target_entry(...)` 公开入口读取 context 捕获的 target。
    - context 无法匹配时回退到 `kernel_gen.core.config` 当前 target。
    - dispatch 时用该值决定是否需要自动加载 backend 模块。

    使用示例:
    - target = _current_target(ctx)
    """

    target = ctx.target_entry(_target_candidates())
    if target is None:
        target = get_target()
    if not isinstance(target, str) or not target:
        raise _emit_registry_error("invalid target name")
    _validate_target_name(target)
    return target


def _ensure_backend_loaded(ctx: EmitCContext) -> str:
    """按当前 target 自动加载 backend 模块。


    功能说明:
    - backend 路径固定为 `kernel_gen.dsl.gen_kernel.emit.<target>`。
    - 内置 `cpu` / `npu_demo` 已由 emit package 初始化导入，不重复导入。
    - 区分目标模块不存在与模块内部导入失败。

    使用示例:
    - target = _ensure_backend_loaded(ctx)
    """

    target = _current_target(ctx)
    if target in _LOADED_BACKENDS:
        return target
    if not _is_registered_target(target):
        return target
    module_name = f"kernel_gen.dsl.gen_kernel.emit.{target}"
    try:
        importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name:
            raise _emit_registry_error(f"backend_not_found: {module_name}") from exc
        raise _emit_registry_error(f"backend_import_failed: {module_name}: {exc}") from exc
    except Exception as exc:
        raise _emit_registry_error(f"backend_import_failed: {module_name}: {type(exc).__name__}: {exc}") from exc
    _LOADED_BACKENDS.add(target)
    return target


def _register_entry(
    table: dict[type[Any], Callable[..., Any]],
    typ: type[Any],
    func: Callable[..., Any],
    *,
    override: bool,
    target: str | None,
) -> None:
    """注册单个 handler 并执行重复注册校验。


    功能说明:
    - 默认拒绝同一 registry 下的同类型重复注册。
    - `override=True` 时显式覆盖原 handler。

    使用示例:
    - _register_entry(scoped, ModuleOp, handler, override=False, target="dummy_generic")
    """

    if typ in table and not override:
        target_label = "<default>" if target is None else target
        raise _emit_registry_error(f"duplicate backend registration: target={target_label} type={typ.__name__}")
    table[typ] = func


def _register_target_entry(
    registry: dict[str, dict[type[Any], Callable[..., Any]]],
    target: str,
    typ: type[Any],
    func: Callable[..., Any],
    *,
    override: bool,
) -> None:
    """注册 target-scoped handler。


    功能说明:
    - 统一 target 名称校验与 target-scoped registry 初始化。
    - 默认不允许重复注册。

    使用示例:
    - _register_target_entry(_TARGET_OP_REGISTRY, "cpu", Operation, handler, override=False)
    """

    _validate_target_name(target)
    scoped = registry.setdefault(target, {})
    _register_entry(scoped, typ, func, override=override, target=target)


def _validate_bundle_path(path: str, seen_paths: set[str]) -> None:
    """校验 SourceBundle artifact 路径。


    功能说明:
    - path 必须为 POSIX 风格安全相对路径。
    - 拒绝空路径、绝对路径、`.`、`..`、反斜杠、NUL、重复路径和 `..` segment。

    使用示例:
    - _validate_bundle_path("include/kernel.h", set())
    """

    if (
        not isinstance(path, str)
        or not path
        or path.startswith("/")
        or path in {".", ".."}
        or "\\" in path
        or "\x00" in path
        or path in seen_paths
    ):
        raise _emit_registry_error("source_bundle_malformed")
    if any(part in {"", ".", ".."} for part in path.split("/")):
        raise _emit_registry_error("source_bundle_malformed")
    seen_paths.add(path)


def _validate_bundle_content(content: str) -> None:
    """校验 SourceBundle artifact 内容。


    功能说明:
    - 内容必须为字符串。
    - 内容中不得包含完整匹配 SourceBundle marker 的行，避免 aggregate 解析歧义。

    使用示例:
    - _validate_bundle_content("int main() {}")
    """

    if not isinstance(content, str):
        raise _emit_registry_error("source_product_invalid")
    for line in content.splitlines():
        if line.startswith(_BUNDLE_MARKER_PREFIX):
            raise _emit_registry_error("source_bundle_malformed")


def _encode_source_bundle(product: Mapping[str, str]) -> str:
    """把多文件 SourceProduct 编码为 aggregate string。


    功能说明:
    - 按用户确认的 `// __KG_BUNDLE_FILE__:<path>` marker 格式编码多文件源码。
    - 仅供本文件内部把 ModuleOp handler 返回的 mapping 转成公开 `str` 返回值。

    使用示例:
    - source = _encode_source_bundle({"kernel.cpp": "void f() {}"})
    """

    if not product:
        raise _emit_registry_error("source_product_invalid")
    seen_paths: set[str] = set()
    chunks: list[str] = []
    for path, content in product.items():
        _validate_bundle_path(path, seen_paths)
        _validate_bundle_content(content)
        chunks.append(f"{_BUNDLE_MARKER_PREFIX}{path}\n{content.rstrip()}")
    return "\n".join(chunks).rstrip() + "\n"


def _normalize_source_product(product: SourceProduct) -> str:
    """把 ModuleOp handler 返回的源码产物规范化为字符串。


    功能说明:
    - `str` 表示单文件源码，原样返回。
    - `Mapping[str, str]` 表示多文件源码，编码为 SourceBundle aggregate string。
    - 其它返回类型稳定失败为 `source_product_invalid`。

    使用示例:
    - source = _normalize_source_product({"kernel.cpp": "void f() {}"})
    """

    if isinstance(product, str):
        return product
    if isinstance(product, Mapping):
        return _encode_source_bundle(product)
    raise _emit_registry_error("source_product_invalid")


def emit_c_impl(
    *types: type[Any],
    target: str | None = None,
    override: bool = False,
) -> Callable[[OpHandler], OpHandler]:
    def decorator(func: OpHandler) -> OpHandler:
        if target is None:
            for typ in types:
                _register_entry(_OP_REGISTRY, typ, func, override=override, target=None)
        else:
            for typ in types:
                _register_target_entry(_TARGET_OP_REGISTRY, target, typ, func, override=override)
        return func

    return decorator


def emit_c_value_impl(
    *types: type[Any],
    target: str | None = None,
    override: bool = False,
) -> Callable[[ValueHandler], ValueHandler]:
    def decorator(func: ValueHandler) -> ValueHandler:
        if target is None:
            for typ in types:
                _register_entry(_VALUE_REGISTRY, typ, func, override=override, target=None)
        else:
            for typ in types:
                _register_target_entry(_TARGET_VALUE_REGISTRY, target, typ, func, override=override)
        return func

    return decorator


def emit_c_type_impl(
    *types: type[Any],
    target: str,
    override: bool = False,
) -> Callable[[TypeHandler], TypeHandler]:
    def decorator(func: TypeHandler) -> TypeHandler:
        for typ in types:
            _register_target_entry(_TARGET_TYPE_REGISTRY, target, typ, func, override=override)
        return func

    return decorator


def emit_c_attr_impl(
    *types: type[Any],
    target: str,
    override: bool = False,
) -> Callable[[AttrHandler], AttrHandler]:
    def decorator(func: AttrHandler) -> AttrHandler:
        for typ in types:
            _register_target_entry(_TARGET_ATTR_REGISTRY, target, typ, func, override=override)
        return func

    return decorator


def emit_c_include_impl(*, target: str, override: bool = False) -> Callable[[IncludeHandler], IncludeHandler]:
    def decorator(func: IncludeHandler) -> IncludeHandler:
        _validate_target_name(target)
        if target in _TARGET_INCLUDE_REGISTRY and not override:
            raise _emit_registry_error(f"duplicate backend registration: target={target} type=include")
        _TARGET_INCLUDE_REGISTRY[target] = func
        return func

    return decorator


def emit_c_name_impl(
    *types: type[Any],
    target: str,
    override: bool = False,
) -> Callable[[NameHandler], NameHandler]:
    def decorator(func: NameHandler) -> NameHandler:
        for typ in types:
            _register_target_entry(_TARGET_NAME_REGISTRY, target, typ, func, override=override)
        return func

    return decorator


def dispatch_op(op: Operation, ctx: EmitCContext) -> str | None:
    target = _ensure_backend_loaded(ctx)
    target_registry = ctx.target_entry(_TARGET_OP_REGISTRY, {})
    dispatched = _dispatch_op_with_registry(op, ctx, target_registry)
    if dispatched is None and isinstance(op, ModuleOp) and target not in {"cpu", "npu_demo"}:
        raise ctx.emit_error("backend loader", f"backend_handler_not_found: target={target} type=ModuleOp")
    return dispatched


def dispatch_op_for_target(op: Operation, ctx: EmitCContext, target: str) -> str | None:
    """按显式 target 名称分发 op。


    功能说明:
    - 保留既有公开 registry 查询入口，用于需要显式 target registry 查询的调用方。
    - 该函数不做 unknown target -> cpu fallback；调用方传入哪个 target 就只查询哪个 target 的 handler。

    使用示例:
    - stmt = dispatch_op_for_target(op, ctx, "dummy_generic")
    """

    _validate_target_name(target)
    _ensure_registered_target(target)
    return _dispatch_op_with_registry(op, ctx, _TARGET_OP_REGISTRY.get(target, {}), include_default=False)


def _dispatch_op_with_registry(
    op: Operation,
    ctx: EmitCContext,
    target_registry: dict[type[Any], OpHandler],
    *,
    include_default: bool = True,
) -> str | None:
    """按给定 registry 分发 op。


    功能说明:
    - 优先查询 target-specific registry。
    - `include_default=True` 时允许普通 `dispatch_op(...)` 继续查询默认 registry。
    - `include_default=False` 时用于 `dispatch_op_for_target(...)`，保证显式 target 查询不会泄漏默认 handler。

    使用示例:
    - stmt = _dispatch_op_with_registry(op, ctx, registry, include_default=False)
    """

    for cls in type(op).__mro__:
        handler = target_registry.get(cls)
        if handler is not None:
            return _normalize_source_product(handler(op, ctx))
        if include_default:
            handler = _OP_REGISTRY.get(cls)
            if handler is not None:
                return _normalize_source_product(handler(op, ctx))
    return None


def dispatch_value(value: SSAValue, ctx: EmitCContext) -> str | None:
    _ensure_backend_loaded(ctx)
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
    _ensure_backend_loaded(ctx)
    target_registry = ctx.target_entry(_TARGET_TYPE_REGISTRY, {})
    for cls in type(attr).__mro__:
        handler = target_registry.get(cls)
        if handler is not None:
            return handler(attr, ctx)
    return None


def dispatch_attr(attr: Any, ctx: EmitCContext) -> str | None:
    _ensure_backend_loaded(ctx)
    target_registry = ctx.target_entry(_TARGET_ATTR_REGISTRY, {})
    for cls in type(attr).__mro__:
        handler = target_registry.get(cls)
        if handler is not None:
            return handler(attr, ctx)
    return None


def dispatch_include(ctx: EmitCContext) -> str:
    _ensure_backend_loaded(ctx)
    handler = ctx.target_entry(_TARGET_INCLUDE_REGISTRY)
    if handler is None:
        return ""
    return handler(ctx)


def dispatch_name(value: SSAValue, ctx: EmitCContext) -> str | None:
    _ensure_backend_loaded(ctx)
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
