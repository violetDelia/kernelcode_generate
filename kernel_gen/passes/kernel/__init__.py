"""kernel pass package.


功能说明:
- 提供 kernel IR family 下 pass 的 canonical package root。
- 当前公开 `kernel-aggregate` 与 `kernel-decompose`。

API 列表:
- `class KernelAggregatePass(matmul_acc: bool = False, fold: bool = True)`
- `class KernelDecomposePass(fold: bool = True)`

使用示例:
- from kernel_gen.passes.kernel import KernelAggregatePass, KernelDecomposePass
- aggregate = KernelAggregatePass(matmul_acc=True)
- decompose = KernelDecomposePass()

关联文件:
- spec: spec/pass/kernel/kernel_aggregate.md
- spec: spec/pass/kernel/kernel_decompose.md
- test: test/passes/kernel/test_kernel_aggregate.py
- test: test/passes/kernel/test_kernel_decompose.py
- 功能实现: kernel_gen/passes/kernel/__init__.py
"""

from .kernel_aggregate import KernelAggregatePass
from .kernel_decompose import KernelDecomposePass

__all__ = ["KernelAggregatePass", "KernelDecomposePass"]
