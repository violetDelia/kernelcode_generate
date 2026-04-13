"""Emit call_symbol tests.

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 覆盖 symbol family emit 拆分入口的最小行为。

使用示例:
- pytest -q test/dsl/mlir_gen/emit/test_call_symbol.py

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/emit/call_symbol.py
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
from kernel_gen.dsl.emit_mlir import _expr_key
from kernel_gen.dsl.mlir_gen.emit import EmitContext, LoweringError
from kernel_gen.dsl.mlir_gen.emit.call_symbol import emit_symbol_call, emit_symbol_for
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType


# EMIT-CALL-SYMBOL-001
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证 emit_symbol_call 可 lowering symbol.to_float。
# 测试目的: 锁定 symbol family 拆分入口会生成单个 symbol.to_float op。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_symbol.py -k test_emit_symbol_call_lowers_to_float
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/call_symbol.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_symbol.py
def test_emit_symbol_call_lowers_to_float() -> None:
    block = Block(arg_types=[SymbolValueType.from_expr("N")])
    source = ScalarArgAST(name="n", value_type=int, is_symbolic=True, location=None)
    ctx = EmitContext(builder=block, symbols={"n": block.args[0]}, types={_expr_key(source): block.args[0].type})
    ctx._set_cache(_expr_key(source), block.args[0])

    result = emit_symbol_call(SymbolToFloatAST(source=source, location=None), ctx)

    body_ops = list(block.ops)
    assert len(body_ops) == 1
    assert isinstance(body_ops[0], SymbolToFloatOp)
    assert result is body_ops[0].result


# EMIT-CALL-SYMBOL-002
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证 emit_symbol_call 可 lowering tensor.get_shape()[axis]。
# 测试目的: 锁定 symbol family 查询入口会生成单个 symbol.get_dim op。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_symbol.py -k test_emit_symbol_call_lowers_get_dim
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/call_symbol.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_symbol.py
def test_emit_symbol_call_lowers_get_dim() -> None:
    memory = Memory([4, 8], NumericType.Float32)
    tensor = TensorAST(name="x", memory=memory, location=None)
    tensor_type = NnMemoryType(
        ArrayAttr([IntAttr(4), IntAttr(8)]),
        ArrayAttr([IntAttr(8), IntAttr(1)]),
        f32,
        NnMemorySpaceAttr.from_name("global"),
    )
    block = Block(arg_types=[tensor_type])
    ctx = EmitContext(builder=block, symbols={"x": block.args[0]}, types={_expr_key(tensor): tensor_type})
    ctx._set_cache(_expr_key(tensor), block.args[0])

    result = emit_symbol_call(
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
# 功能说明: 验证 emit_symbol_for 会保留 symbol.iter 迭代变量且不引入 index_cast。
# 测试目的: 锁定 symbol.for 拆分入口可直接复用现有 lowering。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_symbol.py -k test_emit_symbol_for_lowers_symbolic_loop
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/call_symbol.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_symbol.py
def test_emit_symbol_for_lowers_symbolic_loop() -> None:
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
            _expr_key(tensor): tensor_type,
            _expr_key(start): start_type,
            _expr_key(end): end_type,
            _expr_key(step): step_type,
        },
    )
    ctx._set_cache(_expr_key(tensor), block.args[0])
    ctx._set_cache(_expr_key(start), block.args[1])
    ctx._set_cache(_expr_key(end), block.args[2])
    ctx._set_cache(_expr_key(step), block.args[3])

    emit_symbol_for(loop, ctx)
    loop_ops = [op for op in block.ops if isinstance(op, SymbolForOp)]

    assert len(loop_ops) == 1
    assert isinstance(loop_ops[0].body.block.args[0].type, SymbolIterType)
    assert not any(isinstance(op, arith.IndexCastOp) for op in loop_ops[0].body.block.ops)


# EMIT-CALL-SYMBOL-004
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证 emit_symbol_call / emit_symbol_for 拒绝越界输入类型。
# 测试目的: 锁定 symbol family 拆分入口的输入边界。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_symbol.py -k test_emit_symbol_entry_rejects_invalid_node
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/call_symbol.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_symbol.py
def test_emit_symbol_entry_rejects_invalid_node() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    with pytest.raises(LoweringError, match="emit_symbol_call only handles symbol family AST nodes"):
        emit_symbol_call(ConstAST(1), ctx)  # type: ignore[arg-type]
    with pytest.raises(LoweringError, match="emit_symbol_for expects ForAST"):
        emit_symbol_for(ConstAST(1), ctx)  # type: ignore[arg-type]
