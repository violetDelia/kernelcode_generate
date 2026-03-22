"""Symbol dialect definitions.

创建者: 金铲铲大作战
最后一次更改: 我不是牛马

功能说明:
- 定义仅表示整数符号值语义的 symbol dialect。
- 提供 `SymbolExprAttr`、`SymbolValueType`、`symbol.add/sub/mul`、`symbol.eq/ne/lt/le/gt/ge` 与 `symbol.get_dim/get_stride` 查询 op，不区分 `int8/int64` 等整型宽度。

使用示例:
- from kernel_gen.dialect.symbol import Symbol, SymbolAddOp, SymbolEqOp, SymbolSubOp, SymbolMulOp, SymbolExprAttr, SymbolGetDimOp, SymbolGetStrideOp, SymbolValueType

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/test_symbol_dialect.py
- 功能实现: kernel_gen/dialect/symbol.py
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import ClassVar

from xdsl.dialects.builtin import IntAttr, StringAttr, i1
from xdsl.ir import Attribute, Block, Dialect, Operation, ParametrizedAttribute, Region, SSAValue, TypeAttribute
from xdsl.irdl import (
    IRDLOperation,
    attr_def,
    irdl_attr_definition,
    irdl_op_definition,
    operand_def,
    param_def,
    region_def,
    result_def,
    traits_def,
)
from xdsl.parser import AttrParser
from xdsl.printer import Printer
from xdsl.traits import NoTerminator
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


def _is_symbol_int_type(attr: Attribute) -> bool:
    """判断 attribute 是否为 symbol.int 类型。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 为 `symbol.for` 与 `symbol.get_*` verifier 复用统一的 symbol 类型判断。

    使用示例:
    - _is_symbol_int_type(SymbolValueType.from_expr("N"))

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol_dialect.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    return isinstance(attr, SymbolValueType)


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

    def get_value(self) -> int | str:
        """返回 symbol.int 的公开值。

        创建者: 我不是牛马
        最后一次更改: 我不是牛马

        功能说明:
        - 对常量表达返回 `int`。
        - 对符号表达返回标准化后的字符串。

        使用示例:
        - SymbolValueType.from_expr("N").get_value()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        expr = _normalize_expr(self.expr.expr.data)
        return int(expr) if expr.isdigit() else expr

    def is_symbol(self) -> bool:
        """判断当前值是否为非字面量符号表达。

        创建者: 我不是牛马
        最后一次更改: 我不是牛马

        功能说明:
        - 纯数字常量返回 `False`。
        - 其他 symbol 表达返回 `True`。

        使用示例:
        - SymbolValueType.from_expr("1").is_symbol()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        return not _normalize_expr(self.expr.expr.data).isdigit()

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


class _BaseSymbolBinaryArithOp(IRDLOperation):
    """symbol 二元整数算术 op 基类。"""

    lhs = operand_def(Attribute)
    rhs = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(
        self,
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        result_type: Attribute,
    ) -> None:
        """初始化 symbol 二元整数算术 op。

        创建者: 我不是牛马
        最后一次更改: 我不是牛马

        功能说明:
        - 设置两个 `!symbol.int<"expr">` 操作数与单个 `!symbol.int<"expr">` 结果类型。

        使用示例:
        - SymbolAddOp(lhs, rhs, SymbolValueType.from_expr("M + 1"))

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        super().__init__(operands=[lhs, rhs], result_types=[result_type])

    def verify_(self) -> None:
        """校验 symbol 二元整数算术 op 的类型约束。

        创建者: 我不是牛马
        最后一次更改: 我不是牛马

        功能说明:
        - 校验 `lhs`、`rhs` 与 `result` 均为 `!symbol.int<"expr">`。

        使用示例:
        - SymbolMulOp(lhs, rhs, SymbolValueType.from_expr("M*N")).verify_()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        for field_name in ("lhs", "rhs"):
            operand = SSAValue.get(getattr(self, field_name))
            if not _is_symbol_int_type(operand.type):
                raise VerifyException(f"{self.name} {field_name} must have type !symbol.int<\"expr\">")
        if not _is_symbol_int_type(self.result.type):
            raise VerifyException(f"{self.name} result type must be !symbol.int<\"expr\">")

    def print(self, printer: Printer) -> None:
        """打印 symbol 二元整数算术 op 自定义文本语法。"""

        printer.print_string(" ")
        printer.print_ssa_value(self.lhs)
        printer.print_string(", ")
        printer.print_ssa_value(self.rhs)
        printer.print_string(" : ")
        printer.print_attribute(SSAValue.get(self.lhs).type)
        printer.print_string(", ")
        printer.print_attribute(SSAValue.get(self.rhs).type)
        printer.print_string(" -> ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls, parser: AttrParser):
        """解析 symbol 二元整数算术 op 自定义文本语法。"""

        unresolved_lhs = parser.parse_unresolved_operand()
        parser.parse_characters(",", f" in {cls.name}")
        unresolved_rhs = parser.parse_unresolved_operand()
        parser.parse_characters(":", f" in {cls.name}")
        lhs_type = parser.parse_type()
        parser.parse_characters(",", f" in {cls.name} type list")
        rhs_type = parser.parse_type()
        parser.parse_characters("->", f" in {cls.name}")
        result_type = parser.parse_type()

        lhs = parser.resolve_operand(unresolved_lhs, lhs_type)
        rhs = parser.resolve_operand(unresolved_rhs, rhs_type)
        return cls(lhs, rhs, result_type)


class _BaseSymbolCompareOp(IRDLOperation):
    """symbol 二元整数比较 op 基类。"""

    lhs = operand_def(Attribute)
    rhs = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(
        self,
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        result_type: Attribute = i1,
    ) -> None:
        """初始化 symbol 二元整数比较 op。

        创建者: 我不是牛马
        最后一次更改: 我不是牛马

        功能说明:
        - 设置两个 `!symbol.int<"expr">` 操作数与单个 `i1` 结果类型。

        使用示例:
        - SymbolEqOp(lhs, rhs, i1)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        super().__init__(operands=[lhs, rhs], result_types=[result_type])

    def verify_(self) -> None:
        """校验 symbol 二元整数比较 op 的类型约束。

        创建者: 我不是牛马
        最后一次更改: 我不是牛马

        功能说明:
        - 校验 `lhs` 与 `rhs` 均为 `!symbol.int<"expr">`。
        - 校验 `result` 固定为 `i1`。

        使用示例:
        - SymbolLtOp(lhs, rhs, i1).verify_()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        for field_name in ("lhs", "rhs"):
            operand = SSAValue.get(getattr(self, field_name))
            if not _is_symbol_int_type(operand.type):
                raise VerifyException(f"{self.name} {field_name} must have type !symbol.int<\"expr\">")
        if self.result.type != i1:
            raise VerifyException(f"{self.name} result type must be i1")

    def print(self, printer: Printer) -> None:
        """打印 symbol 二元整数比较 op 自定义文本语法。"""

        printer.print_string(" ")
        printer.print_ssa_value(self.lhs)
        printer.print_string(", ")
        printer.print_ssa_value(self.rhs)
        printer.print_string(" : ")
        printer.print_attribute(SSAValue.get(self.lhs).type)
        printer.print_string(", ")
        printer.print_attribute(SSAValue.get(self.rhs).type)
        printer.print_string(" -> ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls, parser: AttrParser):
        """解析 symbol 二元整数比较 op 自定义文本语法。"""

        unresolved_lhs = parser.parse_unresolved_operand()
        parser.parse_characters(",", f" in {cls.name}")
        unresolved_rhs = parser.parse_unresolved_operand()
        parser.parse_characters(":", f" in {cls.name}")
        lhs_type = parser.parse_type()
        parser.parse_characters(",", f" in {cls.name} type list")
        rhs_type = parser.parse_type()
        parser.parse_characters("->", f" in {cls.name}")
        result_type = parser.parse_type()

        lhs = parser.resolve_operand(unresolved_lhs, lhs_type)
        rhs = parser.resolve_operand(unresolved_rhs, rhs_type)
        return cls(lhs, rhs, result_type)


@irdl_op_definition
class SymbolAddOp(_BaseSymbolBinaryArithOp):
    """两个 symbol.int 值的整数加法。"""

    name = "symbol.add"


@irdl_op_definition
class SymbolSubOp(_BaseSymbolBinaryArithOp):
    """两个 symbol.int 值的整数减法。"""

    name = "symbol.sub"


@irdl_op_definition
class SymbolMulOp(_BaseSymbolBinaryArithOp):
    """两个 symbol.int 值的整数乘法。"""

    name = "symbol.mul"


@irdl_op_definition
class SymbolEqOp(_BaseSymbolCompareOp):
    """两个 symbol.int 值的相等比较。"""

    name = "symbol.eq"


@irdl_op_definition
class SymbolNeOp(_BaseSymbolCompareOp):
    """两个 symbol.int 值的不等比较。"""

    name = "symbol.ne"


@irdl_op_definition
class SymbolLtOp(_BaseSymbolCompareOp):
    """两个 symbol.int 值的小于比较。"""

    name = "symbol.lt"


@irdl_op_definition
class SymbolLeOp(_BaseSymbolCompareOp):
    """两个 symbol.int 值的小于等于比较。"""

    name = "symbol.le"


@irdl_op_definition
class SymbolGtOp(_BaseSymbolCompareOp):
    """两个 symbol.int 值的大于比较。"""

    name = "symbol.gt"


@irdl_op_definition
class SymbolGeOp(_BaseSymbolCompareOp):
    """两个 symbol.int 值的大于等于比较。"""

    name = "symbol.ge"


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


@irdl_op_definition
class SymbolForOp(IRDLOperation):
    """以 symbol.int 边界驱动的半开区间循环。"""

    name = "symbol.for"

    start = operand_def(Attribute)
    end = operand_def(Attribute)
    step = operand_def(Attribute)
    body = region_def()
    traits = traits_def(NoTerminator())

    def __init__(
        self,
        start: SSAValue | Operation,
        end: SSAValue | Operation,
        step: SSAValue | Operation,
        body: Region | Block | Sequence[Operation] | Sequence[Block],
    ) -> None:
        """初始化 symbol.for。

        创建者: 我不是牛马
        最后一次更改: 我不是牛马

        功能说明:
        - 设置 start/end/step 三个 symbol.int 操作数与单块循环体。
        - 循环体块参数表示当前迭代变量 `it`。

        使用示例:
        - SymbolForOp(start, end, step, Block(arg_types=[SymbolValueType.from_expr("M")]))

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        if isinstance(body, Block):
            body = Region(body)
        elif not isinstance(body, Region):
            body = Region(list(body))
        super().__init__(operands=[start, end, step], regions=[body])

    def verify_(self) -> None:
        """校验 symbol.for 约束。

        创建者: 我不是牛马
        最后一次更改: 我不是牛马

        功能说明:
        - 校验 start/end/step/it 均为 `!symbol.int<\"expr\">`。
        - 校验 region 为单块且仅包含一个块参数。
        - 当 step 可静态判定为 `0` 时直接报错。

        使用示例:
        - SymbolForOp(start, end, step, body).verify_()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        for operand_name in ("start", "end", "step"):
            operand = SSAValue.get(getattr(self, operand_name))
            if not _is_symbol_int_type(operand.type):
                raise VerifyException(f"{self.name} {operand_name} must have type !symbol.int<\"expr\">")

        step_type = SSAValue.get(self.step).type
        assert isinstance(step_type, SymbolValueType)
        if _normalize_expr(step_type.expr.expr.data) == "0":
            raise VerifyException(f"{self.name} step must not be zero")

        blocks = list(self.body.blocks)
        if len(blocks) != 1:
            raise VerifyException(f"{self.name} only supports single-block regions")
        block = blocks[0]
        if len(block.args) != 1:
            raise VerifyException(f"{self.name} body must have exactly one block argument")
        iter_arg = block.args[0]
        if not _is_symbol_int_type(iter_arg.type):
            raise VerifyException(f"{self.name} it must have type !symbol.int<\"expr\">")

    def print(self, printer: Printer) -> None:
        """打印 symbol.for 自定义文本语法。"""

        blocks = list(self.body.blocks)
        if len(blocks) != 1 or len(blocks[0].args) != 1:
            printer.print_op_with_default_format(self)
            return
        block = blocks[0]
        iter_arg = block.args[0]
        printer.print_string(" ")
        printer.print_ssa_value(iter_arg)
        printer.print_string(" = ")
        printer.print_ssa_value(self.start)
        printer.print_string(" to ")
        printer.print_ssa_value(self.end)
        printer.print_string(" step ")
        printer.print_ssa_value(self.step)
        printer.print_string(" : ")
        printer.print_attribute(SSAValue.get(self.start).type)
        printer.print_string(", ")
        printer.print_attribute(SSAValue.get(self.end).type)
        printer.print_string(", ")
        printer.print_attribute(SSAValue.get(self.step).type)
        printer.print_string(" {")
        if block.ops:
            with printer.indented():
                for op in block.ops:
                    printer._print_new_line()
                    printer.print_op(op)
            printer._print_new_line(indent=0)
        else:
            printer._print_new_line(indent=0)
        printer.print_string("}")

    @classmethod
    def parse(cls, parser: AttrParser) -> "SymbolForOp":
        """解析 symbol.for 自定义文本语法。"""

        unresolved_iter = parser.parse_argument(expect_type=False)
        parser.parse_characters("=", " in symbol.for")
        start = parser.parse_unresolved_operand()
        parser.parse_characters("to", " in symbol.for")
        end = parser.parse_unresolved_operand()
        parser.parse_characters("step", " in symbol.for")
        step = parser.parse_unresolved_operand()
        parser.parse_characters(":", " in symbol.for")
        start_type = parser.parse_type()
        parser.parse_characters(",", " in symbol.for type list")
        end_type = parser.parse_type()
        parser.parse_characters(",", " in symbol.for type list")
        step_type = parser.parse_type()

        iter_arg = unresolved_iter.resolve(start_type)
        body = parser.parse_region((iter_arg,))
        start_value = parser.resolve_operand(start, start_type)
        end_value = parser.resolve_operand(end, end_type)
        step_value = parser.resolve_operand(step, step_type)
        return cls(start_value, end_value, step_value, body)


Symbol = Dialect(
    "symbol",
    [
        SymbolAddOp,
        SymbolSubOp,
        SymbolMulOp,
        SymbolEqOp,
        SymbolNeOp,
        SymbolLtOp,
        SymbolLeOp,
        SymbolGtOp,
        SymbolGeOp,
        SymbolGetDimOp,
        SymbolGetStrideOp,
        SymbolForOp,
    ],
    [
        SymbolExprAttr,
        SymbolValueType,
    ],
)

__all__ = [
    "Symbol",
    "SymbolAddOp",
    "SymbolEqOp",
    "SymbolExprAttr",
    "SymbolGeOp",
    "SymbolGetDimOp",
    "SymbolMulOp",
    "SymbolGtOp",
    "SymbolLeOp",
    "SymbolLtOp",
    "SymbolNeOp",
    "SymbolForOp",
    "SymbolGetStrideOp",
    "SymbolSubOp",
    "SymbolValueType",
]
