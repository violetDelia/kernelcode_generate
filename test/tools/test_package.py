"""tools package public api tests.


功能说明:
- 只通过 `kernel_gen.tools` 包根验证公开导出和 lazy export 行为。
- 不直连跨文件非公开 helper，作为 repo_conformance S2 的公开 API 证据链。

使用示例:
- pytest -q test/tools/test_package.py

关联文件:
- 功能实现: kernel_gen/tools/__init__.py
- Spec 文档: spec/tools/dsl_run.md
- 测试文件: test/tools/test_package.py
"""

from __future__ import annotations

import importlib

import pytest


def test_tools_package_public_exports() -> None:
    """TC-TOOLS-PKG-001: `kernel_gen.tools` should expose only the documented public symbols."""

    tools_package = importlib.import_module("kernel_gen.tools")
    namespace: dict[str, object] = {}
    exec("from kernel_gen.tools import *", namespace)
    public_names = sorted(name for name in namespace if not name.startswith("__"))

    assert public_names == ["DslRunResult"]
    assert namespace["DslRunResult"] is tools_package.DslRunResult
    assert callable(tools_package.dsl_run)
    assert tools_package.dsl_run.__name__ == "dsl_run"
    assert tools_package.dsl_run.__module__ == "kernel_gen.tools"
    assert tools_package.DslRunResult.__name__ == "DslRunResult"


def test_tools_package_supports_direct_dsl_run_import() -> None:
    """TC-TOOLS-PKG-001A: `from kernel_gen.tools import dsl_run` should resolve to the package-root public function."""

    from kernel_gen.tools import dsl_run as imported_dsl_run

    tools_package = importlib.import_module("kernel_gen.tools")
    assert callable(imported_dsl_run)
    assert imported_dsl_run is tools_package.dsl_run
    assert imported_dsl_run.__module__ == "kernel_gen.tools"


def test_tools_package_rejects_unknown_public_name() -> None:
    """TC-TOOLS-PKG-002: unknown package attributes should still raise AttributeError."""

    tools_package = importlib.import_module("kernel_gen.tools")

    with pytest.raises(AttributeError):
        getattr(tools_package, "missing_tool")
