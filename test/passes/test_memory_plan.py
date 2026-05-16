"""memory-plan pass tests.

功能说明:
- 覆盖 `MemoryPlanPass` 的公开构造、registry/ircheck 路径、free 插入、alias closure 与失败边界。
- 测试只使用公开 API，不直连 `kernel_gen.passes.memory_plan` 内部 helper。

使用示例:
- pytest -q test/passes/test_memory_plan.py

关联文件:
- 功能实现: kernel_gen/passes/memory_plan.py
- Spec 文档: spec/pass/memory_plan.md
- 测试文件: test/passes/test_memory_plan.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects import arith, func, scf
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IndexType, IntegerAttr, ModuleOp, f32, i1, i8, i32
from xdsl.ir import Block, Operation, Region, SSAValue

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.dma import (
    DmaAllocOp,
    DmaBroadcastOp,
    DmaDesliceOp,
    DmaFreeOp,
    DmaReshapeOp,
    DmaSubviewOp,
    DmaViewOp,
)
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolExprAttr, SymbolForOp, SymbolIterType, SymbolValueType
from kernel_gen.passes.memory_plan import MemoryPlanPass
from kernel_gen.tools.ircheck import run_ircheck_text


def _memory_space(name: str = "global") -> NnMemorySpaceAttr:
    """构造测试用 memory space。

    功能说明:
    - 通过公开 `NnMemorySpaceAttr.from_name(...)` 构造 memory space。

    使用示例:
    - space = _memory_space("shared")
    """

    return NnMemorySpaceAttr.from_name(name)


def _symbol_attr(expr: int | str) -> SymbolExprAttr:
    """构造测试用 symbol expr attribute。

    功能说明:
    - 用公开 `SymbolExprAttr.from_expr(...)` 生成 shape/stride attribute。

    使用示例:
    - attr = _symbol_attr("N")
    """

    return SymbolExprAttr.from_expr(str(expr))


def _memory_type(
    shape: tuple[int | str, ...] = (2, 4),
    stride: tuple[int | str, ...] = (4, 1),
    element_type=f32,
    space: str = "global",
) -> NnMemoryType:
    """构造测试用 nn.memory type。

    功能说明:
    - 使用公开 `NnMemoryType`、`SymbolExprAttr` 和 `NnMemorySpaceAttr` 构造内存类型。

    使用示例:
    - mem_type = _memory_type()
    """

    return NnMemoryType(
        ArrayAttr([_symbol_attr(value) for value in shape]),
        ArrayAttr([_symbol_attr(value) for value in stride]),
        element_type,
        _memory_space(space),
    )


def _scalar_i32() -> Operation:
    """构造 i32 标量测试 op。

    功能说明:
    - 为 `dma.broadcast` 的 scalar source 提供公开 `arith.constant` SSA 值。

    使用示例:
    - scalar = _scalar_i32()
    """

    return arith.ConstantOp(IntegerAttr(1, i32))


def _const(value: int) -> SymbolConstOp:
    """构造 symbol.const op。

    功能说明:
    - 用于 `dma.view`、`dma.reshape`、`dma.deslice` 的 shape/offset/stride operand。

    使用示例:
    - zero = _const(0)
    """

    return SymbolConstOp(value)


def _module_with_ops(name: str, ops: list[Operation], return_values: list[SSAValue] | None = None) -> ModuleOp:
    """把 op 列表封装为单函数 module。

    功能说明:
    - 默认生成无返回值 `func.func`。
    - 提供 `return_values` 时同步生成函数返回类型。

    使用示例:
    - module = _module_with_ops("main", [alloc])
    """

    returns = [] if return_values is None else return_values
    block = Block()
    block.add_ops(ops)
    block.add_op(func.ReturnOp(*returns))
    return_types = [value.type for value in returns]
    func_op = func.FuncOp(name, FunctionType.from_lists([], return_types), Region(block))
    return ModuleOp([func_op])


def _module_with_block(name: str, block: Block, return_values: list[SSAValue] | None = None) -> ModuleOp:
    """把已有 block 封装为单函数 module。

    功能说明:
    - 用于需要函数参数的测试，例如动态 shape alloc。

    使用示例:
    - module = _module_with_block("main", block)
    """

    returns = [] if return_values is None else return_values
    block.add_op(func.ReturnOp(*returns))
    arg_types = [arg.type for arg in block.args]
    return_types = [value.type for value in returns]
    func_op = func.FuncOp(name, FunctionType.from_lists(arg_types, return_types), Region(block))
    return ModuleOp([func_op])


def _function_body(module: ModuleOp) -> Block:
    """返回 module 中第一个函数体 block。

    功能说明:
    - 通过公开 `func.FuncOp.body` 读取测试 module 的函数体。

    使用示例:
    - body = _function_body(module)
    """

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    return func_op.body.block


def _apply_memory_plan(module: ModuleOp, *, insert_free: bool = True) -> None:
    """通过公开 `MemoryPlanPass.apply(...)` 执行 pass。

    功能说明:
    - 测试 direct Python API 行为，不调用实现文件私有 helper。

    使用示例:
    - _apply_memory_plan(module)
    """

    MemoryPlanPass(insert_free=insert_free, fold=False).apply(Context(), module)


def _free_source_is(free: DmaFreeOp, value: SSAValue) -> bool:
    """判断 free 是否释放指定 SSA value。

    功能说明:
    - 使用公开 operand 值比较辅助测试断言。

    使用示例:
    - assert _free_source_is(free, alloc.result)
    """

    return SSAValue.get(free.source) is value


def _assert_memory_plan_error(module: ModuleOp, text: str) -> None:
    """断言 memory-plan 公开错误短语。

    功能说明:
    - 仅匹配 `KernelCodeError` 的稳定公开消息。

    使用示例:
    - _assert_memory_plan_error(module, "MemoryPlanInvalidLifetime")
    """

    with pytest.raises(KernelCodeError) as exc_info:
        _apply_memory_plan(module)
    assert text in str(exc_info.value)


# TC-MPLAN-001
# 功能说明: 验证 ircheck/registry 路径能为静态 alloc 插入 dma.free。
# 使用示例: pytest -q test/passes/test_memory_plan.py -k test_memory_plan_ircheck_inserts_free_for_static_alloc
# 对应功能实现文件路径: kernel_gen/passes/memory_plan.py
# 对应 spec 文件路径: spec/pass/memory_plan.md
# 对应测试文件路径: test/passes/test_memory_plan.py
def test_memory_plan_ircheck_inserts_free_for_static_alloc() -> None:
    result = run_ircheck_text(
        """// COMPILE_ARGS: --pass "memory-plan={insert-free=true,fold=false}"
// CHECK: "dma.alloc"
// CHECK: "dma.broadcast"
// CHECK: "dma.free"

builtin.module {
  func.func @static_insert() {
    %scalar = arith.constant 1 : i32
    %alloc = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<2>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], i32, #nn.space<global>>
    "dma.broadcast"(%alloc, %scalar) : (!nn.memory<[#symbol.expr<2>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], i32, #nn.space<global>>, i32) -> ()
    func.return
  }
}
""",
        source_path="memory_plan_static.ircheck",
    )

    assert result.ok, result.message or result.actual_ir


# TC-MPLAN-002
# 功能说明: 验证动态 alloc 保留 dynamic shape operand 并在最后 use 后插入 free。
# 使用示例: pytest -q test/passes/test_memory_plan.py -k test_memory_plan_inserts_free_for_dynamic_alloc
# 对应功能实现文件路径: kernel_gen/passes/memory_plan.py
# 对应 spec 文件路径: spec/pass/memory_plan.md
# 对应测试文件路径: test/passes/test_memory_plan.py
def test_memory_plan_inserts_free_for_dynamic_alloc() -> None:
    dynamic_type = _memory_type(shape=("N", 4), stride=(4, 1), element_type=i32)
    block = Block(arg_types=[SymbolValueType.from_expr("N")])
    scalar = _scalar_i32()
    alloc = DmaAllocOp([block.args[0]], dynamic_type)
    broadcast = DmaBroadcastOp(alloc.result, scalar.result)
    block.add_ops([scalar, alloc, broadcast])
    module = _module_with_block("dynamic_insert", block)

    _apply_memory_plan(module)

    body_ops = list(_function_body(module).ops)
    free_ops = [op for op in body_ops if isinstance(op, DmaFreeOp)]
    assert len(free_ops) == 1
    assert _free_source_is(free_ops[0], alloc.result)
    assert body_ops.index(free_ops[0]) == body_ops.index(broadcast) + 1


# TC-MPLAN-003
# 功能说明: 验证已有合法 free 时 pass 不重复插入。
# 使用示例: pytest -q test/passes/test_memory_plan.py -k test_memory_plan_keeps_existing_free_noop
# 对应功能实现文件路径: kernel_gen/passes/memory_plan.py
# 对应 spec 文件路径: spec/pass/memory_plan.md
# 对应测试文件路径: test/passes/test_memory_plan.py
def test_memory_plan_keeps_existing_free_noop() -> None:
    mem_type = _memory_type(element_type=i32)
    scalar = _scalar_i32()
    alloc = DmaAllocOp([], mem_type)
    broadcast = DmaBroadcastOp(alloc.result, scalar.result)
    free = DmaFreeOp(alloc.result)
    module = _module_with_ops("existing_free", [scalar, alloc, broadcast, free])

    _apply_memory_plan(module)

    free_ops = [op for op in _function_body(module).ops if isinstance(op, DmaFreeOp)]
    assert free_ops == [free]


# TC-MPLAN-004
# 功能说明: 验证 free 早于后续 use 必须失败。
# 使用示例: pytest -q test/passes/test_memory_plan.py -k test_memory_plan_rejects_free_before_last_use
# 对应功能实现文件路径: kernel_gen/passes/memory_plan.py
# 对应 spec 文件路径: spec/pass/memory_plan.md
# 对应测试文件路径: test/passes/test_memory_plan.py
def test_memory_plan_rejects_free_before_last_use() -> None:
    mem_type = _memory_type(element_type=i32)
    scalar = _scalar_i32()
    alloc = DmaAllocOp([], mem_type)
    free = DmaFreeOp(alloc.result)
    broadcast = DmaBroadcastOp(alloc.result, scalar.result)
    module = _module_with_ops("free_before_use", [scalar, alloc, free, broadcast])

    _assert_memory_plan_error(module, "MemoryPlanInvalidLifetime: dma.free appears before last use")


# TC-MPLAN-004A
# 功能说明: 验证 alloc 已 free 后通过 alias 继续 use 必须失败。
# 使用示例: pytest -q test/passes/test_memory_plan.py -k test_memory_plan_rejects_free_before_alias_use
# 对应功能实现文件路径: kernel_gen/passes/memory_plan.py
# 对应 spec 文件路径: spec/pass/memory_plan.md
# 对应测试文件路径: test/passes/test_memory_plan.py
def test_memory_plan_rejects_free_before_alias_use() -> None:
    mem_type = _memory_type(element_type=i32)
    zero0, zero1, two, four, one0, one1 = [_const(value) for value in (0, 0, 2, 4, 1, 1)]
    scalar = _scalar_i32()
    alloc = DmaAllocOp([], mem_type)
    free = DmaFreeOp(alloc.result)
    view = DmaViewOp(
        alloc.result,
        [zero0.result, zero1.result],
        [two.result, four.result],
        [one0.result, one1.result],
        mem_type,
    )
    broadcast = DmaBroadcastOp(view.result, scalar.result)
    module = _module_with_ops(
        "free_before_alias_use",
        [zero0, zero1, two, four, one0, one1, scalar, alloc, free, view, broadcast],
    )

    _assert_memory_plan_error(module, "MemoryPlanInvalidLifetime: dma.free appears before last use")


# TC-MPLAN-005
# 功能说明: 验证重复 free 必须失败。
# 使用示例: pytest -q test/passes/test_memory_plan.py -k test_memory_plan_rejects_multiple_free
# 对应功能实现文件路径: kernel_gen/passes/memory_plan.py
# 对应 spec 文件路径: spec/pass/memory_plan.md
# 对应测试文件路径: test/passes/test_memory_plan.py
def test_memory_plan_rejects_multiple_free() -> None:
    mem_type = _memory_type()
    alloc = DmaAllocOp([], mem_type)
    first = DmaFreeOp(alloc.result)
    second = DmaFreeOp(alloc.result)
    module = _module_with_ops("multiple_free", [alloc, first, second])

    _assert_memory_plan_error(module, "MemoryPlanInvalidLifetime: multiple dma.free for same allocation")


# TC-MPLAN-006
# 功能说明: 验证 view alias 的最后 use 决定 free 插入位置。
# 使用示例: pytest -q test/passes/test_memory_plan.py -k test_memory_plan_tracks_view_alias
# 对应功能实现文件路径: kernel_gen/passes/memory_plan.py
# 对应 spec 文件路径: spec/pass/memory_plan.md
# 对应测试文件路径: test/passes/test_memory_plan.py
def test_memory_plan_tracks_view_alias() -> None:
    mem_type = _memory_type(element_type=i32)
    zero0, zero1, two, four, one0, one1 = [_const(value) for value in (0, 0, 2, 4, 1, 1)]
    scalar = _scalar_i32()
    alloc = DmaAllocOp([], mem_type)
    view = DmaViewOp(
        alloc.result,
        [zero0.result, zero1.result],
        [two.result, four.result],
        [one0.result, one1.result],
        mem_type,
    )
    broadcast = DmaBroadcastOp(view.result, scalar.result)
    module = _module_with_ops("view_alias", [zero0, zero1, two, four, one0, one1, scalar, alloc, view, broadcast])

    _apply_memory_plan(module)

    body_ops = list(_function_body(module).ops)
    free = next(op for op in body_ops if isinstance(op, DmaFreeOp))
    assert _free_source_is(free, alloc.result)
    assert body_ops.index(free) == body_ops.index(broadcast) + 1


# TC-MPLAN-006A
# 功能说明: 验证 reshape alias 的最后 use 决定 free 插入位置。
# 使用示例: pytest -q test/passes/test_memory_plan.py -k test_memory_plan_tracks_reshape_alias
# 对应功能实现文件路径: kernel_gen/passes/memory_plan.py
# 对应 spec 文件路径: spec/pass/memory_plan.md
# 对应测试文件路径: test/passes/test_memory_plan.py
def test_memory_plan_tracks_reshape_alias() -> None:
    source_type = _memory_type(shape=(2, 4), stride=(4, 1), element_type=i32)
    result_type = _memory_type(shape=(8,), stride=(1,), element_type=i32)
    eight = _const(8)
    scalar = _scalar_i32()
    alloc = DmaAllocOp([], source_type)
    reshape = DmaReshapeOp(alloc.result, [eight.result], result_type)
    broadcast = DmaBroadcastOp(reshape.result, scalar.result)
    module = _module_with_ops("reshape_alias", [eight, scalar, alloc, reshape, broadcast])

    _apply_memory_plan(module)

    body_ops = list(_function_body(module).ops)
    free = next(op for op in body_ops if isinstance(op, DmaFreeOp))
    assert _free_source_is(free, alloc.result)
    assert body_ops.index(free) == body_ops.index(broadcast) + 1


# TC-MPLAN-006B
# 功能说明: 验证 subview alias 的最后 use 决定 free 插入位置。
# 使用示例: pytest -q test/passes/test_memory_plan.py -k test_memory_plan_tracks_subview_alias
# 对应功能实现文件路径: kernel_gen/passes/memory_plan.py
# 对应 spec 文件路径: spec/pass/memory_plan.md
# 对应测试文件路径: test/passes/test_memory_plan.py
def test_memory_plan_tracks_subview_alias() -> None:
    pool_type = _memory_type(shape=(64,), stride=(1,), element_type=i8)
    result_type = _memory_type(shape=(8,), stride=(1,), element_type=i32)
    zero, eight, one = [_const(value) for value in (0, 8, 1)]
    scalar = _scalar_i32()
    alloc = DmaAllocOp([], pool_type)
    subview = DmaSubviewOp(alloc.result, zero.result, eight.result, one.result, result_type)
    broadcast = DmaBroadcastOp(subview.result, scalar.result)
    module = _module_with_ops("subview_alias", [zero, eight, one, scalar, alloc, subview, broadcast])

    _apply_memory_plan(module)

    body_ops = list(_function_body(module).ops)
    free = next(op for op in body_ops if isinstance(op, DmaFreeOp))
    assert _free_source_is(free, alloc.result)
    assert body_ops.index(free) == body_ops.index(broadcast) + 1


# TC-MPLAN-007
# 功能说明: 验证 deslice result alias target 且不把 source 纳入 target alias closure。
# 使用示例: pytest -q test/passes/test_memory_plan.py -k test_memory_plan_tracks_deslice_target_alias_not_source
# 对应功能实现文件路径: kernel_gen/passes/memory_plan.py
# 对应 spec 文件路径: spec/pass/memory_plan.md
# 对应测试文件路径: test/passes/test_memory_plan.py
def test_memory_plan_tracks_deslice_target_alias_not_source() -> None:
    mem_type = _memory_type(element_type=i32)
    zero0, zero1, two, four, one0, one1 = [_const(value) for value in (0, 0, 2, 4, 1, 1)]
    scalar_target = _scalar_i32()
    scalar_source = _scalar_i32()
    target_alloc = DmaAllocOp([], mem_type)
    source_alloc = DmaAllocOp([], mem_type)
    deslice = DmaDesliceOp(
        target_alloc.result,
        source_alloc.result,
        [zero0.result, zero1.result],
        [two.result, four.result],
        [one0.result, one1.result],
        mem_type,
    )
    target_broadcast = DmaBroadcastOp(deslice.result, scalar_target.result)
    source_broadcast = DmaBroadcastOp(source_alloc.result, scalar_source.result)
    module = _module_with_ops(
        "deslice_alias",
        [
            zero0,
            zero1,
            two,
            four,
            one0,
            one1,
            scalar_target,
            scalar_source,
            target_alloc,
            source_alloc,
            deslice,
            target_broadcast,
            source_broadcast,
        ],
    )

    _apply_memory_plan(module)

    body_ops = list(_function_body(module).ops)
    free_ops = [op for op in body_ops if isinstance(op, DmaFreeOp)]
    assert len(free_ops) == 2
    assert _free_source_is(free_ops[0], target_alloc.result)
    assert _free_source_is(free_ops[1], source_alloc.result)
    assert body_ops.index(free_ops[0]) == body_ops.index(target_broadcast) + 1
    assert body_ops.index(free_ops[0]) < body_ops.index(source_broadcast)


# TC-MPLAN-008
# 功能说明: 验证 nested symbol.for 中 inner 与 outer alloc 的 free 插入位置。
# 使用示例: pytest -q test/passes/test_memory_plan.py -k test_memory_plan_nested_symbol_for_places_inner_and_outer_free
# 对应功能实现文件路径: kernel_gen/passes/memory_plan.py
# 对应 spec 文件路径: spec/pass/memory_plan.md
# 对应测试文件路径: test/passes/test_memory_plan.py
def test_memory_plan_nested_symbol_for_places_inner_and_outer_free() -> None:
    mem_type = _memory_type(element_type=i32, space="shared")
    outer_block = Block(arg_types=[SymbolIterType.from_bounds("0", "2", "1")])
    inner_block = Block(arg_types=[SymbolIterType.from_bounds("0", "2", "1")])
    outer_alloc = DmaAllocOp([], mem_type)
    inner_alloc = DmaAllocOp([], mem_type)
    inner_broadcast = DmaBroadcastOp(inner_alloc.result, outer_alloc.result)
    inner_block.add_ops([inner_alloc, inner_broadcast])
    inner_start, inner_end, inner_step = [_const(value) for value in (0, 2, 1)]
    inner_loop = SymbolForOp(inner_start.result, inner_end.result, inner_step.result, inner_block)
    zero0, zero1, two, four, one0, one1 = [_const(value) for value in (0, 0, 2, 4, 1, 1)]
    source_alloc = DmaAllocOp([], mem_type)
    view = DmaViewOp(
        outer_alloc.result,
        [zero0.result, zero1.result],
        [two.result, four.result],
        [one0.result, one1.result],
        mem_type,
    )
    deslice = DmaDesliceOp(view.result, source_alloc.result, [zero0.result, zero1.result], [two.result, four.result], [one0.result, one1.result], mem_type)
    outer_block.add_ops([
        outer_alloc,
        inner_start,
        inner_end,
        inner_step,
        inner_loop,
        zero0,
        zero1,
        two,
        four,
        one0,
        one1,
        source_alloc,
        view,
        deslice,
    ])
    outer_start, outer_end, outer_step = [_const(value) for value in (0, 2, 1)]
    outer_loop = SymbolForOp(outer_start.result, outer_end.result, outer_step.result, outer_block)
    module = _module_with_ops("nested_symbol_for", [outer_start, outer_end, outer_step, outer_loop])

    _apply_memory_plan(module)

    outer_ops = list(outer_block.ops)
    inner_ops = list(inner_block.ops)
    inner_free = next(op for op in inner_ops if isinstance(op, DmaFreeOp) and _free_source_is(op, inner_alloc.result))
    outer_free = next(op for op in outer_ops if isinstance(op, DmaFreeOp) and _free_source_is(op, outer_alloc.result))
    assert inner_ops.index(inner_free) == inner_ops.index(inner_broadcast) + 1
    assert outer_ops.index(outer_free) > outer_ops.index(deslice)
    assert outer_ops.index(outer_free) < len(outer_ops)


# TC-MPLAN-008A
# 功能说明: 验证 nested symbol.for 内 free 早于同一 inner body 的后续 use 必须失败。
# 使用示例: pytest -q test/passes/test_memory_plan.py -k test_memory_plan_rejects_nested_symbol_for_free_before_later_inner_use
# 对应功能实现文件路径: kernel_gen/passes/memory_plan.py
# 对应 spec 文件路径: spec/pass/memory_plan.md
# 对应测试文件路径: test/passes/test_memory_plan.py
def test_memory_plan_rejects_nested_symbol_for_free_before_later_inner_use() -> None:
    mem_type = _memory_type(element_type=i32, space="shared")
    alloc = DmaAllocOp([], mem_type)
    inner_block = Block(arg_types=[SymbolIterType.from_bounds("0", "2", "1")])
    free = DmaFreeOp(alloc.result)
    scalar = _scalar_i32()
    broadcast = DmaBroadcastOp(alloc.result, scalar.result)
    inner_block.add_ops([free, scalar, broadcast])
    start, end, step = [_const(value) for value in (0, 2, 1)]
    loop = SymbolForOp(start.result, end.result, step.result, inner_block)
    module = _module_with_ops("nested_free_before_later_inner_use", [alloc, start, end, step, loop])

    _assert_memory_plan_error(module, "MemoryPlanInvalidLifetime: dma.free appears before last use")


# TC-MPLAN-008B
# 功能说明: 验证 nested symbol.for 内释放 owner-block alloc 不能作为合法最终释放。
# 使用示例: pytest -q test/passes/test_memory_plan.py -k test_memory_plan_rejects_nested_symbol_for_free_inside_loop_for_outer_alloc
# 对应功能实现文件路径: kernel_gen/passes/memory_plan.py
# 对应 spec 文件路径: spec/pass/memory_plan.md
# 对应测试文件路径: test/passes/test_memory_plan.py
def test_memory_plan_rejects_nested_symbol_for_free_inside_loop_for_outer_alloc() -> None:
    mem_type = _memory_type(element_type=i32, space="shared")
    alloc = DmaAllocOp([], mem_type)
    inner_block = Block(arg_types=[SymbolIterType.from_bounds("0", "2", "1")])
    scalar = _scalar_i32()
    broadcast = DmaBroadcastOp(alloc.result, scalar.result)
    free = DmaFreeOp(alloc.result)
    inner_block.add_ops([scalar, broadcast, free])
    start, end, step = [_const(value) for value in (0, 2, 1)]
    loop = SymbolForOp(start.result, end.result, step.result, inner_block)
    module = _module_with_ops("nested_free_inside_loop_for_outer_alloc", [alloc, start, end, step, loop])

    _assert_memory_plan_error(module, "MemoryPlanInvalidLifetime: dma.free appears before last use")


# TC-MPLAN-009
# 功能说明: 验证普通 call operand 计为 use，free 插在 call 后。
# 使用示例: pytest -q test/passes/test_memory_plan.py -k test_memory_plan_allows_call_operand
# 对应功能实现文件路径: kernel_gen/passes/memory_plan.py
# 对应 spec 文件路径: spec/pass/memory_plan.md
# 对应测试文件路径: test/passes/test_memory_plan.py
def test_memory_plan_allows_call_operand() -> None:
    mem_type = _memory_type()
    alloc = DmaAllocOp([], mem_type)
    call = func.CallOp("consume", [alloc.result], [])
    module = _module_with_ops("call_operand", [alloc, call])

    _apply_memory_plan(module)

    body_ops = list(_function_body(module).ops)
    free = next(op for op in body_ops if isinstance(op, DmaFreeOp))
    assert body_ops.index(free) == body_ops.index(call) + 1


# TC-MPLAN-010
# 功能说明: 验证 memory-return call 必须按 ownership modelling 缺口失败。
# 使用示例: pytest -q test/passes/test_memory_plan.py -k test_memory_plan_rejects_memory_return_call
# 对应功能实现文件路径: kernel_gen/passes/memory_plan.py
# 对应 spec 文件路径: spec/pass/memory_plan.md
# 对应测试文件路径: test/passes/test_memory_plan.py
def test_memory_plan_rejects_memory_return_call() -> None:
    mem_type = _memory_type()
    alloc = DmaAllocOp([], mem_type)
    call = func.CallOp("produce", [alloc.result], [mem_type])
    module = _module_with_ops("memory_return_call", [alloc, call])

    _assert_memory_plan_error(module, "MemoryPlanUnsupportedCall: func.call returning nn.memory requires ownership modelling")


# TC-MPLAN-011
# 功能说明: 验证 alloc alias 经 func.return 逃逸时必须失败。
# 使用示例: pytest -q test/passes/test_memory_plan.py -k test_memory_plan_rejects_return_escape
# 对应功能实现文件路径: kernel_gen/passes/memory_plan.py
# 对应 spec 文件路径: spec/pass/memory_plan.md
# 对应测试文件路径: test/passes/test_memory_plan.py
def test_memory_plan_rejects_return_escape() -> None:
    mem_type = _memory_type()
    alloc = DmaAllocOp([], mem_type)
    module = _module_with_ops("return_escape", [alloc], return_values=[alloc.result])

    _assert_memory_plan_error(module, "MemoryPlanUnsupportedEscape: dma.alloc escapes current supported region")


# TC-MPLAN-012
# 功能说明: 验证 scf.for 内 alloc 被当前阶段显式拒绝。
# 使用示例: pytest -q test/passes/test_memory_plan.py -k test_memory_plan_rejects_scf_for_region
# 对应功能实现文件路径: kernel_gen/passes/memory_plan.py
# 对应 spec 文件路径: spec/pass/memory_plan.md
# 对应测试文件路径: test/passes/test_memory_plan.py
def test_memory_plan_rejects_scf_for_region() -> None:
    mem_type = _memory_type()
    start = arith.ConstantOp(IntegerAttr(0, IndexType()))
    end = arith.ConstantOp(IntegerAttr(2, IndexType()))
    step = arith.ConstantOp(IntegerAttr(1, IndexType()))
    loop_block = Block(arg_types=[IndexType()])
    alloc = DmaAllocOp([], mem_type)
    loop_block.add_ops([alloc, scf.YieldOp()])
    loop = scf.ForOp(start.result, end.result, step.result, [], loop_block)
    module = _module_with_ops("scf_for_region", [start, end, step, loop])

    _assert_memory_plan_error(module, "MemoryPlanUnsupportedControlFlow: unsupported memory lifetime region")


# TC-MPLAN-012A
# 功能说明: 验证 scf.if 内 alloc 被当前阶段显式拒绝。
# 使用示例: pytest -q test/passes/test_memory_plan.py -k test_memory_plan_rejects_scf_if_region
# 对应功能实现文件路径: kernel_gen/passes/memory_plan.py
# 对应 spec 文件路径: spec/pass/memory_plan.md
# 对应测试文件路径: test/passes/test_memory_plan.py
def test_memory_plan_rejects_scf_if_region() -> None:
    mem_type = _memory_type()
    condition = arith.ConstantOp(IntegerAttr(1, i1))
    true_block = Block()
    alloc = DmaAllocOp([], mem_type)
    true_block.add_ops([alloc, scf.YieldOp()])
    if_op = scf.IfOp(condition.result, [], Region(true_block), None)
    module = _module_with_ops("scf_if_region", [condition, if_op])

    _assert_memory_plan_error(module, "MemoryPlanUnsupportedControlFlow: unsupported memory lifetime region")


# TC-MPLAN-013
# 功能说明: 验证 insert_free=False 是显式 no-op，不做生命周期检查。
# 使用示例: pytest -q test/passes/test_memory_plan.py -k test_memory_plan_disabled_is_noop
# 对应功能实现文件路径: kernel_gen/passes/memory_plan.py
# 对应 spec 文件路径: spec/pass/memory_plan.md
# 对应测试文件路径: test/passes/test_memory_plan.py
def test_memory_plan_disabled_is_noop() -> None:
    mem_type = _memory_type(element_type=i32)
    scalar = _scalar_i32()
    alloc = DmaAllocOp([], mem_type)
    free = DmaFreeOp(alloc.result)
    broadcast = DmaBroadcastOp(alloc.result, scalar.result)
    module = _module_with_ops("disabled_noop", [scalar, alloc, free, broadcast])

    _apply_memory_plan(module, insert_free=False)

    assert [op for op in _function_body(module).ops if isinstance(op, DmaFreeOp)] == [free]
