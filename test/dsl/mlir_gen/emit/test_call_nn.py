"""Emit call_nn public API tests.

创建者: OpenAI
最后一次更改: 金铲铲大作战

功能说明:
- 只通过 `kernel_gen.dsl.mlir_gen.emit` 包根公开入口验证 nn elementwise emit 行为。
- 不再跨文件直连 `emit.call_nn`、`emit.context` 或 `emit.core` 的非公开 helper。

使用示例:
- pytest -q test/dsl/mlir_gen/emit/test_call_nn.py

关联文件:
- 功能实现: [kernel_gen/dsl/mlir_gen/emit/call_nn.py](kernel_gen/dsl/mlir_gen/emit/call_nn.py)
- spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
- 测试: [test/dsl/mlir_gen/emit/test_call_nn.py](test/dsl/mlir_gen/emit/test_call_nn.py)
"""

from __future__ import annotations

import pytest
from xdsl.dialects.builtin import ArrayAttr, Float16Type, IntAttr, f32, i32
from xdsl.ir import Block

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
from kernel_gen.dsl.ast import BinaryExprAST, CompareExprAST, ConstAST, NnUnaryAST, TensorAST
from kernel_gen.dsl.mlir_gen.emit import EmitContext, emit_mlir
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType


def _expr_key(expr: object) -> int:
    """生成测试内部使用的稳定 AST 键。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 在公开测试内部复用 `id(expr)` 作为 `EmitContext.types` 的 key。
    - 避免跨文件依赖 `emit.core._expr_key` 这类非公开 helper。

    使用示例:
    - `types = {_expr_key(tensor): tensor_type}`

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_call_nn.py](test/dsl/mlir_gen/emit/test_call_nn.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/call_nn.py](kernel_gen/dsl/mlir_gen/emit/call_nn.py)
    """

    return id(expr)


def _memory_type(shape: list[int], strides: list[int], element_type: object) -> NnMemoryType:
    """构造公开测试所需的 `NnMemoryType`。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 在测试文件内部显式构造 `nn.memory` 类型。
    - 避免为了类型准备再依赖 emit 子模块里的非公开转换 helper。

    使用示例:
    - `_memory_type([2, 2], [2, 1], f32)`

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_call_nn.py](test/dsl/mlir_gen/emit/test_call_nn.py)
    - 功能实现: [kernel_gen/dialect/nn.py](kernel_gen/dialect/nn.py)
    """

    return NnMemoryType(
        ArrayAttr([IntAttr(dim) for dim in shape]),
        ArrayAttr([IntAttr(stride) for stride in strides]),
        element_type,
        NnMemorySpaceAttr.from_name("global"),
    )


def _build_emit_context(*bindings: tuple[TensorAST, NnMemoryType]) -> tuple[Block, EmitContext]:
    """基于公开 `EmitContext` 入口绑定 tensor 参数。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅通过 `EmitContext(builder, symbols, types)` 建立公开 emit 上下文。
    - 不使用 `_set_cache(...)` 等非公开上下文 helper。

    使用示例:
    - `block, ctx = _build_emit_context((tensor, tensor_type))`

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_call_nn.py](test/dsl/mlir_gen/emit/test_call_nn.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/__init__.py](kernel_gen/dsl/mlir_gen/emit/__init__.py)
    """

    arg_types = [tensor_type for _, tensor_type in bindings]
    block = Block(arg_types=arg_types)
    symbols = {tensor.name: arg for (tensor, _), arg in zip(bindings, block.args)}
    types = {_expr_key(tensor): tensor_type for tensor, tensor_type in bindings}
    return block, EmitContext(builder=block, symbols=symbols, types=types)


# CALL-NN-PUBLIC-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 只通过公开 `emit_mlir(...)` 验证 `nn.relu` 的最小 lowering 行为。
# 测试目的: 锁定公开 emit 入口对 unary memory helper 的可达性。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_nn.py -k test_emit_mlir_lowers_relu_via_public_entry
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/call_nn.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_nn.py
def test_emit_mlir_lowers_relu_via_public_entry() -> None:
    tensor = TensorAST(name="x", memory=Memory([2, 2], NumericType.Float32), location=None)
    tensor_type = _memory_type([2, 2], [2, 1], f32)
    block, ctx = _build_emit_context((tensor, tensor_type))

    result = emit_mlir(NnUnaryAST(kind="relu", value=tensor, location=None), ctx)

    body_ops = list(block.ops)
    assert len(body_ops) == 1
    assert isinstance(body_ops[0], NnReluOp)
    assert result is body_ops[0].result


# CALL-NN-PUBLIC-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 只通过公开 `emit_mlir(...)` 验证 mixed const `nn.add` 的最小 lowering 行为。
# 测试目的: 锁定公开 emit 入口仍会按合同插入 `symbol.const -> symbol.to_float -> nn.add`。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_nn.py -k test_emit_mlir_lowers_add_mixed_const_via_public_entry
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/call_nn.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_nn.py
def test_emit_mlir_lowers_add_mixed_const_via_public_entry() -> None:
    tensor = TensorAST(name="x", memory=Memory([2, 2], NumericType.Float16), location=None)
    tensor_type = _memory_type([2, 2], [2, 1], Float16Type())
    block, ctx = _build_emit_context((tensor, tensor_type))

    result = emit_mlir(BinaryExprAST(op="add", lhs=tensor, rhs=ConstAST(1), location=None), ctx)

    body_ops = list(block.ops)
    assert [type(op) for op in body_ops] == [SymbolConstOp, SymbolToFloatOp, NnAddOp]
    assert result is body_ops[-1].result


# CALL-NN-PUBLIC-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 只通过公开 `emit_mlir(...)` 验证 compare 场景的 cast+broadcast lowering。
# 测试目的: 锁定 `nn.eq` 的公开 lowering 链不回退。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_nn.py -k test_emit_mlir_lowers_compare_cast_and_broadcast_via_public_entry
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/call_nn.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_nn.py
def test_emit_mlir_lowers_compare_cast_and_broadcast_via_public_entry() -> None:
    lhs = TensorAST(name="lhs", memory=Memory([2, 2], NumericType.Float32), location=None)
    rhs = TensorAST(name="rhs", memory=Memory([1, 2], NumericType.Int32), location=None)
    lhs_type = _memory_type([2, 2], [2, 1], f32)
    rhs_type = _memory_type([1, 2], [2, 1], i32)
    block, ctx = _build_emit_context((lhs, lhs_type), (rhs, rhs_type))

    result = emit_mlir(CompareExprAST(op="eq", lhs=lhs, rhs=rhs, location=None), ctx)

    body_ops = list(block.ops)
    assert [type(op) for op in body_ops] == [NnCastOp, NnBroadcastOp, NnEqOp]
    assert result is body_ops[-1].result


# CALL-NN-PUBLIC-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 只通过公开 `emit_mlir(...)` 验证非法 unary helper 的诊断行为。
# 测试目的: 锁定公开入口的错误链不会因内部 helper 拆分回退。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_nn.py -k test_emit_mlir_rejects_unsupported_unary_helper_via_public_entry
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/call_nn.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_nn.py
def test_emit_mlir_rejects_unsupported_unary_helper_via_public_entry() -> None:
    tensor = TensorAST(name="x", memory=Memory([2, 2], NumericType.Float32), location=None)
    tensor_type = _memory_type([2, 2], [2, 1], f32)
    _, ctx = _build_emit_context((tensor, tensor_type))

    with pytest.raises(Exception, match="Unsupported unary helper"):
        emit_mlir(NnUnaryAST(kind="bad_helper", value=tensor, location=None), ctx)


# CALL-NN-PUBLIC-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 只通过公开 `emit_mlir(...)` 验证非法 binary helper 的诊断行为。
# 测试目的: 锁定公开入口对不支持二元算子的错误边界。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_nn.py -k test_emit_mlir_rejects_unsupported_binary_helper_via_public_entry
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/call_nn.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_nn.py
def test_emit_mlir_rejects_unsupported_binary_helper_via_public_entry() -> None:
    lhs = TensorAST(name="lhs", memory=Memory([2, 2], NumericType.Float32), location=None)
    rhs = TensorAST(name="rhs", memory=Memory([2, 2], NumericType.Float32), location=None)
    lhs_type = _memory_type([2, 2], [2, 1], f32)
    rhs_type = _memory_type([2, 2], [2, 1], f32)
    _, ctx = _build_emit_context((lhs, lhs_type), (rhs, rhs_type))

    with pytest.raises(Exception, match="Unsupported binary op: pow"):
        emit_mlir(BinaryExprAST(op="pow", lhs=lhs, rhs=rhs, location=None), ctx)
