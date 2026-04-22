"""case runner helpers for tool-style tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 提供可复用的 case 执行与失败汇总入口，供工具型测试直接调用。
- 将“单个 case 捕获异常”和“最终统一抛出汇总错误”拆成两个稳定 helper。

使用示例:
- failures: list[tuple[str, BaseException]] = []
- run_case(failures, "CASE-1", lambda: None)
- raise_if_failures("tile reduce example", failures)

关联文件:
- spec: [spec/tools/case_runner.md](../../spec/tools/case_runner.md)
- test: [test/tools/test_case_runner.py](../../test/tools/test_case_runner.py)
- 功能实现: [kernel_gen/tools/case_runner.py](case_runner.py)
"""

from __future__ import annotations

from collections.abc import Callable

CaseFailure = tuple[str, BaseException]


def run_case(failures: list[CaseFailure], case_name: str, case_fn: Callable[[], object]) -> None:
    """执行单个 case，并把异常收集到失败列表中。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - case 成功时不修改失败列表。
    - case 失败时捕获普通异常并追加 `(case_name, exc)`。
    - 不吞掉 `KeyboardInterrupt` / `SystemExit` 之类的异常类型。

    使用示例:
    - failures: list[CaseFailure] = []
    - run_case(failures, "CASE-OK", lambda: None)

    关联文件:
    - spec: [spec/tools/case_runner.md](../../spec/tools/case_runner.md)
    - test: [test/tools/test_case_runner.py](../../test/tools/test_case_runner.py)
    - 功能实现: [kernel_gen/tools/case_runner.py](case_runner.py)
    """

    if not case_name:
        raise ValueError("case_name must be non-empty")
    if not callable(case_fn):
        raise TypeError("case_fn must be callable")
    try:
        case_fn()
    except Exception as exc:  # noqa: BLE001 - 工具层需要收集普通异常
        failures.append((case_name, exc))


def raise_if_failures(title: str, failures: list[CaseFailure]) -> None:
    """在存在失败 case 时抛出统一的摘要异常。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 失败列表为空时直接返回。
    - 失败列表非空时生成稳定的多行摘要，便于 pytest / CLI 断言。

    使用示例:
    - raise_if_failures("tile reduce example", failures)

    关联文件:
    - spec: [spec/tools/case_runner.md](../../spec/tools/case_runner.md)
    - test: [test/tools/test_case_runner.py](../../test/tools/test_case_runner.py)
    - 功能实现: [kernel_gen/tools/case_runner.py](case_runner.py)
    """

    if not failures:
        return
    lines = [f"{title} failed ({len(failures)} cases):"]
    for case_name, exc in failures:
        lines.append(f"- {case_name}: {type(exc).__name__}: {exc}")
    raise AssertionError("\n".join(lines))
