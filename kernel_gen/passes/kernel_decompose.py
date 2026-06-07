"""kernel-decompose compatibility module.


功能说明:
- 保留旧公开 import path `kernel_gen.passes.kernel_decompose`。
- 真实实现已迁移到 `kernel_gen.passes.kernel.kernel_decompose`。
- 本文件只 re-export 公开 class，不承载 pass 业务逻辑。

API 列表:
- `class KernelDecomposePass(fold: bool = True)`
- `KernelDecomposePass.from_options(options: dict[str, str]) -> KernelDecomposePass`
- `KernelDecomposePass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.kernel_decompose import KernelDecomposePass
- pass_obj = KernelDecomposePass()

关联文件:
- spec: spec/pass/kernel/kernel_decompose.md
- test: test/passes/kernel/test_kernel_decompose.py
- 功能实现: kernel_gen/passes/kernel/kernel_decompose.py
"""

from kernel_gen.passes.kernel.kernel_decompose import KernelDecomposePass

__all__ = ["KernelDecomposePass"]
