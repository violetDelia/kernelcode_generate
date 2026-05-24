"""arch-parallelize package root.

功能说明:
- 暴露 `arch-parallelize` pass 的 canonical public import path。
- 只从 package root 公开 `ArchParallelizePass`；内部 pattern 不作为跨文件 API。

API 列表:
- `class ArchParallelizePass(target: str = "npu_demo", parallel_level: str = "block")`
- `ArchParallelizePass.from_options(options: dict[str, str]) -> ArchParallelizePass`
- `ArchParallelizePass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.arch_parallelize import ArchParallelizePass
- pass_obj = ArchParallelizePass(target="npu_demo", parallel_level="block")

关联文件:
- spec: spec/pass/arch_parallelize.md
- test: test/passes/test_arch_parallelize.py
- 功能实现: kernel_gen/passes/arch_parallelize/arch_parallelize.py
"""

from .arch_parallelize import ArchParallelizePass

ArchParallelizePass.__module__ = __name__

__all__ = ["ArchParallelizePass"]
