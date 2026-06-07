"""kernel-aggregate compatibility module.


功能说明:
- 保留旧公开 import path `kernel_gen.passes.kernel_aggregate`。
- 真实实现已迁移到 `kernel_gen.passes.kernel.kernel_aggregate`。
- 本文件只 re-export 公开 class，不承载 pass 业务逻辑。

API 列表:
- `class KernelAggregatePass(matmul_acc: bool = False, fold: bool = True)`
- `KernelAggregatePass.from_options(options: dict[str, str]) -> KernelAggregatePass`
- `KernelAggregatePass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.kernel_aggregate import KernelAggregatePass
- pass_obj = KernelAggregatePass(matmul_acc=True)

关联文件:
- spec: spec/pass/kernel/kernel_aggregate.md
- test: test/passes/kernel/test_kernel_aggregate.py
- 功能实现: kernel_gen/passes/kernel/kernel_aggregate.py
"""

from kernel_gen.passes.kernel.kernel_aggregate import KernelAggregatePass

__all__ = ["KernelAggregatePass"]
