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
from xdsl.ir import Block

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.arch import (
    ArchBarrierOp,
    ArchGetBlockIdOp,
    ArchGetBlockNumOp,
    ArchGetDynamicMemoryOp,
    ArchGetSubthreadIdOp,
    ArchGetSubthreadNumOp,
    ArchGetThreadIdOp,
    ArchGetThreadNumOp,
    ArchLaunchKernelOp,
)
from kernel_gen.dialect.symbol import SymbolConstOp
from kernel_gen.dsl.ast.nodes.arch import (
    ArchBarrierAST,
    ArchGetBlockIdAST,
    ArchGetBlockNumAST,
    ArchGetDynamicMemoryAST,
    ArchGetSubthreadIdAST,
    ArchGetSubthreadNumAST,
    ArchGetThreadIdAST,
    ArchGetThreadNumAST,
    ArchLaunchKernelAST,
    ArchQueryAST,
)
from kernel_gen.dsl.ast.nodes.attr import MemorySpaceAttrAST
from kernel_gen.dsl.ast.nodes.basic import ValueAST
from kernel_gen.dsl.ast.nodes.symbol import ConstValueAST
from kernel_gen.operation.arch import BarrierScope, BarrierVisibility
from kernel_gen.symbol_variable.memory import MemorySpace


class _DetachedConstValueAST(ValueAST):
    """测试公开 ValueAST 合同中返回 unattached symbol operation 的路径。"""

    def __init__(self, value: int) -> None:
        self.value = value

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> SymbolConstOp:
        return SymbolConstOp(self.value)


class _NoValueAST(ValueAST):
    """测试公开 ValueAST 合同中不产生 SSA value 的失败路径。"""

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> None:
        return None


def test_arch_query_base_node_rejects_direct_emit() -> None:
    """ArchQueryAST 基类不能直接 emit。"""

    with pytest.raises(KernelCodeError, match="ArchQueryAST base class cannot emit MLIR"):
        ArchQueryAST().emit_mlir(Context(), None)


def test_arch_get_thread_num_emits_specific_query_op() -> None:
    """get_thread_num 专用节点 emit 为对应 arch op。"""

    op = ArchGetThreadNumAST().emit_mlir(Context(), None)

    assert isinstance(op, ArchGetThreadNumOp)


@pytest.mark.parametrize(
    ("node", "op_type"),
    [
        (ArchGetBlockIdAST(), ArchGetBlockIdOp),
        (ArchGetBlockNumAST(), ArchGetBlockNumOp),
        (ArchGetSubthreadIdAST(), ArchGetSubthreadIdOp),
        (ArchGetSubthreadNumAST(), ArchGetSubthreadNumOp),
        (ArchGetThreadIdAST(), ArchGetThreadIdOp),
        (ArchGetThreadNumAST(), ArchGetThreadNumOp),
    ],
)
def test_arch_query_nodes_emit_specific_public_ops(node: ArchQueryAST, op_type: type) -> None:
    """各 arch 查询节点通过公开 emit_mlir 发射对应 op。"""

    assert isinstance(node.emit_mlir(Context(), None), op_type)


def test_arch_dynamic_memory_uses_space_attr_node_emit() -> None:
    """dynamic memory 节点通过 MemorySpaceAttrAST.emit_mlir(...) 取得 space attr。"""

    ctx = Context()

    op = ArchGetDynamicMemoryAST(MemorySpaceAttrAST(MemorySpace.TSM)).emit_mlir(ctx, None)

    assert isinstance(op, ArchGetDynamicMemoryOp)
    assert op.memory_space.space.data == "tsm"
    assert op.result.type.space.space.data == "tsm"


@pytest.mark.parametrize(
    ("space", "space_name", "size_symbol"),
    [
        (MemorySpace.SM, "shared", "SM_SIZE"),
        (MemorySpace.LM, "local", "LM_SIZE"),
        (MemorySpace.TSM, "tsm", "TSM_SIZE"),
        (MemorySpace.TLM1, "tlm1", "TLM1_SIZE"),
        (MemorySpace.TLM2, "tlm2", "TLM2_SIZE"),
        (MemorySpace.TLM3, "tlm3", "TLM3_SIZE"),
    ],
)
def test_arch_dynamic_memory_emits_all_on_chip_spaces(
    space: MemorySpace,
    space_name: str,
    size_symbol: str,
) -> None:
    """dynamic memory 覆盖 spec 定义的所有片上空间。"""

    op = ArchGetDynamicMemoryAST(space).emit_mlir(Context(), None)

    assert isinstance(op, ArchGetDynamicMemoryOp)
    assert op.memory_space.space.data == space_name
    assert op.result.type.shape.data[0].data == size_symbol


def test_arch_dynamic_memory_rejects_global_space() -> None:
    """dynamic memory 拒绝非片上 GM 空间。"""

    with pytest.raises(KernelCodeError, match="get_dynamic_memory space must be on-chip MemorySpace"):
        ArchGetDynamicMemoryAST(MemorySpace.GM).emit_mlir(Context(), None)


def test_arch_barrier_emits_and_rejects_public_attrs() -> None:
    """barrier 节点通过公开 enum 发射 arch.barrier 并拒绝非法枚举类型。"""

    op = ArchBarrierAST(
        visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM],
        scope=BarrierScope.THREAD,
    ).emit_mlir(Context(), None)

    assert isinstance(op, ArchBarrierOp)
    assert op.scope.scope.data == "thread"
    assert [item.visibility.data for item in op.visibility.data] == ["tsm", "tlm"]

    with pytest.raises(KernelCodeError, match="barrier scope must be BarrierScope"):
        ArchBarrierAST(visibility=[BarrierVisibility.TSM], scope="thread").emit_mlir(Context(), None)

    with pytest.raises(KernelCodeError, match="barrier visibility must be BarrierVisibility"):
        ArchBarrierAST(visibility=["tsm"], scope=BarrierScope.THREAD).emit_mlir(Context(), None)


def test_arch_launch_kernel_emits_public_abi_with_args() -> None:
    """launch_kernel 节点发射四字段 ABI 与公开 args 列表。"""

    block = Block()
    op = ArchLaunchKernelAST(
        callee="kernel_body",
        block=1,
        thread=2,
        subthread=3,
        shared_memory_size=0,
        args=[ConstValueAST(4), _DetachedConstValueAST(5)],
    ).emit_mlir(Context(), block)

    assert isinstance(op, ArchLaunchKernelOp)
    assert op.callee.root_reference.data == "kernel_body"
    assert len(op.args) == 2


def test_arch_launch_kernel_rejects_arg_without_ssa_value() -> None:
    """launch_kernel 拒绝不能 lower 成 SSA value 的公开 ValueAST arg。"""

    with pytest.raises(KernelCodeError, match="launch_kernel arg must lower to SSA value"):
        ArchLaunchKernelAST(
            callee="kernel_body",
            block=1,
            thread=1,
            subthread=1,
            args=[_NoValueAST()],
        ).emit_mlir(Context(), Block())
