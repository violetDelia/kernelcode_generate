"""Legacy nn_to_kernel compatibility entry.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 兼容历史导入路径 `kernel_gen.passes.lowing.nn_to_kernel`。
- 将旧路径访问统一转发到 `kernel_gen.passes.lowering.nn_to_kernel`。

使用示例:
- from kernel_gen.passes.lowing.nn_to_kernel import LowerNnToKernelPass
- module = LowerNnToKernelPass().run(module)

关联文件:
- spec: spec/pass/lowering/nn_to_kernel.md
- test: test/pass/test_lowering_nn_to_kernel.py
- 功能实现: kernel_gen/passes/lowing/nn_to_kernel.py
"""

from ..lowering.nn_to_kernel import LowerNnToKernelError, LowerNnToKernelPass

__all__ = ["LowerNnToKernelPass", "LowerNnToKernelError"]
