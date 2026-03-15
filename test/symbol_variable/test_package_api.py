"""package api tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 python.symbol_variable 包入口导出边界、对象一致性与旧路径禁用约束。

使用示例:
- pytest -q test/symbol_variable/test_package_api.py

关联文件:
- 功能实现: python/symbol_variable/__init__.py
- Spec 文档: spec/symbol_variable/package_api.md
- 测试文件: test/symbol_variable/test_package_api.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# PM-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 04:10:18 +0800
# 最近一次运行成功时间: 2026-03-16 04:10:18 +0800
# 功能说明: 验证 python.symbol_variable 顶层导入可用。
# 使用示例: pytest -q test/symbol_variable/test_package_api.py -k test_python_symbol_variable_imports
# 对应功能实现文件路径: python/symbol_variable/__init__.py
# 对应 spec 文件路径: spec/symbol_variable/package_api.md
# 对应测试文件路径: test/symbol_variable/test_package_api.py
def test_python_symbol_variable_imports() -> None:
    from python.symbol_variable import Memory, MemorySpace, SymbolDim, SymbolShape

    assert Memory is not None
    assert MemorySpace is not None
    assert SymbolDim is not None
    assert SymbolShape is not None


# PM-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 04:10:18 +0800
# 最近一次运行成功时间: 2026-03-16 04:10:18 +0800
# 功能说明: 验证旧路径不再可用。
# 使用示例: pytest -q test/symbol_variable/test_package_api.py -k test_legacy_import_disabled
# 对应功能实现文件路径: python/symbol_variable/__init__.py
# 对应 spec 文件路径: spec/symbol_variable/package_api.md
# 对应测试文件路径: test/symbol_variable/test_package_api.py
def test_legacy_import_disabled() -> None:
    import importlib

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("symbol_variable")


# PM-007
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 04:10:18 +0800
# 最近一次运行成功时间: 2026-03-16 04:10:18 +0800
# 功能说明: 验证旧子模块路径不可导入。
# 使用示例: pytest -q test/symbol_variable/test_package_api.py -k test_legacy_submodule_import_disabled
# 对应功能实现文件路径: python/symbol_variable/__init__.py
# 对应 spec 文件路径: spec/symbol_variable/package_api.md
# 对应测试文件路径: test/symbol_variable/test_package_api.py
def test_legacy_submodule_import_disabled() -> None:
    import importlib

    legacy_modules = [
        "symbol_variable.symbol_dim",
        "symbol_variable.symbol_shape",
        "symbol_variable.memory",
        "symbol_variable.type",
    ]
    for module_name in legacy_modules:
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module_name)


# PM-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 04:10:18 +0800
# 最近一次运行成功时间: 2026-03-16 04:10:18 +0800
# 功能说明: 验证 python.symbol_variable 顶层重新导出的类型对象与子模块一致。
# 使用示例: pytest -q test/symbol_variable/test_package_api.py -k test_python_package_type_exports
# 对应功能实现文件路径: python/symbol_variable/__init__.py
# 对应 spec 文件路径: spec/symbol_variable/package_api.md
# 对应测试文件路径: test/symbol_variable/test_package_api.py
def test_python_package_type_exports() -> None:
    from python.symbol_variable import Farmat as PackageFarmat
    from python.symbol_variable import NumericType as PackageNumericType
    from python.symbol_variable.type import Farmat as ModuleFarmat
    from python.symbol_variable.type import NumericType as ModuleNumericType

    assert PackageNumericType is ModuleNumericType
    assert PackageFarmat is ModuleFarmat


# PM-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 04:10:18 +0800
# 最近一次运行成功时间: 2026-03-16 04:10:18 +0800
# 功能说明: 验证顶层导出的类型可直接参与 Memory 构造。
# 使用示例: pytest -q test/symbol_variable/test_package_api.py -k test_package_type_construct_memory
# 对应功能实现文件路径: python/symbol_variable/__init__.py
# 对应 spec 文件路径: spec/symbol_variable/package_api.md
# 对应测试文件路径: test/symbol_variable/test_package_api.py
def test_package_type_construct_memory() -> None:
    from python.symbol_variable import Farmat, Memory, MemorySpace, NumericType

    mem = Memory([1, 2], NumericType.Float32, space=MemorySpace.GM, format=Farmat.Norm)

    assert mem.dtype is NumericType.Float32


# PM-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 04:10:18 +0800
# 最近一次运行成功时间: 2026-03-16 04:10:18 +0800
# 功能说明: 验证 python.symbol_variable.__all__ 与公开导出集合一致。
# 使用示例: pytest -q test/symbol_variable/test_package_api.py -k test_python_package_all_boundary
# 对应功能实现文件路径: python/symbol_variable/__init__.py
# 对应 spec 文件路径: spec/symbol_variable/package_api.md
# 对应测试文件路径: test/symbol_variable/test_package_api.py
def test_python_package_all_boundary() -> None:
    import python.symbol_variable as package_module

    assert package_module.__all__ == [
        "Farmat",
        "LocalSpaceMeta",
        "Memory",
        "MemorySpace",
        "NumericType",
        "SymbolDim",
        "SymbolList",
        "SymbolShape",
    ]


# PM-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 04:10:18 +0800
# 最近一次运行成功时间: 2026-03-16 04:10:18 +0800
# 功能说明: 验证 import * 仅暴露包入口约定的公开符号。
# 使用示例: pytest -q test/symbol_variable/test_package_api.py -k test_python_package_import_star_exports_only_public_names
# 对应功能实现文件路径: python/symbol_variable/__init__.py
# 对应 spec 文件路径: spec/symbol_variable/package_api.md
# 对应测试文件路径: test/symbol_variable/test_package_api.py
def test_python_package_import_star_exports_only_public_names() -> None:
    namespace: dict[str, object] = {}

    exec("from python.symbol_variable import *", {}, namespace)

    assert sorted(namespace) == [
        "Farmat",
        "LocalSpaceMeta",
        "Memory",
        "MemorySpace",
        "NumericType",
        "SymbolDim",
        "SymbolList",
        "SymbolShape",
    ]
