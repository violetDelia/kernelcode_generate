"""expectation case runner tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 `expectation.utils.case_runner` 的 case 收集、失败汇总与参数校验行为。

使用示例:
- `pytest -q test/tools/test_expectation_case_runner.py`

关联文件:
- spec: [`spec/tools/mlir_gen_compare.md`](../../spec/tools/mlir_gen_compare.md)
- test: [`test/tools/test_mlir_gen_compare.py`](test_mlir_gen_compare.py)
- 功能实现: [`expectation/utils/case_runner.py`](../../expectation/utils/case_runner.py)
"""

from __future__ import annotations

import sys
from pathlib import Path
import importlib

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import raise_if_failures, run_case
random_shared = importlib.import_module("expectation.pass.tile._random_shared")
FLOAT_DTYPE = random_shared.FLOAT_DTYPE
SPACE_ATTR = random_shared.SPACE_ATTR
memory_ir = random_shared.memory_ir
random_rank3_static_dynamic = random_shared.random_rank3_static_dynamic


def _raise_value_error() -> None:
    """用于验证 `run_case(...)` 的异常收集路径。"""

    raise ValueError("boom")


def _no_op() -> None:
    """用于验证 `run_case(...)` 的成功路径。"""

    return None


def test_run_case_collects_exception() -> None:
    """验证 `run_case(...)` 会收集普通异常而不中断后续汇总。"""

    failures: list[tuple[str, BaseException]] = []

    run_case(failures, "CASE-1", _raise_value_error)

    assert len(failures) == 1
    case_name, exc = failures[0]
    assert case_name == "CASE-1"
    assert isinstance(exc, ValueError)
    assert str(exc) == "boom"


def test_run_case_passes_successful_case() -> None:
    """验证 `run_case(...)` 在 case 成功时不修改失败列表。"""

    failures: list[tuple[str, BaseException]] = []

    run_case(failures, "CASE-OK", _no_op)

    assert failures == []


def test_raise_if_failures_formats_summary() -> None:
    """验证 `raise_if_failures(...)` 输出稳定的摘要格式。"""

    failures: list[tuple[str, BaseException]] = [("CASE-1", ValueError("boom"))]

    with pytest.raises(AssertionError, match=r"tile reduce fc expectation failed \(1 cases\):") as exc_info:
        raise_if_failures("tile reduce fc expectation", failures)

    message = str(exc_info.value)
    assert "- CASE-1: ValueError: boom" in message


def test_raise_if_failures_empty_is_noop() -> None:
    """验证 `raise_if_failures(...)` 在无失败时直接返回。"""

    raise_if_failures("tile reduce fc expectation", [])


def test_run_case_rejects_invalid_arguments() -> None:
    """验证 `run_case(...)` 对非法参数的显式拒绝行为。"""

    failures: list[tuple[str, BaseException]] = []

    with pytest.raises(ValueError, match="case_name must be non-empty"):
        run_case(failures, "", _no_op)

    with pytest.raises(TypeError, match="case_fn must be callable"):
        run_case(failures, "CASE-2", None)  # type: ignore[arg-type]


def test_random_shared_memory_ir_uses_contiguous_row_major_stride() -> None:
    """验证 tile expectation 共享 helper 的 memory 文本拼装行为。"""

    assert FLOAT_DTYPE == "f32"
    assert SPACE_ATTR == "#nn.space<global>"
    assert memory_ir([4, 8], FLOAT_DTYPE) == "!nn.memory<[4, 8], [8, 1], f32, #nn.space<global>>"
    assert memory_ir(["M", "N"], FLOAT_DTYPE) == "!nn.memory<[M, N], [N, 1], f32, #nn.space<global>>"


def test_random_rank3_static_dynamic_returns_fixed_shape_pairs() -> None:
    """验证 tile reduce 共享维度 helper 返回稳定的 6 元组。"""

    values = random_rank3_static_dynamic()

    assert values == (4, 8, 16, "M", "K", "N")
