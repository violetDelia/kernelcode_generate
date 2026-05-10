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

import pytest
from xdsl.context import Context
from xdsl.dialects import arith, func, scf
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IndexType, IntAttr, IntegerAttr, IntegerType, ModuleOp, StringAttr, bf16, f16, f32, f64, i1, i8, i16, i32, i64
from xdsl.dialects.test import TestOp as _TestOp
from xdsl.ir import Block, Operation, Region, SSAValue
from xdsl.utils.exceptions import VerifyException
import sympy as sp

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.arch import ArchGetDynamicMemoryOp
from kernel_gen.dialect.dma import DmaAllocOp, DmaFreeOp, DmaReshapeOp, DmaViewOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolExprAttr, SymbolForOp, SymbolIterType, SymbolValueType, SymbolYieldOp
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


def _symbol_expr_attr(value: int | str) -> SymbolExprAttr:
    """构造测试用 SymbolExprAttr 维度。"""

    return SymbolExprAttr.from_expr(str(value))


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
        ArrayAttr([_symbol_expr_attr(value) for value in shape]),
        ArrayAttr([_symbol_expr_attr(value) for value in stride]),
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
    - defining_ops = _collect_defining_ops(view.offsets[0])

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


# TC-MP-022
# 功能说明: 验证 MemoryPoolPass 公开构造参数与 registry option 的错误边界。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_public_option_matrix
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_public_option_matrix() -> None:
    invalid_ctor_cases = [
        ({"rewrite": "true"}, "rewrite must be bool"),
        ({"fold": "false"}, "fold must be bool"),
        ({"alignment": True}, "alignment must be non-negative integer"),
        ({"alignment": -1}, "alignment must be non-negative integer"),
    ]
    for kwargs, expected in invalid_ctor_cases:
        try:
            MemoryPoolPass(**kwargs)
        except KernelCodeError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError(f"expected KernelCodeError for {kwargs}")

    parsed = MemoryPoolPass.from_options({"rewrite": "off", "fold": "no", "alignment": "0"})
    assert parsed.rewrite is False
    assert parsed.fold is False
    assert parsed.alignment == 0

    invalid_option_cases = [
        ({"rewrite": "maybe"}, "rewrite must be bool"),
        ({"fold": "maybe"}, "fold must be bool"),
        ({"alignment": "invalid"}, "alignment must be non-negative integer"),
        ({"unknown": "true"}, "unknown option: unknown"),
    ]
    for options, expected in invalid_option_cases:
        try:
            MemoryPoolPass.from_options(options)
        except KernelCodeError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError(f"expected KernelCodeError for {options}")


# TC-MP-026
# 功能说明: 验证 summary 优先使用 dma.alloc 结果的公开 SSA name hint。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_summary_uses_alloc_name_hint
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_summary_uses_alloc_name_hint() -> None:
    mem_type = _make_memory_type(shape=(2,), stride=(1,), space="shared")
    alloc = DmaAllocOp(_make_symbol_operands([2]), mem_type)
    alloc.result.name_hint = "scratch"
    free = DmaFreeOp(alloc.result)
    module = _build_module("name_hint", [alloc, free])

    pass_obj = MemoryPoolPass(rewrite=False)
    pass_obj.apply(Context(), module)

    assert pass_obj.get_summary("name_hint").intervals[0].name == "scratch"


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
# 功能说明: 验证直线路径改写生成 dynamic memory + view + reshape。
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
    view_ops = [op for op in block.ops if isinstance(op, DmaViewOp)]
    reshape_ops = [op for op in block.ops if isinstance(op, DmaReshapeOp)]

    assert len(alloc_ops) == 0
    assert len(free_ops) == 0
    assert len(backing_ops) == 1
    assert len(view_ops) == 2
    assert len(reshape_ops) == 2

    backing_type = backing_ops[0].result.type
    assert isinstance(backing_type, NnMemoryType)
    assert len(backing_type.shape.data) == 1
    assert backing_type.element_type == i8
    view_offsets = [op.offsets[0].type.get_value() for op in view_ops]
    assert view_offsets == [0, 8]
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
    view_ops = [op for op in ops if isinstance(op, DmaViewOp)]

    assert backing_spaces == ["shared", "tlm1"]
    assert len(view_ops) == 2
    assert [op.result.type.space.space.data for op in view_ops] == ["shared", "tlm1"]


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

    view_ops = [
        op for op in _collect_ops_recursive(module.body.block) if isinstance(op, DmaViewOp)
    ]
    assert [op.offsets[0].type.get_value() for op in view_ops] == [0, 8]
    assert [op.shape[0].type.get_value() for op in view_ops] == [8, 10]


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
    view_ops = [op for op in _collect_ops_recursive(block) if isinstance(op, DmaViewOp)]
    assert len(view_ops) == 2
    offsets = []
    for view_op in view_ops:
        offset0 = view_op.offsets[0]
        offset_type = offset0.type
        assert isinstance(offset_type, SymbolValueType)
        offsets.append(offset_type.get_value())
    assert offsets == [0, 8]


# TC-MP-023
# 功能说明: 验证 rank-0/rank-1 allocation 经公开 rewrite 后的 flat view 与 reshape 形态。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_rewrite_rank_zero_and_rank_one
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_rewrite_rank_zero_and_rank_one() -> None:
    rank0_type = NnMemoryType(
        ArrayAttr([]),
        ArrayAttr([]),
        i32,
        _make_space("shared"),
    )
    rank0_alloc = DmaAllocOp([], rank0_type)
    rank0_free = DmaFreeOp(rank0_alloc.result)
    rank0_module = _build_module("rank0", [rank0_alloc, rank0_free])

    MemoryPoolPass(rewrite=True, alignment=0).apply(Context(), rank0_module)

    rank0_ops = _collect_ops_recursive(rank0_module.body.block)
    rank0_views = [op for op in rank0_ops if isinstance(op, DmaViewOp)]
    rank0_reshapes = [op for op in rank0_ops if isinstance(op, DmaReshapeOp)]
    assert [op.shape[0].type.get_value() for op in rank0_views] == [1]
    assert rank0_reshapes[0].result.type == rank0_type

    rank1_type = _make_memory_type(shape=(4,), stride=(1,), space="shared")
    rank1_alloc = DmaAllocOp(_make_symbol_operands([4]), rank1_type)
    rank1_free = DmaFreeOp(rank1_alloc.result)
    rank1_module = _build_module("rank1", [rank1_alloc, rank1_free])

    MemoryPoolPass(rewrite=True, alignment=0).apply(Context(), rank1_module)

    rank1_ops = _collect_ops_recursive(rank1_module.body.block)
    rank1_views = [op for op in rank1_ops if isinstance(op, DmaViewOp)]
    rank1_reshapes = [op for op in rank1_ops if isinstance(op, DmaReshapeOp)]
    assert [op.shape[0].type.get_value() for op in rank1_views] == [4]
    assert rank1_reshapes[0].result.type == rank1_type


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
        ArrayAttr([_symbol_expr_attr("N"), _symbol_expr_attr(4)]),
        ArrayAttr([_symbol_expr_attr(4), _symbol_expr_attr(1)]),
        i32,
        _make_space("shared"),
    )
    symbolic_alloc = DmaAllocOp(_make_symbol_operands(["N", 4]), symbolic_type)
    symbolic_free = DmaFreeOp(symbolic_alloc.result)
    symbolic_module = _build_module("symbolic", [symbolic_alloc, symbolic_free])
    symbolic_pass = MemoryPoolPass(rewrite=True)

    symbolic_pass.apply(Context(), symbolic_module)
    symbolic_summary = symbolic_pass.get_summary("symbolic")
    view_ops = [
        op
        for op in _collect_ops_recursive(symbolic_module.body.block)
        if isinstance(op, DmaViewOp)
    ]
    reshape_ops = [
        op
        for op in _collect_ops_recursive(symbolic_module.body.block)
        if isinstance(op, DmaReshapeOp)
    ]

    assert "size_bytes=16*N" in symbolic_summary.to_text()
    assert "(#SM) -> 16*N" in symbolic_summary.to_text()
    assert len(view_ops) == 1
    assert len(reshape_ops) == 1
    assert reshape_ops[0].result.type == symbolic_type


# TC-MP-007A
# 功能说明: 验证 full-rank `?` dynamic_shape 按 result layout 的 SymbolExprAttr 语义参与 rewrite。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_rewrite_binds_unknown_full_rank_dynamic_shape_to_result_layout
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_rewrite_binds_unknown_full_rank_dynamic_shape_to_result_layout() -> None:
    dynamic_type = NnMemoryType(
        ArrayAttr([_symbol_expr_attr("M"), _symbol_expr_attr("N")]),
        ArrayAttr([_symbol_expr_attr("N"), _symbol_expr_attr("1")]),
        f32,
        _make_space("shared"),
    )
    m_value = _TestOp(result_types=[SymbolValueType.from_expr("?")])
    n_value = _TestOp(result_types=[SymbolValueType.from_expr("?")])
    alloc = DmaAllocOp([m_value.results[0], n_value.results[0]], dynamic_type)
    free = DmaFreeOp(alloc.result)
    module = _build_module("unknown_full_rank_dynamic", [m_value, n_value, alloc, free])

    MemoryPoolPass(rewrite=True, alignment=0).apply(Context(), module)

    ops = _collect_ops_recursive(module.body.block)
    view_ops = [op for op in ops if isinstance(op, DmaViewOp)]
    reshape_ops = [op for op in ops if isinstance(op, DmaReshapeOp)]

    assert [op.shape[0].type.get_value() for op in view_ops] == ["M*N"]
    assert [[value.type.get_value() for value in op.shape] for op in reshape_ops] == [["M", "N"]]
    assert not any(isinstance(op, DmaAllocOp) for op in ops)


# TC-MP-007B
# 功能说明: 验证同一 block 内后续 full-rank `?` dynamic_shape 在自身 alloc 前定义时按自身 anchor 物化。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_rewrite_later_unknown_dynamic_shape_uses_own_anchor
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_rewrite_later_unknown_dynamic_shape_uses_own_anchor() -> None:
    first_type = NnMemoryType(
        ArrayAttr([_symbol_expr_attr("M")]),
        ArrayAttr([_symbol_expr_attr("1")]),
        f32,
        _make_space("shared"),
    )
    second_type = NnMemoryType(
        ArrayAttr([_symbol_expr_attr("N")]),
        ArrayAttr([_symbol_expr_attr("1")]),
        f32,
        _make_space("shared"),
    )
    first_dim = _TestOp(result_types=[SymbolValueType.from_expr("?")])
    first_alloc = DmaAllocOp([first_dim.results[0]], first_type)
    first_free = DmaFreeOp(first_alloc.result)
    second_dim = _TestOp(result_types=[SymbolValueType.from_expr("?")])
    second_alloc = DmaAllocOp([second_dim.results[0]], second_type)
    second_free = DmaFreeOp(second_alloc.result)
    module = _build_module(
        "unknown_later_dynamic",
        [first_dim, first_alloc, first_free, second_dim, second_alloc, second_free],
    )

    MemoryPoolPass(rewrite=True, alignment=0).apply(Context(), module)

    ops = _collect_ops_recursive(module.body.block)
    view_ops = [op for op in ops if isinstance(op, DmaViewOp)]
    reshape_ops = [op for op in ops if isinstance(op, DmaReshapeOp)]

    assert [op.offsets[0].type.get_value() for op in view_ops] == [0, "M"]
    assert [op.shape[0].type.get_value() for op in view_ops] == ["M", "N"]
    assert [[value.type.get_value() for value in op.shape] for op in reshape_ops] == [["M"], ["N"]]
    assert not any(isinstance(op, DmaAllocOp) for op in ops)


# TC-MP-020
# 功能说明: 验证公开 pass 对匿名 stride 与重复 free 的错误边界。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_public_invalid_shape_stride_and_free_edges
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_public_invalid_shape_stride_and_free_edges() -> None:
    anonymous_stride = NnMemoryType(
        ArrayAttr([_symbol_expr_attr(2)]),
        ArrayAttr([_symbol_expr_attr("?")]),
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

    with pytest.raises(VerifyException, match="shape dimensions must be SymbolExprAttr"):
        NnMemoryType(
            ArrayAttr([IntAttr(2)]),
            ArrayAttr([IntAttr(1)]),
            i32,
            _make_space("shared"),
        )


# TC-MP-024
# 功能说明: 验证公开 rewrite 对 dynamic shape、alignment 与生命周期顺序的拒绝边界。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_public_rewrite_error_edges
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_public_rewrite_error_edges() -> None:
    mem_type = _make_memory_type(space="shared")
    free_before_alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    free_before_free = DmaFreeOp(free_before_alloc.result)
    free_before_module = _build_module(
        "free_before_alloc",
        [free_before_free, free_before_alloc],
    )
    try:
        MemoryPoolPass(rewrite=False).apply(Context(), free_before_module)
    except KernelCodeError as exc:
        assert "MemoryPoolLifetimeError: dma.free before alloc" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for dma.free before alloc")

    dynamic_type = NnMemoryType(
        ArrayAttr([_symbol_expr_attr("N"), _symbol_expr_attr(4)]),
        ArrayAttr([_symbol_expr_attr(4), _symbol_expr_attr(1)]),
        i32,
        _make_space("shared"),
    )
    n_value = _TestOp(result_types=[SymbolValueType.from_expr("N")])
    dynamic_alloc = DmaAllocOp([n_value.results[0]], dynamic_type)
    dynamic_free = DmaFreeOp(dynamic_alloc.result)
    static_alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    static_free = DmaFreeOp(static_alloc.result)
    dynamic_alignment_module = _build_module(
        "dynamic_alignment",
        [n_value, dynamic_alloc, dynamic_free, static_alloc, static_free],
    )
    analysis_pass = MemoryPoolPass(rewrite=False, alignment=1024)
    analysis_pass.apply(Context(), dynamic_alignment_module)
    offsets = {interval.name: interval.offset_bytes_expr for interval in analysis_pass.get_summary("dynamic_alignment").intervals}
    symbol_n = sp.Symbol("N", integer=True, positive=True)
    assert str(offsets["alloc1"]) == "0"
    assert sp.simplify(offsets["alloc2"] - sp.Integer(16) * symbol_n) == 0

    try:
        MemoryPoolPass(rewrite=True, alignment=1024).apply(Context(), dynamic_alignment_module)
    except KernelCodeError as exc:
        assert "MemoryPoolUnsupportedAlignment: dynamic aligned offset is not supported" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for dynamic aligned offset")

    missing_operand_type = NnMemoryType(
        ArrayAttr([_symbol_expr_attr("M"), _symbol_expr_attr(4)]),
        ArrayAttr([_symbol_expr_attr(4), _symbol_expr_attr(1)]),
        i32,
        _make_space("shared"),
    )
    n_arg = _TestOp(result_types=[SymbolValueType.from_expr("N")])
    missing_alloc = DmaAllocOp([n_arg.results[0]], missing_operand_type)
    missing_free = DmaFreeOp(missing_alloc.result)
    missing_module = _build_module("missing_dynamic_operand", [n_arg, missing_alloc, missing_free])
    try:
        MemoryPoolPass(rewrite=True, alignment=0).apply(Context(), missing_module)
    except KernelCodeError as exc:
        assert "MemoryPoolUnsupportedShape: dynamic shape operand not found for M" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for missing dynamic shape operand")

    bad_dynamic_operand = _TestOp(result_types=[i32])
    bad_dynamic_alloc = DmaAllocOp([bad_dynamic_operand.results[0]], dynamic_type)
    bad_dynamic_free = DmaFreeOp(bad_dynamic_alloc.result)
    bad_dynamic_module = _build_module(
        "bad_dynamic_shape_type",
        [bad_dynamic_operand, bad_dynamic_alloc, bad_dynamic_free],
    )
    try:
        MemoryPoolPass(rewrite=True, alignment=0).apply(Context(), bad_dynamic_module)
    except KernelCodeError as exc:
        assert "MemoryPoolUnsupportedShape: dynamic shape must be !symbol.int" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for non-symbol dynamic shape operand")

    anonymous_type = NnMemoryType(
        ArrayAttr([_symbol_expr_attr("?")]),
        ArrayAttr([_symbol_expr_attr(1)]),
        i32,
        _make_space("shared"),
    )
    anonymous_value = _TestOp(result_types=[SymbolValueType.from_expr("N")])
    anonymous_alloc = DmaAllocOp([anonymous_value.results[0]], anonymous_type)
    anonymous_free = DmaFreeOp(anonymous_alloc.result)
    anonymous_module = _build_module("anonymous_rewrite", [anonymous_value, anonymous_alloc, anonymous_free])
    try:
        MemoryPoolPass(rewrite=True, alignment=0).apply(Context(), anonymous_module)
    except KernelCodeError as exc:
        assert "MemoryPoolUnsupportedShape: anonymous shape is not supported" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for anonymous rewrite shape")

    global_type = _make_memory_type(shape=(2, 4), stride=(4, 1), space="global")
    global_alloc = DmaAllocOp(_make_symbol_operands([2, 4]), global_type)
    global_free = DmaFreeOp(global_alloc.result)
    global_module = _build_module("global_rewrite", [global_alloc, global_free])
    global_pass = MemoryPoolPass(rewrite=True, alignment=0)
    global_pass.apply(Context(), global_module)
    global_summary = global_pass.get_summary("global_rewrite")
    global_ops = _collect_ops_recursive(global_module.body.block)
    assert global_summary.pool_count == 1
    assert global_summary.intervals[0].bucket_key == ("#GM",)
    assert any(isinstance(op, DmaAllocOp) for op in global_ops)
    assert any(isinstance(op, DmaFreeOp) for op in global_ops)
    assert not any(isinstance(op, (ArchGetDynamicMemoryOp, DmaViewOp, DmaReshapeOp)) for op in global_ops)

    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "4", "1")])
    loop_alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    loop_block.add_ops([loop_alloc])
    loop_op = SymbolForOp(_symbol_value(0), _symbol_value(4), _symbol_value(1), loop_block)
    outer_free = DmaFreeOp(loop_alloc.result)
    loop_escape_module = _build_module("loop_escape", [loop_op, outer_free])
    try:
        MemoryPoolPass(rewrite=True, alignment=0).apply(Context(), loop_escape_module)
    except KernelCodeError as exc:
        assert "MemoryPoolEscapingAlloc: alloc escapes current region" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for loop alloc escaping to outer free")

    loop_init = SymbolConstOp(1)
    carried_block = Block(
        arg_types=[
            SymbolIterType.from_bounds("0", "4", "1"),
            SymbolValueType.from_expr("ACC"),
        ],
    )
    carried_type = _make_memory_type(shape=("ACC",), stride=(1,), space="shared")
    carried_alloc = DmaAllocOp([carried_block.args[1]], carried_type)
    carried_free = DmaFreeOp(carried_alloc.result)
    carried_block.add_ops([carried_alloc, carried_free, SymbolYieldOp(carried_block.args[1])])
    carried_loop = SymbolForOp(
        _symbol_value(0),
        _symbol_value(4),
        _symbol_value(1),
        carried_block,
        init=loop_init.result,
        result_type=SymbolValueType.from_expr("ACC"),
    )
    later_alloc = DmaAllocOp(_make_symbol_operands([2]), _make_memory_type(shape=(2,), stride=(1,), space="shared"))
    later_free = DmaFreeOp(later_alloc.result)
    carried_module = _build_module(
        "loop_carried_dynamic",
        [loop_init, carried_loop, later_alloc, later_free],
    )
    try:
        MemoryPoolPass(rewrite=True, alignment=0).apply(Context(), carried_module)
    except KernelCodeError as exc:
        assert "dynamic loop alloc size does not dominate later offset" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for non-dominating dynamic loop size")

    mismatch_alloc_block = Block(arg_types=[SymbolIterType.from_bounds("0", "2", "1")])
    mismatch_alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    mismatch_alloc_block.add_ops([mismatch_alloc])
    mismatch_free_block = Block(arg_types=[SymbolIterType.from_bounds("0", "2", "1")])
    mismatch_free_block.add_ops([DmaFreeOp(mismatch_alloc.result)])
    mismatch_alloc_loop = SymbolForOp(_symbol_value(0), _symbol_value(2), _symbol_value(1), mismatch_alloc_block)
    mismatch_free_loop = SymbolForOp(_symbol_value(0), _symbol_value(2), _symbol_value(1), mismatch_free_block)
    mismatch_module = _build_module("loop_free_mismatch", [mismatch_alloc_loop, mismatch_free_loop])
    try:
        MemoryPoolPass(rewrite=False).apply(Context(), mismatch_module)
    except KernelCodeError as exc:
        assert "MemoryPoolLifetimeError: loop alloc/free mismatch" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for loop alloc/free mismatch")

    multiblock_loop = SymbolForOp(
        _symbol_value(0),
        _symbol_value(2),
        _symbol_value(1),
        [
            Block(arg_types=[SymbolIterType.from_bounds("0", "2", "1")]),
            Block(arg_types=[SymbolIterType.from_bounds("0", "2", "1")]),
        ],
    )
    multiblock_module = _build_module("multiblock_loop", [multiblock_loop])
    try:
        MemoryPoolPass(rewrite=False).apply(Context(), multiblock_module)
    except KernelCodeError as exc:
        assert "MemoryPoolUnsupportedRegionEscape: loop must have single block" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for multi-block symbol.for")


# TC-MP-025
# 功能说明: 验证 mixed dtype 的公开 rewrite 分支覆盖整除、不可整除与动态 ratio offset。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_mixed_dtype_rewrite_edges
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_mixed_dtype_rewrite_edges() -> None:
    f16_ok_type = _make_memory_type(shape=(2,), stride=(1,), element_type=f16, space="shared")
    f16_ok_alloc = DmaAllocOp(_make_symbol_operands([2]), f16_ok_type)
    f16_ok_free = DmaFreeOp(f16_ok_alloc.result)
    i32_ok_type = _make_memory_type(shape=(2,), stride=(1,), element_type=i32, space="shared")
    i32_ok_alloc = DmaAllocOp(_make_symbol_operands([2]), i32_ok_type)
    i32_ok_free = DmaFreeOp(i32_ok_alloc.result)
    static_ok_module = _build_module(
        "static_mixed_ok",
        [f16_ok_alloc, f16_ok_free, i32_ok_alloc, i32_ok_free],
    )

    MemoryPoolPass(rewrite=True, alignment=0).apply(Context(), static_ok_module)

    static_ok_views = [
        op for op in _collect_ops_recursive(static_ok_module.body.block) if isinstance(op, DmaViewOp)
    ]
    assert [op.offsets[0].type.get_value() for op in static_ok_views] == [0, 1]

    f16_second_type = _make_memory_type(shape=(4,), stride=(1,), element_type=f16, space="shared")
    f16_first_alloc = DmaAllocOp(_make_symbol_operands([2]), f16_ok_type)
    f16_first_free = DmaFreeOp(f16_first_alloc.result)
    f16_second_alloc = DmaAllocOp(_make_symbol_operands([4]), f16_second_type)
    f16_second_free = DmaFreeOp(f16_second_alloc.result)
    i32_third_alloc = DmaAllocOp(_make_symbol_operands([2]), i32_ok_type)
    i32_third_free = DmaFreeOp(i32_third_alloc.result)
    static_three_module = _build_module(
        "static_mixed_three",
        [
            f16_first_alloc,
            f16_first_free,
            f16_second_alloc,
            f16_second_free,
            i32_third_alloc,
            i32_third_free,
        ],
    )

    MemoryPoolPass(rewrite=True, alignment=0).apply(Context(), static_three_module)

    static_three_views = [
        op for op in _collect_ops_recursive(static_three_module.body.block) if isinstance(op, DmaViewOp)
    ]
    assert [op.offsets[0].type.get_value() for op in static_three_views] == [0, 2, 3]

    f16_type = _make_memory_type(shape=(3,), stride=(1,), element_type=f16, space="shared")
    f16_alloc = DmaAllocOp(_make_symbol_operands([3]), f16_type)
    f16_free = DmaFreeOp(f16_alloc.result)
    i32_type = _make_memory_type(shape=(2,), stride=(1,), element_type=i32, space="shared")
    i32_alloc = DmaAllocOp(_make_symbol_operands([2]), i32_type)
    i32_free = DmaFreeOp(i32_alloc.result)
    static_bad_module = _build_module("static_mixed_bad", [f16_alloc, f16_free, i32_alloc, i32_free])
    try:
        MemoryPoolPass(rewrite=True, alignment=0).apply(Context(), static_bad_module)
    except KernelCodeError as exc:
        assert "MemoryPoolTypedViewOutOfBounds: byte offset is not divisible by dtype size" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for indivisible mixed dtype offset")

    f16_align_alloc = DmaAllocOp(_make_symbol_operands([3]), f16_type)
    f16_align_free = DmaFreeOp(f16_align_alloc.result)
    i32_align_alloc = DmaAllocOp(_make_symbol_operands([2]), i32_type)
    i32_align_free = DmaFreeOp(i32_align_alloc.result)
    static_align_bad_module = _build_module(
        "static_mixed_alignment_bad",
        [f16_align_alloc, f16_align_free, i32_align_alloc, i32_align_free],
    )
    try:
        MemoryPoolPass(rewrite=True, alignment=1).apply(Context(), static_align_bad_module)
    except KernelCodeError as exc:
        assert "MemoryPoolTypedViewOutOfBounds: byte offset is not divisible by dtype size" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for aligned indivisible mixed dtype offset")

    n_bad = _TestOp(result_types=[SymbolValueType.from_expr("N")])
    dynamic_f16_type = _make_memory_type(shape=("N",), stride=(1,), element_type=f16, space="shared")
    dynamic_f16_alloc = DmaAllocOp([n_bad.results[0]], dynamic_f16_type)
    dynamic_f16_free = DmaFreeOp(dynamic_f16_alloc.result)
    i32_after_dynamic_alloc = DmaAllocOp(_make_symbol_operands([2]), i32_type)
    i32_after_dynamic_free = DmaFreeOp(i32_after_dynamic_alloc.result)
    dynamic_bad_module = _build_module(
        "dynamic_mixed_bad",
        [n_bad, dynamic_f16_alloc, dynamic_f16_free, i32_after_dynamic_alloc, i32_after_dynamic_free],
    )
    try:
        MemoryPoolPass(rewrite=True, alignment=0).apply(Context(), dynamic_bad_module)
    except KernelCodeError as exc:
        assert "MemoryPoolTypedViewOutOfBounds: byte offset is not divisible by dtype size" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for dynamic mixed dtype ratio")

    n_value = _TestOp(result_types=[SymbolValueType.from_expr("N")])
    dynamic_i32_type = _make_memory_type(shape=("N",), stride=(1,), element_type=i32, space="shared")
    dynamic_i32_alloc = DmaAllocOp([n_value.results[0]], dynamic_i32_type)
    dynamic_i32_free = DmaFreeOp(dynamic_i32_alloc.result)
    f16_type_ok = _make_memory_type(shape=(2,), stride=(1,), element_type=f16, space="shared")
    f16_alloc_ok = DmaAllocOp(_make_symbol_operands([2]), f16_type_ok)
    f16_free_ok = DmaFreeOp(f16_alloc_ok.result)
    dynamic_ratio_module = _build_module(
        "dynamic_mixed_ratio",
        [n_value, dynamic_i32_alloc, dynamic_i32_free, f16_alloc_ok, f16_free_ok],
    )

    MemoryPoolPass(rewrite=True, alignment=0).apply(Context(), dynamic_ratio_module)

    view_ops = [
        op for op in _collect_ops_recursive(dynamic_ratio_module.body.block) if isinstance(op, DmaViewOp)
    ]
    assert [op.offsets[0].type.get_value() for op in view_ops] == [0, "2*N"]

    n_ratio = _TestOp(result_types=[SymbolValueType.from_expr("N")])
    m_ratio = _TestOp(result_types=[SymbolValueType.from_expr("M")])
    i64_dynamic_type = _make_memory_type(shape=("N",), stride=(1,), element_type=i64, space="shared")
    i32_dynamic_type = _make_memory_type(shape=("M",), stride=(1,), element_type=i32, space="shared")
    i16_tail_type = _make_memory_type(shape=(2,), stride=(1,), element_type=i16, space="shared")
    i64_dynamic_alloc = DmaAllocOp([n_ratio.results[0]], i64_dynamic_type)
    i64_dynamic_free = DmaFreeOp(i64_dynamic_alloc.result)
    i32_dynamic_alloc = DmaAllocOp([m_ratio.results[0]], i32_dynamic_type)
    i32_dynamic_free = DmaFreeOp(i32_dynamic_alloc.result)
    i16_tail_alloc = DmaAllocOp(_make_symbol_operands([2]), i16_tail_type)
    i16_tail_free = DmaFreeOp(i16_tail_alloc.result)
    multi_ratio_module = _build_module(
        "dynamic_mixed_multi_ratio",
        [
            n_ratio,
            i64_dynamic_alloc,
            i64_dynamic_free,
            m_ratio,
            i32_dynamic_alloc,
            i32_dynamic_free,
            i16_tail_alloc,
            i16_tail_free,
        ],
    )

    MemoryPoolPass(rewrite=True, alignment=0).apply(Context(), multi_ratio_module)

    multi_ratio_views = [
        op for op in _collect_ops_recursive(multi_ratio_module.body.block) if isinstance(op, DmaViewOp)
    ]
    assert [op.offsets[0].type.get_value() for op in multi_ratio_views] == [
        0,
        "2*N",
        "2*M + 4*N",
    ]


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
        isinstance(op, (DmaAllocOp, DmaFreeOp, DmaViewOp, DmaReshapeOp, ArchGetDynamicMemoryOp))
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
        ArrayAttr([_symbol_expr_attr("?"), _symbol_expr_attr(4)]),
        ArrayAttr([_symbol_expr_attr(4), _symbol_expr_attr(1)]),
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
# 功能说明: 验证 symbol.for 内 alloc 按线性切分规则生成 view。
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
    view_ops = [op for op in _collect_ops_recursive(block) if isinstance(op, DmaViewOp)]
    assert len(view_ops) == 3
    view_offsets: list[int] = []
    for view_op in view_ops:
        offset0 = view_op.offsets[0]
        offset_type = offset0.type
        assert isinstance(offset_type, SymbolValueType)
        view_offsets.append(offset_type.get_value())
    assert view_offsets == [0, 8, 16]

    top_level_views = [op for op in block.ops if isinstance(op, DmaViewOp)]
    assert [op.offsets[0].type.get_value() for op in top_level_views] == [0, 16]
    loop_views = [op for op in loop_op.body.blocks[0].ops if isinstance(op, DmaViewOp)]
    assert [op.offsets[0].type.get_value() for op in loop_views] == [8]


# TC-MP-014B
# 功能说明: 验证 symbol.for 内动态 alloc 不会让后续函数体 view offset 依赖 loop body SSA。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_symbol_for_dynamic_alloc_dominates_later_offset
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_symbol_for_dynamic_alloc_dominates_later_offset() -> None:
    static_type = _make_memory_type(space="shared")
    dynamic_type = NnMemoryType(
        ArrayAttr([_symbol_expr_attr("N"), _symbol_expr_attr(4)]),
        ArrayAttr([_symbol_expr_attr(4), _symbol_expr_attr(1)]),
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
    top_level_views = [op for op in block.ops if isinstance(op, DmaViewOp)]
    assert [op.offsets[0].type.get_value() for op in top_level_views] == [0, "4*N + 8"]

    loop_views = [op for op in loop_op.body.blocks[0].ops if isinstance(op, DmaViewOp)]
    assert [op.offsets[0].type.get_value() for op in loop_views] == [8]

    loop_body_ops = set(loop_op.body.blocks[0].ops)
    func_offset_defs = _collect_defining_ops(top_level_views[1].offsets[0])
    assert all(op not in loop_body_ops for op in func_offset_defs)


# TC-MP-014C
# 功能说明: 验证外层 symbol.for 内 alloc 可被内层 symbol.for 使用，rewrite 后不误判为逃逸。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_symbol_for_outer_alloc_can_feed_inner_loop
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_symbol_for_outer_alloc_can_feed_inner_loop() -> None:
    mem_type = _make_memory_type(space="shared")
    outer_block = Block(arg_types=[SymbolIterType.from_bounds("0", "3", "1")])
    outer_alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)

    inner_block = Block(arg_types=[SymbolIterType.from_bounds("0", "2", "1")])
    dim0 = SymbolConstOp(2)
    dim1 = SymbolConstOp(4)
    inner_reshape = DmaReshapeOp(outer_alloc.result, [dim0.result, dim1.result], mem_type)
    inner_block.add_ops([dim0, dim1, inner_reshape])
    inner_loop = SymbolForOp(_symbol_value(0), _symbol_value(2), _symbol_value(1), inner_block)
    outer_free = DmaFreeOp(outer_alloc.result)
    outer_block.add_ops([outer_alloc, inner_loop, outer_free])
    outer_loop = SymbolForOp(_symbol_value(0), _symbol_value(3), _symbol_value(1), outer_block)
    module = _build_module("outer_alloc_inner_use", [outer_loop])

    MemoryPoolPass(rewrite=True, alignment=0).apply(Context(), module)

    ops = _collect_ops_recursive(module.body.block)
    outer_ops = list(outer_block.ops)
    inner_ops = list(inner_block.ops)
    replacement_reshape = next(op for op in outer_ops if isinstance(op, DmaReshapeOp))
    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in ops)
    assert any(isinstance(op, ArchGetDynamicMemoryOp) for op in ops)
    assert any(isinstance(op, DmaViewOp) for op in outer_ops)
    assert inner_reshape.source is replacement_reshape.result
    assert inner_reshape in inner_ops


# TC-MP-014D
# 功能说明: 验证 scf.for 内 alloc 通过函数级 backing memory 与 loop body view 改写。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_scf_for_alloc_uses_function_backing
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_scf_for_alloc_uses_function_backing() -> None:
    mem_type = _make_memory_type(space="shared")
    start = arith.ConstantOp(IntegerAttr(0, IndexType()))
    end = arith.ConstantOp(IntegerAttr(2, IndexType()))
    step = arith.ConstantOp(IntegerAttr(1, IndexType()))
    loop_block = Block(arg_types=[IndexType()])
    loop_alloc = DmaAllocOp(_make_symbol_operands([2, 4]), mem_type)
    loop_free = DmaFreeOp(loop_alloc.result)
    loop_block.add_ops([loop_alloc, loop_free, scf.YieldOp()])
    loop = scf.ForOp(start.result, end.result, step.result, [], loop_block)
    module = _build_module("scf_loop_alloc", [start, end, step, loop])

    MemoryPoolPass(rewrite=True, alignment=0).apply(Context(), module)

    func_block = next(op for op in module.ops if isinstance(op, func.FuncOp)).body.blocks[0]
    loop_body_ops = list(loop_block.ops)
    assert any(isinstance(op, ArchGetDynamicMemoryOp) for op in func_block.ops)
    assert any(isinstance(op, DmaViewOp) for op in loop_body_ops)
    assert any(isinstance(op, DmaReshapeOp) for op in loop_body_ops)
    assert not any(isinstance(op, (DmaAllocOp, DmaFreeOp)) for op in _collect_ops_recursive(func_block))


# TC-MP-014E
# 功能说明: 验证函数参数 symbol 维度可支配 memory-pool metadata 与 reshape shape。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_function_arg_dynamic_shape_rewrite
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_function_arg_dynamic_shape_rewrite() -> None:
    dynamic_type = NnMemoryType(
        ArrayAttr([_symbol_expr_attr("N")]),
        ArrayAttr([_symbol_expr_attr("1")]),
        f32,
        _make_space("shared"),
    )
    block = Block(arg_types=[SymbolValueType.from_expr("N")])
    alloc = DmaAllocOp([block.args[0]], dynamic_type)
    free = DmaFreeOp(alloc.result)
    block.add_ops([alloc, free, func.ReturnOp()])
    func_op = func.FuncOp(
        "function_arg_dynamic",
        FunctionType.from_lists([SymbolValueType.from_expr("N")], []),
        Region(block),
    )
    module = ModuleOp([func_op])

    MemoryPoolPass(rewrite=True, alignment=0).apply(Context(), module)

    reshape_ops = [op for op in _collect_ops_recursive(block) if isinstance(op, DmaReshapeOp)]
    assert len(reshape_ops) == 1
    assert list(reshape_ops[0].shape) == [block.args[0]]
    assert not any(isinstance(op, DmaAllocOp) for op in _collect_ops_recursive(block))


# TC-MP-014F
# 功能说明: 验证 loop body 内 alloc 可使用同 block 中位于 alloc 前的动态维 SSA。
# 使用示例: pytest -q test/passes/test_memory_pool.py -k test_memory_pool_loop_local_dynamic_shape_rewrite
# 对应功能实现文件路径: kernel_gen/passes/memory_pool.py
# 对应 spec 文件路径: spec/pass/lowering/memory_pool.md
# 对应测试文件路径: test/passes/test_memory_pool.py
def test_memory_pool_loop_local_dynamic_shape_rewrite() -> None:
    dynamic_type = NnMemoryType(
        ArrayAttr([_symbol_expr_attr("N")]),
        ArrayAttr([_symbol_expr_attr("1")]),
        i32,
        _make_space("shared"),
    )
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "4", "1")])
    n_value = _TestOp(result_types=[SymbolValueType.from_expr("N")])
    alloc = DmaAllocOp([n_value.results[0]], dynamic_type)
    free = DmaFreeOp(alloc.result)
    loop_block.add_ops([n_value, alloc, free])
    loop = SymbolForOp(_symbol_value(0), _symbol_value(4), _symbol_value(1), loop_block)
    module = _build_module("loop_local_dynamic", [loop])

    MemoryPoolPass(rewrite=True, alignment=0).apply(Context(), module)

    reshape_ops = [op for op in _collect_ops_recursive(loop_block) if isinstance(op, DmaReshapeOp)]
    assert len(reshape_ops) == 1
    assert list(reshape_ops[0].shape) == [n_value.results[0]]
    assert not any(isinstance(op, DmaAllocOp) for op in _collect_ops_recursive(loop_block))


# TC-MP-015
# 功能说明: 验证 analysis-only 允许 escaping alloc 摘要，rewrite 仍拒绝 escaping alloc。
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
    pass_obj.apply(Context(), module)
    summary = pass_obj.get_summary("main")
    assert len(summary.intervals) == 1
    assert summary.intervals[0].begin_index == 0

    rewrite_pass = MemoryPoolPass(rewrite=True)
    try:
        rewrite_pass.apply(Context(), module)
    except KernelCodeError as exc:
        assert "MemoryPoolEscapingAlloc" in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for escaping alloc rewrite")


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
