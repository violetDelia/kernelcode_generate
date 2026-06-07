"""memory-plan compatibility module.


功能说明:
- 保留旧公开 import path `kernel_gen.passes.memory_plan`。
- 真实实现已迁移到 `kernel_gen.passes.memory.memory_plan`。
- 本文件只 re-export 公开 class，不承载 pass 业务逻辑。

API 列表:
- `class MemoryPlanPass(insert_free: bool = False, fold: bool = True, reuse: bool = False, auto_pad: bool = False)`
- `MemoryPlanPass.from_options(options: dict[str, str]) -> MemoryPlanPass`
- `MemoryPlanPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.memory_plan import MemoryPlanPass
- pass_obj = MemoryPlanPass(insert_free=True, reuse=True)

关联文件:
- spec: spec/pass/memory/memory_plan.md
- test: test/passes/memory/test_memory_plan.py
- 功能实现: kernel_gen/passes/memory/memory_plan.py
"""

from kernel_gen.passes.memory.memory_plan import MemoryPlanPass

__all__ = ["MemoryPlanPass"]
