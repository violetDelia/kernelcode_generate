"""type module tests.


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

import sys
from pathlib import Path

import pytest


# TY-001
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
# 测试目的: 验证 `kernel_gen.symbol_variable.type` 模块的公开 API 可达，且测试边界不依赖 `__all__` 元数据。
# 使用示例: pytest -q test/symbol_variable/test_type.py -k test_python_type_module_public_api_boundary
# 对应功能实现文件路径: kernel_gen/symbol_variable/type.py
# 对应 spec 文件路径: spec/symbol_variable/type.md
# 对应测试文件路径: test/symbol_variable/test_type.py
def test_python_type_module_public_api_boundary() -> None:
    import kernel_gen.symbol_variable.type as type_module

    assert hasattr(type_module, "NumericType")
    assert hasattr(type_module, "Farmat")
    assert hasattr(type_module, "FLOAT_DTYPES")
    assert hasattr(type_module, "INT_DTYPES")
    assert hasattr(type_module, "ARITHMETIC_DTYPE_ORDER")
    assert hasattr(type_module, "ARITHMETIC_DTYPE_RANK")
    assert hasattr(type_module, "NN_FLOAT_DTYPES")
    assert hasattr(type_module, "is_integer_dtype")
    assert hasattr(type_module, "is_float_dtype")
    assert not hasattr(type_module, "Memory")
    assert not hasattr(type_module, "MemorySpace")


# TY-004
# 测试目的: 验证 import * 仅暴露 type 模块约定的公开符号。
# 使用示例: pytest -q test/symbol_variable/test_type.py -k test_python_type_import_star_exports_only_public_names
# 对应功能实现文件路径: kernel_gen/symbol_variable/type.py
# 对应 spec 文件路径: spec/symbol_variable/type.md
# 对应测试文件路径: test/symbol_variable/test_type.py
def test_python_type_import_star_exports_only_public_names() -> None:
    namespace: dict[str, object] = {}

    exec("from kernel_gen.symbol_variable.type import *", {}, namespace)

    assert sorted(namespace) == [
        "ARITHMETIC_DTYPE_ORDER",
        "ARITHMETIC_DTYPE_RANK",
        "FLOAT_DTYPES",
        "Farmat",
        "INT_DTYPES",
        "NN_FLOAT_DTYPES",
        "NumericType",
        "is_float_dtype",
        "is_integer_dtype",
    ]


# TY-004A
# 测试目的: 验证 `FLOAT_DTYPES` / `INT_DTYPES` 成为 type.py 的公开 dtype family 真源。
# 使用示例: pytest -q test/symbol_variable/test_type.py -k test_python_type_public_dtype_family_constants
# 对应功能实现文件路径: kernel_gen/symbol_variable/type.py
# 对应 spec 文件路径: spec/symbol_variable/type.md
# 对应测试文件路径: test/symbol_variable/test_type.py
def test_python_type_public_dtype_family_constants() -> None:
    from kernel_gen.symbol_variable.type import FLOAT_DTYPES, INT_DTYPES, NN_FLOAT_DTYPES, NumericType

    assert FLOAT_DTYPES == {
        NumericType.Float16,
        NumericType.BFloat16,
        NumericType.Float32,
        NumericType.Float64,
    }
    assert INT_DTYPES == {
        NumericType.Int8,
        NumericType.Int16,
        NumericType.Int32,
        NumericType.Int64,
        NumericType.Uint8,
        NumericType.Uint16,
        NumericType.Uint32,
        NumericType.Uint64,
    }
    assert NumericType.Bool not in FLOAT_DTYPES
    assert NumericType.Bool not in INT_DTYPES
    assert NN_FLOAT_DTYPES is FLOAT_DTYPES


# TY-004B
# 测试目的: 验证 arithmetic dtype promotion 常量已整合到 type.py 真源。
# 使用示例: pytest -q test/symbol_variable/test_type.py -k test_python_type_public_arithmetic_dtype_order_and_rank
# 对应功能实现文件路径: kernel_gen/symbol_variable/type.py
# 对应 spec 文件路径: spec/symbol_variable/type.md
# 对应测试文件路径: test/symbol_variable/test_type.py
def test_python_type_public_arithmetic_dtype_order_and_rank() -> None:
    from kernel_gen.symbol_variable.type import ARITHMETIC_DTYPE_ORDER, ARITHMETIC_DTYPE_RANK, NumericType

    expected_order = (
        NumericType.Int8,
        NumericType.Uint8,
        NumericType.Int16,
        NumericType.Uint16,
        NumericType.Int32,
        NumericType.Uint32,
        NumericType.Int64,
        NumericType.Uint64,
        NumericType.Float16,
        NumericType.BFloat16,
        NumericType.Float32,
        NumericType.Float64,
    )
    assert ARITHMETIC_DTYPE_ORDER == expected_order
    assert ARITHMETIC_DTYPE_RANK == {dtype: index for index, dtype in enumerate(expected_order)}


# TY-006
# 测试目的: 验证旧路径 symbol_variable.type 不可导入。
# 使用示例: pytest -q test/symbol_variable/test_type.py -k test_legacy_type_import_disabled
# 对应功能实现文件路径: kernel_gen/symbol_variable/type.py
# 对应 spec 文件路径: spec/symbol_variable/type.md
# 对应测试文件路径: test/symbol_variable/test_type.py
def test_legacy_type_import_disabled() -> None:
    import importlib

    test_dir = str(Path(__file__).resolve().parents[1])
    original_sys_path = sys.path[:]
    # 清理可能由前序测试残留的旧别名缓存，确保此处验证的是当前 legacy 导入边界。
    legacy_modules = [
        "symbol_variable",
        "symbol_variable.type",
    ]
    try:
        sys.path = [path for path in sys.path if path != test_dir]
        for module_name in legacy_modules:
            sys.modules.pop(module_name, None)

        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("symbol_variable.type")
    finally:
        sys.path[:] = original_sys_path


# TY-008
# 测试目的: 验证 `is_integer_dtype(...)` 仅把公开整数成员判为 True。
# 使用示例: pytest -q test/symbol_variable/test_type.py -k test_is_integer_dtype_public_family
# 对应功能实现文件路径: kernel_gen/symbol_variable/type.py
# 对应 spec 文件路径: spec/symbol_variable/type.md
# 对应测试文件路径: test/symbol_variable/test_type.py
def test_is_integer_dtype_public_family() -> None:
    from kernel_gen.symbol_variable.type import NumericType, is_integer_dtype

    assert is_integer_dtype(NumericType.Int32) is True
    assert is_integer_dtype(NumericType.Uint64) is True
    assert is_integer_dtype(NumericType.Bool) is False
    assert is_integer_dtype(NumericType.Float32) is False


# TY-009
# 测试目的: 验证 `is_float_dtype(...)` 仅把公开浮点成员判为 True。
# 使用示例: pytest -q test/symbol_variable/test_type.py -k test_is_float_dtype_public_family
# 对应功能实现文件路径: kernel_gen/symbol_variable/type.py
# 对应 spec 文件路径: spec/symbol_variable/type.md
# 对应测试文件路径: test/symbol_variable/test_type.py
def test_is_float_dtype_public_family() -> None:
    from kernel_gen.symbol_variable.type import NumericType, is_float_dtype

    assert is_float_dtype(NumericType.Float16) is True
    assert is_float_dtype(NumericType.BFloat16) is True
    assert is_float_dtype(NumericType.Int32) is False
    assert is_float_dtype(NumericType.Bool) is False


# TY-010
# 测试目的: 验证 dtype family helper 拒绝非 `NumericType` 输入。
# 使用示例: pytest -q test/symbol_variable/test_type.py -k test_dtype_family_helpers_reject_non_numeric_type
# 对应功能实现文件路径: kernel_gen/symbol_variable/type.py
# 对应 spec 文件路径: spec/symbol_variable/type.md
# 对应测试文件路径: test/symbol_variable/test_type.py
def test_dtype_family_helpers_reject_non_numeric_type() -> None:
    from kernel_gen.symbol_variable.type import is_float_dtype, is_integer_dtype

    with pytest.raises(TypeError, match=r"^dtype must be NumericType$"):
        is_integer_dtype("int32")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^dtype must be NumericType$"):
        is_float_dtype(object())  # type: ignore[arg-type]
