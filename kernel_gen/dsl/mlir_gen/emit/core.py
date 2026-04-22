"""AST emit utilities for DSL nodes.

创建者: 小李飞刀
最后一次更改: jcc你莫辜负

功能说明:
- 提供 AST 节点到 MLIR SSA value/op 的发射入口。
- 维护节点发射所需的上下文、类型推导与显式错误。

使用示例:
- from kernel_gen.dsl.mlir_gen.emit import EmitContext, emit_mlir
- value = emit_mlir(expr_ast, ctx)

关联文件:
- spec: spec/dsl/emit_mlir.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: kernel_gen/dsl/mlir_gen/emit/core.py
"""

from __future__ import annotations

import ast as py_ast
import re
from typing import Sequence

from xdsl.dialects import arith, func, scf
from xdsl.dialects.builtin import (
    ArrayAttr,
    BFloat16Type,
    FloatAttr,
    Float16Type,
    Float32Type,
    Float64Type,
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
    i64,
)
from xdsl.ir import Attribute, Block, SSAValue
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.arch import (
    ArchBarrierOp,
    ArchGetBlockIdOp,
    ArchGetBlockNumOp,
    ArchGetDynamicMemoryOp,
    ArchGetSubthreadIdOp,
    ArchGetSubthreadNumOp,
    ArchLaunchKernelOp,
    ArchScopeAttr,
    ArchVisibilityAttr,
    ArchGetThreadIdOp,
    ArchGetThreadNumOp,
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
    NnCastOp,
    NnEqOp,
    NnExpOp,
    NnFloorDivOp,
    NnGeOp,
    NnGtOp,
    NnHardSigmoidOp,
    NnMatmulOp,
    NnLeakyReluOp,
    NnLeOp,
    NnLtOp,
    NnImg2col1dOp,
    NnImg2col2dOp,
    NnMemorySpaceAttr,
    NnMemoryType,
    NnMulOp,
    NnNeOp,
    NnReduceMaxOp,
    NnReduceMinOp,
    NnReduceSumOp,
    NnReluOp,
    NnSigmoidOp,
    NnSoftmaxOp,
    NnSubOp,
    NnTanhOp,
    NnTrueDivOp,
    NnTransposeOp,
)
from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolConstOp,
    SymbolDivOp,
    SymbolEqOp,
    SymbolGeOp,
    SymbolGtOp,
    SymbolFloorDivOp,
    SymbolForOp,
    SymbolGetDimOp,
    SymbolGetStrideOp,
    SymbolLeOp,
    SymbolLtOp,
    SymbolMulOp,
    SymbolNeOp,
    SymbolIterType,
    SymbolSubOp,
    SymbolToIntOp,
    SymbolToFloatOp,
    SymbolValueType,
    build_public_symbol_expr,
)
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import Farmat, NumericType
from kernel_gen.operation import dma as _KG_OPERATION_DMA
from kernel_gen.target import registry
from kernel_gen.operation import arch as _KG_OPERATION_ARCH
from kernel_gen.operation import nn as _KG_OPERATION_NN

from kernel_gen.dsl.ast import (
    ArchBarrierAST,
    ArchGetDynamicMemoryAST,
    ArchLaunchKernelAST,
    ArchQueryAST,
    BinaryExprAST,
    BlockAST,
    CompareExprAST,
    ConstAST,
    ConvAST,
    DmaAllocAST,
    DmaCastAST,
    DmaCopyAST,
    DmaFlattenAST,
    DmaFreeAST,
    DmaReshapeAST,
    DmaViewAST,
    FCAST,
    ForAST,
    FunctionAST,
    Img2ColAST,
    LoadAST,
    MatmulAST,
    NnBroadcastAST,
    NnBroadcastToAST,
    NnReduceAST,
    NnSoftmaxAST,
    NnTransposeAST,
    NnUnaryAST,
    PythonCalleeCallAST,
    ScalarArgAST,
    SymbolToFloatAST,
    SourceLocation,
    StoreAST,
    TensorAST,
    TensorAxisAccessAST,
    VarAST,
)


_MEMORY_SPACE_MAP = {
    MemorySpace.GM: "global",
    MemorySpace.SM: "shared",
    MemorySpace.LM: "local",
    MemorySpace.TSM: "tsm",
    MemorySpace.TLM1: "tlm1",
    MemorySpace.TLM2: "tlm2",
    MemorySpace.TLM3: "tlm3",
}

_DYNAMIC_MEMORY_SPACE_MAP = {
    MemorySpace.SM: "shared",
    MemorySpace.LM: "local",
    MemorySpace.TSM: "tsm",
    MemorySpace.TLM1: "tlm1",
    MemorySpace.TLM2: "tlm2",
    MemorySpace.TLM3: "tlm3",
}

_MLIR_GEN_CALLEE_REGISTRY_CONFIG_KEY = "__mlir_gen_callee_registry__"
_MLIR_GEN_CALLEE_COMPILER_CONFIG_KEY = "__mlir_gen_callee_compiler__"

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

_CONV_PARAM_DEFAULTS: dict[str, int] = {
    "sh": 1,
    "sw": 1,
    "dh": 1,
    "dw": 1,
    "ph": 0,
    "pw": 0,
    "pl": 0,
    "pr": 0,
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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


def _ctx_runtime_values(ctx: EmitContext) -> dict[str, object] | None:
    """读取发射上下文中的 runtime_values。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 统一从 `ctx.config["__runtime_values__"]` 读取运行时符号表。
    - 仅接受 `dict[str, object]`，其他配置一律视作不存在。

    使用示例:
    - runtime_values = _ctx_runtime_values(ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

    if not isinstance(ctx.config, dict):
        return None
    candidate = ctx.config.get("__runtime_values__")
    if isinstance(candidate, dict):
        return candidate
    return None


def _dtype_to_xdsl(dtype: NumericType, location: SourceLocation | None = None) -> object:
    """将 NumericType 映射为 xdsl element type。

    创建者: 我不是牛马
    最后一次更改: 小李飞刀

    功能说明:
    - 将 DSL NumericType 转为 nn.memory 的 element_type，当前覆盖 Bool/Int8/Int32/Int64/BFloat16/Float16/Float32/Float64。
    - 遇到不支持类型时抛出 LoweringError。

    使用示例:
    - _dtype_to_xdsl(NumericType.Float32)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    if dtype is NumericType.Bool:
        return i1
    if dtype is NumericType.BFloat16:
        return BFloat16Type()
    if dtype is NumericType.Float16:
        return Float16Type()
    if dtype is NumericType.Float32:
        return f32
    if dtype is NumericType.Float64:
        return Float64Type()
    if dtype is NumericType.Int8:
        return i8
    if dtype is NumericType.Int32:
        return i32
    if dtype is NumericType.Int64:
        return i64
    if dtype is NumericType.Bool:
        return i1
    raise _LoweringError(f"Unsupported dtype: {dtype}", location=location)


def _xdsl_to_dtype(element_type: Attribute, location: SourceLocation | None = None) -> NumericType:
    """将 xdsl element_type 还原为 NumericType。

    创建者: 我不是牛马
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 Float16/BFloat16/Float32/Float64/Int32/Int64/Bool 解析为 NumericType。
    - 不支持的 element_type 抛出 LoweringError。

    使用示例:
    - _xdsl_to_dtype(f32)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    if isinstance(element_type, BFloat16Type):
        return NumericType.BFloat16
    if isinstance(element_type, Float16Type):
        return NumericType.Float16
    if element_type == f32:
        return NumericType.Float32
    if isinstance(element_type, Float64Type):
        return NumericType.Float64
    if element_type == i8:
        return NumericType.Int8
    if element_type == i32:
        return NumericType.Int32
    if element_type == i64:
        return NumericType.Int64
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    try:
        lhs_dtype = _xdsl_to_dtype(lhs_type.element_type, location)
        rhs_dtype = _xdsl_to_dtype(rhs_type.element_type, location)
        target_dtype = Memory._promote_ranked_dtype(lhs_dtype, rhs_dtype)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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


def _eval_symbolic_dim_node(expr: py_ast.AST, location: SourceLocation | None) -> int | SymbolDim:
    """求值符号维表达式 AST 节点为 `int` 或 `SymbolDim`。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 仅接受 `int`、标识符与 `+ - * /` 基础算术。
    - 使用 `SymbolDim` 运算保持与运行时符号表达式一致。

    使用示例:
    - _eval_symbolic_dim_node(py_ast.parse("N + 1", mode="eval").body, None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    if isinstance(expr, py_ast.Constant) and isinstance(expr.value, int):
        return expr.value
    if isinstance(expr, py_ast.Name):
        return SymbolDim(expr.id)
    if isinstance(expr, py_ast.UnaryOp) and isinstance(expr.op, py_ast.USub):
        value = _eval_symbolic_dim_node(expr.operand, location)
        if isinstance(value, SymbolDim):
            return SymbolDim(0) - value
        if isinstance(value, int):
            return -value
        raise _LoweringError("Unsupported symbolic dim expression", location=location)
    if isinstance(expr, py_ast.BinOp):
        lhs = _eval_symbolic_dim_node(expr.left, location)
        rhs = _eval_symbolic_dim_node(expr.right, location)
        if isinstance(expr.op, py_ast.Add):
            return lhs + rhs
        if isinstance(expr.op, py_ast.Sub):
            return lhs - rhs
        if isinstance(expr.op, py_ast.Mult):
            return lhs * rhs
        if isinstance(expr.op, py_ast.Div):
            if isinstance(lhs, int) and isinstance(rhs, int):
                if rhs == 0 or lhs % rhs != 0:
                    raise _LoweringError("Unsupported symbolic dim expression", location=location)
                return lhs // rhs
            if isinstance(lhs, int):
                lhs = SymbolDim(lhs)
            if isinstance(rhs, int):
                return lhs / rhs
            return lhs / rhs
        raise _LoweringError("Unsupported symbolic dim expression", location=location)
    raise _LoweringError("Unsupported symbolic dim expression", location=location)


def _eval_symbolic_dim_expr(expr_text: str, location: SourceLocation | None) -> SymbolDim:
    """解析符号维表达式文本为 `SymbolDim`。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 通过 Python AST 安全解析表达式，并使用 `SymbolDim` 运算求值。
    - 统一为 `SymbolDim` 返回，便于后续 stride/shape 推导。

    使用示例:
    - _eval_symbolic_dim_expr("(N + 1) / 2 + 1", location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    try:
        parsed = py_ast.parse(expr_text, mode="eval").body
    except SyntaxError as exc:
        raise _LoweringError("Unsupported symbolic dim expression", location=location) from exc
    value = _eval_symbolic_dim_node(parsed, location)
    if isinstance(value, int):
        return SymbolDim(value)
    if isinstance(value, SymbolDim):
        return value
    raise _LoweringError("Unsupported symbolic dim expression", location=location)


def _shape_attr_to_symbol_dim(attr: Attribute, location: SourceLocation | None) -> SymbolDim | None:
    """将 shape Attribute 规整为 SymbolDim，支持未知维度兜底。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - IntAttr 转为静态 SymbolDim。
    - StringAttr 转为符号表达式 SymbolDim；若为 "?" 则返回 None 表示未知。

    使用示例:
    - _shape_attr_to_symbol_dim(IntAttr(4), location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    if isinstance(attr, IntAttr):
        return SymbolDim(attr.data)
    if isinstance(attr, StringAttr):
        if attr.data == "?":
            return None
        return _eval_symbolic_dim_expr(attr.data, location)
    raise _LoweringError("Unsupported shape attribute", location=location)


def _build_symbolic_stride_attrs(shape: Sequence[Attribute], location: SourceLocation | None) -> list[Attribute]:
    """基于 SymbolDim 语义生成 stride 属性。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 使用 `SymbolDim` 的算术语义构造 stride，确保与 Memory 的默认 stride 表达式一致。
    - 若存在未知维度（"?"），其自身及更高维 stride 统一记为 "?"。

    使用示例:
    - _build_symbolic_stride_attrs([IntAttr(2), StringAttr("N")], location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    stride_values: list[int | str] = []
    running: SymbolDim | None = SymbolDim(1)
    for dim_attr in reversed(shape):
        if running is None:
            stride_values.append("?")
            continue
        stride_values.append(running.get_value())
        dim_symbol = _shape_attr_to_symbol_dim(dim_attr, location)
        if dim_symbol is None:
            running = None
        else:
            running = dim_symbol * running
    stride_values.reverse()
    return [_dim_to_attr(value) for value in stride_values]


def _dim_to_attr(value: int | str | SymbolDim) -> object:
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    if isinstance(value, SymbolDim):
        value = value.get_value()
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    最后一次更改: 金铲铲大作战

    功能说明:
    - 直接生成 `symbol.const`，保持 !symbol.int<"expr"> 常量形态一致。

    使用示例:
    - _const_symbol_int(4, ctx, location)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    op = SymbolConstOp(value)
    ctx.builder.add_op(op)
    return op.result


def _const_i32(value: int, ctx: EmitContext, location: SourceLocation | None) -> SSAValue:
    """构造 i32 常量 SSA value。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 生成 `arith.constant` i32 常量，供 img2col 等 op 使用。

    使用示例:
    - value_operand = _const_i32(4, ctx, location)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    attr = IntegerAttr(value, i32)
    op = arith.ConstantOp(attr)
    ctx.builder.add_op(op)
    return op.result


def _build_arch_barrier_visibility_attr(
    visibility: object,
    location: SourceLocation | None,
) -> ArrayAttr[Attribute]:
    """将 barrier visibility AST 值转换为 arch.barrier 属性。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅接受非空 `list[BarrierVisibility]`。
    - 将 `BarrierVisibility.TSM/TLM` 映射为 `#arch.visibility<tsm/tlm>`，保持原有顺序。

    使用示例:
    - _build_arch_barrier_visibility_attr(
    -     [_KG_OPERATION_ARCH.BarrierVisibility.TSM, _KG_OPERATION_ARCH.BarrierVisibility.TLM],
    -     location=None,
    - )

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    if not isinstance(visibility, list) or not visibility or not all(
        isinstance(space, _KG_OPERATION_ARCH.BarrierVisibility) for space in visibility
    ):
        raise _LoweringError("barrier visibility must be non-empty BarrierVisibility list", location=location)
    space_map = {
        _KG_OPERATION_ARCH.BarrierVisibility.TSM: "tsm",
        _KG_OPERATION_ARCH.BarrierVisibility.TLM: "tlm",
    }
    attrs: list[Attribute] = []
    for space in visibility:
        space_name = space_map.get(space)
        if space_name is None:
            raise _LoweringError("barrier visibility must be non-empty BarrierVisibility list", location=location)
        attrs.append(ArchVisibilityAttr.from_name(space_name))
    return ArrayAttr(attrs)


def _build_arch_barrier_scope_attr(
    scope: object,
    location: SourceLocation | None,
) -> ArchScopeAttr:
    """将 barrier scope AST 值转换为 `#arch.scope<...>`。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅接受 operation 层 `BarrierScope` 枚举。
    - 统一复用 `ArchScopeAttr.from_name(...)` 构造 IR 属性。

    使用示例:
    - _build_arch_barrier_scope_attr(_KG_OPERATION_ARCH.BarrierScope.BLOCK, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    if not isinstance(scope, _KG_OPERATION_ARCH.BarrierScope):
        raise _LoweringError("barrier scope must be BarrierScope", location=location)
    return ArchScopeAttr.from_name(scope.value)


def _lower_launch_extent_symbol(
    extent: object,
    dim_name: str,
    ctx: EmitContext,
    location: SourceLocation | None,
    *,
    allow_zero: bool = False,
) -> SSAValue:
    """将 launch extent 归一化为 `!symbol.int<...>`。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 `ConstAST(int)` 与 `ScalarArgAST(int)` 两类 DSL extent 入口。
    - 对静态已知值保持正整数或非负整数约束，并统一返回 `!symbol.int` SSAValue。

    使用示例:
    - _lower_launch_extent_symbol(ConstAST(8), "thread", ctx, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    if isinstance(extent, ConstAST):
        if not isinstance(extent.value, int):
            raise _LoweringError(f"launch_kernel {dim_name} must be !symbol.int", location=location)
        if allow_zero:
            if extent.value < 0:
                raise _LoweringError(f"launch_kernel {dim_name} must be >= 0", location=location)
        elif extent.value <= 0:
            raise _LoweringError(f"launch_kernel {dim_name} must be > 0", location=location)
        return _const_symbol_int(extent.value, ctx, location)

    value = _lower_expr(extent, ctx)
    if isinstance(value.type, SymbolValueType):
        expr_text = value.type.expr.expr.data
        if isinstance(expr_text, str) and expr_text.lstrip("-").isdigit():
            int_value = int(expr_text)
            if allow_zero:
                if int_value < 0:
                    raise _LoweringError(f"launch_kernel {dim_name} must be >= 0", location=location)
            elif int_value <= 0:
                raise _LoweringError(f"launch_kernel {dim_name} must be > 0", location=location)
        return value

    if isinstance(extent, ScalarArgAST):
        return _cast_to_symbol_int(value, ctx, extent.name, location)
    raise _LoweringError(f"launch_kernel {dim_name} must be !symbol.int", location=location)


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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    if isinstance(value.type, (SymbolValueType, SymbolIterType)):
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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


def _materialize_index_symbol_from_symbol_alias(
    name: str,
    ctx: EmitContext,
    location: SourceLocation | None,
) -> SSAValue | None:
    """从已绑定的 `!symbol.int` 参数中回查符号别名。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 当 `ctx.symbols` 只按参数名缓存符号 SSAValue 时，补做一次按 `!symbol.int<expr>` 的 expr 名匹配。
    - 命中后把 `name -> SSAValue` 写回 `ctx.symbols`，供后续动态 shape/stride lowering 直接复用。

    使用示例:
    - _materialize_index_symbol_from_symbol_alias("TILE_M", ctx, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    del location
    for candidate in ctx.symbols.values():
        if not isinstance(candidate, SSAValue):
            continue
        candidate_type = candidate.type
        if not isinstance(candidate_type, SymbolValueType):
            continue
        if candidate_type.expr.expr.data != name:
            continue
        ctx.symbols[name] = candidate
        return candidate
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    if name not in ctx.symbols:
        aliased = _materialize_index_symbol_from_symbol_alias(name, ctx, location)
        if aliased is not None:
            return aliased
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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


def _build_symbol_index_result(
    lhs: SSAValue,
    rhs: SSAValue,
    op_symbol: str,
    ctx: EmitContext,
    location: SourceLocation | None,
) -> SSAValue:
    """基于两个 symbol.int 操作数构造索引表达式结果。"""

    lhs_expr = lhs.type.expr.expr.data if isinstance(lhs.type, SymbolValueType) else None
    rhs_expr = rhs.type.expr.expr.data if isinstance(rhs.type, SymbolValueType) else None
    if lhs_expr is None or rhs_expr is None:
        raise _LoweringError("Unsupported index expression", location=location)
    lhs_value = _cast_to_symbol_int(lhs, ctx, lhs_expr, location)
    rhs_value = _cast_to_symbol_int(rhs, ctx, rhs_expr, location)
    result_type = SymbolValueType.from_expr(build_public_symbol_expr(lhs_value.type.expr.expr.data, rhs_value.type.expr.expr.data, op_symbol))
    if op_symbol == "+":
        op = SymbolAddOp(lhs_value, rhs_value, result_type)
    elif op_symbol == "-":
        op = SymbolSubOp(lhs_value, rhs_value, result_type)
    elif op_symbol == "*":
        op = SymbolMulOp(lhs_value, rhs_value, result_type)
    elif op_symbol == "/":
        op = SymbolDivOp(lhs_value, rhs_value, result_type)
    elif op_symbol == "//":
        op = SymbolFloorDivOp(lhs_value, rhs_value, result_type)
    else:
        raise _LoweringError("Unsupported index expression", location=location)
    ctx.builder.add_op(op)
    return op.result


def _get_symbol_index_constant(
    value: int,
    ctx: EmitContext,
    location: SourceLocation | None,
    const_cache: dict[int, SSAValue] | None,
) -> SSAValue:
    """获取或创建索引表达式里的 symbol.const。"""

    if const_cache is not None and value in const_cache:
        return const_cache[value]
    result = _const_symbol_int(value, ctx, location)
    if const_cache is not None:
        const_cache[value] = result
    return result


def _preload_symbolic_index_constants(
    expr: object,
    ctx: EmitContext,
    location: SourceLocation | None,
    const_cache: dict[int, SSAValue],
) -> None:
    """在 lowering 前预先 materialize 索引表达式里的整数常量。"""

    if isinstance(expr, ConstAST) and isinstance(expr.value, int):
        _get_symbol_index_constant(expr.value, ctx, expr.location, const_cache)
        return
    if isinstance(expr, BinaryExprAST):
        _preload_symbolic_index_constants(expr.lhs, ctx, getattr(expr.lhs, "location", None) or location, const_cache)
        _preload_symbolic_index_constants(expr.rhs, ctx, getattr(expr.rhs, "location", None) or location, const_cache)
        return
    if isinstance(expr, int):
        _get_symbol_index_constant(expr, ctx, location, const_cache)
        return
    if isinstance(expr, str):
        try:
            parsed = py_ast.parse(expr, mode="eval").body
        except SyntaxError:
            return

        def _walk(node: py_ast.AST) -> None:
            if isinstance(node, py_ast.Constant) and isinstance(node.value, int):
                _get_symbol_index_constant(node.value, ctx, location, const_cache)
                return
            if isinstance(node, py_ast.UnaryOp):
                _walk(node.operand)
                return
            if isinstance(node, py_ast.BinOp):
                _walk(node.left)
                _walk(node.right)

        _walk(parsed)


def _lower_symbolic_index_node(
    expr: py_ast.AST,
    ctx: EmitContext,
    location: SourceLocation | None,
    const_cache: dict[int, SSAValue] | None = None,
) -> SSAValue:
    """将字符串索引表达式 AST 下沉为 `!symbol.int`。"""

    if isinstance(expr, py_ast.Constant) and isinstance(expr.value, int):
        return _get_symbol_index_constant(expr.value, ctx, location, const_cache)
    if isinstance(expr, py_ast.Name):
        return _resolve_index_symbol(expr.id, ctx, location)
    if isinstance(expr, py_ast.UnaryOp) and isinstance(expr.op, py_ast.USub):
        zero = _get_symbol_index_constant(0, ctx, location, const_cache)
        operand = _lower_symbolic_index_node(expr.operand, ctx, location, const_cache)
        return _build_symbol_index_result(zero, operand, "-", ctx, location)
    if isinstance(expr, py_ast.BinOp):
        lhs = _lower_symbolic_index_node(expr.left, ctx, location, const_cache)
        rhs = _lower_symbolic_index_node(expr.right, ctx, location, const_cache)
        if isinstance(expr.op, py_ast.Add):
            return _build_symbol_index_result(lhs, rhs, "+", ctx, location)
        if isinstance(expr.op, py_ast.Sub):
            return _build_symbol_index_result(lhs, rhs, "-", ctx, location)
        if isinstance(expr.op, py_ast.Mult):
            return _build_symbol_index_result(lhs, rhs, "*", ctx, location)
        if isinstance(expr.op, py_ast.Div):
            return _build_symbol_index_result(lhs, rhs, "/", ctx, location)
        if isinstance(expr.op, py_ast.FloorDiv):
            return _build_symbol_index_result(lhs, rhs, "//", ctx, location)
    raise _LoweringError("Unsupported index expression", location=location)


def _lower_symbolic_index_text(
    expr_text: str,
    ctx: EmitContext,
    location: SourceLocation | None,
    const_cache: dict[int, SSAValue] | None = None,
) -> SSAValue:
    """将字符串形式的索引表达式下沉为 `!symbol.int`。"""

    try:
        parsed = py_ast.parse(expr_text, mode="eval").body
    except SyntaxError as exc:
        raise _LoweringError("Unsupported index expression", location=location) from exc
    return _lower_symbolic_index_node(parsed, ctx, location, const_cache)


def _resolve_index_operand(
    expr: object,
    ctx: EmitContext,
    location: SourceLocation | None,
    const_cache: dict[int, SSAValue] | None = None,
) -> SSAValue:
    """将索引表达式 lowering 为 SSA operand。

    创建者: OpenAI
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持常量、symbol 名称、循环变量和显式字符串乘法表达式。
    - 对非法输入保持统一的 index 诊断文案。
    - 常量会直接生成 `symbol.const`，保持 symbol.int 路径一致。

    使用示例:
    - _resolve_index_operand(ConstAST(2), ctx, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    if isinstance(expr, ConstAST):
        if isinstance(expr.value, int):
            return _get_symbol_index_constant(expr.value, ctx, expr.location, const_cache)
        if isinstance(expr.value, str):
            return _lower_symbolic_index_text(expr.value, ctx, expr.location, const_cache)
        raise _LoweringError("Index must be int or str", location=expr.location)
    if isinstance(expr, (ScalarArgAST, VarAST)):
        value = _lookup_symbol(expr, ctx)
        if not isinstance(value, SSAValue):
            raise _LoweringError("Index operand must be SSA value", location=expr.location)
        return _ensure_index_value(value, ctx, expr.location)
    if isinstance(expr, BinaryExprAST):
        lhs = _resolve_index_operand(expr.lhs, ctx, getattr(expr.lhs, "location", None) or location, const_cache)
        rhs = _resolve_index_operand(expr.rhs, ctx, getattr(expr.rhs, "location", None) or location, const_cache)
        op_symbol = {
            "add": "+",
            "sub": "-",
            "mul": "*",
            "div": "/",
            "floordiv": "//",
        }.get(expr.op)
        if op_symbol is None:
            raise _LoweringError("Unsupported index expression", location=location or expr.location)
        return _build_symbol_index_result(lhs, rhs, op_symbol, ctx, location or expr.location)
    if isinstance(expr, int):
        return _get_symbol_index_constant(expr, ctx, location, const_cache)
    if isinstance(expr, str):
        return _lower_symbolic_index_text(expr, ctx, location, const_cache)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    if isinstance(expr, ConstAST):
        if isinstance(expr.value, (int, str)):
            return _resolve_static_index_expr(expr, location=expr.location)
        raise _LoweringError("Index must be int or str", location=expr.location)
    if isinstance(expr, ScalarArgAST):
        return expr.name
    if isinstance(expr, VarAST):
        loop_vars = _get_loop_vars(ctx)
        if expr.name in loop_vars:
            return loop_vars[expr.name]
        raise _LoweringError("Unknown loop variable", location=expr.location)
    if isinstance(expr, BinaryExprAST):
        lhs = _resolve_index_expr(expr.lhs, ctx)
        rhs = _resolve_index_expr(expr.rhs, ctx)
        value = _apply_symbolic_index_binary_op(lhs, rhs, expr.op, expr.location)
        if isinstance(value, SymbolDim):
            normalized = value.get_value()
            if not isinstance(normalized, (int, str)):
                raise _LoweringError("Unsupported index expression", location=expr.location)
            return normalized
        return value
    if isinstance(expr, (int, str)):
        return _resolve_static_index_expr(expr, location=getattr(expr, "location", None))
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持常量、标量参数与循环变量引用。
    - 不支持的表达式维持统一的 loop bound 诊断。

    使用示例:
    - _lower_loop_bound(ConstAST(8), ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    if isinstance(expr, ConstAST):
        if isinstance(expr.value, int):
            return _const_symbol_int(expr.value, ctx, expr.location)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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


def _apply_symbolic_index_binary_op(
    lhs: int | str | SymbolDim,
    rhs: int | str | SymbolDim,
    op: str,
    location: SourceLocation | None,
) -> int | SymbolDim:
    """执行索引表达式的静态算术。"""

    lhs_value: int | SymbolDim
    rhs_value: int | SymbolDim
    if isinstance(lhs, SymbolDim):
        lhs_value = lhs
    elif isinstance(lhs, str):
        lhs_value = _eval_symbolic_dim_expr(lhs, location)
    else:
        lhs_value = lhs
    if isinstance(rhs, SymbolDim):
        rhs_value = rhs
    elif isinstance(rhs, str):
        rhs_value = _eval_symbolic_dim_expr(rhs, location)
    else:
        rhs_value = rhs

    if op == "add":
        return lhs_value + rhs_value
    if op == "sub":
        return lhs_value - rhs_value
    if op == "mul":
        return lhs_value * rhs_value
    if op == "div":
        if isinstance(lhs_value, int) and isinstance(rhs_value, int):
            if rhs_value == 0 or lhs_value % rhs_value != 0:
                raise _LoweringError("Unsupported index expression", location=location)
            return lhs_value // rhs_value
        if isinstance(lhs_value, int):
            lhs_value = SymbolDim(lhs_value)
        return lhs_value / rhs_value
    if op == "floordiv":
        if isinstance(lhs_value, int) and isinstance(rhs_value, int):
            if rhs_value == 0:
                raise _LoweringError("Unsupported index expression", location=location)
            return lhs_value // rhs_value
        if isinstance(lhs_value, int):
            lhs_value = SymbolDim(lhs_value)
        return lhs_value // rhs_value
    raise _LoweringError("Unsupported index expression", location=location)


def _resolve_symbolic_index_value(
    expr: object,
    *,
    location: SourceLocation | None = None,
    runtime_values: dict[str, object] | None = None,
) -> int | SymbolDim:
    """解析索引表达式为静态 `int|SymbolDim`。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 `ConstAST`、`ScalarArgAST`、`VarAST`、`BinaryExprAST` 以及直接的 `int|str`。
    - 当 `runtime_values` 提供 `int|SymbolDim` 时，优先使用运行时标量值参与 helper 参数与 symbol shape 计算。
    - 对纯符号表达式返回 `SymbolDim`，供 facade、helper 参数校验与类型推导统一复用。

    使用示例:
    - value = _resolve_symbolic_index_value(expr.axis, location=expr.location, runtime_values=runtime_values)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

    if isinstance(expr, ConstAST):
        if isinstance(expr.value, int):
            return expr.value
        if isinstance(expr.value, str):
            return _eval_symbolic_dim_expr(expr.value, expr.location)
        raise _LoweringError("Index must be int or str", location=expr.location)
    if isinstance(expr, ScalarArgAST):
        if runtime_values is not None and expr.name in runtime_values:
            runtime_value = runtime_values[expr.name]
            if isinstance(runtime_value, (int, SymbolDim)):
                return runtime_value
        return SymbolDim(expr.name)
    if isinstance(expr, VarAST):
        if runtime_values is not None and expr.name in runtime_values:
            runtime_value = runtime_values[expr.name]
            if isinstance(runtime_value, (int, SymbolDim)):
                return runtime_value
        return SymbolDim(expr.name)
    if isinstance(expr, BinaryExprAST):
        lhs = _resolve_symbolic_index_value(expr.lhs, location=expr.location, runtime_values=runtime_values)
        rhs = _resolve_symbolic_index_value(expr.rhs, location=expr.location, runtime_values=runtime_values)
        return _apply_symbolic_index_binary_op(lhs, rhs, expr.op, expr.location)
    if isinstance(expr, int):
        return expr
    if isinstance(expr, str):
        return _eval_symbolic_dim_expr(expr, location)
    raise _LoweringError("Unsupported index expression", location=location or getattr(expr, "location", None))


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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    value = _resolve_symbolic_index_value(expr, location=location, runtime_values=runtime_values)
    if isinstance(value, SymbolDim):
        normalized = value.get_value()
        if not isinstance(normalized, (int, str)):
            raise _LoweringError("Unsupported index expression", location=location or getattr(expr, "location", None))
        return normalized
    return value


def _resolve_helper_index_param_value(
    helper_name: str,
    param_name: str,
    value: object,
    location: SourceLocation | None,
    runtime_values: dict[str, object] | None = None,
) -> int | str:
    """解析 helper 的整数/符号参数为静态值表达式。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一复用 `int` 与符号索引表达式解析逻辑。
    - 对非法参数统一收敛到 `helper param must be int or symbol` 诊断。

    使用示例:
    - _resolve_helper_index_param_value("img2col1d", "kw", ScalarArgAST("kw"), location=None, runtime_values={"kw": SymbolDim("KW")})

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    try:
        return _resolve_static_index_expr(
            value,
            location=getattr(value, "location", None) or location,
            runtime_values=runtime_values,
        )
    except _LoweringError as exc:
        raise _LoweringError(
            f"{helper_name} {param_name} must be int or symbol",
            location=getattr(value, "location", None) or location,
        ) from exc


def _helper_index_value_to_symbolic(
    helper_name: str,
    param_name: str,
    value: int | str | SymbolDim,
    location: SourceLocation | None,
) -> int | SymbolDim:
    """将 helper 参数值规整为 `int|SymbolDim`。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - `int` 直接返回。
    - 符号字符串按 `SymbolDim` 语义解析，便于 shape 公式统一计算。

    使用示例:
    - _helper_index_value_to_symbolic("conv", "ph", "PH", location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    if isinstance(value, int):
        return value
    if isinstance(value, SymbolDim):
        return value
    if isinstance(value, str):
        return _eval_symbolic_dim_expr(value, location)
    raise _LoweringError(f"{helper_name} {param_name} must be int or symbol", location=location)


def _resolve_runtime_scalar_value(
    expr: object,
    inferred_type: Attribute | None,
    runtime_values: dict[str, object] | None = None,
) -> object | None:
    """解析算术/激活 helper 在类型推导阶段使用的标量值。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 优先解析 `ConstAST` 与 `runtime_values` 中可直接使用的标量值。
    - 对符号输入统一返回 `SymbolDim`，供 mixed binary/helper 类型推导复用。
    - 在仅有 `inferred_type` 时提供整数/浮点默认值，避免推导阶段出现空值分支。

    使用示例:
    - _resolve_runtime_scalar_value(ConstAST(1), i32, runtime_values=None)
    - _resolve_runtime_scalar_value(ScalarArgAST("alpha"), f32, runtime_values={"alpha": 0.125})

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    if isinstance(expr, ConstAST) and isinstance(expr.value, (int, float, bool)):
        return expr.value
    if isinstance(expr, ScalarArgAST):
        if runtime_values is not None and expr.name in runtime_values:
            return runtime_values[expr.name]
        if expr.is_symbolic:
            return SymbolDim(expr.name)
    if isinstance(expr, VarAST) and isinstance(inferred_type, SymbolValueType):
        return SymbolDim(inferred_type.expr.expr.data)
    if isinstance(inferred_type, SymbolValueType):
        return SymbolDim(inferred_type.expr.expr.data)
    if isinstance(inferred_type, IntegerType):
        return 0
    if isinstance(inferred_type, (Float16Type, BFloat16Type, Float32Type, Float64Type)):
        return 0.0
    return None


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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    if isinstance(value, (list, tuple)):
        entries = list(value)
    else:
        entries = [value]
    const_cache: dict[int, SSAValue] = {}
    for entry in entries:
        _preload_symbolic_index_constants(entry, ctx, getattr(entry, "location", None) or location, const_cache)
    return [
        _resolve_index_operand(entry, ctx, getattr(entry, "location", None) or location, const_cache) for entry in entries
    ]


def _symbolic_index_sequence(
    value: object,
    *,
    location: SourceLocation | None = None,
    runtime_values: dict[str, object] | None = None,
) -> list[int | SymbolDim]:
    """将索引参数规整为 `int|SymbolDim` 序列。"""

    entries = list(value) if isinstance(value, (list, tuple)) else [value]
    return [
        _resolve_symbolic_index_value(entry, location=getattr(entry, "location", None) or location, runtime_values=runtime_values)
        for entry in entries
    ]


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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    total_static = 1
    symbol_parts: list[str] = []
    for dim in shape:
        if isinstance(dim, IntAttr):
            total_static *= dim.data
            continue
        if isinstance(dim, StringAttr):
            if dim.data == "?":
                return StringAttr("?")
            symbol_parts.append(dim.data)
            continue
        return StringAttr("?")
    if not symbol_parts:
        return IntAttr(total_static)
    expr_parts: list[str] = []
    if total_static != 1:
        expr_parts.append(str(total_static))
    for part in symbol_parts:
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", part):
            expr_parts.append(part)
            continue
        expr_parts.append(f"({part})")
    if not expr_parts:
        return IntAttr(1)
    if len(expr_parts) == 1:
        return StringAttr(expr_parts[0])
    return StringAttr("*".join(expr_parts))


def _shape_attr_to_symbol_operand(
    attr: Attribute,
    ctx: EmitContext,
    *,
    location: SourceLocation | None = None,
) -> SSAValue:
    """将 shape 条目转换为 `!symbol.int` SSA operand。

    创建者: 朽木露琪亚
    最后一次更改: jcc你莫辜负

    功能说明:
    - `IntAttr` 直接物化为 `!symbol.int<"n">` 常量。
    - `StringAttr` 复用索引解析路径，并在需要时转换为 `!symbol.int<"expr">`。
    - 供 conv helper 分解生成 `dma.reshape` 的 shape operand 复用。

    使用示例:
    - _shape_attr_to_symbol_operand(IntAttr(4), ctx, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    if isinstance(attr, IntAttr):
        return _const_symbol_int(attr.data, ctx, location)
    if isinstance(attr, StringAttr):
        if attr.data == "?":
            raise _LoweringError("Unsupported layout attribute", location=location)
        value = _resolve_index_operand(attr.data, ctx, location)
        if isinstance(value.type, SymbolValueType):
            return value
        return _cast_to_symbol_int(value, ctx, attr.data, location)
    raise _LoweringError("Unsupported layout attribute", location=location)


def _shape_attr_to_helper_index_operand(
    attr: Attribute,
    ctx: EmitContext,
    *,
    location: SourceLocation | None = None,
) -> SSAValue:
    """将 shape 条目转换为 helper 参数使用的整数/symbol operand。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 静态整型 shape 维保持为 `i32` 常量，兼容当前 helper 静态路径。
    - 符号 shape 维转换为 `!symbol.int`，供 img2col/conv 符号参数路径复用。

    使用示例:
    - _shape_attr_to_helper_index_operand(IntAttr(3), ctx, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    if isinstance(attr, IntAttr):
        return _const_i32(attr.data, ctx, location)
    if isinstance(attr, StringAttr):
        return _shape_attr_to_symbol_operand(attr, ctx, location=location)
    raise _LoweringError("Unsupported layout attribute", location=location)


def _lower_helper_index_operand(
    expr: object,
    ctx: EmitContext,
    *,
    location: SourceLocation | None = None,
) -> SSAValue:
    """将 helper 参数表达式转换为 `i32` 或 `!symbol.int` operand。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 保持静态字面量为 `i32` 常量。
    - 保持符号与符号表达式为 `!symbol.int`。
    - 对整型 SSA 输入直接复用，避免 helper 参数被无意义地转成 `index`。

    使用示例:
    - _lower_helper_index_operand(ScalarArgAST("kw"), ctx, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    if isinstance(expr, ConstAST):
        if isinstance(expr.value, int):
            return _const_i32(expr.value, ctx, expr.location)
        return _resolve_index_operand(expr, ctx, expr.location)
    if isinstance(expr, int):
        return _const_i32(expr, ctx, location)
    if isinstance(expr, ScalarArgAST):
        value = _lookup_symbol(expr, ctx)
        if not isinstance(value, SSAValue):
            raise _LoweringError("Index operand must be SSA value", location=expr.location)
        if isinstance(value.type, (IntegerType, SymbolValueType)):
            return value
        if isinstance(value.type, IndexType):
            cast = arith.IndexCastOp(value, IntegerType(32))
            ctx.builder.add_op(cast)
            return cast.result
        raise _LoweringError("Index operand must be integer or symbol", location=expr.location)
    if isinstance(expr, VarAST):
        value = _lookup_symbol(expr, ctx)
        if not isinstance(value, SSAValue):
            raise _LoweringError("Index operand must be SSA value", location=expr.location)
        if isinstance(value.type, (IntegerType, SymbolValueType)):
            return value
        if isinstance(value.type, IndexType):
            cast = arith.IndexCastOp(value, IntegerType(32))
            ctx.builder.add_op(cast)
            return cast.result
        return _resolve_index_operand(expr, ctx, expr.location)
    return _resolve_index_operand(expr, ctx, location)


def _build_symbol_product_operand(
    values: Sequence[SSAValue],
    ctx: EmitContext,
    *,
    location: SourceLocation | None = None,
) -> SSAValue:
    """将多个 `!symbol.int` 值串成乘法表达式。

    创建者: 朽木露琪亚
    最后一次更改: jcc你莫辜负

    功能说明:
    - 复用 `symbol.mul` 组合多个符号维度。
    - 用于 conv helper 中 `B * OH * OW` 这类 image_dim 形状构造。

    使用示例:
    - _build_symbol_product_operand([lhs, rhs], ctx, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    if not values:
        raise _LoweringError("Symbol product requires at least one operand", location=location)
    current = values[0]
    for value in values[1:]:
        result_type = SymbolValueType.from_expr(
            build_public_symbol_expr(f"({current.type.expr.expr.data})", f"({value.type.expr.expr.data})", "*")
        )
        op = SymbolMulOp(current, value, result_type)
        ctx.builder.add_op(op)
        current = op.result
    return current


def _build_img2col2d_output_dim_operands(
    source: SSAValue,
    ctx: EmitContext,
) -> tuple[SSAValue, SSAValue, SSAValue]:
    """读取 `nn.img2col2d` 结果中的 `N/OH/OW` 维度 operand。

    创建者: 朽木露琪亚
    最后一次更改: jcc你莫辜负

    功能说明:
    - 约定 `img2col2d` 结果布局为 `[N, C, KH, KW, OH, OW]`。
    - 输出 `N`、`OH`、`OW` 对应的 `!symbol.int` 值，供后续 reshape 复用。

    使用示例:
    - batch_dim, out_h_dim, out_w_dim = _build_img2col2d_output_dim_operands(img2col.result, ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    batch_op = SymbolGetDimOp(source, IntAttr(0))
    out_h_op = SymbolGetDimOp(source, IntAttr(4))
    out_w_op = SymbolGetDimOp(source, IntAttr(5))
    ctx.builder.add_op(batch_op)
    ctx.builder.add_op(out_h_op)
    ctx.builder.add_op(out_w_op)
    return batch_op.result, out_h_op.result, out_w_op.result


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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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


def _infer_matmul_memory_type(
    lhs_type: NnMemoryType,
    rhs_type: NnMemoryType,
    memoryspace: MemorySpace | None,
    location: SourceLocation | None,
) -> NnMemoryType:
    """推导 `nn.matmul` 的目标 nn.memory 类型。

    创建者: 朽木露琪亚
    最后一次更改: jcc你莫辜负

    功能说明:
    - 仅接受 rank-2 `nn.memory` x `nn.memory`。
    - 结果 shape 固定为 `[lhs.M, rhs.N]`，stride 为默认连续布局。
    - 要求 lhs/rhs element_type 一致，不接受 mixed dtype。

    使用示例:
    - _infer_matmul_memory_type(lhs_type, rhs_type, None, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    if lhs_type.space != rhs_type.space:
        raise _LoweringError("nn.matmul operands must use the same space", location=location)
    lhs_shape = list(lhs_type.shape.data)
    rhs_shape = list(rhs_type.shape.data)
    if len(lhs_shape) != 2 or len(rhs_shape) != 2:
        raise _LoweringError("matmul operands must be rank-2 nn.memory", location=location)
    if not _dims_equal(lhs_shape[1], rhs_shape[0]):
        raise _LoweringError("matmul contracting dimension mismatch", location=location)
    if lhs_type.element_type != rhs_type.element_type:
        raise _LoweringError("matmul element_type must match", location=location)
    target_space = _memory_space_from_ast(memoryspace, lhs_type.space)
    target_element_type = lhs_type.element_type
    out_shape = [lhs_shape[0], rhs_shape[1]]
    out_stride = _build_default_stride_attrs(out_shape)
    return _memory_type_from_parts(out_shape, out_stride, target_element_type, target_space)


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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    shape = memory.shape.get_values()
    stride_values = memory.stride.get_values() if memory.stride is not None else _build_stride(shape)
    shape_attr = ArrayAttr([_dim_to_attr(dim) for dim in shape])
    stride_attr = ArrayAttr([_dim_to_attr(dim) for dim in stride_values])
    element_type = _dtype_to_xdsl(memory.dtype, location=location)
    space_name = _MEMORY_SPACE_MAP.get(memory.space, "global")
    space = NnMemorySpaceAttr.from_name(space_name)
    return NnMemoryType(shape_attr, stride_attr, element_type, space)


def _nn_memory_type_to_memory(
    memory_type: NnMemoryType,
    location: SourceLocation | None = None,
) -> Memory:
    """将 `NnMemoryType` 转换为运行时 `Memory` 描述。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 读取 `nn.memory` 的 shape/stride/element_type/space 并规整为 `Memory` 描述。
    - 拒绝包含未知维度的 shape/stride，避免在 broadcast 类路径中生成不完整的空间信息。

    使用示例:
    - _nn_memory_type_to_memory(memory_type, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    shape: list[SymbolDim] = []
    for dim_attr in memory_type.shape.data:
        dim_symbol = _shape_attr_to_symbol_dim(dim_attr, location)
        if dim_symbol is None:
            raise _LoweringError("nn.memory shape contains unknown dimension", location=location)
        shape.append(dim_symbol)
    stride: list[SymbolDim] = []
    for dim_attr in memory_type.stride.data:
        dim_symbol = _shape_attr_to_symbol_dim(dim_attr, location)
        if dim_symbol is None:
            raise _LoweringError("nn.memory stride contains unknown dimension", location=location)
        stride.append(dim_symbol)
    dtype = _xdsl_to_dtype(memory_type.element_type, location)
    space_name = memory_type.space.space.data
    space_map = {
        "global": MemorySpace.GM,
        "shared": MemorySpace.SM,
        "local": MemorySpace.LM,
        "tsm": MemorySpace.TSM,
        "tlm1": MemorySpace.TLM1,
        "tlm2": MemorySpace.TLM2,
        "tlm3": MemorySpace.TLM3,
    }
    space = space_map.get(space_name)
    if space is None:
        raise _LoweringError("Unsupported nn.memory space", location=location)
    return Memory(shape, dtype, space=space, stride=stride)


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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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


def _resolve_tensor_axis_index(
    axis_expr: object,
    location: SourceLocation | None = None,
    runtime_values: dict[str, object] | None = None,
) -> int:
    """解析 `tensor.get_shape/get_stride()[axis]` 的静态轴号。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 复用静态索引解析逻辑收敛 `shape/stride` 访问的轴号。
    - 拒绝非静态整数、负数轴号，保证查询 op 只接收合法静态轴。

    使用示例:
    - _resolve_tensor_axis_index(ConstAST(1), location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    axis = _resolve_static_index_expr(axis_expr, location, runtime_values)
    if not isinstance(axis, int):
        raise _LoweringError("Tensor axis must be static int", location=location)
    if axis < 0:
        raise _LoweringError("Tensor axis must be non-negative", location=location)
    return axis


def _infer_tensor_axis_access_type(
    expr: TensorAxisAccessAST,
    type_map: dict[int, object],
    runtime_values: dict[str, object] | None = None,
) -> SymbolValueType:
    """推导 `tensor.get_shape/get_stride()[axis]` 的 symbol 返回类型。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 从 `TensorAST` 对应的 `nn.memory` 类型中读取指定轴的 `shape/stride` 条目。
    - 将静态整数或符号条目映射为 `!symbol.int`，并统一拒绝越界轴号与匿名动态条目。

    使用示例:
    - _infer_tensor_axis_access_type(expr, type_map)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    tensor_type = type_map.get(_expr_key(expr.tensor))
    if not isinstance(tensor_type, NnMemoryType):
        raise _LoweringError("Tensor axis access source must be nn.memory", location=expr.location)
    axis = _resolve_tensor_axis_index(expr.axis, expr.location, runtime_values)
    entries = tensor_type.shape.data if expr.kind == "shape" else tensor_type.stride.data
    if axis >= len(entries):
        raise _LoweringError("Tensor axis out of range", location=expr.location)
    entry = entries[axis]
    if isinstance(entry, IntAttr):
        return SymbolValueType.from_expr(str(entry.data))
    if isinstance(entry, StringAttr) and entry.data != "?":
        return SymbolValueType.from_expr(entry.data)
    raise _LoweringError("Tensor axis access does not support unknown entry '?'", location=expr.location)


def _infer_img2col_input_format(input_type: NnMemoryType) -> Farmat:
    """推导 img2col helper 输入的布局语义。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 对 rank-3 输入按 `[N, W, C]` 与 `[N, C, W]` 的现有公开合同做最小启发式判断。
    - 对 rank-4 输入按 `[N, H, W, C]` 与 `[N, C, H, W]` 做同样判断。
    - 其余情况默认回落 `Farmat.Norm`，保持现有 emit 兼容行为。

    使用示例:
    - layout = _infer_img2col_input_format(input_type)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

    shape = list(input_type.shape.data)
    if len(shape) == 3:
        if isinstance(shape[1], StringAttr) and not isinstance(shape[2], StringAttr):
            return Farmat.CLast
        return Farmat.Norm
    if len(shape) == 4:
        if isinstance(shape[3], IntAttr) and (isinstance(shape[1], StringAttr) or isinstance(shape[2], StringAttr)):
            return Farmat.CLast
        return Farmat.Norm
    return Farmat.Norm


def _nn_memory_type_to_memory_with_format(
    memory_type: NnMemoryType,
    format_value: Farmat,
    location: SourceLocation | None = None,
) -> Memory:
    """将 `NnMemoryType` 转为显式包含 format 的 `Memory`。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 复用 `_nn_memory_type_to_memory(...)` 的 shape/stride/dtype/space 解析逻辑。
    - 在 DSL helper 类型推导阶段补上运行时 `Memory.format`，以便复用 operation API。

    使用示例:
    - memory = _nn_memory_type_to_memory_with_format(memory_type, Farmat.CLast)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

    memory = _nn_memory_type_to_memory(memory_type, location=location)
    return Memory(memory.shape, memory.dtype, space=memory.space, stride=memory.stride, format=format_value)


def _resolve_helper_index_param(
    *,
    op_name: str,
    param_name: str,
    value: object,
    location: SourceLocation | None,
    runtime_values: dict[str, object] | None,
    allow_zero: bool,
) -> int | SymbolDim:
    """解析 helper 参数为 `int|SymbolDim` 并校验取值范围。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 接受 `ConstAST`、`ScalarArgAST`、`VarAST`、`BinaryExprAST` 以及直接的 `int|str|SymbolDim`。
    - 对静态整数执行正值/非负约束，动态符号值保持原样下传给 operation API 与方言 verifier。

    使用示例:
    - kw = _resolve_helper_index_param(op_name="img2col1d", param_name="kw", value=kw_ast, location=None, runtime_values=None, allow_zero=False)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

    if isinstance(value, SymbolDim):
        resolved: int | SymbolDim = value
    else:
        resolved = _resolve_symbolic_index_value(value, location=location, runtime_values=runtime_values)
    if isinstance(resolved, int):
        if allow_zero:
            if resolved < 0:
                raise _LoweringError(f"{op_name} {param_name} must be non-negative", location=location)
        elif resolved <= 0:
            raise _LoweringError(f"{op_name} {param_name} must be positive", location=location)
    return resolved


def _resolve_img2col_param_values(
    expr: Img2ColAST,
    params: dict[str, object],
    runtime_values: dict[str, object] | None,
) -> dict[str, int | SymbolDim]:
    """解析 img2col helper 参数为 `int|SymbolDim` 映射。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 保留 `img2col1d/img2col2d` 的默认值与参数顺序合同。
    - 支持 `kw/kh/sh/sw/dh/dw/ph/pw/pl/pr` 由 `SymbolDim` 或符号表达式驱动。

    使用示例:
    - params = _resolve_img2col_param_values(expr, raw_params, runtime_values=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

    resolved: dict[str, int | SymbolDim] = {}
    for name, value in params.items():
        resolved[name] = _resolve_helper_index_param(
            op_name=expr.kind,
            param_name=name,
            value=value,
            location=getattr(value, "location", None) or expr.location,
            runtime_values=runtime_values,
            allow_zero=name in {"ph", "pw", "pl", "pr"},
        )
    return resolved


def _resolve_conv_param_values(
    expr: ConvAST,
    params: dict[str, object],
    runtime_values: dict[str, object] | None,
) -> dict[str, int | SymbolDim]:
    """解析 conv helper 参数为 `int|SymbolDim` 映射。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 `sh/sw/dh/dw/ph/pw/pl/pr` 接受 `int|SymbolDim`。
    - 对静态正值/非负约束执行最小前置校验，动态符号值继续交给后续合同处理。

    使用示例:
    - params = _resolve_conv_param_values(expr, raw_params, runtime_values=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/emit_mlir.py](kernel_gen/dsl/emit_mlir.py)
    """

    resolved: dict[str, int | SymbolDim] = {}
    for name, value in params.items():
        resolved[name] = _resolve_helper_index_param(
            op_name="conv",
            param_name=name,
            value=value,
            location=getattr(value, "location", None) or expr.location,
            runtime_values=runtime_values,
            allow_zero=name in {"ph", "pw", "pl", "pr"},
        )
    return resolved


def _parse_img2col_helper(expr: Img2ColAST) -> tuple[object, dict[str, object]]:
    """解析 img2col helper 调用参数。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一解析 `img2col1d/img2col2d` 的位置参数与关键字参数。
    - 应用默认值并保留 helper 参数 AST/标量原值，供 emit/type 推导分别解析。

    使用示例:
    - input_expr, param_exprs, attrs = _parse_img2col_helper(img2col_ast)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    return input_expr, params


def _parse_conv_helper(expr: ConvAST) -> tuple[object, object, dict[str, object]]:
    """解析 conv helper 调用参数。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 统一解析 `conv(value, weight, sh=..., sw=..., ...)` 的参数。
    - 当前仅承接不带 bias 的前端分解路径，并保留 helper 参数 AST/标量原值供后续解析。

    使用示例:
    - value_expr, weight_expr, param_exprs, params = _parse_conv_helper(conv_ast)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    params: dict[str, object] = dict(expr.kwargs)
    resolved: dict[str, object] = {}
    for name, default_value in _CONV_PARAM_DEFAULTS.items():
        resolved[name] = params.pop(name, default_value)
    if params:
        unexpected = next(iter(params))
        raise _LoweringError(f"conv got unexpected keyword '{unexpected}'", location=expr.location)
    return expr.value, expr.weight, resolved


def _validate_conv_helper_params(params: dict[str, int | str], location: SourceLocation | None) -> None:
    """校验 conv helper 的静态参数约束。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 要求 `sh/sw/dh/dw` 为正整数。
    - 要求 `ph/pw/pl/pr` 为非负整数。
    - 失败时抛出 `VerifyException`，保持 expectation 依赖的显式失败口径。

    使用示例:
    - _validate_conv_helper_params({"sh": 1, "sw": 1, "dh": 1, "dw": 1, "ph": 0, "pw": 0, "pl": 0, "pr": 0}, None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    for name in ("sh", "sw", "dh", "dw"):
        value = _helper_index_value_to_symbolic("conv", name, params[name], location)
        normalized = value if isinstance(value, int) else value.get_value()
        if isinstance(normalized, int) and normalized <= 0:
            raise VerifyException(f"{name} must be positive")
    for name in ("ph", "pw", "pl", "pr"):
        value = _helper_index_value_to_symbolic("conv", name, params[name], location)
        normalized = value if isinstance(value, int) else value.get_value()
        if isinstance(normalized, int) and normalized < 0:
            raise VerifyException(f"{name} must be non-negative")


def _static_kernel_dim(attr: Attribute, name: str, location: SourceLocation | None) -> int:
    """读取 conv 权重中的静态 kernel 维度。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 当前前端分解仅支持静态 `kh/kw`。
    - 非 `IntAttr` 时在 emit/type 推导入口报错，避免构造不合法的 `nn.img2col2d` 属性。

    使用示例:
    - kh = _static_kernel_dim(IntAttr(3), "kh", None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    if isinstance(attr, IntAttr):
        if attr.data <= 0:
            raise VerifyException(f"{name} must be positive")
        return attr.data
    if isinstance(attr, StringAttr):
        symbolic = _eval_symbolic_dim_expr(attr.data, location)
        normalized = symbolic.get_value()
        if isinstance(normalized, int) and normalized <= 0:
            raise VerifyException(f"{name} must be positive")
        return symbolic
    raise _LoweringError(f"conv {name} must be int or symbol", location=location)


def _conv_out_dim_value(
    dim: Attribute,
    *,
    axis_name: str,
    kernel: int | str,
    stride: int | str,
    dilation: int | str,
    pad_before: int | str,
    pad_after: int | str,
    location: SourceLocation | None,
) -> int | str:
    """计算 conv 输出维度表达式。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 静态维度返回整数结果，并在结果 `<= 0` 时抛出 `VerifyException`。
    - 符号维度返回保持对外字符串语义的表达式。

    使用示例:
    - _conv_out_dim_value(IntAttr(5), axis_name="height", kernel=3, stride=1, dilation=1, pad_before=1, pad_after=1, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    kernel_value = _helper_index_value_to_symbolic("conv", f"{axis_name}-kernel", kernel, location)
    stride_value = _helper_index_value_to_symbolic("conv", f"{axis_name}-stride", stride, location)
    dilation_value = _helper_index_value_to_symbolic("conv", f"{axis_name}-dilation", dilation, location)
    pad_before_value = _helper_index_value_to_symbolic("conv", f"{axis_name}-pad-before", pad_before, location)
    pad_after_value = _helper_index_value_to_symbolic("conv", f"{axis_name}-pad-after", pad_after, location)
    if isinstance(dim, IntAttr):
        dim_value: int | SymbolDim = dim.data
    elif isinstance(dim, StringAttr):
        dim_value = SymbolDim(dim.data)
    else:
        raise _LoweringError("conv dim must be int or symbol", location=location)
    if all(
        isinstance(value, int)
        for value in (dim_value, kernel_value, stride_value, dilation_value, pad_before_value, pad_after_value)
    ):
        normalized = (
            (dim_value + pad_before_value + pad_after_value - dilation_value * (kernel_value - 1) - 1) // stride_value + 1
        )
        if normalized <= 0:
            raise VerifyException(f"output {axis_name} must be positive")
        return normalized
    expr = (dim_value + pad_before_value + pad_after_value - dilation_value * (kernel_value - 1) - 1) / stride_value + 1
    normalized = expr if isinstance(expr, int) else expr.get_value()
    if isinstance(normalized, int) and normalized <= 0:
        raise VerifyException(f"output {axis_name} must be positive")
    return normalized


def _infer_conv_memory_type(
    expr: ConvAST,
    value_type: NnMemoryType,
    weight_type: NnMemoryType,
    runtime_values: dict[str, object] | None = None,
) -> NnMemoryType:
    """推导 conv helper 的结果类型。

    创建者: 朽木露琪亚
    最后一次更改: 小李飞刀

    功能说明:
    - 仅接受 `rank-4 value` 与 `rank-4 weight`。
    - 复用前端分解所需的 `sh/sw/dh/dw/ph/pw/pl/pr` 参数，并保持输出 shape/stride 与公开 `conv` 合同一致。

    使用示例:
    - result_type = _infer_conv_memory_type(expr, value_type, weight_type)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    value_memory = _nn_memory_type_to_memory(value_type, location=expr.location)
    weight_memory = _nn_memory_type_to_memory(weight_type, location=expr.location)
    _, _, raw_params = _parse_conv_helper(expr)
    params = _resolve_conv_param_values(expr, raw_params, runtime_values)
    result_memory = _KG_OPERATION_NN.conv(
        value_memory,
        weight_memory,
        sh=params["sh"],
        sw=params["sw"],
        dh=params["dh"],
        dw=params["dw"],
        ph=params["ph"],
        pw=params["pw"],
        pl=params["pl"],
        pr=params["pr"],
    )
    return _memory_to_nn_type(result_memory, location=expr.location)


def _img2col_out_dim_value(
    dim: Attribute,
    k: int | str,
    s: int | str,
    d: int | str,
    p1: int | str,
    p2: int | str,
    location: SourceLocation | None,
) -> int | str:
    """计算 img2col 输出维度表达式。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 静态维度返回整数结果。
    - 符号维度返回保持注解语义的字符串表达式。

    使用示例:
    - _img2col_out_dim_value(IntAttr(8), 3, 1, 1, 1, 1, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    kernel_value = _helper_index_value_to_symbolic("img2col", "k", k, location)
    stride_value = _helper_index_value_to_symbolic("img2col", "s", s, location)
    dilation_value = _helper_index_value_to_symbolic("img2col", "d", d, location)
    pad_left_value = _helper_index_value_to_symbolic("img2col", "p1", p1, location)
    pad_right_value = _helper_index_value_to_symbolic("img2col", "p2", p2, location)
    if isinstance(dim, IntAttr):
        dim_value: int | SymbolDim = dim.data
    elif isinstance(dim, StringAttr):
        dim_value = SymbolDim(dim.data)
    else:
        raise _LoweringError("img2col dim must be int or symbol", location=location)
    if all(
        isinstance(value, int)
        for value in (dim_value, kernel_value, stride_value, dilation_value, pad_left_value, pad_right_value)
    ):
        return (dim_value + pad_left_value + pad_right_value - dilation_value * (kernel_value - 1) - 1) // stride_value + 1
    expr = (dim_value + pad_left_value + pad_right_value - dilation_value * (kernel_value - 1) - 1) / stride_value + 1
    return expr if isinstance(expr, int) else expr.get_value()


def _infer_img2col_output_shape_attrs(
    expr: Img2ColAST,
    input_type: NnMemoryType,
    params: dict[str, int | SymbolDim],
) -> list[Attribute]:
    """推导 img2col 输出 shape 属性列表。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 支持 img2col1d/img2col2d 的结构化输出维度合同。
    - 通过输入 shape 的符号分布粗略区分 NCHW/NWC、NCHW/NHWC。

    使用示例:
    - _infer_img2col_output_shape_attrs(expr, input_type, params)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    input_memory = _nn_memory_type_to_memory_with_format(
        input_type,
        _infer_img2col_input_format(input_type),
        location=expr.location,
    )
    if expr.kind == "img2col1d":
        result_memory = _KG_OPERATION_NN.img2col1d(
            input_memory,
            kw=params["kw"],
            sw=params["sw"],
            dw=params["dw"],
            pl=params["pl"],
            pr=params["pr"],
        )
    elif expr.kind == "img2col2d":
        result_memory = _KG_OPERATION_NN.img2col2d(
            input_memory,
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
        )
    else:
        raise _LoweringError("Unsupported img2col helper", location=expr.location)
    result_type = _memory_to_nn_type(result_memory, location=expr.location)
    return list(result_type.shape.data)


def _parse_reduce_axis_expr(axis_expr: object | None, location: SourceLocation | None) -> list[int] | None:
    """解析 reduce 的 axis 表达式为轴列表。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 允许 int / ConstAST[int] / list/tuple 的轴值解析。
    - 未提供 axis 时返回 None，表示“reduce all axes”。

    使用示例:
    - _parse_reduce_axis_expr(ConstAST(1), location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    if axis_expr is None:
        return None
    if isinstance(axis_expr, ConstAST):
        if isinstance(axis_expr.value, int):
            return [axis_expr.value]
        raise _LoweringError("reduce axis must be int", location=axis_expr.location)
    if isinstance(axis_expr, int):
        return [axis_expr]
    if isinstance(axis_expr, (list, tuple)):
        axes: list[int] = []
        for entry in axis_expr:
            if isinstance(entry, ConstAST) and isinstance(entry.value, int):
                axes.append(entry.value)
                continue
            if isinstance(entry, int):
                axes.append(entry)
                continue
            raise _LoweringError("reduce axis must be int", location=getattr(entry, "location", None) or location)
        return axes
    raise _LoweringError("reduce axis must be int or list of int", location=location)


def _parse_softmax_axis_expr(axis_expr: object | None, rank: int, location: SourceLocation | None) -> int:
    """解析 softmax axis 表达式为整数。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 int / ConstAST[int] 的 axis。
    - 未提供 axis 时默认使用末轴，并统一规整为非负轴。
    - 不提前拒绝越界正轴，保留给 `NnSoftmaxOp.verify()` 产出方言级诊断。

    使用示例:
    - _parse_softmax_axis_expr(ConstAST(1), rank=2, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    if axis_expr is None:
        value = -1
    else:
        value = axis_expr
        if isinstance(axis_expr, ConstAST):
            value = axis_expr.value
            location = axis_expr.location or location
    if isinstance(value, bool) or not isinstance(value, int):
        raise _LoweringError("softmax axis must be int", location=location)
    normalized = value + rank if value < 0 else value
    return normalized if normalized >= 0 else value


def _parse_transpose_perm_expr(perm_expr: object | None, location: SourceLocation | None) -> list[int]:
    """解析 transpose perm 表达式为轴列表。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 list/tuple/int/ConstAST[int] 的 perm 解析。
    - 仅做基础类型校验，排列合法性由后续 verifier 处理。

    使用示例:
    - _parse_transpose_perm_expr([ConstAST(1), ConstAST(0)], location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    if perm_expr is None:
        raise _LoweringError("transpose perm must be list of int", location=location)
    if isinstance(perm_expr, ConstAST):
        if isinstance(perm_expr.value, int):
            return [perm_expr.value]
        raise _LoweringError("transpose perm entries must be int", location=perm_expr.location or location)
    if isinstance(perm_expr, int):
        return [perm_expr]
    if isinstance(perm_expr, (list, tuple)):
        perm_values: list[int] = []
        for entry in perm_expr:
            if isinstance(entry, ConstAST) and isinstance(entry.value, int):
                perm_values.append(entry.value)
                continue
            if isinstance(entry, int):
                perm_values.append(entry)
                continue
            raise _LoweringError(
                "transpose perm entries must be int",
                location=getattr(entry, "location", None) or location,
            )
        return perm_values
    raise _LoweringError("transpose perm must be list of int", location=location)


def _parse_reduce_keepdim_expr(
    keepdim_expr: object | None,
    location: SourceLocation | None,
) -> tuple[bool | int, bool]:
    """解析 reduce keepdim 表达式并返回值与合法性标记。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 支持 bool/int/ConstAST(bool|int) 的 keepdim 输入。
    - 返回 keepdim 值以及是否满足布尔语义（0/1/True/False）。

    使用示例:
    - _parse_reduce_keepdim_expr(ConstAST(True), location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    if keepdim_expr is None:
        return False, True
    value: object
    if isinstance(keepdim_expr, ConstAST):
        value = keepdim_expr.value
    else:
        value = keepdim_expr
    if isinstance(value, bool):
        return value, True
    if isinstance(value, int):
        return value, value in (0, 1)
    raise _LoweringError("reduce keepdim must be bool or int", location=location)


def _build_reduce_result_shape_attrs(
    input_shape: Sequence[Attribute],
    axes: set[int],
    keepdim: bool,
) -> list[Attribute]:
    """基于 axes/keepdim 推导 reduce 结果 shape。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - keepdim=true 时将归约轴替换为 1。
    - keepdim=false 时移除归约轴；若结果为空则返回 [1]。

    使用示例:
    - _build_reduce_result_shape_attrs([IntAttr(2), IntAttr(3)], {0}, keepdim=False)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    if keepdim:
        return [IntAttr(1) if index in axes else dim for index, dim in enumerate(input_shape)]
    reduced = [dim for index, dim in enumerate(input_shape) if index not in axes]
    if not reduced:
        return [IntAttr(1)]
    return reduced


def _infer_reduce_output_shape_attrs(expr: NnReduceAST, input_type: NnMemoryType) -> list[Attribute]:
    """推导 reduce_* 的输出 shape 属性列表。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - axes/keepdim 合法时按合同推导结果 shape。
    - axes/keepdim 非法时返回输入 shape 兜底，以便 verifier 报错。

    使用示例:
    - _infer_reduce_output_shape_attrs(expr, input_type)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    shape = list(input_type.shape.data)
    rank = len(shape)
    axes = _parse_reduce_axis_expr(expr.axis, expr.location)
    keepdim_value, keepdim_valid = _parse_reduce_keepdim_expr(expr.keepdim, expr.location)
    if axes is None:
        axes_list = list(range(rank))
    else:
        axes_list = axes

    axes_valid = bool(axes_list) and len(set(axes_list)) == len(axes_list)
    if axes_valid and any(axis < 0 or axis >= rank for axis in axes_list):
        axes_valid = False

    if not axes_valid or not keepdim_valid:
        return shape

    keepdim = keepdim_value if isinstance(keepdim_value, bool) else bool(keepdim_value)
    return _build_reduce_result_shape_attrs(shape, set(axes_list), keepdim)


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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
                ConvAST,
                Img2ColAST,
                FCAST,
                MatmulAST,
                NnBroadcastAST,
                NnBroadcastToAST,
                NnReduceAST,
                NnSoftmaxAST,
                NnTransposeAST,
                NnUnaryAST,
                DmaFreeAST,
                ForAST,
                ArchBarrierAST,
                ArchGetDynamicMemoryAST,
                ArchLaunchKernelAST,
                ArchQueryAST,
                PythonCalleeCallAST,
                SymbolToFloatAST,
                TensorAxisAccessAST,
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    return id(expr)


def _infer_expr_type(
    expr: object,
    type_map: dict[int, object],
    runtime_values: dict[str, object] | None = None,
    config: dict[str, object] | None = None,
) -> object:
    """推导表达式在 lowering 前的结果类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一处理常量、DMA、arch query、`symbol.to_float`、symbol 与 nn 二元表达式的类型推导。
    - 对 `nn.add` mixed memory+const/symbol 路径执行 promotion，并在纯 scalar/symbol 输入时给出显式诊断。

    使用示例:
    - _infer_expr_type(BinaryExprAST(op="add", lhs=lhs, rhs=rhs), type_map)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """

    expr_key = _expr_key(expr)
    if expr_key in type_map:
        return type_map[expr_key]
    if runtime_values is None and isinstance(config, dict):
        candidate_runtime_values = config.get("__runtime_values__")
        if isinstance(candidate_runtime_values, dict):
            runtime_values = candidate_runtime_values

    if isinstance(expr, PythonCalleeCallAST):
        registry_value: object = {}
        compiler_value: object = None
        if isinstance(config, dict):
            registry_value = config.get(_MLIR_GEN_CALLEE_REGISTRY_CONFIG_KEY, {})
            compiler_value = config.get(_MLIR_GEN_CALLEE_COMPILER_CONFIG_KEY)
        if not isinstance(registry_value, dict):
            raise _LoweringError("Python callee registry must be dict", location=expr.location)

        arg_types = [
            _infer_expr_type(arg, type_map, runtime_values=runtime_values, config=config) for arg in expr.args
        ]
        if compiler_value is not None:
            if not callable(compiler_value):
                raise _LoweringError("Python callee compiler must be callable", location=expr.location)
            compiler_value(expr.callee, arg_types, expr.location)

        callee_op = registry_value.get(expr.callee)
        if not isinstance(callee_op, func.FuncOp):
            raise _LoweringError("Python callee is missing from registry", location=expr.location)
        output_types = list(callee_op.function_type.outputs.data)
        if len(output_types) != 1:
            raise _LoweringError("Python callee must return exactly one value", location=expr.location)
        type_map[expr_key] = output_types[0]
        return output_types[0]

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
        source_memory = _nn_memory_type_to_memory(source_type, location=expr.location)
        offsets_value = _symbolic_index_sequence(expr.offset, location=expr.location, runtime_values=runtime_values)
        sizes_value = (
            [dim for dim in source_memory.shape]
            if expr.sizes is None
            else _symbolic_index_sequence(expr.sizes, location=expr.location, runtime_values=runtime_values)
        )
        strides_value = (
            None
            if expr.stride is None
            else _symbolic_index_sequence(expr.stride, location=expr.location, runtime_values=runtime_values)
        )
        target_space = source_memory.space if expr.space is None else expr.space
        result_memory = (
            _KG_OPERATION_DMA.slice(source_memory, offsets_value, sizes_value, strides_value, target_space)
            if expr.kind == "slice"
            else _KG_OPERATION_DMA.load(source_memory, offsets_value, sizes_value, strides_value, target_space)
        )
        result_type = _memory_to_nn_type(result_memory, location=expr.location)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, DmaAllocAST):
        shape_value = _symbolic_index_sequence(expr.shape, location=expr.location, runtime_values=runtime_values)
        stride_value = (
            None
            if expr.stride is None
            else _symbolic_index_sequence(expr.stride, location=expr.location, runtime_values=runtime_values)
        )
        result_memory = _KG_OPERATION_DMA.alloc(shape_value, expr.dtype, expr.space, stride=stride_value)
        shape_attr = _build_static_index_attrs_exact(expr.shape, location=expr.location, runtime_values=runtime_values)
        stride_attr = (
            _build_static_index_attrs_exact(expr.stride, location=expr.location, runtime_values=runtime_values)
            if expr.stride is not None
            else _build_default_stride_attrs(shape_attr)
        )
        default_stride = _build_default_stride_attrs(shape_attr)
        if stride_attr != default_stride:
            raise _LoweringError("dma.alloc only supports contiguous stride", location=expr.location)
        result_type = _memory_to_nn_type(result_memory, location=expr.location)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, DmaCopyAST):
        source_type = _infer_expr_type(expr.source, type_map, runtime_values=runtime_values)
        if not isinstance(source_type, NnMemoryType):
            raise _LoweringError("copy source must have nn.memory type", location=expr.location)
        source_memory = _nn_memory_type_to_memory(source_type, location=expr.location)
        result_type = _memory_to_nn_type(_KG_OPERATION_DMA.copy(source_memory, expr.space), location=expr.location)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, DmaCastAST):
        source_type = _infer_expr_type(expr.source, type_map, runtime_values=runtime_values)
        if not isinstance(source_type, NnMemoryType):
            raise _LoweringError("cast source must have nn.memory type", location=expr.location)
        source_memory = _nn_memory_type_to_memory(source_type, location=expr.location)
        result_type = _memory_to_nn_type(
            _KG_OPERATION_DMA.cast(source_memory, expr.dtype, memoryspace=expr.memoryspace),
            location=expr.location,
        )
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, DmaViewAST):
        source_type = _infer_expr_type(expr.source, type_map, runtime_values=runtime_values)
        if not isinstance(source_type, NnMemoryType):
            raise _LoweringError("view source must have nn.memory type", location=expr.location)
        source_memory = _nn_memory_type_to_memory(source_type, location=expr.location)
        offset_value = _symbolic_index_sequence(expr.offset, location=expr.location, runtime_values=runtime_values)
        size_value = _symbolic_index_sequence(expr.size, location=expr.location, runtime_values=runtime_values)
        stride_value = _symbolic_index_sequence(expr.stride, location=expr.location, runtime_values=runtime_values)
        result_type = _memory_to_nn_type(
            _KG_OPERATION_DMA.view(source_memory, offset_value, size_value, stride_value),
            location=expr.location,
        )
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, DmaReshapeAST):
        source_type = _infer_expr_type(expr.source, type_map, runtime_values=runtime_values)
        if not isinstance(source_type, NnMemoryType):
            raise _LoweringError("reshape source must have nn.memory type", location=expr.location)
        source_memory = _nn_memory_type_to_memory(source_type, location=expr.location)
        shape_value = _symbolic_index_sequence(expr.shape, location=expr.location, runtime_values=runtime_values)
        result_type = _memory_to_nn_type(_KG_OPERATION_DMA.reshape(source_memory, shape_value), location=expr.location)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, DmaFlattenAST):
        source_type = _infer_expr_type(expr.source, type_map, runtime_values=runtime_values)
        if not isinstance(source_type, NnMemoryType):
            raise _LoweringError("flatten source must have nn.memory type", location=expr.location)
        source_memory = _nn_memory_type_to_memory(source_type, location=expr.location)
        result_type = _memory_to_nn_type(_KG_OPERATION_DMA.flatten(source_memory), location=expr.location)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, NnBroadcastAST):
        value_type = _infer_expr_type(expr.value, type_map, runtime_values=runtime_values)
        target_type = _infer_expr_type(expr.target, type_map, runtime_values=runtime_values)
        if not isinstance(value_type, NnMemoryType) or not isinstance(target_type, NnMemoryType):
            raise _LoweringError("broadcast operands must be nn.memory", location=expr.location)
        source_memory = _nn_memory_type_to_memory(value_type, location=expr.location)
        target_memory = _nn_memory_type_to_memory(target_type, location=expr.location)
        output_memory = _KG_OPERATION_NN.broadcast(source_memory, target_memory)
        result_type = _memory_to_nn_type(output_memory, location=expr.location)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, NnBroadcastToAST):
        source_type = _infer_expr_type(expr.source, type_map, runtime_values=runtime_values)
        if not isinstance(source_type, NnMemoryType):
            raise _LoweringError("broadcast_to source must be nn.memory", location=expr.location)
        source_memory = _nn_memory_type_to_memory(source_type, location=expr.location)
        target_attrs = _build_static_index_attrs_exact(
            expr.target_shape,
            location=expr.location,
            runtime_values=runtime_values,
        )
        target_dims: list[SymbolDim] = []
        for attr in target_attrs:
            dim_symbol = _shape_attr_to_symbol_dim(attr, expr.location)
            if dim_symbol is None:
                raise _LoweringError("broadcast_to target_shape contains unknown dimension", location=expr.location)
            target_dims.append(dim_symbol)
        if not isinstance(expr.space, MemorySpace):
            raise _LoweringError("broadcast_to space must be MemorySpace", location=expr.location)
        output_memory = _KG_OPERATION_NN.broadcast_to(source_memory, target_dims, expr.space)
        result_type = _memory_to_nn_type(output_memory, location=expr.location)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, NnTransposeAST):
        value_type = _infer_expr_type(expr.value, type_map, runtime_values=runtime_values)
        if not isinstance(value_type, NnMemoryType):
            raise _LoweringError("transpose input must be nn.memory", location=expr.location)
        perm_values = _parse_transpose_perm_expr(expr.perm, expr.location)
        input_memory = _nn_memory_type_to_memory(value_type, location=expr.location)
        output_memory = _KG_OPERATION_NN.transpose(input_memory, perm_values)
        result_type = _memory_to_nn_type(output_memory, location=expr.location)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, NnUnaryAST):
        from kernel_gen.dsl.mlir_gen.emit.call_nn import infer_nn_type

        result_type = infer_nn_type(expr, type_map, runtime_values=runtime_values, config=config)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, NnReduceAST):
        input_type = _infer_expr_type(expr.value, type_map, runtime_values=runtime_values)
        if not isinstance(input_type, NnMemoryType):
            raise _LoweringError("reduce input must be nn.memory", location=expr.location)
        output_shape = _infer_reduce_output_shape_attrs(expr, input_type)
        stride_attr = _build_symbolic_stride_attrs(output_shape, expr.location)
        result_type = _memory_type_from_parts(
            output_shape,
            stride_attr,
            input_type.element_type,
            input_type.space,
        )
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, NnSoftmaxAST):
        input_type = _infer_expr_type(expr.value, type_map, runtime_values=runtime_values)
        if not isinstance(input_type, NnMemoryType):
            raise _LoweringError("softmax input must be nn.memory", location=expr.location)
        result_type = input_type
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, ConvAST):
        value_type = _infer_expr_type(expr.value, type_map, runtime_values=runtime_values)
        weight_type = _infer_expr_type(expr.weight, type_map, runtime_values=runtime_values)
        if not isinstance(value_type, NnMemoryType) or not isinstance(weight_type, NnMemoryType):
            raise _LoweringError("conv operands must be nn.memory", location=expr.location)
        result_type = _infer_conv_memory_type(expr, value_type, weight_type, runtime_values=runtime_values)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, Img2ColAST):
        input_expr, raw_params = _parse_img2col_helper(expr)
        input_type = _infer_expr_type(input_expr, type_map, runtime_values=runtime_values)
        if not isinstance(input_type, NnMemoryType):
            raise _LoweringError(f"{expr.kind} input must be nn.memory", location=expr.location)
        params = _resolve_img2col_param_values(expr, raw_params, runtime_values)
        out_shape = _infer_img2col_output_shape_attrs(expr, input_type, params)
        stride_attr = _build_symbolic_stride_attrs(out_shape, expr.location)
        result_type = _memory_type_from_parts(out_shape, stride_attr, input_type.element_type, input_type.space)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, FCAST):
        value_type = _infer_expr_type(expr.value, type_map, runtime_values=runtime_values)
        weight_type = _infer_expr_type(expr.weight, type_map, runtime_values=runtime_values)
        if not isinstance(value_type, NnMemoryType) or not isinstance(weight_type, NnMemoryType):
            raise _LoweringError("fc operands must be nn.memory", location=expr.location)
        value_shape = list(value_type.shape.data)
        weight_shape = list(weight_type.shape.data)
        if len(value_shape) != 2 or len(weight_shape) != 2:
            raise _LoweringError("fc operands must be rank-2 nn.memory", location=expr.location)
        out_shape = [value_shape[0], weight_shape[0]]
        out_stride = _build_default_stride_attrs(out_shape)
        result_type = _memory_type_from_parts(out_shape, out_stride, value_type.element_type, value_type.space)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, MatmulAST):
        lhs_type = _infer_expr_type(expr.lhs, type_map, runtime_values=runtime_values)
        rhs_type = _infer_expr_type(expr.rhs, type_map, runtime_values=runtime_values)
        if not isinstance(lhs_type, NnMemoryType) or not isinstance(rhs_type, NnMemoryType):
            raise _LoweringError("matmul operands must be nn.memory", location=expr.location)
        result_type = _infer_matmul_memory_type(lhs_type, rhs_type, expr.memoryspace, expr.location)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, StoreAST):
        raise _LoweringError("StoreAST does not produce a value", location=expr.location)
    if isinstance(expr, DmaFreeAST):
        raise _LoweringError("free does not produce a value", location=expr.location)
    if isinstance(expr, ForAST):
        raise _LoweringError("ForAST does not produce a value", location=expr.location)
    if isinstance(expr, ArchBarrierAST):
        raise _LoweringError("barrier does not produce a value", location=expr.location)
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
    if isinstance(expr, TensorAxisAccessAST):
        result_type = _infer_tensor_axis_access_type(expr, type_map, runtime_values=runtime_values)
        type_map[expr_key] = result_type
        return result_type
    if isinstance(expr, SymbolToFloatAST):
        source_type = _infer_expr_type(expr.source, type_map, runtime_values=runtime_values)
        if not isinstance(source_type, SymbolValueType):
            raise _LoweringError('symbol.to_float source must have type !symbol.int<"expr">', location=expr.location)
        type_map[expr_key] = f32
        return f32

    if isinstance(expr, BinaryExprAST):
        from kernel_gen.dsl.mlir_gen.emit.call_nn import infer_nn_type

        result_type = infer_nn_type(expr, type_map, runtime_values=runtime_values, config=config)
        type_map[expr_key] = result_type
        return result_type

    if isinstance(expr, CompareExprAST):
        from kernel_gen.dsl.mlir_gen.emit.call_nn import infer_nn_type

        result_type = infer_nn_type(expr, type_map, runtime_values=runtime_values, config=config)
        type_map[expr_key] = result_type
        return result_type

    if isinstance(expr, (TensorAST, ScalarArgAST, VarAST)):
        if expr_key not in type_map:
            raise _LoweringError("Unknown input reference", location=getattr(expr, "location", None))
        return type_map[expr_key]

    raise _LoweringError("Unsupported expression for lowering", location=getattr(expr, "location", None))


def _cast_nn_scalar_operand(
    value: SSAValue,
    target_element_type: Attribute,
    ctx: EmitContext,
    location: SourceLocation | None,
) -> SSAValue:
    """将 nn mixed 路径中的标量 operand 转换到目标 dtype。

    创建者: 小李飞刀
    最后一次更改: OpenAI

    功能说明:
    - `!symbol.int` 根据目标类型 lowering 为 `symbol.to_int` 或 `symbol.to_float`。
    - 普通整型按需 lowering 为 `arith.sitofp`，浮点之间按需做 ext/trunc。

    使用示例:
    - _cast_nn_scalar_operand(value, f32, ctx, location=None)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
            if source_type == target_element_type:
                return value
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
        if source_type == target_element_type:
            return value
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
    """为 nn mixed binary 路径生成符合公开合同的标量 SSA value。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 对整数字面量统一经 `symbol.const` 生成 `!symbol.int`，保持 mixed 路径一致语义。
    - 对已有 scalar SSA value 默认按目标 element type 执行 `_cast_nn_scalar_operand(...)`。
    - `cast_to_element_type=False` 时保留 `!symbol.int`，用于 `nn.floordiv(memory, symbol)` 合同。
    - 若无法物化 scalar operand，抛出稳定错误短语供调用方诊断。

    使用示例:
    - _materialize_mixed_binary_scalar_operand(expr.rhs, rhs, f32, ctx, expr.location)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    """lower nn elementwise arithmetic 的 mixed memory+scalar/symbol 路径。

    创建者: 小李飞刀
    最后一次更改: OpenAI

    功能说明:
    - 保持 memory operand 的 `shape/stride/space`，并在 dtype 不一致时插入 `nn.cast`。
    - 整数字面量走 `symbol.const`，symbol 标量按目标 dtype 转成 `symbol.to_int`/`symbol.to_float`。

    使用示例:
    - _lower_mixed_binary_expr(expr, lhs, rhs, ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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

    result_type = _infer_expr_type(
        expr,
        ctx.types,
        runtime_values=_ctx_runtime_values(ctx),
        config=ctx.config,
    )
    if not isinstance(result_type, NnMemoryType):
        raise _LoweringError("Binary op result must be nn.memory", location=expr.location)

    memory_value = lhs if lhs_is_memory else rhs
    memory_type = lhs_type if lhs_is_memory else rhs_type
    scalar_value = rhs if lhs_is_memory else lhs
    scalar_expr = expr.rhs if lhs_is_memory else expr.lhs
    if not isinstance(memory_type, NnMemoryType):
        raise _LoweringError("Binary op operands must have nn.memory type", location=expr.location)

    if memory_type.element_type != result_type.element_type:
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
    ctx._set_cache(_expr_key(expr), op.result)
    return op.result


def _lower_expr(expr: object, ctx: EmitContext) -> object:
    """将表达式 AST 递归下沉为 MLIR SSA value。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 递归处理常量、内存操作、`symbol.to_float` 与算术/比较表达式，生成对应的 MLIR op。
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
    """
    expr_key = _expr_key(expr)
    runtime_values = _ctx_runtime_values(ctx)
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
        result_type = _infer_expr_type(expr, ctx.types, runtime_values=runtime_values, config=ctx.config)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("LoadAST result must be nn.memory", location=expr.location)
        if expr.kind == "slice":
            if any(isinstance(dim, StringAttr) for dim in result_type.shape.data):
                alloc_shape = _build_index_operands_from_layout(result_type.shape, ctx, location=expr.location)
            else:
                alloc_shape = []
            alloc_op = DmaAllocOp(alloc_shape, result_type)
            ctx.builder.add_op(alloc_op)
            slice_op = DmaSliceOp(alloc_op.result, source, offsets, sizes, strides)
            ctx.builder.add_op(slice_op)
            ctx._set_cache(expr_key, alloc_op.result)
            return alloc_op.result
        if any(isinstance(dim, StringAttr) for dim in result_type.shape.data):
            alloc_shape = _build_index_operands_from_layout(result_type.shape, ctx, location=expr.location)
        else:
            alloc_shape = []
        alloc_op = DmaAllocOp(alloc_shape, result_type)
        ctx.builder.add_op(alloc_op)
        load_op = DmaLoadOp(
            alloc_op.result,
            source,
            offsets,
            sizes,
            strides,
        )
        ctx.builder.add_op(load_op)
        ctx._set_cache(expr_key, alloc_op.result)
        return alloc_op.result
    if isinstance(expr, DmaAllocAST):
        result_type = _infer_expr_type(expr, ctx.types, runtime_values=runtime_values, config=ctx.config)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("alloc result must be nn.memory", location=expr.location)
        if isinstance(expr.shape, (list, tuple)):
            shape_entries = list(expr.shape)
        else:
            shape_entries = [expr.shape]
        is_static_shape = True
        for entry in shape_entries:
            if isinstance(entry, ConstAST) and isinstance(entry.value, int):
                continue
            if isinstance(entry, int):
                continue
            is_static_shape = False
            break
        shape = [] if is_static_shape else _build_index_operands_exact(expr.shape, ctx, location=expr.location)
        op = DmaAllocOp(shape, result_type)
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        return op.result
    if isinstance(expr, DmaCopyAST):
        source = _lower_expr(expr.source, ctx)
        source_type = _expect_memory_value(source, expr.location)
        result_type = _infer_expr_type(expr, ctx.types, runtime_values=runtime_values, config=ctx.config)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("copy result must be nn.memory", location=expr.location)
        if all(isinstance(dim, IntAttr) for dim in result_type.shape.data):
            alloc_shape: list[SSAValue] = []
        else:
            alloc_shape = _build_index_operands_from_layout(result_type.shape, ctx, location=expr.location)
        alloc_op = DmaAllocOp(alloc_shape, result_type)
        ctx.builder.add_op(alloc_op)
        copy_op = DmaCopyOp(alloc_op.result, source)
        ctx.builder.add_op(copy_op)
        ctx._set_cache(expr_key, alloc_op.result)
        ctx.types[_expr_key(expr.source)] = source_type
        return alloc_op.result
    if isinstance(expr, DmaCastAST):
        source = _lower_expr(expr.source, ctx)
        _expect_memory_value(source, expr.location)
        result_type = _infer_expr_type(expr, ctx.types, runtime_values=runtime_values, config=ctx.config)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("cast result must be nn.memory", location=expr.location)
        if all(isinstance(dim, IntAttr) for dim in result_type.shape.data):
            alloc_shape = []
        else:
            alloc_shape = _build_index_operands_from_layout(result_type.shape, ctx, location=expr.location)
        alloc_op = DmaAllocOp(alloc_shape, result_type)
        ctx.builder.add_op(alloc_op)
        op = DmaCastOp(alloc_op.result, source)
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, alloc_op.result)
        return alloc_op.result
    if isinstance(expr, DmaViewAST):
        source = _lower_expr(expr.source, ctx)
        _expect_memory_value(source, expr.location)
        result_type = _infer_expr_type(expr, ctx.types, runtime_values=runtime_values, config=ctx.config)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("view result must be nn.memory", location=expr.location)
        rank = len(result_type.shape.data)
        offsets = _build_index_attrs(expr.offset, rank, ctx, location=expr.location)
        shape = _build_index_operands_exact(expr.size, ctx, location=expr.location)
        stride = _build_index_attrs(expr.stride, rank, ctx, default_value=1, location=expr.location)
        op = DmaViewOp(source, offsets, shape, stride, result_type)
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        return op.result
    if isinstance(expr, DmaReshapeAST):
        source = _lower_expr(expr.source, ctx)
        _expect_memory_value(source, expr.location)
        result_type = _infer_expr_type(expr, ctx.types, runtime_values=runtime_values, config=ctx.config)
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
        result_type = _infer_expr_type(expr, ctx.types, runtime_values=runtime_values, config=ctx.config)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("flatten result must be nn.memory", location=expr.location)
        shape_operand = _build_flatten_shape_operands(source, source_type, ctx, location=expr.location)
        op = DmaReshapeOp(source, shape_operand, result_type)
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        return op.result
    if isinstance(expr, NnUnaryAST):
        from kernel_gen.dsl.mlir_gen.emit.call_nn import emit_nn_call

        return emit_nn_call(expr, ctx)
    if isinstance(expr, NnBroadcastAST):
        value = _lower_expr(expr.value, ctx)
        target = _lower_expr(expr.target, ctx)
        _expect_memory_value(value, expr.location)
        target_type = _expect_memory_value(target, expr.location)
        result_type = _infer_expr_type(expr, ctx.types, runtime_values=runtime_values, config=ctx.config)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("broadcast result must be nn.memory", location=expr.location)
        if result_type != target_type:
            raise _LoweringError("broadcast result must match target type", location=expr.location)
        op = NnBroadcastOp(value, result_type, result_type.space)
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        return op.result
    if isinstance(expr, NnBroadcastToAST):
        source = _lower_expr(expr.source, ctx)
        _expect_memory_value(source, expr.location)
        result_type = _infer_expr_type(expr, ctx.types, runtime_values=runtime_values, config=ctx.config)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("broadcast_to result must be nn.memory", location=expr.location)
        op = NnBroadcastOp(source, result_type, result_type.space)
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        return op.result
    if isinstance(expr, NnTransposeAST):
        value = _lower_expr(expr.value, ctx)
        input_type = _expect_memory_value(value, expr.location)
        result_type = _infer_expr_type(expr, ctx.types, runtime_values=runtime_values, config=ctx.config)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("transpose result must be nn.memory", location=expr.location)
        perm_values = _parse_transpose_perm_expr(expr.perm, expr.location)
        op = NnTransposeOp(value, result_type, perm=perm_values, space=input_type.space)
        op.verify()
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        return op.result
    if isinstance(expr, NnReduceAST):
        input_value = _lower_expr(expr.value, ctx)
        input_type = _expect_memory_value(input_value, expr.location)
        result_type = _infer_expr_type(expr, ctx.types, runtime_values=runtime_values, config=ctx.config)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("reduce result must be nn.memory", location=expr.location)
        axes = _parse_reduce_axis_expr(expr.axis, expr.location)
        if axes is None:
            axes = list(range(len(input_type.shape.data)))
        keepdim_value, keepdim_valid = _parse_reduce_keepdim_expr(expr.keepdim, expr.location)
        keepdim_arg: object = keepdim_value
        if not keepdim_valid and isinstance(keepdim_value, int):
            keepdim_arg = IntegerAttr(int(keepdim_value), IntegerType(64))
        op_map = {
            "reduce_sum": NnReduceSumOp,
            "reduce_min": NnReduceMinOp,
            "reduce_max": NnReduceMaxOp,
        }
        if expr.kind not in op_map:
            raise _LoweringError("Unsupported reduce helper", location=expr.location)
        op = op_map[expr.kind](input_value, result_type, axes=axes, keepdim=keepdim_arg, space=input_type.space)
        op.verify()
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        return op.result
    if isinstance(expr, NnSoftmaxAST):
        input_value = _lower_expr(expr.value, ctx)
        input_type = _expect_memory_value(input_value, expr.location)
        result_type = _infer_expr_type(expr, ctx.types, runtime_values=runtime_values, config=ctx.config)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("softmax result must be nn.memory", location=expr.location)
        axis_value = _parse_softmax_axis_expr(expr.axis, len(input_type.shape.data), expr.location)
        op = NnSoftmaxOp(input_value, result_type, axis=axis_value, space=input_type.space)
        op.verify()
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        return op.result
    if isinstance(expr, ConvAST):
        value = _lower_expr(expr.value, ctx)
        weight = _lower_expr(expr.weight, ctx)
        value_type = _expect_memory_value(value, expr.location)
        weight_type = _expect_memory_value(weight, expr.location)
        result_type = _infer_expr_type(expr, ctx.types, runtime_values=runtime_values, config=ctx.config)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("conv result must be nn.memory", location=expr.location)

        _, _, raw_params = _parse_conv_helper(expr)
        params = _resolve_conv_param_values(expr, raw_params, runtime_values)
        c_out_dim, _, kh_attr, kw_attr = weight_type.shape.data
        value_memory = _nn_memory_type_to_memory(value_type, location=expr.location)
        kh_dim = _shape_attr_to_symbol_dim(kh_attr, expr.location)
        kw_dim = _shape_attr_to_symbol_dim(kw_attr, expr.location)
        if kh_dim is None or kw_dim is None:
            raise _LoweringError("conv kh/kw must be int or symbol", location=expr.location)
        img2col_memory = _KG_OPERATION_NN.img2col2d(
            value_memory,
            kh=kh_dim,
            kw=kw_dim,
            sh=params["sh"],
            sw=params["sw"],
            dh=params["dh"],
            dw=params["dw"],
            ph=params["ph"],
            pw=params["pw"],
            pl=params["pl"],
            pr=params["pr"],
        )
        img2col_type = _memory_to_nn_type(img2col_memory, location=expr.location)
        img2col_op = NnImg2col2dOp(
            value,
            img2col_type,
            kh=_shape_attr_to_symbol_operand(kh_attr, ctx, location=expr.location),
            kw=_shape_attr_to_symbol_operand(kw_attr, ctx, location=expr.location),
            sh=_resolve_index_operand(raw_params["sh"], ctx, expr.location),
            sw=_resolve_index_operand(raw_params["sw"], ctx, expr.location),
            dh=_resolve_index_operand(raw_params["dh"], ctx, expr.location),
            dw=_resolve_index_operand(raw_params["dw"], ctx, expr.location),
            ph=_resolve_index_operand(raw_params["ph"], ctx, expr.location),
            pw=_resolve_index_operand(raw_params["pw"], ctx, expr.location),
            pl=_resolve_index_operand(raw_params["pl"], ctx, expr.location),
            pr=_resolve_index_operand(raw_params["pr"], ctx, expr.location),
            space=value_type.space,
        )
        img2col_op.verify()
        ctx.builder.add_op(img2col_op)

        batch_dim, out_h_dim, out_w_dim = _build_img2col2d_output_dim_operands(img2col_op.result, ctx)
        contract_dim = _shape_numel_attr(weight_type.shape.data[1:])
        image_dim = _shape_numel_attr([img2col_type.shape.data[0], img2col_type.shape.data[4], img2col_type.shape.data[5]])
        weight_matrix_shape = [c_out_dim, contract_dim]
        weight_matrix_type = _memory_type_from_parts(
            weight_matrix_shape,
            _build_symbolic_stride_attrs(weight_matrix_shape, expr.location),
            weight_type.element_type,
            weight_type.space,
        )
        weight_reshape = DmaReshapeOp(
            weight,
            [
                _shape_attr_to_symbol_operand(c_out_dim, ctx, location=expr.location),
                _shape_attr_to_symbol_operand(contract_dim, ctx, location=expr.location),
            ],
            weight_matrix_type,
        )
        weight_reshape.verify()
        ctx.builder.add_op(weight_reshape)

        col_matrix_shape = [contract_dim, image_dim]
        col_matrix_type = _memory_type_from_parts(
            col_matrix_shape,
            _build_symbolic_stride_attrs(col_matrix_shape, expr.location),
            img2col_type.element_type,
            img2col_type.space,
        )
        col_reshape = DmaReshapeOp(
            img2col_op.result,
            [
                _shape_attr_to_symbol_operand(contract_dim, ctx, location=expr.location),
                _build_symbol_product_operand([batch_dim, out_h_dim, out_w_dim], ctx, location=expr.location),
            ],
            col_matrix_type,
        )
        ctx.builder.add_op(col_reshape)

        matmul_result_type = _infer_matmul_memory_type(weight_matrix_type, col_matrix_type, None, expr.location)
        matmul_op = NnMatmulOp(weight_reshape.result, col_reshape.result, matmul_result_type, weight_matrix_type.space)
        matmul_op.verify()
        ctx.builder.add_op(matmul_op)

        result_reshape = DmaReshapeOp(
            matmul_op.result,
            [
                batch_dim,
                _shape_attr_to_symbol_operand(c_out_dim, ctx, location=expr.location),
                out_h_dim,
                out_w_dim,
            ],
            result_type,
        )
        ctx.builder.add_op(result_reshape)
        ctx._set_cache(expr_key, result_reshape.result)
        return result_reshape.result
    if isinstance(expr, Img2ColAST):
        input_expr, raw_params = _parse_img2col_helper(expr)
        input_value = _lower_expr(input_expr, ctx)
        input_type = _expect_memory_value(input_value, expr.location)
        result_type = _infer_expr_type(expr, ctx.types, runtime_values=runtime_values, config=ctx.config)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError(f"{expr.kind} result must be nn.memory", location=expr.location)
        if expr.kind == "img2col1d":
            op = NnImg2col1dOp(
                input_value,
                result_type,
                kw=_resolve_index_operand(raw_params["kw"], ctx, expr.location),
                sw=_resolve_index_operand(raw_params["sw"], ctx, expr.location),
                dw=_resolve_index_operand(raw_params["dw"], ctx, expr.location),
                pl=_resolve_index_operand(raw_params["pl"], ctx, expr.location),
                pr=_resolve_index_operand(raw_params["pr"], ctx, expr.location),
                space=input_type.space,
            )
        elif expr.kind == "img2col2d":
            op = NnImg2col2dOp(
                input_value,
                result_type,
                kh=_resolve_index_operand(raw_params["kh"], ctx, expr.location),
                kw=_resolve_index_operand(raw_params["kw"], ctx, expr.location),
                sh=_resolve_index_operand(raw_params["sh"], ctx, expr.location),
                sw=_resolve_index_operand(raw_params["sw"], ctx, expr.location),
                dh=_resolve_index_operand(raw_params["dh"], ctx, expr.location),
                dw=_resolve_index_operand(raw_params["dw"], ctx, expr.location),
                ph=_resolve_index_operand(raw_params["ph"], ctx, expr.location),
                pw=_resolve_index_operand(raw_params["pw"], ctx, expr.location),
                pl=_resolve_index_operand(raw_params["pl"], ctx, expr.location),
                pr=_resolve_index_operand(raw_params["pr"], ctx, expr.location),
                space=input_type.space,
            )
        else:
            raise _LoweringError("Unsupported img2col helper", location=expr.location)
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        return op.result
    if isinstance(expr, FCAST):
        value = _lower_expr(expr.value, ctx)
        weight = _lower_expr(expr.weight, ctx)
        value_type = _expect_memory_value(value, expr.location)
        weight_type = _expect_memory_value(weight, expr.location)
        if len(value_type.shape.data) != 2 or len(weight_type.shape.data) != 2:
            raise _LoweringError("fc operands must be rank-2 nn.memory", location=expr.location)
        transposed_shape = [weight_type.shape.data[1], weight_type.shape.data[0]]
        transposed_stride = [weight_type.stride.data[1], weight_type.stride.data[0]]
        transpose_type = NnMemoryType(
            ArrayAttr(list(transposed_shape)),
            ArrayAttr(list(transposed_stride)),
            weight_type.element_type,
            weight_type.space,
        )
        transpose_op = NnTransposeOp(weight, transpose_type, perm=[1, 0], space=weight_type.space)
        transpose_op.verify()
        ctx.builder.add_op(transpose_op)
        result_type = _infer_expr_type(expr, ctx.types, runtime_values=runtime_values, config=ctx.config)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("fc result must be nn.memory", location=expr.location)
        matmul_op = NnMatmulOp(value, transpose_op.result, result_type, result_type.space)
        matmul_op.verify()
        ctx.builder.add_op(matmul_op)
        ctx._set_cache(expr_key, matmul_op.result)
        return matmul_op.result
    if isinstance(expr, MatmulAST):
        lhs = _lower_expr(expr.lhs, ctx)
        rhs = _lower_expr(expr.rhs, ctx)
        lhs_type = _expect_memory_value(lhs, expr.location)
        rhs_type = _expect_memory_value(rhs, expr.location)
        result_type = _infer_expr_type(expr, ctx.types, runtime_values=runtime_values, config=ctx.config)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("matmul result must be nn.memory", location=expr.location)
        if lhs_type.element_type != result_type.element_type:
            cast_type = _memory_type_from_parts(
                lhs_type.shape.data,
                lhs_type.stride.data,
                result_type.element_type,
                lhs_type.space,
            )
            lhs_cast_alloc = DmaAllocOp([], cast_type)
            ctx.builder.add_op(lhs_cast_alloc)
            cast_op = DmaCastOp(lhs_cast_alloc.result, lhs)
            ctx.builder.add_op(cast_op)
            lhs = lhs_cast_alloc.result
        if rhs_type.element_type != result_type.element_type:
            cast_type = _memory_type_from_parts(
                rhs_type.shape.data,
                rhs_type.stride.data,
                result_type.element_type,
                rhs_type.space,
            )
            rhs_cast_alloc = DmaAllocOp([], cast_type)
            ctx.builder.add_op(rhs_cast_alloc)
            cast_op = DmaCastOp(rhs_cast_alloc.result, rhs)
            ctx.builder.add_op(cast_op)
            rhs = rhs_cast_alloc.result
        op = NnMatmulOp(lhs, rhs, result_type, result_type.space)
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
    if isinstance(expr, TensorAxisAccessAST):
        source = _lower_expr(expr.tensor, ctx)
        _expect_memory_value(source, expr.location)
        axis = _resolve_tensor_axis_index(expr.axis, expr.location)
        if expr.kind == "shape":
            op = SymbolGetDimOp(source, IntAttr(axis))
        elif expr.kind == "stride":
            op = SymbolGetStrideOp(source, IntAttr(axis))
        else:
            raise _LoweringError("Unsupported tensor axis access kind", location=expr.location)
        try:
            op.verify()
        except VerifyException as exc:
            raise _LoweringError(str(exc), location=expr.location) from exc
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        ctx.types[expr_key] = op.result.type
        return op.result
    if isinstance(expr, SymbolToFloatAST):
        source = _lower_expr(expr.source, ctx)
        if not isinstance(getattr(source, "type", None), SymbolValueType):
            raise _LoweringError('symbol.to_float source must have type !symbol.int<"expr">', location=expr.location)
        op = SymbolToFloatOp(source, f32)
        ctx.builder.add_op(op)
        ctx._set_cache(expr_key, op.result)
        ctx.types[expr_key] = op.result.type
        return op.result

    if isinstance(expr, PythonCalleeCallAST):
        result_type = _infer_expr_type(expr, ctx.types, config=ctx.config)
        registry_value: object = {}
        if isinstance(ctx.config, dict):
            registry_value = ctx.config.get(_MLIR_GEN_CALLEE_REGISTRY_CONFIG_KEY, {})
        if not isinstance(registry_value, dict):
            raise _LoweringError("Python callee registry must be dict", location=expr.location)
        callee_op = registry_value.get(expr.callee)
        if not isinstance(callee_op, func.FuncOp):
            raise _LoweringError("Python callee is missing from registry", location=expr.location)
        callee_name = callee_op.sym_name.data
        args = [SSAValue.get(_lower_expr(arg, ctx)) for arg in expr.args]
        call_op = func.CallOp(callee_name, args, [result_type])
        ctx.builder.add_op(call_op)
        if len(call_op.results) != 1:
            raise _LoweringError("Python callee must return exactly one value", location=expr.location)
        ctx._set_cache(expr_key, call_op.results[0])
        ctx.types[expr_key] = call_op.results[0].type
        return call_op.results[0]

    if isinstance(expr, BinaryExprAST):
        from kernel_gen.dsl.mlir_gen.emit.call_nn import emit_nn_call

        return emit_nn_call(expr, ctx)

    if isinstance(expr, CompareExprAST):
        from kernel_gen.dsl.mlir_gen.emit.call_nn import emit_nn_call

        return emit_nn_call(expr, ctx)

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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/core.py](kernel_gen/dsl/mlir_gen/emit/core.py)
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
            ConvAST,
            Img2ColAST,
            FCAST,
            MatmulAST,
            NnBroadcastAST,
            NnBroadcastToAST,
            NnReduceAST,
            NnSoftmaxAST,
            NnTransposeAST,
            NnUnaryAST,
            ArchGetDynamicMemoryAST,
            ArchQueryAST,
            PythonCalleeCallAST,
            SymbolToFloatAST,
            TensorAxisAccessAST,
        ),
    ):
        if _expr_key(node) not in ctx.types and not isinstance(node, (TensorAST, ScalarArgAST, VarAST)):
            _infer_expr_type(node, ctx.types, runtime_values=_ctx_runtime_values(ctx), config=ctx.config)
        return _lower_expr(node, ctx)
    if isinstance(node, StoreAST):
        runtime_values = _ctx_runtime_values(ctx)
        try:
            source_memory_type = _infer_expr_type(node.value, ctx.types, runtime_values=runtime_values, config=ctx.config)
        except _LoweringError:
            source_memory_type = None
        try:
            target_memory_type = _infer_expr_type(
                node.tensor,
                ctx.types,
                runtime_values=runtime_values,
                config=ctx.config,
            )
        except _LoweringError:
            target_memory_type = None
        if isinstance(source_memory_type, NnMemoryType) and isinstance(target_memory_type, NnMemoryType):
            source_memory = _nn_memory_type_to_memory(source_memory_type, location=node.location)
            target_memory = _nn_memory_type_to_memory(target_memory_type, location=node.location)
            offsets_value = _symbolic_index_sequence(node.offset, location=node.location, runtime_values=runtime_values)
            sizes_value = (
                [dim for dim in source_memory.shape]
                if node.sizes is None
                else _symbolic_index_sequence(node.sizes, location=node.location, runtime_values=runtime_values)
            )
            strides_value = (
                None
                if node.stride is None
                else _symbolic_index_sequence(node.stride, location=node.location, runtime_values=runtime_values)
            )
            if node.kind == "deslice":
                _KG_OPERATION_DMA.deslice(source_memory, target_memory, offsets_value, sizes_value, strides_value)
            else:
                _KG_OPERATION_DMA.store(source_memory, target_memory, offsets_value, sizes_value, strides_value)
        target = _lower_expr(node.tensor, ctx)
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
        try:
            value_type = _infer_expr_type(
                node.value,
                ctx.types,
                runtime_values=_ctx_runtime_values(ctx),
                config=ctx.config,
            )
        except _LoweringError:
            value_type = None
        if not isinstance(value_type, NnMemoryType):
            raw_value = node.value.value if isinstance(node.value, ConstAST) else node.value
            _KG_OPERATION_DMA.free(raw_value)
        value = _lower_expr(node.value, ctx)
        _expect_memory_value(value, node.location)
        free_op = DmaFreeOp(value)
        ctx.builder.add_op(free_op)
        return free_op
    if isinstance(node, ArchBarrierAST):
        barrier_op = ArchBarrierOp(
            _build_arch_barrier_scope_attr(node.scope, node.location),
            _build_arch_barrier_visibility_attr(node.visibility, node.location),
        )
        try:
            barrier_op.verify()
        except VerifyException as exc:
            raise _LoweringError(str(exc), location=node.location) from exc
        ctx.builder.add_op(barrier_op)
        return barrier_op
    if isinstance(node, ArchLaunchKernelAST):
        if not isinstance(node.callee, str) or node.callee == "":
            raise _LoweringError("launch_kernel callee must be function symbol reference", location=node.location)
        block = _lower_launch_extent_symbol(node.block, "block", ctx, node.location)
        thread = _lower_launch_extent_symbol(node.thread, "thread", ctx, node.location)
        subthread = _lower_launch_extent_symbol(node.subthread, "subthread", ctx, node.location)
        shared_memory_size = _lower_launch_extent_symbol(
            node.shared_memory_size,
            "shared_memory_size",
            ctx,
            node.location,
            allow_zero=True,
        )
        args = [SSAValue.get(_lower_expr(arg, ctx)) for arg in node.args]
        op = ArchLaunchKernelOp(node.callee, block, thread, subthread, shared_memory_size, args)
        try:
            op.verify()
        except VerifyException as exc:
            raise _LoweringError(str(exc), location=node.location) from exc
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
            start_expr = start_value.type.expr.expr.data
            end_expr = end_value.type.expr.expr.data
            step_expr = step_value.type.expr.expr.data
            iter_type = SymbolIterType.from_bounds(start_expr, end_expr, step_expr)
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
