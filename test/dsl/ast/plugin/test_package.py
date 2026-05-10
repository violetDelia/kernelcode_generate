"""DSL AST plugin package facade tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast.plugin` 包根公开注册 API。
- 测试结构对应 `spec/dsl/ast/plugin/__init__.md` 与 `kernel_gen/dsl/ast/plugin/__init__.py`。

使用示例:
- pytest -q test/dsl/ast/plugin/test_package.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/plugin/__init__.py
- Spec 文档: spec/dsl/ast/plugin/__init__.md
- 测试文件: test/dsl/ast/plugin/test_package.py
"""

from __future__ import annotations

import importlib

from kernel_gen.operation import kernel
from kernel_gen.operation.nn import relu


def test_plugin_package_exports_registry_api_and_loads_builtin_modules() -> None:
    """plugin facade 只导出注册 API，并在导入时加载 builtin 注册。"""

    plugin = importlib.import_module("kernel_gen.dsl.ast.plugin")
    namespace: dict[str, object] = {}
    exec("from kernel_gen.dsl.ast.plugin import *", namespace)
    public_names = sorted(name for name in namespace if not name.startswith("__"))

    assert public_names == [
        "BuiltinCall",
        "BuiltinEntry",
        "all_builtin_names",
        "dsl_builtin",
        "external_builtin",
        "lookup_builtin",
    ]
    assert plugin.lookup_builtin(relu) is not None
    assert plugin.lookup_builtin(kernel.add) is not None
    assert "_REGISTRY" not in public_names
