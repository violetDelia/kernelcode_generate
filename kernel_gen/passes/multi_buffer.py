"""multi-buffer compatibility module.


功能说明:
- 保留旧公开 import path `kernel_gen.passes.multi_buffer`。
- 真实实现已迁移到 `kernel_gen.passes.memory.multi_buffer`。
- 本文件只 re-export 公开 class，不承载 pass 业务逻辑。

API 列表:
- `class MultiBufferPass(memory_stage: int = 2, fold: bool = True, target: str | None = None)`
- `MultiBufferPass.from_options(options: dict[str, str]) -> MultiBufferPass`
- `MultiBufferPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.multi_buffer import MultiBufferPass
- MultiBufferPass(memory_stage=2).apply(Context(), module)

关联文件:
- spec: spec/pass/memory/multi_buffer.md
- test: test/passes/memory/test_multi_buffer.py
- 功能实现: kernel_gen/passes/memory/multi_buffer.py
"""

from kernel_gen.passes.memory.multi_buffer import MultiBufferPass

__all__ = ["MultiBufferPass"]
