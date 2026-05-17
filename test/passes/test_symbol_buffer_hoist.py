"""symbol-buffer-hoist pass tests.


功能说明:
- 覆盖 `symbol-buffer-hoist` 的公开 pass、公开 pattern getter、registry builder 与固定失败边界。
- 只通过 `kernel_gen.passes.symbol_buffer_hoist`、`kernel_gen.passes` 与 `kernel_gen.passes.registry`
  的公开入口观察行为，不直连文件内 helper。

使用示例:
- pytest -q test/passes/test_symbol_buffer_hoist.py

关联文件:
- spec: spec/pass/symbol_buffer_hoist.md
- test: test/passes/test_symbol_buffer_hoist.py
- 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects import func, scf
from xdsl.dialects.builtin import ArrayAttr, FunctionType, ModuleOp, i32
from xdsl.ir import Block, Region, SSAValue
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import GreedyRewritePatternApplier, PatternRewriteWalker

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp, DmaDesliceOp, DmaFreeOp, DmaSliceOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import (
    SymbolConstOp,
    SymbolEqOp,
    SymbolExprAttr,
    SymbolForOp,
    SymbolIterType,
    SymbolValueType,
    SymbolYieldOp,
)

pass_module = importlib.import_module("kernel_gen.passes.symbol_buffer_hoist")
package_module = importlib.import_module("kernel_gen.passes")
registry_module = importlib.import_module("kernel_gen.passes.registry")

DmaAllocInSymbolForHoistPattern = pass_module.DmaAllocInSymbolForHoistPattern
SymbolBufferHoistPass = pass_module.SymbolBufferHoistPass
get_symbol_buffer_hoist_patterns = pass_module.get_symbol_buffer_hoist_patterns
build_registered_pass = registry_module.build_registered_pass
load_builtin_passes = registry_module.load_builtin_passes


def _memory_type(shape: tuple[int | str, ...]) -> NnMemoryType:
    """构造测试用 `nn.memory` 类型。


    功能说明:
    - 使用 `i32` 与 `global` space 构造紧致 stride memory 类型。
    - shape 支持 `int` 与符号名字符串。

    使用示例:
    - tile_type = _memory_type(("TM", "TN"))

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    strides: list[int | str] = []
    running: int | str = 1
    for dim in reversed(shape):
        strides.append(running)
        if isinstance(dim, int):
            running = running * dim if isinstance(running, int) else f"{dim}*{running}"
        elif running == 1:
            running = dim
        else:
            running = f"{dim}*{running}"
    strides.reverse()
    return NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr(str(dim)) for dim in shape]),
        ArrayAttr([SymbolExprAttr.from_expr(str(stride)) for stride in strides]),
        i32,
        NnMemorySpaceAttr.from_name("global"),
    )


def _const_symbol(value: int) -> SymbolConstOp:
    """构造测试用 `symbol.const`。


    功能说明:
    - 统一复用 `symbol.for` 边界、offset/size/stride 所需的公开 `!symbol.int` 常量。

    使用示例:
    - zero = _const_symbol(0)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    return SymbolConstOp(value)


def _build_slice_module() -> ModuleOp:
    """构造输入 staging buffer 正例 module。


    功能说明:
    - loop 内 `dma.alloc` 只作为 `dma.slice` target 使用。
    - alloc shape 完全来自 loop 外 `symbol.const`，满足外提前提。

    使用示例:
    - module = _build_slice_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    source_type = _memory_type((32, 64))
    tile_type = _memory_type((8, 16))
    zero = _const_symbol(0)
    one = _const_symbol(1)
    tm = _const_symbol(8)
    tk = _const_symbol(16)
    top_block = Block(arg_types=[source_type])
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    alloc = DmaAllocOp([tm.result, tk.result], tile_type)
    slice_op = DmaSliceOp(
        alloc.result,
        top_block.args[0],
        [zero.result, zero.result],
        [tm.result, tk.result],
        [one.result, one.result],
    )
    loop_block.add_ops([alloc, slice_op])
    loop = SymbolForOp(zero.result, one.result, one.result, loop_block)
    top_block.add_ops([zero, one, tm, tk, loop, func.ReturnOp()])
    func_op = func.FuncOp("slice_case", FunctionType.from_lists([source_type], []), Region(top_block))
    return ModuleOp([func_op])


def _build_deslice_module() -> ModuleOp:
    """构造 output scratch 正例 module。


    功能说明:
    - loop 内 `dma.alloc` 只作为 `dma.deslice` source 使用。
    - `dma.deslice` 直接 use 不视为 buffer escape。

    使用示例:
    - module = _build_deslice_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    target_type = _memory_type((32, 64))
    scratch_type = _memory_type((8, 16))
    zero = _const_symbol(0)
    one = _const_symbol(1)
    tm = _const_symbol(8)
    tn = _const_symbol(16)
    top_block = Block(arg_types=[target_type])
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    alloc = DmaAllocOp([tm.result, tn.result], scratch_type)
    deslice = DmaDesliceOp(
        top_block.args[0],
        alloc.result,
        [zero.result, zero.result],
        [tm.result, tn.result],
        [one.result, one.result],
        target_type,
    )
    loop_block.add_ops([alloc, deslice])
    loop = SymbolForOp(zero.result, one.result, one.result, loop_block)
    top_block.add_ops([zero, one, tm, tn, loop, func.ReturnOp()])
    func_op = func.FuncOp("deslice_case", FunctionType.from_lists([target_type], []), Region(top_block))
    return ModuleOp([func_op])


def _build_slice_with_free_module() -> ModuleOp:
    """构造输入 staging buffer 与匹配 free 的正例 module。


    功能说明:
    - loop 内 `dma.alloc` 先被 `dma.slice` 使用，再由同一 body 内唯一 `dma.free` 释放。
    - 该形态应把 alloc 移到 loop 前，把 free 移到 loop 后。

    使用示例:
    - module = _build_slice_with_free_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    source_type = _memory_type((32, 64))
    tile_type = _memory_type((8, 16))
    zero = _const_symbol(0)
    one = _const_symbol(1)
    tm = _const_symbol(8)
    tk = _const_symbol(16)
    top_block = Block(arg_types=[source_type])
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    alloc = DmaAllocOp([tm.result, tk.result], tile_type)
    slice_op = DmaSliceOp(
        alloc.result,
        top_block.args[0],
        [zero.result, zero.result],
        [tm.result, tk.result],
        [one.result, one.result],
    )
    free = DmaFreeOp(alloc.result)
    loop_block.add_ops([alloc, slice_op, free])
    loop = SymbolForOp(zero.result, one.result, one.result, loop_block)
    top_block.add_ops([zero, one, tm, tk, loop, func.ReturnOp()])
    func_op = func.FuncOp("slice_free_case", FunctionType.from_lists([source_type], []), Region(top_block))
    return ModuleOp([func_op])


def _build_deslice_with_free_module() -> ModuleOp:
    """构造 output scratch buffer 与匹配 free 的正例 module。


    功能说明:
    - loop 内 `dma.alloc` 作为 `dma.deslice` source 使用后再被 `dma.free` 释放。
    - 该形态应把 alloc/free 成对移出 loop，保留 deslice 在 loop 内。

    使用示例:
    - module = _build_deslice_with_free_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    target_type = _memory_type((32, 64))
    scratch_type = _memory_type((8, 16))
    zero = _const_symbol(0)
    one = _const_symbol(1)
    tm = _const_symbol(8)
    tn = _const_symbol(16)
    top_block = Block(arg_types=[target_type])
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    alloc = DmaAllocOp([tm.result, tn.result], scratch_type)
    deslice = DmaDesliceOp(
        top_block.args[0],
        alloc.result,
        [zero.result, zero.result],
        [tm.result, tn.result],
        [one.result, one.result],
        target_type,
    )
    free = DmaFreeOp(alloc.result)
    loop_block.add_ops([alloc, deslice, free])
    loop = SymbolForOp(zero.result, one.result, one.result, loop_block)
    top_block.add_ops([zero, one, tm, tn, loop, func.ReturnOp()])
    func_op = func.FuncOp("deslice_free_case", FunctionType.from_lists([target_type], []), Region(top_block))
    return ModuleOp([func_op])


def _build_slice_with_free_before_use_module() -> ModuleOp:
    """构造 free 早于 data use 的反例 module。


    功能说明:
    - loop 内 `dma.free` 早于 `dma.slice`，`symbol-buffer-hoist` 必须保持 no-op。

    使用示例:
    - module = _build_slice_with_free_before_use_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    source_type = _memory_type((32, 64))
    tile_type = _memory_type((8, 16))
    zero = _const_symbol(0)
    one = _const_symbol(1)
    tm = _const_symbol(8)
    tk = _const_symbol(16)
    top_block = Block(arg_types=[source_type])
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    alloc = DmaAllocOp([tm.result, tk.result], tile_type)
    free = DmaFreeOp(alloc.result)
    slice_op = DmaSliceOp(
        alloc.result,
        top_block.args[0],
        [zero.result, zero.result],
        [tm.result, tk.result],
        [one.result, one.result],
    )
    loop_block.add_ops([alloc, free, slice_op])
    loop = SymbolForOp(zero.result, one.result, one.result, loop_block)
    top_block.add_ops([zero, one, tm, tk, loop, func.ReturnOp()])
    func_op = func.FuncOp("free_before_use_case", FunctionType.from_lists([source_type], []), Region(top_block))
    return ModuleOp([func_op])


def _build_slice_with_multiple_free_module() -> ModuleOp:
    """构造多个 matching free 的反例 module。


    功能说明:
    - 同一 loop body 内出现两个 `dma.free` 时，pass 必须保持 no-op。

    使用示例:
    - module = _build_slice_with_multiple_free_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    module = _build_slice_with_free_module()
    _top_block, _loop_op, loop_block = _get_blocks(module)
    alloc = next(op for op in loop_block.ops if isinstance(op, DmaAllocOp))
    loop_block.add_op(DmaFreeOp(alloc.result))
    return module


def _build_slice_with_nested_free_module() -> ModuleOp:
    """构造 free 位于 nested `symbol.for` 内的反例 module。


    功能说明:
    - alloc 与 data use 在 owner loop body 内，但 matching free 位于 nested loop body。
    - 该形态不是安全成对外提，pass 必须保持 no-op。

    使用示例:
    - module = _build_slice_with_nested_free_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    source_type = _memory_type((32, 64))
    tile_type = _memory_type((8, 16))
    zero = _const_symbol(0)
    one = _const_symbol(1)
    tm = _const_symbol(8)
    tk = _const_symbol(16)
    top_block = Block(arg_types=[source_type])
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    alloc = DmaAllocOp([tm.result, tk.result], tile_type)
    slice_op = DmaSliceOp(
        alloc.result,
        top_block.args[0],
        [zero.result, zero.result],
        [tm.result, tk.result],
        [one.result, one.result],
    )
    nested_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    nested_free = DmaFreeOp(alloc.result)
    nested_block.add_op(nested_free)
    nested_loop = SymbolForOp(zero.result, one.result, one.result, nested_block)
    loop_block.add_ops([alloc, slice_op, nested_loop])
    loop = SymbolForOp(zero.result, one.result, one.result, loop_block)
    top_block.add_ops([zero, one, tm, tk, loop, func.ReturnOp()])
    func_op = func.FuncOp("nested_free_case", FunctionType.from_lists([source_type], []), Region(top_block))
    return ModuleOp([func_op])


def _build_slice_with_free_not_in_owner_loop_body_module() -> ModuleOp:
    """构造 matching free 不在 owner loop 直接 body 的反例 module。


    功能说明:
    - alloc 与 `dma.slice` data use 位于 owner loop 直接 body。
    - matching `dma.free` 位于同一 owner loop 内的 `scf.if` sibling region block，pass 必须保持 no-op。

    使用示例:
    - module = _build_slice_with_free_not_in_owner_loop_body_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    source_type = _memory_type((32, 64))
    tile_type = _memory_type((8, 16))
    zero = _const_symbol(0)
    one = _const_symbol(1)
    tm = _const_symbol(8)
    tk = _const_symbol(16)
    top_block = Block(arg_types=[source_type])
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    alloc = DmaAllocOp([tm.result, tk.result], tile_type)
    slice_op = DmaSliceOp(
        alloc.result,
        top_block.args[0],
        [zero.result, zero.result],
        [tm.result, tk.result],
        [one.result, one.result],
    )
    condition = SymbolEqOp(zero.result, one.result)
    free_block = Block()
    free = DmaFreeOp(alloc.result)
    free_block.add_ops([free, scf.YieldOp()])
    sibling_free_branch = scf.IfOp(condition.result, [], Region(free_block), None)
    loop_block.add_ops([alloc, slice_op, condition, sibling_free_branch])
    owner_loop = SymbolForOp(zero.result, one.result, one.result, loop_block)
    top_block.add_ops([zero, one, tm, tk, owner_loop, func.ReturnOp()])
    func_op = func.FuncOp("free_not_in_owner_loop_body_case", FunctionType.from_lists([source_type], []), Region(top_block))
    return ModuleOp([func_op])


def _build_unknown_direct_use_module() -> ModuleOp:
    """构造未知 direct use 的反例 module。


    功能说明:
    - loop 内 alloc 被 `dma.broadcast` 直接使用，不属于 `dma.slice target` 或 `dma.deslice source`。
    - pass 必须保持 no-op，避免把未承接副作用规则做宽。

    使用示例:
    - module = _build_unknown_direct_use_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    target_type = _memory_type((8, 16))
    zero = _const_symbol(0)
    one = _const_symbol(1)
    tm = _const_symbol(8)
    tk = _const_symbol(16)
    scalar = _const_symbol(3)
    top_block = Block()
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    alloc = DmaAllocOp([tm.result, tk.result], target_type)
    broadcast = DmaBroadcastOp(alloc.result, scalar.result)
    loop_block.add_ops([alloc, broadcast])
    loop = SymbolForOp(zero.result, one.result, one.result, loop_block)
    top_block.add_ops([zero, one, tm, tk, scalar, loop, func.ReturnOp()])
    func_op = func.FuncOp("unknown_direct_use_case", FunctionType.from_lists([], []), Region(top_block))
    return ModuleOp([func_op])


def _build_loop_carried_shape_module() -> ModuleOp:
    """构造 shape 依赖 loop-carried 的反例 module。


    功能说明:
    - alloc 第一维直接依赖 `symbol.for` 的 carried block argument。
    - 即使 direct use 属于 `dma.slice` target，pass 也必须保持 no-op。

    使用示例:
    - module = _build_loop_carried_shape_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    source_type = _memory_type((32, 64))
    tile_type = _memory_type(("ACC", 16))
    zero = _const_symbol(0)
    one = _const_symbol(1)
    init = _const_symbol(8)
    tk = _const_symbol(16)
    top_block = Block(arg_types=[source_type])
    loop_block = Block(
        arg_types=[
            SymbolIterType.from_bounds("0", "1", "1"),
            SymbolValueType.from_expr("ACC"),
        ]
    )
    alloc = DmaAllocOp([loop_block.args[1], tk.result], tile_type)
    slice_op = DmaSliceOp(
        alloc.result,
        top_block.args[0],
        [zero.result, zero.result],
        [loop_block.args[1], tk.result],
        [one.result, one.result],
    )
    loop_block.add_ops([alloc, slice_op, SymbolYieldOp(loop_block.args[1])])
    loop = SymbolForOp(
        zero.result,
        one.result,
        one.result,
        loop_block,
        init=init.result,
        result_type=SymbolValueType.from_expr("ACC"),
    )
    top_block.add_ops([zero, one, init, tk, loop, func.ReturnOp()])
    func_op = func.FuncOp("loop_carried_case", FunctionType.from_lists([source_type], []), Region(top_block))
    return ModuleOp([func_op])


def _build_invalid_verify_module() -> ModuleOp:
    """构造应触发 verifier 前缀翻译的非法 module。


    功能说明:
    - 故意构造带 loop-carried 结果但缺失 `symbol.yield` 的 `symbol.for`。
    - pass 执行完成后必须通过 `SymbolBufferHoistVerifierError:` 前缀回报 verifier 失败。

    使用示例:
    - module = _build_invalid_verify_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    source_type = _memory_type((32, 64))
    tile_type = _memory_type(("ACC", 16))
    zero = _const_symbol(0)
    one = _const_symbol(1)
    init = _const_symbol(8)
    tk = _const_symbol(16)
    top_block = Block(arg_types=[source_type])
    loop_block = Block(
        arg_types=[
            SymbolIterType.from_bounds("0", "1", "1"),
            SymbolValueType.from_expr("ACC"),
        ]
    )
    alloc = DmaAllocOp([loop_block.args[1], tk.result], tile_type)
    slice_op = DmaSliceOp(
        alloc.result,
        top_block.args[0],
        [zero.result, zero.result],
        [loop_block.args[1], tk.result],
        [one.result, one.result],
    )
    loop_block.add_ops([alloc, slice_op])
    loop = SymbolForOp(
        zero.result,
        one.result,
        one.result,
        loop_block,
        init=init.result,
        result_type=SymbolValueType.from_expr("ACC"),
    )
    top_block.add_ops([zero, one, init, tk, loop, func.ReturnOp()])
    func_op = func.FuncOp("invalid_verify_case", FunctionType.from_lists([source_type], []), Region(top_block))
    return ModuleOp([func_op])


def _get_blocks(module: ModuleOp) -> tuple[Block, SymbolForOp, Block]:
    """返回 top-level block、loop op 与 loop body block。


    功能说明:
    - 统一提取测试断言需要的块层级。

    使用示例:
    - top_block, loop_op, loop_block = _get_blocks(module)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    top_block = func_op.body.blocks[0]
    loop_op = next(op for op in top_block.ops if isinstance(op, SymbolForOp))
    return top_block, loop_op, loop_op.body.blocks[0]


def _free_source_is(free: DmaFreeOp, value: SSAValue) -> bool:
    """判断 `dma.free` 是否释放指定 SSA value。


    功能说明:
    - 使用公开 operand 读取与 SSA identity 比较辅助断言生命周期位置。

    使用示例:
    - assert _free_source_is(free, alloc.result)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    return SSAValue.get(free.source) is value


# TC-SYMBOL-BUFFER-HOIST-001
# 功能说明: 验证公开 pattern 类、公开 getter 与包根 SymbolBufferHoistPass 可达。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_public_patterns_are_reachable
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_public_patterns_are_reachable() -> None:
    patterns = get_symbol_buffer_hoist_patterns()

    assert package_module.SymbolBufferHoistPass is SymbolBufferHoistPass
    assert len(patterns) == 1
    assert isinstance(patterns[0], DmaAllocInSymbolForHoistPattern)


# TC-SYMBOL-BUFFER-HOIST-002
# 功能说明: 验证公开 pattern 直接运行时可外提 input staging buffer。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_pattern_hoists_input_staging_alloc
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_pattern_hoists_input_staging_alloc() -> None:
    module = _build_slice_module()

    PatternRewriteWalker(
        GreedyRewritePatternApplier([DmaAllocInSymbolForHoistPattern()], ctx=Context(), dce_enabled=False)
    ).rewrite_module(module)

    top_block, _loop_op, loop_block = _get_blocks(module)
    top_level_allocs = [op for op in top_block.ops if isinstance(op, DmaAllocOp)]
    loop_allocs = [op for op in loop_block.ops if isinstance(op, DmaAllocOp)]
    slice_op = next(op for op in loop_block.ops if isinstance(op, DmaSliceOp))

    assert len(top_level_allocs) == 1
    assert not loop_allocs
    assert slice_op.target is top_level_allocs[0].result


# TC-SYMBOL-BUFFER-HOIST-003
# 功能说明: 验证 SymbolBufferHoistPass 可外提 input staging buffer。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_pass_hoists_input_staging_alloc
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_pass_hoists_input_staging_alloc() -> None:
    module = _build_slice_module()

    SymbolBufferHoistPass().apply(Context(), module)

    result = module

    top_block, _loop_op, loop_block = _get_blocks(result)
    assert len([op for op in top_block.ops if isinstance(op, DmaAllocOp)]) == 1
    assert not any(isinstance(op, DmaAllocOp) for op in loop_block.ops)


# TC-SYMBOL-BUFFER-HOIST-004
# 功能说明: 验证 SymbolBufferHoistPass 可外提 output scratch buffer。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_pass_hoists_output_scratch_alloc
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_pass_hoists_output_scratch_alloc() -> None:
    module = _build_deslice_module()

    SymbolBufferHoistPass().apply(Context(), module)

    result = module

    top_block, _loop_op, loop_block = _get_blocks(result)
    top_level_alloc = next(op for op in top_block.ops if isinstance(op, DmaAllocOp))
    deslice_op = next(op for op in loop_block.ops if isinstance(op, DmaDesliceOp))

    assert deslice_op.source is top_level_alloc.result
    assert not any(isinstance(op, DmaAllocOp) for op in loop_block.ops)


# TC-SYMBOL-BUFFER-HOIST-004A
# 功能说明: 验证 input staging buffer 与同 body 内 matching free 会成对外提。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_hoists_input_staging_alloc_and_matching_free
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_hoists_input_staging_alloc_and_matching_free() -> None:
    module = _build_slice_with_free_module()

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, loop_op, loop_block = _get_blocks(module)
    top_ops = list(top_block.ops)
    top_alloc = next(op for op in top_ops if isinstance(op, DmaAllocOp))
    top_free = next(op for op in top_ops if isinstance(op, DmaFreeOp))
    slice_op = next(op for op in loop_block.ops if isinstance(op, DmaSliceOp))
    loop_index = top_ops.index(loop_op)

    assert top_ops.index(top_alloc) < loop_index
    assert top_ops.index(top_free) > loop_index
    assert _free_source_is(top_free, top_alloc.result)
    assert slice_op.target is top_alloc.result
    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in loop_block.ops)


# TC-SYMBOL-BUFFER-HOIST-004B
# 功能说明: 验证 output scratch buffer 与同 body 内 matching free 会成对外提。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_hoists_output_scratch_alloc_and_matching_free
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_hoists_output_scratch_alloc_and_matching_free() -> None:
    module = _build_deslice_with_free_module()

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, loop_op, loop_block = _get_blocks(module)
    top_ops = list(top_block.ops)
    top_alloc = next(op for op in top_ops if isinstance(op, DmaAllocOp))
    top_free = next(op for op in top_ops if isinstance(op, DmaFreeOp))
    deslice_op = next(op for op in loop_block.ops if isinstance(op, DmaDesliceOp))
    loop_index = top_ops.index(loop_op)

    assert top_ops.index(top_alloc) < loop_index
    assert top_ops.index(top_free) > loop_index
    assert _free_source_is(top_free, top_alloc.result)
    assert deslice_op.source is top_alloc.result
    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in loop_block.ops)


# TC-SYMBOL-BUFFER-HOIST-004C
# 功能说明: 验证 matching free 早于 data use 时 alloc/free 保持在 loop 内。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_keeps_alloc_when_free_precedes_data_use
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_keeps_alloc_when_free_precedes_data_use() -> None:
    module = _build_slice_with_free_before_use_module()

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, _loop_op, loop_block = _get_blocks(module)
    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in top_block.ops)
    assert len([op for op in loop_block.ops if isinstance(op, DmaAllocOp)]) == 1
    assert len([op for op in loop_block.ops if isinstance(op, DmaFreeOp)]) == 1


# TC-SYMBOL-BUFFER-HOIST-004D
# 功能说明: 验证多个 matching free 时 alloc/free 保持在 loop 内。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_keeps_alloc_when_multiple_free
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_keeps_alloc_when_multiple_free() -> None:
    module = _build_slice_with_multiple_free_module()

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, _loop_op, loop_block = _get_blocks(module)
    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in top_block.ops)
    assert len([op for op in loop_block.ops if isinstance(op, DmaAllocOp)]) == 1
    assert len([op for op in loop_block.ops if isinstance(op, DmaFreeOp)]) == 2


# TC-SYMBOL-BUFFER-HOIST-004E
# 功能说明: 验证 matching free 位于 nested loop 时 alloc/free 不外提。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_keeps_alloc_when_free_is_nested
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_keeps_alloc_when_free_is_nested() -> None:
    module = _build_slice_with_nested_free_module()

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, _loop_op, loop_block = _get_blocks(module)
    nested_loop = next(op for op in loop_block.ops if isinstance(op, SymbolForOp))
    nested_block = nested_loop.body.blocks[0]
    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in top_block.ops)
    assert len([op for op in loop_block.ops if isinstance(op, DmaAllocOp)]) == 1
    assert len([op for op in nested_block.ops if isinstance(op, DmaFreeOp)]) == 1


# TC-SYMBOL-BUFFER-HOIST-004F
# 功能说明: 验证 matching free 不在 owner loop 直接 body 时 alloc/free 不外提。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_keeps_alloc_when_free_not_in_owner_loop_body
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_keeps_alloc_when_free_not_in_owner_loop_body() -> None:
    module = _build_slice_with_free_not_in_owner_loop_body_module()

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, _loop_op, loop_block = _get_blocks(module)
    free_branch = next(op for op in loop_block.ops if isinstance(op, scf.IfOp))
    free_block = free_branch.true_region.block
    alloc = next(op for op in loop_block.ops if isinstance(op, DmaAllocOp))
    slice_op = next(op for op in loop_block.ops if isinstance(op, DmaSliceOp))
    free = next(op for op in free_block.ops if isinstance(op, DmaFreeOp))
    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in top_block.ops)
    assert slice_op.target is alloc.result
    assert not any(isinstance(op, DmaFreeOp) for op in loop_block.ops)
    assert _free_source_is(free, alloc.result)


# TC-SYMBOL-BUFFER-HOIST-004G
# 功能说明: 验证未知 direct use / alias escape 形态不被做宽外提。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_keeps_alloc_for_unknown_direct_use_or_alias_escape
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_keeps_alloc_for_unknown_direct_use_or_alias_escape() -> None:
    module = _build_unknown_direct_use_module()

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, _loop_op, loop_block = _get_blocks(module)
    assert not any(isinstance(op, DmaAllocOp) for op in top_block.ops)
    assert len([op for op in loop_block.ops if isinstance(op, DmaAllocOp)]) == 1


# TC-SYMBOL-BUFFER-HOIST-005
# 功能说明: 验证 shape 依赖 loop-carried 时 alloc 保持在 loop 内。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_keeps_loop_carried_shape_inside_loop
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_keeps_loop_carried_shape_inside_loop() -> None:
    module = _build_loop_carried_shape_module()

    SymbolBufferHoistPass().apply(Context(), module)

    result = module

    top_block, _loop_op, loop_block = _get_blocks(result)
    assert not any(isinstance(op, DmaAllocOp) for op in top_block.ops)
    assert len([op for op in loop_block.ops if isinstance(op, DmaAllocOp)]) == 1


# TC-SYMBOL-BUFFER-HOIST-006
# 功能说明: 验证非 builtin.module 输入复用共享 KernelCodeError 边界。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_rejects_non_module_input
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_rejects_non_module_input() -> None:
    with pytest.raises(KernelCodeError, match=r"^module must be builtin.module$"):
        SymbolBufferHoistPass().apply(Context(), "not-module")  # type: ignore[arg-type]


# TC-SYMBOL-BUFFER-HOIST-007
# 功能说明: 验证 verifier 失败统一转换为 SymbolBufferHoistVerifierError 前缀。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_wraps_verify_failure_prefix
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_wraps_verify_failure_prefix() -> None:
    module = _build_invalid_verify_module()

    with pytest.raises(KernelCodeError, match=r"^SymbolBufferHoistVerifierError:"):
        SymbolBufferHoistPass().apply(Context(), module)


# TC-SYMBOL-BUFFER-HOIST-008
# 功能说明: 验证 registry builder 返回 canonical module path 下的 ModulePass。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_build_registered_symbol_buffer_hoist_pass
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_build_registered_symbol_buffer_hoist_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("symbol-buffer-hoist")

    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.name == "symbol-buffer-hoist"
    assert type(pass_obj).__name__ == "SymbolBufferHoistPass"
    assert pass_obj.__class__.__module__ == "kernel_gen.passes.symbol_buffer_hoist"
