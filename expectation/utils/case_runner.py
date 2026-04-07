"""Expectation case runner 共享辅助。

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 为 expectation 脚本提供统一的多 case 执行与汇总失败行为。
- 每个 case 都会独立执行；只有全部 case 跑完后，才按汇总结果抛出异常。
- 预期失败 case 可在各脚本内部自行处理；本辅助只负责收集未被脚本消费的异常。

使用示例:
- `from expectation.utils.case_runner import run_case, raise_if_failures`
- `run_case(failures, "CASE-1", check_case_1)`
- `raise_if_failures("dsl mlir_gen broadcast expectation", failures)`

关联文件:
- spec: [`spec/dsl/mlir_gen.md`](spec/dsl/mlir_gen.md)
- test: [`test/dsl/test_ast_visitor.py`](test/dsl/test_ast_visitor.py)
- 功能实现: [`expectation/utils/case_runner.py`](expectation/utils/case_runner.py)
"""

from __future__ import annotations

from collections.abc import Callable

Failure = tuple[str, BaseException]


def run_case(failures: list[Failure], case_name: str, action: Callable[[], None]) -> None:
    """执行单个 case，并把非中断异常加入汇总列表。"""

    try:
        action()
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        failures.append((case_name, exc))


def raise_if_failures(prefix: str, failures: list[Failure]) -> None:
    """若存在失败 case，则统一抛出汇总异常。"""

    if failures:
        details = "\n".join(f"- {name}: {type(exc).__name__}: {exc}" for name, exc in failures)
        raise AssertionError(f"{prefix} failed ({len(failures)} cases):\n{details}")
