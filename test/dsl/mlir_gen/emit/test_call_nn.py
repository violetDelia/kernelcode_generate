"""Emit call_nn tests.

创建者: OpenAI
最后一次更改: OpenAI

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
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolToFloatOp
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
