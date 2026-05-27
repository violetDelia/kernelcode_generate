"""kernel operation package.

功能说明:
- 聚合 kernel package 内公开 op。

API 列表:
- `class KernelBinaryElewiseOp(out: SSAValue | Operation, lhs: SSAValue | Operation, rhs: SSAValue | Operation, *, kind: str | StringAttr, space: NnMemorySpaceAttr)`
- `class KernelMatmulOp(out: SSAValue | Operation, lhs: SSAValue | Operation, rhs: SSAValue | Operation, space: NnMemorySpaceAttr, *, acc: bool | int | IntegerAttr | IntAttr | SSAValue | Operation = False)`
- `class KernelMatmulFusionOp(out: SSAValue | Operation, lhs: SSAValue | Operation, rhs: SSAValue | Operation, acc: SSAValue | Operation, *, space: NnMemorySpaceAttr, fusion_list: str | StringAttr = "")`
- `class KernelImg2col1dOp(out: SSAValue | Operation, input_value: SSAValue | Operation, k: SSAValue | Operation, s: SSAValue | Operation, d: SSAValue | Operation, p_left: SSAValue | Operation, p_right: SSAValue | Operation, space: NnMemorySpaceAttr)`
- `class KernelImg2col2dOp(out: SSAValue | Operation, input_value: SSAValue | Operation, kh: SSAValue | Operation, kw: SSAValue | Operation, sh: SSAValue | Operation, sw: SSAValue | Operation, dh: SSAValue | Operation, dw: SSAValue | Operation, ph: SSAValue | Operation, pw: SSAValue | Operation, pl: SSAValue | Operation, pr: SSAValue | Operation, space: NnMemorySpaceAttr)`
- `class KernelSelectOp(out: SSAValue | Operation, cond: SSAValue | Operation, lhs: SSAValue | Operation, rhs: SSAValue | Operation, space: NnMemorySpaceAttr)`
- `class KernelExpOp(input_value: SSAValue | Operation, out: SSAValue | Operation, space: NnMemorySpaceAttr)`
- `class KernelReduceOp(out: SSAValue | Operation, input_value: SSAValue | Operation, *, kind: str | StringAttr, axis: int | IntegerAttr | IntAttr, keepdim: bool | int | IntegerAttr | IntAttr, space: NnMemorySpaceAttr)`
- `class KernelReduceMinOp(out: SSAValue | Operation, input_value: SSAValue | Operation, axis: int | IntegerAttr | IntAttr, keepdim: bool | int | IntegerAttr | IntAttr, space: NnMemorySpaceAttr)`

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
from .structured import KernelImg2col1dOp, KernelImg2col2dOp, KernelMatmulFusionOp, KernelMatmulOp
from .unary import KernelExpOp

__all__ = ["KernelBinaryElewiseOp", "KernelMatmulOp", "KernelMatmulFusionOp", "KernelImg2col1dOp", "KernelImg2col2dOp", "KernelSelectOp", "KernelExpOp", "KernelReduceOp", "KernelReduceMinOp"]
