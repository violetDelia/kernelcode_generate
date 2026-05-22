"""nn operation package.

功能说明:
- 承载 nn dialect package 拆分后的 nn operation package 实现。

API 列表:
- `class NnAddOp(...)`
- `class NnBroadcastOp(...)`
- `class NnReduceSumOp(...)`
- `class NnMatmulOp(...)`

使用示例:
- from kernel_gen.dialect.nn.operation import NnAddOp

关联文件:
- spec: spec/dialect/nn.md
- test: test/dialect/nn/
- 功能实现: kernel_gen/dialect/nn/operation/__init__.py
"""

from __future__ import annotations

from kernel_gen.dialect.nn.operation.active import (
    NnExpOp,
    NnHardSigmoidOp,
    NnLeakyReluOp,
    NnReluOp,
    NnSigmoidOp,
    NnSoftmaxOp,
    NnTanhOp,
)
from kernel_gen.dialect.nn.operation.binary import (
    NnAddOp,
    NnDivOp,
    NnEqOp,
    NnFloorDivOp,
    NnGeOp,
    NnGtOp,
    NnLeOp,
    NnLtOp,
    NnMulOp,
    NnNeOp,
    NnSubOp,
    NnTrueDivOp,
)
from kernel_gen.dialect.nn.operation.elewise import NnBroadcastOp, NnCastOp, NnSelectOp, NnTransposeOp
from kernel_gen.dialect.nn.operation.reduce import NnReduceMaxOp, NnReduceMinOp, NnReduceSumOp
from kernel_gen.dialect.nn.operation.structured import NnImg2col1dOp, NnImg2col2dOp, NnMatmulOp

__all__ = [
    "NnAddOp",
    "NnSubOp",
    "NnMulOp",
    "NnDivOp",
    "NnTrueDivOp",
    "NnFloorDivOp",
    "NnEqOp",
    "NnNeOp",
    "NnLtOp",
    "NnLeOp",
    "NnGtOp",
    "NnGeOp",
    "NnSelectOp",
    "NnCastOp",
    "NnBroadcastOp",
    "NnTransposeOp",
    "NnReluOp",
    "NnSigmoidOp",
    "NnTanhOp",
    "NnLeakyReluOp",
    "NnHardSigmoidOp",
    "NnSoftmaxOp",
    "NnExpOp",
    "NnReduceSumOp",
    "NnReduceMinOp",
    "NnReduceMaxOp",
    "NnImg2col1dOp",
    "NnImg2col2dOp",
    "NnMatmulOp",
]
