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

from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE
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
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import NnMemoryType

from ..common import _format_error, _raise_verify_error
from ..expr.parser import (_SymbolExprNode, _SymbolExprToken, _SymbolExprParserBase, _SymbolExprTextParser, _SymbolExprAttrParser, _tokenize_symbol_expr, _make_symbol_expr_const, _make_symbol_expr_symbol, _make_symbol_expr_unknown, _is_symbol_expr_unknown, _contains_symbol_expr_unknown, _contains_symbol_expr_iter, _make_symbol_expr_iter, _get_symbol_expr_const, _get_concrete_symbol_expr_node_value, _linear_symbol_expr_terms, _make_symbol_expr_neg, _make_symbol_expr_add, _make_symbol_expr_sub, _make_symbol_expr_mul, _make_symbol_expr_keyword_binary, _make_symbol_expr_min, _make_symbol_expr_max, _symbol_expr_precedence, _format_symbol_expr_node, _format_symbol_expr_add, _parse_symbol_expr_from_text, _parse_symbol_expr_from_attr_parser, _normalize_expr, _evaluate_concrete_expr, _canonicalize_symbolic_expr, _is_supported_symbol_expr, _unwrap_symbol_expr_attr_text)
from ..attr import SymbolExprAttr, SymbolIterAttr
from ..type import SymbolIterType, SymbolPtrType, SymbolValueType
from .common import (_verify_axis, _entry_to_expr, _infer_result_type, _is_symbol_int_type, _is_symbol_arith_operand_type, _is_unknown_symbol_int_type, _parse_symbol_binary_operand_types, _symbol_iter_type_expr_node, _symbol_arith_operand_expr_node, _symbol_arith_operand_contains_unknown, _symbol_expr_bounds_are_full_tiles, _linear_distance_is_positive_multiple, _symbol_expr_full_tile_residual_step, _symbol_expr_full_tile_min_step, _symbol_min_full_tile_step_value, _requires_unknown_arith_result, _infer_symbol_arith_result_expr, _alternate_symbol_arith_result_exprs, _get_concrete_symbol_int_value)

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
            _raise_verify_error(f"{self.name} source must be nn.memory")
        source_type.verify()
        entries = source_type.shape.data if self.FIELD_NAME == "shape" else source_type.stride.data
        axis = _verify_axis(self.axis, len(entries), self.name)
        expected = SymbolValueType.from_expr(_entry_to_expr(entries[axis], self.name, self.FIELD_NAME))
        if self.result.type != expected:
            _raise_verify_error(f"{self.name} result type must match source {self.FIELD_NAME} entry")

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
        except VerifyException:
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
