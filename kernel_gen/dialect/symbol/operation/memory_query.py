"""symbol memory query operations.

功能说明:
- 定义 symbol.get_dim 与 symbol.get_stride op。

API 列表:
- `class SymbolGetDimOp(memory: SSAValue, index: int | IntAttr)`
- `class SymbolGetStrideOp(memory: SSAValue, index: int | IntAttr)`

使用示例:
- `from kernel_gen.dialect.symbol.operation import ...`

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/symbol/
- 功能实现: kernel_gen/dialect/symbol/operation/memory_query.py
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE, KernelCodeError
from kernel_gen.core.contracts import raise_verify_error
from xdsl.dialects import arith
from xdsl.dialects.builtin import BFloat16Type, Float16Type, Float32Type, Float64Type, IntAttr, IntegerAttr, IntegerType, StringAttr, f32, f64, i1, i32
from xdsl.dialect_interfaces.constant_materialization import ConstantMaterializationInterface
from xdsl.ir import Attribute, Block, Dialect, Operation, ParametrizedAttribute, Region, SSAValue, TypeAttribute
from xdsl.irdl import (
    IRDLOperation,
    attr_def,
    irdl_attr_definition,
    irdl_op_definition,
    opt_operand_def,
    opt_result_def,
    operand_def,
    param_def,
    region_def,
    result_def,
    traits_def,
    var_operand_def,
)
from xdsl.interfaces import HasFolderInterface
from xdsl.parser import AttrParser
from xdsl.printer import Printer
from xdsl.traits import IsTerminator, NoTerminator, Pure

from kernel_gen.dialect.nn import NnMemoryType

from ..attr import SymbolExprAttr, SymbolIterAttr
from ..type import SymbolIterType, SymbolPtrType, SymbolValueType

from ..type import SymbolIterType, SymbolValueType

# Localized helpers from retired package-internal modules.

_ERROR_SCENE = "dialect.symbol"

def _format_error(expected: str, actual: str = ERROR_ACTUAL) -> str:
    """格式化 symbol dialect 统一错误文本。

    功能说明:
    - 复用核心错误模板生成 verifier、value error 与 type error 的稳定文本。

    使用示例:
    - message = _format_error("symbol value type expected")
    """

    return ERROR_TEMPLATE.format(
        scene=_ERROR_SCENE,
        expected=expected,
        actual=actual,
        action=ERROR_ACTION,
    )

def _verify_axis(axis: Attribute, rank: int, op_name: str) -> int:
    """校验 axis attribute 并返回轴号。


    功能说明:
    - 统一校验 `symbol.get_dim/get_stride` 的静态整数轴号约束。

    使用示例:
    - _verify_axis(IntAttr(0), 2, "symbol.get_dim")

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/symbol/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol/
    """

    if not isinstance(axis, IntAttr):
        raise_verify_error(_ERROR_SCENE, f"{op_name} axis must be a static integer")
    if axis.data < 0 or axis.data >= rank:
        raise_verify_error(_ERROR_SCENE, f"{op_name} axis out of range")
    return axis.data

def _infer_result_type(
    source: SSAValue | Operation,
    axis: Attribute,
    op_name: str,
    field_name: str,
) -> SymbolValueType:
    """根据 memory type 推导查询 op 的结果类型。


    功能说明:
    - 从 `NnMemoryType` 的 `shape/stride` 中读取真实条目，并推导 `SymbolValueType`。
    - 当 source/axis 非法时返回占位类型，交由 verifier 报出正式错误。

    使用示例:
    - _infer_result_type(source, IntAttr(0), "symbol.get_dim", "shape")

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/symbol/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol/
    """

    fallback = SymbolValueType.from_expr("0")
    source_value = SSAValue.get(source)
    if not isinstance(source_value.type, NnMemoryType):
        return fallback
    entries = source_value.type.shape.data if field_name == "shape" else source_value.type.stride.data
    if not isinstance(axis, IntAttr) or axis.data < 0 or axis.data >= len(entries):
        return fallback
    try:
        entry = entries[axis.data]
        if not isinstance(entry, SymbolExprAttr):
            return fallback
        return SymbolValueType.from_expr(entry.expr.data)
    except KernelCodeError:
        return fallback

def _entry_to_expr(entry: Attribute, op_name: str, field_name: str) -> str:
    """将 memory shape/stride 条目转换为可验证 symbol 表达式。


    功能说明:
    - 校验条目必须是 `SymbolExprAttr`，并保留匿名动态值 `?` 的现有 verifier 行为。

    使用示例:
    - expr = _entry_to_expr(entry, "symbol.get_dim", "shape")

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/symbol/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol/
    """

    if not isinstance(entry, SymbolExprAttr):
        raise_verify_error(_ERROR_SCENE, f"{op_name} {field_name} entry must be SymbolExprAttr")
    entry.verify()
    expr_text = entry.expr.data
    return expr_text

def _get_concrete_symbol_int_value(attr: Attribute) -> int | None:
    """提取静态可求值的 `!symbol.int` 整数值。


    功能说明:
    - 仅当 `attr` 是静态整数 `SymbolValueType` 时返回具体整数。
    - 动态 symbol 表达返回 `None`，供 fold 逻辑保守拒绝。

    使用示例:
    - _get_concrete_symbol_int_value(SymbolValueType.from_expr("3"))

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/symbol/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol/
    """

    if not isinstance(attr, SymbolValueType):
        return None
    value = attr.get_value()
    if not isinstance(value, int):
        return None
    return value


class _BaseSymbolMemoryQueryOp(IRDLOperation, HasFolderInterface):
    """memory 元信息查询 op 基类。"""

    traits = traits_def(Pure())
    source = operand_def(Attribute)
    axis = attr_def(Attribute)
    result = result_def(SymbolValueType)

    FIELD_NAME: ClassVar[str]

    def __init__(
        self: "_BaseSymbolMemoryQueryOp",
        source: SSAValue | Operation,
        axis: int | Attribute,
    ) -> None:
        """初始化 memory 元信息查询 op。


        功能说明:
        - 设置 source operand、静态轴号 attribute 与推导后的 symbol 结果类型。

        使用示例:
        - SymbolGetDimOp(source, 0)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        axis_attr = axis if isinstance(axis, Attribute) else IntAttr(axis)
        super().__init__(
            operands=[source],
            result_types=[_infer_result_type(source, axis_attr, self.name, self.FIELD_NAME)],
            attributes={"axis": axis_attr},
        )

    def verify_(self: "_BaseSymbolMemoryQueryOp") -> None:
        """校验 memory 元信息查询 op。


        功能说明:
        - 校验 source 必须为 `NnMemoryType`、axis 合法，且目标条目不是匿名动态值 `?`。

        使用示例:
        - SymbolGetStrideOp(source, 0).verify_()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        source_type = SSAValue.get(self.source).type
        if not isinstance(source_type, NnMemoryType):
            raise_verify_error(_ERROR_SCENE, f"{self.name} source must be nn.memory")
        source_type.verify()
        entries = source_type.shape.data if self.FIELD_NAME == "shape" else source_type.stride.data
        axis = _verify_axis(self.axis, len(entries), self.name)
        expected = SymbolValueType.from_expr(_entry_to_expr(entries[axis], self.name, self.FIELD_NAME))
        if self.result.type != expected:
            raise_verify_error(_ERROR_SCENE, f"{self.name} result type must match source {self.FIELD_NAME} entry")

    def fold(self: "_BaseSymbolMemoryQueryOp") -> Sequence[SSAValue | Attribute] | None:
        """折叠静态 memory 元信息查询 op。


        功能说明:
        - 当 `symbol.get_dim/get_stride` 读取到静态整数 shape/stride 条目时，返回 `IntAttr` 交给
          `SymbolConstantMaterializationInterface` 物化为 `symbol.const`。
        - 动态符号表达、未知 `?`、非法 source/axis 或 result type 不匹配时保守不折叠。

        使用示例:
        - SymbolGetDimOp(source, 0).fold()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        source_type = SSAValue.get(self.source).type
        if not isinstance(source_type, NnMemoryType):
            return None
        entries = source_type.shape.data if self.FIELD_NAME == "shape" else source_type.stride.data
        if not isinstance(self.axis, IntAttr) or self.axis.data < 0 or self.axis.data >= len(entries):
            return None
        try:
            expected_type = SymbolValueType.from_expr(_entry_to_expr(entries[self.axis.data], self.name, self.FIELD_NAME))
        except KernelCodeError:
            return None
        if SSAValue.get(self.result).type != expected_type:
            return None
        concrete_value = _get_concrete_symbol_int_value(expected_type)
        if concrete_value is None:
            return None
        return (IntAttr(concrete_value),)


@irdl_op_definition
class SymbolGetDimOp(_BaseSymbolMemoryQueryOp):
    """从 nn.memory 读取指定轴 dim 的 symbol 值。"""

    name = "symbol.get_dim"
    FIELD_NAME: ClassVar[str] = "shape"


@irdl_op_definition
class SymbolGetStrideOp(_BaseSymbolMemoryQueryOp):
    """从 nn.memory 读取指定轴 stride 的 symbol 值。"""

    name = "symbol.get_stride"
    FIELD_NAME: ClassVar[str] = "stride"

__all__ = ["SymbolGetDimOp", "SymbolGetStrideOp"]
