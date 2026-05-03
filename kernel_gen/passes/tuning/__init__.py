"""tuning pass package.


功能说明:
- 提供 tuning 目录下 pass 的公开导出入口。
- 当前包含 `launch-kernel-cost-func` pass，可 standalone 使用，也可由 `npu-demo-lowering` pipeline 复用。

API 列表:
- `LaunchKernelCostFuncPass`

使用示例:
- from kernel_gen.passes.tuning import LaunchKernelCostFuncPass
- pass_obj = LaunchKernelCostFuncPass()
- pass_obj = LaunchKernelCostFuncPass(cost_kind="compute|memory")

关联文件:
- spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
- test: [test/passes/tuning/test_launch_kernel_cost_func.py](test/passes/tuning/test_launch_kernel_cost_func.py)
- 功能实现:
  - [kernel_gen/passes/tuning/__init__.py](kernel_gen/passes/tuning/__init__.py)
  - [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
"""

from .launch_kernel_cost_func import LaunchKernelCostFuncPass

__all__ = ["LaunchKernelCostFuncPass"]
