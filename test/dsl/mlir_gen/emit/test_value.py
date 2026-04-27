"""Emit value public integration tests.

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 只覆盖 `kernel_gen.dsl.mlir_gen.emit` 包根公开入口中与 value/index 相关的可观察行为。
- 不再把 `value.py` 子模块 helper 视为测试合同。

使用示例:
- pytest -q test/dsl/mlir_gen/emit/test_value.py

覆盖率信息:
- 覆盖率命令: coverage run -m pytest -q test/dsl/mlir_gen/emit/test_value.py && coverage report --include=kernel_gen/dsl/mlir_gen/emit/value.py -m
- 覆盖率结果: 未统计（待补充）
- 达标线: 90%

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/emit/__init__.py
- Spec 文档: spec/dsl/emit_mlir.md
- 测试文件: test/dsl/mlir_gen/emit/test_value.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.dialects import arith
from xdsl.dialects.builtin import ArrayAttr, IndexType, IntAttr, f32, i32
from xdsl.ir import Block

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp, DmaLoadOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolValueType
from kernel_gen.dsl.ast import ConstAST, LoadAST, TensorAST, VarAST
from kernel_gen.dsl.mlir_gen.emit import EmitContext, emit_mlir
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType


def _expr_cache_key(expr: object) -> int:
    return id(expr)


# EMIT-VALUE-001
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证公开 `emit_mlir(...)` 对 `ConstAST` 的最小下沉行为。
# 测试目的: 确保公开入口返回常量 op 结果。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_value.py -k test_emit_mlir_const
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_value.py
def test_emit_mlir_const() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    result = emit_mlir(ConstAST(1), ctx)

    body_ops = list(block.ops)
    if len(body_ops) != 1:
        raise AssertionError("expected one emitted op")
    if not isinstance(body_ops[0], arith.ConstantOp):
        raise AssertionError("expected arith.ConstantOp")
    if result is not body_ops[0].result:
        raise AssertionError("expected result to be constant op result")


# EMIT-VALUE-002
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证公开 `emit_mlir(...)` 对未知变量的错误路径。
# 测试目的: 锁定公开 value 入口的缺失引用诊断。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_value.py -k test_emit_mlir_unknown_var
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_value.py
def test_emit_mlir_unknown_var() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    with pytest.raises(ValueError, match="Unknown input reference"):
        emit_mlir(VarAST("x"), ctx)


# EMIT-VALUE-003
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证公开 `emit_mlir(...)` 在 DMA offset 中下沉 `symbol.const`。
# 测试目的: 锁定公开索引路径仍会生成 `symbol.const`。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_value.py -k test_emit_mlir_lowers_symbol_const_in_dma_offset
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_value.py
def test_emit_mlir_lowers_symbol_const_in_dma_offset() -> None:
    tensor = TensorAST(name="x", memory=Memory([4, 4], NumericType.Float32), location=None)
    tensor_type = NnMemoryType(
        ArrayAttr([IntAttr(4), IntAttr(4)]),
        ArrayAttr([IntAttr(4), IntAttr(1)]),
        f32,
        NnMemorySpaceAttr.from_name("global"),
    )
    block = Block(arg_types=[tensor_type])
    ctx = EmitContext(builder=block, symbols={"x": block.args[0]}, types={_expr_cache_key(tensor): tensor_type})
    emit_mlir(tensor, ctx)

    result = emit_mlir(
        LoadAST(tensor=tensor, offset=[ConstAST(2), ConstAST(0)], stride=None, sizes=[ConstAST(1), ConstAST(1)], location=None),
        ctx,
    )

    assert isinstance(result.owner, DmaAllocOp)
    load_ops = [op for op in block.ops if isinstance(op, DmaLoadOp)]
    assert len(load_ops) == 1
    assert load_ops[0].target is result
    assert any(isinstance(op, SymbolConstOp) for op in block.ops)


def test_emit_mlir_lowers_index_cast_for_i32_dma_offset() -> None:
    tensor = TensorAST(name="x", memory=Memory([4, 4], NumericType.Float32), location=None)
    tensor_type = NnMemoryType(
        ArrayAttr([IntAttr(4), IntAttr(4)]),
        ArrayAttr([IntAttr(4), IntAttr(1)]),
        f32,
        NnMemorySpaceAttr.from_name("global"),
    )
    block = Block(arg_types=[tensor_type, i32])
    ctx = EmitContext(
        builder=block,
        symbols={"x": block.args[0], "i32_value": block.args[1]},
        types={_expr_cache_key(tensor): tensor_type},
    )
    emit_mlir(tensor, ctx)

    result = emit_mlir(
        LoadAST(
            tensor=tensor,
            offset=[VarAST("i32_value"), ConstAST(0)],
            stride=None,
            sizes=[ConstAST(1), ConstAST(1)],
            location=None,
        ),
        ctx,
    )

    assert isinstance(result.owner, DmaAllocOp)
    load_ops = [op for op in block.ops if isinstance(op, DmaLoadOp)]
    assert len(load_ops) == 1
    assert load_ops[0].target is result
    assert any(isinstance(op, arith.IndexCastOp) for op in block.ops)
