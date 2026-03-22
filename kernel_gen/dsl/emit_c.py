"""C-like fragment emission helpers for DSL lowering.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 提供单个 MLIR op/value 到 C 风格源码片段的最小生成规则。
- 仅负责节点级片段生成，不负责完整函数签名与函数级组织。

使用示例:
- from kernel_gen.dsl.emit_c import EmitCContext, emit_c_op, emit_c_value
- stmt = emit_c_op(op, EmitCContext(target="cpu"))

关联文件:
- spec: spec/dsl/emit_c.md
- test: test/dsl/test_emit_c.py
- 功能实现: kernel_gen/dsl/emit_c.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from xdsl.dialects import arith, func, scf
from xdsl.dialects.builtin import FloatAttr, IndexType, IntAttr, IntegerAttr, IntegerType
from xdsl.ir import BlockArgument, Operation, SSAValue

from kernel_gen.dialect.dma import DmaLoadOp, DmaStoreOp
from kernel_gen.dialect.nn import NnMemoryType


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

    def allocate_name(self, value: SSAValue, prefix: str = "v") -> str:
        existing = self.lookup_name(value)
        if existing is not None:
            return existing
        if self.naming is not None:
            if callable(self.naming):
                name = self.naming(value)
            elif hasattr(self.naming, "allocate"):
                name = self.naming.allocate(value)
            else:
                raise EmitCError(f"target={self.target}: unsupported naming strategy")
        else:
            name = f"{prefix}{self._next_id}"
            self._next_id += 1
        return self.bind_name(value, name)


def _emit_error(ctx: EmitCContext, subject: str, reason: str) -> EmitCError:
    return EmitCError(f"target={ctx.target}: {subject}: {reason}")


_BINARY_SIGILS = {
    "arith.addi": "+",
    "arith.addf": "+",
    "arith.subi": "-",
    "arith.subf": "-",
    "arith.muli": "*",
    "arith.mulf": "*",
    "arith.divf": "/",
}

_CMPI_SIGILS = {
    0: "==",
    1: "!=",
    2: "<",
    3: "<=",
    4: ">",
    5: ">=",
}


def _type_to_c(attr: Any, ctx: EmitCContext) -> str:
    if ctx.type_converter is not None:
        if callable(ctx.type_converter):
            return ctx.type_converter(attr)
        if hasattr(ctx.type_converter, "convert"):
            return ctx.type_converter.convert(attr)
        raise EmitCError(f"target={ctx.target}: unsupported type converter")
    if isinstance(attr, IntegerType):
        if attr.width.data == 1:
            return "bool"
        return f"int{attr.width.data}_t"
    if isinstance(attr, IndexType):
        return "long long"
    if isinstance(attr, NnMemoryType):
        return f"Memory<{_type_to_c(attr.element_type, ctx)}>"
    raise _emit_error(ctx, f"type {attr}", "unsupported type")


def _format_literal(op: arith.ConstantOp, ctx: EmitCContext) -> str:
    value = op.value
    if isinstance(value, IntegerAttr):
        return str(value.value.data)
    if isinstance(value, FloatAttr):
        return str(value.value.data)
    raise _emit_error(ctx, op.name, "unsupported constant literal")


def _memory_base_name(value: SSAValue, ctx: EmitCContext) -> str:
    bound = ctx.lookup_name(value)
    if bound is not None:
        return bound
    if isinstance(value, BlockArgument):
        return ctx.allocate_name(value, prefix="arg")
    owner = value.owner
    if isinstance(owner, DmaLoadOp):
        return ctx.allocate_name(value)
    raise _emit_error(ctx, f"value {value}", "invalid dependency")


def _format_indices(indices: tuple[SSAValue, ...], ctx: EmitCContext) -> str:
    return "".join(f"[{emit_c_value(index, ctx)}]" for index in indices)


def _is_unit_tile(memory_type: NnMemoryType) -> bool:
    if len(memory_type.shape.data) == 0:
        return False
    return all(isinstance(dim, IntAttr) and dim.data == 1 for dim in memory_type.shape.data)


def _emit_dma_load_expr(op: DmaLoadOp, ctx: EmitCContext) -> str:
    result_type = op.result.type
    if not isinstance(result_type, NnMemoryType) or not _is_unit_tile(result_type):
        raise _emit_error(ctx, op.name, "only unit-tile dma.load is supported")
    base = _memory_base_name(op.source, ctx)
    return f"{base}{_format_indices(op.offsets, ctx)}"


def _emit_dma_store_stmt(op: DmaStoreOp, ctx: EmitCContext) -> str:
    source_type = op.source.type
    if not isinstance(source_type, NnMemoryType) or not _is_unit_tile(source_type):
        raise _emit_error(ctx, op.name, "only unit-tile dma.store source is supported")
    source_expr = _memory_base_name(op.source, ctx)
    target_expr = _memory_base_name(op.target, ctx)
    return f"{ctx.current_indent}{target_expr}{_format_indices(op.offsets, ctx)} = {source_expr};"


def emit_c_value(value: SSAValue, ctx: EmitCContext) -> str:
    """把 SSA value 生成为右值表达式。"""

    bound = ctx.lookup_name(value)
    if bound is not None:
        return bound
    if isinstance(value, BlockArgument):
        return ctx.allocate_name(value, prefix="arg")
    owner = value.owner
    if isinstance(owner, arith.ConstantOp):
        return _format_literal(owner, ctx)
    if owner.name in _BINARY_SIGILS:
        lhs = emit_c_value(owner.operands[0], ctx)
        rhs = emit_c_value(owner.operands[1], ctx)
        return f"({lhs} {_BINARY_SIGILS[owner.name]} {rhs})"
    if isinstance(owner, arith.CmpiOp):
        predicate = owner.predicate.value.data
        if predicate not in _CMPI_SIGILS:
            raise _emit_error(ctx, owner.name, "unsupported comparison predicate")
        lhs = emit_c_value(owner.lhs, ctx)
        rhs = emit_c_value(owner.rhs, ctx)
        return f"({lhs} {_CMPI_SIGILS[predicate]} {rhs})"
    if isinstance(owner, DmaLoadOp):
        return _emit_dma_load_expr(owner, ctx)
    raise _emit_error(ctx, owner.name, f"invalid dependency for value {value}")


def _emit_assignment(op: Operation, ctx: EmitCContext) -> str:
    result = op.results[0]
    result_type = _type_to_c(result.type, ctx)
    if isinstance(op, DmaLoadOp) and isinstance(result.type, NnMemoryType) and _is_unit_tile(result.type):
        result_type = _type_to_c(result.type.element_type, ctx)
    expr = emit_c_value(result, ctx)
    result_name = ctx.allocate_name(result)
    return f"{ctx.current_indent}{result_type} {result_name} = {expr};"


def _emit_loop(op: scf.ForOp, ctx: EmitCContext) -> str:
    iv_name = ctx.allocate_name(op.body.block.args[0], prefix="i")
    lower = emit_c_value(op.lb, ctx)
    upper = emit_c_value(op.ub, ctx)
    step = emit_c_value(op.step, ctx)
    lines = [f"{ctx.current_indent}for (long long {iv_name} = {lower}; {iv_name} < {upper}; {iv_name} += {step}) {{"]
    ctx.push_indent()
    for body_op in op.body.block.ops:
        if isinstance(body_op, scf.YieldOp):
            continue
        lines.append(emit_c_op(body_op, ctx))
    ctx.pop_indent()
    lines.append(f"{ctx.current_indent}}}")
    return "\n".join(lines)


def emit_c_op(op: Operation, ctx: EmitCContext) -> str:
    """把单个 op 生成为语句或语句块。"""

    if op.name in _BINARY_SIGILS or isinstance(op, arith.CmpiOp):
        return _emit_assignment(op, ctx)
    if isinstance(op, DmaLoadOp):
        return _emit_assignment(op, ctx)
    if isinstance(op, DmaStoreOp):
        return _emit_dma_store_stmt(op, ctx)
    if isinstance(op, arith.ConstantOp):
        return ""
    if isinstance(op, scf.ForOp):
        return _emit_loop(op, ctx)
    if isinstance(op, func.ReturnOp):
        if not op.arguments:
            return ""
        if len(op.arguments) != 1:
            raise _emit_error(ctx, op.name, "unsupported return arity")
        return f"{ctx.current_indent}return {emit_c_value(op.arguments[0], ctx)};"
    raise _emit_error(ctx, op.name, "unsupported op")


__all__ = ["EmitCContext", "EmitCError", "emit_c_op", "emit_c_value"]
