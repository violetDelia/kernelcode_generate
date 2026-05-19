"""multi-buffer pass tests.

功能说明:
- 覆盖 `MultiBufferPass` 的公开构造、registry option 与 matmul staging ring 化行为。
- 验证 lhs/rhs 成对生命周期才会改写，非目标结构和 stale slot use 均被公开断言锁定。

使用示例:
- pytest -q test/passes/test_multi_buffer.py

关联文件:
- 功能实现: kernel_gen/passes/multi_buffer.py
- Spec 文档: spec/pass/multi_buffer.md
- 测试文件: test/passes/test_multi_buffer.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects import func, scf
from xdsl.dialects.builtin import ArrayAttr, FunctionType, ModuleOp, i8, i32
from xdsl.ir import Block, Operation, Region, SSAValue
from xdsl.passes import ModulePass

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.dma import (
    DmaAdvanceRingOp,
    DmaAllocOp,
    DmaCopyOp,
    DmaCurrentRingOp,
    DmaFreeOp,
    DmaMakeRingOp,
    DmaRingType,
    DmaReshapeOp,
)
from kernel_gen.dialect.kernel import KernelMatmulOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolExprAttr, SymbolForOp, SymbolIterType, SymbolNeOp
from kernel_gen.passes.multi_buffer import MultiBufferPass
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes


def _make_memory_type(
    *,
    shape: tuple[int, ...],
    stride: tuple[int, ...],
    space: str,
) -> NnMemoryType:
    """构造 `MultiBufferPass` 测试用静态 memory type。

    功能说明:
    - 统一创建带公开 `SymbolExprAttr` shape/stride 的 `NnMemoryType`。

    使用示例:
    - mem_type = _make_memory_type(shape=(2, 3), stride=(3, 1), space="tlm1")

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    return NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr(str(dim)) for dim in shape]),
        ArrayAttr([SymbolExprAttr.from_expr(str(dim)) for dim in stride]),
        i32,
        NnMemorySpaceAttr.from_name(space),
    )


def _make_byte_pool_type(*, bytes_count: int, space: str) -> NnMemoryType:
    """构造 ring backing byte pool memory type。

    功能说明:
    - 为已有 ring no-op 测试创建公开 `dma.make_ring` 所需的一维 i8 backing memory。

    使用示例:
    - mem_type = _make_byte_pool_type(bytes_count=75, space="tlm1")

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    return NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr(str(bytes_count))]),
        ArrayAttr([SymbolExprAttr.from_expr("1")]),
        i8,
        NnMemorySpaceAttr.from_name(space),
    )


def _matmul_types() -> tuple[NnMemoryType, NnMemoryType, NnMemoryType, NnMemoryType, NnMemoryType]:
    """返回 matmul 输入输出和 staging memory type。

    功能说明:
    - 保持 source type 与 staging type 的 shape/stride/element_type 一致，仅 space 不同。

    使用示例:
    - out_type, lhs_type, rhs_type, lhs_slot_type, rhs_slot_type = _matmul_types()

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    out_type = _make_memory_type(shape=(2, 4), stride=(4, 1), space="tsm")
    lhs_type = _make_memory_type(shape=(2, 3), stride=(3, 1), space="tsm")
    rhs_type = _make_memory_type(shape=(3, 4), stride=(4, 1), space="tsm")
    lhs_slot_type = _make_memory_type(shape=(2, 3), stride=(3, 1), space="tlm1")
    rhs_slot_type = _make_memory_type(shape=(3, 4), stride=(4, 1), space="tlm2")
    return out_type, lhs_type, rhs_type, lhs_slot_type, rhs_slot_type


def _build_loop_matmul_module(
    *,
    lhs_free: bool = True,
    rhs_free: bool = True,
    free_before_matmul: bool = False,
    alias_escape: bool = False,
    extra_lhs_free: bool = False,
) -> tuple[ModuleOp, Block, SymbolForOp, Block, KernelMatmulOp]:
    """构造含 loop 内 matmul staging 生命周期的 module。

    功能说明:
    - 使用公开 dialect op 构造 `symbol.for` 直接 body 内的 lhs/rhs staging 模式。
    - 参数用于生成 no-op 边界输入。

    使用示例:
    - module, top_block, loop_op, loop_block, matmul = _build_loop_matmul_module()

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    out_type, lhs_type, rhs_type, lhs_slot_type, rhs_slot_type = _matmul_types()
    func_type = FunctionType.from_lists([out_type, lhs_type, rhs_type], [])
    top_block = Block(arg_types=[out_type, lhs_type, rhs_type])
    c0 = SymbolConstOp(0)
    c8 = SymbolConstOp(8)
    c1 = SymbolConstOp(1)

    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "8", "1")])
    lhs_alloc = DmaAllocOp([], lhs_slot_type)
    lhs_copy = DmaCopyOp(lhs_alloc.result, top_block.args[1])
    rhs_alloc = DmaAllocOp([], rhs_slot_type)
    rhs_copy = DmaCopyOp(rhs_alloc.result, top_block.args[2])
    matmul = KernelMatmulOp(top_block.args[0], lhs_alloc.result, rhs_alloc.result, NnMemorySpaceAttr.from_name("tsm"))
    lhs_free_op = DmaFreeOp(lhs_alloc.result)
    rhs_free_op = DmaFreeOp(rhs_alloc.result)

    body_ops: list[Operation] = [lhs_alloc, lhs_copy, rhs_alloc, rhs_copy]
    if alias_escape:
        dim2 = SymbolConstOp(2)
        dim3 = SymbolConstOp(3)
        alias = DmaReshapeOp(lhs_alloc.result, [dim2.result, dim3.result], lhs_slot_type)
        body_ops.extend([dim2, dim3, alias])
    if free_before_matmul:
        body_ops.append(lhs_free_op)
    body_ops.append(matmul)
    if lhs_free and not free_before_matmul:
        body_ops.append(lhs_free_op)
    if rhs_free:
        body_ops.append(rhs_free_op)
    if extra_lhs_free:
        body_ops.append(DmaFreeOp(lhs_alloc.result))
    loop_block.add_ops(body_ops)
    loop_op = SymbolForOp(c0.result, c8.result, c1.result, loop_block)
    top_block.add_ops([c0, c8, c1, loop_op, func.ReturnOp()])
    func_op = func.FuncOp("multi_buffer_matmul", func_type, Region(top_block))
    return ModuleOp([func_op]), top_block, loop_op, loop_block, matmul


def _walk_ops(module: ModuleOp, op_type: type[Operation]) -> list[Operation]:
    """收集 module 内指定 operation 类型。

    功能说明:
    - 为公开 pass 结果断言提供统一 walk helper。

    使用示例:
    - rings = _walk_ops(module, DmaMakeRingOp)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    return [op for op in module.walk() if isinstance(op, op_type)]


def _same_value(lhs: SSAValue, rhs: SSAValue) -> bool:
    """判断两个 SSA value 是否为同一公开对象。

    功能说明:
    - 避免测试依赖 SSA name hint，只比较公开 SSAValue identity。

    使用示例:
    - assert _same_value(copy.target, current.result)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    return SSAValue.get(lhs) is SSAValue.get(rhs)


def _assert_no_new_ring_rewrite(module: ModuleOp, initial_ring_count: int = 0) -> None:
    """断言 pass 没有新增 ring rewrite。

    功能说明:
    - 对 no-op 场景统一校验 `dma.make_ring` 数量不增加。

    使用示例:
    - _assert_no_new_ring_rewrite(module)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    assert len(_walk_ops(module, DmaMakeRingOp)) == initial_ring_count


def _assert_no_stale_current_slot_use(loop_block: Block) -> None:
    """断言 `dma.advance_ring` 后不再使用推进前 current slot。

    功能说明:
    - 对每个 current slot 找到同 ring 的 advance，检查 advance 之后没有 op 继续消费旧 current result。

    使用示例:
    - _assert_no_stale_current_slot_use(loop_block)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    body_ops = list(loop_block.ops)
    for current in [op for op in body_ops if isinstance(op, DmaCurrentRingOp)]:
        matching_advances = [
            op
            for op in body_ops
            if isinstance(op, DmaAdvanceRingOp) and _same_value(op.ring, current.ring)
        ]
        assert matching_advances
        first_advance_index = min(body_ops.index(op) for op in matching_advances)
        for op in body_ops[first_advance_index + 1 :]:
            assert all(not _same_value(operand, current.result) for operand in op.operands)


def _insert_existing_ring_operand(top_block: Block, loop_op: SymbolForOp, loop_block: Block, matmul: KernelMatmulOp) -> None:
    """把 matmul lhs 替换为已有 ring current slot。

    功能说明:
    - 构造合法 `dma.make_ring/current_ring` 作为输入，使 pass 必须识别已有 ring 并保持整对 no-op。

    使用示例:
    - _insert_existing_ring_operand(top_block, loop_op, loop_block, matmul)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    lhs_slot_type = SSAValue.get(matmul.operands[1]).type
    assert isinstance(lhs_slot_type, NnMemoryType)
    backing = DmaAllocOp([], _make_byte_pool_type(bytes_count=75, space=lhs_slot_type.space.space.data))
    count = SymbolConstOp(3)
    offset = SymbolConstOp(25)
    shape_bytes = SymbolConstOp(24)
    ring_type = DmaRingType(SymbolExprAttr.from_expr("25"), lhs_slot_type)
    make_ring = DmaMakeRingOp(backing.result, count.result, offset.result, shape_bytes.result, ring_type)
    current = DmaCurrentRingOp(make_ring.result)

    top_block.insert_ops_before([backing, count, offset, shape_bytes, make_ring], loop_op)
    loop_block.insert_ops_before([current], matmul)
    matmul.operands[1] = current.result


def _build_function_body_matmul_module() -> tuple[ModuleOp, Block, KernelMatmulOp]:
    """构造不在 `symbol.for` 直接 body 内的 matmul staging module。

    功能说明:
    - 用于验证 v1 只处理 `symbol.for` 直接 body 内的 staging 生命周期。

    使用示例:
    - module, top_block, matmul = _build_function_body_matmul_module()

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    out_type, lhs_type, rhs_type, lhs_slot_type, rhs_slot_type = _matmul_types()
    func_type = FunctionType.from_lists([out_type, lhs_type, rhs_type], [])
    top_block = Block(arg_types=[out_type, lhs_type, rhs_type])
    lhs_alloc = DmaAllocOp([], lhs_slot_type)
    lhs_copy = DmaCopyOp(lhs_alloc.result, top_block.args[1])
    rhs_alloc = DmaAllocOp([], rhs_slot_type)
    rhs_copy = DmaCopyOp(rhs_alloc.result, top_block.args[2])
    matmul = KernelMatmulOp(top_block.args[0], lhs_alloc.result, rhs_alloc.result, NnMemorySpaceAttr.from_name("tsm"))
    top_block.add_ops(
        [
            lhs_alloc,
            lhs_copy,
            rhs_alloc,
            rhs_copy,
            matmul,
            DmaFreeOp(lhs_alloc.result),
            DmaFreeOp(rhs_alloc.result),
            func.ReturnOp(),
        ]
    )
    func_op = func.FuncOp("multi_buffer_function_body_matmul", func_type, Region(top_block))
    return ModuleOp([func_op]), top_block, matmul


def _insert_nested_symbol_for_use(top_block: Block, loop_block: Block, matmul: KernelMatmulOp) -> SymbolForOp:
    """在 nested `symbol.for` 中插入额外 staging use。

    功能说明:
    - 通过公开 dialect op 构造跨 nested region 的 alloc use。
    - 用于锁定 `MultiBufferPass` 遇到 nested region use 时必须保持 no-op。

    使用示例:
    - nested_loop = _insert_nested_symbol_for_use(top_block, loop_block, matmul)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    lhs_alloc = SSAValue.get(matmul.operands[1]).owner
    assert isinstance(lhs_alloc, DmaAllocOp)
    c0 = SymbolConstOp(0)
    c2 = SymbolConstOp(2)
    c1 = SymbolConstOp(1)
    nested_block = Block(arg_types=[SymbolIterType.from_bounds("0", "2", "1")])
    nested_block.add_op(DmaCopyOp(lhs_alloc.result, top_block.args[1]))
    nested_loop = SymbolForOp(c0.result, c2.result, c1.result, nested_block)
    loop_block.insert_ops_before([c0, c2, c1, nested_loop], matmul)
    return nested_loop


def _insert_sibling_if_region_use(top_block: Block, loop_block: Block, matmul: KernelMatmulOp) -> scf.IfOp:
    """在 `scf.if` sibling branch 中插入额外 staging use。

    功能说明:
    - 用公开 `SymbolNeOp` 构造 if condition，并在 then branch 使用外层 alloc。
    - 用于锁定 sibling region use 不会被 `MultiBufferPass` 误判为 direct body 生命周期。

    使用示例:
    - if_op = _insert_sibling_if_region_use(top_block, loop_block, matmul)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    lhs_alloc = SSAValue.get(matmul.operands[1]).owner
    assert isinstance(lhs_alloc, DmaAllocOp)
    cond_lhs = SymbolConstOp(0)
    cond_rhs = SymbolConstOp(1)
    condition = SymbolNeOp(cond_lhs.result, cond_rhs.result)
    then_block = Block()
    then_block.add_op(DmaCopyOp(lhs_alloc.result, top_block.args[1]))
    then_block.add_op(scf.YieldOp())
    else_block = Block()
    else_block.add_op(scf.YieldOp())
    if_op = scf.IfOp(condition.result, [], [then_block], [else_block])
    loop_block.insert_ops_before([cond_lhs, cond_rhs, condition, if_op], matmul)
    return if_op


# TC-MULTI-BUFFER-001
# 功能说明: 验证公开构造参数与 from_options 边界。
# 使用示例: pytest -q test/passes/test_multi_buffer.py -k test_multi_buffer_public_options
# 对应功能实现文件路径: kernel_gen/passes/multi_buffer.py
# 对应 spec 文件路径: spec/pass/multi_buffer.md
# 对应测试文件路径: test/passes/test_multi_buffer.py
def test_multi_buffer_public_options() -> None:
    pass_obj = MultiBufferPass(memory_stage=4, fold=False)

    assert pass_obj.name == "multi-buffer"
    assert pass_obj.memory_stage == 4
    assert pass_obj.fold is False
    assert MultiBufferPass(memory_stage=1).memory_stage == 1
    assert MultiBufferPass.from_options({"memory-stage": "1"}).memory_stage == 1
    assert MultiBufferPass.from_options({"memory-stage": "5"}).memory_stage == 5
    with pytest.raises(KernelCodeError, match="memory_stage must be positive"):
        MultiBufferPass(memory_stage=0)
    with pytest.raises(KernelCodeError, match="memory-stage must be positive"):
        MultiBufferPass.from_options({"memory-stage": "0"})
    with pytest.raises(KernelCodeError, match="memory-stage must be positive"):
        MultiBufferPass.from_options({"memory-stage": "-1"})
    with pytest.raises(KernelCodeError, match="unknown option: fold"):
        MultiBufferPass.from_options({"fold": "false"})


# TC-MULTI-BUFFER-002
# 功能说明: 验证 registry 可构造 multi-buffer，并由 registry 通用 fold 处理 fold option。
# 使用示例: pytest -q test/passes/test_multi_buffer.py -k test_multi_buffer_registry_options
# 对应功能实现文件路径: kernel_gen/passes/multi_buffer.py
# 对应 spec 文件路径: spec/pass/multi_buffer.md
# 对应测试文件路径: test/passes/test_multi_buffer.py
def test_multi_buffer_registry_options() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("multi-buffer", {"memory-stage": "3", "fold": "false"})

    assert isinstance(pass_obj, MultiBufferPass)
    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.memory_stage == 3
    assert pass_obj.fold is False


# TC-MULTI-BUFFER-003
# 功能说明: 验证 lhs/rhs 成对 staging 生命周期会被改写成 DMA ring。
# 使用示例: pytest -q test/passes/test_multi_buffer.py -k test_multi_buffer_rewrites_matmul_lhs_rhs_pair
# 对应功能实现文件路径: kernel_gen/passes/multi_buffer.py
# 对应 spec 文件路径: spec/pass/multi_buffer.md
# 对应测试文件路径: test/passes/test_multi_buffer.py
def test_multi_buffer_rewrites_matmul_lhs_rhs_pair() -> None:
    module, top_block, _loop_op, loop_block, matmul = _build_loop_matmul_module()

    MultiBufferPass(memory_stage=3).apply(Context(), module)

    make_rings = _walk_ops(module, DmaMakeRingOp)
    currents = _walk_ops(module, DmaCurrentRingOp)
    advances = _walk_ops(module, DmaAdvanceRingOp)
    assert len(make_rings) == 2
    assert len(currents) == 2
    assert len(advances) == 2
    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in loop_block.ops)
    assert len([op for op in top_block.ops if isinstance(op, DmaAllocOp)]) == 2
    copies = [op for op in loop_block.ops if isinstance(op, DmaCopyOp)]
    assert len(copies) == 2
    assert _same_value(copies[0].target, currents[0].result)
    assert _same_value(copies[1].target, currents[1].result)
    assert _same_value(matmul.operands[1], currents[0].result)
    assert _same_value(matmul.operands[2], currents[1].result)
    body_ops = list(loop_block.ops)
    assert body_ops.index(currents[0]) < body_ops.index(copies[0]) < body_ops.index(matmul)
    assert body_ops.index(currents[1]) < body_ops.index(copies[1]) < body_ops.index(matmul)
    assert body_ops.index(matmul) < body_ops.index(advances[0])
    assert body_ops.index(matmul) < body_ops.index(advances[1])
    _assert_no_stale_current_slot_use(loop_block)
    module.verify()


# TC-MULTI-BUFFER-004
# 功能说明: 验证缺少任一 staging free 时整对保持 no-op。
# 使用示例: pytest -q test/passes/test_multi_buffer.py -k test_multi_buffer_keeps_missing_free_noop
# 对应功能实现文件路径: kernel_gen/passes/multi_buffer.py
# 对应 spec 文件路径: spec/pass/multi_buffer.md
# 对应测试文件路径: test/passes/test_multi_buffer.py
def test_multi_buffer_keeps_missing_free_noop() -> None:
    module, _top_block, _loop_op, loop_block, matmul = _build_loop_matmul_module(lhs_free=False)
    original_operands = list(matmul.operands)

    MultiBufferPass(memory_stage=3).apply(Context(), module)

    _assert_no_new_ring_rewrite(module)
    assert list(matmul.operands) == original_operands
    assert len([op for op in loop_block.ops if isinstance(op, DmaAllocOp)]) == 2
    assert len([op for op in loop_block.ops if isinstance(op, DmaFreeOp)]) == 1
    module.verify()


# TC-MULTI-BUFFER-005
# 功能说明: 验证 free 早于 matmul use 时保持 no-op。
# 使用示例: pytest -q test/passes/test_multi_buffer.py -k test_multi_buffer_keeps_free_before_matmul_noop
# 对应功能实现文件路径: kernel_gen/passes/multi_buffer.py
# 对应 spec 文件路径: spec/pass/multi_buffer.md
# 对应测试文件路径: test/passes/test_multi_buffer.py
def test_multi_buffer_keeps_free_before_matmul_noop() -> None:
    module, _top_block, _loop_op, loop_block, matmul = _build_loop_matmul_module(free_before_matmul=True)
    original_operands = list(matmul.operands)

    MultiBufferPass(memory_stage=3).apply(Context(), module)

    _assert_no_new_ring_rewrite(module)
    assert list(matmul.operands) == original_operands
    assert len([op for op in loop_block.ops if isinstance(op, DmaAllocOp)]) == 2
    module.verify()


# TC-MULTI-BUFFER-006
# 功能说明: 验证 alloc result 存在额外 alias use 时保持 no-op，避免宽泛 alias 推断。
# 使用示例: pytest -q test/passes/test_multi_buffer.py -k test_multi_buffer_keeps_alias_escape_noop
# 对应功能实现文件路径: kernel_gen/passes/multi_buffer.py
# 对应 spec 文件路径: spec/pass/multi_buffer.md
# 对应测试文件路径: test/passes/test_multi_buffer.py
def test_multi_buffer_keeps_alias_escape_noop() -> None:
    module, _top_block, _loop_op, loop_block, matmul = _build_loop_matmul_module(alias_escape=True)
    original_operands = list(matmul.operands)

    MultiBufferPass(memory_stage=3).apply(Context(), module)

    _assert_no_new_ring_rewrite(module)
    assert list(matmul.operands) == original_operands
    assert any(isinstance(op, DmaReshapeOp) for op in loop_block.ops)
    module.verify()


# TC-MULTI-BUFFER-007
# 功能说明: 验证 allocator 存在多 free 时整对保持 no-op。
# 使用示例: pytest -q test/passes/test_multi_buffer.py -k test_multi_buffer_keeps_multiple_free_noop
# 对应功能实现文件路径: kernel_gen/passes/multi_buffer.py
# 对应 spec 文件路径: spec/pass/multi_buffer.md
# 对应测试文件路径: test/passes/test_multi_buffer.py
def test_multi_buffer_keeps_multiple_free_noop() -> None:
    module, _top_block, _loop_op, loop_block, matmul = _build_loop_matmul_module(extra_lhs_free=True)
    original_operands = list(matmul.operands)

    MultiBufferPass(memory_stage=3).apply(Context(), module)

    _assert_no_new_ring_rewrite(module)
    assert list(matmul.operands) == original_operands
    assert len([op for op in loop_block.ops if isinstance(op, DmaFreeOp)]) == 3
    module.verify()


# TC-MULTI-BUFFER-008
# 功能说明: 验证已有 ring 输入时保持 no-op，不能与当前 staging pair 混写。
# 使用示例: pytest -q test/passes/test_multi_buffer.py -k test_multi_buffer_keeps_existing_ring_noop
# 对应功能实现文件路径: kernel_gen/passes/multi_buffer.py
# 对应 spec 文件路径: spec/pass/multi_buffer.md
# 对应测试文件路径: test/passes/test_multi_buffer.py
def test_multi_buffer_keeps_existing_ring_noop() -> None:
    module, top_block, loop_op, loop_block, matmul = _build_loop_matmul_module()
    _insert_existing_ring_operand(top_block, loop_op, loop_block, matmul)
    operands_before_pass = list(matmul.operands)

    MultiBufferPass(memory_stage=3).apply(Context(), module)

    _assert_no_new_ring_rewrite(module, initial_ring_count=1)
    assert list(matmul.operands) == operands_before_pass
    assert len([op for op in loop_block.ops if isinstance(op, DmaAllocOp)]) == 2
    module.verify()


# TC-MULTI-BUFFER-009
# 功能说明: 验证 lhs-only / rhs-only partial pair 保持 no-op。
# 使用示例: pytest -q test/passes/test_multi_buffer.py -k test_multi_buffer_keeps_partial_pair_noop
# 对应功能实现文件路径: kernel_gen/passes/multi_buffer.py
# 对应 spec 文件路径: spec/pass/multi_buffer.md
# 对应测试文件路径: test/passes/test_multi_buffer.py
@pytest.mark.parametrize(("operand_index", "source_arg_index"), [(1, 1), (2, 2)])
def test_multi_buffer_keeps_partial_pair_noop(operand_index: int, source_arg_index: int) -> None:
    module, top_block, _loop_op, loop_block, matmul = _build_loop_matmul_module()
    matmul.operands[operand_index] = top_block.args[source_arg_index]
    operands_before_pass = list(matmul.operands)

    MultiBufferPass(memory_stage=3).apply(Context(), module)

    _assert_no_new_ring_rewrite(module)
    assert list(matmul.operands) == operands_before_pass
    assert len([op for op in loop_block.ops if isinstance(op, DmaAllocOp)]) == 2
    module.verify()


# TC-MULTI-BUFFER-010
# 功能说明: 验证不在 symbol.for 直接 body 内的 matmul 不被 v1 ring 化。
# 使用示例: pytest -q test/passes/test_multi_buffer.py -k test_multi_buffer_keeps_non_direct_body_noop
# 对应功能实现文件路径: kernel_gen/passes/multi_buffer.py
# 对应 spec 文件路径: spec/pass/multi_buffer.md
# 对应测试文件路径: test/passes/test_multi_buffer.py
def test_multi_buffer_keeps_non_direct_body_noop() -> None:
    module, top_block, matmul = _build_function_body_matmul_module()
    original_operands = list(matmul.operands)

    MultiBufferPass(memory_stage=3).apply(Context(), module)

    _assert_no_new_ring_rewrite(module)
    assert list(matmul.operands) == original_operands
    assert len([op for op in top_block.ops if isinstance(op, DmaAllocOp)]) == 2
    module.verify()


# TC-MULTI-BUFFER-011
# 功能说明: 验证 loop 内没有 matmul 时保持 no-op。
# 使用示例: pytest -q test/passes/test_multi_buffer.py -k test_multi_buffer_keeps_non_matmul_noop
# 对应功能实现文件路径: kernel_gen/passes/multi_buffer.py
# 对应 spec 文件路径: spec/pass/multi_buffer.md
# 对应测试文件路径: test/passes/test_multi_buffer.py
def test_multi_buffer_keeps_non_matmul_noop() -> None:
    module, _top_block, _loop_op, loop_block, matmul = _build_loop_matmul_module()
    loop_block.erase_op(matmul)

    MultiBufferPass(memory_stage=3).apply(Context(), module)

    _assert_no_new_ring_rewrite(module)
    assert len([op for op in loop_block.ops if isinstance(op, DmaAllocOp)]) == 2
    assert len([op for op in loop_block.ops if isinstance(op, DmaFreeOp)]) == 2
    module.verify()


# TC-MULTI-BUFFER-012
# 功能说明: 验证 accumulator/output alloc 不属于 lhs/rhs staging pair 时不会被 ring 化。
# 使用示例: pytest -q test/passes/test_multi_buffer.py -k test_multi_buffer_keeps_accumulator_alloc_unringed
# 对应功能实现文件路径: kernel_gen/passes/multi_buffer.py
# 对应 spec 文件路径: spec/pass/multi_buffer.md
# 对应测试文件路径: test/passes/test_multi_buffer.py
def test_multi_buffer_keeps_accumulator_alloc_unringed() -> None:
    module, _top_block, _loop_op, loop_block, matmul = _build_loop_matmul_module()
    out_type = SSAValue.get(matmul.operands[0]).type
    assert isinstance(out_type, NnMemoryType)
    accumulator = DmaAllocOp([], out_type)
    loop_block.insert_ops_before([accumulator], matmul)
    matmul.operands[0] = accumulator.result
    loop_block.insert_ops_after([DmaFreeOp(accumulator.result)], matmul)
    operands_before_pass = list(matmul.operands)

    MultiBufferPass(memory_stage=3).apply(Context(), module)

    assert len(_walk_ops(module, DmaMakeRingOp)) == 2
    assert _same_value(matmul.operands[0], operands_before_pass[0])
    assert not _same_value(matmul.operands[1], operands_before_pass[1])
    assert not _same_value(matmul.operands[2], operands_before_pass[2])
    assert len([op for op in loop_block.ops if isinstance(op, DmaAllocOp)]) == 1
    assert len([op for op in loop_block.ops if isinstance(op, DmaFreeOp)]) == 1
    module.verify()


# TC-MULTI-BUFFER-013
# 功能说明: 验证 staging alloc 存在 nested symbol.for region use 时整对保持 no-op。
# 使用示例: pytest -q test/passes/test_multi_buffer.py -k test_multi_buffer_keeps_nested_region_use_noop
# 对应功能实现文件路径: kernel_gen/passes/multi_buffer.py
# 对应 spec 文件路径: spec/pass/multi_buffer.md
# 对应测试文件路径: test/passes/test_multi_buffer.py
def test_multi_buffer_keeps_nested_region_use_noop() -> None:
    module, top_block, _loop_op, loop_block, matmul = _build_loop_matmul_module()
    nested_loop = _insert_nested_symbol_for_use(top_block, loop_block, matmul)
    operands_before_pass = list(matmul.operands)

    MultiBufferPass(memory_stage=3).apply(Context(), module)

    _assert_no_new_ring_rewrite(module)
    assert list(matmul.operands) == operands_before_pass
    assert nested_loop in list(loop_block.ops)
    assert len([op for op in loop_block.ops if isinstance(op, DmaAllocOp)]) == 2
    module.verify()


# TC-MULTI-BUFFER-014
# 功能说明: 验证 staging alloc 存在 sibling branch region use 时整对保持 no-op。
# 使用示例: pytest -q test/passes/test_multi_buffer.py -k test_multi_buffer_keeps_sibling_region_use_noop
# 对应功能实现文件路径: kernel_gen/passes/multi_buffer.py
# 对应 spec 文件路径: spec/pass/multi_buffer.md
# 对应测试文件路径: test/passes/test_multi_buffer.py
def test_multi_buffer_keeps_sibling_region_use_noop() -> None:
    module, top_block, _loop_op, loop_block, matmul = _build_loop_matmul_module()
    if_op = _insert_sibling_if_region_use(top_block, loop_block, matmul)
    operands_before_pass = list(matmul.operands)

    MultiBufferPass(memory_stage=3).apply(Context(), module)

    _assert_no_new_ring_rewrite(module)
    assert list(matmul.operands) == operands_before_pass
    assert if_op in list(loop_block.ops)
    assert len([op for op in loop_block.ops if isinstance(op, DmaAllocOp)]) == 2
    module.verify()
