"""Analysis tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖逐元素算术/比较、broadcast、matmul 与函数级聚合统计。

使用示例:
- pytest -q test/analysis/test_analysis.py

覆盖率信息:
- 当前覆盖率: `100%` (`kernel_gen/analysis/analysis.py`，2026-03-22 15:24:43 +0800)。
- 达标判定: 已达到 `95%` 覆盖率达标线。
- 当前覆盖对象: `kernel_gen/analysis/analysis.py`。

覆盖率命令:
- coverage run -m pytest -q test/analysis/test_analysis.py && coverage report --include=kernel_gen/analysis/analysis.py -m

关联文件:
- 功能实现: kernel_gen/analysis/analysis.py
- Spec 文档: spec/analysis/analysis_kernel.md
- 测试文件: test/analysis/test_analysis.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from collections.abc import Callable

import sympy as sp
import pytest
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

from kernel_gen.analysis.analysis import (
    AnalysisConfig,
    AnalysisError,
    AnalysisResult,
    AnalysisSummary,
    AnalyzeKernelSummary,
    MemoryRef,
    OpStats,
    Operation,
    ValueTraffic,
    analysis,
    analyze_add,
    analyze_elementwise,
    analyze_broadcast,
    analyze_broadcast_op,
    analyze_eq,
    analyze_kernel,
    analyze_function,
    analyze_matmul,
    analyze_matmul_op,
)
import kernel_gen.analysis.analysis as analysis_module
from kernel_gen.dialect.dma import (
    DmaAllocOp,
    DmaCopyOp,
    DmaDesliceOp,
    DmaFreeOp,
    DmaLoadOp,
    DmaSliceOp,
    DmaStoreOp,
)
from kernel_gen.dialect.nn import (
    NnAddOp,
    NnEqOp,
    NnMatmulOp,
    NnMemorySpaceAttr,
    NnMemoryType,
    NnMulOp,
)
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


@irdl_op_definition
class FakeNnAddOp(IRDLOperation):
    """测试用 nn.add op，允许常量 operand。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 用于构造 memory + const 的测试输入。

    使用示例:
    - FakeNnAddOp(lhs, const, result_type, space)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
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

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 用于触发 analyze_kernel 的 unknown op warning。

    使用示例:
    - UnknownOp()

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    name = "test.unknown"

    def __init__(self) -> None:
        super().__init__(operands=[], result_types=[])


@irdl_op_definition
class FakeKernelScalarAddOp(IRDLOperation):
    """测试用标量 kernel.add op。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 为 A1 的单 op 统一入口测试提供 `kernel.add(i32, i32) -> i32` 形态。

    使用示例:
    - FakeKernelScalarAddOp(i32)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    name = "kernel.add"

    lhs = operand_def(Attribute)
    rhs = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(
        self,
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        result_type: Attribute,
    ) -> None:
        super().__init__(operands=[lhs, rhs], result_types=[result_type])


def _make_space(space_name: str) -> NnMemorySpaceAttr:
    """构造 nn.memory 空间属性。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一从名称创建 NnMemorySpaceAttr。

    使用示例:
    - space = _make_space("global")

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    return NnMemorySpaceAttr.from_name(space_name)


def _make_memory_type(
    shape: list[Attribute],
    element_type: Attribute,
    space_name: str,
    stride: list[Attribute] | None = None,
) -> NnMemoryType:
    """构造 nn.memory type。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 以 shape/stride/element_type/space 生成 NnMemoryType。

    使用示例:
    - mem_type = _make_memory_type([IntAttr(2), IntAttr(4)], f32, "global")

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
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

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 根据 op_builder 生成 ops，并追加 func.return。

    使用示例:
    - module, func_op, block = _build_module([lhs_type], result_type, builder)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
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

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 使用 sympy.simplify 校验表达式差值为 0。

    使用示例:
    - _assert_expr_equal(summary.total_compute, expected)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    assert sp.simplify(actual - expected) == 0


def _value_traffic_map(summary: AnalyzeKernelSummary) -> dict[str, ValueTraffic]:
    """将 value_traffic 列表转为 dict。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 以 value_key 为 key 构造映射，方便断言。

    使用示例:
    - traffic = _value_traffic_map(summary)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    return {item.value_key: item for item in summary.value_traffic}


# AN-001
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 add 的计算量与搬运量统计。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_add_counts
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_add_counts() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    out = Memory(["A", "B"], NumericType.Float32)
    stats = analyze_add(lhs, rhs, out)
    a, b, s = sp.Symbol("A"), sp.Symbol("B"), sp.Symbol("S")
    assert stats.compute == a * b
    assert stats.read_bytes == 2 * a * b * s
    assert stats.write_bytes == a * b * s

    sized = analyze_add(lhs, rhs, out, dtype_size=4)
    assert sized.read_bytes == 2 * a * b * sp.Integer(4)
    assert sized.write_bytes == a * b * sp.Integer(4)


# AN-002
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 eq 的计算量与搬运量统计。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_eq_counts
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_eq_counts() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    out = Memory(["A", "B"], NumericType.Int32)
    stats = analyze_eq(lhs, rhs, out)
    a, b, s, p = sp.Symbol("A"), sp.Symbol("B"), sp.Symbol("S"), sp.Symbol("P")
    assert stats.compute == a * b
    assert stats.read_bytes == 2 * a * b * s
    assert stats.write_bytes == a * b * p


# AN-003
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 broadcast 的读写量统计。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_broadcast_counts
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_broadcast_counts() -> None:
    inp = Memory([1, "N"], NumericType.Float32)
    out = Memory(["M", "N"], NumericType.Float32)
    stats = analyze_broadcast_op(inp, out)
    m, n, s = sp.Symbol("M"), sp.Symbol("N"), sp.Symbol("S")
    assert stats.compute == 0
    assert stats.read_bytes == n * s
    assert stats.write_bytes == m * n * s


# AN-004
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 matmul 的计算量与读写量统计。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_matmul_counts
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_matmul_counts() -> None:
    lhs = Memory(["M", "K"], NumericType.Float32)
    rhs = Memory(["K", "N"], NumericType.Float32)
    out = Memory(["M", "N"], NumericType.Float32)
    stats = analyze_matmul_op(lhs, rhs, out)
    m, n, k, s = sp.Symbol("M"), sp.Symbol("N"), sp.Symbol("K"), sp.Symbol("S")
    assert stats.compute == 2 * m * n * k
    expected_read = (m * k + k * n) * s
    assert sp.simplify(stats.read_bytes - expected_read) == 0
    assert stats.write_bytes == m * n * s


# AN-005
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证函数级聚合统计会计入中间物化。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_materialized_intermediate
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_materialized_intermediate() -> None:
    a1 = Memory(["A", "B"], NumericType.Float32)
    a2 = Memory(["A", "B"], NumericType.Float32)
    a3 = Memory(["A", "B"], NumericType.Float32)
    c = Memory(["A", "B"], NumericType.Float32)
    d = Memory(["A", "B"], NumericType.Float32)

    ops = [
        Operation("add", [MemoryRef("A1", a1), MemoryRef("A2", a2)], MemoryRef("C", c)),
        Operation("mul", [MemoryRef("C", c), MemoryRef("A3", a3)], MemoryRef("D", d)),
    ]
    summary = analyze_function(ops)
    assert isinstance(summary, AnalysisSummary)

    a, b, s = sp.Symbol("A"), sp.Symbol("B"), sp.Symbol("S")
    assert summary.total.compute == 2 * a * b
    assert summary.total.read_bytes == 4 * a * b * s
    assert summary.total.write_bytes == 2 * a * b * s


# AN-006
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证函数级聚合在融合场景不计入中间物化。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_fused_intermediate
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_fused_intermediate() -> None:
    a1 = Memory(["A", "B"], NumericType.Float32)
    a2 = Memory(["A", "B"], NumericType.Float32)
    a3 = Memory(["A", "B"], NumericType.Float32)
    c = Memory(["A", "B"], NumericType.Float32)
    d = Memory(["A", "B"], NumericType.Float32)

    ops = [
        Operation(
            "add",
            [MemoryRef("A1", a1), MemoryRef("A2", a2)],
            MemoryRef("C", c),
            materialize=False,
        ),
        Operation("mul", [MemoryRef("C", c), MemoryRef("A3", a3)], MemoryRef("D", d)),
    ]
    summary = analyze_function(ops)

    a, b, s = sp.Symbol("A"), sp.Symbol("B"), sp.Symbol("S")
    assert summary.total.compute == 2 * a * b
    assert summary.total.read_bytes == 3 * a * b * s
    assert summary.total.write_bytes == a * b * s


# AN-007
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 read_mask 长度不匹配时报 AnalysisError。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_read_mask_length_mismatch
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_read_mask_length_mismatch() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    out = Memory(["A", "B"], NumericType.Float32)
    with pytest.raises(AnalysisError, match="read_mask length mismatch"):
        analyze_elementwise(lhs, rhs, out, read_mask=[True])


# AN-008
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 analyze_function 输入数量不匹配时报 AnalysisError。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_function_inputs_mismatch
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_function_inputs_mismatch() -> None:
    a1 = Memory(["A", "B"], NumericType.Float32)
    out = Memory(["A", "B"], NumericType.Float32)
    ops = [Operation("add", [MemoryRef("A1", a1)], MemoryRef("C", out))]
    with pytest.raises(AnalysisError, match="Operation inputs length mismatch"):
        analyze_function(ops)


# AN-009
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 OpStats 与非 OpStats 相加返回 NotImplemented。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_opstats_add_returns_notimplemented
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_opstats_add_returns_notimplemented() -> None:
    stats = OpStats(sp.Integer(1), sp.Integer(2), sp.Integer(3))
    assert stats.__add__("invalid") is NotImplemented


# AN-010
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 _to_symbol 遇到非法类型抛出 AnalysisError。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_to_symbol_rejects_invalid_type
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_to_symbol_rejects_invalid_type() -> None:
    with pytest.raises(AnalysisError, match="Unsupported dimension"):
        analysis_module._to_symbol(1.5)


# AN-011
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证逐元素输出 shape 不一致时抛 AnalysisError。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_elementwise_output_shape_mismatch
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_elementwise_output_shape_mismatch() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    out = Memory(["A", "C"], NumericType.Float32)
    with pytest.raises(AnalysisError, match="Elementwise output shape mismatch"):
        analyze_add(lhs, rhs, out)


# AN-012
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 broadcast 形状不合法时抛 AnalysisError。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_broadcast_shape_mismatch
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_broadcast_shape_mismatch() -> None:
    inp = Memory(["A", "B"], NumericType.Float32)
    out_rank = Memory(["B"], NumericType.Float32)
    with pytest.raises(AnalysisError, match="Broadcast output rank must be"):
        analyze_broadcast_op(inp, out_rank)

    out_dim = Memory(["A", "C"], NumericType.Float32)
    with pytest.raises(AnalysisError, match="Broadcast dimension mismatch"):
        analyze_broadcast_op(inp, out_dim)


# AN-013
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 broadcast read_mask 长度不正确时抛 AnalysisError。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_broadcast_read_mask_length_mismatch
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_broadcast_read_mask_length_mismatch() -> None:
    inp = Memory([1, "N"], NumericType.Float32)
    out = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(AnalysisError, match="read_mask length mismatch"):
        analyze_broadcast(inp, out, read_mask=[True, False])


# AN-014
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 matmul 形状不合法时抛 AnalysisError。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_matmul_shape_mismatch
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_matmul_shape_mismatch() -> None:
    lhs = Memory(["M"], NumericType.Float32)
    rhs = Memory(["M", "N"], NumericType.Float32)
    out = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(AnalysisError, match="Matmul requires rank-2 tensors"):
        analyze_matmul_op(lhs, rhs, out)

    lhs = Memory(["M", "K"], NumericType.Float32)
    rhs = Memory(["Q", "N"], NumericType.Float32)
    out = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(AnalysisError, match="Matmul inner dimension mismatch"):
        analyze_matmul_op(lhs, rhs, out)

    lhs = Memory(["M", "K"], NumericType.Float32)
    rhs = Memory(["K", "N"], NumericType.Float32)
    out = Memory(["M", "Q"], NumericType.Float32)
    with pytest.raises(AnalysisError, match="Matmul output shape mismatch"):
        analyze_matmul_op(lhs, rhs, out)


# AN-015
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 matmul read_mask 长度不正确时抛 AnalysisError。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_matmul_read_mask_length_mismatch
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_matmul_read_mask_length_mismatch() -> None:
    lhs = Memory(["M", "K"], NumericType.Float32)
    rhs = Memory(["K", "N"], NumericType.Float32)
    out = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(AnalysisError, match="read_mask length mismatch"):
        analyze_matmul(lhs, rhs, out, read_mask=[True])


# AN-016
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 analyze_function 覆盖 compare/broadcast/matmul 分支统计。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_function_branches
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_function_branches() -> None:
    eq_lhs = Memory(["A", "B"], NumericType.Float32)
    eq_rhs = Memory(["A", "B"], NumericType.Float32)
    eq_out = Memory(["A", "B"], NumericType.Int32)
    bc_inp = Memory([1, "N"], NumericType.Float32)
    bc_out = Memory(["M", "N"], NumericType.Float32)
    mm_lhs = Memory(["M", "K"], NumericType.Float32)
    mm_rhs = Memory(["K", "N"], NumericType.Float32)
    mm_out = Memory(["M", "N"], NumericType.Float32)

    ops = [
        Operation("eq", [MemoryRef("EQ1", eq_lhs), MemoryRef("EQ2", eq_rhs)], MemoryRef("EQO", eq_out)),
        Operation("broadcast", [MemoryRef("BCI", bc_inp)], MemoryRef("BCO", bc_out)),
        Operation("matmul", [MemoryRef("ML", mm_lhs), MemoryRef("MR", mm_rhs)], MemoryRef("MO", mm_out)),
    ]
    summary = analyze_function(ops, predicate_size=1)
    a, b, m, n, k, s = (
        sp.Symbol("A"),
        sp.Symbol("B"),
        sp.Symbol("M"),
        sp.Symbol("N"),
        sp.Symbol("K"),
        sp.Symbol("S"),
    )
    expected_compute = a * b + sp.Integer(2) * m * n * k
    expected_read = 2 * a * b * s + n * s + (m * k + k * n) * s
    expected_write = a * b * sp.Integer(1) + 2 * m * n * s
    assert sp.simplify(summary.total.compute - expected_compute) == 0
    assert sp.simplify(summary.total.read_bytes - expected_read) == 0
    assert sp.simplify(summary.total.write_bytes - expected_write) == 0


# AN-017
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 analyze_function 遇到不支持的 op 会报错。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_function_unsupported_op
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_function_unsupported_op() -> None:
    inp = Memory(["A", "B"], NumericType.Float32)
    ops = [Operation("noop", [MemoryRef("A1", inp)], MemoryRef("B1", inp))]
    with pytest.raises(AnalysisError, match="Unsupported op for analysis"):
        analyze_function(ops)


# AN-018
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-03 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-03 00:00:00 +0800
# 测试目的: 验证单 op 统一入口返回新结果结构，且默认不写 analysis.* 属性。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_entry_returns_new_result_for_scalar_kernel_add
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_entry_returns_new_result_for_scalar_kernel_add() -> None:
    lhs = arith.ConstantOp(IntegerAttr(1, i32))
    rhs = arith.ConstantOp(IntegerAttr(2, i32))
    add_op = FakeKernelScalarAddOp(lhs.result, rhs.result, i32)

    result = analysis(
        add_op,
        AnalysisConfig(
            enable_compute=True,
            enable_memory=False,
            write_op_attrs=False,
            write_func_attrs=False,
        ),
    )

    assert isinstance(result, AnalysisResult)
    assert len(result.compute_items) == 1
    item = result.compute_items[0]
    assert item.kind == "scalar"
    _assert_expr_equal(item.amount, sp.Integer(1))
    assert item.dtype == "i32"
    assert result.memory_items == ()
    assert result.compute_totals_by_kind["scalar"] == sp.Integer(1)
    assert "analysis.compute" not in add_op.attributes


# AN-019
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-03 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-03 00:00:00 +0800
# 测试目的: 验证统一入口只有在 write_op_attrs=True 时才写回 op attributes。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_entry_write_op_attrs_is_explicit
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_entry_write_op_attrs_is_explicit() -> None:
    lhs = arith.ConstantOp(IntegerAttr(1, i32))
    rhs = arith.ConstantOp(IntegerAttr(2, i32))
    add_op = FakeKernelScalarAddOp(lhs.result, rhs.result, i32)

    analysis(
        add_op,
        AnalysisConfig(
            enable_compute=True,
            enable_memory=False,
            write_op_attrs=True,
            write_func_attrs=False,
        ),
    )

    assert add_op.attributes["analysis.compute"].data == "1"
    assert add_op.attributes["analysis.read_bytes"].data == "0"
    assert add_op.attributes["analysis.write_bytes"].data == "0"
    assert add_op.attributes["analysis.compute.kind0"].data == "scalar"
    assert add_op.attributes["analysis.compute.amount0"].data == "1"
    assert add_op.attributes["analysis.compute.dtype0"].data == "i32"


# AN-020
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-03 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-03 00:00:00 +0800
# 测试目的: 验证 func.func 统一入口默认不写 attrs，显式开启后写 func attrs，且 analyze_kernel 为 derived facade。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_func_write_attrs_is_explicit_and_analyze_kernel_is_facade
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_func_write_attrs_is_explicit_and_analyze_kernel_is_facade() -> None:
    mem_type = _make_memory_type([IntAttr(2), IntAttr(3)], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)
        return [add_op], add_op.result

    _, func_op, _ = _build_module([mem_type, mem_type], mem_type, _builder)
    result = analysis(
        func_op,
        AnalysisConfig(
            enable_compute=True,
            enable_memory=True,
            write_op_attrs=False,
            write_func_attrs=False,
            dtype_size_overrides={"f32": 4},
        ),
    )

    assert "analysis.compute" not in func_op.attributes
    summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4})
    assert summary.op_costs == result.op_costs
    assert summary.value_traffic == result.value_traffic
    _assert_expr_equal(summary.total_compute, result.total_compute)
    _assert_expr_equal(summary.total_read_bytes, result.total_read_bytes)
    _assert_expr_equal(summary.total_write_bytes, result.total_write_bytes)

    analysis(
        func_op,
        AnalysisConfig(
            enable_compute=True,
            enable_memory=True,
            write_op_attrs=False,
            write_func_attrs=True,
            dtype_size_overrides={"f32": 4},
        ),
    )
    assert func_op.attributes["analysis.compute"].data == "6"
    assert func_op.attributes["analysis.read_bytes"].data == "48"
    assert func_op.attributes["analysis.write_bytes"].data == "24"


# AN-021
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-03 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-03 00:00:00 +0800
# 测试目的: 验证 `analysis(func_op, ...)` 的函数级聚合显式逐 op 调用公开入口 `analysis(op, ...)`。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_func_aggregates_via_public_entry
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_func_aggregates_via_public_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    mem_type = _make_memory_type([IntAttr(2), IntAttr(3)], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)
        return [add_op], add_op.result

    _, func_op, _ = _build_module([mem_type, mem_type], mem_type, _builder)
    original_analysis = analysis_module.analysis
    seen_ops: list[str] = []

    def _spy(op: object, config: AnalysisConfig, otherargs: object = None) -> AnalysisResult:
        if not isinstance(op, func.FuncOp):
            seen_ops.append(op.name)
        return original_analysis(op, config, otherargs)

    monkeypatch.setattr(analysis_module, "analysis", _spy)
    result = analysis_module.analysis(
        func_op,
        AnalysisConfig(
            enable_compute=True,
            enable_memory=True,
            write_op_attrs=False,
            write_func_attrs=False,
            dtype_size_overrides={"f32": 4},
        ),
    )

    expected_ops = [op.name for op in analysis_module._iter_func_ops(func_op)]
    assert seen_ops == expected_ops
    assert result.op_costs[0].op_name == "nn.add"
    _assert_expr_equal(result.total_compute, sp.Integer(6))


# AN-022
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-03 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-03 00:00:00 +0800
# 测试目的: 验证 `analysis(func_op, ...)` 在 `write_op_attrs=True` 时仍通过公开入口写回逐 op attrs，不抛运行时错误。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_func_write_op_attrs_via_public_entry
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_func_write_op_attrs_via_public_entry() -> None:
    mem_type = _make_memory_type([IntAttr(2), IntAttr(3)], f32, "global")
    space = _make_space("global")
    captured_ops: dict[str, Operation] = {}

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)
        captured_ops["add"] = add_op
        return [add_op], add_op.result

    _, func_op, _ = _build_module([mem_type, mem_type], mem_type, _builder)
    result = analysis(
        func_op,
        AnalysisConfig(
            enable_compute=True,
            enable_memory=True,
            write_op_attrs=True,
            write_func_attrs=False,
            dtype_size_overrides={"f32": 4},
        ),
    )

    add_op = captured_ops["add"]
    assert add_op.attributes["analysis.compute"].data == "6"
    assert add_op.attributes["analysis.read_bytes"].data == "48"
    assert add_op.attributes["analysis.write_bytes"].data == "24"
    assert "analysis.compute" not in func_op.attributes
    assert result.op_costs[0].op_name == "nn.add"


# AK-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-31 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-31 00:00:00 +0800
# 测试目的: 验证 analyze_kernel 逐元素统计。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_nn_add_symbolic_shape
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_nn_add_symbolic_shape() -> None:
    mem_type = _make_memory_type([StringAttr("A"), StringAttr("B")], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)
        return [add_op], add_op.result

    _, func_op, _ = _build_module([mem_type, mem_type], mem_type, _builder)
    summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4})

    expected_numel = SymbolDim("A").get_symbol() * SymbolDim("B").get_symbol()
    assert summary.func_name == "main"
    _assert_expr_equal(summary.total_compute, expected_numel)
    _assert_expr_equal(summary.total_read_bytes, expected_numel * 2 * 4)
    _assert_expr_equal(summary.total_write_bytes, expected_numel * 4)
    assert summary.op_costs[0].op_name == "nn.add"


# AK-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-31 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-31 00:00:00 +0800
# 测试目的: 验证 analyze_kernel tensor + const 不计常量读流量。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_tensor_plus_const
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_tensor_plus_const() -> None:
    mem_type = _make_memory_type([StringAttr("A"), StringAttr("B")], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        const_op = arith.ConstantOp(IntegerAttr(1, i32))
        add_op = FakeNnAddOp(block.args[0], const_op.result, mem_type, space)
        return [const_op, add_op], add_op.result

    _, func_op, _ = _build_module([mem_type], mem_type, _builder)
    summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4})

    expected_numel = SymbolDim("A").get_symbol() * SymbolDim("B").get_symbol()
    _assert_expr_equal(summary.total_compute, expected_numel)
    _assert_expr_equal(summary.total_read_bytes, expected_numel * 4)
    _assert_expr_equal(summary.total_write_bytes, expected_numel * 4)
    traffic = _value_traffic_map(summary)
    assert set(traffic.keys()) == {"arg0", "op0.result0"}


# AK-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-31 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-31 00:00:00 +0800
# 测试目的: 验证 value_traffic 对中间结果读写归属。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_chain_value_traffic
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_chain_value_traffic() -> None:
    mem_type = _make_memory_type([StringAttr("A"), StringAttr("B")], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)
        mul_op = NnMulOp(add_op.result, block.args[2], mem_type, space)
        return [add_op, mul_op], mul_op.result

    _, func_op, _ = _build_module([mem_type, mem_type, mem_type], mem_type, _builder)
    summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4})
    traffic = _value_traffic_map(summary)
    for key in ["arg0", "arg1", "arg2", "op0.result0", "op1.result0"]:
        assert key in traffic

    expected_bytes = SymbolDim("A").get_symbol() * SymbolDim("B").get_symbol() * 4
    _assert_expr_equal(traffic["op0.result0"].write_bytes, expected_bytes)
    _assert_expr_equal(traffic["op0.result0"].read_bytes, expected_bytes)


# AK-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-31 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-31 00:00:00 +0800
# 测试目的: 验证 analyze_kernel matmul 公式。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_matmul_formula
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_matmul_formula() -> None:
    lhs_type = _make_memory_type([StringAttr("M"), StringAttr("K")], f32, "global")
    rhs_type = _make_memory_type([StringAttr("K"), StringAttr("N")], f32, "global")
    out_type = _make_memory_type([StringAttr("M"), StringAttr("N")], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        matmul_op = NnMatmulOp(block.args[0], block.args[1], out_type, space)
        return [matmul_op], matmul_op.result

    _, func_op, _ = _build_module([lhs_type, rhs_type], out_type, _builder)
    summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4})

    m = SymbolDim("M").get_symbol()
    n = SymbolDim("N").get_symbol()
    k = SymbolDim("K").get_symbol()
    _assert_expr_equal(summary.total_compute, sp.Integer(2) * m * n * k)
    _assert_expr_equal(summary.total_read_bytes, (m * k + k * n) * 4)
    _assert_expr_equal(summary.total_write_bytes, m * n * 4)


# AK-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-31 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-31 00:00:00 +0800
# 测试目的: 验证 dma.load 同时记录源读与结果写流量。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_dma_load_tracks_source_and_result
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_dma_load_tracks_source_and_result() -> None:
    mem_type = _make_memory_type([IntAttr(2), IntAttr(2)], f32, "global")
    space = _make_space("global")
    symbol_types = [
        SymbolValueType.from_expr("0"),
        SymbolValueType.from_expr("0"),
        SymbolValueType.from_expr("2"),
        SymbolValueType.from_expr("2"),
        SymbolValueType.from_expr("1"),
        SymbolValueType.from_expr("1"),
    ]

    arg_types = [mem_type, *symbol_types]

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        offsets = [block.args[1], block.args[2]]
        sizes = [block.args[3], block.args[4]]
        strides = [block.args[5], block.args[6]]
        load_op = DmaLoadOp(block.args[0], offsets, sizes, strides, mem_type, space)
        return [load_op], load_op.result

    _, func_op, _ = _build_module(arg_types, mem_type, _builder)
    summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4})
    expected_bytes = sp.Integer(16)
    _assert_expr_equal(summary.total_compute, sp.Integer(0))
    _assert_expr_equal(summary.total_read_bytes, expected_bytes)
    _assert_expr_equal(summary.total_write_bytes, expected_bytes)

    traffic = _value_traffic_map(summary)
    _assert_expr_equal(traffic["arg0"].read_bytes, expected_bytes)
    _assert_expr_equal(traffic["op0.result0"].write_bytes, expected_bytes)


# AK-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-31 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-31 00:00:00 +0800
# 测试目的: 验证 analyze_kernel 拒绝非 func 输入。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_rejects_non_func_input
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_rejects_non_func_input() -> None:
    module = ModuleOp([])
    with pytest.raises(AnalysisError, match="func.FuncOp"):
        analyze_kernel(module)


# AK-007
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-31 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-31 00:00:00 +0800
# 测试目的: 验证 analyze_kernel 拒绝非 iterable args。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_rejects_non_iterable_args
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_rejects_non_iterable_args() -> None:
    mem_type = _make_memory_type([IntAttr(2), IntAttr(2)], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)
        return [add_op], add_op.result

    _, func_op, _ = _build_module([mem_type, mem_type], mem_type, _builder)
    with pytest.raises(AnalysisError, match="args must be iterable"):
        analyze_kernel(func_op, args=object())


# AK-008
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-31 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-31 00:00:00 +0800
# 测试目的: 验证 analyze_kernel args 长度与参数位次不匹配时报错。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_rejects_args_length_mismatch
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_rejects_args_length_mismatch() -> None:
    mem_type = _make_memory_type([IntAttr(2), IntAttr(2)], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)
        return [add_op], add_op.result

    _, func_op, _ = _build_module([mem_type, mem_type], mem_type, _builder)
    with pytest.raises(AnalysisError, match="args length mismatch"):
        analyze_kernel(func_op, args=[object()])


# AK-009
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-02 05:49:01 +0800
# 最近一次运行成功时间: 2026-04-02 05:49:01 +0800
# 测试目的: 验证未知 op skip + warning。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_unknown_op_warns_and_skips
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_unknown_op_warns_and_skips() -> None:
    mem_type = _make_memory_type([StringAttr("A"), StringAttr("B")], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        unknown = UnknownOp()
        add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)
        return [unknown, add_op], add_op.result

    _, func_op, _ = _build_module([mem_type, mem_type], mem_type, _builder)
    with pytest.warns(UserWarning, match="test.unknown"):
        summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4})

    expected_numel = SymbolDim("A").get_symbol() * SymbolDim("B").get_symbol()
    _assert_expr_equal(summary.total_compute, expected_numel)
    assert len(summary.op_costs) == 1
    assert summary.op_costs[0].op_name == "nn.add"
    traffic = _value_traffic_map(summary)
    assert set(traffic.keys()) == {"arg0", "arg1", "op0.result0"}


# AK-010
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-02 05:49:01 +0800
# 最近一次运行成功时间: 2026-04-02 05:49:01 +0800
# 测试目的: 验证 compare i1 写回使用 predicate_size 优先级。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_compare_i1_uses_predicate_size
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_compare_i1_uses_predicate_size() -> None:
    lhs_type = _make_memory_type([StringAttr("A"), StringAttr("B")], f32, "global")
    rhs_type = _make_memory_type([StringAttr("A"), StringAttr("B")], f32, "global")
    out_type = _make_memory_type([StringAttr("A"), StringAttr("B")], i1, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        eq_op = NnEqOp(block.args[0], block.args[1], out_type, space)
        return [eq_op], eq_op.result

    _, func_op, _ = _build_module([lhs_type, rhs_type], out_type, _builder)
    summary = analyze_kernel(
        func_op,
        predicate_size=2,
        dtype_size_overrides={"f32": 4, "i1": 8},
    )

    expected_numel = SymbolDim("A").get_symbol() * SymbolDim("B").get_symbol()
    _assert_expr_equal(summary.total_write_bytes, expected_numel * 2)
    _assert_expr_equal(summary.op_costs[0].write_bytes, expected_numel * 2)
    traffic = _value_traffic_map(summary)
    _assert_expr_equal(traffic["op0.result0"].write_bytes, expected_numel * 2)


# AN-018
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-02 05:49:01 +0800
# 最近一次运行成功时间: 2026-04-02 05:49:01 +0800
# 测试目的: 验证公开 DMA 分支中的 dma.copy 与 dma.store 会记录源读/目标写流量。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_dma_copy_and_store_track_source_and_target_traffic
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_dma_copy_and_store_track_source_and_target_traffic() -> None:
    mem_type = _make_memory_type([IntAttr(2), IntAttr(2)], f32, "global")
    symbol_types = [
        SymbolValueType.from_expr("0"),
        SymbolValueType.from_expr("0"),
        SymbolValueType.from_expr("2"),
        SymbolValueType.from_expr("2"),
        SymbolValueType.from_expr("1"),
        SymbolValueType.from_expr("1"),
    ]

    arg_types = [mem_type, mem_type, *symbol_types]

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        copy_op = DmaCopyOp(block.args[0], block.args[1])
        store_op = DmaStoreOp(
            block.args[0],
            block.args[1],
            [block.args[2], block.args[3]],
            [block.args[4], block.args[5]],
            [block.args[6], block.args[7]],
        )
        return [copy_op, store_op], block.args[1]

    _, func_op, _ = _build_module(arg_types, mem_type, _builder)
    summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4})

    expected_bytes = sp.Integer(16)
    _assert_expr_equal(summary.total_compute, sp.Integer(0))
    _assert_expr_equal(summary.total_read_bytes, expected_bytes * 2)
    _assert_expr_equal(summary.total_write_bytes, expected_bytes * 2)
    traffic = _value_traffic_map(summary)
    _assert_expr_equal(traffic["arg0"].read_bytes, expected_bytes * 2)
    _assert_expr_equal(traffic["arg1"].write_bytes, expected_bytes * 2)


# AN-019
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-02 05:49:01 +0800
# 最近一次运行成功时间: 2026-04-02 05:49:01 +0800
# 测试目的: 验证公开 DMA 分支前置条件失败时 analyze_kernel 会抛出 AnalysisError。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_rejects_invalid_public_dma_op
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_rejects_invalid_public_dma_op() -> None:
    source_type = _make_memory_type([IntAttr(2), IntAttr(2)], f32, "global")
    target_type = _make_memory_type([IntAttr(2), IntAttr(4)], f32, "global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        copy_op = DmaCopyOp(block.args[0], block.args[1])
        return [copy_op], block.args[0]

    _, func_op, _ = _build_module([source_type, target_type], source_type, _builder)
    with pytest.raises(AnalysisError, match="dma.copy source/target shape mismatch"):
        analyze_kernel(func_op, dtype_size_overrides={"f32": 4})


# AN-020
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-02 05:49:01 +0800
# 最近一次运行成功时间: 2026-04-02 05:49:01 +0800
# 测试目的: 验证当前未公开 DMA 分支执行 skip + warning，且不计入主入口统计。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_skips_non_public_dma_ops_with_warning
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_skips_non_public_dma_ops_with_warning() -> None:
    full_type = _make_memory_type([IntAttr(2), IntAttr(4)], f32, "global")
    tile_type = _make_memory_type([IntAttr(1), IntAttr(2)], f32, "global")
    symbol_types = [
        SymbolValueType.from_expr("0"),
        SymbolValueType.from_expr("0"),
        SymbolValueType.from_expr("1"),
        SymbolValueType.from_expr("2"),
        SymbolValueType.from_expr("1"),
        SymbolValueType.from_expr("1"),
    ]

    arg_types = [full_type, *symbol_types]

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        offsets = [block.args[1], block.args[2]]
        sizes = [block.args[3], block.args[4]]
        strides = [block.args[5], block.args[6]]
        alloc_op = DmaAllocOp(sizes, tile_type)
        slice_op = DmaSliceOp(alloc_op.result, block.args[0], offsets, sizes, strides)
        deslice_op = DmaDesliceOp(alloc_op.result, block.args[0], offsets, sizes, strides, full_type)
        free_op = DmaFreeOp(alloc_op.result)
        return [alloc_op, slice_op, deslice_op, free_op], block.args[0]

    _, func_op, _ = _build_module(arg_types, full_type, _builder)
    with pytest.warns(UserWarning) as records:
        summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4})

    assert [str(item.message) for item in records] == [
        "analysis_kernel skip dma.alloc: unsupported op",
        "analysis_kernel skip dma.slice: unsupported op",
        "analysis_kernel skip dma.deslice: unsupported op",
        "analysis_kernel skip dma.free: unsupported op",
    ]
    assert summary.op_costs == []
    _assert_expr_equal(summary.total_compute, sp.Integer(0))
    _assert_expr_equal(summary.total_read_bytes, sp.Integer(0))
    _assert_expr_equal(summary.total_write_bytes, sp.Integer(0))
    traffic = _value_traffic_map(summary)
    assert set(traffic.keys()) == {f"arg{index}" for index in range(len(arg_types))}
