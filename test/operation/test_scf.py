"""scf operation API tests.


功能说明:
- 覆盖 kernel_gen/operation/scf.py 的 loop 语义。

当前覆盖率信息:
- 统计时间: 2026-03-22 14:12:16 +0800
- 覆盖率结果: 97% (34 statements, 1 missed line)
- 达标结论: 已达到 95% 达标线

覆盖率命令:
- pytest --cov=kernel_gen.operation.scf --cov-report=term-missing test/operation/test_scf.py

使用示例:
- pytest -q test/operation/test_scf.py

关联文件:
- 功能实现: kernel_gen/operation/scf.py
- Spec 文档: spec/operation/scf.md
- 测试文件: test/operation/test_scf.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.operation.scf import LoopRange, loop
from kernel_gen.symbol_variable.symbol_dim import SymbolDim


# TC-OP-SCF-001
# 测试目的: 验证 loop 纯整数输入等价于 range 半开区间。
# 使用示例: pytest -q test/operation/test_scf.py -k test_loop_integer_range
# 对应功能实现文件路径: kernel_gen/operation/scf.py
# 对应 spec 文件路径: spec/operation/scf.md
# 对应测试文件路径: test/operation/test_scf.py
def test_loop_integer_range() -> None:
    assert list(loop(0, 4, 1)) == [0, 1, 2, 3]


# TC-OP-SCF-002
# 测试目的: 验证负步长半开区间语义。
# 使用示例: pytest -q test/operation/test_scf.py -k test_loop_negative_step
# 对应功能实现文件路径: kernel_gen/operation/scf.py
# 对应 spec 文件路径: spec/operation/scf.md
# 对应测试文件路径: test/operation/test_scf.py
def test_loop_negative_step() -> None:
    assert list(loop(4, 0, -1)) == [4, 3, 2, 1]


# TC-OP-SCF-003
# 测试目的: 验证 SymbolDim 输入返回 LoopRange 并保留属性。
# 使用示例: pytest -q test/operation/test_scf.py -k test_loop_symbol_dim_range
# 对应功能实现文件路径: kernel_gen/operation/scf.py
# 对应 spec 文件路径: spec/operation/scf.md
# 对应测试文件路径: test/operation/test_scf.py
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
# 测试目的: 验证 step 为 0 时抛出 KernelCodeError。
# 使用示例: pytest -q test/operation/test_scf.py -k test_loop_step_zero
# 对应功能实现文件路径: kernel_gen/operation/scf.py
# 对应 spec 文件路径: spec/operation/scf.md
# 对应测试文件路径: test/operation/test_scf.py
def test_loop_step_zero() -> None:
    with pytest.raises(KernelCodeError):
        loop(0, 4, 0)


# TC-OP-SCF-005
# 测试目的: 验证非法类型与 bool 输入均抛出 KernelCodeError。
# 使用示例: pytest -q test/operation/test_scf.py -k test_loop_invalid_type
# 对应功能实现文件路径: kernel_gen/operation/scf.py
# 对应 spec 文件路径: spec/operation/scf.md
# 对应测试文件路径: test/operation/test_scf.py
def test_loop_invalid_type() -> None:
    with pytest.raises(KernelCodeError):
        loop("0", 4, 1)
    with pytest.raises(KernelCodeError):
        loop(0, "4", 1)
    with pytest.raises(KernelCodeError):
        loop(0, 4, "1")


# TC-OP-SCF-008
# 测试目的: 验证 start/end/step/trip_count 中的 bool 不再按 int 接受。
# 使用示例: pytest -q test/operation/test_scf.py -k test_loop_rejects_bool_operands
# 对应功能实现文件路径: kernel_gen/operation/scf.py
# 对应 spec 文件路径: spec/operation/scf.md
# 对应测试文件路径: test/operation/test_scf.py
def test_loop_rejects_bool_operands() -> None:
    with pytest.raises(KernelCodeError, match="start must be int or SymbolDim"):
        loop(True, 4, 1)
    with pytest.raises(KernelCodeError, match="end must be int or SymbolDim"):
        loop(0, False, 1)
    with pytest.raises(KernelCodeError, match="step must be int or SymbolDim"):
        loop(0, 4, True)
    with pytest.raises(KernelCodeError, match="trip_count must be int or SymbolDim"):
        loop(0, 4, 1, trip_count=True)


# TC-OP-SCF-009
# 测试目的: 验证非法 bound 输入在 `end` 位置触发显式 KernelCodeError。
# 使用示例: pytest -q test/operation/test_scf.py -k test_loop_rejects_invalid_bound_operand
# 对应功能实现文件路径: kernel_gen/operation/scf.py
# 对应 spec 文件路径: spec/operation/scf.md
# 对应测试文件路径: test/operation/test_scf.py
def test_loop_rejects_invalid_bound_operand() -> None:
    with pytest.raises(KernelCodeError, match="end must be int or SymbolDim"):
        loop(0, object(), 1)


# TC-OP-SCF-010
# 测试目的: 验证符号步长路径继续返回 LoopRange，并保留 trip_count 合同。
# 使用示例: pytest -q test/operation/test_scf.py -k test_loop_symbolic_step_contract
# 对应功能实现文件路径: kernel_gen/operation/scf.py
# 对应 spec 文件路径: spec/operation/scf.md
# 对应测试文件路径: test/operation/test_scf.py
def test_loop_symbolic_step_contract() -> None:
    loop_range = loop(0, SymbolDim("N"), SymbolDim("S"), trip_count=3)

    assert isinstance(loop_range, LoopRange)
    assert loop_range.start == 0
    assert loop_range.end.get_value() == "N"
    assert loop_range.step.get_value() == "S"
    assert loop_range.trip_count == 3
    assert [item if isinstance(item, int) else item.get_value() for item in loop_range] == [
        0,
        "S",
        "2*S",
    ]


# TC-OP-SCF-006
# 测试目的: 验证 trip_count <= 0 时抛出 KernelCodeError。
# 使用示例: pytest -q test/operation/test_scf.py -k test_loop_trip_count_invalid
# 对应功能实现文件路径: kernel_gen/operation/scf.py
# 对应 spec 文件路径: spec/operation/scf.md
# 对应测试文件路径: test/operation/test_scf.py
def test_loop_trip_count_invalid() -> None:
    start = SymbolDim("M")
    end = SymbolDim("N")
    step = SymbolDim("S")
    with pytest.raises(KernelCodeError):
        loop(start, end, step, trip_count=0)
    with pytest.raises(KernelCodeError):
        loop(start, end, step, trip_count=-1)


# TC-OP-SCF-007
# 测试目的: 验证 trip_count=3 时序列语义与 LoopRange 可访问 trip_count。
# 使用示例: pytest -q test/operation/test_scf.py -k test_loop_trip_count_sequence_semantics
# 对应功能实现文件路径: kernel_gen/operation/scf.py
# 对应 spec 文件路径: spec/operation/scf.md
# 对应测试文件路径: test/operation/test_scf.py
def test_loop_trip_count_sequence_semantics() -> None:
    end = SymbolDim("N")
    loop_range = loop(1, end, 2, trip_count=3)
    assert isinstance(loop_range, LoopRange)
    assert loop_range.trip_count == 3
    assert list(loop_range) == [1, 3, 5]


# TC-OP-SCF-011
# 测试目的: 验证 LoopRange(...) 直接构造与 loop(...) 共享输入校验。
# 使用示例: pytest -q test/operation/test_scf.py -k test_looprange_shares_input_validation
# 对应功能实现文件路径: kernel_gen/operation/scf.py
# 对应 spec 文件路径: spec/operation/scf.md
# 对应测试文件路径: test/operation/test_scf.py
def test_looprange_shares_input_validation() -> None:
    with pytest.raises(KernelCodeError, match="start must be int or SymbolDim"):
        LoopRange(True, 4, 1)
    with pytest.raises(KernelCodeError, match="end must be int or SymbolDim"):
        LoopRange(0, object(), 1)
    with pytest.raises(KernelCodeError, match="trip_count must be int or SymbolDim"):
        LoopRange(0, SymbolDim("N"), SymbolDim("S"), trip_count=True)
    with pytest.raises(KernelCodeError, match="trip_count must be > 0"):
        LoopRange(0, SymbolDim("N"), SymbolDim("S"), trip_count=0)


# TC-OP-SCF-012
# 测试目的: 验证 LoopRange(...) 直接构造会把 trip_count=None 归一化为 1。
# 使用示例: pytest -q test/operation/test_scf.py -k test_looprange_none_trip_count_defaults_to_one
# 对应功能实现文件路径: kernel_gen/operation/scf.py
# 对应 spec 文件路径: spec/operation/scf.md
# 对应测试文件路径: test/operation/test_scf.py
def test_looprange_none_trip_count_defaults_to_one() -> None:
    loop_range = LoopRange(0, SymbolDim("N"), SymbolDim("S"), trip_count=None)
    assert loop_range.trip_count == 1
    assert list(loop_range) == [0]


# TC-OP-SCF-013
# 测试目的: 验证 trip_count=SymbolDim 时当前运行期 helper 仅保守产出首项，并保留 trip_count 本身。
# 使用示例: pytest -q test/operation/test_scf.py -k test_loop_symbolic_trip_count_is_conservative_single_item
# 对应功能实现文件路径: kernel_gen/operation/scf.py
# 对应 spec 文件路径: spec/operation/scf.md
# 对应测试文件路径: test/operation/test_scf.py
def test_loop_symbolic_trip_count_is_conservative_single_item() -> None:
    trip_count = SymbolDim("T")
    loop_range = loop(0, SymbolDim("N"), SymbolDim("S"), trip_count=trip_count)

    assert isinstance(loop_range, LoopRange)
    assert loop_range.trip_count is trip_count
    assert list(loop_range) == [0]
