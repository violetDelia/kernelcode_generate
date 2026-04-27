"""package api tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 kernel_gen.symbol_variable 包入口导出边界、对象一致性与旧路径禁用约束。

使用示例:
- pytest -q test/symbol_variable/test_package_api.py

关联文件:
- 功能实现: kernel_gen/symbol_variable/__init__.py
- Spec 文档: spec/symbol_variable/package_api.md
- 测试文件: test/symbol_variable/test_package_api.py

覆盖率信息:
- 当前覆盖率: `98.86%`（`kernel_gen.symbol_variable`，全量用例，2026-04-09 +0800）
- 达标判定: 已达到 `95%` 覆盖率达标线。
- 说明: 本文件聚焦包入口边界；单文件运行的包级覆盖率不作为达标口径。

覆盖率命令:
- `pytest --cov=kernel_gen.symbol_variable --cov-report=term-missing --cov-fail-under=95 -q test/symbol_variable`
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


LEGACY_MODULES = [
    "symbol_variable",
    "symbol_variable.symbol_dim",
    "symbol_variable.symbol_shape",
    "symbol_variable.memory",
    "symbol_variable.type",
]
PUBLIC_EXPORTS = [
    "Farmat",
    "LocalSpaceMeta",
    "Memory",
    "MemorySpace",
    "NumericType",
    "SymbolDim",
    "SymbolList",
    "SymbolShape",
]


def _without_test_dir() -> None:
    """移除测试目录并清理旧模块缓存。"""
    test_dir = str(Path(__file__).resolve().parents[1])
    sys.path[:] = [path for path in sys.path if path != test_dir]
    for module_name in LEGACY_MODULES:
        sys.modules.pop(module_name, None)


# PM-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:52:17 +0800
# 最近一次运行成功时间: 2026-03-22 13:52:17 +0800
# 功能说明: 验证 kernel_gen.symbol_variable 顶层导入可用。
# 使用示例: pytest -q test/symbol_variable/test_package_api.py -k test_python_symbol_variable_imports
# 对应功能实现文件路径: kernel_gen/symbol_variable/__init__.py
# 对应 spec 文件路径: spec/symbol_variable/package_api.md
# 对应测试文件路径: test/symbol_variable/test_package_api.py
def test_python_symbol_variable_imports() -> None:
    from kernel_gen.symbol_variable import Memory, MemorySpace, SymbolDim, SymbolShape

    assert Memory is not None
    assert MemorySpace is not None
    assert SymbolDim is not None
    assert SymbolShape is not None


# PM-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:52:17 +0800
# 最近一次运行成功时间: 2026-03-22 13:52:17 +0800
# 功能说明: 验证旧路径不再可用。
# 使用示例: pytest -q test/symbol_variable/test_package_api.py -k test_legacy_import_disabled
# 对应功能实现文件路径: kernel_gen/symbol_variable/__init__.py
# 对应 spec 文件路径: spec/symbol_variable/package_api.md
# 对应测试文件路径: test/symbol_variable/test_package_api.py
def test_legacy_import_disabled() -> None:
    import importlib

    original_sys_path = sys.path[:]
    try:
        _without_test_dir()
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("symbol_variable")
    finally:
        sys.path[:] = original_sys_path


# PM-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:52:17 +0800
# 最近一次运行成功时间: 2026-03-22 13:52:17 +0800
# 功能说明: 验证旧子模块路径不可导入。
# 使用示例: pytest -q test/symbol_variable/test_package_api.py -k test_legacy_submodule_import_disabled
# 对应功能实现文件路径: kernel_gen/symbol_variable/__init__.py
# 对应 spec 文件路径: spec/symbol_variable/package_api.md
# 对应测试文件路径: test/symbol_variable/test_package_api.py
def test_legacy_submodule_import_disabled() -> None:
    import importlib

    original_sys_path = sys.path[:]
    try:
        _without_test_dir()
        for module_name in LEGACY_MODULES[1:]:
            with pytest.raises(ModuleNotFoundError):
                importlib.import_module(module_name)
    finally:
        sys.path[:] = original_sys_path


# PM-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:52:17 +0800
# 最近一次运行成功时间: 2026-03-22 13:52:17 +0800
# 功能说明: 验证 kernel_gen.symbol_variable 顶层重新导出的对象与子模块一致。
# 使用示例: pytest -q test/symbol_variable/test_package_api.py -k test_python_package_type_exports
# 对应功能实现文件路径: kernel_gen/symbol_variable/__init__.py
# 对应 spec 文件路径: spec/symbol_variable/package_api.md
# 对应测试文件路径: test/symbol_variable/test_package_api.py
def test_python_package_type_exports() -> None:
    from kernel_gen.symbol_variable import Farmat as PackageFarmat
    from kernel_gen.symbol_variable import LocalSpaceMeta as PackageLocalSpaceMeta
    from kernel_gen.symbol_variable import Memory as PackageMemory
    from kernel_gen.symbol_variable import MemorySpace as PackageMemorySpace
    from kernel_gen.symbol_variable import NumericType as PackageNumericType
    from kernel_gen.symbol_variable import SymbolDim as PackageSymbolDim
    from kernel_gen.symbol_variable import SymbolList as PackageSymbolList
    from kernel_gen.symbol_variable import SymbolShape as PackageSymbolShape
    from kernel_gen.symbol_variable.memory import LocalSpaceMeta as ModuleLocalSpaceMeta
    from kernel_gen.symbol_variable.memory import Memory as ModuleMemory
    from kernel_gen.symbol_variable.memory import MemorySpace as ModuleMemorySpace
    from kernel_gen.symbol_variable.symbol_dim import SymbolDim as ModuleSymbolDim
    from kernel_gen.symbol_variable.symbol_shape import SymbolList as ModuleSymbolList
    from kernel_gen.symbol_variable.symbol_shape import SymbolShape as ModuleSymbolShape
    from kernel_gen.symbol_variable.type import Farmat as ModuleFarmat
    from kernel_gen.symbol_variable.type import NumericType as ModuleNumericType

    assert PackageMemory is ModuleMemory
    assert PackageSymbolDim is ModuleSymbolDim
    assert PackageSymbolList is ModuleSymbolList
    assert PackageSymbolShape is ModuleSymbolShape
    assert PackageLocalSpaceMeta is ModuleLocalSpaceMeta
    assert PackageMemorySpace is ModuleMemorySpace
    assert PackageNumericType is ModuleNumericType
    assert PackageFarmat is ModuleFarmat


# PM-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:52:17 +0800
# 最近一次运行成功时间: 2026-03-22 13:52:17 +0800
# 功能说明: 验证顶层导出的类型可直接参与 Memory 构造。
# 使用示例: pytest -q test/symbol_variable/test_package_api.py -k test_package_type_construct_memory
# 对应功能实现文件路径: kernel_gen/symbol_variable/__init__.py
# 对应 spec 文件路径: spec/symbol_variable/package_api.md
# 对应测试文件路径: test/symbol_variable/test_package_api.py
def test_package_type_construct_memory() -> None:
    from kernel_gen.symbol_variable import Farmat, Memory, MemorySpace, NumericType

    mem = Memory([1, 2], NumericType.Float32, space=MemorySpace.GM, format=Farmat.Norm)

    assert mem.dtype is NumericType.Float32


# PM-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:52:17 +0800
# 最近一次运行成功时间: 2026-03-22 13:52:17 +0800
# 功能说明: 验证 kernel_gen.symbol_variable 包入口稳定公开集合可显式导入且不额外暴露 Ptr。
# 使用示例: pytest -q test/symbol_variable/test_package_api.py -k test_python_package_exports_match_public_contract
# 对应功能实现文件路径: kernel_gen/symbol_variable/__init__.py
# 对应 spec 文件路径: spec/symbol_variable/package_api.md
# 对应测试文件路径: test/symbol_variable/test_package_api.py
def test_python_package_exports_match_public_contract() -> None:
    import kernel_gen.symbol_variable as package_module

    assert sorted(name for name in PUBLIC_EXPORTS if hasattr(package_module, name)) == PUBLIC_EXPORTS
    assert not hasattr(package_module, "Ptr")
    assert not hasattr(package_module, "is_integer_dtype")
    assert not hasattr(package_module, "is_float_dtype")


# PM-007
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:52:17 +0800
# 最近一次运行成功时间: 2026-03-22 13:52:17 +0800
# 功能说明: 验证 import * 仅暴露包入口约定的公开符号。
# 使用示例: pytest -q test/symbol_variable/test_package_api.py -k test_python_package_import_star_exports_only_public_names
# 对应功能实现文件路径: kernel_gen/symbol_variable/__init__.py
# 对应 spec 文件路径: spec/symbol_variable/package_api.md
# 对应测试文件路径: test/symbol_variable/test_package_api.py
def test_python_package_import_star_exports_only_public_names() -> None:
    namespace: dict[str, object] = {}

    exec("from kernel_gen.symbol_variable import *", {}, namespace)

    assert sorted(namespace) == PUBLIC_EXPORTS
