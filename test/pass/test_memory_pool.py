"""memory_pool pass tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 MemoryPoolPass 的 summary/interval/peak 统计。
- 覆盖 summary 文本输出稳定性与直线路径改写。

使用示例:
- pytest -q test/pass/test_memory_pool.py -k "summary or interval or peak"

当前覆盖率信息:
- `kernel_gen.passes.memory_pool`：`未采集`（新增测试，待补充统计）。

覆盖率命令:
- `pytest --cov=kernel_gen.passes.memory_pool --cov-report=term-missing -q test/pass/test_memory_pool.py`

关联文件:
- 功能实现: kernel_gen/passes/memory_pool.py
- Spec 文档: spec/pass/lowering/memory_pool.md
- 测试文件: test/pass/test_memory_pool.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SYMPY_GMPY", "0")

import sympy as sp
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, StringAttr, i8, i32
from xdsl.dialects.test import TestOp as _TestOp
from xdsl.ir import Block, Operation, Region, SSAValue

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp, DmaFreeOp, DmaViewOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolForOp, SymbolIterType, SymbolValueType
from kernel_gen.passes.memory_pool import MemoryPoolError, MemoryPoolPass


def _make_space(space: str = "global") -> NnMemorySpaceAttr:
    """构造 nn memory space。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 提供 `NnMemorySpaceAttr` 的便捷构造。

    使用示例:
    - _make_space("global")

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    return NnMemorySpaceAttr.from_name(space)


def _make_memory_type(
    shape: tuple[int, ...] = (2, 4),
    stride: tuple[int, ...] = (4, 1),
    element_type=i32,
    space: str = "global",
) -> NnMemoryType:
    """构造 nn.memory type。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 生成默认 contiguous 布局的 memory type。

    使用示例:
    - mem_type = _make_memory_type()

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    return NnMemoryType(
        ArrayAttr([IntAttr(value) for value in shape]),
        ArrayAttr([IntAttr(value) for value in stride]),
        element_type,
        _make_space(space),
    )


def _make_symbol_operands(values: list[int | str]) -> list[SSAValue]:
    """构造 `!symbol.int<"expr">` operand 列表。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 将 `int/str` 映射为 `!symbol.int<"expr">` SSA 值。

    使用示例:
    - _make_symbol_operands([2, "N"])

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    operands: list[SSAValue] = []
    for index, value in enumerate(values):
        expr = f"v{index}" if value is None else str(value)
        operands.append(_TestOp(result_types=[SymbolValueType.from_expr(expr)]).results[0])
    return operands


def _symbol_value(expr: int | str) -> SSAValue:
    """构造单个 `!symbol.int<\"expr\">` SSA value。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 将 int/str 转为对应 symbol 值类型。

    使用示例:
    - value = _symbol_value(1)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    return _TestOp(result_types=[SymbolValueType.from_expr(str(expr))]).results[0]


def _collect_ops_recursive(block: Block) -> list[Operation]:
    """递归收集 block 及子 region 的 op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 便于验证 rewrite 后 IR 中的 op 数量与参数。

    使用示例:
    - ops = _collect_ops_recursive(block)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    ops: list[Operation] = []
    for op in block.ops:
        ops.append(op)
        for region in op.regions:
            for child in region.blocks:
                ops.extend(_collect_ops_recursive(child))
    return ops


def _build_module(func_name: str, ops: list[Operation]) -> ModuleOp:
    """构造单函数 module。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 将给定 op 列表封装进 `func.func` 与 `builtin.module`。

    使用示例:
    - module = _build_module("main", ops)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    block = Block()
    block.add_ops(ops)
    block.add_ops([func.ReturnOp()])
    func_op = func.FuncOp(func_name, FunctionType.from_lists([], []), Region(block))
    return ModuleOp([func_op])


# TC-MP-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-07 10:30:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:30:00 +0800
# 功能说明: 验证 MemoryPoolPass 生成 summary 与 bucket 信息稳定。
# 使用示例: pytest -q test/pass/test_memory_pool.py -k test_memory_pool_summary_basic
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/pass/test_memory_pool.py
def test_memory_pool_summary_basic() -> None:
    mem_type = _make_memory_type()
    alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free = DmaFreeOp(alloc.result)
    module = _build_module("main", [alloc, free])

    pass_obj = MemoryPoolPass(rewrite=False)
    pass_obj.run(module)
    summary = pass_obj.get_summary("main")

    assert summary.func_name == "main"
    assert len(summary.intervals) == 1
    interval = summary.intervals[0]
    assert interval.name == "alloc1"
    assert interval.bucket_key == ("#GM",)
    assert str(interval.size_bytes_expr) == "32"
    text = summary.to_text()
    assert "func_name = main" in text
    assert "pool_count = 1" in text


# TC-MP-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-07 10:30:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:30:00 +0800
# 功能说明: 验证 interval 的 begin/end 索引随词法顺序变化。
# 使用示例: pytest -q test/pass/test_memory_pool.py -k test_memory_pool_interval_indices
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/pass/test_memory_pool.py
def test_memory_pool_interval_indices() -> None:
    mem_type = _make_memory_type()
    dummy = _TestOp()
    alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free = DmaFreeOp(alloc.result)
    module = _build_module("main", [dummy, alloc, free])

    pass_obj = MemoryPoolPass(rewrite=False)
    pass_obj.run(module)
    summary = pass_obj.get_summary("main")
    interval = summary.intervals[0]
    assert interval.begin_index == 1
    assert interval.end_index == 2


# TC-MP-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-07 10:30:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:30:00 +0800
# 功能说明: 验证重叠区间的 peak 统计正确。
# 使用示例: pytest -q test/pass/test_memory_pool.py -k test_memory_pool_peak_overlap
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/pass/test_memory_pool.py
def test_memory_pool_peak_overlap() -> None:
    mem_type = _make_memory_type(shape=(2, 2), stride=(2, 1))
    alloc_a = DmaAllocOp(_make_symbol_operands([2, 2]), mem_type)
    alloc_b = DmaAllocOp(_make_symbol_operands([2, 2]), mem_type)
    free_a = DmaFreeOp(alloc_a.result)
    free_b = DmaFreeOp(alloc_b.result)
    module = _build_module("main", [alloc_a, alloc_b, free_a, free_b])

    pass_obj = MemoryPoolPass(rewrite=False)
    pass_obj.run(module)
    summary = pass_obj.get_summary("main")
    bucket = ("#GM",)
    assert summary.pool_count == 1
    assert str(summary.peak_bytes_by_bucket[bucket]) == str(sp.Integer(32))


# TC-MP-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-07 10:30:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:30:00 +0800
# 功能说明: 验证直线路径改写生成 pool + view。
# 使用示例: pytest -q test/pass/test_memory_pool.py -k "rewrite and straight_line"
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/pass/test_memory_pool.py
def test_memory_pool_rewrite_straight_line_pool_reuse() -> None:
    mem_type = _make_memory_type()
    alloc_a = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free_a = DmaFreeOp(alloc_a.result)
    alloc_b = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free_b = DmaFreeOp(alloc_b.result)
    module = _build_module("main", [alloc_a, free_a, alloc_b, free_b])

    pass_obj = MemoryPoolPass(rewrite=True)
    pass_obj.run(module)

    func_ops = [op for op in module.ops if isinstance(op, func.FuncOp)]
    assert len(func_ops) == 1
    block = func_ops[0].body.blocks[0]
    alloc_ops = [op for op in block.ops if isinstance(op, DmaAllocOp)]
    free_ops = [op for op in block.ops if isinstance(op, DmaFreeOp)]
    view_ops = [op for op in block.ops if isinstance(op, DmaViewOp)]

    assert len(alloc_ops) == 1
    assert len(free_ops) == 1
    assert len(view_ops) == 2

    pool_type = alloc_ops[0].result.type
    assert isinstance(pool_type, NnMemoryType)
    assert len(pool_type.shape.data) == 1
    assert pool_type.element_type == i8
    for view_op in view_ops:
        assert view_op.result.type == mem_type


# TC-MP-010
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-07 10:30:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:30:00 +0800
# 功能说明: 验证直线路径多 bucket 会报错。
# 使用示例: pytest -q test/pass/test_memory_pool.py -k test_memory_pool_rewrite_multiple_buckets
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/pass/test_memory_pool.py
def test_memory_pool_rewrite_multiple_buckets() -> None:
    mem_type_gm = _make_memory_type(space="global")
    mem_type_sm = _make_memory_type(space="shared")
    alloc_a = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type_gm)
    free_a = DmaFreeOp(alloc_a.result)
    alloc_b = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type_sm)
    free_b = DmaFreeOp(alloc_b.result)
    module = _build_module("main", [alloc_a, free_a, alloc_b, free_b])

    pass_obj = MemoryPoolPass(rewrite=True)
    try:
        pass_obj.run(module)
    except MemoryPoolError as exc:
        assert "MemoryPoolUnsupportedPoolBucket: mixed space is not supported" in str(exc)
    else:
        raise AssertionError("expected MemoryPoolError for multiple buckets")


# TC-MP-011
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-07 10:30:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:30:00 +0800
# 功能说明: 验证直线路径 size 不一致会报错。
# 使用示例: pytest -q test/pass/test_memory_pool.py -k test_memory_pool_rewrite_size_mismatch
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/pass/test_memory_pool.py
def test_memory_pool_rewrite_size_mismatch() -> None:
    mem_type = _make_memory_type()
    mem_type_b = _make_memory_type(shape=(2, 5), stride=(5, 1))
    alloc_a = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free_a = DmaFreeOp(alloc_a.result)
    alloc_b = DmaAllocOp(_make_symbol_operands([2, 5]), mem_type_b)
    free_b = DmaFreeOp(alloc_b.result)
    module = _build_module("main", [alloc_a, free_a, alloc_b, free_b])

    pass_obj = MemoryPoolPass(rewrite=True)
    try:
        pass_obj.run(module)
    except MemoryPoolError as exc:
        assert "MemoryPoolUnsupportedPoolBucket: size mismatch" in str(exc)
    else:
        raise AssertionError("expected MemoryPoolError for size mismatch")


# TC-MP-012
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-07 10:30:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:30:00 +0800
# 功能说明: 验证直线路径生命周期重叠会分配不同 offset 并成功改写。
# 使用示例: pytest -q test/pass/test_memory_pool.py -k test_memory_pool_rewrite_overlap
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/pass/test_memory_pool.py
def test_memory_pool_rewrite_overlap() -> None:
    mem_type = _make_memory_type()
    alloc_a = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    alloc_b = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free_a = DmaFreeOp(alloc_a.result)
    free_b = DmaFreeOp(alloc_b.result)
    module = _build_module("main", [alloc_a, alloc_b, free_a, free_b])

    pass_obj = MemoryPoolPass(rewrite=True)
    pass_obj.run(module)
    func_ops = [op for op in module.ops if isinstance(op, func.FuncOp)]
    block = func_ops[0].body.blocks[0]
    view_ops = [op for op in _collect_ops_recursive(block) if isinstance(op, DmaViewOp)]
    assert len(view_ops) == 2
    offsets = []
    for view_op in view_ops:
        offset0 = view_op.offsets[0]
        offset_type = offset0.type
        assert isinstance(offset_type, SymbolValueType)
        offsets.append(offset_type.get_value())
    assert set(offsets) == {0, 2}


# TC-MP-013
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-07 10:30:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:30:00 +0800
# 功能说明: 验证多 block 直线路径改写会报错。
# 使用示例: pytest -q test/pass/test_memory_pool.py -k test_memory_pool_rewrite_multiple_blocks
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/pass/test_memory_pool.py
def test_memory_pool_rewrite_multiple_blocks() -> None:
    mem_type = _make_memory_type()
    alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free = DmaFreeOp(alloc.result)
    block0 = Block()
    block0.add_ops([alloc, free, func.ReturnOp()])
    block1 = Block()
    block1.add_ops([func.ReturnOp()])
    func_op = func.FuncOp("main", FunctionType.from_lists([], []), Region([block0, block1]))
    module = ModuleOp([func_op])

    pass_obj = MemoryPoolPass(rewrite=True)
    try:
        pass_obj.run(module)
    except MemoryPoolError as exc:
        assert "MemoryPoolRewriteUnsupported: function must have single block" in str(exc)
    else:
        raise AssertionError("expected MemoryPoolError for multiple blocks")


# TC-MP-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-07 10:30:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:30:00 +0800
# 功能说明: 验证非 builtin.module 输入会报错。
# 使用示例: pytest -q test/pass/test_memory_pool.py -k test_memory_pool_invalid_module
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/pass/test_memory_pool.py
def test_memory_pool_invalid_module() -> None:
    pass_obj = MemoryPoolPass(rewrite=False)
    try:
        pass_obj.run(_TestOp())
    except MemoryPoolError as exc:
        assert "MemoryPoolInvalidModule" in str(exc)
    else:
        raise AssertionError("expected MemoryPoolError for invalid module")


# TC-MP-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-07 10:30:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:30:00 +0800
# 功能说明: 验证非 contiguous 布局会报错。
# 使用示例: pytest -q test/pass/test_memory_pool.py -k test_memory_pool_non_contiguous_layout
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/pass/test_memory_pool.py
def test_memory_pool_non_contiguous_layout() -> None:
    mem_type = _make_memory_type(shape=(2, 4), stride=(5, 1))
    alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free = DmaFreeOp(alloc.result)
    module = _build_module("main", [alloc, free])
    pass_obj = MemoryPoolPass(rewrite=False)
    try:
        pass_obj.run(module)
    except MemoryPoolError as exc:
        assert "MemoryPoolUnsupportedNonLinearAlloc" in str(exc)
    else:
        raise AssertionError("expected MemoryPoolError for non-contiguous layout")


# TC-MP-007
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-07 10:30:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:30:00 +0800
# 功能说明: 验证 alloc/free 不成对会报错。
# 使用示例: pytest -q test/pass/test_memory_pool.py -k test_memory_pool_unpaired_alloc
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/pass/test_memory_pool.py
def test_memory_pool_unpaired_alloc() -> None:
    mem_type = _make_memory_type()
    alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    module = _build_module("main", [alloc])
    pass_obj = MemoryPoolPass(rewrite=False)
    try:
        pass_obj.run(module)
    except MemoryPoolError as exc:
        assert "MemoryPoolInvalidLifetime" in str(exc)
    else:
        raise AssertionError("expected MemoryPoolError for missing dma.free")


# TC-MP-008
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-07 10:30:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:30:00 +0800
# 功能说明: 验证匿名维度会报错。
# 使用示例: pytest -q test/pass/test_memory_pool.py -k test_memory_pool_anonymous_dim
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/pass/test_memory_pool.py
def test_memory_pool_anonymous_dim() -> None:
    mem_type = NnMemoryType(
        ArrayAttr([StringAttr("?"), IntAttr(4)]),
        ArrayAttr([IntAttr(4), IntAttr(1)]),
        i32,
        _make_space("global"),
    )
    alloc = DmaAllocOp(_make_symbol_operands(["M", 4]), mem_type)
    free = DmaFreeOp(alloc.result)
    module = _build_module("main", [alloc, free])
    pass_obj = MemoryPoolPass(rewrite=False)
    try:
        pass_obj.run(module)
    except MemoryPoolError as exc:
        assert "MemoryPoolUnsupportedShape" in str(exc)
    else:
        raise AssertionError("expected MemoryPoolError for anonymous shape")


# TC-MP-009
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-07 10:30:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:30:00 +0800
# 功能说明: 验证 alloc 结果非 nn.memory 会报错。
# 使用示例: pytest -q test/pass/test_memory_pool.py -k test_memory_pool_alloc_non_memory
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/pass/test_memory_pool.py
def test_memory_pool_alloc_non_memory() -> None:
    alloc = DmaAllocOp(_make_symbol_operands([2, 4]), i32)
    free = DmaFreeOp(alloc.result)
    module = _build_module("main", [alloc, free])
    pass_obj = MemoryPoolPass(rewrite=False)
    try:
        pass_obj.run(module)
    except MemoryPoolError as exc:
        assert "MemoryPoolInvalidAlloc" in str(exc)
    else:
        raise AssertionError("expected MemoryPoolError for alloc result type")


# TC-MP-014
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-07 10:30:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:30:00 +0800
# 功能说明: 验证 symbol.for 内 alloc 的 offset 复用规则。
# 使用示例: pytest -q test/pass/test_memory_pool.py -k test_memory_pool_symbol_for_reuse
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/pass/test_memory_pool.py
def test_memory_pool_symbol_for_reuse() -> None:
    mem_type = _make_memory_type()
    alloc1 = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)

    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "4", "1")])
    alloc2 = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free2 = DmaFreeOp(alloc2.result)
    loop_block.add_ops([alloc2, free2])
    loop_op = SymbolForOp(_symbol_value(0), _symbol_value(4), _symbol_value(1), loop_block)

    alloc3 = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free3 = DmaFreeOp(alloc3.result)
    free1 = DmaFreeOp(alloc1.result)

    module = _build_module("pool_loop", [alloc1, loop_op, alloc3, free3, free1])

    pass_obj = MemoryPoolPass(rewrite=True)
    pass_obj.run(module)
    summary = pass_obj.get_summary("pool_loop")

    offsets = {interval.name: interval.offset_bytes_expr for interval in summary.intervals}
    assert str(offsets["alloc1"]) == "0"
    assert str(offsets["alloc2"]) == "32"
    assert str(offsets["alloc3"]) == "32"

    func_ops = [op for op in module.ops if isinstance(op, func.FuncOp)]
    block = func_ops[0].body.blocks[0]
    view_ops = [op for op in _collect_ops_recursive(block) if isinstance(op, DmaViewOp)]
    assert len(view_ops) == 3
    view_offsets = []
    for view_op in view_ops:
        offset0 = view_op.offsets[0]
        offset_type = offset0.type
        assert isinstance(offset_type, SymbolValueType)
        view_offsets.append(offset_type.get_value())
    assert view_offsets.count(0) == 1
    assert view_offsets.count(2) == 2


# TC-MP-015
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-07 10:30:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:30:00 +0800
# 功能说明: 验证 alloc 逃逸到 return 会被拒绝。
# 使用示例: pytest -q test/pass/test_memory_pool.py -k test_memory_pool_escape_return
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/pass/test_memory_pool.py
def test_memory_pool_escape_return() -> None:
    mem_type = _make_memory_type()
    alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    block = Block()
    block.add_ops([alloc, func.ReturnOp(alloc.result)])
    func_op = func.FuncOp("main", FunctionType.from_lists([], [mem_type]), Region(block))
    module = ModuleOp([func_op])

    pass_obj = MemoryPoolPass(rewrite=False)
    try:
        pass_obj.run(module)
    except MemoryPoolError as exc:
        assert "MemoryPoolEscapingAlloc" in str(exc)
    else:
        raise AssertionError("expected MemoryPoolError for escaping alloc")


# TC-MP-016
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-07 10:30:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:30:00 +0800
# 功能说明: 验证 alloc 在 loop 外、free 在 loop 内会被拒绝。
# 使用示例: pytest -q test/pass/test_memory_pool.py -k test_memory_pool_invalid_lifetime_loop
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/pass/test_memory_pool.py
def test_memory_pool_invalid_lifetime_loop() -> None:
    mem_type = _make_memory_type()
    alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "4", "1")])
    loop_block.add_ops([DmaFreeOp(alloc.result)])
    loop_op = SymbolForOp(_symbol_value(0), _symbol_value(4), _symbol_value(1), loop_block)
    module = _build_module("main", [alloc, loop_op])

    pass_obj = MemoryPoolPass(rewrite=True)
    try:
        pass_obj.run(module)
    except MemoryPoolError as exc:
        assert "MemoryPoolInvalidLifetime: dma.free inside symbol.for" in str(exc)
    else:
        raise AssertionError("expected MemoryPoolError for invalid loop lifetime")


# TC-MP-017
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-07 10:30:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:30:00 +0800
# 功能说明: 验证未知 region 会触发拒绝路径。
# 使用示例: pytest -q test/pass/test_memory_pool.py -k test_memory_pool_unsupported_region_escape
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/pass/test_memory_pool.py
def test_memory_pool_unsupported_region_escape() -> None:
    mem_type = _make_memory_type()
    alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free = DmaFreeOp(alloc.result)
    nested = ModuleOp([])
    module = _build_module("main", [nested, alloc, free])
    pass_obj = MemoryPoolPass(rewrite=False)
    try:
        pass_obj.run(module)
    except MemoryPoolError as exc:
        assert "MemoryPoolUnsupportedRegionEscape" in str(exc)
    else:
        raise AssertionError("expected MemoryPoolError for unsupported region")
