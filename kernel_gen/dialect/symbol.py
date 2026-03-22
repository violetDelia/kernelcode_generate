"""Symbol dialect definitions.

创建者: 金铲铲大作战
最后一次更改: 我不是牛马

功能说明:
- 定义仅表示整数符号值语义的 symbol dialect。
- 提供 `SymbolExprAttr`、`SymbolValueType` 与 `symbol.get_dim/get_stride` 查询 op，不区分 `int8/int64` 等整型宽度。

使用示例:
- from kernel_gen.dialect.symbol import Symbol, SymbolExprAttr, SymbolGetDimOp, SymbolGetStrideOp, SymbolValueType

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/test_symbol_dialect.py
- 功能实现: kernel_gen/dialect/symbol.py
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import ClassVar

from xdsl.dialects.builtin import IntAttr, StringAttr
from xdsl.ir import Attribute, Dialect, Operation, ParametrizedAttribute, SSAValue, TypeAttribute
from xdsl.irdl import IRDLOperation, attr_def, irdl_attr_definition, irdl_op_definition, operand_def, param_def, result_def
from xdsl.parser import AttrParser
from xdsl.printer import Printer
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import NnMemoryType

_SYMBOL_EXPR_PATTERN = re.compile(
    r"^(?:[A-Za-z_][A-Za-z0-9_]*|[0-9]+)(?:\s*[+\-*]\s*(?:[A-Za-z_][A-Za-z0-9_]*|[0-9]+))*$"
)


def _normalize_expr(expr: str) -> str:
    """标准化符号表达字符串。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 去除首尾空白，供 verifier 与打印使用。

    使用示例:
    - _normalize_expr("  N + 1  ")

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol_dialect.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    return expr.strip()


def _verify_axis(axis: Attribute, rank: int, op_name: str) -> int:
    """校验 axis attribute 并返回轴号。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 统一校验 `symbol.get_dim/get_stride` 的静态整数轴号约束。

    使用示例:
    - _verify_axis(IntAttr(0), 2, "symbol.get_dim")

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol_dialect.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    if not isinstance(axis, IntAttr):
        raise VerifyException(f"{op_name} axis must be a static integer")
    if axis.data < 0 or axis.data >= rank:
        raise VerifyException(f"{op_name} axis out of range")
    return axis.data


def _entry_to_expr(entry: Attribute, op_name: str, field_name: str) -> str:
    """将 memory 元信息条目转换为 symbol 表达。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 将 `NnMemoryType` 中的 `shape/stride` 条目收敛为 `!symbol.int<\"expr\">` 所需字符串。

    使用示例:
    - _entry_to_expr(IntAttr(4), "symbol.get_dim", "shape")

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol_dialect.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    if isinstance(entry, IntAttr):
        return str(entry.data)
    if isinstance(entry, StringAttr) and entry.data != "?":
        return entry.data
    raise VerifyException(f"{op_name} does not support unknown {field_name} entry '?'")


def _infer_result_type(
    source: SSAValue | Operation,
    axis: Attribute,
    op_name: str,
    field_name: str,
) -> SymbolValueType:
    """根据 memory type 推导查询 op 的结果类型。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 从 `NnMemoryType` 的 `shape/stride` 中读取真实条目，并推导 `SymbolValueType`。
    - 当 source/axis 非法时返回占位类型，交由 verifier 报出正式错误。

    使用示例:
    - _infer_result_type(source, IntAttr(0), "symbol.get_dim", "shape")

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol_dialect.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    fallback = SymbolValueType.from_expr("0")
    source_value = SSAValue.get(source)
    if not isinstance(source_value.type, NnMemoryType):
        return fallback
    entries = source_value.type.shape.data if field_name == "shape" else source_value.type.stride.data
    if not isinstance(axis, IntAttr) or axis.data < 0 or axis.data >= len(entries):
        return fallback
    try:
        return SymbolValueType.from_expr(_entry_to_expr(entries[axis.data], op_name, field_name))
    except VerifyException:
        return fallback


@irdl_attr_definition
class SymbolExprAttr(ParametrizedAttribute):
    """承载单个整数符号表达。"""

    name = "symbol.expr"

    expr: StringAttr = param_def(StringAttr)

    @classmethod
    def parse_parameters(cls, parser: AttrParser) -> Sequence[Attribute]:
        """解析符号表达参数。"""

        parser.parse_punctuation("<", "Expected '<' for symbol expr attribute.")
        expr = parser.parse_str_literal("Expected quoted symbol expression.")
        parser.parse_punctuation(">", "Expected '>' for symbol expr attribute.")
        return (StringAttr(expr),)

    def print_parameters(self, printer: Printer) -> None:
        """打印符号表达参数。"""

        printer.print_string("<")
        printer.print_string_literal(_normalize_expr(self.expr.data))
        printer.print_string(">")

    def verify(self) -> None:
        """校验符号表达。"""

        expr = _normalize_expr(self.expr.data)
        if not expr:
            raise VerifyException("symbol expr must not be empty")
        if not _SYMBOL_EXPR_PATTERN.fullmatch(expr):
            raise VerifyException("symbol expr must contain identifiers, integers, spaces, +, - or *")

    @classmethod
    def from_expr(cls, expr: str) -> "SymbolExprAttr":
        """从字符串构造符号表达 attribute。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 为测试与实现提供统一的构造入口。

        使用示例:
        - SymbolExprAttr.from_expr("N")

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        return cls(StringAttr(_normalize_expr(expr)))


@irdl_attr_definition
class SymbolValueType(ParametrizedAttribute, TypeAttribute):
    """仅表示整数符号值语义的类型。"""

    name = "symbol.int"

    expr: SymbolExprAttr = param_def(SymbolExprAttr)

    @classmethod
    def parse_parameters(cls, parser: AttrParser) -> Sequence[Attribute]:
        """解析整数符号值类型参数。"""

        parser.parse_punctuation("<", "Expected '<' for symbol int type.")
        expr = parser.parse_str_literal("Expected quoted symbol expression.")
        parser.parse_punctuation(">", "Expected '>' for symbol int type.")
        return (SymbolExprAttr.from_expr(expr),)

    def print_parameters(self, printer: Printer) -> None:
        """打印整数符号值类型参数。"""

        printer.print_string("<")
        printer.print_string_literal(_normalize_expr(self.expr.expr.data))
        printer.print_string(">")

    def verify(self) -> None:
        """校验整数符号值类型。"""

        self.expr.verify()

    @classmethod
    def from_expr(cls, expr: str) -> "SymbolValueType":
        """从字符串构造整数符号值类型。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 统一创建只表示整数类型的 symbol value type。

        使用示例:
        - SymbolValueType.from_expr("N")

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        return cls(SymbolExprAttr.from_expr(expr))


class _BaseSymbolMemoryQueryOp(IRDLOperation):
    """memory 元信息查询 op 基类。"""

    source = operand_def(Attribute)
    axis = attr_def(Attribute)
    result = result_def(SymbolValueType)

    FIELD_NAME: ClassVar[str]

    def __init__(self, source: SSAValue | Operation, axis: int | Attribute) -> None:
        """初始化 memory 元信息查询 op。

        创建者: 我不是牛马
        最后一次更改: 我不是牛马

        功能说明:
        - 设置 source operand、静态轴号 attribute 与推导后的 symbol 结果类型。

        使用示例:
        - SymbolGetDimOp(source, 0)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        axis_attr = axis if isinstance(axis, Attribute) else IntAttr(axis)
        super().__init__(
            operands=[source],
            result_types=[_infer_result_type(source, axis_attr, self.name, self.FIELD_NAME)],
            attributes={"axis": axis_attr},
        )

    def verify_(self) -> None:
        """校验 memory 元信息查询 op。

        创建者: 我不是牛马
        最后一次更改: 我不是牛马

        功能说明:
        - 校验 source 必须为 `NnMemoryType`、axis 合法，且目标条目不是匿名动态值 `?`。

        使用示例:
        - SymbolGetStrideOp(source, 0).verify_()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        source_type = SSAValue.get(self.source).type
        if not isinstance(source_type, NnMemoryType):
            raise VerifyException(f"{self.name} source must be nn.memory")
        source_type.verify()
        entries = source_type.shape.data if self.FIELD_NAME == "shape" else source_type.stride.data
        axis = _verify_axis(self.axis, len(entries), self.name)
        expected = SymbolValueType.from_expr(_entry_to_expr(entries[axis], self.name, self.FIELD_NAME))
        if self.result.type != expected:
            raise VerifyException(f"{self.name} result type must match source {self.FIELD_NAME} entry")


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


Symbol = Dialect(
    "symbol",
    [
        SymbolGetDimOp,
        SymbolGetStrideOp,
    ],
    [
        SymbolExprAttr,
        SymbolValueType,
    ],
)

__all__ = [
    "Symbol",
    "SymbolExprAttr",
    "SymbolGetDimOp",
    "SymbolGetStrideOp",
    "SymbolValueType",
]
