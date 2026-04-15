"""outline-device-kernel pass tests.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 `OutlineDeviceKernelPass` 当前 S2 骨架阶段的公开合同。
- 锁定 pass 名称、非 `ModuleOp` 输入的稳定错误短语，以及空模块无副作用返回行为。

使用示例:
- pytest -q test/pass/test_outline_device_kernel.py -k 'registry or non_module or empty_module'

关联文件:
- spec: [spec/pass/lowering/outline_device_kernel.md](spec/pass/lowering/outline_device_kernel.md)
- test: [test/pass/test_outline_device_kernel.py](test/pass/test_outline_device_kernel.py)
- 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](kernel_gen/passes/lowering/outline_device_kernel.py)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.dialects.builtin import ModuleOp

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.passes.lowering.outline_device_kernel import (
    OutlineDeviceKernelError,
    OutlineDeviceKernelPass,
)


# TC-ODK-001
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 锁定公开 pass 名称，供 registry 与 standalone 构造共同复用。
# 使用示例: pytest -q test/pass/test_outline_device_kernel.py -k test_outline_device_kernel_pass_registry_name
# 对应功能实现文件路径: kernel_gen/passes/lowering/outline_device_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/outline_device_kernel.md
# 对应测试文件路径: test/pass/test_outline_device_kernel.py
def test_outline_device_kernel_pass_registry_name() -> None:
    assert OutlineDeviceKernelPass.name == "outline-device-kernel"


# TC-ODK-002
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 锁定非 builtin.module 输入时报稳定错误类型与短语。
# 使用示例: pytest -q test/pass/test_outline_device_kernel.py -k test_outline_device_kernel_non_module_input_raises_stable_error
# 对应功能实现文件路径: kernel_gen/passes/lowering/outline_device_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/outline_device_kernel.md
# 对应测试文件路径: test/pass/test_outline_device_kernel.py
def test_outline_device_kernel_non_module_input_raises_stable_error() -> None:
    with pytest.raises(
        OutlineDeviceKernelError,
        match=r"^OutlineDeviceKernelError: module must be builtin\.module$",
    ):
        OutlineDeviceKernelPass().run(object())


# TC-ODK-003
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 锁定空 module 直接返回同一对象，不在 S2 引入额外改写副作用。
# 使用示例: pytest -q test/pass/test_outline_device_kernel.py -k test_outline_device_kernel_empty_module_returns_same_object
# 对应功能实现文件路径: kernel_gen/passes/lowering/outline_device_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/outline_device_kernel.md
# 对应测试文件路径: test/pass/test_outline_device_kernel.py
def test_outline_device_kernel_empty_module_returns_same_object() -> None:
    module = ModuleOp([])

    result = OutlineDeviceKernelPass().run(module)

    assert result is module
    assert list(module.ops) == []
