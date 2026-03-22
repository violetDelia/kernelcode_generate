"""Analysis tests.

创建者: 金铲铲大作战
最后一次更改: 小李飞刀

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

import sympy as sp
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.analysis.analysis import (
    AnalysisError,
    AnalysisSummary,
    MemoryRef,
    OpStats,
    Operation,
    analyze_add,
    analyze_elementwise,
    analyze_broadcast,
    analyze_broadcast_op,
    analyze_eq,
    analyze_function,
    analyze_matmul,
    analyze_matmul_op,
)
import kernel_gen.analysis.analysis as analysis_module
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType


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
