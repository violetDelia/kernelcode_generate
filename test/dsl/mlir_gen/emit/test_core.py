"""Emit public API regression tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 只覆盖 `kernel_gen.dsl.mlir_gen.emit` 当前 spec 已定义的公开行为。
- 避免测试再直连 `emit.core` 的私有 helper、缓存接口或内部错误类型。

使用示例:
- pytest -q test/dsl/mlir_gen/emit/test_core.py

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/emit/__init__.py
- Spec 文档: spec/dsl/emit_mlir.md
- 测试文件: test/dsl/mlir_gen/emit/test_core.py
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

from kernel_gen.dialect.arch import ArchGetThreadNumOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolToFloatOp, SymbolValueType
from kernel_gen.dsl.ast import ArchQueryAST, ConstAST, ScalarArgAST, SymbolToFloatAST, TensorAST
from kernel_gen.dsl.mlir_gen.emit import EmitContext, emit_mlir, memory_type_from_memory
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType


def _expr_cache_key(expr: object) -> int:
    return id(expr)


def test_emit_context_validates_public_config() -> None:
    with pytest.raises(ValueError, match="EmitContext config must be dict or None"):
        EmitContext(builder=Block(), symbols={}, types={}, config=[])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="EmitContext target must be str"):
        EmitContext(builder=Block(), symbols={}, types={}, config={"target": 1})
    with pytest.raises(ValueError, match="EmitContext hardware must be dict\\[str, int\\]"):
        EmitContext(builder=Block(), symbols={}, types={}, config={"hardware": []})


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
    ctx = EmitContext(
        builder=block,
        symbols={"x": block.args[0]},
        types={_expr_cache_key(tensor): tensor_type},
    )

    result = emit_mlir(tensor, ctx)

    assert result is block.args[0]


def test_emit_mlir_lowers_symbol_to_float_through_public_entry() -> None:
    source = ScalarArgAST(name="n", value_type=int, is_symbolic=True, location=None)
    block = Block(arg_types=[SymbolValueType.from_expr("N")])
    ctx = EmitContext(
        builder=block,
        symbols={"n": block.args[0]},
        types={_expr_cache_key(source): block.args[0].type},
    )
    emit_mlir(source, ctx)

    result = emit_mlir(SymbolToFloatAST(source=source, location=None), ctx)

    body_ops = list(block.ops)
    assert len(body_ops) == 1
    assert isinstance(body_ops[0], SymbolToFloatOp)
    assert result is body_ops[0].result


def test_emit_mlir_rejects_non_symbol_to_float_source() -> None:
    source = ScalarArgAST(name="x", value_type=float, is_symbolic=False, location=None)
    block = Block(arg_types=[f32])
    ctx = EmitContext(
        builder=block,
        symbols={"x": block.args[0]},
        types={_expr_cache_key(source): block.args[0].type},
    )
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


def test_emit_package_root_memory_type_from_memory_keeps_public_layout() -> None:
    mem_type = memory_type_from_memory(Memory([2, "N"], NumericType.Float32, space=MemorySpace.TSM))

    assert [dim.data for dim in mem_type.shape.data] == [2, "N"]
    assert [dim.data for dim in mem_type.stride.data] == ["N", 1]
    assert mem_type.element_type == f32
    assert mem_type.space == NnMemorySpaceAttr.from_name("tsm")
