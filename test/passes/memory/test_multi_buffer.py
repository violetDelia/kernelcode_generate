"""multi-buffer pass tests.

功能说明:
- 覆盖 `MultiBufferAnalysisPass`、`MultiBufferApplyPass` 与兼容 `MultiBufferPass` 的公开构造、registry option 与 matmul staging ring 化行为。
- 验证 analysis-only 三属性、apply-only 属性消费、facade 兼容、target auto 和 aligned-slot backing。

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
from xdsl.dialects import arith, func, scf
from xdsl.dialects.builtin import ArrayAttr, FunctionType, ModuleOp, StringAttr, f32, i8, i32
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
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolExprAttr, SymbolForOp, SymbolIterType, SymbolValueType, SymbolYieldOp
from kernel_gen.passes.memory.multi_buffer import MultiBufferAnalysisPass, MultiBufferApplyPass, MultiBufferPass
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


def _string_attr_array(values: tuple[str, ...]) -> ArrayAttr[Attribute]:
    """构造字符串数组属性。

    功能说明:
    - 为 `multi_buffer.update_points/use_points` 测试输入和断言复用同一结构。

    使用示例:
    - attr = _string_attr_array(("loop1-1",))

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    attrs: list[Attribute] = []
    for value in values:
        attr = StringAttr(value)
        attrs.append(attr)
    result = ArrayAttr(attrs)
    return result


def _string_array_values(attr: Attribute) -> tuple[str, ...]:
    """读取测试用字符串数组属性。

    功能说明:
    - 验证 attr 是 `ArrayAttr[StringAttr]` 并返回内部字符串。

    使用示例:
    - values = _string_array_values(alloc.attributes["multi_buffer.update_points"])

    关联文件:
    - spec: spec/pass/memory/multi_buffer.md
    - test: test/passes/memory/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/memory/multi_buffer.py
    """

    assert isinstance(attr, ArrayAttr)
    values: list[str] = []
    for item in attr.data:
        assert isinstance(item, StringAttr)
        values.append(item.data)
    return tuple(values)


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


def _build_loop_local_direct_slice_module(
    *,
    with_terminator: bool = False,
) -> tuple[ModuleOp, Block, SymbolForOp, Block, DmaSliceOp, NnMemoryType]:
    """构造 loop-local direct-use staging alloc 测试 module。

    功能说明:
    - 在 `symbol.for` body 内创建 `dma.alloc -> dma.slice -> dma.free` 生命周期。
    - 该形态没有中间 view alias，用于覆盖 direct alloc use 的 loop-local `num=1` ring 化。
    - `with_terminator=True` 时构造 loop-carried `symbol.for`，用于验证 advance 插在 terminator 前。

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
    loop_arg_types: list[Attribute] = [SymbolIterType.from_bounds("0", "4", "1")]
    if with_terminator:
        loop_arg_types.append(SymbolValueType.from_expr("ACC"))
    loop_block = Block(arg_types=loop_arg_types)
    alloc = DmaAllocOp([], slot_type)
    slice_op = DmaSliceOp(alloc.result, top_block.args[0], [c0.result], [c4.result], [c1.result])
    loop_block.add_ops([alloc, slice_op, DmaFreeOp(alloc.result)])
    if with_terminator:
        loop_block.add_op(SymbolYieldOp(loop_block.args[1]))
        loop_op = SymbolForOp(c0.result, c4.result, c1.result, loop_block, init=c0.result, result_type=SymbolValueType.from_expr("ACC"))
    else:
        loop_op = SymbolForOp(c0.result, c4.result, c1.result, loop_block)
    top_block.add_ops([c0, c4, c1, loop_op, func.ReturnOp()])
    func_op = func.FuncOp("multi_buffer_loop_local_slice", func_type, Region(top_block))
    return ModuleOp([func_op]), top_block, loop_op, loop_block, slice_op, slot_type


def _build_if_path_direct_slice_module() -> tuple[ModuleOp, Block, SymbolForOp, scf.IfOp, SymbolForOp, DmaSliceOp, NnMemoryType]:
    """构造 loop 外 alloc、if branch 内 direct use 的生命周期候选。

    功能说明:
    - alloc/free 位于外层 loop 外，direct `dma.slice` 位于 loop body 内的 `scf.if` branch。
    - loop body 另含一个更深的空 `symbol.for`，用于覆盖非最大 depth candidate 写 fixed=2。

    使用示例:
    - module, top_block, loop_op, if_op, inner_loop, slice_op, slot_type = _build_if_path_direct_slice_module()

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
    condition = arith.ConstantOp.from_int_and_width(1, 1)
    alloc = DmaAllocOp([], slot_type)
    then_block = Block()
    slice_op = DmaSliceOp(alloc.result, top_block.args[0], [c0.result], [c4.result], [c1.result])
    then_block.add_ops([slice_op, scf.YieldOp()])
    if_op = scf.IfOp(condition.result, [], Region(then_block), None)
    inner_block = Block(arg_types=[SymbolIterType.from_bounds("0", "4", "1")])
    inner_loop = SymbolForOp(c0.result, c4.result, c1.result, inner_block)
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "4", "1")])
    loop_block.add_ops([if_op, inner_loop])
    loop_op = SymbolForOp(c0.result, c4.result, c1.result, loop_block)
    top_block.add_ops([c0, c4, c1, condition, alloc, loop_op, DmaFreeOp(alloc.result), func.ReturnOp()])
    func_op = func.FuncOp("multi_buffer_if_path_slice", func_type, Region(top_block))
    return ModuleOp([func_op]), top_block, loop_op, if_op, inner_loop, slice_op, slot_type


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


def _assert_static_ring(make_ring: DmaMakeRingOp, slot_type: NnMemoryType, num: int, *, alignment: int = 1024) -> None:
    """断言静态 ring operands 与 result type。

    功能说明:
    - 锁定 `num/offset` operands、aligned backing bytes 与新 `DmaRingType(slot_type)`。
    - `alignment=0` 时保持 raw slot bytes，用于覆盖关闭对齐的公开选项。

    使用示例:
    - _assert_static_ring(make_ring, slot_type, 2, alignment=1024)

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
    aligned_slot_bytes = slot_bytes if alignment == 0 else ((slot_bytes + alignment - 1) // alignment) * alignment
    num_owner = SSAValue.get(make_ring.num).owner
    offset_owner = SSAValue.get(make_ring.offset).owner
    assert isinstance(num_owner, SymbolConstOp)
    assert isinstance(offset_owner, SymbolConstOp)
    assert int(num_owner.value.data) == num
    assert int(offset_owner.value.data) == aligned_slot_bytes
    backing_type = make_ring.memory.type
    assert isinstance(backing_type, NnMemoryType)
    backing_dim = backing_type.shape.data[0]
    assert isinstance(backing_dim, SymbolExprAttr)
    assert int(backing_dim.expr.data) == num * aligned_slot_bytes
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


def _insert_existing_ring_operand(
    top_block: Block,
    loop_op: SymbolForOp,
    loop_block: Block,
    matmul: KernelMatmulOp,
    *,
    replace_matmul_lhs: bool = True,
) -> None:
    """把 matmul lhs 替换为已有 ring current slot。

    功能说明:
    - 构造合法 `dma.make_ring/current_ring` 作为输入，使 pass 必须识别已有 ring 并保持整对 no-op。
    - 默认把 matmul lhs 替换成 current；`replace_matmul_lhs=False` 只注入无关 existing current。

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
    if replace_matmul_lhs:
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
    analysis = MultiBufferAnalysisPass(memory_stage=4, fold=False, target="npu_demo")
    apply = MultiBufferApplyPass(fold=False, target="npu_demo", alignment=0)
    pass_obj = MultiBufferPass(memory_stage=4, fold=False, target="npu_demo", alignment=2048)

    assert analysis.name == "multi-buffer-analysis"
    assert analysis.memory_stage == 4
    assert analysis.target == "npu_demo"
    assert analysis.fold is False
    assert apply.name == "multi-buffer-apply"
    assert apply.target == "npu_demo"
    assert apply.alignment == 0
    assert apply.fold is False
    assert pass_obj.name == "multi-buffer"
    assert pass_obj.memory_stage == 4
    assert pass_obj.target == "npu_demo"
    assert pass_obj.alignment == 2048
    assert pass_obj.fold is False
    assert MultiBufferAnalysisPass(memory_stage=1).memory_stage == 1
    assert MultiBufferAnalysisPass.from_options({}).memory_stage == 2
    assert MultiBufferAnalysisPass.from_options({"memory-stage": "5", "target": "npu_demo"}).target == "npu_demo"
    assert MultiBufferApplyPass().alignment == 1024
    assert MultiBufferApplyPass.from_options({"alignment": "0"}).alignment == 0
    assert MultiBufferApplyPass.from_options({"target": "npu_demo"}).target == "npu_demo"
    assert MultiBufferPass(memory_stage=1).memory_stage == 1
    assert MultiBufferPass().memory_stage == 2
    assert MultiBufferPass.from_options({}).memory_stage == 2
    assert MultiBufferPass.from_options({"memory-stage": "1"}).memory_stage == 1
    assert MultiBufferPass.from_options({"memory-stage": "5", "target": "npu_demo"}).target == "npu_demo"
    assert MultiBufferPass.from_options({"alignment": "0"}).alignment == 0
    with pytest.raises(KernelCodeError, match="memory_stage must be positive"):
        MultiBufferAnalysisPass(memory_stage=0)
    with pytest.raises(KernelCodeError, match="target must be non-empty"):
        MultiBufferAnalysisPass(target="")
    with pytest.raises(KernelCodeError, match="unknown option: fold"):
        MultiBufferAnalysisPass.from_options({"fold": "false"})
    with pytest.raises(KernelCodeError, match="target must be non-empty"):
        MultiBufferApplyPass(target="")
    with pytest.raises(KernelCodeError, match="alignment must be non-negative integer"):
        MultiBufferApplyPass(alignment=-1)
    with pytest.raises(KernelCodeError, match="alignment must be non-negative integer"):
        MultiBufferApplyPass.from_options({"alignment": "bad"})
    with pytest.raises(KernelCodeError, match="unknown option: memory-stage"):
        MultiBufferApplyPass.from_options({"memory-stage": "2"})
    with pytest.raises(KernelCodeError, match="memory_stage must be positive"):
        MultiBufferPass(memory_stage=0)
    with pytest.raises(KernelCodeError, match="target must be non-empty"):
        MultiBufferPass(target="")
    with pytest.raises(KernelCodeError, match="alignment must be non-negative integer"):
        MultiBufferPass(alignment=-1)
    with pytest.raises(KernelCodeError, match="memory-stage must be positive"):
        MultiBufferPass.from_options({"memory-stage": "0"})
    with pytest.raises(KernelCodeError, match="memory-stage must be positive"):
        MultiBufferPass.from_options({"memory-stage": "-1"})
    with pytest.raises(KernelCodeError, match="target must be non-empty"):
        MultiBufferPass.from_options({"target": " "})
    with pytest.raises(KernelCodeError, match="alignment must be non-negative integer"):
        MultiBufferPass.from_options({"alignment": "-1"})
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

    analysis = build_registered_pass(
        "multi-buffer-analysis",
        {"memory-stage": "4", "target": "npu_demo", "fold": "false"},
    )
    apply = build_registered_pass("multi-buffer-apply", {"target": "npu_demo", "alignment": "0", "fold": "false"})
    pass_obj = build_registered_pass(
        "multi-buffer",
        {"memory-stage": "4", "target": "npu_demo", "alignment": "2048", "fold": "false"},
    )

    assert isinstance(analysis, MultiBufferAnalysisPass)
    assert isinstance(analysis, ModulePass)
    assert analysis.memory_stage == 4
    assert analysis.target == "npu_demo"
    assert analysis.fold is False
    assert isinstance(apply, MultiBufferApplyPass)
    assert isinstance(apply, ModulePass)
    assert apply.target == "npu_demo"
    assert apply.alignment == 0
    assert apply.fold is False
    assert isinstance(pass_obj, MultiBufferPass)
    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.memory_stage == 4
    assert pass_obj.target == "npu_demo"
    assert pass_obj.alignment == 2048
    assert pass_obj.fold is False


# TC-MULTI-BUFFER-002A
# 功能说明: 验证 analysis pass 只写三项临时属性，不生成 ring。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_analysis_writes_attrs_without_rewrite
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_analysis_writes_attrs_without_rewrite() -> None:
    module, top_block, loop_op, _loop_block, _matmul, _lhs_slot_type, _rhs_slot_type = _build_loop_matmul_module()

    MultiBufferAnalysisPass(memory_stage=3).apply(Context(), module)

    allocs = [op for op in top_block.ops if isinstance(op, DmaAllocOp)]
    assert len(allocs) == 2
    assert loop_op.attributes["analysis.loop_id"] == StringAttr("loop1-1")
    for alloc in allocs:
        assert alloc.attributes["multi_buffer.update_points"] == _string_attr_array(("loop1-1",))
        assert alloc.attributes["multi_buffer.use_points"] == _string_attr_array(("loop1-1",))
        assert alloc.attributes["multi_buffer.num"] == StringAttr("3")
    assert not _walk_ops(module, DmaMakeRingOp)
    assert not _walk_ops(module, DmaCurrentRingOp)
    assert len(_walk_ops(module, DmaFreeOp)) == 2
    module.verify()


# TC-MULTI-BUFFER-002B
# 功能说明: 验证 apply pass 只消费三项属性，且 alignment=0 使用 raw slot bytes。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_apply_consumes_attrs_with_alignment_zero
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_apply_consumes_attrs_with_alignment_zero() -> None:
    module, top_block, loop_op, _loop_block, _matmul, lhs_slot_type, rhs_slot_type = _build_loop_matmul_module()
    loop_op.attributes["analysis.loop_id"] = StringAttr("loop1-1")
    allocs = [op for op in top_block.ops if isinstance(op, DmaAllocOp)]
    assert len(allocs) == 2
    for alloc in allocs:
        alloc.attributes["multi_buffer.update_points"] = _string_attr_array(("loop1-1",))
        alloc.attributes["multi_buffer.use_points"] = _string_attr_array(("loop1-1",))
        alloc.attributes["multi_buffer.num"] = StringAttr("2")

    MultiBufferApplyPass(alignment=0).apply(Context(), module)

    make_rings = _walk_ops(module, DmaMakeRingOp)
    assert len(make_rings) == 2
    _assert_static_ring(make_rings[0], lhs_slot_type, 2, alignment=0)
    _assert_static_ring(make_rings[1], rhs_slot_type, 2, alignment=0)
    assert "multi_buffer." not in str(module)
    assert not _walk_ops(module, DmaFreeOp)
    module.verify()


# TC-MULTI-BUFFER-002C
# 功能说明: 验证 apply-only 在无三项 multi_buffer 属性时不写 analysis control-flow id。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_apply_without_attrs_does_not_write_analysis_ids
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_apply_without_attrs_does_not_write_analysis_ids() -> None:
    module, _top_block, loop_op, if_op, inner_loop, _slice_op, _slot_type = _build_if_path_direct_slice_module()

    MultiBufferApplyPass().apply(Context(), module)

    assert "analysis.loop_id" not in loop_op.attributes
    assert "analysis.if_id" not in if_op.attributes
    assert "analysis.loop_id" not in inner_loop.attributes
    assert not _walk_ops(module, DmaMakeRingOp)
    assert not _walk_ops(module, DmaCurrentRingOp)
    assert "multi_buffer." not in str(module)
    module.verify()


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
    assert body_ops[0] is currents[0]
    assert body_ops[1] is currents[1]
    assert body_ops.index(currents[0]) < body_ops.index(copies[0]) < body_ops.index(matmul)
    assert body_ops.index(currents[1]) < body_ops.index(copies[1]) < body_ops.index(matmul)
    assert body_ops[-2] is advances[0]
    assert body_ops[-1] is advances[1]
    module.verify()


# TC-MULTI-BUFFER-003A
# 功能说明: 验证 current/advance 插入到 use block 边界，而不是首个/最后一个实际 use 附近。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_places_ring_ops_at_use_block_boundaries
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_places_ring_ops_at_use_block_boundaries() -> None:
    module, _top_block, _loop_op, loop_block, matmul, _lhs_slot_type, _rhs_slot_type = _build_loop_matmul_module()
    prefix_const = SymbolConstOp(99)
    suffix_const = SymbolConstOp(100)
    loop_block.insert_ops_before([prefix_const], list(loop_block.ops)[0])
    loop_block.insert_ops_after([suffix_const], matmul)

    MultiBufferPass().apply(Context(), module)

    currents = _walk_ops(module, DmaCurrentRingOp)
    advances = _walk_ops(module, DmaAdvanceRingOp)
    body_ops = list(loop_block.ops)
    assert len(currents) == 2
    assert len(advances) == 2
    assert body_ops[0] is currents[0]
    assert body_ops[1] is currents[1]
    assert body_ops.index(prefix_const) == 2
    assert body_ops.index(matmul) < body_ops.index(suffix_const)
    assert body_ops[-2] is advances[0]
    assert body_ops[-1] is advances[1]
    assert body_ops.index(suffix_const) < body_ops.index(advances[0])
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


# TC-MULTI-BUFFER-009A
# 功能说明: 验证 apply-only matmul pair 带三项属性但 use block 已有 current 时保持 no-op。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_apply_keeps_existing_current_pair_noop
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_apply_keeps_existing_current_pair_noop() -> None:
    module, top_block, loop_op, loop_block, matmul, _lhs_slot_type, _rhs_slot_type = _build_loop_matmul_module()
    loop_op.attributes["analysis.loop_id"] = StringAttr("loop1-1")
    allocs = [op for op in top_block.ops if isinstance(op, DmaAllocOp)]
    assert len(allocs) == 2
    for alloc in allocs:
        alloc.attributes["multi_buffer.update_points"] = _string_attr_array(("loop1-1",))
        alloc.attributes["multi_buffer.use_points"] = _string_attr_array(("loop1-1",))
        alloc.attributes["multi_buffer.num"] = StringAttr("2")
    _insert_existing_ring_operand(top_block, loop_op, loop_block, matmul, replace_matmul_lhs=False)
    initial_ring_count = len(_walk_ops(module, DmaMakeRingOp))
    initial_current_count = len(_walk_ops(module, DmaCurrentRingOp))
    operands_before_pass = list(matmul.operands)

    MultiBufferApplyPass().apply(Context(), module)

    _assert_no_new_ring_rewrite(module, initial_ring_count=initial_ring_count)
    assert len(_walk_ops(module, DmaCurrentRingOp)) == initial_current_count
    assert list(matmul.operands) == operands_before_pass
    assert all("multi_buffer.num" in alloc.attributes for alloc in allocs)
    assert len(_walk_ops(module, DmaFreeOp)) == 2
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
    lhs_offset_expr = _symbol_expr(make_rings[0].offset)
    rhs_offset_expr = _symbol_expr(make_rings[1].offset)
    assert "4*S1*S2" in lhs_offset_expr
    assert "1023" in lhs_offset_expr
    assert "1024" in lhs_offset_expr
    assert "floordiv" in lhs_offset_expr
    assert "4*S2*S3" in rhs_offset_expr
    assert "1023" in rhs_offset_expr
    assert "1024" in rhs_offset_expr
    assert "floordiv" in rhs_offset_expr
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


# TC-MULTI-BUFFER-014A
# 功能说明: 验证 mixed fixed/auto apply 先扣同 scope fixed reserved，再为 auto group 计算共享 num。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_apply_fixed_reserved_before_auto_static_num
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_apply_fixed_reserved_before_auto_static_num() -> None:
    fixed_a_type = _make_memory_type(shape=(4096,), stride=(1,), space="tsm", element_type=f32)
    fixed_b_type = _make_memory_type(shape=(256,), stride=(1,), space="tsm", element_type=f32)
    fixed_c_type = _make_memory_type(shape=(4096,), stride=(1,), space="tsm", element_type=f32)
    auto_lhs_type = _make_memory_type(shape=(3584,), stride=(1,), space="tsm", element_type=f32)
    auto_rhs_type = _make_memory_type(shape=(2816,), stride=(1,), space="tsm", element_type=f32)
    source_types = [
        _make_memory_type(shape=(4096,), stride=(1,), space="global", element_type=f32),
        _make_memory_type(shape=(256,), stride=(1,), space="global", element_type=f32),
        _make_memory_type(shape=(4096,), stride=(1,), space="global", element_type=f32),
        _make_memory_type(shape=(3584,), stride=(1,), space="global", element_type=f32),
        _make_memory_type(shape=(2816,), stride=(1,), space="global", element_type=f32),
    ]
    func_type = FunctionType.from_lists(source_types, [])
    top_block = Block(arg_types=source_types)
    c0 = SymbolConstOp(0)
    cend = SymbolConstOp(5)
    c1 = SymbolConstOp(1)
    size_fixed_large = SymbolConstOp(4096)
    size_fixed_small = SymbolConstOp(256)
    size_auto_lhs = SymbolConstOp(3584)
    size_auto_rhs = SymbolConstOp(2816)
    fixed_a = DmaAllocOp([], fixed_a_type)
    fixed_b = DmaAllocOp([], fixed_b_type)
    fixed_c = DmaAllocOp([], fixed_c_type)
    auto_lhs = DmaAllocOp([], auto_lhs_type)
    auto_rhs = DmaAllocOp([], auto_rhs_type)
    for alloc, raw_num in (
        (fixed_a, "2"),
        (fixed_b, "2"),
        (fixed_c, "2"),
        (auto_lhs, "auto"),
        (auto_rhs, "auto"),
    ):
        alloc.attributes["multi_buffer.update_points"] = _string_attr_array(("loop1-1",))
        alloc.attributes["multi_buffer.use_points"] = _string_attr_array(("loop1-1",))
        alloc.attributes["multi_buffer.num"] = StringAttr(raw_num)

    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "5", "1")])
    loop_block.add_ops(
        [
            DmaSliceOp(fixed_a.result, top_block.args[0], [c0.result], [size_fixed_large.result], [c1.result]),
            DmaSliceOp(fixed_b.result, top_block.args[1], [c0.result], [size_fixed_small.result], [c1.result]),
            DmaSliceOp(fixed_c.result, top_block.args[2], [c0.result], [size_fixed_large.result], [c1.result]),
            DmaSliceOp(auto_lhs.result, top_block.args[3], [c0.result], [size_auto_lhs.result], [c1.result]),
            DmaSliceOp(auto_rhs.result, top_block.args[4], [c0.result], [size_auto_rhs.result], [c1.result]),
        ]
    )
    loop_op = SymbolForOp(c0.result, cend.result, c1.result, loop_block)
    loop_op.attributes["analysis.loop_id"] = StringAttr("loop1-1")
    top_block.add_ops(
        [
            c0,
            cend,
            c1,
            size_fixed_large,
            size_fixed_small,
            size_auto_lhs,
            size_auto_rhs,
            fixed_a,
            fixed_b,
            fixed_c,
            auto_lhs,
            auto_rhs,
            loop_op,
            DmaFreeOp(fixed_a.result),
            DmaFreeOp(fixed_b.result),
            DmaFreeOp(fixed_c.result),
            DmaFreeOp(auto_lhs.result),
            DmaFreeOp(auto_rhs.result),
            func.ReturnOp(),
        ]
    )
    module = ModuleOp([func.FuncOp("multi_buffer_fixed_reserved_before_auto", func_type, Region(top_block))])

    MultiBufferApplyPass(target="npu_demo").apply(Context(), module)

    make_rings = _walk_ops(module, DmaMakeRingOp)
    assert len(make_rings) == 5
    expected_rings = (
        (fixed_a_type, 2),
        (fixed_b_type, 2),
        (fixed_c_type, 2),
        (auto_lhs_type, 79),
        (auto_rhs_type, 79),
    )
    for make_ring, (slot_type, num) in zip(make_rings, expected_rings, strict=True):
        _assert_static_ring(make_ring, slot_type, num)
    assert len(_walk_ops(module, DmaCurrentRingOp)) == 5
    assert len(_walk_ops(module, DmaAdvanceRingOp)) == 5
    assert not _walk_ops(module, DmaFreeOp)
    module_text = str(module)
    assert "multi_buffer." not in module_text
    assert "symbol.const 81" not in module_text
    module.verify()


# TC-MULTI-BUFFER-015
# 功能说明: 验证 loop-local direct alloc use 可改写为 `num=1` ring。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_rewrites_loop_local_direct_slice_use
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_rewrites_loop_local_direct_slice_use() -> None:
    module, _top_block, _loop_op, loop_block, slice_op, slot_type = _build_loop_local_direct_slice_module()
    prefix_const = SymbolConstOp(11)
    suffix_const = SymbolConstOp(12)
    loop_block.insert_ops_before([prefix_const], list(loop_block.ops)[0])
    loop_block.insert_ops_after([suffix_const], slice_op)

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
    assert body_ops.index(make_rings[0]) < body_ops.index(currents[0]) < body_ops.index(prefix_const)
    assert body_ops.index(prefix_const) < body_ops.index(slice_op)
    assert body_ops.index(slice_op) < body_ops.index(suffix_const) < body_ops.index(advances[0])
    assert body_ops[-1] is advances[0]
    assert not any(isinstance(op, DmaFreeOp) for op in loop_block.ops)
    module.verify()


# TC-MULTI-BUFFER-015B
# 功能说明: 验证 loop-local direct-use advance 插在 use block terminator 前。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_rewrites_loop_local_direct_slice_before_terminator
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_rewrites_loop_local_direct_slice_before_terminator() -> None:
    module, _top_block, _loop_op, loop_block, slice_op, _slot_type = _build_loop_local_direct_slice_module(with_terminator=True)
    suffix_const = SymbolConstOp(13)
    loop_block.insert_ops_after([suffix_const], slice_op)

    MultiBufferPass(memory_stage=2, target="npu_demo").apply(Context(), module)

    advances = _walk_ops(module, DmaAdvanceRingOp)
    terminators = _walk_ops(module, SymbolYieldOp)
    assert len(advances) == 1
    assert len(terminators) == 1
    body_ops = list(loop_block.ops)
    assert body_ops.index(slice_op) < body_ops.index(suffix_const) < body_ops.index(advances[0])
    assert body_ops[-2] is advances[0]
    assert body_ops[-1] is terminators[0]
    module.verify()


# TC-MULTI-BUFFER-015C
# 功能说明: 验证 analysis 为 if path direct-use 候选写 control-flow id、列表属性与 fixed=2。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_analysis_marks_if_path_lifecycle_points
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_analysis_marks_if_path_lifecycle_points() -> None:
    module, top_block, loop_op, if_op, inner_loop, _slice_op, _slot_type = _build_if_path_direct_slice_module()

    MultiBufferAnalysisPass(memory_stage=4, target="npu_demo").apply(Context(), module)

    alloc = next(op for op in top_block.ops if isinstance(op, DmaAllocOp))
    assert loop_op.attributes["analysis.loop_id"] == StringAttr("loop1-1")
    assert if_op.attributes["analysis.if_id"] == StringAttr("if1-1")
    assert inner_loop.attributes["analysis.loop_id"] == StringAttr("loop2-2")
    assert _string_array_values(alloc.attributes["multi_buffer.update_points"]) == ("loop1-1",)
    assert _string_array_values(alloc.attributes["multi_buffer.use_points"]) == ("if1-1",)
    assert alloc.attributes["multi_buffer.num"] == StringAttr("2")
    assert not _walk_ops(module, DmaMakeRingOp)
    module.verify()


# TC-MULTI-BUFFER-015D
# 功能说明: 验证 apply 能把 if branch 内 direct-use 候选改写为 outer loop current/advance ring。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_rewrites_if_path_direct_slice_use
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_rewrites_if_path_direct_slice_use() -> None:
    module, top_block, loop_op, if_op, inner_loop, slice_op, slot_type = _build_if_path_direct_slice_module()

    MultiBufferPass(memory_stage=4, target="npu_demo").apply(Context(), module)

    make_rings = _walk_ops(module, DmaMakeRingOp)
    currents = _walk_ops(module, DmaCurrentRingOp)
    advances = _walk_ops(module, DmaAdvanceRingOp)
    assert len(make_rings) == 1
    assert len(currents) == 1
    assert len(advances) == 1
    _assert_static_ring(make_rings[0], slot_type, 2)
    assert _same_value(slice_op.target, currents[0].result)
    loop_body_ops = list(loop_op.body.blocks[0].ops)
    assert loop_body_ops.index(currents[0]) < loop_body_ops.index(if_op)
    assert loop_body_ops.index(if_op) < loop_body_ops.index(inner_loop) < loop_body_ops.index(advances[0])
    assert not any(isinstance(op, DmaFreeOp) for op in top_block.ops)
    assert "multi_buffer." not in str(module)
    module.verify()


# TC-MULTI-BUFFER-015A
# 功能说明: 验证 apply-only direct-use staging 带三项属性但 use block 已有 current 时保持 no-op。
# 使用示例: pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_apply_keeps_existing_current_direct_use_noop
# 对应功能实现文件路径: kernel_gen/passes/memory/multi_buffer.py
# 对应 spec 文件路径: spec/pass/memory/multi_buffer.md
# 对应测试文件路径: test/passes/memory/test_multi_buffer.py
def test_multi_buffer_apply_keeps_existing_current_direct_use_noop() -> None:
    module, top_block, loop_op, loop_block, slice_op, slot_type = _build_loop_local_direct_slice_module()
    loop_op.attributes["analysis.loop_id"] = StringAttr("loop1-1")
    alloc = next(op for op in loop_block.ops if isinstance(op, DmaAllocOp))
    alloc.attributes["multi_buffer.update_points"] = _string_attr_array(("main",))
    alloc.attributes["multi_buffer.use_points"] = _string_attr_array(("loop1-1",))
    alloc.attributes["multi_buffer.num"] = StringAttr("1")
    backing = DmaAllocOp([], _make_byte_pool_type(bytes_count=16, space="tlm1"))
    num = SymbolConstOp(1)
    offset = SymbolConstOp(16)
    make_ring = DmaMakeRingOp(backing.result, num.result, offset.result, DmaRingType(slot_type))
    current = DmaCurrentRingOp(make_ring.result)
    top_block.insert_ops_before([backing, num, offset, make_ring], loop_op)
    loop_block.insert_ops_before([current], slice_op)
    initial_ring_count = len(_walk_ops(module, DmaMakeRingOp))
    initial_current_count = len(_walk_ops(module, DmaCurrentRingOp))

    MultiBufferApplyPass().apply(Context(), module)

    _assert_no_new_ring_rewrite(module, initial_ring_count=initial_ring_count)
    assert len(_walk_ops(module, DmaCurrentRingOp)) == initial_current_count
    assert _same_value(slice_op.target, alloc.result)
    assert "multi_buffer.num" in alloc.attributes
    assert len(_walk_ops(module, DmaFreeOp)) == 1
    module.verify()
