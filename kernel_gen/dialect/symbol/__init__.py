"""symbol dialect package root.

功能说明:
- 暴露 symbol dialect 稳定 root API。

API 列表:
- `Symbol`
- `class SymbolAddOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- `class SymbolCastOp(source: SSAValue | Operation, result_type: Attribute = i32)`
- `class SymbolConstOp(value: int | IntAttr, result_type: SymbolValueType | None = None)`
- `class SymbolDivOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- `class SymbolEqOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- `class SymbolExprAttr(expr: StringAttr)`
- `class SymbolGeOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- `class SymbolGetDimOp(source: SSAValue | Operation, axis: int | Attribute)`
- `class SymbolMulOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- `class SymbolMinOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- `class SymbolMaxOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- `class SymbolGtOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- `class SymbolLeOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- `class SymbolLtOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- `class SymbolNeOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- `class SymbolIterType(start: SymbolExprAttr, end: SymbolExprAttr, step: SymbolExprAttr)`
- `class SymbolIterAttr(start: SymbolExprAttr, end: SymbolExprAttr, step: SymbolExprAttr)`
- `class SymbolYieldOp(value: SSAValue | Operation)`
- `class SymbolToFloatOp(source: SSAValue | Operation, result_type: Attribute = f32)`
- `class SymbolForOp(start: SSAValue | Operation, end: SSAValue | Operation, step: SSAValue | Operation, body: Region | Block | Sequence[Operation] | Sequence[Block], iter_attr: SymbolIterAttr | None = None, init: SSAValue | Operation | None = None, result_type: Attribute | None = None)`
- `class SymbolFloorDivOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- `class SymbolGetStrideOp(source: SSAValue | Operation, axis: int | Attribute)`
- `class SymbolPtrType(dtype: Attribute, template_name: StringAttr | str | None = None)`
- `class SymbolSubOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- `class SymbolToIntOp(source: SSAValue | Operation, result_type: Attribute = i32)`
- `class SymbolValueType(expr: SymbolExprAttr)`

使用示例:
- `from kernel_gen.dialect.symbol import Symbol, SymbolExprAttr, SymbolForOp`

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/symbol/
- 功能实现: kernel_gen/dialect/symbol/__init__.py
"""

from __future__ import annotations

from xdsl.ir import Dialect

from .attr import SymbolExprAttr, SymbolIterAttr
from .operation import (
    SymbolAddOp, SymbolCastOp, SymbolConstOp, SymbolConstantMaterializationInterface, SymbolDivOp, SymbolEqOp, SymbolFloorDivOp, SymbolForOp, SymbolGeOp, SymbolGetDimOp, SymbolGetStrideOp, SymbolGtOp, SymbolLeOp, SymbolLtOp, SymbolMaxOp, SymbolMinOp, SymbolMulOp, SymbolNeOp, SymbolSubOp, SymbolToFloatOp, SymbolToIntOp, SymbolYieldOp,
)
from .type import SymbolIterType, SymbolPtrType, SymbolValueType

Symbol = Dialect("symbol", [SymbolConstOp, SymbolAddOp, SymbolSubOp, SymbolMulOp, SymbolDivOp, SymbolFloorDivOp, SymbolMinOp, SymbolMaxOp, SymbolEqOp, SymbolNeOp, SymbolLtOp, SymbolLeOp, SymbolGtOp, SymbolGeOp, SymbolCastOp, SymbolToIntOp, SymbolToFloatOp, SymbolGetDimOp, SymbolGetStrideOp, SymbolYieldOp, SymbolForOp], [SymbolExprAttr, SymbolPtrType, SymbolIterAttr, SymbolIterType, SymbolValueType], [SymbolConstantMaterializationInterface()])

__all__ = [
    "Symbol",
    "SymbolAddOp",
    "SymbolCastOp",
    "SymbolConstOp",
    "SymbolDivOp",
    "SymbolEqOp",
    "SymbolExprAttr",
    "SymbolGeOp",
    "SymbolGetDimOp",
    "SymbolMulOp",
    "SymbolMinOp",
    "SymbolMaxOp",
    "SymbolGtOp",
    "SymbolLeOp",
    "SymbolLtOp",
    "SymbolNeOp",
    "SymbolIterType",
    "SymbolIterAttr",
    "SymbolYieldOp",
    "SymbolToFloatOp",
    "SymbolForOp",
    "SymbolFloorDivOp",
    "SymbolGetStrideOp",
    "SymbolPtrType",
    "SymbolSubOp",
    "SymbolToIntOp",
    "SymbolValueType",
]
