"""symbol-loop-hoist pass tests.


功能说明:
- 覆盖 `SymbolLoopHoistPass` 的外提白名单、禁止项与固定失败短语。

使用示例:
- pytest -q test/passes/test_symbol_loop_hoist.py

当前覆盖率信息:
- `kernel_gen.passes.symbol_loop_hoist`：`80%`（Stmts=135 Miss=20 Branch=66 BrPart=14；最近一次统计：2026-04-24 04:42:42 +0800）。

覆盖率命令:
- `pytest -q --cov=kernel_gen.passes.symbol_loop_hoist --cov-branch --cov-report=term-missing test/passes/test_symbol_loop_hoist.py`

关联文件:
- 功能实现: kernel_gen/passes/symbol_loop_hoist.py
- Spec 文档: spec/pass/symbol_loop_hoist.md
- 测试文件: test/passes/test_symbol_loop_hoist.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from xdsl.dialects import arith, func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, IntegerAttr, ModuleOp, StringAttr, i32
from xdsl.ir import Block, Region, SSAValue
from xdsl.dialects.builtin import UnrealizedConversionCastOp
from xdsl.context import Context
from xdsl.passes import ModulePass

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolConstOp,
    SymbolDivOp,
    SymbolFloorDivOp,
    SymbolForOp,
    SymbolGetDimOp,
    SymbolGetStrideOp,
    SymbolIterType,
    SymbolMulOp,
    SymbolSubOp,
    SymbolValueType,
    SymbolYieldOp,
)
from kernel_gen.dialect.tuner import TunerParamOp

pass_module = importlib.import_module("kernel_gen.passes.symbol_loop_hoist")
SymbolAddHoistPattern = pass_module.SymbolAddHoistPattern
SymbolConstHoistPattern = pass_module.SymbolConstHoistPattern
SymbolDivHoistPattern = pass_module.SymbolDivHoistPattern
SymbolFloorDivHoistPattern = pass_module.SymbolFloorDivHoistPattern
SymbolGetDimHoistPattern = pass_module.SymbolGetDimHoistPattern
SymbolGetStrideHoistPattern = pass_module.SymbolGetStrideHoistPattern
SymbolLoopHoistPass = pass_module.SymbolLoopHoistPass
SymbolMulHoistPattern = pass_module.SymbolMulHoistPattern
SymbolSubHoistPattern = pass_module.SymbolSubHoistPattern
TunerParamHoistPattern = pass_module.TunerParamHoistPattern
get_symbol_loop_hoist_patterns = pass_module.get_symbol_loop_hoist_patterns
lowering_pass_module = importlib.import_module("kernel_gen.passes.lowering")


def _const_symbol_int(value: int) -> tuple[arith.ConstantOp, UnrealizedConversionCastOp, SSAValue]:
    const = arith.ConstantOp(IntegerAttr(value, i32))
    cast = UnrealizedConversionCastOp(
        operands=[const.result],
        result_types=[SymbolValueType.from_expr(str(value))],
    )
    return const, cast, cast.results[0]


def _memory_type(shape: tuple[int | str, ...]) -> NnMemoryType:
    strides: list[object] = []
    running: int | str | None = 1
    for dim in reversed(shape):
        if running is None:
            strides.append(StringAttr("?"))
        elif isinstance(running, int):
            strides.append(IntAttr(running))
        else:
            strides.append(StringAttr(running))
        if running is None:
            continue
        if isinstance(dim, int):
            if dim == 1:
                continue
            if isinstance(running, int):
                running *= dim
            else:
                running = f"{dim}*{running}"
            continue
        if isinstance(dim, str):
            if dim == "?":
                running = None
            elif running == 1:
                running = dim
            else:
                running = f"{dim}*{running}"
            continue
        running = None
    strides.reverse()
    return NnMemoryType(
        ArrayAttr([IntAttr(d) if isinstance(d, int) else StringAttr(d) for d in shape]),
        ArrayAttr([s if isinstance(s, (IntAttr, StringAttr)) else StringAttr(str(s)) for s in strides]),
        i32,
        NnMemorySpaceAttr.from_name("global"),
    )


def _make_module_for_symbol_dim_hoist() -> ModuleOp:
    mem_type = _memory_type(("M", 128))
    block = Block(arg_types=[mem_type])
    ops: list[object] = []
    c0, c0_cast, zero = _const_symbol_int(0)
    c1, c1_cast, one = _const_symbol_int(1)
    ops.extend([c0, c0_cast, c1, c1_cast])

    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    get_dim = SymbolGetDimOp(block.args[0], IntAttr(0))
    get_stride = SymbolGetStrideOp(block.args[0], IntAttr(1))
    loop_block.add_ops([get_dim, get_stride])
    loop = SymbolForOp(zero, one, one, loop_block)
    ops.append(loop)
    ops.append(func.ReturnOp())
    block.add_ops(ops)
    func_op = func.FuncOp(
        "hoist_symbol_dim",
        FunctionType.from_lists([mem_type], []),
        Region(block),
    )
    return ModuleOp([func_op])


def _make_module_for_const_hoist() -> ModuleOp:
    block = Block(arg_types=[])
    ops: list[object] = []
    c0 = SymbolConstOp(0)
    c1 = SymbolConstOp(1)
    c2 = SymbolConstOp(1)
    ops.extend([c0, c1, c2])

    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    hoist_const = SymbolConstOp(2)
    loop_block.add_ops([hoist_const])
    loop = SymbolForOp(c0.result, c1.result, c2.result, loop_block)
    ops.append(loop)
    ops.append(func.ReturnOp())
    block.add_ops(ops)
    func_op = func.FuncOp(
        "hoist_const",
        FunctionType.from_lists([], []),
        Region(block),
    )
    return ModuleOp([func_op])


def _make_module_for_tuner_param_hoist() -> ModuleOp:
    block = Block(arg_types=[])
    ops: list[object] = []
    c0 = SymbolConstOp(0)
    c1 = SymbolConstOp(1)
    c2 = SymbolConstOp(1)
    ops.extend([c0, c1, c2])

    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    loop_block.add_ops([TunerParamOp(SymbolValueType.from_expr("TILE_D0"))])
    loop = SymbolForOp(c0.result, c1.result, c2.result, loop_block)
    ops.append(loop)
    ops.append(func.ReturnOp())
    block.add_ops(ops)
    func_op = func.FuncOp(
        "hoist_tuner_param",
        FunctionType.from_lists([], []),
        Region(block),
    )
    return ModuleOp([func_op])


def _make_module_for_symbol_elewise_hoist() -> ModuleOp:
    block = Block(arg_types=[])
    ops: list[object] = []
    c0 = SymbolConstOp(0)
    c1 = SymbolConstOp(1)
    c2 = SymbolConstOp(1)
    c4 = SymbolConstOp(4)
    c5 = SymbolConstOp(5)
    c6 = SymbolConstOp(6)
    c7 = SymbolConstOp(7)
    c8 = SymbolConstOp(8)
    ops.extend([c0, c1, c2, c4, c5, c6, c7, c8])

    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    add = SymbolAddOp(c4.result, c5.result, SymbolValueType.from_expr("4 + 5"))
    sub = SymbolSubOp(c6.result, c1.result, SymbolValueType.from_expr("6 - 1"))
    mul = SymbolMulOp(c4.result, c2.result, SymbolValueType.from_expr("4 * 1"))
    div = SymbolDivOp(c8.result, c2.result, SymbolValueType.from_expr("8 floordiv 1"))
    floordiv = SymbolFloorDivOp(c7.result, c2.result, SymbolValueType.from_expr("7 floordiv 1"))
    loop_block.add_ops([add, sub, mul, div, floordiv])
    loop = SymbolForOp(c0.result, c1.result, c2.result, loop_block)
    ops.append(loop)
    ops.append(func.ReturnOp())
    block.add_ops(ops)
    func_op = func.FuncOp(
        "hoist_symbol_elewise",
        FunctionType.from_lists([], []),
        Region(block),
    )
    return ModuleOp([func_op])


def _make_module_for_loop_carried_symbol_add() -> ModuleOp:
    block = Block(arg_types=[])
    ops: list[object] = []
    c0 = SymbolConstOp(0)
    c1 = SymbolConstOp(1)
    c2 = SymbolConstOp(1)
    ops.extend([c0, c1, c2])

    loop_block = Block(
        arg_types=[
            SymbolIterType.from_bounds("0", "1", "1"),
            SymbolValueType.from_expr("TOTAL"),
        ]
    )
    carried = loop_block.args[1]
    carried_add = SymbolAddOp(carried, c1.result, SymbolValueType.from_expr("TOTAL + 1"))
    loop_block.add_ops([carried_add, SymbolYieldOp(carried_add.result)])
    loop = SymbolForOp(
        c0.result,
        c1.result,
        c2.result,
        loop_block,
        init=c0.result,
        result_type=SymbolValueType.from_expr("TOTAL"),
    )
    ops.append(loop)
    ops.append(func.ReturnOp())
    block.add_ops(ops)
    func_op = func.FuncOp(
        "keep_loop_carried_symbol_add",
        FunctionType.from_lists([], []),
        Region(block),
    )
    return ModuleOp([func_op])


def _make_module_for_loop_local_symbol_inputs() -> ModuleOp:
    mem_type = _memory_type((4,))
    block = Block(arg_types=[])
    ops: list[object] = []
    c0 = SymbolConstOp(0)
    c1 = SymbolConstOp(1)
    c2 = SymbolConstOp(1)
    ops.extend([c0, c1, c2])

    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    local_const = arith.ConstantOp(IntegerAttr(3, i32))
    local_symbol = UnrealizedConversionCastOp(
        operands=[local_const.result],
        result_types=[SymbolValueType.from_expr("3")],
    )
    local_alloc = DmaAllocOp([], mem_type)
    get_dim = SymbolGetDimOp(local_alloc.result, IntAttr(0))
    get_stride = SymbolGetStrideOp(local_alloc.result, IntAttr(0))
    add = SymbolAddOp(local_symbol.results[0], c1.result, SymbolValueType.from_expr("3 + 1"))
    sub = SymbolSubOp(local_symbol.results[0], c1.result, SymbolValueType.from_expr("3 - 1"))
    mul = SymbolMulOp(local_symbol.results[0], c1.result, SymbolValueType.from_expr("3 * 1"))
    div = SymbolDivOp(local_symbol.results[0], c1.result, SymbolValueType.from_expr("3 floordiv 1"))
    floordiv = SymbolFloorDivOp(local_symbol.results[0], c1.result, SymbolValueType.from_expr("3 floordiv 1"))
    loop_block.add_ops([
        local_const,
        local_symbol,
        local_alloc,
        get_dim,
        get_stride,
        add,
        sub,
        mul,
        div,
        floordiv,
    ])
    loop = SymbolForOp(c0.result, c1.result, c2.result, loop_block)
    ops.append(loop)
    ops.append(func.ReturnOp())
    block.add_ops(ops)
    func_op = func.FuncOp(
        "keep_loop_local_symbol_inputs",
        FunctionType.from_lists([], []),
        Region(block),
    )
    return ModuleOp([func_op])


def _make_module_for_loop_carried_symbol_elewise() -> ModuleOp:
    block = Block(arg_types=[])
    ops: list[object] = []
    c0 = SymbolConstOp(0)
    c1 = SymbolConstOp(1)
    c2 = SymbolConstOp(1)
    ops.extend([c0, c1, c2])

    loop_block = Block(
        arg_types=[
            SymbolIterType.from_bounds("0", "1", "1"),
            SymbolValueType.from_expr("TOTAL"),
        ]
    )
    carried = loop_block.args[1]
    add = SymbolAddOp(carried, c1.result, SymbolValueType.from_expr("TOTAL + 1"))
    sub = SymbolSubOp(carried, c1.result, SymbolValueType.from_expr("TOTAL - 1"))
    mul = SymbolMulOp(carried, c1.result, SymbolValueType.from_expr("TOTAL * 1"))
    div = SymbolDivOp(carried, c1.result, SymbolValueType.from_expr("TOTAL floordiv 1"))
    floordiv = SymbolFloorDivOp(carried, c1.result, SymbolValueType.from_expr("TOTAL floordiv 1"))
    loop_block.add_ops([add, sub, mul, div, floordiv, SymbolYieldOp(add.result)])
    loop = SymbolForOp(
        c0.result,
        c1.result,
        c2.result,
        loop_block,
        init=c0.result,
        result_type=SymbolValueType.from_expr("TOTAL"),
    )
    ops.append(loop)
    ops.append(func.ReturnOp())
    block.add_ops(ops)
    func_op = func.FuncOp(
        "keep_loop_carried_symbol_elewise",
        FunctionType.from_lists([], []),
        Region(block),
    )
    return ModuleOp([func_op])


def _make_module_without_symbol_for() -> ModuleOp:
    block = Block(arg_types=[])
    only_const = SymbolConstOp(7)
    block.add_ops([only_const, func.ReturnOp()])
    func_op = func.FuncOp(
        "no_symbol_for",
        FunctionType.from_lists([], []),
        Region(block),
    )
    return ModuleOp([func_op])


def _make_module_with_step_zero() -> ModuleOp:
    mem_type = _memory_type(("M", 128))
    block = Block(arg_types=[mem_type, mem_type, mem_type])
    ops: list[object] = []
    c0, c0_cast, zero = _const_symbol_int(0)
    c1, c1_cast, one = _const_symbol_int(1)
    ops.extend([c0, c0_cast, c1, c1_cast])

    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "0")])
    get_dim = SymbolGetDimOp(block.args[0], IntAttr(0))
    loop_block.add_ops([get_dim])
    loop = SymbolForOp(zero, one, zero, loop_block)
    ops.append(loop)
    ops.append(func.ReturnOp())
    block.add_ops(ops)
    func_op = func.FuncOp(
        "step_zero",
        FunctionType.from_lists([mem_type, mem_type, mem_type], []),
        Region(block),
    )
    return ModuleOp([func_op])


# TC-SLH-001
# 测试目的: 验证 loop 内 invariant `symbol.get_dim/get_stride` 会被向上提一层到 `symbol.for` 之前。
# 对应功能实现文件路径: kernel_gen/passes/symbol_loop_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_loop_hoist.md
# 对应测试文件路径: test/passes/test_symbol_loop_hoist.py
def test_symbol_loop_hoist_hoists_symbol_dim_ops() -> None:
    module = _make_module_for_symbol_dim_hoist()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.blocks.first
    loop = next(op for op in block.ops if isinstance(op, SymbolForOp))

    SymbolLoopHoistPass(fold=False).apply(Context(), module)

    ops = list(block.ops)
    loop_index = ops.index(loop)
    hoisted_ops = [op for op in ops[:loop_index] if isinstance(op, (SymbolGetDimOp, SymbolGetStrideOp))]
    assert [type(op) for op in hoisted_ops] == [SymbolGetDimOp, SymbolGetStrideOp]
    assert not any(isinstance(op, (SymbolGetDimOp, SymbolGetStrideOp)) for op in loop.body.blocks.first.ops)


# TC-SLH-001A
# 测试目的: 验证 loop 内的 invariant `symbol.const` 会被向上提一层到 `symbol.for` 之前。
# 对应功能实现文件路径: kernel_gen/passes/symbol_loop_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_loop_hoist.md
# 对应测试文件路径: test/passes/test_symbol_loop_hoist.py
def test_symbol_loop_hoist_hoists_symbol_const() -> None:
    module = _make_module_for_const_hoist()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.blocks.first
    loop = next(op for op in block.ops if isinstance(op, SymbolForOp))

    SymbolLoopHoistPass(fold=False).apply(Context(), module)

    ops = list(block.ops)
    loop_index = ops.index(loop)
    hoisted_consts = [op for op in ops[:loop_index] if isinstance(op, SymbolConstOp)]
    assert len(hoisted_consts) == 4
    assert [op.value.data for op in hoisted_consts] == [0, 1, 1, 2]


def test_symbol_loop_hoist_is_exported_from_lowering_package() -> None:
    assert lowering_pass_module.SymbolLoopHoistPass is SymbolLoopHoistPass


# TC-SLH-001B
# 测试目的: 验证公开 pattern 与 getter 可导入，且 getter 顺序稳定。
# 对应功能实现文件路径: kernel_gen/passes/symbol_loop_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_loop_hoist.md
# 对应测试文件路径: test/passes/test_symbol_loop_hoist.py
def test_symbol_loop_hoist_patterns_are_public_and_stable() -> None:
    patterns = get_symbol_loop_hoist_patterns()

    assert [type(pattern) for pattern in patterns] == [
        SymbolConstHoistPattern,
        TunerParamHoistPattern,
        SymbolGetDimHoistPattern,
        SymbolGetStrideHoistPattern,
        SymbolAddHoistPattern,
        SymbolSubHoistPattern,
        SymbolMulHoistPattern,
        SymbolDivHoistPattern,
        SymbolFloorDivHoistPattern,
    ]


# TC-SLH-001C
# 测试目的: 验证 loop 内 invariant `tuner.param` 会被向上提一层到 `symbol.for` 之前。
# 对应功能实现文件路径: kernel_gen/passes/symbol_loop_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_loop_hoist.md
# 对应测试文件路径: test/passes/test_symbol_loop_hoist.py
def test_symbol_loop_hoist_hoists_tuner_param() -> None:
    module = _make_module_for_tuner_param_hoist()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.blocks.first
    loop = next(op for op in block.ops if isinstance(op, SymbolForOp))

    SymbolLoopHoistPass().apply(Context(), module)

    ops = list(block.ops)
    loop_index = ops.index(loop)
    hoisted_ops = [op for op in ops[:loop_index] if isinstance(op, TunerParamOp)]
    assert len(hoisted_ops) == 1
    assert not any(isinstance(op, TunerParamOp) for op in loop.body.blocks.first.ops)


# TC-SLH-001D
# 测试目的: 验证 loop 内 invariant `symbol.add/sub/mul/div/floordiv` 会被向上提一层到 `symbol.for` 之前。
# 对应功能实现文件路径: kernel_gen/passes/symbol_loop_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_loop_hoist.md
# 对应测试文件路径: test/passes/test_symbol_loop_hoist.py
def test_symbol_loop_hoist_hoists_symbol_elewise_ops() -> None:
    module = _make_module_for_symbol_elewise_hoist()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.blocks.first
    loop = next(op for op in block.ops if isinstance(op, SymbolForOp))

    SymbolLoopHoistPass(fold=False).apply(Context(), module)

    ops = list(block.ops)
    loop_index = ops.index(loop)
    hoisted_ops = [
        op
        for op in ops[:loop_index]
        if isinstance(op, (SymbolAddOp, SymbolSubOp, SymbolMulOp, SymbolDivOp, SymbolFloorDivOp))
    ]
    assert [type(op) for op in hoisted_ops] == [
        SymbolAddOp,
        SymbolSubOp,
        SymbolMulOp,
        SymbolDivOp,
        SymbolFloorDivOp,
    ]


# TC-SLH-001E
# 测试目的: 验证 `SymbolLoopHoistPass` 作为 ModulePass 可直接通过 apply(ctx, module) 执行。
# 对应功能实现文件路径: kernel_gen/passes/symbol_loop_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_loop_hoist.md
# 对应测试文件路径: test/passes/test_symbol_loop_hoist.py
def test_symbol_loop_hoist_apply_behaves_like_module_pass() -> None:
    module = _make_module_for_const_hoist()
    pass_obj = SymbolLoopHoistPass()
    ctx = Context()

    assert isinstance(pass_obj, ModulePass)

    result = pass_obj.apply(ctx, module)

    assert result is None
    module.verify()


# TC-SLH-001F
# 测试目的: 验证 module 不含 `symbol.for` 时保持 no-op。
# 对应功能实现文件路径: kernel_gen/passes/symbol_loop_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_loop_hoist.md
# 对应测试文件路径: test/passes/test_symbol_loop_hoist.py
def test_symbol_loop_hoist_keeps_module_without_symbol_for_no_op() -> None:
    module = _make_module_without_symbol_for()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.blocks.first
    before_ops = list(block.ops)

    SymbolLoopHoistPass().apply(Context(), module)

    assert list(block.ops) == before_ops


# TC-SLH-002
# 测试目的: 验证依赖 loop iv 的 `symbol.add` 保持在 loop 内。
# 对应功能实现文件路径: kernel_gen/passes/symbol_loop_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_loop_hoist.md
# 对应测试文件路径: test/passes/test_symbol_loop_hoist.py
def test_symbol_loop_hoist_keeps_loop_carried_symbol_add_in_loop() -> None:
    module = _make_module_for_loop_carried_symbol_add()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.blocks.first
    loop = next(op for op in block.ops if isinstance(op, SymbolForOp))

    SymbolLoopHoistPass().apply(Context(), module)

    ops = list(block.ops)
    loop_index = ops.index(loop)
    assert not any(isinstance(op, SymbolAddOp) for op in ops[:loop_index])
    assert any(isinstance(op, SymbolAddOp) for op in loop.body.blocks.first.ops)


# TC-SLH-002A
# 测试目的: 验证依赖 loop-local 生产者的 get_dim/get_stride 与 symbol 算术保持在 loop 内。
# 对应功能实现文件路径: kernel_gen/passes/symbol_loop_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_loop_hoist.md
# 对应测试文件路径: test/passes/test_symbol_loop_hoist.py
def test_symbol_loop_hoist_keeps_loop_local_symbol_inputs_in_loop() -> None:
    module = _make_module_for_loop_local_symbol_inputs()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.blocks.first
    loop = next(op for op in block.ops if isinstance(op, SymbolForOp))

    SymbolLoopHoistPass(fold=False).apply(Context(), module)

    ops = list(block.ops)
    loop_index = ops.index(loop)
    hoist_candidates = (
        SymbolGetDimOp,
        SymbolGetStrideOp,
        SymbolAddOp,
        SymbolSubOp,
        SymbolMulOp,
        SymbolDivOp,
        SymbolFloorDivOp,
    )
    assert not any(isinstance(op, hoist_candidates) for op in ops[:loop_index])
    loop_ops = list(loop.body.blocks.first.ops)
    assert [type(op) for op in loop_ops[-7:]] == [
        SymbolGetDimOp,
        SymbolGetStrideOp,
        SymbolAddOp,
        SymbolSubOp,
        SymbolMulOp,
        SymbolDivOp,
        SymbolFloorDivOp,
    ]


# TC-SLH-002B
# 测试目的: 验证依赖 loop-carried 值的 symbol 算术白名单全部保持在 loop 内。
# 对应功能实现文件路径: kernel_gen/passes/symbol_loop_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_loop_hoist.md
# 对应测试文件路径: test/passes/test_symbol_loop_hoist.py
def test_symbol_loop_hoist_keeps_loop_carried_symbol_elewise_in_loop() -> None:
    module = _make_module_for_loop_carried_symbol_elewise()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.blocks.first
    loop = next(op for op in block.ops if isinstance(op, SymbolForOp))

    SymbolLoopHoistPass(fold=False).apply(Context(), module)

    ops = list(block.ops)
    loop_index = ops.index(loop)
    symbol_ops = (SymbolAddOp, SymbolSubOp, SymbolMulOp, SymbolDivOp, SymbolFloorDivOp)
    assert not any(isinstance(op, symbol_ops) for op in ops[:loop_index])
    loop_ops = list(loop.body.blocks.first.ops)
    assert [type(op) for op in loop_ops[:5]] == [
        SymbolAddOp,
        SymbolSubOp,
        SymbolMulOp,
        SymbolDivOp,
        SymbolFloorDivOp,
    ]


# TC-SLH-007
# 测试目的: 验证 `module.verify()` 失败会被包装为固定失败短语 `SymbolLoopHoistVerifierError`。
# 对应功能实现文件路径: kernel_gen/passes/symbol_loop_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_loop_hoist.md
# 对应测试文件路径: test/passes/test_symbol_loop_hoist.py
def test_symbol_loop_hoist_verifier_errors_are_wrapped() -> None:
    module = _make_module_with_step_zero()
    with pytest.raises(KernelCodeError, match="SymbolLoopHoistVerifierError"):
        SymbolLoopHoistPass().apply(Context(), module)
