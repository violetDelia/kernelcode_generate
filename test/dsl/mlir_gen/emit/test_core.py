"""Emit core helper and edge-case tests.

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 覆盖 `kernel_gen/dsl/mlir_gen/emit/core.py` 的 helper、错误分支与少量 lowering 变体。
- 用实际 `diff` 反推 `pytest`，避免只依赖集成路径补覆盖。

使用示例:
- pytest -q test/dsl/mlir_gen/emit/test_core.py

覆盖率信息:
- 覆盖率命令: coverage run -m pytest -q test/dsl/mlir_gen/emit/test_core.py && coverage report --include=kernel_gen/dsl/mlir_gen/emit/core.py -m
- 覆盖率结果: 未统计（待补充）
- 达标线: 95%

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/emit/core.py
- Spec 文档: spec/dsl/emit_mlir.md
- 测试文件: test/dsl/mlir_gen/emit/test_core.py
"""

from __future__ import annotations

import ast as py_ast
import sys
from pathlib import Path

import pytest
from xdsl.dialects import arith, func
from xdsl.dialects.builtin import (
    ArrayAttr,
    BFloat16Type,
    Float16Type,
    Float64Type,
    FloatAttr,
    IndexType,
    IntAttr,
    IntegerType,
    SymbolRefAttr,
    StringAttr,
    f32,
    i1,
    i32,
    i64,
    i8,
)
from xdsl.ir import Block, Region
from xdsl.utils.exceptions import VerifyException

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dsl.ast import (
    ArchBarrierAST,
    ArchGetDynamicMemoryAST,
    ArchLaunchKernelAST,
    ArchQueryAST,
    BinaryExprAST,
    BlockAST,
    ConstAST,
    DmaAllocAST,
    DmaCastAST,
    DmaCopyAST,
    DmaFlattenAST,
    DmaFreeAST,
    DmaReshapeAST,
    DmaViewAST,
    ConvAST,
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
    PythonCalleeCallAST,
    ScalarArgAST,
    SourceLocation,
    StoreAST,
    SymbolToFloatAST,
    TensorAST,
    TensorAxisAccessAST,
    VarAST,
)
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.dsl.mlir_gen.emit import EmitContext
from kernel_gen.dsl.mlir_gen.emit import core as emit_core
from kernel_gen.dsl.mlir_gen.emit.core import emit_mlir
from kernel_gen.operation.arch import BarrierScope, BarrierVisibility
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


def _memory_type(
    shape: list[int | str],
    *,
    stride: list[int | str] | None = None,
    element_type: object = f32,
    space: MemorySpace = MemorySpace.GM,
) -> NnMemoryType:
    """构造测试用 `NnMemoryType`。

    使用示例:
    - _memory_type([2, "N"], stride=[2, 1], element_type=f32)
    """

    shape_attrs = [emit_core._dim_to_attr(dim) for dim in shape]
    stride_values = stride if stride is not None else emit_core._build_stride(list(shape))
    stride_attrs = [emit_core._dim_to_attr(dim) for dim in stride_values]
    fallback = NnMemorySpaceAttr.from_name("global")
    return emit_core._memory_type_from_parts(
        shape_attrs,
        stride_attrs,
        element_type,
        emit_core._memory_space_from_ast(space, fallback),
    )


def _memory_ctx(memory_type: NnMemoryType, symbol_name: str = "value") -> tuple[Block, EmitContext, object]:
    """创建单个 memory SSAValue 对应的测试上下文。

    使用示例:
    - block, ctx, value = _memory_ctx(_memory_type([2, 2]))
    """

    block = Block(arg_types=[memory_type])
    ctx = EmitContext(builder=block, symbols={symbol_name: block.args[0]}, types={})
    return block, ctx, block.args[0]


def _symbol_ctx(expr: str = "N", symbol_name: str = "n") -> tuple[Block, EmitContext, object]:
    """创建单个 `!symbol.int` SSAValue 对应的测试上下文。

    使用示例:
    - block, ctx, value = _symbol_ctx("N", "n")
    """

    block = Block(arg_types=[emit_core.SymbolValueType.from_expr(expr)])
    ctx = EmitContext(builder=block, symbols={symbol_name: block.args[0]}, types={})
    return block, ctx, block.args[0]


# CORE-001
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证 EmitContext config 校验与 NumericType / xdsl element_type 映射的完整基础分支。
# 测试目的: 锁定 config 形态错误、target/hardware 约束与 dtype roundtrip 诊断。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_validate_emit_context_config_and_dtype_mapping
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_validate_emit_context_config_and_dtype_mapping() -> None:
    emit_core._validate_emit_context_config(None)

    with pytest.raises(emit_core._LoweringError, match="EmitContext config must be dict or None"):
        emit_core._validate_emit_context_config([])  # type: ignore[arg-type]

    with pytest.raises(emit_core._LoweringError, match="EmitContext target must be str"):
        emit_core._validate_emit_context_config({"target": 1})

    with pytest.raises(emit_core._LoweringError, match="EmitContext hardware must be dict\\[str, int\\]"):
        emit_core._validate_emit_context_config({"hardware": []})

    with pytest.raises(emit_core._LoweringError, match="target"):
        emit_core._validate_emit_context_config({"target": "not-a-target"})

    dtype_cases = [
        (NumericType.Bool, i1),
        (NumericType.Int8, i8),
        (NumericType.Int32, i32),
        (NumericType.Int64, i64),
        (NumericType.BFloat16, BFloat16Type()),
        (NumericType.Float16, Float16Type()),
        (NumericType.Float32, f32),
        (NumericType.Float64, Float64Type()),
    ]
    for dtype, expected in dtype_cases:
        assert emit_core._dtype_to_xdsl(dtype) == expected
        assert emit_core._xdsl_to_dtype(expected) == dtype

    with pytest.raises(emit_core._LoweringError, match="Unsupported dtype"):
        emit_core._dtype_to_xdsl(object())  # type: ignore[arg-type]
    with pytest.raises(emit_core._LoweringError, match="Unsupported element_type for nn arithmetic"):
        emit_core._xdsl_to_dtype(StringAttr("broken"))


# CORE-002
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证 shape / symbolic-dim / stride / numel 辅助函数的核心分支。
# 测试目的: 锁定静态维、符号维、未知维与表达式分解路径。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_symbolic_shape_and_stride_helpers
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_symbolic_shape_and_stride_helpers() -> None:
    assert emit_core._build_stride([2, 3, "N"]) == [3, 1, "?"]
    assert emit_core._mul_symbol(2, 3) == 6
    assert emit_core._mul_symbol(1, "N") == "N"
    assert emit_core._mul_symbol("N", 1) == "N"
    default_stride = emit_core._build_default_stride_attrs([IntAttr(2), StringAttr("N"), StringAttr("?")])
    assert len(default_stride) == 3

    node = py_ast.parse("-(N + 1) / 2", mode="eval").body
    value = emit_core._eval_symbolic_dim_node(node, None)
    assert isinstance(value, SymbolDim)
    assert emit_core._eval_symbolic_dim_expr("N + 1", None).get_value() == "N + 1"

    assert emit_core._shape_attr_to_symbol_dim(IntAttr(4), None).get_value() == 4
    assert emit_core._shape_attr_to_symbol_dim(StringAttr("?"), None) is None
    assert emit_core._shape_attr_to_symbol_dim(StringAttr("N + 1"), None).get_value() == "N + 1"
    with pytest.raises(emit_core._LoweringError, match="Unsupported shape attribute"):
        emit_core._shape_attr_to_symbol_dim(FloatAttr(1.0, f32), None)

    stride_attrs = emit_core._build_symbolic_stride_attrs([IntAttr(2), StringAttr("N"), StringAttr("?")], None)
    assert len(stride_attrs) == 3
    assert emit_core._shape_numel_attr([IntAttr(2), IntAttr(3)]) == IntAttr(6)
    assert emit_core._shape_numel_attr([IntAttr(2), StringAttr("N")]) == StringAttr("2*N")
    assert emit_core._shape_numel_attr([StringAttr("?")]) == StringAttr("?")


# CORE-003
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证 launch extent / index value / loop bound / stride 入口的错误与成功路径。
# 测试目的: 锁定 symbol.int 物化、index cast 与 launch extent 的范围校验。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_launch_extent_and_index_value_helpers
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_launch_extent_and_index_value_helpers() -> None:
    block, ctx, symbol_value = _symbol_ctx("BLOCK", "block")
    assert emit_core._lower_launch_extent_symbol(ConstAST(4), "block", ctx, None).type == emit_core.SymbolValueType.from_expr("4")
    assert emit_core._lower_launch_extent_symbol(ConstAST(0), "shared_memory_size", ctx, None, allow_zero=True).type == emit_core.SymbolValueType.from_expr("0")
    scalar_extent = ScalarArgAST("block", int, is_symbolic=True)
    ctx._set_cache(emit_core._expr_key(scalar_extent), symbol_value)
    assert emit_core._lower_launch_extent_symbol(scalar_extent, "block", ctx, None) is symbol_value
    with pytest.raises(emit_core._LoweringError, match="launch_kernel block must be > 0"):
        emit_core._lower_launch_extent_symbol(ConstAST(0), "block", ctx, None)
    with pytest.raises(emit_core._LoweringError, match="launch_kernel block must be >= 0"):
        emit_core._lower_launch_extent_symbol(ConstAST(-1), "block", ctx, None, allow_zero=True)
    with pytest.raises(emit_core._LoweringError, match="launch_kernel block must be !symbol.int"):
        emit_core._lower_launch_extent_symbol(ConstAST("bad"), "block", ctx, None)

    index_block = Block(arg_types=[IndexType(), IntegerType(32), emit_core.SymbolValueType.from_expr("X"), f32])
    index_ctx = EmitContext(
        builder=index_block,
        symbols={"idx": index_block.args[0], "int32": index_block.args[1], "sym": index_block.args[2], "flt": index_block.args[3]},
        types={},
    )
    assert emit_core._ensure_index_value(index_block.args[0], index_ctx, None) is index_block.args[0]
    assert emit_core._ensure_index_value(index_block.args[1], index_ctx, None).type == IndexType()
    assert emit_core._ensure_index_value(index_block.args[2], index_ctx, None) is index_block.args[2]
    with pytest.raises(emit_core._LoweringError, match="Index operand must be integer or index"):
        emit_core._ensure_index_value(index_block.args[3], index_ctx, None)

    expr_ctx = EmitContext(builder=Block(), symbols={"N": _symbol_ctx("N", "N")[2]}, types={})
    expr = BinaryExprAST(op="mul", lhs=ConstAST("N"), rhs=ConstAST(2), location=None)
    resolved = emit_core._resolve_index_operand(expr, expr_ctx, None)
    assert isinstance(resolved.type, emit_core.SymbolValueType)
    assert emit_core._resolve_index_operand(ConstAST(2), expr_ctx, None).type == emit_core.SymbolValueType.from_expr("2")
    assert emit_core._resolve_index_operand("N*2", expr_ctx, None).type == emit_core.SymbolValueType.from_expr("2*N")
    with pytest.raises(emit_core._LoweringError, match="Unsupported index expression"):
        emit_core._resolve_index_operand(BinaryExprAST(op="mod", lhs=ConstAST(1), rhs=ConstAST(2), location=None), expr_ctx, None)

    loop_block = Block()
    loop_ctx = EmitContext(builder=loop_block, symbols={}, types={})
    loop_ctx.config = {"loop_vars": {"i": 3}}
    assert emit_core._resolve_index_expr(VarAST("i"), loop_ctx) == 3
    with pytest.raises(emit_core._LoweringError, match="Unknown loop variable"):
        emit_core._resolve_index_expr(VarAST("j"), loop_ctx)
    assert len(emit_core._build_index_attrs(None, 2, loop_ctx, default_value=0)) == 2
    assert len(emit_core._build_index_attrs(ConstAST(1), 2, loop_ctx, default_value=0)) == 2
    with pytest.raises(emit_core._LoweringError, match="Index rank mismatch"):
        emit_core._build_index_attrs([ConstAST(1)], 2, loop_ctx, default_value=0)
    with pytest.raises(emit_core._LoweringError, match="Only unit stride is supported"):
        emit_core._build_stride_attrs([ConstAST(2)], 1, loop_ctx)


# CORE-004
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证 index symbol materialize / alias / preload / product 的核心路径。
# 测试目的: 锁定 memory shape/stride 回查、别名回查和符号乘法链路。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_index_symbol_materialization_and_resolution_helpers
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_index_symbol_materialization_and_resolution_helpers() -> None:
    memory_type = _memory_type([["M"][0], 4], stride=["S", 1], element_type=f32)  # type: ignore[list-item]
    symbol_type = emit_core.SymbolValueType.from_expr("TILE")
    block = Block(arg_types=[memory_type, symbol_type])
    ctx = EmitContext(builder=block, symbols={"tensor": block.args[0], "tile": block.args[1]}, types={})

    dim_result = emit_core._materialize_index_symbol_from_memory("M", ctx, None)
    stride_result = emit_core._materialize_index_symbol_from_memory("S", ctx, None)
    assert dim_result is not None and stride_result is not None
    assert any(isinstance(op, emit_core.SymbolGetDimOp) for op in block.ops)
    assert any(isinstance(op, emit_core.SymbolGetStrideOp) for op in block.ops)

    alias_result = emit_core._materialize_index_symbol_from_symbol_alias("TILE", ctx, None)
    assert alias_result is block.args[1]
    assert emit_core._resolve_index_symbol("TILE", ctx, None) is block.args[1]
    assert emit_core._resolve_index_symbol("M", ctx, None) is dim_result
    with pytest.raises(emit_core._LoweringError, match="Unknown index symbol"):
        emit_core._resolve_index_symbol("UNKNOWN", EmitContext(builder=Block(), symbols={}, types={}), None)

    assert emit_core._split_symbol_multiplication("M*N*K") == ["M", "N", "K"]
    assert emit_core._split_symbol_multiplication("M + N") is None
    assert emit_core._split_symbol_multiplication("") is None


# CORE-S7-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 覆盖 core helper 的剩余死角与统一错误短语。
# 测试目的: 锁定 dtype/type promotion、flatten/index helper、python callee registry 与 softmax/get_dynamic_memory 的边界不回退。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_emit_core_private_remaining_helper_edges
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_emit_core_private_remaining_helper_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    lhs_type = _memory_type([2], element_type=i32)
    rhs_type = _memory_type([2], element_type=i32)

    def _raise_type_error(_lhs: object, _rhs: object) -> object:
        raise TypeError("boom")

    monkeypatch.setattr(emit_core.Memory, "_promote_ranked_dtype", staticmethod(_raise_type_error))
    with pytest.raises(emit_core._LoweringError, match="Binary op operands must have compatible element_type"):
        emit_core._resolve_nn_arith_element_type(lhs_type, rhs_type, None)

    assert emit_core._eval_symbolic_dim_node(py_ast.parse("-3", mode="eval").body, None) == -3
    symbolic_div = emit_core._eval_symbolic_dim_node(py_ast.parse("N / M", mode="eval").body, None)
    assert isinstance(symbolic_div, SymbolDim)
    assert emit_core._eval_symbolic_dim_expr("1", None).get_value() == 1
    with pytest.raises(emit_core._LoweringError, match="Unsupported symbolic dim expression"):
        emit_core._eval_symbolic_dim_expr("(", None)

    rank0_type = _memory_type([], stride=[])
    _, rank0_ctx, rank0_value = _memory_ctx(rank0_type)
    rank0_shape = emit_core._build_flatten_shape_operands(rank0_value, rank0_type, rank0_ctx, location=None)
    assert len(rank0_shape) == 1
    assert rank0_shape[0].owner.value.data == 1

    with pytest.raises(emit_core._LoweringError, match="conv kw must be int or symbol"):
        emit_core._resolve_helper_index_param_value("conv", "kw", object(), None)

    helper_block = Block(arg_types=[i32, f32, IndexType()])
    helper_ctx = EmitContext(
        builder=helper_block,
        symbols={"kw": helper_block.args[0], "bad_scalar": 7, "bad_var": 9, "flt": helper_block.args[1], "idx": helper_block.args[2]},
        types={},
    )
    casted_symbol = emit_core._shape_attr_to_symbol_operand(StringAttr("kw"), helper_ctx, location=None)
    assert type(casted_symbol.owner).__name__ == "UnrealizedConversionCastOp"
    assert type(casted_symbol.owner.operands[0].owner).__name__ == "IndexCastOp"
    assert isinstance(emit_core._lower_helper_index_operand(ConstAST("kw"), helper_ctx, location=None).type, IndexType)
    assert emit_core._lower_helper_index_operand(3, helper_ctx, location=None).owner.value.value.data == 3
    original_lookup_symbol = emit_core._lookup_symbol
    monkeypatch.setattr(
        emit_core,
        "_lookup_symbol",
        lambda node, ctx: 7 if getattr(node, "name", "") == "bad_scalar" else (9 if getattr(node, "name", "") == "bad_var" else original_lookup_symbol(node, ctx)),
    )
    with pytest.raises(emit_core._LoweringError, match="Index operand must be SSA value"):
        emit_core._lower_helper_index_operand(ScalarArgAST("bad_scalar", int, location=None), helper_ctx, location=None)
    with pytest.raises(emit_core._LoweringError, match="Index operand must be SSA value"):
        emit_core._lower_helper_index_operand(VarAST("bad_var"), helper_ctx, location=None)
    monkeypatch.setattr(emit_core, "_lookup_symbol", original_lookup_symbol)
    with pytest.raises(emit_core._LoweringError, match="Index operand must be integer or symbol"):
        emit_core._lower_helper_index_operand(ScalarArgAST("flt", float, location=None), helper_ctx, location=None)
    assert emit_core._lower_helper_index_operand(VarAST("idx"), helper_ctx, location=None).type == IntegerType(32)
    assert emit_core._resolve_index_expr(7, EmitContext(builder=Block(), symbols={}, types={})) == 7
    with pytest.raises(emit_core._LoweringError, match="Unsupported index expression"):
        emit_core._resolve_index_expr(object(), EmitContext(builder=Block(), symbols={}, types={}))

    assert emit_core._infer_broadcast_shape(
        [IntAttr(2)],
        [IntAttr(3), IntAttr(2)],
        None,
    ) == [IntAttr(3), IntAttr(2)]
    assert emit_core._infer_broadcast_shape(
        [StringAttr("?"), IntAttr(2)],
        [StringAttr("?"), IntAttr(2)],
        None,
    ) == [StringAttr("?"), IntAttr(2)]

    unknown_tensor = TensorAST(name="missing", memory=Memory([2], NumericType.Float32), location=None)
    with pytest.raises(emit_core._LoweringError, match="Unknown input reference"):
        emit_core._infer_expr_type(unknown_tensor, {})

    softmax_block = Block(arg_types=[i32])
    softmax_ctx = EmitContext(builder=softmax_block, symbols={"x": softmax_block.args[0]}, types={})
    softmax_expr = NnSoftmaxAST(value=ScalarArgAST("x", int, location=None), axis=0, location=None)
    softmax_ctx._set_cache(emit_core._expr_key(softmax_expr.value), softmax_block.args[0])
    softmax_ctx.types[emit_core._expr_key(softmax_expr)] = _memory_type([2], element_type=f32)
    with pytest.raises(emit_core._LoweringError, match="softmax input must be nn.memory"):
        emit_core._lower_expr(softmax_expr, softmax_ctx)

    arch_ctx = EmitContext(builder=Block(), symbols={}, types={})
    with pytest.raises(emit_core._LoweringError, match="get_dynamic_memory space must be on-chip MemorySpace"):
        emit_core._lower_expr(ArchGetDynamicMemoryAST(space=MemorySpace.GM, location=None), arch_ctx)

    py_ctx = EmitContext(builder=Block(), symbols={}, types={}, config={emit_core._MLIR_GEN_CALLEE_REGISTRY_CONFIG_KEY: []})
    py_expr = PythonCalleeCallAST(callee="callee", args=[ConstAST(1)], location=None)
    py_ctx.types[emit_core._expr_key(py_expr)] = i32
    with pytest.raises(emit_core._LoweringError, match="Python callee registry must be dict"):
        emit_core._lower_expr(py_expr, py_ctx)

    missing_registry_ctx = EmitContext(builder=Block(), symbols={}, types={}, config={emit_core._MLIR_GEN_CALLEE_REGISTRY_CONFIG_KEY: {}})
    missing_registry_ctx.types[emit_core._expr_key(py_expr)] = i32
    with pytest.raises(emit_core._LoweringError, match="Python callee is missing from registry"):
        emit_core._lower_expr(py_expr, missing_registry_ctx)

    product_block, product_ctx, _ = _symbol_ctx("M", "M")
    product_ctx.symbols["N"] = _symbol_ctx("N", "N")[2]
    product = emit_core._resolve_index_symbol_product("M*N", product_ctx, None)
    assert isinstance(product.type, emit_core.SymbolValueType)

    const_cache: dict[int, object] = {}
    first = emit_core._get_symbol_index_constant(3, product_ctx, None, const_cache)
    second = emit_core._get_symbol_index_constant(3, product_ctx, None, const_cache)
    assert first is second
    emit_core._preload_symbolic_index_constants(BinaryExprAST(op="add", lhs=ConstAST(2), rhs=BinaryExprAST(op="mul", lhs=ConstAST(3), rhs=ConstAST(4), location=None), location=None), product_ctx, None, const_cache)
    assert {2, 3, 4}.issubset(const_cache.keys())


# CORE-005
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证 runtime/static index 表达式与 helper 参数规整函数。
# 测试目的: 锁定运行时标量回填、默认索引列表与 exact 索引构造行为。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_runtime_and_static_index_helpers
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_runtime_and_static_index_helpers() -> None:
    runtime_values = {"n": SymbolDim("N"), "m": 7}
    assert emit_core._resolve_runtime_scalar_value(ConstAST(1), i32, runtime_values) == 1
    assert emit_core._resolve_runtime_scalar_value(ConstAST(1.5), f32, runtime_values) == 1.5
    assert emit_core._resolve_runtime_scalar_value(ConstAST(True), None, runtime_values) is True
    assert emit_core._resolve_runtime_scalar_value(ScalarArgAST("n", int, is_symbolic=True), None, runtime_values) == SymbolDim("N")
    assert emit_core._resolve_runtime_scalar_value(VarAST("m"), emit_core.SymbolValueType.from_expr("M"), runtime_values) == SymbolDim("M")
    assert emit_core._resolve_runtime_scalar_value(object(), IntegerType(32), runtime_values) == 0
    assert emit_core._resolve_runtime_scalar_value(object(), f32, runtime_values) == 0.0
    assert emit_core._resolve_runtime_scalar_value(object(), None, runtime_values) is None

    block, ctx, _ = _symbol_ctx("N", "n")
    assert emit_core._resolve_symbolic_index_value(ConstAST(2), location=None, runtime_values=runtime_values) == 2
    assert emit_core._resolve_symbolic_index_value(ConstAST("N + 1"), location=None, runtime_values=runtime_values).get_value() == "N + 1"
    assert emit_core._resolve_symbolic_index_value(ScalarArgAST("n", int, is_symbolic=True), location=None, runtime_values=runtime_values) == SymbolDim("N")
    assert emit_core._resolve_static_index_expr(ScalarArgAST("n", int, is_symbolic=True), location=None, runtime_values=runtime_values) == "N"
    assert emit_core._resolve_helper_index_param_value("conv", "kw", ScalarArgAST("n", int, is_symbolic=True), None, runtime_values=runtime_values) == "N"
    assert emit_core._helper_index_value_to_symbolic("conv", "kw", SymbolDim("K"), None) == SymbolDim("K")
    assert emit_core._helper_index_value_to_symbolic("conv", "kw", "K", None).get_value() == "K"
    with pytest.raises(emit_core._LoweringError, match="conv kw must be int or symbol"):
        emit_core._helper_index_value_to_symbolic("conv", "kw", object(), None)  # type: ignore[arg-type]

    assert len(emit_core._build_static_index_list(None, 2, default_value=1)) == 2
    assert len(emit_core._build_static_index_attrs_exact([ConstAST(4), "N"], runtime_values=runtime_values)) == 2
    assert len(emit_core._build_index_operands_exact([ConstAST(4), "N"], ctx, location=None)) == 2
    assert emit_core._symbolic_index_sequence([ConstAST(1), "N"], runtime_values=runtime_values)[0] == 1
    assert emit_core._symbolic_index_sequence(ConstAST(1), runtime_values=runtime_values) == [1]


# CORE-006
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证 memory / broadcast / binary / matmul / axis 辅助函数的分支。
# 测试目的: 锁定 shape/stride 转换、broadcast 形状推导与 matmul 校验。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_memory_broadcast_and_axis_helpers
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_memory_broadcast_and_axis_helpers() -> None:
    memory_type = _memory_type([2, 3], stride=[3, 1], element_type=i64, space=MemorySpace.SM)
    runtime_memory = emit_core._nn_memory_type_to_memory(memory_type)
    roundtrip_type = emit_core._memory_to_nn_type(runtime_memory)
    assert roundtrip_type.element_type == i64
    assert list(roundtrip_type.shape.data)[0] == IntAttr(2)
    assert list(roundtrip_type.stride.data) == [IntAttr(3), IntAttr(1)]

    with pytest.raises(emit_core._LoweringError, match="nn.memory shape contains unknown dimension"):
        emit_core._nn_memory_type_to_memory(_memory_type(["?"], stride=[1], element_type=f32))

    assert emit_core._build_dynamic_memory_type(MemorySpace.SM).space.space.data == "shared"
    with pytest.raises(emit_core._LoweringError, match="get_dynamic_memory space must be on-chip MemorySpace"):
        emit_core._build_dynamic_memory_type(MemorySpace.GM)

    assert emit_core._resolve_tensor_axis_index(ConstAST(1), None) == 1
    with pytest.raises(emit_core._LoweringError, match="Tensor axis must be non-negative"):
        emit_core._resolve_tensor_axis_index(ConstAST(-1), None)
    with pytest.raises(emit_core._LoweringError, match="Tensor axis must be static int"):
        emit_core._resolve_tensor_axis_index(ConstAST("N"), None)

    axis_type = _memory_type([4, "N"], stride=["S", 1], element_type=f32, space=MemorySpace.GM)
    axis_tensor = TensorAST("x", Memory([4, 2], NumericType.Float32), location=None)
    axis_type_map = {emit_core._expr_key(axis_tensor): axis_type}
    shape_access = TensorAxisAccessAST(tensor=axis_tensor, kind="shape", axis=ConstAST(1), location=None)
    stride_access = TensorAxisAccessAST(tensor=axis_tensor, kind="stride", axis=ConstAST(0), location=None)
    assert emit_core._infer_tensor_axis_access_type(shape_access, axis_type_map) == emit_core.SymbolValueType.from_expr("N")
    assert emit_core._infer_tensor_axis_access_type(stride_access, axis_type_map) == emit_core.SymbolValueType.from_expr("S")
    with pytest.raises(emit_core._LoweringError, match="Tensor axis out of range"):
        emit_core._infer_tensor_axis_access_type(TensorAxisAccessAST(tensor=axis_tensor, kind="shape", axis=ConstAST(3), location=None), axis_type_map)
    with pytest.raises(emit_core._LoweringError, match="Tensor axis access does not support unknown entry '\\?'"):
        emit_core._infer_tensor_axis_access_type(
            TensorAxisAccessAST(tensor=axis_tensor, kind="shape", axis=ConstAST(0), location=None),
            {emit_core._expr_key(axis_tensor): _memory_type(["?"], stride=[1], element_type=f32)},
        )
    with pytest.raises(emit_core._LoweringError, match="Tensor axis access source must be nn.memory"):
        emit_core._infer_tensor_axis_access_type(
            TensorAxisAccessAST(tensor=axis_tensor, kind="shape", axis=ConstAST(0), location=None),
            {emit_core._expr_key(axis_tensor): i32},
        )

    assert emit_core._infer_img2col_input_format(_memory_type([2, "C", 4])) == emit_core.Farmat.CLast
    assert emit_core._infer_img2col_input_format(_memory_type([2, "H", 4, 3])) == emit_core.Farmat.CLast
    assert emit_core._infer_img2col_input_format(_memory_type([2, 4])) == emit_core.Farmat.Norm
    formatted = emit_core._nn_memory_type_to_memory_with_format(memory_type, emit_core.Farmat.CLast)
    assert formatted.format == emit_core.Farmat.CLast

    lhs_type = _memory_type([1, 4], element_type=i32, space=MemorySpace.GM)
    rhs_type = _memory_type([2, 4], element_type=i32, space=MemorySpace.GM)
    broadcast = emit_core._infer_broadcast_memory_type(lhs_type, rhs_type, None)
    assert [attr.data for attr in broadcast.shape.data] == [2, 4]
    with pytest.raises(emit_core._LoweringError, match="Implicit broadcast dimension mismatch"):
        emit_core._infer_broadcast_shape([IntAttr(2)], [IntAttr(3)], None)
    with pytest.raises(emit_core._LoweringError, match="Binary op operands must have the same space"):
        emit_core._infer_broadcast_memory_type(lhs_type, _memory_type([2, 4], element_type=i32, space=MemorySpace.SM), None)

    assert emit_core._resolve_binary_element_type(i32, i32, None) == i32
    assert emit_core._resolve_binary_element_type(i32, f32, None) == f32
    with pytest.raises(emit_core._LoweringError, match="Binary op operands must have the same element_type"):
        emit_core._resolve_binary_element_type(Float64Type(), f32, None)
    assert emit_core._normalize_add_scalar_element_type(emit_core.SymbolValueType.from_expr("K"), None) == i32
    assert emit_core._normalize_add_scalar_element_type(Float16Type(), None) == Float16Type()
    with pytest.raises(emit_core._LoweringError, match="nn.add scalar element_type must be i32/f16/f32 or symbol.int"):
        emit_core._normalize_add_scalar_element_type(i64, None)

    mixed = emit_core._infer_add_mixed_memory_type(_memory_type([2, 2], element_type=Float16Type()), i32, None)
    assert isinstance(mixed, NnMemoryType)
    binary = emit_core._infer_binary_memory_type(lhs_type, rhs_type, None)
    assert isinstance(binary, NnMemoryType)
    with pytest.raises(emit_core._LoweringError, match="Binary op operands must have the same space"):
        emit_core._infer_binary_memory_type(lhs_type, _memory_type([2, 4], element_type=i32, space=MemorySpace.SM), None)

    matmul = emit_core._infer_matmul_memory_type(
        _memory_type([2, 3], element_type=i32, space=MemorySpace.GM),
        _memory_type([3, 4], element_type=i32, space=MemorySpace.GM),
        None,
        None,
    )
    assert [attr.data for attr in matmul.shape.data] == [2, 4]
    with pytest.raises(emit_core._LoweringError, match="matmul operands must be rank-2 nn.memory"):
        emit_core._infer_matmul_memory_type(
            _memory_type([2, 3, 4], element_type=i32, space=MemorySpace.GM),
            _memory_type([3, 4], element_type=i32, space=MemorySpace.GM),
            None,
            None,
        )
    with pytest.raises(emit_core._LoweringError, match="matmul contracting dimension mismatch"):
        emit_core._infer_matmul_memory_type(
            _memory_type([2, 3], element_type=i32, space=MemorySpace.GM),
            _memory_type([4, 4], element_type=i32, space=MemorySpace.GM),
            None,
            None,
        )


# CORE-007
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证 img2col / conv / reduce / transpose helper 的解析与校验分支。
# 测试目的: 锁定参数默认值、非法参数、输出维度计算与 verifier 前置错误。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_helper_parsing_reduce_and_conv_helpers
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_helper_parsing_reduce_and_conv_helpers() -> None:
    value = TensorAST("value", Memory([4, 4], NumericType.Float32), location=None)
    img2col_1d = Img2ColAST(kind="img2col1d", args=[value, ConstAST(3)], kwargs={}, location=None)
    input_expr, params = emit_core._parse_img2col_helper(img2col_1d)
    assert input_expr is value
    assert params["sw"] == 1 and params["dw"] == 1
    with pytest.raises(emit_core._LoweringError, match="img2col1d got unexpected keyword 'bad'"):
        emit_core._parse_img2col_helper(Img2ColAST(kind="img2col1d", args=[value], kwargs={"bad": 1}, location=None))

    conv_expr = emit_core._parse_conv_helper(ConvAST(value=value, weight=value, kwargs={}, location=None))
    assert conv_expr[0] is value and conv_expr[1] is value
    with pytest.raises(emit_core._LoweringError, match="conv got unexpected keyword 'bad'"):
        emit_core._parse_conv_helper(ConvAST(value=value, weight=value, kwargs={"bad": 1}, location=None))

    emit_core._validate_conv_helper_params({"sh": 1, "sw": 1, "dh": 1, "dw": 1, "ph": 0, "pw": 0, "pl": 0, "pr": 0}, None)
    with pytest.raises(VerifyException, match="sh must be positive"):
        emit_core._validate_conv_helper_params({"sh": 0, "sw": 1, "dh": 1, "dw": 1, "ph": 0, "pw": 0, "pl": 0, "pr": 0}, None)
    with pytest.raises(VerifyException, match="ph must be non-negative"):
        emit_core._validate_conv_helper_params({"sh": 1, "sw": 1, "dh": 1, "dw": 1, "ph": -1, "pw": 0, "pl": 0, "pr": 0}, None)

    assert emit_core._static_kernel_dim(IntAttr(3), "kh", None) == 3
    assert emit_core._static_kernel_dim(StringAttr("K"), "kw", None).get_value() == "K"
    with pytest.raises(VerifyException, match="kh must be positive"):
        emit_core._static_kernel_dim(IntAttr(0), "kh", None)
    with pytest.raises(emit_core._LoweringError, match="conv kh must be int or symbol"):
        emit_core._static_kernel_dim(FloatAttr(1.0, f32), "kh", None)

    assert emit_core._conv_out_dim_value(IntAttr(5), axis_name="height", kernel=3, stride=1, dilation=1, pad_before=1, pad_after=1, location=None) == 5
    assert emit_core._img2col_out_dim_value(IntAttr(8), 3, 1, 1, 1, 1, None) == 8
    with pytest.raises(VerifyException, match="output height must be positive"):
        emit_core._conv_out_dim_value(IntAttr(1), axis_name="height", kernel=3, stride=1, dilation=1, pad_before=0, pad_after=0, location=None)
    assert isinstance(
        emit_core._conv_out_dim_value(StringAttr("H"), axis_name="height", kernel="K", stride="S", dilation="D", pad_before="P1", pad_after="P2", location=None),
        str,
    )
    assert isinstance(emit_core._img2col_out_dim_value(StringAttr("H"), "K", "S", "D", "P1", "P2", None), str)

    assert emit_core._parse_reduce_axis_expr(None, None) is None
    assert emit_core._parse_reduce_axis_expr(ConstAST(1), None) == [1]
    assert emit_core._parse_reduce_axis_expr([ConstAST(1), 2], None) == [1, 2]
    with pytest.raises(emit_core._LoweringError, match="reduce axis must be int"):
        emit_core._parse_reduce_axis_expr(ConstAST("bad"), None)
    assert emit_core._parse_softmax_axis_expr(None, 4, None) == 3
    assert emit_core._parse_softmax_axis_expr(ConstAST(-1), 4, None) == 3
    with pytest.raises(emit_core._LoweringError, match="softmax axis must be int"):
        emit_core._parse_softmax_axis_expr(True, 4, None)
    with pytest.raises(emit_core._LoweringError, match="transpose perm must be list of int"):
        emit_core._parse_transpose_perm_expr(None, None)
    assert emit_core._parse_transpose_perm_expr(ConstAST(1), None) == [1]
    assert emit_core._parse_transpose_perm_expr([ConstAST(1), 0], None) == [1, 0]
    assert emit_core._parse_reduce_keepdim_expr(None, None) == (False, True)
    assert emit_core._parse_reduce_keepdim_expr(ConstAST(True), None) == (True, True)
    assert emit_core._parse_reduce_keepdim_expr(ConstAST(2), None) == (2, False)
    with pytest.raises(emit_core._LoweringError, match="reduce keepdim must be bool or int"):
        emit_core._parse_reduce_keepdim_expr("bad", None)
    assert emit_core._build_reduce_result_shape_attrs([IntAttr(2), IntAttr(3)], {0}, True) == [IntAttr(1), IntAttr(3)]
    assert emit_core._build_reduce_result_shape_attrs([IntAttr(2), IntAttr(3)], {0, 1}, False) == [IntAttr(1)]

    reduce_expr = NnReduceAST(kind="reduce_sum", value=value, axis=[ConstAST(1)], keepdim=ConstAST(False), location=None)
    reduce_type = _memory_type([2, 3], element_type=f32, space=MemorySpace.GM)
    assert [attr.data for attr in emit_core._infer_reduce_output_shape_attrs(reduce_expr, reduce_type)] == [2]
    bad_reduce = NnReduceAST(kind="reduce_sum", value=value, axis=[ConstAST(4)], keepdim=ConstAST(True), location=None)
    assert [attr.data for attr in emit_core._infer_reduce_output_shape_attrs(bad_reduce, reduce_type)] == [2, 3]


# CORE-008
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证 PythonCalleeCallAST、动态 memory 与 mixed binary lowering 的关键分支。
# 测试目的: 锁定 caller registry/compiler、dynamic memory space 与 mixed scalar cast/错误路径。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_python_callee_and_mixed_binary_lowering_paths
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_python_callee_and_mixed_binary_lowering_paths() -> None:
    def callee(value: int) -> int:
        return value

    callee_op = build_func_op(callee, 1)
    calls: list[tuple[object, list[object]]] = []

    def compiler(callee_name: str, arg_types: list[object], location: SourceLocation | None) -> None:
        del location
        calls.append((callee_name, arg_types))

    call_expr = PythonCalleeCallAST(callee="callee", args=[ConstAST(1)], location=None)
    call_ctx = EmitContext(
        builder=Block(),
        symbols={},
        types={},
        config={
            emit_core._MLIR_GEN_CALLEE_REGISTRY_CONFIG_KEY: {"callee": callee_op},
            emit_core._MLIR_GEN_CALLEE_COMPILER_CONFIG_KEY: compiler,
        },
    )
    inferred = emit_core._infer_expr_type(call_expr, call_ctx.types, config=call_ctx.config)
    assert inferred == callee_op.function_type.outputs.data[0]
    result = emit_core._lower_expr(call_expr, call_ctx)
    assert result.type == inferred
    assert len(calls) == 1
    assert any(isinstance(op, func.CallOp) for op in call_ctx.builder.ops)

    bad_registry_ctx = EmitContext(builder=Block(), symbols={}, types={}, config={emit_core._MLIR_GEN_CALLEE_REGISTRY_CONFIG_KEY: []})
    with pytest.raises(emit_core._LoweringError, match="Python callee registry must be dict"):
        emit_core._infer_expr_type(call_expr, bad_registry_ctx.types, config=bad_registry_ctx.config)
    bad_compiler_ctx = EmitContext(
        builder=Block(),
        symbols={},
        types={},
        config={
            emit_core._MLIR_GEN_CALLEE_REGISTRY_CONFIG_KEY: {"callee": callee_op},
            emit_core._MLIR_GEN_CALLEE_COMPILER_CONFIG_KEY: object(),
        },
    )
    with pytest.raises(emit_core._LoweringError, match="Python callee compiler must be callable"):
        emit_core._infer_expr_type(call_expr, bad_compiler_ctx.types, config=bad_compiler_ctx.config)
    missing_ctx = EmitContext(builder=Block(), symbols={}, types={}, config={emit_core._MLIR_GEN_CALLEE_REGISTRY_CONFIG_KEY: {}})
    with pytest.raises(emit_core._LoweringError, match="Python callee is missing from registry"):
        emit_core._infer_expr_type(call_expr, missing_ctx.types, config=missing_ctx.config)

    dyn_type = _memory_type(["N", 4], stride=[4, 1], element_type=f32, space=MemorySpace.GM)
    dyn_block = Block(arg_types=[dyn_type, emit_core.SymbolValueType.from_expr("N")])
    dyn_tensor = TensorAST("x", Memory([2, 4], NumericType.Float32), location=None)
    dyn_ctx = EmitContext(builder=dyn_block, symbols={"x": dyn_block.args[0], "n": dyn_block.args[1]}, types={})
    dyn_ctx._set_cache(emit_core._expr_key(dyn_tensor), dyn_block.args[0])
    dyn_ctx.types[emit_core._expr_key(dyn_tensor)] = dyn_type

    load_result = emit_core._lower_expr(LoadAST(tensor=dyn_tensor, offset=[ConstAST(0), ConstAST(0)], stride=None, location=None), dyn_ctx)
    assert isinstance(load_result.owner, emit_core.DmaAllocOp)
    copy_result = emit_core._lower_expr(DmaCopyAST(source=dyn_tensor, space=MemorySpace.SM, location=None), dyn_ctx)
    assert isinstance(copy_result.owner, emit_core.DmaAllocOp)
    cast_result = emit_core._lower_expr(DmaCastAST(source=dyn_tensor, dtype=NumericType.Float16, memoryspace=MemorySpace.SM, location=None), dyn_ctx)
    assert isinstance(cast_result.owner, emit_core.DmaAllocOp)
    view_result = emit_core._lower_expr(
        DmaViewAST(
            source=dyn_tensor,
            offset=[ConstAST(0), ConstAST(0)],
            size=[ConstAST(1), ConstAST(4)],
            stride=[ConstAST(1), ConstAST(1)],
            location=None,
        ),
        dyn_ctx,
    )
    assert isinstance(view_result.owner, emit_core.DmaViewOp)
    dyn_ctx._cache.clear()
    dyn_ctx._set_cache(emit_core._expr_key(dyn_tensor), dyn_block.args[0])
    reshape_result = emit_core._lower_expr(DmaReshapeAST(source=dyn_tensor, shape=[ConstAST(2), ConstAST(4)], location=None), dyn_ctx)
    assert isinstance(reshape_result.owner, emit_core.DmaReshapeOp)
    flatten_result = emit_core._lower_expr(DmaFlattenAST(source=dyn_tensor, location=None), dyn_ctx)
    assert isinstance(flatten_result.owner, emit_core.DmaReshapeOp)

    dyn_memory = emit_core._lower_expr(ArchGetDynamicMemoryAST(space=MemorySpace.SM, location=None), EmitContext(builder=Block(), symbols={}, types={}))
    assert dyn_memory.type.space.space.data == "shared"
    with pytest.raises(emit_core._LoweringError, match="get_dynamic_memory space must be on-chip MemorySpace"):
        emit_core._infer_expr_type(ArchGetDynamicMemoryAST(space=MemorySpace.GM, location=None), {})

    with pytest.raises(emit_core._LoweringError, match="Unsupported constant type"):
        emit_core._lower_expr(ConstAST("broken"), EmitContext(builder=Block(), symbols={}, types={}))

    with pytest.raises(emit_core._LoweringError, match="Unsupported tensor axis access kind"):
        emit_core._lower_expr(TensorAxisAccessAST(tensor=dyn_tensor, kind="bad", axis=ConstAST(0), location=None), dyn_ctx)

    mixed_memory_type = _memory_type([2, 2], element_type=Float16Type())
    mixed_tensor = TensorAST("mixed", Memory([2, 2], NumericType.Float16), location=None)
    mixed_block = Block(arg_types=[mixed_memory_type])
    mixed_ctx = EmitContext(
        builder=mixed_block,
        symbols={"mixed": mixed_block.args[0]},
        types={emit_core._expr_key(mixed_tensor): mixed_memory_type},
    )
    mixed_ctx._set_cache(emit_core._expr_key(mixed_tensor), mixed_block.args[0])
    rhs_value = emit_core._lower_expr(ConstAST(1), mixed_ctx)
    mixed_expr = BinaryExprAST(op="add", lhs=mixed_tensor, rhs=ConstAST(1), location=None)
    mixed_result = emit_core._lower_mixed_binary_expr(mixed_expr, mixed_block.args[0], rhs_value, mixed_ctx)
    assert mixed_result is not None
    floordiv_expr = BinaryExprAST(op="floordiv", lhs=mixed_tensor, rhs=ConstAST(2), location=None)
    floordiv_result = emit_core._lower_mixed_binary_expr(floordiv_expr, mixed_block.args[0], None, mixed_ctx)
    assert floordiv_result is not None
    with pytest.raises(emit_core._LoweringError, match="nn.add requires at least one nn.memory operand"):
        emit_core._lower_mixed_binary_expr(BinaryExprAST(op="add", lhs=ConstAST(1), rhs=ConstAST(2), location=None), None, None, mixed_ctx)
    with pytest.raises(emit_core._LoweringError, match="Unsupported binary op: mod"):
        emit_core._lower_mixed_binary_expr(BinaryExprAST(op="mod", lhs=mixed_tensor, rhs=ConstAST(1), location=None), mixed_block.args[0], rhs_value, mixed_ctx)


# CORE-009
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证 core.py 公开 lowering 辅助函数的基础表面不回归。
# 测试目的: 锁定 _ensure_supported_statements / _expect_memory_value / _expr_key 等简单分支。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_supported_statements_and_simple_helpers
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_supported_statements_and_simple_helpers() -> None:
    func_ast = FunctionAST("simple", [], [], BlockAST([ConstAST(1)]), returns_none=True)
    assert emit_core._ensure_supported_statements(func_ast) == [ConstAST(1)]
    with pytest.raises(emit_core._LoweringError, match="Function body is empty"):
        emit_core._ensure_supported_statements(FunctionAST("empty", [], [], BlockAST([]), returns_none=True))
    with pytest.raises(emit_core._LoweringError, match="Unsupported AST expression for lowering"):
        emit_core._ensure_supported_statements(FunctionAST("bad", [], [], BlockAST([object()]), returns_none=True))  # type: ignore[list-item]

    memory_type = _memory_type([2, 2], element_type=f32)
    value_block, value_ctx, value = _memory_ctx(memory_type)
    assert emit_core._expect_memory_value(value, None) == memory_type
    with pytest.raises(emit_core._LoweringError, match="Operand must be nn.memory"):
        bad_block = Block(arg_types=[i32])
        emit_core._expect_memory_value(bad_block.args[0], None)
    first_const = ConstAST(1)
    second_const = ConstAST(2)
    assert emit_core._expr_key(first_const) != emit_core._expr_key(second_const)


# CORE-010
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证索引表达式、布局 operand 规整与 flatten/product helper 的分支。
# 测试目的: 锁定纯 helper 路径、符号归一化和基础错误短语。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_symbol_index_and_layout_helper_surfaces
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_symbol_index_and_layout_helper_surfaces() -> None:
    loop_block = Block()
    loop_ctx = EmitContext(builder=loop_block, symbols={}, types={})
    loop_ctx.config = {"loop_vars": {"i": 3}}

    assert emit_core._resolve_index_expr(ConstAST(3), loop_ctx) == 3
    assert emit_core._resolve_index_expr(ScalarArgAST("n", int, is_symbolic=True), loop_ctx) == "n"
    assert emit_core._resolve_index_expr(VarAST("i"), loop_ctx) == 3
    assert emit_core._resolve_index_expr("N + 1", loop_ctx) == "N + 1"
    assert emit_core._resolve_index_expr("N*2", loop_ctx) == "2*N"
    assert emit_core._resolve_index_expr(BinaryExprAST(op="add", lhs=ConstAST(1), rhs=ConstAST(2), location=None), loop_ctx) == 3
    assert emit_core._resolve_index_expr(BinaryExprAST(op="floordiv", lhs=ConstAST(5), rhs=ConstAST(2), location=None), loop_ctx) == 2
    with pytest.raises(emit_core._LoweringError, match="Unsupported index expression"):
        emit_core._resolve_index_expr(BinaryExprAST(op="mod", lhs=ConstAST(1), rhs=ConstAST(2), location=None), loop_ctx)

    sym_block, sym_ctx, sym_value = _symbol_ctx("N", "n")
    layout = ArrayAttr([IntAttr(2), StringAttr("N")])
    layout_values = emit_core._build_index_operands_from_layout(layout, sym_ctx)
    assert len(layout_values) == 2
    assert layout_values[1] is sym_value
    with pytest.raises(emit_core._LoweringError, match="Unsupported layout attribute"):
        emit_core._build_index_operands_from_layout(ArrayAttr([FloatAttr(1.0, f32)]), sym_ctx)

    static_block, static_ctx, static_value = _memory_ctx(_memory_type([2, 3], element_type=f32))
    static_flatten = emit_core._build_flatten_shape_operands(static_value, _memory_type([2, 3], element_type=f32), static_ctx)
    assert len(static_flatten) == 1
    assert isinstance(static_flatten[0].owner, emit_core.SymbolConstOp)
    symbol_block = Block(arg_types=[_memory_type([2, "N"], stride=["N", 1], element_type=f32)])
    symbol_ctx = EmitContext(builder=symbol_block, symbols={"x": symbol_block.args[0]}, types={})
    symbol_flatten = emit_core._build_flatten_shape_operands(symbol_block.args[0], _memory_type([2, "N"], stride=["N", 1], element_type=f32), symbol_ctx)
    assert len(symbol_flatten) == 1
    assert any(isinstance(op, emit_core.SymbolGetDimOp) for op in symbol_block.ops)
    assert any(isinstance(op, emit_core.SymbolMulOp) for op in symbol_block.ops)

    assert emit_core._apply_symbolic_index_binary_op(2, 3, "add", None) == 5
    assert emit_core._apply_symbolic_index_binary_op(5, 3, "sub", None) == 2
    assert isinstance(emit_core._apply_symbolic_index_binary_op(2, "N", "mul", None), SymbolDim)
    assert isinstance(emit_core._apply_symbolic_index_binary_op("N", 2, "div", None), SymbolDim)
    assert isinstance(emit_core._apply_symbolic_index_binary_op("N", 2, "floordiv", None), SymbolDim)
    with pytest.raises(emit_core._LoweringError, match="Unsupported index expression"):
        emit_core._apply_symbolic_index_binary_op(1, 2, "mod", None)
    with pytest.raises(emit_core._LoweringError, match="Unsupported index expression"):
        emit_core._apply_symbolic_index_binary_op(1, 0, "div", None)

    runtime_values = {"n": SymbolDim("N")}
    assert emit_core._resolve_symbolic_index_value(ConstAST(2), location=None, runtime_values=runtime_values) == 2
    assert emit_core._resolve_symbolic_index_value(ConstAST("N + 1"), location=None, runtime_values=runtime_values).get_value() == "N + 1"
    assert emit_core._resolve_symbolic_index_value(ScalarArgAST("n", int, is_symbolic=True), location=None, runtime_values=runtime_values) == SymbolDim("N")
    assert emit_core._resolve_symbolic_index_value(BinaryExprAST(op="add", lhs=ConstAST(1), rhs=ConstAST(2), location=None), location=None, runtime_values=runtime_values) == 3
    with pytest.raises(emit_core._LoweringError, match="Unsupported index expression"):
        emit_core._resolve_symbolic_index_value(object(), location=None, runtime_values=runtime_values)  # type: ignore[arg-type]

    index_block = Block(arg_types=[emit_core.SymbolValueType.from_expr("K"), IntegerType(32), IndexType()])
    index_ctx = EmitContext(builder=index_block, symbols={"sym": index_block.args[0], "i32": index_block.args[1], "idx": index_block.args[2]}, types={})
    assert emit_core._shape_attr_to_symbol_operand(IntAttr(4), index_ctx, location=None).type == emit_core.SymbolValueType.from_expr("4")
    assert emit_core._shape_attr_to_symbol_operand(StringAttr("K"), index_ctx, location=None) is index_block.args[0]
    with pytest.raises(emit_core._LoweringError, match="Unsupported layout attribute"):
        emit_core._shape_attr_to_symbol_operand(StringAttr("?"), index_ctx, location=None)
    with pytest.raises(emit_core._LoweringError, match="Unsupported layout attribute"):
        emit_core._shape_attr_to_symbol_operand(FloatAttr(1.0, f32), index_ctx, location=None)

    assert emit_core._shape_attr_to_helper_index_operand(IntAttr(3), index_ctx, location=None).type == IntegerType(32)
    assert emit_core._shape_attr_to_helper_index_operand(StringAttr("K"), index_ctx, location=None) is index_block.args[0]
    with pytest.raises(emit_core._LoweringError, match="Unsupported layout attribute"):
        emit_core._shape_attr_to_helper_index_operand(FloatAttr(1.0, f32), index_ctx, location=None)

    i32_arg = ScalarArgAST("i32", int, is_symbolic=True)
    sym_arg = ScalarArgAST("sym", int, is_symbolic=True)
    idx_var = VarAST("idx")
    assert emit_core._lower_helper_index_operand(ConstAST(2), index_ctx, location=None).type == IntegerType(32)
    assert emit_core._lower_helper_index_operand(i32_arg, index_ctx, location=None) is index_block.args[1]
    assert emit_core._lower_helper_index_operand(sym_arg, index_ctx, location=None) is index_block.args[0]
    assert emit_core._lower_helper_index_operand(idx_var, index_ctx, location=None).type == IntegerType(32)
    with pytest.raises(emit_core._LoweringError, match="Unsupported index expression"):
        emit_core._lower_helper_index_operand(object(), index_ctx, location=None)  # type: ignore[arg-type]

    product_ctx = EmitContext(builder=Block(), symbols={}, types={})
    left_block, left_ctx, left_value = _symbol_ctx("M", "m")
    right_block, right_ctx, right_value = _symbol_ctx("N", "n")
    product_ctx.builder = Block()
    product = emit_core._build_symbol_product_operand([left_value, right_value], product_ctx, location=None)
    assert isinstance(product.type, emit_core.SymbolValueType)
    with pytest.raises(emit_core._LoweringError, match="Symbol product requires at least one operand"):
        emit_core._build_symbol_product_operand([], product_ctx, location=None)

    img2col_block = Block(arg_types=[_memory_type([2, 3, 4, 5, 6, 7], element_type=f32)])
    img2col_ctx = EmitContext(builder=img2col_block, symbols={"x": img2col_block.args[0]}, types={})
    batch_dim, out_h_dim, out_w_dim = emit_core._build_img2col2d_output_dim_operands(img2col_block.args[0], img2col_ctx)
    assert all(isinstance(value.owner, emit_core.SymbolGetDimOp) for value in (batch_dim, out_h_dim, out_w_dim))

    assert emit_core._memory_space_from_ast(None, NnMemorySpaceAttr.from_name("global")) == NnMemorySpaceAttr.from_name("global")


# CORE-S7-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 补齐 core helper 在符号表达式、barrier 和 stride 校验上的剩余边角。
# 测试目的: 锁定 `_eval_symbolic_dim_node`、`_build_arch_barrier_visibility_attr`、`_build_stride_attrs` 和 `_conv_out_dim_value` 的少量漏测分支。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_emit_core_private_s7_helper_topoff_edges
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_emit_core_private_s7_helper_topoff_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    original_eval_symbolic_dim_node = emit_core._eval_symbolic_dim_node

    def _patched_eval_symbolic_dim_node(node: object, location: SourceLocation | None) -> object:
        if isinstance(node, py_ast.Name) and node.id == "bad":
            return object()
        return original_eval_symbolic_dim_node(node, location)

    monkeypatch.setattr(emit_core, "_eval_symbolic_dim_node", _patched_eval_symbolic_dim_node)
    with pytest.raises(emit_core._LoweringError, match="Unsupported symbolic dim expression"):
        original_eval_symbolic_dim_node(py_ast.parse("-bad", mode="eval").body, None)

    with pytest.raises(emit_core._LoweringError, match="barrier visibility must be non-empty BarrierVisibility list"):
        emit_core._build_arch_barrier_visibility_attr([object()], None)

    two_constant = arith.ConstantOp.from_int_and_width(2, 32)
    monkeypatch.setattr(emit_core, "_build_index_attrs", lambda *_args, **_kwargs: [two_constant.result])
    with pytest.raises(emit_core._LoweringError, match="Only unit stride is supported"):
        emit_core._build_stride_attrs([ConstAST(2)], 1, EmitContext(builder=Block(), symbols={}, types={}))

    monkeypatch.setattr(emit_core.SymbolDim, "get_value", lambda self: 0)
    with pytest.raises(VerifyException, match="output height must be positive"):
        emit_core._conv_out_dim_value(
            StringAttr("H"),
            axis_name="height",
            kernel=1,
            stride=1,
            dilation=1,
            pad_before=0,
            pad_after=0,
            location=None,
        )

    loop_var = VarAST("loop")
    assert emit_core._infer_expr_type(loop_var, {emit_core._expr_key(loop_var): i32}) == i32


# CORE-S7-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 补齐 core lowering 在 mixed binary、conv、img2col、dynamic memory 与 store 上的剩余回退分支。
# 测试目的: 锁定 emit 阶段少量只能通过 monkeypatch 进入的异常路径，确保诊断文案稳定。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_emit_core_private_s7_lowering_topoff_edges
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_emit_core_private_s7_lowering_topoff_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    tensor = TensorAST(name="x", memory=Memory([2], NumericType.Float32), location=None)
    tensor_type = _memory_type([2], stride=[1], element_type=f32)
    mixed_block = Block(arg_types=[tensor_type])
    mixed_ctx = EmitContext(
        builder=mixed_block,
        symbols={"x": mixed_block.args[0]},
        types={emit_core._expr_key(tensor): tensor_type},
    )
    mixed_ctx._set_cache(emit_core._expr_key(tensor), mixed_block.args[0])
    mixed_expr = BinaryExprAST(op="pow", lhs=tensor, rhs=ConstAST(2), location=None)
    mixed_ctx.types[emit_core._expr_key(mixed_expr)] = tensor_type
    mixed_rhs = emit_core._lower_expr(ConstAST(2), mixed_ctx)
    with pytest.raises(emit_core._LoweringError, match="Unsupported binary op: pow"):
        emit_core._lower_mixed_binary_expr(mixed_expr, mixed_block.args[0], mixed_rhs, mixed_ctx)

    value = TensorAST(name="value", memory=Memory([1, 1, 4, 4], NumericType.Float32), location=None)
    weight = TensorAST(name="weight", memory=Memory([1, 1, 3, 3], NumericType.Float32), location=None)
    value_type = _memory_type([1, 1, 4, 4], stride=[16, 16, 4, 1], element_type=f32)
    weight_type = _memory_type([1, 1, 3, "KW"], stride=[3, 3, 1, 1], element_type=f32)
    conv_expr = ConvAST(value=value, weight=weight, kwargs={}, location=None)
    conv_result_type = _memory_type([1, 1, 2, 2], stride=[4, 4, 2, 1], element_type=f32)
    conv_block = Block(arg_types=[value_type, weight_type])
    conv_ctx = EmitContext(
        builder=conv_block,
        symbols={"value": conv_block.args[0], "weight": conv_block.args[1]},
        types={
            emit_core._expr_key(value): value_type,
            emit_core._expr_key(weight): weight_type,
            emit_core._expr_key(conv_expr): conv_result_type,
        },
    )
    conv_ctx._set_cache(emit_core._expr_key(value), conv_block.args[0])
    conv_ctx._set_cache(emit_core._expr_key(weight), conv_block.args[1])
    kw_attr = weight_type.shape.data[3]
    original_shape_attr_to_symbol_dim = emit_core._shape_attr_to_symbol_dim
    monkeypatch.setattr(
        emit_core,
        "_shape_attr_to_symbol_dim",
        lambda attr, location: None if attr == kw_attr else original_shape_attr_to_symbol_dim(attr, location),
    )
    with pytest.raises(emit_core._LoweringError, match="conv kh/kw must be int or symbol"):
        emit_core._lower_expr(conv_expr, conv_ctx)

    img2col_expr = Img2ColAST(kind="img2colX", args=[tensor], kwargs={}, location=None)
    img2col_block = Block(arg_types=[tensor_type])
    img2col_ctx = EmitContext(
        builder=img2col_block,
        symbols={"x": img2col_block.args[0]},
        types={emit_core._expr_key(tensor): tensor_type, emit_core._expr_key(img2col_expr): tensor_type},
    )
    img2col_ctx._set_cache(emit_core._expr_key(tensor), img2col_block.args[0])
    monkeypatch.setattr(emit_core, "_parse_img2col_helper", lambda _expr: (tensor, {}))
    with pytest.raises(emit_core._LoweringError, match="Unsupported img2col helper"):
        emit_core._lower_expr(img2col_expr, img2col_ctx)

    monkeypatch.setattr(emit_core, "_build_dynamic_memory_type", lambda *_args, **_kwargs: tensor_type)
    with pytest.raises(emit_core._LoweringError, match="get_dynamic_memory space must be on-chip MemorySpace"):
        emit_core._lower_expr(
            ArchGetDynamicMemoryAST(space=MemorySpace.GM, location=None),
            EmitContext(builder=Block(), symbols={}, types={}),
        )

    source = TensorAST(name="source", memory=Memory([2], NumericType.Float32), location=None)
    target = TensorAST(name="target", memory=Memory([2, 2], NumericType.Float32), location=None)
    source_type = _memory_type([2], stride=[1], element_type=f32)
    target_type = _memory_type([2, 2], stride=[2, 1], element_type=f32)
    store_expr = StoreAST(
        tensor=target,
        value=source,
        offset=[ConstAST(0), ConstAST(0)],
        sizes=None,
        stride=None,
        kind="store",
        location=None,
    )
    store_block = Block(arg_types=[target_type, source_type])
    store_ctx = EmitContext(
        builder=store_block,
        symbols={"target": store_block.args[0], "source": store_block.args[1]},
        types={emit_core._expr_key(target): target_type, emit_core._expr_key(source): source_type},
    )
    store_ctx._set_cache(emit_core._expr_key(target), store_block.args[0])
    store_ctx._set_cache(emit_core._expr_key(source), store_block.args[1])
    monkeypatch.setattr(emit_core._KG_OPERATION_DMA, "store", lambda *_args, **_kwargs: None)
    with pytest.raises(emit_core._LoweringError, match="Store source rank mismatch"):
        emit_core.emit_mlir(store_expr, store_ctx)
    assert emit_core._memory_space_from_ast(MemorySpace.SM, NnMemorySpaceAttr.from_name("global")) == NnMemorySpaceAttr.from_name("shared")
    assert emit_core._dims_equal(IntAttr(2), IntAttr(2))
    assert not emit_core._dims_equal(IntAttr(2), IntAttr(3))
    assert emit_core._dims_equal(StringAttr("N"), StringAttr("N"))
    assert not emit_core._dims_equal(StringAttr("N"), StringAttr("M"))
    assert emit_core._infer_broadcast_shape([IntAttr(1), IntAttr(4)], [IntAttr(2), IntAttr(4)], None) == [IntAttr(2), IntAttr(4)]
    with pytest.raises(emit_core._LoweringError, match="Implicit broadcast dimension mismatch"):
        emit_core._infer_broadcast_shape([StringAttr("?")], [IntAttr(2)], None)


# CORE-011
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证 broadcast / dtype 决议 / helper 参数解析 / conv img2col shape 推导分支。
# 测试目的: 锁定 nn 类型 promotion、参数规整和结构化 helper 推导的关键路径。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_type_resolution_and_helper_param_surfaces
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_type_resolution_and_helper_param_surfaces() -> None:
    lhs_type = _memory_type([1, 4], element_type=i32, space=MemorySpace.GM)
    rhs_type = _memory_type([2, 4], element_type=f32, space=MemorySpace.GM)
    broadcast_type = emit_core._infer_broadcast_memory_type(lhs_type, rhs_type, None, element_type=f32)
    assert broadcast_type.element_type == f32
    assert [attr.data for attr in broadcast_type.shape.data] == [2, 4]
    with pytest.raises(emit_core._LoweringError, match="Binary op operands must have the same element_type"):
        emit_core._infer_broadcast_memory_type(lhs_type, rhs_type, None)
    with pytest.raises(emit_core._LoweringError, match="Binary op operands must have the same space"):
        emit_core._infer_broadcast_memory_type(lhs_type, _memory_type([2, 4], element_type=i32, space=MemorySpace.SM), None)

    assert emit_core._resolve_binary_element_type(i32, f32, None) == f32
    assert emit_core._resolve_binary_element_type(Float16Type(), i32, None) == Float16Type()
    with pytest.raises(emit_core._LoweringError, match="Binary op operands must have the same element_type"):
        emit_core._resolve_binary_element_type(StringAttr("bad"), f32, None)

    assert emit_core._normalize_add_scalar_element_type(emit_core.SymbolValueType.from_expr("K"), None) == i32
    assert emit_core._normalize_add_scalar_element_type(Float16Type(), None) == Float16Type()
    assert emit_core._normalize_add_scalar_element_type(f32, None) == f32
    with pytest.raises(emit_core._LoweringError, match="nn.add scalar element_type must be i32/f16/f32 or symbol.int"):
        emit_core._normalize_add_scalar_element_type(i64, None)

    mixed_type = emit_core._infer_add_mixed_memory_type(_memory_type([2, 2], element_type=Float16Type()), i32, None)
    assert mixed_type.element_type == Float16Type()
    assert isinstance(mixed_type, NnMemoryType)
    binary_type = emit_core._infer_binary_memory_type(lhs_type, _memory_type([1, 4], element_type=f32, space=MemorySpace.GM), None)
    assert binary_type.element_type == f32
    with pytest.raises(emit_core._LoweringError, match="Binary op operands must have the same space"):
        emit_core._infer_binary_memory_type(lhs_type, _memory_type([2, 4], element_type=f32, space=MemorySpace.SM), None)

    matmul_type = emit_core._infer_matmul_memory_type(
        _memory_type([2, 3], element_type=i32, space=MemorySpace.GM),
        _memory_type([3, 4], element_type=i32, space=MemorySpace.GM),
        None,
        None,
    )
    assert [attr.data for attr in matmul_type.shape.data] == [2, 4]
    with pytest.raises(emit_core._LoweringError, match="matmul operands must be rank-2 nn.memory"):
        emit_core._infer_matmul_memory_type(
            _memory_type([2, 3, 4], element_type=i32, space=MemorySpace.GM),
            _memory_type([3, 4], element_type=i32, space=MemorySpace.GM),
            None,
            None,
        )
    with pytest.raises(emit_core._LoweringError, match="matmul contracting dimension mismatch"):
        emit_core._infer_matmul_memory_type(
            _memory_type([2, 3], element_type=i32, space=MemorySpace.GM),
            _memory_type([4, 4], element_type=i32, space=MemorySpace.GM),
            None,
            None,
        )

    helper_value = TensorAST("helper", Memory([4, 4], NumericType.Float32), location=None)
    helper_expr = Img2ColAST(kind="img2col2d", args=[helper_value], kwargs={}, location=None)
    helper_input_type = _memory_type([2, 3, "H", 4], stride=[24, 12, "S", 1], element_type=f32)
    helper_params = {"kh": 3, "kw": 3, "sh": 1, "sw": 1, "dh": 1, "dw": 1, "ph": 0, "pw": 0, "pl": 0, "pr": 0}
    helper_shape = emit_core._infer_img2col_output_shape_attrs(helper_expr, helper_input_type, helper_params)
    assert len(helper_shape) == 6

    conv_value = TensorAST("conv_value", Memory([1, 3, 4, 4], NumericType.Float32), location=None)
    conv_weight = TensorAST("conv_weight", Memory([2, 3, 3, 3], NumericType.Float32), location=None)
    conv_expr = ConvAST(value=conv_value, weight=conv_weight, kwargs={}, location=None)
    conv_value_type = _memory_type([1, 3, 4, 4], element_type=f32, space=MemorySpace.GM)
    conv_weight_type = _memory_type([2, 3, 3, 3], element_type=f32, space=MemorySpace.GM)
    conv_result = emit_core._infer_conv_memory_type(conv_expr, conv_value_type, conv_weight_type)
    assert conv_result.element_type == f32
    assert len(conv_result.shape.data) == 4

    assert emit_core._resolve_helper_index_param(
        op_name="img2col2d",
        param_name="kw",
        value=ConstAST(3),
        location=None,
        runtime_values=None,
        allow_zero=False,
    ) == 3
    assert emit_core._resolve_helper_index_param(
        op_name="img2col2d",
        param_name="kw",
        value=SymbolDim("KW"),
        location=None,
        runtime_values=None,
        allow_zero=False,
    ) == SymbolDim("KW")
    with pytest.raises(emit_core._LoweringError, match="must be positive"):
        emit_core._resolve_helper_index_param(
            op_name="img2col2d",
            param_name="kw",
            value=ConstAST(0),
            location=None,
            runtime_values=None,
            allow_zero=False,
        )
    with pytest.raises(emit_core._LoweringError, match="must be non-negative"):
        emit_core._resolve_helper_index_param(
            op_name="img2col2d",
            param_name="pl",
            value=ConstAST(-1),
            location=None,
            runtime_values=None,
            allow_zero=True,
        )

    img2col_expr = Img2ColAST(kind="img2col1d", args=[helper_value], kwargs={}, location=None)
    resolved_img2col = emit_core._resolve_img2col_param_values(
        img2col_expr,
        {"kw": ConstAST(3), "sw": SymbolDim("SW"), "dw": 1, "pl": 0, "pr": 2},
        runtime_values=None,
    )
    assert resolved_img2col["kw"] == 3
    assert resolved_img2col["sw"] == SymbolDim("SW")
    conv_resolved = emit_core._resolve_conv_param_values(
        conv_expr,
        {"sh": ConstAST(1), "sw": SymbolDim("SW"), "dh": 1, "dw": 1, "ph": 0, "pw": 0, "pl": 0, "pr": 0},
        runtime_values=None,
    )
    assert conv_resolved["sw"] == SymbolDim("SW")


# CORE-012
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证 arch barrier / launch lowering 与 extent 归一化边界。
# 测试目的: 锁定 barrier visibility/scope 属性、launch extent 的 numeric-string 分支与 statement lowering。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_barrier_and_launch_statement_lowering_paths
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_barrier_and_launch_statement_lowering_paths() -> None:
    visibility = emit_core._build_arch_barrier_visibility_attr(
        [BarrierVisibility.TSM, BarrierVisibility.TLM],
        None,
    )
    assert list(visibility.data) == [
        emit_core.ArchVisibilityAttr.from_name("tsm"),
        emit_core.ArchVisibilityAttr.from_name("tlm"),
    ]
    assert emit_core._build_arch_barrier_scope_attr(BarrierScope.BLOCK, None) == emit_core.ArchScopeAttr.from_name("block")
    with pytest.raises(emit_core._LoweringError, match="barrier visibility must be non-empty BarrierVisibility list"):
        emit_core._build_arch_barrier_visibility_attr([], None)
    with pytest.raises(emit_core._LoweringError, match="barrier scope must be BarrierScope"):
        emit_core._build_arch_barrier_scope_attr("block", None)  # type: ignore[arg-type]

    numeric_block, numeric_ctx, numeric_value = _symbol_ctx("4", "block")
    assert numeric_block.args[0] is numeric_value
    numeric_ctx._set_cache(emit_core._expr_key(ScalarArgAST("block", int, is_symbolic=True)), numeric_value)
    assert emit_core._lower_launch_extent_symbol(
        ScalarArgAST("block", int, is_symbolic=True),
        "block",
        numeric_ctx,
        None,
    ) is numeric_value
    zero_block, zero_ctx, zero_value = _symbol_ctx("0", "shared_memory_size")
    assert zero_block.args[0] is zero_value
    zero_ctx._set_cache(
        emit_core._expr_key(ScalarArgAST("shared_memory_size", int, is_symbolic=True)),
        zero_value,
    )
    assert emit_core._lower_launch_extent_symbol(
        ScalarArgAST("shared_memory_size", int, is_symbolic=True),
        "shared_memory_size",
        zero_ctx,
        None,
        allow_zero=True,
    ) is zero_value
    with pytest.raises(emit_core._LoweringError, match="launch_kernel block must be > 0"):
        emit_core._lower_launch_extent_symbol(ConstAST(0), "block", numeric_ctx, None)

    with pytest.raises(emit_core._LoweringError, match="barrier does not produce a value"):
        emit_core._infer_expr_type(
            ArchBarrierAST(visibility=[BarrierVisibility.TSM], scope=BarrierScope.BLOCK),
            {},
        )
    with pytest.raises(emit_core._LoweringError, match="launch_kernel does not produce a value"):
        emit_core._infer_expr_type(
            ArchLaunchKernelAST(
                callee="kernel_body",
                block=ConstAST(1),
                thread=ConstAST(1),
                subthread=ConstAST(1),
                args=[],
                shared_memory_size=ConstAST(0),
            ),
            {},
        )

    barrier_block = Block()
    barrier_ctx = EmitContext(builder=barrier_block, symbols={}, types={})
    barrier_op = emit_mlir(
        ArchBarrierAST(
            visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM],
            scope=BarrierScope.THREAD,
            location=None,
        ),
        barrier_ctx,
    )
    assert isinstance(barrier_op, emit_core.ArchBarrierOp)
    assert list(barrier_block.ops)[-1] is barrier_op
    assert list(barrier_op.visibility.data) == [
        emit_core.ArchVisibilityAttr.from_name("tsm"),
        emit_core.ArchVisibilityAttr.from_name("tlm"),
    ]
    assert barrier_op.scope == emit_core.ArchScopeAttr.from_name("thread")
    with pytest.raises(emit_core._LoweringError, match="barrier visibility must be non-empty BarrierVisibility list"):
        emit_mlir(ArchBarrierAST(visibility=[], scope=BarrierScope.THREAD, location=None), barrier_ctx)
    with pytest.raises(emit_core._LoweringError, match="barrier scope must be BarrierScope"):
        emit_mlir(
            ArchBarrierAST(visibility=[BarrierVisibility.TSM], scope="thread", location=None),  # type: ignore[arg-type]
            barrier_ctx,
        )

    launch_type = _memory_type([2, 4], element_type=f32)
    launch_tensor = TensorAST("lhs", Memory([2, 4], NumericType.Float32), location=None)
    launch_block = Block(arg_types=[launch_type])
    launch_ctx = EmitContext(
        builder=launch_block,
        symbols={"lhs": launch_block.args[0]},
        types={emit_core._expr_key(launch_tensor): launch_type},
    )
    launch_ctx._set_cache(emit_core._expr_key(launch_tensor), launch_block.args[0])
    launch_op = emit_mlir(
        ArchLaunchKernelAST(
            callee="kernel_body",
            block=ConstAST(2),
            thread=ConstAST(3),
            subthread=ConstAST(1),
            args=[launch_tensor],
            shared_memory_size=ConstAST(0),
            location=None,
        ),
        launch_ctx,
    )
    assert isinstance(launch_op, emit_core.ArchLaunchKernelOp)
    assert list(launch_block.ops)[-1] is launch_op
    assert launch_op.callee == SymbolRefAttr("kernel_body")
    assert launch_op.block.type == emit_core.SymbolValueType.from_expr("2")
    assert launch_op.thread.type == emit_core.SymbolValueType.from_expr("3")
    assert launch_op.subthread.type == emit_core.SymbolValueType.from_expr("1")
    assert launch_op.shared_memory_size.type == emit_core.SymbolValueType.from_expr("0")
    assert len(tuple(launch_op.args)) == 1
    with pytest.raises(emit_core._LoweringError, match="launch_kernel callee must be function symbol reference"):
        emit_mlir(
            ArchLaunchKernelAST(
                callee="",
                block=ConstAST(1),
                thread=ConstAST(1),
                subthread=ConstAST(1),
                args=[],
                shared_memory_size=ConstAST(0),
                location=None,
            ),
            launch_ctx,
        )
    with pytest.raises(emit_core._LoweringError, match="launch_kernel block must be > 0"):
        emit_mlir(
            ArchLaunchKernelAST(
                callee="kernel_body",
                block=ConstAST(0),
                thread=ConstAST(1),
                subthread=ConstAST(1),
                args=[],
                shared_memory_size=ConstAST(0),
                location=None,
            ),
            launch_ctx,
        )


# CORE-013
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证 symbolic index 算术、文本物化与乘法链路的边界分支。
# 测试目的: 锁定 _build_symbol_index_result / _lower_symbolic_index_text / _resolve_index_symbol_product 的完整分支。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_symbolic_index_text_and_arithmetic_branches
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_symbolic_index_text_and_arithmetic_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    symbol_block = Block(arg_types=[emit_core.SymbolValueType.from_expr("M"), emit_core.SymbolValueType.from_expr("N")])
    symbol_ctx = EmitContext(
        builder=symbol_block,
        symbols={"M": symbol_block.args[0], "N": symbol_block.args[1]},
        types={},
    )
    lhs = symbol_block.args[0]
    rhs = symbol_block.args[1]

    for op_symbol in ("+", "-", "*", "/", "//"):
        result = emit_core._build_symbol_index_result(lhs, rhs, op_symbol, symbol_ctx, None)
        assert isinstance(result.type, emit_core.SymbolValueType)
    monkeypatch.setattr(emit_core, "build_public_symbol_expr", lambda lhs_expr, rhs_expr, op_symbol: f"{lhs_expr} + {rhs_expr}")
    with pytest.raises(emit_core._LoweringError, match="Unsupported index expression"):
        emit_core._build_symbol_index_result(lhs, rhs, "%", symbol_ctx, None)

    const_cache: dict[int, object] = {}
    unary = emit_core._lower_symbolic_index_text("-M", symbol_ctx, None, const_cache)
    multiplied = emit_core._lower_symbolic_index_text("M*N", symbol_ctx, None, const_cache)
    assert isinstance(unary.type, emit_core.SymbolValueType)
    assert isinstance(multiplied.type, emit_core.SymbolValueType)
    assert emit_core._resolve_index_symbol_product("M", symbol_ctx, None) is lhs
    assert emit_core._split_symbol_multiplication("M*N*K") == ["M", "N", "K"]
    with pytest.raises(emit_core._LoweringError, match="Unsupported index expression"):
        emit_core._lower_symbolic_index_text("M % N", symbol_ctx, None, const_cache)


# CORE-013A
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证 _const_index / _cast_to_symbol_int / _preload_symbolic_index_constants / _lower_symbolic_index_node 的剩余分支。
# 测试目的: 锁定 index 常量、symbol.cast、字符串预热与符号索引 AST 物化的边界行为。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_symbolic_index_node_preload_and_cast_edges
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_symbolic_index_node_preload_and_cast_edges() -> None:
    index_block = Block(arg_types=[IndexType(), IntegerType(32), emit_core.SymbolValueType.from_expr("M"), f32])
    index_ctx = EmitContext(builder=index_block, symbols={"idx": index_block.args[0], "i32": index_block.args[1], "sym": index_block.args[2], "flt": index_block.args[3]}, types={})

    const_index = emit_core._const_index(4, index_ctx)
    assert const_index.type == IndexType()

    assert emit_core._cast_to_symbol_int(index_block.args[0], index_ctx, "M", None).type == emit_core.SymbolValueType.from_expr("M")
    assert emit_core._cast_to_symbol_int(index_block.args[2], index_ctx, "M", None) is index_block.args[2]
    with pytest.raises(emit_core._LoweringError, match="Index operand must be integer or index"):
        emit_core._cast_to_symbol_int(index_block.args[3], index_ctx, "M", None)

    preload_ctx = EmitContext(builder=Block(), symbols={}, types={})
    const_cache: dict[int, object] = {}
    emit_core._preload_symbolic_index_constants("-1 + (2 * 3)", preload_ctx, None, const_cache)
    assert len(const_cache) >= 3
    assert len(preload_ctx.builder.ops) >= 3
    emit_core._preload_symbolic_index_constants("M +", preload_ctx, None, const_cache)

    symbol_block = Block(arg_types=[emit_core.SymbolValueType.from_expr("M")])
    symbol_ctx = EmitContext(builder=symbol_block, symbols={"M": symbol_block.args[0]}, types={})
    parsed = py_ast.parse("-M // 2", mode="eval").body
    lowered = emit_core._lower_symbolic_index_node(parsed, symbol_ctx, None, {})
    assert isinstance(lowered.type, emit_core.SymbolValueType)
    assert hasattr(emit_core._lower_symbolic_index_node(py_ast.parse("1", mode="eval").body, symbol_ctx, None, {}), "type")
    with pytest.raises(emit_core._LoweringError, match="Unsupported index expression"):
        emit_core._lower_symbolic_index_node(py_ast.parse("M % 2", mode="eval").body, symbol_ctx, None, {})


# CORE-014
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证 nn helper lowering 的 broadcast / transpose / reduce / softmax 分支。
# 测试目的: 锁定 emit_mlir 对 nn family 的类型推导、成功 lowering 与失败路径。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_nn_family_lowering_branches
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_nn_family_lowering_branches() -> None:
    lhs_type = _memory_type([1, 4], element_type=f32)
    rhs_type = _memory_type([2, 4], element_type=f32)
    transpose_type = _memory_type([4, 2], element_type=f32)
    reduce_type = _memory_type([2, 3], element_type=f32)
    softmax_type = _memory_type([2, 3], element_type=f32)
    broadcast_block = Block(arg_types=[lhs_type, rhs_type, transpose_type, reduce_type, softmax_type])
    lhs_tensor = TensorAST("lhs", Memory([1, 4], NumericType.Float32), location=None)
    rhs_tensor = TensorAST("rhs", Memory([2, 4], NumericType.Float32), location=None)
    transpose_tensor = TensorAST("transpose", Memory([4, 2], NumericType.Float32), location=None)
    reduce_tensor = TensorAST("reduce", Memory([2, 3], NumericType.Float32), location=None)
    softmax_tensor = TensorAST("softmax", Memory([2, 3], NumericType.Float32), location=None)
    broadcast_ctx = EmitContext(
        builder=broadcast_block,
        symbols={
            "lhs": broadcast_block.args[0],
            "rhs": broadcast_block.args[1],
            "transpose": broadcast_block.args[2],
            "reduce": broadcast_block.args[3],
            "softmax": broadcast_block.args[4],
        },
        types={
            emit_core._expr_key(lhs_tensor): lhs_type,
            emit_core._expr_key(rhs_tensor): rhs_type,
            emit_core._expr_key(transpose_tensor): transpose_type,
            emit_core._expr_key(reduce_tensor): reduce_type,
            emit_core._expr_key(softmax_tensor): softmax_type,
        },
    )
    for tensor, value in (
        (lhs_tensor, broadcast_block.args[0]),
        (rhs_tensor, broadcast_block.args[1]),
        (transpose_tensor, broadcast_block.args[2]),
        (reduce_tensor, broadcast_block.args[3]),
        (softmax_tensor, broadcast_block.args[4]),
    ):
        broadcast_ctx._set_cache(emit_core._expr_key(tensor), value)

    broadcast_expr = NnBroadcastAST(value=lhs_tensor, target=rhs_tensor, location=None)
    broadcast_op = emit_mlir(broadcast_expr, broadcast_ctx)
    assert isinstance(broadcast_op.owner, emit_core.NnBroadcastOp)
    assert list(broadcast_block.ops)[-1] is broadcast_op.owner
    assert broadcast_op.type == rhs_type
    bad_broadcast_value = ConstAST(1)
    with pytest.raises(emit_core._LoweringError, match="broadcast operands must be nn.memory"):
        emit_mlir(NnBroadcastAST(value=bad_broadcast_value, target=rhs_tensor, location=None), broadcast_ctx)

    broadcast_to_shape = [ConstAST(2), ConstAST(4)]
    broadcast_to_expr = NnBroadcastToAST(
        source=lhs_tensor,
        target_shape=broadcast_to_shape,
        space=MemorySpace.SM,
        location=None,
    )
    broadcast_to_op = emit_mlir(broadcast_to_expr, broadcast_ctx)
    assert isinstance(broadcast_to_op.owner, emit_core.NnBroadcastOp)
    assert list(broadcast_block.ops)[-1] is broadcast_to_op.owner
    bad_broadcast_to_source = ConstAST(1)
    bad_broadcast_to_shape = [ConstAST(2)]
    with pytest.raises(emit_core._LoweringError, match="broadcast_to source must be nn.memory"):
        emit_mlir(
            NnBroadcastToAST(
                source=bad_broadcast_to_source,
                target_shape=bad_broadcast_to_shape,
                space=MemorySpace.SM,
                location=None,
            ),
            broadcast_ctx,
        )
    broadcast_ctx.config = {"__runtime_values__": {"q": SymbolDim("?")}}
    with pytest.raises(emit_core._LoweringError, match="broadcast_to target_shape contains unknown dimension"):
        emit_mlir(
            NnBroadcastToAST(
                source=lhs_tensor,
                target_shape=[ScalarArgAST("q", int, is_symbolic=True)],
                space=MemorySpace.SM,
                location=None,
            ),
            broadcast_ctx,
        )

    post_block = Block(arg_types=[transpose_type, reduce_type, softmax_type])
    post_ctx = EmitContext(
        builder=post_block,
        symbols={
            "transpose": post_block.args[0],
            "reduce": post_block.args[1],
            "softmax": post_block.args[2],
        },
        types={
            emit_core._expr_key(transpose_tensor): transpose_type,
            emit_core._expr_key(reduce_tensor): reduce_type,
            emit_core._expr_key(softmax_tensor): softmax_type,
        },
    )
    for tensor, value in (
        (transpose_tensor, post_block.args[0]),
        (reduce_tensor, post_block.args[1]),
        (softmax_tensor, post_block.args[2]),
    ):
        post_ctx._set_cache(emit_core._expr_key(tensor), value)

    transpose_expr = NnTransposeAST(value=transpose_tensor, perm=[ConstAST(1), ConstAST(0)], location=None)
    transpose_op = emit_mlir(transpose_expr, post_ctx)
    assert isinstance(transpose_op.owner, emit_core.NnTransposeOp)
    assert list(post_block.ops)[-1] is transpose_op.owner

    reduce_sum_expr = NnReduceAST(kind="reduce_sum", value=reduce_tensor, axis=[ConstAST(1)], keepdim=ConstAST(False), location=None)
    reduce_min_expr = NnReduceAST(kind="reduce_min", value=reduce_tensor, axis=[ConstAST(1)], keepdim=ConstAST(True), location=None)
    reduce_max_expr = NnReduceAST(kind="reduce_max", value=reduce_tensor, axis=None, keepdim=None, location=None)
    reduce_sum = emit_mlir(reduce_sum_expr, post_ctx)
    reduce_min = emit_mlir(reduce_min_expr, post_ctx)
    reduce_max = emit_mlir(reduce_max_expr, post_ctx)
    assert isinstance(reduce_sum.owner, emit_core.NnReduceSumOp)
    assert isinstance(reduce_min.owner, emit_core.NnReduceMinOp)
    assert isinstance(reduce_max.owner, emit_core.NnReduceMaxOp)
    with pytest.raises(emit_core._LoweringError, match="Unsupported reduce helper"):
        emit_mlir(
            NnReduceAST(kind="reduce_mean", value=reduce_tensor, axis=[ConstAST(1)], keepdim=None, location=None),
            post_ctx,
        )

    softmax_expr = NnSoftmaxAST(value=softmax_tensor, axis=ConstAST(-1), location=None)
    softmax_op = emit_mlir(softmax_expr, post_ctx)
    assert isinstance(softmax_op.owner, emit_core.NnSoftmaxOp)
    assert list(post_block.ops)[-1] is softmax_op.owner
    with pytest.raises(emit_core._LoweringError, match="softmax input must be nn.memory"):
        emit_mlir(NnSoftmaxAST(value=ConstAST(1), axis=None, location=None), post_ctx)


# CORE-015
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证 core.py 其余类型推导错误分支与 Python callee 多返回保护。
# 测试目的: 补齐 Python callee、dma.alloc/copy/cast/view/reshape/flatten、nn/conv/fc/matmul、statement helper 的错误路径。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_remaining_infer_expr_type_error_branches
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_remaining_infer_expr_type_error_branches() -> None:
    callee_block = Block(arg_types=[i32])
    callee_block.add_op(func.ReturnOp(callee_block.args[0], callee_block.args[0]))
    multi_return_callee = func.FuncOp("multi_return", ([i32], [i32, i32]), Region(callee_block))
    callee_expr = PythonCalleeCallAST(callee="multi_return", args=[ConstAST(1)], location=None)
    callee_ctx = EmitContext(
        builder=Block(),
        symbols={},
        types={},
        config={
            emit_core._MLIR_GEN_CALLEE_REGISTRY_CONFIG_KEY: {"multi_return": multi_return_callee},
            emit_core._MLIR_GEN_CALLEE_COMPILER_CONFIG_KEY: lambda callee_name, arg_types, location: None,
        },
    )
    with pytest.raises(emit_core._LoweringError, match="Python callee must return exactly one value"):
        emit_core._infer_expr_type(callee_expr, callee_ctx.types, config=callee_ctx.config)

    with pytest.raises(emit_core._LoweringError, match="dma.alloc only supports contiguous stride"):
        emit_core._infer_expr_type(
            DmaAllocAST(
                shape=[ConstAST(2), ConstAST(3)],
                dtype=NumericType.Float32,
                stride=[ConstAST(2), ConstAST(1)],
                location=None,
            ),
            {},
        )

    invalid_lowering_cases = [
        (DmaCopyAST(source=ConstAST(1), space=MemorySpace.SM, location=None), "copy source must have nn.memory type"),
        (
            DmaCastAST(source=ConstAST(1), dtype=NumericType.Float16, memoryspace=MemorySpace.SM, location=None),
            "cast source must have nn.memory type",
        ),
        (
            DmaViewAST(
                source=ConstAST(1),
                offset=[ConstAST(0)],
                size=[ConstAST(1)],
                stride=[ConstAST(1)],
                location=None,
            ),
            "view source must have nn.memory type",
        ),
        (DmaReshapeAST(source=ConstAST(1), shape=[ConstAST(1)], location=None), "reshape source must have nn.memory type"),
        (DmaFlattenAST(source=ConstAST(1), location=None), "flatten source must have nn.memory type"),
        (NnBroadcastAST(value=ConstAST(1), target=ConstAST(2), location=None), "broadcast operands must be nn.memory"),
        (
            NnBroadcastToAST(source=ConstAST(1), target_shape=[ConstAST(2)], space=MemorySpace.SM, location=None),
            "broadcast_to source must be nn.memory",
        ),
        (NnTransposeAST(value=ConstAST(1), perm=[ConstAST(1), ConstAST(0)], location=None), "transpose input must be nn.memory"),
        (NnReduceAST(kind="reduce_sum", value=ConstAST(1), axis=[ConstAST(0)], keepdim=ConstAST(True), location=None), "reduce input must be nn.memory"),
        (NnSoftmaxAST(value=ConstAST(1), axis=ConstAST(0), location=None), "softmax input must be nn.memory"),
            (ConvAST(value=ConstAST(1), weight=ConstAST(2), kwargs={}, location=None), "conv operands must be nn.memory"),
            (
                Img2ColAST(kind="img2col1d", args=[ConstAST(1), ConstAST(3)], kwargs={}, location=None),
                "img2col1d input must be nn.memory",
            ),
        (FCAST(value=ConstAST(1), weight=ConstAST(2), location=None), "fc operands must be nn.memory"),
        (MatmulAST(lhs=ConstAST(1), rhs=ConstAST(2), memoryspace=None, location=None), "matmul operands must be nn.memory"),
        (StoreAST(tensor=TensorAST("out", Memory([1], NumericType.Float32), location=None), offset=ConstAST(0), stride=None, value=ConstAST(1), location=None), "StoreAST does not produce a value"),
        (DmaFreeAST(value=ConstAST(1), location=None), "free does not produce a value"),
        (ForAST(var=VarAST("i"), start=ConstAST(0), end=ConstAST(1), body=BlockAST([]), location=None), "ForAST does not produce a value"),
        (ArchBarrierAST(visibility=[BarrierVisibility.TSM], scope=BarrierScope.BLOCK, location=None), "barrier does not produce a value"),
        (
            ArchLaunchKernelAST(
                callee="kernel_body",
                block=ConstAST(1),
                thread=ConstAST(1),
                subthread=ConstAST(1),
                args=[],
                shared_memory_size=ConstAST(0),
                location=None,
            ),
            "launch_kernel does not produce a value",
        ),
        (ArchQueryAST(query_name="bad"), "Unsupported arch query"),
        (SymbolToFloatAST(source=ConstAST(1), location=None), 'symbol.to_float source must have type !symbol.int<"expr">'),
    ]
    for expr, message in invalid_lowering_cases:
        with pytest.raises(emit_core._LoweringError, match=message):
            emit_core._infer_expr_type(expr, {})

    tensor = TensorAST("missing", Memory([1], NumericType.Float32), location=None)
    with pytest.raises(emit_core._LoweringError, match="Unknown input reference"):
        emit_core._infer_expr_type(tensor, {})

    dynamic_type = emit_core._infer_expr_type(ArchGetDynamicMemoryAST(space=MemorySpace.SM, location=None), {})
    assert isinstance(dynamic_type, NnMemoryType)

    broadcast_source = TensorAST("broadcast_source", Memory([2], NumericType.Float32), location=None)
    broadcast_types = {emit_core._expr_key(broadcast_source): _memory_type([2], element_type=f32)}
    with pytest.raises(emit_core._LoweringError, match="broadcast_to space must be MemorySpace"):
        emit_core._infer_expr_type(
            NnBroadcastToAST(
                source=broadcast_source,
                target_shape=[ConstAST(2)],
                space="bad",  # type: ignore[arg-type]
                location=None,
            ),
            broadcast_types,
        )


# CORE-016
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证 mixed scalar cast、materialize 与 mixed binary lowering 的剩余分支。
# 测试目的: 锁定 `_cast_nn_scalar_operand` / `_materialize_mixed_binary_scalar_operand` / `_lower_mixed_binary_expr` 的错误和 cast 路径。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_mixed_scalar_cast_and_binary_branches
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_mixed_scalar_cast_and_binary_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    block = Block(
        arg_types=[
            emit_core.SymbolValueType.from_expr("N"),
            i32,
            Float16Type(),
            f32,
        ]
    )
    ctx = EmitContext(builder=block, symbols={"sym": block.args[0], "i32": block.args[1], "f16": block.args[2], "f32": block.args[3]}, types={})

    symbol_to_int = emit_core._cast_nn_scalar_operand(block.args[0], IntegerType(32), ctx, None)
    symbol_to_float = emit_core._cast_nn_scalar_operand(block.args[0], f32, ctx, None)
    int_to_float = emit_core._cast_nn_scalar_operand(block.args[1], f32, ctx, None)
    float_ext = emit_core._cast_nn_scalar_operand(block.args[2], f32, ctx, None)
    float_trunc = emit_core._cast_nn_scalar_operand(block.args[3], Float16Type(), ctx, None)
    assert isinstance(symbol_to_int.owner, emit_core.SymbolToIntOp)
    assert isinstance(symbol_to_float.owner, emit_core.SymbolToFloatOp)
    assert isinstance(int_to_float.owner, arith.SIToFPOp)
    assert isinstance(float_ext.owner, arith.ExtFOp)
    assert isinstance(float_trunc.owner, arith.TruncFOp)
    with pytest.raises(emit_core._LoweringError, match="nn scalar integer width conversion is unsupported"):
        emit_core._cast_nn_scalar_operand(block.args[1], i64, ctx, None)
    with pytest.raises(emit_core._LoweringError, match="nn scalar element_type must be integer/float or symbol.int"):
        emit_core._cast_nn_scalar_operand(block.args[0], StringAttr("bad"), ctx, None)

    with pytest.raises(emit_core._LoweringError, match="Binary op scalar operand could not be materialized"):
        emit_core._materialize_mixed_binary_scalar_operand(VarAST("missing"), None, f32, ctx, None)
    no_cast = emit_core._materialize_mixed_binary_scalar_operand(ConstAST(1), None, f32, ctx, None, cast_to_element_type=False)
    assert isinstance(no_cast.type, emit_core.SymbolValueType)

    lhs_type = _memory_type([2, 2], element_type=i32)
    lhs_tensor = TensorAST("lhs", Memory([2, 2], NumericType.Int32), location=None)
    lhs_block = Block(arg_types=[lhs_type])
    lhs_ctx = EmitContext(
        builder=lhs_block,
        symbols={"lhs": lhs_block.args[0]},
        types={emit_core._expr_key(lhs_tensor): lhs_type},
    )
    lhs_ctx._set_cache(emit_core._expr_key(lhs_tensor), lhs_block.args[0])

    both_memory_expr = BinaryExprAST(op="add", lhs=lhs_tensor, rhs=lhs_tensor, location=None)
    assert emit_core._lower_mixed_binary_expr(both_memory_expr, lhs_block.args[0], lhs_block.args[0], lhs_ctx) is None
    with pytest.raises(emit_core._LoweringError, match="Binary op operands must have nn.memory type"):
        emit_core._lower_mixed_binary_expr(BinaryExprAST(op="sub", lhs=ConstAST(1), rhs=ConstAST(2), location=None), None, None, lhs_ctx)

    rhs_value = emit_core._lower_expr(ConstAST(1.5), lhs_ctx)
    result_type_expr = BinaryExprAST(op="add", lhs=lhs_tensor, rhs=ConstAST(1.5), location=None)
    original_infer = emit_core._infer_expr_type

    def fake_result_type_infer(expr: object, type_map: dict[int, object], runtime_values: dict[str, object] | None = None, config: dict[str, object] | None = None) -> object:
        if expr is result_type_expr:
            return i32
        return original_infer(expr, type_map, runtime_values=runtime_values, config=config)

    monkeypatch.setattr(emit_core, "_infer_expr_type", fake_result_type_infer)
    with pytest.raises(emit_core._LoweringError, match="Binary op result must be nn.memory"):
        emit_core._lower_mixed_binary_expr(result_type_expr, lhs_block.args[0], rhs_value, lhs_ctx)

    cast_expr = BinaryExprAST(op="add", lhs=lhs_tensor, rhs=ConstAST(1.5), location=None)

    def fake_cast_type_infer(expr: object, type_map: dict[int, object], runtime_values: dict[str, object] | None = None, config: dict[str, object] | None = None) -> object:
        if expr is cast_expr:
            return _memory_type([2, 2], element_type=f32)
        return original_infer(expr, type_map, runtime_values=runtime_values, config=config)

    monkeypatch.setattr(emit_core, "_infer_expr_type", fake_cast_type_infer)
    cast_result = emit_core._lower_mixed_binary_expr(cast_expr, lhs_block.args[0], rhs_value, lhs_ctx)
    assert cast_result is not None
    assert isinstance(cast_result.type, emit_core.NnMemoryType)
    assert any(isinstance(op, emit_core.NnCastOp) for op in lhs_block.ops)
    assert any(isinstance(op, emit_core.NnAddOp) for op in lhs_block.ops)


# CORE-017
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证索引、shape、runtime scalar 与 helper 参数的剩余边界分支。
# 测试目的: 补齐 _materialize/_resolve/_shape_numel/_build_stride 等 helper 的异常与归一化路径。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_remaining_index_helper_edge_branches
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_remaining_index_helper_edge_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    class BadSymbolDim(SymbolDim):
        def get_value(self) -> object:  # pragma: no cover - 仅用于触发防御分支
            return object()

    memory_type = _memory_type(["M", 4], stride=["S", 1], element_type=f32)
    block = Block(
        arg_types=[
            memory_type,
            emit_core.SymbolValueType.from_expr("TILE"),
            emit_core.SymbolValueType.from_expr("N"),
            IndexType(),
            IntegerType(32),
            f32,
        ]
    )
    ctx = EmitContext(
        builder=block,
        symbols={
            "bad": 123,
            "memory": block.args[0],
            "tile": block.args[1],
            "N": block.args[2],
            "idx": block.args[3],
            "i32": block.args[4],
            "flt": block.args[5],
        },
        types={},
    )

    assert emit_core._materialize_index_symbol_from_symbol_alias("TILE", ctx, None) is block.args[1]
    assert emit_core._materialize_index_symbol_from_memory("M", ctx, None) is not None
    assert emit_core._materialize_index_symbol_from_memory("S", ctx, None) is not None
    with pytest.raises(emit_core._LoweringError, match="Unknown index symbol"):
        emit_core._resolve_index_symbol("missing", EmitContext(builder=Block(), symbols={}, types={}), None)
    with pytest.raises(emit_core._LoweringError, match="Index symbol must be SSA value"):
        emit_core._resolve_index_symbol("bad", ctx, None)
    assert emit_core._resolve_index_symbol("idx", ctx, None) is block.args[3]
    with pytest.raises(emit_core._LoweringError, match="Index operand must be integer or index"):
        emit_core._resolve_index_symbol("flt", ctx, None)

    assert emit_core._split_symbol_multiplication("M**N") is None
    with pytest.raises(emit_core._LoweringError, match="Unsupported index expression"):
        emit_core._resolve_index_symbol_product("M**N", ctx, None)
    with pytest.raises(emit_core._LoweringError, match="Unsupported index expression"):
        emit_core._build_symbol_index_result(block.args[3], block.args[1], "+", ctx, None)

    const_cache: dict[int, object] = {}
    emit_core._preload_symbolic_index_constants(7, ctx, None, const_cache)
    with pytest.raises(emit_core._LoweringError, match="Unsupported index expression"):
        emit_core._lower_symbolic_index_text("M +", ctx, None, const_cache)

    lowered_add = emit_core._lower_symbolic_index_node(py_ast.parse("M + N", mode="eval").body, ctx, None, const_cache)
    lowered_sub = emit_core._lower_symbolic_index_node(py_ast.parse("M - N", mode="eval").body, ctx, None, const_cache)
    lowered_div = emit_core._lower_symbolic_index_node(py_ast.parse("M / N", mode="eval").body, ctx, None, const_cache)
    lowered_floordiv = emit_core._lower_symbolic_index_node(py_ast.parse("M // N", mode="eval").body, ctx, None, const_cache)
    assert isinstance(lowered_add.type, emit_core.SymbolValueType)
    assert isinstance(lowered_sub.type, emit_core.SymbolValueType)
    assert isinstance(lowered_div.type, emit_core.SymbolValueType)
    assert isinstance(lowered_floordiv.type, emit_core.SymbolValueType)
    with pytest.raises(emit_core._LoweringError, match="Unsupported index expression"):
        emit_core._lower_symbolic_index_node(py_ast.parse("M % N", mode="eval").body, ctx, None, const_cache)

    class NotSSAValue:
        type = IntegerType(32)

    ctx.symbols["bad_scalar"] = NotSSAValue()
    with pytest.raises(emit_core._LoweringError, match="Index operand must be SSA value"):
        emit_core._resolve_index_operand(ScalarArgAST("bad_scalar", int, is_symbolic=True), ctx, None)

    assert emit_core._apply_symbolic_index_binary_op(SymbolDim("A"), SymbolDim("B"), "add", None) == SymbolDim("A") + SymbolDim("B")
    assert emit_core._apply_symbolic_index_binary_op(6, 3, "div", None) == 2
    assert emit_core._apply_symbolic_index_binary_op(6, 3, "floordiv", None) == 2
    assert isinstance(emit_core._apply_symbolic_index_binary_op(2, SymbolDim("B"), "div", None), SymbolDim)
    assert isinstance(emit_core._apply_symbolic_index_binary_op(2, SymbolDim("B"), "floordiv", None), SymbolDim)
    with pytest.raises(emit_core._LoweringError, match="Unsupported index expression"):
        emit_core._apply_symbolic_index_binary_op(6, 0, "floordiv", None)

    assert emit_core._resolve_symbolic_index_value(ScalarArgAST("sym", int, is_symbolic=True), location=None, runtime_values=None) == SymbolDim("sym")
    assert emit_core._resolve_symbolic_index_value(VarAST("runtime"), location=None, runtime_values={"runtime": SymbolDim("R")}) == SymbolDim("R")
    assert emit_core._resolve_runtime_scalar_value(ScalarArgAST("sym", int, is_symbolic=True), None, None) == SymbolDim("sym")
    assert emit_core._resolve_runtime_scalar_value(object(), emit_core.SymbolValueType.from_expr("R"), None) == SymbolDim("R")

    assert emit_core._build_static_index_list([ConstAST(1), "N"], 2, default_value=0) == [IntAttr(1), StringAttr("N")]
    assert emit_core._build_static_index_list(ConstAST(2), 2, default_value=1) == [IntAttr(2), IntAttr(2)]
    assert emit_core._build_static_index_attrs_exact(ConstAST(2)) == [IntAttr(2)]
    assert len(emit_core._build_index_operands_exact(ConstAST(2), ctx)) == 1

    assert emit_core._shape_numel_attr([FloatAttr(1.0, f32)]) == StringAttr("?")
    assert emit_core._shape_numel_attr([IntAttr(1), StringAttr("N")]) == StringAttr("N")
    assert emit_core._shape_numel_attr([IntAttr(2), StringAttr("N + 1")]) == StringAttr("2*(N + 1)")

    bad_symbol = BadSymbolDim("bad")
    with monkeypatch.context() as m:
        m.setattr(
            emit_core,
            "_apply_symbolic_index_binary_op",
            lambda *args, **kwargs: bad_symbol,
        )
        with pytest.raises(emit_core._LoweringError, match="Unsupported index expression"):
            emit_core._resolve_index_expr(BinaryExprAST(op="add", lhs=ConstAST(1), rhs=ConstAST(2), location=None), ctx)

    with monkeypatch.context() as m:
        m.setattr(emit_core, "_resolve_symbolic_index_value", lambda *args, **kwargs: bad_symbol)
        with pytest.raises(emit_core._LoweringError, match="Unsupported index expression"):
            emit_core._resolve_static_index_expr("N", location=None)

    with pytest.raises(emit_core._LoweringError, match="Unsupported loop bound expression"):
        emit_core._lower_loop_bound(object(), ctx)

    stride_block = Block(arg_types=[emit_core.SymbolValueType.from_expr("TILE"), IndexType()])
    stride_ctx = EmitContext(builder=stride_block, symbols={"tile": stride_block.args[0], "idx": stride_block.args[1]}, types={})
    with pytest.raises(emit_core._LoweringError, match="Only unit stride is supported"):
        emit_core._build_stride_attrs([ScalarArgAST("tile", int, is_symbolic=True)], 1, stride_ctx)
    with pytest.raises(emit_core._LoweringError, match="Only unit stride is supported"):
        emit_core._build_stride_attrs([ScalarArgAST("idx", int, is_symbolic=False)], 1, stride_ctx)
    with pytest.raises(emit_core._LoweringError, match="Only unit stride is supported"):
        emit_core._build_stride_attrs([ConstAST(2)], 1, stride_ctx)


# CORE-018
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证 _infer_expr_type / _lower_expr 的剩余成功与错误分支。
# 测试目的: 补齐 core.py 中 conv、fc、matmul、arch 查询、symbol 转换与 tensor axis 的剩余路径。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_remaining_expr_lowering_and_inference_branches
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_remaining_expr_lowering_and_inference_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    def make_ctx(*bindings: tuple[str, object, TensorAST]) -> EmitContext:
        block = Block(arg_types=[binding[1] for binding in bindings])
        ctx = EmitContext(builder=block, symbols={}, types={})
        for index, (name, memory_type, tensor) in enumerate(bindings):
            ctx.symbols[name] = block.args[index]
            ctx.types[emit_core._expr_key(tensor)] = memory_type
            ctx._set_cache(emit_core._expr_key(tensor), block.args[index])
        return ctx

    def expect_lowering_error(expr: object, ctx: EmitContext, result_type: object, message: str) -> None:
        original = emit_core._infer_expr_type

        def fake(
            node: object,
            type_map: dict[int, object],
            runtime_values: dict[str, object] | None = None,
            config: dict[str, object] | None = None,
        ) -> object:
            if node is expr:
                return result_type
            return original(node, type_map, runtime_values=runtime_values, config=config)

        monkeypatch.setattr(emit_core, "_infer_expr_type", fake)
        with pytest.raises(emit_core._LoweringError, match=message):
            emit_core._lower_expr(expr, ctx)
        monkeypatch.setattr(emit_core, "_infer_expr_type", original)

    sym_type = _memory_type(["N", 2], stride=["S", 1], element_type=f32)
    sym_tensor = TensorAST("sym", Memory([2, 2], NumericType.Float32), location=None)
    sym_ctx = make_ctx(("sym", sym_type, sym_tensor))
    slice_expr = LoadAST(tensor=sym_tensor, offset=[ConstAST(0), ConstAST(0)], sizes=None, stride=None, kind="slice", location=None)
    slice_result = emit_core._lower_expr(slice_expr, sym_ctx)
    assert isinstance(slice_result.owner, emit_core.DmaAllocOp)

    infer_source_type = _memory_type([2, 3], element_type=f32)
    infer_weight_type = _memory_type([3, 4], element_type=f32)
    infer_value_tensor = TensorAST("infer_value", Memory([2, 3], NumericType.Float32), location=None)
    infer_weight_tensor = TensorAST("infer_weight", Memory([3, 4], NumericType.Float32), location=None)
    infer_ctx = make_ctx(("infer_value", infer_source_type, infer_value_tensor), ("infer_weight", infer_weight_type, infer_weight_tensor))
    conv_expr = ConvAST(value=infer_value_tensor, weight=infer_weight_tensor, kwargs={}, location=None)
    fcast_expr = FCAST(value=infer_value_tensor, weight=infer_weight_tensor, location=None)
    matmul_expr = MatmulAST(lhs=infer_value_tensor, rhs=infer_weight_tensor, memoryspace=None, location=None)
    expect_lowering_error(conv_expr, infer_ctx, i32, "conv result must be nn.memory")
    expect_lowering_error(fcast_expr, infer_ctx, i32, "fc result must be nn.memory")
    expect_lowering_error(matmul_expr, infer_ctx, i32, "matmul result must be nn.memory")

    copy_expr = DmaCopyAST(source=sym_tensor, space=MemorySpace.SM, location=None)
    cast_expr = DmaCastAST(source=sym_tensor, dtype=NumericType.Float16, memoryspace=MemorySpace.SM, location=None)
    view_expr = DmaViewAST(
        source=sym_tensor,
        offset=[ConstAST(0), ConstAST(0)],
        size=[ConstAST(1), ConstAST(2)],
        stride=[ConstAST(1), ConstAST(1)],
        location=None,
    )
    reshape_expr = DmaReshapeAST(source=sym_tensor, shape=[ConstAST(2), ConstAST(2)], location=None)
    flatten_expr = DmaFlattenAST(source=sym_tensor, location=None)
    broadcast_target_tensor = TensorAST("broadcast_target", Memory([2, 2], NumericType.Float32), location=None)
    broadcast_target_type = _memory_type([2, 2], element_type=f32)
    broadcast_ctx = make_ctx(("sym", sym_type, sym_tensor), ("broadcast_target", broadcast_target_type, broadcast_target_tensor))
    broadcast_expr = NnBroadcastAST(value=sym_tensor, target=broadcast_target_tensor, location=None)
    broadcast_to_expr = NnBroadcastToAST(source=sym_tensor, target_shape=[ConstAST(2), ConstAST(2)], space=MemorySpace.SM, location=None)
    transpose_expr = NnTransposeAST(value=sym_tensor, perm=[ConstAST(1), ConstAST(0)], location=None)
    reduce_expr = NnReduceAST(kind="reduce_sum", value=sym_tensor, axis=[ConstAST(1)], keepdim=ConstAST(False), location=None)
    softmax_expr = NnSoftmaxAST(value=sym_tensor, axis=ConstAST(-1), location=None)
    img2col_expr = Img2ColAST(kind="img2col1d", args=[sym_tensor, ConstAST(3)], kwargs={}, location=None)

    for expr, ctx, message in (
        (DmaAllocAST(shape=[ConstAST(2), ConstAST(2)], dtype=NumericType.Float32, stride=None, location=None), infer_ctx, "alloc result must be nn.memory"),
        (copy_expr, sym_ctx, "copy result must be nn.memory"),
        (cast_expr, sym_ctx, "cast result must be nn.memory"),
        (view_expr, sym_ctx, "view result must be nn.memory"),
        (reshape_expr, sym_ctx, "reshape result must be nn.memory"),
        (flatten_expr, sym_ctx, "flatten result must be nn.memory"),
        (broadcast_expr, broadcast_ctx, "broadcast result must be nn.memory"),
        (broadcast_to_expr, sym_ctx, "broadcast_to result must be nn.memory"),
        (transpose_expr, sym_ctx, "transpose result must be nn.memory"),
        (reduce_expr, sym_ctx, "reduce result must be nn.memory"),
        (softmax_expr, sym_ctx, "softmax result must be nn.memory"),
        (img2col_expr, sym_ctx, "img2col1d result must be nn.memory"),
    ):
        expect_lowering_error(expr, ctx, i32, message)

    mismatch_expr = NnBroadcastAST(value=sym_tensor, target=broadcast_target_tensor, location=None)
    expect_lowering_error(mismatch_expr, broadcast_ctx, _memory_type([1, 2], element_type=f32), "broadcast result must match target type")

    with pytest.raises(emit_core._LoweringError, match="get_dynamic_memory space must be on-chip MemorySpace"):
        emit_core._lower_expr(ArchGetDynamicMemoryAST(space=MemorySpace.GM, location=None), EmitContext(builder=Block(), symbols={}, types={}))
    with pytest.raises(emit_core._LoweringError, match="Unsupported arch query"):
        emit_core._lower_expr(ArchQueryAST(query_name="bad", location=None), EmitContext(builder=Block(), symbols={}, types={}))
    with pytest.raises(emit_core._LoweringError, match='symbol.to_float source must have type !symbol.int<"expr">'):
        emit_core._lower_expr(SymbolToFloatAST(source=ConstAST(1), location=None), EmitContext(builder=Block(), symbols={}, types={}))

    callee_block = Block(arg_types=[i32])
    callee_block.add_op(func.ReturnOp(callee_block.args[0], callee_block.args[0]))
    callee_op = func.FuncOp("callee", ([i32], [i32]), Region(callee_block))
    call_expr = PythonCalleeCallAST(callee="callee", args=[ConstAST(1)], location=None)
    call_ctx = EmitContext(
        builder=Block(),
        symbols={},
        types={},
        config={emit_core._MLIR_GEN_CALLEE_REGISTRY_CONFIG_KEY: {"callee": callee_op}},
    )
    with pytest.raises(emit_core._LoweringError, match="Python callee registry must be dict"):
        emit_core._lower_expr(call_expr, EmitContext(builder=Block(), symbols={}, types={}, config={emit_core._MLIR_GEN_CALLEE_REGISTRY_CONFIG_KEY: []}))
    with pytest.raises(emit_core._LoweringError, match="Python callee is missing from registry"):
        emit_core._lower_expr(call_expr, EmitContext(builder=Block(), symbols={}, types={}, config={emit_core._MLIR_GEN_CALLEE_REGISTRY_CONFIG_KEY: {}}))

    class FakeCallOp:
        def __init__(self, callee_name: str, args: list[object], result_types: list[object]) -> None:
            self.callee_name = callee_name
            self.args = args
            self.result_types = result_types
            self.results: list[object] = []

    with monkeypatch.context() as m:
        m.setattr(emit_core.func, "CallOp", FakeCallOp)
        m.setattr(call_ctx.builder, "add_op", lambda op: None)
        with pytest.raises(emit_core._LoweringError, match="Python callee must return exactly one value"):
            emit_core._lower_expr(call_expr, call_ctx)

    axis_tensor = TensorAST("axis", Memory([2, 2], NumericType.Float32), location=None)
    axis_type = _memory_type([2, 2], element_type=f32)
    axis_block = Block(arg_types=[axis_type])
    axis_ctx = EmitContext(builder=axis_block, symbols={"axis": axis_block.args[0]}, types={emit_core._expr_key(axis_tensor): axis_type})
    axis_ctx._set_cache(emit_core._expr_key(axis_tensor), axis_block.args[0])
    with monkeypatch.context() as m:
        m.setattr(emit_core.SymbolGetDimOp, "verify", lambda self: (_ for _ in ()).throw(VerifyException("boom")))
        with pytest.raises(emit_core._LoweringError, match="boom"):
            emit_core._lower_expr(TensorAxisAccessAST(tensor=axis_tensor, kind="shape", axis=ConstAST(0), location=None), axis_ctx)


# CORE-019
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证 emit_mlir 的 statement / control-flow 剩余分支。
# 测试目的: 补齐 store、free、barrier、launch、for、BlockAST / FunctionAST 的门禁分支。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_remaining_statement_emission_branches
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_remaining_statement_emission_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    target_type = _memory_type([2, 2], element_type=f32)
    source_type = _memory_type([2, 2], element_type=f32)
    target_tensor = TensorAST("target", Memory([2, 2], NumericType.Float32), location=None)
    source_tensor = TensorAST("source", Memory([2, 2], NumericType.Float32), location=None)
    store_block = Block(arg_types=[target_type, source_type])
    store_ctx = EmitContext(
        builder=store_block,
        symbols={"target": store_block.args[0], "source": store_block.args[1]},
        types={
            emit_core._expr_key(target_tensor): target_type,
            emit_core._expr_key(source_tensor): source_type,
        },
    )
    store_ctx._set_cache(emit_core._expr_key(target_tensor), store_block.args[0])
    store_ctx._set_cache(emit_core._expr_key(source_tensor), store_block.args[1])
    store_expr = StoreAST(tensor=target_tensor, offset=[ConstAST(0), ConstAST(0)], stride=None, value=source_tensor, location=None)
    original = emit_core._infer_expr_type

    def fake_store_infer(
        node: object,
        type_map: dict[int, object],
        runtime_values: dict[str, object] | None = None,
        config: dict[str, object] | None = None,
    ) -> object:
        if node is store_expr.tensor or node is store_expr.value:
            raise emit_core._LoweringError("forced store inference failure", location=None)
        return original(node, type_map, runtime_values=runtime_values, config=config)

    monkeypatch.setattr(emit_core, "_infer_expr_type", fake_store_infer)
    store_op = emit_mlir(store_expr, store_ctx)
    assert isinstance(store_op, (emit_core.DmaStoreOp, emit_core.DmaDesliceOp))
    monkeypatch.setattr(emit_core, "_infer_expr_type", original)

    mismatch_tensor = TensorAST("mismatch", Memory([2], NumericType.Float32), location=None)
    mismatch_block = Block(arg_types=[target_type, _memory_type([2], element_type=f32)])
    mismatch_ctx = EmitContext(
        builder=mismatch_block,
        symbols={"target": mismatch_block.args[0], "mismatch": mismatch_block.args[1]},
        types={
            emit_core._expr_key(target_tensor): target_type,
            emit_core._expr_key(mismatch_tensor): _memory_type([2], element_type=f32),
        },
    )
    mismatch_ctx._set_cache(emit_core._expr_key(target_tensor), mismatch_block.args[0])
    mismatch_ctx._set_cache(emit_core._expr_key(mismatch_tensor), mismatch_block.args[1])
    with pytest.raises(ValueError, match="Index rank mismatch"):
        emit_mlir(
            StoreAST(
                tensor=target_tensor,
                offset=[ConstAST(0), ConstAST(0)],
                stride=None,
                value=mismatch_tensor,
                location=None,
            ),
            mismatch_ctx,
        )

    free_ctx = EmitContext(builder=Block(), symbols={}, types={})

    free_value = ConstAST(1)

    def fake_free_infer(
        node: object,
        type_map: dict[int, object],
        runtime_values: dict[str, object] | None = None,
        config: dict[str, object] | None = None,
    ) -> object:
        if node is free_value:
            raise emit_core._LoweringError("forced free inference failure", location=None)
        return original(node, type_map, runtime_values=runtime_values, config=config)

    monkeypatch.setattr(emit_core, "_infer_expr_type", fake_free_infer)
    with pytest.raises(TypeError, match="value must be Memory"):
        emit_mlir(DmaFreeAST(value=free_value, location=None), free_ctx)
    monkeypatch.setattr(emit_core, "_infer_expr_type", original)

    with monkeypatch.context() as m:
        m.setattr(emit_core.ArchBarrierOp, "verify", lambda self: (_ for _ in ()).throw(VerifyException("barrier verify failed")))
        with pytest.raises(emit_core._LoweringError, match="barrier verify failed"):
            emit_mlir(
                ArchBarrierAST(visibility=[BarrierVisibility.TSM], scope=BarrierScope.THREAD, location=None),
                EmitContext(builder=Block(), symbols={}, types={}),
            )

    launch_ctx = EmitContext(builder=Block(), symbols={}, types={})
    with monkeypatch.context() as m:
        m.setattr(emit_core.ArchLaunchKernelOp, "verify", lambda self: (_ for _ in ()).throw(VerifyException("launch verify failed")))
        with pytest.raises(emit_core._LoweringError, match="launch verify failed"):
            emit_mlir(
                ArchLaunchKernelAST(
                    callee="kernel_body",
                    block=ConstAST(1),
                    thread=ConstAST(1),
                    subthread=ConstAST(1),
                    args=[],
                    shared_memory_size=ConstAST(0),
                    location=None,
                ),
                launch_ctx,
            )

    numeric_block = Block(arg_types=[IntegerType(32), IntegerType(32), IntegerType(32)])
    numeric_ctx = EmitContext(
        builder=numeric_block,
        symbols={"start": numeric_block.args[0], "end": numeric_block.args[1], "step": numeric_block.args[2]},
        types={},
    )
    numeric_loop = ForAST(
        var=VarAST("i"),
        start=ScalarArgAST("start", int, is_symbolic=False),
        end=ScalarArgAST("end", int, is_symbolic=False),
        step=ScalarArgAST("step", int, is_symbolic=False),
        body=BlockAST([VarAST("i")]),
        location=None,
    )
    numeric_result = emit_mlir(numeric_loop, numeric_ctx)
    assert numeric_result is not None

    symbolic_block = Block(
        arg_types=[
            emit_core.SymbolValueType.from_expr("START"),
            emit_core.SymbolValueType.from_expr("END"),
            emit_core.SymbolValueType.from_expr("STEP"),
        ]
    )
    symbolic_ctx = EmitContext(
        builder=symbolic_block,
        symbols={"start": symbolic_block.args[0], "end": symbolic_block.args[1], "step": symbolic_block.args[2]},
        types={},
    )
    symbolic_loop = ForAST(
        var=VarAST("i"),
        start=ScalarArgAST("start", int, is_symbolic=True),
        end=ScalarArgAST("end", int, is_symbolic=True),
        step=ScalarArgAST("step", int, is_symbolic=True),
        body=BlockAST([VarAST("i")]),
        location=None,
    )
    symbolic_result = emit_mlir(symbolic_loop, symbolic_ctx)
    assert symbolic_result is not None

    with pytest.raises(emit_core._LoweringError, match="BlockAST must be lowered via AstVisitor"):
        emit_mlir(BlockAST([]), EmitContext(builder=Block(), symbols={}, types={}))
    with pytest.raises(emit_core._LoweringError, match="FunctionAST must be lowered via AstVisitor"):
        emit_mlir(FunctionAST("simple", [], [], BlockAST([ConstAST(1)]), returns_none=True), EmitContext(builder=Block(), symbols={}, types={}))


# CORE-020
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证 core.py 的关键成功 lowering 分支与缓存回读。
# 测试目的: 补齐 conv/fc/matmul、dma.alloc、dma.copy/dma.cast 的正向发射路径。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_remaining_successful_emit_branches
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_remaining_successful_emit_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    def make_ctx(*bindings: tuple[str, object, TensorAST]) -> EmitContext:
        block = Block(arg_types=[binding[1] for binding in bindings])
        ctx = EmitContext(builder=block, symbols={}, types={})
        for index, (name, memory_type, tensor) in enumerate(bindings):
            ctx.symbols[name] = block.args[index]
            ctx.types[emit_core._expr_key(tensor)] = memory_type
            ctx._set_cache(emit_core._expr_key(tensor), block.args[index])
        return ctx

    cached_tensor = TensorAST("cached", Memory([2, 2], NumericType.Float32), location=None)
    cached_type = _memory_type([2, 2], element_type=f32)
    cached_types = {emit_core._expr_key(cached_tensor): cached_type}
    assert emit_core._infer_expr_type(cached_tensor, cached_types) is cached_type

    conv_value_tensor = TensorAST("conv_value", Memory([1, 3, 4, 4], NumericType.Float32), location=None)
    conv_weight_tensor = TensorAST("conv_weight", Memory([2, 3, 3, 3], NumericType.Float32), location=None)
    conv_value_type = _memory_type([1, 3, 4, 4], element_type=f32)
    conv_weight_type = _memory_type([2, 3, 3, 3], element_type=f32)
    conv_expr = ConvAST(value=conv_value_tensor, weight=conv_weight_tensor, kwargs={}, location=None)
    conv_infer_types = {
        emit_core._expr_key(conv_value_tensor): conv_value_type,
        emit_core._expr_key(conv_weight_tensor): conv_weight_type,
    }
    assert isinstance(emit_core._infer_expr_type(conv_expr, conv_infer_types), NnMemoryType)

    fcast_value_tensor = TensorAST("fcast_value", Memory([2, 3], NumericType.Float32), location=None)
    fcast_weight_tensor = TensorAST("fcast_weight", Memory([4, 3], NumericType.Float32), location=None)
    fcast_value_type = _memory_type([2, 3], element_type=f32)
    fcast_weight_type = _memory_type([4, 3], element_type=f32)
    fcast_expr = FCAST(value=fcast_value_tensor, weight=fcast_weight_tensor, location=None)
    fcast_infer_types = {
        emit_core._expr_key(fcast_value_tensor): fcast_value_type,
        emit_core._expr_key(fcast_weight_tensor): fcast_weight_type,
    }
    assert isinstance(emit_core._infer_expr_type(fcast_expr, fcast_infer_types), NnMemoryType)

    matmul_value_tensor = TensorAST("matmul_value", Memory([2, 3], NumericType.Float32), location=None)
    matmul_weight_tensor = TensorAST("matmul_weight", Memory([3, 4], NumericType.Float32), location=None)
    matmul_value_type = _memory_type([2, 3], element_type=f32)
    matmul_weight_type = _memory_type([3, 4], element_type=f32)
    matmul_expr = MatmulAST(lhs=matmul_value_tensor, rhs=matmul_weight_tensor, memoryspace=None, location=None)
    matmul_infer_types = {
        emit_core._expr_key(matmul_value_tensor): matmul_value_type,
        emit_core._expr_key(matmul_weight_tensor): matmul_weight_type,
    }
    assert isinstance(emit_core._infer_expr_type(matmul_expr, matmul_infer_types), NnMemoryType)

    conv_ctx = make_ctx(
        ("conv_value", conv_value_type, conv_value_tensor),
        ("conv_weight", conv_weight_type, conv_weight_tensor),
    )
    conv_result = emit_mlir(conv_expr, conv_ctx)
    assert isinstance(conv_result.owner, emit_core.DmaReshapeOp)

    fcast_ctx = make_ctx(
        ("fcast_value", fcast_value_type, fcast_value_tensor),
        ("fcast_weight", fcast_weight_type, fcast_weight_tensor),
    )
    fcast_result = emit_mlir(fcast_expr, fcast_ctx)
    assert isinstance(fcast_result.owner, emit_core.NnMatmulOp)

    alloc_ctx = EmitContext(builder=Block(), symbols={}, types={})
    static_alloc = emit_mlir(DmaAllocAST(shape=[ConstAST(2), ConstAST(3)], dtype=NumericType.Float32, stride=None, location=None), alloc_ctx)
    assert isinstance(static_alloc.owner, emit_core.DmaAllocOp)

    symbolic_block = Block(arg_types=[emit_core.SymbolValueType.from_expr("N")])
    symbolic_ctx = EmitContext(builder=symbolic_block, symbols={"n": symbolic_block.args[0]}, types={})
    symbolic_alloc = emit_mlir(
        DmaAllocAST(shape=ScalarArgAST("n", int, is_symbolic=True), dtype=NumericType.Float32, stride=None, location=None),
        symbolic_ctx,
    )
    assert isinstance(symbolic_alloc.owner, emit_core.DmaAllocOp)

    copy_source_tensor = TensorAST("copy_source", Memory([2, 4], NumericType.Float32), location=None)
    copy_source_type = _memory_type([2, 4], element_type=f32)
    n_symbol_tensor = ScalarArgAST("N", int, is_symbolic=True)
    copy_ctx = make_ctx(
        ("copy_source", copy_source_type, copy_source_tensor),
        ("N", emit_core.SymbolValueType.from_expr("N"), n_symbol_tensor),
    )
    copy_expr = DmaCopyAST(source=copy_source_tensor, space=MemorySpace.SM, location=None)
    cast_expr = DmaCastAST(source=copy_source_tensor, dtype=NumericType.Float16, memoryspace=MemorySpace.SM, location=None)
    forced_copy_type = _memory_type(["N", 4], element_type=f32)
    forced_cast_type = _memory_type(["N", 4], element_type=Float16Type())

    original_infer = emit_core._infer_expr_type

    def fake_infer(
        node: object,
        type_map: dict[int, object],
        runtime_values: dict[str, object] | None = None,
        config: dict[str, object] | None = None,
    ) -> object:
        if node is copy_expr:
            return forced_copy_type
        if node is cast_expr:
            return forced_cast_type
        return original_infer(node, type_map, runtime_values=runtime_values, config=config)

    with monkeypatch.context() as m:
        m.setattr(emit_core, "_infer_expr_type", fake_infer)
        copy_result = emit_mlir(copy_expr, copy_ctx)
        cast_result = emit_mlir(cast_expr, copy_ctx)
        assert copy_result is not None
        assert cast_result is not None
        assert any(isinstance(op, emit_core.DmaCopyOp) for op in copy_ctx.builder.ops)
        assert any(isinstance(op, emit_core.DmaCastOp) for op in copy_ctx.builder.ops)

    matmul_lhs_tensor = TensorAST("matmul_lhs", Memory([2, 3], NumericType.Float16), location=None)
    matmul_rhs_tensor = TensorAST("matmul_rhs", Memory([3, 2], NumericType.Float16), location=None)
    matmul_lhs_type = _memory_type([2, 3], element_type=Float16Type())
    matmul_rhs_type = _memory_type([3, 2], element_type=Float16Type())
    matmul_ctx = make_ctx(
        ("matmul_lhs", matmul_lhs_type, matmul_lhs_tensor),
        ("matmul_rhs", matmul_rhs_type, matmul_rhs_tensor),
    )
    matmul_lower_expr = MatmulAST(lhs=matmul_lhs_tensor, rhs=matmul_rhs_tensor, memoryspace=None, location=None)
    forced_matmul_type = _memory_type([2, 2], element_type=f32)

    def fake_matmul_infer(
        node: object,
        type_map: dict[int, object],
        runtime_values: dict[str, object] | None = None,
        config: dict[str, object] | None = None,
    ) -> object:
        if node is matmul_lower_expr:
            return forced_matmul_type
        return original_infer(node, type_map, runtime_values=runtime_values, config=config)

    with monkeypatch.context() as m:
        m.setattr(emit_core, "_infer_expr_type", fake_matmul_infer)
        matmul_result = emit_mlir(matmul_lower_expr, matmul_ctx)
        assert matmul_result is not None
        assert any(isinstance(op, emit_core.DmaCastOp) for op in matmul_ctx.builder.ops)
        assert any(isinstance(op, emit_core.NnMatmulOp) for op in matmul_ctx.builder.ops)


# CORE-022
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 补齐 core helper 与表达式发射剩余边界。
# 测试目的: 覆盖当前全量统计里仍缺失的符号维、helper 参数、conv/img2col/fc/store 诊断分支。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_core.py -k test_emit_core_private_s7_remaining_branch_edges
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_core.py
def test_emit_core_private_s7_remaining_branch_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    assert isinstance(emit_core._eval_symbolic_dim_node(py_ast.parse("2 / N", mode="eval").body, None), SymbolDim)
    with pytest.raises(emit_core._LoweringError, match="Unsupported symbolic dim expression"):
        emit_core._eval_symbolic_dim_node(py_ast.parse("N % 2", mode="eval").body, None)
    with pytest.raises(emit_core._LoweringError, match="Unsupported symbolic dim expression"):
        emit_core._eval_symbolic_dim_node(py_ast.List(elts=[], ctx=py_ast.Load()), None)

    original_eval_symbolic_dim_node = emit_core._eval_symbolic_dim_node
    monkeypatch.setattr(emit_core, "_eval_symbolic_dim_node", lambda expr, location: object())
    with pytest.raises(emit_core._LoweringError, match="Unsupported symbolic dim expression"):
        emit_core._eval_symbolic_dim_expr("N", None)
    monkeypatch.setattr(emit_core, "_eval_symbolic_dim_node", original_eval_symbolic_dim_node)

    launch_tensor = TensorAST("mem", Memory([1], NumericType.Float32), location=None)
    launch_tensor_type = _memory_type([1], element_type=f32)
    launch_block = Block(
        arg_types=[
            emit_core.SymbolValueType.from_expr("-1"),
            emit_core.SymbolValueType.from_expr("0"),
            launch_tensor_type,
        ]
    )
    launch_ctx = EmitContext(
        builder=launch_block,
        symbols={"neg": launch_block.args[0], "zero": launch_block.args[1], "mem": launch_block.args[2]},
        types={},
    )
    negative_extent = ScalarArgAST("neg", int, is_symbolic=True, location=None)
    zero_extent = ScalarArgAST("zero", int, is_symbolic=True, location=None)
    launch_ctx._set_cache(emit_core._expr_key(negative_extent), launch_block.args[0])
    launch_ctx._set_cache(emit_core._expr_key(zero_extent), launch_block.args[1])
    launch_ctx._set_cache(emit_core._expr_key(launch_tensor), launch_block.args[2])
    with pytest.raises(emit_core._LoweringError, match="launch_kernel block must be >= 0"):
        emit_core._lower_launch_extent_symbol(negative_extent, "block", launch_ctx, None, allow_zero=True)
    with pytest.raises(emit_core._LoweringError, match="launch_kernel block must be > 0"):
        emit_core._lower_launch_extent_symbol(zero_extent, "block", launch_ctx, None)
    with pytest.raises(emit_core._LoweringError, match="launch_kernel block must be !symbol.int"):
        emit_core._lower_launch_extent_symbol(launch_tensor, "block", launch_ctx, None)

    resolve_ctx = EmitContext(builder=Block(), symbols={}, types={})
    assert emit_core._resolve_index_expr(
        BinaryExprAST(op="mul", lhs=ConstAST("N"), rhs=ConstAST(2), location=None),
        resolve_ctx,
    ) == "2*N"

    loop_bound = emit_core._lower_loop_bound(ConstAST(1.5), EmitContext(builder=Block(), symbols={}, types={}))
    assert isinstance(loop_bound.owner, arith.ConstantOp)

    helper_block = Block(arg_types=[i32, f32])
    helper_ctx = EmitContext(builder=helper_block, symbols={"i": helper_block.args[0], "f": helper_block.args[1]}, types={})
    assert emit_core._lower_helper_index_operand(VarAST("i"), helper_ctx, location=None) is helper_block.args[0]
    with pytest.raises(emit_core._LoweringError, match="Index operand must be integer or index"):
        emit_core._lower_helper_index_operand(VarAST("f"), helper_ctx, location=None)

    assert emit_core._resolve_binary_element_type(i32, Float16Type(), None) == Float16Type()
    with pytest.raises(emit_core._LoweringError, match="Binary op operands must have the same element_type"):
        emit_core._resolve_binary_element_type(i32, IntAttr(1), None)

    with pytest.raises(emit_core._LoweringError, match="matmul element_type must match"):
        emit_core._infer_matmul_memory_type(
            _memory_type([2, 3], element_type=i32, space=MemorySpace.GM),
            _memory_type([3, 4], element_type=f32, space=MemorySpace.GM),
            None,
            None,
        )

    with pytest.raises(emit_core._LoweringError, match="nn.memory stride contains unknown dimension"):
        emit_core._nn_memory_type_to_memory(_memory_type([2], stride=["?"], element_type=f32))
    valid_memory_type = _memory_type([1], stride=[1], element_type=f32)

    class _FakeUnsupportedSpace:
        def __init__(self) -> None:
            self.space = StringAttr("weird")

    class _FakeUnsupportedMemoryType:
        def __init__(self, base: NnMemoryType) -> None:
            self.shape = base.shape
            self.stride = base.stride
            self.element_type = base.element_type
            self.space = _FakeUnsupportedSpace()

    unsupported_space_type = _FakeUnsupportedMemoryType(valid_memory_type)
    with pytest.raises(emit_core._LoweringError, match="Unsupported nn.memory space"):
        emit_core._nn_memory_type_to_memory(unsupported_space_type)

    helper_value = TensorAST("value", Memory([4, 4], NumericType.Float32), location=None)
    with pytest.raises(emit_core._LoweringError, match="Unsupported img2col helper"):
        emit_core._parse_img2col_helper(Img2ColAST(kind="img2colX", args=[helper_value], kwargs={}, location=None))
    with pytest.raises(emit_core._LoweringError, match="img2col1d arity mismatch"):
        emit_core._parse_img2col_helper(
            Img2ColAST(
                kind="img2col1d",
                args=[helper_value, ConstAST(3), ConstAST(1), ConstAST(1), ConstAST(0), ConstAST(0), ConstAST(9)],
                kwargs={},
                location=None,
            )
        )
    with pytest.raises(emit_core._LoweringError, match="img2col1d got multiple values for argument 'kw'"):
        emit_core._parse_img2col_helper(
            Img2ColAST(kind="img2col1d", args=[helper_value, ConstAST(3)], kwargs={"kw": ConstAST(5)}, location=None)
        )
    with pytest.raises(emit_core._LoweringError, match="img2col1d missing required argument 'kw'"):
        emit_core._parse_img2col_helper(
            Img2ColAST(
                kind="img2col1d",
                args=[helper_value],
                kwargs={"sw": ConstAST(1), "dw": ConstAST(1), "pl": ConstAST(0), "pr": ConstAST(0)},
                location=None,
            )
        )

    with pytest.raises(VerifyException, match="kw must be positive"):
        emit_core._static_kernel_dim(StringAttr("-1"), "kw", None)
    with pytest.raises(emit_core._LoweringError, match="conv dim must be int or symbol"):
        emit_core._conv_out_dim_value(
            FloatAttr(1.0, f32),
            axis_name="height",
            kernel=1,
            stride=1,
            dilation=1,
            pad_before=0,
            pad_after=0,
            location=None,
        )
    with pytest.raises(VerifyException, match="output height must be positive"):
        emit_core._conv_out_dim_value(
            IntAttr(1),
            axis_name="height",
            kernel=3,
            stride=1,
            dilation=1,
            pad_before=0,
            pad_after=0,
            location=None,
        )
    with pytest.raises(emit_core._LoweringError, match="img2col dim must be int or symbol"):
        emit_core._img2col_out_dim_value(FloatAttr(1.0, f32), 3, 1, 1, 0, 0, None)
    with pytest.raises(emit_core._LoweringError, match="Unsupported img2col helper"):
        emit_core._infer_img2col_output_shape_attrs(
            Img2ColAST(kind="img2colX", args=[helper_value], kwargs={}, location=None),
            _memory_type([2, 3], element_type=f32),
            {},
        )

    assert emit_core._parse_reduce_axis_expr(1, None) == [1]
    with pytest.raises(emit_core._LoweringError, match="reduce axis must be int"):
        emit_core._parse_reduce_axis_expr([ConstAST(1), "bad"], None)
    with pytest.raises(emit_core._LoweringError, match="reduce axis must be int or list of int"):
        emit_core._parse_reduce_axis_expr("bad", None)

    with pytest.raises(emit_core._LoweringError, match="transpose perm entries must be int"):
        emit_core._parse_transpose_perm_expr(ConstAST("bad"), None)
    assert emit_core._parse_transpose_perm_expr(1, None) == [1]
    with pytest.raises(emit_core._LoweringError, match="transpose perm entries must be int"):
        emit_core._parse_transpose_perm_expr([ConstAST(1), "bad"], None)
    with pytest.raises(emit_core._LoweringError, match="transpose perm must be list of int"):
        emit_core._parse_transpose_perm_expr("bad", None)

    fc_value = TensorAST("fc_value", Memory([2], NumericType.Float32), location=None)
    fc_weight = TensorAST("fc_weight", Memory([2, 2], NumericType.Float32), location=None)
    with pytest.raises(emit_core._LoweringError, match="fc operands must be rank-2 nn.memory"):
        emit_core._infer_expr_type(
            FCAST(value=fc_value, weight=fc_weight, location=None),
            {
                emit_core._expr_key(fc_value): _memory_type([2], element_type=f32),
                emit_core._expr_key(fc_weight): _memory_type([2, 2], element_type=f32),
            },
        )

    known_tensor = TensorAST("known", Memory([2], NumericType.Float32), location=None)
    known_tensor_type = _memory_type([2], element_type=f32)
    assert emit_core._infer_expr_type(known_tensor, {emit_core._expr_key(known_tensor): known_tensor_type}) == known_tensor_type

    cast_block = Block(arg_types=[i32])
    cast_ctx = EmitContext(builder=cast_block, symbols={"i": cast_block.args[0]}, types={})
    with pytest.raises(emit_core._LoweringError, match="nn scalar element_type must be integer/float or symbol.int"):
        emit_core._cast_nn_scalar_operand(cast_block.args[0], StringAttr("bad"), cast_ctx, None)

    with pytest.raises(emit_core._LoweringError, match="Unknown input reference"):
        emit_core._lower_expr(TensorAST("missing", Memory([1], NumericType.Float32), location=None), EmitContext(builder=Block(), symbols={}, types={}))

    alloc_expr = DmaAllocAST(shape=2, dtype=NumericType.Float32, stride=None, location=None)
    alloc_type = _memory_type([2], element_type=f32)
    alloc_ctx = EmitContext(builder=Block(), symbols={}, types={emit_core._expr_key(alloc_expr): alloc_type})
    alloc_result = emit_core._lower_expr(alloc_expr, alloc_ctx)
    assert alloc_result.type == alloc_type

    fc_lower_value = TensorAST("fc_lower_value", Memory([2], NumericType.Float32), location=None)
    fc_lower_weight = TensorAST("fc_lower_weight", Memory([2, 2], NumericType.Float32), location=None)
    fc_lower_block = Block(arg_types=[_memory_type([2], element_type=f32), _memory_type([2, 2], element_type=f32)])
    fc_lower_ctx = EmitContext(
        builder=fc_lower_block,
        symbols={"fc_lower_value": fc_lower_block.args[0], "fc_lower_weight": fc_lower_block.args[1]},
        types={
            emit_core._expr_key(fc_lower_value): fc_lower_block.args[0].type,
            emit_core._expr_key(fc_lower_weight): fc_lower_block.args[1].type,
        },
    )
    fc_lower_ctx._set_cache(emit_core._expr_key(fc_lower_value), fc_lower_block.args[0])
    fc_lower_ctx._set_cache(emit_core._expr_key(fc_lower_weight), fc_lower_block.args[1])
    with pytest.raises(emit_core._LoweringError, match="fc operands must be rank-2 nn.memory"):
        emit_core._lower_expr(FCAST(value=fc_lower_value, weight=fc_lower_weight, location=None), fc_lower_ctx)

    with pytest.raises(emit_core._LoweringError, match="free does not produce a value"):
        emit_core._lower_expr(DmaFreeAST(value=ConstAST(1), location=None), EmitContext(builder=Block(), symbols={}, types={}))

    store_target = TensorAST("target", Memory([2, 2], NumericType.Float32), location=None)
    store_value = TensorAST("value", Memory([2], NumericType.Float32), location=None)
    store_block = Block(arg_types=[_memory_type([2, 2], element_type=f32), _memory_type([2], element_type=f32)])
    store_ctx = EmitContext(
        builder=store_block,
        symbols={"target": store_block.args[0], "value": store_block.args[1]},
        types={
            emit_core._expr_key(store_target): store_block.args[0].type,
            emit_core._expr_key(store_value): store_block.args[1].type,
        },
    )
    store_ctx._set_cache(emit_core._expr_key(store_target), store_block.args[0])
    store_ctx._set_cache(emit_core._expr_key(store_value), store_block.args[1])
    with pytest.raises(ValueError, match="Index rank mismatch"):
        emit_mlir(
            StoreAST(
                tensor=store_target,
                offset=[ConstAST(0), ConstAST(0)],
                stride=None,
                value=store_value,
                location=None,
            ),
            store_ctx,
        )
