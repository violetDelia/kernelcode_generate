"""tuning pass package.


功能说明:
- 提供 tuning 目录下 pass 的公开导出入口。
- 当前包含 `lower-dma-memory-hierarchy`、`kernel-pattern-attach` 与
  `launch-kernel-cost-func` pass，可 standalone 使用，也可由 pipeline 复用。

API 列表:
- `class LowerDmaMemoryHierarchyPass(fold: bool = True, apply_op: str | None = None)`
- `class KernelPatternAttachPass(fold: bool = True)`
- `class LaunchKernelCostFuncPass(cost_kind: str = "DMA1|DMA2|DMA3|DMA4|MAC|VECTOR1|VECTOR2", fold: bool = True)`

使用示例:
- from kernel_gen.passes.tuning import LowerDmaMemoryHierarchyPass, KernelPatternAttachPass
- pass_obj = LowerDmaMemoryHierarchyPass(apply_op='matmul{["", "tlm1", "tlm2"]}')
- pattern_pass = KernelPatternAttachPass()
- pass_obj = LaunchKernelCostFuncPass(cost_kind="DMA1|MAC|VECTOR1")

关联文件:
- spec: [spec/pass/lowering/dma_memory_hierarchy/spec.md](spec/pass/lowering/dma_memory_hierarchy/spec.md)
- spec: [spec/pass/kernel_pattern_attach.md](spec/pass/kernel_pattern_attach.md)
- spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
- test: [test/passes/test_dma_memory_hierarchy.py](test/passes/test_dma_memory_hierarchy.py)
- test: [test/passes/test_kernel_pattern_attach.py](test/passes/test_kernel_pattern_attach.py)
- test: [test/passes/tuning/test_launch_kernel_cost_func.py](test/passes/tuning/test_launch_kernel_cost_func.py)
- 功能实现:
  - [kernel_gen/passes/tuning/__init__.py](kernel_gen/passes/tuning/__init__.py)
  - [kernel_gen/passes/tuning/dma_memory_hierarchy.py](kernel_gen/passes/tuning/dma_memory_hierarchy.py)
  - [kernel_gen/passes/tuning/kernel_pattern_attach.py](kernel_gen/passes/tuning/kernel_pattern_attach.py)
  - [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
"""

from .dma_memory_hierarchy import LowerDmaMemoryHierarchyPass
from .kernel_pattern_attach import KernelPatternAttachPass
from .launch_kernel_cost_func import LaunchKernelCostFuncPass

__all__ = ["LowerDmaMemoryHierarchyPass", "KernelPatternAttachPass", "LaunchKernelCostFuncPass"]
