"""expectation 全量递归入口。

创建者: Codex
最后修改人: Codex

功能说明:
- 作为 `python -m expectation` 的根入口，递归运行 `expectation` 子目录下所有 case。
- 该入口不依赖子目录手写 `__main__.py` 聚合表，新增 case 只要提供无参 `main()` 就会被自动发现。
- 私有 helper、`utils` 工具目录、`__main__.py` 聚合入口不会作为 case 重复执行。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation`

关联文件:
- spec: [`AGENTS.md`](../AGENTS.md)
- test: [`expectation/__main__.py`](__main__.py)
- 功能实现: [`expectation/utils/suite_runner.py`](utils/suite_runner.py)
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.suite_runner import run_discovered_expectation_suite


def main() -> None:
    """运行 `expectation` 目录下递归发现的全部 case。

    创建者: Codex
    最后修改人: Codex

    功能说明:
    - 调用 `run_discovered_expectation_suite(...)`，以 `expectation` 为根包递归扫描所有 case。
    - 失败格式复用 `expectation.utils.case_runner`，方便定位具体模块。

    使用示例:
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation`

    关联文件:
    - spec: [`AGENTS.md`](../AGENTS.md)
    - test: [`expectation/__main__.py`](__main__.py)
    - 功能实现: [`expectation/utils/suite_runner.py`](utils/suite_runner.py)
    """

    run_discovered_expectation_suite("expectation", __file__, "expectation")


if __name__ == "__main__":
    main()
