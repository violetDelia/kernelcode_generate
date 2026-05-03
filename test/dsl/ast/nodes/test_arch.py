"""DSL AST arch node tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast.nodes.arch` 的查询与动态内存节点。
- 测试结构对应 `spec/dsl/ast/nodes/arch.md` 与 `kernel_gen/dsl/ast/nodes/arch.py`。

使用示例:
- pytest -q test/dsl/ast/nodes/test_arch.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/nodes/arch.py
- Spec 文档: spec/dsl/ast/nodes/arch.md
- 测试文件: test/dsl/ast/nodes/test_arch.py
"""

from __future__ import annotations

import pytest
from xdsl.context import Context

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.arch import ArchGetDynamicMemoryOp, ArchGetThreadNumOp
from kernel_gen.dsl.ast.nodes.arch import ArchGetDynamicMemoryAST, ArchGetThreadNumAST, ArchQueryAST
from kernel_gen.dsl.ast.nodes.attr import MemorySpaceAttrAST
from kernel_gen.symbol_variable.memory import MemorySpace


def test_arch_query_base_node_rejects_direct_emit() -> None:
    """ArchQueryAST 基类不能直接 emit。"""

    with pytest.raises(KernelCodeError, match="ArchQueryAST base class cannot emit MLIR"):
        ArchQueryAST().emit_mlir(Context(), None)


def test_arch_get_thread_num_emits_specific_query_op() -> None:
    """get_thread_num 专用节点 emit 为对应 arch op。"""

    op = ArchGetThreadNumAST().emit_mlir(Context(), None)

    assert isinstance(op, ArchGetThreadNumOp)


def test_arch_dynamic_memory_uses_space_attr_node_emit() -> None:
    """dynamic memory 节点通过 MemorySpaceAttrAST.emit_mlir(...) 取得 space attr。"""

    ctx = Context()

    op = ArchGetDynamicMemoryAST(MemorySpaceAttrAST(MemorySpace.TSM)).emit_mlir(ctx, None)

    assert isinstance(op, ArchGetDynamicMemoryOp)
    assert op.memory_space.space.data == "tsm"
    assert op.result.type.space.space.data == "tsm"
