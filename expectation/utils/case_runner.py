"""Expectation case runner helpers.

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 为 expectation 脚本提供统一的 case 执行与失败汇总入口，减少每个脚本重复维护 `failures`、`try/except` 与统一报错格式。
- `run_case(...)` 负责执行单个 case，并把普通异常收集到共享 `failures` 列表中。
- `raise_if_failures(...)` 负责在所有 case 跑完后统一抛出 `AssertionError`，格式稳定，便于 expectation 黑盒复用。

使用示例:
- `failures: list[tuple[str, BaseException]] = []`
- `run_case(failures, "CASE-1", case_ok)`
- `run_case(failures, "CASE-2", case_fail)`
- `raise_if_failures("my expectation", failures)`

关联文件:
- spec: [`agents/standard/测试文件约定.md`](agents/standard/测试文件约定.md)
- test: [`test/tools/test_case_runner.py`](test/tools/test_case_runner.py)
- 功能实现: [`expectation/utils/case_runner.py`](expectation/utils/case_runner.py)
"""

from __future__ import annotations

from collections.abc import Callable

FailureItem = tuple[str, BaseException]
FailureList = list[FailureItem]


def run_case(failures: FailureList, case_name: str, case_fn: Callable[[], None]) -> None:
    """执行单个 expectation case，并在失败时收集异常。

    参数:
    - failures: 共享失败列表；若 `case_fn` 抛出普通异常，则追加 `(case_name, exc)`。
    - case_name: 用于最终汇总的稳定 case 名称，例如 `CASE-1`。
    - case_fn: 不接受参数、执行单个 case 断言的函数。

    使用示例:
    - `run_case(failures, "CASE-1", case_static_contract)`
    - `run_case(failures, "CASE-2", lambda: assert_contract("x"))`
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

    参数:
    - expectation_name: 当前 expectation 的稳定名称，会写入最终错误消息。
    - failures: 由 `run_case(...)` 收集的失败列表。

    使用示例:
    - `raise_if_failures("nn_to_kernel broadcast expectation", failures)`
    """

    if not expectation_name:
        raise ValueError("expectation_name must be non-empty")
    if not failures:
        return

    details = "\n".join(
        f"- {case_name}: {type(exc).__name__}: {exc}"
        for case_name, exc in failures
    )
    raise AssertionError(
        f"{expectation_name} failed ({len(failures)} cases):\n{details}"
    )


__all__ = [
    "FailureItem",
    "FailureList",
    "raise_if_failures",
    "run_case",
]
