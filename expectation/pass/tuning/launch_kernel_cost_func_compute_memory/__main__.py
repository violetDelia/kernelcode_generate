"""launch-kernel-cost-func compute/memory expectation runner。

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 汇总 `launch_kernel_cost_func_compute_memory` 目录下当前生效的两 kind expectation。
- 当前只运行 `basic_all.py`，不接线历史 immutable `invalid_kind.py`。
- 作为 `python -m expectation.pass.tuning.launch_kernel_cost_func_compute_memory` 的统一入口。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.pass.tuning.launch_kernel_cost_func_compute_memory`

关联文件:
- spec: [`spec/pass/tuning/launch_kernel_cost_func.md`](spec/pass/tuning/launch_kernel_cost_func.md)
- test: [`test/pass/test_launch_kernel_cost_func.py`](test/pass/test_launch_kernel_cost_func.py)
- 功能实现: [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py`](expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py)
"""

from __future__ import annotations

from importlib import import_module

_CANONICAL_BASIC_ALL_MODULE = (
    "expectation.pass.tuning.launch_kernel_cost_func_compute_memory.basic_all"
)


def _load_runner_basic_all_module() -> object:
    """加载 compute/memory runner 对应的 `basic_all` 模块。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 包上下文正常存在时，优先走相对导入 `from . import basic_all`。
    - 只有在 `basic_all` 目标模块本身缺失，或当前入口没有包上下文时，才 fallback 到 canonical package import。
    - `basic_all.py` 内部真实依赖错误会直接向外抛出，不再被宽泛的 `except ImportError` 兜底吞掉。

    使用示例:
    - `runner_basic_all_module = _load_runner_basic_all_module()`

    关联文件:
    - spec: [`spec/pass/tuning/launch_kernel_cost_func.md`](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [`test/pass/test_launch_kernel_cost_func.py`](test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py`](expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py)
    """

    if not __package__:
        return import_module(_CANONICAL_BASIC_ALL_MODULE)

    try:
        from . import basic_all as module
    except ModuleNotFoundError as exc:
        missing_module_names = {
            "basic_all",
            _CANONICAL_BASIC_ALL_MODULE,
        }
        if exc.name not in missing_module_names:
            raise
        return import_module(_CANONICAL_BASIC_ALL_MODULE)

    return module


runner_basic_all_module = _load_runner_basic_all_module()


def main() -> None:
    """运行 compute/memory 两 kind 的目录级 expectation。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 串行运行当前目录中的 canonical 两 kind expectation。
    - 不导入也不执行历史 immutable `invalid_kind.py`。

    使用示例:
    - `main()`

    关联文件:
    - spec: [`spec/pass/tuning/launch_kernel_cost_func.md`](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [`test/pass/test_launch_kernel_cost_func.py`](test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py`](expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py)
    """

    print("[RUN] basic_all")
    runner_basic_all_module.main()
    print("[OK] launch-kernel-cost-func compute/memory expectation passed")


if __name__ == "__main__":
    main()
