"""NN dialect package root.

功能说明:
- 承载 nn dialect package 拆分后的 NN dialect package root 实现。

API 列表:
- `Nn`
- `class NnMemorySpaceAttr(space: StringAttr)`
- `class NnMemoryType(shape: ArrayAttr[SymbolExprAttr], stride: ArrayAttr[SymbolExprAttr], element_type: Attribute, space: NnMemorySpaceAttr, template_name: StringAttr | str | None = None, *, external_attrs: DictionaryAttr | dict[str, Attribute] | None = None)`
- `copy_memory_type(memory_type: NnMemoryType, *, shape: ArrayAttr[SymbolExprAttr] | None = None, stride: ArrayAttr[SymbolExprAttr] | None = None, element_type: Attribute | None = None, space: NnMemorySpaceAttr | None = None) -> NnMemoryType`
- `copy_memory_type_with_template_name(memory_type: NnMemoryType, template_name: str | StringAttr, *, shape: ArrayAttr[SymbolExprAttr] | None = None, stride: ArrayAttr[SymbolExprAttr] | None = None, element_type: Attribute | None = None, space: NnMemorySpaceAttr | None = None) -> NnMemoryType`
- `copy_memory_type_with_external_attr(memory_type: NnMemoryType, key: str, value: Attribute) -> NnMemoryType`
- `class NnAddOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnSubOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnMulOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnDivOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnTrueDivOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnFloorDivOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnEqOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnNeOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnLtOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnLeOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnGtOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnGeOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnSelectOp(pred: SSAValue, on_true: SSAValue, on_false: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnCastOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnBroadcastOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnTransposeOp(input_value: SSAValue, result_type: NnMemoryType, perm: Sequence[int] | ArrayAttr[IntegerAttr], space: NnMemorySpaceAttr)`
- `class NnReluOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnSigmoidOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnTanhOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnLeakyReluOp(input_value: SSAValue, alpha: SSAValue | None, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnHardSigmoidOp(input_value: SSAValue, alpha: SSAValue | None, beta: SSAValue | None, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnSoftmaxOp(input_value: SSAValue, result_type: NnMemoryType, axis: int | IntegerAttr, space: NnMemorySpaceAttr)`
- `class NnExpOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnReduceSumOp(input_value: SSAValue, result_type: NnMemoryType, axes: Sequence[int] | ArrayAttr[IntegerAttr], keepdim: bool | IntegerAttr, space: NnMemorySpaceAttr)`
- `class NnReduceMinOp(input_value: SSAValue, result_type: NnMemoryType, axes: Sequence[int] | ArrayAttr[IntegerAttr], keepdim: bool | IntegerAttr, space: NnMemorySpaceAttr)`
- `class NnReduceMaxOp(input_value: SSAValue, result_type: NnMemoryType, axes: Sequence[int] | ArrayAttr[IntegerAttr], keepdim: bool | IntegerAttr, space: NnMemorySpaceAttr)`
- `class NnImg2col1dOp(input_value: SSAValue, result_type: NnMemoryType, kw: SSAValue, sw: SSAValue, dw: SSAValue, pl: SSAValue, pr: SSAValue, space: NnMemorySpaceAttr)`
- `class NnImg2col2dOp(input_value: SSAValue, result_type: NnMemoryType, kh: SSAValue, kw: SSAValue, sh: SSAValue, sw: SSAValue, dh: SSAValue, dw: SSAValue, ph: SSAValue, pw: SSAValue, pl: SSAValue, pr: SSAValue, space: NnMemorySpaceAttr)`
- `class NnMatmulOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

使用示例:
- from kernel_gen.dialect.nn import Nn, NnAddOp, NnMemoryType

关联文件:
- spec: spec/dialect/nn.md
- test: test/dialect/nn/
- 功能实现: kernel_gen/dialect/nn/__init__.py
"""

from __future__ import annotations

from kernel_gen.dialect.nn.attr.space_attr import NnMemorySpaceAttr
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
from kernel_gen.dialect.nn.type.memory_type import (
    NnMemoryType,
    copy_memory_type,
    copy_memory_type_with_external_attr,
    copy_memory_type_with_template_name,
)
from xdsl.ir import Dialect

Nn = Dialect(
    "nn",
    [
        NnAddOp,
        NnSubOp,
        NnMulOp,
        NnDivOp,
        NnTrueDivOp,
        NnFloorDivOp,
        NnEqOp,
        NnNeOp,
        NnLtOp,
        NnLeOp,
        NnGtOp,
        NnGeOp,
        NnSelectOp,
        NnCastOp,
        NnBroadcastOp,
        NnTransposeOp,
        NnReluOp,
        NnSigmoidOp,
        NnTanhOp,
        NnLeakyReluOp,
        NnHardSigmoidOp,
        NnSoftmaxOp,
        NnExpOp,
        NnReduceSumOp,
        NnReduceMinOp,
        NnReduceMaxOp,
        NnImg2col1dOp,
        NnImg2col2dOp,
        NnMatmulOp,
    ],
    [
        NnMemorySpaceAttr,
        NnMemoryType,
    ],
)

__all__ = [
    "Nn",
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
    "NnMemorySpaceAttr",
    "NnMemoryType",
    "copy_memory_type",
    "copy_memory_type_with_template_name",
    "copy_memory_type_with_external_attr",
]
