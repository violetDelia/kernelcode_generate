"""type module tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 python.symbol_variable.type 的枚举语义、导出边界与旧路径禁用约束。

使用示例:
- pytest -q test/symbol_variable/test_type.py

关联文件:
- 功能实现: python/symbol_variable/type.py
- Spec 文档: spec/symbol_variable/type.md
- 测试文件: test/symbol_variable/test_type.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# TY-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 20:40:27 +0800
# 最近一次运行成功时间: 2026-03-16 20:40:27 +0800
# 功能说明: 验证 NumericType 枚举名称和值保持稳定。
# 使用示例: pytest -q test/symbol_variable/test_type.py -k test_numeric_type_values
# 对应功能实现文件路径: python/symbol_variable/type.py
# 对应 spec 文件路径: spec/symbol_variable/type.md
# 对应测试文件路径: test/symbol_variable/test_type.py
def test_numeric_type_values() -> None:
    from python.symbol_variable.type import NumericType

    assert NumericType.Int32.value == "int32"
    assert NumericType.Float32.value == "float32"


# TY-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 20:40:27 +0800
# 最近一次运行成功时间: 2026-03-16 20:40:27 +0800
# 功能说明: 验证 Farmat 别名与名称行为稳定。
# 使用示例: pytest -q test/symbol_variable/test_type.py -k test_farmat_aliases
# 对应功能实现文件路径: python/symbol_variable/type.py
# 对应 spec 文件路径: spec/symbol_variable/type.md
# 对应测试文件路径: test/symbol_variable/test_type.py
def test_farmat_aliases() -> None:
    from python.symbol_variable.type import Farmat

    assert Farmat.Norm is Farmat.NCHW
    assert Farmat.CLast is Farmat.NHWC
    assert Farmat.Norm.name == "NCHW"
    assert Farmat.CLast.name == "NHWC"
    assert repr(Farmat.Norm) == "<Farmat.NCHW: 'NCHW'>"
    assert repr(Farmat.CLast) == "<Farmat.NHWC: 'NHWC'>"


# TY-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 20:40:27 +0800
# 最近一次运行成功时间: 2026-03-16 20:40:27 +0800
# 功能说明: 验证 python.symbol_variable.type 仅公开 NumericType 与 Farmat。
# 使用示例: pytest -q test/symbol_variable/test_type.py -k test_python_type_module_all_boundary
# 对应功能实现文件路径: python/symbol_variable/type.py
# 对应 spec 文件路径: spec/symbol_variable/type.md
# 对应测试文件路径: test/symbol_variable/test_type.py
def test_python_type_module_all_boundary() -> None:
    import python.symbol_variable.type as type_module

    assert type_module.__all__ == ["NumericType", "Farmat"]


# TY-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 20:40:27 +0800
# 最近一次运行成功时间: 2026-03-16 20:40:27 +0800
# 功能说明: 验证 import * 仅暴露 type 模块约定的公开符号。
# 使用示例: pytest -q test/symbol_variable/test_type.py -k test_python_type_import_star_exports_only_public_names
# 对应功能实现文件路径: python/symbol_variable/type.py
# 对应 spec 文件路径: spec/symbol_variable/type.md
# 对应测试文件路径: test/symbol_variable/test_type.py
def test_python_type_import_star_exports_only_public_names() -> None:
    namespace: dict[str, object] = {}

    exec("from python.symbol_variable.type import *", {}, namespace)

    assert sorted(namespace) == ["Farmat", "NumericType"]


# TY-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-16 20:40:27 +0800
# 最近一次运行成功时间: 2026-03-16 20:40:27 +0800
# 功能说明: 验证旧路径 symbol_variable.type 不可导入。
# 使用示例: pytest -q test/symbol_variable/test_type.py -k test_legacy_type_import_disabled
# 对应功能实现文件路径: python/symbol_variable/type.py
# 对应 spec 文件路径: spec/symbol_variable/type.md
# 对应测试文件路径: test/symbol_variable/test_type.py
def test_legacy_type_import_disabled() -> None:
    import importlib

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("symbol_variable.type")
