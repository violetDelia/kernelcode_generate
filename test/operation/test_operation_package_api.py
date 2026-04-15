"""operation package API tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 锁定 `kernel_gen.operation` 顶层稳定导出集合与非导出边界。

使用示例:
- pytest -q test/operation/test_operation_package_api.py

关联文件:
- Spec 文档: spec/operation/nn.md
- Spec 文档: spec/operation/dma.md
- Spec 文档: spec/operation/scf.md
- Spec 文档: spec/operation/arch.md
- 功能实现: kernel_gen/operation/__init__.py
- 测试文件: test/operation/test_operation_package_api.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import kernel_gen.operation as operation
import kernel_gen.operation.dma as operation_dma
import kernel_gen.operation.nn as operation_nn
import kernel_gen.operation.scf as operation_scf


# TC-OP-PKG-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-16 09:05:00 +0800
# 最近一次运行成功时间: 2026-04-16 09:05:00 +0800
# 测试目的: 验证 kernel_gen.operation.__all__ 显式锁定稳定顶层导出集合与顺序。
# 使用示例: pytest -q test/operation/test_operation_package_api.py -k test_operation_top_level_all_matches_stable_exports
# 对应功能实现文件路径: kernel_gen/operation/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_package_api.py
def test_operation_top_level_all_matches_stable_exports() -> None:
    assert operation.__all__ == [
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


# TC-OP-PKG-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-16 09:05:00 +0800
# 最近一次运行成功时间: 2026-04-16 09:05:00 +0800
# 测试目的: 验证星号导入只暴露稳定顶层 API，不泄露额外 helper。
# 使用示例: pytest -q test/operation/test_operation_package_api.py -k test_operation_star_import_exposes_only_stable_exports
# 对应功能实现文件路径: kernel_gen/operation/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/test_operation_package_api.py
def test_operation_star_import_exposes_only_stable_exports() -> None:
    namespace: dict[str, object] = {}

    exec("from kernel_gen.operation import *", namespace)

    imported_names = {name for name in namespace if name != "__builtins__"}

    assert imported_names == set(operation.__all__)
    assert namespace["add"] is operation.add
    assert namespace["alloc"] is operation.alloc
    assert namespace["loop"] is operation.loop


# TC-OP-PKG-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-16 09:05:00 +0800
# 最近一次运行成功时间: 2026-04-16 09:05:00 +0800
# 测试目的: 验证 arch helper 与 nn 扩展 helper 不上提到 kernel_gen.operation 顶层命名空间。
# 使用示例: pytest -q test/operation/test_operation_package_api.py -k test_operation_top_level_namespace_does_not_export_arch_or_extended_nn_helpers
# 对应功能实现文件路径: kernel_gen/operation/__init__.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_package_api.py
def test_operation_top_level_namespace_does_not_export_arch_or_extended_nn_helpers() -> None:
    hidden_names = {
        "barrier",
        "launch_kernel",
        "get_block_id",
        "get_thread_num",
        "broadcast",
        "broadcast_to",
        "relu",
        "softmax",
        "conv",
        "img2col1d",
        "img2col2d",
        "transpose",
    }

    for name in hidden_names:
        assert not hasattr(operation, name)


# TC-OP-PKG-004
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


# TC-OP-PKG-005
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
    assert operation.add is operation_nn.add
    assert operation.matmul is operation_nn.matmul
    assert operation.alloc is operation_dma.alloc
    assert operation.slice is operation_dma.slice
    assert operation.loop is operation_scf.loop
