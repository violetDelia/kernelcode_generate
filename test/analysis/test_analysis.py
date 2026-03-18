"""Analysis tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖逐元素算术/比较、broadcast、matmul 与函数级聚合统计。

使用示例:
- pytest -q test/analysis/test_analysis.py

关联文件:
- 功能实现: python/analysis/analysis.py
- Spec 文档: spec/analysis/分析.md
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

from python.analysis.analysis import (
    AnalysisError,
    AnalysisSummary,
    MemoryRef,
    Operation,
    analyze_add,
    analyze_elementwise,
    analyze_broadcast_op,
    analyze_eq,
    analyze_function,
    analyze_matmul_op,
)
from python.symbol_variable.memory import Memory
from python.symbol_variable.type import NumericType


# AN-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 03:42:29 +0800
# 最近一次运行成功时间: 2026-03-19 03:42:29 +0800
# 功能说明: 验证 add 的计算量与搬运量统计。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_add_counts
# 对应功能实现文件路径: python/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/分析.md
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


# AN-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 03:42:29 +0800
# 最近一次运行成功时间: 2026-03-19 03:42:29 +0800
# 功能说明: 验证 eq 的计算量与搬运量统计。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_eq_counts
# 对应功能实现文件路径: python/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/分析.md
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
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 03:42:29 +0800
# 最近一次运行成功时间: 2026-03-19 03:42:29 +0800
# 功能说明: 验证 broadcast 的读写量统计。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_broadcast_counts
# 对应功能实现文件路径: python/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/分析.md
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
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 03:42:29 +0800
# 最近一次运行成功时间: 2026-03-19 03:42:29 +0800
# 功能说明: 验证 matmul 的计算量与读写量统计。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_matmul_counts
# 对应功能实现文件路径: python/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/分析.md
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
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 03:42:29 +0800
# 最近一次运行成功时间: 2026-03-19 03:42:29 +0800
# 功能说明: 验证函数级聚合统计会计入中间物化。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_materialized_intermediate
# 对应功能实现文件路径: python/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/分析.md
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
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 03:42:29 +0800
# 最近一次运行成功时间: 2026-03-19 03:42:29 +0800
# 功能说明: 验证函数级聚合在融合场景不计入中间物化。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_fused_intermediate
# 对应功能实现文件路径: python/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/分析.md
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
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 06:34:36 +0800
# 最近一次运行成功时间: 2026-03-19 06:34:36 +0800
# 功能说明: 验证 read_mask 长度不匹配时报 AnalysisError。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_read_mask_length_mismatch
# 对应功能实现文件路径: python/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/分析.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_read_mask_length_mismatch() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    out = Memory(["A", "B"], NumericType.Float32)
    with pytest.raises(AnalysisError, match="read_mask length mismatch"):
        analyze_elementwise(lhs, rhs, out, read_mask=[True])


# AN-008
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 06:34:36 +0800
# 最近一次运行成功时间: 2026-03-19 06:34:36 +0800
# 功能说明: 验证 analyze_function 输入数量不匹配时报 AnalysisError。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_function_inputs_mismatch
# 对应功能实现文件路径: python/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/分析.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_function_inputs_mismatch() -> None:
    a1 = Memory(["A", "B"], NumericType.Float32)
    out = Memory(["A", "B"], NumericType.Float32)
    ops = [Operation("add", [MemoryRef("A1", a1)], MemoryRef("C", out))]
    with pytest.raises(AnalysisError, match="Operation inputs length mismatch"):
        analyze_function(ops)
