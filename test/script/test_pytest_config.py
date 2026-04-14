"""pytest config tests.

创建者: 小李飞刀
最后一次更改: jcc你莫辜负

功能说明:
- 校验 `pytest.ini` 中 pytest 配置的关键合同项。

关联文件:
- 功能实现: pytest.ini
- Spec 文档: spec/script/pytest_config.md
- 测试文件: test/script/test_pytest_config.py

使用示例:
- pytest -q test/script/test_pytest_config.py
"""

from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTEST_INI = REPO_ROOT / "pytest.ini"

pytestmark = pytest.mark.infra


def _load_pytest_ini() -> ConfigParser:
    """读取仓库根目录 `pytest.ini` 并解析为 `ConfigParser`。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 统一处理 pytest ini 配置文件的加载入口。
    - 关闭插值，避免把 pytest 原始配置值误解释为 `configparser` 模板。

    使用示例:
    - parser = _load_pytest_ini()

    关联文件:
    - 功能实现: [pytest.ini](pytest.ini)
    - Spec 文档: [spec/script/pytest_config.md](spec/script/pytest_config.md)
    - 测试文件: [test/script/test_pytest_config.py](test/script/test_pytest_config.py)
    """
    parser = ConfigParser(interpolation=None)
    read_files = parser.read(PYTEST_INI, encoding="utf-8")
    assert read_files == [str(PYTEST_INI)]
    return parser


def _split_ini_lines(raw_value: str) -> list[str]:
    """把 pytest ini 多行值拆成去空白后的行列表。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 用于解析 `markers`、`testpaths` 与 `norecursedirs` 这类支持多行书写的配置项。
    - 过滤空行和首尾空白，便于测试按稳定列表断言。

    使用示例:
    - values = _split_ini_lines("a\\n b\\n")

    关联文件:
    - 功能实现: [pytest.ini](pytest.ini)
    - Spec 文档: [spec/script/pytest_config.md](spec/script/pytest_config.md)
    - 测试文件: [test/script/test_pytest_config.py](test/script/test_pytest_config.py)
    """
    return [line.strip() for line in raw_value.splitlines() if line.strip()]


def _pytest_options() -> dict[str, object]:
    """提取 `pytest.ini` 中的 `[pytest]` 配置块。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 基于 `_load_pytest_ini()` 返回的解析结果读取 `[pytest]` 区段。
    - 将多行配置项转换为稳定的列表形式，便于断言关键合同值。

    使用示例:
    - options = _pytest_options()

    关联文件:
    - 功能实现: [pytest.ini](pytest.ini)
    - Spec 文档: [spec/script/pytest_config.md](spec/script/pytest_config.md)
    - 测试文件: [test/script/test_pytest_config.py](test/script/test_pytest_config.py)
    """
    parser = _load_pytest_ini()
    assert parser.has_section("pytest")
    return {
        "markers": _split_ini_lines(parser.get("pytest", "markers", fallback="")),
        "testpaths": _split_ini_lines(parser.get("pytest", "testpaths", fallback="")),
        "addopts": parser.get("pytest", "addopts", fallback="").strip(),
        "norecursedirs": _split_ini_lines(parser.get("pytest", "norecursedirs", fallback="")),
    }


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
    assert options.get("addopts") == "--import-mode=importlib"
    assert options.get("norecursedirs") == ["wt-*", "tmp", "tmp/*", "tmp/**", "__pycache__"]
