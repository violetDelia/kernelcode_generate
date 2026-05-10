"""DSL AST kernel node tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast.nodes.kernel` 公开节点构造与 MLIR 发射。
- 测试只通过公开 AST 节点类和公开 xDSL 发射入口验证。

使用示例:
- pytest -q test/dsl/ast/nodes/test_kernel.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/nodes/kernel.py
- Spec 文档: spec/dsl/ast/nodes/kernel.md
- 测试文件: test/dsl/ast/nodes/test_kernel.py
"""

from __future__ import annotations

import pytest
from xdsl.context import Context
from xdsl.ir import Block

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp, KernelImg2col2dOp, KernelMatmulOp
from kernel_gen.dsl.ast.nodes import (
    ConstValueAST,
    KernelAddAST,
    KernelBinaryElewiseAST,
    KernelImg2Col2dAST,
    KernelMatmulAST,
    MemoryAST,
)
from kernel_gen.operation.kernel import KernelBinaryElewiseKind
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


def _memory_node(name: str, memory: Memory) -> MemoryAST:
    """构造公开 MemoryAST 节点。"""

    return MemoryAST.from_memory(name, memory)


def _block_for_memories(*nodes: MemoryAST) -> tuple[Context, Block]:
    """为公开 MemoryAST 输入构造 Context 与 Block。"""

    ctx = Context()
    block = Block(arg_types=[node.to_mlir_type(ctx) for node in nodes])
    for arg, node in zip(block.args, nodes, strict=True):
        arg.name_hint = node.name
    return ctx, block


# TC-AST-NODE-KERNEL-001
# 功能说明: 验证 KernelAddAST 发射为 kernel.binary_elewise。
# 测试目的: 固定 helper 不生成不存在的 kernel.add dialect op。
# 使用示例: pytest -q test/dsl/ast/nodes/test_kernel.py -k add
# 对应功能实现文件路径: kernel_gen/dsl/ast/nodes/kernel.py
# 对应 spec 文件路径: spec/dsl/ast/nodes/kernel.md
# 对应测试文件路径: test/dsl/ast/nodes/test_kernel.py
def test_kernel_add_node_emits_binary_elewise_op() -> None:
    memory = Memory([2, 4], NumericType.Float32, space=MemorySpace.GM)
    out = _memory_node("out", memory)
    lhs = _memory_node("lhs", memory)
    rhs = _memory_node("rhs", memory)
    ctx, block = _block_for_memories(out, lhs, rhs)

    emitted = KernelAddAST(out, lhs, rhs).emit_mlir(ctx, block)

    assert isinstance(emitted, KernelBinaryElewiseOp)
    assert emitted.kind.data == "add"


# TC-AST-NODE-KERNEL-002
# 功能说明: 验证显式 KernelBinaryElewiseAST 保存 enum kind。
# 测试目的: binary_elewise 只接受 KernelBinaryElewiseKind，不接受字符串 kind。
# 使用示例: pytest -q test/dsl/ast/nodes/test_kernel.py -k binary
# 对应功能实现文件路径: kernel_gen/dsl/ast/nodes/kernel.py
# 对应 spec 文件路径: spec/dsl/ast/nodes/kernel.md
# 对应测试文件路径: test/dsl/ast/nodes/test_kernel.py
def test_kernel_binary_elewise_node_rejects_string_kind() -> None:
    memory = Memory([2, 4], NumericType.Float32)
    out = _memory_node("out", memory)
    lhs = _memory_node("lhs", memory)
    rhs = _memory_node("rhs", memory)

    with pytest.raises(KernelCodeError, match="KernelBinaryElewiseKind"):
        KernelBinaryElewiseAST(out, lhs, rhs, "add")


# TC-AST-NODE-KERNEL-003
# 功能说明: 验证 KernelMatmulAST 发射 kernel.matmul。
# 测试目的: out-first matmul 允许 mixed-space operand 并生成无结果 dialect op。
# 使用示例: pytest -q test/dsl/ast/nodes/test_kernel.py -k matmul
# 对应功能实现文件路径: kernel_gen/dsl/ast/nodes/kernel.py
# 对应 spec 文件路径: spec/dsl/ast/nodes/kernel.md
# 对应测试文件路径: test/dsl/ast/nodes/test_kernel.py
def test_kernel_matmul_node_emits_matmul_op() -> None:
    m_dim = SymbolDim("M")
    k_dim = SymbolDim("K")
    n_dim = SymbolDim("N")
    out = _memory_node("out", Memory([m_dim, n_dim], NumericType.Float32, space=MemorySpace.TSM))
    lhs = _memory_node("lhs", Memory([m_dim, k_dim], NumericType.Float32, space=MemorySpace.TLM1))
    rhs = _memory_node("rhs", Memory([k_dim, n_dim], NumericType.Float32, space=MemorySpace.TLM2))
    ctx, block = _block_for_memories(out, lhs, rhs)

    emitted = KernelMatmulAST(out, lhs, rhs).emit_mlir(ctx, block)

    assert isinstance(emitted, KernelMatmulOp)
    assert len(emitted.results) == 0


# TC-AST-NODE-KERNEL-004
# 功能说明: 验证 KernelImg2Col2dAST 发射 kernel.img2col2d。
# 测试目的: img2col2d 窗口参数必须 lower 为 symbol.int operand。
# 使用示例: pytest -q test/dsl/ast/nodes/test_kernel.py -k img2col2d
# 对应功能实现文件路径: kernel_gen/dsl/ast/nodes/kernel.py
# 对应 spec 文件路径: spec/dsl/ast/nodes/kernel.md
# 对应测试文件路径: test/dsl/ast/nodes/test_kernel.py
def test_kernel_img2col2d_node_emits_img2col2d_op() -> None:
    input_value = _memory_node("input_value", Memory([1, 3, 8, 8], NumericType.Float32))
    out = _memory_node("out", Memory([1, 3, 3, 3, 8, 8], NumericType.Float32))
    ctx, block = _block_for_memories(out, input_value)

    emitted = KernelImg2Col2dAST(
        out,
        input_value,
        ConstValueAST(3),
        ConstValueAST(3),
        ph=ConstValueAST(1),
        pw=ConstValueAST(1),
        pl=ConstValueAST(1),
        pr=ConstValueAST(1),
    ).emit_mlir(ctx, block)

    assert isinstance(emitted, KernelImg2col2dOp)
