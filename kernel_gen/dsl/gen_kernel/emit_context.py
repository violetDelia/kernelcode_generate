"""`gen_kernel.emit` 公开上下文定义。

创建者: 小李飞刀
最后一次更改: OpenAI Codex

功能说明:
- 定义 `EmitCContext` / `EmitCError` 的稳定公开入口。
- 供 `emit` / `emit_c` / `gen_kernel` 共享同一份上下文与错误类型。

使用示例:
- from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext
- ctx = EmitCContext(target="cpu")

关联文件:
- spec: [spec/dsl/gen_kernel/emit.md](../../../spec/dsl/gen_kernel/emit.md)
- test: [test/dsl/gen_kernel/emit/test_emit.py](../../../test/dsl/gen_kernel/emit/test_emit.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit_context.py](../../../kernel_gen/dsl/gen_kernel/emit_context.py)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from xdsl.dialects.builtin import BFloat16Type, Float16Type, Float64Type, IndexType, IntegerType, Signedness, f32, f64
from xdsl.ir import SSAValue
from xdsl.ir import Operation

from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType


class EmitCError(ValueError):
    """emit_c 阶段错误。"""


@dataclass
class EmitCContext:
    """单次片段生成上下文。"""

    target: str
    indent: str = "    "
    naming: Any | None = None
    type_converter: Any | None = None
    config: dict[str, Any] | None = None
    _names: dict[int, str] = field(default_factory=dict)
    _next_id: int = 0
    _indent_level: int = 0
    _symbol_const_names: dict[int, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.config is None:
            self.config = {}

    @property
    def current_indent(self) -> str:
        return self.indent * self._indent_level

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

    def create_or_get_name(
        self,
        value: SSAValue,
        *,
        preferred: str | None = None,
        prefix: str = "v",
    ) -> str:
        existing = self.lookup_name(value)
        if existing is not None:
            return existing

        from .emit.register import dispatch_name

        dispatched = dispatch_name(value, self, preferred=preferred, prefix=prefix)
        if dispatched is not None:
            name = dispatched
        else:
            if self.naming is not None:
                if callable(self.naming):
                    name = self.naming(value)
                elif hasattr(self.naming, "allocate"):
                    name = self.naming.allocate(value)
                else:
                    raise EmitCError(f"target={self.target}: unsupported naming strategy")
            elif preferred is not None:
                name = preferred
            else:
                name = f"{prefix}{self._next_id}"
                self._next_id += 1
        used_names = set(self._names.values())
        if name in used_names:
            base_name = name
            suffix = 1
            while f"{base_name}_{suffix}" in used_names:
                suffix += 1
            name = f"{base_name}_{suffix}"
        return self.bind_name(value, name)

    def clone_for_target(self, target: str) -> "EmitCContext":
        return EmitCContext(
            target=target,
            indent=self.indent,
            naming=self.naming,
            type_converter=self.type_converter,
            config=dict(self.config or {}),
        )

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
        if self.type_converter is not None:
            if callable(self.type_converter):
                return self.type_converter(attr)
            if hasattr(self.type_converter, "convert"):
                return self.type_converter.convert(attr)
            raise EmitCError(f"target={self.target}: type converter: unsupported type converter")

        from .emit.register import dispatch_type

        try:
            dispatched = dispatch_type(attr, self)
        except ValueError as exc:
            raise EmitCError(f"target={self.target}: {exc}") from exc
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
                raise EmitCError(f"target={self.target}: type {attr}: unsupported memory space attr")
            raw_space = dispatched_space
            space_param = f"MemorySpace::{raw_space}" if self.target == "cpu" else raw_space
            return f"Memory<{space_param}, {self.dispatch_type(attr.element_type)}>"
        if isinstance(attr, SymbolValueType):
            return "S_INT" if self.target == "npu_demo" else "long long"
        raise EmitCError(f"target={self.target}: type {attr}: unsupported type")

    def dispatch_attr(self, attr: Any) -> str | None:
        from .emit.register import dispatch_attr

        try:
            return dispatch_attr(attr, self)
        except ValueError as exc:
            raise EmitCError(f"target={self.target}: {exc}") from exc

    def dispatch_include(self) -> str:
        from .emit.register import dispatch_include

        return dispatch_include(self)

__all__ = ["EmitCContext", "EmitCError"]
