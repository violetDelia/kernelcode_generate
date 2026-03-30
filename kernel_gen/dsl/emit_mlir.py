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
    UnrealizedConversionCastOp,
    f32,
    i1,
    i8,
    i32,
)
from xdsl.ir import Attribute, Block, SSAValue

from kernel_gen.dialect.arch import (
    ArchGetBlockIdOp,
    ArchGetBlockNumOp,
    ArchGetDynamicMemoryOp,
    ArchGetSubthreadIdOp,
    ArchGetSubthreadNumOp,
    ArchGetThreadIdOp,
    ArchGetThreadNumOp,
    ArchLaunchKernelOp,
)
from kernel_gen.dialect.dma import (
    DmaAllocOp,
    DmaCastOp,
    DmaCopyOp,
    DmaDesliceOp,
    DmaFreeOp,
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
    NnImg2col1dOp,
    NnImg2col2dOp,
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
    SymbolGetDimOp,
    SymbolGetStrideOp,
    SymbolMulOp,
    SymbolSubOp,
    SymbolValueType,
    build_public_symbol_expr,
)
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType
from kernel_gen.target import registry

from .ast import (
    ArchGetDynamicMemoryAST,
    ArchLaunchKernelAST,
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
    Img2ColAST,
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

_DYNAMIC_MEMORY_SPACE_MAP = {
    MemorySpace.SM: "shared",
    MemorySpace.LM: "local",
    MemorySpace.TSM: "tsm",
    MemorySpace.TLM: "tlm",
}

_IMG2COL_PARAM_TABLE: dict[str, tuple[tuple[str, ...], dict[str, int]]] = {
    "img2col1d": (
        ("value", "kw", "sw", "dw", "pl", "pr"),
        {"sw": 1, "dw": 1, "pl": 0, "pr": 0},
    ),
    "img2col2d": (
        ("value", "kh", "kw", "sh", "sw", "dh", "dw", "ph", "pw", "pl", "pr"),
        {"sh": 1, "sw": 1, "dh": 1, "dw": 1, "ph": 0, "pw": 0, "pl": 0, "pr": 0},
    ),
}


class _LoweringError(ValueError):
    """lowering/emit 阶段错误。"""

    def __init__(self: "_LoweringError", message: str, location: SourceLocation | None = None) -> None:
        super().__init__(message)
        self.location = location


def _validate_emit_context_config(config: dict[str, object] | None) -> None:
    """校验 EmitContext.config 中的 target/hardware 字段。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 当 config 中包含 target/hardware 时，校验其类型与字段约束。
    - 约束规则与 spec/target/registry.md 一致，仅做字段合法性检查。

    使用示例:
    - _validate_emit_context_config({"target": "gpu_a", "hardware": {"thread_num": 256}})

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md), [spec/target/registry.md](spec/target/registry.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    if config is None:
        return
    if not isinstance(config, dict):
        raise _LoweringError("EmitContext config must be dict or None")
    if "target" in config:
        target = config["target"]
        if not isinstance(target, str):
            raise _LoweringError("EmitContext target must be str")
        try:
            registry._validate_target_name(target)
        except ValueError as exc:
            raise _LoweringError(str(exc)) from exc
    if "hardware" in config:
        hardware = config["hardware"]
        if not isinstance(hardware, dict):
            raise _LoweringError("EmitContext hardware must be dict[str, int]")
        target_name = config.get("target")
        target_label = target_name if isinstance(target_name, str) else "emit_context"
        try:
            registry._validate_hardware_map(hardware, target_label)
        except ValueError as exc:
            raise _LoweringError(str(exc)) from exc


class EmitContext:
    """AST 节点发射上下文。"""

    def __init__(
        self: "EmitContext",
        builder: Block,
        symbols: dict[str, object],
        types: dict[int, object],
        config: dict[str, object] | None = None,
    ) -> None:
        _validate_emit_context_config(config)
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
    最后一次更改: 小李飞刀

    功能说明:
    - 将 DSL NumericType 转为 nn.memory 的 element_type。
    - 遇到不支持类型时抛出 LoweringError。

    使用示例:
    - _dtype_to_xdsl(NumericType.Float32)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    if dtype is NumericType.Bool:
        return i1
    if dtype is NumericType.Float16:
        return Float16Type()
    if dtype is NumericType.Float32:
        return f32
    if dtype is NumericType.Int8:
        return i8
    if dtype is NumericType.Int32:
        return i32
    if dtype is NumericType.Bool:
        return i1
    raise _LoweringError(f"Unsupported dtype: {dtype}", location=location)


def _xdsl_to_dtype(element_type: Attribute, location: SourceLocation | None = None) -> NumericType:
    """将 xdsl element_type 还原为 NumericType。

    创建者: 我不是牛马
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 Float16/Float32/Int32/Bool 解析为 NumericType。
    - 不支持的 element_type 抛出 LoweringError。

    使用示例:
    - _xdsl_to_dtype(f32)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    if isinstance(element_type, Float16Type):
        return NumericType.Float16
    if element_type == f32:
        return NumericType.Float32
    if element_type == i8:
        return NumericType.Int8
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
    最后一次更改: 小李飞刀

    功能说明:
    - 按 Memory 算术 dtype 决议规则选择目标 element_type。
    - 无法解析时抛出 LoweringError。

    使用示例:
    - _resolve_nn_arith_element_type(lhs_type, rhs_type, location)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    try:
        lhs_dtype = _xdsl_to_dtype(lhs_type.element_type, location)
        rhs_dtype = _xdsl_to_dtype(rhs_type.element_type, location)
        target_dtype = Memory._promote_dtype(lhs_dtype, rhs_dtype)
    except TypeError as exc:
        raise _LoweringError("Binary op operands must have compatible element_type", location=location) from exc
    return _dtype_to_xdsl(target_dtype, location)


def _build_stride(shape: list[int | str]) -> list[int | str]:
    """根据 shape 列表构造默认连续内存 stride。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 按行主序从尾到头累计计算 stride。
    - 遇到符号维时保留 `?`，避免在静态阶段做错误折叠。

    使用示例:
    - _build_stride([2, 3, 4]) -> [12, 4, 1]

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
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
    """组合静态/符号维度乘法表达式。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 在 stride 与 numel 推导时合并 `int|str` 两类维度。
    - 对乘以 1 的场景做最小化化简，其他情况保留字符串表达式。

    使用示例:
    - _mul_symbol("M", 4) -> "M*4"

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    if isinstance(dim, int) and isinstance(running, int):
        return dim * running
    if isinstance(dim, int) and dim == 1:
        return running
    if isinstance(running, int) and running == 1:
        return dim
    return f"{dim}*{running}"


def _build_default_stride_attrs(shape: Sequence[Attribute]) -> list[Attribute]:
    """从 shape 属性列表生成默认 stride 属性列表。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 输入为 `IntAttr/StringAttr` 形式的 shape 属性。
    - 输出连续布局 stride，并复用 `_mul_symbol` 处理符号维表达式。

    使用示例:
    - _build_default_stride_attrs([IntAttr(2), IntAttr(4)])

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
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
    """将静态或符号维度值转换为 xDSL 属性。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - `int` 转为 `IntAttr`。
    - `str` 转为 `StringAttr`，用于符号维与动态占位。

    使用示例:
    - _dim_to_attr("M")

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    if isinstance(value, int):
        return IntAttr(value)
    return StringAttr(value)


def _const_index(value: int, ctx: EmitContext) -> SSAValue:
    """构造 `index` 常量 SSA 值。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 以 `arith.constant` 发射 `IndexType` 常量。
    - 统一供 offset/shape/stride 等索引 operand 构造复用。

    使用示例:
    - _const_index(4, ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    attr = IntegerAttr(value, IndexType())
    op = arith.ConstantOp(attr)
    ctx.builder.add_op(op)
    return op.result


def _cast_to_symbol_int(
    value: SSAValue,
    ctx: EmitContext,
    expr: str,
    location: SourceLocation | None,
) -> SSAValue:
    """将 SSAValue 转换为指定表达式的 !symbol.int<"expr">。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 若已是 SymbolValueType，则直接返回。
    - 否则通过 UnrealizedConversionCastOp 生成 !symbol.int<"expr">。

    使用示例:
    - _cast_to_symbol_int(value, ctx, "M", location)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

    if isinstance(value.type, SymbolValueType):
        return value
    if not isinstance(value.type, (IndexType, IntegerType)):
        raise _LoweringError("Index operand must be integer or index", location=location)
    result_type = SymbolValueType.from_expr(expr)
    op = UnrealizedConversionCastOp(operands=[value], result_types=[result_type])
    ctx.builder.add_op(op)
    return op.results[0]


def _const_symbol_int(value: int, ctx: EmitContext, location: SourceLocation | None) -> SSAValue:
    """构造 !symbol.int<"expr"> 常量 SSA value。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 先创建 i32 常量，再转换为 !symbol.int<"expr">。

    使用示例:
    - _const_symbol_int(4, ctx, location)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

    attr = IntegerAttr(value, i32)
    op = arith.ConstantOp(attr)
    ctx.builder.add_op(op)
    return _cast_to_symbol_int(op.result, ctx, str(value), location)


def _ensure_index_value(value: SSAValue, ctx: EmitContext, location: SourceLocation | None) -> SSAValue:
    """确保索引 operand 为可接受的 `index` 或 `!symbol.int` 值。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - `!symbol.int` 与 `index` 直接复用。
    - `i32` 等整数值通过 `arith.index_cast` 转成 `index`。

    使用示例:
    - _ensure_index_value(value, ctx, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    if isinstance(value.type, SymbolValueType):
        return value
    if isinstance(value.type, IndexType):
        return value
    if isinstance(value.type, IntegerType):
        op = arith.IndexCastOp(value, IndexType())
        ctx.builder.add_op(op)
        return op.result
    raise _LoweringError("Index operand must be integer or index", location=location)


def _materialize_index_symbol_from_memory(
    name: str,
    ctx: EmitContext,
    location: SourceLocation | None,
) -> SSAValue | None:
    """从上下文 memory 值中物化符号索引。

    创建者: jcc你莫辜负
    最后一次更改: 小李飞刀

    功能说明:
    - 当 `ctx.symbols` 缺少目标符号时，尝试在已知 `nn.memory` 的 shape/stride 中查找同名符号。
    - 命中 shape 时生成 `symbol.get_dim`，命中 stride 时生成 `symbol.get_stride`，并写回 `ctx.symbols` 缓存。

    使用示例:
    - _materialize_index_symbol_from_memory("M", ctx, location)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

    for candidate in ctx.symbols.values():
        if not isinstance(candidate, SSAValue):
            continue
        candidate_type = candidate.type
        if not isinstance(candidate_type, NnMemoryType):
            continue
        for axis, dim in enumerate(candidate_type.shape.data):
            if isinstance(dim, StringAttr) and dim.data == name:
                op = SymbolGetDimOp(candidate, IntAttr(axis))
                ctx.builder.add_op(op)
                ctx.symbols[name] = op.result
                return op.result
        for axis, stride in enumerate(candidate_type.stride.data):
            if isinstance(stride, StringAttr) and stride.data == name:
                op = SymbolGetStrideOp(candidate, IntAttr(axis))
                ctx.builder.add_op(op)
                ctx.symbols[name] = op.result
                return op.result
    return None


def _resolve_index_symbol(name: str, ctx: EmitContext, location: SourceLocation | None) -> SSAValue:
    """解析索引表达式中的符号名引用。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 优先从 `ctx.symbols` 命中已有符号。
    - 若缺失则尝试从已知 `nn.memory` 的 shape/stride 中物化同名符号。

    使用示例:
    - _resolve_index_symbol("M", ctx, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    if name not in ctx.symbols:
        materialized = _materialize_index_symbol_from_memory(name, ctx, location)
        if materialized is None:
            raise _LoweringError("Unknown index symbol", location=location)
    value = ctx.symbols[name]
    if not isinstance(value, SSAValue):
        raise _LoweringError("Index symbol must be SSA value", location=location)
    if isinstance(value.type, SymbolValueType):
        return value
    if isinstance(value.type, (IndexType, IntegerType)):
        return _ensure_index_value(value, ctx, location)
    return _cast_to_symbol_int(value, ctx, name, location)


def _split_symbol_multiplication(expr: str) -> list[str] | None:
    """将符号乘法表达式拆分为多个 symbol 名称。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅支持以 `*` 连接的简单 symbol 乘法表达式。
    - 包含其他运算符或空段时返回 None。

    使用示例:
    - _split_symbol_multiplication("M*N*K") -> ["M", "N", "K"]

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    normalized = expr.strip()
    if not normalized:
        return None
    for token in ("+", "-", "/", "//", "(", ")", " "):
        if token in normalized:
            return None
    parts = normalized.split("*")
    if any(not part for part in parts):
        return None
    return parts


def _resolve_index_symbol_product(expr: str, ctx: EmitContext, location: SourceLocation | None) -> SSAValue:
    """将 `A*B*...` 解析为 symbol.mul 链。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅支持符号名的乘法链，逐步 lowering 为 SymbolMulOp。
    - 确保生成结果为 !symbol.int<...>。

    使用示例:
    - _resolve_index_symbol_product("M*N", ctx, location)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    parts = _split_symbol_multiplication(expr)
    if parts is None:
        raise _LoweringError("Unsupported index expression", location=location)
    if len(parts) == 1:
        return _resolve_index_symbol(parts[0], ctx, location)
    current = _cast_to_symbol_int(_resolve_index_symbol(parts[0], ctx, location), ctx, parts[0], location)
    for part in parts[1:]:
        rhs = _cast_to_symbol_int(_resolve_index_symbol(part, ctx, location), ctx, part, location)
        rhs_expr = rhs.type.expr.expr.data
        result_type = SymbolValueType.from_expr(build_public_symbol_expr(current.type.expr.expr.data, rhs_expr, "*"))
        op = SymbolMulOp(current, rhs, result_type)
        ctx.builder.add_op(op)
        current = op.result
    return current


def _resolve_index_operand(expr: object, ctx: EmitContext, location: SourceLocation | None) -> SSAValue:
    """将索引表达式 lowering 为 SSA operand。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 支持常量、symbol 名称、循环变量和显式字符串乘法表达式。
    - 对非法输入保持统一的 index 诊断文案。

    使用示例:
    - _resolve_index_operand(ConstAST(2), ctx, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    if isinstance(expr, ConstAST):
        if isinstance(expr.value, int):
            return _const_index(expr.value, ctx)
        if isinstance(expr.value, str):
            return _resolve_index_symbol(expr.value, ctx, expr.location)
        raise _LoweringError("Index must be int or str", location=expr.location)
    if isinstance(expr, (ScalarArgAST, VarAST)):
        value = _lookup_symbol(expr, ctx)
        if not isinstance(value, SSAValue):
            raise _LoweringError("Index operand must be SSA value", location=expr.location)
        return _ensure_index_value(value, ctx, expr.location)
    if isinstance(expr, int):
        return _const_index(expr, ctx)
    if isinstance(expr, str):
        if "*" in expr:
            return _resolve_index_symbol_product(expr, ctx, location)
        return _resolve_index_symbol(expr, ctx, location)
    raise _LoweringError("Unsupported index expression", location=location or getattr(expr, "location", None))


def _get_loop_vars(ctx: EmitContext) -> dict[str, int]:
    """读取并初始化上下文中的循环变量表。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 确保 `ctx.config["loop_vars"]` 始终存在且类型为 `dict`。
    - 供索引解析阶段查询 `ForAST` 绑定的循环变量。

    使用示例:
    - loop_vars = _get_loop_vars(ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    if ctx.config is None:
        ctx.config = {}
    loop_vars = ctx.config.setdefault("loop_vars", {})
    if not isinstance(loop_vars, dict):
        raise _LoweringError("loop_vars must be a dict", location=None)
    return loop_vars


def _resolve_index_expr(expr: object, ctx: EmitContext) -> int | str:
    """在静态解析阶段提取索引表达式的 `int|str` 形式。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 供 shape/stride 等类型推导路径复用。
    - 支持常量、标量参数、循环变量与直接字面量。

    使用示例:
    - _resolve_index_expr(VarAST(name="i"), ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
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
    """按 rank 构造索引 operand 列表。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 支持单值广播到整 rank，或校验显式索引列表长度。
    - 默认值常用于 offset=0、stride=1 等场景补位。

    使用示例:
    - _build_index_attrs(None, 2, ctx, default_value=0)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
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
    """将 `ArrayAttr` 布局描述转换为索引 operand。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 接收由 `IntAttr/StringAttr` 组成的 shape/stride 布局属性。
    - 逐项下沉为 `index` 或 `!symbol.int` SSA 值。

    使用示例:
    - _build_index_operands_from_layout(ArrayAttr([IntAttr(4)]), ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    values: list[object] = []
    for dim in layout.data:
        if isinstance(dim, IntAttr):
            values.append(dim.data)
        elif isinstance(dim, StringAttr):
            values.append(dim.data)
        else:
            raise _LoweringError("Unsupported layout attribute", location=location)
    return [_resolve_index_operand(item, ctx, location) for item in values]


def _build_flatten_shape_operands(
    source: SSAValue,
    source_type: NnMemoryType,
    ctx: EmitContext,
    *,
    location: SourceLocation | None = None,
) -> list[SSAValue]:
    """构造 flatten 结果的一维 shape operand。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 静态 shape 直接使用常量 operand。
    - 符号 shape 通过 symbol.get_dim/symbol.mul 组合出总元素数。

    使用示例:
    - _build_flatten_shape_operands(source, source_type, ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

    if all(isinstance(dim, IntAttr) for dim in source_type.shape.data):
        return _build_index_operands_from_layout(
            ArrayAttr([_shape_numel_attr(source_type.shape.data)]),
            ctx,
            location=location,
        )
    dim_values: list[SSAValue] = []
    for axis, _ in enumerate(source_type.shape.data):
        op = SymbolGetDimOp(source, IntAttr(axis))
        ctx.builder.add_op(op)
        dim_values.append(op.result)
    if not dim_values:
        raise _LoweringError("flatten source rank must be >= 1", location=location)
    total = dim_values[0]
    for value in dim_values[1:]:
        result_type = SymbolValueType.from_expr(
            build_public_symbol_expr(total.type.expr.expr.data, value.type.expr.expr.data, "*")
        )
        op = SymbolMulOp(total, value, result_type)
        ctx.builder.add_op(op)
        total = op.result
    return [total]


def _lower_loop_bound(expr: object, ctx: EmitContext) -> object:
    """将 `for` 上下界表达式 lowering 为 SSA 值。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 支持常量、标量参数与循环变量引用。
    - 不支持的表达式维持统一的 loop bound 诊断。

    使用示例:
    - _lower_loop_bound(ConstAST(8), ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
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
    """构造 store/deslice 使用的 stride operand，并限制为单位步长。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 基于 `_build_index_attrs` 生成 stride operand。
    - 当前仅允许全 1 stride，非单位步长统一报错。

    使用示例:
    - _build_stride_attrs(None, 2, ctx, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    stride = _build_index_attrs(value, rank, ctx, default_value=1, location=location)
    for entry in stride:
        if isinstance(entry.type, SymbolValueType):
            if entry.type.get_value() != 1:
                raise _LoweringError("Only unit stride is supported", location=location)
            continue
        owner = entry.owner
        if not isinstance(owner, arith.ConstantOp) or not isinstance(owner.value, IntegerAttr):
            raise _LoweringError("Only unit stride is supported", location=location)
        if owner.value.value.data != 1:
            raise _LoweringError("Only unit stride is supported", location=location)
    return stride


def _resolve_static_index_expr(
    expr: object,
    location: SourceLocation | None = None,
    runtime_values: dict[str, object] | None = None,
) -> int | str:
    """解析类型推导阶段使用的索引表达式。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 `ConstAST`、`ScalarArgAST`、`VarAST` 以及直接的 `int|str`。

    使用示例:
    - _resolve_static_index_expr("N")

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

    if isinstance(expr, ConstAST):
        if isinstance(expr.value, (int, str)):
            return expr.value
        raise _LoweringError("Index must be int or str", location=expr.location)
    if isinstance(expr, ScalarArgAST):
        if runtime_values is not None and expr.name in runtime_values:
            runtime_value = runtime_values[expr.name]
            if isinstance(runtime_value, SymbolDim):
                return str(runtime_value.get_symbol())
            if isinstance(runtime_value, int):
                return runtime_value
        return expr.name
    if isinstance(expr, VarAST):
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
    runtime_values: dict[str, object] | None = None,
) -> list[Attribute]:
    """构造类型推导阶段使用的索引属性列表。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 将静态或符号索引表达式转成 `IntAttr/StringAttr`。

    使用示例:
    - _build_static_index_list([4, "N"], 2, default_value=1)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

    if value is None:
        values = [default_value for _ in range(rank)]
    elif isinstance(value, (list, tuple)):
        if len(value) != rank:
            raise _LoweringError("Index rank mismatch", location=location)
        values = [_resolve_static_index_expr(entry, location, runtime_values) for entry in value]
    else:
        scalar = _resolve_static_index_expr(value, location, runtime_values)
        values = [scalar for _ in range(rank)]
    return [_dim_to_attr(item) for item in values]


def _build_static_index_attrs_exact(
    value: object,
    *,
    location: SourceLocation | None = None,
    runtime_values: dict[str, object] | None = None,
) -> list[Attribute]:
    """按显式维度列表构造静态索引属性。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 仅接受单个索引或显式索引序列，不使用默认补值。

    使用示例:
    - _build_static_index_attrs_exact([ConstAST(4), "N"])

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

    if isinstance(value, (list, tuple)):
        entries = [_resolve_static_index_expr(entry, location, runtime_values) for entry in value]
    else:
        entries = [_resolve_static_index_expr(value, location, runtime_values)]
    return [_dim_to_attr(entry) for entry in entries]


def _build_index_operands_exact(
    value: object,
    ctx: EmitContext,
    *,
    location: SourceLocation | None = None,
) -> list[SSAValue]:
    """按显式维度列表构造 SSA 索引操作数。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 仅接受单个索引或显式索引序列，不使用默认补值。

    使用示例:
    - _build_index_operands_exact([ConstAST(4), "N"], ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
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
    """基于 shape/stride/element_type/space 组装 `NnMemoryType`。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 统一封装 `NnMemoryType` 的构造逻辑，避免重复写 `ArrayAttr(list(...))`。
    - 保持 shape/stride/space 不变，仅组合目标 element_type。

    使用示例:
    - _memory_type_from_parts(shape, stride, f32, space)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

    return NnMemoryType(ArrayAttr(list(shape)), ArrayAttr(list(stride)), element_type, space)


def _shape_numel_attr(shape: Sequence[Attribute]) -> Attribute:
    """根据 shape 计算 flatten 后的一维元素总数属性。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 全静态 shape 返回 `IntAttr(numel)`。
    - 含符号维时返回折叠后的 `StringAttr` 符号表达式，动态未知时返回 `?`。

    使用示例:
    - _shape_numel_attr([IntAttr(2), StringAttr("N")])

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

    total_static = 1
    total_symbol: SymbolDim | None = None
    for dim in shape:
        if isinstance(dim, IntAttr):
            if total_symbol is None:
                total_static *= dim.data
            else:
                total_symbol = total_symbol * dim.data
            continue
        if isinstance(dim, StringAttr):
            if dim.data == "?":
                return StringAttr("?")
            if total_symbol is None:
                total_symbol = SymbolDim(total_static) * dim.data
            else:
                total_symbol = total_symbol * dim.data
            continue
        return StringAttr("?")
    if total_symbol is None:
        return IntAttr(total_static)
    if not total_symbol.is_dynamic():
        return IntAttr(int(total_symbol.get_symbol()))
    return StringAttr(str(total_symbol.get_symbol()))


def _memory_space_from_ast(space: MemorySpace | None, fallback: NnMemorySpaceAttr) -> NnMemorySpaceAttr:
    """将 AST 中的 `MemorySpace` 映射为 nn dialect space attribute。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 未显式指定时返回 fallback。
    - 显式指定时转换到 `NnMemorySpaceAttr`。

    使用示例:
    - _memory_space_from_ast(MemorySpace.LM, source_type.space)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

    if space is None:
        return fallback
    space_name = _MEMORY_SPACE_MAP.get(space, "global")
    return NnMemorySpaceAttr.from_name(space_name)


def _dims_equal(lhs: Attribute, rhs: Attribute) -> bool:
    """比较两个维度属性是否语义相等。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 仅比较 `IntAttr` 与 `StringAttr` 两类维度。
    - 用于 broadcast 过程中判断维度是否可直接复用。

    使用示例:
    - _dims_equal(IntAttr(4), IntAttr(4)) -> True

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
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
    """推导两个 memory 参与隐式 broadcast 后的目标 shape。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 按 numpy 风格从尾维开始对齐比较。
    - 支持 `1` 扩展和完全相等维度；其余不兼容情况直接报错。

    使用示例:
    - _infer_broadcast_shape([IntAttr(1), IntAttr(4)], [IntAttr(2), IntAttr(4)], None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
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
    """为 broadcast 结果 shape 生成默认 stride。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 当前 broadcast 结果使用默认连续布局。
    - 逻辑委托给 `_build_default_stride_attrs` 统一处理。

    使用示例:
    - _build_broadcast_stride([IntAttr(2), IntAttr(4)])

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    return _build_default_stride_attrs(shape)


def _infer_broadcast_memory_type(
    lhs_type: NnMemoryType,
    rhs_type: NnMemoryType,
    location: SourceLocation | None,
    element_type: Attribute | None = None,
) -> NnMemoryType:
    """推导二元 broadcast 目标 memory type。

    创建者: 我不是牛马
    最后一次更改: 小李飞刀

    功能说明:
    - 依据隐式 broadcast 推导目标 shape 与 stride。
    - 默认要求 element_type 一致；允许显式传入 element_type 覆盖。

    使用示例:
    - _infer_broadcast_memory_type(lhs_type, rhs_type, location)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
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


def _resolve_binary_element_type(
    lhs_type: Attribute,
    rhs_type: Attribute,
    location: SourceLocation | None,
) -> Attribute:
    """解析 nn 二元算术的 element_type 决议。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 对支持的 element_type 按固定优先级选择目标类型。
    - 不支持的类型组合保持原有诊断文案。

    使用示例:
    - _resolve_binary_element_type(i32, f32, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    if lhs_type == rhs_type:
        return lhs_type
    if lhs_type == i32:
        lhs_rank = 4
    elif isinstance(lhs_type, Float16Type):
        lhs_rank = 8
    elif lhs_type == f32:
        lhs_rank = 10
    else:
        raise _LoweringError("Binary op operands must have the same element_type", location=location)

    if rhs_type == i32:
        rhs_rank = 4
    elif isinstance(rhs_type, Float16Type):
        rhs_rank = 8
    elif rhs_type == f32:
        rhs_rank = 10
    else:
        raise _LoweringError("Binary op operands must have the same element_type", location=location)
    return lhs_type if lhs_rank >= rhs_rank else rhs_type


def _normalize_add_scalar_element_type(
    scalar_type: Attribute,
    location: SourceLocation | None,
) -> Attribute:
    """归一化 `nn.add` mixed memory+scalar/symbol 的标量 dtype。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 将 `!symbol.int` 统一视为 `i32` 参与 `nn.add` promotion。
    - 仅接受 `i32/f16/f32` 与 `!symbol.int` 四类标量输入。

    使用示例:
    - _normalize_add_scalar_element_type(SymbolValueType.from_expr("K"), location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

    if isinstance(scalar_type, SymbolValueType):
        return i32
    if scalar_type == i32 or isinstance(scalar_type, Float16Type) or scalar_type == f32:
        return scalar_type
    raise _LoweringError("nn.add scalar element_type must be i32/f16/f32 or symbol.int", location=location)


def _infer_add_mixed_memory_type(
    memory_type: NnMemoryType,
    scalar_type: Attribute,
    location: SourceLocation | None,
) -> NnMemoryType:
    """推导 `nn.add` mixed memory+scalar/symbol 的目标类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 结果 `shape/stride/space` 直接继承 memory operand。
    - 标量侧按 `i32 < f16 < f32` 与 `!symbol.int -> i32` 规则参与 promotion。

    使用示例:
    - _infer_add_mixed_memory_type(memory_type, i32, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

    target_element_type = _resolve_binary_element_type(
        memory_type.element_type,
        _normalize_add_scalar_element_type(scalar_type, location),
        location,
    )
    return _memory_type_from_parts(
        memory_type.shape.data,
        memory_type.stride.data,
        target_element_type,
        memory_type.space,
    )


def _infer_binary_memory_type(
    lhs_type: NnMemoryType,
    rhs_type: NnMemoryType,
    location: SourceLocation | None,
) -> NnMemoryType:
    """推导 nn 二元算术的目标 nn.memory 类型。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 允许隐式 broadcast 推导共同目标 shape。
    - element_type 按 nn 二元算术固定优先级决议。

    使用示例:
    - _infer_binary_memory_type(lhs_type, rhs_type, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    if lhs_type.space != rhs_type.space:
        raise _LoweringError("Binary op operands must have the same space", location=location)
    target_shape = _infer_broadcast_shape(lhs_type.shape.data, rhs_type.shape.data, location)
    target_stride = _build_broadcast_stride(target_shape)
    target_element_type = _resolve_binary_element_type(lhs_type.element_type, rhs_type.element_type, location)
    return NnMemoryType(
        ArrayAttr(list(target_shape)),
        ArrayAttr(list(target_stride)),
        target_element_type,
        lhs_type.space,
    )


def _memory_to_nn_type(memory: Memory, location: SourceLocation | None = None) -> NnMemoryType:
    """将运行时 `Memory` 描述转换为 `NnMemoryType`。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 读取 `Memory` 的 shape/stride/dtype/space，并映射到 nn dialect 类型。
    - 未显式提供 stride 时自动按连续布局补齐。

    使用示例:
    - _memory_to_nn_type(Memory([2, 2], NumericType.Float32))

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    shape = memory.shape.get_values()
    stride_values = memory.stride.get_values() if memory.stride is not None else _build_stride(shape)
    shape_attr = ArrayAttr([_dim_to_attr(dim) for dim in shape])
    stride_attr = ArrayAttr([_dim_to_attr(dim) for dim in stride_values])
    element_type = _dtype_to_xdsl(memory.dtype, location=location)
    space_name = _MEMORY_SPACE_MAP.get(memory.space, "global")
    space = NnMemorySpaceAttr.from_name(space_name)
    return NnMemoryType(shape_attr, stride_attr, element_type, space)


def _build_dynamic_memory_type(
    space: MemorySpace,
    location: SourceLocation | None = None,
) -> NnMemoryType:
    """构造 `arch.get_dynamic_memory` 返回的动态 memory 类型。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 仅允许 on-chip memory space。
    - 返回 `shape=[?]`、`stride=[1]`、`element_type=i8` 的占位动态内存类型。

    使用示例:
    - _build_dynamic_memory_type(MemorySpace.LM, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    space_name = _DYNAMIC_MEMORY_SPACE_MAP.get(space)
    if space_name is None:
        raise _LoweringError("get_dynamic_memory space must be on-chip MemorySpace", location=location)
    return NnMemoryType(
        ArrayAttr([StringAttr("?")]),
        ArrayAttr([IntAttr(1)]),
        i8,
        NnMemorySpaceAttr.from_name(space_name),
    )


def _parse_img2col_helper(expr: Img2ColAST) -> tuple[object, dict[str, int]]:
    """解析 img2col helper 调用参数。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一解析 `img2col1d/img2col2d` 的位置参数与关键字参数。
    - 应用默认值并输出数值化属性，供 emit/type 推导复用。

    使用示例:
    - input_expr, attrs = _parse_img2col_helper(img2col_ast)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    spec = _IMG2COL_PARAM_TABLE.get(expr.kind)
    if spec is None:
        raise _LoweringError("Unsupported img2col helper", location=expr.location)
    param_names, defaults = spec

    if len(expr.args) > len(param_names):
        raise _LoweringError(f"{expr.kind} arity mismatch", location=expr.location)

    params: dict[str, object] = {}
    for index, arg in enumerate(expr.args):
        params[param_names[index]] = arg

    for key, value in expr.kwargs.items():
        if key not in param_names:
            raise _LoweringError(f"{expr.kind} got unexpected keyword '{key}'", location=expr.location)
        if key in params:
            raise _LoweringError(f"{expr.kind} got multiple values for argument '{key}'", location=expr.location)
        params[key] = value

    for name in param_names:
        if name in params:
            continue
        if name in defaults:
            params[name] = defaults[name]
            continue
        raise _LoweringError(f"{expr.kind} missing required argument '{name}'", location=expr.location)

    input_expr = params.pop("value")
    resolved: dict[str, int] = {}
    for name, value in params.items():
        if isinstance(value, ConstAST):
            if isinstance(value.value, int):
                resolved[name] = value.value
                continue
            raise _LoweringError(f"{expr.kind} {name} must be int", location=value.location)
        if isinstance(value, int):
            resolved[name] = value
            continue
        raise _LoweringError(f"{expr.kind} {name} must be int", location=getattr(value, "location", None))

    return input_expr, resolved


def _ensure_supported_statements(function_ast: FunctionAST) -> list[object]:
    """校验函数体中的 AST 语句是否属于当前 lowering 支持范围。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 拒绝空函数体。
    - 遍历并检查每条语句的 AST 类型，提前在发射前给出统一诊断。

    使用示例:
    - _ensure_supported_statements(function_ast)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
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
                Img2ColAST,
                DmaFreeAST,
                ForAST,
                ArchGetDynamicMemoryAST,
                ArchLaunchKernelAST,
                ArchQueryAST,
            ),
        ):
            raise _LoweringError("Unsupported AST expression for lowering", location=getattr(expr, "location", None))
    return statements


def _expect_memory_value(value: object, location: SourceLocation | None) -> NnMemoryType:
    """断言 operand/result 的类型为 `nn.memory`。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 统一校验 `value.type` 是否为 `NnMemoryType`。
    - 校验成功时返回具体类型，便于调用方继续使用。

    使用示例:
    - value_type = _expect_memory_value(value, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    if not isinstance(value.type, NnMemoryType):
        raise _LoweringError("Operand must be nn.memory", location=location)
    return value.type


def _expr_key(expr: object) -> int:
    """为 AST 节点生成缓存键。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 当前直接使用 Python 对象 `id(expr)` 作为缓存键。
    - 供 `ctx.cache` 与 `ctx.types` 在单次 lowering 流程中复用。

    使用示例:
    - key = _expr_key(expr)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
    return id(expr)


def _infer_expr_type(
    expr: object,
    type_map: dict[int, object],
    runtime_values: dict[str, object] | None = None,
) -> object:
    """推导表达式在 lowering 前的结果类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一处理常量、DMA、arch query、symbol 与 nn 二元表达式的类型推导。
    - 对 `nn.add` mixed memory+const/symbol 路径执行 promotion，并在纯 scalar/symbol 输入时给出显式诊断。

    使用示例:
    - _infer_expr_type(BinaryExprAST(op="add", lhs=lhs, rhs=rhs), type_map)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

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
            shape_attr = ArrayAttr(
                _build_static_index_list(
                    expr.sizes,
                    rank,
                    default_value=1,
                    location=expr.location,
                    runtime_values=runtime_values,
                )
            )
        stride_attr = ArrayAttr(_build_default_stride_attrs(shape_attr.data))
        space_attr = _memory_space_from_ast(expr.space, source_type.space)
        result_type = NnMemoryType(shape_attr, stride_attr, source_type.element_type, space_attr)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, DmaAllocAST):
        shape_attr = _build_static_index_attrs_exact(expr.shape, location=expr.location, runtime_values=runtime_values)
        stride_attr = (
            _build_static_index_attrs_exact(expr.stride, location=expr.location, runtime_values=runtime_values)
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
        source_type = _infer_expr_type(expr.source, type_map, runtime_values=runtime_values)
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
        source_type = _infer_expr_type(expr.source, type_map, runtime_values=runtime_values)
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
        source_type = _infer_expr_type(expr.source, type_map, runtime_values=runtime_values)
        if not isinstance(source_type, NnMemoryType):
            raise _LoweringError("view source must have nn.memory type", location=expr.location)
        shape_attr = _build_static_index_attrs_exact(expr.size, location=expr.location, runtime_values=runtime_values)
        stride_attr = source_type.stride.data
        result_type = _memory_type_from_parts(shape_attr, stride_attr, source_type.element_type, source_type.space)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, DmaReshapeAST):
        source_type = _infer_expr_type(expr.source, type_map, runtime_values=runtime_values)
        if not isinstance(source_type, NnMemoryType):
            raise _LoweringError("reshape source must have nn.memory type", location=expr.location)
        shape_attr = _build_static_index_attrs_exact(expr.shape, location=expr.location, runtime_values=runtime_values)
        result_type = _memory_type_from_parts(
            shape_attr,
            _build_default_stride_attrs(shape_attr),
            source_type.element_type,
            source_type.space,
        )
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, DmaFlattenAST):
        source_type = _infer_expr_type(expr.source, type_map, runtime_values=runtime_values)
        if not isinstance(source_type, NnMemoryType):
            raise _LoweringError("flatten source must have nn.memory type", location=expr.location)
        shape_attr = [_shape_numel_attr(source_type.shape.data)]
        result_type = _memory_type_from_parts(shape_attr, [IntAttr(1)], source_type.element_type, source_type.space)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, Img2ColAST):
        input_expr, params = _parse_img2col_helper(expr)
        input_type = _infer_expr_type(input_expr, type_map, runtime_values=runtime_values)
        if not isinstance(input_type, NnMemoryType):
            raise _LoweringError(f"{expr.kind} input must be nn.memory", location=expr.location)

        def _dim_value(attr: Attribute) -> int | str:
            """解析维度属性为 Python 值。

            功能说明：
            - 支持 `IntAttr` / `StringAttr`，分别返回整数或字符串；其他类型返回 `"?"`。

            使用示例：
            - `_dim_value(IntAttr(3)) -> 3`
            - `_dim_value(StringAttr("K")) -> "K"`

            创建者：朽木露琪亚
            最后修改人：朽木露琪亚

            关联文件：
            - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
            - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
            - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
            """
            if isinstance(attr, IntAttr):
                return attr.data
            if isinstance(attr, StringAttr):
                return attr.data
            return "?"

        def _mul_dim(lhs: int | str, rhs: int | str) -> int | str:
            """执行维度乘法合并。

            功能说明：
            - 当任一输入为 `"?"` 时返回 `"?"`；否则返回 `_mul_symbol` 的合并结果。

            使用示例：
            - `_mul_dim(2, 3) -> 6`
            - `_mul_dim("?", 4) -> "?"`

            创建者：朽木露琪亚
            最后修改人：朽木露琪亚

            关联文件：
            - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
            - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
            - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
            """
            if lhs == "?" or rhs == "?":
                return "?"
            return _mul_symbol(lhs, rhs)

        def _img2col_out_dim(dim: int | str, k: int, s: int, d: int, p1: int, p2: int) -> int | str:
            """计算 img2col 输出维度。

            功能说明：
            - 输入维度为整数且 `s != 0` 时计算输出尺寸；否则返回 `"?"`。

            使用示例：
            - `_img2col_out_dim(32, 3, 1, 1, 1, 1) -> 32`
            - `_img2col_out_dim("?", 3, 1, 1, 0, 0) -> "?"`

            创建者：朽木露琪亚
            最后修改人：朽木露琪亚

            关联文件：
            - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
            - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
            - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
            """
            if not isinstance(dim, int) or s == 0:
                return "?"
            return (dim + p1 + p2 - d * (k - 1) - 1) // s + 1

        shape = list(input_type.shape.data)
        if expr.kind == "img2col1d":
            if len(shape) != 3:
                raise _LoweringError("img2col1d input must be rank-3 nn.memory", location=expr.location)
            n_dim, c_dim, w_dim = (_dim_value(item) for item in shape)
            kw = params["kw"]
            sw = params["sw"]
            dw = params["dw"]
            pl = params["pl"]
            pr = params["pr"]
            w_out = _img2col_out_dim(w_dim, kw, sw, dw, pl, pr)
            out_channels = _mul_dim(c_dim, kw)
            out_shape = [_dim_to_attr(n_dim), _dim_to_attr(out_channels), _dim_to_attr(w_out)]
        elif expr.kind == "img2col2d":
            if len(shape) != 4:
                raise _LoweringError("img2col2d input must be rank-4 nn.memory", location=expr.location)
            n_dim, c_dim, h_dim, w_dim = (_dim_value(item) for item in shape)
            kh = params["kh"]
            kw = params["kw"]
            sh = params["sh"]
            sw = params["sw"]
            dh = params["dh"]
            dw = params["dw"]
            ph = params["ph"]
            pw = params["pw"]
            pl = params["pl"]
            pr = params["pr"]
            h_out = _img2col_out_dim(h_dim, kh, sh, dh, ph, pw)
            w_out = _img2col_out_dim(w_dim, kw, sw, dw, pl, pr)
            out_channels = _mul_dim(_mul_dim(c_dim, kh), kw)
            out_hw = _mul_dim(h_out, w_out)
            out_shape = [_dim_to_attr(n_dim), _dim_to_attr(out_channels), _dim_to_attr(out_hw)]
        else:
            raise _LoweringError("Unsupported img2col helper", location=expr.location)

        stride_attr = _build_default_stride_attrs(out_shape)
        result_type = _memory_type_from_parts(out_shape, stride_attr, input_type.element_type, input_type.space)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, StoreAST):
        raise _LoweringError("StoreAST does not produce a value", location=expr.location)
    if isinstance(expr, DmaFreeAST):
        raise _LoweringError("free does not produce a value", location=expr.location)
    if isinstance(expr, ForAST):
        raise _LoweringError("ForAST does not produce a value", location=expr.location)
    if isinstance(expr, ArchLaunchKernelAST):
        raise _LoweringError("launch_kernel does not produce a value", location=expr.location)
    if isinstance(expr, ArchGetDynamicMemoryAST):
        result_type = _build_dynamic_memory_type(expr.space, location=expr.location)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, ArchQueryAST):
        query_map = {
            "get_block_id": "block_id",
            "get_block_num": "block_num",
            "get_subthread_id": "subthread_id",
            "get_subthread_num": "subthread_num",
            "get_thread_id": "thread_id",
            "get_thread_num": "thread_num",
        }
        symbol_name = query_map.get(expr.query_name)
        if symbol_name is None:
            raise _LoweringError("Unsupported arch query", location=expr.location)
        result_type = SymbolValueType.from_expr(symbol_name)
        type_map[expr_key] = result_type
        return result_type

    if isinstance(expr, BinaryExprAST):
        lhs_type = _infer_expr_type(expr.lhs, type_map, runtime_values=runtime_values)
        rhs_type = _infer_expr_type(expr.rhs, type_map, runtime_values=runtime_values)
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
        lhs_is_memory = isinstance(lhs_type, NnMemoryType)
        rhs_is_memory = isinstance(rhs_type, NnMemoryType)
        if expr.op == "add" and lhs_is_memory != rhs_is_memory:
            memory_type = lhs_type if lhs_is_memory else rhs_type
            scalar_type = rhs_type if lhs_is_memory else lhs_type
            if not isinstance(memory_type, NnMemoryType):
                raise _LoweringError("nn.add requires at least one nn.memory operand", location=expr.location)
            result_type = _infer_add_mixed_memory_type(memory_type, scalar_type, expr.location)
            type_map[expr_key] = result_type
            return result_type
        if expr.op == "add" and not lhs_is_memory and not rhs_is_memory:
            raise _LoweringError("nn.add requires at least one nn.memory operand", location=expr.location)
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
        lhs_type = _infer_expr_type(expr.lhs, type_map, runtime_values=runtime_values)
        rhs_type = _infer_expr_type(expr.rhs, type_map, runtime_values=runtime_values)
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


def _cast_add_scalar_operand(
    value: SSAValue,
    target_element_type: Attribute,
    ctx: EmitContext,
    location: SourceLocation | None,
) -> SSAValue:
    """将 `nn.add` mixed 路径中的标量 operand 转换到目标 dtype。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - `!symbol.int` 视为有符号整数，并在需要时 lowering 为浮点 cast。
    - 仅生成满足 `nn.add` mixed promotion 所需的最少标量 cast。

    使用示例:
    - _cast_add_scalar_operand(value, f32, ctx, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

    source_type = value.type
    _normalize_add_scalar_element_type(source_type, location)
    if source_type == target_element_type:
        return value

    if isinstance(source_type, SymbolValueType) or source_type == i32:
        if isinstance(target_element_type, Float16Type) or target_element_type == f32:
            cast_op = arith.SIToFPOp(value, target_element_type)
            ctx.builder.add_op(cast_op)
            return cast_op.result
        return value
    if isinstance(source_type, Float16Type) and target_element_type == f32:
        cast_op = arith.ExtFOp(value, target_element_type)
        ctx.builder.add_op(cast_op)
        return cast_op.result
    if source_type == f32 and isinstance(target_element_type, Float16Type):
        cast_op = arith.TruncFOp(value, target_element_type)
        ctx.builder.add_op(cast_op)
        return cast_op.result
    raise _LoweringError("nn.add scalar element_type must be i32/f16/f32 or symbol.int", location=location)


def _lower_mixed_add_expr(
    expr: BinaryExprAST,
    lhs: SSAValue,
    rhs: SSAValue,
    ctx: EmitContext,
) -> SSAValue | None:
    """lower `nn.add` 的 mixed memory+scalar/symbol 路径。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 保持 memory operand 的 `shape/stride/space`，并只在 memory dtype 落后于目标 dtype 时插入 `dma.cast`。
    - 标量侧根据 promotion 结果插入最少 `arith` cast，最终发射单个 `nn.add`。

    使用示例:
    - _lower_mixed_add_expr(expr, lhs, rhs, ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

    lhs_type = getattr(lhs, "type", None)
    rhs_type = getattr(rhs, "type", None)
    lhs_is_memory = isinstance(lhs_type, NnMemoryType)
    rhs_is_memory = isinstance(rhs_type, NnMemoryType)
    if lhs_is_memory and rhs_is_memory:
        return None
    if not lhs_is_memory and not rhs_is_memory:
        raise _LoweringError("nn.add requires at least one nn.memory operand", location=expr.location)

    result_type = _infer_expr_type(expr, ctx.types)
    if not isinstance(result_type, NnMemoryType):
        raise _LoweringError("Binary op result must be nn.memory", location=expr.location)

    memory_value = lhs if lhs_is_memory else rhs
    memory_type = lhs_type if lhs_is_memory else rhs_type
    scalar_value = rhs if lhs_is_memory else lhs
    if not isinstance(memory_type, NnMemoryType):
        raise _LoweringError("nn.add requires at least one nn.memory operand", location=expr.location)

    if memory_type.element_type != result_type.element_type:
        cast_type = _memory_type_from_parts(
            memory_type.shape.data,
            memory_type.stride.data,
            result_type.element_type,
            memory_type.space,
        )
        cast_op = DmaCastOp(memory_value, cast_type)
        ctx.builder.add_op(cast_op)
        memory_value = cast_op.result
        memory_type = cast_type

    scalar_value = _cast_add_scalar_operand(scalar_value, result_type.element_type, ctx, expr.location)
    op = NnAddOp(
        memory_value if lhs_is_memory else scalar_value,
        scalar_value if lhs_is_memory else memory_value,
        result_type,
        result_type.space,
    )
    ctx.builder.add_op(op)
    ctx._set_cache(_expr_key(expr), op.result)
    return op.result


def _lower_expr(expr: object, ctx: EmitContext) -> object:
    """将表达式 AST 递归下沉为 MLIR SSA value。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 递归处理常量、内存操作与算术/比较表达式，生成对应的 MLIR op。
    - 通过 `EmitContext` 缓存表达式结果，避免重复发射。

    参数说明:
    - expr: 待下沉的 AST 节点。
    - ctx: 发射上下文，包含 builder、symbols、types 与缓存。

    返回说明:
    - 返回对应的 SSAValue（通常为 op.result），供后续表达式使用。

    限制与异常:
    - 不支持的 AST 节点会抛出 `_LoweringError`。
    - `StoreAST` 与 `DmaFreeAST` 不产生值，会抛出 `_LoweringError`。
    - 未知输入引用会抛出 `_LoweringError`。

    使用示例:
    - value = _lower_expr(expr, ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
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
        rank = len(result_type.shape.data)
        offsets = _build_index_attrs(expr.offset, rank, ctx, location=expr.location)
        shape = _build_index_operands_exact(expr.size, ctx, location=expr.location)
        stride = _build_index_operands_from_layout(result_type.stride, ctx, location=expr.location)
        op = DmaViewOp(source, offsets, shape, stride, result_type)
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
        shape_operand = _build_flatten_shape_operands(source, source_type, ctx, location=expr.location)
        op = DmaReshapeOp(source, shape_operand, result_type)
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        return op.result
    if isinstance(expr, Img2ColAST):
        input_expr, params = _parse_img2col_helper(expr)
        input_value = _lower_expr(input_expr, ctx)
        input_type = _expect_memory_value(input_value, expr.location)
        result_type = _infer_expr_type(expr, ctx.types)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError(f"{expr.kind} result must be nn.memory", location=expr.location)
        if expr.kind == "img2col1d":
            op = NnImg2col1dOp(
                input_value,
                result_type,
                kw=params["kw"],
                sw=params["sw"],
                dw=params["dw"],
                pl=params["pl"],
                pr=params["pr"],
                space=input_type.space,
            )
        elif expr.kind == "img2col2d":
            op = NnImg2col2dOp(
                input_value,
                result_type,
                kh=params["kh"],
                kw=params["kw"],
                sh=params["sh"],
                sw=params["sw"],
                dh=params["dh"],
                dw=params["dw"],
                ph=params["ph"],
                pw=params["pw"],
                pl=params["pl"],
                pr=params["pr"],
                space=input_type.space,
            )
        else:
            raise _LoweringError("Unsupported img2col helper", location=expr.location)
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        return op.result
    if isinstance(expr, StoreAST):
        raise _LoweringError("StoreAST does not produce a value", location=expr.location)
    if isinstance(expr, DmaFreeAST):
        raise _LoweringError("free does not produce a value", location=expr.location)
    if isinstance(expr, ArchGetDynamicMemoryAST):
        result_type = _build_dynamic_memory_type(expr.space, location=expr.location)
        space_name = _DYNAMIC_MEMORY_SPACE_MAP.get(expr.space)
        if space_name is None:
            raise _LoweringError("get_dynamic_memory space must be on-chip MemorySpace", location=expr.location)
        op = ArchGetDynamicMemoryOp(NnMemorySpaceAttr.from_name(space_name), result_type)
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        ctx.types[expr_key] = op.result.type
        return op.result
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
        elif expr.query_name == "get_thread_num":
            op = ArchGetThreadNumOp()
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
        if expr.op == "add":
            mixed_add_result = _lower_mixed_add_expr(expr, lhs, rhs, ctx)
            if mixed_add_result is not None:
                return mixed_add_result
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
    """查询并缓存符号引用对应的 SSA value。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 从上下文符号表读取输入 value，并写入表达式缓存。
    - 同步更新 `ctx.types` 中的类型映射。

    参数说明:
    - node: 输入引用节点（TensorAST/ScalarArgAST/VarAST）。
    - ctx: 发射上下文，包含 symbols/types/cache。

    返回说明:
    - 返回已缓存的 SSAValue。

    限制与异常:
    - 符号不存在时抛出 `_LoweringError`。

    使用示例:
    - value = _lookup_symbol(node, ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """
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
    """将单个 AST 节点发射为 MLIR value 或 op。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 统一处理 expression 与 statement 节点的 lowering 入口。
    - 按节点类型分派到符号查找、表达式 lowering 或 store 发射路径。
    - 对需要类型信息的表达式先补做 `_infer_expr_type`，再进入 `_lower_expr`。
    - `free(...)` 作为语句 helper 时会发射单个 `dma.free`，但不会产生新的 SSA 结果。

    使用示例:
    - value = emit_mlir(BinaryExprAST(op="add", lhs=lhs, rhs=rhs), ctx)
    - emit_mlir(DmaFreeAST(value=tensor_ast, location=None), ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py), [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

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
            Img2ColAST,
            ArchGetDynamicMemoryAST,
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
        free_op = DmaFreeOp(value)
        ctx.builder.add_op(free_op)
        return free_op
    if isinstance(node, ArchLaunchKernelAST):
        if not isinstance(node.name, str) or node.name == "":
            raise _LoweringError("launch_kernel name must be non-empty str", location=node.location)
        block = _lower_expr(node.block, ctx)
        thread = _lower_expr(node.thread, ctx)
        subthread = _lower_expr(node.subthread, ctx)

        def _ensure_symbol_extent(value: SSAValue, dim_name: str) -> None:
            if not isinstance(value.type, SymbolValueType):
                raise _LoweringError(f"launch_kernel {dim_name} must be !symbol.int", location=node.location)
            expr_text = value.type.expr.expr.data
            if isinstance(expr_text, str) and expr_text.lstrip("-").isdigit():
                if int(expr_text) <= 0:
                    raise _LoweringError(f"launch_kernel {dim_name} must be > 0", location=node.location)

        _ensure_symbol_extent(block, "block")
        _ensure_symbol_extent(thread, "thread")
        _ensure_symbol_extent(subthread, "subthread")
        op = ArchLaunchKernelOp(node.name, block, thread, subthread)
        ctx.builder.add_op(op)
        return op
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
