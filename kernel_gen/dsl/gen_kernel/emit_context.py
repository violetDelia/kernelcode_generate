"""`gen_kernel.emit` 公开上下文定义。

创建者: 小李飞刀
最后一次更改: OpenAI Codex

功能说明:
- 定义 `EmitCContext` / `EmitCError` 的稳定公开入口。
- 供 `emit` / `emit_c` / `gen_kernel` 共享同一份上下文与错误类型。
- 将非私有可配置项统一收口到 `config`，避免 context 再维护平行公开字段。

API 列表:
- `EmitCError(message: str)`
- `EmitCContext(*, config: dict[str, Any] | None = None)`
- `EmitCContext.create_or_get_name(value: SSAValue) -> str`
- `EmitCContext.dispatch(obj: Any) -> str | None`
- `EmitCContext.dispatch_op(op: Operation) -> str | None`
- `EmitCContext.dispatch_value(value: SSAValue) -> str | None`
- `EmitCContext.dispatch_type(attr: Any) -> str`
- `EmitCContext.dispatch_attr(attr: Any) -> str | None`
- `EmitCContext.dispatch_include() -> str`

helper 清单:
- `EmitCContext.current_indent -> str`
- `EmitCContext.push_indent() -> None`
- `EmitCContext.pop_indent() -> None`
- `EmitCContext.bind_name(value: SSAValue, name: str) -> str`
- `EmitCContext.lookup_name(value: SSAValue) -> str | None`

使用示例:
- from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext
- ctx = EmitCContext(config={"target": "cpu", "indent": "  "})

关联文件:
- spec: [spec/dsl/gen_kernel/emit_context.md](../../../spec/dsl/gen_kernel/emit_context.md)
- spec: [spec/dsl/gen_kernel/emit.md](../../../spec/dsl/gen_kernel/emit.md)
- test: [test/dsl/gen_kernel/emit/test_emit.py](../../../test/dsl/gen_kernel/emit/test_emit.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit_context.py](../../../kernel_gen/dsl/gen_kernel/emit_context.py)
"""

from __future__ import annotations

from typing import Any

from xdsl.dialects.builtin import BFloat16Type, Float16Type, Float64Type, IndexType, IntegerType, Signedness, f32, f64
from xdsl.ir import SSAValue
from xdsl.ir import Operation

from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType


class EmitCError(ValueError):
    """emit_c 阶段错误。"""


class EmitCContext:
    """单次片段生成上下文。"""

    config: dict[str, Any]
    _names: dict[int, str]
    _next_id: int
    _indent_level: int

    def __init__(self, *, config: dict[str, Any] | None = None) -> None:
        self.config = dict(config or {})
        target = self.config.get("target")
        if not isinstance(target, str) or not target:
            raise EmitCError("EmitCContext: config['target'] must be non-empty str")
        indent = self.config.get("indent", "    ")
        if not isinstance(indent, str):
            raise EmitCError("EmitCContext: config['indent'] must be str")
        self._names = {}
        self._next_id = 0
        self._indent_level = 0

    @property
    def current_indent(self) -> str:
        return self.config.get("indent", "    ") * self._indent_level

    def push_indent(self) -> None:
        self._indent_level += 1

    def pop_indent(self) -> None:
        if self._indent_level == 0:
            return
        self._indent_level -= 1

    def bind_name(self, value: SSAValue, name: str) -> str:
        self._names[id(value)] = name
        return name

    def lookup_name(self, value: SSAValue) -> str | None:
        return self._names.get(id(value))

    def _dedupe_name(self, name: str) -> str:
        used_names = set(self._names.values())
        if name not in used_names:
            return name
        base_name = name
        suffix = 1
        while f"{base_name}_{suffix}" in used_names:
            suffix += 1
        return f"{base_name}_{suffix}"

    def _allocate_name(self, value: SSAValue) -> str:
        naming = self.config.get("naming")
        if naming is not None:
            if callable(naming):
                return naming(value)
            if hasattr(naming, "allocate"):
                return naming.allocate(value)
            raise EmitCError(f"target={self.config['target']}: unsupported naming strategy")
        name = f"v{self._next_id}"
        self._next_id += 1
        return name

    def create_or_get_name(self, value: SSAValue) -> str:
        existing = self.lookup_name(value)
        if existing is not None:
            return existing

        from .emit.register import dispatch_name

        name = dispatch_name(value, self)
        if name is None:
            name = self._allocate_name(value)
        return self.bind_name(value, self._dedupe_name(name))

    def dispatch(self, obj: Any) -> str | None:
        if isinstance(obj, SSAValue):
            return self.dispatch_value(obj)
        if isinstance(obj, Operation):
            return self.dispatch_op(obj)
        return self.dispatch_attr(obj)

    def dispatch_op(self, op: Operation) -> str | None:
        from .emit.register import dispatch_op

        return dispatch_op(op, self)

    def dispatch_value(self, value: SSAValue) -> str | None:
        from .emit.register import dispatch_value

        return dispatch_value(value, self)

    def dispatch_type(self, attr: Any) -> str:
        type_converter = self.config.get("type_converter")
        if type_converter is not None:
            if callable(type_converter):
                return type_converter(attr)
            if hasattr(type_converter, "convert"):
                return type_converter.convert(attr)
            raise EmitCError(f"target={self.config['target']}: type converter: unsupported type converter")

        from .emit.register import dispatch_type

        try:
            dispatched = dispatch_type(attr, self)
        except ValueError as exc:
            raise EmitCError(f"target={self.config['target']}: {exc}") from exc
        if dispatched is not None:
            return dispatched
        if isinstance(attr, IntegerType):
            if attr.width.data == 1:
                return "bool"
            prefix = "uint" if attr.signedness.data == Signedness.UNSIGNED else "int"
            return f"{prefix}{attr.width.data}_t"
        if isinstance(attr, Float16Type):
            return "half"
        if isinstance(attr, BFloat16Type):
            return "bfloat16_t"
        if attr == f32:
            return "float"
        if isinstance(attr, Float64Type) or attr == f64:
            return "double"
        if isinstance(attr, IndexType):
            return "long long"
        if isinstance(attr, NnMemoryType):
            dispatched_space = self.dispatch_attr(attr)
            if dispatched_space is None:
                raise EmitCError(f"target={self.config['target']}: type {attr}: unsupported memory space attr")
            raw_space = dispatched_space
            space_param = f"MemorySpace::{raw_space}" if self.config["target"] == "cpu" else raw_space
            return f"Memory<{space_param}, {self.dispatch_type(attr.element_type)}>"
        if isinstance(attr, SymbolValueType):
            return "S_INT" if self.config["target"] == "npu_demo" else "long long"
        raise EmitCError(f"target={self.config['target']}: type {attr}: unsupported type")

    def dispatch_attr(self, attr: Any) -> str | None:
        from .emit.register import dispatch_attr

        try:
            return dispatch_attr(attr, self)
        except ValueError as exc:
            raise EmitCError(f"target={self.config['target']}: {exc}") from exc

    def dispatch_include(self) -> str:
        from .emit.register import dispatch_include

        return dispatch_include(self)

__all__ = ["EmitCContext", "EmitCError"]
