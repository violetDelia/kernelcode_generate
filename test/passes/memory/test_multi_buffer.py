"""multi-buffer pass tests.

功能说明:
- 覆盖 `MultiBufferPass` 的公开构造、registry option 与 matmul staging ring 化行为。
- 验证 loop 外 lhs/rhs staging 生命周期会被改写为 DMA ring，target 优先路径按 target memory capacity 计算 num。

使用示例:
- pytest -q test/passes/memory/test_multi_buffer.py

关联文件:
- 功能实现: kernel_gen/passes/memory/multi_buffer.py
- Spec 文档: spec/pass/memory/multi_buffer.md
- 测试文件: test/passes/memory/test_multi_buffer.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, ModuleOp, f32, i8, i32
from xdsl.ir import Attribute, Block, Operation, Region, SSAValue
from xdsl.passes import ModulePass

REPO_ROOT = Path(__file__).resolve().parents[3]
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
    DmaReshapeOp,
    DmaRingType,
    DmaSliceOp,
)
from kernel_gen.dialect.kernel import KernelMatmulOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolExprAttr, SymbolForOp, SymbolIterType, SymbolValueType
from kernel_gen.passes.memory.multi_buffer import MultiBufferPass
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes


def _symbol_array(values: tuple[int | str, ...]) -> ArrayAttr[Attribute]:
    """构造公开 `SymbolExprAttr` 数组。

    功能说明:
    - 为 memory shape/stride 和 symbol type 构造稳定测试输入。

    使用示例:
    - dims = _symbol_array((2, "S1"))

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    return ArrayAttr([SymbolExprAttr.from_expr(str(value)) for value in values])


def _make_memory_type(
    *,
    shape: tuple[int | str, ...],
    stride: tuple[int | str, ...],
    space: str,
    element_type: Attribute = i32,
) -> NnMemoryType:
    """构造 `MultiBufferPass` 测试用 memory type。

    功能说明:
    - 统一创建带公开 `SymbolExprAttr` shape/stride 的 `NnMemoryType`。

    使用示例:
    - mem_type = _make_memory_type(shape=(2, 3), stride=(3, 1), space="tlm1")

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    return NnMemoryType(
        _symbol_array(shape),
        _symbol_array(stride),
        element_type,
        NnMemorySpaceAttr.from_name(space),
    )


def _make_byte_pool_type(*, bytes_count: int, space: str) -> NnMemoryType:
    """构造 ring backing byte pool memory type。

    功能说明:
    - 为已有 ring no-op 测试创建公开 `dma.make_ring` 所需的一维 i8 backing memory。

    使用示例:
    - mem_type = _make_byte_pool_type(bytes_count=72, space="tlm1")

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    return _make_memory_type(shape=(bytes_count,), stride=(1,), space=space, element_type=i8)


def _matmul_types(
    *,
    m_dim: int = 2,
    k_dim: int = 3,
    n_dim: int = 4,
    lhs_space: str = "tlm1",
    rhs_space: str = "tlm2",
    element_type: Attribute = i32,
) -> tuple[NnMemoryType, NnMemoryType, NnMemoryType, NnMemoryType, NnMemoryType]:
    """返回 matmul 输入输出和 staging memory type。

    功能说明:
    - 保持 source type 与 staging type 的 shape/stride/element_type 一致，仅 space 不同。

    使用示例:
    - out_type, lhs_type, rhs_type, lhs_slot_type, rhs_slot_type = _matmul_types()

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    out_type = _make_memory_type(shape=(m_dim, n_dim), stride=(n_dim, 1), space="tsm", element_type=element_type)
    lhs_type = _make_memory_type(shape=(m_dim, k_dim), stride=(k_dim, 1), space="tsm", element_type=element_type)
    rhs_type = _make_memory_type(shape=(k_dim, n_dim), stride=(n_dim, 1), space="tsm", element_type=element_type)
    lhs_slot_type = _make_memory_type(shape=(m_dim, k_dim), stride=(k_dim, 1), space=lhs_space, element_type=element_type)
    rhs_slot_type = _make_memory_type(shape=(k_dim, n_dim), stride=(n_dim, 1), space=rhs_space, element_type=element_type)
    return out_type, lhs_type, rhs_type, lhs_slot_type, rhs_slot_type


def _build_loop_matmul_module(
    *,
    lhs_space: str = "tlm1",
    rhs_space: str = "tlm2",
    m_dim: int = 2,
    k_dim: int = 3,
    n_dim: int = 4,
    lhs_free: bool = True,
    rhs_free: bool = True,
    free_before_loop: bool = False,
    alias_escape: bool = False,
    extra_lhs_free: bool = False,
    alloc_inside_loop: bool = False,
) -> tuple[ModuleOp, Block, SymbolForOp, Block, KernelMatmulOp, NnMemoryType, NnMemoryType]:
    """构造含 loop 外 matmul staging 生命周期的 module。

    功能说明:
    - 默认输入为 `symbol.for` 外 `dma.alloc/free`、loop body 内 `dma.copy + kernel.matmul`。
    - 参数用于生成 no-op 边界输入。

    使用示例:
    - module, top_block, loop_op, loop_block, matmul, lhs_slot, rhs_slot = _build_loop_matmul_module()

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    out_type, lhs_type, rhs_type, lhs_slot_type, rhs_slot_type = _matmul_types(
        m_dim=m_dim,
        k_dim=k_dim,
        n_dim=n_dim,
        lhs_space=lhs_space,
        rhs_space=rhs_space,
    )
    func_type = FunctionType.from_lists([out_type, lhs_type, rhs_type], [])
    top_block = Block(arg_types=[out_type, lhs_type, rhs_type])
    c0 = SymbolConstOp(0)
    c8 = SymbolConstOp(8)
    c1 = SymbolConstOp(1)

    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "8", "1")])
    lhs_alloc = DmaAllocOp([], lhs_slot_type)
    rhs_alloc = DmaAllocOp([], rhs_slot_type)
    lhs_copy = DmaCopyOp(lhs_alloc.result, top_block.args[1])
    rhs_copy = DmaCopyOp(rhs_alloc.result, top_block.args[2])
    matmul = KernelMatmulOp(top_block.args[0], lhs_alloc.result, rhs_alloc.result, NnMemorySpaceAttr.from_name("tsm"))
    body_ops: list[Operation] = []
    if alloc_inside_loop:
        body_ops.extend([lhs_alloc, rhs_alloc])
    body_ops.extend([lhs_copy, rhs_copy])
    if alias_escape:
        dim2 = SymbolConstOp(m_dim)
        dim3 = SymbolConstOp(k_dim)
        alias = DmaReshapeOp(lhs_alloc.result, [dim2.result, dim3.result], lhs_slot_type)
        body_ops.extend([dim2, dim3, alias])
    body_ops.append(matmul)
    if alloc_inside_loop:
        if lhs_free:
            body_ops.append(DmaFreeOp(lhs_alloc.result))
        if rhs_free:
            body_ops.append(DmaFreeOp(rhs_alloc.result))
        if extra_lhs_free:
            body_ops.append(DmaFreeOp(lhs_alloc.result))
    loop_block.add_ops(body_ops)
    loop_op = SymbolForOp(c0.result, c8.result, c1.result, loop_block)

    top_ops: list[Operation] = [c0, c8, c1]
    if not alloc_inside_loop:
        top_ops.extend([lhs_alloc, rhs_alloc])
        if free_before_loop and lhs_free:
            top_ops.append(DmaFreeOp(lhs_alloc.result))
    top_ops.append(loop_op)
    if not alloc_inside_loop:
        if lhs_free and not free_before_loop:
            top_ops.append(DmaFreeOp(lhs_alloc.result))
        if rhs_free:
            top_ops.append(DmaFreeOp(rhs_alloc.result))
        if extra_lhs_free:
            top_ops.append(DmaFreeOp(lhs_alloc.result))
    top_ops.append(func.ReturnOp())
    top_block.add_ops(top_ops)
    func_op = func.FuncOp("multi_buffer_matmul", func_type, Region(top_block))
    return ModuleOp([func_op]), top_block, loop_op, loop_block, matmul, lhs_slot_type, rhs_slot_type


def _build_dynamic_same_space_module() -> tuple[ModuleOp, Block, SymbolForOp, Block, KernelMatmulOp]:
    """构造动态 shape same-space target 测试 module。

    功能说明:
    - 输入 staging 使用 `dma.alloc(%s1, %s2)` 与 `dma.alloc(%s2, %s3)`，动态 shape 来源为 kernel 参数。

    使用示例:
    - module, top_block, loop_op, loop_block, matmul = _build_dynamic_same_space_module()

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    s1_type = SymbolValueType.from_expr("S1")
    s2_type = SymbolValueType.from_expr("S2")
    s3_type = SymbolValueType.from_expr("S3")
    out_type = _make_memory_type(shape=("S1", "S3"), stride=("S3", 1), space="tsm", element_type=f32)
    lhs_type = _make_memory_type(shape=("S1", "S2"), stride=("S2", 1), space="tsm", element_type=f32)
    rhs_type = _make_memory_type(shape=("S2", "S3"), stride=("S3", 1), space="tsm", element_type=f32)
    lhs_slot_type = _make_memory_type(shape=("S1", "S2"), stride=("S2", 1), space="tlm1", element_type=f32)
    rhs_slot_type = _make_memory_type(shape=("S2", "S3"), stride=("S3", 1), space="tlm1", element_type=f32)
    func_type = FunctionType.from_lists([out_type, lhs_type, rhs_type, s1_type, s2_type, s3_type], [])
    top_block = Block(arg_types=[out_type, lhs_type, rhs_type, s1_type, s2_type, s3_type])
    c0 = SymbolConstOp(0)
    c7 = SymbolConstOp(7)
    c1 = SymbolConstOp(1)
    lhs_alloc = DmaAllocOp([top_block.args[3], top_block.args[4]], lhs_slot_type)
    rhs_alloc = DmaAllocOp([top_block.args[4], top_block.args[5]], rhs_slot_type)
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "7", "1")])
    lhs_copy = DmaCopyOp(lhs_alloc.result, top_block.args[1])
    rhs_copy = DmaCopyOp(rhs_alloc.result, top_block.args[2])
    matmul = KernelMatmulOp(top_block.args[0], lhs_alloc.result, rhs_alloc.result, NnMemorySpaceAttr.from_name("tsm"))
    loop_block.add_ops([lhs_copy, rhs_copy, matmul])
    loop_op = SymbolForOp(c0.result, c7.result, c1.result, loop_block)
    top_block.add_ops(
        [
            c0,
            c7,
            c1,
            lhs_alloc,
            rhs_alloc,
            loop_op,
            DmaFreeOp(lhs_alloc.result),
            DmaFreeOp(rhs_alloc.result),
            func.ReturnOp(),
        ]
    )
    func_op = func.FuncOp("multi_buffer_matmul_dynamic_same_space", func_type, Region(top_block))
    return ModuleOp([func_op]), top_block, loop_op, loop_block, matmul


def _build_loop_local_direct_slice_module() -> tuple[ModuleOp, Block, SymbolForOp, Block, DmaSliceOp, NnMemoryType]:
    """构造 loop-local direct-use staging alloc 测试 module。

    功能说明:
    - 在 `symbol.for` body 内创建 `dma.alloc -> dma.slice -> dma.free` 生命周期。
    - 该形态没有中间 view alias，用于覆盖 direct alloc use 的 loop-local `num=1` ring 化。

    使用示例:
    - module, top_block, loop_op, loop_block, slice_op, slot_type = _build_loop_local_direct_slice_module()

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    slot_type = NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr("4")]),
        ArrayAttr([SymbolExprAttr.from_expr("1")]),
        i32,
        NnMemorySpaceAttr.from_name("tlm1"),
    )
    source_type = NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr("4")]),
        ArrayAttr([SymbolExprAttr.from_expr("1")]),
        i32,
        NnMemorySpaceAttr.from_name("global"),
    )
    func_type = FunctionType.from_lists([source_type], [])
    top_block = Block(arg_types=[source_type])
    c0 = SymbolConstOp(0)
    c4 = SymbolConstOp(4)
    c1 = SymbolConstOp(1)
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "4", "1")])
    alloc = DmaAllocOp([], slot_type)
    slice_op = DmaSliceOp(alloc.result, top_block.args[0], [c0.result], [c4.result], [c1.result])
    loop_block.add_ops([alloc, slice_op, DmaFreeOp(alloc.result)])
    loop_op = SymbolForOp(c0.result, c4.result, c1.result, loop_block)
    top_block.add_ops([c0, c4, c1, loop_op, func.ReturnOp()])
    func_op = func.FuncOp("multi_buffer_loop_local_slice", func_type, Region(top_block))
    return ModuleOp([func_op]), top_block, loop_op, loop_block, slice_op, slot_type


def _walk_ops(module: ModuleOp, op_type: type[Operation]) -> list[Operation]:
    """收集 module 内指定 operation 类型。

    功能说明:
    - 为公开 pass 结果断言提供统一 walk helper。

    使用示例:
    - rings = _walk_ops(module, DmaMakeRingOp)

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    return [op for op in module.walk() if isinstance(op, op_type)]


def _same_value(lhs: SSAValue, rhs: SSAValue) -> bool:
    """判断两个 SSA value 是否为同一公开对象。

    功能说明:
    - 避免测试依赖 SSA name hint，只比较公开 SSAValue identity。

    使用示例:
    - assert _same_value(copy.target, current.result)

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    return SSAValue.get(lhs) is SSAValue.get(rhs)


def _symbol_expr(value: SSAValue) -> str:
    """读取公开 `!symbol.int` value 的表达式文本。

    功能说明:
    - 用于断言 `num/offset` operands 的公开类型语义。

    使用示例:
    - expr = _symbol_expr(make_ring.num)

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    symbol_value = SSAValue.get(value)
    value_type = symbol_value.type
    assert isinstance(value_type, SymbolValueType)
    expr_attr = value_type.expr
    assert isinstance(expr_attr, SymbolExprAttr)
    return expr_attr.expr.data


def _symbol_const_value(value: SSAValue) -> int:
    """读取 `symbol.const` SSA value 的整数值。

    功能说明:
    - 用于静态 ring num/offset 的精确断言。

    使用示例:
    - num = _symbol_const_value(make_ring.num)

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    symbol_value = SSAValue.get(value)
    owner = symbol_value.owner
    assert isinstance(owner, SymbolConstOp)
    raw_value = owner.value.data
    parsed_value = int(raw_value)
    assert parsed_value == int(raw_value)
    return parsed_value


def _static_memory_bytes(memory_type: NnMemoryType) -> int:
    """计算测试静态 memory 的字节数。

    功能说明:
    - 当前测试只传入 i32 静态 matmul slot，固定按 4 字节计算。

    使用示例:
    - bytes_count = _static_memory_bytes(slot_type)

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    total = 1
    for dim in memory_type.shape.data:
        assert isinstance(dim, SymbolExprAttr)
        total *= int(dim.expr.data)
    return total * 4


def _backing_bytes(make_ring: DmaMakeRingOp) -> int:
    """读取 make_ring backing memory 的静态 byte pool 大小。

    功能说明:
    - 用于断言 backing bytes 为 `num * offset`。

    使用示例:
    - assert _backing_bytes(make_ring) == 72

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    memory_type = make_ring.memory.type
    assert isinstance(memory_type, NnMemoryType)
    dim = memory_type.shape.data[0]
    assert isinstance(dim, SymbolExprAttr)
    return int(dim.expr.data)


def _assert_static_ring(make_ring: DmaMakeRingOp, slot_type: NnMemoryType, num: int) -> None:
    """断言静态 ring operands 与 result type。

    功能说明:
    - 锁定 `num/offset` operands、backing bytes 与新 `DmaRingType(slot_type)`。

    使用示例:
    - _assert_static_ring(make_ring, slot_type, 2)

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    slot_numel = 1
    for dim in slot_type.shape.data:
        assert isinstance(dim, SymbolExprAttr)
        slot_numel *= int(dim.expr.data)
    slot_bytes = slot_numel * 4
    num_owner = SSAValue.get(make_ring.num).owner
    offset_owner = SSAValue.get(make_ring.offset).owner
    assert isinstance(num_owner, SymbolConstOp)
    assert isinstance(offset_owner, SymbolConstOp)
    assert int(num_owner.value.data) == num
    assert int(offset_owner.value.data) == slot_bytes
    backing_type = make_ring.memory.type
    assert isinstance(backing_type, NnMemoryType)
    backing_dim = backing_type.shape.data[0]
    assert isinstance(backing_dim, SymbolExprAttr)
    assert int(backing_dim.expr.data) == num * slot_bytes
    assert isinstance(make_ring.result.type, DmaRingType)
    assert make_ring.result.type.memory_type == slot_type


def _assert_no_new_ring_rewrite(module: ModuleOp, initial_ring_count: int = 0) -> None:
    """断言 pass 没有新增 ring rewrite。

    功能说明:
    - 对 no-op 场景统一校验 `dma.make_ring` 数量不增加。

    使用示例:
    - _assert_no_new_ring_rewrite(module)

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    assert len(_walk_ops(module, DmaMakeRingOp)) == initial_ring_count


def _insert_existing_ring_operand(top_block: Block, loop_op: SymbolForOp, loop_block: Block, matmul: KernelMatmulOp) -> None:
    """把 matmul lhs 替换为已有 ring current slot。

    功能说明:
    - 构造合法 `dma.make_ring/current_ring` 作为输入，使 pass 必须识别已有 ring 并保持整对 no-op。

    使用示例:
    - _insert_existing_ring_operand(top_block, loop_op, loop_block, matmul)

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    lhs_slot_type = SSAValue.get(matmul.operands[1]).type
    assert isinstance(lhs_slot_type, NnMemoryType)
    backing_type = NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr("72")]),
        ArrayAttr([SymbolExprAttr.from_expr("1")]),
        i8,
        NnMemorySpaceAttr.from_name(lhs_slot_type.space.space.data),
    )
    backing = DmaAllocOp([], backing_type)
    num = SymbolConstOp(3)
    offset = SymbolConstOp(24)
    make_ring = DmaMakeRingOp(backing.result, num.result, offset.result, DmaRingType(lhs_slot_type))
    current = DmaCurrentRingOp(make_ring.result)

    top_block.insert_ops_before([backing, num, offset, make_ring], loop_op)
    loop_block.insert_ops_before([current], matmul)
    matmul.operands[1] = current.result


def _insert_nested_symbol_for_use(top_block: Block, loop_block: Block, matmul: KernelMatmulOp) -> SymbolForOp:
    """在 nested `symbol.for` 中插入额外 staging use。

    功能说明:
    - 用于锁定跨 nested region 的 alloc use 不会被 `MultiBufferPass` 误判为 direct body 生命周期。

    使用示例:
    - nested_loop = _insert_nested_symbol_for_use(top_block, loop_block, matmul)

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
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


# TC-MULTI-BUFFER-001
# 功能说明: 验证公开构造参数与 from_options 边界。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_public_options
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_public_options() -> None:
    pass_obj = MultiBufferPass(memory_stage=4, fold=False, target="npu_demo")

    assert pass_obj.name == "multi-buffer"
    assert pass_obj.memory_stage == 4
    assert pass_obj.target == "npu_demo"
    assert pass_obj.fold is False
    assert MultiBufferPass(memory_stage=1).memory_stage == 1
    assert MultiBufferPass().memory_stage == 2
    assert MultiBufferPass.from_options({}).memory_stage == 2
    assert MultiBufferPass.from_options({"memory-stage": "1"}).memory_stage == 1
    assert MultiBufferPass.from_options({"memory-stage": "5", "target": "npu_demo"}).target == "npu_demo"
    with pytest.raises(KernelCodeError, match="memory_stage must be positive"):
        MultiBufferPass(memory_stage=0)
    with pytest.raises(KernelCodeError, match="target must be non-empty"):
        MultiBufferPass(target="")
    with pytest.raises(KernelCodeError, match="memory-stage must be positive"):
        MultiBufferPass.from_options({"memory-stage": "0"})
    with pytest.raises(KernelCodeError, match="memory-stage must be positive"):
        MultiBufferPass.from_options({"memory-stage": "-1"})
    with pytest.raises(KernelCodeError, match="target must be non-empty"):
        MultiBufferPass.from_options({"target": " "})
    with pytest.raises(KernelCodeError, match="unknown option: fold"):
        MultiBufferPass.from_options({"fold": "false"})


# TC-MULTI-BUFFER-002
# 功能说明: 验证 registry 可构造 multi-buffer，并由 registry 通用 fold 处理 fold option。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_registry_options
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_registry_options() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("multi-buffer", {"memory-stage": "4", "target": "npu_demo", "fold": "false"})

    assert isinstance(pass_obj, MultiBufferPass)
    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.memory_stage == 4
    assert pass_obj.target == "npu_demo"
    assert pass_obj.fold is False


# TC-MULTI-BUFFER-003
# 功能说明: 验证 loop 外 lhs/rhs 成对 staging 生命周期会被改写成 DMA ring。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_rewrites_matmul_lhs_rhs_pair
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_rewrites_matmul_lhs_rhs_pair() -> None:
    module, top_block, _loop_op, loop_block, matmul, lhs_slot_type, rhs_slot_type = _build_loop_matmul_module()

    MultiBufferPass().apply(Context(), module)

    make_rings = _walk_ops(module, DmaMakeRingOp)
    currents = _walk_ops(module, DmaCurrentRingOp)
    advances = _walk_ops(module, DmaAdvanceRingOp)
    assert len(make_rings) == 2
    assert len(currents) == 2
    assert len(advances) == 2
    _assert_static_ring(make_rings[0], lhs_slot_type, 2)
    _assert_static_ring(make_rings[1], rhs_slot_type, 2)
    assert not any(isinstance(op, DmaFreeOp) for op in top_block.ops)
    assert not any(isinstance(op, DmaAllocOp) for op in loop_block.ops)
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
    module.verify()


# TC-MULTI-BUFFER-004
# 功能说明: 验证缺少任一 loop 外 staging free 时整对保持 no-op。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_keeps_missing_free_noop
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_keeps_missing_free_noop() -> None:
    module, top_block, _loop_op, _loop_block, matmul, _lhs_slot_type, _rhs_slot_type = _build_loop_matmul_module(lhs_free=False)
    original_operands = list(matmul.operands)

    MultiBufferPass().apply(Context(), module)

    _assert_no_new_ring_rewrite(module)
    assert list(matmul.operands) == original_operands
    assert len([op for op in top_block.ops if isinstance(op, DmaAllocOp)]) == 2
    assert len([op for op in top_block.ops if isinstance(op, DmaFreeOp)]) == 1
    module.verify()


# TC-MULTI-BUFFER-005
# 功能说明: 验证 free 早于 symbol.for 时保持 no-op。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_keeps_free_before_loop_noop
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_keeps_free_before_loop_noop() -> None:
    module, top_block, _loop_op, _loop_block, matmul, _lhs_slot_type, _rhs_slot_type = _build_loop_matmul_module(free_before_loop=True)
    original_operands = list(matmul.operands)

    MultiBufferPass().apply(Context(), module)

    _assert_no_new_ring_rewrite(module)
    assert list(matmul.operands) == original_operands
    assert len([op for op in top_block.ops if isinstance(op, DmaAllocOp)]) == 2
    module.verify()


# TC-MULTI-BUFFER-006
# 功能说明: 验证旧 loop 内 alloc/free staging 形态保持 no-op。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_keeps_loop_internal_alloc_noop
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_keeps_loop_internal_alloc_noop() -> None:
    module, _top_block, _loop_op, loop_block, matmul, _lhs_slot_type, _rhs_slot_type = _build_loop_matmul_module(alloc_inside_loop=True)
    original_operands = list(matmul.operands)

    MultiBufferPass().apply(Context(), module)

    _assert_no_new_ring_rewrite(module)
    assert list(matmul.operands) == original_operands
    assert len([op for op in loop_block.ops if isinstance(op, DmaAllocOp)]) == 2
    assert len([op for op in loop_block.ops if isinstance(op, DmaFreeOp)]) == 2
    module.verify()


# TC-MULTI-BUFFER-007
# 功能说明: 验证 alloc result 存在额外 alias use 时保持 no-op。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_keeps_alias_escape_noop
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_keeps_alias_escape_noop() -> None:
    module, _top_block, _loop_op, loop_block, matmul, _lhs_slot_type, _rhs_slot_type = _build_loop_matmul_module(alias_escape=True)
    original_operands = list(matmul.operands)

    MultiBufferPass().apply(Context(), module)

    _assert_no_new_ring_rewrite(module)
    assert list(matmul.operands) == original_operands
    assert any(isinstance(op, DmaReshapeOp) for op in loop_block.ops)
    module.verify()


# TC-MULTI-BUFFER-008
# 功能说明: 验证 allocator 存在多 free 时整对保持 no-op。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_keeps_multiple_free_noop
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_keeps_multiple_free_noop() -> None:
    module, top_block, _loop_op, _loop_block, matmul, _lhs_slot_type, _rhs_slot_type = _build_loop_matmul_module(extra_lhs_free=True)
    original_operands = list(matmul.operands)

    MultiBufferPass().apply(Context(), module)

    _assert_no_new_ring_rewrite(module)
    assert list(matmul.operands) == original_operands
    assert len([op for op in top_block.ops if isinstance(op, DmaFreeOp)]) == 3
    module.verify()


# TC-MULTI-BUFFER-009
# 功能说明: 验证已有 ring 输入时保持 no-op，不能与当前 staging pair 混写。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_keeps_existing_ring_noop
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_keeps_existing_ring_noop() -> None:
    module, top_block, loop_op, loop_block, matmul, _lhs_slot_type, _rhs_slot_type = _build_loop_matmul_module()
    _insert_existing_ring_operand(top_block, loop_op, loop_block, matmul)
    operands_before_pass = list(matmul.operands)

    MultiBufferPass().apply(Context(), module)

    _assert_no_new_ring_rewrite(module, initial_ring_count=1)
    assert list(matmul.operands) == operands_before_pass
    assert len([op for op in top_block.ops if isinstance(op, DmaAllocOp)]) == 3
    module.verify()


# TC-MULTI-BUFFER-010
# 功能说明: 验证 lhs-only / rhs-only partial pair 保持 no-op。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_keeps_partial_pair_noop
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
@pytest.mark.parametrize(("operand_index", "source_arg_index"), [(1, 1), (2, 2)])
def test_multi_buffer_keeps_partial_pair_noop(operand_index: int, source_arg_index: int) -> None:
    module, top_block, _loop_op, _loop_block, matmul, _lhs_slot_type, _rhs_slot_type = _build_loop_matmul_module()
    matmul.operands[operand_index] = top_block.args[source_arg_index]
    operands_before_pass = list(matmul.operands)

    MultiBufferPass().apply(Context(), module)

    _assert_no_new_ring_rewrite(module)
    assert list(matmul.operands) == operands_before_pass
    module.verify()


# TC-MULTI-BUFFER-011
# 功能说明: 验证 staging alloc 存在 nested symbol.for region use 时整对保持 no-op。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_keeps_nested_region_use_noop
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_keeps_nested_region_use_noop() -> None:
    module, top_block, _loop_op, loop_block, matmul, _lhs_slot_type, _rhs_slot_type = _build_loop_matmul_module()
    nested_loop = _insert_nested_symbol_for_use(top_block, loop_block, matmul)
    operands_before_pass = list(matmul.operands)

    MultiBufferPass().apply(Context(), module)

    _assert_no_new_ring_rewrite(module)
    assert list(matmul.operands) == operands_before_pass
    assert nested_loop in list(loop_block.ops)
    module.verify()


# TC-MULTI-BUFFER-012
# 功能说明: 验证 target=npu_demo same-space 静态 case 按同 space shape bytes 合计计算 num。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_target_same_space_static_num
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_target_same_space_static_num() -> None:
    module, _top_block, _loop_op, _loop_block, _matmul, lhs_slot_type, rhs_slot_type = _build_loop_matmul_module(
        lhs_space="tlm1",
        rhs_space="tlm1",
    )
    lhs_bytes = _static_memory_bytes(lhs_slot_type)
    rhs_bytes = _static_memory_bytes(rhs_slot_type)
    expected_num = 524288 // (
        ((lhs_bytes + 1023) // 1024) * 1024
        + ((rhs_bytes + 1023) // 1024) * 1024
    )

    MultiBufferPass(memory_stage=2, target="npu_demo").apply(Context(), module)

    make_rings = _walk_ops(module, DmaMakeRingOp)
    assert len(make_rings) == 2
    _assert_static_ring(make_rings[0], lhs_slot_type, expected_num)
    _assert_static_ring(make_rings[1], rhs_slot_type, expected_num)
    assert expected_num != 2
    module.verify()


# TC-MULTI-BUFFER-013
# 功能说明: 验证 target=npu_demo different-space 静态 case 按各自 space capacity 计算 num。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_target_different_space_static_num
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_target_different_space_static_num() -> None:
    module, _top_block, _loop_op, _loop_block, _matmul, lhs_slot_type, rhs_slot_type = _build_loop_matmul_module(
        lhs_space="tlm1",
        rhs_space="tlm2",
        n_dim=2,
    )
    lhs_bytes = _static_memory_bytes(lhs_slot_type)
    rhs_bytes = _static_memory_bytes(rhs_slot_type)
    lhs_num = 524288 // (((lhs_bytes + 1023) // 1024) * 1024)
    rhs_num = 1048576 // (((rhs_bytes + 1023) // 1024) * 1024)

    MultiBufferPass(memory_stage=2, target="npu_demo").apply(Context(), module)

    make_rings = _walk_ops(module, DmaMakeRingOp)
    assert len(make_rings) == 2
    _assert_static_ring(make_rings[0], lhs_slot_type, lhs_num)
    _assert_static_ring(make_rings[1], rhs_slot_type, rhs_num)
    assert lhs_num != rhs_num
    assert lhs_num != 2
    assert rhs_num != 2
    module.verify()


# TC-MULTI-BUFFER-014
# 功能说明: 验证 target=npu_demo dynamic same-space case 复用 kernel 参数计算动态 num。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_target_dynamic_same_space_num
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_target_dynamic_same_space_num() -> None:
    module, top_block, _loop_op, _loop_block, _matmul = _build_dynamic_same_space_module()

    MultiBufferPass(memory_stage=2, target="npu_demo").apply(Context(), module)

    make_rings = _walk_ops(module, DmaMakeRingOp)
    assert len(make_rings) == 2
    assert _symbol_expr(make_rings[0].offset) == "4*S1*S2"
    assert _symbol_expr(make_rings[1].offset) == "4*S2*S3"
    assert _same_value(make_rings[0].num, make_rings[1].num)
    num_expr = _symbol_expr(make_rings[0].num)
    assert "524288 floordiv" in num_expr
    assert "4*S1*S2" in num_expr
    assert "4*S2*S3" in num_expr
    assert "1024" in num_expr
    assert not any(op.name == "symbol.get_dim" for op in module.walk())
    backing_allocs = [op for op in top_block.ops if isinstance(op, DmaAllocOp)]
    assert len(backing_allocs) == 2
    assert all(len(op.dynamic_shape) == 1 for op in backing_allocs)
    module.verify()


# TC-MULTI-BUFFER-015
# 功能说明: 验证 loop-local direct alloc use 可改写为 `num=1` ring。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_rewrites_loop_local_direct_slice_use
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_rewrites_loop_local_direct_slice_use() -> None:
    module, _top_block, _loop_op, loop_block, slice_op, slot_type = _build_loop_local_direct_slice_module()

    MultiBufferPass(memory_stage=2, target="npu_demo").apply(Context(), module)

    make_rings = _walk_ops(module, DmaMakeRingOp)
    currents = _walk_ops(module, DmaCurrentRingOp)
    advances = _walk_ops(module, DmaAdvanceRingOp)
    assert len(make_rings) == 1
    assert len(currents) == 1
    assert len(advances) == 1
    _assert_static_ring(make_rings[0], slot_type, 1)
    assert _same_value(slice_op.target, currents[0].result)
    body_ops = list(loop_block.ops)
    assert body_ops.index(make_rings[0]) < body_ops.index(currents[0]) < body_ops.index(slice_op)
    assert body_ops.index(slice_op) < body_ops.index(advances[0])
    assert not any(isinstance(op, DmaFreeOp) for op in loop_block.ops)
    module.verify()
