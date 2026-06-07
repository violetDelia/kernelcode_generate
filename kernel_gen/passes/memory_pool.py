"""memory-pool compatibility module.


功能说明:
- 保留旧公开 import path `kernel_gen.passes.memory_pool`。
- 真实实现已迁移到 `kernel_gen.passes.memory.memory_pool`。
- 本文件只 re-export 公开 class，不承载 pass 业务逻辑。

API 列表:
- `class MemoryPoolPass(rewrite: bool = False, fold: bool = True, alignment: int = 1024)`
- `MemoryPoolPass.from_options(options: dict[str, str]) -> MemoryPoolPass`
- `MemoryPoolPass.apply(ctx: Context, module: ModuleOp) -> None`
- `MemoryPoolPass.get_summary(func_name: str) -> MemoryPoolSummary`
- `MemoryPoolPass.all_summaries() -> dict[str, MemoryPoolSummary]`
- `class MemoryPoolSummary(func_name: str, intervals: tuple[MemoryPoolInterval, ...], peak_bytes_by_bucket: dict[tuple[str], sympy.Basic], pool_count: int)`
- `class MemoryPoolInterval(name: str, bucket_key: tuple[str], size_bytes_expr: sympy.Basic, begin_index: int, end_index: int, offset_bytes_expr: sympy.Basic)`

使用示例:
- from kernel_gen.passes.memory_pool import MemoryPoolPass
- pass_obj = MemoryPoolPass(rewrite=True)

关联文件:
- spec: spec/pass/memory/memory_pool.md
- test: test/passes/memory/test_memory_pool.py
- 功能实现: kernel_gen/passes/memory/memory_pool.py
"""

from kernel_gen.passes.memory.memory_pool import MemoryPoolInterval, MemoryPoolPass, MemoryPoolSummary

__all__ = ["MemoryPoolInterval", "MemoryPoolPass", "MemoryPoolSummary"]
