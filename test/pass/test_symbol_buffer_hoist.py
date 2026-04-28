"""symbol-buffer-hoist pass tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 `symbol-buffer-hoist` 的公开 pass、公开 pattern getter、registry builder 与固定失败边界。
- 只通过 `kernel_gen.passes.symbol_buffer_hoist`、`kernel_gen.passes` 与 `kernel_gen.passes.registry`
  的公开入口观察行为，不直连文件内 helper。

使用示例:
- pytest -q test/pass/test_symbol_buffer_hoist.py

关联文件:
- spec: spec/pass/symbol_buffer_hoist.md
- test: test/pass/test_symbol_buffer_hoist.py
- 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, StringAttr, i32
from xdsl.ir import Block, Region, SSAValue
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import GreedyRewritePatternApplier, PatternRewriteWalker

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.dma import DmaAllocOp, DmaDesliceOp, DmaSliceOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolForOp, SymbolIterType, SymbolValueType, SymbolYieldOp

pass_module = importlib.import_module("kernel_gen.passes.symbol_buffer_hoist")
package_module = importlib.import_module("kernel_gen.passes")
registry_module = importlib.import_module("kernel_gen.passes.registry")

DmaAllocInSymbolForHoistPattern = pass_module.DmaAllocInSymbolForHoistPattern
SymbolBufferHoistPass = pass_module.SymbolBufferHoistPass
get_symbol_buffer_hoist_patterns = pass_module.get_symbol_buffer_hoist_patterns
build_registered_pass = registry_module.build_registered_pass
load_builtin_passes = registry_module.load_builtin_passes


def _memory_type(shape: tuple[object, ...]) -> NnMemoryType:
    """构造测试用 `nn.memory` 类型。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 使用 `i32` 与 `global` space 构造紧致 stride memory 类型。
    - shape 支持 `int` 与符号名字符串。

    使用示例:
    - tile_type = _memory_type(("TM", "TN"))

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/pass/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    strides: list[object] = []
    running: int | str = 1
    for dim in reversed(shape):
        strides.append(IntAttr(running) if isinstance(running, int) else StringAttr(running))
        if isinstance(dim, int):
            running = running * dim if isinstance(running, int) else f"{dim}*{running}"
        elif running == 1:
            running = dim
        else:
            running = f"{dim}*{running}"
    strides.reverse()
    return NnMemoryType(
        ArrayAttr([IntAttr(dim) if isinstance(dim, int) else StringAttr(dim) for dim in shape]),
        ArrayAttr([stride if isinstance(stride, (IntAttr, StringAttr)) else StringAttr(str(stride)) for stride in strides]),
        i32,
        NnMemorySpaceAttr.from_name("global"),
    )


def _const_symbol(value: int) -> SymbolConstOp:
    """构造测试用 `symbol.const`。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一复用 `symbol.for` 边界、offset/size/stride 所需的公开 `!symbol.int` 常量。

    使用示例:
    - zero = _const_symbol(0)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/pass/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    return SymbolConstOp(value)


def _build_slice_module() -> ModuleOp:
    """构造输入 staging buffer 正例 module。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - loop 内 `dma.alloc` 只作为 `dma.slice` target 使用。
    - alloc shape 完全来自 loop 外 `symbol.const`，满足外提前提。

    使用示例:
    - module = _build_slice_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/pass/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    source_type = _memory_type((32, 64))
    tile_type = _memory_type(("TM", "TK"))
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

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - loop 内 `dma.alloc` 只作为 `dma.deslice` source 使用。
    - `dma.deslice` 直接 use 不视为 buffer escape。

    使用示例:
    - module = _build_deslice_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/pass/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    target_type = _memory_type((32, 64))
    scratch_type = _memory_type(("TM", "TN"))
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


def _build_loop_carried_shape_module() -> ModuleOp:
    """构造 shape 依赖 loop-carried 的反例 module。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - alloc 第一维直接依赖 `symbol.for` 的 carried block argument。
    - 即使 direct use 属于 `dma.slice` target，pass 也必须保持 no-op。

    使用示例:
    - module = _build_loop_carried_shape_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/pass/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    source_type = _memory_type((32, 64))
    tile_type = _memory_type(("ACC", "TK"))
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

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 故意构造带 loop-carried 结果但缺失 `symbol.yield` 的 `symbol.for`。
    - pass 执行完成后必须通过 `SymbolBufferHoistVerifierError:` 前缀回报 verifier 失败。

    使用示例:
    - module = _build_invalid_verify_module()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/pass/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    source_type = _memory_type((32, 64))
    tile_type = _memory_type(("ACC", "TK"))
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

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一提取测试断言需要的块层级。

    使用示例:
    - top_block, loop_op, loop_block = _get_blocks(module)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/pass/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    top_block = func_op.body.blocks[0]
    loop_op = next(op for op in top_block.ops if isinstance(op, SymbolForOp))
    return top_block, loop_op, loop_op.body.blocks[0]


# TC-SYMBOL-BUFFER-HOIST-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证公开 pattern 类、公开 getter 与包根 SymbolBufferHoistPass 可达。
# 使用示例: pytest -q test/pass/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_public_patterns_are_reachable
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/pass/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_public_patterns_are_reachable() -> None:
    patterns = get_symbol_buffer_hoist_patterns()

    assert package_module.SymbolBufferHoistPass is SymbolBufferHoistPass
    assert len(patterns) == 1
    assert isinstance(patterns[0], DmaAllocInSymbolForHoistPattern)


# TC-SYMBOL-BUFFER-HOIST-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证公开 pattern 直接运行时可外提 input staging buffer。
# 使用示例: pytest -q test/pass/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_pattern_hoists_input_staging_alloc
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/pass/test_symbol_buffer_hoist.py
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
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 SymbolBufferHoistPass 可外提 input staging buffer。
# 使用示例: pytest -q test/pass/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_pass_hoists_input_staging_alloc
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/pass/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_pass_hoists_input_staging_alloc() -> None:
    module = _build_slice_module()

    result = SymbolBufferHoistPass().run(module)

    top_block, _loop_op, loop_block = _get_blocks(result)
    assert len([op for op in top_block.ops if isinstance(op, DmaAllocOp)]) == 1
    assert not any(isinstance(op, DmaAllocOp) for op in loop_block.ops)


# TC-SYMBOL-BUFFER-HOIST-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 SymbolBufferHoistPass 可外提 output scratch buffer。
# 使用示例: pytest -q test/pass/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_pass_hoists_output_scratch_alloc
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/pass/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_pass_hoists_output_scratch_alloc() -> None:
    module = _build_deslice_module()

    result = SymbolBufferHoistPass().run(module)

    top_block, _loop_op, loop_block = _get_blocks(result)
    top_level_alloc = next(op for op in top_block.ops if isinstance(op, DmaAllocOp))
    deslice_op = next(op for op in loop_block.ops if isinstance(op, DmaDesliceOp))

    assert deslice_op.source is top_level_alloc.result
    assert not any(isinstance(op, DmaAllocOp) for op in loop_block.ops)


# TC-SYMBOL-BUFFER-HOIST-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 shape 依赖 loop-carried 时 alloc 保持在 loop 内。
# 使用示例: pytest -q test/pass/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_keeps_loop_carried_shape_inside_loop
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/pass/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_keeps_loop_carried_shape_inside_loop() -> None:
    module = _build_loop_carried_shape_module()

    result = SymbolBufferHoistPass().run(module)

    top_block, _loop_op, loop_block = _get_blocks(result)
    assert not any(isinstance(op, DmaAllocOp) for op in top_block.ops)
    assert len([op for op in loop_block.ops if isinstance(op, DmaAllocOp)]) == 1


# TC-SYMBOL-BUFFER-HOIST-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证非 builtin.module 输入复用共享 KernelCodeError 边界。
# 使用示例: pytest -q test/pass/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_rejects_non_module_input
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/pass/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_rejects_non_module_input() -> None:
    with pytest.raises(KernelCodeError, match=r"^module must be builtin.module$"):
        SymbolBufferHoistPass().run(object())


# TC-SYMBOL-BUFFER-HOIST-007
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 verifier 失败统一转换为 SymbolBufferHoistVerifierError 前缀。
# 使用示例: pytest -q test/pass/test_symbol_buffer_hoist.py -k test_symbol_buffer_hoist_wraps_verify_failure_prefix
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/pass/test_symbol_buffer_hoist.py
def test_symbol_buffer_hoist_wraps_verify_failure_prefix() -> None:
    module = _build_invalid_verify_module()

    with pytest.raises(KernelCodeError, match=r"^SymbolBufferHoistVerifierError:"):
        SymbolBufferHoistPass().run(module)


# TC-SYMBOL-BUFFER-HOIST-008
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 registry builder 返回 canonical module path 下的 ModulePass。
# 使用示例: pytest -q test/pass/test_symbol_buffer_hoist.py -k test_build_registered_symbol_buffer_hoist_pass
# 对应功能实现文件路径: kernel_gen/passes/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/pass/test_symbol_buffer_hoist.py
def test_build_registered_symbol_buffer_hoist_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("symbol-buffer-hoist")

    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.name == "symbol-buffer-hoist"
    assert type(pass_obj).__name__ == "SymbolBufferHoistPass"
    assert pass_obj.__class__.__module__ == "kernel_gen.passes.symbol_buffer_hoist"
