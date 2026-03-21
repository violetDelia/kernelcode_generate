"""lowering pass package.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 提供 nn -> kernel lowering pass 的公开入口。

使用示例:
- from kernel_gen.pass.lowing.nn_to_kernel import LowerNnToKernelPass
- pass_obj = LowerNnToKernelPass()

关联文件:
- spec: spec/pass/lowing/nn_to_kernel.md
- test: test/pass/test_lowing_nn_to_kernel.py
- 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
"""

from .nn_to_kernel import LowerNnToKernelPass, LowerNnToKernelError

__all__ = ["LowerNnToKernelPass", "LowerNnToKernelError"]
