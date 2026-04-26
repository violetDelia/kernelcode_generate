"""Symbol dialect definitions.

创建者: 金铲铲大作战
最后一次更改: 小李飞刀

功能说明:
- 定义仅表示整数符号值语义的 symbol dialect。
- 提供 `SymbolExprAttr`、`SymbolValueType`、`SymbolDimType`、`SymbolIterAttr`、`SymbolIterType`、`symbol.add/sub/mul/div/floordiv`、`symbol.eq/ne/lt/le/gt/ge`、`symbol.to_int/symbol.to_float`、`symbol.get_dim/get_stride`，以及带单个 loop-carried `!symbol.int<"...">` 的 `symbol.for` / `symbol.yield`。
- `symbol.for` 同时兼容旧的无 carried-value 形式和新的 `iter_args(%acc = %zero) ... -> !symbol.int<"...">` 文本语法。
- 在导入 sympy 前设置 `SYMPY_GMPY=0`，规避外部 gmpy 引发的 SystemError。

使用示例:
- from kernel_gen.dialect.symbol import Symbol, SymbolAddOp, SymbolConstOp, SymbolDivOp, SymbolEqOp, SymbolFloorDivOp, SymbolForOp, SymbolYieldOp, SymbolSubOp, SymbolMulOp, SymbolToIntOp, SymbolExprAttr, SymbolGetDimOp, SymbolGetStrideOp, SymbolValueType

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/test_symbol_dialect.py
- 功能实现: kernel_gen/dialect/symbol.py
"""

from __future__ import annotations

import ast as py_ast
import os
import re
from collections.abc import Sequence
from typing import ClassVar, TYPE_CHECKING

from kernel_gen.common.errors import _ERROR_TEMPLATE
os.environ.setdefault("SYMPY_GMPY", "0")
from xdsl.dialects.builtin import BFloat16Type, Float16Type, Float32Type, Float64Type, IntAttr, IntegerType, StringAttr, f32, f64, i1, i32
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
from xdsl.traits import IsTerminator, NoTerminator
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import NnMemoryType

if TYPE_CHECKING:
    from kernel_gen.symbol_variable.symbol_dim import SymbolDim

_SYMBOL_TOKEN_PATTERN = r"(?:[A-Za-z_][A-Za-z0-9_]*|[+-]?[0-9]+)"
_SYMBOL_EXPR_PATTERN = re.compile(
    rf"^(?:{_SYMBOL_TOKEN_PATTERN}(?:\s*(?://|[+\-*/])\s*{_SYMBOL_TOKEN_PATTERN})*|floor\(\s*{_SYMBOL_TOKEN_PATTERN}\s*/\s*{_SYMBOL_TOKEN_PATTERN}\s*\))$"
)
_SYMBOL_DIM_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ERROR_ACTION = "请按接口约束传参"
_ERROR_ACTUAL = "不满足期望"
_ERROR_SCENE = "dialect.symbol"


def _format_error(expected: str, actual: str = _ERROR_ACTUAL) -> str:
    return _ERROR_TEMPLATE.format(
        scene=_ERROR_SCENE,
        expected=expected,
        actual=actual,
        action=_ERROR_ACTION,
    )


def _raise_verify_error(expected: str, *, actual: str = _ERROR_ACTUAL) -> None:
    """统一抛出 symbol dialect verifier 错误。"""

    raise VerifyException(_format_error(expected, actual))


def _raise_value_error(expected: str, *, actual: str = _ERROR_ACTUAL) -> None:
    """统一抛出 symbol dialect value error。"""

    raise ValueError(_format_error(expected, actual))


def _raise_type_error(expected: str, *, actual: str = _ERROR_ACTUAL) -> None:
    """统一抛出 symbol dialect type error。"""

    raise TypeError(_format_error(expected, actual))


def _normalize_symbol_dim_name(name: str) -> str:
    """规范化 symbol.dim 名称。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 去除首尾空白并校验名称合法性。
    - 确保名称满足标识符格式 `[A-Za-z_][A-Za-z0-9_]*`。

    使用示例:
    - _normalize_symbol_dim_name("BLOCK_M")

    关联文件:
    - spec: spec/dialect/tuner.md
    - test: test/dialect/test_tuner_dialect.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    normalized = name.strip()
    if not normalized:
        _raise_verify_error("symbol dim name must not be empty")
    if _SYMBOL_DIM_NAME_PATTERN.fullmatch(normalized) is None:
        _raise_verify_error("symbol dim name must match [A-Za-z_][A-Za-z0-9_]*")
    return normalized


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

    normalized = expr.strip()
    concrete_value = _evaluate_concrete_expr(normalized)
    return str(concrete_value) if concrete_value is not None else normalized


def _evaluate_concrete_expr(expr: str) -> int | None:
    """尝试计算不含符号名的整数表达式。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 对仅由整数常量与 `+/-/*` 组成的表达式返回具体整数值。
    - 当表达式包含符号名或不满足受支持语法时返回 `None`。

    使用示例:
    - _evaluate_concrete_expr("3 + -4")

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol_dialect.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    normalized = expr.strip()
    try:
        parsed = py_ast.parse(normalized, mode="eval")
    except SyntaxError:
        return None

    def _eval(node: py_ast.AST) -> int:
        if isinstance(node, py_ast.Expression):
            return _eval(node.body)
        if isinstance(node, py_ast.Constant) and isinstance(node.value, int):
            return int(node.value)
        if isinstance(node, py_ast.UnaryOp) and isinstance(node.op, (py_ast.UAdd, py_ast.USub)):
            operand = _eval(node.operand)
            return operand if isinstance(node.op, py_ast.UAdd) else -operand
        if isinstance(node, py_ast.BinOp) and isinstance(node.op, (py_ast.Add, py_ast.Sub, py_ast.Mult, py_ast.Div, py_ast.FloorDiv)):
            lhs = _eval(node.left)
            rhs = _eval(node.right)
            if isinstance(node.op, py_ast.Add):
                return lhs + rhs
            if isinstance(node.op, py_ast.Sub):
                return lhs - rhs
            if isinstance(node.op, py_ast.Mult):
                return lhs * rhs
            if rhs == 0:
                _raise_value_error("division by zero is not a concrete integer expression")
            if isinstance(node.op, py_ast.FloorDiv):
                return lhs // rhs
            if lhs % rhs == 0:
                return lhs // rhs
            _raise_value_error("division result is not an exact integer expression")
        _raise_value_error("expression is not a concrete integer expression")

    try:
        return _eval(parsed)
    except ValueError:
        return None


def _make_symbol_runtime_value(expr: str) -> int | "SymbolDim":
    """将公开 symbol 表达解析为运行时可比较值。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 以 `SymbolDim` 的运行时算术语义解释 `+/-/*///` 与 `floor(...)`。
    - 对纯常量表达直接返回 `int`；对符号表达返回 `SymbolDim`。

    使用示例:
    - _make_symbol_runtime_value("4 + N")

    关联文件:
    - spec: spec/dsl/mlir_gen.md
    - test: test/dsl/ast/test_visitor_integration.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    concrete_value = _evaluate_concrete_expr(expr)
    if concrete_value is not None:
        return concrete_value

    try:
        from kernel_gen.symbol_variable.symbol_dim import SymbolDim  # pylint: disable=import-error
    except Exception:
        _raise_value_error("unsupported public symbol expression")

    try:
        parsed = py_ast.parse(expr, mode="eval")
    except SyntaxError:
        try:
            import sympy as sp  # pylint: disable=import-error
        except Exception:
            _raise_value_error("unsupported public symbol expression")
        symbol_names = {
            name
            for name in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr)
            if name != "floor"
        }
        locals_map = {name: sp.Symbol(name, integer=True, real=True) for name in symbol_names}
        locals_map["floor"] = sp.floor
        parsed_expr = sp.sympify(expr, locals=locals_map, evaluate=False)
        concrete_value = _evaluate_concrete_expr(str(parsed_expr))
        return concrete_value if concrete_value is not None else SymbolDim(parsed_expr)

    def _eval(node: py_ast.AST) -> int | SymbolDim:
        if isinstance(node, py_ast.Expression):
            return _eval(node.body)
        if isinstance(node, py_ast.Constant) and isinstance(node.value, int):
            return int(node.value)
        if isinstance(node, py_ast.Name):
            return SymbolDim(node.id)
        if isinstance(node, py_ast.UnaryOp) and isinstance(node.op, py_ast.UAdd):
            return _eval(node.operand)
        if isinstance(node, py_ast.UnaryOp) and isinstance(node.op, py_ast.USub):
            operand = _eval(node.operand)
            return -operand if isinstance(operand, int) else 0 - operand
        if isinstance(node, py_ast.BinOp):
            lhs = _eval(node.left)
            rhs = _eval(node.right)
            if isinstance(node.op, py_ast.Add):
                return lhs + rhs
            if isinstance(node.op, py_ast.Sub):
                return lhs - rhs
            if isinstance(node.op, py_ast.Mult):
                return lhs * rhs
            if isinstance(node.op, py_ast.Div):
                return lhs / rhs
            if isinstance(node.op, py_ast.FloorDiv):
                return lhs // rhs
        if isinstance(node, py_ast.Call):
            if (
                isinstance(node.func, py_ast.Name)
                and node.func.id == "floor"
                and not node.keywords
                and len(node.args) == 1
            ):
                arg_value = _eval(node.args[0])
                if isinstance(arg_value, int):
                    return arg_value
                try:
                    import sympy as sp  # pylint: disable=import-error
                except Exception:
                    _raise_value_error("unsupported public symbol expression")
                return SymbolDim(sp.floor(arg_value.get_symbol()))
        _raise_value_error("unsupported public symbol expression")

    return _eval(parsed)


def _canonicalize_symbolic_expr(expr: str) -> str:
    """生成对外比较用的稳定符号表达文本。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 基于 `SymbolDim` 运行时语义生成公开比较文本。

    使用示例:
    - _canonicalize_symbolic_expr("4 + N")

    关联文件:
    - spec: spec/dsl/mlir_gen.md
    - test: test/dsl/ast/test_visitor_integration.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    value = _make_symbol_runtime_value(expr)
    return str(value if isinstance(value, int) else value.get_value())


def build_public_symbol_expr(lhs_expr: str, rhs_expr: str, op_symbol: str) -> str:
    """按运行时 symbol 语义构造公开表达文本。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一收敛 lowering 结果类型上的公开 `symbol.int<expr>` 文本。

    使用示例:
    - build_public_symbol_expr("N", "4", "*")

    关联文件:
    - spec: spec/dsl/mlir_gen.md
    - test: test/dsl/ast/test_visitor_integration.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    value = _make_symbol_runtime_value(f"{lhs_expr} {op_symbol} {rhs_expr}")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    return str(value.get_value())


def _is_supported_symbol_expr(expr: str) -> bool:
    """判断符号表达是否属于当前 dialect 支持的最小语法。 

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 允许整数常量、标识符、一元 `+/-`、二元 `+/-/*///` 与 `floor(...)`。
    - 用于替代纯正则匹配，接受 SymPy 规范化后的 `-N + M`、`floor(7/N)` 等公开文本。

    使用示例:
    - _is_supported_symbol_expr("-N + M")

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol_dialect.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    try:
        parsed = py_ast.parse(expr, mode="eval")
    except SyntaxError:
        return False

    def _check(node: py_ast.AST) -> bool:
        if isinstance(node, py_ast.Expression):
            return _check(node.body)
        if isinstance(node, py_ast.Name):
            return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", node.id))
        if isinstance(node, py_ast.Constant):
            return isinstance(node.value, int)
        if isinstance(node, py_ast.UnaryOp):
            return isinstance(node.op, (py_ast.UAdd, py_ast.USub)) and _check(node.operand)
        if isinstance(node, py_ast.BinOp):
            return isinstance(node.op, (py_ast.Add, py_ast.Sub, py_ast.Mult, py_ast.Div, py_ast.FloorDiv)) and _check(
                node.left
            ) and _check(node.right)
        if isinstance(node, py_ast.Call):
            return (
                isinstance(node.func, py_ast.Name)
                and node.func.id == "floor"
                and not node.keywords
                and len(node.args) == 1
                and _check(node.args[0])
            )
        return False

    return _check(parsed)


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
        _raise_verify_error(f"{op_name} axis must be a static integer")
    if axis.data < 0 or axis.data >= rank:
        _raise_verify_error(f"{op_name} axis out of range")
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
    _raise_verify_error(f"{op_name} does not support unknown {field_name} entry '?'")


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


def _get_concrete_symbol_int_value(attr: Attribute) -> int | None:
    """提取静态可求值的 `!symbol.int` 整数值。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 仅当 `attr` 是静态整数 `SymbolValueType` 时返回具体整数。
    - 动态 symbol 表达返回 `None`，供 fold 逻辑保守拒绝。

    使用示例:
    - _get_concrete_symbol_int_value(SymbolValueType.from_expr("3"))

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol_dialect.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    if not isinstance(attr, SymbolValueType):
        return None
    value = attr.get_value()
    return value if isinstance(value, int) else None


@irdl_attr_definition
class SymbolExprAttr(ParametrizedAttribute):
    """承载单个整数符号表达。"""

    name = "symbol.expr"

    expr: StringAttr = param_def(StringAttr)

    @classmethod
    def parse_parameters(cls: type["SymbolExprAttr"], parser: AttrParser) -> Sequence[Attribute]:
        """解析符号表达参数。"""

        parser.parse_punctuation("<", "Expected '<' for symbol expr attribute.")
        expr = parser.parse_str_literal("Expected quoted symbol expression.")
        parser.parse_punctuation(">", "Expected '>' for symbol expr attribute.")
        return (StringAttr(expr),)

    def print_parameters(self: "SymbolExprAttr", printer: Printer) -> None:
        """打印符号表达参数。"""

        printer.print_string("<")
        printer.print_string_literal(_normalize_expr(self.expr.data))
        printer.print_string(">")

    def verify(self: "SymbolExprAttr") -> None:
        """校验符号表达。"""

        expr = _normalize_expr(self.expr.data)
        if not expr:
            _raise_verify_error("symbol expr must not be empty")
        if not _is_supported_symbol_expr(expr):
            _raise_verify_error("symbol expr must contain identifiers, integers, +, -, *, /, // or floor(...)")

    @classmethod
    def from_expr(cls: type["SymbolExprAttr"], expr: str) -> "SymbolExprAttr":
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
class SymbolDimType(ParametrizedAttribute, TypeAttribute):
    """表示符号维度名称的类型。"""

    name = "symbol.dim"

    dim: StringAttr = param_def(StringAttr)

    def __post_init__(self: "SymbolDimType") -> None:
        """延迟 symbol.dim 构造期校验。

        创建者: 我不是牛马
        最后一次更改: 我不是牛马

        功能说明:
        - 跳过构造期校验，改由显式 verify 或 op/module verify 触发。
        - 允许 Parser.parse_module 完成后再由 verifier 统一拒绝非法名称。

        使用示例:
        - SymbolDimType(StringAttr("BLOCK_M")).verify()

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        if not isinstance(self, ParametrizedAttribute):
            _raise_type_error("SymbolDimType must be ParametrizedAttribute")

    @classmethod
    def parse_parameters(cls: type["SymbolDimType"], parser: AttrParser) -> Sequence[Attribute]:
        """解析 symbol.dim 类型参数。

        创建者: 我不是牛马
        最后一次更改: 我不是牛马

        功能说明:
        - 解析 `!symbol.dim<"name">` 的名称参数。

        使用示例:
        - SymbolDimType.parse_parameters(parser)

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        parser.parse_punctuation("<", "Expected '<' for symbol dim type.")
        name = parser.parse_str_literal("Expected quoted symbol dim name.")
        parser.parse_punctuation(">", "Expected '>' for symbol dim type.")
        return (StringAttr(name),)

    def print_parameters(self: "SymbolDimType", printer: Printer) -> None:
        """打印 symbol.dim 类型参数。

        创建者: 我不是牛马
        最后一次更改: 我不是牛马

        功能说明:
        - 输出 `!symbol.dim<\"name\">` 的名称参数。

        使用示例:
        - SymbolDimType.from_name("BLOCK_M").print_parameters(printer)

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        printer.print_string("<")
        printer.print_string_literal(self.dim.data)
        printer.print_string(">")

    def verify(self: "SymbolDimType") -> None:
        """校验 symbol.dim 名称合法性。

        创建者: 我不是牛马
        最后一次更改: 我不是牛马

        功能说明:
        - 拒绝空名称或非法标识符。

        使用示例:
        - SymbolDimType.from_name("BLOCK_M").verify()

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        _normalize_symbol_dim_name(self.dim.data)

    def __str__(self: "SymbolDimType") -> str:
        """返回公开的 symbol.dim 文本表示。

        创建者: 我不是牛马
        最后一次更改: 我不是牛马

        功能说明:
        - 生成 `symbol.dim<name>` 形式的字符串表示。

        使用示例:
        - str(SymbolDimType.from_name("BLOCK_M"))

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        return f"symbol.dim<{self.dim.data}>"

    @classmethod
    def from_name(cls: type["SymbolDimType"], name: str) -> "SymbolDimType":
        """从名称构造 symbol.dim 类型。

        创建者: 我不是牛马
        最后一次更改: 我不是牛马

        功能说明:
        - 对名称执行规范化校验并返回类型实例。

        使用示例:
        - SymbolDimType.from_name("BLOCK_M")

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        return cls(StringAttr(_normalize_symbol_dim_name(name)))


@irdl_attr_definition
class SymbolValueType(ParametrizedAttribute, TypeAttribute):
    """仅表示整数符号值语义的类型。"""

    name = "symbol.int"

    expr: SymbolExprAttr = param_def(SymbolExprAttr)

    @classmethod
    def parse_parameters(cls: type["SymbolValueType"], parser: AttrParser) -> Sequence[Attribute]:
        """解析整数符号值类型参数。"""

        parser.parse_punctuation("<", "Expected '<' for symbol int type.")
        expr = parser.parse_str_literal("Expected quoted symbol expression.")
        parser.parse_punctuation(">", "Expected '>' for symbol int type.")
        return (SymbolExprAttr.from_expr(expr),)

    def print_parameters(self: "SymbolValueType", printer: Printer) -> None:
        """打印整数符号值类型参数。"""

        printer.print_string("<")
        printer.print_string_literal(_normalize_expr(self.expr.expr.data))
        printer.print_string(">")

    def verify(self: "SymbolValueType") -> None:
        """校验整数符号值类型。"""

        self.expr.verify()

    def __str__(self: "SymbolValueType") -> str:
        """返回公开的 symbol.int 文本表示。"""

        return f"symbol.int<{_normalize_expr(self.expr.expr.data)}>"

    def get_value(self: "SymbolValueType") -> int | str:
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
        concrete_value = _evaluate_concrete_expr(expr)
        return concrete_value if concrete_value is not None else _canonicalize_symbolic_expr(expr)

    def is_symbol(self: "SymbolValueType") -> bool:
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

        return _evaluate_concrete_expr(self.expr.expr.data) is None

    @classmethod
    def from_expr(cls: type["SymbolValueType"], expr: str) -> "SymbolValueType":
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


@irdl_attr_definition
class SymbolIterAttr(ParametrizedAttribute):
    """承载 `symbol.iter` 循环边界 attribute。"""

    name = "symbol.iter"

    start: SymbolExprAttr = param_def(SymbolExprAttr)
    end: SymbolExprAttr = param_def(SymbolExprAttr)
    step: SymbolExprAttr = param_def(SymbolExprAttr)

    @classmethod
    def parse_parameters(cls: type["SymbolIterAttr"], parser: AttrParser) -> Sequence[Attribute]:
        """解析 symbol.iter attribute 参数。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 解析 `#symbol.iter<start = "...", end = "...", step = "...">` 语法。

        使用示例:
        - SymbolIterAttr.parse_parameters(parser)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        parser.parse_punctuation("<", "Expected '<' for symbol.iter attribute.")
        parser.parse_keyword("start", " in symbol.iter attribute")
        parser.parse_characters("=", " in symbol.iter attribute")
        start = parser.parse_str_literal("Expected quoted symbol expression.")
        parser.parse_characters(",", " in symbol.iter attribute")
        parser.parse_keyword("end", " in symbol.iter attribute")
        parser.parse_characters("=", " in symbol.iter attribute")
        end = parser.parse_str_literal("Expected quoted symbol expression.")
        parser.parse_characters(",", " in symbol.iter attribute")
        parser.parse_keyword("step", " in symbol.iter attribute")
        parser.parse_characters("=", " in symbol.iter attribute")
        step = parser.parse_str_literal("Expected quoted symbol expression.")
        parser.parse_punctuation(">", "Expected '>' for symbol.iter attribute.")
        return (
            SymbolExprAttr.from_expr(start),
            SymbolExprAttr.from_expr(end),
            SymbolExprAttr.from_expr(step),
        )

    def print_parameters(self: "SymbolIterAttr", printer: Printer) -> None:
        """打印 symbol.iter attribute 参数。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 输出 `#symbol.iter<start = "...", end = "...", step = "...">` 语法。

        使用示例:
        - SymbolIterAttr.from_bounds("0", "N", "TILE_D0").print_parameters(printer)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        printer.print_string("<start = ")
        printer.print_string_literal(_normalize_expr(self.start.expr.data))
        printer.print_string(", end = ")
        printer.print_string_literal(_normalize_expr(self.end.expr.data))
        printer.print_string(", step = ")
        printer.print_string_literal(_normalize_expr(self.step.expr.data))
        printer.print_string(">")

    def verify(self: "SymbolIterAttr") -> None:
        """校验 symbol.iter attribute 参数。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 校验 start/end/step 的 symbol 表达式合法性。

        使用示例:
        - SymbolIterAttr.from_bounds("0", "N", "TILE_D0").verify()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        self.start.verify()
        self.end.verify()
        self.step.verify()

    @classmethod
    def from_bounds(cls: type["SymbolIterAttr"], start: str, end: str, step: str) -> "SymbolIterAttr":
        """从 start/end/step 字符串构造 symbol.iter attribute。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 统一构造 `#symbol.iter<start = "...", end = "...", step = "...">`。

        使用示例:
        - SymbolIterAttr.from_bounds("0", "N", "TILE_D0")

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        return cls(
            SymbolExprAttr.from_expr(start),
            SymbolExprAttr.from_expr(end),
            SymbolExprAttr.from_expr(step),
        )


@irdl_attr_definition
class SymbolIterType(ParametrizedAttribute, TypeAttribute):
    """表示循环迭代变量的 symbol 类型。"""

    name = "symbol.iter"

    start: SymbolExprAttr = param_def(SymbolExprAttr)
    end: SymbolExprAttr = param_def(SymbolExprAttr)
    step: SymbolExprAttr = param_def(SymbolExprAttr)

    @classmethod
    def parse_parameters(cls: type["SymbolIterType"], parser: AttrParser) -> Sequence[Attribute]:
        """解析循环迭代类型参数。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 解析 `!symbol.iter<start = "...", end = "...", step = "...">` 语法。
        - 兼容旧格式 `!symbol.iter<"expr">`，自动补齐 `start=0` 与 `step=1`。

        使用示例:
        - SymbolIterType.parse_parameters(parser)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        parser.parse_punctuation("<", "Expected '<' for symbol iter type.")
        if parser.parse_optional_keyword("start") is not None:
            parser.parse_characters("=", " in symbol.iter type")
            start = parser.parse_str_literal("Expected quoted symbol expression.")
            parser.parse_characters(",", " in symbol.iter type")
            parser.parse_keyword("end", " in symbol.iter type")
            parser.parse_characters("=", " in symbol.iter type")
            end = parser.parse_str_literal("Expected quoted symbol expression.")
            parser.parse_characters(",", " in symbol.iter type")
            parser.parse_keyword("step", " in symbol.iter type")
            parser.parse_characters("=", " in symbol.iter type")
            step = parser.parse_str_literal("Expected quoted symbol expression.")
            parser.parse_punctuation(">", "Expected '>' for symbol iter type.")
            return (
                SymbolExprAttr.from_expr(start),
                SymbolExprAttr.from_expr(end),
                SymbolExprAttr.from_expr(step),
            )
        expr = parser.parse_str_literal("Expected quoted symbol expression.")
        parser.parse_punctuation(">", "Expected '>' for symbol iter type.")
        return (
            SymbolExprAttr.from_expr("0"),
            SymbolExprAttr.from_expr(expr),
            SymbolExprAttr.from_expr("1"),
        )

    def print_parameters(self: "SymbolIterType", printer: Printer) -> None:
        """打印循环迭代类型参数。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 输出 `!symbol.iter<start = "...", end = "...", step = "...">` 的表达式参数。

        使用示例:
        - SymbolIterType.from_bounds("0", "N", "TILE_D0").print_parameters(printer)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        printer.print_string("<start = ")
        printer.print_string_literal(_normalize_expr(self.start.expr.data))
        printer.print_string(", end = ")
        printer.print_string_literal(_normalize_expr(self.end.expr.data))
        printer.print_string(", step = ")
        printer.print_string_literal(_normalize_expr(self.step.expr.data))
        printer.print_string(">")

    def verify(self: "SymbolIterType") -> None:
        """校验循环迭代类型参数。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 复用 symbol.expr 的合法性校验，确保 start/end/step 都合法。

        使用示例:
        - SymbolIterType.from_bounds("0", "N", "TILE_D0").verify()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        self.start.verify()
        self.end.verify()
        self.step.verify()

    def __str__(self: "SymbolIterType") -> str:
        """返回公开的 symbol.iter 文本表示。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 生成 `symbol.iter<start,end,step>` 形式的字符串表示。

        使用示例:
        - str(SymbolIterType.from_bounds("0", "N", "TILE_D0"))

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        return (
            "symbol.iter<"
            f"start={_normalize_expr(self.start.expr.data)}, "
            f"end={_normalize_expr(self.end.expr.data)}, "
            f"step={_normalize_expr(self.step.expr.data)}>"
        )

    @classmethod
    def from_bounds(cls: type["SymbolIterType"], start: str, end: str, step: str) -> "SymbolIterType":
        """从 start/end/step 构造循环迭代类型。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 统一创建 `!symbol.iter<start = "...", end = "...", step = "...">`。

        使用示例:
        - SymbolIterType.from_bounds("0", "N", "TILE_D0")

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        return cls(
            SymbolExprAttr.from_expr(start),
            SymbolExprAttr.from_expr(end),
            SymbolExprAttr.from_expr(step),
        )

    @classmethod
    def from_attr(cls: type["SymbolIterType"], attr: SymbolIterAttr) -> "SymbolIterType":
        """从 symbol.iter attribute 构造循环迭代类型。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 将 `#symbol.iter<...>` 转换为对应的 `!symbol.iter<...>` 类型。

        使用示例:
        - SymbolIterType.from_attr(SymbolIterAttr.from_bounds("0", "N", "TILE_D0"))

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        return cls(attr.start, attr.end, attr.step)

    @classmethod
    def from_expr(cls: type["SymbolIterType"], expr: str) -> "SymbolIterType":
        """从字符串构造循环迭代类型（legacy 语义）。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 兼容旧的 `!symbol.iter<"expr">` 语义，补齐 `start=0` 与 `step=1`。

        使用示例:
        - SymbolIterType.from_expr("index")

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        return cls.from_bounds("0", expr, "1")


@irdl_attr_definition
class SymbolPtrType(ParametrizedAttribute, TypeAttribute):
    """符号指针类型。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 表示 `!symbol.ptr<dtype>` 的指针类型承载。
    - 作为 DSL `Ptr(dtype)` 与 IR 类型的唯一桥接入口。

    使用示例:
    - SymbolPtrType(f32)

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol_dialect.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    name = "symbol.ptr"

    dtype: Attribute = param_def(Attribute)

    @classmethod
    def parse_parameters(cls: type["SymbolPtrType"], parser: AttrParser) -> Sequence[Attribute]:
        """解析 symbol.ptr 类型参数。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 解析 `!symbol.ptr<dtype>` 中的 dtype。

        使用示例:
        - SymbolPtrType.parse_parameters(parser)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        parser.parse_punctuation("<", "Expected '<' for symbol ptr type.")
        dtype = parser.parse_type()
        parser.parse_punctuation(">", "Expected '>' for symbol ptr type.")
        return (dtype,)

    def print_parameters(self: "SymbolPtrType", printer: Printer) -> None:
        """打印 symbol.ptr 类型参数。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 输出 `!symbol.ptr<dtype>` 的 dtype 部分。

        使用示例:
        - SymbolPtrType(f32).print_parameters(printer)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        printer.print_string("<")
        printer.print_attribute(self.dtype)
        printer.print_string(">")

    def verify(self: "SymbolPtrType") -> None:
        """校验 symbol.ptr 的 dtype。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 要求 dtype 为合法 TypeAttribute。
        - 明确拒绝 `!symbol.int<...>` 作为 ptr dtype。

        使用示例:
        - SymbolPtrType(f32).verify()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        if not isinstance(self.dtype, TypeAttribute):
            _raise_verify_error("symbol.ptr dtype must be type")
        if isinstance(self.dtype, SymbolValueType):
            _raise_verify_error("symbol.ptr dtype must not be symbol.int")


class _BaseSymbolBinaryArithOp(IRDLOperation, HasFolderInterface):
    """symbol 二元整数算术 op 基类。"""

    lhs = operand_def(Attribute)
    rhs = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(
        self: "_BaseSymbolBinaryArithOp",
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

    def verify_(self: "_BaseSymbolBinaryArithOp") -> None:
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
                _raise_verify_error(f"{self.name} {field_name} must have type !symbol.int<\"expr\">")
        if not _is_symbol_int_type(self.result.type):
            _raise_verify_error(f"{self.name} result type must be !symbol.int<\"expr\">")

    def fold(self: "_BaseSymbolBinaryArithOp") -> Sequence[SSAValue | Attribute] | None:
        """折叠静态整数 symbol 二元算术 op。

        创建者: jcc你莫辜负
        最后一次更改: jcc你莫辜负

        功能说明:
        - 仅当 lhs/rhs/result 都是静态整数 `!symbol.int` 时折叠。
        - 动态 symbol 表达一律保守返回 `None`，避免误折叠。

        使用示例:
        - SymbolAddOp(SymbolConstOp(1).result, SymbolConstOp(2).result, SymbolValueType.from_expr("3")).fold()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        lhs_value = _get_concrete_symbol_int_value(SSAValue.get(self.lhs).type)
        rhs_value = _get_concrete_symbol_int_value(SSAValue.get(self.rhs).type)
        result_type = SSAValue.get(self.result).type
        if lhs_value is None or rhs_value is None or not isinstance(result_type, SymbolValueType):
            return None

        if self.name == "symbol.add":
            result_value = lhs_value + rhs_value
        elif self.name == "symbol.sub":
            result_value = lhs_value - rhs_value
        elif self.name == "symbol.mul":
            result_value = lhs_value * rhs_value
        elif self.name == "symbol.div":
            if rhs_value == 0 or lhs_value % rhs_value != 0:
                return None
            result_value = lhs_value // rhs_value
        elif self.name == "symbol.floordiv":
            if rhs_value == 0:
                return None
            result_value = lhs_value // rhs_value
        else:
            return None

        if result_type.get_value() != result_value:
            return None
        return (IntAttr(result_value),)

    def print(self: "_BaseSymbolBinaryArithOp", printer: Printer) -> None:
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
    def parse(cls: type["_BaseSymbolBinaryArithOp"], parser: AttrParser) -> "_BaseSymbolBinaryArithOp":
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
        self: "_BaseSymbolCompareOp",
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

    def verify_(self: "_BaseSymbolCompareOp") -> None:
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
                _raise_verify_error(f"{self.name} {field_name} must have type !symbol.int<\"expr\">")
        if self.result.type != i1:
            _raise_verify_error(f"{self.name} result type must be i1")

    def print(self: "_BaseSymbolCompareOp", printer: Printer) -> None:
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
    def parse(cls: type["_BaseSymbolCompareOp"], parser: AttrParser) -> "_BaseSymbolCompareOp":
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
class SymbolConstOp(IRDLOperation):
    """创建 symbol.int 常量。"""

    name = "symbol.const"

    value = attr_def(IntAttr)
    result = result_def(SymbolValueType)

    def __init__(
        self: "SymbolConstOp",
        value: int | IntAttr,
        result_type: SymbolValueType | None = None,
    ) -> None:
        """初始化 symbol.const。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 记录整数常量 attribute，并生成对应的 `!symbol.int<"...">` 结果类型。

        使用示例:
        - SymbolConstOp(3)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        value_attr = value if isinstance(value, IntAttr) else IntAttr(value)
        inferred_type = result_type or SymbolValueType.from_expr(str(value_attr.data))
        super().__init__(result_types=[inferred_type], attributes={"value": value_attr})

    def verify_(self: "SymbolConstOp") -> None:
        """校验 symbol.const 的类型约束。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 校验 value 必须为整型 attribute。
        - 校验 result 必须是 `!symbol.int<"...">`，且表达式与常量值一致。

        使用示例:
        - SymbolConstOp(3).verify_()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        if not isinstance(self.value, IntAttr):
            _raise_verify_error(f"{self.name} value must be integer attribute")
        if not isinstance(self.result.type, SymbolValueType):
            _raise_verify_error(f"{self.name} result type must be !symbol.int<\"expr\">")
        expected_type = SymbolValueType.from_expr(str(self.value.data))
        if self.result.type != expected_type:
            _raise_verify_error(f"{self.name} result type must match value")

    def print(self: "SymbolConstOp", printer: Printer) -> None:
        """打印 symbol.const 自定义文本语法。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 输出 `symbol.const <value> : !symbol.int<"...">` 的文本形式。

        使用示例:
        - SymbolConstOp(3)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        printer.print_string(" ")
        printer.print_string(str(self.value.data))
        printer.print_string(" : ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls: type["SymbolConstOp"], parser: AttrParser) -> "SymbolConstOp":
        """解析 symbol.const 自定义文本语法。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 解析整数常量与 `!symbol.int<"...">` 结果类型。

        使用示例:
        - SymbolConstOp.parse(parser)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        value = parser.parse_integer(allow_boolean=False, allow_negative=True, context_msg=f" in {cls.name}")
        parser.parse_characters(":", f" in {cls.name}")
        result_type = parser.parse_type()
        return cls(value, result_type)


class SymbolConstantMaterializationInterface(ConstantMaterializationInterface):
    """将 folded 整数属性 materialize 回 symbol.const。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 仅接受与 `SymbolValueType` 一致的静态整数常量。
    - 为 xdsl folding 提供 `symbol.const` 物化入口，不新增独立 cleanup pass。

    使用示例:
    - SymbolConstantMaterializationInterface().materialize_constant(IntAttr(3), SymbolValueType.from_expr("3"))

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol_dialect.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    def materialize_constant(self, value: Attribute, type: Attribute) -> Operation | None:
        """把整数常量 materialize 为 `symbol.const`。"""

        if not isinstance(value, IntAttr):
            return None
        if not isinstance(type, SymbolValueType):
            return None
        if type.get_value() != value.data:
            return None
        return SymbolConstOp(value, type)


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
class SymbolDivOp(_BaseSymbolBinaryArithOp):
    """两个 symbol.int 值的符号除法。"""

    name = "symbol.div"


@irdl_op_definition
class SymbolFloorDivOp(_BaseSymbolBinaryArithOp):
    """两个 symbol.int 值的符号整除。"""

    name = "symbol.floordiv"


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


@irdl_op_definition
class SymbolToFloatOp(IRDLOperation):
    """将 symbol.int 标量转换为 f32。"""

    name = "symbol.to_float"

    source = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(
        self: "SymbolToFloatOp",
        source: SSAValue | Operation,
        result_type: Attribute = f32,
    ) -> None:
        """初始化 symbol.to_float。

        创建者: 我不是牛马
        最后一次更改: 小李飞刀

        功能说明:
        - 设置单个 `!symbol.int<"expr">` 操作数与浮点结果类型。

        使用示例:
        - SymbolToFloatOp(source, f32)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        super().__init__(operands=[source], result_types=[result_type])

    def verify_(self: "SymbolToFloatOp") -> None:
        """校验 symbol.to_float 的类型约束。

        创建者: 我不是牛马
        最后一次更改: 小李飞刀

        功能说明:
        - 校验 source 必须为 `!symbol.int<"expr">`。
        - 校验 result 必须为浮点类型。

        使用示例:
        - SymbolToFloatOp(source, f32).verify_()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        source_value = SSAValue.get(self.source)
        if not _is_symbol_int_type(source_value.type):
            _raise_verify_error(f"{self.name} source must have type !symbol.int<\"expr\">")
        if not isinstance(self.result.type, (Float16Type, BFloat16Type, Float32Type, Float64Type)):
            _raise_verify_error(f"{self.name} result type must be float")

    def print(self: "SymbolToFloatOp", printer: Printer) -> None:
        """打印 symbol.to_float 自定义文本语法。"""

        printer.print_string(" ")
        printer.print_ssa_value(self.source)
        printer.print_string(" : ")
        printer.print_attribute(SSAValue.get(self.source).type)
        printer.print_string(" -> ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls: type["SymbolToFloatOp"], parser: AttrParser) -> "SymbolToFloatOp":
        """解析 symbol.to_float 自定义文本语法。"""

        unresolved_source = parser.parse_unresolved_operand()
        parser.parse_characters(":", f" in {cls.name}")
        source_type = parser.parse_type()
        parser.parse_characters("->", f" in {cls.name}")
        result_type = parser.parse_type()
        source = parser.resolve_operand(unresolved_source, source_type)
        return cls(source, result_type)


@irdl_op_definition
class SymbolToIntOp(IRDLOperation):
    """将 symbol.int 标量转换为普通整型。"""

    name = "symbol.to_int"

    source = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(
        self: "SymbolToIntOp",
        source: SSAValue | Operation,
        result_type: Attribute = i32,
    ) -> None:
        """初始化 symbol.to_int。

        创建者: 摸鱼小分队
        最后一次更改: 摸鱼小分队

        功能说明:
        - 设置单个 `!symbol.int<"expr">` 操作数与普通整型结果类型。

        使用示例:
        - SymbolToIntOp(source, i32)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        super().__init__(operands=[source], result_types=[result_type])

    def verify_(self: "SymbolToIntOp") -> None:
        """校验 symbol.to_int 的类型约束。

        创建者: 摸鱼小分队
        最后一次更改: 摸鱼小分队

        功能说明:
        - 校验 source 必须为 `!symbol.int<"expr">`。
        - 校验 result 必须为 builtin 整型（`IntegerType`）。

        使用示例:
        - SymbolToIntOp(source, i32).verify_()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        source_value = SSAValue.get(self.source)
        if not _is_symbol_int_type(source_value.type):
            _raise_verify_error(f"{self.name} source must have type !symbol.int<\"expr\">")
        if not isinstance(self.result.type, IntegerType):
            _raise_verify_error(f"{self.name} result type must be integer")

    def print(self: "SymbolToIntOp", printer: Printer) -> None:
        """打印 symbol.to_int 自定义文本语法。"""

        printer.print_string(" ")
        printer.print_ssa_value(self.source)
        printer.print_string(" : ")
        printer.print_attribute(SSAValue.get(self.source).type)
        printer.print_string(" -> ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls: type["SymbolToIntOp"], parser: AttrParser) -> "SymbolToIntOp":
        """解析 symbol.to_int 自定义文本语法。"""

        unresolved_source = parser.parse_unresolved_operand()
        parser.parse_characters(":", f" in {cls.name}")
        source_type = parser.parse_type()
        parser.parse_characters("->", f" in {cls.name}")
        result_type = parser.parse_type()
        source = parser.resolve_operand(unresolved_source, source_type)
        return cls(source, result_type)


@irdl_op_definition
class SymbolCastOp(IRDLOperation):
    """将 symbol.int 标量转换为普通整型。"""

    name = "symbol.cast"

    source = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(
        self: "SymbolCastOp",
        source: SSAValue | Operation,
        result_type: Attribute = i32,
    ) -> None:
        """初始化 symbol.cast。

        创建者: jcc你莫辜负
        最后修改人: jcc你莫辜负

        功能说明:
        - 设置单个 `!symbol.int<"expr">` 操作数与普通整型结果类型。
        - 供 `emit_c/npu_demo` 读取 `symbol.cast` 文本输入。

        使用示例:
        - SymbolCastOp(source, i32)

        关联文件:
        - spec: spec/dsl/gen_kernel/emit.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        super().__init__(operands=[source], result_types=[result_type])

    def verify_(self: "SymbolCastOp") -> None:
        """校验 symbol.cast 的类型约束。

        创建者: jcc你莫辜负
        最后修改人: jcc你莫辜负

        功能说明:
        - 校验 source 必须为 `!symbol.int<"expr">`。
        - 校验 result 必须为 builtin 整型。

        使用示例:
        - SymbolCastOp(source, i32).verify_()

        关联文件:
        - spec: spec/dsl/gen_kernel/emit.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """
        source_value = SSAValue.get(self.source)
        if not _is_symbol_int_type(source_value.type):
            _raise_verify_error(f"{self.name} source must have type !symbol.int<\"expr\">")
        if not isinstance(self.result.type, IntegerType):
            _raise_verify_error(f"{self.name} result type must be integer")

    def print(self: "SymbolCastOp", printer: Printer) -> None:
        """打印 symbol.cast 自定义文本语法。"""
        printer.print_string(" ")
        printer.print_ssa_value(self.source)
        printer.print_string(" : ")
        printer.print_attribute(SSAValue.get(self.source).type)
        printer.print_string(" -> ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls: type["SymbolCastOp"], parser: AttrParser) -> "SymbolCastOp":
        """解析 symbol.cast 自定义文本语法。"""
        unresolved_source = parser.parse_unresolved_operand()
        parser.parse_characters(":", f" in {cls.name}")
        source_type = parser.parse_type()
        parser.parse_characters("->", f" in {cls.name}")
        result_type = parser.parse_type()
        source = parser.resolve_operand(unresolved_source, source_type)
        return cls(source, result_type)


class _BaseSymbolMemoryQueryOp(IRDLOperation):
    """memory 元信息查询 op 基类。"""

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

    def verify_(self: "_BaseSymbolMemoryQueryOp") -> None:
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
            _raise_verify_error(f"{self.name} source must be nn.memory")
        source_type.verify()
        entries = source_type.shape.data if self.FIELD_NAME == "shape" else source_type.stride.data
        axis = _verify_axis(self.axis, len(entries), self.name)
        expected = SymbolValueType.from_expr(_entry_to_expr(entries[axis], self.name, self.FIELD_NAME))
        if self.result.type != expected:
            _raise_verify_error(f"{self.name} result type must match source {self.FIELD_NAME} entry")


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
class SymbolYieldOp(IRDLOperation):
    """承载 symbol.for 单个 carried `!symbol.int<"...">` 的循环末尾值。"""

    name = "symbol.yield"

    value = operand_def(Attribute)
    traits = traits_def(IsTerminator())

    def __init__(self: "SymbolYieldOp", value: SSAValue | Operation) -> None:
        """初始化 symbol.yield。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 构造仅承载一个 `!symbol.int<"...">` operand 的 terminator。
        - 该 op 只服务带 carried-value 的 `symbol.for` 循环体。

        使用示例:
        - SymbolYieldOp(value)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        super().__init__(operands=[value])

    def verify_(self: "SymbolYieldOp") -> None:
        """校验 symbol.yield 只能在 carried symbol.for 末尾使用。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 要求 `value` 类型固定为 `!symbol.int<"...">`。
        - 要求当前 op 位于带单个 carried `!symbol.int<"...">` 的 `symbol.for` 单块 region 末尾。

        使用示例:
        - SymbolYieldOp(value).verify()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        if not _is_symbol_int_type(SSAValue.get(self.value).type):
            _raise_verify_error(f'{self.name} value must have type !symbol.int<"expr">')

        parent_op = self.parent_op()
        if not isinstance(parent_op, SymbolForOp):
            _raise_verify_error(f"{self.name} must appear inside symbol.for")
        if parent_op.init is None or parent_op.result is None:
            _raise_verify_error(f'{self.name} requires symbol.for loop-carried !symbol.int<"expr">')

        parent_block = self.parent_block()
        if parent_block is None or parent_block.last_op is not self:
            _raise_verify_error(f"{self.name} must terminate symbol.for body")

    def print(self: "SymbolYieldOp", printer: Printer) -> None:
        """打印 symbol.yield 自定义文本语法。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 输出 `symbol.yield %value : !symbol.int<"...">` 形式文本。

        使用示例:
        - SymbolYieldOp(value).print(printer)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        printer.print_string(" ")
        printer.print_ssa_value(self.value)
        printer.print_string(" : ")
        printer.print_attribute(SSAValue.get(self.value).type)

    @classmethod
    def parse(cls: type["SymbolYieldOp"], parser: AttrParser) -> "SymbolYieldOp":
        """解析 symbol.yield 自定义文本语法。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 解析 `symbol.yield %value : !symbol.int<"...">`。
        - 在解析阶段把 unresolved operand 解析为具体验证类型，保持 print 后再 parse 闭环。

        使用示例:
        - SymbolYieldOp.parse(parser)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        value = parser.parse_unresolved_operand()
        parser.parse_characters(":", f" in {cls.name}")
        value_type = parser.parse_type()
        value = parser.resolve_operand(value, value_type)
        return cls(value)


@irdl_op_definition
class SymbolForOp(IRDLOperation):
    """以 symbol.int 边界驱动的半开区间循环。"""

    name = "symbol.for"

    start = operand_def(Attribute)
    end = operand_def(Attribute)
    step = operand_def(Attribute)
    init = opt_operand_def(Attribute)
    iter_attr = attr_def(SymbolIterAttr, attr_name="iter")
    body = region_def()
    result = opt_result_def(Attribute)
    traits = traits_def(NoTerminator())

    def __init__(
        self: "SymbolForOp",
        start: SSAValue | Operation,
        end: SSAValue | Operation,
        step: SSAValue | Operation,
        body: Region | Block | Sequence[Operation] | Sequence[Block],
        iter_attr: SymbolIterAttr | None = None,
        init: SSAValue | Operation | None = None,
        result_type: Attribute | None = None,
    ) -> None:
        """初始化 symbol.for。

        创建者: 我不是牛马
        最后一次更改: 金铲铲大作战

        功能说明:
        - 设置 `start/end/step` 三个 `!symbol.int<"...">` 操作数与单块循环体。
        - 兼容旧的无 carried-value 形式，也支持通过 `init` 构造单个 loop-carried `!symbol.int<"...">` 结果。
        - `iter` attribute 与块参数类型共同表达迭代边界语义。

        使用示例:
        - SymbolForOp(start, end, step, Block(arg_types=[SymbolIterType.from_bounds("0", "M", "TILE_D0")]))
        - SymbolForOp(start, end, step, Block(arg_types=[SymbolIterType.from_bounds("0", "M", "TILE_D0"), SymbolValueType.from_expr("ACC")]), init=zero, result_type=SymbolValueType.from_expr("TOTAL"))

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        if isinstance(body, Block):
            body = Region(body)
        elif not isinstance(body, Region):
            body = Region(list(body))
        if iter_attr is None:
            start_type = SSAValue.get(start).type
            end_type = SSAValue.get(end).type
            step_type = SSAValue.get(step).type
            if isinstance(start_type, SymbolValueType) and isinstance(end_type, SymbolValueType) and isinstance(step_type, SymbolValueType):
                iter_attr = SymbolIterAttr.from_bounds(
                    _normalize_expr(start_type.expr.expr.data),
                    _normalize_expr(end_type.expr.expr.data),
                    _normalize_expr(step_type.expr.expr.data),
                )
            else:
                iter_attr = SymbolIterAttr.from_bounds("0", "0", "1")
        super().__init__(
            operands=[start, end, step, [] if init is None else [init]],
            regions=[body],
            result_types=[[] if init is None else [result_type or SSAValue.get(init).type]],
            attributes={"iter": iter_attr},
        )

    def verify_(self: "SymbolForOp") -> None:
        """校验 symbol.for 约束。

        创建者: 我不是牛马
        最后一次更改: 金铲铲大作战

        功能说明:
        - 校验 start/end/step 均为 `!symbol.int<\"expr\">`。
        - 校验 `iter` attribute 与 block 参数类型一致。
        - 校验 region 为单块；无 carried-value 时仅包含 `it` 一个块参数，带 carried-value 时包含 `it/acc` 两个块参数。
        - 校验 loop-carried `!symbol.int<"...">` 的 `init/result/symbol.yield` 口径与 terminator 形状。
        - 当 step 可静态判定为 `0` 时直接报错。

        使用示例:
        - SymbolForOp(start, end, step, body).verify_()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        start_value = SSAValue.get(self.start)
        end_value = SSAValue.get(self.end)
        step_value = SSAValue.get(self.step)
        for operand_name, operand in (("start", start_value), ("end", end_value), ("step", step_value)):
            if not _is_symbol_int_type(operand.type):
                _raise_verify_error(f"{self.name} {operand_name} must have type !symbol.int<\"expr\">")

        step_type = step_value.type
        assert isinstance(step_type, SymbolValueType)
        step_expr = _normalize_expr(step_type.expr.expr.data)
        if step_expr == "0":
            _raise_verify_error(f"{self.name} step must not be zero")

        blocks = list(self.body.blocks)
        if len(blocks) != 1:
            _raise_verify_error(f"{self.name} only supports single-block regions")
        block = blocks[0]
        carried_init = self.init
        carried_result = self.result
        has_carried = carried_init is not None or carried_result is not None
        if carried_init is None and carried_result is not None:
            _raise_verify_error(f'{self.name} loop-carried !symbol.int<"expr"> requires init operand')
        if carried_init is not None and carried_result is None:
            _raise_verify_error(f'{self.name} loop-carried !symbol.int<"expr"> requires single symbol.int result')
        expected_block_args = 2 if has_carried else 1
        if len(block.args) != expected_block_args:
            if has_carried:
                _raise_verify_error(f'{self.name} loop-carried !symbol.int<"expr"> requires exactly two block arguments')
            _raise_verify_error(f"{self.name} body must have exactly one block argument")
        iter_arg = block.args[0]
        if not isinstance(iter_arg.type, SymbolIterType):
            _raise_verify_error(f"{self.name} it must have type !symbol.iter<...>")
        iter_attr = self.iter_attr
        if not isinstance(iter_attr, SymbolIterAttr):
            _raise_verify_error(f"{self.name} iter attribute must be #symbol.iter<...>")
        start_expr = _normalize_expr(start_value.type.expr.expr.data)
        end_expr = _normalize_expr(end_value.type.expr.expr.data)
        if _normalize_expr(iter_attr.start.expr.data) != start_expr:
            _raise_verify_error(f"{self.name} iter.start must match start operand")
        if _normalize_expr(iter_attr.end.expr.data) != end_expr:
            _raise_verify_error(f"{self.name} iter.end must match end operand")
        if _normalize_expr(iter_attr.step.expr.data) != step_expr:
            _raise_verify_error(f"{self.name} iter.step must match step operand")
        expected_iter_type = SymbolIterType.from_attr(iter_attr)
        if iter_arg.type != expected_iter_type:
            _raise_verify_error(f"{self.name} it must have type {expected_iter_type}")
        if not has_carried:
            return

        if not _is_symbol_int_type(carried_init.type):
            _raise_verify_error(f'{self.name} loop-carried init must have type !symbol.int<"expr">')
        if not _is_symbol_int_type(block.args[1].type):
            _raise_verify_error(f'{self.name} loop-carried acc must have type !symbol.int<"expr">')
        if not _is_symbol_int_type(carried_result.type):
            _raise_verify_error(f'{self.name} loop-carried result must have type !symbol.int<"expr">')

        terminator = block.last_op
        if not isinstance(terminator, SymbolYieldOp):
            _raise_verify_error(f"{self.name} loop-carried body must terminate with symbol.yield")
        if not _is_symbol_int_type(SSAValue.get(terminator.value).type):
            _raise_verify_error(f'{self.name} loop-carried yield must have type !symbol.int<"expr">')

    def print(self: "SymbolForOp", printer: Printer) -> None:
        """打印 symbol.for 自定义文本语法。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 无 carried-value 时输出旧文本语法。
        - 带 carried-value 时输出 `iter_args(%acc = %init) {iter = ...} -> !symbol.int<"..."> { ... }`，与 parser 使用同一公开顺序。

        使用示例:
        - SymbolForOp(start, end, step, body, init=zero).print(printer)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        blocks = list(self.body.blocks)
        has_carried = self.init is not None and self.result is not None
        if len(blocks) != 1 or len(blocks[0].args) != (2 if has_carried else 1):
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
        if has_carried:
            printer.print_string(" iter_args(")
            printer.print_ssa_value(block.args[1])
            printer.print_string(" = ")
            printer.print_ssa_value(self.init)
            printer.print_string(")")
        printer.print_string(" {iter = ")
        printer.print_attribute(self.iter_attr)
        printer.print_string("}")
        if has_carried:
            printer.print_string(" -> ")
            printer.print_attribute(self.result.type)
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
    def parse(cls: type["SymbolForOp"], parser: AttrParser) -> "SymbolForOp":
        """解析 symbol.for 自定义文本语法。

        创建者: 我不是牛马
        最后一次更改: 金铲铲大作战

        功能说明:
        - 解析旧的 `symbol.for %it = %start to %end step %step {iter = #symbol.iter<...>} { ... }`。
        - 解析新的 `symbol.for %it = %start to %end step %step iter_args(%acc = %zero) {iter = #symbol.iter<...>} -> !symbol.int<"..."> { ... }`。
        - 迭代变量与 carried `acc` 都在进入 region 前完成类型解析，保持 print 后再 parse 闭环。

        使用示例:
        - SymbolForOp.parse(parser)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol_dialect.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        unresolved_iter = parser.parse_argument(expect_type=False)
        parser.parse_characters("=", " in symbol.for")
        start_value = parser.parse_operand()
        parser.parse_characters("to", " in symbol.for")
        end_value = parser.parse_operand()
        parser.parse_characters("step", " in symbol.for")
        step_value = parser.parse_operand()
        init_value = None
        acc_arg = None
        if parser.parse_optional_keyword("iter_args") is not None:
            parser.parse_punctuation("(", " in symbol.for")
            unresolved_acc = parser.parse_argument(expect_type=False)
            parser.parse_characters("=", " in symbol.for")
            init_value = parser.parse_operand()
            parser.parse_punctuation(")", " in symbol.for")
        parser.parse_characters("{", " in symbol.for")
        parser.parse_keyword("iter", " in symbol.for")
        parser.parse_characters("=", " in symbol.for")
        iter_attr = parser.parse_attribute()
        if not isinstance(iter_attr, SymbolIterAttr):
            raise VerifyException(_format_error("symbol.for iter attribute must be #symbol.iter<...>"))
        parser.parse_characters("}", " in symbol.for")
        iter_arg = unresolved_iter.resolve(SymbolIterType.from_attr(iter_attr))
        result_type = None
        if parser.parse_optional_characters("->") is not None:
            result_type = parser.parse_type()
        if init_value is None and result_type is not None:
            raise VerifyException(_format_error('symbol.for result type requires loop-carried !symbol.int<"expr">'))
        if init_value is not None:
            if not isinstance(result_type, SymbolValueType):
                raise VerifyException(_format_error('symbol.for loop-carried result must be !symbol.int<"expr">'))
            acc_arg = unresolved_acc.resolve(result_type)
        block_args = (iter_arg,) if acc_arg is None else (iter_arg, acc_arg)
        body = parser.parse_region(block_args)
        op = cls(start_value, end_value, step_value, body, iter_attr, init=init_value, result_type=result_type)
        return op


Symbol = Dialect(
    "symbol",
    [
        SymbolConstOp,
        SymbolAddOp,
        SymbolSubOp,
        SymbolMulOp,
        SymbolDivOp,
        SymbolFloorDivOp,
        SymbolEqOp,
        SymbolNeOp,
        SymbolLtOp,
        SymbolLeOp,
        SymbolGtOp,
        SymbolGeOp,
        SymbolCastOp,
        SymbolToIntOp,
        SymbolToFloatOp,
        SymbolGetDimOp,
        SymbolGetStrideOp,
        SymbolYieldOp,
        SymbolForOp,
    ],
    [
        SymbolExprAttr,
        SymbolDimType,
        SymbolPtrType,
        SymbolIterAttr,
        SymbolIterType,
        SymbolValueType,
    ],
    [
        SymbolConstantMaterializationInterface(),
    ],
)

__all__ = [
    "Symbol",
    "SymbolAddOp",
    "SymbolCastOp",
    "SymbolConstOp",
    "SymbolDivOp",
    "SymbolDimType",
    "SymbolEqOp",
    "SymbolExprAttr",
    "SymbolGeOp",
    "SymbolGetDimOp",
    "SymbolMulOp",
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
