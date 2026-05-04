"""Symbol dialect definitions.


功能说明:
- 定义仅表示整数符号值语义的 symbol dialect。
- 提供 `SymbolExprAttr`、`SymbolValueType`、`SymbolDimType`、`SymbolIterAttr`、`SymbolIterType`、`symbol.add/sub/mul/div/floordiv/min`、`symbol.eq/ne/lt/le/gt/ge`、`symbol.to_int/symbol.to_float`、`symbol.get_dim/get_stride`，以及带单个 loop-carried `!symbol.int<#symbol.expr<...>>` 的 `symbol.for` / `symbol.yield`。
- `symbol.for` 同时兼容无 carried-value 形式和新的 `iter_args(%acc = %zero) ... -> !symbol.int<#symbol.expr<...>>` 文本语法。
- 在导入 sympy 前设置 `SYMPY_GMPY=0`，规避外部 gmpy 引发的 SystemError。

API 列表:
- `class SymbolExprAttr(expr: StringAttr)`
- `SymbolExprAttr.from_expr(expr: str) -> SymbolExprAttr`
- `class SymbolDimType(dim: StringAttr)`
- `SymbolDimType.from_name(name: str) -> SymbolDimType`
- `class SymbolValueType(expr: SymbolExprAttr)`
- `SymbolValueType.from_expr(expr: str) -> SymbolValueType`
- `SymbolValueType.get_value(self) -> int | str`
- `SymbolValueType.is_symbol(self) -> bool`
- `class SymbolIterAttr(start: SymbolExprAttr, end: SymbolExprAttr, step: SymbolExprAttr)`
- `SymbolIterAttr.from_bounds(start: str, end: str, step: str) -> SymbolIterAttr`
- `class SymbolIterType(start: SymbolExprAttr, end: SymbolExprAttr, step: SymbolExprAttr)`
- `SymbolIterType.from_bounds(start: str, end: str, step: str) -> SymbolIterType`
- `SymbolIterType.from_attr(attr: SymbolIterAttr) -> SymbolIterType`
- `class SymbolPtrType(dtype: Attribute)`
- `class SymbolConstOp(value: int | IntAttr, result_type: SymbolValueType | None = None)`
- `class SymbolAddOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- `class SymbolSubOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- `class SymbolMulOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- `class SymbolDivOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- `class SymbolFloorDivOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- `class SymbolMinOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- `class SymbolEqOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- `class SymbolNeOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- `class SymbolLtOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- `class SymbolLeOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- `class SymbolGtOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- `class SymbolGeOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- `class SymbolToFloatOp(value: SSAValue, result_type: Attribute)`
- `class SymbolToIntOp(value: SSAValue, result_type: Attribute)`
- `class SymbolCastOp(value: SSAValue, result_type: Attribute)`
- `class SymbolGetDimOp(memory: SSAValue, index: int | IntAttr)`
- `class SymbolGetStrideOp(memory: SSAValue, index: int | IntAttr)`
- `class SymbolYieldOp(value: SSAValue | Operation)`
- `class SymbolForOp(start: SSAValue | Operation, end: SSAValue | Operation, step: SSAValue | Operation, body: Region | Block | Sequence[Operation] | Sequence[Block], iter_attr: SymbolIterAttr | None = None, init: SSAValue | Operation | None = None, result_type: Attribute | None = None)`
- `Symbol`

使用示例:
- from kernel_gen.dialect.symbol import Symbol, SymbolAddOp, SymbolConstOp, SymbolDivOp, SymbolEqOp, SymbolFloorDivOp, SymbolForOp, SymbolYieldOp, SymbolSubOp, SymbolMulOp, SymbolMinOp, SymbolToIntOp, SymbolExprAttr, SymbolGetDimOp, SymbolGetStrideOp, SymbolValueType

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/test_symbol.py
- 功能实现: kernel_gen/dialect/symbol.py
"""

from __future__ import annotations

import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE
os.environ.setdefault("SYMPY_GMPY", "0")
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

_SYMBOL_DIM_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SYMBOL_EXPR_TOKEN_PATTERN = re.compile(
    r"\s*(?:(?P<int>[0-9]+)|(?P<ident>[A-Za-z_][A-Za-z0-9_]*)|(?P<punct>[()+\-*,?])|(?P<invalid>.))",
    re.DOTALL,
)
_ERROR_SCENE = "dialect.symbol"
_UNKNOWN_SYMBOL_EXPR = "?"
_SYMBOL_EXPR_EXPR_PRECEDENCE = 10
_SYMBOL_EXPR_TERM_PRECEDENCE = 20
_SYMBOL_EXPR_UNARY_PRECEDENCE = 30
_SYMBOL_EXPR_ATOM_PRECEDENCE = 40


def _format_error(expected: str, actual: str = ERROR_ACTUAL) -> str:
    return ERROR_TEMPLATE.format(
        scene=_ERROR_SCENE,
        expected=expected,
        actual=actual,
        action=ERROR_ACTION,
    )


def _raise_verify_error(expected: str, *, actual: str = ERROR_ACTUAL) -> None:
    """统一抛出 symbol dialect verifier 错误。"""

    raise VerifyException(_format_error(expected, actual))


def _raise_value_error(expected: str, *, actual: str = ERROR_ACTUAL) -> None:
    """统一抛出 symbol dialect value error。"""

    raise ValueError(_format_error(expected, actual))


def _raise_type_error(expected: str, *, actual: str = ERROR_ACTUAL) -> None:
    """统一抛出 symbol dialect type error。"""

    raise TypeError(_format_error(expected, actual))


def _normalize_symbol_dim_name(name: str) -> str:
    """规范化 symbol.dim 名称。


    功能说明:
    - 去除首尾空白并校验名称合法性。
    - 确保名称满足标识符格式 `[A-Za-z_][A-Za-z0-9_]*`。

    使用示例:
    - _normalize_symbol_dim_name("BLOCK_M")

    关联文件:
    - spec: spec/dialect/tuner.md
    - test: test/dialect/test_tuner.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    normalized = name.strip()
    if not normalized:
        _raise_verify_error("symbol dim name must not be empty")
    if _SYMBOL_DIM_NAME_PATTERN.fullmatch(normalized) is None:
        _raise_verify_error("symbol dim name must match [A-Za-z_][A-Za-z0-9_]*")
    return normalized


@dataclass(frozen=True)
class _SymbolExprNode:
    """当前文件内的 symbol 表达式 AST 节点。

    功能说明:
    - 保存 `SymbolExprAttr` canonicalize 所需的最小表达式结构。
    - 只在 `kernel_gen.dialect.symbol` 内使用，不作为公开 API。

    使用示例:
    - _SymbolExprNode("symbol", value="N")
    """

    kind: str
    value: int | str | None = None
    args: tuple["_SymbolExprNode", ...] = ()


@dataclass(frozen=True)
class _SymbolExprToken:
    """当前文件内的 symbol 表达式字符串 token。

    功能说明:
    - 服务 `SymbolExprAttr.from_expr(...)` 的纯文本解析。
    - 不暴露给其它模块或测试。

    使用示例:
    - _SymbolExprToken("ident", "N")
    """

    kind: str
    text: str


class _SymbolExprParserBase:
    """当前文件内共享的 symbol 表达式递归下降 parser。

    功能说明:
    - 为字符串构造入口与 xDSL attribute parser 入口复用同一语法与 canonical 规则。
    - 支持 `+`、`-`、`*`、`floordiv`、`ceildiv`、`mod`、`min(lhs, rhs)`、`max(lhs, rhs)`、括号与 `?`。

    使用示例:
    - _SymbolExprTextParser("N floordiv 2").parse_all()
    """

    def parse_expression(self: "_SymbolExprParserBase") -> _SymbolExprNode:
        """解析最低优先级表达式。

        功能说明:
        - 解析加法与减法，并把结果交给 canonical builder。

        使用示例:
        - parser.parse_expression()
        """

        node = self.parse_term()
        while True:
            if self.consume_punctuation("+"):
                node = _make_symbol_expr_add(node, self.parse_term())
            elif self.consume_punctuation("-"):
                node = _make_symbol_expr_sub(node, self.parse_term())
            else:
                return node

    def parse_term(self: "_SymbolExprParserBase") -> _SymbolExprNode:
        """解析乘法与 affine 风格整除表达式。

        功能说明:
        - 解析 `*`、`floordiv`、`ceildiv` 与 `mod`。
        - 裸 `/` 和 `//` 不属于 lexer 公开 token，也不在本 parser 内兼容。

        使用示例:
        - parser.parse_term()
        """

        node = self.parse_primary()
        while True:
            if self.consume_punctuation("*"):
                node = _make_symbol_expr_mul(node, self.parse_primary())
            elif self.consume_keyword("floordiv"):
                node = _make_symbol_expr_keyword_binary("floordiv", node, self.parse_primary())
            elif self.consume_keyword("ceildiv"):
                node = _make_symbol_expr_keyword_binary("ceildiv", node, self.parse_primary())
            elif self.consume_keyword("mod"):
                node = _make_symbol_expr_keyword_binary("mod", node, self.parse_primary())
            else:
                return node

    def parse_primary(self: "_SymbolExprParserBase") -> _SymbolExprNode:
        """解析 symbol 表达式 primary。

        功能说明:
        - 支持整数、标识符、`?`、括号、一元正负号与二元 `min(lhs, rhs)`。

        使用示例:
        - parser.parse_primary()
        """

        if self.consume_punctuation("+"):
            return self.parse_primary()
        if self.consume_punctuation("-"):
            return _make_symbol_expr_neg(self.parse_primary())
        if self.consume_punctuation("?"):
            return _make_symbol_expr_unknown()
        integer = self.consume_integer()
        if integer is not None:
            return _make_symbol_expr_const(integer)
        if self.consume_keyword("min"):
            self.expect_punctuation("(")
            lhs = self.parse_expression()
            self.expect_punctuation(",")
            rhs = self.parse_expression()
            self.expect_punctuation(")")
            return _make_symbol_expr_min(lhs, rhs)
        if self.consume_keyword("max"):
            self.expect_punctuation("(")
            lhs = self.parse_expression()
            self.expect_punctuation(",")
            rhs = self.parse_expression()
            self.expect_punctuation(")")
            return _make_symbol_expr_max(lhs, rhs)
        identifier = self.consume_identifier()
        if identifier is not None:
            return _make_symbol_expr_symbol(identifier)
        if self.consume_punctuation("("):
            node = self.parse_expression()
            self.expect_punctuation(")")
            return node
        self.raise_parse_error("symbol expr must contain identifiers, ?, integers, +, -, *, floordiv, ceildiv, mod, min(lhs, rhs) or max(lhs, rhs)")

    def consume_punctuation(self: "_SymbolExprParserBase", punctuation: str) -> bool:
        """消费可选标点。

        功能说明:
        - 由子类接入具体 token 来源。

        使用示例:
        - parser.consume_punctuation("+")
        """

        raise NotImplementedError

    def expect_punctuation(self: "_SymbolExprParserBase", punctuation: str) -> None:
        """消费必需标点。

        功能说明:
        - 缺失时抛出当前 parser 类型对应的错误。

        使用示例:
        - parser.expect_punctuation(")")
        """

        raise NotImplementedError

    def consume_keyword(self: "_SymbolExprParserBase", keyword: str) -> bool:
        """消费可选关键字。

        功能说明:
        - 关键字用于 `min`、`max`、`floordiv`、`ceildiv` 与 `mod`。

        使用示例:
        - parser.consume_keyword("floordiv")
        """

        raise NotImplementedError

    def consume_identifier(self: "_SymbolExprParserBase") -> str | None:
        """消费可选标识符。

        功能说明:
        - 标识符表示具名 symbol dim。

        使用示例:
        - parser.consume_identifier()
        """

        raise NotImplementedError

    def consume_integer(self: "_SymbolExprParserBase") -> int | None:
        """消费可选非负整数字面量。

        功能说明:
        - 一元负号由 `parse_primary` 统一处理。

        使用示例:
        - parser.consume_integer()
        """

        raise NotImplementedError

    def raise_parse_error(self: "_SymbolExprParserBase", message: str) -> None:
        """抛出 parser 错误。

        功能说明:
        - 字符串 parser 转为 `VerifyException`，xDSL parser 转为 `ParseError`。

        使用示例:
        - parser.raise_parse_error("message")
        """

        raise NotImplementedError


class _SymbolExprTextParser(_SymbolExprParserBase):
    """解析 Python 字符串形式的公开 symbol 表达。

    功能说明:
    - 服务 `SymbolExprAttr.from_expr(...)` 与 verifier 路径。
    - 明确拒绝裸 `/`、`//`、quoted string 和未知字符。

    使用示例:
    - _SymbolExprTextParser("N + 1").parse_all()
    """

    def __init__(self: "_SymbolExprTextParser", expr: str) -> None:
        """初始化字符串 parser。

        功能说明:
        - 将输入表达式 token 化并保存当前位置。

        使用示例:
        - _SymbolExprTextParser("N").parse_all()
        """

        self.tokens = _tokenize_symbol_expr(expr)
        self.index = 0

    def parse_all(self: "_SymbolExprTextParser") -> _SymbolExprNode:
        """解析完整字符串表达式。

        功能说明:
        - 要求表达式非空且所有 token 被消费。

        使用示例:
        - _SymbolExprTextParser("N + 1").parse_all()
        """

        if not self.tokens:
            _raise_verify_error("symbol expr must not be empty")
        node = self.parse_expression()
        if self.index != len(self.tokens):
            self.raise_parse_error("symbol expr contains trailing tokens")
        return node

    def consume_punctuation(self: "_SymbolExprTextParser", punctuation: str) -> bool:
        """消费字符串 token 中的可选标点。

        功能说明:
        - 当前位置匹配时前进一个 token。

        使用示例:
        - parser.consume_punctuation("+")
        """

        if self.index < len(self.tokens):
            token = self.tokens[self.index]
            if token.kind == "punct" and token.text == punctuation:
                self.index += 1
                return True
        return False

    def expect_punctuation(self: "_SymbolExprTextParser", punctuation: str) -> None:
        """消费字符串 token 中的必需标点。

        功能说明:
        - 缺失时抛出 `VerifyException`。

        使用示例:
        - parser.expect_punctuation(")")
        """

        if not self.consume_punctuation(punctuation):
            self.raise_parse_error(f"expected `{punctuation}` in symbol expr")

    def consume_keyword(self: "_SymbolExprTextParser", keyword: str) -> bool:
        """消费字符串 token 中的可选关键字。

        功能说明:
        - 仅当 token 文本与关键字完全一致时消费。

        使用示例:
        - parser.consume_keyword("mod")
        """

        if self.index < len(self.tokens):
            token = self.tokens[self.index]
            if token.kind == "ident" and token.text == keyword:
                self.index += 1
                return True
        return False

    def consume_identifier(self: "_SymbolExprTextParser") -> str | None:
        """消费字符串 token 中的可选 symbol 名称。

        功能说明:
        - `floordiv`、`ceildiv`、`mod`、`min`、`max` 在 primary 位置不作为普通 symbol 名称。

        使用示例:
        - parser.consume_identifier()
        """

        if self.index < len(self.tokens):
            token = self.tokens[self.index]
            if token.kind == "ident" and token.text not in {"floordiv", "ceildiv", "mod", "min", "max"}:
                self.index += 1
                return token.text
        return None

    def consume_integer(self: "_SymbolExprTextParser") -> int | None:
        """消费字符串 token 中的可选整数。

        功能说明:
        - 返回 Python `int`，不接受布尔或带符号 token。

        使用示例:
        - parser.consume_integer()
        """

        if self.index < len(self.tokens):
            token = self.tokens[self.index]
            if token.kind == "int":
                self.index += 1
                return int(token.text)
        return None

    def raise_parse_error(self: "_SymbolExprTextParser", message: str) -> None:
        """抛出字符串解析错误。

        功能说明:
        - 使用仓库统一 verifier 错误格式。

        使用示例:
        - parser.raise_parse_error("bad")
        """

        _raise_verify_error(message)


class _SymbolExprAttrParser(_SymbolExprParserBase):
    """接入 xDSL `AttrParser` 的 symbol 表达式 parser。

    功能说明:
    - 只使用 xDSL 公开 parser token 接口，不使用 `_resume_from` 等私有能力。
    - 因 xDSL lexer 不公开裸 `/` token，本 parser 只支持 `floordiv`、`ceildiv` 与 `mod`。

    使用示例:
    - _SymbolExprAttrParser(parser).parse_expression()
    """

    def __init__(self: "_SymbolExprAttrParser", parser: AttrParser) -> None:
        """初始化 xDSL attribute parser 适配器。

        功能说明:
        - 保存公开 `AttrParser` 对象供后续 token 消费。

        使用示例:
        - _SymbolExprAttrParser(parser)
        """

        self.parser = parser

    def consume_punctuation(self: "_SymbolExprAttrParser", punctuation: str) -> bool:
        """消费 xDSL parser 中的可选标点。

        功能说明:
        - 调用 `parse_optional_punctuation` 公开接口。

        使用示例:
        - parser.consume_punctuation("*")
        """

        return self.parser.parse_optional_punctuation(punctuation) is not None

    def expect_punctuation(self: "_SymbolExprAttrParser", punctuation: str) -> None:
        """消费 xDSL parser 中的必需标点。

        功能说明:
        - 调用 `parse_punctuation` 公开接口。

        使用示例:
        - parser.expect_punctuation(")")
        """

        self.parser.parse_punctuation(punctuation, " in symbol expr")

    def consume_keyword(self: "_SymbolExprAttrParser", keyword: str) -> bool:
        """消费 xDSL parser 中的可选关键字。

        功能说明:
        - 调用 `parse_optional_keyword` 公开接口。

        使用示例:
        - parser.consume_keyword("ceildiv")
        """

        return self.parser.parse_optional_keyword(keyword) is not None

    def consume_identifier(self: "_SymbolExprAttrParser") -> str | None:
        """消费 xDSL parser 中的可选 symbol 名称。

        功能说明:
        - 调用 `parse_optional_identifier` 公开接口，关键字不作为 symbol 名称。

        使用示例:
        - parser.consume_identifier()
        """

        identifier = self.parser.parse_optional_identifier()
        if identifier in {"floordiv", "ceildiv", "mod", "min", "max"}:
            self.parser.raise_error("keyword cannot be used as bare symbol expr name")
        return identifier

    def consume_integer(self: "_SymbolExprAttrParser") -> int | None:
        """消费 xDSL parser 中的可选非负整数。

        功能说明:
        - 一元负号由表达式 parser 处理。

        使用示例:
        - parser.consume_integer()
        """

        return self.parser.parse_optional_integer(allow_boolean=False, allow_negative=False)

    def raise_parse_error(self: "_SymbolExprAttrParser", message: str) -> None:
        """抛出 xDSL parser 错误。

        功能说明:
        - 使用 xDSL parser 的公开错误入口。

        使用示例:
        - parser.raise_parse_error("bad")
        """

        self.parser.raise_error(message)


def _tokenize_symbol_expr(expr: str) -> list[_SymbolExprToken]:
    """把公开 symbol 表达式字符串转换为 token。

    功能说明:
    - 接受标识符、整数与受支持标点。
    - 裸 `/`、`//`、引号和其它字符直接报错。

    使用示例:
    - _tokenize_symbol_expr("N floordiv 2")
    """

    tokens: list[_SymbolExprToken] = []
    position = 0
    while position < len(expr):
        if expr[position:].strip() == "":
            break
        match = _SYMBOL_EXPR_TOKEN_PATTERN.match(expr, position)
        if match is None:
            _raise_verify_error("unsupported public symbol expression")
        position = match.end()
        if text := match.group("int"):
            tokens.append(_SymbolExprToken("int", text))
        elif text := match.group("ident"):
            tokens.append(_SymbolExprToken("ident", text))
        elif text := match.group("punct"):
            tokens.append(_SymbolExprToken("punct", text))
        else:
            invalid = match.group("invalid") or ""
            if invalid in {"/", '"'}:
                _raise_verify_error("symbol expr does not support quoted string, bare / or //; use floordiv, ceildiv or mod")
            _raise_verify_error("unsupported public symbol expression")
    return tokens


def _make_symbol_expr_const(value: int) -> _SymbolExprNode:
    """构造常量表达节点。

    功能说明:
    - 统一保存整数常量。

    使用示例:
    - _make_symbol_expr_const(4)
    """

    return _SymbolExprNode("const", value=value)


def _make_symbol_expr_symbol(value: str) -> _SymbolExprNode:
    """构造具名 symbol 表达节点。

    功能说明:
    - 校验名称满足公开标识符规则。

    使用示例:
    - _make_symbol_expr_symbol("N")
    """

    if _SYMBOL_DIM_NAME_PATTERN.fullmatch(value) is None:
        _raise_verify_error("symbol expr name must match [A-Za-z_][A-Za-z0-9_]*")
    return _SymbolExprNode("symbol", value=value)


def _make_symbol_expr_unknown() -> _SymbolExprNode:
    """构造 unknown 表达节点。

    功能说明:
    - unknown 公开文本固定为 `?`。

    使用示例:
    - _make_symbol_expr_unknown()
    """

    return _SymbolExprNode("unknown")


def _is_symbol_expr_unknown(node: _SymbolExprNode) -> bool:
    """判断表达节点是否为 unknown。

    功能说明:
    - 服务 `?` 传播规则。

    使用示例:
    - _is_symbol_expr_unknown(node)
    """

    return node.kind == "unknown"


def _get_symbol_expr_const(node: _SymbolExprNode) -> int | None:
    """提取常量节点的整数值。

    功能说明:
    - 非常量返回 `None`。

    使用示例:
    - _get_symbol_expr_const(node)
    """

    return int(node.value) if node.kind == "const" and isinstance(node.value, int) else None


def _make_symbol_expr_neg(node: _SymbolExprNode) -> _SymbolExprNode:
    """构造一元负号表达。

    功能说明:
    - 常量直接折叠；unknown 继续传播。

    使用示例:
    - _make_symbol_expr_neg(_make_symbol_expr_symbol("N"))
    """

    if _is_symbol_expr_unknown(node):
        return _make_symbol_expr_unknown()
    const = _get_symbol_expr_const(node)
    if const is not None:
        return _make_symbol_expr_const(-const)
    if node.kind == "neg":
        return node.args[0]
    return _SymbolExprNode("neg", args=(node,))


def _make_symbol_expr_add(lhs: _SymbolExprNode, rhs: _SymbolExprNode) -> _SymbolExprNode:
    """构造 canonical 加法表达。

    功能说明:
    - 常量折叠、零 identity、交换律排序与 `?` 传播。

    使用示例:
    - _make_symbol_expr_add(_make_symbol_expr_symbol("N"), _make_symbol_expr_const(1))
    """

    if _is_symbol_expr_unknown(lhs) or _is_symbol_expr_unknown(rhs):
        return _make_symbol_expr_unknown()
    lhs_const = _get_symbol_expr_const(lhs)
    rhs_const = _get_symbol_expr_const(rhs)
    if lhs_const is not None and rhs_const is not None:
        return _make_symbol_expr_const(lhs_const + rhs_const)
    terms: list[_SymbolExprNode] = []
    const_sum = 0
    for node in (lhs, rhs):
        if node.kind == "add":
            source = node.args
        else:
            source = (node,)
        for term in source:
            term_const = _get_symbol_expr_const(term)
            if term_const is None:
                terms.append(term)
            else:
                const_sum += term_const
    terms.sort(key=_format_symbol_expr_node)
    if const_sum != 0:
        terms.append(_make_symbol_expr_const(const_sum))
    if not terms:
        return _make_symbol_expr_const(0)
    if len(terms) == 1:
        return terms[0]
    return _SymbolExprNode("add", args=tuple(terms))


def _make_symbol_expr_sub(lhs: _SymbolExprNode, rhs: _SymbolExprNode) -> _SymbolExprNode:
    """构造 canonical 减法表达。

    功能说明:
    - 常量折叠、减零 identity 与 `?` 传播。

    使用示例:
    - _make_symbol_expr_sub(_make_symbol_expr_symbol("N"), _make_symbol_expr_const(1))
    """

    if _is_symbol_expr_unknown(lhs) or _is_symbol_expr_unknown(rhs):
        return _make_symbol_expr_unknown()
    lhs_const = _get_symbol_expr_const(lhs)
    rhs_const = _get_symbol_expr_const(rhs)
    if lhs_const is not None and rhs_const is not None:
        return _make_symbol_expr_const(lhs_const - rhs_const)
    if rhs_const == 0:
        return lhs
    if rhs_const is not None:
        return _make_symbol_expr_add(lhs, _make_symbol_expr_const(-rhs_const))
    if lhs_const == 0:
        return _make_symbol_expr_neg(rhs)
    if lhs == rhs:
        return _make_symbol_expr_const(0)
    return _SymbolExprNode("sub", args=(lhs, rhs))


def _make_symbol_expr_mul(lhs: _SymbolExprNode, rhs: _SymbolExprNode) -> _SymbolExprNode:
    """构造 canonical 乘法表达。

    功能说明:
    - 常量折叠、零/一规则、交换律排序与 `?` 传播。

    使用示例:
    - _make_symbol_expr_mul(_make_symbol_expr_symbol("N"), _make_symbol_expr_const(2))
    """

    if _is_symbol_expr_unknown(lhs) or _is_symbol_expr_unknown(rhs):
        return _make_symbol_expr_unknown()
    lhs_const = _get_symbol_expr_const(lhs)
    rhs_const = _get_symbol_expr_const(rhs)
    if lhs_const is not None and rhs_const is not None:
        return _make_symbol_expr_const(lhs_const * rhs_const)
    terms: list[_SymbolExprNode] = []
    const_product = 1
    for node in (lhs, rhs):
        if node.kind == "mul":
            source = node.args
        else:
            source = (node,)
        for term in source:
            term_const = _get_symbol_expr_const(term)
            if term_const is None:
                terms.append(term)
            else:
                const_product *= term_const
    if const_product == 0:
        return _make_symbol_expr_const(0)
    terms.sort(key=_format_symbol_expr_node)
    if const_product != 1 or not terms:
        terms.insert(0, _make_symbol_expr_const(const_product))
    if len(terms) == 1:
        return terms[0]
    return _SymbolExprNode("mul", args=tuple(terms))


def _make_symbol_expr_keyword_binary(op: str, lhs: _SymbolExprNode, rhs: _SymbolExprNode) -> _SymbolExprNode:
    """构造 affine 风格关键字二元表达。

    功能说明:
    - 支持 `floordiv`、`ceildiv` 与 `mod`。
    - 常量场景直接折叠，除零稳定报错。

    使用示例:
    - _make_symbol_expr_keyword_binary("floordiv", lhs, rhs)
    """

    if _is_symbol_expr_unknown(lhs) or _is_symbol_expr_unknown(rhs):
        return _make_symbol_expr_unknown()
    lhs_const = _get_symbol_expr_const(lhs)
    rhs_const = _get_symbol_expr_const(rhs)
    if rhs_const == 0:
        _raise_verify_error("symbol expr division by zero is not supported")
    if lhs_const is not None and rhs_const is not None:
        if op == "floordiv":
            return _make_symbol_expr_const(lhs_const // rhs_const)
        if op == "ceildiv":
            return _make_symbol_expr_const(-(-lhs_const // rhs_const))
        if op == "mod":
            return _make_symbol_expr_const(lhs_const % rhs_const)
    if rhs_const == 1:
        if op in {"floordiv", "ceildiv"}:
            return lhs
        if op == "mod":
            return _make_symbol_expr_const(0)
    return _SymbolExprNode(op, args=(lhs, rhs))


def _make_symbol_expr_min(lhs: _SymbolExprNode, rhs: _SymbolExprNode) -> _SymbolExprNode:
    """构造 canonical `min(lhs, rhs)` 表达。

    功能说明:
    - 支持二元 min、常量折叠、交换律排序与 `?` 传播。

    使用示例:
    - _make_symbol_expr_min(lhs, rhs)
    """

    if _is_symbol_expr_unknown(lhs) or _is_symbol_expr_unknown(rhs):
        return _make_symbol_expr_unknown()
    lhs_const = _get_symbol_expr_const(lhs)
    rhs_const = _get_symbol_expr_const(rhs)
    if lhs_const is not None and rhs_const is not None:
        return _make_symbol_expr_const(min(lhs_const, rhs_const))
    if lhs == rhs:
        return lhs
    ordered = tuple(sorted((lhs, rhs), key=_format_symbol_expr_node))
    return _SymbolExprNode("min", args=ordered)


def _make_symbol_expr_max(lhs: _SymbolExprNode, rhs: _SymbolExprNode) -> _SymbolExprNode:
    """构造 canonical `max(lhs, rhs)` 表达。

    功能说明:
    - 支持二元 max、常量折叠、交换律排序与 `?` 传播。

    使用示例:
    - _make_symbol_expr_max(lhs, rhs)
    """

    if _is_symbol_expr_unknown(lhs) or _is_symbol_expr_unknown(rhs):
        return _make_symbol_expr_unknown()
    lhs_const = _get_symbol_expr_const(lhs)
    rhs_const = _get_symbol_expr_const(rhs)
    if lhs_const is not None and rhs_const is not None:
        return _make_symbol_expr_const(max(lhs_const, rhs_const))
    if lhs == rhs:
        return lhs
    ordered = tuple(sorted((lhs, rhs), key=_format_symbol_expr_node))
    return _SymbolExprNode("max", args=ordered)


def _symbol_expr_precedence(node: _SymbolExprNode) -> int:
    """返回表达节点打印优先级。

    功能说明:
    - 用于生成可稳定重新解析的 canonical 文本。

    使用示例:
    - _symbol_expr_precedence(node)
    """

    if node.kind in {"const", "symbol", "unknown", "min", "max"}:
        return _SYMBOL_EXPR_ATOM_PRECEDENCE
    if node.kind == "neg":
        return _SYMBOL_EXPR_UNARY_PRECEDENCE
    if node.kind in {"mul", "floordiv", "ceildiv", "mod"}:
        return _SYMBOL_EXPR_TERM_PRECEDENCE
    return _SYMBOL_EXPR_EXPR_PRECEDENCE


def _format_symbol_expr_node(node: _SymbolExprNode, parent_precedence: int = 0) -> str:
    """打印 canonical symbol 表达式节点。

    功能说明:
    - 生成 `SymbolExprAttr.expr.data` 的稳定文本。
    - 只在必要时添加括号。

    使用示例:
    - _format_symbol_expr_node(node)
    """

    if node.kind == "const":
        text = str(node.value)
    elif node.kind == "symbol":
        text = str(node.value)
    elif node.kind == "unknown":
        text = _UNKNOWN_SYMBOL_EXPR
    elif node.kind == "neg":
        text = "-" + _format_symbol_expr_node(node.args[0], _SYMBOL_EXPR_UNARY_PRECEDENCE)
    elif node.kind == "add":
        text = _format_symbol_expr_add(node)
    elif node.kind == "sub":
        lhs, rhs = node.args
        text = (
            f"{_format_symbol_expr_node(lhs, _SYMBOL_EXPR_EXPR_PRECEDENCE)} - "
            f"{_format_symbol_expr_node(rhs, _SYMBOL_EXPR_EXPR_PRECEDENCE + 1)}"
        )
    elif node.kind == "mul":
        text = "*".join(_format_symbol_expr_node(arg, _SYMBOL_EXPR_TERM_PRECEDENCE) for arg in node.args)
    elif node.kind in {"floordiv", "ceildiv", "mod"}:
        lhs, rhs = node.args
        text = (
            f"{_format_symbol_expr_node(lhs, _SYMBOL_EXPR_TERM_PRECEDENCE)} {node.kind} "
            f"{_format_symbol_expr_node(rhs, _SYMBOL_EXPR_TERM_PRECEDENCE + 1)}"
        )
    elif node.kind == "min":
        text = f"min({_format_symbol_expr_node(node.args[0])}, {_format_symbol_expr_node(node.args[1])})"
    elif node.kind == "max":
        text = f"max({_format_symbol_expr_node(node.args[0])}, {_format_symbol_expr_node(node.args[1])})"
    else:
        _raise_verify_error("unsupported public symbol expression")
    if _symbol_expr_precedence(node) < parent_precedence:
        return f"({text})"
    return text


def _format_symbol_expr_add(node: _SymbolExprNode) -> str:
    """打印 canonical 加法表达式。

    功能说明:
    - 把负常量和一元负号打印为 `lhs - rhs` 形式。

    使用示例:
    - _format_symbol_expr_add(node)
    """

    pieces: list[str] = []
    for term in node.args:
        const = _get_symbol_expr_const(term)
        if const is not None and const < 0:
            if not pieces:
                pieces.append(str(const))
            else:
                pieces.append(f"- {abs(const)}")
            continue
        if term.kind == "neg":
            text = _format_symbol_expr_node(term.args[0], _SYMBOL_EXPR_EXPR_PRECEDENCE + 1)
            pieces.append(f"- {text}" if pieces else f"-{text}")
            continue
        text = _format_symbol_expr_node(term, _SYMBOL_EXPR_EXPR_PRECEDENCE)
        pieces.append(text if not pieces else f"+ {text}")
    return " ".join(pieces)


def _parse_symbol_expr_from_text(expr: str) -> _SymbolExprNode:
    """解析字符串为 canonical symbol 表达节点。

    功能说明:
    - 统一 `from_expr`、verifier 与内部 result 推导路径。

    使用示例:
    - _parse_symbol_expr_from_text("N + 1")
    """

    return _SymbolExprTextParser(expr).parse_all()


def _parse_symbol_expr_from_attr_parser(parser: AttrParser) -> _SymbolExprNode:
    """从 xDSL attribute parser 解析 symbol 表达。

    功能说明:
    - 只消费 `#symbol.expr<...>` 内部表达 token。

    使用示例:
    - _parse_symbol_expr_from_attr_parser(parser)
    """

    return _SymbolExprAttrParser(parser).parse_expression()


def _normalize_expr(expr: str) -> str:
    """标准化符号表达字符串。

    功能说明:
    - 解析公开 symbol 表达并输出 canonical 文本。
    - 裸 `/`、`//`、quoted string 和非法字符均被拒绝。

    使用示例:
    - _normalize_expr("1 + N")
    """

    return _format_symbol_expr_node(_parse_symbol_expr_from_text(expr.strip()))


def _evaluate_concrete_expr(expr: str) -> int | None:
    """尝试计算不含符号名的整数表达式。

    功能说明:
    - 对 canonical 语法下的纯整数表达返回具体整数值。
    - 对动态 symbol 或 unknown 返回 `None`。

    使用示例:
    - _evaluate_concrete_expr("8 floordiv 2")
    """

    try:
        node = _parse_symbol_expr_from_text(expr)
    except VerifyException:
        return None
    return _get_symbol_expr_const(node)


def _canonicalize_symbolic_expr(expr: str) -> str:
    """生成对外比较用的稳定符号表达文本。

    功能说明:
    - 复用 `SymbolExprAttr` canonical parser。

    使用示例:
    - _canonicalize_symbolic_expr("1 + N")
    """

    return _normalize_expr(expr)


def _is_supported_symbol_expr(expr: str) -> bool:
    """判断符号表达是否属于当前 dialect 支持的最小语法。

    功能说明:
    - 支持整数、标识符、`?`、`+`、`-`、`*`、`floordiv`、`ceildiv`、`mod`、二元 `min/max` 与括号。
    - 不支持裸 `/`、`//`、quoted string 或 `floor(...)`。

    使用示例:
    - _is_supported_symbol_expr("N floordiv 2")
    """

    try:
        _parse_symbol_expr_from_text(expr)
    except VerifyException:
        return False
    return True


def _unwrap_symbol_expr_attr_text(expr: str) -> str:
    """提取 memory 条目中内联 `#symbol.expr<...>` 的表达式正文。

    功能说明:
    - 兼容 `NnMemoryType` raw parser 当前把 `#symbol.expr<...>` 条目保存为 `StringAttr` 的事实。
    - 对裸 `N`、`K*N`、`?` 等旧条目保持原文本返回，不在 symbol 层调整 nn parser。

    使用示例:
    - _unwrap_symbol_expr_attr_text("#symbol.expr<N>")
    """

    stripped = expr.strip()
    prefix = "#symbol.expr<"
    if stripped.startswith(prefix) and stripped.endswith(">"):
        return stripped[len(prefix) : -1].strip()
    return stripped


def _verify_axis(axis: Attribute, rank: int, op_name: str) -> int:
    """校验 axis attribute 并返回轴号。


    功能说明:
    - 统一校验 `symbol.get_dim/get_stride` 的静态整数轴号约束。

    使用示例:
    - _verify_axis(IntAttr(0), 2, "symbol.get_dim")

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    if not isinstance(axis, IntAttr):
        _raise_verify_error(f"{op_name} axis must be a static integer")
    if axis.data < 0 or axis.data >= rank:
        _raise_verify_error(f"{op_name} axis out of range")
    return axis.data


def _entry_to_expr(entry: Attribute, op_name: str, field_name: str) -> str:
    """将 memory 元信息条目转换为 symbol 表达。


    功能说明:
    - 将 `NnMemoryType` 中的 `shape/stride` 条目收敛为 `!symbol.int<#symbol.expr<...>>` 所需字符串。

    使用示例:
    - _entry_to_expr(IntAttr(4), "symbol.get_dim", "shape")

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    if isinstance(entry, IntAttr):
        return str(entry.data)
    if isinstance(entry, SymbolExprAttr):
        return entry.expr.data
    if isinstance(entry, StringAttr):
        expr = _unwrap_symbol_expr_attr_text(entry.data)
        if expr != "?":
            return expr
    _raise_verify_error(f"{op_name} does not support unknown {field_name} entry '?'")


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
    - test: test/dialect/test_symbol.py
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


    功能说明:
    - 为 `symbol.for` 与 `symbol.get_*` verifier 复用统一的 symbol 类型判断。

    使用示例:
    - _is_symbol_int_type(SymbolValueType.from_expr("N"))

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    return isinstance(attr, SymbolValueType)


def _is_symbol_arith_operand_type(attr: Attribute) -> bool:
    """判断 attribute 是否可作为 symbol 算术/比较 operand。

    功能说明:
    - symbol 算术允许 `!symbol.int` 与 loop-carried `!symbol.iter`，供 tail `min(tile, dim - idx)` 使用。

    使用示例:
    - ok = _is_symbol_arith_operand_type(SymbolValueType.from_expr("N"))
    """

    return isinstance(attr, (SymbolValueType, SymbolIterType))


def _is_unknown_symbol_int_type(attr: Attribute) -> bool:
    """判断 `!symbol.int<#symbol.expr<??>>` unknown 类型。

    功能说明:
    - 只在 symbol dialect 当前文件内服务 verifier 与 fold 边界。
    - unknown 是保守值语义，不等同具名符号表达。

    使用示例:
    - _is_unknown_symbol_int_type(SymbolValueType.from_expr("?"))
    """

    return isinstance(attr, SymbolValueType) and attr.get_value() == _UNKNOWN_SYMBOL_EXPR


def _requires_unknown_arith_result(lhs_type: Attribute, rhs_type: Attribute) -> bool:
    """判断 symbol 算术结果是否必须为 unknown。

    功能说明:
    - 任一 operand 为 `!symbol.iter<...>` 或 `!symbol.int<#symbol.expr<??>>` 时，算术结果必须保守为 `!symbol.int<#symbol.expr<??>>`。

    使用示例:
    - needs_unknown = _requires_unknown_arith_result(lhs.type, rhs.type)
    """

    return (
        isinstance(lhs_type, SymbolIterType)
        or isinstance(rhs_type, SymbolIterType)
        or _is_unknown_symbol_int_type(lhs_type)
        or _is_unknown_symbol_int_type(rhs_type)
    )


def _infer_symbol_arith_result_expr(op_name: str, lhs_type: Attribute, rhs_type: Attribute) -> str | None:
    """推导 symbol 二元算术的 canonical 结果表达。

    功能说明:
    - 对两个确定 `SymbolValueType` operand 复用 `SymbolExprAttr` canonical 逻辑。
    - `iter` 或 `?` 场景由调用方使用 unknown 规则处理。

    使用示例:
    - _infer_symbol_arith_result_expr("symbol.add", lhs.type, rhs.type)
    """

    if not isinstance(lhs_type, SymbolValueType) or not isinstance(rhs_type, SymbolValueType):
        return None
    lhs = _parse_symbol_expr_from_text(lhs_type.expr.expr.data)
    rhs = _parse_symbol_expr_from_text(rhs_type.expr.expr.data)
    if op_name == "symbol.add":
        return _format_symbol_expr_node(_make_symbol_expr_add(lhs, rhs))
    if op_name == "symbol.sub":
        return _format_symbol_expr_node(_make_symbol_expr_sub(lhs, rhs))
    if op_name == "symbol.mul":
        return _format_symbol_expr_node(_make_symbol_expr_mul(lhs, rhs))
    if op_name in {"symbol.div", "symbol.floordiv"}:
        return _format_symbol_expr_node(_make_symbol_expr_keyword_binary("floordiv", lhs, rhs))
    if op_name == "symbol.min":
        return _format_symbol_expr_node(_make_symbol_expr_min(lhs, rhs))
    return None


def _get_concrete_symbol_int_value(attr: Attribute) -> int | None:
    """提取静态可求值的 `!symbol.int` 整数值。


    功能说明:
    - 仅当 `attr` 是静态整数 `SymbolValueType` 时返回具体整数。
    - 动态 symbol 表达返回 `None`，供 fold 逻辑保守拒绝。

    使用示例:
    - _get_concrete_symbol_int_value(SymbolValueType.from_expr("3"))

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol.py
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

    def __post_init__(self: "SymbolExprAttr") -> None:
        """规范化构造期表达式。

        功能说明:
        - 公开构造 `SymbolExprAttr(StringAttr(...))` 与 `from_expr(...)` 使用同一 canonical 规则。
        - 拒绝 quoted string、裸 `/`、`//` 与非法表达式。

        使用示例:
        - SymbolExprAttr(StringAttr("1 + N"))
        """

        object.__setattr__(self, "expr", StringAttr(_normalize_expr(self.expr.data)))

    @classmethod
    def parse_parameters(cls: type["SymbolExprAttr"], parser: AttrParser) -> Sequence[Attribute]:
        """解析符号表达参数。

        功能说明:
        - 解析 `#symbol.expr<N + 1>` 形式的非 quoted 公开语法。
        - 只使用 xDSL 公开 parser token 接口。

        使用示例:
        - Parser(ctx, "#symbol.expr<N>").parse_attribute()
        """

        parser.parse_punctuation("<", "Expected '<' for symbol expr attribute.")
        expr = _parse_symbol_expr_from_attr_parser(parser)
        parser.parse_punctuation(">", "Expected '>' for symbol expr attribute.")
        return (StringAttr(_format_symbol_expr_node(expr)),)

    def print_parameters(self: "SymbolExprAttr", printer: Printer) -> None:
        """打印符号表达参数。

        功能说明:
        - 输出 `#symbol.expr<...>` 非 quoted 公开语法。

        使用示例:
        - SymbolExprAttr.from_expr("N").print_parameters(printer)
        """

        printer.print_string("<")
        printer.print_string(_normalize_expr(self.expr.data))
        printer.print_string(">")

    def verify(self: "SymbolExprAttr") -> None:
        """校验符号表达。

        功能说明:
        - 确认内部表达属于公开 symbol 表达式语法。

        使用示例:
        - SymbolExprAttr.from_expr("N floordiv 2").verify()
        """

        expr = _normalize_expr(self.expr.data)
        if not expr:
            _raise_verify_error("symbol expr must not be empty")
        if not _is_supported_symbol_expr(expr):
            _raise_verify_error("symbol expr must contain identifiers, ?, integers, +, -, *, floordiv, ceildiv, mod, min(lhs, rhs) or max(lhs, rhs)")

    @classmethod
    def from_expr(cls: type["SymbolExprAttr"], expr: str) -> "SymbolExprAttr":
        """从字符串构造符号表达 attribute。


        功能说明:
        - 为测试与实现提供统一的构造入口。

        使用示例:
        - SymbolExprAttr.from_expr("N")

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
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


        功能说明:
        - 跳过构造期校验，改由显式 verify 或 op/module verify 触发。
        - 允许 Parser.parse_module 完成后再由 verifier 统一拒绝非法名称。

        使用示例:
        - SymbolDimType(StringAttr("BLOCK_M")).verify()

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        if not isinstance(self, ParametrizedAttribute):
            _raise_type_error("SymbolDimType must be ParametrizedAttribute")

    @classmethod
    def parse_parameters(cls: type["SymbolDimType"], parser: AttrParser) -> Sequence[Attribute]:
        """解析 symbol.dim 类型参数。


        功能说明:
        - 解析 `!symbol.dim<"name">` 的名称参数。

        使用示例:
        - SymbolDimType.parse_parameters(parser)

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        parser.parse_punctuation("<", "Expected '<' for symbol dim type.")
        name = parser.parse_str_literal("Expected quoted symbol dim name.")
        parser.parse_punctuation(">", "Expected '>' for symbol dim type.")
        return (StringAttr(name),)

    def print_parameters(self: "SymbolDimType", printer: Printer) -> None:
        """打印 symbol.dim 类型参数。


        功能说明:
        - 输出 `!symbol.dim<\"name\">` 的名称参数。

        使用示例:
        - SymbolDimType.from_name("BLOCK_M").print_parameters(printer)

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        printer.print_string("<")
        printer.print_string_literal(self.dim.data)
        printer.print_string(">")

    def verify(self: "SymbolDimType") -> None:
        """校验 symbol.dim 名称合法性。


        功能说明:
        - 拒绝空名称或非法标识符。

        使用示例:
        - SymbolDimType.from_name("BLOCK_M").verify()

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        _normalize_symbol_dim_name(self.dim.data)

    def __str__(self: "SymbolDimType") -> str:
        """返回公开的 symbol.dim 文本表示。


        功能说明:
        - 生成 `symbol.dim<name>` 形式的字符串表示。

        使用示例:
        - str(SymbolDimType.from_name("BLOCK_M"))

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        return f"symbol.dim<{self.dim.data}>"

    @classmethod
    def from_name(cls: type["SymbolDimType"], name: str) -> "SymbolDimType":
        """从名称构造 symbol.dim 类型。


        功能说明:
        - 对名称执行规范化校验并返回类型实例。

        使用示例:
        - SymbolDimType.from_name("BLOCK_M")

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner.py
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
        """解析整数符号值类型参数。

        功能说明:
        - 解析 `!symbol.int<#symbol.expr<...>>` 或 alias attribute。
        - 拒绝旧 quoted string 参数。

        使用示例:
        - Parser(ctx, "!symbol.int<#symbol.expr<N>>").parse_attribute()
        """

        parser.parse_punctuation("<", "Expected '<' for symbol int type.")
        expr = parser.parse_attribute()
        parser.parse_punctuation(">", "Expected '>' for symbol int type.")
        if not isinstance(expr, SymbolExprAttr):
            parser.raise_error("symbol.int expects SymbolExprAttr parameter")
        return (expr,)

    def print_parameters(self: "SymbolValueType", printer: Printer) -> None:
        """打印整数符号值类型参数。

        功能说明:
        - 输出 `!symbol.int<#symbol.expr<...>>`。

        使用示例:
        - SymbolValueType.from_expr("N").print_parameters(printer)
        """

        printer.print_string("<")
        printer.print_attribute(self.expr)
        printer.print_string(">")

    def verify(self: "SymbolValueType") -> None:
        """校验整数符号值类型。

        功能说明:
        - 校验参数必须是合法 `SymbolExprAttr`。

        使用示例:
        - SymbolValueType.from_expr("N").verify()
        """

        self.expr.verify()

    def __str__(self: "SymbolValueType") -> str:
        """返回公开的 symbol.int 文本表示。

        功能说明:
        - 返回不带 dialect sigil 的调试文本。

        使用示例:
        - str(SymbolValueType.from_expr("N"))
        """

        return f"symbol.int<#{self.expr.name}<{_normalize_expr(self.expr.expr.data)}>>"

    def get_value(self: "SymbolValueType") -> int | str:
        """返回 symbol.int 的公开值。


        功能说明:
        - 对常量表达返回 `int`。
        - 对符号表达返回标准化后的字符串。

        使用示例:
        - SymbolValueType.from_expr("N").get_value()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        expr = _normalize_expr(self.expr.expr.data)
        if expr == _UNKNOWN_SYMBOL_EXPR:
            return _UNKNOWN_SYMBOL_EXPR
        concrete_value = _evaluate_concrete_expr(expr)
        return concrete_value if concrete_value is not None else _canonicalize_symbolic_expr(expr)

    def is_symbol(self: "SymbolValueType") -> bool:
        """判断当前值是否为非字面量符号表达。


        功能说明:
        - 纯数字常量返回 `False`。
        - 其他 symbol 表达返回 `True`。

        使用示例:
        - SymbolValueType.from_expr("1").is_symbol()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        expr = _normalize_expr(self.expr.expr.data)
        return expr != _UNKNOWN_SYMBOL_EXPR and _evaluate_concrete_expr(expr) is None

    @classmethod
    def from_expr(cls: type["SymbolValueType"], expr: str) -> "SymbolValueType":
        """从字符串构造整数符号值类型。


        功能说明:
        - 统一创建只表示整数类型的 symbol value type。

        使用示例:
        - SymbolValueType.from_expr("N")

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
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


        功能说明:
        - 解析 `#symbol.iter<start = #symbol.expr<...>, end = #symbol.expr<...>, step = #symbol.expr<...>>` 语法。

        使用示例:
        - SymbolIterAttr.parse_parameters(parser)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        parser.parse_punctuation("<", "Expected '<' for symbol.iter attribute.")
        parser.parse_keyword("start", " in symbol.iter attribute")
        parser.parse_characters("=", " in symbol.iter attribute")
        start = parser.parse_attribute()
        if not isinstance(start, SymbolExprAttr):
            parser.raise_error("symbol.iter start expects SymbolExprAttr")
        parser.parse_characters(",", " in symbol.iter attribute")
        parser.parse_keyword("end", " in symbol.iter attribute")
        parser.parse_characters("=", " in symbol.iter attribute")
        end = parser.parse_attribute()
        if not isinstance(end, SymbolExprAttr):
            parser.raise_error("symbol.iter end expects SymbolExprAttr")
        parser.parse_characters(",", " in symbol.iter attribute")
        parser.parse_keyword("step", " in symbol.iter attribute")
        parser.parse_characters("=", " in symbol.iter attribute")
        step = parser.parse_attribute()
        if not isinstance(step, SymbolExprAttr):
            parser.raise_error("symbol.iter step expects SymbolExprAttr")
        parser.parse_punctuation(">", "Expected '>' for symbol.iter attribute.")
        return (start, end, step)

    def print_parameters(self: "SymbolIterAttr", printer: Printer) -> None:
        """打印 symbol.iter attribute 参数。


        功能说明:
        - 输出 `#symbol.iter<start = #symbol.expr<...>, end = #symbol.expr<...>, step = #symbol.expr<...>>` 语法。

        使用示例:
        - SymbolIterAttr.from_bounds("0", "N", "TILE_D0").print_parameters(printer)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        printer.print_string("<start = ")
        printer.print_attribute(self.start)
        printer.print_string(", end = ")
        printer.print_attribute(self.end)
        printer.print_string(", step = ")
        printer.print_attribute(self.step)
        printer.print_string(">")

    def verify(self: "SymbolIterAttr") -> None:
        """校验 symbol.iter attribute 参数。


        功能说明:
        - 校验 start/end/step 的 symbol 表达式合法性。

        使用示例:
        - SymbolIterAttr.from_bounds("0", "N", "TILE_D0").verify()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        self.start.verify()
        self.end.verify()
        self.step.verify()

    @classmethod
    def from_bounds(cls: type["SymbolIterAttr"], start: str, end: str, step: str) -> "SymbolIterAttr":
        """从 start/end/step 字符串构造 symbol.iter attribute。


        功能说明:
        - 统一构造 `#symbol.iter<start = #symbol.expr<...>, end = #symbol.expr<...>, step = #symbol.expr<...>>`。

        使用示例:
        - SymbolIterAttr.from_bounds("0", "N", "TILE_D0")

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
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


        功能说明:
        - 解析 `!symbol.iter<start = #symbol.expr<...>, end = #symbol.expr<...>, step = #symbol.expr<...>>` 语法。
        - 明确拒绝旧格式 `!symbol.iter<"expr">`。

        使用示例:
        - SymbolIterType.parse_parameters(parser)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        parser.parse_punctuation("<", "Expected '<' for symbol iter type.")
        parser.parse_keyword("start", " in symbol.iter type")
        parser.parse_characters("=", " in symbol.iter type")
        start = parser.parse_attribute()
        if not isinstance(start, SymbolExprAttr):
            parser.raise_error("symbol.iter start expects SymbolExprAttr")
        parser.parse_characters(",", " in symbol.iter type")
        parser.parse_keyword("end", " in symbol.iter type")
        parser.parse_characters("=", " in symbol.iter type")
        end = parser.parse_attribute()
        if not isinstance(end, SymbolExprAttr):
            parser.raise_error("symbol.iter end expects SymbolExprAttr")
        parser.parse_characters(",", " in symbol.iter type")
        parser.parse_keyword("step", " in symbol.iter type")
        parser.parse_characters("=", " in symbol.iter type")
        step = parser.parse_attribute()
        if not isinstance(step, SymbolExprAttr):
            parser.raise_error("symbol.iter step expects SymbolExprAttr")
        parser.parse_punctuation(">", "Expected '>' for symbol iter type.")
        return (start, end, step)

    def print_parameters(self: "SymbolIterType", printer: Printer) -> None:
        """打印循环迭代类型参数。


        功能说明:
        - 输出 `!symbol.iter<start = #symbol.expr<...>, end = #symbol.expr<...>, step = #symbol.expr<...>>` 的表达式参数。

        使用示例:
        - SymbolIterType.from_bounds("0", "N", "TILE_D0").print_parameters(printer)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        printer.print_string("<start = ")
        printer.print_attribute(self.start)
        printer.print_string(", end = ")
        printer.print_attribute(self.end)
        printer.print_string(", step = ")
        printer.print_attribute(self.step)
        printer.print_string(">")

    def verify(self: "SymbolIterType") -> None:
        """校验循环迭代类型参数。


        功能说明:
        - 复用 symbol.expr 的合法性校验，确保 start/end/step 都合法。

        使用示例:
        - SymbolIterType.from_bounds("0", "N", "TILE_D0").verify()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        self.start.verify()
        self.end.verify()
        self.step.verify()

    def __str__(self: "SymbolIterType") -> str:
        """返回公开的 symbol.iter 文本表示。


        功能说明:
        - 生成 `symbol.iter<start,end,step>` 形式的字符串表示。

        使用示例:
        - str(SymbolIterType.from_bounds("0", "N", "TILE_D0"))

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
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


        功能说明:
        - 统一创建 `!symbol.iter<start = #symbol.expr<...>, end = #symbol.expr<...>, step = #symbol.expr<...>>`。

        使用示例:
        - SymbolIterType.from_bounds("0", "N", "TILE_D0")

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
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


        功能说明:
        - 将 `#symbol.iter<...>` 转换为对应的 `!symbol.iter<...>` 类型。

        使用示例:
        - SymbolIterType.from_attr(SymbolIterAttr.from_bounds("0", "N", "TILE_D0"))

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        return cls(attr.start, attr.end, attr.step)


@irdl_attr_definition
class SymbolPtrType(ParametrizedAttribute, TypeAttribute):
    """符号指针类型。


    功能说明:
    - 表示 `!symbol.ptr<dtype>` 的指针类型承载。
    - 作为 DSL `Ptr(dtype)` 与 IR 类型的唯一桥接入口。

    使用示例:
    - SymbolPtrType(f32)

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    name = "symbol.ptr"

    dtype: Attribute = param_def(Attribute)

    @classmethod
    def parse_parameters(cls: type["SymbolPtrType"], parser: AttrParser) -> Sequence[Attribute]:
        """解析 symbol.ptr 类型参数。


        功能说明:
        - 解析 `!symbol.ptr<dtype>` 中的 dtype。

        使用示例:
        - SymbolPtrType.parse_parameters(parser)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        parser.parse_punctuation("<", "Expected '<' for symbol ptr type.")
        dtype = parser.parse_type()
        parser.parse_punctuation(">", "Expected '>' for symbol ptr type.")
        return (dtype,)

    def print_parameters(self: "SymbolPtrType", printer: Printer) -> None:
        """打印 symbol.ptr 类型参数。


        功能说明:
        - 输出 `!symbol.ptr<dtype>` 的 dtype 部分。

        使用示例:
        - SymbolPtrType(f32).print_parameters(printer)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        printer.print_string("<")
        printer.print_attribute(self.dtype)
        printer.print_string(">")

    def verify(self: "SymbolPtrType") -> None:
        """校验 symbol.ptr 的 dtype。


        功能说明:
        - 要求 dtype 为合法 TypeAttribute。
        - 明确拒绝 `!symbol.int<...>` 作为 ptr dtype。

        使用示例:
        - SymbolPtrType(f32).verify()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        if not isinstance(self.dtype, TypeAttribute):
            _raise_verify_error("symbol.ptr dtype must be type")
        if isinstance(self.dtype, SymbolValueType):
            _raise_verify_error("symbol.ptr dtype must not be symbol.int")


class _BaseSymbolBinaryArithOp(IRDLOperation, HasFolderInterface):
    """symbol 二元整数算术 op 基类。"""

    traits = traits_def(Pure())
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


        功能说明:
        - 设置两个 `!symbol.int<#symbol.expr<expr>>` 操作数与单个 `!symbol.int<#symbol.expr<expr>>` 结果类型。

        使用示例:
        - SymbolAddOp(lhs, rhs, SymbolValueType.from_expr("M + 1"))

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        super().__init__(operands=[lhs, rhs], result_types=[result_type])

    def verify_(self: "_BaseSymbolBinaryArithOp") -> None:
        """校验 symbol 二元整数算术 op 的类型约束。


        功能说明:
        - 校验 `lhs`、`rhs` 为 `!symbol.int<#symbol.expr<expr>>` 或循环迭代 `!symbol.iter<...>`。
        - 校验 `result` 为 `!symbol.int<#symbol.expr<expr>>`。

        使用示例:
        - SymbolMulOp(lhs, rhs, SymbolValueType.from_expr("M*N")).verify_()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        for field_name in ("lhs", "rhs"):
            operand = SSAValue.get(getattr(self, field_name))
            if not _is_symbol_arith_operand_type(operand.type):
                _raise_verify_error(f"{self.name} {field_name} must have type !symbol.int<#symbol.expr<expr>> or !symbol.iter<...>")
        if not _is_symbol_int_type(self.result.type):
            _raise_verify_error(f"{self.name} result type must be !symbol.int<#symbol.expr<expr>>")
        lhs_type = SSAValue.get(self.lhs).type
        rhs_type = SSAValue.get(self.rhs).type
        result_type = SSAValue.get(self.result).type
        if _requires_unknown_arith_result(lhs_type, rhs_type) and not _is_unknown_symbol_int_type(result_type):
            _raise_verify_error(f"{self.name} result type must be !symbol.int<#symbol.expr<?>> when operand is !symbol.iter<...> or !symbol.int<#symbol.expr<?>>")
        if not _requires_unknown_arith_result(lhs_type, rhs_type) and isinstance(result_type, SymbolValueType):
            inferred_expr = _infer_symbol_arith_result_expr(self.name, lhs_type, rhs_type)
            if inferred_expr is not None and result_type.get_value() != _UNKNOWN_SYMBOL_EXPR:
                expected_type = SymbolValueType.from_expr(inferred_expr)
                if result_type != expected_type:
                    _raise_verify_error(f"{self.name} result type must match canonical symbol expression")

    def fold(self: "_BaseSymbolBinaryArithOp") -> Sequence[SSAValue | Attribute] | None:
        """折叠静态整数 symbol 二元算术 op。


        功能说明:
        - 仅当 lhs/rhs 都是静态整数 `!symbol.int` 时折叠。
        - result 为 `!symbol.int<#symbol.expr<??>>` 时仍可物化确定 `symbol.const`。
        - 动态 symbol、`?` 与 iter 表达一律保守返回 `None`，避免误折叠。

        使用示例:
        - SymbolAddOp(SymbolConstOp(1).result, SymbolConstOp(2).result, SymbolValueType.from_expr("3")).fold()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
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
        elif self.name == "symbol.min":
            result_value = min(lhs_value, rhs_value)
        else:
            return None

        result_expr = result_type.get_value()
        if result_expr != _UNKNOWN_SYMBOL_EXPR and result_expr != result_value:
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


class _BaseSymbolCompareOp(IRDLOperation, HasFolderInterface):
    """symbol 二元整数比较 op 基类。"""

    traits = traits_def(Pure())
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


        功能说明:
        - 设置两个 `!symbol.int<#symbol.expr<expr>>` 操作数与单个 `i1` 结果类型。

        使用示例:
        - SymbolEqOp(lhs, rhs, i1)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        super().__init__(operands=[lhs, rhs], result_types=[result_type])

    def verify_(self: "_BaseSymbolCompareOp") -> None:
        """校验 symbol 二元整数比较 op 的类型约束。


        功能说明:
        - 校验 `lhs` 与 `rhs` 均为 `!symbol.int<#symbol.expr<expr>>` 或循环迭代 `!symbol.iter<...>`。
        - 校验 `result` 固定为 `i1`。

        使用示例:
        - SymbolLtOp(lhs, rhs, i1).verify_()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        for field_name in ("lhs", "rhs"):
            operand = SSAValue.get(getattr(self, field_name))
            if not _is_symbol_arith_operand_type(operand.type):
                _raise_verify_error(f"{self.name} {field_name} must have type !symbol.int<#symbol.expr<expr>> or !symbol.iter<...>")
        if self.result.type != i1:
            _raise_verify_error(f"{self.name} result type must be i1")

    def fold(self: "_BaseSymbolCompareOp") -> Sequence[SSAValue | Attribute] | None:
        """折叠静态整数 symbol 比较 op。

        功能说明:
        - 仅当 lhs/rhs 均为静态整数 `!symbol.int` 时折叠。
        - 结果固定物化为 `i1` bool 常量。
        - 动态 symbol、`?` 与 iter operand 不折叠。

        使用示例:
        - SymbolEqOp(SymbolConstOp(1).result, SymbolConstOp(1).result).fold()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        lhs_value = _get_concrete_symbol_int_value(SSAValue.get(self.lhs).type)
        rhs_value = _get_concrete_symbol_int_value(SSAValue.get(self.rhs).type)
        if lhs_value is None or rhs_value is None or self.result.type != i1:
            return None
        if self.name == "symbol.eq":
            result_value = lhs_value == rhs_value
        elif self.name == "symbol.ne":
            result_value = lhs_value != rhs_value
        elif self.name == "symbol.lt":
            result_value = lhs_value < rhs_value
        elif self.name == "symbol.le":
            result_value = lhs_value <= rhs_value
        elif self.name == "symbol.gt":
            result_value = lhs_value > rhs_value
        elif self.name == "symbol.ge":
            result_value = lhs_value >= rhs_value
        else:
            return None
        return (IntegerAttr.from_bool(result_value),)

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
    traits = traits_def(Pure())

    value = attr_def(IntAttr)
    result = result_def(SymbolValueType)

    def __init__(
        self: "SymbolConstOp",
        value: int | IntAttr,
        result_type: SymbolValueType | None = None,
    ) -> None:
        """初始化 symbol.const。


        功能说明:
        - 记录整数常量 attribute，并生成对应的 `!symbol.int<#symbol.expr<...>>` 结果类型。
        - 公开构造只接受 Python `int` 或 `IntAttr`；`IntegerAttr` 属于 arith/builtin 常量属性，不作为 `symbol.const` 输入。
        - `bool` 与 `IntAttr(data=True/False)` 不是 symbol 整数常量输入；布尔比较 fold 由 `arith.constant i1` 承接。

        使用示例:
        - SymbolConstOp(3)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        if isinstance(value, IntAttr):
            if isinstance(value.data, bool):
                raise TypeError("SymbolConstOp value must be non-bool int or IntAttr with non-bool data")
            value_attr = value
        elif isinstance(value, int):
            if isinstance(value, bool):
                raise TypeError("SymbolConstOp value must be non-bool int or IntAttr with non-bool data")
            value_attr = IntAttr(value)
        else:
            raise TypeError("SymbolConstOp value must be non-bool int or IntAttr with non-bool data")
        inferred_type = result_type or SymbolValueType.from_expr(str(value_attr.data))
        super().__init__(result_types=[inferred_type], attributes={"value": value_attr})

    def verify_(self: "SymbolConstOp") -> None:
        """校验 symbol.const 的类型约束。


        功能说明:
        - 校验 value 必须为整型 attribute。
        - 校验 result 必须是 `!symbol.int<#symbol.expr<...>>`，且表达式与常量值一致。

        使用示例:
        - SymbolConstOp(3).verify_()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        if not isinstance(self.value, IntAttr):
            _raise_verify_error(f"{self.name} value must be integer attribute")
        if not isinstance(self.result.type, SymbolValueType):
            _raise_verify_error(f"{self.name} result type must be !symbol.int<#symbol.expr<expr>>")
        expected_type = SymbolValueType.from_expr(str(self.value.data))
        if self.result.type != expected_type:
            _raise_verify_error(f"{self.name} result type must match value")

    def print(self: "SymbolConstOp", printer: Printer) -> None:
        """打印 symbol.const 自定义文本语法。


        功能说明:
        - 输出 `symbol.const <value> : !symbol.int<#symbol.expr<...>>` 的文本形式。

        使用示例:
        - SymbolConstOp(3)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        printer.print_string(" ")
        printer.print_string(str(self.value.data))
        printer.print_string(" : ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls: type["SymbolConstOp"], parser: AttrParser) -> "SymbolConstOp":
        """解析 symbol.const 自定义文本语法。


        功能说明:
        - 解析整数常量与 `!symbol.int<#symbol.expr<...>>` 结果类型。

        使用示例:
        - SymbolConstOp.parse(parser)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        value = parser.parse_integer(allow_boolean=False, allow_negative=True, context_msg=f" in {cls.name}")
        parser.parse_characters(":", f" in {cls.name}")
        result_type = parser.parse_type()
        return cls(value, result_type)


class SymbolConstantMaterializationInterface(ConstantMaterializationInterface):
    """将 folded 常量 materialize 为对应公开 IR operation。


    功能说明:
    - 为 xdsl folding 提供 symbol dialect 常量物化入口，不新增独立 cleanup pass。
    - `IntegerAttr + i1` 对应 symbol compare fold，物化为 `arith.constant`。
    - `IntAttr + SymbolValueType` 对应 symbol arithmetic fold，物化为 `symbol.const`。
    - `!symbol.int<#symbol.expr<??>>` result 接收确定 `IntAttr` 并物化为确定 `SymbolConstOp`。
    - 其它 value/type 组合返回 `None`，由 folding 框架保守保留原 op。

    使用示例:
    - SymbolConstantMaterializationInterface().materialize_constant(IntAttr(3), SymbolValueType.from_expr("3"))
    - SymbolConstantMaterializationInterface().materialize_constant(IntAttr(3), SymbolValueType.from_expr("?"))
    - SymbolConstantMaterializationInterface().materialize_constant(IntegerAttr.from_bool(True), i1)

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    def materialize_constant(self, value: Attribute, type: Attribute) -> Operation | None:
        """把 folded 常量 materialize 为公开 IR operation。

        功能说明:
        - `IntegerAttr + i1` 对应 symbol compare fold，物化为 `arith.constant`。
        - `IntAttr + SymbolValueType` 对应 symbol arithmetic fold，物化为 `symbol.const`。
        - `!symbol.int<#symbol.expr<??>>` 结果类型接收确定 `IntAttr` 并返回确定 `SymbolConstOp`。
        - 其它 value/type 组合返回 `None`，交由 folding 框架保守保留原 op。

        使用示例:
        - SymbolConstantMaterializationInterface().materialize_constant(IntAttr(3), SymbolValueType.from_expr("?"))
        - SymbolConstantMaterializationInterface().materialize_constant(IntegerAttr.from_bool(True), i1)
        """

        if isinstance(value, IntegerAttr) and type == i1:
            return arith.ConstantOp(value)
        if not isinstance(value, IntAttr):
            return None
        if not isinstance(type, SymbolValueType):
            return None
        type_value = type.get_value()
        if type_value == _UNKNOWN_SYMBOL_EXPR:
            return SymbolConstOp(value)
        if type_value != value.data:
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
class SymbolMinOp(_BaseSymbolBinaryArithOp):
    """两个 symbol.int 值的整数最小值。"""

    name = "symbol.min"


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
    traits = traits_def(Pure())

    source = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(
        self: "SymbolToFloatOp",
        source: SSAValue | Operation,
        result_type: Attribute = f32,
    ) -> None:
        """初始化 symbol.to_float。


        功能说明:
        - 设置单个 `!symbol.int<#symbol.expr<expr>>` 操作数与浮点结果类型。

        使用示例:
        - SymbolToFloatOp(source, f32)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        super().__init__(operands=[source], result_types=[result_type])

    def verify_(self: "SymbolToFloatOp") -> None:
        """校验 symbol.to_float 的类型约束。


        功能说明:
        - 校验 source 必须为 `!symbol.int<#symbol.expr<expr>>`。
        - 校验 result 必须为浮点类型。

        使用示例:
        - SymbolToFloatOp(source, f32).verify_()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        source_value = SSAValue.get(self.source)
        if not _is_symbol_int_type(source_value.type):
            _raise_verify_error(f"{self.name} source must have type !symbol.int<#symbol.expr<expr>>")
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
    traits = traits_def(Pure())

    source = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(
        self: "SymbolToIntOp",
        source: SSAValue | Operation,
        result_type: Attribute = i32,
    ) -> None:
        """初始化 symbol.to_int。


        功能说明:
        - 设置单个 `!symbol.int<#symbol.expr<expr>>` 操作数与普通整型结果类型。

        使用示例:
        - SymbolToIntOp(source, i32)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        super().__init__(operands=[source], result_types=[result_type])

    def verify_(self: "SymbolToIntOp") -> None:
        """校验 symbol.to_int 的类型约束。


        功能说明:
        - 校验 source 必须为 `!symbol.int<#symbol.expr<expr>>`。
        - 校验 result 必须为 builtin 整型（`IntegerType`）。

        使用示例:
        - SymbolToIntOp(source, i32).verify_()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        source_value = SSAValue.get(self.source)
        if not _is_symbol_int_type(source_value.type):
            _raise_verify_error(f"{self.name} source must have type !symbol.int<#symbol.expr<expr>>")
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
    traits = traits_def(Pure())

    source = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(
        self: "SymbolCastOp",
        source: SSAValue | Operation,
        result_type: Attribute = i32,
    ) -> None:
        """初始化 symbol.cast。


        功能说明:
        - 设置单个 `!symbol.int<#symbol.expr<expr>>` 操作数与普通整型结果类型。
        - 供 `emit_c/npu_demo` 读取 `symbol.cast` 文本输入。

        使用示例:
        - SymbolCastOp(source, i32)

        关联文件:
        - spec: spec/dsl/gen_kernel/emit.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        super().__init__(operands=[source], result_types=[result_type])

    def verify_(self: "SymbolCastOp") -> None:
        """校验 symbol.cast 的类型约束。


        功能说明:
        - 校验 source 必须为 `!symbol.int<#symbol.expr<expr>>`。
        - 校验 result 必须为 builtin 整型。

        使用示例:
        - SymbolCastOp(source, i32).verify_()

        关联文件:
        - spec: spec/dsl/gen_kernel/emit.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """
        source_value = SSAValue.get(self.source)
        if not _is_symbol_int_type(source_value.type):
            _raise_verify_error(f"{self.name} source must have type !symbol.int<#symbol.expr<expr>>")
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
        - test: test/dialect/test_symbol.py
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


        功能说明:
        - 校验 source 必须为 `NnMemoryType`、axis 合法，且目标条目不是匿名动态值 `?`。

        使用示例:
        - SymbolGetStrideOp(source, 0).verify_()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
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
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
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


@irdl_op_definition
class SymbolYieldOp(IRDLOperation):
    """承载 symbol.for 单个 carried `!symbol.int<#symbol.expr<...>>` 的循环末尾值。"""

    name = "symbol.yield"

    value = operand_def(Attribute)
    traits = traits_def(IsTerminator())

    def __init__(self: "SymbolYieldOp", value: SSAValue | Operation) -> None:
        """初始化 symbol.yield。


        功能说明:
        - 构造仅承载一个 `!symbol.int<#symbol.expr<...>>` operand 的 terminator。
        - 该 op 只服务带 carried-value 的 `symbol.for` 循环体。

        使用示例:
        - SymbolYieldOp(value)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        super().__init__(operands=[value])

    def verify_(self: "SymbolYieldOp") -> None:
        """校验 symbol.yield 只能在 carried symbol.for 末尾使用。


        功能说明:
        - 要求 `value` 类型固定为 `!symbol.int<#symbol.expr<...>>`。
        - 要求当前 op 位于带单个 carried `!symbol.int<#symbol.expr<...>>` 的 `symbol.for` 单块 region 末尾。

        使用示例:
        - SymbolYieldOp(value).verify()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        if not _is_symbol_int_type(SSAValue.get(self.value).type):
            _raise_verify_error(f"{self.name} value must have type !symbol.int<#symbol.expr<expr>>")

        parent_op = self.parent_op()
        if not isinstance(parent_op, SymbolForOp):
            _raise_verify_error(f"{self.name} must appear inside symbol.for")
        if parent_op.init is None or parent_op.result is None:
            _raise_verify_error(f"{self.name} requires symbol.for loop-carried !symbol.int<#symbol.expr<expr>>")

        parent_block = self.parent_block()
        if parent_block is None or parent_block.last_op is not self:
            _raise_verify_error(f"{self.name} must terminate symbol.for body")

    def print(self: "SymbolYieldOp", printer: Printer) -> None:
        """打印 symbol.yield 自定义文本语法。


        功能说明:
        - 输出 `symbol.yield %value : !symbol.int<#symbol.expr<...>>` 形式文本。

        使用示例:
        - SymbolYieldOp(value).print(printer)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        printer.print_string(" ")
        printer.print_ssa_value(self.value)
        printer.print_string(" : ")
        printer.print_attribute(SSAValue.get(self.value).type)

    @classmethod
    def parse(cls: type["SymbolYieldOp"], parser: AttrParser) -> "SymbolYieldOp":
        """解析 symbol.yield 自定义文本语法。


        功能说明:
        - 解析 `symbol.yield %value : !symbol.int<#symbol.expr<...>>`。
        - 在解析阶段把 unresolved operand 解析为具体验证类型，保持 print 后再 parse 闭环。

        使用示例:
        - SymbolYieldOp.parse(parser)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
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


        功能说明:
        - 设置 `start/end/step` 三个 `!symbol.int<#symbol.expr<...>>` 操作数与单块循环体。
        - 兼容旧的无 carried-value 形式，也支持通过 `init` 构造单个 loop-carried `!symbol.int<#symbol.expr<...>>` 结果。
        - `iter` attribute 与块参数类型共同表达迭代边界语义。

        使用示例:
        - SymbolForOp(start, end, step, Block(arg_types=[SymbolIterType.from_bounds("0", "M", "TILE_D0")]))
        - SymbolForOp(start, end, step, Block(arg_types=[SymbolIterType.from_bounds("0", "M", "TILE_D0"), SymbolValueType.from_expr("ACC")]), init=zero, result_type=SymbolValueType.from_expr("TOTAL"))

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
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


        功能说明:
        - 校验 start/end/step 均为 `!symbol.int<\"expr\">`。
        - 校验 `iter` attribute 与 block 参数类型一致。
        - 校验 region 为单块；无 carried-value 时仅包含 `it` 一个块参数，带 carried-value 时包含 `it/acc` 两个块参数。
        - 校验 loop-carried `!symbol.int<#symbol.expr<...>>` 的 `init/result/symbol.yield` 口径与 terminator 形状。
        - 当 step 可静态判定为 `0` 时直接报错。

        使用示例:
        - SymbolForOp(start, end, step, body).verify_()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol.py
        """

        start_value = SSAValue.get(self.start)
        end_value = SSAValue.get(self.end)
        step_value = SSAValue.get(self.step)
        for operand_name, operand in (("start", start_value), ("end", end_value), ("step", step_value)):
            if not _is_symbol_int_type(operand.type):
                _raise_verify_error(f"{self.name} {operand_name} must have type !symbol.int<#symbol.expr<expr>>")

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
            _raise_verify_error(f"{self.name} loop-carried !symbol.int<#symbol.expr<expr>> requires init operand")
        if carried_init is not None and carried_result is None:
            _raise_verify_error(f"{self.name} loop-carried !symbol.int<#symbol.expr<expr>> requires single symbol.int result")
        expected_block_args = 2 if has_carried else 1
        if len(block.args) != expected_block_args:
            if has_carried:
                _raise_verify_error(f"{self.name} loop-carried !symbol.int<#symbol.expr<expr>> requires exactly two block arguments")
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
            _raise_verify_error(f"{self.name} loop-carried init must have type !symbol.int<#symbol.expr<expr>>")
        if not _is_symbol_int_type(block.args[1].type):
            _raise_verify_error(f"{self.name} loop-carried acc must have type !symbol.int<#symbol.expr<expr>>")
        if not _is_symbol_int_type(carried_result.type):
            _raise_verify_error(f"{self.name} loop-carried result must have type !symbol.int<#symbol.expr<expr>>")

        terminator = block.last_op
        if not isinstance(terminator, SymbolYieldOp):
            _raise_verify_error(f"{self.name} loop-carried body must terminate with symbol.yield")
        if not _is_symbol_int_type(SSAValue.get(terminator.value).type):
            _raise_verify_error(f"{self.name} loop-carried yield must have type !symbol.int<#symbol.expr<expr>>")

    def print(self: "SymbolForOp", printer: Printer) -> None:
        """打印 symbol.for 自定义文本语法。


        功能说明:
        - 无 carried-value 时输出旧文本语法。
        - 带 carried-value 时输出 `iter_args(%acc = %init) {iter = ...} -> !symbol.int<#symbol.expr<...>> { ... }`，与 parser 使用同一公开顺序。

        使用示例:
        - SymbolForOp(start, end, step, body, init=zero).print(printer)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
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
                    printer.print_string("\n")
                    printer.print_op(op)
            printer.print_string("\n", indent=0)
        else:
            printer.print_string("\n", indent=0)
        printer.print_string("}")

    @classmethod
    def parse(cls: type["SymbolForOp"], parser: AttrParser) -> "SymbolForOp":
        """解析 symbol.for 自定义文本语法。


        功能说明:
        - 解析旧的 `symbol.for %it = %start to %end step %step {iter = #symbol.iter<...>} { ... }`。
        - 解析新的 `symbol.for %it = %start to %end step %step iter_args(%acc = %zero) {iter = #symbol.iter<...>} -> !symbol.int<#symbol.expr<...>> { ... }`。
        - 迭代变量与 carried `acc` 都在进入 region 前完成类型解析，保持 print 后再 parse 闭环。

        使用示例:
        - SymbolForOp.parse(parser)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/test_symbol.py
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
            raise VerifyException(_format_error("symbol.for result type requires loop-carried !symbol.int<#symbol.expr<expr>>"))
        if init_value is not None:
            if not isinstance(result_type, SymbolValueType):
                raise VerifyException(_format_error("symbol.for loop-carried result must be !symbol.int<#symbol.expr<expr>>"))
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
        SymbolMinOp,
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
    "SymbolMinOp",
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
