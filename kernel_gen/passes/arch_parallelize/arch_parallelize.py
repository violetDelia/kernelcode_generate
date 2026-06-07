"""arch-parallelize compatibility submodule.


功能说明:
- 保留旧公开 import path `kernel_gen.passes.arch_parallelize.arch_parallelize`。
- 真实实现已迁移到 `kernel_gen.passes.arch.arch_parallelize`。
- 本文件只 re-export 公开 class，不承载 pass 业务逻辑。

API 列表:
- `class ArchParallelizePass(target: str = "npu_demo", parallel_level: str = "block")`
- `ArchParallelizePass.from_options(options: dict[str, str]) -> ArchParallelizePass`
- `ArchParallelizePass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.arch_parallelize.arch_parallelize import ArchParallelizePass
- pass_obj = ArchParallelizePass(target="npu_demo", parallel_level="block")

关联文件:
- spec: spec/pass/arch/arch_parallelize.md
- test: test/passes/arch/test_arch_parallelize.py
- 功能实现: kernel_gen/passes/arch/arch_parallelize.py
"""

from kernel_gen.passes.arch.arch_parallelize import ArchParallelizePass

__all__ = ["ArchParallelizePass"]
