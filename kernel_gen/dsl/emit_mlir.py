"""AST emit utilities for DSL nodes.

创建者: 小李飞刀
最后一次更改: 我不是牛马

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

from xdsl.dialects import arith, func, scf
from xdsl.dialects.builtin import (
    ArrayAttr,
    FloatAttr,
    Float16Type,
    IndexType,
    IntAttr,
    IntegerAttr,
    IntegerType,
    StringAttr,
    f32,
    i1,
    i32,
)
from xdsl.ir import Attribute, Block, SSAValue

from kernel_gen.dialect.arch import (
    ArchGetBlockIdOp,
    ArchGetBlockNumOp,
    ArchGetSubthreadIdOp,
    ArchGetSubthreadNumOp,
    ArchGetThreadIdOp,
)
from kernel_gen.dialect.dma import (
    DmaAllocOp,
    DmaCastOp,
    DmaCopyOp,
    DmaDesliceOp,
    DmaLoadOp,
    DmaReshapeOp,
    DmaSliceOp,
    DmaStoreOp,
    DmaViewOp,
)
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
from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolDivOp,
    SymbolEqOp,
    SymbolGeOp,
    SymbolFloorDivOp,
    SymbolForOp,
    SymbolMulOp,
    SymbolSubOp,
    SymbolValueType,
    build_public_symbol_expr,
)
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType

from .ast import (
    ArchQueryAST,
    BinaryExprAST,
    BlockAST,
    CompareExprAST,
    ConstAST,
    DmaAllocAST,
    DmaCastAST,
    DmaCopyAST,
    DmaFlattenAST,
    DmaFreeAST,
    DmaReshapeAST,
    DmaViewAST,
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

    def __init__(self: "_LoweringError", message: str, location: SourceLocation | None = None) -> None:
        super().__init__(message)
        self.location = location


class EmitContext:
    """AST 节点发射上下文。"""

    def __init__(
        self: "EmitContext",
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

    def _has_cache(self: "EmitContext", key: int) -> bool:
        return key in self._cache

    def _get_cache(self: "EmitContext", key: int) -> object | None:
        return self._cache.get(key)

    def _set_cache(self: "EmitContext", key: int, value: object) -> None:
        self._cache[key] = value

    def _setdefault_cache(self: "EmitContext", key: int, value: object) -> object:
        return self._cache.setdefault(key, value)

    def _snapshot_cache(self: "EmitContext") -> dict[int, object]:
        return dict(self._cache)

    def _restore_cache(self: "EmitContext", snapshot: dict[int, object]) -> None:
        self._cache = dict(snapshot)


def _dtype_to_xdsl(dtype: NumericType, location: SourceLocation | None = None) -> object:
    """将 NumericType 映射为 xdsl element type。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 将 DSL NumericType 转为 nn.memory 的 element_type。
    - 遇到不支持类型时抛出 LoweringError。

    使用示例:
    - _dtype_to_xdsl(NumericType.Float32)

    关联文件:
    - spec: spec/dsl/emit_mlir.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/emit_mlir.py
    """
    if dtype is NumericType.Bool:
        return i1
    if dtype is NumericType.Float16:
        return Float16Type()
    if dtype is NumericType.Float32:
        return f32
    if dtype is NumericType.Int32:
        return i32
    raise _LoweringError(f"Unsupported dtype: {dtype}", location=location)


def _xdsl_to_dtype(element_type: Attribute, location: SourceLocation | None = None) -> NumericType:
    """将 xdsl element_type 还原为 NumericType。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 支持 Float16/Float32/Int32/Bool 解析为 NumericType。
    - 不支持的 element_type 抛出 LoweringError。

    使用示例:
    - _xdsl_to_dtype(f32)

    关联文件:
    - spec: spec/dsl/emit_mlir.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/emit_mlir.py
    """
    if isinstance(element_type, Float16Type):
        return NumericType.Float16
    if element_type == f32:
        return NumericType.Float32
    if element_type == i32:
        return NumericType.Int32
    if element_type == i1:
        return NumericType.Bool
    raise _LoweringError("Unsupported element_type for nn arithmetic", location=location)


def _resolve_nn_arith_element_type(
    lhs_type: NnMemoryType,
    rhs_type: NnMemoryType,
    location: SourceLocation | None,
) -> Attribute:
    """解析 nn 算术 element_type 决议结果。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 按 Memory 算术 dtype 决议规则选择目标 element_type。
    - 无法解析时抛出 LoweringError。

    使用示例:
    - _resolve_nn_arith_element_type(lhs_type, rhs_type, location)

    关联文件:
    - spec: spec/dsl/emit_mlir.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/emit_mlir.py
    """
    try:
        lhs_dtype = _xdsl_to_dtype(lhs_type.element_type, location)
        rhs_dtype = _xdsl_to_dtype(rhs_type.element_type, location)
        target_dtype = Memory._promote_dtype(lhs_dtype, rhs_dtype)
    except TypeError as exc:
        raise _LoweringError("Binary op operands must have compatible element_type", location=location) from exc
    return _dtype_to_xdsl(target_dtype, location)


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


def _mul_symbol(dim: int | str, running: int | str) -> int | str:
    if isinstance(dim, int) and isinstance(running, int):
        return dim * running
    if isinstance(dim, int) and dim == 1:
        return running
    if isinstance(running, int) and running == 1:
        return dim
    return f"{dim}*{running}"


def _build_default_stride_attrs(shape: Sequence[Attribute]) -> list[Attribute]:
    stride_values: list[int | str] = []
    running: int | str = 1
    for dim in reversed(shape):
        stride_values.append(running)
        if isinstance(dim, IntAttr):
            running = _mul_symbol(dim.data, running)
        elif isinstance(dim, StringAttr):
            running = _mul_symbol(dim.data, running)
        else:
            running = "?"
    stride_values.reverse()
    return [_dim_to_attr(value) for value in stride_values]


def _dim_to_attr(value: int | str) -> object:
    if isinstance(value, int):
        return IntAttr(value)
    return StringAttr(value)


def _const_index(value: int, ctx: EmitContext) -> SSAValue:
    attr = IntegerAttr(value, IndexType())
    op = arith.ConstantOp(attr)
    ctx.builder.add_op(op)
    return op.result


def _ensure_index_value(value: SSAValue, ctx: EmitContext, location: SourceLocation | None) -> SSAValue:
    if isinstance(value.type, SymbolValueType):
        return value
    if isinstance(value.type, IndexType):
        return value
    if isinstance(value.type, IntegerType):
        op = arith.IndexCastOp(value, IndexType())
        ctx.builder.add_op(op)
        return op.result
    raise _LoweringError("Index operand must be integer or index", location=location)


def _resolve_index_symbol(name: str, ctx: EmitContext, location: SourceLocation | None) -> SSAValue:
    if name not in ctx.symbols:
        raise _LoweringError("Unknown index symbol", location=location)
    value = ctx.symbols[name]
    return _ensure_index_value(value, ctx, location)


def _resolve_index_operand(expr: object, ctx: EmitContext, location: SourceLocation | None) -> SSAValue:
    if isinstance(expr, ConstAST):
        if isinstance(expr.value, int):
            return _const_index(expr.value, ctx)
        if isinstance(expr.value, str):
            return _resolve_index_symbol(expr.value, ctx, expr.location)
        raise _LoweringError("Index must be int or str", location=expr.location)
    if isinstance(expr, (ScalarArgAST, VarAST)):
        value = _lookup_symbol(expr, ctx)
        return _ensure_index_value(value, ctx, expr.location)
    if isinstance(expr, int):
        return _const_index(expr, ctx)
    if isinstance(expr, str):
        return _resolve_index_symbol(expr, ctx, location)
    raise _LoweringError("Unsupported index expression", location=location or getattr(expr, "location", None))


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
    if isinstance(expr, ScalarArgAST):
        return expr.name
    if isinstance(expr, VarAST):
        loop_vars = _get_loop_vars(ctx)
        if expr.name in loop_vars:
            return loop_vars[expr.name]
        raise _LoweringError("Unknown loop variable", location=expr.location)
    if isinstance(expr, (int, str)):
        return expr
    raise _LoweringError("Unsupported index expression", location=getattr(expr, "location", None))


def _build_index_attrs(
    value: object | None,
    rank: int,
    ctx: EmitContext,
    *,
    default_value: int = 0,
    location: SourceLocation | None = None,
) -> list[SSAValue]:
    if value is None:
        values = [default_value for _ in range(rank)]
    elif isinstance(value, (list, tuple)):
        if len(value) != rank:
            raise _LoweringError("Index rank mismatch", location=location or getattr(value, "location", None))
        values = list(value)
    else:
        values = [value for _ in range(rank)]
    return [_resolve_index_operand(item, ctx, getattr(item, "location", None) or location) for item in values]


def _build_index_operands_from_layout(
    layout: ArrayAttr[Attribute],
    ctx: EmitContext,
    *,
    location: SourceLocation | None = None,
) -> list[SSAValue]:
    values: list[object] = []
    for dim in layout.data:
        if isinstance(dim, IntAttr):
            values.append(dim.data)
        elif isinstance(dim, StringAttr):
            values.append(dim.data)
        else:
            raise _LoweringError("Unsupported layout attribute", location=location)
    return [_resolve_index_operand(item, ctx, location) for item in values]


def _lower_loop_bound(expr: object, ctx: EmitContext) -> object:
    if isinstance(expr, ConstAST):
        return _lower_expr(expr, ctx)
    if isinstance(expr, (ScalarArgAST, VarAST)):
        return _lookup_symbol(expr, ctx)
    raise _LoweringError("Unsupported loop bound expression", location=getattr(expr, "location", None))


def _build_stride_attrs(
    value: object | None,
    rank: int,
    ctx: EmitContext,
    *,
    location: SourceLocation | None = None,
) -> list[SSAValue]:
    stride = _build_index_attrs(value, rank, ctx, default_value=1, location=location)
    for entry in stride:
        owner = entry.owner
        if not isinstance(owner, arith.ConstantOp) or not isinstance(owner.value, IntegerAttr):
            raise _LoweringError("Only unit stride is supported", location=location)
        if owner.value.value.data != 1:
            raise _LoweringError("Only unit stride is supported", location=location)
    return stride


def _resolve_static_index_expr(expr: object, location: SourceLocation | None = None) -> int | str:
    """解析类型推导阶段使用的索引表达式。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 支持 `ConstAST`、`ScalarArgAST`、`VarAST` 以及直接的 `int|str`。

    使用示例:
    - _resolve_static_index_expr(ScalarArgAST(name="n", value_type=int))

    关联文件:
    - spec: spec/dsl/emit_mlir.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/emit_mlir.py
    """

    if isinstance(expr, ConstAST):
        if isinstance(expr.value, (int, str)):
            return expr.value
        raise _LoweringError("Index must be int or str", location=expr.location)
    if isinstance(expr, (ScalarArgAST, VarAST)):
        return expr.name
    if isinstance(expr, (int, str)):
        return expr
    raise _LoweringError("Unsupported index expression", location=location or getattr(expr, "location", None))


def _build_static_index_list(
    value: object | None,
    rank: int,
    *,
    default_value: int,
    location: SourceLocation | None = None,
) -> list[Attribute]:
    """构造类型推导阶段使用的索引属性列表。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 将静态或符号索引表达式转成 `IntAttr/StringAttr`。

    使用示例:
    - _build_static_index_list([ScalarArgAST(name="n", value_type=int)], 1, default_value=1)

    关联文件:
    - spec: spec/dsl/emit_mlir.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/emit_mlir.py
    """

    if value is None:
        values = [default_value for _ in range(rank)]
    elif isinstance(value, (list, tuple)):
        if len(value) != rank:
            raise _LoweringError("Index rank mismatch", location=location)
        values = [_resolve_static_index_expr(entry, location) for entry in value]
    else:
        scalar = _resolve_static_index_expr(value, location)
        values = [scalar for _ in range(rank)]
    return [_dim_to_attr(item) for item in values]


def _build_static_index_attrs_exact(
    value: object,
    *,
    location: SourceLocation | None = None,
) -> list[Attribute]:
    """按显式维度列表构造静态索引属性。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 仅接受单个索引或显式索引序列，不使用默认补值。

    使用示例:
    - _build_static_index_attrs_exact([ConstAST(4), ScalarArgAST(name="n", value_type=int)])

    关联文件:
    - spec: spec/dsl/emit_mlir.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/emit_mlir.py
    """

    if isinstance(value, (list, tuple)):
        entries = [_resolve_static_index_expr(entry, location) for entry in value]
    else:
        entries = [_resolve_static_index_expr(value, location)]
    return [_dim_to_attr(entry) for entry in entries]


def _build_index_operands_exact(
    value: object,
    ctx: EmitContext,
    *,
    location: SourceLocation | None = None,
) -> list[SSAValue]:
    """按显式维度列表构造 SSA 索引操作数。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 仅接受单个索引或显式索引序列，不使用默认补值。

    使用示例:
    - _build_index_operands_exact([ConstAST(4), ScalarArgAST(name="n", value_type=int)], ctx)

    关联文件:
    - spec: spec/dsl/emit_mlir.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/emit_mlir.py
    """

    if isinstance(value, (list, tuple)):
        entries = list(value)
    else:
        entries = [value]
    return [_resolve_index_operand(entry, ctx, getattr(entry, "location", None) or location) for entry in entries]


def _memory_type_from_parts(
    shape: Sequence[Attribute],
    stride: Sequence[Attribute],
    element_type: Attribute,
    space: NnMemorySpaceAttr,
) -> NnMemoryType:
    """基于 shape/stride/element_type/space 组装内存类型。"""

    return NnMemoryType(ArrayAttr(list(shape)), ArrayAttr(list(stride)), element_type, space)


def _shape_numel_attr(shape: Sequence[Attribute]) -> Attribute:
    """根据 shape 计算一维 flatten 结果的元素总数属性。"""

    total: int | str = 1
    for dim in shape:
        if isinstance(dim, IntAttr):
            total = _mul_symbol(dim.data, total)
        elif isinstance(dim, StringAttr):
            total = _mul_symbol(dim.data, total)
        else:
            total = "?"
    return _dim_to_attr(total)


def _memory_space_from_ast(space: MemorySpace | None, fallback: NnMemorySpaceAttr) -> NnMemorySpaceAttr:
    """将 AST 中的 `MemorySpace` 映射为 nn dialect space attribute。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 未显式指定时返回 fallback。
    - 显式指定时转换到 `NnMemorySpaceAttr`。

    使用示例:
    - _memory_space_from_ast(MemorySpace.LM, source_type.space)

    关联文件:
    - spec: spec/dsl/emit_mlir.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/emit_mlir.py
    """

    if space is None:
        return fallback
    space_name = _MEMORY_SPACE_MAP.get(space, "global")
    return NnMemorySpaceAttr.from_name(space_name)


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
    return _build_default_stride_attrs(shape)


def _infer_broadcast_memory_type(
    lhs_type: NnMemoryType,
    rhs_type: NnMemoryType,
    location: SourceLocation | None,
    element_type: Attribute | None = None,
) -> NnMemoryType:
    """推导二元 broadcast 目标 memory type。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 依据隐式 broadcast 推导目标 shape 与 stride。
    - 默认要求 element_type 一致；允许显式传入 element_type 覆盖。

    使用示例:
    - _infer_broadcast_memory_type(lhs_type, rhs_type, location)

    关联文件:
    - spec: spec/dsl/emit_mlir.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/emit_mlir.py
    """
    if element_type is None and lhs_type.element_type != rhs_type.element_type:
        raise _LoweringError("Binary op operands must have the same element_type", location=location)
    if lhs_type.space != rhs_type.space:
        raise _LoweringError("Binary op operands must have the same space", location=location)
    target_element_type = element_type or lhs_type.element_type
    target_shape = _infer_broadcast_shape(lhs_type.shape.data, rhs_type.shape.data, location)
    target_stride = _build_broadcast_stride(target_shape)
    return NnMemoryType(
        ArrayAttr(list(target_shape)),
        ArrayAttr(list(target_stride)),
        target_element_type,
        lhs_type.space,
    )


def _memory_to_nn_type(memory: Memory, location: SourceLocation | None = None) -> NnMemoryType:
    shape = memory.shape.get_values()
    stride_values = memory.stride.get_values() if memory.stride is not None else _build_stride(shape)
    shape_attr = ArrayAttr([_dim_to_attr(dim) for dim in shape])
    stride_attr = ArrayAttr([_dim_to_attr(dim) for dim in stride_values])
    element_type = _dtype_to_xdsl(memory.dtype, location=location)
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
            (
                BinaryExprAST,
                CompareExprAST,
                ConstAST,
                TensorAST,
                ScalarArgAST,
                VarAST,
                LoadAST,
                StoreAST,
                DmaAllocAST,
                DmaCopyAST,
                DmaCastAST,
                DmaViewAST,
                DmaReshapeAST,
                DmaFlattenAST,
                DmaFreeAST,
                ForAST,
                ArchQueryAST,
            ),
        ):
            raise _LoweringError("Unsupported AST expression for lowering", location=getattr(expr, "location", None))
    return statements


def _expect_memory_value(value: object, location: SourceLocation | None) -> NnMemoryType:
    if not isinstance(value.type, NnMemoryType):
        raise _LoweringError("Operand must be nn.memory", location=location)
    return value.type


def _expr_key(expr: object) -> int:
    return id(expr)


def _infer_expr_type(
    expr: object,
    type_map: dict[int, object],
    runtime_values: dict[str, object] | None = None,
) -> object:
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
        source_type = type_map[tensor_key]
        rank = len(source_type.shape.data)
        if expr.sizes is None:
            shape_attr = source_type.shape
        else:
            shape_attr = ArrayAttr(_build_static_index_list(expr.sizes, rank, default_value=1, location=expr.location))
        stride_attr = ArrayAttr(_build_default_stride_attrs(shape_attr.data))
        space_attr = _memory_space_from_ast(expr.space, source_type.space)
        result_type = NnMemoryType(shape_attr, stride_attr, source_type.element_type, space_attr)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, DmaAllocAST):
        shape_attr = _build_static_index_attrs_exact(expr.shape, location=expr.location)
        stride_attr = (
            _build_static_index_attrs_exact(expr.stride, location=expr.location)
            if expr.stride is not None
            else _build_default_stride_attrs(shape_attr)
        )
        default_stride = _build_default_stride_attrs(shape_attr)
        if stride_attr != default_stride:
            raise _LoweringError("dma.alloc only supports contiguous stride", location=expr.location)
        result_type = _memory_type_from_parts(
            shape_attr,
            default_stride,
            _dtype_to_xdsl(expr.dtype, location=expr.location),
            _memory_space_from_ast(expr.space, NnMemorySpaceAttr.from_name("global")),
        )
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, DmaCopyAST):
        source_type = _infer_expr_type(expr.source, type_map)
        if not isinstance(source_type, NnMemoryType):
            raise _LoweringError("copy source must have nn.memory type", location=expr.location)
        result_type = _memory_type_from_parts(
            source_type.shape.data,
            source_type.stride.data,
            source_type.element_type,
            _memory_space_from_ast(expr.space, source_type.space),
        )
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, DmaCastAST):
        source_type = _infer_expr_type(expr.source, type_map)
        if not isinstance(source_type, NnMemoryType):
            raise _LoweringError("cast source must have nn.memory type", location=expr.location)
        result_type = _memory_type_from_parts(
            source_type.shape.data,
            source_type.stride.data,
            _dtype_to_xdsl(expr.dtype, location=expr.location),
            _memory_space_from_ast(expr.memoryspace, source_type.space),
        )
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, DmaViewAST):
        source_type = _infer_expr_type(expr.source, type_map)
        if not isinstance(source_type, NnMemoryType):
            raise _LoweringError("view source must have nn.memory type", location=expr.location)
        shape_attr = _build_static_index_attrs_exact(expr.size, location=expr.location)
        stride_attr = _build_default_stride_attrs(shape_attr)
        result_type = _memory_type_from_parts(shape_attr, stride_attr, source_type.element_type, source_type.space)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, DmaReshapeAST):
        source_type = _infer_expr_type(expr.source, type_map)
        if not isinstance(source_type, NnMemoryType):
            raise _LoweringError("reshape source must have nn.memory type", location=expr.location)
        shape_attr = _build_static_index_attrs_exact(expr.shape, location=expr.location)
        result_type = _memory_type_from_parts(
            shape_attr,
            _build_default_stride_attrs(shape_attr),
            source_type.element_type,
            source_type.space,
        )
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, DmaFlattenAST):
        source_type = _infer_expr_type(expr.source, type_map)
        if not isinstance(source_type, NnMemoryType):
            raise _LoweringError("flatten source must have nn.memory type", location=expr.location)
        shape_attr = [_shape_numel_attr(source_type.shape.data)]
        result_type = _memory_type_from_parts(shape_attr, [IntAttr(1)], source_type.element_type, source_type.space)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, StoreAST):
        raise _LoweringError("StoreAST does not produce a value", location=expr.location)
    if isinstance(expr, DmaFreeAST):
        raise _LoweringError("free does not produce a value", location=expr.location)
    if isinstance(expr, ForAST):
        raise _LoweringError("ForAST does not produce a value", location=expr.location)
    if isinstance(expr, ArchQueryAST):
        query_map = {
            "get_block_id": "block_id",
            "get_block_num": "block_num",
            "get_subthread_id": "subthread_id",
            "get_subthread_num": "subthread_num",
            "get_thread_id": "thread_id",
        }
        symbol_name = query_map.get(expr.query_name)
        if symbol_name is None:
            raise _LoweringError("Unsupported arch query", location=expr.location)
        result_type = SymbolValueType.from_expr(symbol_name)
        type_map[expr_key] = result_type
        return result_type

    if isinstance(expr, BinaryExprAST):
        lhs_type = _infer_expr_type(expr.lhs, type_map)
        rhs_type = _infer_expr_type(expr.rhs, type_map)
        if isinstance(lhs_type, SymbolValueType) and isinstance(rhs_type, SymbolValueType):
            if expr.op not in {"add", "sub", "mul", "div", "floordiv"}:
                raise _LoweringError("Unsupported symbol binary op", location=expr.location)
            lhs_expr = lhs_type.expr.expr.data
            rhs_expr = rhs_type.expr.expr.data
            op_symbol = {
                "add": "+",
                "sub": "-",
                "mul": "*",
                "div": "/",
                "floordiv": "//",
            }[expr.op]
            result_type = SymbolValueType.from_expr(build_public_symbol_expr(lhs_expr, rhs_expr, op_symbol))
            type_map[expr_key] = result_type
            return result_type
        if not isinstance(lhs_type, NnMemoryType) or not isinstance(rhs_type, NnMemoryType):
            raise _LoweringError("Binary op operands must have nn.memory type", location=expr.location)
        if lhs_type == rhs_type:
            type_map[expr_key] = lhs_type
            return lhs_type
        target_element_type = lhs_type.element_type
        if lhs_type.element_type != rhs_type.element_type:
            target_element_type = _resolve_nn_arith_element_type(lhs_type, rhs_type, expr.location)
        target_type = _infer_broadcast_memory_type(
            lhs_type,
            rhs_type,
            expr.location,
            element_type=target_element_type,
        )
        type_map[expr_key] = target_type
        return target_type

    if isinstance(expr, CompareExprAST):
        lhs_type = _infer_expr_type(expr.lhs, type_map)
        rhs_type = _infer_expr_type(expr.rhs, type_map)
        if isinstance(lhs_type, SymbolValueType) and isinstance(rhs_type, SymbolValueType):
            if expr.op not in {"eq", "ge"}:
                raise _LoweringError("Unsupported symbol compare op", location=expr.location)
            type_map[expr_key] = i1
            return i1
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
        offsets = _build_index_attrs(expr.offset, rank, ctx, location=expr.location)
        sizes = (
            _build_index_attrs(expr.sizes, rank, ctx, default_value=1, location=expr.location)
            if expr.sizes is not None
            else _build_index_operands_from_layout(source_type.shape, ctx, location=expr.location)
        )
        strides = _build_stride_attrs(expr.stride, rank, ctx, location=expr.location)
        result_type = _infer_expr_type(expr, ctx.types)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("LoadAST result must be nn.memory", location=expr.location)
        if expr.kind == "slice":
            load_op = DmaSliceOp(
                source,
                offsets,
                sizes,
                strides,
                result_type,
                _memory_space_from_ast(expr.space, source_type.space),
            )
        else:
            load_op = DmaLoadOp(
                source,
                offsets,
                sizes,
                strides,
                result_type,
                _memory_space_from_ast(expr.space, source_type.space),
            )
        ctx.builder.add_op(load_op)
        ctx._set_cache(expr_key, load_op.result)
        return load_op.result
    if isinstance(expr, DmaAllocAST):
        result_type = _infer_expr_type(expr, ctx.types)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("alloc result must be nn.memory", location=expr.location)
        shape = _build_index_operands_exact(expr.shape, ctx, location=expr.location)
        op = DmaAllocOp(shape, result_type)
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        return op.result
    if isinstance(expr, DmaCopyAST):
        source = _lower_expr(expr.source, ctx)
        source_type = _expect_memory_value(source, expr.location)
        result_type = _infer_expr_type(expr, ctx.types)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("copy result must be nn.memory", location=expr.location)
        alloc_op = DmaAllocOp(_build_index_operands_from_layout(result_type.shape, ctx, location=expr.location), result_type)
        ctx.builder.add_op(alloc_op)
        copy_op = DmaCopyOp(source, alloc_op.result)
        ctx.builder.add_op(copy_op)
        ctx._set_cache(expr_key, alloc_op.result)
        ctx.types[_expr_key(expr.source)] = source_type
        return alloc_op.result
    if isinstance(expr, DmaCastAST):
        source = _lower_expr(expr.source, ctx)
        _expect_memory_value(source, expr.location)
        result_type = _infer_expr_type(expr, ctx.types)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("cast result must be nn.memory", location=expr.location)
        op = DmaCastOp(source, result_type)
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        return op.result
    if isinstance(expr, DmaViewAST):
        source = _lower_expr(expr.source, ctx)
        _expect_memory_value(source, expr.location)
        result_type = _infer_expr_type(expr, ctx.types)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("view result must be nn.memory", location=expr.location)
        shape = _build_index_operands_exact(expr.size, ctx, location=expr.location)
        stride = _build_index_operands_from_layout(result_type.stride, ctx, location=expr.location)
        op = DmaViewOp(source, shape, stride, result_type)
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        return op.result
    if isinstance(expr, DmaReshapeAST):
        source = _lower_expr(expr.source, ctx)
        _expect_memory_value(source, expr.location)
        result_type = _infer_expr_type(expr, ctx.types)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("reshape result must be nn.memory", location=expr.location)
        shape = _build_index_operands_exact(expr.shape, ctx, location=expr.location)
        op = DmaReshapeOp(source, shape, result_type)
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        return op.result
    if isinstance(expr, DmaFlattenAST):
        source = _lower_expr(expr.source, ctx)
        source_type = _expect_memory_value(source, expr.location)
        result_type = _infer_expr_type(expr, ctx.types)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("flatten result must be nn.memory", location=expr.location)
        shape_operand = _build_index_operands_from_layout(ArrayAttr([_shape_numel_attr(source_type.shape.data)]), ctx, location=expr.location)
        op = DmaReshapeOp(source, shape_operand, result_type)
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        return op.result
    if isinstance(expr, StoreAST):
        raise _LoweringError("StoreAST does not produce a value", location=expr.location)
    if isinstance(expr, DmaFreeAST):
        raise _LoweringError("free does not produce a value", location=expr.location)
    if isinstance(expr, ArchQueryAST):
        if expr.query_name == "get_block_id":
            op = ArchGetBlockIdOp()
        elif expr.query_name == "get_block_num":
            op = ArchGetBlockNumOp()
        elif expr.query_name == "get_subthread_id":
            op = ArchGetSubthreadIdOp()
        elif expr.query_name == "get_subthread_num":
            op = ArchGetSubthreadNumOp()
        elif expr.query_name == "get_thread_id":
            op = ArchGetThreadIdOp()
        else:
            raise _LoweringError("Unsupported arch query", location=expr.location)
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        ctx.types[expr_key] = op.result.type
        return op.result

    if isinstance(expr, BinaryExprAST):
        lhs = _lower_expr(expr.lhs, ctx)
        rhs = _lower_expr(expr.rhs, ctx)
        lhs_attr = getattr(lhs, "type", None)
        rhs_attr = getattr(rhs, "type", None)
        if isinstance(lhs_attr, SymbolValueType) and isinstance(rhs_attr, SymbolValueType):
            if expr.op not in {"add", "sub", "mul", "div", "floordiv"}:
                raise _LoweringError("Unsupported symbol binary op", location=expr.location)
            result_type = _infer_expr_type(expr, ctx.types)
            if not isinstance(result_type, SymbolValueType):
                raise _LoweringError("Symbol binary op result must be !symbol.int", location=expr.location)
            op_map = {
                "add": SymbolAddOp,
                "sub": SymbolSubOp,
                "mul": SymbolMulOp,
                "div": SymbolDivOp,
                "floordiv": SymbolFloorDivOp,
            }
            op = op_map[expr.op](lhs, rhs, result_type)
            ctx.builder.add_op(op)
            ctx._set_cache(expr_key, op.result)
            return op.result
        lhs_type = _expect_memory_value(lhs, expr.location)
        rhs_type = _expect_memory_value(rhs, expr.location)
        result_type = _infer_expr_type(expr, ctx.types)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("Binary op result must be nn.memory", location=expr.location)
        target_type = result_type
        if lhs_type.element_type != target_type.element_type:
            cast_type = _memory_type_from_parts(
                lhs_type.shape.data,
                lhs_type.stride.data,
                target_type.element_type,
                lhs_type.space,
            )
            cast_op = DmaCastOp(lhs, cast_type)
            ctx.builder.add_op(cast_op)
            lhs = cast_op.result
            lhs_type = cast_type
        if rhs_type.element_type != target_type.element_type:
            cast_type = _memory_type_from_parts(
                rhs_type.shape.data,
                rhs_type.stride.data,
                target_type.element_type,
                rhs_type.space,
            )
            cast_op = DmaCastOp(rhs, cast_type)
            ctx.builder.add_op(cast_op)
            rhs = cast_op.result
            rhs_type = cast_type
        if lhs_type != target_type:
            broadcast_op = NnBroadcastOp(lhs, target_type, target_type.space)
            ctx.builder.add_op(broadcast_op)
            lhs = broadcast_op.result
            lhs_type = target_type
        if rhs_type != target_type:
            broadcast_op = NnBroadcastOp(rhs, target_type, target_type.space)
            ctx.builder.add_op(broadcast_op)
            rhs = broadcast_op.result
            rhs_type = target_type
        op_map = {"add": NnAddOp, "sub": NnSubOp, "mul": NnMulOp, "div": NnTrueDivOp}
        if expr.op not in op_map:
            raise _LoweringError(f"Unsupported binary op: {expr.op}", location=expr.location)
        op = op_map[expr.op](lhs, rhs, target_type, target_type.space)
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        return op.result

    if isinstance(expr, CompareExprAST):
        lhs = _lower_expr(expr.lhs, ctx)
        rhs = _lower_expr(expr.rhs, ctx)
        lhs_attr = getattr(lhs, "type", None)
        rhs_attr = getattr(rhs, "type", None)
        if isinstance(lhs_attr, SymbolValueType) and isinstance(rhs_attr, SymbolValueType):
            if expr.op not in {"eq", "ge"}:
                raise _LoweringError("Unsupported symbol compare op", location=expr.location)
            op_map = {"eq": SymbolEqOp, "ge": SymbolGeOp}
            op = op_map[expr.op](lhs, rhs, i1)
            ctx.builder.add_op(op)
            ctx._set_cache(expr_key, op.result)
            return op.result
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
    if isinstance(
        node,
        (
            BinaryExprAST,
            CompareExprAST,
            ConstAST,
            LoadAST,
            DmaAllocAST,
            DmaCopyAST,
            DmaCastAST,
            DmaViewAST,
            DmaReshapeAST,
            DmaFlattenAST,
            ArchQueryAST,
        ),
    ):
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
        offsets = _build_index_attrs(node.offset, rank, ctx, location=node.location)
        sizes = (
            _build_index_attrs(node.sizes, rank, ctx, default_value=1, location=node.location)
            if node.sizes is not None
            else _build_index_operands_from_layout(value_type.shape, ctx, location=node.location)
        )
        strides = _build_stride_attrs(node.stride, rank, ctx, location=node.location)
        if node.kind == "deslice":
            store_op = DmaDesliceOp(value, target, offsets, sizes, strides, target_type)
        else:
            store_op = DmaStoreOp(value, target, offsets, sizes, strides)
        ctx.builder.add_op(store_op)
        return store_op
    if isinstance(node, DmaFreeAST):
        value = _lower_expr(node.value, ctx)
        _expect_memory_value(value, node.location)
        return None
    if isinstance(node, ForAST):
        start_value = _lower_loop_bound(node.start, ctx)
        end_value = _lower_loop_bound(node.end, ctx)
        step_expr = node.step if node.step is not None else ConstAST(1, location=node.location)
        step_value = _lower_loop_bound(step_expr, ctx)
        use_symbol_for = all(
            isinstance(value.type, SymbolValueType) for value in (start_value, end_value, step_value)
        )
        if use_symbol_for:
            iter_type = SymbolValueType.from_expr(node.var.name)
            body_block = Block(arg_types=[iter_type])
            loop_op = SymbolForOp(start_value, end_value, step_value, body_block)
        else:
            body_block = Block(arg_types=[start_value.type])
            loop_op = scf.ForOp(start_value, end_value, step_value, [], body_block)
        ctx.builder.add_op(loop_op)

        nested_symbols = dict(ctx.symbols)
        induction_arg = body_block.args[0]
        nested_symbols[node.var.name] = induction_arg
        nested_ctx = EmitContext(builder=body_block, symbols=nested_symbols, types=ctx.types, config=ctx.config)
        nested_ctx._cache = ctx._snapshot_cache()
        nested_ctx._set_cache(_expr_key(node.var), induction_arg)
        nested_ctx.types[_expr_key(node.var)] = induction_arg.type

        loop_vars = _get_loop_vars(nested_ctx)
        previous = loop_vars.get(node.var.name)
        loop_vars[node.var.name] = node.var.name
        last_value = None
        for stmt in node.body.statements:
            last_value = emit_mlir(stmt, nested_ctx)
        if not use_symbol_for:
            body_block.add_op(scf.YieldOp())
        if previous is None:
            loop_vars.pop(node.var.name, None)
        else:
            loop_vars[node.var.name] = previous
        return loop_op if last_value is None else last_value
    if isinstance(node, BlockAST):
        raise _LoweringError("BlockAST must be lowered via AstVisitor", location=node.location)
    if isinstance(node, FunctionAST):
        raise _LoweringError("FunctionAST must be lowered via AstVisitor", location=node.location)
    if isinstance(node, func.ReturnOp):
        return node
    raise _LoweringError("Unsupported expression for lowering", location=getattr(node, "location", None))
