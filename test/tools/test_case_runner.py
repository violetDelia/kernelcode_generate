"""case_runner tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 `kernel_gen.tools.case_runner` 的 case 收集、失败汇总与参数校验行为。

关联文件:
- 功能实现: [kernel_gen/tools/case_runner.py](../../kernel_gen/tools/case_runner.py)
- Spec 文档: [spec/tools/case_runner.md](../../spec/tools/case_runner.md)
- 测试文件: [test/tools/test_case_runner.py](test/tools/test_case_runner.py)

使用示例:
- pytest -q test/tools/test_case_runner.py
"""

from __future__ import annotations

import pytest

from kernel_gen.tools.case_runner import raise_if_failures, run_case

pytestmark = pytest.mark.infra


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

    with pytest.raises(AssertionError, match=r"tile reduce fc helper failed \(1 cases\):") as exc_info:
        raise_if_failures("tile reduce fc helper", failures)

    message = str(exc_info.value)
    assert "- CASE-1: ValueError: boom" in message


def test_raise_if_failures_empty_is_noop() -> None:
    """验证 `raise_if_failures(...)` 在无失败时直接返回。"""

    raise_if_failures("tile reduce fc helper", [])


def test_run_case_rejects_invalid_arguments() -> None:
    """验证 `run_case(...)` 对非法参数的显式拒绝行为。"""

    failures: list[tuple[str, BaseException]] = []

    with pytest.raises(ValueError, match="case_name must be non-empty"):
        run_case(failures, "", _no_op)

    with pytest.raises(TypeError, match="case_fn must be callable"):
        run_case(failures, "CASE-2", None)  # type: ignore[arg-type]
