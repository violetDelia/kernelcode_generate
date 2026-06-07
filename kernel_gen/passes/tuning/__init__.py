"""tuning pass package.


功能说明:
- 提供 tuning 目录下 pass 的公开导出入口。
- 当前包含 `lower-dma-memory-hierarchy`、`kernel-pattern-attach`、
  `outline-device-kernel` 与 `transform-apply` pass，可 standalone 使用，也可由 pipeline 复用。

API 列表:
- `class LowerDmaMemoryHierarchyPass(fold: bool = True, apply_op: str | None = None)`
- `class KernelPatternAttachPass(fold: bool = True)`
- `class OutlineDeviceKernelFuncPattern(candidates: dict[str, tuple[int, int, int, int]])`
- `OutlineDeviceKernelFuncPattern.match_and_rewrite(op: func.FuncOp, rewriter: PatternRewriter) -> None`
- `get_outline_device_kernel_pass_patterns(candidates: dict[str, tuple[int, int, int, int]]) -> list[RewritePattern]`
- `class OutlineDeviceKernelPass()`
- `OutlineDeviceKernelPass.apply(ctx: Context, module: ModuleOp) -> None`
- `class TransformApplyPass(fold: bool = True)`

使用示例:
- from kernel_gen.passes.tuning import LowerDmaMemoryHierarchyPass, KernelPatternAttachPass
- pass_obj = LowerDmaMemoryHierarchyPass(apply_op='matmul{["", "tlm1", "tlm2"]}')
- pattern_pass = KernelPatternAttachPass()
- outline_pass = OutlineDeviceKernelPass()
- transform_pass = TransformApplyPass()

关联文件:
- spec: [spec/pass/tuning/dma_memory_hierarchy.md](spec/pass/tuning/dma_memory_hierarchy.md)
- spec: [spec/pass/tuning/kernel_pattern_attach.md](spec/pass/tuning/kernel_pattern_attach.md)
- spec: [spec/pass/tuning/outline_device_kernel.md](spec/pass/tuning/outline_device_kernel.md)
- spec: [spec/pass/tuning/transform_apply.md](spec/pass/tuning/transform_apply.md)
- test: [test/passes/tuning/test_dma_memory_hierarchy.py](test/passes/tuning/test_dma_memory_hierarchy.py)
- test: [test/passes/tuning/test_kernel_pattern_attach.py](test/passes/tuning/test_kernel_pattern_attach.py)
- test: [test/passes/tuning/test_outline_device_kernel.py](test/passes/tuning/test_outline_device_kernel.py)
- test: [test/passes/tuning/test_transform_apply.py](test/passes/tuning/test_transform_apply.py)
- 功能实现:
  - [kernel_gen/passes/tuning/__init__.py](kernel_gen/passes/tuning/__init__.py)
  - [kernel_gen/passes/tuning/dma_memory_hierarchy.py](kernel_gen/passes/tuning/dma_memory_hierarchy.py)
  - [kernel_gen/passes/tuning/kernel_pattern_attach.py](kernel_gen/passes/tuning/kernel_pattern_attach.py)
  - [kernel_gen/passes/tuning/outline_device_kernel.py](kernel_gen/passes/tuning/outline_device_kernel.py)
  - [kernel_gen/passes/tuning/transform_apply.py](kernel_gen/passes/tuning/transform_apply.py)
"""

from .dma_memory_hierarchy import LowerDmaMemoryHierarchyPass
from .kernel_pattern_attach import KernelPatternAttachPass
from .outline_device_kernel import (
    OutlineDeviceKernelFuncPattern,
    OutlineDeviceKernelPass,
    get_outline_device_kernel_pass_patterns,
)
from .transform_apply import TransformApplyPass

__all__ = [
    "LowerDmaMemoryHierarchyPass",
    "KernelPatternAttachPass",
    "OutlineDeviceKernelFuncPattern",
    "OutlineDeviceKernelPass",
    "get_outline_device_kernel_pass_patterns",
    "TransformApplyPass",
]
