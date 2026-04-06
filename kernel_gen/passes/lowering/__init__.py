"""lowering pass package.

创建者: 金铲铲大作战
最后一次更改: jcc你莫辜负

功能说明:
- 提供 nn -> kernel lowering pass 的公开入口。
- 提供 buffer-results-to-out-params pass 的公开入口。
- 提供 lower-dma-memory-hierarchy pass 的公开入口。

使用示例:
- from kernel_gen.passes.lowering.nn_to_kernel import LowerNnToKernelPass
- pass_obj = LowerNnToKernelPass()
- from kernel_gen.passes.lowering.buffer_results_to_out_params import BufferResultsToOutParamsPass
- pass_obj = BufferResultsToOutParamsPass()
- from kernel_gen.passes.lowering.dma_memory_hierarchy import LowerDmaMemoryHierarchyPass
- pass_obj = LowerDmaMemoryHierarchyPass()

关联文件:
- spec:
  - spec/pass/lowering/nn_to_kernel.md
  - spec/pass/lowering/buffer_results_to_out_params.md
  - spec/pass/lowering/dma_memory_hierarchy.md
- test:
  - test/pass/test_lowering_nn_to_kernel.py
  - test/pass/test_buffer_results_to_out_params.py
  - test/pass/test_dma_memory_hierarchy.py
- 功能实现:
  - kernel_gen/passes/lowering/nn_to_kernel.py
  - kernel_gen/passes/lowering/buffer_results_to_out_params.py
  - kernel_gen/passes/lowering/dma_memory_hierarchy.py
"""

from .buffer_results_to_out_params import (
    BufferResultsToOutParamsError,
    BufferResultsToOutParamsPass,
)
from .dma_memory_hierarchy import (
    LowerDmaMemoryHierarchyError,
    LowerDmaMemoryHierarchyPass,
)
from .nn_to_kernel import LowerNnToKernelPass, LowerNnToKernelError

__all__ = [
    "LowerNnToKernelPass",
    "LowerNnToKernelError",
    "BufferResultsToOutParamsPass",
    "BufferResultsToOutParamsError",
    "LowerDmaMemoryHierarchyPass",
    "LowerDmaMemoryHierarchyError",
]
