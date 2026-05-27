"""kernel dialect package root.

功能说明:
- 暴露 kernel dialect 稳定 root API。

API 列表:
- `Kernel`
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
- `from kernel_gen.dialect.kernel import Kernel, KernelBinaryElewiseOp, KernelReduceOp`

关联文件:
- spec: spec/dialect/kernel.md
- test: test/dialect/kernel/
- 功能实现: kernel_gen/dialect/kernel/__init__.py
"""

from __future__ import annotations

from xdsl.ir import Dialect

from .operation import KernelBinaryElewiseOp, KernelExpOp, KernelImg2col1dOp, KernelImg2col2dOp, KernelMatmulFusionOp, KernelMatmulOp, KernelReduceMinOp, KernelReduceOp, KernelSelectOp

Kernel = Dialect("kernel", [KernelBinaryElewiseOp, KernelMatmulOp, KernelMatmulFusionOp, KernelImg2col1dOp, KernelImg2col2dOp, KernelSelectOp, KernelExpOp, KernelReduceOp, KernelReduceMinOp], [])

__all__ = [
    "Kernel",
    "KernelBinaryElewiseOp",
    "KernelMatmulOp",
    "KernelMatmulFusionOp",
    "KernelImg2col1dOp",
    "KernelImg2col2dOp",
    "KernelSelectOp",
    "KernelExpOp",
    "KernelReduceOp",
    "KernelReduceMinOp",
]
