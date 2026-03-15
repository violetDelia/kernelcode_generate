"""type tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 __all__ 定义与 import * 导出范围。

使用示例:
- pytest -q test/symbol_variable/test_type.py

关联文件:
- 功能实现: symbol_variable/type.py
- Spec 文档: spec/symbol_variable/type.md
- 测试文件: test/symbol_variable/test_type.py
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import symbol_variable.type as type_module
from symbol_variable.type import Farmat, NumericType


# TY-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-15 23:33:44 +0800
# 最近一次运行成功时间: 2026-03-15 23:33:44 +0800
# 功能说明: 验证 __all__ 存在且精确包含 NumericType 与 Farmat。
# 使用示例: pytest -q test/symbol_variable/test_type.py -k test_all_defined
# 对应功能实现文件路径: symbol_variable/type.py
# 对应 spec 文件路径: spec/symbol_variable/type.md
# 对应测试文件路径: test/symbol_variable/test_type.py
def test_all_defined() -> None:
    assert hasattr(type_module, "__all__")
    assert isinstance(type_module.__all__, Iterable)
    assert set(type_module.__all__) == {"NumericType", "Farmat"}


# TY-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-15 23:33:44 +0800
# 最近一次运行成功时间: 2026-03-15 23:33:44 +0800
# 功能说明: 验证 import * 仅导出 __all__ 中列出的符号。
# 使用示例: pytest -q test/symbol_variable/test_type.py -k test_import_star_exports_only_all
# 对应功能实现文件路径: symbol_variable/type.py
# 对应 spec 文件路径: spec/symbol_variable/type.md
# 对应测试文件路径: test/symbol_variable/test_type.py
def test_import_star_exports_only_all() -> None:
    namespace: dict[str, object] = {}
    exec("from symbol_variable.type import *", {}, namespace)
    exported = {name for name in namespace.keys() if name != "__builtins__"}
    assert exported == {"NumericType", "Farmat"}


# TY-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-15 23:33:44 +0800
# 最近一次运行成功时间: 2026-03-15 23:33:44 +0800
# 功能说明: 验证枚举可用性保持不变。
# 使用示例: pytest -q test/symbol_variable/test_type.py -k test_enum_access
# 对应功能实现文件路径: symbol_variable/type.py
# 对应 spec 文件路径: spec/symbol_variable/type.md
# 对应测试文件路径: test/symbol_variable/test_type.py
def test_enum_access() -> None:
    assert NumericType.Float32.value == "float32"
    assert Farmat.Norm is Farmat.NCHW
