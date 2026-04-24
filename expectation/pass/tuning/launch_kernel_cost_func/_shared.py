"""launch-kernel-cost-func expectation 共享 helper。

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 为 `launch_kernel_cost_func` family 的当前目录入口提供统一 case 收集与 ircheck helper。
- 让 `launch_kernel_cost_func_compute_memory/basic_all.py` 在纯 worktree 场景下不再依赖缺失的 `expectation.utils.case_runner`。
- 只承接当前 `compute / memory` 目录入口所需 helper，不引回旧四 kind 子资产。

使用示例:
- `run_case(failures, "CASE-1", case_ok)`
- `result = run_ircheck_success(case_text, source_path="case#compute")`

关联文件:
- spec: [`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../spec/pass/tuning/launch_kernel_cost_func.md)
- spec: [`spec/tools/ircheck.md`](../../../../spec/tools/ircheck.md)
- test: [`test/pass/test_launch_kernel_cost_func.py`](../../../../test/pass/test_launch_kernel_cost_func.py)
- 功能实现: [`expectation/pass/tuning/launch_kernel_cost_func/_shared.py`](../../../../expectation/pass/tuning/launch_kernel_cost_func/_shared.py)
- 功能实现: [`kernel_gen/tools/ircheck.py`](../../../../kernel_gen/tools/ircheck.py)
"""

from __future__ import annotations

from collections.abc import Callable

from kernel_gen.tools.ircheck import IrcheckResult, run_ircheck_text

FailureItem = tuple[str, BaseException]
FailureList = list[FailureItem]


def run_case(failures: FailureList, case_name: str, case_fn: Callable[[], None]) -> None:
    """执行单个 expectation case，并在失败时收集异常。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 统一执行单个 expectation case。
    - 遇到普通异常时把 `(case_name, exc)` 追加到共享失败列表。
    - 保留 `KeyboardInterrupt` 与 `SystemExit` 的直接中断语义。

    使用示例:
    - `run_case(failures, "CASE-1", case_static_contract)`

    关联文件:
    - spec: [`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [`test/pass/test_launch_kernel_cost_func.py`](../../../../test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [`expectation/pass/tuning/launch_kernel_cost_func/_shared.py`](../../../../expectation/pass/tuning/launch_kernel_cost_func/_shared.py)
    """

    if not case_name:
        raise ValueError("case_name must be non-empty")
    if not callable(case_fn):
        raise TypeError("case_fn must be callable")

    try:
        case_fn()
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as exc:  # noqa: BLE001 - expectation 需要统一收集失败
        failures.append((case_name, exc))


def raise_if_failures(expectation_name: str, failures: FailureList) -> None:
    """在存在失败 case 时统一抛出 `AssertionError`。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 在所有 case 跑完后统一检查失败列表。
    - 若存在失败，则使用稳定摘要格式抛出 `AssertionError`。

    使用示例:
    - `raise_if_failures("launch-kernel-cost-func expectation", failures)`

    关联文件:
    - spec: [`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [`test/pass/test_launch_kernel_cost_func.py`](../../../../test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [`expectation/pass/tuning/launch_kernel_cost_func/_shared.py`](../../../../expectation/pass/tuning/launch_kernel_cost_func/_shared.py)
    """

    if not expectation_name:
        raise ValueError("expectation_name must be non-empty")
    if not failures:
        return

    details = "\n".join(
        f"- {case_name}: {type(exc).__name__}: {exc}"
        for case_name, exc in failures
    )
    raise AssertionError(f"{expectation_name} failed ({len(failures)} cases):\n{details}")


def run_ircheck_success(case_text: str, *, source_path: str) -> IrcheckResult:
    """运行一条成功路径 ircheck case 并返回结果。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 统一调用 `run_ircheck_text(...)`。
    - 锁定成功路径的最小合同：`ok=True`、`exit_code=0`、`failed_check=None`、`message` 为空。

    使用示例:
    - `result = run_ircheck_success(case_text, source_path="case#all")`

    关联文件:
    - spec: [`spec/tools/ircheck.md`](../../../../spec/tools/ircheck.md)
    - test: [`test/pass/test_launch_kernel_cost_func.py`](../../../../test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [`expectation/pass/tuning/launch_kernel_cost_func/_shared.py`](../../../../expectation/pass/tuning/launch_kernel_cost_func/_shared.py)
    - 功能实现: [`kernel_gen/tools/ircheck.py`](../../../../kernel_gen/tools/ircheck.py)
    """

    result = run_ircheck_text(case_text, source_path=source_path)
    assert result.ok is True, f"expected ok=True, got ok={result.ok}, message={result.message!r}"
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert result.failed_check is None, "successful ircheck run must not report failed_check"
    assert result.message in (None, ""), f"successful ircheck run must not report message, got {result.message!r}"
    return result


def run_ircheck_failure(case_text: str, *, source_path: str) -> IrcheckResult:
    """运行一条失败路径 ircheck case 并返回结果。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 统一调用 `run_ircheck_text(...)`。
    - 锁定失败路径的最小合同：`ok=False` 且 `message` 非空。

    使用示例:
    - `result = run_ircheck_failure(case_text, source_path="case#bad-kind")`

    关联文件:
    - spec: [`spec/tools/ircheck.md`](../../../../spec/tools/ircheck.md)
    - test: [`test/pass/test_launch_kernel_cost_func.py`](../../../../test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [`expectation/pass/tuning/launch_kernel_cost_func/_shared.py`](../../../../expectation/pass/tuning/launch_kernel_cost_func/_shared.py)
    - 功能实现: [`kernel_gen/tools/ircheck.py`](../../../../kernel_gen/tools/ircheck.py)
    """

    result = run_ircheck_text(case_text, source_path=source_path)
    assert result.ok is False, "failing ircheck run must report ok=False"
    assert result.message is not None, "failing ircheck run must expose message"
    return result


__all__ = [
    "FailureItem",
    "FailureList",
    "raise_if_failures",
    "run_case",
    "run_ircheck_failure",
    "run_ircheck_success",
]
