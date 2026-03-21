"""AST emit utilities for DSL nodes.

创建者: 小李飞刀
最后一次更改: 朽木露琪亚

功能说明:
- 提供 AST 节点到 MLIR SSA value/op 的发射入口。
- 维护节点发射所需的上下文、类型推导与显式错误。

使用示例:
- from kernel_gen.dsl.emit_mlir import EmitContext, emit_mlir
- value = emit_mlir(expr_ast, ctx)

关联文件:
- spec: spec/dsl/emit_mlir.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: kernel_gen/dsl/emit_mlir.py
"""

from __future__ import annotations

from typing import Sequence

from xdsl.dialects import arith, func
from xdsl.dialects.builtin import ArrayAttr, FloatAttr, IntAttr, IntegerAttr, StringAttr, i1, i32, f32
from xdsl.ir import Attribute, Block

from kernel_gen.dialect.dma import DmaLoadOp, DmaStoreOp
from kernel_gen.dialect.nn import (
    NnAddOp,
    NnBroadcastOp,
    NnEqOp,
    NnGeOp,
    NnGtOp,
    NnLeOp,
    NnLtOp,
    NnMemorySpaceAttr,
    NnMemoryType,
    NnMulOp,
    NnNeOp,
    NnSubOp,
    NnTrueDivOp,
)
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType

from .ast import (
    BinaryExprAST,
    BlockAST,
    CompareExprAST,
    ConstAST,
    ForAST,
    FunctionAST,
    LoadAST,
    ScalarArgAST,
    SourceLocation,
    StoreAST,
    TensorAST,
    VarAST,
)


_MEMORY_SPACE_MAP = {
    MemorySpace.GM: "global",
    MemorySpace.SM: "shared",
    MemorySpace.LM: "local",
    MemorySpace.TSM: "shared",
    MemorySpace.TLM: "local",
}


class _LoweringError(ValueError):
    """lowering/emit 阶段错误。"""

    def __init__(self, message: str, location: SourceLocation | None = None) -> None:
        super().__init__(message)
        self.location = location


class EmitContext:
    """AST 节点发射上下文。"""

    def __init__(
        self,
        builder: Block,
        symbols: dict[str, object],
        types: dict[int, object],
        config: dict[str, object] | None = None,
    ) -> None:
        self.builder = builder
        self.symbols = symbols
        self.types = types
        self.config = config
        self._cache: dict[int, object] = {}

    def _has_cache(self, key: int) -> bool:
        return key in self._cache

    def _get_cache(self, key: int) -> object | None:
        return self._cache.get(key)

    def _set_cache(self, key: int, value: object) -> None:
        self._cache[key] = value

    def _setdefault_cache(self, key: int, value: object) -> object:
        return self._cache.setdefault(key, value)

    def _snapshot_cache(self) -> dict[int, object]:
        return dict(self._cache)

    def _restore_cache(self, snapshot: dict[int, object]) -> None:
        self._cache = dict(snapshot)


def _dtype_to_xdsl(dtype: NumericType) -> object:
    if dtype is NumericType.Float32:
        return f32
    if dtype is NumericType.Int32:
        return i32
    raise _LoweringError(f"Unsupported dtype: {dtype}")


def _build_stride(shape: list[int | str]) -> list[int | str]:
    stride: list[int | str] = []
    acc = 1
    for dim in reversed(shape):
        if isinstance(dim, int):
            stride.insert(0, acc)
            acc *= dim
        else:
            stride.insert(0, "?")
    return stride


def _dim_to_attr(value: int | str) -> object:
    if isinstance(value, int):
        return IntAttr(value)
    return StringAttr(value)


def _get_loop_vars(ctx: EmitContext) -> dict[str, int]:
    if ctx.config is None:
        ctx.config = {}
    loop_vars = ctx.config.setdefault("loop_vars", {})
    if not isinstance(loop_vars, dict):
        raise _LoweringError("loop_vars must be a dict", location=None)
    return loop_vars


def _resolve_index_expr(expr: object, ctx: EmitContext) -> int | str:
    if isinstance(expr, ConstAST):
        if isinstance(expr.value, (int, str)):
            return expr.value
        raise _LoweringError("Index must be int or str", location=expr.location)
    if isinstance(expr, VarAST):
        loop_vars = _get_loop_vars(ctx)
        if expr.name in loop_vars:
            return loop_vars[expr.name]
        raise _LoweringError("Unknown loop variable", location=expr.location)
    if isinstance(expr, (int, str)):
        return expr
    raise _LoweringError("Unsupported index expression", location=getattr(expr, "location", None))


def _build_index_attrs(value: object | None, rank: int, ctx: EmitContext, *, default_value: int = 0) -> ArrayAttr:
    if value is None:
        values = [default_value for _ in range(rank)]
    elif isinstance(value, (list, tuple)):
        if len(value) != rank:
            raise _LoweringError("Index rank mismatch", location=getattr(value, "location", None))
        values = [_resolve_index_expr(entry, ctx) for entry in value]
    else:
        scalar = _resolve_index_expr(value, ctx)
        values = [scalar for _ in range(rank)]
    return ArrayAttr([_dim_to_attr(item) for item in values])


def _build_stride_attrs(value: object | None, rank: int, ctx: EmitContext) -> ArrayAttr:
    stride = _build_index_attrs(value, rank, ctx, default_value=1)
    for entry in stride.data:
        if not isinstance(entry, IntAttr) or entry.data != 1:
            raise _LoweringError("Only unit stride is supported", location=None)
    return stride


def _dims_equal(lhs: Attribute, rhs: Attribute) -> bool:
    if isinstance(lhs, IntAttr) and isinstance(rhs, IntAttr):
        return lhs.data == rhs.data
    if isinstance(lhs, StringAttr) and isinstance(rhs, StringAttr):
        return lhs.data == rhs.data
    return False


def _infer_broadcast_shape(
    lhs_shape: Sequence[Attribute],
    rhs_shape: Sequence[Attribute],
    location: SourceLocation | None,
) -> list[Attribute]:
    max_rank = max(len(lhs_shape), len(rhs_shape))
    result: list[Attribute] = []
    for index in range(1, max_rank + 1):
        lhs_dim = lhs_shape[-index] if index <= len(lhs_shape) else None
        rhs_dim = rhs_shape[-index] if index <= len(rhs_shape) else None
        if lhs_dim is None:
            result.insert(0, rhs_dim)
            continue
        if rhs_dim is None:
            result.insert(0, lhs_dim)
            continue
        if isinstance(lhs_dim, StringAttr) and lhs_dim.data == "?":
            if _dims_equal(lhs_dim, rhs_dim):
                result.insert(0, lhs_dim)
                continue
            raise _LoweringError("Implicit broadcast dimension mismatch", location=location)
        if isinstance(rhs_dim, StringAttr) and rhs_dim.data == "?":
            if _dims_equal(lhs_dim, rhs_dim):
                result.insert(0, rhs_dim)
                continue
            raise _LoweringError("Implicit broadcast dimension mismatch", location=location)
        if _dims_equal(lhs_dim, rhs_dim):
            result.insert(0, lhs_dim)
            continue
        if isinstance(lhs_dim, IntAttr) and lhs_dim.data == 1:
            result.insert(0, rhs_dim)
            continue
        if isinstance(rhs_dim, IntAttr) and rhs_dim.data == 1:
            result.insert(0, lhs_dim)
            continue
        raise _LoweringError("Implicit broadcast dimension mismatch", location=location)
    return result


def _build_broadcast_stride(shape: Sequence[Attribute]) -> list[Attribute]:
    stride: list[Attribute] = []
    for dim in shape:
        if isinstance(dim, IntAttr):
            stride.append(IntAttr(1))
        elif isinstance(dim, StringAttr) and dim.data == "?":
            stride.append(IntAttr(1))
        else:
            stride.append(StringAttr("?"))
    return stride


def _infer_broadcast_memory_type(
    lhs_type: NnMemoryType,
    rhs_type: NnMemoryType,
    location: SourceLocation | None,
) -> NnMemoryType:
    if lhs_type.element_type != rhs_type.element_type:
        raise _LoweringError("Binary op operands must have the same element_type", location=location)
    if lhs_type.space != rhs_type.space:
        raise _LoweringError("Binary op operands must have the same space", location=location)
    target_shape = _infer_broadcast_shape(lhs_type.shape.data, rhs_type.shape.data, location)
    target_stride = _build_broadcast_stride(target_shape)
    return NnMemoryType(
        ArrayAttr(list(target_shape)),
        ArrayAttr(list(target_stride)),
        lhs_type.element_type,
        lhs_type.space,
    )


def _memory_to_nn_type(memory: Memory) -> NnMemoryType:
    shape = memory.shape.get_values()
    stride_values = memory.stride.get_values() if memory.stride is not None else _build_stride(shape)
    shape_attr = ArrayAttr([_dim_to_attr(dim) for dim in shape])
    stride_attr = ArrayAttr([_dim_to_attr(dim) for dim in stride_values])
    element_type = _dtype_to_xdsl(memory.dtype)
    space_name = _MEMORY_SPACE_MAP.get(memory.space, "global")
    space = NnMemorySpaceAttr.from_name(space_name)
    return NnMemoryType(shape_attr, stride_attr, element_type, space)


def _ensure_supported_statements(function_ast: FunctionAST) -> list[object]:
    statements = function_ast.body.statements
    if not statements:
        raise _LoweringError("Function body is empty", location=function_ast.location)
    for expr in statements:
        if not isinstance(
            expr,
            (BinaryExprAST, CompareExprAST, ConstAST, TensorAST, ScalarArgAST, VarAST, LoadAST, StoreAST, ForAST),
        ):
            raise _LoweringError("Unsupported AST expression for lowering", location=getattr(expr, "location", None))
    return statements


def _expect_memory_value(value: object, location: SourceLocation | None) -> NnMemoryType:
    if not isinstance(value.type, NnMemoryType):
        raise _LoweringError("Operand must be nn.memory", location=location)
    return value.type


def _expr_key(expr: object) -> int:
    return id(expr)


def _infer_expr_type(expr: object, type_map: dict[int, object]) -> object:
    expr_key = _expr_key(expr)
    if expr_key in type_map:
        return type_map[expr_key]

    if isinstance(expr, ConstAST):
        if isinstance(expr.value, int):
            type_map[expr_key] = i32
            return i32
        if isinstance(expr.value, float):
            type_map[expr_key] = f32
            return f32
        raise _LoweringError("Unsupported constant type", location=expr.location)
    if isinstance(expr, LoadAST):
        tensor_key = _expr_key(expr.tensor)
        if tensor_key not in type_map or not isinstance(type_map[tensor_key], NnMemoryType):
            raise _LoweringError("Unknown input reference", location=getattr(expr.tensor, "location", None))
        type_map[expr_key] = type_map[tensor_key]
        return type_map[tensor_key]
    if isinstance(expr, StoreAST):
        raise _LoweringError("StoreAST does not produce a value", location=expr.location)
    if isinstance(expr, ForAST):
        raise _LoweringError("ForAST does not produce a value", location=expr.location)

    if isinstance(expr, BinaryExprAST):
        lhs_type = _infer_expr_type(expr.lhs, type_map)
        rhs_type = _infer_expr_type(expr.rhs, type_map)
        if not isinstance(lhs_type, NnMemoryType) or not isinstance(rhs_type, NnMemoryType):
            raise _LoweringError("Binary op operands must have nn.memory type", location=expr.location)
        if lhs_type == rhs_type:
            type_map[expr_key] = lhs_type
            return lhs_type
        target_type = _infer_broadcast_memory_type(lhs_type, rhs_type, expr.location)
        type_map[expr_key] = target_type
        return target_type

    if isinstance(expr, CompareExprAST):
        lhs_type = _infer_expr_type(expr.lhs, type_map)
        rhs_type = _infer_expr_type(expr.rhs, type_map)
        if not isinstance(lhs_type, NnMemoryType) or not isinstance(rhs_type, NnMemoryType):
            raise _LoweringError("Compare op operands must have nn.memory type", location=expr.location)
        if lhs_type == rhs_type:
            result_type = NnMemoryType(lhs_type.shape, lhs_type.stride, i1, lhs_type.space)
            type_map[expr_key] = result_type
            return result_type
        target_type = _infer_broadcast_memory_type(lhs_type, rhs_type, expr.location)
        result_type = NnMemoryType(target_type.shape, target_type.stride, i1, target_type.space)
        type_map[expr_key] = result_type
        return result_type

    if isinstance(expr, (TensorAST, ScalarArgAST, VarAST)):
        if expr_key not in type_map:
            raise _LoweringError("Unknown input reference", location=getattr(expr, "location", None))
        return type_map[expr_key]

    raise _LoweringError("Unsupported expression for lowering", location=getattr(expr, "location", None))


def _lower_expr(expr: object, ctx: EmitContext) -> object:
    expr_key = _expr_key(expr)
    if ctx._has_cache(expr_key):
        return ctx._get_cache(expr_key)

    if isinstance(expr, (TensorAST, ScalarArgAST, VarAST)):
        if not ctx._has_cache(expr_key):
            raise _LoweringError("Unknown input reference", location=getattr(expr, "location", None))
        return ctx._get_cache(expr_key)
    if isinstance(expr, ConstAST):
        if isinstance(expr.value, int):
            attr = IntegerAttr(expr.value, i32)
            op = arith.ConstantOp(attr)
        elif isinstance(expr.value, float):
            attr = FloatAttr(expr.value, f32)
            op = arith.ConstantOp(attr)
        else:
            raise _LoweringError("Unsupported constant type", location=expr.location)
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        return op.result
    if isinstance(expr, LoadAST):
        source = _lower_expr(expr.tensor, ctx)
        source_type = _expect_memory_value(source, expr.location)
        rank = len(source_type.shape.data)
        offsets = _build_index_attrs(expr.offset, rank, ctx)
        sizes = source_type.shape
        strides = _build_stride_attrs(expr.stride, rank, ctx)
        load_op = DmaLoadOp(source, offsets, sizes, strides, source_type, source_type.space)
        ctx.builder.add_op(load_op)
        ctx._set_cache(expr_key, load_op.result)
        return load_op.result
    if isinstance(expr, StoreAST):
        raise _LoweringError("StoreAST does not produce a value", location=expr.location)

    if isinstance(expr, BinaryExprAST):
        lhs = _lower_expr(expr.lhs, ctx)
        rhs = _lower_expr(expr.rhs, ctx)
        lhs_type = _expect_memory_value(lhs, expr.location)
        rhs_type = _expect_memory_value(rhs, expr.location)
        if lhs_type != rhs_type:
            target_type = _infer_broadcast_memory_type(lhs_type, rhs_type, expr.location)
            if lhs_type != target_type:
                broadcast_op = NnBroadcastOp(lhs, target_type, target_type.space)
                ctx.builder.add_op(broadcast_op)
                lhs = broadcast_op.result
            if rhs_type != target_type:
                broadcast_op = NnBroadcastOp(rhs, target_type, target_type.space)
                ctx.builder.add_op(broadcast_op)
                rhs = broadcast_op.result
            lhs_type = target_type
        op_map = {"add": NnAddOp, "sub": NnSubOp, "mul": NnMulOp, "div": NnTrueDivOp}
        if expr.op not in op_map:
            raise _LoweringError(f"Unsupported binary op: {expr.op}", location=expr.location)
        op = op_map[expr.op](lhs, rhs, lhs_type, lhs_type.space)
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        return op.result

    if isinstance(expr, CompareExprAST):
        lhs = _lower_expr(expr.lhs, ctx)
        rhs = _lower_expr(expr.rhs, ctx)
        lhs_type = _expect_memory_value(lhs, expr.location)
        rhs_type = _expect_memory_value(rhs, expr.location)
        if lhs_type != rhs_type:
            target_type = _infer_broadcast_memory_type(lhs_type, rhs_type, expr.location)
            if lhs_type != target_type:
                broadcast_op = NnBroadcastOp(lhs, target_type, target_type.space)
                ctx.builder.add_op(broadcast_op)
                lhs = broadcast_op.result
            if rhs_type != target_type:
                broadcast_op = NnBroadcastOp(rhs, target_type, target_type.space)
                ctx.builder.add_op(broadcast_op)
                rhs = broadcast_op.result
            lhs_type = target_type
        result_type = NnMemoryType(lhs_type.shape, lhs_type.stride, i1, lhs_type.space)
        op_map = {"eq": NnEqOp, "ne": NnNeOp, "lt": NnLtOp, "le": NnLeOp, "gt": NnGtOp, "ge": NnGeOp}
        if expr.op not in op_map:
            raise _LoweringError(f"Unsupported compare op: {expr.op}", location=expr.location)
        op = op_map[expr.op](lhs, rhs, result_type, lhs_type.space)
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        return op.result

    raise _LoweringError("Unsupported expression for lowering", location=getattr(expr, "location", None))


def _lookup_symbol(node: TensorAST | ScalarArgAST | VarAST, ctx: EmitContext) -> object:
    expr_key = _expr_key(node)
    if ctx._has_cache(expr_key):
        return ctx._get_cache(expr_key)
    if node.name not in ctx.symbols:
        raise _LoweringError("Unknown input reference", location=getattr(node, "location", None))
    value = ctx.symbols[node.name]
    ctx._set_cache(expr_key, value)
    ctx.types.setdefault(expr_key, value.type)
    return value


def emit_mlir(node: object, ctx: EmitContext) -> object:
    """将单个 AST 节点发射为 MLIR value 或 op。"""

    if isinstance(node, (TensorAST, ScalarArgAST, VarAST)):
        return _lookup_symbol(node, ctx)
    if isinstance(node, (BinaryExprAST, CompareExprAST, ConstAST, LoadAST)):
        if _expr_key(node) not in ctx.types and not isinstance(node, (TensorAST, ScalarArgAST, VarAST)):
            _infer_expr_type(node, ctx.types)
        return _lower_expr(node, ctx)
    if isinstance(node, StoreAST):
        target = _lookup_symbol(node.tensor, ctx)
        target_type = _expect_memory_value(target, node.location)
        value = _lower_expr(node.value, ctx)
        value_type = _expect_memory_value(value, node.location)
        rank = len(target_type.shape.data)
        if len(value_type.shape.data) != rank:
            raise _LoweringError("Store source rank mismatch", location=node.location)
        offsets = _build_index_attrs(node.offset, rank, ctx)
        sizes = value_type.shape
        strides = _build_stride_attrs(node.stride, rank, ctx)
        store_op = DmaStoreOp(value, target, offsets, sizes, strides)
        ctx.builder.add_op(store_op)
        return store_op
    if isinstance(node, ForAST):
        loop_vars = _get_loop_vars(ctx)
        start_value = _resolve_index_expr(node.start, ctx)
        end_value = _resolve_index_expr(node.end, ctx)
        if not isinstance(start_value, int) or not isinstance(end_value, int):
            raise _LoweringError("ForAST bounds must be int", location=node.location)
        previous = loop_vars.get(node.var.name)
        base_values = ctx._snapshot_cache()
        last_value = None
        for index in range(start_value, end_value):
            loop_vars[node.var.name] = index
            ctx._restore_cache(base_values)
            for stmt in node.body.statements:
                last_value = emit_mlir(stmt, ctx)
        ctx._restore_cache(base_values)
        if previous is None:
            loop_vars.pop(node.var.name, None)
        else:
            loop_vars[node.var.name] = previous
        return last_value
    if isinstance(node, BlockAST):
        raise _LoweringError("BlockAST must be lowered via AstVisitor", location=node.location)
    if isinstance(node, FunctionAST):
        raise _LoweringError("FunctionAST must be lowered via AstVisitor", location=node.location)
    if isinstance(node, func.ReturnOp):
        return node
    raise _LoweringError("Unsupported expression for lowering", location=getattr(node, "location", None))
