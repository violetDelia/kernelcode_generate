"""emit_c npu_demo cost expectation 目录入口。

创建者: 金铲铲大作战
最后一次更改: 朽木露琪亚

功能说明:
- 运行 `expectation/dsl/emit_c/npu_demo/cost` 目录下的全部 expectation。
- 聚合 `tuner.cost` 在 npu_demo 目标下的节点级 cost helper 源码合同。
- 作为 `python -m expectation.dsl.emit_c.npu_demo.cost` 的统一入口。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.emit_c.npu_demo.cost`

关联文件:
- spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
- spec: [`spec/pass/tuning/launch_kernel_cost_func.md`](spec/pass/tuning/launch_kernel_cost_func.md)
- test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/cost/__main__.py`](expectation/dsl/emit_c/npu_demo/cost/__main__.py)
"""

from importlib import import_module
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent


def _load_shared_runner() -> object:
    """加载 `cost` 目录入口依赖的共享 runner。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 包上下文可用时优先走 sibling package import。
    - 包上下文缺失时退回绝对导入，避免依赖旧目录结构或临时 `sys.path` 注入。

    使用示例:
    - `discover_and_run_modules = _load_shared_runner()`

    关联文件:
    - spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
    - test: [`test/tools/test_emitc_case_runner.py`](test/tools/test_emitc_case_runner.py)
    - 功能实现: [`expectation/dsl/emit_c/npu_demo/cost/__main__.py`](expectation/dsl/emit_c/npu_demo/cost/__main__.py)
    """

    if __package__:
        from .._shared import discover_and_run_modules as module_runner
        return module_runner
    return import_module("expectation.dsl.emit_c.npu_demo._shared").discover_and_run_modules


discover_and_run_modules = _load_shared_runner()


def main() -> None:
    """运行 `cost` 目录下自动发现到的全部 emit_c expectation。

    创建者: 金铲铲大作战
    最后一次更改: 朽木露琪亚

    功能说明:
    - 自动发现 `cost/` 目录下全部非 `_*.py` expectation 文件。
    - 统一串行执行 `kernel.add`、`kernel.matmul` 与 `dma.copy` 的 cost helper 合同。

    使用示例:
    - `main()`

    关联文件:
    - spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
    - test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
    - 功能实现: [`expectation/dsl/emit_c/npu_demo/cost/__main__.py`](expectation/dsl/emit_c/npu_demo/cost/__main__.py)
    """

    discover_and_run_modules(CURRENT_DIR, "expectation.dsl.emit_c.npu_demo.cost")


if __name__ == "__main__":
    main()
