"""Legacy compatibility package for `kernel_gen.passes.lowing`.

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 为历史拼写 `lowing` 提供兼容导入入口。
- 将旧路径请求转发到当前正式实现 `kernel_gen.passes.lowering`。

使用示例:
- from kernel_gen.passes.lowing.nn_to_kernel import LowerNnToKernelPass
- lowered_module = LowerNnToKernelPass().run(module)

关联文件:
- spec: spec/pass/lowering/nn_to_kernel.md
- test: test/pass/test_lowering_nn_to_kernel.py
- 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
"""

from ..lowering import LowerNnToKernelError, LowerNnToKernelPass

__all__ = ["LowerNnToKernelPass", "LowerNnToKernelError"]
