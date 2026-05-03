"""memory_pool pass tests.


功能说明:
- 覆盖 MemoryPoolPass 的 summary/interval/peak 统计。
- 覆盖 summary 文本输出稳定性与直线路径改写。

使用示例:
- pytest -q test/passes/test_memory_pool.py -k "summary or interval or peak"

当前覆盖率信息:
- `kernel_gen.passes.memory_pool`：`未采集`（新增测试，待补充统计）。

覆盖率命令:
- `pytest --cov=kernel_gen.passes.memory_pool --cov-report=term-missing -q test/passes/test_memory_pool.py`

关联文件:
- 功能实现: kernel_gen/passes/memory_pool.py
- Spec 文档: spec/pass/lowering/memory_pool.md
- 测试文件: test/passes/test_memory_pool.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SYMPY_GMPY", "0")

import sympy as sp
from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, IntegerType, ModuleOp, StringAttr, bf16, f16, f32, f64, i1, i8, i16, i32, i64
from xdsl.dialects.test import TestOp as _TestOp
from xdsl.ir import Block, Operation, Region, SSAValue

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.arch import ArchGetDynamicMemoryOp
from kernel_gen.dialect.dma import DmaAllocOp, DmaFreeOp, DmaReshapeOp, DmaSubviewOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolForOp, SymbolIterType, SymbolValueType
from kernel_gen.passes.memory_pool import MemoryPoolInterval, MemoryPoolPass, MemoryPoolSummary
from kernel_gen.tools.ircheck import run_ircheck_text


def _make_space(space: str = "global") -> NnMemorySpaceAttr:
    """构造 nn memory space。


    功能说明:
    - 提供 `NnMemorySpaceAttr` 的便捷构造。

    使用示例:
    - _make_space("global")

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
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


    功能说明:
    - 生成默认 contiguous 布局的 memory type。

    使用示例:
    - mem_type = _make_memory_type()

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
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


    功能说明:
    - 将 `int/str` 映射为 `!symbol.int<"expr">` SSA 值。

    使用示例:
    - _make_symbol_operands([2, "N"])

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    operands: list[SSAValue] = []
    for index, value in enumerate(values):
        expr = f"v{index}" if value is None else str(value)
        operands.append(_TestOp(result_types=[SymbolValueType.from_expr(expr)]).results[0])
    return operands


def _symbol_value(expr: int | str) -> SSAValue:
    """构造单个 `!symbol.int<\"expr\">` SSA value。


    功能说明:
    - 将 int/str 转为对应 symbol 值类型。

    使用示例:
    - value = _symbol_value(1)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    return _TestOp(result_types=[SymbolValueType.from_expr(str(expr))]).results[0]


def _collect_ops_recursive(block: Block) -> list[Operation]:
    """递归收集 block 及子 region 的 op。


    功能说明:
    - 便于验证 rewrite 后 IR 中的 op 数量与参数。

    使用示例:
    - ops = _collect_ops_recursive(block)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    ops: list[Operation] = []
    for op in block.ops:
        ops.append(op)
        for region in op.regions:
            for child in region.blocks:
                ops.extend(_collect_ops_recursive(child))
    return ops


def _collect_defining_ops(value: SSAValue) -> list[Operation]:
    """递归收集 SSA value 依赖的定义 op。


    功能说明:
    - 从一个 SSA value 出发沿 operand 链收集定义它所需的 op。
    - 用于确认函数体 offset 不依赖 loop body 内定义的 SSA。

    使用示例:
    - defining_ops = _collect_defining_ops(subview.offset[0])

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    result: list[Operation] = []
    seen: set[Operation] = set()
    pending: list[SSAValue] = [value]
    while pending:
        current = pending.pop()
        owner = current.owner
        if not isinstance(owner, Operation) or owner in seen:
            continue
        seen.add(owner)
        result.append(owner)
        pending.extend(owner.operands)
    return result


def _build_module(func_name: str, ops: list[Operation]) -> ModuleOp:
    """构造单函数 module。


    功能说明:
    - 将给定 op 列表封装进 `func.func` 与 `builtin.module`。

    使用示例:
    - module = _build_module("main", ops)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    block = Block()
    block.add_ops(ops)
    block.add_ops([func.ReturnOp()])
    func_op = func.FuncOp(func_name, FunctionType.from_lists([], []), Region(block))
    return ModuleOp([func_op])


# TC-MP-001
# 功能说明: 验证 MemoryPoolPass 生成 summary 与 bucket 信息稳定。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_summary_basic
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_summary_basic() -> None:
    mem_type = _make_memory_type()
    alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free = DmaFreeOp(alloc.result)
    module = _build_module("main", [alloc, free])

    pass_obj = MemoryPoolPass(rewrite=False)
    pass_obj.apply(Context(), module)
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


# TC-MP-018
# 功能说明: 验证 MemoryPoolPass 的公开 summary 查询、空函数摘要、多 key bucket 文本与 all_summaries 拷贝语义。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_public_summary_access_edges
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_public_summary_access_edges() -> None:
    module = ModuleOp([
        _TestOp(),
        func.FuncOp("empty", FunctionType.from_lists([], []), Region(Block())),
    ])
    pass_obj = MemoryPoolPass(rewrite=True)

    pass_obj.apply(Context(), module)
    summary = pass_obj.get_summary("empty")
    summary_text = summary.to_text()

    assert summary.func_name == "empty"
    assert "  - <empty>" in summary_text
    assert "pool_count = 0" in summary_text

    returned = pass_obj.all_summaries()
    returned["manual"] = MemoryPoolSummary("manual", (), {}, 0)
    assert "manual" not in pass_obj.all_summaries()
    try:
        pass_obj.get_summary("manual")
    except KernelCodeError as exc:
        assert "MemoryPoolSummaryNotFound" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for missing summary")

    manual = MemoryPoolSummary(
        "manual",
        (
            MemoryPoolInterval(
                "allocx",
                ("#GM", "#SM"),
                sp.Integer(8),
                0,
                0,
                sp.Integer(0),
            ),
        ),
        {("#GM", "#SM"): sp.Integer(8)},
        1,
    )
    assert "(#GM, #SM) -> 8" in manual.to_text()


# TC-MP-002
# 功能说明: 验证 interval 的 begin/end 索引随词法顺序变化。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_interval_indices
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_interval_indices() -> None:
    mem_type = _make_memory_type()
    dummy = _TestOp()
    alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free = DmaFreeOp(alloc.result)
    module = _build_module("main", [dummy, alloc, free])

    pass_obj = MemoryPoolPass(rewrite=False)
    pass_obj.apply(Context(), module)
    summary = pass_obj.get_summary("main")
    interval = summary.intervals[0]
    assert interval.begin_index == 1
    assert interval.end_index == 2


# TC-MP-003
# 功能说明: 验证重叠区间的 peak 统计正确。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_peak_overlap
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_peak_overlap() -> None:
    mem_type = _make_memory_type(shape=(2, 2), stride=(2, 1))
    alloc_a = DmaAllocOp(_make_symbol_operands([2, 2]), mem_type)
    alloc_b = DmaAllocOp(_make_symbol_operands([2, 2]), mem_type)
    free_a = DmaFreeOp(alloc_a.result)
    free_b = DmaFreeOp(alloc_b.result)
    module = _build_module("main", [alloc_a, alloc_b, free_a, free_b])

    pass_obj = MemoryPoolPass(rewrite=False)
    pass_obj.apply(Context(), module)
    summary = pass_obj.get_summary("main")
    bucket = ("#GM",)
    assert summary.pool_count == 1
    assert str(summary.peak_bytes_by_bucket[bucket]) == str(sp.Integer(32))


# TC-MP-004
# 功能说明: 验证直线路径改写生成 dynamic memory + subview + reshape。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k "rewrite and straight_line"
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_rewrite_straight_line_pool_reuse() -> None:
    mem_type = _make_memory_type(space="shared")
    alloc_a = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free_a = DmaFreeOp(alloc_a.result)
    alloc_b = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free_b = DmaFreeOp(alloc_b.result)
    module = _build_module("main", [alloc_a, free_a, alloc_b, free_b])

    pass_obj = MemoryPoolPass(rewrite=True, alignment=0)
    pass_obj.apply(Context(), module)

    func_ops = [op for op in module.ops if isinstance(op, func.FuncOp)]
    assert len(func_ops) == 1
    block = func_ops[0].body.blocks[0]
    alloc_ops = [op for op in block.ops if isinstance(op, DmaAllocOp)]
    free_ops = [op for op in block.ops if isinstance(op, DmaFreeOp)]
    backing_ops = [op for op in block.ops if isinstance(op, ArchGetDynamicMemoryOp)]
    subview_ops = [op for op in block.ops if isinstance(op, DmaSubviewOp)]
    reshape_ops = [op for op in block.ops if isinstance(op, DmaReshapeOp)]

    assert len(alloc_ops) == 0
    assert len(free_ops) == 0
    assert len(backing_ops) == 1
    assert len(subview_ops) == 2
    assert len(reshape_ops) == 2

    backing_type = backing_ops[0].result.type
    assert isinstance(backing_type, NnMemoryType)
    assert len(backing_type.shape.data) == 1
    assert backing_type.element_type == i8
    subview_offsets = [op.offset[0].type.get_value() for op in subview_ops]
    assert subview_offsets == [0, 8]
    for reshape_op in reshape_ops:
        assert reshape_op.result.type == mem_type


# TC-MP-010
# 功能说明: 验证直线路径多 memory space 会分别生成 dynamic memory backing。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_rewrite_multiple_buckets
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_rewrite_multiple_buckets() -> None:
    mem_type_gm = _make_memory_type(space="shared")
    mem_type_tlm = _make_memory_type(space="tlm1")
    alloc_a = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type_gm)
    free_a = DmaFreeOp(alloc_a.result)
    alloc_b = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type_tlm)
    free_b = DmaFreeOp(alloc_b.result)
    module = _build_module("main", [alloc_a, free_a, alloc_b, free_b])

    pass_obj = MemoryPoolPass(rewrite=True, alignment=0)
    pass_obj.apply(Context(), module)

    ops = _collect_ops_recursive(module.body.block)
    backing_spaces = [
        op.result.type.space.space.data
        for op in ops
        if isinstance(op, ArchGetDynamicMemoryOp) and isinstance(op.result.type, NnMemoryType)
    ]
    subview_ops = [op for op in ops if isinstance(op, DmaSubviewOp)]

    assert backing_spaces == ["shared", "tlm1"]
    assert len(subview_ops) == 2
    assert [op.result.type.space.space.data for op in subview_ops] == ["shared", "tlm1"]


# TC-MP-011
# 功能说明: 验证直线路径不同 size 会按出现顺序线性切分。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_rewrite_size_mismatch
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_rewrite_size_mismatch() -> None:
    mem_type = _make_memory_type(space="shared")
    mem_type_b = _make_memory_type(shape=(2, 5), stride=(5, 1), space="shared")
    alloc_a = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free_a = DmaFreeOp(alloc_a.result)
    alloc_b = DmaAllocOp(_make_symbol_operands([2, 5]), mem_type_b)
    free_b = DmaFreeOp(alloc_b.result)
    module = _build_module("main", [alloc_a, free_a, alloc_b, free_b])

    pass_obj = MemoryPoolPass(rewrite=True, alignment=0)
    pass_obj.apply(Context(), module)

    subview_ops = [
        op for op in _collect_ops_recursive(module.body.block) if isinstance(op, DmaSubviewOp)
    ]
    assert [op.offset[0].type.get_value() for op in subview_ops] == [0, 8]
    assert [op.size[0].type.get_value() for op in subview_ops] == [8, 10]


# TC-MP-012
# 功能说明: 验证直线路径生命周期重叠会分配不同 offset 并成功改写。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_rewrite_overlap
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_rewrite_overlap() -> None:
    mem_type = _make_memory_type(space="shared")
    alloc_a = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    alloc_b = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free_a = DmaFreeOp(alloc_a.result)
    free_b = DmaFreeOp(alloc_b.result)
    module = _build_module("main", [alloc_a, alloc_b, free_a, free_b])

    pass_obj = MemoryPoolPass(rewrite=True, alignment=0)
    pass_obj.apply(Context(), module)
    func_ops = [op for op in module.ops if isinstance(op, func.FuncOp)]
    block = func_ops[0].body.blocks[0]
    subview_ops = [op for op in _collect_ops_recursive(block) if isinstance(op, DmaSubviewOp)]
    assert len(subview_ops) == 2
    offsets = []
    for subview_op in subview_ops:
        offset0 = subview_op.offset[0]
        offset_type = offset0.type
        assert isinstance(offset_type, SymbolValueType)
        offsets.append(offset_type.get_value())
    assert offsets == [0, 8]


# TC-MP-019
# 功能说明: 验证 MemoryPoolPass 的公开 dtype 矩阵、非内置 dtype 拒绝与符号 shape rewrite 行为。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_dtype_and_symbolic_shape_matrix
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_dtype_and_symbolic_shape_matrix() -> None:
    dtype_cases = [
        (i1, "2"),
        (i8, "2"),
        (i16, "4"),
        (i32, "8"),
        (i64, "16"),
        (f16, "4"),
        (bf16, "4"),
        (f32, "8"),
        (f64, "16"),
    ]

    for element_type, expected_size in dtype_cases:
        mem_type = _make_memory_type(shape=(2,), stride=(1,), element_type=element_type)
        alloc = DmaAllocOp(_make_symbol_operands([2]), mem_type)
        free = DmaFreeOp(alloc.result)
        module = _build_module("main", [alloc, free])
        pass_obj = MemoryPoolPass(rewrite=False)

        pass_obj.apply(Context(), module)

        interval = pass_obj.get_summary("main").intervals[0]
        assert str(interval.size_bytes_expr) == expected_size

    unsupported_type = _make_memory_type(shape=(2,), stride=(1,), element_type=StringAttr("bad"))
    unsupported_alloc = DmaAllocOp(_make_symbol_operands([2]), unsupported_type)
    unsupported_free = DmaFreeOp(unsupported_alloc.result)
    unsupported_module = _build_module("bad_dtype", [unsupported_alloc, unsupported_free])
    try:
        MemoryPoolPass(rewrite=False).apply(Context(), unsupported_module)
    except KernelCodeError as exc:
        assert "MemoryPoolUnsupportedDtype" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for unsupported dtype")

    unsupported_width = _make_memory_type(shape=(2,), stride=(1,), element_type=IntegerType(7))
    unsupported_width_alloc = DmaAllocOp(_make_symbol_operands([2]), unsupported_width)
    unsupported_width_free = DmaFreeOp(unsupported_width_alloc.result)
    unsupported_width_module = _build_module(
        "bad_integer_width",
        [unsupported_width_alloc, unsupported_width_free],
    )
    try:
        MemoryPoolPass(rewrite=False).apply(Context(), unsupported_width_module)
    except KernelCodeError as exc:
        assert "MemoryPoolUnsupportedDtype" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for unsupported integer width")

    symbolic_type = NnMemoryType(
        ArrayAttr([StringAttr("N"), IntAttr(4)]),
        ArrayAttr([IntAttr(4), IntAttr(1)]),
        i32,
        _make_space("shared"),
    )
    symbolic_alloc = DmaAllocOp(_make_symbol_operands(["N", 4]), symbolic_type)
    symbolic_free = DmaFreeOp(symbolic_alloc.result)
    symbolic_module = _build_module("symbolic", [symbolic_alloc, symbolic_free])
    symbolic_pass = MemoryPoolPass(rewrite=True)

    symbolic_pass.apply(Context(), symbolic_module)
    symbolic_summary = symbolic_pass.get_summary("symbolic")
    subview_ops = [
        op
        for op in _collect_ops_recursive(symbolic_module.body.block)
        if isinstance(op, DmaSubviewOp)
    ]
    reshape_ops = [
        op
        for op in _collect_ops_recursive(symbolic_module.body.block)
        if isinstance(op, DmaReshapeOp)
    ]

    assert "size_bytes=16*N" in symbolic_summary.to_text()
    assert "(#SM) -> 16*N" in symbolic_summary.to_text()
    assert len(subview_ops) == 1
    assert len(reshape_ops) == 1
    assert reshape_ops[0].result.type == symbolic_type


# TC-MP-020
# 功能说明: 验证公开 pass 对匿名 stride 与重复 free 的错误边界。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_public_invalid_shape_stride_and_free_edges
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_public_invalid_shape_stride_and_free_edges() -> None:
    anonymous_stride = NnMemoryType(
        ArrayAttr([IntAttr(2)]),
        ArrayAttr([StringAttr("?")]),
        i32,
        _make_space("global"),
    )
    anonymous_stride_alloc = DmaAllocOp(_make_symbol_operands([2]), anonymous_stride)
    anonymous_stride_free = DmaFreeOp(anonymous_stride_alloc.result)
    anonymous_stride_module = _build_module(
        "anonymous_stride",
        [anonymous_stride_alloc, anonymous_stride_free],
    )
    try:
        MemoryPoolPass(rewrite=False).apply(Context(), anonymous_stride_module)
    except KernelCodeError as exc:
        assert "MemoryPoolUnsupportedLayout" in str(exc)
        assert "non-contiguous" in str(exc) or "custom stride" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for anonymous stride")

    mem_type = _make_memory_type()
    duplicate_alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    duplicate_free_a = DmaFreeOp(duplicate_alloc.result)
    duplicate_free_b = DmaFreeOp(duplicate_alloc.result)
    duplicate_module = _build_module(
        "duplicate_free",
        [duplicate_alloc, duplicate_free_a, duplicate_free_b],
    )
    try:
        MemoryPoolPass(rewrite=False).apply(Context(), duplicate_module)
    except KernelCodeError as exc:
        assert "MemoryPoolLifetimeError: multiple dma.free for alloc" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for duplicate dma.free")


# TC-MP-021
# 功能说明: 验证 rewrite=True 遇到非 alloc 函数时保持公开 no-op 行为。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_rewrite_non_alloc_noop
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_rewrite_non_alloc_noop() -> None:
    module = _build_module("no_alloc", [_TestOp()])
    pass_obj = MemoryPoolPass(rewrite=True)

    pass_obj.apply(Context(), module)

    summary = pass_obj.get_summary("no_alloc")
    func_ops = [op for op in module.ops if isinstance(op, func.FuncOp)]
    block_ops = list(func_ops[0].body.blocks[0].ops)
    assert summary.pool_count == 0
    assert summary.intervals == ()
    assert not any(
        isinstance(op, (DmaAllocOp, DmaFreeOp, DmaSubviewOp, DmaReshapeOp, ArchGetDynamicMemoryOp))
        for op in block_ops
    )


# TC-MP-013
# 功能说明: 验证多 block 直线路径改写会报错。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_rewrite_multiple_blocks
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_rewrite_multiple_blocks() -> None:
    mem_type = _make_memory_type(space="shared")
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
        pass_obj.apply(Context(), module)
    except KernelCodeError as exc:
        assert "MemoryPoolUnsupportedControlFlow: function must have single block" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for multiple blocks")


# TC-MP-005
# 功能说明: 验证非 builtin.module 输入会报错。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_invalid_module
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_invalid_module() -> None:
    pass_obj = MemoryPoolPass(rewrite=False)
    try:
        pass_obj.apply(Context(), _TestOp())
    except KernelCodeError as exc:
        assert "MemoryPoolInvalidModule" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for invalid module")


# TC-MP-006
# 功能说明: 验证非 contiguous 布局会报错。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_non_contiguous_layout
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_non_contiguous_layout() -> None:
    mem_type = _make_memory_type(shape=(2, 4), stride=(5, 1))
    alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free = DmaFreeOp(alloc.result)
    module = _build_module("main", [alloc, free])
    pass_obj = MemoryPoolPass(rewrite=False)
    try:
        pass_obj.apply(Context(), module)
    except KernelCodeError as exc:
        assert "MemoryPoolUnsupportedLayout" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for non-contiguous layout")


# TC-MP-007
# 功能说明: 验证 alloc/free 不成对时按所在 region 结束记录生命周期。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_unpaired_alloc
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_unpaired_alloc() -> None:
    mem_type = _make_memory_type()
    alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    module = _build_module("main", [alloc])
    pass_obj = MemoryPoolPass(rewrite=False)
    pass_obj.apply(Context(), module)

    interval = pass_obj.get_summary("main").intervals[0]
    assert interval.begin_index == 0
    assert interval.end_index == 1
    assert str(interval.size_bytes_expr) == "32"


# TC-MP-008
# 功能说明: 验证匿名维度会报错。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_anonymous_dim
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
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
        pass_obj.apply(Context(), module)
    except KernelCodeError as exc:
        assert "MemoryPoolUnsupportedShape" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for anonymous shape")


# TC-MP-009
# 功能说明: 验证 alloc 结果非 nn.memory 会报错。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_alloc_non_memory
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_alloc_non_memory() -> None:
    alloc = DmaAllocOp(_make_symbol_operands([2, 4]), i32)
    free = DmaFreeOp(alloc.result)
    module = _build_module("main", [alloc, free])
    pass_obj = MemoryPoolPass(rewrite=False)
    try:
        pass_obj.apply(Context(), module)
    except KernelCodeError as exc:
        assert "MemoryPoolInvalidAlloc" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for alloc result type")


# TC-MP-014
# 功能说明: 验证 symbol.for 内 alloc 按线性切分规则生成 subview。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_symbol_for_reuse
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_symbol_for_reuse() -> None:
    mem_type = _make_memory_type(space="shared")
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

    pass_obj = MemoryPoolPass(rewrite=True, alignment=0)
    pass_obj.apply(Context(), module)
    summary = pass_obj.get_summary("pool_loop")

    offsets = {interval.name: interval.offset_bytes_expr for interval in summary.intervals}
    assert str(offsets["alloc1"]) == "0"
    assert str(offsets["alloc2"]) == "32"
    assert str(offsets["alloc3"]) == "64"

    func_ops = [op for op in module.ops if isinstance(op, func.FuncOp)]
    block = func_ops[0].body.blocks[0]
    subview_ops = [op for op in _collect_ops_recursive(block) if isinstance(op, DmaSubviewOp)]
    assert len(subview_ops) == 3
    view_offsets: list[int] = []
    for subview_op in subview_ops:
        offset0 = subview_op.offset[0]
        offset_type = offset0.type
        assert isinstance(offset_type, SymbolValueType)
        view_offsets.append(offset_type.get_value())
    assert view_offsets == [0, 8, 16]

    top_level_subviews = [op for op in block.ops if isinstance(op, DmaSubviewOp)]
    assert [op.offset[0].type.get_value() for op in top_level_subviews] == [0, 16]
    loop_subviews = [op for op in loop_op.body.blocks[0].ops if isinstance(op, DmaSubviewOp)]
    assert [op.offset[0].type.get_value() for op in loop_subviews] == [8]


# TC-MP-014B
# 功能说明: 验证 symbol.for 内动态 alloc 不会让后续函数体 subview offset 依赖 loop body SSA。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_symbol_for_dynamic_alloc_dominates_later_offset
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_symbol_for_dynamic_alloc_dominates_later_offset() -> None:
    static_type = _make_memory_type(space="shared")
    dynamic_type = NnMemoryType(
        ArrayAttr([StringAttr("N"), IntAttr(4)]),
        ArrayAttr([IntAttr(4), IntAttr(1)]),
        i32,
        _make_space("shared"),
    )
    n_value_op = _TestOp(result_types=[SymbolValueType.from_expr("N")])
    alloc1 = DmaAllocOp(_make_symbol_operands([2, 4]), static_type)

    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "4", "1")])
    alloc2 = DmaAllocOp([n_value_op.results[0]], dynamic_type)
    free2 = DmaFreeOp(alloc2.result)
    loop_block.add_ops([alloc2, free2])
    loop_op = SymbolForOp(_symbol_value(0), _symbol_value(4), _symbol_value(1), loop_block)

    alloc3 = DmaAllocOp(_make_symbol_operands([2, 4]), static_type)
    free3 = DmaFreeOp(alloc3.result)
    free1 = DmaFreeOp(alloc1.result)

    module = _build_module("pool_loop_dynamic", [n_value_op, alloc1, loop_op, alloc3, free3, free1])

    pass_obj = MemoryPoolPass(rewrite=True, alignment=0)
    pass_obj.apply(Context(), module)
    summary = pass_obj.get_summary("pool_loop_dynamic")

    symbol_n = sp.Symbol("N", integer=True, positive=True)
    offsets = {interval.name: interval.offset_bytes_expr for interval in summary.intervals}
    assert str(offsets["alloc1"]) == "0"
    assert str(offsets["alloc2"]) == "32"
    assert sp.simplify(offsets["alloc3"] - (sp.Integer(32) + sp.Integer(16) * symbol_n)) == 0

    func_ops = [op for op in module.ops if isinstance(op, func.FuncOp)]
    block = func_ops[0].body.blocks[0]
    top_level_subviews = [op for op in block.ops if isinstance(op, DmaSubviewOp)]
    assert [op.offset[0].type.get_value() for op in top_level_subviews] == [0, "4*N + 8"]

    loop_subviews = [op for op in loop_op.body.blocks[0].ops if isinstance(op, DmaSubviewOp)]
    assert [op.offset[0].type.get_value() for op in loop_subviews] == [8]

    loop_body_ops = set(loop_op.body.blocks[0].ops)
    func_offset_defs = _collect_defining_ops(top_level_subviews[1].offset[0])
    assert all(op not in loop_body_ops for op in func_offset_defs)


# TC-MP-015
# 功能说明: 验证 alloc 逃逸到 return 会被拒绝。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_escape_return
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_escape_return() -> None:
    mem_type = _make_memory_type()
    alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    block = Block()
    block.add_ops([alloc, func.ReturnOp(alloc.result)])
    func_op = func.FuncOp("main", FunctionType.from_lists([], [mem_type]), Region(block))
    module = ModuleOp([func_op])

    pass_obj = MemoryPoolPass(rewrite=False)
    try:
        pass_obj.apply(Context(), module)
    except KernelCodeError as exc:
        assert "MemoryPoolEscapingAlloc" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for escaping alloc")


# TC-MP-016
# 功能说明: 验证 alloc 在 loop 外、free 在 loop 内会被拒绝。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_invalid_lifetime_loop
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_invalid_lifetime_loop() -> None:
    mem_type = _make_memory_type()
    alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "4", "1")])
    loop_block.add_ops([DmaFreeOp(alloc.result)])
    loop_op = SymbolForOp(_symbol_value(0), _symbol_value(4), _symbol_value(1), loop_block)
    module = _build_module("main", [alloc, loop_op])

    pass_obj = MemoryPoolPass(rewrite=True)
    try:
        pass_obj.apply(Context(), module)
    except KernelCodeError as exc:
        assert "MemoryPoolLifetimeError: dma.free inside loop" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for invalid loop lifetime")


# TC-MP-017
# 功能说明: 验证未知 region 会触发拒绝路径。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_unsupported_region_escape
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_unsupported_region_escape() -> None:
    mem_type = _make_memory_type()
    alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free = DmaFreeOp(alloc.result)
    nested = ModuleOp([])
    module = _build_module("main", [nested, alloc, free])
    pass_obj = MemoryPoolPass(rewrite=False)
    try:
        pass_obj.apply(Context(), module)
    except KernelCodeError as exc:
        assert "MemoryPoolUnsupportedRegionEscape" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for unsupported region")


# TC-MP-018
# 功能说明: 验证 memory-pool 非法 alignment option 经 ircheck 公开入口稳定失败。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_ircheck_rejects_invalid_alignment_option
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_ircheck_rejects_invalid_alignment_option() -> None:
    result = run_ircheck_text(
        """// COMPILE_ARGS: --pass "memory-pool={rewrite=true,fold=false,alignment=-1}"
// CHECK: builtin.module

builtin.module {
  func.func @main() {
    func.return
  }
}
""",
        source_path="test/passes/test_memory_pool.py#invalid_alignment",
    )

    assert result.ok is False
    assert result.exit_code == 2
    assert result.message is not None
    assert "alignment must be non-negative integer" in result.message
