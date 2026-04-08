"""memory_pool loop_reuse expectation。

创建者: 朽木露琪亚
最后一次更改: 小李飞刀

功能说明:
- 覆盖 `MemoryPoolPass` 在 `symbol.for` 场景下的 offset 复用输出。
- 覆盖 `MemoryPoolEscapingAlloc`、`MemoryPoolUnsupportedNonLinearAlloc`、
  `MemoryPoolInvalidLifetime`、`MemoryPoolUnsupportedRegionEscape` 四条拒绝路径。
- 默认设置 `SYMPY_GMPY=0`，避免 sympy/gmpy 在部分环境下触发 `SystemError`，不改变语义。

使用示例:
- `PYTHONPATH=. python expectation/pass/lowing/memory_pool/loop_reuse.py`

关联文件:
- spec: [`spec/pass/lowering/memory_pool.md`](spec/pass/lowering/memory_pool.md)
- test: [`test/pass/test_memory_pool.py`](test/pass/test_memory_pool.py)
- 功能实现: [`kernel_gen/passes/lowering/memory_pool.py`](kernel_gen/passes/lowering/memory_pool.py)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SYMPY_GMPY", "0")

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, Region, i32
from xdsl.dialects.test import TestOp as _TestOp
from xdsl.ir import Block, Operation, SSAValue

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp, DmaFreeOp, DmaViewOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolForOp, SymbolValueType
from kernel_gen.passes.lowering.memory_pool import MemoryPoolError, MemoryPoolPass


def _make_space(space: str = "global") -> NnMemorySpaceAttr:
    """构造 `nn.space` attribute。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 为 `memory_pool` expectation 统一生成 `NnMemorySpaceAttr`。

    使用示例:
    - `_make_space("global")`

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    return NnMemorySpaceAttr.from_name(space)


def _make_memory_type(
    shape: tuple[int, ...] = (2, 4),
    stride: tuple[int, ...] = (4, 1),
) -> NnMemoryType:
    """构造默认 `nn.memory` 类型。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 生成 `i32 + global` 的 memory type。
    - 默认使用 contiguous stride；失败用例会显式传入非线性 stride。

    使用示例:
    - `_make_memory_type()`

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    return NnMemoryType(
        ArrayAttr([IntAttr(value) for value in shape]),
        ArrayAttr([IntAttr(value) for value in stride]),
        i32,
        _make_space("global"),
    )


def _make_symbol_operands(values: list[int | str]) -> list[SSAValue]:
    """构造 `!symbol.int<...>` operand 列表。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 将 `int/str` 转换成测试用 symbol SSA value。

    使用示例:
    - `_make_symbol_operands([2, 4])`

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    operands: list[SSAValue] = []
    for value in values:
        operands.append(_TestOp(result_types=[SymbolValueType.from_expr(str(value))]).results[0])
    return operands


def _symbol_value(expr: int | str) -> SSAValue:
    """构造单个 symbol SSA value。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 用于 `symbol.for` 的 `lb/ub/step` 参数。

    使用示例:
    - `_symbol_value(4)`

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    return _TestOp(result_types=[SymbolValueType.from_expr(str(expr))]).results[0]


def _build_module(func_name: str, ops: list[Operation]) -> tuple[ModuleOp, func.FuncOp]:
    """构造单函数 module。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 将给定 op 列表包进 `func.func` 与 `builtin.module`。

    使用示例:
    - `module, func_op = _build_module("main", [alloc, free])`

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    block = Block()
    block.add_ops(ops)
    block.add_ops([func.ReturnOp()])
    func_op = func.FuncOp(func_name, FunctionType.from_lists([], []), Region(block))
    return ModuleOp([func_op]), func_op


def _collect_ops_recursive(block: Block) -> list[Operation]:
    """递归收集 block 及其子 region 的 op。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 便于验证 `rewrite=True` 后 `dma.view` 的数量与 offset。

    使用示例:
    - `ops = _collect_ops_recursive(func_op.body.blocks[0])`

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    ops: list[Operation] = []
    for op in block.ops:
        ops.append(op)
        for region in op.regions:
            for child in region.blocks:
                ops.extend(_collect_ops_recursive(child))
    return ops


def _case_1_symbol_for_reuse() -> None:
    """验证 `symbol.for` 生命周期与 offset 复用。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 对齐 `S3` 的 loop-local / loop 外 alloc 竞争规则。

    使用示例:
    - `_case_1_symbol_for_reuse()`

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    print("[CASE-1] 正例：symbol.for 内外 alloc 的 offset 竞争必须稳定。")
    mem_type = _make_memory_type()
    alloc1 = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)

    loop_block = Block(arg_types=[SymbolValueType.from_expr("i")])
    alloc2 = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free2 = DmaFreeOp(alloc2.result)
    loop_block.add_ops([alloc2, free2])
    loop_op = SymbolForOp(_symbol_value(0), _symbol_value(4), _symbol_value(1), loop_block)

    alloc3 = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free3 = DmaFreeOp(alloc3.result)
    free1 = DmaFreeOp(alloc1.result)
    module, func_op = _build_module("pool_loop", [alloc1, loop_op, alloc3, free3, free1])

    print("[BEFORE]")
    print(module)

    pass_obj = MemoryPoolPass(rewrite=True)
    pass_obj.run(module)
    summary = pass_obj.get_summary("pool_loop")

    print("[SUMMARY]")
    print(summary.to_text())
    print("[AFTER]")
    print(module)

    offsets = {interval.name: str(interval.offset_bytes_expr) for interval in summary.intervals}
    assert offsets["alloc1"] == "0"
    assert offsets["alloc2"] == "32"
    assert offsets["alloc3"] == "32"

    block = func_op.body.blocks[0]
    view_ops = [op for op in _collect_ops_recursive(block) if isinstance(op, DmaViewOp)]
    assert len(view_ops) == 3
    view_offsets = []
    for view_op in view_ops:
        offset_type = view_op.offsets[0].type
        assert isinstance(offset_type, SymbolValueType)
        view_offsets.append(offset_type.get_value())
    assert view_offsets.count(0) == 1
    assert view_offsets.count(2) == 2


def _case_2_escape_return() -> None:
    """验证 alloc 逃逸到 return 时拒绝。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 对齐 `MemoryPoolEscapingAlloc` 固定短语。

    使用示例:
    - `_case_2_escape_return()`

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    print("[CASE-2] 失败边界：alloc 被 func.return 直接返回时必须拒绝。")
    mem_type = _make_memory_type()
    alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    block = Block()
    block.add_ops([alloc, func.ReturnOp(alloc.result)])
    func_op = func.FuncOp("escape", FunctionType.from_lists([], [mem_type]), Region(block))
    module = ModuleOp([func_op])

    with pytest.raises(MemoryPoolError, match="MemoryPoolEscapingAlloc"):
        MemoryPoolPass(rewrite=False).run(module)


def _case_3_non_linear_alloc() -> None:
    """验证非线性布局拒绝路径。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 对齐 `MemoryPoolUnsupportedNonLinearAlloc` 固定短语。

    使用示例:
    - `_case_3_non_linear_alloc()`

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    print("[CASE-3] 失败边界：non-contiguous layout 必须显式拒绝。")
    mem_type = _make_memory_type(stride=(8, 1))
    alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free = DmaFreeOp(alloc.result)
    module, _ = _build_module("layout_fail", [alloc, free])

    with pytest.raises(MemoryPoolError, match="MemoryPoolUnsupportedNonLinearAlloc"):
        MemoryPoolPass(rewrite=False).run(module)


def _case_4_invalid_lifetime_loop() -> None:
    """验证 loop 内外 free 归属错误。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 对齐 `MemoryPoolInvalidLifetime: dma.free inside symbol.for` 固定短语。

    使用示例:
    - `_case_4_invalid_lifetime_loop()`

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    print("[CASE-4] 失败边界：alloc 在 loop 外、free 在 loop 内必须拒绝。")
    mem_type = _make_memory_type()
    alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    loop_block = Block(arg_types=[SymbolValueType.from_expr("i")])
    loop_block.add_ops([DmaFreeOp(alloc.result)])
    loop_op = SymbolForOp(_symbol_value(0), _symbol_value(4), _symbol_value(1), loop_block)
    module, _ = _build_module("invalid_loop", [alloc, loop_op])

    with pytest.raises(MemoryPoolError, match="MemoryPoolInvalidLifetime: dma.free inside symbol.for"):
        MemoryPoolPass(rewrite=True).run(module)


def _case_5_unsupported_region_escape() -> None:
    """验证未知 region 拒绝路径。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 对齐 `MemoryPoolUnsupportedRegionEscape` 固定短语。

    使用示例:
    - `_case_5_unsupported_region_escape()`

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    print("[CASE-5] 失败边界：未知 nested region 必须拒绝。")
    mem_type = _make_memory_type()
    alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free = DmaFreeOp(alloc.result)
    nested = ModuleOp([])
    module, _ = _build_module("region_fail", [nested, alloc, free])

    with pytest.raises(MemoryPoolError, match="MemoryPoolUnsupportedRegionEscape"):
        MemoryPoolPass(rewrite=False).run(module)


def main() -> None:
    """运行 `memory_pool` S3 expectation。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 顺序执行 loop reuse 正例与四条拒绝路径。

    使用示例:
    - `main()`

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    _case_1_symbol_for_reuse()
    _case_2_escape_return()
    _case_3_non_linear_alloc()
    _case_4_invalid_lifetime_loop()
    _case_5_unsupported_region_escape()


if __name__ == "__main__":
    main()
