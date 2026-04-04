"""scf operation API tests.

创建者: 摸鱼小分队
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 kernel_gen/operation/scf.py 的 loop 语义。

当前覆盖率信息:
- 统计时间: 2026-03-22 14:12:16 +0800
- 覆盖率结果: 97% (34 statements, 1 missed line)
- 达标结论: 已达到 95% 达标线

覆盖率命令:
- pytest --cov=kernel_gen.operation.scf --cov-report=term-missing test/operation/test_operation_scf.py

使用示例:
- pytest -q test/operation/test_operation_scf.py

关联文件:
- 功能实现: kernel_gen/operation/scf.py
- Spec 文档: spec/operation/scf.md
- 测试文件: test/operation/test_operation_scf.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.operation.scf import LoopRange, loop
from kernel_gen.symbol_variable.symbol_dim import SymbolDim


# TC-OP-SCF-001
# 创建者: 摸鱼小分队
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-22 13:15:14 +0800
# 最近一次运行成功时间: 2026-03-22 13:15:14 +0800
# 测试目的: 验证 loop 纯整数输入等价于 range 半开区间。
# 使用示例: pytest -q test/operation/test_operation_scf.py -k test_loop_integer_range
# 对应功能实现文件路径: kernel_gen/operation/scf.py
# 对应 spec 文件路径: spec/operation/scf.md
# 对应测试文件路径: test/operation/test_operation_scf.py
def test_loop_integer_range() -> None:
    assert list(loop(0, 4, 1)) == [0, 1, 2, 3]


# TC-OP-SCF-002
# 创建者: 摸鱼小分队
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-22 13:15:14 +0800
# 最近一次运行成功时间: 2026-03-22 13:15:14 +0800
# 测试目的: 验证负步长半开区间语义。
# 使用示例: pytest -q test/operation/test_operation_scf.py -k test_loop_negative_step
# 对应功能实现文件路径: kernel_gen/operation/scf.py
# 对应 spec 文件路径: spec/operation/scf.md
# 对应测试文件路径: test/operation/test_operation_scf.py
def test_loop_negative_step() -> None:
    assert list(loop(4, 0, -1)) == [4, 3, 2, 1]


# TC-OP-SCF-003
# 创建者: 摸鱼小分队
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-22 13:15:14 +0800
# 最近一次运行成功时间: 2026-03-22 13:15:14 +0800
# 测试目的: 验证 SymbolDim 输入返回 LoopRange 并保留属性。
# 使用示例: pytest -q test/operation/test_operation_scf.py -k test_loop_symbol_dim_range
# 对应功能实现文件路径: kernel_gen/operation/scf.py
# 对应 spec 文件路径: spec/operation/scf.md
# 对应测试文件路径: test/operation/test_operation_scf.py
def test_loop_symbol_dim_range() -> None:
    start = SymbolDim("M")
    end = SymbolDim("N")
    step = SymbolDim("S")
    loop_range = loop(start, end, step)
    assert isinstance(loop_range, LoopRange)
    assert loop_range.start is start
    assert loop_range.end is end
    assert loop_range.step is step


# TC-OP-SCF-004
# 创建者: 摸鱼小分队
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-22 13:15:14 +0800
# 最近一次运行成功时间: 2026-03-22 13:15:14 +0800
# 测试目的: 验证 step 为 0 时抛出 ValueError。
# 使用示例: pytest -q test/operation/test_operation_scf.py -k test_loop_step_zero
# 对应功能实现文件路径: kernel_gen/operation/scf.py
# 对应 spec 文件路径: spec/operation/scf.md
# 对应测试文件路径: test/operation/test_operation_scf.py
def test_loop_step_zero() -> None:
    with pytest.raises(ValueError):
        loop(0, 4, 0)


# TC-OP-SCF-005
# 创建者: 摸鱼小分队
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-22 13:15:14 +0800
# 最近一次运行成功时间: 2026-03-22 13:15:14 +0800
# 测试目的: 验证非法类型输入抛出 TypeError。
# 使用示例: pytest -q test/operation/test_operation_scf.py -k test_loop_invalid_type
# 对应功能实现文件路径: kernel_gen/operation/scf.py
# 对应 spec 文件路径: spec/operation/scf.md
# 对应测试文件路径: test/operation/test_operation_scf.py
def test_loop_invalid_type() -> None:
    with pytest.raises(TypeError):
        loop("0", 4, 1)
    with pytest.raises(TypeError):
        loop(0, "4", 1)
    with pytest.raises(TypeError):
        loop(0, 4, "1")


# TC-OP-SCF-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-04 21:02:42 +0800
# 最近一次运行成功时间: 2026-04-04 21:02:42 +0800
# 测试目的: 验证 trip_count <= 0 时抛出 ValueError。
# 使用示例: pytest -q test/operation/test_operation_scf.py -k test_loop_trip_count_invalid
# 对应功能实现文件路径: kernel_gen/operation/scf.py
# 对应 spec 文件路径: spec/operation/scf.md
# 对应测试文件路径: test/operation/test_operation_scf.py
def test_loop_trip_count_invalid() -> None:
    start = SymbolDim("M")
    end = SymbolDim("N")
    step = SymbolDim("S")
    with pytest.raises(ValueError):
        loop(start, end, step, trip_count=0)
    with pytest.raises(ValueError):
        loop(start, end, step, trip_count=-1)


# TC-OP-SCF-007
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-04 21:02:42 +0800
# 最近一次运行成功时间: 2026-04-04 21:02:42 +0800
# 测试目的: 验证 trip_count=3 时序列语义与 LoopRange 可访问 trip_count。
# 使用示例: pytest -q test/operation/test_operation_scf.py -k test_loop_trip_count_sequence_semantics
# 对应功能实现文件路径: kernel_gen/operation/scf.py
# 对应 spec 文件路径: spec/operation/scf.md
# 对应测试文件路径: test/operation/test_operation_scf.py
def test_loop_trip_count_sequence_semantics() -> None:
    end = SymbolDim("N")
    loop_range = loop(1, end, 2, trip_count=3)
    assert isinstance(loop_range, LoopRange)
    assert loop_range.trip_count == 3
    assert [loop_range.start + loop_range.step * i for i in range(loop_range.trip_count)] == [1, 3, 5]
