"""outline-device-kernel compatibility module.


功能说明:
- 保留旧公开 import path `kernel_gen.passes.outline_device_kernel`。
- 真实实现已迁移到 `kernel_gen.passes.tuning.outline_device_kernel`。
- 本文件只 re-export 公开 pass、pattern class 与 pattern getter，不承载 pass 业务逻辑。

API 列表:
- `class OutlineDeviceKernelFuncPattern(candidates: dict[str, tuple[int, int, int, int]])`
- `get_outline_device_kernel_pass_patterns(candidates: dict[str, tuple[int, int, int, int]]) -> list[RewritePattern]`
- `class OutlineDeviceKernelPass(fold: bool = True)`
- `OutlineDeviceKernelPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.outline_device_kernel import OutlineDeviceKernelPass
- pass_obj = OutlineDeviceKernelPass()

关联文件:
- spec: spec/pass/tuning/outline_device_kernel.md
- test: test/passes/tuning/test_outline_device_kernel.py
- 功能实现: kernel_gen/passes/tuning/outline_device_kernel.py
"""

from kernel_gen.passes.tuning.outline_device_kernel import (
    OutlineDeviceKernelFuncPattern,
    OutlineDeviceKernelPass,
    get_outline_device_kernel_pass_patterns,
)

__all__ = [
    "OutlineDeviceKernelFuncPattern",
    "OutlineDeviceKernelPass",
    "get_outline_device_kernel_pass_patterns",
]
