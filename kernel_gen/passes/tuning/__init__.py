"""tuning pass package.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 提供 tuning 目录下 pass 的公开导出入口。
- 当前包含 `launch-kernel-cost-func` standalone pass。

使用示例:
- from kernel_gen.passes.tuning import LaunchKernelCostFuncPass
- pass_obj = LaunchKernelCostFuncPass(kind="all")

关联文件:
- spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
- test: [test/pass/test_launch_kernel_cost_func.py](test/pass/test_launch_kernel_cost_func.py)
- 功能实现:
  - [kernel_gen/passes/tuning/__init__.py](kernel_gen/passes/tuning/__init__.py)
  - [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
"""

from .launch_kernel_cost_func import LaunchKernelCostFuncError, LaunchKernelCostFuncPass

__all__ = ["LaunchKernelCostFuncError", "LaunchKernelCostFuncPass"]
