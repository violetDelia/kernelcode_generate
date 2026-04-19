"""symbol-loop-hoist pass tests.

创建者: 朽木露琪亚
最后一次更改: 小李飞刀

功能说明:
- 覆盖 `SymbolLoopHoistPass` 的外提白名单、禁止项与固定失败短语。

使用示例:
- pytest -q test/pass/test_symbol_loop_hoist.py

当前覆盖率信息:
- `kernel_gen.passes.symbol_loop_hoist`：`80%`（Stmts=133 Miss=20 Branch=70 BrPart=14；最近一次统计：2026-04-07 09:40:00 +0800）。

覆盖率命令:
- `pytest -q --cov=kernel_gen.passes.symbol_loop_hoist --cov-branch --cov-report=term-missing test/pass/test_symbol_loop_hoist.py`

关联文件:
- 功能实现: kernel_gen/passes/symbol_loop_hoist.py
- Spec 文档: spec/pass/symbol_loop_hoist.md
- 测试文件: test/pass/test_symbol_loop_hoist.py
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

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp, DmaDesliceOp, DmaFreeOp, DmaSliceOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolForOp, SymbolGetDimOp, SymbolIterType, SymbolValueType

pass_module = importlib.import_module("kernel_gen.passes.symbol_loop_hoist")
SymbolLoopHoistError = pass_module.SymbolLoopHoistError
SymbolLoopHoistPass = pass_module.SymbolLoopHoistPass
lowering_pass_module = importlib.import_module("kernel_gen.passes.lowering")


def _const_symbol_int(value: int) -> tuple[arith.ConstantOp, UnrealizedConversionCastOp, SSAValue]:
    const = arith.ConstantOp(IntegerAttr(value, i32))
    cast = UnrealizedConversionCastOp(
        operands=[const.result],
        result_types=[SymbolValueType.from_expr(str(value))],
    )
    return const, cast, cast.results[0]


def _memory_type(shape: tuple[object, ...]) -> NnMemoryType:
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


def _make_module_for_hoist_alloc() -> ModuleOp:
    mem_type = _memory_type(("M", 128))
    block = Block(arg_types=[mem_type, mem_type, mem_type])
    ops: list[object] = []
    c0, c0_cast, zero = _const_symbol_int(0)
    c1, c1_cast, one = _const_symbol_int(1)
    c128, c128_cast, one_two_eight = _const_symbol_int(128)
    ops.extend([c0, c0_cast, c1, c1_cast, c128, c128_cast])

    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    get_dim = SymbolGetDimOp(block.args[0], IntAttr(0))
    alloc_type = NnMemoryType(
        mem_type.shape,
        mem_type.stride,
        mem_type.element_type,
        NnMemorySpaceAttr.from_name("local"),
    )
    alloc = DmaAllocOp([get_dim.result, one_two_eight], alloc_type)
    loop_block.add_ops([get_dim, alloc])
    loop = SymbolForOp(zero, one, one, loop_block)
    ops.append(loop)
    ops.append(func.ReturnOp())
    block.add_ops(ops)
    func_op = func.FuncOp(
        "hoist_alloc",
        FunctionType.from_lists([mem_type, mem_type, mem_type], []),
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


def _make_module_for_fixed_read_slice() -> ModuleOp:
    mem_type = _memory_type((1, 128))
    block = Block(arg_types=[mem_type, mem_type, mem_type])
    ops: list[object] = []
    c0, c0_cast, zero = _const_symbol_int(0)
    c1, c1_cast, one = _const_symbol_int(1)
    c128, c128_cast, one_two_eight = _const_symbol_int(128)
    ops.extend([c0, c0_cast, c1, c1_cast, c128, c128_cast])

    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    bias_type = NnMemoryType(
        ArrayAttr([IntAttr(1), IntAttr(128)]),
        ArrayAttr([IntAttr(128), IntAttr(1)]),
        i32,
        NnMemorySpaceAttr.from_name("local"),
    )
    bias_alloc = DmaAllocOp([one, one_two_eight], bias_type)
    bias_slice = DmaSliceOp(
        bias_alloc.result,
        block.args[0],
        offsets=[zero, zero],
        sizes=[one, one_two_eight],
        strides=[one, one],
    )
    loop_block.add_ops([bias_alloc, bias_slice])
    loop = SymbolForOp(zero, one, one, loop_block)
    ops.append(loop)
    ops.append(func.ReturnOp())
    block.add_ops(ops)
    func_op = func.FuncOp(
        "fixed_read_slice",
        FunctionType.from_lists([mem_type, mem_type, mem_type], []),
        Region(block),
    )
    return ModuleOp([func_op])


def _make_module_with_forbidden_invariant_deslice() -> ModuleOp:
    mem_type = _memory_type((1, 128))
    block = Block(arg_types=[mem_type, mem_type, mem_type])
    ops: list[object] = []
    c0, c0_cast, zero = _const_symbol_int(0)
    c1, c1_cast, one = _const_symbol_int(1)
    c128, c128_cast, one_two_eight = _const_symbol_int(128)
    ops.extend([c0, c0_cast, c1, c1_cast, c128, c128_cast])

    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    lm_type = NnMemoryType(
        ArrayAttr([IntAttr(1), IntAttr(128)]),
        ArrayAttr([IntAttr(128), IntAttr(1)]),
        i32,
        NnMemorySpaceAttr.from_name("local"),
    )
    alloc = DmaAllocOp([one, one_two_eight], lm_type)
    deslice = DmaDesliceOp(
        alloc.result,
        block.args[0],
        offsets=[zero, zero],
        sizes=[one, one_two_eight],
        strides=[one, one],
        result_type=mem_type,
    )
    loop_block.add_ops([alloc, deslice])
    loop = SymbolForOp(zero, one, one, loop_block)
    ops.append(loop)
    ops.append(func.ReturnOp())
    block.add_ops(ops)
    func_op = func.FuncOp(
        "forbidden_deslice",
        FunctionType.from_lists([mem_type, mem_type, mem_type], []),
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


def _make_module_with_alloc_freed_in_loop() -> ModuleOp:
    mem_type = _memory_type(("M", 128))
    block = Block(arg_types=[mem_type, mem_type, mem_type])
    ops: list[object] = []
    c0, c0_cast, zero = _const_symbol_int(0)
    c1, c1_cast, one = _const_symbol_int(1)
    c128, c128_cast, one_two_eight = _const_symbol_int(128)
    ops.extend([c0, c0_cast, c1, c1_cast, c128, c128_cast])

    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    get_dim = SymbolGetDimOp(block.args[0], IntAttr(0))
    alloc_type = NnMemoryType(
        mem_type.shape,
        mem_type.stride,
        mem_type.element_type,
        NnMemorySpaceAttr.from_name("local"),
    )
    alloc = DmaAllocOp([get_dim.result, one_two_eight], alloc_type)
    free = DmaFreeOp(alloc.result)
    loop_block.add_ops([get_dim, alloc, free])
    loop = SymbolForOp(zero, one, one, loop_block)
    ops.append(loop)
    ops.append(func.ReturnOp())
    block.add_ops(ops)
    func_op = func.FuncOp(
        "alloc_freed_in_loop",
        FunctionType.from_lists([mem_type, mem_type, mem_type], []),
        Region(block),
    )
    return ModuleOp([func_op])


def _make_module_with_fixed_read_slice_target_rewritten() -> ModuleOp:
    mem_type = _memory_type((1, 128))
    block = Block(arg_types=[mem_type, mem_type, mem_type])
    ops: list[object] = []
    c0, c0_cast, zero = _const_symbol_int(0)
    c1, c1_cast, one = _const_symbol_int(1)
    c128, c128_cast, one_two_eight = _const_symbol_int(128)
    ops.extend([c0, c0_cast, c1, c1_cast, c128, c128_cast])

    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    iv = loop_block.args[0]
    bias_type = NnMemoryType(
        ArrayAttr([IntAttr(1), IntAttr(128)]),
        ArrayAttr([IntAttr(128), IntAttr(1)]),
        i32,
        NnMemorySpaceAttr.from_name("local"),
    )
    bias_alloc = DmaAllocOp([one, one_two_eight], bias_type)
    fixed_read = DmaSliceOp(
        bias_alloc.result,
        block.args[0],
        offsets=[zero, zero],
        sizes=[one, one_two_eight],
        strides=[one, one],
    )
    loop_dependent_rewrite = DmaSliceOp(
        bias_alloc.result,
        block.args[0],
        offsets=[iv, zero],
        sizes=[one, one_two_eight],
        strides=[one, one],
    )
    loop_block.add_ops([bias_alloc, fixed_read, loop_dependent_rewrite])
    loop = SymbolForOp(zero, one, one, loop_block)
    ops.append(loop)
    ops.append(func.ReturnOp())
    block.add_ops(ops)
    func_op = func.FuncOp(
        "fixed_read_source_mutated",
        FunctionType.from_lists([mem_type, mem_type, mem_type], []),
        Region(block),
    )
    return ModuleOp([func_op])


def _make_module_with_fixed_read_slice_source_mutated() -> ModuleOp:
    mem_type = _memory_type((1, 128))
    block = Block(arg_types=[mem_type, mem_type, mem_type])
    ops: list[object] = []
    c0, c0_cast, zero = _const_symbol_int(0)
    c1, c1_cast, one = _const_symbol_int(1)
    c128, c128_cast, one_two_eight = _const_symbol_int(128)
    ops.extend([c0, c0_cast, c1, c1_cast, c128, c128_cast])

    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    iv = loop_block.args[0]
    bias_type = NnMemoryType(
        ArrayAttr([IntAttr(1), IntAttr(128)]),
        ArrayAttr([IntAttr(128), IntAttr(1)]),
        i32,
        NnMemorySpaceAttr.from_name("local"),
    )
    bias_alloc = DmaAllocOp([one, one_two_eight], bias_type)
    fixed_read = DmaSliceOp(
        bias_alloc.result,
        block.args[0],
        offsets=[zero, zero],
        sizes=[one, one_two_eight],
        strides=[one, one],
    )

    # 让来源 buffer 在 loop 内被写入，但该写入依赖 loop iv，从而不会触发 invariant side-effect 的直接拒绝。
    lm_only = DmaAllocOp([one, one_two_eight], bias_type)
    writeback = DmaDesliceOp(
        lm_only.result,
        block.args[0],
        offsets=[iv, zero],
        sizes=[one, one_two_eight],
        strides=[one, one],
        result_type=mem_type,
    )
    loop_block.add_ops([bias_alloc, fixed_read, lm_only, writeback])
    loop = SymbolForOp(zero, one, one, loop_block)
    ops.append(loop)
    ops.append(func.ReturnOp())
    block.add_ops(ops)
    func_op = func.FuncOp(
        "fixed_read_result_rewritten",
        FunctionType.from_lists([mem_type, mem_type, mem_type], []),
        Region(block),
    )
    return ModuleOp([func_op])


# TC-SLH-001
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 09:10:00 +0800
# 最近一次运行成功时间: 2026-04-07 09:10:00 +0800
# 测试目的: 验证 `symbol.get_dim + dma.alloc` 可从 `symbol.for` 内外提到循环外。
# 对应功能实现文件路径: kernel_gen/passes/symbol_loop_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_loop_hoist.md
# 对应测试文件路径: test/pass/test_symbol_loop_hoist.py
def test_symbol_loop_hoist_hoists_get_dim_and_alloc() -> None:
    module = _make_module_for_hoist_alloc()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.blocks.first
    loop = next(op for op in block.ops if isinstance(op, SymbolForOp))

    SymbolLoopHoistPass().run(module)

    ops = list(block.ops)
    loop_index = ops.index(loop)
    assert any(isinstance(op, SymbolGetDimOp) for op in ops[:loop_index])
    assert any(isinstance(op, DmaAllocOp) for op in ops[:loop_index])


# TC-SLH-001A
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-20 00:00:00 +0800
# 最近一次运行成功时间: N/A
# 测试目的: 验证 loop 内的 invariant `symbol.const` 会被向上提一层到 `symbol.for` 之前。
# 对应功能实现文件路径: kernel_gen/passes/symbol_loop_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_loop_hoist.md
# 对应测试文件路径: test/pass/test_symbol_loop_hoist.py
def test_symbol_loop_hoist_hoists_symbol_const() -> None:
    module = _make_module_for_const_hoist()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.blocks.first
    loop = next(op for op in block.ops if isinstance(op, SymbolForOp))

    SymbolLoopHoistPass().run(module)

    ops = list(block.ops)
    loop_index = ops.index(loop)
    hoisted_consts = [op for op in ops[:loop_index] if isinstance(op, SymbolConstOp)]
    assert len(hoisted_consts) == 4
    assert [op.value.data for op in hoisted_consts] == [0, 1, 1, 2]


def test_symbol_loop_hoist_is_exported_from_lowering_package() -> None:
    assert lowering_pass_module.SymbolLoopHoistPass is SymbolLoopHoistPass
    assert lowering_pass_module.SymbolLoopHoistError is SymbolLoopHoistError


# TC-SLH-002
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 09:10:00 +0800
# 最近一次运行成功时间: 2026-04-07 09:10:00 +0800
# 测试目的: 验证固定窗口只读来源的 `dma.slice` 可外提，且外提后循环体内仍能使用准备好的 buffer。
# 对应功能实现文件路径: kernel_gen/passes/symbol_loop_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_loop_hoist.md
# 对应测试文件路径: test/pass/test_symbol_loop_hoist.py
def test_symbol_loop_hoist_hoists_fixed_read_slice() -> None:
    module = _make_module_for_fixed_read_slice()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.blocks.first
    loop = next(op for op in block.ops if isinstance(op, SymbolForOp))

    SymbolLoopHoistPass().run(module)

    ops = list(block.ops)
    loop_index = ops.index(loop)
    assert any(isinstance(op, DmaAllocOp) for op in ops[:loop_index])
    assert any(isinstance(op, DmaSliceOp) for op in ops[:loop_index])


# TC-SLH-003
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 09:10:00 +0800
# 最近一次运行成功时间: 2026-04-07 09:10:00 +0800
# 测试目的: 验证禁止项（`dma.deslice`）在 loop invariant 形态下会触发显式失败短语。
# 对应功能实现文件路径: kernel_gen/passes/symbol_loop_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_loop_hoist.md
# 对应测试文件路径: test/pass/test_symbol_loop_hoist.py
def test_symbol_loop_hoist_rejects_invariant_deslice() -> None:
    module = _make_module_with_forbidden_invariant_deslice()
    with pytest.raises(SymbolLoopHoistError, match="SymbolLoopHoistSideEffectOp"):
        SymbolLoopHoistPass().run(module)

# TC-SLH-004
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 09:40:00 +0800
# 最近一次运行成功时间: 2026-04-07 09:40:00 +0800
# 测试目的: 验证 `dma.alloc` 在 loop 内释放会触发固定失败短语 `SymbolLoopHoistAllocLifetimeUnsafe`。
# 对应功能实现文件路径: kernel_gen/passes/symbol_loop_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_loop_hoist.md
# 对应测试文件路径: test/pass/test_symbol_loop_hoist.py
def test_symbol_loop_hoist_rejects_alloc_freed_in_loop() -> None:
    module = _make_module_with_alloc_freed_in_loop()
    with pytest.raises(SymbolLoopHoistError, match="SymbolLoopHoistAllocLifetimeUnsafe"):
        SymbolLoopHoistPass().run(module)


# TC-SLH-005
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 09:40:00 +0800
# 最近一次运行成功时间: 2026-04-07 09:40:00 +0800
# 测试目的: 验证固定窗口 `dma.slice` 的目标 buffer 在 loop 内仍被写会触发 `SymbolLoopHoistFixedReadResultRewritten`。
# 对应功能实现文件路径: kernel_gen/passes/symbol_loop_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_loop_hoist.md
# 对应测试文件路径: test/pass/test_symbol_loop_hoist.py
def test_symbol_loop_hoist_rejects_fixed_read_slice_target_rewritten() -> None:
    module = _make_module_with_fixed_read_slice_target_rewritten()
    with pytest.raises(SymbolLoopHoistError, match="SymbolLoopHoistFixedReadResultRewritten"):
        SymbolLoopHoistPass().run(module)


# TC-SLH-006
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 09:40:00 +0800
# 最近一次运行成功时间: 2026-04-07 09:40:00 +0800
# 测试目的: 验证固定窗口 `dma.slice` 的来源在 loop 内被写会触发 `SymbolLoopHoistFixedReadSourceMutated`。
# 对应功能实现文件路径: kernel_gen/passes/symbol_loop_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_loop_hoist.md
# 对应测试文件路径: test/pass/test_symbol_loop_hoist.py
def test_symbol_loop_hoist_rejects_fixed_read_slice_source_mutated() -> None:
    module = _make_module_with_fixed_read_slice_source_mutated()
    with pytest.raises(SymbolLoopHoistError, match="SymbolLoopHoistFixedReadSourceMutated"):
        SymbolLoopHoistPass().run(module)


# TC-SLH-007
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 09:40:00 +0800
# 最近一次运行成功时间: 2026-04-07 09:40:00 +0800
# 测试目的: 验证 `module.verify()` 失败会被包装为固定失败短语 `SymbolLoopHoistVerifierError`。
# 对应功能实现文件路径: kernel_gen/passes/symbol_loop_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_loop_hoist.md
# 对应测试文件路径: test/pass/test_symbol_loop_hoist.py
def test_symbol_loop_hoist_verifier_errors_are_wrapped() -> None:
    module = _make_module_with_step_zero()
    with pytest.raises(SymbolLoopHoistError, match="SymbolLoopHoistVerifierError"):
        SymbolLoopHoistPass().run(module)
