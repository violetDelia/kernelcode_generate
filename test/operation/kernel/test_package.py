"""kernel operation package tests.


功能说明:
- 覆盖 `kernel_gen.operation.kernel` 子模块公开导出。
- 验证 package-root 只公开 `kernel` 子模块，不上提 helper。

使用示例:
- pytest -q test/operation/kernel/test_package.py

关联文件:
- 功能实现: kernel_gen/operation/kernel/__init__.py
- 功能实现: kernel_gen/operation/__init__.py
- Spec 文档: spec/operation/kernel.md
- 测试文件: test/operation/kernel/test_package.py
"""

from __future__ import annotations

import kernel_gen.operation as operation
from kernel_gen.operation import kernel


PUBLIC_KERNEL_EXPORTS = (
    "KernelBinaryElewiseKind",
    "binary_elewise",
    "add",
    "sub",
    "mul",
    "div",
    "truediv",
    "eq",
    "ne",
    "lt",
    "le",
    "gt",
    "ge",
    "exp",
    "KernelReduceKind",
    "reduce",
    "matmul",
    "img2col1d",
    "img2col2d",
)


# TC-OP-KERNEL-PKG-001
# 功能说明: 验证 kernel 子模块公开对象可达。
# 测试目的: 锁定 spec/operation/kernel.md 的 API 列表与模块导出一致。
# 使用示例: pytest -q test/operation/kernel/test_package.py -k public_exports
# 对应功能实现文件路径: kernel_gen/operation/kernel/__init__.py
# 对应 spec 文件路径: spec/operation/kernel.md
# 对应测试文件路径: test/operation/kernel/test_package.py
def test_kernel_submodule_public_exports_match_spec() -> None:
    for name in PUBLIC_KERNEL_EXPORTS:
        assert hasattr(kernel, name)


# TC-OP-KERNEL-PKG-002
# 功能说明: 验证 package-root 导出边界。
# 测试目的: `kernel` 子模块可从包根导入，但 out-first helper 不上提避免与 nn helper 冲突。
# 使用示例: pytest -q test/operation/kernel/test_package.py -k package_root
# 对应功能实现文件路径: kernel_gen/operation/__init__.py
# 对应 spec 文件路径: spec/operation/kernel.md
# 对应测试文件路径: test/operation/kernel/test_package.py
def test_operation_package_exports_kernel_submodule_only() -> None:
    assert operation.kernel is kernel
    assert operation.add is not kernel.add
    assert operation.matmul is not kernel.matmul
