"""Emit shape public integration tests.

创建者: jcc你莫辜负
最后一次更改: 小李飞刀

功能说明:
- 只覆盖 `kernel_gen.dsl.mlir_gen.emit` 包根公开入口中的 shape/index 可观察行为。
- 不再把 `shape_utils.py` 子模块 helper 视为测试合同。

使用示例:
- pytest -q test/dsl/mlir_gen/emit/test_shape_utils.py

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/emit/__init__.py
- Spec 文档: spec/dsl/emit_mlir.md
- 测试文件: test/dsl/mlir_gen/emit/test_shape_utils.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.dialects.builtin import ArrayAttr, IntAttr, f32
from xdsl.ir import Block

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.dma import DmaAllocOp, DmaLoadOp, DmaViewOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dsl.ast import ConstAST, DmaViewAST, LoadAST, TensorAST
from kernel_gen.dsl.mlir_gen.emit import EmitContext, emit_mlir
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType


def _expr_cache_key(expr: object) -> int:
    return id(expr)


def _tensor_type() -> NnMemoryType:
    return NnMemoryType(
        ArrayAttr([IntAttr(4), IntAttr(4)]),
        ArrayAttr([IntAttr(4), IntAttr(1)]),
        f32,
        NnMemorySpaceAttr.from_name("global"),
    )


def _tensor_and_ctx() -> tuple[TensorAST, Block, EmitContext]:
    tensor = TensorAST(name="x", memory=Memory([4, 4], NumericType.Float32), location=None)
    tensor_type = _tensor_type()
    block = Block(arg_types=[tensor_type])
    ctx = EmitContext(builder=block, symbols={"x": block.args[0]}, types={_expr_cache_key(tensor): tensor_type})
    emit_mlir(tensor, ctx)
    return tensor, block, ctx


def test_emit_mlir_lowers_dma_load_with_public_index_layout() -> None:
    tensor, block, ctx = _tensor_and_ctx()

    result = emit_mlir(
        LoadAST(
            tensor=tensor,
            offset=[ConstAST(0), ConstAST(0)],
            stride=None,
            sizes=[ConstAST(1), ConstAST(1)],
            location=None,
        ),
        ctx,
    )

    load_ops = [op for op in block.ops if isinstance(op, DmaLoadOp)]
    assert isinstance(result.owner, DmaAllocOp)
    assert len(load_ops) == 1
    assert load_ops[0].target is result


def test_emit_mlir_lowers_dma_view_with_public_shape_layout() -> None:
    tensor, block, ctx = _tensor_and_ctx()

    result = emit_mlir(
        DmaViewAST(
            source=tensor,
            offset=[ConstAST(1), ConstAST(1)],
            size=[ConstAST(2), ConstAST(2)],
            stride=[ConstAST(1), ConstAST(1)],
            location=None,
        ),
        ctx,
    )

    view_ops = [op for op in block.ops if isinstance(op, DmaViewOp)]
    assert len(view_ops) == 1
    assert result is view_ops[0].result
    assert [attr.data for attr in result.type.shape.data] == [2, 2]


def test_emit_mlir_rejects_view_index_rank_mismatch() -> None:
    tensor, _block, ctx = _tensor_and_ctx()

    with pytest.raises(KernelCodeError, match="Index rank mismatch"):
        emit_mlir(
            DmaViewAST(
                source=tensor,
                offset=[ConstAST(1)],
                size=[ConstAST(2), ConstAST(2)],
                stride=[ConstAST(1), ConstAST(1)],
                location=None,
            ),
            ctx,
        )


def test_emit_mlir_rejects_non_unit_stride_layout() -> None:
    tensor, _block, ctx = _tensor_and_ctx()

    with pytest.raises(KernelCodeError, match="Only unit stride is supported"):
        emit_mlir(
            LoadAST(
                tensor=tensor,
                offset=[ConstAST(1), ConstAST(1)],
                sizes=[ConstAST(1), ConstAST(1)],
                stride=[ConstAST(2), ConstAST(1)],
                location=None,
            ),
            ctx,
        )
