"""Emit call_dma tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 dma family emit 拆分入口的最小行为。

使用示例:
- pytest -q test/dsl/mlir_gen/emit/test_call_dma.py

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/emit/call_dma.py
- Spec 文档: spec/dsl/emit_mlir.md
- 测试文件: test/dsl/mlir_gen/emit/test_call_dma.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.dialects.builtin import f32
from xdsl.ir import Block

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp, DmaCastOp, DmaCopyOp, DmaFreeOp, DmaLoadOp, DmaStoreOp, DmaViewOp
from kernel_gen.dsl.ast import ConstAST, DmaAllocAST, DmaCastAST, DmaCopyAST, DmaFreeAST, DmaViewAST, LoadAST, StoreAST, TensorAST
from kernel_gen.dsl.mlir_gen.emit.core import _expr_key, _memory_to_nn_type
from kernel_gen.dsl.mlir_gen.emit import EmitContext
from kernel_gen.dsl.mlir_gen.emit.context import LoweringError
from kernel_gen.dsl.mlir_gen.emit.call_dma import emit_dma_call
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType


def _memory_tensor(name: str, shape: list[object], *, space: MemorySpace = MemorySpace.GM) -> TensorAST:
    """构造最小 Memory/Tensor 测试输入。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 为 call_dma 相关测试统一生成 `TensorAST + Memory`。

    使用示例:
    - tensor = _memory_tensor("src", [2, 3])

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_call_dma.py](test/dsl/mlir_gen/emit/test_call_dma.py)
    - 功能实现: [test/dsl/mlir_gen/emit/test_call_dma.py](test/dsl/mlir_gen/emit/test_call_dma.py)
    """

    return TensorAST(name=name, memory=Memory(shape, NumericType.Float32, space=space), location=None)


# EMIT-CALL-DMA-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 验证 emit_dma_call 可 lowering dma.alloc。
# 测试目的: 锁定 dma family 拆分入口会生成单个 dma.alloc op。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_dma.py -k test_emit_dma_call_lowers_alloc
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/call_dma.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_dma.py
def test_emit_dma_call_lowers_alloc() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    result = emit_dma_call(
        DmaAllocAST(shape=[ConstAST(2), ConstAST(3)], dtype=NumericType.Float32, space=MemorySpace.SM, location=None),
        ctx,
    )

    body_ops = list(block.ops)
    assert len(body_ops) == 1
    assert isinstance(body_ops[0], DmaAllocOp)
    assert result is body_ops[0].result
    assert result.type.space.space.data == "shared"
    assert result.type.element_type == f32


# EMIT-CALL-DMA-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 验证 emit_dma_call 可 lowering dma.copy。
# 测试目的: 锁定 dma.copy 拆分入口会复用 alloc + copy lowering。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_dma.py -k test_emit_dma_call_lowers_copy
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/call_dma.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_dma.py
def test_emit_dma_call_lowers_copy() -> None:
    source = _memory_tensor("src", [2, 3], space=MemorySpace.GM)
    block = Block(arg_types=[_memory_to_nn_type(source.memory)])
    ctx = EmitContext(builder=block, symbols={"src": block.args[0]}, types={})
    ctx._set_cache(_expr_key(source), block.args[0])
    ctx.types[_expr_key(source)] = block.args[0].type

    result = emit_dma_call(DmaCopyAST(source=source, space=MemorySpace.SM, location=None), ctx)

    body_ops = list(block.ops)
    assert isinstance(result.owner, DmaAllocOp)
    assert any(isinstance(op, DmaCopyOp) for op in body_ops)
    assert result.type.space.space.data == "shared"
    copy_ops = [op for op in body_ops if isinstance(op, DmaCopyOp)]
    assert len(copy_ops) == 1
    assert copy_ops[0].target is result


# EMIT-CALL-DMA-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 验证 emit_dma_call 可 lowering dma.view。
# 测试目的: 锁定 dma.view 拆分入口会生成单个 dma.view op。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_dma.py -k test_emit_dma_call_lowers_view
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/call_dma.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_dma.py
def test_emit_dma_call_lowers_view() -> None:
    source = _memory_tensor("src", [4, 4], space=MemorySpace.GM)
    block = Block(arg_types=[_memory_to_nn_type(source.memory)])
    ctx = EmitContext(builder=block, symbols={"src": block.args[0]}, types={})
    ctx._set_cache(_expr_key(source), block.args[0])
    ctx.types[_expr_key(source)] = block.args[0].type

    result = emit_dma_call(
        DmaViewAST(
            source=source,
            offset=[ConstAST(1), ConstAST(1)],
            size=[ConstAST(2), ConstAST(2)],
            stride=[ConstAST(1), ConstAST(1)],
            location=None,
        ),
        ctx,
    )

    body_ops = list(block.ops)
    view_ops = [op for op in body_ops if isinstance(op, DmaViewOp)]
    assert len(view_ops) == 1
    assert result is view_ops[0].result
    assert [attr.data for attr in result.type.shape.data] == [2, 2]


# EMIT-CALL-DMA-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 验证 emit_dma_call 可 lowering dma.load 与 dma.store。
# 测试目的: 锁定 read/write 入口会生成对应 dma.load / dma.store。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_dma.py -k test_emit_dma_call_lowers_read_and_write
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/call_dma.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_dma.py
def test_emit_dma_call_lowers_read_and_write() -> None:
    source = _memory_tensor("src", [2, 2], space=MemorySpace.GM)
    value = _memory_tensor("value", [1, 1], space=MemorySpace.SM)
    block = Block(arg_types=[_memory_to_nn_type(source.memory), _memory_to_nn_type(value.memory)])
    ctx = EmitContext(builder=block, symbols={"src": block.args[0], "value": block.args[1]}, types={})
    ctx._set_cache(_expr_key(source), block.args[0])
    ctx._set_cache(_expr_key(value), block.args[1])
    ctx.types[_expr_key(source)] = block.args[0].type
    ctx.types[_expr_key(value)] = block.args[1].type

    load_result = emit_dma_call(
        LoadAST(
            tensor=source,
            offset=[ConstAST(0), ConstAST(0)],
            stride=None,
            sizes=[ConstAST(1), ConstAST(1)],
            location=None,
        ),
        ctx,
    )
    store_result = emit_dma_call(
        StoreAST(
            tensor=source,
            offset=[ConstAST(0), ConstAST(0)],
            stride=None,
            sizes=[ConstAST(1), ConstAST(1)],
            value=value,
            location=None,
        ),
        ctx,
    )

    body_ops = list(block.ops)
    assert isinstance(load_result.owner, DmaAllocOp)
    assert isinstance(store_result, DmaStoreOp)
    load_ops = [op for op in body_ops if isinstance(op, DmaLoadOp)]
    assert len(load_ops) == 1
    assert load_ops[0].target is load_result
    assert any(isinstance(op, DmaStoreOp) for op in body_ops)


def test_emit_dma_call_lowers_cast() -> None:
    source = _memory_tensor("src", [2, 3], space=MemorySpace.GM)
    block = Block(arg_types=[_memory_to_nn_type(source.memory)])
    ctx = EmitContext(builder=block, symbols={"src": block.args[0]}, types={})
    ctx._set_cache(_expr_key(source), block.args[0])
    ctx.types[_expr_key(source)] = block.args[0].type

    result = emit_dma_call(DmaCastAST(source=source, dtype=NumericType.Float16, memoryspace=MemorySpace.SM, location=None), ctx)

    body_ops = list(block.ops)
    assert isinstance(result.owner, DmaAllocOp)
    cast_ops = [op for op in body_ops if isinstance(op, DmaCastOp)]
    assert len(cast_ops) == 1
    assert cast_ops[0].target is result
    assert result.type.element_type != block.args[0].type.element_type
    assert result.type.space.space.data == "shared"


# EMIT-CALL-DMA-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 验证 emit_dma_call 可 lowering dma.free。
# 测试目的: 锁定 dma.free 拆分入口不会生成额外 SSA 结果。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_dma.py -k test_emit_dma_call_lowers_free
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/call_dma.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_dma.py
def test_emit_dma_call_lowers_free() -> None:
    source = _memory_tensor("src", [2, 3], space=MemorySpace.SM)
    block = Block(arg_types=[_memory_to_nn_type(source.memory)])
    ctx = EmitContext(builder=block, symbols={"src": block.args[0]}, types={})
    ctx._set_cache(_expr_key(source), block.args[0])
    ctx.types[_expr_key(source)] = block.args[0].type

    result = emit_dma_call(DmaFreeAST(value=source, location=None), ctx)

    body_ops = list(block.ops)
    assert len(body_ops) == 1
    assert isinstance(result, DmaFreeOp)
    assert body_ops[0] is result


# EMIT-CALL-DMA-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 验证 emit_dma_call 拒绝非 dma AST。
# 测试目的: 锁定 dma family 拆分入口的输入边界。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_dma.py -k test_emit_dma_call_rejects_non_dma_ast
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/call_dma.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_dma.py
def test_emit_dma_call_rejects_non_dma_ast() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    with pytest.raises(LoweringError, match="emit_dma_call only handles dma family AST nodes"):
        emit_dma_call(ConstAST(1), ctx)  # type: ignore[arg-type]
