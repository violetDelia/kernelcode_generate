"""Legacy lowing pass package compatibility layer.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 为仍引用 `kernel_gen.passes.lowing` 的旧脚本提供向后兼容导入入口。
- 统一转发到当前生效实现 `kernel_gen.passes.lowering`，不改变 pass 语义。

使用示例:
- from kernel_gen.passes.lowing.nn_to_kernel import LowerNnToKernelPass
- pass_obj = LowerNnToKernelPass()

关联文件:
- spec: spec/pass/lowering/nn_to_kernel.md
- test: test/pass/test_lowering_nn_to_kernel.py
- 功能实现: kernel_gen/passes/lowing/__init__.py
"""

from ..lowering.nn_to_kernel import LowerNnToKernelError, LowerNnToKernelPass

__all__ = ["LowerNnToKernelPass", "LowerNnToKernelError"]
