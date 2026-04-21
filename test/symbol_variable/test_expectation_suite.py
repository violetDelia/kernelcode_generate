"""symbol_variable expectation suite tests.

创建者: 大闸蟹
最后修改人: 大闸蟹

功能说明:
- 验证 `expectation.symbol_variable` 目录级入口可作为 symbol_variable 合同真源运行。
- 该测试只覆盖 expectation 入口可执行性，不重复断言 `SymbolDim` 或 `Memory` 的内部行为。

使用示例:
- `pytest -q test/symbol_variable/test_expectation_suite.py`

关联文件:
- spec: [`spec/symbol_variable/package_api.md`](../../spec/symbol_variable/package_api.md)
- spec: [`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)
- spec: [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)
- test: [`test/symbol_variable/test_expectation_suite.py`](../../test/symbol_variable/test_expectation_suite.py)
- 功能实现: [`expectation/symbol_variable/__main__.py`](../../expectation/symbol_variable/__main__.py)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_symbol_variable_expectation_package_entrypoint() -> None:
    """验证 symbol_variable expectation 目录级入口可完整运行。

    创建者: 大闸蟹
    最后修改人: 大闸蟹

    功能说明:
    - 使用 `python -m expectation.symbol_variable` 触发目录级入口。
    - 设置 `PYTHONDONTWRITEBYTECODE=1`，避免测试运行生成新的缓存文件。

    使用示例:
    - `pytest -q test/symbol_variable/test_expectation_suite.py -k test_symbol_variable_expectation_package_entrypoint`

    关联文件:
    - spec: [`spec/symbol_variable/package_api.md`](../../spec/symbol_variable/package_api.md)
    - test: [`test/symbol_variable/test_expectation_suite.py`](../../test/symbol_variable/test_expectation_suite.py)
    - 功能实现: [`expectation/symbol_variable/__main__.py`](../../expectation/symbol_variable/__main__.py)
    """

    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "expectation.symbol_variable"],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[CASE-1]" in result.stdout
    assert "symbol_variable.symbol_dim" in result.stdout
    assert "symbol_variable.memory" in result.stdout
