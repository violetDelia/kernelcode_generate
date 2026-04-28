"""Emit nn elementwise family helper.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 收口 `emit_mlir(...)` 的 nn family 内部拆分实现，覆盖 unary/binary/compare 三类 AST。
- 当前文件只承载 emit 内部拆分逻辑，对外公开入口仍是 `EmitContext(...)` / `emit_mlir(node, ctx)`。

API 列表:
- 无；当前文件仅提供 `emit_mlir(node, ctx)` 的 nn family 内部拆分实现。

使用示例:
- value = emit_mlir(NnUnaryAST(kind="relu", value=tensor), ctx)

关联文件:
- spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
- test: [test/dsl/mlir_gen/emit/test_call_nn.py](test/dsl/mlir_gen/emit/test_call_nn.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/emit/call_nn.py](kernel_gen/dsl/mlir_gen/emit/call_nn.py)
"""

from __future__ import annotations

from xdsl.dialects import arith
from xdsl.dialects.builtin import (
    ArrayAttr,
    Attribute,
    BFloat16Type,
    Float16Type,
    Float32Type,
    Float64Type,
    IntAttr,
    IntegerAttr,
    IntegerType,
    Signedness,
    StringAttr,
    f32,
    i1,
    i8,
    i32,
    i64,
)
from xdsl.ir import SSAValue

from kernel_gen.dialect.nn import (
    NnAddOp,
    NnBroadcastOp,
    NnCastOp,
    NnEqOp,
    NnExpOp,
    NnFloorDivOp,
    NnGeOp,
    NnGtOp,
    NnHardSigmoidOp,
    NnLeakyReluOp,
    NnLeOp,
    NnLtOp,
    NnMemorySpaceAttr,
    NnMemoryType,
    NnMulOp,
    NnNeOp,
    NnReluOp,
    NnSigmoidOp,
    NnSubOp,
    NnTanhOp,
    NnTrueDivOp,
)
from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolConstOp,
    SymbolDivOp,
    SymbolEqOp,
    SymbolFloorDivOp,
    SymbolGeOp,
    SymbolGtOp,
    SymbolLeOp,
    SymbolLtOp,
    SymbolMulOp,
    SymbolNeOp,
    SymbolSubOp,
    SymbolToFloatOp,
    SymbolToIntOp,
    SymbolValueType,
    build_public_symbol_expr,
)
from kernel_gen.dsl.ast import (
    BinaryExprAST,
    CompareExprAST,
    ConstAST,
    DmaReshapeAST,
    MatmulAST,
    NnBroadcastToAST,
    NnReduceAST,
    NnTransposeAST,
    NnUnaryAST,
    ScalarArgAST,
    SourceLocation,
    TensorAST,
    TensorAxisAccessAST,
    VarAST,
)
from kernel_gen.operation import dma as _KG_OPERATION_DMA
from kernel_gen.operation import nn as _KG_OPERATION_NN
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

from .context import EmitContext


class LoweringError(ValueError):
    """当前文件内使用的 nn emit 失败错误。"""

    def __init__(self, message: str, location: SourceLocation | None = None) -> None:
        super().__init__(message)
        self.location = location

_LoweringError = LoweringError
_ARITHMETIC_DTYPE_RANK = {
    NumericType.Int8: 0,
    NumericType.Uint8: 1,
    NumericType.Int16: 2,
    NumericType.Uint16: 3,
    NumericType.Int32: 4,
    NumericType.Uint32: 5,
    NumericType.Int64: 6,
    NumericType.Uint64: 7,
    NumericType.Float16: 8,
    NumericType.BFloat16: 9,
    NumericType.Float32: 10,
    NumericType.Float64: 11,
}


def _expr_key(expr: object) -> int:
    return id(expr)


def _infer_expr_type(
    expr: object,
    type_map: dict[int, object],
    runtime_values: dict[str, object] | None = None,
    config: dict[str, object] | None = None,
) -> object:
    """推导公开 nn/dma 复合表达式的结果类型。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 为 `infer_nn_type(...)` 内部递归提供统一类型入口，覆盖常量、symbol 标量、memory 轴访问与当前公开 helper 复合 AST。
    - 对 `reshape/transpose/matmul/reduce/broadcast_to` 这类公开 helper，复用公开 operation API 做结果类型推导。

    使用示例:
    - result_type = _infer_expr_type(expr, type_map, runtime_values=runtime_values, config=config)
    """

    expr_key = _expr_key(expr)
    if expr_key in type_map:
        return type_map[expr_key]
    if runtime_values is None and isinstance(config, dict):
        candidate_runtime_values = config.get("__runtime_values__")
        if isinstance(candidate_runtime_values, dict):
            runtime_values = candidate_runtime_values
    if isinstance(expr, ConstAST):
        result_type: object
        if isinstance(expr.value, int):
            result_type = i32
        elif isinstance(expr.value, float):
            result_type = f32
        else:
            raise _LoweringError("Unsupported constant type", location=expr.location)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, (TensorAST, ScalarArgAST, VarAST)):
        if expr_key not in type_map:
            raise _LoweringError("Unknown input reference", location=getattr(expr, "location", None))
        return type_map[expr_key]
    if isinstance(expr, TensorAxisAccessAST):
        if not isinstance(expr.axis, ConstAST) or not isinstance(expr.axis.value, int):
            raise _LoweringError("Unsupported AST expression for lowering", location=expr.location)
        dims = expr.tensor.memory.shape if expr.kind == "shape" else expr.tensor.memory.stride
        dim_value = dims[expr.axis.value].get_value()
        result_type = SymbolValueType.from_expr(dim_value if isinstance(dim_value, str) else str(dim_value))
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, DmaReshapeAST):
        source_type = _emit_infer_expr_type(expr.source, type_map, runtime_values=runtime_values, config=config)
        if not isinstance(source_type, NnMemoryType):
            raise _LoweringError("reshape source must have nn.memory type", location=expr.location)
        source_memory = _nn_memory_type_to_memory(source_type, location=expr.location)
        result_memory = _KG_OPERATION_DMA.reshape(
            source_memory,
            _resolve_public_shape_values(expr.shape, type_map, runtime_values, config, expr.location),
        )
        result_type = _memory_to_nn_type(result_memory, location=expr.location)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, NnTransposeAST):
        value_type = _emit_infer_expr_type(expr.value, type_map, runtime_values=runtime_values, config=config)
        if not isinstance(value_type, NnMemoryType):
            raise _LoweringError("transpose source must have nn.memory type", location=expr.location)
        result_memory = _KG_OPERATION_NN.transpose(
            _nn_memory_type_to_memory(value_type, location=expr.location),
            _resolve_static_int_list(expr.perm, expr.location),
        )
        result_type = _memory_to_nn_type(result_memory, location=expr.location)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, MatmulAST):
        lhs_type = _emit_infer_expr_type(expr.lhs, type_map, runtime_values=runtime_values, config=config)
        rhs_type = _emit_infer_expr_type(expr.rhs, type_map, runtime_values=runtime_values, config=config)
        if not isinstance(lhs_type, NnMemoryType) or not isinstance(rhs_type, NnMemoryType):
            raise _LoweringError("matmul operands must have nn.memory type", location=expr.location)
        result_memory = _KG_OPERATION_NN.matmul(
            _nn_memory_type_to_memory(lhs_type, location=expr.location),
            _nn_memory_type_to_memory(rhs_type, location=expr.location),
            expr.memoryspace,
        )
        result_type = _memory_to_nn_type(result_memory, location=expr.location)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, NnReduceAST):
        value_type = _emit_infer_expr_type(expr.value, type_map, runtime_values=runtime_values, config=config)
        if not isinstance(value_type, NnMemoryType):
            raise _LoweringError("reduce source must have nn.memory type", location=expr.location)
        reduce_fn_map = {
            "reduce_sum": _KG_OPERATION_NN.reduce_sum,
            "reduce_min": _KG_OPERATION_NN.reduce_min,
            "reduce_max": _KG_OPERATION_NN.reduce_max,
        }
        reduce_fn = reduce_fn_map.get(expr.kind)
        if reduce_fn is None:
            raise _LoweringError("Unsupported AST expression for lowering", location=expr.location)
        axis = None if expr.axis is None else _resolve_static_int(expr.axis, expr.location)
        keepdim = False if expr.keepdim is None else _resolve_static_bool(expr.keepdim, expr.location)
        result_memory = reduce_fn(
            _nn_memory_type_to_memory(value_type, location=expr.location),
            axis=axis,
            keepdim=keepdim,
        )
        result_type = _memory_to_nn_type(result_memory, location=expr.location)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, NnBroadcastToAST):
        source_type = _emit_infer_expr_type(expr.source, type_map, runtime_values=runtime_values, config=config)
        if not isinstance(source_type, NnMemoryType):
            raise _LoweringError("broadcast_to source must have nn.memory type", location=expr.location)
        result_memory = _KG_OPERATION_NN.broadcast_to(
            _nn_memory_type_to_memory(source_type, location=expr.location),
            _resolve_public_shape_values(expr.target_shape, type_map, runtime_values, config, expr.location),
            expr.space,
        )
        result_type = _memory_to_nn_type(result_memory, location=expr.location)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, (NnUnaryAST, BinaryExprAST, CompareExprAST)):
        return infer_nn_type(expr, type_map, runtime_values=runtime_values, config=config)
    raise _LoweringError("Unsupported AST expression for lowering", location=getattr(expr, "location", None))


_emit_infer_expr_type = _infer_expr_type


def _emit_lower_expr(expr: object, ctx: EmitContext) -> SSAValue:
    from .dispatch import emit_mlir

    value = emit_mlir(expr, ctx)
    if not isinstance(value, SSAValue):
        raise LoweringError("Unsupported expression for lowering", location=getattr(expr, "location", None))
    return value


def _const_symbol_int(value: int, ctx: EmitContext, location: SourceLocation | None) -> SSAValue:
    del location
    op = SymbolConstOp(value)
    ctx.builder.add_op(op)
    return op.result


def _expect_memory_value(value: object, location: SourceLocation | None) -> NnMemoryType:
    if not isinstance(getattr(value, "type", None), NnMemoryType):
        raise LoweringError("Operand must be nn.memory", location=location)
    return value.type


def _dtype_to_xdsl(dtype: NumericType, location: SourceLocation | None) -> Attribute:
    if dtype is NumericType.Bool:
        return i1
    if dtype is NumericType.Int8:
        return i8
    if dtype is NumericType.Int32:
        return i32
    if dtype is NumericType.Int64:
        return i64
    if dtype is NumericType.BFloat16:
        return BFloat16Type()
    if dtype is NumericType.Float16:
        return Float16Type()
    if dtype is NumericType.Float32:
        return f32
    if dtype is NumericType.Float64:
        return Float64Type()
    raise LoweringError("Unsupported element_type for nn arithmetic", location=location)


def _xdsl_to_dtype(element_type: Attribute, location: SourceLocation | None) -> NumericType:
    if isinstance(element_type, BFloat16Type):
        return NumericType.BFloat16
    if isinstance(element_type, Float16Type):
        return NumericType.Float16
    if element_type == f32:
        return NumericType.Float32
    if isinstance(element_type, Float64Type):
        return NumericType.Float64
    if element_type == i1:
        return NumericType.Bool
    if isinstance(element_type, IntegerType):
        width = element_type.width.data
        signedness = element_type.signedness.data
        if signedness == Signedness.UNSIGNED:
            if width == 8:
                return NumericType.Uint8
            if width == 16:
                return NumericType.Uint16
            if width == 32:
                return NumericType.Uint32
            if width == 64:
                return NumericType.Uint64
        if width == 8:
            return NumericType.Int8
        if width == 16:
            return NumericType.Int16
        if width == 32:
            return NumericType.Int32
        if width == 64:
            return NumericType.Int64
    raise LoweringError("Unsupported element_type for nn arithmetic", location=location)


def _promote_ranked_dtype(lhs: NumericType, rhs: NumericType) -> NumericType:
    """按 nn emit 当前公开算术优先级选择更高 rank 的 dtype。"""

    if lhs not in _ARITHMETIC_DTYPE_RANK or rhs not in _ARITHMETIC_DTYPE_RANK:
        raise TypeError("Memory dtype mismatch")
    return lhs if _ARITHMETIC_DTYPE_RANK[lhs] >= _ARITHMETIC_DTYPE_RANK[rhs] else rhs


def _resolve_nn_arith_element_type(
    lhs_type: NnMemoryType,
    rhs_type: NnMemoryType,
    location: SourceLocation | None,
) -> Attribute:
    try:
        lhs_dtype = _xdsl_to_dtype(lhs_type.element_type, location)
        rhs_dtype = _xdsl_to_dtype(rhs_type.element_type, location)
        target_dtype = _promote_ranked_dtype(lhs_dtype, rhs_dtype)
    except TypeError as exc:
        raise LoweringError("Binary op operands must have compatible element_type", location=location) from exc
    return _dtype_to_xdsl(target_dtype, location)


def _resolve_runtime_scalar_value(
    expr: object,
    inferred_type: Attribute | None,
    runtime_values: dict[str, object] | None = None,
) -> object | None:
    if isinstance(expr, ConstAST) and isinstance(expr.value, (int, float, bool)):
        return expr.value
    if isinstance(expr, ScalarArgAST):
        if runtime_values is not None and expr.name in runtime_values:
            return runtime_values[expr.name]
        if expr.is_symbolic:
            return SymbolDim(expr.name)
    if isinstance(inferred_type, SymbolValueType):
        return SymbolDim(inferred_type.expr.expr.data)
    if isinstance(inferred_type, IntegerType):
        return 0
    if isinstance(inferred_type, (Float16Type, BFloat16Type, Float32Type, Float64Type)):
        return 0.0
    return None


def _shape_attr_to_symbol_dim(attr: Attribute, location: SourceLocation | None) -> SymbolDim | None:
    if isinstance(attr, IntAttr):
        return SymbolDim(attr.data)
    if isinstance(attr, StringAttr):
        if attr.data == "?":
            return None
        return SymbolDim(attr.data)
    raise LoweringError("Unsupported shape attribute", location=location)


def _resolve_static_int(expr: object, location: SourceLocation | None) -> int:
    """解析公开 AST 整数字面量。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 只接受 `ConstAST(int)` 且显式排除 `bool`。
    - 为 `reduce axis`、`transpose perm` 等需要静态整数的公开 helper 提供统一校验。

    使用示例:
    - axis = _resolve_static_int(ConstAST(1, location=None), location=None)
    """

    if isinstance(expr, ConstAST) and isinstance(expr.value, int) and not isinstance(expr.value, bool):
        return expr.value
    raise LoweringError("Unsupported AST expression for lowering", location=location or getattr(expr, "location", None))


def _resolve_static_bool(expr: object, location: SourceLocation | None) -> bool:
    """解析公开 AST 布尔字面量。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 只接受 `ConstAST(bool)`。
    - 为 `keepdim` 这类公开 keyword 参数提供统一校验。

    使用示例:
    - keepdim = _resolve_static_bool(ConstAST(True, location=None), location=None)
    """

    if isinstance(expr, ConstAST) and isinstance(expr.value, bool):
        return expr.value
    raise LoweringError("Unsupported AST expression for lowering", location=location or getattr(expr, "location", None))


def _resolve_static_int_list(values: list[object], location: SourceLocation | None) -> list[int]:
    """解析静态整数列表。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 逐项复用 `_resolve_static_int(...)`。
    - 供 `transpose perm` 这类公开整型列表参数复用。

    使用示例:
    - perm = _resolve_static_int_list([ConstAST(1, None), ConstAST(0, None)], location=None)
    """

    return [_resolve_static_int(value, location) for value in values]


def _resolve_public_shape_values(
    values: list[object],
    type_map: dict[int, object],
    runtime_values: dict[str, object] | None,
    config: dict[str, object] | None,
    location: SourceLocation | None,
) -> list[int | SymbolDim]:
    """解析公开 shape 列表为 `int | SymbolDim`。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 支持 `ConstAST(int)`、公开 `SymbolValueType`、runtime `SymbolDim/int` 与 tensor 轴访问。
    - 为 `reshape` / `broadcast_to` 这类公开 helper 统一提供 shape 参数归一。

    使用示例:
    - shape = _resolve_public_shape_values(expr.shape, type_map, runtime_values, config, expr.location)
    """

    resolved: list[int | SymbolDim] = []
    for value in values:
        inferred_type = _emit_infer_expr_type(value, type_map, runtime_values=runtime_values, config=config)
        runtime_value = _resolve_runtime_scalar_value(value, inferred_type, runtime_values)
        if isinstance(runtime_value, (int, SymbolDim)) and not isinstance(runtime_value, bool):
            resolved.append(runtime_value)
            continue
        if isinstance(inferred_type, SymbolValueType):
            resolved.append(SymbolDim(inferred_type.expr.expr.data))
            continue
        raise LoweringError("Unsupported AST expression for lowering", location=location or getattr(value, "location", None))
    return resolved


def _space_attr_from_memory_space(space: MemorySpace) -> NnMemorySpaceAttr:
    return NnMemorySpaceAttr.from_name(
        {
            MemorySpace.GM: "global",
            MemorySpace.SM: "shared",
            MemorySpace.LM: "local",
            MemorySpace.TSM: "tsm",
            MemorySpace.TLM1: "tlm1",
            MemorySpace.TLM2: "tlm2",
            MemorySpace.TLM3: "tlm3",
        }[space]
    )


def _memory_to_nn_type(memory: Memory, location: SourceLocation | None = None) -> NnMemoryType:
    del location
    return _memory_type_from_parts(
        [_dim_to_attr(dim) for dim in memory.get_shape()],
        [_dim_to_attr(dim) for dim in memory.get_stride()],
        _dtype_to_xdsl(memory.get_type(), None),
        _space_attr_from_memory_space(memory.get_space()),
    )


def _memory_type_from_parts(
    shape: list[Attribute] | tuple[Attribute, ...] | ArrayAttr,
    stride: list[Attribute] | tuple[Attribute, ...] | ArrayAttr,
    element_type: Attribute,
    space: NnMemorySpaceAttr,
) -> NnMemoryType:
    shape_seq = list(shape.data) if isinstance(shape, ArrayAttr) else list(shape)
    stride_seq = list(stride.data) if isinstance(stride, ArrayAttr) else list(stride)
    return NnMemoryType(ArrayAttr(shape_seq), ArrayAttr(stride_seq), element_type, space)


def _nn_memory_type_to_memory(memory_type: NnMemoryType, location: SourceLocation | None = None) -> Memory:
    shape: list[SymbolDim] = []
    for dim_attr in memory_type.shape.data:
        dim_symbol = _shape_attr_to_symbol_dim(dim_attr, location)
        if dim_symbol is None:
            raise LoweringError("nn.memory shape contains unknown dimension", location=location)
        shape.append(dim_symbol)
    stride: list[SymbolDim] = []
    for dim_attr in memory_type.stride.data:
        dim_symbol = _shape_attr_to_symbol_dim(dim_attr, location)
        if dim_symbol is None:
            raise LoweringError("nn.memory stride contains unknown dimension", location=location)
        stride.append(dim_symbol)
    dtype = _xdsl_to_dtype(memory_type.element_type, location)
    space_map = {
        "global": MemorySpace.GM,
        "shared": MemorySpace.SM,
        "local": MemorySpace.LM,
        "tsm": MemorySpace.TSM,
        "tlm1": MemorySpace.TLM1,
        "tlm2": MemorySpace.TLM2,
        "tlm3": MemorySpace.TLM3,
    }
    space = space_map.get(memory_type.space.space.data)
    if space is None:
        raise LoweringError("Unsupported nn.memory space", location=location)
    return Memory(shape, dtype, space=space, stride=stride)


def _dims_equal(lhs: Attribute, rhs: Attribute) -> bool:
    if isinstance(lhs, IntAttr) and isinstance(rhs, IntAttr):
        return lhs.data == rhs.data
    if isinstance(lhs, StringAttr) and isinstance(rhs, StringAttr):
        return lhs.data == rhs.data
    return False


def _dim_to_attr(value: int | str | SymbolDim) -> IntAttr | StringAttr:
    if isinstance(value, SymbolDim):
        value = value.get_value()
    if isinstance(value, int):
        return IntAttr(value)
    return StringAttr(str(value))


def _build_default_stride_attrs(shape: list[Attribute]) -> list[Attribute]:
    stride_values: list[int | str] = []
    running: SymbolDim | None = SymbolDim(1)
    for dim_attr in reversed(shape):
        if running is None:
            stride_values.append("?")
            continue
        stride_values.append(running.get_value())
        dim_symbol = _shape_attr_to_symbol_dim(dim_attr, None)
        if dim_symbol is None:
            running = None
        else:
            running = dim_symbol * running
    stride_values.reverse()
    return [_dim_to_attr(value) for value in stride_values]


def _infer_broadcast_shape(
    lhs_shape: list[Attribute],
    rhs_shape: list[Attribute],
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
            raise LoweringError("Implicit broadcast dimension mismatch", location=location)
        if isinstance(rhs_dim, StringAttr) and rhs_dim.data == "?":
            if _dims_equal(lhs_dim, rhs_dim):
                result.insert(0, rhs_dim)
                continue
            raise LoweringError("Implicit broadcast dimension mismatch", location=location)
        if _dims_equal(lhs_dim, rhs_dim):
            result.insert(0, lhs_dim)
            continue
        if isinstance(lhs_dim, IntAttr) and lhs_dim.data == 1:
            result.insert(0, rhs_dim)
            continue
        if isinstance(rhs_dim, IntAttr) and rhs_dim.data == 1:
            result.insert(0, lhs_dim)
            continue
        raise LoweringError("Implicit broadcast dimension mismatch", location=location)
    return result


def _infer_broadcast_memory_type(
    lhs_type: NnMemoryType,
    rhs_type: NnMemoryType,
    location: SourceLocation | None,
    element_type: Attribute | None = None,
) -> NnMemoryType:
    if element_type is None and lhs_type.element_type != rhs_type.element_type:
        raise LoweringError("Binary op operands must have the same element_type", location=location)
    if lhs_type.space != rhs_type.space:
        raise LoweringError("Binary op operands must have the same space", location=location)
    target_shape = _infer_broadcast_shape(list(lhs_type.shape.data), list(rhs_type.shape.data), location)
    target_stride = _build_default_stride_attrs(target_shape)
    return _memory_type_from_parts(target_shape, target_stride, element_type or lhs_type.element_type, lhs_type.space)


def infer_nn_type(
    node: object,
    type_map: dict[str, object],
    runtime_values: dict[str, object] | None = None,
    config: dict[str, object] | None = None,
) -> object:
    """推导 nn elementwise family 的结果类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅处理 `NnUnaryAST`、`BinaryExprAST`、`CompareExprAST`。
    - 对外暴露 elementwise 的统一类型推导入口，供 facade 与函数级入口复用。

    使用示例:
    - result_type = infer_nn_type(BinaryExprAST(op="add", lhs=lhs, rhs=rhs), type_map)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/call_nn.py](kernel_gen/dsl/mlir_gen/emit/call_nn.py)
    """

    if isinstance(node, NnUnaryAST):
        return _infer_unary_type(node, type_map, runtime_values=runtime_values, config=config)
    if isinstance(node, BinaryExprAST):
        return _infer_binary_type(node, type_map, runtime_values=runtime_values, config=config)
    if isinstance(node, CompareExprAST):
        return _infer_compare_type(node, type_map, runtime_values=runtime_values, config=config)
    raise LoweringError("infer_nn_type only handles nn elementwise AST nodes", location=getattr(node, "location", None))


def emit_nn_call(node: object, ctx: EmitContext) -> object:
    """发射 nn elementwise family AST。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅接受 `NnUnaryAST`、`BinaryExprAST`、`CompareExprAST`。
    - 统一承接 unary/binary/compare 的 lowering 规则，作为 facade 的长期实现归属。

    使用示例:
    - value = emit_nn_call(BinaryExprAST(op="add", lhs=lhs, rhs=rhs), ctx)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/emit/test_call_nn.py](test/dsl/mlir_gen/emit/test_call_nn.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/call_nn.py](kernel_gen/dsl/mlir_gen/emit/call_nn.py)
    """

    if isinstance(node, NnUnaryAST):
        return _emit_unary(node, ctx)
    if isinstance(node, BinaryExprAST):
        return _emit_binary(node, ctx)
    if isinstance(node, CompareExprAST):
        return _emit_compare(node, ctx)
    raise LoweringError("emit_nn_call only handles nn elementwise AST nodes", location=getattr(node, "location", None))


def _infer_unary_type(
    expr: NnUnaryAST,
    type_map: dict[str, object],
    runtime_values: dict[str, object] | None,
    config: dict[str, object] | None,
) -> NnMemoryType:
    value_type = _emit_infer_expr_type(expr.value, type_map, runtime_values=runtime_values, config=config)
    if not isinstance(value_type, NnMemoryType):
        raise _LoweringError("Unary op operand must be nn.memory", location=expr.location)
    input_memory = _nn_memory_type_to_memory(value_type, location=expr.location)
    if expr.kind == "leaky_relu":
        alpha_type = (
            _emit_infer_expr_type(expr.alpha, type_map, runtime_values=runtime_values, config=config)
            if expr.alpha is not None
            else f32
        )
        alpha_value = (
            _resolve_runtime_scalar_value(expr.alpha, alpha_type, runtime_values) if expr.alpha is not None else 0.01
        )
        output_memory = _KG_OPERATION_NN.leaky_relu(input_memory, alpha=0.01 if alpha_value is None else alpha_value)
    elif expr.kind == "hard_sigmoid":
        alpha_type = (
            _emit_infer_expr_type(expr.alpha, type_map, runtime_values=runtime_values, config=config)
            if expr.alpha is not None
            else f32
        )
        beta_type = (
            _emit_infer_expr_type(expr.beta, type_map, runtime_values=runtime_values, config=config)
            if expr.beta is not None
            else f32
        )
        alpha_value = (
            _resolve_runtime_scalar_value(expr.alpha, alpha_type, runtime_values) if expr.alpha is not None else 0.2
        )
        beta_value = (
            _resolve_runtime_scalar_value(expr.beta, beta_type, runtime_values) if expr.beta is not None else 0.5
        )
        output_memory = _KG_OPERATION_NN.hard_sigmoid(
            input_memory,
            alpha=0.2 if alpha_value is None else alpha_value,
            beta=0.5 if beta_value is None else beta_value,
        )
    else:
        unary_map = {
            "relu": _KG_OPERATION_NN.relu,
            "sigmoid": _KG_OPERATION_NN.sigmoid,
            "tanh": _KG_OPERATION_NN.tanh,
            "exp": _KG_OPERATION_NN.exp,
        }
        unary_fn = unary_map.get(expr.kind)
        if unary_fn is None:
            raise _LoweringError("Unsupported unary helper", location=expr.location)
        output_memory = unary_fn(input_memory)
    return _memory_to_nn_type(output_memory, location=expr.location)


def _infer_binary_type(
    expr: BinaryExprAST,
    type_map: dict[str, object],
    runtime_values: dict[str, object] | None,
    config: dict[str, object] | None,
) -> object:
    """推导 nn binary family 的结果类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一处理 `add/sub/mul/div/floordiv` 的 memory、mixed scalar 与纯 symbol 标量三条路径。
    - 当 `runtime_values` 提供 `int|SymbolDim` 时，纯标量 binary 会收口为公开 `SymbolValueType` 表达式。
    - mixed memory/scalar 路径继续复用 `nn` operation API 的 dtype/shape 语义。

    使用示例:
    - result_type = _infer_binary_type(BinaryExprAST(op="add", lhs=lhs, rhs=rhs), type_map, runtime_values, config)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/call_nn.py](kernel_gen/dsl/mlir_gen/emit/call_nn.py)
    """

    lhs_type = _emit_infer_expr_type(expr.lhs, type_map, runtime_values=runtime_values, config=config)
    rhs_type = _emit_infer_expr_type(expr.rhs, type_map, runtime_values=runtime_values, config=config)
    expr_key = _expr_key(expr)
    lhs_symbol_expr = _symbol_scalar_expr_text(expr.lhs, lhs_type, runtime_values)
    rhs_symbol_expr = _symbol_scalar_expr_text(expr.rhs, rhs_type, runtime_values)
    if lhs_symbol_expr is not None and rhs_symbol_expr is not None:
        if expr.op not in {"add", "sub", "mul", "div", "floordiv"}:
            raise _LoweringError("Unsupported symbol binary op", location=expr.location)
        op_symbol = {"add": "+", "sub": "-", "mul": "*", "div": "/", "floordiv": "//"}[expr.op]
        result_type = SymbolValueType.from_expr(build_public_symbol_expr(lhs_symbol_expr, rhs_symbol_expr, op_symbol))
        type_map[expr_key] = result_type
        return result_type
    nn_binary_map = {
        "add": _KG_OPERATION_NN.add,
        "sub": _KG_OPERATION_NN.sub,
        "mul": _KG_OPERATION_NN.mul,
        "div": _KG_OPERATION_NN.truediv,
        "floordiv": _KG_OPERATION_NN.floordiv,
    }
    binary_fn = nn_binary_map.get(expr.op)
    if binary_fn is None:
        raise _LoweringError(f"Unsupported binary op: {expr.op}", location=expr.location)
    lhs_is_memory = isinstance(lhs_type, NnMemoryType)
    rhs_is_memory = isinstance(rhs_type, NnMemoryType)
    if not lhs_is_memory and not rhs_is_memory:
        if expr.op == "add":
            raise _LoweringError("nn.add requires at least one nn.memory operand", location=expr.location)
        raise _LoweringError("Binary op operands must have nn.memory type", location=expr.location)
    if lhs_is_memory != rhs_is_memory and (isinstance(lhs_type, SymbolValueType) or isinstance(rhs_type, SymbolValueType)):
        memory_type = lhs_type if lhs_is_memory else rhs_type
        if not isinstance(memory_type, NnMemoryType):
            raise _LoweringError("Binary op operands must have nn.memory type", location=expr.location)
        type_map[expr_key] = memory_type
        return memory_type
    if lhs_is_memory != rhs_is_memory:
        memory_type = lhs_type if lhs_is_memory else rhs_type
        scalar_type = rhs_type if lhs_is_memory else lhs_type
        if not isinstance(memory_type, NnMemoryType) or not isinstance(scalar_type, Attribute):
            raise _LoweringError("Binary op operands must have nn.memory type", location=expr.location)
        result_type = _infer_mixed_binary_type(memory_type, scalar_type, expr.location, op_name=expr.op)
        type_map[expr_key] = result_type
        return result_type
    lhs_value = (
        _nn_memory_type_to_memory(lhs_type, location=expr.location)
        if isinstance(lhs_type, NnMemoryType)
        else _resolve_runtime_scalar_value(expr.lhs, lhs_type, runtime_values)
    )
    rhs_value = (
        _nn_memory_type_to_memory(rhs_type, location=expr.location)
        if isinstance(rhs_type, NnMemoryType)
        else _resolve_runtime_scalar_value(expr.rhs, rhs_type, runtime_values)
    )
    if lhs_value is None or rhs_value is None:
        if expr.op == "add":
            raise _LoweringError("nn.add requires at least one nn.memory operand", location=expr.location)
        raise _LoweringError("Binary op operands must have nn.memory type", location=expr.location)
    output_memory = binary_fn(lhs_value, rhs_value)
    if not isinstance(output_memory, Memory):
        raise _LoweringError("nn.add requires at least one nn.memory operand", location=expr.location)
    result_type = _memory_to_nn_type(output_memory, location=expr.location)
    type_map[expr_key] = result_type
    return result_type


def _normalize_mixed_scalar_element_type(scalar_type: Attribute, location: SourceLocation | None) -> Attribute:
    """规范化 mixed scalar 路径允许的标量 element type。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 收口 `nn` mixed memory-scalar 路径当前公开支持的标量类型集合。
    - 统一拒绝 `i32/f16/bf16/f32/f64/symbol.int` 之外的 element type，避免后续推导走出合同。

    使用示例:
    - scalar_type = _normalize_mixed_scalar_element_type(i32, expr.location)

    关联文件:
    - spec: spec/dsl/mlir_gen.md
    - test: test/dsl/mlir_gen/emit/test_call_nn.py
    - 功能实现: kernel_gen/dsl/mlir_gen/emit/call_nn.py
    """

    if isinstance(scalar_type, SymbolValueType):
        return scalar_type
    if scalar_type == i32:
        return scalar_type
    if isinstance(scalar_type, (Float16Type, BFloat16Type, Float32Type, Float64Type)):
        return scalar_type
    raise _LoweringError("nn.add scalar element_type must be i32/f16/f32 or symbol.int", location=location)


def _symbol_scalar_expr_text(
    expr: object,
    inferred_type: object,
    runtime_values: dict[str, object] | None,
) -> str | None:
    """解析纯标量 binary expr 的公开 symbol 表达式文本。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 `ConstAST(int)`、runtime `int`、`SymbolDim` 与 `!symbol.int` 输入。
    - 供纯标量 `add/sub/mul/div/floordiv` 分支统一决定是否走 `symbol.*` lowering。

    使用示例:
    - expr_text = _symbol_scalar_expr_text(ConstAST(4), i32, runtime_values=None)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/call_nn.py](kernel_gen/dsl/mlir_gen/emit/call_nn.py)
    """

    if isinstance(inferred_type, SymbolValueType):
        return inferred_type.expr.expr.data
    if isinstance(expr, ConstAST) and isinstance(expr.value, int) and not isinstance(expr.value, bool):
        return str(expr.value)
    if isinstance(expr, ScalarArgAST) and runtime_values is not None and expr.name in runtime_values:
        runtime_value = runtime_values[expr.name]
        if isinstance(runtime_value, SymbolDim):
            value = runtime_value.get_value()
            return value if isinstance(value, str) else str(value)
        if isinstance(runtime_value, int) and not isinstance(runtime_value, bool):
            return str(runtime_value)
    return None


def _runtime_values_from_ctx(ctx: EmitContext) -> dict[str, object] | None:
    """读取 emit 上下文中的 runtime values。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 从 `EmitContext.config["__runtime_values__"]` 读取当前函数构建阶段的运行时标量值映射。
    - 仅在配置对象与目标字段都为 `dict` 时返回映射，其他情况统一返回 `None`。
    - 供 symbol scalar binary 与 helper 参数解析共用，避免各 lowering 分支重复读取 config。

    使用示例:
    - runtime_values = _runtime_values_from_ctx(ctx)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/call_nn.py](kernel_gen/dsl/mlir_gen/emit/call_nn.py)
    """

    if not isinstance(ctx.config, dict):
        return None
    runtime_values = ctx.config.get("__runtime_values__")
    return runtime_values if isinstance(runtime_values, dict) else None


def _materialize_symbol_binary_operand(
    operand_expr: object,
    operand_type: object,
    ctx: EmitContext,
    location: SourceLocation | None,
) -> SSAValue:
    """把纯标量 binary operand 物化为 `!symbol.int` SSAValue。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 常量整数统一物化为 `symbol.const`。
    - 现有 `!symbol.int` 输入直接复用缓存中的 SSAValue。
    - runtime `int|SymbolDim` 统一落到公开 `symbol` 表达式。

    使用示例:
    - lhs = _materialize_symbol_binary_operand(expr.lhs, lhs_type, ctx, expr.location)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/call_nn.py](kernel_gen/dsl/mlir_gen/emit/call_nn.py)
    """

    runtime_values = _runtime_values_from_ctx(ctx)
    if isinstance(operand_type, SymbolValueType):
        value = _emit_lower_expr(operand_expr, ctx)
        if isinstance(getattr(value, "type", None), SymbolValueType):
            return value
    runtime_value = _resolve_runtime_scalar_value(operand_expr, operand_type, runtime_values)
    if isinstance(runtime_value, SymbolDim):
        raw_value = runtime_value.get_value()
        if isinstance(raw_value, int):
            return _const_symbol_int(raw_value, ctx, location)
        value = _emit_lower_expr(operand_expr, ctx)
        if isinstance(getattr(value, "type", None), SymbolValueType):
            return value
    if isinstance(runtime_value, int) and not isinstance(runtime_value, bool):
        return _const_symbol_int(int(runtime_value), ctx, location)
    raise _LoweringError("Binary op operands must have nn.memory type", location=location)


def _infer_mixed_binary_type(
    memory_type: NnMemoryType,
    scalar_type: Attribute,
    location: SourceLocation | None,
    *,
    op_name: str = "add",
) -> NnMemoryType:
    """推导 mixed memory-scalar binary expr 的结果类型。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 根据 memory operand 与 scalar operand 的 element type，决定 mixed binary 的结果 `nn.memory` 类型。
    - `floordiv` 复用 operation API 的 scalar promotion 规则，保证 `Int8 // scalar` 提升为 `Int32`。
    - 统一复用 mixed scalar 的 dtype promotion 规则，确保 `call_nn.py` 内只有这一份长期推导逻辑。

    使用示例:
    - result_type = _infer_mixed_binary_type(memory_type, f32, expr.location, op_name="add")

    关联文件:
    - spec: spec/dsl/mlir_gen.md
    - test: test/dsl/mlir_gen/emit/test_call_nn.py
    - 功能实现: kernel_gen/dsl/mlir_gen/emit/call_nn.py
    """

    if op_name == "floordiv":
        output_memory = _KG_OPERATION_NN.floordiv(_nn_memory_type_to_memory(memory_type, location=location), 1)
        if not isinstance(output_memory, Memory):
            raise _LoweringError("Binary op result must be nn.memory", location=location)
        return _memory_to_nn_type(output_memory, location=location)

    scalar_type = _normalize_mixed_scalar_element_type(scalar_type, location)
    target_element_type = memory_type.element_type
    if isinstance(scalar_type, SymbolValueType) or scalar_type == i32:
        target_element_type = memory_type.element_type
    elif isinstance(memory_type.element_type, IntegerType):
        target_element_type = scalar_type
    return _memory_type_from_parts(
        memory_type.shape.data,
        memory_type.stride.data,
        target_element_type,
        memory_type.space,
    )


def _infer_compare_type(
    expr: CompareExprAST,
    type_map: dict[str, object],
    runtime_values: dict[str, object] | None,
    config: dict[str, object] | None,
) -> object:
    lhs_type = _emit_infer_expr_type(expr.lhs, type_map, runtime_values=runtime_values, config=config)
    rhs_type = _emit_infer_expr_type(expr.rhs, type_map, runtime_values=runtime_values, config=config)
    expr_key = _expr_key(expr)
    if isinstance(lhs_type, SymbolValueType) and isinstance(rhs_type, SymbolValueType):
        if expr.op not in {"eq", "ge", "gt", "le", "lt", "ne"}:
            raise _LoweringError("Unsupported symbol compare op", location=expr.location)
        type_map[expr_key] = i1
        return i1
    if not isinstance(lhs_type, NnMemoryType) or not isinstance(rhs_type, NnMemoryType):
        raise _LoweringError("Compare op operands must have nn.memory type", location=expr.location)
    if lhs_type == rhs_type:
        result_type = NnMemoryType(lhs_type.shape, lhs_type.stride, i1, lhs_type.space)
        type_map[expr_key] = result_type
        return result_type
    target_element_type = lhs_type.element_type
    if lhs_type.element_type != rhs_type.element_type:
        target_element_type = _resolve_nn_arith_element_type(lhs_type, rhs_type, expr.location)
    target_type = _infer_broadcast_memory_type(
        lhs_type,
        rhs_type,
        expr.location,
        element_type=target_element_type,
    )
    result_type = NnMemoryType(target_type.shape, target_type.stride, i1, target_type.space)
    type_map[expr_key] = result_type
    return result_type


def _cast_nn_scalar_operand(
    value: SSAValue,
    target_element_type: Attribute,
    ctx: EmitContext,
    location: SourceLocation | None,
) -> SSAValue:
    """把 mixed scalar operand 转成目标 element type。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一处理 `symbol.int`、整型、浮点型标量到目标 element type 的 cast 规则。
    - 为 mixed binary lowering 提供唯一的标量 cast 入口，避免旧路径残留第二份 dtype 转换逻辑。

    使用示例:
    - cast_value = _cast_nn_scalar_operand(alpha, result_type.element_type, ctx, expr.location)

    关联文件:
    - spec: spec/dsl/mlir_gen.md
    - test: test/dsl/mlir_gen/emit/test_call_nn.py
    - 功能实现: kernel_gen/dsl/mlir_gen/emit/call_nn.py
    """

    source_type = value.type
    if source_type == target_element_type:
        return value

    if isinstance(source_type, SymbolValueType):
        if isinstance(target_element_type, IntegerType):
            cast_op = SymbolToIntOp(value, target_element_type)
            ctx.builder.add_op(cast_op)
            return cast_op.result
        if isinstance(target_element_type, (Float16Type, BFloat16Type, Float32Type, Float64Type)):
            cast_op = SymbolToFloatOp(value, target_element_type)
            ctx.builder.add_op(cast_op)
            return cast_op.result
        raise _LoweringError("nn scalar element_type must be integer/float or symbol.int", location=location)
    if isinstance(source_type, IntegerType):
        if isinstance(target_element_type, IntegerType):
            raise _LoweringError("nn scalar integer width conversion is unsupported", location=location)
        if isinstance(target_element_type, (Float16Type, BFloat16Type, Float32Type, Float64Type)):
            cast_op = arith.SIToFPOp(value, target_element_type)
            ctx.builder.add_op(cast_op)
            return cast_op.result
        raise _LoweringError("nn scalar element_type must be integer/float or symbol.int", location=location)
    if isinstance(source_type, (Float16Type, BFloat16Type, Float32Type, Float64Type)) and isinstance(
        target_element_type,
        (Float16Type, BFloat16Type, Float32Type, Float64Type),
    ):
        source_width = 16 if isinstance(source_type, (Float16Type, BFloat16Type)) else (32 if isinstance(source_type, Float32Type) else 64)
        target_width = 16 if isinstance(target_element_type, (Float16Type, BFloat16Type)) else (32 if isinstance(target_element_type, Float32Type) else 64)
        if source_width < target_width:
            cast_op = arith.ExtFOp(value, target_element_type)
            ctx.builder.add_op(cast_op)
            return cast_op.result
        cast_op = arith.TruncFOp(value, target_element_type)
        ctx.builder.add_op(cast_op)
        return cast_op.result
    raise _LoweringError("nn scalar element_type must be integer/float or symbol.int", location=location)


def _materialize_mixed_binary_scalar_operand(
    scalar_expr: object,
    scalar_value: SSAValue | None,
    target_element_type: Attribute,
    ctx: EmitContext,
    location: SourceLocation | None,
    *,
    cast_to_element_type: bool = True,
) -> SSAValue:
    """物化 mixed binary 中的标量操作数。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 把 `ConstAST(int)`、runtime scalar 或 symbol scalar 统一物化为可参与 `nn` binary op 的 SSAValue。
    - 默认在物化完成后立即走 `_cast_nn_scalar_operand(...)`，保证 mixed scalar lowering 使用同一条公开类型路径。
    - `cast_to_element_type=False` 时保留 `!symbol.int`，用于 `nn.floordiv(memory, symbol)` 合同。

    使用示例:
    - rhs_value = _materialize_mixed_binary_scalar_operand(expr.rhs, rhs, result_type.element_type, ctx, expr.location)

    关联文件:
    - spec: spec/dsl/mlir_gen.md
    - test: test/dsl/mlir_gen/emit/test_call_nn.py
    - 功能实现: kernel_gen/dsl/mlir_gen/emit/call_nn.py
    """

    if isinstance(scalar_expr, ConstAST) and isinstance(scalar_expr.value, int):
        scalar_value = _const_symbol_int(int(scalar_expr.value), ctx, location)
    if scalar_value is None:
        raise _LoweringError("Binary op scalar operand could not be materialized", location=location)
    if not cast_to_element_type:
        return scalar_value
    return _cast_nn_scalar_operand(scalar_value, target_element_type, ctx, location)


def _lower_mixed_binary_expr(
    expr: BinaryExprAST,
    lhs: SSAValue | None,
    rhs: SSAValue | None,
    ctx: EmitContext,
) -> SSAValue | None:
    """lower mixed memory-scalar binary expr。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一处理 `memory + scalar`、`memory - scalar`、`memory * scalar`、`memory / scalar`、`memory // scalar` 的 lowering。
    - 若当前表达式不是 mixed scalar 路径，则返回 `None` 让常规 memory-memory lowering 继续处理。

    使用示例:
    - mixed_result = _lower_mixed_binary_expr(expr, lhs, rhs, ctx)

    关联文件:
    - spec: spec/dsl/mlir_gen.md
    - test: test/dsl/mlir_gen/emit/test_call_nn.py
    - 功能实现: kernel_gen/dsl/mlir_gen/emit/call_nn.py
    """

    lhs_type = getattr(lhs, "type", None)
    rhs_type = getattr(rhs, "type", None)
    lhs_is_memory = isinstance(lhs_type, NnMemoryType)
    rhs_is_memory = isinstance(rhs_type, NnMemoryType)
    if lhs_is_memory and rhs_is_memory:
        return None
    if not lhs_is_memory and not rhs_is_memory:
        if expr.op == "add":
            raise _LoweringError("nn.add requires at least one nn.memory operand", location=expr.location)
        raise _LoweringError("Binary op operands must have nn.memory type", location=expr.location)

    result_type = _emit_infer_expr_type(expr, ctx.types, config=ctx.config)
    if not isinstance(result_type, NnMemoryType):
        raise _LoweringError("Binary op result must be nn.memory", location=expr.location)

    memory_value = lhs if lhs_is_memory else rhs
    memory_type = lhs_type if lhs_is_memory else rhs_type
    scalar_value = rhs if lhs_is_memory else lhs
    scalar_expr = expr.rhs if lhs_is_memory else expr.lhs
    if not isinstance(memory_type, NnMemoryType):
        raise _LoweringError("Binary op operands must have nn.memory type", location=expr.location)

    if expr.op != "floordiv" and memory_type.element_type != result_type.element_type:
        cast_type = _memory_type_from_parts(
            memory_type.shape.data,
            memory_type.stride.data,
            result_type.element_type,
            memory_type.space,
        )
        cast_op = NnCastOp(memory_value, cast_type, cast_type.space)
        ctx.builder.add_op(cast_op)
        memory_value = cast_op.result
        memory_type = cast_type

    scalar_value = _materialize_mixed_binary_scalar_operand(
        scalar_expr,
        scalar_value,
        result_type.element_type,
        ctx,
        expr.location,
        cast_to_element_type=expr.op != "floordiv",
    )
    op_map = {
        "add": NnAddOp,
        "sub": NnSubOp,
        "mul": NnMulOp,
        "div": NnTrueDivOp,
        "floordiv": NnFloorDivOp,
    }
    op_cls = op_map.get(expr.op)
    if op_cls is None:
        raise _LoweringError(f"Unsupported binary op: {expr.op}", location=expr.location)
    op = op_cls(
        memory_value if lhs_is_memory else scalar_value,
        scalar_value if lhs_is_memory else memory_value,
        result_type,
        result_type.space,
    )
    ctx.builder.add_op(op)
    return op.result


def _emit_unary(expr: NnUnaryAST, ctx: EmitContext) -> SSAValue:
    """发射 nn unary expr。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一发射 `relu/sigmoid/tanh/exp/leaky_relu/hard_sigmoid` 的 unary lowering。
    - 负责把默认常量参数、结果类型推导与缓存写回收口到 `call_nn.py` 的唯一实现点。

    使用示例:
    - value = _emit_unary(expr, ctx)

    关联文件:
    - spec: spec/dsl/mlir_gen.md
    - test: test/dsl/mlir_gen/emit/test_call_nn.py
    - 功能实现: kernel_gen/dsl/mlir_gen/emit/call_nn.py
    """

    expr_key = _expr_key(expr)
    input_value = _emit_lower_expr(expr.value, ctx)
    input_type = _expect_memory_value(input_value, expr.location)
    result_type = _emit_infer_expr_type(expr, ctx.types, config=ctx.config)
    if not isinstance(result_type, NnMemoryType):
        raise _LoweringError("Unary op result must be nn.memory", location=expr.location)
    if expr.kind in {"relu", "sigmoid", "tanh", "exp"}:
        op_map = {
            "relu": NnReluOp,
            "sigmoid": NnSigmoidOp,
            "tanh": NnTanhOp,
            "exp": NnExpOp,
        }
        op = op_map[expr.kind](input_value, result_type, input_type.space)
    elif expr.kind == "leaky_relu":
        alpha = _emit_lower_expr(expr.alpha, ctx) if expr.alpha is not None else _emit_lower_expr(ConstAST(0.01), ctx)
        op = NnLeakyReluOp(input_value, alpha, result_type, input_type.space)
    elif expr.kind == "hard_sigmoid":
        alpha = _emit_lower_expr(expr.alpha, ctx) if expr.alpha is not None else _emit_lower_expr(ConstAST(0.2), ctx)
        beta = _emit_lower_expr(expr.beta, ctx) if expr.beta is not None else _emit_lower_expr(ConstAST(0.5), ctx)
        op = NnHardSigmoidOp(input_value, alpha, beta, result_type, input_type.space)
    else:
        raise _LoweringError("Unsupported unary helper", location=expr.location)
    ctx.builder.add_op(op)
    return op.result


def _emit_binary(expr: BinaryExprAST, ctx: EmitContext) -> SSAValue:
    """发射 nn binary expr。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一处理 symbol-symbol、memory-memory、memory-scalar 三类 binary lowering 分支。
    - 负责把 cast、broadcast、mixed scalar 物化与结果缓存全部收口到 `call_nn.py`。

    使用示例:
    - value = _emit_binary(expr, ctx)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/emit/test_call_nn.py](test/dsl/mlir_gen/emit/test_call_nn.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/call_nn.py](kernel_gen/dsl/mlir_gen/emit/call_nn.py)
    """

    expr_key = _expr_key(expr)
    lhs_hint = infer_nn_type(expr.lhs, ctx.types, config=ctx.config) if isinstance(expr.lhs, NnUnaryAST) else _emit_infer_expr_type(expr.lhs, ctx.types, config=ctx.config)
    rhs_hint = infer_nn_type(expr.rhs, ctx.types, config=ctx.config) if isinstance(expr.rhs, NnUnaryAST) else _emit_infer_expr_type(expr.rhs, ctx.types, config=ctx.config)
    runtime_values = _runtime_values_from_ctx(ctx)
    lhs_symbol_expr = _symbol_scalar_expr_text(expr.lhs, lhs_hint, runtime_values)
    rhs_symbol_expr = _symbol_scalar_expr_text(expr.rhs, rhs_hint, runtime_values)
    if lhs_symbol_expr is not None and rhs_symbol_expr is not None:
        if expr.op not in {"add", "sub", "mul", "div", "floordiv"}:
            raise _LoweringError("Unsupported symbol binary op", location=expr.location)
        lhs = _materialize_symbol_binary_operand(expr.lhs, lhs_hint, ctx, expr.location)
        rhs = _materialize_symbol_binary_operand(expr.rhs, rhs_hint, ctx, expr.location)
        result_type = _emit_infer_expr_type(expr, ctx.types, runtime_values=runtime_values, config=ctx.config)
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
        return op.result
    lhs_is_memory_hint = isinstance(lhs_hint, NnMemoryType)
    rhs_is_memory_hint = isinstance(rhs_hint, NnMemoryType)
    lhs_const_int = isinstance(expr.lhs, ConstAST) and isinstance(expr.lhs.value, int)
    rhs_const_int = isinstance(expr.rhs, ConstAST) and isinstance(expr.rhs.value, int)
    lhs = None if (rhs_is_memory_hint and lhs_const_int and not lhs_is_memory_hint) else _emit_lower_expr(expr.lhs, ctx)
    rhs = None if (lhs_is_memory_hint and rhs_const_int and not rhs_is_memory_hint) else _emit_lower_expr(expr.rhs, ctx)
    lhs_attr = getattr(lhs, "type", None)
    rhs_attr = getattr(rhs, "type", None)
    if isinstance(lhs_attr, SymbolValueType) and isinstance(rhs_attr, SymbolValueType):
        if expr.op not in {"add", "sub", "mul", "div", "floordiv"}:
            raise _LoweringError("Unsupported symbol binary op", location=expr.location)
        result_type = _emit_infer_expr_type(expr, ctx.types, config=ctx.config)
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
        return op.result
    mixed_binary_result = _lower_mixed_binary_expr(expr, lhs, rhs, ctx)
    if mixed_binary_result is not None:
        return mixed_binary_result
    if lhs is None or rhs is None:
        raise _LoweringError("Binary op operands must have nn.memory type", location=expr.location)
    lhs_type = _expect_memory_value(lhs, expr.location)
    rhs_type = _expect_memory_value(rhs, expr.location)
    result_type = _emit_infer_expr_type(expr, ctx.types, config=ctx.config)
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
        cast_op = NnCastOp(lhs, cast_type, cast_type.space)
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
        cast_op = NnCastOp(rhs, cast_type, cast_type.space)
        ctx.builder.add_op(cast_op)
        rhs = cast_op.result
        rhs_type = cast_type
    if lhs_type != target_type:
        broadcast_op = NnBroadcastOp(lhs, target_type, target_type.space)
        ctx.builder.add_op(broadcast_op)
        lhs = broadcast_op.result
    if rhs_type != target_type:
        broadcast_op = NnBroadcastOp(rhs, target_type, target_type.space)
        ctx.builder.add_op(broadcast_op)
        rhs = broadcast_op.result
    op_map = {
        "add": NnAddOp,
        "sub": NnSubOp,
        "mul": NnMulOp,
        "div": NnTrueDivOp,
        "floordiv": NnFloorDivOp,
    }
    op_cls = op_map.get(expr.op)
    if op_cls is None:
        raise _LoweringError(f"Unsupported binary op: {expr.op}", location=expr.location)
    op = op_cls(lhs, rhs, target_type, target_type.space)
    ctx.builder.add_op(op)
    return op.result


def _emit_compare(expr: CompareExprAST, ctx: EmitContext) -> SSAValue:
    """发射 nn compare expr。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一处理 symbol compare 与 memory compare 两条 lowering 分支。
    - 负责 compare 路径中的 dtype 对齐、broadcast 与 `i1` 结果 memory 构造，避免 compare 规则散落到 facade 层。

    使用示例:
    - value = _emit_compare(expr, ctx)

    关联文件:
    - spec: spec/dsl/mlir_gen.md
    - test: test/dsl/mlir_gen/emit/test_call_nn.py
    - 功能实现: kernel_gen/dsl/mlir_gen/emit/call_nn.py
    """

    expr_key = _expr_key(expr)
    lhs = _emit_lower_expr(expr.lhs, ctx)
    rhs = _emit_lower_expr(expr.rhs, ctx)
    lhs_attr = getattr(lhs, "type", None)
    rhs_attr = getattr(rhs, "type", None)
    if isinstance(lhs_attr, SymbolValueType) and isinstance(rhs_attr, SymbolValueType):
        if expr.op not in {"eq", "ge", "gt", "le", "lt", "ne"}:
            raise _LoweringError("Unsupported symbol compare op", location=expr.location)
        op_map = {
            "eq": SymbolEqOp,
            "ge": SymbolGeOp,
            "gt": SymbolGtOp,
            "le": SymbolLeOp,
            "lt": SymbolLtOp,
            "ne": SymbolNeOp,
        }
        op = op_map[expr.op](lhs, rhs, i1)
        ctx.builder.add_op(op)
        return op.result
    lhs_type = _expect_memory_value(lhs, expr.location)
    rhs_type = _expect_memory_value(rhs, expr.location)
    if lhs_type != rhs_type:
        target_element_type = lhs_type.element_type
        if lhs_type.element_type != rhs_type.element_type:
            target_element_type = _resolve_nn_arith_element_type(lhs_type, rhs_type, expr.location)
        target_type = _infer_broadcast_memory_type(
            lhs_type,
            rhs_type,
            expr.location,
            element_type=target_element_type,
        )
        if lhs_type.element_type != target_type.element_type:
            cast_type = _memory_type_from_parts(
                lhs_type.shape.data,
                lhs_type.stride.data,
                target_type.element_type,
                lhs_type.space,
            )
            cast_op = NnCastOp(lhs, cast_type, cast_type.space)
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
            cast_op = NnCastOp(rhs, cast_type, cast_type.space)
            ctx.builder.add_op(cast_op)
            rhs = cast_op.result
            rhs_type = cast_type
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
    op_cls = op_map.get(expr.op)
    if op_cls is None:
        raise _LoweringError(f"Unsupported compare op: {expr.op}", location=expr.location)
    op = op_cls(lhs, rhs, result_type, lhs_type.space)
    ctx.builder.add_op(op)
    return op.result
