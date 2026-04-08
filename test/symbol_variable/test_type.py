"""type module tests.

创建者: 金铲铲大作战
最后一次更改: 小李飞刀

功能说明:
- 覆盖 kernel_gen.symbol_variable.type 的枚举语义、导出边界与旧路径禁用约束。

使用示例:
- pytest -q test/symbol_variable/test_type.py

覆盖率信息:
- 当前覆盖率: `100%`（`kernel_gen.symbol_variable.type`，2026-04-09 +0800）
- 达标判定: 已达到 `95%` 覆盖率达标线。

覆盖率命令:
- `pytest -q --cov=kernel_gen.symbol_variable.type --cov-report=term-missing --cov-fail-under=95 test/symbol_variable/test_type.py`

关联文件:
- 功能实现: kernel_gen/symbol_variable/type.py
- Spec 文档: spec/symbol_variable/type.md
- 测试文件: test/symbol_variable/test_type.py
"""

from __future__ import annotations

import pytest


# TY-001
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:28:43 +0800
# 最近一次运行成功时间: 2026-03-22 14:28:43 +0800
# 测试目的: 验证 NumericType 枚举名称和值保持稳定。
# 使用示例: pytest -q test/symbol_variable/test_type.py -k test_numeric_type_values
# 对应功能实现文件路径: kernel_gen/symbol_variable/type.py
# 对应 spec 文件路径: spec/symbol_variable/type.md
# 对应测试文件路径: test/symbol_variable/test_type.py
def test_numeric_type_values() -> None:
    from kernel_gen.symbol_variable.type import NumericType

    assert NumericType.Int8.value == "int8"
    assert NumericType.Int16.value == "int16"
    assert NumericType.Uint8.value == "uint8"
    assert NumericType.Uint16.value == "uint16"
    assert NumericType.Uint32.value == "uint32"
    assert NumericType.Uint64.value == "uint64"
    assert NumericType.Float16.value == "float16"
    assert NumericType.BFloat16.value == "bf16"
    assert NumericType.Int32.value == "int32"
    assert NumericType.Int64.value == "int64"
    assert NumericType.Float32.value == "float32"
    assert NumericType.Float64.value == "float64"


# TY-005
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:28:43 +0800
# 最近一次运行成功时间: 2026-03-22 14:28:43 +0800
# 测试目的: 验证新增基础类型成员可直接访问。
# 使用示例: pytest -q test/symbol_variable/test_type.py -k test_numeric_type_member_access
# 对应功能实现文件路径: kernel_gen/symbol_variable/type.py
# 对应 spec 文件路径: spec/symbol_variable/type.md
# 对应测试文件路径: test/symbol_variable/test_type.py
def test_numeric_type_member_access() -> None:
    from kernel_gen.symbol_variable.type import NumericType

    assert NumericType.Int8.name == "Int8"
    assert NumericType.Int16.name == "Int16"
    assert NumericType.Uint8.name == "Uint8"
    assert NumericType.Uint16.name == "Uint16"
    assert NumericType.Uint32.name == "Uint32"
    assert NumericType.Uint64.name == "Uint64"
    assert NumericType.Float16.name == "Float16"
    assert NumericType.BFloat16.name == "BFloat16"
    assert NumericType.Int32.name == "Int32"
    assert NumericType.Int64.name == "Int64"
    assert NumericType.Float32.name == "Float32"
    assert NumericType.Float64.name == "Float64"


# TY-002
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:28:43 +0800
# 最近一次运行成功时间: 2026-03-22 14:28:43 +0800
# 测试目的: 验证 Farmat 仅公开 Norm/CLast 成员。
# 使用示例: pytest -q test/symbol_variable/test_type.py -k test_farmat_public_members
# 对应功能实现文件路径: kernel_gen/symbol_variable/type.py
# 对应 spec 文件路径: spec/symbol_variable/type.md
# 对应测试文件路径: test/symbol_variable/test_type.py
def test_farmat_public_members() -> None:
    from kernel_gen.symbol_variable.type import Farmat

    assert [member.name for member in Farmat] == ["Norm", "CLast"]
    assert Farmat.Norm.name == "Norm"
    assert Farmat.CLast.name == "CLast"
    assert not hasattr(Farmat, "NHWC")
    assert not hasattr(Farmat, "NCHW")


# TY-003
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:28:43 +0800
# 最近一次运行成功时间: 2026-03-22 14:28:43 +0800
# 测试目的: 验证 kernel_gen.symbol_variable.type 仅公开 NumericType 与 Farmat。
# 使用示例: pytest -q test/symbol_variable/test_type.py -k test_python_type_module_all_boundary
# 对应功能实现文件路径: kernel_gen/symbol_variable/type.py
# 对应 spec 文件路径: spec/symbol_variable/type.md
# 对应测试文件路径: test/symbol_variable/test_type.py
def test_python_type_module_all_boundary() -> None:
    import kernel_gen.symbol_variable.type as type_module

    assert type_module.__all__ == ["NumericType", "Farmat"]


# TY-004
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:28:43 +0800
# 最近一次运行成功时间: 2026-03-22 14:28:43 +0800
# 测试目的: 验证 import * 仅暴露 type 模块约定的公开符号。
# 使用示例: pytest -q test/symbol_variable/test_type.py -k test_python_type_import_star_exports_only_public_names
# 对应功能实现文件路径: kernel_gen/symbol_variable/type.py
# 对应 spec 文件路径: spec/symbol_variable/type.md
# 对应测试文件路径: test/symbol_variable/test_type.py
def test_python_type_import_star_exports_only_public_names() -> None:
    namespace: dict[str, object] = {}

    exec("from kernel_gen.symbol_variable.type import *", {}, namespace)

    assert sorted(namespace) == ["Farmat", "NumericType"]


# TY-006
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 14:28:43 +0800
# 最近一次运行成功时间: 2026-03-22 14:28:43 +0800
# 测试目的: 验证旧路径 symbol_variable.type 不可导入。
# 使用示例: pytest -q test/symbol_variable/test_type.py -k test_legacy_type_import_disabled
# 对应功能实现文件路径: kernel_gen/symbol_variable/type.py
# 对应 spec 文件路径: spec/symbol_variable/type.md
# 对应测试文件路径: test/symbol_variable/test_type.py
def test_legacy_type_import_disabled() -> None:
    import importlib

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("symbol_variable.type")
