"""launch-kernel-cost-func expectation 目录入口。

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 作为当前 tracked worktree 中 `expectation.pass.tuning.launch_kernel_cost_func` 的统一目录入口。
- 当前入口只承接已生效的 `compute / memory` expectation 资产，不再依赖主仓额外状态中的旧四 kind package。
- 通过 canonical package import 接线到 `launch_kernel_cost_func_compute_memory`，保持纯 worktree 场景可直接运行。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.pass.tuning.launch_kernel_cost_func`

关联文件:
- spec: [`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../spec/pass/tuning/launch_kernel_cost_func.md)
- test: [`test/pass/test_launch_kernel_cost_func.py`](../../../../test/pass/test_launch_kernel_cost_func.py)
- 功能实现: [`expectation/pass/tuning/launch_kernel_cost_func/__main__.py`](../../../../expectation/pass/tuning/launch_kernel_cost_func/__main__.py)
- 功能实现: [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py`](../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py)
"""

from __future__ import annotations

from importlib import import_module

_CANONICAL_RUNNER_MODULE = (
    "expectation.pass.tuning.launch_kernel_cost_func_compute_memory.__main__"
)


def _load_compute_memory_runner_module() -> object:
    """加载当前目录入口对应的 compute/memory runner 模块。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 包上下文可用时优先走 sibling package import。
    - 只有 sibling package 本身缺失时，才 fallback 到 canonical package import。
    - 不再读取主仓额外状态中的历史 `invalid_kind` / `multi_kind` 入口。

    使用示例:
    - `runner_module = _load_compute_memory_runner_module()`

    关联文件:
    - spec: [`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [`test/pass/test_launch_kernel_cost_func.py`](../../../../test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [`expectation/pass/tuning/launch_kernel_cost_func/__main__.py`](../../../../expectation/pass/tuning/launch_kernel_cost_func/__main__.py)
    """

    try:
        from ..launch_kernel_cost_func_compute_memory import __main__ as module
    except ModuleNotFoundError as exc:
        missing_module_names = {
            "launch_kernel_cost_func_compute_memory",
            _CANONICAL_RUNNER_MODULE,
        }
        if exc.name not in missing_module_names:
            raise
        return import_module(_CANONICAL_RUNNER_MODULE)

    return module


runner_compute_memory_module = _load_compute_memory_runner_module()


def main() -> None:
    """运行当前目录级 launch-kernel-cost-func expectation。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 串行运行当前生效的 `compute / memory` expectation 入口。
    - 不接线历史四 kind 子资产，也不依赖未 tracked 的旧目录文件。

    使用示例:
    - `main()`

    关联文件:
    - spec: [`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [`test/pass/test_launch_kernel_cost_func.py`](../../../../test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [`expectation/pass/tuning/launch_kernel_cost_func/__main__.py`](../../../../expectation/pass/tuning/launch_kernel_cost_func/__main__.py)
    """

    print("[RUN] compute_memory")
    runner_compute_memory_module.main()
    print("[OK] launch-kernel-cost-func expectation passed")


if __name__ == "__main__":
    main()
