"""outline-device-kernel lowering pass.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 提供 `outline-device-kernel` pass 的公开骨架实现。
- 当前阶段仅锁定公开名称、输入边界与稳定错误类型，为后续 outline 逻辑预留入口。
- 对非 `builtin.module` 输入显式报稳定错误；空模块保持原样返回。

使用示例:
- from xdsl.dialects.builtin import ModuleOp
- from kernel_gen.passes.lowering.outline_device_kernel import OutlineDeviceKernelPass
- module = ModuleOp([])
- assert OutlineDeviceKernelPass().run(module) is module

关联文件:
- spec: [spec/pass/lowering/outline_device_kernel.md](spec/pass/lowering/outline_device_kernel.md)
- test: [test/pass/test_outline_device_kernel.py](test/pass/test_outline_device_kernel.py)
- 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](kernel_gen/passes/lowering/outline_device_kernel.py)
"""

from __future__ import annotations

from xdsl.dialects.builtin import ModuleOp

from kernel_gen.passes.pass_manager import Pass


class OutlineDeviceKernelError(ValueError):
    """outline-device-kernel pass 的稳定错误类型。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 统一承载当前骨架阶段的显式失败路径。
    - 保持错误前缀稳定，便于测试与后续 expectation 做机械匹配。

    使用示例:
    - raise OutlineDeviceKernelError("OutlineDeviceKernelError: module must be builtin.module")

    关联文件:
    - spec: [spec/pass/lowering/outline_device_kernel.md](spec/pass/lowering/outline_device_kernel.md)
    - test: [test/pass/test_outline_device_kernel.py](test/pass/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](kernel_gen/passes/lowering/outline_device_kernel.py)
    """


class OutlineDeviceKernelPass(Pass):
    """outline-device-kernel pass 骨架。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 固定公开名称为 `outline-device-kernel`。
    - 当前只校验输入必须为 `ModuleOp`，并在空模块时保持无副作用返回。

    使用示例:
    - module = OutlineDeviceKernelPass().run(ModuleOp([]))

    关联文件:
    - spec: [spec/pass/lowering/outline_device_kernel.md](spec/pass/lowering/outline_device_kernel.md)
    - test: [test/pass/test_outline_device_kernel.py](test/pass/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](kernel_gen/passes/lowering/outline_device_kernel.py)
    """

    name = "outline-device-kernel"

    def run(self: "OutlineDeviceKernelPass", module: object) -> ModuleOp:
        """执行 outline-device-kernel 骨架 pass。

        创建者: 朽木露琪亚
        最后一次更改: 朽木露琪亚

        功能说明:
        - 仅接受 `builtin.module` 作为 pass 输入。
        - 空模块直接返回，为 S3 真实改写逻辑预留稳定入口。

        使用示例:
        - module = ModuleOp([])
        - same_module = OutlineDeviceKernelPass().run(module)

        关联文件:
        - spec: [spec/pass/lowering/outline_device_kernel.md](spec/pass/lowering/outline_device_kernel.md)
        - test: [test/pass/test_outline_device_kernel.py](test/pass/test_outline_device_kernel.py)
        - 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](kernel_gen/passes/lowering/outline_device_kernel.py)
        """

        if not isinstance(module, ModuleOp):
            raise OutlineDeviceKernelError("OutlineDeviceKernelError: module must be builtin.module")
        if not any(True for _ in module.ops):
            return module
        return module


__all__ = ["OutlineDeviceKernelError", "OutlineDeviceKernelPass"]
