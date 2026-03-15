"""package api tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 symbol_variable 包级导出策略。

使用示例:
- pytest -q test/symbol_variable/test_package_api.py

关联文件:
- 功能实现: symbol_variable/__init__.py
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


# PA-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-15 23:49:01 +0800
# 最近一次运行成功时间: 2026-03-15 23:49:01 +0800
# 功能说明: 验证现有公共类型包级导出可用。
# 使用示例: pytest -q test/symbol_variable/test_package_api.py -k test_package_exports_base
# 对应功能实现文件路径: symbol_variable/__init__.py
# 对应 spec 文件路径: spec/symbol_variable/package_api.md
# 对应测试文件路径: test/symbol_variable/test_package_api.py
def test_package_exports_base() -> None:
    from symbol_variable import (  # noqa: WPS433 - import for API validation
        LocalSpaceMeta,
        Memory,
        MemorySpace,
        SymbolDim,
        SymbolList,
        SymbolShape,
    )

    assert LocalSpaceMeta is not None
    assert Memory is not None
    assert MemorySpace is not None
    assert SymbolDim is not None
    assert SymbolList is not None
    assert SymbolShape is not None


# PA-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-15 23:49:01 +0800
# 最近一次运行成功时间: 2026-03-15 23:49:01 +0800
# 功能说明: 验证新增 NumericType/Farmat 顶层导出。
# 使用示例: pytest -q test/symbol_variable/test_package_api.py -k test_package_exports_types
# 对应功能实现文件路径: symbol_variable/__init__.py
# 对应 spec 文件路径: spec/symbol_variable/package_api.md
# 对应测试文件路径: test/symbol_variable/test_package_api.py
def test_package_exports_types() -> None:
    from symbol_variable import Farmat, NumericType  # noqa: WPS433

    assert NumericType is not None
    assert Farmat is not None


# PA-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-15 23:49:01 +0800
# 最近一次运行成功时间: 2026-03-15 23:49:01 +0800
# 功能说明: 验证顶层导出的枚举对象与定义模块一致。
# 使用示例: pytest -q test/symbol_variable/test_package_api.py -k test_package_exports_identity
# 对应功能实现文件路径: symbol_variable/__init__.py
# 对应 spec 文件路径: spec/symbol_variable/package_api.md
# 对应测试文件路径: test/symbol_variable/test_package_api.py
def test_package_exports_identity() -> None:
    from symbol_variable import Farmat as TopFarmat
    from symbol_variable import NumericType as TopNumericType
    from symbol_variable.type import Farmat as ModuleFarmat
    from symbol_variable.type import NumericType as ModuleNumericType

    assert TopNumericType is ModuleNumericType
    assert TopFarmat is ModuleFarmat


# PA-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-15 23:49:01 +0800
# 最近一次运行成功时间: 2026-03-15 23:49:01 +0800
# 功能说明: 验证旧路径导入继续可用。
# 使用示例: pytest -q test/symbol_variable/test_package_api.py -k test_package_old_path
# 对应功能实现文件路径: symbol_variable/__init__.py
# 对应 spec 文件路径: spec/symbol_variable/package_api.md
# 对应测试文件路径: test/symbol_variable/test_package_api.py
def test_package_old_path() -> None:
    from symbol_variable.type import Farmat, NumericType

    assert NumericType.Float32.value == "float32"
    assert Farmat.Norm.value == "NCHW"


# PA-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-15 23:49:01 +0800
# 最近一次运行成功时间: 2026-03-15 23:49:01 +0800
# 功能说明: 验证顶层导入后构造 Memory。
# 使用示例: pytest -q test/symbol_variable/test_package_api.py -k test_package_memory_construct
# 对应功能实现文件路径: symbol_variable/__init__.py
# 对应 spec 文件路径: spec/symbol_variable/package_api.md
# 对应测试文件路径: test/symbol_variable/test_package_api.py
def test_package_memory_construct() -> None:
    from symbol_variable import Farmat, Memory, MemorySpace, NumericType

    mem = Memory([1, 2], NumericType.Float32, space=MemorySpace.GM, format=Farmat.Norm)
    assert mem.space is MemorySpace.GM
    assert mem.dtype is NumericType.Float32
    assert mem.format is Farmat.Norm
