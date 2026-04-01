"""func_cost analysis pass tests.

创建者: jcc你莫辜负
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 func_cost pass 的 compute/read/write 统计与属性回写。
- 覆盖符号维度、常量输入、DMA 统计、未知 op 跳过等路径。

使用示例:
- pytest -q test/pass/test_analysis_func_cost.py

当前覆盖率信息:
- 未统计覆盖率（2026-03-28 19:49:06 +0800）。

覆盖率命令:
- pytest --cov=kernel_gen.passes.analysis.func_cost --cov-report=term-missing -q test/pass/test_analysis_func_cost.py

关联文件:
- 功能实现: kernel_gen/passes/analysis/func_cost.py
- Spec 文档: spec/pass/analysis/func_cost.md
- 测试文件: test/pass/test_analysis_func_cost.py
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
import sympy as sp
from xdsl.dialects import arith, func
from xdsl.dialects.builtin import (
    ArrayAttr,
    FunctionType,
    IntAttr,
    IntegerAttr,
    ModuleOp,
    StringAttr,
    f32,
    i1,
    i32,
)
from xdsl.irdl import IRDLOperation, attr_def, irdl_op_definition, operand_def, result_def
from xdsl.ir import Attribute, Block, Operation, Region, SSAValue

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp, DmaCopyOp, DmaDesliceOp, DmaLoadOp, DmaSliceOp, DmaStoreOp
from kernel_gen.dialect.nn import (
    NnAddOp,
    NnEqOp,
    NnMatmulOp,
    NnMemorySpaceAttr,
    NnMemoryType,
    NnMulOp,
)
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.analysis.analysis import analyze_kernel
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

pass_module = importlib.import_module("kernel_gen.passes.analysis.func_cost")
AnalyzeFuncCostPass = pass_module.AnalyzeFuncCostPass


@irdl_op_definition
class FakeNnAddOp(IRDLOperation):
    """测试用 nn.add op，允许常量 operand。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 用于构造 tensor + const 的测试输入。

    使用示例:
    - FakeNnAddOp(lhs, const, result_type, space)

    关联文件:
    - spec: spec/pass/analysis/func_cost.md
    - test: test/pass/test_analysis_func_cost.py
    - 功能实现: kernel_gen/passes/analysis/func_cost.py
    """

    name = "nn.add"

    lhs = operand_def(Attribute)
    rhs = operand_def(Attribute)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        super().__init__(
            operands=[lhs, rhs],
            result_types=[result_type],
            attributes={"space": space},
        )


@irdl_op_definition
class UnknownOp(IRDLOperation):
    """测试用未知 op。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 用于触发 func_cost 对未知 op 的告警分支。

    使用示例:
    - UnknownOp()

    关联文件:
    - spec: spec/pass/analysis/func_cost.md
    - test: test/pass/test_analysis_func_cost.py
    - 功能实现: kernel_gen/passes/analysis/func_cost.py
    """

    name = "test.unknown"

    def __init__(self) -> None:
        super().__init__(operands=[], result_types=[])


def _make_space(space_name: str) -> NnMemorySpaceAttr:
    """构造 nn.memory 空间属性。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 统一从名称创建 NnMemorySpaceAttr。

    使用示例:
    - space = _make_space("global")

    关联文件:
    - spec: spec/pass/analysis/func_cost.md
    - test: test/pass/test_analysis_func_cost.py
    - 功能实现: kernel_gen/passes/analysis/func_cost.py
    """

    return NnMemorySpaceAttr.from_name(space_name)


def _make_memory_type(
    shape: list[Attribute],
    element_type: Attribute,
    space_name: str,
    stride: list[Attribute] | None = None,
) -> NnMemoryType:
    """构造 nn.memory type。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 以 shape/stride/element_type/space 生成 NnMemoryType。

    使用示例:
    - mem_type = _make_memory_type([IntAttr(2), IntAttr(4)], f32, "global")

    关联文件:
    - spec: spec/pass/analysis/func_cost.md
    - test: test/pass/test_analysis_func_cost.py
    - 功能实现: kernel_gen/passes/analysis/func_cost.py
    """

    if stride is None:
        stride = [IntAttr(1) for _ in shape]
    return NnMemoryType(
        ArrayAttr(shape),
        ArrayAttr(stride),
        element_type,
        _make_space(space_name),
    )


def _build_module(
    arg_types: list[Attribute],
    result_type: Attribute,
    op_builder: Callable[[Block], tuple[list[Operation], SSAValue]],
) -> tuple[ModuleOp, func.FuncOp, Block]:
    """构造包含单个 func 的 module。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 根据 op_builder 生成 ops，并追加 func.return。

    使用示例:
    - module, func_op, block = _build_module([lhs_type, rhs_type], result_type, builder)

    关联文件:
    - spec: spec/pass/analysis/func_cost.md
    - test: test/pass/test_analysis_func_cost.py
    - 功能实现: kernel_gen/passes/analysis/func_cost.py
    """

    block = Block(arg_types=arg_types)
    ops, return_value = op_builder(block)
    if not ops:
        raise ValueError("op_builder must return at least one operation")
    for op in ops:
        block.add_op(op)
    block.add_op(func.ReturnOp(return_value))
    func_type = FunctionType.from_lists(arg_types, [result_type])
    func_op = func.FuncOp("main", func_type, Region(block))
    module = ModuleOp([func_op])
    return module, func_op, block


def _assert_expr_equal(actual: sp.Basic, expected: sp.Basic) -> None:
    """断言 sympy 表达式等价。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 使用 sympy.simplify 校验表达式差值为 0。

    使用示例:
    - _assert_expr_equal(summary.total_compute, expected)

    关联文件:
    - spec: spec/pass/analysis/func_cost.md
    - test: test/pass/test_analysis_func_cost.py
    - 功能实现: kernel_gen/passes/analysis/func_cost.py
    """

    diff = sp.simplify(actual - expected)
    if diff != 0:
        raise AssertionError(f"expr mismatch: actual={actual}, expected={expected}")


# FC-001
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-03-28 19:49:06 +0800
# 最近一次运行成功时间: 2026-03-28 19:49:06 +0800
# 测试目的: 输入 shape=[A,B] 的 nn.add，预期 compute=A*B。
# 使用示例: pytest -q test/pass/test_analysis_func_cost.py -k test_func_cost_nn_add_symbolic_shape
# 对应功能实现文件路径: kernel_gen/passes/analysis/func_cost.py
# 对应 spec 文件路径: spec/pass/analysis/func_cost.md
# 对应测试文件路径: test/pass/test_analysis_func_cost.py
def test_func_cost_nn_add_symbolic_shape() -> None:
    a_dim = StringAttr("A")
    b_dim = StringAttr("B")
    mem_type = _make_memory_type([a_dim, b_dim], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)
        return [add_op], add_op.results[0]

    module, _, _ = _build_module([mem_type, mem_type], mem_type, _builder)
    pass_obj = AnalyzeFuncCostPass()
    pass_obj.run(module)
    summary = pass_obj.get_summary("main")

    expected_numel = SymbolDim("A").get_symbol() * SymbolDim("B").get_symbol()
    op_cost = summary.ops[0]
    _assert_expr_equal(op_cost.compute, expected_numel)
    _assert_expr_equal(op_cost.read_bytes, expected_numel * 2 * 4)
    _assert_expr_equal(op_cost.write_bytes, expected_numel * 4)


# FC-002
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-03-28 19:49:06 +0800
# 最近一次运行成功时间: 2026-03-28 19:49:06 +0800
# 测试目的: 输入 tensor + const，预期常量不计读取流量。
# 使用示例: pytest -q test/pass/test_analysis_func_cost.py -k test_func_cost_tensor_plus_const
# 对应功能实现文件路径: kernel_gen/passes/analysis/func_cost.py
# 对应 spec 文件路径: spec/pass/analysis/func_cost.md
# 对应测试文件路径: test/pass/test_analysis_func_cost.py
def test_func_cost_tensor_plus_const() -> None:
    a_dim = StringAttr("A")
    b_dim = StringAttr("B")
    mem_type = _make_memory_type([a_dim, b_dim], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        const_op = arith.ConstantOp(IntegerAttr(1, i32))
        add_op = FakeNnAddOp(block.args[0], const_op.result, mem_type, space)
        return [const_op, add_op], add_op.results[0]

    module, _, _ = _build_module([mem_type], mem_type, _builder)
    pass_obj = AnalyzeFuncCostPass()
    pass_obj.run(module)
    summary = pass_obj.get_summary("main")

    expected_numel = SymbolDim("A").get_symbol() * SymbolDim("B").get_symbol()
    op_cost = summary.ops[0]
    _assert_expr_equal(op_cost.compute, expected_numel)
    _assert_expr_equal(op_cost.read_bytes, expected_numel * 4)
    _assert_expr_equal(op_cost.write_bytes, expected_numel * 4)


# FC-003
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-03-28 19:49:06 +0800
# 最近一次运行成功时间: 2026-03-28 19:49:06 +0800
# 测试目的: func 内串联两个逐元素 op，预期总量为逐项求和。
# 使用示例: pytest -q test/pass/test_analysis_func_cost.py -k test_func_cost_chain_accumulate
# 对应功能实现文件路径: kernel_gen/passes/analysis/func_cost.py
# 对应 spec 文件路径: spec/pass/analysis/func_cost.md
# 对应测试文件路径: test/pass/test_analysis_func_cost.py
def test_func_cost_chain_accumulate() -> None:
    a_dim = StringAttr("A")
    b_dim = StringAttr("B")
    mem_type = _make_memory_type([a_dim, b_dim], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)
        mul_op = NnMulOp(add_op.result, block.args[1], mem_type, space)
        return [add_op, mul_op], mul_op.result

    module, _, _ = _build_module([mem_type, mem_type], mem_type, _builder)
    pass_obj = AnalyzeFuncCostPass()
    pass_obj.run(module)
    summary = pass_obj.get_summary("main")

    expected_numel = SymbolDim("A").get_symbol() * SymbolDim("B").get_symbol()
    _assert_expr_equal(summary.total_compute, expected_numel * 2)
    _assert_expr_equal(summary.total_read_bytes, expected_numel * 4 * 4)
    _assert_expr_equal(summary.total_write_bytes, expected_numel * 4 * 2)


# FC-004
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-03-28 19:49:06 +0800
# 最近一次运行成功时间: 2026-03-28 19:49:06 +0800
# 测试目的: 输入 lhs=[M,K], rhs=[K,N] 的 nn.matmul，预期 compute=2*M*N*K。
# 使用示例: pytest -q test/pass/test_analysis_func_cost.py -k test_func_cost_matmul_formula
# 对应功能实现文件路径: kernel_gen/passes/analysis/func_cost.py
# 对应 spec 文件路径: spec/pass/analysis/func_cost.md
# 对应测试文件路径: test/pass/test_analysis_func_cost.py
def test_func_cost_matmul_formula() -> None:
    lhs_type = _make_memory_type([StringAttr("M"), StringAttr("K")], f32, "global")
    rhs_type = _make_memory_type([StringAttr("K"), StringAttr("N")], f32, "global")
    out_type = _make_memory_type([StringAttr("M"), StringAttr("N")], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        matmul_op = NnMatmulOp(block.args[0], block.args[1], out_type, space)
        return [matmul_op], matmul_op.results[0]

    module, _, _ = _build_module([lhs_type, rhs_type], out_type, _builder)
    pass_obj = AnalyzeFuncCostPass()
    pass_obj.run(module)
    summary = pass_obj.get_summary("main")

    m_dim = SymbolDim("M").get_symbol()
    n_dim = SymbolDim("N").get_symbol()
    k_dim = SymbolDim("K").get_symbol()
    expected_compute = sp.Integer(2) * m_dim * n_dim * k_dim
    expected_read = (m_dim * k_dim + k_dim * n_dim) * 4
    expected_write = m_dim * n_dim * 4

    op_cost = summary.ops[0]
    _assert_expr_equal(op_cost.compute, expected_compute)
    _assert_expr_equal(op_cost.read_bytes, expected_read)
    _assert_expr_equal(op_cost.write_bytes, expected_write)


# FC-005
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-03-28 19:49:06 +0800
# 最近一次运行成功时间: 2026-03-28 19:49:06 +0800
# 测试目的: 输入 dma.copy/load/store，预期 compute=0 且读写字节按元素数统计。
# 使用示例: pytest -q test/pass/test_analysis_func_cost.py -k test_func_cost_dma_memory_traffic
# 对应功能实现文件路径: kernel_gen/passes/analysis/func_cost.py
# 对应 spec 文件路径: spec/pass/analysis/func_cost.md
# 对应测试文件路径: test/pass/test_analysis_func_cost.py
def test_func_cost_dma_memory_traffic() -> None:
    mem_type = _make_memory_type([IntAttr(2), IntAttr(4)], f32, "global")
    space = _make_space("global")
    symbol_types = [
        SymbolValueType.from_expr("0"),
        SymbolValueType.from_expr("0"),
        SymbolValueType.from_expr("2"),
        SymbolValueType.from_expr("4"),
        SymbolValueType.from_expr("1"),
        SymbolValueType.from_expr("1"),
    ]

    arg_types = [mem_type, mem_type, *symbol_types]

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        copy_op = DmaCopyOp(block.args[0], block.args[1])
        load_op = DmaLoadOp(
            block.args[0],
            [block.args[2], block.args[3]],
            [block.args[4], block.args[5]],
            [block.args[6], block.args[7]],
            mem_type,
            space,
        )
        store_op = DmaStoreOp(
            load_op.result,
            block.args[1],
            [block.args[2], block.args[3]],
            [block.args[4], block.args[5]],
            [block.args[6], block.args[7]],
        )
        return [copy_op, load_op, store_op], load_op.result

    module, _, _ = _build_module(arg_types, mem_type, _builder)
    pass_obj = AnalyzeFuncCostPass()
    pass_obj.run(module)
    summary = pass_obj.get_summary("main")

    expected_bytes = sp.Integer(32)
    _assert_expr_equal(summary.total_compute, sp.Integer(0))
    _assert_expr_equal(summary.total_read_bytes, expected_bytes * 3)
    _assert_expr_equal(summary.total_write_bytes, expected_bytes * 3)


# FC-005 (sizes < shape)
# 创建者: jcc你莫辜负
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-02 06:18:51 +0800
# 最近一次运行成功时间: 2026-04-02 06:18:51 +0800
# 测试目的: sizes 小于 shape 时仅当前公开 DMA 分支参与统计，非公开 DMA 分支执行 skip+warning。
# 使用示例: pytest -q test/pass/test_analysis_func_cost.py -k test_func_cost_dma_sizes_smaller_than_shape
# 对应功能实现文件路径: kernel_gen/passes/analysis/func_cost.py
# 对应 spec 文件路径: spec/pass/analysis/func_cost.md
# 对应测试文件路径: test/pass/test_analysis_func_cost.py
def test_func_cost_dma_sizes_smaller_than_shape() -> None:
    full_type = _make_memory_type([IntAttr(2), IntAttr(4)], f32, "global")
    tile_type = _make_memory_type([IntAttr(1), IntAttr(2)], f32, "global")
    space = _make_space("global")
    symbol_types = [
        SymbolValueType.from_expr("0"),
        SymbolValueType.from_expr("0"),
        SymbolValueType.from_expr("1"),
        SymbolValueType.from_expr("2"),
        SymbolValueType.from_expr("1"),
        SymbolValueType.from_expr("1"),
    ]

    arg_types = [full_type, full_type, *symbol_types]

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        offsets = [block.args[2], block.args[3]]
        sizes = [block.args[4], block.args[5]]
        strides = [block.args[6], block.args[7]]
        load_op = DmaLoadOp(block.args[0], offsets, sizes, strides, tile_type, space)
        alloc_op = DmaAllocOp(sizes, tile_type)
        slice_op = DmaSliceOp(alloc_op.result, block.args[0], offsets, sizes, strides)
        store_op = DmaStoreOp(load_op.result, block.args[1], offsets, sizes, strides)
        deslice_op = DmaDesliceOp(load_op.result, block.args[1], offsets, sizes, strides, full_type)
        return [load_op, alloc_op, slice_op, store_op, deslice_op], deslice_op.result

    module, func_op, _ = _build_module(arg_types, full_type, _builder)
    pass_obj = AnalyzeFuncCostPass()
    with pytest.warns(UserWarning) as records:
        pass_obj.run(module)
    summary = pass_obj.get_summary("main")
    with pytest.warns(UserWarning) as kernel_records:
        kernel_summary = analyze_kernel(func_op)

    expected_bytes = sp.Integer(8)
    _assert_expr_equal(summary.total_compute, sp.Integer(0))
    _assert_expr_equal(summary.total_read_bytes, expected_bytes * 2)
    _assert_expr_equal(summary.total_write_bytes, expected_bytes * 2)
    assert [str(item.message) for item in records] == [
        "func_cost skip dma.alloc: unsupported op",
        "func_cost skip dma.slice: unsupported op",
        "func_cost skip dma.deslice: unsupported op",
    ]
    assert [str(item.message) for item in kernel_records] == [
        "analysis_kernel skip dma.alloc: unsupported op",
        "analysis_kernel skip dma.slice: unsupported op",
        "analysis_kernel skip dma.deslice: unsupported op",
    ]
    assert summary.op_costs == kernel_summary.op_costs
    assert summary.value_traffic == kernel_summary.value_traffic
    _assert_expr_equal(summary.total_compute, kernel_summary.total_compute)
    _assert_expr_equal(summary.total_read_bytes, kernel_summary.total_read_bytes)
    _assert_expr_equal(summary.total_write_bytes, kernel_summary.total_write_bytes)


# FC-006
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-03-28 19:49:06 +0800
# 最近一次运行成功时间: 2026-03-28 19:49:06 +0800
# 测试目的: 未知 op 被跳过并告警，支持 op 统计不受影响。
# 使用示例: pytest -q test/pass/test_analysis_func_cost.py -k test_func_cost_skips_unknown_op_with_warning
# 对应功能实现文件路径: kernel_gen/passes/analysis/func_cost.py
# 对应 spec 文件路径: spec/pass/analysis/func_cost.md
# 对应测试文件路径: test/pass/test_analysis_func_cost.py
def test_func_cost_skips_unknown_op_with_warning() -> None:
    mem_type = _make_memory_type([IntAttr(2), IntAttr(2)], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        unknown = UnknownOp()
        add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)
        return [unknown, add_op], add_op.result

    module, _, _ = _build_module([mem_type, mem_type], mem_type, _builder)
    pass_obj = AnalyzeFuncCostPass()
    with pytest.warns(UserWarning, match="func_cost skip test.unknown"):
        pass_obj.run(module)

    summary = pass_obj.get_summary("main")
    expected_numel = sp.Integer(4)
    _assert_expr_equal(summary.total_compute, expected_numel)


# FC-007
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-03-28 19:49:06 +0800
# 最近一次运行成功时间: 2026-03-28 19:49:06 +0800
# 测试目的: attach_attrs=True 时回写 analysis.* 属性。
# 使用示例: pytest -q test/pass/test_analysis_func_cost.py -k test_func_cost_attach_attrs
# 对应功能实现文件路径: kernel_gen/passes/analysis/func_cost.py
# 对应 spec 文件路径: spec/pass/analysis/func_cost.md
# 对应测试文件路径: test/pass/test_analysis_func_cost.py
def test_func_cost_attach_attrs() -> None:
    mem_type = _make_memory_type([IntAttr(2), IntAttr(3)], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)
        return [add_op], add_op.result

    module, func_op, _ = _build_module([mem_type, mem_type], mem_type, _builder)
    pass_obj = AnalyzeFuncCostPass(attach_attrs=True)
    pass_obj.run(module)

    assert isinstance(func_op, func.FuncOp)
    assert func_op.attributes["analysis.compute"].data == "6"
    assert func_op.attributes["analysis.read_bytes"].data == "48"
    assert func_op.attributes["analysis.write_bytes"].data == "24"


# FC-008
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-29 13:21:48 +0800
# 最近一次运行成功时间: 2026-03-29 13:21:48 +0800
# 测试目的: compare 输出为 i1 时，write_bytes 按 predicate_size 统计，且优先于 dtype_size_overrides。
# 使用示例: pytest -q test/pass/test_analysis_func_cost.py -k test_func_cost_compare_i1_uses_predicate_size
# 对应功能实现文件路径: kernel_gen/passes/analysis/func_cost.py
# 对应 spec 文件路径: spec/pass/analysis/func_cost.md
# 对应测试文件路径: test/pass/test_analysis_func_cost.py
def test_func_cost_compare_i1_uses_predicate_size() -> None:
    lhs_type = _make_memory_type([IntAttr(2), IntAttr(3)], f32, "global")
    result_type = _make_memory_type([IntAttr(2), IntAttr(3)], i1, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        eq_op = NnEqOp(block.args[0], block.args[1], result_type, space)
        return [eq_op], eq_op.result

    module, _, _ = _build_module([lhs_type, lhs_type], result_type, _builder)
    pass_obj = AnalyzeFuncCostPass(predicate_size=2, dtype_size_overrides={"i1": 8})
    pass_obj.run(module)
    summary = pass_obj.get_summary("main")

    op_cost = summary.ops[0]
    expected_numel = sp.Integer(6)
    _assert_expr_equal(op_cost.compute, expected_numel)
    _assert_expr_equal(op_cost.read_bytes, expected_numel * 2 * 4)
    _assert_expr_equal(op_cost.write_bytes, expected_numel * 2)


# FC-010
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-02 06:18:51 +0800
# 最近一次运行成功时间: 2026-04-02 06:18:51 +0800
# 测试目的: 验证 func_cost pass 在相同 args/predicate_size/dtype_size_overrides 下复用 analyze_kernel，且 attach_attrs 可观察。
# 使用示例: pytest -q test/pass/test_analysis_func_cost.py -k test_func_cost_matches_analyze_kernel_on_same_func
# 对应功能实现文件路径: kernel_gen/passes/analysis/func_cost.py
# 对应 spec 文件路径: spec/pass/analysis/func_cost.md
# 对应测试文件路径: test/pass/test_analysis_func_cost.py
def test_func_cost_matches_analyze_kernel_on_same_func() -> None:
    mem_type = _make_memory_type([StringAttr("A"), StringAttr("B")], f32, "global")
    out_type = _make_memory_type([StringAttr("A"), StringAttr("B")], i1, "global")
    space = _make_space("global")
    runtime_args = ["lhs", "rhs"]
    dtype_overrides = {"f32": 4, "i1": 8}

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        eq_op = NnEqOp(block.args[0], block.args[1], out_type, space)
        return [eq_op], eq_op.result

    module, func_op, _ = _build_module([mem_type, mem_type], out_type, _builder)
    pass_obj = AnalyzeFuncCostPass(
        predicate_size=2,
        attach_attrs=True,
        dtype_size_overrides=dtype_overrides,
        args={"main": runtime_args},
    )
    pass_obj.run(module)

    pass_summary = pass_obj.get_summary("main")
    kernel_summary = analyze_kernel(
        func_op,
        args=runtime_args,
        predicate_size=2,
        dtype_size_overrides=dtype_overrides,
        attach_attrs=True,
    )

    assert pass_summary.op_costs == kernel_summary.op_costs
    assert pass_summary.value_traffic == kernel_summary.value_traffic
    _assert_expr_equal(pass_summary.total_compute, kernel_summary.total_compute)
    _assert_expr_equal(pass_summary.total_read_bytes, kernel_summary.total_read_bytes)
    _assert_expr_equal(pass_summary.total_write_bytes, kernel_summary.total_write_bytes)
    assert func_op.attributes["analysis.compute"].data == str(kernel_summary.total_compute)
    assert func_op.attributes["analysis.read_bytes"].data == str(kernel_summary.total_read_bytes)
    assert func_op.attributes["analysis.write_bytes"].data == str(kernel_summary.total_write_bytes)
