"""Legacy compatibility shim for `kernel_gen.passes.lowing.nn_to_kernel`.

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 兼容旧导入路径 `kernel_gen.passes.lowing.nn_to_kernel`。
- 统一复用正式实现 `kernel_gen.passes.lowering.nn_to_kernel`，避免双份逻辑漂移。

使用示例:
- from kernel_gen.passes.lowing.nn_to_kernel import LowerNnToKernelPass
- module = LowerNnToKernelPass().run(module)

关联文件:
- spec: spec/pass/lowering/nn_to_kernel.md
- test: test/pass/test_lowering_nn_to_kernel.py
- 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
"""

from ..lowering.nn_to_kernel import LowerNnToKernelError, LowerNnToKernelPass

__all__ = ["LowerNnToKernelPass", "LowerNnToKernelError"]
