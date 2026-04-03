"""lowering pass package.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 提供 nn -> kernel lowering pass 的公开入口。
- 提供 buffer-results-to-out-params pass 的公开入口。

使用示例:
- from kernel_gen.passes.lowering.nn_to_kernel import LowerNnToKernelPass
- pass_obj = LowerNnToKernelPass()
- from kernel_gen.passes.lowering.buffer_results_to_out_params import BufferResultsToOutParamsPass
- pass_obj = BufferResultsToOutParamsPass()

关联文件:
- spec: spec/pass/lowering/nn_to_kernel.md
- test:
  - test/pass/test_lowering_nn_to_kernel.py
  - test/pass/test_buffer_results_to_out_params.py
- 功能实现:
  - kernel_gen/passes/lowering/nn_to_kernel.py
  - kernel_gen/passes/lowering/buffer_results_to_out_params.py
"""

from .buffer_results_to_out_params import (
    BufferResultsToOutParamsError,
    BufferResultsToOutParamsPass,
)
from .nn_to_kernel import LowerNnToKernelPass, LowerNnToKernelError

__all__ = [
    "LowerNnToKernelPass",
    "LowerNnToKernelError",
    "BufferResultsToOutParamsPass",
    "BufferResultsToOutParamsError",
]
