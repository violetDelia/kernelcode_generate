"""memory pass package.


功能说明:
- 提供 memory planning family 下 pass 的 canonical package root。
- 当前公开 `memory-plan`、`memory-pool`、`multi-buffer-analysis`、`multi-buffer-apply` 与 `multi-buffer`。

API 列表:
- `class MemoryPlanPass(insert_free: bool = False, fold: bool = True, reuse: bool = False, auto_pad: bool = False)`
- `class MemoryPoolPass(rewrite: bool = False, fold: bool = True, alignment: int = 1024)`
- `MemoryPoolPass.get_summary(func_name: str) -> MemoryPoolSummary`
- `MemoryPoolPass.all_summaries() -> dict[str, MemoryPoolSummary]`
- `class MemoryPoolSummary(func_name: str, intervals: tuple[MemoryPoolInterval, ...], peak_bytes_by_bucket: dict[tuple[str], sympy.Basic], pool_count: int)`
- `class MemoryPoolInterval(name: str, bucket_key: tuple[str], size_bytes_expr: sympy.Basic, begin_index: int, end_index: int, offset_bytes_expr: sympy.Basic)`
- `class MultiBufferAnalysisPass(memory_stage: int = 2, fold: bool = True, target: str | None = None)`
- `class MultiBufferApplyPass(fold: bool = True, target: str | None = None, alignment: int = 1024)`
- `class MultiBufferPass(memory_stage: int = 2, fold: bool = True, target: str | None = None, alignment: int = 1024)`

使用示例:
- from kernel_gen.passes.memory import MemoryPlanPass, MemoryPoolPass, MultiBufferAnalysisPass, MultiBufferApplyPass, MultiBufferPass
- memory_plan = MemoryPlanPass(insert_free=True, reuse=True)
- memory_pool = MemoryPoolPass(rewrite=True)
- analysis = MultiBufferAnalysisPass(memory_stage=2)
- apply = MultiBufferApplyPass(target="npu_demo")
- facade = MultiBufferPass(memory_stage=2)

关联文件:
- spec: spec/pass/memory/memory_plan.md
- spec: spec/pass/memory/memory_pool.md
- spec: spec/pass/memory/multi_buffer.md
- test: test/passes/memory/test_memory_plan.py
- test: test/passes/memory/test_memory_pool.py
- test: test/passes/memory/test_multi_buffer.py
- 功能实现: kernel_gen/passes/memory/__init__.py
"""

from .memory_plan import MemoryPlanPass
from .memory_pool import MemoryPoolInterval, MemoryPoolPass, MemoryPoolSummary
from .multi_buffer import MultiBufferAnalysisPass, MultiBufferApplyPass, MultiBufferPass

__all__ = [
    "MemoryPlanPass",
    "MemoryPoolInterval",
    "MemoryPoolPass",
    "MemoryPoolSummary",
    "MultiBufferAnalysisPass",
    "MultiBufferApplyPass",
    "MultiBufferPass",
]
