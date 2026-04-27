"""Emit MLIR public integration tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 只覆盖 `emit_mlir`、`build_func_op`、`build_func_op_from_ast` 的公开行为。
- 不再把 `emit.core` 私有 helper、缓存接口或内部错误类型视为公开合同。

使用示例:
- pytest -q test/dsl/test_emit_mlir.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/visitor.py
- 功能实现: kernel_gen/dsl/mlir_gen/emit/__init__.py
- 功能实现: kernel_gen/dsl/mlir_gen/function_builder.py
- Spec 文档: spec/dsl/ast/visitor.md
- Spec 文档: spec/dsl/emit_mlir.md
- Spec 文档: spec/dsl/mlir_gen.md
- 测试文件: test/dsl/test_emit_mlir.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.dialects import arith, func
from xdsl.dialects.builtin import ArrayAttr, IntAttr, f32
from xdsl.ir import Block

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.arch import ArchGetThreadNumOp
from kernel_gen.dialect.dma import DmaAllocOp, DmaCopyOp, DmaFreeOp
from kernel_gen.dialect.nn import NnMatmulOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolToFloatOp, SymbolValueType
from kernel_gen.dsl import build_func_op, build_func_op_from_ast, parse_function
from kernel_gen.dsl.ast import ArchQueryAST, AstParseError, ConstAST, ScalarArgAST, SymbolToFloatAST, TensorAST
from kernel_gen.dsl.ast.visitor import AstVisitorError
from kernel_gen.dsl.mlir_gen.emit import EmitContext, emit_mlir, memory_type_from_memory
from kernel_gen.operation import copy as dma_copy
from kernel_gen.operation import free as dma_free
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType
import kernel_gen.operation.nn as nn


def _expr_cache_key(expr: object) -> int:
    return id(expr)


def _tensor_arg(shape: list[object], *, dtype: NumericType = NumericType.Float32, space: MemorySpace = MemorySpace.GM) -> Memory:
    return Memory(shape, dtype, space=space)


def test_emit_mlir_lowers_const_through_public_entry() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    result = emit_mlir(ConstAST(1), ctx)

    body_ops = list(block.ops)
    assert len(body_ops) == 1
    assert isinstance(body_ops[0], arith.ConstantOp)
    assert result is body_ops[0].result


def test_emit_mlir_uses_symbol_table_for_tensor() -> None:
    memory = Memory([2, 3], NumericType.Float32, space=MemorySpace.GM)
    tensor = TensorAST(name="x", memory=memory, location=None)
    tensor_type = NnMemoryType(
        ArrayAttr([IntAttr(2), IntAttr(3)]),
        ArrayAttr([IntAttr(3), IntAttr(1)]),
        f32,
        NnMemorySpaceAttr.from_name("global"),
    )
    block = Block(arg_types=[tensor_type])
    ctx = EmitContext(builder=block, symbols={"x": block.args[0]}, types={_expr_cache_key(tensor): tensor_type})

    result = emit_mlir(tensor, ctx)

    assert result is block.args[0]


def test_emit_mlir_lowers_symbol_to_float_through_public_entry() -> None:
    source = ScalarArgAST(name="n", value_type=int, is_symbolic=True, location=None)
    block = Block(arg_types=[SymbolValueType.from_expr("N")])
    ctx = EmitContext(builder=block, symbols={"n": block.args[0]}, types={_expr_cache_key(source): block.args[0].type})
    emit_mlir(source, ctx)

    result = emit_mlir(SymbolToFloatAST(source=source, location=None), ctx)

    body_ops = list(block.ops)
    assert len(body_ops) == 1
    assert isinstance(body_ops[0], SymbolToFloatOp)
    assert result is body_ops[0].result


def test_emit_mlir_rejects_non_symbol_source_for_symbol_to_float() -> None:
    source = ScalarArgAST(name="x", value_type=float, is_symbolic=False, location=None)
    block = Block(arg_types=[f32])
    ctx = EmitContext(builder=block, symbols={"x": block.args[0]}, types={_expr_cache_key(source): block.args[0].type})
    emit_mlir(source, ctx)

    with pytest.raises(ValueError, match='symbol.to_float source must have type !symbol.int<"expr">'):
        emit_mlir(SymbolToFloatAST(source=source, location=None), ctx)


def test_emit_mlir_lowers_arch_query_through_public_entry() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    result = emit_mlir(ArchQueryAST(query_name="get_thread_num", location=None), ctx)

    body_ops = list(block.ops)
    assert len(body_ops) == 1
    assert isinstance(body_ops[0], ArchGetThreadNumOp)
    assert result is body_ops[0].result


def test_build_func_op_from_ast_matches_public_add_lowering() -> None:
    def add(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x + y

    lhs = _tensor_arg([2, 2])
    rhs = _tensor_arg([2, 2])
    func_ast = parse_function(add)

    direct_func = build_func_op(add, lhs, rhs)
    ast_func = build_func_op_from_ast(func_ast, runtime_args=[lhs, rhs])

    direct_ops = [type(op) for op in direct_func.body.block.ops]
    ast_ops = [type(op) for op in ast_func.body.block.ops]
    assert direct_ops == ast_ops
    assert isinstance(direct_func.body.block.ops.first, object)


def test_build_func_op_reports_broadcast_mismatch_via_public_error() -> None:
    def add(x: "Tensor[f32, A, B]", y: "Tensor[f32, A, C]") -> "Tensor[f32, A, B]":
        return x + y

    with pytest.raises(AstVisitorError, match="Implicit broadcast dimension mismatch") as exc_info:
        build_func_op(add, _tensor_arg(["A", "B"]), _tensor_arg(["A", "C"]))
    assert exc_info.value.location is not None


def test_build_func_op_lowers_dma_copy_and_free_public_helpers() -> None:
    def dma_kernel(src: "Tensor[f32, 2, 2]") -> None:
        local = dma_copy(src, MemorySpace.SM)
        dma_free(local)

    func_op = build_func_op(dma_kernel, _tensor_arg([2, 2]))

    body_ops = list(func_op.body.block.ops)
    assert any(isinstance(op, DmaAllocOp) for op in body_ops)
    assert any(isinstance(op, DmaCopyOp) for op in body_ops)
    assert any(isinstance(op, DmaFreeOp) for op in body_ops)
    assert isinstance(body_ops[-1], func.ReturnOp)


def test_build_func_op_lowers_nn_matmul_public_helper() -> None:
    def matmul_kernel(lhs: "Tensor[f32, 2, 3]", rhs: "Tensor[f32, 3, 4]") -> "Tensor[f32, 2, 4]":
        return nn.matmul(lhs, rhs)

    func_op = build_func_op(matmul_kernel, _tensor_arg([2, 3]), _tensor_arg([3, 4]))

    matmul_ops = [op for op in func_op.body.block.ops if isinstance(op, NnMatmulOp)]
    assert len(matmul_ops) == 1
    assert matmul_ops[0].result.type.shape.data[0].data == 2
    assert matmul_ops[0].result.type.shape.data[1].data == 4


def test_parse_function_public_error_path_stays_ast_parse_error() -> None:
    def bad(x):
        return x

    with pytest.raises(AstParseError):
        parse_function(bad)


def test_emit_package_root_memory_type_from_memory_keeps_public_layout() -> None:
    mem_type = memory_type_from_memory(Memory([2, "N"], NumericType.Float32, space=MemorySpace.TSM))

    assert [dim.data for dim in mem_type.shape.data] == [2, "N"]
    assert [dim.data for dim in mem_type.stride.data] == ["N", 1]
    assert mem_type.element_type == f32
    assert mem_type.space == NnMemorySpaceAttr.from_name("tsm")
