"""kernel operation package.

功能说明:
- 聚合 kernel package 内公开 op。

API 列表:
- `class KernelBinaryElewiseOp(...)`
- `class KernelMatmulOp(...)`
- `class KernelSelectOp(...)`
- `class KernelExpOp(...)`
- `class KernelReduceOp(...)`

使用示例:
- `from kernel_gen.dialect.kernel.operation import ...`

关联文件:
- spec: spec/dialect/kernel.md
- test: test/dialect/kernel/
- 功能实现: kernel_gen/dialect/kernel/operation/__init__.py
"""

from __future__ import annotations

from .binary import KernelBinaryElewiseOp
from .reduce import KernelReduceMinOp, KernelReduceOp
from .select import KernelSelectOp
from .structured import KernelImg2col1dOp, KernelImg2col2dOp, KernelMatmulOp
from .unary import KernelExpOp

__all__ = ["KernelBinaryElewiseOp", "KernelMatmulOp", "KernelImg2col1dOp", "KernelImg2col2dOp", "KernelSelectOp", "KernelExpOp", "KernelReduceOp", "KernelReduceMinOp"]
