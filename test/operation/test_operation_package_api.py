"""operation package API tests.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

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

NN_TOP_LEVEL_EXPORTS = (
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
)

DMA_TOP_LEVEL_EXPORTS = (
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
)

SCF_TOP_LEVEL_EXPORTS = ("loop",)

STABLE_TOP_LEVEL_EXPORTS = (
    NN_TOP_LEVEL_EXPORTS
    + DMA_TOP_LEVEL_EXPORTS
    + SCF_TOP_LEVEL_EXPORTS
)


# TC-OP-PKG-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-16 09:05:00 +0800
# 最近一次运行成功时间: 2026-04-16 09:05:00 +0800
# 测试目的: 验证 spec 已定义的 kernel_gen.operation 顶层公开对象可直接从 package-root 获取。
# 使用示例: pytest -q test/operation/test_operation_package_api.py -k test_operation_top_level_public_exports_match_spec
# 对应功能实现文件路径: kernel_gen/operation/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md, spec/operation/dma.md, spec/operation/scf.md
# 对应测试文件路径: test/operation/test_operation_package_api.py
def test_operation_top_level_public_exports_match_spec() -> None:
    for name in STABLE_TOP_LEVEL_EXPORTS:
        assert hasattr(operation, name)


# TC-OP-PKG-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-16 09:05:00 +0800
# 最近一次运行成功时间: 2026-04-16 09:05:00 +0800
# 测试目的: 验证显式公开导入只引入 spec 已定义的顶层公开对象，不依赖模块元数据。
# 使用示例: pytest -q test/operation/test_operation_package_api.py -k test_operation_explicit_import_exposes_only_public_exports
# 对应功能实现文件路径: kernel_gen/operation/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md, spec/operation/dma.md, spec/operation/scf.md
# 对应测试文件路径: test/operation/test_operation_package_api.py
def test_operation_explicit_import_exposes_only_public_exports() -> None:
    namespace: dict[str, object] = {}

    exec(
        f"from kernel_gen.operation import {', '.join(STABLE_TOP_LEVEL_EXPORTS)}",
        namespace,
    )

    imported_names = {name for name in namespace if name != "__builtins__"}

    assert imported_names == set(STABLE_TOP_LEVEL_EXPORTS)
    for name in STABLE_TOP_LEVEL_EXPORTS:
        assert namespace[name] is getattr(operation, name)


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
        "fill",
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


# TC-OP-PKG-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 测试目的: 验证 `fill` 只在 `kernel_gen.operation.dma` 子模块公开，不上提到 package-root。
# 使用示例: pytest -q test/operation/test_operation_package_api.py -k test_operation_dma_fill_is_public_only_in_dma_submodule
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_package_api.py
def test_operation_dma_fill_is_public_only_in_dma_submodule() -> None:
    assert hasattr(operation_dma, "fill")
    assert not hasattr(operation, "fill")


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
    for name in NN_TOP_LEVEL_EXPORTS:
        assert getattr(operation, name) is getattr(operation_nn, name)
    for name in DMA_TOP_LEVEL_EXPORTS:
        assert getattr(operation, name) is getattr(operation_dma, name)
    for name in SCF_TOP_LEVEL_EXPORTS:
        assert getattr(operation, name) is getattr(operation_scf, name)
