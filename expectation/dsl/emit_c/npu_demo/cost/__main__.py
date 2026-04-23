"""emit_c npu_demo cost expectation 目录入口。

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

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

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

try:
    from .._shared import discover_and_run_modules
except ImportError:
    from expectation.dsl.emit_c.npu_demo._shared import discover_and_run_modules


def main() -> None:
    """运行 `cost` 目录下自动发现到的全部 emit_c expectation。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

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
