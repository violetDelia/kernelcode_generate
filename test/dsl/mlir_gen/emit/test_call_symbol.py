"""Emit symbol public integration tests.

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 只覆盖 `kernel_gen.dsl.mlir_gen.emit` 包根公开入口的 symbol family 可观察行为。
- 不再把 `call_symbol.py` 子模块 helper 视为测试合同。

使用示例:
- pytest -q test/dsl/mlir_gen/emit/test_call_symbol.py

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/emit/__init__.py
- Spec 文档: spec/dsl/emit_mlir.md
- 测试文件: test/dsl/mlir_gen/emit/test_call_symbol.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.dialects import arith
from xdsl.dialects.builtin import ArrayAttr, IntAttr, f32
from xdsl.ir import Block

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolForOp, SymbolGetDimOp, SymbolIterType, SymbolToFloatOp, SymbolValueType
from kernel_gen.dsl.ast import (
    BlockAST,
    ConstAST,
    ForAST,
    LoadAST,
    ScalarArgAST,
    SymbolToFloatAST,
    TensorAST,
    TensorAxisAccessAST,
    VarAST,
)
from kernel_gen.dsl.mlir_gen.emit import EmitContext, emit_mlir
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType


def _expr_cache_key(expr: object) -> int:
    return id(expr)


# EMIT-CALL-SYMBOL-001
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证公开 `emit_mlir(...)` 可 lowering symbol.to_float。
# 测试目的: 锁定公开 symbol lowering 会生成单个 symbol.to_float op。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_symbol.py -k test_emit_mlir_lowers_symbol_to_float
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_symbol.py
def test_emit_mlir_lowers_symbol_to_float() -> None:
    block = Block(arg_types=[SymbolValueType.from_expr("N")])
    source = ScalarArgAST(name="n", value_type=int, is_symbolic=True, location=None)
    ctx = EmitContext(builder=block, symbols={"n": block.args[0]}, types={_expr_cache_key(source): block.args[0].type})
    emit_mlir(source, ctx)

    result = emit_mlir(SymbolToFloatAST(source=source, location=None), ctx)

    body_ops = list(block.ops)
    assert len(body_ops) == 1
    assert isinstance(body_ops[0], SymbolToFloatOp)
    assert result is body_ops[0].result


# EMIT-CALL-SYMBOL-002
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证公开 `emit_mlir(...)` 可 lowering tensor.get_shape()[axis]。
# 测试目的: 锁定公开 symbol 查询会生成单个 symbol.get_dim op。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_symbol.py -k test_emit_mlir_lowers_symbol_get_dim
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_symbol.py
def test_emit_mlir_lowers_symbol_get_dim() -> None:
    memory = Memory([4, 8], NumericType.Float32)
    tensor = TensorAST(name="x", memory=memory, location=None)
    tensor_type = NnMemoryType(
        ArrayAttr([IntAttr(4), IntAttr(8)]),
        ArrayAttr([IntAttr(8), IntAttr(1)]),
        f32,
        NnMemorySpaceAttr.from_name("global"),
    )
    block = Block(arg_types=[tensor_type])
    ctx = EmitContext(builder=block, symbols={"x": block.args[0]}, types={_expr_cache_key(tensor): tensor_type})
    emit_mlir(tensor, ctx)

    result = emit_mlir(
        TensorAxisAccessAST(tensor=tensor, kind="shape", axis=ConstAST(0), location=None),
        ctx,
    )

    body_ops = list(block.ops)
    assert len(body_ops) == 1
    assert isinstance(body_ops[0], SymbolGetDimOp)
    assert result is body_ops[0].result


# EMIT-CALL-SYMBOL-003
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证公开 `emit_mlir(...)` 会保留 symbol.iter 迭代变量且不引入 index_cast。
# 测试目的: 锁定公开 `ForAST` lowering 可直接生成 `symbol.for`。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_symbol.py -k test_emit_mlir_lowers_symbolic_loop
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_symbol.py
def test_emit_mlir_lowers_symbolic_loop() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    tensor = TensorAST(name="x", memory=memory, location=None)
    start = ScalarArgAST(name="start", value_type=int, is_symbolic=True, location=None)
    end = ScalarArgAST(name="end", value_type=int, is_symbolic=True, location=None)
    step = ScalarArgAST(name="step", value_type=int, is_symbolic=True, location=None)
    loop_var = VarAST(name="i", location=None)
    loop = ForAST(
        var=loop_var,
        start=start,
        end=end,
        step=step,
        body=BlockAST([LoadAST(tensor=tensor, offset=[loop_var, ConstAST(0)], stride=None, location=None)]),
        location=None,
    )
    tensor_type = NnMemoryType(
        ArrayAttr([IntAttr(2), IntAttr(2)]),
        ArrayAttr([IntAttr(2), IntAttr(1)]),
        f32,
        NnMemorySpaceAttr.from_name("global"),
    )
    start_type = SymbolValueType.from_expr("START")
    end_type = SymbolValueType.from_expr("END")
    step_type = SymbolValueType.from_expr("STEP")
    block = Block(arg_types=[tensor_type, start_type, end_type, step_type])
    ctx = EmitContext(
        builder=block,
        symbols={
            "x": block.args[0],
            "start": block.args[1],
            "end": block.args[2],
            "step": block.args[3],
        },
        types={
            _expr_cache_key(tensor): tensor_type,
            _expr_cache_key(start): start_type,
            _expr_cache_key(end): end_type,
            _expr_cache_key(step): step_type,
        },
    )
    emit_mlir(tensor, ctx)
    emit_mlir(start, ctx)
    emit_mlir(end, ctx)
    emit_mlir(step, ctx)

    emit_mlir(loop, ctx)
    loop_ops = [op for op in block.ops if isinstance(op, SymbolForOp)]

    assert len(loop_ops) == 1
    assert isinstance(loop_ops[0].body.block.args[0].type, SymbolIterType)
    assert not any(isinstance(op, arith.IndexCastOp) for op in loop_ops[0].body.block.ops)


# EMIT-CALL-SYMBOL-004
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证公开 `emit_mlir(...)` 会拒绝非法 tensor axis kind。
# 测试目的: 锁定 symbol 公开入口的错误路径，不再依赖 `call_symbol.py` 子模块边界。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_symbol.py -k test_emit_mlir_rejects_invalid_tensor_axis_kind
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_symbol.py
def test_emit_mlir_rejects_invalid_tensor_axis_kind() -> None:
    memory = Memory([4, 8], NumericType.Float32)
    tensor = TensorAST(name="x", memory=memory, location=None)
    tensor_type = NnMemoryType(
        ArrayAttr([IntAttr(4), IntAttr(8)]),
        ArrayAttr([IntAttr(8), IntAttr(1)]),
        f32,
        NnMemorySpaceAttr.from_name("global"),
    )
    block = Block(arg_types=[tensor_type])
    ctx = EmitContext(builder=block, symbols={"x": block.args[0]}, types={_expr_cache_key(tensor): tensor_type})
    emit_mlir(tensor, ctx)

    with pytest.raises(ValueError, match="Unsupported tensor axis access kind"):
        emit_mlir(TensorAxisAccessAST(tensor=tensor, kind="bad", axis=ConstAST(0), location=None), ctx)
