"""operation package api tests.

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 覆盖 `kernel_gen.operation` 包入口导出边界、对象一致性与 `import *` 行为。

使用示例:
- pytest -q test/operation/test_operation_package_api.py

当前覆盖率信息:
- 不再要求覆盖率；本文件以包入口导出闭环为准。

覆盖率命令:
- 不再要求覆盖率命令；本文件以包入口导出闭环为准。

关联文件:
- 功能实现: kernel_gen/operation/__init__.py
- Spec 文档: spec/operation/nn.md
- Spec 文档: spec/operation/dma.md
- Spec 文档: spec/operation/scf.md
- 测试文件: test/operation/test_operation_package_api.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import kernel_gen.operation as operation_api
import kernel_gen.operation.dma as operation_dma
import kernel_gen.operation.nn as operation_nn
import kernel_gen.operation.scf as operation_scf


# TC-OP-PKG-001
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-15 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-15 00:00:00 +0800
# 测试目的: 验证 kernel_gen.operation 顶层导入可直接暴露常用 nn/dma/scf API。
# 使用示例: pytest -q test/operation/test_operation_package_api.py -k test_operation_package_top_level_imports
# 对应功能实现文件路径: kernel_gen/operation/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md, spec/operation/dma.md, spec/operation/scf.md
# 对应测试文件路径: test/operation/test_operation_package_api.py
def test_operation_package_top_level_imports() -> None:
    from kernel_gen.operation import add, alloc, loop, matmul

    assert add is not None
    assert alloc is not None
    assert loop is not None
    assert matmul is not None


# TC-OP-PKG-002
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-15 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-15 00:00:00 +0800
# 测试目的: 验证顶层重新导出的对象与对应子模块对象一致。
# 使用示例: pytest -q test/operation/test_operation_package_api.py -k test_operation_package_export_identity
# 对应功能实现文件路径: kernel_gen/operation/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md, spec/operation/dma.md, spec/operation/scf.md
# 对应测试文件路径: test/operation/test_operation_package_api.py
def test_operation_package_export_identity() -> None:
    assert operation_api.add is operation_nn.add
    assert operation_api.matmul is operation_nn.matmul
    assert operation_api.alloc is operation_dma.alloc
    assert operation_api.slice is operation_dma.slice
    assert operation_api.loop is operation_scf.loop


# TC-OP-PKG-003
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-15 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-15 00:00:00 +0800
# 测试目的: 锁定 kernel_gen.operation.__all__ 的公开导出边界。
# 使用示例: pytest -q test/operation/test_operation_package_api.py -k test_operation_package_all_boundary
# 对应功能实现文件路径: kernel_gen/operation/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md, spec/operation/dma.md, spec/operation/scf.md
# 对应测试文件路径: test/operation/test_operation_package_api.py
def test_operation_package_all_boundary() -> None:
    assert operation_api.__all__ == [
        "add",
        "sub",
        "mul",
        "truediv",
        "eq",
        "ne",
        "lt",
        "le",
        "gt",
        "ge",
        "matmul",
        "alloc",
        "free",
        "copy",
        "load",
        "store",
        "slice",
        "deslice",
        "view",
        "reshape",
        "flatten",
        "cast",
        "loop",
    ]


# TC-OP-PKG-004
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-15 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-15 00:00:00 +0800
# 测试目的: 验证 import * 仅暴露包入口约定的公开符号。
# 使用示例: pytest -q test/operation/test_operation_package_api.py -k test_operation_package_import_star_exports_only_public_names
# 对应功能实现文件路径: kernel_gen/operation/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md, spec/operation/dma.md, spec/operation/scf.md
# 对应测试文件路径: test/operation/test_operation_package_api.py
def test_operation_package_import_star_exports_only_public_names() -> None:
    namespace: dict[str, object] = {}

    exec("from kernel_gen.operation import *", {}, namespace)

    assert sorted(namespace) == sorted(operation_api.__all__)


# TC-OP-PKG-005
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-15 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-15 00:00:00 +0800
# 测试目的: 验证顶层导出不混入 arch helper，公开边界仍限定为 nn/dma/scf API。
# 使用示例: pytest -q test/operation/test_operation_package_api.py -k test_operation_package_excludes_arch_helpers
# 对应功能实现文件路径: kernel_gen/operation/__init__.py
# 对应 spec 文件路径: spec/operation/arch.md, spec/operation/nn.md, spec/operation/dma.md, spec/operation/scf.md
# 对应测试文件路径: test/operation/test_operation_package_api.py
def test_operation_package_excludes_arch_helpers() -> None:
    assert "barrier" not in operation_api.__all__
    assert "get_dynamic_memory" not in operation_api.__all__
    assert not hasattr(operation_api, "barrier")
    assert not hasattr(operation_api, "get_dynamic_memory")

    with pytest.raises(ImportError):
        exec("from kernel_gen.operation import barrier", {}, {})
