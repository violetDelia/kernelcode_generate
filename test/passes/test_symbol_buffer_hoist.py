"""symbol-buffer-hoist pass tests.


功能说明:
- 覆盖 `symbol-buffer-hoist` 的公开 pass、公开 pattern getter、registry builder 与固定失败边界。
- 只通过 `kernel_gen.passes.hoist.symbol_buffer_hoist`、`kernel_gen.passes` 与 `kernel_gen.passes.registry`
  的公开入口观察行为，不直连文件内 helper。

使用示例:
- pytest -q test/passes/test_symbol_buffer_hoist.py

关联文件:
- spec: spec/pass/symbol_buffer_hoist.md
- test: test/passes/test_symbol_buffer_hoist.py
- 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects import func, scf
from xdsl.dialects.builtin import ArrayAttr, FunctionType, ModuleOp, i8, i32
from xdsl.ir import Attribute, Block, Region, SSAValue
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import GreedyRewritePatternApplier, PatternRewriteWalker, RewritePattern

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.dma import (
    DmaAllocOp,
    DmaBroadcastOp,
    DmaCopyOp,
    DmaDesliceOp,
    DmaFillOp,
    DmaFreeOp,
    DmaReinterpretOp,
    DmaReshapeOp,
    DmaSliceOp,
    DmaSubviewOp,
    DmaViewOp,
)
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp, KernelMatmulOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import (
    SymbolConstOp,
    SymbolEqOp,
    SymbolExprAttr,
    SymbolForOp,
    SymbolIterType,
    SymbolGetDimOp,
    SymbolGetStrideOp,
    SymbolValueType,
    SymbolYieldOp,
)

pass_module = importlib.import_module("kernel_gen.passes.hoist.symbol_buffer_hoist")
package_module = importlib.import_module("kernel_gen.passes")
registry_module = importlib.import_module("kernel_gen.passes.registry")

DmaAllocInSymbolForHoistPattern = pass_module.DmaAllocInSymbolForHoistPattern
SymbolBufferHoistPass = pass_module.SymbolBufferHoistPass
get_symbol_buffer_hoist_patterns = pass_module.get_symbol_buffer_hoist_patterns
build_registered_pass = registry_module.build_registered_pass
load_builtin_passes = registry_module.load_builtin_passes


def _memory_type(shape: tuple[int | str, ...], *, element_type: Attribute = i32, space: str = "global") -> NnMemoryType:
    """构造测试用 `nn.memory` 类型。


    功能说明:
    - 默认使用 `i32` 与 `global` space 构造紧致 stride memory 类型。
    - shape 支持 `int` 与符号名字符串；alias op 用例可指定 element type 与 memory space。

    使用示例:
    - tile_type = _memory_type(("TM", "TN"))

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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
        element_type,
        NnMemorySpaceAttr.from_name(space),
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
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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


def _build_view_with_free_module(*, loop_dependent_offset: bool = False) -> ModuleOp:
    """构造 `dma.view` alias op 外提正反例 module。


    功能说明:
    - 默认形态中 alloc/free 成对外提后，loop-invariant `dma.view` 也应单独外提一层。
    - `loop_dependent_offset=True` 时 view 的 offset 来自当前 loop iterator，view 必须保留在 loop 内。

    使用示例:
    - module = _build_view_with_free_module(loop_dependent_offset=True)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    target_type = _memory_type((16, 16))
    tile_type = _memory_type((8, 8), space="shared")
    zero = _const_symbol(0)
    one = _const_symbol(1)
    tile = _const_symbol(8)
    end = _const_symbol(16)
    top_block = Block(arg_types=[target_type])
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "16", "8")])
    alloc = DmaAllocOp([], tile_type)
    first_offset = loop_block.args[0] if loop_dependent_offset else zero.result
    view = DmaViewOp(
        alloc.result,
        [first_offset, zero.result],
        [tile.result, tile.result],
        [one.result, one.result],
        tile_type,
    )
    deslice = DmaDesliceOp(
        top_block.args[0],
        view.result,
        [loop_block.args[0], zero.result],
        [tile.result, tile.result],
        [one.result, one.result],
        target_type,
    )
    free = DmaFreeOp(alloc.result)
    loop_block.add_ops([alloc, view, deslice, free])
    loop = SymbolForOp(zero.result, end.result, tile.result, loop_block)
    top_block.add_ops([zero, one, tile, end, loop, func.ReturnOp()])
    func_op = func.FuncOp("view_free_case", FunctionType.from_lists([target_type], []), Region(top_block))
    return ModuleOp([func_op])


def _build_reinterpret_with_free_module() -> ModuleOp:
    """构造 `dma.reinterpret` alias op 外提正例 module。


    功能说明:
    - alloc/free 成对外提后，loop-invariant `dma.reinterpret` 也应单独外提一层。
    - 该用例锁定 reinterpret 被视为无副作用 alias source use。

    使用示例:
    - module = _build_reinterpret_with_free_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    target_type = _memory_type((16, 16))
    tile_type = _memory_type((8, 8), space="shared")
    zero = _const_symbol(0)
    one = _const_symbol(1)
    tile = _const_symbol(8)
    end = _const_symbol(16)
    top_block = Block(arg_types=[target_type])
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "16", "8")])
    alloc = DmaAllocOp([], tile_type)
    reinterpret = DmaReinterpretOp(
        alloc.result,
        zero.result,
        [tile.result, tile.result],
        [tile.result, one.result],
        tile_type,
    )
    deslice = DmaDesliceOp(
        top_block.args[0],
        reinterpret.result,
        [loop_block.args[0], zero.result],
        [tile.result, tile.result],
        [one.result, one.result],
        target_type,
    )
    free = DmaFreeOp(alloc.result)
    loop_block.add_ops([alloc, reinterpret, deslice, free])
    loop = SymbolForOp(zero.result, end.result, tile.result, loop_block)
    top_block.add_ops([zero, one, tile, end, loop, func.ReturnOp()])
    func_op = func.FuncOp("reinterpret_free_case", FunctionType.from_lists([target_type], []), Region(top_block))
    return ModuleOp([func_op])


def _build_reshape_with_free_module(*, loop_dependent_shape: bool = False) -> ModuleOp:
    """构造 `dma.reshape` alias op 外提正反例 module。


    功能说明:
    - 默认形态中 alloc/free 成对外提后，loop-invariant `dma.reshape` 也应单独外提一层。
    - `loop_dependent_shape=True` 时 shape 来自当前 loop-carried 值，reshape 必须保留在 loop 内。

    使用示例:
    - module = _build_reshape_with_free_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    target_type = _memory_type((16,))
    tile_type = _memory_type((4, 4), space="shared")
    flat_type = _memory_type((16,), space="shared")
    zero = _const_symbol(0)
    one = _const_symbol(1)
    four = _const_symbol(4)
    sixteen = _const_symbol(16)
    top_block = Block(arg_types=[target_type])
    if loop_dependent_shape:
        loop_block = Block(
            arg_types=[
                SymbolIterType.from_bounds("0", "16", "16"),
                SymbolValueType.from_expr("16"),
            ]
        )
        shape_operand = loop_block.args[1]
        loop = SymbolForOp(
            zero.result,
            sixteen.result,
            sixteen.result,
            loop_block,
            init=sixteen.result,
            result_type=SymbolValueType.from_expr("16"),
        )
    else:
        loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "16", "16")])
        shape_operand = sixteen.result
        loop = SymbolForOp(zero.result, sixteen.result, sixteen.result, loop_block)
    alloc = DmaAllocOp([], tile_type)
    reshape = DmaReshapeOp(alloc.result, [shape_operand], flat_type)
    deslice = DmaDesliceOp(
        top_block.args[0],
        reshape.result,
        [loop_block.args[0]],
        [sixteen.result],
        [one.result],
        target_type,
    )
    free = DmaFreeOp(alloc.result)
    loop_block.add_ops([alloc, reshape, deslice, free])
    if loop_dependent_shape:
        loop_block.add_op(SymbolYieldOp(loop_block.args[1]))
    top_block.add_ops([zero, one, four, sixteen, loop, func.ReturnOp()])
    func_op = func.FuncOp("reshape_free_case", FunctionType.from_lists([target_type], []), Region(top_block))
    return ModuleOp([func_op])


def _build_subview_with_free_module(*, loop_dependent_size: bool = False) -> ModuleOp:
    """构造 `dma.subview` alias op 外提正反例 module。


    功能说明:
    - 默认形态中 alloc/free 成对外提后，loop-invariant `dma.subview` 也应单独外提一层。
    - `loop_dependent_size=True` 时 size 来自当前 loop-carried 值，subview 必须保留在 loop 内。

    使用示例:
    - module = _build_subview_with_free_module(loop_dependent_size=True)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    target_type = _memory_type((16,))
    pool_type = _memory_type((1024,), element_type=i8, space="shared")
    tile_type = _memory_type((16,), space="shared")
    zero = _const_symbol(0)
    one = _const_symbol(1)
    sixteen = _const_symbol(16)
    pool_size = _const_symbol(1024)
    top_block = Block(arg_types=[target_type])
    if loop_dependent_size:
        loop_block = Block(
            arg_types=[
                SymbolIterType.from_bounds("0", "16", "16"),
                SymbolValueType.from_expr("16"),
            ]
        )
        size_operand = loop_block.args[1]
        loop = SymbolForOp(
            zero.result,
            sixteen.result,
            sixteen.result,
            loop_block,
            init=sixteen.result,
            result_type=SymbolValueType.from_expr("16"),
        )
    else:
        loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "16", "16")])
        size_operand = sixteen.result
        loop = SymbolForOp(zero.result, sixteen.result, sixteen.result, loop_block)
    alloc = DmaAllocOp([], pool_type)
    subview = DmaSubviewOp(alloc.result, zero.result, size_operand, one.result, tile_type)
    deslice = DmaDesliceOp(
        top_block.args[0],
        subview.result,
        [loop_block.args[0]],
        [sixteen.result],
        [one.result],
        target_type,
    )
    free = DmaFreeOp(alloc.result)
    loop_block.add_ops([alloc, subview, deslice, free])
    if loop_dependent_size:
        loop_block.add_op(SymbolYieldOp(loop_block.args[1]))
    top_block.add_ops([zero, one, sixteen, pool_size, loop, func.ReturnOp()])
    func_op = func.FuncOp("subview_free_case", FunctionType.from_lists([target_type], []), Region(top_block))
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
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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


def _build_same_value_broadcast_module() -> ModuleOp:
    """构造 same-value broadcast 反例 module。


    功能说明:
    - loop 内 alloc result 同时作为 `dma.broadcast` 的 target 与 source。
    - pass 必须保持 no-op，避免把同值 `READ+WRITE` 做成自证 reset/write。

    使用示例:
    - module = _build_same_value_broadcast_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    target_type = _memory_type((8, 16))
    zero = _const_symbol(0)
    one = _const_symbol(1)
    tm = _const_symbol(8)
    tk = _const_symbol(16)
    top_block = Block()
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    alloc = DmaAllocOp([tm.result, tk.result], target_type)
    broadcast = DmaBroadcastOp(alloc.result, alloc.result)
    loop_block.add_ops([alloc, broadcast])
    loop = SymbolForOp(zero.result, one.result, one.result, loop_block)
    top_block.add_ops([zero, one, tm, tk, loop, func.ReturnOp()])
    func_op = func.FuncOp("same_value_broadcast_case", FunctionType.from_lists([], []), Region(top_block))
    return ModuleOp([func_op])


def _build_broadcast_lifecycle_module(*, same_value: bool = False, with_kernel_read: bool = False) -> ModuleOp:
    """构造 broadcast 生命周期证明 module。


    功能说明:
    - broadcast target 绑定 loop 内 alloc result。
    - `same_value=True` 时，source 与 target 取同一 alloc result，覆盖 `READ+WRITE` 自证 no-op 反例。
    - `with_kernel_read=True` 时，后续再挂一个公开 `kernel.*` read，覆盖 broadcast reset 正例。

    使用示例:
    - module = _build_broadcast_lifecycle_module(with_kernel_read=True)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    tile_type = _memory_type((4, 4))
    zero = _const_symbol(0)
    one = _const_symbol(1)
    scalar = _const_symbol(3)
    top_block = Block(arg_types=[tile_type])
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    alloc = DmaAllocOp([], tile_type)
    broadcast_source = alloc.result if same_value else scalar.result
    broadcast = DmaBroadcastOp(alloc.result, broadcast_source)
    loop_ops: list = [alloc, broadcast]
    if with_kernel_read:
        kernel_use = KernelBinaryElewiseOp(
            top_block.args[0],
            alloc.result,
            top_block.args[0],
            kind="add",
            space=NnMemorySpaceAttr.from_name("global"),
        )
        loop_ops.append(kernel_use)
    loop_ops.append(DmaFreeOp(alloc.result))
    loop_block.add_ops(loop_ops)
    loop = SymbolForOp(zero.result, one.result, one.result, loop_block)
    top_block.add_ops([zero, one, scalar, loop, func.ReturnOp()])
    func_op = func.FuncOp("broadcast_lifecycle_case", FunctionType.from_lists([tile_type], []), Region(top_block))
    return ModuleOp([func_op])


def _build_metadata_query_module(*, include_data_use: bool) -> ModuleOp:
    """构造 Pure metadata query 的阻断/非阻断 module。


    功能说明:
    - alloc result 先被 `symbol.get_dim` / `symbol.get_stride` 读取 shape / stride 元信息。
    - `include_data_use=True` 时再追加一个可证明的 `dma.slice` data use，验证 metadata query 不阻断 hoist。
    - `include_data_use=False` 时只保留 metadata query 与 `dma.free`，验证 metadata query 不能单独证明 reset/write。

    使用示例:
    - module = _build_metadata_query_module(include_data_use=True)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    source_type = _memory_type((32, 64))
    tile_type = _memory_type(("TM", "TK"))
    zero = _const_symbol(0)
    one = _const_symbol(1)
    top_block = Block(arg_types=[source_type, SymbolValueType.from_expr("TM"), SymbolValueType.from_expr("TK")])
    tm = top_block.args[1]
    tk = top_block.args[2]
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    alloc = DmaAllocOp([tm, tk], tile_type)
    get_dim = SymbolGetDimOp(alloc.result, 0)
    get_stride = SymbolGetStrideOp(alloc.result, 0)
    loop_ops: list = [alloc, get_dim, get_stride]
    if include_data_use:
        loop_ops.append(
            DmaSliceOp(
                alloc.result,
                top_block.args[0],
                [zero.result, zero.result],
                [tm, tk],
                [one.result, one.result],
            )
        )
    loop_ops.append(DmaFreeOp(alloc.result))
    loop_block.add_ops(loop_ops)
    loop = SymbolForOp(zero.result, one.result, one.result, loop_block)
    top_block.add_ops([zero, one, loop, func.ReturnOp()])
    func_op = func.FuncOp(
        "metadata_query_case",
        FunctionType.from_lists([source_type, SymbolValueType.from_expr("TM"), SymbolValueType.from_expr("TK")], []),
        Region(top_block),
    )
    return ModuleOp([func_op])


def _build_conditional_write_module(*, read_in_branch: bool) -> ModuleOp:
    """构造 `scf.if` conditional write / merge read 的 effect-first module。


    功能说明:
    - `read_in_branch=True` 时，write 与 read 位于同一个 `scf.if` 分支 block，证明可继续外提。
    - `read_in_branch=False` 时，write 在分支内而 read 在 merge 点，验证 merge read 不能被分支写证明。

    使用示例:
    - module = _build_conditional_write_module(read_in_branch=True)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    tile_type = _memory_type((4, 4))
    zero = _const_symbol(0)
    one = _const_symbol(1)
    top_block = Block(arg_types=[tile_type])
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    alloc = DmaAllocOp([], tile_type)
    condition = SymbolEqOp(zero.result, zero.result)
    true_block = Block()
    fill = DmaFillOp(alloc.result, zero.result)
    true_block.add_op(fill)
    if read_in_branch:
        branch_read = KernelBinaryElewiseOp(
            top_block.args[0],
            alloc.result,
            top_block.args[0],
            kind="add",
            space=NnMemorySpaceAttr.from_name("global"),
        )
        true_block.add_op(branch_read)
    true_block.add_op(scf.YieldOp())
    conditional = scf.IfOp(condition.result, [], Region(true_block), None)
    loop_ops = [alloc, condition, conditional]
    if not read_in_branch:
        loop_ops.append(
            KernelBinaryElewiseOp(
                top_block.args[0],
                alloc.result,
                top_block.args[0],
                kind="add",
                space=NnMemorySpaceAttr.from_name("global"),
            )
        )
    loop_ops.append(DmaFreeOp(alloc.result))
    loop_block.add_ops(loop_ops)
    loop = SymbolForOp(zero.result, one.result, one.result, loop_block)
    top_block.add_ops([zero, one, loop, func.ReturnOp()])
    func_op = func.FuncOp("conditional_write_case", FunctionType.from_lists([tile_type], []), Region(top_block))
    return ModuleOp([func_op])


def _build_alias_result_kernel_use_module() -> ModuleOp:
    """构造 alias result 流向 kernel op 的 no-op 反例 module。


    功能说明:
    - loop 内 `dma.alloc` 先经 `dma.reshape` 生成 alias result，再由 `kernel.binary_elewise` 直接使用。
    - `kernel.*` 不属于 alias result 白名单，pass 必须保持 alloc、alias op 与 free 原位。

    使用示例:
    - module = _build_alias_result_kernel_use_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    tile_type = _memory_type((4, 4))
    flat_type = _memory_type((16,))
    zero = _const_symbol(0)
    one = _const_symbol(1)
    sixteen = _const_symbol(16)
    top_block = Block()
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    alloc = DmaAllocOp([], tile_type)
    reshape = DmaReshapeOp(alloc.result, [sixteen.result], flat_type)
    kernel_use = KernelBinaryElewiseOp(
        reshape.result,
        reshape.result,
        reshape.result,
        kind="add",
        space=NnMemorySpaceAttr.from_name("global"),
    )
    free = DmaFreeOp(alloc.result)
    loop_block.add_ops([alloc, reshape, kernel_use, free])
    loop = SymbolForOp(zero.result, one.result, one.result, loop_block)
    top_block.add_ops([zero, one, sixteen, loop, func.ReturnOp()])
    func_op = func.FuncOp("alias_result_kernel_use_case", FunctionType.from_lists([], []), Region(top_block))
    return ModuleOp([func_op])


def _build_kernel_lifecycle_reset_module() -> ModuleOp:
    """构造 kernel read/write 由 fill reset 支配的正例 module。


    功能说明:
    - loop 内 alloc 先被 `dma.fill` 写入，再被 `kernel.binary_elewise` 同时读写。
    - `MemoryEffect` 证明首次 read 前已有 reset/write，因此 alloc/free 可成对外提。

    使用示例:
    - module = _build_kernel_lifecycle_reset_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    tile_type = _memory_type((4, 4))
    zero = _const_symbol(0)
    one = _const_symbol(1)
    top_block = Block(arg_types=[tile_type])
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    alloc = DmaAllocOp([], tile_type)
    fill = DmaFillOp(alloc.result, zero.result)
    kernel_use = KernelBinaryElewiseOp(
        alloc.result,
        alloc.result,
        top_block.args[0],
        kind="add",
        space=NnMemorySpaceAttr.from_name("global"),
    )
    free = DmaFreeOp(alloc.result)
    loop_block.add_ops([alloc, fill, kernel_use, free])
    loop = SymbolForOp(zero.result, one.result, one.result, loop_block)
    top_block.add_ops([zero, one, loop, func.ReturnOp()])
    func_op = func.FuncOp("kernel_lifecycle_reset_case", FunctionType.from_lists([tile_type], []), Region(top_block))
    return ModuleOp([func_op])


def build_copy_cross_space_full_write_module() -> ModuleOp:
    """构造 dma.copy 跨 memory space 完整写入的正例 module。


    功能说明:
    - `dma.copy(target=alloc, source=arg)` 的 source/target shape、stride、dtype 相同但 memory space 不同。
    - copy 后的 `kernel.binary_elewise` 读取 alloc，应由 copy target WRITE 证明 alloc root 已完整 reset。

    使用示例:
    - module = build_copy_cross_space_full_write_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    source_type = _memory_type((4, 4), space="tsm")
    tile_type = _memory_type((4, 4), space="tlm1")
    zero = _const_symbol(0)
    one = _const_symbol(1)
    top_block = Block(arg_types=[source_type, tile_type, tile_type])
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    alloc = DmaAllocOp([], tile_type)
    copy = DmaCopyOp(alloc.result, top_block.args[0])
    kernel_use = KernelBinaryElewiseOp(
        top_block.args[1],
        alloc.result,
        top_block.args[2],
        kind="add",
        space=NnMemorySpaceAttr.from_name("tlm1"),
    )
    free = DmaFreeOp(alloc.result)
    loop_block.add_ops([alloc, copy, kernel_use, free])
    loop = SymbolForOp(zero.result, one.result, one.result, loop_block)
    top_block.add_ops([zero, one, loop, func.ReturnOp()])
    func_op = func.FuncOp(
        "copy_cross_space_full_write_case",
        FunctionType.from_lists([source_type, tile_type, tile_type], []),
        Region(top_block),
    )
    return ModuleOp([func_op])


def _build_kernel_lifecycle_read_before_write_module() -> ModuleOp:
    """构造 kernel read 早于 reset/write 的反例 module。


    功能说明:
    - loop 内 alloc 首次 use 是 `kernel.binary_elewise` 的 input read，后续才被 `dma.fill` 写入。
    - `symbol-buffer-hoist` 必须保持 alloc/free 原位。

    使用示例:
    - module = _build_kernel_lifecycle_read_before_write_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    tile_type = _memory_type((4, 4))
    zero = _const_symbol(0)
    one = _const_symbol(1)
    top_block = Block(arg_types=[tile_type, tile_type])
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    alloc = DmaAllocOp([], tile_type)
    kernel_use = KernelBinaryElewiseOp(
        top_block.args[1],
        alloc.result,
        top_block.args[0],
        kind="add",
        space=NnMemorySpaceAttr.from_name("global"),
    )
    fill = DmaFillOp(alloc.result, zero.result)
    free = DmaFreeOp(alloc.result)
    loop_block.add_ops([alloc, kernel_use, fill, free])
    loop = SymbolForOp(zero.result, one.result, one.result, loop_block)
    top_block.add_ops([zero, one, loop, func.ReturnOp()])
    func_op = func.FuncOp(
        "kernel_lifecycle_read_before_write_case",
        FunctionType.from_lists([tile_type, tile_type], []),
        Region(top_block),
    )
    return ModuleOp([func_op])


def _build_unknown_call_use_module() -> ModuleOp:
    """构造 alloc result 逃逸到未知 call 的反例 module。


    功能说明:
    - loop 内 alloc 先被 `dma.fill` reset，再作为 `func.call` operand 传出。
    - `func.call` 没有本 pass 可判定的公开 MemoryEffect，必须阻止 alloc/free 外提。

    使用示例:
    - module = _build_unknown_call_use_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    tile_type = _memory_type((4, 4))
    zero = _const_symbol(0)
    one = _const_symbol(1)
    top_block = Block(arg_types=[])
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    alloc = DmaAllocOp([], tile_type)
    fill = DmaFillOp(alloc.result, zero.result)
    call = func.CallOp("consume", [alloc.result], [])
    free = DmaFreeOp(alloc.result)
    loop_block.add_ops([alloc, fill, call, free])
    loop = SymbolForOp(zero.result, one.result, one.result, loop_block)
    top_block.add_ops([zero, one, loop, func.ReturnOp()])
    func_op = func.FuncOp("unknown_call_use_case", FunctionType.from_lists([], []), Region(top_block))
    consume_block = Block(arg_types=[tile_type])
    consume_block.add_op(func.ReturnOp())
    consume_op = func.FuncOp("consume", FunctionType.from_lists([tile_type], []), Region(consume_block))
    return ModuleOp([func_op, consume_op])


def _build_nested_alias_kernel_use_module() -> ModuleOp:
    """构造 nested loop 内 alias result 流向 kernel op 的正例 module。


    功能说明:
    - `dma.reshape` 的 source 与 shape 都支配 outer loop。
    - result 只在 nested loop 内被带公开 MemoryEffect 的 `kernel.matmul` 使用。
    - fixed-point rewrite 应把 reshape 逐层外提到 outer loop 前。

    使用示例:
    - module = _build_nested_alias_kernel_use_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    matrix_type = _memory_type((4, 4))
    zero = _const_symbol(0)
    one = _const_symbol(1)
    four = _const_symbol(4)
    top_block = Block(arg_types=[matrix_type, matrix_type, matrix_type])
    outer_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    inner_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    reshape = DmaReshapeOp(top_block.args[0], [four.result, four.result], matrix_type)
    matmul = KernelMatmulOp(
        top_block.args[2],
        reshape.result,
        top_block.args[1],
        NnMemorySpaceAttr.from_name("global"),
    )
    inner_block.add_ops([reshape, matmul])
    inner_loop = SymbolForOp(zero.result, one.result, one.result, inner_block)
    outer_block.add_op(inner_loop)
    outer_loop = SymbolForOp(zero.result, one.result, one.result, outer_block)
    top_block.add_ops([zero, one, four, outer_loop, func.ReturnOp()])
    func_op = func.FuncOp(
        "nested_alias_kernel_use_case",
        FunctionType.from_lists([matrix_type, matrix_type, matrix_type], []),
        Region(top_block),
    )
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
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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


def _build_fixed_point_alloc_free_fill_module(*, dynamic_shape: bool) -> ModuleOp:
    """构造 nested alloc/free fixed-point 外提正例 module。


    功能说明:
    - alloc/free 位于三层 `symbol.for` 最内层，`dma.fill` 对完整 alloc root 写入。
    - `dynamic_shape=True` 时 alloc shape 来自函数参数，验证动态 shape 也能逐层外提。

    使用示例:
    - module = _build_fixed_point_alloc_free_fill_module(dynamic_shape=True)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    zero = _const_symbol(0)
    one = _const_symbol(1)
    four = _const_symbol(4)
    if dynamic_shape:
        tile_type = _memory_type(("M", "N"))
        input_types = [SymbolValueType.from_expr("M"), SymbolValueType.from_expr("N")]
        top_block = Block(arg_types=input_types)
        dynamic_shape_operands = [top_block.args[0], top_block.args[1]]
    else:
        tile_type = _memory_type((4, 4))
        input_types = []
        top_block = Block()
        dynamic_shape_operands = []

    outer_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    middle_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    inner_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    alloc = DmaAllocOp(dynamic_shape_operands, tile_type)
    fill = DmaFillOp(alloc.result, zero.result)
    free = DmaFreeOp(alloc.result)
    inner_block.add_ops([alloc, fill, free])
    inner_loop = SymbolForOp(zero.result, one.result, one.result, inner_block)
    middle_block.add_op(inner_loop)
    middle_loop = SymbolForOp(zero.result, one.result, one.result, middle_block)
    outer_block.add_op(middle_loop)
    outer_loop = SymbolForOp(zero.result, one.result, one.result, outer_block)
    top_block.add_ops([zero, one, four, outer_loop, func.ReturnOp()])
    func_op = func.FuncOp("fixed_point_alloc_free_fill_case", FunctionType.from_lists(input_types, []), Region(top_block))
    return ModuleOp([func_op])


def _build_dynamic_matmul_loop_local_scratch_module() -> ModuleOp:
    """构造动态 matmul loop-local scratch 外提正例 module。


    功能说明:
    - 模拟动态 matmul 的 outer M/N/K 三层 loop，acc/tmp/lhs/rhs scratch 的 shape 均来自函数级 tile symbol。
    - acc/tmp 位于 N loop body，lhs/rhs 位于 K loop body，均带同一 owner block 内唯一 matching `dma.free`。
    - `dma.fill`、`kernel.matmul` 与 `kernel.binary_elewise` 保留在原循环语义位置，用于验证只移动 alloc/free 生命周期边界。

    使用示例:
    - module = _build_dynamic_matmul_loop_local_scratch_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    symbol_types = [
        SymbolValueType.from_expr("TM"),
        SymbolValueType.from_expr("TN"),
        SymbolValueType.from_expr("TK"),
        SymbolValueType.from_expr("M"),
        SymbolValueType.from_expr("N"),
        SymbolValueType.from_expr("K"),
    ]
    acc_type = NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr("TM"), SymbolExprAttr.from_expr("TN")]),
        ArrayAttr([SymbolExprAttr.from_expr("TN"), SymbolExprAttr.from_expr("1")]),
        i32,
        NnMemorySpaceAttr.from_name("tsm"),
    )
    lhs_type = NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr("TM"), SymbolExprAttr.from_expr("TK")]),
        ArrayAttr([SymbolExprAttr.from_expr("TK"), SymbolExprAttr.from_expr("1")]),
        i32,
        NnMemorySpaceAttr.from_name("tsm"),
    )
    rhs_type = NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr("TK"), SymbolExprAttr.from_expr("TN")]),
        ArrayAttr([SymbolExprAttr.from_expr("TN"), SymbolExprAttr.from_expr("1")]),
        i32,
        NnMemorySpaceAttr.from_name("tsm"),
    )
    zero = SymbolConstOp(0)
    top_block = Block(arg_types=symbol_types)
    tm, tn, tk, m, n, k = top_block.args
    outer_block = Block(arg_types=[SymbolIterType.from_bounds("0", "M", "TM")])
    middle_block = Block(arg_types=[SymbolIterType.from_bounds("0", "N", "TN")])
    inner_block = Block(arg_types=[SymbolIterType.from_bounds("0", "K", "TK")])
    acc = DmaAllocOp([tm, tn], acc_type)
    tmp = DmaAllocOp([tm, tn], acc_type)
    acc_fill = DmaFillOp(acc.result, zero.result)
    lhs = DmaAllocOp([tm, tk], lhs_type)
    rhs = DmaAllocOp([tk, tn], rhs_type)
    lhs_fill = DmaFillOp(lhs.result, zero.result)
    rhs_fill = DmaFillOp(rhs.result, zero.result)
    matmul = KernelMatmulOp(tmp.result, lhs.result, rhs.result, NnMemorySpaceAttr.from_name("tsm"))
    accumulate = KernelBinaryElewiseOp(
        acc.result,
        acc.result,
        tmp.result,
        kind="add",
        space=NnMemorySpaceAttr.from_name("tsm"),
    )
    lhs_free = DmaFreeOp(lhs.result)
    rhs_free = DmaFreeOp(rhs.result)
    tmp_free = DmaFreeOp(tmp.result)
    acc_free = DmaFreeOp(acc.result)
    inner_block.add_ops([lhs, rhs, lhs_fill, rhs_fill, matmul, accumulate, rhs_free, lhs_free])
    inner_loop = SymbolForOp(zero.result, k, tk, inner_block)
    middle_block.add_ops([acc, tmp, acc_fill, inner_loop, tmp_free, acc_free])
    middle_loop = SymbolForOp(zero.result, n, tn, middle_block)
    outer_block.add_op(middle_loop)
    outer_loop = SymbolForOp(zero.result, m, tm, outer_block)
    top_block.add_ops([zero, outer_loop, func.ReturnOp()])
    func_op = func.FuncOp("dynamic_matmul_scratch_case", FunctionType.from_lists(symbol_types, []), Region(top_block))
    return ModuleOp([func_op])


def _build_nested_acc_fill_before_read_module() -> ModuleOp:
    """构造 owner block fill 支配 nested kernel read 的 acc buffer 正例。


    功能说明:
    - owner loop 内 alloc 先被 `dma.fill` 完整 reset，再进入 nested loop 被 kernel read/write。
    - matching free 位于 owner loop body 末尾，应允许 alloc/free 外提到 owner loop 外。

    使用示例:
    - module = _build_nested_acc_fill_before_read_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    tile_type = _memory_type((4, 4))
    zero = _const_symbol(0)
    one = _const_symbol(1)
    top_block = Block(arg_types=[tile_type])
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    inner_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    alloc = DmaAllocOp([], tile_type)
    fill = DmaFillOp(alloc.result, zero.result)
    kernel_use = KernelBinaryElewiseOp(
        alloc.result,
        alloc.result,
        top_block.args[0],
        kind="add",
        space=NnMemorySpaceAttr.from_name("global"),
    )
    inner_block.add_op(kernel_use)
    inner_loop = SymbolForOp(zero.result, one.result, one.result, inner_block)
    free = DmaFreeOp(alloc.result)
    loop_block.add_ops([alloc, fill, inner_loop, free])
    loop = SymbolForOp(zero.result, one.result, one.result, loop_block)
    top_block.add_ops([zero, one, loop, func.ReturnOp()])
    func_op = func.FuncOp("nested_acc_fill_before_read_case", FunctionType.from_lists([tile_type], []), Region(top_block))
    return ModuleOp([func_op])


def _build_nested_deslice_source_module(*, with_reset: bool) -> ModuleOp:
    """构造 nested `dma.deslice source` 生命周期正反例。


    功能说明:
    - `with_reset=False` 时 nested `dma.deslice` 直接读取 alloc，缺少 full reset/write，必须 no-op。
    - `with_reset=True` 时 owner block 内 `dma.fill` 支配 nested deslice READ，alloc/free 可外提。

    使用示例:
    - module = _build_nested_deslice_source_module(with_reset=True)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    tile_type = _memory_type((4, 4))
    zero = _const_symbol(0)
    one = _const_symbol(1)
    four = _const_symbol(4)
    top_block = Block(arg_types=[tile_type])
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    inner_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    alloc = DmaAllocOp([], tile_type)
    fill = DmaFillOp(alloc.result, zero.result)
    deslice = DmaDesliceOp(
        top_block.args[0],
        alloc.result,
        [zero.result, zero.result],
        [four.result, four.result],
        [one.result, one.result],
        tile_type,
    )
    inner_block.add_op(deslice)
    inner_loop = SymbolForOp(zero.result, one.result, one.result, inner_block)
    free = DmaFreeOp(alloc.result)
    if with_reset:
        loop_block.add_ops([alloc, fill, inner_loop, free])
    else:
        loop_block.add_ops([alloc, inner_loop, free])
    loop = SymbolForOp(zero.result, one.result, one.result, loop_block)
    top_block.add_ops([zero, one, four, loop, func.ReturnOp()])
    func_op = func.FuncOp("nested_deslice_source_case", FunctionType.from_lists([tile_type], []), Region(top_block))
    return ModuleOp([func_op])


def _build_nested_write_may_not_run_module() -> ModuleOp:
    """构造 nested loop write 可能不执行但后续 read 的反例 module。


    功能说明:
    - nested loop end 为 0，`dma.fill` 不支配 owner loop body 内后续 kernel read。
    - `symbol-buffer-hoist` 必须保持 alloc/free 原位，避免跨迭代共享未初始化 scratch。

    使用示例:
    - module = _build_nested_write_may_not_run_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    tile_type = _memory_type((4, 4))
    zero = _const_symbol(0)
    one = _const_symbol(1)
    top_block = Block(arg_types=[tile_type])
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    inner_block = Block(arg_types=[SymbolIterType.from_bounds("0", "0", "1")])
    alloc = DmaAllocOp([], tile_type)
    fill = DmaFillOp(alloc.result, zero.result)
    inner_block.add_op(fill)
    inner_loop = SymbolForOp(zero.result, zero.result, one.result, inner_block)
    kernel_use = KernelBinaryElewiseOp(
        top_block.args[0],
        alloc.result,
        top_block.args[0],
        kind="add",
        space=NnMemorySpaceAttr.from_name("global"),
    )
    free = DmaFreeOp(alloc.result)
    loop_block.add_ops([alloc, inner_loop, kernel_use, free])
    loop = SymbolForOp(zero.result, one.result, one.result, loop_block)
    top_block.add_ops([zero, one, loop, func.ReturnOp()])
    func_op = func.FuncOp("nested_write_may_not_run_case", FunctionType.from_lists([tile_type], []), Region(top_block))
    return ModuleOp([func_op])


def _build_partial_subview_write_before_root_read_module() -> ModuleOp:
    """构造 partial alias write 后 root read 的反例 module。


    功能说明:
    - `dma.subview` 只覆盖 byte pool 的局部 typed view。
    - 后续 `dma.copy` 读取完整 root pool，partial write 不能证明 root 已完整 reset。

    使用示例:
    - module = _build_partial_subview_write_before_root_read_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    pool_type = _memory_type((1024,), element_type=i8, space="shared")
    tile_type = _memory_type((16,), space="shared")
    zero = _const_symbol(0)
    one = _const_symbol(1)
    sixteen = _const_symbol(16)
    top_block = Block(arg_types=[pool_type])
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    alloc = DmaAllocOp([], pool_type)
    subview = DmaSubviewOp(alloc.result, zero.result, sixteen.result, one.result, tile_type)
    fill = DmaFillOp(subview.result, zero.result)
    copy = DmaCopyOp(top_block.args[0], alloc.result)
    free = DmaFreeOp(alloc.result)
    loop_block.add_ops([alloc, subview, fill, copy, free])
    loop = SymbolForOp(zero.result, one.result, one.result, loop_block)
    top_block.add_ops([zero, one, sixteen, loop, func.ReturnOp()])
    func_op = func.FuncOp("partial_subview_write_before_root_read_case", FunctionType.from_lists([pool_type], []), Region(top_block))
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
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    return SSAValue.get(free.source) is value


# TC-SYMBOL-BUFFER-HOIST-001
# 功能说明: 验证公开 pattern 类、公开 getter 与包根 SymbolBufferHoistPass 可达。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_public_patterns_are_reachable
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_public_patterns_are_reachable() -> None:
    patterns = get_symbol_buffer_hoist_patterns()

    assert package_module.SymbolBufferHoistPass is SymbolBufferHoistPass
    assert len(patterns) == 5
    assert isinstance(patterns[0], DmaAllocInSymbolForHoistPattern)
    assert all(isinstance(pattern, RewritePattern) for pattern in patterns)


# TC-SYMBOL-BUFFER-HOIST-002
# 功能说明: 验证公开 pattern 直接运行时不外提无 matching free 的 input staging buffer。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_pattern_keeps_input_staging_alloc_without_free
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_pattern_keeps_input_staging_alloc_without_free() -> None:
    module = _build_slice_module()

    PatternRewriteWalker(
        GreedyRewritePatternApplier([DmaAllocInSymbolForHoistPattern()], ctx=Context(), dce_enabled=False)
    ).rewrite_module(module)

    top_block, _loop_op, loop_block = _get_blocks(module)
    top_level_allocs = [op for op in top_block.ops if isinstance(op, DmaAllocOp)]
    loop_allocs = [op for op in loop_block.ops if isinstance(op, DmaAllocOp)]
    slice_op = next(op for op in loop_block.ops if isinstance(op, DmaSliceOp))

    assert not top_level_allocs
    assert len(loop_allocs) == 1
    assert slice_op.target is loop_allocs[0].result


# TC-SYMBOL-BUFFER-HOIST-003
# 功能说明: 验证 SymbolBufferHoistPass 不外提无 matching free 的 input staging buffer。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_pass_keeps_input_staging_alloc_without_free
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_pass_keeps_input_staging_alloc_without_free() -> None:
    module = _build_slice_module()

    SymbolBufferHoistPass().apply(Context(), module)

    result = module

    top_block, _loop_op, loop_block = _get_blocks(result)
    assert not any(isinstance(op, DmaAllocOp) for op in top_block.ops)
    assert len([op for op in loop_block.ops if isinstance(op, DmaAllocOp)]) == 1


# TC-SYMBOL-BUFFER-HOIST-004
# 功能说明: 验证 SymbolBufferHoistPass 不外提无 matching free 的 output scratch buffer。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_pass_keeps_output_scratch_alloc_without_free
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_pass_keeps_output_scratch_alloc_without_free() -> None:
    module = _build_deslice_module()

    SymbolBufferHoistPass().apply(Context(), module)

    result = module

    top_block, _loop_op, loop_block = _get_blocks(result)
    loop_alloc = next(op for op in loop_block.ops if isinstance(op, DmaAllocOp))
    deslice_op = next(op for op in loop_block.ops if isinstance(op, DmaDesliceOp))

    assert not any(isinstance(op, DmaAllocOp) for op in top_block.ops)
    assert deslice_op.source is loop_alloc.result


# TC-SYMBOL-BUFFER-HOIST-004A
# 功能说明: 验证 input staging buffer 与同 body 内 matching free 会成对外提。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_hoists_input_staging_alloc_and_matching_free
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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


# TC-SYMBOL-BUFFER-HOIST-004B1
# 功能说明: 验证 loop-invariant dma.view 在 alloc/free 成对外提后继续单 op 外提一层。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_hoists_loop_invariant_dma_view_one_layer
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_hoists_loop_invariant_dma_view_one_layer() -> None:
    module = _build_view_with_free_module()

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, loop_op, loop_block = _get_blocks(module)
    top_ops = list(top_block.ops)
    top_alloc = next(op for op in top_ops if isinstance(op, DmaAllocOp))
    top_view = next(op for op in top_ops if isinstance(op, DmaViewOp))
    top_free = next(op for op in top_ops if isinstance(op, DmaFreeOp))
    deslice_op = next(op for op in loop_block.ops if isinstance(op, DmaDesliceOp))
    loop_index = top_ops.index(loop_op)

    assert top_ops.index(top_alloc) < top_ops.index(top_view) < loop_index < top_ops.index(top_free)
    assert top_view.source is top_alloc.result
    assert deslice_op.source is top_view.result
    assert not any(isinstance(op, (DmaAllocOp, DmaViewOp, DmaFreeOp)) for op in loop_block.ops)


# TC-SYMBOL-BUFFER-HOIST-004B1A
# 功能说明: 验证 loop-invariant dma.reinterpret 在 alloc/free 成对外提后继续单 op 外提一层。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_hoists_loop_invariant_dma_reinterpret_one_layer
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_hoists_loop_invariant_dma_reinterpret_one_layer() -> None:
    module = _build_reinterpret_with_free_module()

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, loop_op, loop_block = _get_blocks(module)
    top_ops = list(top_block.ops)
    top_alloc = next(op for op in top_ops if isinstance(op, DmaAllocOp))
    top_reinterpret = next(op for op in top_ops if isinstance(op, DmaReinterpretOp))
    top_free = next(op for op in top_ops if isinstance(op, DmaFreeOp))
    deslice_op = next(op for op in loop_block.ops if isinstance(op, DmaDesliceOp))
    loop_index = top_ops.index(loop_op)

    assert top_ops.index(top_alloc) < top_ops.index(top_reinterpret) < loop_index < top_ops.index(top_free)
    assert top_reinterpret.source is top_alloc.result
    assert deslice_op.source is top_reinterpret.result
    assert not any(isinstance(op, (DmaAllocOp, DmaReinterpretOp, DmaFreeOp)) for op in loop_block.ops)


# TC-SYMBOL-BUFFER-HOIST-004B2
# 功能说明: 验证 loop-invariant dma.reshape 在 alloc/free 成对外提后继续单 op 外提一层。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_hoists_loop_invariant_dma_reshape_one_layer
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_hoists_loop_invariant_dma_reshape_one_layer() -> None:
    module = _build_reshape_with_free_module()

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, loop_op, loop_block = _get_blocks(module)
    top_ops = list(top_block.ops)
    top_alloc = next(op for op in top_ops if isinstance(op, DmaAllocOp))
    top_reshape = next(op for op in top_ops if isinstance(op, DmaReshapeOp))
    top_free = next(op for op in top_ops if isinstance(op, DmaFreeOp))
    deslice_op = next(op for op in loop_block.ops if isinstance(op, DmaDesliceOp))
    loop_index = top_ops.index(loop_op)

    assert top_ops.index(top_alloc) < top_ops.index(top_reshape) < loop_index < top_ops.index(top_free)
    assert top_reshape.source is top_alloc.result
    assert deslice_op.source is top_reshape.result
    assert not any(isinstance(op, (DmaAllocOp, DmaReshapeOp, DmaFreeOp)) for op in loop_block.ops)


# TC-SYMBOL-BUFFER-HOIST-004B3
# 功能说明: 验证 loop-invariant dma.subview 在 alloc/free 成对外提后继续单 op 外提一层。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_hoists_loop_invariant_dma_subview_one_layer
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_hoists_loop_invariant_dma_subview_one_layer() -> None:
    module = _build_subview_with_free_module()

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, loop_op, loop_block = _get_blocks(module)
    top_ops = list(top_block.ops)
    top_alloc = next(op for op in top_ops if isinstance(op, DmaAllocOp))
    top_subview = next(op for op in top_ops if isinstance(op, DmaSubviewOp))
    top_free = next(op for op in top_ops if isinstance(op, DmaFreeOp))
    deslice_op = next(op for op in loop_block.ops if isinstance(op, DmaDesliceOp))
    loop_index = top_ops.index(loop_op)

    assert top_ops.index(top_alloc) < top_ops.index(top_subview) < loop_index < top_ops.index(top_free)
    assert top_subview.source[0] is top_alloc.result
    assert deslice_op.source is top_subview.result
    assert not any(isinstance(op, (DmaAllocOp, DmaSubviewOp, DmaFreeOp)) for op in loop_block.ops)


# TC-SYMBOL-BUFFER-HOIST-004B4
# 功能说明: 验证 dma.view 的 offset 依赖当前 iterator 时 view 保留在 loop 内，alloc/free 仍可成对外提。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_keeps_dma_view_when_offset_depends_on_loop_iterator
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_keeps_dma_view_when_offset_depends_on_loop_iterator() -> None:
    module = _build_view_with_free_module(loop_dependent_offset=True)

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, loop_op, loop_block = _get_blocks(module)
    top_ops = list(top_block.ops)
    top_alloc = next(op for op in top_ops if isinstance(op, DmaAllocOp))
    top_free = next(op for op in top_ops if isinstance(op, DmaFreeOp))
    loop_view = next(op for op in loop_block.ops if isinstance(op, DmaViewOp))
    deslice_op = next(op for op in loop_block.ops if isinstance(op, DmaDesliceOp))
    loop_index = top_ops.index(loop_op)

    assert top_ops.index(top_alloc) < loop_index < top_ops.index(top_free)
    assert loop_view.source is top_alloc.result
    assert loop_view.offsets[0] is loop_block.args[0]
    assert deslice_op.source is loop_view.result


# TC-SYMBOL-BUFFER-HOIST-004B5
# 功能说明: 验证 dma.reshape 的 shape 依赖 loop-carried 值时 reshape 保留在 loop 内。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_keeps_dma_reshape_when_shape_is_loop_carried
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_keeps_dma_reshape_when_shape_is_loop_carried() -> None:
    module = _build_reshape_with_free_module(loop_dependent_shape=True)

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, loop_op, loop_block = _get_blocks(module)
    top_ops = list(top_block.ops)
    top_alloc = next(op for op in top_ops if isinstance(op, DmaAllocOp))
    top_free = next(op for op in top_ops if isinstance(op, DmaFreeOp))
    loop_reshape = next(op for op in loop_block.ops if isinstance(op, DmaReshapeOp))
    loop_index = top_ops.index(loop_op)

    assert top_ops.index(top_alloc) < loop_index < top_ops.index(top_free)
    assert loop_reshape.source is top_alloc.result
    assert loop_reshape.shape[0] is loop_block.args[1]


# TC-SYMBOL-BUFFER-HOIST-004B6
# 功能说明: 验证 dma.subview 的 size 依赖 loop-carried 值时 subview 保留在 loop 内。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_keeps_dma_subview_when_size_is_loop_carried
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_keeps_dma_subview_when_size_is_loop_carried() -> None:
    module = _build_subview_with_free_module(loop_dependent_size=True)

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, loop_op, loop_block = _get_blocks(module)
    top_ops = list(top_block.ops)
    top_alloc = next(op for op in top_ops if isinstance(op, DmaAllocOp))
    top_free = next(op for op in top_ops if isinstance(op, DmaFreeOp))
    loop_subview = next(op for op in loop_block.ops if isinstance(op, DmaSubviewOp))
    loop_index = top_ops.index(loop_op)

    assert top_ops.index(top_alloc) < loop_index < top_ops.index(top_free)
    assert loop_subview.source[0] is top_alloc.result
    assert loop_subview.size[0] is loop_block.args[1]


# TC-SYMBOL-BUFFER-HOIST-004C
# 功能说明: 验证 matching free 早于 data use 时 alloc/free 保持在 loop 内。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_keeps_alloc_when_free_precedes_data_use
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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
# 功能说明: 验证同一 alloc 同时作为 dma.broadcast target/source 时不得自证 reset/write。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_keeps_alloc_for_same_value_broadcast_read_write
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_keeps_alloc_for_same_value_broadcast_read_write() -> None:
    module = _build_same_value_broadcast_module()

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, _loop_op, loop_block = _get_blocks(module)
    assert not any(isinstance(op, DmaAllocOp) for op in top_block.ops)
    assert len([op for op in loop_block.ops if isinstance(op, DmaAllocOp)]) == 1


# TC-SYMBOL-BUFFER-HOIST-004G1
# 功能说明: 验证 dma.broadcast target WRITE 能作为后续 kernel READ 的 reset/write proof。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_hoists_alloc_when_broadcast_resets_kernel_read
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_hoists_alloc_when_broadcast_resets_kernel_read() -> None:
    module = _build_broadcast_lifecycle_module(with_kernel_read=True)

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, loop_op, loop_block = _get_blocks(module)
    top_ops = list(top_block.ops)
    top_alloc = next(op for op in top_ops if isinstance(op, DmaAllocOp))
    top_free = next(op for op in top_ops if isinstance(op, DmaFreeOp))
    loop_index = top_ops.index(loop_op)
    broadcast = next(op for op in loop_block.ops if isinstance(op, DmaBroadcastOp))
    kernel_use = next(op for op in loop_block.ops if isinstance(op, KernelBinaryElewiseOp))

    assert top_ops.index(top_alloc) < loop_index < top_ops.index(top_free)
    assert broadcast.target is top_alloc.result
    assert kernel_use.lhs is top_alloc.result
    assert _free_source_is(top_free, top_alloc.result)


# TC-SYMBOL-BUFFER-HOIST-004G2
# 功能说明: 验证 symbol.get_dim/get_stride metadata query 不阻断合法 data use 外提。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_hoists_alloc_with_metadata_queries_and_slice_use
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_hoists_alloc_with_metadata_queries_and_slice_use() -> None:
    module = _build_metadata_query_module(include_data_use=True)

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, loop_op, loop_block = _get_blocks(module)
    top_ops = list(top_block.ops)
    top_alloc = next(op for op in top_ops if isinstance(op, DmaAllocOp))
    top_free = next(op for op in top_ops if isinstance(op, DmaFreeOp))
    get_dim = next(op for op in loop_block.ops if isinstance(op, SymbolGetDimOp))
    get_stride = next(op for op in loop_block.ops if isinstance(op, SymbolGetStrideOp))
    slice_op = next(op for op in loop_block.ops if isinstance(op, DmaSliceOp))
    loop_index = top_ops.index(loop_op)

    assert top_ops.index(top_alloc) < loop_index < top_ops.index(top_free)
    assert get_dim.source is top_alloc.result
    assert get_stride.source is top_alloc.result
    assert slice_op.target is top_alloc.result
    assert _free_source_is(top_free, top_alloc.result)


# TC-SYMBOL-BUFFER-HOIST-004G3
# 功能说明: 验证 symbol.get_dim/get_stride 不能单独作为生命周期 data use。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_keeps_alloc_when_only_metadata_queries_exist
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_keeps_alloc_when_only_metadata_queries_exist() -> None:
    module = _build_metadata_query_module(include_data_use=False)

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, _loop_op, loop_block = _get_blocks(module)
    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in top_block.ops)
    assert len([op for op in loop_block.ops if isinstance(op, DmaAllocOp)]) == 1
    assert len([op for op in loop_block.ops if isinstance(op, DmaFreeOp)]) == 1
    assert any(isinstance(op, SymbolGetDimOp) for op in loop_block.ops)
    assert any(isinstance(op, SymbolGetStrideOp) for op in loop_block.ops)


# TC-SYMBOL-BUFFER-HOIST-004G4
# 功能说明: 验证同一 scf.if region block 内 write-before-read 可证明生命周期安全。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_hoists_alloc_when_conditional_write_and_read_are_same_branch
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_hoists_alloc_when_conditional_write_and_read_are_same_branch() -> None:
    module = _build_conditional_write_module(read_in_branch=True)

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, loop_op, loop_block = _get_blocks(module)
    top_ops = list(top_block.ops)
    top_alloc = next(op for op in top_ops if isinstance(op, DmaAllocOp))
    top_free = next(op for op in top_ops if isinstance(op, DmaFreeOp))
    branch = next(op for op in loop_block.ops if isinstance(op, scf.IfOp))
    branch_block = branch.true_region.block
    fill = next(op for op in branch_block.ops if isinstance(op, DmaFillOp))
    kernel_use = next(op for op in branch_block.ops if isinstance(op, KernelBinaryElewiseOp))
    loop_index = top_ops.index(loop_op)

    assert top_ops.index(top_alloc) < loop_index < top_ops.index(top_free)
    assert fill.target is top_alloc.result
    assert kernel_use.lhs is top_alloc.result
    assert _free_source_is(top_free, top_alloc.result)


# TC-SYMBOL-BUFFER-HOIST-004G5
# 功能说明: 验证 scf.if 分支内 write 不能证明 merge 点 read。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_keeps_alloc_when_conditional_write_feeds_merge_read
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_keeps_alloc_when_conditional_write_feeds_merge_read() -> None:
    module = _build_conditional_write_module(read_in_branch=False)

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, _loop_op, loop_block = _get_blocks(module)
    branch = next(op for op in loop_block.ops if isinstance(op, scf.IfOp))
    branch_block = branch.true_region.block
    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in top_block.ops)
    assert len([op for op in loop_block.ops if isinstance(op, DmaAllocOp)]) == 1
    assert len([op for op in loop_block.ops if isinstance(op, DmaFreeOp)]) == 1
    assert any(isinstance(op, DmaFillOp) for op in branch_block.ops)
    assert any(isinstance(op, KernelBinaryElewiseOp) for op in loop_block.ops)


# TC-SYMBOL-BUFFER-HOIST-004H
# 功能说明: 验证 alias result 流向 kernel.* 时按逃逸/no-op 处理。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_keeps_alias_result_when_used_by_kernel_op
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_keeps_alias_result_when_used_by_kernel_op() -> None:
    module = _build_alias_result_kernel_use_module()

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, _loop_op, loop_block = _get_blocks(module)
    loop_ops = list(loop_block.ops)
    alloc = next(op for op in loop_ops if isinstance(op, DmaAllocOp))
    reshape = next(op for op in loop_ops if isinstance(op, DmaReshapeOp))
    kernel_use = next(op for op in loop_ops if isinstance(op, KernelBinaryElewiseOp))
    free = next(op for op in loop_ops if isinstance(op, DmaFreeOp))

    assert not any(isinstance(op, (DmaAllocOp, DmaReshapeOp, DmaFreeOp)) for op in top_block.ops)
    assert loop_ops.index(alloc) < loop_ops.index(reshape) < loop_ops.index(kernel_use) < loop_ops.index(free)
    assert reshape.source is alloc.result
    assert kernel_use.out is reshape.result
    assert kernel_use.lhs is reshape.result
    assert kernel_use.rhs is reshape.result
    assert _free_source_is(free, alloc.result)


# TC-SYMBOL-BUFFER-HOIST-004H1
# 功能说明: 验证 kernel read/write 被 fill reset 支配时 alloc/free 可由 MemoryEffect 证明后成对外提。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_hoists_alloc_when_kernel_read_is_reset_by_fill
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_hoists_alloc_when_kernel_read_is_reset_by_fill() -> None:
    module = _build_kernel_lifecycle_reset_module()

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, loop_op, loop_block = _get_blocks(module)
    top_ops = list(top_block.ops)
    top_alloc = next(op for op in top_ops if isinstance(op, DmaAllocOp))
    top_free = next(op for op in top_ops if isinstance(op, DmaFreeOp))
    loop_index = top_ops.index(loop_op)
    fill = next(op for op in loop_block.ops if isinstance(op, DmaFillOp))
    kernel_use = next(op for op in loop_block.ops if isinstance(op, KernelBinaryElewiseOp))

    assert top_ops.index(top_alloc) < loop_index < top_ops.index(top_free)
    assert fill.target is top_alloc.result
    assert kernel_use.out is top_alloc.result
    assert kernel_use.lhs is top_alloc.result
    assert _free_source_is(top_free, top_alloc.result)


# TC-SYMBOL-BUFFER-HOIST-004H1A
# 功能说明: 验证 dma.copy 跨 memory space 但 shape/stride/dtype 一致时可证明 target 完整写。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_hoists_alloc_when_copy_cross_space_full_write_resets_kernel_read
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_hoists_alloc_when_copy_cross_space_full_write_resets_kernel_read() -> None:
    module = build_copy_cross_space_full_write_module()

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, loop_op, loop_block = _get_blocks(module)
    top_ops = list(top_block.ops)
    top_alloc = next(op for op in top_ops if isinstance(op, DmaAllocOp))
    top_free = next(op for op in top_ops if isinstance(op, DmaFreeOp))
    loop_index = top_ops.index(loop_op)
    copy = next(op for op in loop_block.ops if isinstance(op, DmaCopyOp))
    kernel_use = next(op for op in loop_block.ops if isinstance(op, KernelBinaryElewiseOp))

    assert top_ops.index(top_alloc) < loop_index < top_ops.index(top_free)
    assert copy.target is top_alloc.result
    assert copy.source is top_block.args[0]
    assert kernel_use.lhs is top_alloc.result
    assert kernel_use.out is top_block.args[1]
    assert _free_source_is(top_free, top_alloc.result)


# TC-SYMBOL-BUFFER-HOIST-004H2
# 功能说明: 验证 kernel read 早于 reset/write 时 alloc/free 保持在 loop 内。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_keeps_alloc_when_kernel_reads_before_reset
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_keeps_alloc_when_kernel_reads_before_reset() -> None:
    module = _build_kernel_lifecycle_read_before_write_module()

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, _loop_op, loop_block = _get_blocks(module)
    loop_ops = list(loop_block.ops)
    alloc = next(op for op in loop_ops if isinstance(op, DmaAllocOp))
    kernel_use = next(op for op in loop_ops if isinstance(op, KernelBinaryElewiseOp))
    fill = next(op for op in loop_ops if isinstance(op, DmaFillOp))
    free = next(op for op in loop_ops if isinstance(op, DmaFreeOp))

    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in top_block.ops)
    assert loop_ops.index(alloc) < loop_ops.index(kernel_use) < loop_ops.index(fill) < loop_ops.index(free)
    assert kernel_use.lhs is alloc.result
    assert fill.target is alloc.result
    assert _free_source_is(free, alloc.result)


# TC-SYMBOL-BUFFER-HOIST-004H3
# 功能说明: 验证 nested loop 内 alias result 流向 kernel op 时 alias op 逐层 fixed-point 外提。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_hoists_nested_alias_result_used_by_kernel_op
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_hoists_nested_alias_result_used_by_kernel_op() -> None:
    module = _build_nested_alias_kernel_use_module()

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, outer_loop, outer_block = _get_blocks(module)
    top_ops = list(top_block.ops)
    top_reshape = next(op for op in top_ops if isinstance(op, DmaReshapeOp))
    inner_loop = next(op for op in outer_block.ops if isinstance(op, SymbolForOp))
    inner_block = inner_loop.body.blocks[0]
    matmul = next(op for op in inner_block.ops if isinstance(op, KernelMatmulOp))

    assert top_ops.index(top_reshape) < top_ops.index(outer_loop)
    assert not any(isinstance(op, DmaReshapeOp) for op in outer_block.ops)
    assert not any(isinstance(op, DmaReshapeOp) for op in inner_block.ops)
    assert matmul.lhs is top_reshape.result


# TC-SYMBOL-BUFFER-HOIST-004H4
# 功能说明: 验证静态 nested alloc/free 经 fixed-point 逐层外提到最外层 loop 外。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_alloc_free_fixed_point_nested_loop_static
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_alloc_free_fixed_point_nested_loop_static() -> None:
    module = _build_fixed_point_alloc_free_fill_module(dynamic_shape=False)

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, outer_loop, outer_block = _get_blocks(module)
    top_ops = list(top_block.ops)
    middle_loop = next(op for op in outer_block.ops if isinstance(op, SymbolForOp))
    middle_block = middle_loop.body.blocks[0]
    inner_loop = next(op for op in middle_block.ops if isinstance(op, SymbolForOp))
    inner_block = inner_loop.body.blocks[0]
    top_alloc = next(op for op in top_ops if isinstance(op, DmaAllocOp))
    top_free = next(op for op in top_ops if isinstance(op, DmaFreeOp))
    fill = next(op for op in inner_block.ops if isinstance(op, DmaFillOp))

    assert top_ops.index(top_alloc) < top_ops.index(outer_loop) < top_ops.index(top_free)
    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in outer_block.ops)
    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in middle_block.ops)
    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in inner_block.ops)
    assert fill.target is top_alloc.result
    assert _free_source_is(top_free, top_alloc.result)


# TC-SYMBOL-BUFFER-HOIST-004H5
# 功能说明: 验证动态 shape nested alloc/free 也能经 fixed-point 逐层外提。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_alloc_free_fixed_point_nested_loop_dynamic
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_alloc_free_fixed_point_nested_loop_dynamic() -> None:
    module = _build_fixed_point_alloc_free_fill_module(dynamic_shape=True)

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, outer_loop, outer_block = _get_blocks(module)
    top_ops = list(top_block.ops)
    middle_loop = next(op for op in outer_block.ops if isinstance(op, SymbolForOp))
    inner_loop = next(op for op in middle_loop.body.blocks[0].ops if isinstance(op, SymbolForOp))
    inner_block = inner_loop.body.blocks[0]
    top_alloc = next(op for op in top_ops if isinstance(op, DmaAllocOp))
    top_free = next(op for op in top_ops if isinstance(op, DmaFreeOp))
    fill = next(op for op in inner_block.ops if isinstance(op, DmaFillOp))

    assert top_ops.index(top_alloc) < top_ops.index(outer_loop) < top_ops.index(top_free)
    assert list(top_alloc.dynamic_shape) == [top_block.args[0], top_block.args[1]]
    assert fill.target is top_alloc.result
    assert _free_source_is(top_free, top_alloc.result)


# TC-SYMBOL-BUFFER-HOIST-004H5A
# 功能说明: 验证动态 matmul loop-local acc/tmp/lhs/rhs scratch alloc/free 可逐层外提，计算 op 保持循环内。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_hoists_dynamic_matmul_loop_local_scratch_allocs
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_hoists_dynamic_matmul_loop_local_scratch_allocs() -> None:
    module = _build_dynamic_matmul_loop_local_scratch_module()

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, outer_loop, outer_block = _get_blocks(module)
    top_ops = list(top_block.ops)
    top_allocs = [op for op in top_ops if isinstance(op, DmaAllocOp)]
    top_frees = [op for op in top_ops if isinstance(op, DmaFreeOp)]
    outer_index = top_ops.index(outer_loop)
    middle_loop = next(op for op in outer_block.ops if isinstance(op, SymbolForOp))
    middle_block = middle_loop.body.blocks[0]
    inner_loop = next(op for op in middle_block.ops if isinstance(op, SymbolForOp))
    inner_block = inner_loop.body.blocks[0]
    middle_fill = next(op for op in middle_block.ops if isinstance(op, DmaFillOp))
    inner_fills = [op for op in inner_block.ops if isinstance(op, DmaFillOp)]
    matmul = next(op for op in inner_block.ops if isinstance(op, KernelMatmulOp))
    accumulate = next(op for op in inner_block.ops if isinstance(op, KernelBinaryElewiseOp))
    hoisted_values = tuple(alloc.result for alloc in top_allocs)
    acc_value = accumulate.out
    tmp_value = accumulate.rhs
    lhs_value = matmul.lhs
    rhs_value = matmul.rhs

    assert len(top_allocs) == 4
    assert len(top_frees) == 4
    assert all(top_ops.index(alloc) < outer_index for alloc in top_allocs)
    assert all(top_ops.index(free) > outer_index for free in top_frees)
    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in outer_block.ops)
    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in middle_block.ops)
    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in inner_block.ops)
    assert all(any(value is hoisted for hoisted in hoisted_values) for value in (acc_value, tmp_value, lhs_value, rhs_value))
    assert accumulate.lhs is acc_value
    assert matmul.out is tmp_value
    assert middle_fill.target is acc_value
    assert any(fill.target is lhs_value for fill in inner_fills)
    assert any(fill.target is rhs_value for fill in inner_fills)
    assert all(any(_free_source_is(free, value) for free in top_frees) for value in (acc_value, tmp_value, lhs_value, rhs_value))


# TC-SYMBOL-BUFFER-HOIST-004H6
# 功能说明: 验证 owner block fill 支配 nested kernel read 时 acc buffer 可外提。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_acc_buffer_hoists_when_fill_dominates_reads
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_acc_buffer_hoists_when_fill_dominates_reads() -> None:
    module = _build_nested_acc_fill_before_read_module()

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, loop_op, loop_block = _get_blocks(module)
    top_ops = list(top_block.ops)
    inner_loop = next(op for op in loop_block.ops if isinstance(op, SymbolForOp))
    inner_block = inner_loop.body.blocks[0]
    top_alloc = next(op for op in top_ops if isinstance(op, DmaAllocOp))
    top_free = next(op for op in top_ops if isinstance(op, DmaFreeOp))
    fill = next(op for op in loop_block.ops if isinstance(op, DmaFillOp))
    kernel_use = next(op for op in inner_block.ops if isinstance(op, KernelBinaryElewiseOp))

    assert top_ops.index(top_alloc) < top_ops.index(loop_op) < top_ops.index(top_free)
    assert fill.target is top_alloc.result
    assert kernel_use.out is top_alloc.result
    assert kernel_use.lhs is top_alloc.result
    assert _free_source_is(top_free, top_alloc.result)


# TC-SYMBOL-BUFFER-HOIST-004H6A
# 功能说明: 验证 nested dma.deslice source 无 reset/write 时不能绕过 lifecycle proof。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_keeps_nested_deslice_source_without_reset
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_keeps_nested_deslice_source_without_reset() -> None:
    module = _build_nested_deslice_source_module(with_reset=False)

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, _loop_op, loop_block = _get_blocks(module)
    inner_loop = next(op for op in loop_block.ops if isinstance(op, SymbolForOp))
    inner_block = inner_loop.body.blocks[0]
    alloc = next(op for op in loop_block.ops if isinstance(op, DmaAllocOp))
    deslice = next(op for op in inner_block.ops if isinstance(op, DmaDesliceOp))

    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in top_block.ops)
    assert deslice.source is alloc.result


# TC-SYMBOL-BUFFER-HOIST-004H6B
# 功能说明: 验证 owner block reset 支配 nested dma.deslice source READ 时允许外提。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_hoists_nested_deslice_source_after_reset
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_hoists_nested_deslice_source_after_reset() -> None:
    module = _build_nested_deslice_source_module(with_reset=True)

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, loop_op, loop_block = _get_blocks(module)
    top_ops = list(top_block.ops)
    inner_loop = next(op for op in loop_block.ops if isinstance(op, SymbolForOp))
    inner_block = inner_loop.body.blocks[0]
    top_alloc = next(op for op in top_ops if isinstance(op, DmaAllocOp))
    top_free = next(op for op in top_ops if isinstance(op, DmaFreeOp))
    fill = next(op for op in loop_block.ops if isinstance(op, DmaFillOp))
    deslice = next(op for op in inner_block.ops if isinstance(op, DmaDesliceOp))

    assert top_ops.index(top_alloc) < top_ops.index(loop_op) < top_ops.index(top_free)
    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in loop_block.ops)
    assert fill.target is top_alloc.result
    assert deslice.source is top_alloc.result
    assert _free_source_is(top_free, top_alloc.result)


# TC-SYMBOL-BUFFER-HOIST-004H6C
# 功能说明: 验证 alloc result 传给未知 call 时 alloc/free 保持在 loop 内。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_keeps_alloc_when_unknown_call_uses_buffer
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_keeps_alloc_when_unknown_call_uses_buffer() -> None:
    module = _build_unknown_call_use_module()

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, _loop_op, loop_block = _get_blocks(module)
    alloc = next(op for op in loop_block.ops if isinstance(op, DmaAllocOp))
    call = next(op for op in loop_block.ops if isinstance(op, func.CallOp))
    free = next(op for op in loop_block.ops if isinstance(op, DmaFreeOp))
    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in top_block.ops)
    assert call.operands[0] is alloc.result
    assert _free_source_is(free, alloc.result)


# TC-SYMBOL-BUFFER-HOIST-004H7
# 功能说明: 验证分支内 write 不支配 merge read，alloc/free 保持原位。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_keeps_alloc_when_branch_write_misses_merge_path
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_keeps_alloc_when_branch_write_misses_merge_path() -> None:
    module = _build_conditional_write_module(read_in_branch=False)

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, _loop_op, loop_block = _get_blocks(module)
    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in top_block.ops)
    assert any(isinstance(op, DmaAllocOp) for op in loop_block.ops)
    assert any(isinstance(op, DmaFreeOp) for op in loop_block.ops)


# TC-SYMBOL-BUFFER-HOIST-004H8
# 功能说明: 验证 nested loop write 可能不执行时不能证明后续 owner-block read。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_keeps_alloc_when_nested_loop_write_may_not_run
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_keeps_alloc_when_nested_loop_write_may_not_run() -> None:
    module = _build_nested_write_may_not_run_module()

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, _loop_op, loop_block = _get_blocks(module)
    nested_loop = next(op for op in loop_block.ops if isinstance(op, SymbolForOp))
    nested_block = nested_loop.body.blocks[0]
    kernel_use = next(op for op in loop_block.ops if isinstance(op, KernelBinaryElewiseOp))
    alloc = next(op for op in loop_block.ops if isinstance(op, DmaAllocOp))

    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in top_block.ops)
    assert any(isinstance(op, DmaFillOp) for op in nested_block.ops)
    assert kernel_use.lhs is alloc.result


# TC-SYMBOL-BUFFER-HOIST-004H9
# 功能说明: 验证 partial subview write 不能证明完整 root read 已 reset。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_keeps_alloc_when_partial_write_precedes_full_read
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_keeps_alloc_when_partial_write_precedes_full_read() -> None:
    module = _build_partial_subview_write_before_root_read_module()

    SymbolBufferHoistPass().apply(Context(), module)

    top_block, _loop_op, loop_block = _get_blocks(module)
    alloc = next(op for op in loop_block.ops if isinstance(op, DmaAllocOp))
    subview = next(op for op in loop_block.ops if isinstance(op, DmaSubviewOp))
    fill = next(op for op in loop_block.ops if isinstance(op, DmaFillOp))
    copy = next(op for op in loop_block.ops if isinstance(op, DmaCopyOp))

    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in top_block.ops)
    assert subview.source[0] is alloc.result
    assert fill.target is subview.result
    assert copy.source is alloc.result


# TC-SYMBOL-BUFFER-HOIST-005
# 功能说明: 验证 shape 依赖 loop-carried 时 alloc 保持在 loop 内。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_keeps_loop_carried_shape_inside_loop
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_rejects_non_module_input() -> None:
    with pytest.raises(KernelCodeError, match=r"^module must be builtin.module$"):
        SymbolBufferHoistPass().apply(Context(), "not-module")  # type: ignore[arg-type]


# TC-SYMBOL-BUFFER-HOIST-007
# 功能说明: 验证 verifier 失败统一转换为 SymbolBufferHoistVerifierError 前缀。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_wraps_verify_failure_prefix
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_wraps_verify_failure_prefix() -> None:
    module = _build_invalid_verify_module()

    with pytest.raises(KernelCodeError, match=r"^SymbolBufferHoistVerifierError:"):
        SymbolBufferHoistPass().apply(Context(), module)


# TC-SYMBOL-BUFFER-HOIST-008
# 功能说明: 验证 registry builder 返回 canonical module path 下的 ModulePass。
# 使用示例: pytest -q test/passes/test_symbol_buffer_hoist.py -k test_build_registered_symbol_buffer_hoist_pass
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/test_symbol_buffer_hoist.py
def test_build_registered_symbol_buffer_hoist_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("symbol-buffer-hoist")

    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.name == "symbol-buffer-hoist"
    assert type(pass_obj).__name__ == "SymbolBufferHoistPass"
    assert pass_obj.__class__.__module__ == "kernel_gen.passes.hoist.symbol_buffer_hoist"
