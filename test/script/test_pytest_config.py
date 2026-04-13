"""pyproject pytest config tests.

创建者: 小李飞刀
最后一次更改: jcc你莫辜负

功能说明:
- 校验 `pyproject.toml` 中 pytest 配置的关键合同项。

关联文件:
- 功能实现: pyproject.toml
- Spec 文档: spec/script/pytest_config.md
- 测试文件: test/script/test_pytest_config.py

使用示例:
- pytest -q test/script/test_pytest_config.py
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover - fallback by environment
    try:
        import tomli as tomllib  # type: ignore[assignment]
    except ModuleNotFoundError:  # pragma: no cover - fallback by environment
        tomllib = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / "pyproject.toml"

pytestmark = pytest.mark.infra


def _load_pyproject() -> dict:
    """读取仓库根目录 `pyproject.toml` 并解析为字典。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 统一处理 `tomllib/tomli` 两种 TOML 解析入口。
    - 当当前环境缺少 TOML 解析库时，直接 `pytest.skip(...)`，避免把环境缺件误判为配置失败。

    使用示例:
    - data = _load_pyproject()

    关联文件:
    - 功能实现: [pyproject.toml](pyproject.toml)
    - Spec 文档: [spec/script/pytest_config.md](spec/script/pytest_config.md)
    - 测试文件: [test/script/test_pytest_config.py](test/script/test_pytest_config.py)
    """
    if tomllib is None:
        pytest.skip("tomli is required to parse pyproject.toml")
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def _pytest_options() -> dict:
    """提取 `pyproject.toml` 中的 `tool.pytest.ini_options` 配置块。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 基于 `_load_pyproject()` 返回的完整 TOML 数据继续下钻。
    - 为当前测试文件中的断言统一提供 pytest 配置字典，避免重复拼接嵌套 key。

    使用示例:
    - options = _pytest_options()

    关联文件:
    - 功能实现: [pyproject.toml](pyproject.toml)
    - Spec 文档: [spec/script/pytest_config.md](spec/script/pytest_config.md)
    - 测试文件: [test/script/test_pytest_config.py](test/script/test_pytest_config.py)
    """
    data = _load_pyproject()
    return data.get("tool", {}).get("pytest", {}).get("ini_options", {})


def test_pytest_ini_options_present() -> None:
    """TC-PC-001: pytest 配置块存在且包含 infra 标记。"""
    options = _pytest_options()
    assert options
    markers = options.get("markers", [])
    assert "infra: 标记脚本与基础设施测试" in markers


def test_pytest_config_values() -> None:
    """TC-PC-002: pytest 配置关键项与合同一致。"""
    options = _pytest_options()
    assert options.get("testpaths") == ["test"]
    assert options.get("addopts") == ["--import-mode=importlib"]
    assert options.get("norecursedirs") == ["wt-*", "tmp", "tmp/*", "tmp/**", "__pycache__"]
