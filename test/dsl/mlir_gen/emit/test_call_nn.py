"""Emit call_nn tests.

创建者: OpenAI
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 nn elementwise family emit 拆分入口的最小行为。

使用示例:
- pytest -q test/dsl/mlir_gen/emit/test_call_nn.py

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/emit/call_nn.py
- Spec 文档: spec/dsl/emit_mlir.md
- 测试文件: test/dsl/mlir_gen/emit/test_call_nn.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from xdsl.dialects import arith
from xdsl.dialects.builtin import ArrayAttr, Float16Type, Float64Type, IntAttr, f32, i1, i32
from xdsl.ir import Block

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.nn import (
    NnAddOp,
    NnBroadcastOp,
    NnCastOp,
    NnEqOp,
    NnMemorySpaceAttr,
    NnMemoryType,
    NnReluOp,
)
from kernel_gen.dialect.symbol import SymbolAddOp, SymbolConstOp, SymbolDivOp, SymbolFloorDivOp, SymbolMulOp, SymbolSubOp, SymbolToFloatOp
from kernel_gen.dsl.ast import BinaryExprAST, CompareExprAST, ConstAST, NnUnaryAST, ScalarArgAST, TensorAST
from kernel_gen.dsl.mlir_gen.emit.core import _expr_key
from kernel_gen.dsl.mlir_gen.emit import EmitContext
from kernel_gen.dsl.mlir_gen.emit.context import LoweringError
from kernel_gen.dsl.mlir_gen.emit.call_nn import emit_nn_call
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

call_nn_module = importlib.import_module("kernel_gen.dsl.mlir_gen.emit.call_nn")


def _memory_type(shape: list[int], strides: list[int], element_type: object) -> NnMemoryType:
    return NnMemoryType(
        ArrayAttr([IntAttr(dim) for dim in shape]),
        ArrayAttr([IntAttr(stride) for stride in strides]),
        element_type,
        NnMemorySpaceAttr.from_name("global"),
    )


def test_emit_nn_call_lowers_relu() -> None:
    tensor = TensorAST(name="x", memory=Memory([2, 2], NumericType.Float32), location=None)
    tensor_type = _memory_type([2, 2], [2, 1], f32)
    block = Block(arg_types=[tensor_type])
    ctx = EmitContext(builder=block, symbols={"x": block.args[0]}, types={_expr_key(tensor): tensor_type})
    ctx._set_cache(_expr_key(tensor), block.args[0])

    result = emit_nn_call(NnUnaryAST(kind="relu", value=tensor, location=None), ctx)

    body_ops = list(block.ops)
    assert len(body_ops) == 1
    assert isinstance(body_ops[0], NnReluOp)
    assert result is body_ops[0].result


def test_emit_nn_call_lowers_add_mixed_const_via_symbol_const() -> None:
    tensor = TensorAST(name="x", memory=Memory([2, 2], NumericType.Float16), location=None)
    tensor_type = _memory_type([2, 2], [2, 1], Float16Type())
    block = Block(arg_types=[tensor_type])
    ctx = EmitContext(builder=block, symbols={"x": block.args[0]}, types={_expr_key(tensor): tensor_type})
    ctx._set_cache(_expr_key(tensor), block.args[0])

    result = emit_nn_call(BinaryExprAST(op="add", lhs=tensor, rhs=ConstAST(1), location=None), ctx)

    body_ops = list(block.ops)
    assert [type(op) for op in body_ops] == [SymbolConstOp, SymbolToFloatOp, NnAddOp]
    assert result is body_ops[-1].result


def test_emit_nn_call_lowers_compare_cast_and_broadcast() -> None:
    lhs = TensorAST(name="lhs", memory=Memory([2, 2], NumericType.Float32), location=None)
    rhs = TensorAST(name="rhs", memory=Memory([1, 2], NumericType.Int32), location=None)
    lhs_type = _memory_type([2, 2], [2, 1], f32)
    rhs_type = _memory_type([1, 2], [2, 1], i32)
    block = Block(arg_types=[lhs_type, rhs_type])
    ctx = EmitContext(
        builder=block,
        symbols={"lhs": block.args[0], "rhs": block.args[1]},
        types={_expr_key(lhs): lhs_type, _expr_key(rhs): rhs_type},
    )
    ctx._set_cache(_expr_key(lhs), block.args[0])
    ctx._set_cache(_expr_key(rhs), block.args[1])

    result = emit_nn_call(CompareExprAST(op="eq", lhs=lhs, rhs=rhs, location=None), ctx)

    body_ops = list(block.ops)
    assert [type(op) for op in body_ops] == [NnCastOp, NnBroadcastOp, NnEqOp]
    assert result is body_ops[-1].result


def test_emit_nn_call_rejects_invalid_node() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    with pytest.raises(LoweringError, match="emit_nn_call only handles nn elementwise AST nodes"):
        emit_nn_call(ConstAST(1), ctx)  # type: ignore[arg-type]


# CALL-NN-S6-HELPER-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 直接覆盖 nn elementwise helper 的纯推导、cast 与 mixed scalar 分支。
# 测试目的: 锁定 symbol / memory / mixed scalar / compare 的 helper 级语义与异常边界。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_nn.py -k test_call_nn_private_helpers_contracts
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/call_nn.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_nn.py
def test_call_nn_private_helpers_contracts() -> None:
    tensor = TensorAST(name="x", memory=Memory([2, 2], NumericType.Float32), location=None)
    tensor_type = _memory_type([2, 2], [2, 1], f32)
    type_map = {_expr_key(tensor): tensor_type}

    assert call_nn_module._normalize_mixed_scalar_element_type(i32, None) == i32
    assert call_nn_module._normalize_mixed_scalar_element_type(Float16Type(), None) == Float16Type()
    assert call_nn_module._normalize_mixed_scalar_element_type(Float64Type(), None) == Float64Type()
    with pytest.raises(LoweringError, match="nn.add scalar element_type must be i32/f16/f32 or symbol.int"):
        call_nn_module._normalize_mixed_scalar_element_type(IntAttr(1), None)

    symbol_block = Block(arg_types=[call_nn_module.SymbolValueType.from_expr("N"), i32, f32])
    symbol_ctx = EmitContext(builder=symbol_block, symbols={"sym": symbol_block.args[0], "i": symbol_block.args[1], "f": symbol_block.args[2]}, types={})
    symbol_cast = call_nn_module._cast_nn_scalar_operand(symbol_block.args[0], i32, symbol_ctx, None)
    assert symbol_cast.type == i32
    float_cast = call_nn_module._cast_nn_scalar_operand(symbol_block.args[0], f32, symbol_ctx, None)
    assert float_cast.type == f32
    int_to_float = call_nn_module._cast_nn_scalar_operand(symbol_block.args[1], f32, symbol_ctx, None)
    assert isinstance(list(symbol_block.ops)[2], arith.SIToFPOp)
    assert int_to_float.type == f32
    widen_block = Block(arg_types=[f32])
    widen_ctx = EmitContext(builder=widen_block, symbols={"w": widen_block.args[0]}, types={})
    widened = call_nn_module._cast_nn_scalar_operand(widen_block.args[0], Float64Type(), widen_ctx, None)
    assert isinstance(list(widen_block.ops)[0], arith.ExtFOp)
    assert widened.type == Float64Type()
    narrow_block = Block(arg_types=[Float64Type()])
    narrow_ctx = EmitContext(builder=narrow_block, symbols={"n": narrow_block.args[0]}, types={})
    narrowed = call_nn_module._cast_nn_scalar_operand(narrow_block.args[0], Float16Type(), narrow_ctx, None)
    assert isinstance(list(narrow_block.ops)[0], arith.TruncFOp)
    assert narrowed.type == Float16Type()

    unary_expr = NnUnaryAST(kind="leaky_relu", value=tensor, alpha=ConstAST(0.25), location=None)
    unary_result = call_nn_module._infer_unary_type(unary_expr, type_map, runtime_values=None, config=None)
    assert isinstance(unary_result, NnMemoryType)
    assert unary_result.element_type == f32

    hard_sigmoid_expr = NnUnaryAST(kind="hard_sigmoid", value=tensor, alpha=ConstAST(0.2), beta=ConstAST(0.5), location=None)
    hard_sigmoid_result = call_nn_module._infer_unary_type(hard_sigmoid_expr, type_map, runtime_values=None, config=None)
    assert isinstance(hard_sigmoid_result, NnMemoryType)

    lhs_symbol = ScalarArgAST(name="lhs", value_type=int, is_symbolic=True, location=None)
    rhs_symbol = ScalarArgAST(name="rhs", value_type=int, is_symbolic=True, location=None)
    symbol_type_map = {
        _expr_key(lhs_symbol): call_nn_module.SymbolValueType.from_expr("M"),
        _expr_key(rhs_symbol): call_nn_module.SymbolValueType.from_expr("N"),
    }
    symbol_binary = BinaryExprAST(op="add", lhs=lhs_symbol, rhs=rhs_symbol, location=None)
    symbol_binary_result = call_nn_module._infer_binary_type(symbol_binary, symbol_type_map, runtime_values=None, config=None)
    assert isinstance(symbol_binary_result, call_nn_module.SymbolValueType)
    assert str(symbol_binary_result.expr.expr.data).replace(" ", "") == "M+N"

    mixed_binary = BinaryExprAST(op="add", lhs=tensor, rhs=ConstAST(1), location=None)
    mixed_result = call_nn_module._infer_binary_type(mixed_binary, type_map, runtime_values=None, config=None)
    assert isinstance(mixed_result, NnMemoryType)
    assert mixed_result.element_type == f32

    compare_expr = CompareExprAST(op="eq", lhs=lhs_symbol, rhs=rhs_symbol, location=None)
    compare_result = call_nn_module._infer_compare_type(compare_expr, symbol_type_map, runtime_values=None, config=None)
    assert compare_result == i1

    memory_compare = CompareExprAST(op="eq", lhs=tensor, rhs=tensor, location=None)
    memory_compare_result = call_nn_module._infer_compare_type(memory_compare, type_map, runtime_values=None, config=None)
    assert isinstance(memory_compare_result, NnMemoryType)
    assert memory_compare_result.element_type == i1

    mixed_floor = BinaryExprAST(op="floordiv", lhs=tensor, rhs=ConstAST(2), location=None)
    mixed_floor_result = call_nn_module._infer_binary_type(mixed_floor, type_map, runtime_values=None, config=None)
    assert isinstance(mixed_floor_result, NnMemoryType)


# CALL-NN-S7-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 覆盖 symbol binary lowering 的五种公开算子映射。
# 测试目的: 锁定 add/sub/mul/div/floordiv 在 symbol 路径下保持独立 op，不回退到 memory 或 mixed-scalar 分支。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_nn.py -k test_call_nn_private_emit_binary_lowers_symbol_op_matrix
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/call_nn.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_nn.py
@pytest.mark.parametrize(
    ("op_name", "expected_op_type"),
    [
        ("add", SymbolAddOp),
        ("sub", SymbolSubOp),
        ("mul", SymbolMulOp),
        ("div", SymbolDivOp),
        ("floordiv", SymbolFloorDivOp),
    ],
)
def test_call_nn_private_emit_binary_lowers_symbol_op_matrix(
    op_name: str,
    expected_op_type: type[object],
) -> None:
    lhs = ScalarArgAST(name="lhs", value_type=int, is_symbolic=True, location=None)
    rhs = ScalarArgAST(name="rhs", value_type=int, is_symbolic=True, location=None)
    lhs_type = call_nn_module.SymbolValueType.from_expr("M")
    rhs_type = call_nn_module.SymbolValueType.from_expr("N")
    block = Block(arg_types=[lhs_type, rhs_type])
    ctx = EmitContext(
        builder=block,
        symbols={"lhs": block.args[0], "rhs": block.args[1]},
        types={_expr_key(lhs): lhs_type, _expr_key(rhs): rhs_type},
    )
    ctx._set_cache(_expr_key(lhs), block.args[0])
    ctx._set_cache(_expr_key(rhs), block.args[1])

    result = call_nn_module._emit_binary(BinaryExprAST(op=op_name, lhs=lhs, rhs=rhs, location=None), ctx)

    body_ops = list(block.ops)
    assert len(body_ops) == 1
    assert isinstance(body_ops[0], expected_op_type)
    assert result is body_ops[0].result


# CALL-NN-S7-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 覆盖 binary / compare 在 lhs 需要提升类型时的 cast 路径。
# 测试目的: 锁定 call_nn 在 lhs 为较窄 memory 元素类型时会显式插入 NnCastOp，不依赖 rhs-only cast。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_nn.py -k test_call_nn_private_emit_binary_and_compare_cast_lhs_memory_operand
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/call_nn.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_nn.py
def test_call_nn_private_emit_binary_and_compare_cast_lhs_memory_operand() -> None:
    lhs = TensorAST(name="lhs", memory=Memory([2, 2], NumericType.Int32), location=None)
    rhs = TensorAST(name="rhs", memory=Memory([2, 2], NumericType.Float32), location=None)
    lhs_type = _memory_type([2, 2], [2, 1], i32)
    rhs_type = _memory_type([2, 2], [2, 1], f32)

    binary_block = Block(arg_types=[lhs_type, rhs_type])
    binary_ctx = EmitContext(
        builder=binary_block,
        symbols={"lhs": binary_block.args[0], "rhs": binary_block.args[1]},
        types={_expr_key(lhs): lhs_type, _expr_key(rhs): rhs_type},
    )
    binary_ctx._set_cache(_expr_key(lhs), binary_block.args[0])
    binary_ctx._set_cache(_expr_key(rhs), binary_block.args[1])

    binary_result = call_nn_module._emit_binary(BinaryExprAST(op="add", lhs=lhs, rhs=rhs, location=None), binary_ctx)

    binary_ops = list(binary_block.ops)
    assert [type(op) for op in binary_ops] == [NnCastOp, NnAddOp]
    assert binary_result is binary_ops[-1].result

    compare_block = Block(arg_types=[lhs_type, rhs_type])
    compare_ctx = EmitContext(
        builder=compare_block,
        symbols={"lhs": compare_block.args[0], "rhs": compare_block.args[1]},
        types={_expr_key(lhs): lhs_type, _expr_key(rhs): rhs_type},
    )
    compare_ctx._set_cache(_expr_key(lhs), compare_block.args[0])
    compare_ctx._set_cache(_expr_key(rhs), compare_block.args[1])

    compare_result = call_nn_module._emit_compare(CompareExprAST(op="eq", lhs=lhs, rhs=rhs, location=None), compare_ctx)

    compare_ops = list(compare_block.ops)
    assert [type(op) for op in compare_ops] == [NnCastOp, NnEqOp]
    assert compare_result is compare_ops[-1].result


# CALL-NN-S7-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 覆盖 symbol/runtime 标量物化、mixed binary 错误路径与 symbol binary 非法算子边界。
# 测试目的: 锁定 call_nn 的 runtime values、mixed scalar 与 symbol-only helper 在异常场景下保持稳定诊断。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_nn.py -k test_call_nn_private_runtime_and_error_edges
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/call_nn.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_nn.py
def test_call_nn_private_runtime_and_error_edges() -> None:
    tensor = TensorAST(name="x", memory=Memory([2, 2], NumericType.Float32), location=None)
    tensor_type = _memory_type([2, 2], [2, 1], f32)
    scalar_expr = ScalarArgAST(name="scale", value_type=int, is_symbolic=False, location=None)
    symbol_expr = ScalarArgAST(name="sym", value_type=int, is_symbolic=True, location=None)

    runtime_ctx = EmitContext(
        builder=Block(),
        symbols={},
        types={},
        config={"__runtime_values__": {"scale": 7, "sym": SymbolDim("K")}},
    )
    assert call_nn_module._runtime_values_from_ctx(runtime_ctx) == {"scale": 7, "sym": SymbolDim("K")}
    assert call_nn_module._symbol_scalar_expr_text(scalar_expr, i32, {"scale": 7}) == "7"
    assert call_nn_module._symbol_scalar_expr_text(symbol_expr, i32, {"sym": SymbolDim("K")}) == "K"
    assert call_nn_module._symbol_scalar_expr_text(ConstAST(True), i32, {"scale": 7}) is None

    symbol_block = Block(arg_types=[call_nn_module.SymbolValueType.from_expr("K")])
    symbol_ctx = EmitContext(
        builder=symbol_block,
        symbols={"sym": symbol_block.args[0]},
        types={_expr_key(symbol_expr): symbol_block.args[0].type},
        config={"__runtime_values__": {"sym": SymbolDim(9)}},
    )
    symbol_ctx._set_cache(_expr_key(symbol_expr), symbol_block.args[0])
    symbol_value = call_nn_module._materialize_symbol_binary_operand(
        symbol_expr,
        symbol_block.args[0].type,
        symbol_ctx,
        None,
    )
    assert symbol_value is symbol_block.args[0]

    runtime_symbol_ctx = EmitContext(
        builder=Block(),
        symbols={},
        types={},
        config={"__runtime_values__": {"sym": SymbolDim(5)}},
    )
    runtime_symbol_value = call_nn_module._materialize_symbol_binary_operand(
        symbol_expr,
        i32,
        runtime_symbol_ctx,
        None,
    )
    assert isinstance(runtime_symbol_value.owner, SymbolConstOp)
    assert int(runtime_symbol_value.owner.value.data) == 5

    with pytest.raises(LoweringError, match="Binary op operands must have nn.memory type"):
        call_nn_module._materialize_symbol_binary_operand(
            scalar_expr,
            i1,
            EmitContext(builder=Block(), symbols={}, types={}, config={"__runtime_values__": {"scale": True}}),
            None,
        )

    no_memory_ctx = EmitContext(builder=Block(), symbols={}, types={}, config={})
    with pytest.raises(LoweringError, match="nn.add requires at least one nn.memory operand"):
        call_nn_module._lower_mixed_binary_expr(
            BinaryExprAST(op="add", lhs=ConstAST(1), rhs=ConstAST(2), location=None),
            None,
            None,
            no_memory_ctx,
        )

    invalid_result_block = Block(arg_types=[tensor_type, i32])
    invalid_result_expr = BinaryExprAST(op="add", lhs=tensor, rhs=ConstAST(1), location=None)
    invalid_result_ctx = EmitContext(
        builder=invalid_result_block,
        symbols={"x": invalid_result_block.args[0], "scale": invalid_result_block.args[1]},
        types={_expr_key(tensor): tensor_type, _expr_key(invalid_result_expr): i32},
    )
    invalid_result_ctx._set_cache(_expr_key(tensor), invalid_result_block.args[0])
    with pytest.raises(LoweringError, match="Binary op result must be nn.memory"):
        call_nn_module._lower_mixed_binary_expr(
            invalid_result_expr,
            invalid_result_block.args[0],
            invalid_result_block.args[1],
            invalid_result_ctx,
        )

    lhs_symbol = ScalarArgAST(name="lhs", value_type=int, is_symbolic=True, location=None)
    rhs_symbol = ScalarArgAST(name="rhs", value_type=int, is_symbolic=True, location=None)
    lhs_type = call_nn_module.SymbolValueType.from_expr("M")
    rhs_type = call_nn_module.SymbolValueType.from_expr("N")
    unsupported_block = Block(arg_types=[lhs_type, rhs_type])
    unsupported_ctx = EmitContext(
        builder=unsupported_block,
        symbols={"lhs": unsupported_block.args[0], "rhs": unsupported_block.args[1]},
        types={_expr_key(lhs_symbol): lhs_type, _expr_key(rhs_symbol): rhs_type},
    )
    unsupported_ctx._set_cache(_expr_key(lhs_symbol), unsupported_block.args[0])
    unsupported_ctx._set_cache(_expr_key(rhs_symbol), unsupported_block.args[1])
    with pytest.raises(LoweringError, match="Unsupported symbol binary op"):
        call_nn_module._emit_binary(
            BinaryExprAST(op="pow", lhs=lhs_symbol, rhs=rhs_symbol, location=None),
            unsupported_ctx,
        )


# CALL-NN-S7-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 补齐 call_nn 的 infer/unary/mixed-scalar 与 memory-memory 剩余边界。
# 测试目的: 锁定 call_nn facade 在非法节点、dtype cast、broadcast 和 unary 默认参数路径上的稳定行为。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_nn.py -k test_call_nn_private_additional_error_and_broadcast_edges
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/call_nn.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_nn.py
def test_call_nn_private_additional_error_and_broadcast_edges() -> None:
    tensor = TensorAST(name="x", memory=Memory([2, 2], NumericType.Float32), location=None)
    tensor_type = _memory_type([2, 2], [2, 1], f32)
    symbol_scalar = ScalarArgAST(name="sym", value_type=int, is_symbolic=True, location=None)
    scalar = ScalarArgAST(name="scale", value_type=int, is_symbolic=False, location=None)

    with pytest.raises(LoweringError, match="infer_nn_type only handles nn elementwise AST nodes"):
        call_nn_module.infer_nn_type(ConstAST(1), {})  # type: ignore[arg-type]
    with pytest.raises(LoweringError, match="Unary op operand must be nn.memory"):
        call_nn_module._infer_unary_type(
            NnUnaryAST(kind="relu", value=scalar, location=None),
            {_expr_key(scalar): i32},
            runtime_values=None,
            config=None,
        )
    with pytest.raises(LoweringError, match="Unsupported unary helper"):
        call_nn_module._infer_unary_type(
            NnUnaryAST(kind="unknown", value=tensor, location=None),
            {_expr_key(tensor): tensor_type},
            runtime_values=None,
            config=None,
        )
    with pytest.raises(LoweringError, match="Unsupported binary op: pow"):
        call_nn_module._infer_binary_type(
            BinaryExprAST(op="pow", lhs=tensor, rhs=tensor, location=None),
            {_expr_key(tensor): tensor_type},
            runtime_values=None,
            config=None,
        )
    with pytest.raises(LoweringError, match="nn.add requires at least one nn.memory operand"):
        call_nn_module._infer_binary_type(
            BinaryExprAST(op="add", lhs=ConstAST(True), rhs=ConstAST(False), location=None),
            {},
            runtime_values=None,
            config=None,
        )

    symbol_memory_result = call_nn_module._infer_binary_type(
        BinaryExprAST(op="add", lhs=tensor, rhs=symbol_scalar, location=None),
        {_expr_key(tensor): tensor_type, _expr_key(symbol_scalar): call_nn_module.SymbolValueType.from_expr("K")},
        runtime_values=None,
        config=None,
    )
    assert symbol_memory_result == tensor_type

    symbol_block = Block(arg_types=[call_nn_module.SymbolValueType.from_expr("M"), i32, f32, Float16Type()])
    symbol_ctx = EmitContext(builder=symbol_block, symbols={}, types={})
    same_int = call_nn_module._cast_nn_scalar_operand(symbol_block.args[1], i32, symbol_ctx, None)
    assert same_int is symbol_block.args[1]
    same_float = call_nn_module._cast_nn_scalar_operand(symbol_block.args[2], f32, symbol_ctx, None)
    assert same_float is symbol_block.args[2]
    with pytest.raises(LoweringError, match="integer width conversion is unsupported"):
        call_nn_module._cast_nn_scalar_operand(symbol_block.args[1], i1, symbol_ctx, None)
    with pytest.raises(LoweringError, match="integer/float or symbol.int"):
        call_nn_module._cast_nn_scalar_operand(symbol_block.args[1], IntAttr(1), symbol_ctx, None)
    with pytest.raises(LoweringError, match="integer/float or symbol.int"):
        call_nn_module._cast_nn_scalar_operand(symbol_block.args[0], IntAttr(1), symbol_ctx, None)
    with pytest.raises(LoweringError, match="integer/float or symbol.int"):
        call_nn_module._cast_nn_scalar_operand(symbol_block.args[3], IntAttr(1), symbol_ctx, None)

    runtime_symbol_ctx = EmitContext(builder=Block(), symbols={}, types={}, config={"__runtime_values__": {"sym": 7}})
    runtime_symbol_value = call_nn_module._materialize_symbol_binary_operand(symbol_scalar, i32, runtime_symbol_ctx, None)
    assert isinstance(runtime_symbol_value.owner, SymbolConstOp)
    assert int(runtime_symbol_value.owner.value.data) == 7

    const_ctx = EmitContext(builder=Block(), symbols={}, types={})
    const_value = call_nn_module._materialize_mixed_binary_scalar_operand(ConstAST(4), None, i32, const_ctx, None, cast_to_element_type=False)
    assert isinstance(const_value.owner, SymbolConstOp)
    with pytest.raises(LoweringError, match="could not be materialized"):
        call_nn_module._materialize_mixed_binary_scalar_operand(scalar, None, i32, EmitContext(builder=Block(), symbols={}, types={}), None)

    unary_block = Block(arg_types=[tensor_type])
    unary_ctx = EmitContext(
        builder=unary_block,
        symbols={"x": unary_block.args[0]},
        types={_expr_key(tensor): tensor_type},
    )
    unary_ctx._set_cache(_expr_key(tensor), unary_block.args[0])
    leaky_result = call_nn_module._emit_unary(NnUnaryAST(kind="leaky_relu", value=tensor, location=None), unary_ctx)
    hard_sigmoid_result = call_nn_module._emit_unary(NnUnaryAST(kind="hard_sigmoid", value=tensor, location=None), unary_ctx)
    unary_ops = list(unary_block.ops)
    assert isinstance(unary_ops[0], arith.ConstantOp)
    assert leaky_result is unary_ops[1].result
    assert isinstance(unary_ops[2], arith.ConstantOp)
    assert hard_sigmoid_result is unary_ops[-1].result

    bad_unary_expr = NnUnaryAST(kind="relu", value=tensor, location=None)
    bad_unary_block = Block(arg_types=[tensor_type])
    bad_unary_ctx = EmitContext(
        builder=bad_unary_block,
        symbols={"x": bad_unary_block.args[0]},
        types={_expr_key(tensor): tensor_type, _expr_key(bad_unary_expr): i32},
    )
    bad_unary_ctx._set_cache(_expr_key(tensor), bad_unary_block.args[0])
    with pytest.raises(LoweringError, match="Unary op result must be nn.memory"):
        call_nn_module._emit_unary(bad_unary_expr, bad_unary_ctx)

    lhs = TensorAST(name="lhs", memory=Memory([1, 2], NumericType.Int32), location=None)
    rhs = TensorAST(name="rhs", memory=Memory([2, 2], NumericType.Float32), location=None)
    lhs_type = _memory_type([1, 2], [2, 1], i32)
    rhs_type = _memory_type([2, 2], [2, 1], f32)
    binary_expr = BinaryExprAST(op="add", lhs=lhs, rhs=rhs, location=None)
    binary_block = Block(arg_types=[lhs_type, rhs_type])
    binary_ctx = EmitContext(
        builder=binary_block,
        symbols={"lhs": binary_block.args[0], "rhs": binary_block.args[1]},
        types={_expr_key(lhs): lhs_type, _expr_key(rhs): rhs_type},
    )
    binary_ctx._set_cache(_expr_key(lhs), binary_block.args[0])
    binary_ctx._set_cache(_expr_key(rhs), binary_block.args[1])
    result = call_nn_module._emit_binary(binary_expr, binary_ctx)
    binary_ops = list(binary_block.ops)
    assert [type(op) for op in binary_ops] == [NnCastOp, NnBroadcastOp, NnAddOp]
    assert result is binary_ops[-1].result

    bad_binary_ctx = EmitContext(
        builder=Block(arg_types=[lhs_type, rhs_type]),
        symbols={},
        types={_expr_key(lhs): lhs_type, _expr_key(rhs): rhs_type, _expr_key(binary_expr): i32},
    )
    bad_binary_ctx._set_cache(_expr_key(lhs), bad_binary_ctx.builder.args[0])
    bad_binary_ctx._set_cache(_expr_key(rhs), bad_binary_ctx.builder.args[1])
    with pytest.raises(LoweringError, match="Binary op result must be nn.memory"):
        call_nn_module._emit_binary(binary_expr, bad_binary_ctx)
    with pytest.raises(LoweringError, match="Unsupported binary op: pow"):
        call_nn_module._emit_binary(
            BinaryExprAST(op="pow", lhs=lhs, rhs=rhs, location=None),
            binary_ctx,
        )


# CALL-NN-S7-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 补齐 call_nn 剩余推导与 lowering 分支。
# 测试目的: 锁定 symbol/memory 混合场景、回退错误短语和二次 symbol lowering 分派不回退。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_nn.py -k test_call_nn_private_remaining_branch_edges
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/call_nn.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_nn.py
def test_call_nn_private_remaining_branch_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    tensor = TensorAST(name="x", memory=Memory([2, 2], NumericType.Float32), location=None)
    tensor_type = _memory_type([2, 2], [2, 1], f32)
    tensor_type_map = {_expr_key(tensor): tensor_type}
    symbol_lhs = ScalarArgAST(name="lhs", value_type=int, is_symbolic=True, location=None)
    symbol_rhs = ScalarArgAST(name="rhs", value_type=int, is_symbolic=True, location=None)
    bad_scalar = ScalarArgAST(name="bad", value_type=int, is_symbolic=False, location=None)
    symbol_type_map = {
        _expr_key(symbol_lhs): call_nn_module.SymbolValueType.from_expr("M"),
        _expr_key(symbol_rhs): call_nn_module.SymbolValueType.from_expr("N"),
    }

    with pytest.raises(LoweringError, match="Unsupported symbol binary op"):
        call_nn_module._infer_binary_type(
            BinaryExprAST(op="pow", lhs=symbol_lhs, rhs=symbol_rhs, location=None),
            symbol_type_map,
            runtime_values=None,
            config=None,
        )
    with pytest.raises(LoweringError, match="Binary op operands must have nn.memory type"):
        call_nn_module._infer_binary_type(
            BinaryExprAST(op="sub", lhs=ConstAST(True), rhs=ConstAST(False), location=None),
            {},
            runtime_values=None,
            config=None,
        )
    with pytest.raises(LoweringError, match="Binary op operands must have nn.memory type"):
        call_nn_module._infer_binary_type(
            BinaryExprAST(
                op="sub",
                lhs=tensor,
                rhs=bad_scalar,
                location=None,
            ),
            {
                _expr_key(tensor): tensor_type,
                _expr_key(bad_scalar): object(),
            },
            runtime_values=None,
            config=None,
        )

    original_memory_to_runtime = call_nn_module._nn_memory_type_to_memory
    monkeypatch.setattr(call_nn_module, "_nn_memory_type_to_memory", lambda *_args, **_kwargs: None)
    with pytest.raises(LoweringError, match="nn.add requires at least one nn.memory operand"):
        call_nn_module._infer_binary_type(
            BinaryExprAST(op="add", lhs=tensor, rhs=tensor, location=None),
            tensor_type_map,
            runtime_values=None,
            config=None,
        )
    with pytest.raises(LoweringError, match="Binary op operands must have nn.memory type"):
        call_nn_module._infer_binary_type(
            BinaryExprAST(op="sub", lhs=tensor, rhs=tensor, location=None),
            tensor_type_map,
            runtime_values=None,
            config=None,
        )
    monkeypatch.setattr(call_nn_module, "_nn_memory_type_to_memory", original_memory_to_runtime)

    monkeypatch.setattr(call_nn_module._KG_OPERATION_NN, "add", lambda *_args, **_kwargs: object())
    with pytest.raises(LoweringError, match="nn.add requires at least one nn.memory operand"):
        call_nn_module._infer_binary_type(
            BinaryExprAST(op="add", lhs=tensor, rhs=tensor, location=None),
            tensor_type_map,
            runtime_values=None,
            config=None,
        )

    symbol_value_type = call_nn_module.SymbolValueType.from_expr("K")
    assert call_nn_module._normalize_mixed_scalar_element_type(symbol_value_type, None) == symbol_value_type

    runtime_symbol = ScalarArgAST(name="sym", value_type=int, is_symbolic=True, location=None)
    runtime_symbol_block = Block(arg_types=[call_nn_module.SymbolValueType.from_expr("K")])
    runtime_symbol_ctx = EmitContext(
        builder=runtime_symbol_block,
        symbols={"sym": runtime_symbol_block.args[0]},
        types={_expr_key(runtime_symbol): runtime_symbol_block.args[0].type},
        config={"__runtime_values__": {"sym": SymbolDim("K")}},
    )
    runtime_symbol_ctx._set_cache(_expr_key(runtime_symbol), runtime_symbol_block.args[0])
    assert (
        call_nn_module._materialize_symbol_binary_operand(runtime_symbol, i32, runtime_symbol_ctx, None)
        is runtime_symbol_block.args[0]
    )

    monkeypatch.setattr(call_nn_module._KG_OPERATION_NN, "floordiv", lambda *_args, **_kwargs: object())
    with pytest.raises(LoweringError, match="Binary op result must be nn.memory"):
        call_nn_module._infer_mixed_binary_type(tensor_type, i32, None, op_name="floordiv")

    with pytest.raises(LoweringError, match="Binary op operands must have nn.memory type"):
        call_nn_module._lower_mixed_binary_expr(
            BinaryExprAST(op="sub", lhs=ConstAST(True), rhs=ConstAST(False), location=None),
            None,
            None,
            EmitContext(builder=Block(), symbols={}, types={}),
        )

    mixed_scalar = ScalarArgAST(name="scale", value_type=int, is_symbolic=False, location=None)
    mixed_expr = BinaryExprAST(op="pow", lhs=tensor, rhs=mixed_scalar, location=None)
    mixed_block = Block(arg_types=[tensor_type, i32])
    mixed_ctx = EmitContext(
        builder=mixed_block,
        symbols={"x": mixed_block.args[0], "scale": mixed_block.args[1]},
        types={_expr_key(mixed_expr): tensor_type},
    )
    with pytest.raises(LoweringError, match="Unsupported binary op: pow"):
        call_nn_module._lower_mixed_binary_expr(mixed_expr, mixed_block.args[0], mixed_block.args[1], mixed_ctx)

    unary_expr = NnUnaryAST(kind="unknown", value=tensor, location=None)
    unary_block = Block(arg_types=[tensor_type])
    unary_ctx = EmitContext(
        builder=unary_block,
        symbols={"x": unary_block.args[0]},
        types={_expr_key(tensor): tensor_type, _expr_key(unary_expr): tensor_type},
    )
    unary_ctx._set_cache(_expr_key(tensor), unary_block.args[0])
    with pytest.raises(LoweringError, match="Unsupported unary helper"):
        call_nn_module._emit_unary(unary_expr, unary_ctx)

    symbol_block = Block(arg_types=[symbol_type_map[_expr_key(symbol_lhs)], symbol_type_map[_expr_key(symbol_rhs)]])
    symbol_ctx = EmitContext(
        builder=symbol_block,
        symbols={"lhs": symbol_block.args[0], "rhs": symbol_block.args[1]},
        types={
            _expr_key(symbol_lhs): symbol_block.args[0].type,
            _expr_key(symbol_rhs): symbol_block.args[1].type,
        },
    )
    symbol_ctx._set_cache(_expr_key(symbol_lhs), symbol_block.args[0])
    symbol_ctx._set_cache(_expr_key(symbol_rhs), symbol_block.args[1])
    symbol_expr = BinaryExprAST(op="add", lhs=symbol_lhs, rhs=symbol_rhs, location=None)
    symbol_ctx.types[_expr_key(symbol_expr)] = call_nn_module.SymbolValueType.from_expr("M + N")
    original_symbol_scalar_expr_text = call_nn_module._symbol_scalar_expr_text
    monkeypatch.setattr(call_nn_module, "_symbol_scalar_expr_text", lambda *_args, **_kwargs: None)
    symbol_result = call_nn_module._emit_binary(symbol_expr, symbol_ctx)
    symbol_ops = list(symbol_block.ops)
    assert len(symbol_ops) == 1
    assert isinstance(symbol_ops[0], SymbolAddOp)
    assert symbol_result is symbol_ops[0].result

    bad_symbol_expr = BinaryExprAST(op="sub", lhs=symbol_lhs, rhs=symbol_rhs, location=None)
    bad_symbol_ctx = EmitContext(
        builder=Block(arg_types=[symbol_type_map[_expr_key(symbol_lhs)], symbol_type_map[_expr_key(symbol_rhs)]]),
        symbols={},
        types={
            _expr_key(symbol_lhs): symbol_type_map[_expr_key(symbol_lhs)],
            _expr_key(symbol_rhs): symbol_type_map[_expr_key(symbol_rhs)],
            _expr_key(bad_symbol_expr): i32,
        },
    )
    bad_symbol_ctx._set_cache(_expr_key(symbol_lhs), bad_symbol_ctx.builder.args[0])
    bad_symbol_ctx._set_cache(_expr_key(symbol_rhs), bad_symbol_ctx.builder.args[1])
    with pytest.raises(LoweringError, match="Symbol binary op result must be !symbol.int"):
        call_nn_module._emit_binary(bad_symbol_expr, bad_symbol_ctx)
    monkeypatch.setattr(call_nn_module, "_symbol_scalar_expr_text", original_symbol_scalar_expr_text)

    rhs_tensor = TensorAST(name="rhs", memory=Memory([2, 2], NumericType.Float32), location=None)
    null_mixed_ctx = EmitContext(
        builder=Block(arg_types=[tensor_type]),
        symbols={},
        types={_expr_key(tensor): tensor_type},
    )
    null_mixed_ctx.symbols["x"] = null_mixed_ctx.builder.args[0]
    null_mixed_ctx._set_cache(_expr_key(tensor), null_mixed_ctx.builder.args[0])
    monkeypatch.setattr(call_nn_module, "_lower_mixed_binary_expr", lambda expr, lhs, rhs, ctx: None)
    with pytest.raises(LoweringError, match="Binary op operands must have nn.memory type"):
        call_nn_module._emit_binary(
            BinaryExprAST(op="add", lhs=ConstAST(1), rhs=tensor, location=None),
            null_mixed_ctx,
        )

    unsupported_binary_expr = BinaryExprAST(op="pow", lhs=tensor, rhs=rhs_tensor, location=None)
    unsupported_binary_block = Block(arg_types=[tensor_type, tensor_type])
    unsupported_binary_ctx = EmitContext(
        builder=unsupported_binary_block,
        symbols={"lhs": unsupported_binary_block.args[0], "rhs": unsupported_binary_block.args[1]},
        types={
            _expr_key(tensor): tensor_type,
            _expr_key(rhs_tensor): tensor_type,
            _expr_key(unsupported_binary_expr): tensor_type,
        },
    )
    unsupported_binary_ctx._set_cache(_expr_key(tensor), unsupported_binary_block.args[0])
    unsupported_binary_ctx._set_cache(_expr_key(rhs_tensor), unsupported_binary_block.args[1])
    with pytest.raises(LoweringError, match="Unsupported binary op: pow"):
        call_nn_module._emit_binary(unsupported_binary_expr, unsupported_binary_ctx)


# CALL-NN-S7-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 补齐 compare element-type 提升与 symbol-only pow 的直接 helper 分支。
# 测试目的: 锁定 `_infer_compare_type` 的 element promotion 和 `_emit_binary` 的 symbol 非法算子诊断不回退。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_nn.py -k test_call_nn_private_compare_promotion_and_symbol_pow_edges
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/call_nn.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_nn.py
def test_call_nn_private_compare_promotion_and_symbol_pow_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    lhs = TensorAST(name="lhs", memory=Memory([2, 2], NumericType.Int32), location=None)
    rhs = TensorAST(name="rhs", memory=Memory([2, 2], NumericType.Float32), location=None)
    lhs_type = _memory_type([2, 2], [2, 1], i32)
    rhs_type = _memory_type([2, 2], [2, 1], f32)

    compare_result = call_nn_module._infer_compare_type(
        CompareExprAST(op="eq", lhs=lhs, rhs=rhs, location=None),
        {_expr_key(lhs): lhs_type, _expr_key(rhs): rhs_type},
        runtime_values=None,
        config=None,
    )
    assert isinstance(compare_result, NnMemoryType)
    assert compare_result.element_type == i1

    lhs_symbol = ScalarArgAST(name="lhs", value_type=int, is_symbolic=True, location=None)
    rhs_symbol = ScalarArgAST(name="rhs", value_type=int, is_symbolic=True, location=None)
    symbol_block = Block(arg_types=[call_nn_module.SymbolValueType.from_expr("M"), call_nn_module.SymbolValueType.from_expr("N")])
    symbol_ctx = EmitContext(
        builder=symbol_block,
        symbols={"lhs": symbol_block.args[0], "rhs": symbol_block.args[1]},
        types={
            _expr_key(lhs_symbol): symbol_block.args[0].type,
            _expr_key(rhs_symbol): symbol_block.args[1].type,
        },
    )
    symbol_ctx._set_cache(_expr_key(lhs_symbol), symbol_block.args[0])
    symbol_ctx._set_cache(_expr_key(rhs_symbol), symbol_block.args[1])

    with pytest.raises(LoweringError, match="Unsupported symbol binary op"):
        call_nn_module._emit_binary(
            BinaryExprAST(op="pow", lhs=lhs_symbol, rhs=rhs_symbol, location=None),
            symbol_ctx,
        )

    monkeypatch.setattr(call_nn_module, "_symbol_scalar_expr_text", lambda *_args, **_kwargs: None)
    with pytest.raises(LoweringError, match="Unsupported symbol binary op"):
        call_nn_module._emit_binary(
            BinaryExprAST(op="pow", lhs=lhs_symbol, rhs=rhs_symbol, location=None),
            symbol_ctx,
        )
