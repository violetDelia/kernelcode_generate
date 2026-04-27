"""AST visitor public integration tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 只验证 `AstVisitor`、`EmitContext`、`emit_mlir`、`build_func_op`、`build_func_op_from_ast` 的公开集成行为。
- 不再把 `emit.core` 私有 helper、缓存接口或内部错误类型当作公开合同。

使用示例:
- pytest -q test/dsl/ast/test_visitor_integration.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/visitor.py
- 功能实现: kernel_gen/dsl/mlir_gen/emit/__init__.py
- 功能实现: kernel_gen/dsl/mlir_gen/function_builder.py
- Spec 文档: spec/dsl/ast/visitor.md
- Spec 文档: spec/dsl/emit_mlir.md
- Spec 文档: spec/dsl/mlir_gen.md
- 测试文件: test/dsl/ast/test_visitor_integration.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.dialects import func
from xdsl.ir import Block

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaCopyOp, DmaFreeOp
from kernel_gen.dialect.nn import NnAddOp
from kernel_gen.dialect.symbol import SymbolGetDimOp
from kernel_gen.dsl import (
    AstVisitor,
    AstVisitorError,
    EmitContext,
    build_func_op,
    build_func_op_from_ast,
    emit_mlir,
    parse_function,
)
from kernel_gen.dsl.ast import SourceLocation, VarAST
from kernel_gen.dsl.mlir_gen.emit import memory_type_from_memory
from kernel_gen.operation import copy as dma_copy
from kernel_gen.operation import free as dma_free
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType


def _tensor_arg(shape: list[object], *, space: MemorySpace = MemorySpace.GM) -> Memory:
    return Memory(shape, NumericType.Float32, space=space)


def test_ast_visitor_visit_function_lowers_public_add_kernel() -> None:
    def add(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x + y

    func_ast = parse_function(add)
    lhs_type = memory_type_from_memory(_tensor_arg([2, 2]))
    rhs_type = memory_type_from_memory(_tensor_arg([2, 2]))
    block = Block(arg_types=[lhs_type, rhs_type])
    ctx = EmitContext(
        builder=block,
        symbols={},
        types={id(func_ast.inputs[0]): lhs_type, id(func_ast.inputs[1]): rhs_type},
    )

    result = AstVisitor().visit_function(func_ast, ctx)

    add_ops = [op for op in block.ops if isinstance(op, NnAddOp)]
    assert len(add_ops) == 1
    assert result is add_ops[0].result


def test_ast_visitor_visit_expr_wraps_public_emit_failure() -> None:
    expr = VarAST(name="missing", location=SourceLocation(3, 7))
    ctx = EmitContext(builder=Block(), symbols={}, types={})

    with pytest.raises(AstVisitorError, match="Unknown input reference") as exc_info:
        AstVisitor().visit_expr(expr, ctx)

    assert exc_info.value.location == expr.location


def test_build_func_op_from_ast_matches_public_build_func_op() -> None:
    def add(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x + y

    lhs = _tensor_arg([2, 2])
    rhs = _tensor_arg([2, 2])
    func_ast = parse_function(add)

    direct_func = build_func_op(add, lhs, rhs)
    ast_func = build_func_op_from_ast(func_ast, runtime_args=[lhs, rhs])

    assert [type(op) for op in direct_func.body.block.ops] == [type(op) for op in ast_func.body.block.ops]


def test_build_func_op_lowers_public_tensor_axis_access() -> None:
    def shape_axis(x: "Tensor[f32, 4, 8]") -> int:
        return x.get_shape()[1]

    func_op = build_func_op(shape_axis, _tensor_arg([4, 8]))

    get_dim_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolGetDimOp)]
    assert len(get_dim_ops) == 1
    assert get_dim_ops[0].axis.data == 1


def test_build_func_op_lowers_public_dma_helpers() -> None:
    def dma_kernel(src: "Tensor[f32, 2, 2]") -> None:
        local = dma_copy(src, MemorySpace.SM)
        dma_free(local)

    func_op = build_func_op(dma_kernel, _tensor_arg([2, 2]))

    body_ops = list(func_op.body.block.ops)
    assert any(isinstance(op, DmaCopyOp) for op in body_ops)
    assert any(isinstance(op, DmaFreeOp) for op in body_ops)
    assert isinstance(body_ops[-1], func.ReturnOp)


def test_build_func_op_reports_public_broadcast_mismatch() -> None:
    def add(x: "Tensor[f32, A, B]", y: "Tensor[f32, A, C]") -> "Tensor[f32, A, B]":
        return x + y

    with pytest.raises(AstVisitorError, match="Implicit broadcast dimension mismatch") as exc_info:
        build_func_op(add, _tensor_arg(["A", "B"]), _tensor_arg(["A", "C"]))

    assert exc_info.value.location is not None


def test_emit_mlir_rejects_block_ast_outside_public_visitor_path() -> None:
    def identity(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x

    block_ast = parse_function(identity).body
    ctx = EmitContext(builder=Block(), symbols={}, types={})

    with pytest.raises(ValueError, match="BlockAST must be lowered via AstVisitor"):
        emit_mlir(block_ast, ctx)
