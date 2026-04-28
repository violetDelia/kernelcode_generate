"""Emit NN public integration tests.

创建者: OpenAI
最后一次更改: 小李飞刀

功能说明:
- 只覆盖 `kernel_gen.dsl.mlir_gen.emit` 包根公开入口的 NN family 可观察行为。
- 不再把 `call_nn.py` 的私有 helper、缓存方法或内部模块结构当成测试合同。

使用示例:
- pytest -q test/dsl/mlir_gen/emit/test_call_nn.py

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/emit/__init__.py
- Spec 文档: spec/dsl/emit_mlir.md
- 测试文件: test/dsl/mlir_gen/emit/test_call_nn.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.dialects.builtin import ArrayAttr, Float16Type, IntAttr, f32, i32
from xdsl.ir import Block

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.nn import (
    NnAddOp,
    NnBroadcastOp,
    NnCastOp,
    NnEqOp,
    NnMemorySpaceAttr,
    NnMemoryType,
    NnReluOp,
)
from kernel_gen.dialect.symbol import SymbolAddOp, SymbolConstOp, SymbolToFloatOp, SymbolValueType
from kernel_gen.dsl.ast import BinaryExprAST, CompareExprAST, ConstAST, NnUnaryAST, ScalarArgAST, TensorAST
from kernel_gen.dsl.mlir_gen.emit import EmitContext, emit_mlir
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType


def _memory_type(shape: list[int], strides: list[int], element_type: object) -> NnMemoryType:
    return NnMemoryType(
        ArrayAttr([IntAttr(dim) for dim in shape]),
        ArrayAttr([IntAttr(stride) for stride in strides]),
        element_type,
        NnMemorySpaceAttr.from_name("global"),
    )


def _expr_cache_key(expr: object) -> int:
    return id(expr)


def test_emit_mlir_lowers_nn_relu() -> None:
    tensor = TensorAST(name="x", memory=Memory([2, 2], NumericType.Float32), location=None)
    tensor_type = _memory_type([2, 2], [2, 1], f32)
    block = Block(arg_types=[tensor_type])
    ctx = EmitContext(builder=block, symbols={"x": block.args[0]}, types={_expr_cache_key(tensor): tensor_type})
    emit_mlir(tensor, ctx)

    result = emit_mlir(NnUnaryAST(kind="relu", value=tensor, location=None), ctx)

    body_ops = list(block.ops)
    assert len(body_ops) == 1
    assert isinstance(body_ops[0], NnReluOp)
    assert result is body_ops[0].result


def test_emit_mlir_lowers_nn_add_mixed_const_via_symbol_const() -> None:
    tensor = TensorAST(name="x", memory=Memory([2, 2], NumericType.Float16), location=None)
    tensor_type = _memory_type([2, 2], [2, 1], Float16Type())
    block = Block(arg_types=[tensor_type])
    ctx = EmitContext(builder=block, symbols={"x": block.args[0]}, types={_expr_cache_key(tensor): tensor_type})
    emit_mlir(tensor, ctx)

    result = emit_mlir(BinaryExprAST(op="add", lhs=tensor, rhs=ConstAST(1), location=None), ctx)

    body_ops = list(block.ops)
    assert [type(op) for op in body_ops] == [SymbolConstOp, SymbolToFloatOp, NnAddOp]
    assert result is body_ops[-1].result


def test_emit_mlir_lowers_nn_compare_cast_and_broadcast() -> None:
    lhs = TensorAST(name="lhs", memory=Memory([2, 2], NumericType.Float32), location=None)
    rhs = TensorAST(name="rhs", memory=Memory([1, 2], NumericType.Int32), location=None)
    lhs_type = _memory_type([2, 2], [2, 1], f32)
    rhs_type = _memory_type([1, 2], [2, 1], i32)
    block = Block(arg_types=[lhs_type, rhs_type])
    ctx = EmitContext(
        builder=block,
        symbols={"lhs": block.args[0], "rhs": block.args[1]},
        types={_expr_cache_key(lhs): lhs_type, _expr_cache_key(rhs): rhs_type},
    )
    emit_mlir(lhs, ctx)
    emit_mlir(rhs, ctx)

    result = emit_mlir(CompareExprAST(op="eq", lhs=lhs, rhs=rhs, location=None), ctx)

    body_ops = list(block.ops)
    assert [type(op) for op in body_ops] == [NnCastOp, NnBroadcastOp, NnEqOp]
    assert result is body_ops[-1].result


def test_emit_mlir_lowers_symbol_add() -> None:
    lhs = ScalarArgAST(name="lhs", value_type=int, is_symbolic=True, location=None)
    rhs = ScalarArgAST(name="rhs", value_type=int, is_symbolic=True, location=None)
    lhs_type = SymbolValueType.from_expr("M")
    rhs_type = SymbolValueType.from_expr("N")
    block = Block(arg_types=[lhs_type, rhs_type])
    ctx = EmitContext(
        builder=block,
        symbols={"lhs": block.args[0], "rhs": block.args[1]},
        types={_expr_cache_key(lhs): lhs_type, _expr_cache_key(rhs): rhs_type},
    )
    emit_mlir(lhs, ctx)
    emit_mlir(rhs, ctx)

    result = emit_mlir(BinaryExprAST(op="add", lhs=lhs, rhs=rhs, location=None), ctx)

    body_ops = list(block.ops)
    assert len(body_ops) == 1
    assert isinstance(body_ops[0], SymbolAddOp)
    assert result is body_ops[0].result


def test_emit_mlir_rejects_unsupported_symbol_binary_op() -> None:
    lhs = ScalarArgAST(name="lhs", value_type=int, is_symbolic=True, location=None)
    rhs = ScalarArgAST(name="rhs", value_type=int, is_symbolic=True, location=None)
    lhs_type = SymbolValueType.from_expr("M")
    rhs_type = SymbolValueType.from_expr("N")
    block = Block(arg_types=[lhs_type, rhs_type])
    ctx = EmitContext(
        builder=block,
        symbols={"lhs": block.args[0], "rhs": block.args[1]},
        types={_expr_cache_key(lhs): lhs_type, _expr_cache_key(rhs): rhs_type},
    )
    emit_mlir(lhs, ctx)
    emit_mlir(rhs, ctx)

    with pytest.raises(KernelCodeError, match="Unsupported symbol binary op"):
        emit_mlir(BinaryExprAST(op="pow", lhs=lhs, rhs=rhs, location=None), ctx)
