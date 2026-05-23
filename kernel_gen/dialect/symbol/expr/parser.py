"""symbol expression parser and normalizer.

功能说明:
- 承载 symbol 表达式节点、解析、格式化、规范化与静态求值 helper。

API 列表:
- 包内实现模块，无 root 公开 API。

使用示例:
- `from kernel_gen.dialect.symbol.expr import ...`

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/symbol/
- 功能实现: kernel_gen/dialect/symbol/expr/parser.py
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

from ..common import _format_error, _raise_type_error, _raise_value_error, _raise_verify_error

_SYMBOL_EXPR_TOKEN_PATTERN = re.compile(
    r"\s*(?:(?P<int>[0-9]+)|(?P<ident>[A-Za-z_][A-Za-z0-9_]*)|(?P<punct>[()+\-*,?<>])|(?P<invalid>.))",
    re.DOTALL,
)
_SYMBOL_EXPR_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SYMBOL_PTR_TEMPLATE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ERROR_SCENE = "dialect.symbol"
_UNKNOWN_SYMBOL_EXPR = "?"
_SYMBOL_EXPR_EXPR_PRECEDENCE = 10
_SYMBOL_EXPR_TERM_PRECEDENCE = 20
_SYMBOL_EXPR_UNARY_PRECEDENCE = 30
_SYMBOL_EXPR_ATOM_PRECEDENCE = 40

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
    - 支持 `+`、`-`、`*`、`floordiv`、`ceildiv`、`mod`、`min(lhs, rhs)`、`max(lhs, rhs)`、`iter<start,end,step>`、括号与 `?`。

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
        - 支持整数、标识符、`?`、括号、一元正负号、`iter<start,end,step>` 与二元 `min(lhs, rhs)`。

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
        if self.consume_keyword("iter"):
            self.expect_punctuation("<")
            start = self.parse_expression()
            self.expect_punctuation(",")
            end = self.parse_expression()
            self.expect_punctuation(",")
            step = self.parse_expression()
            self.expect_punctuation(">")
            return _make_symbol_expr_iter(start, end, step)
        identifier = self.consume_identifier()
        if identifier is not None:
            return _make_symbol_expr_symbol(identifier)
        if self.consume_punctuation("("):
            node = self.parse_expression()
            self.expect_punctuation(")")
            return node
        self.raise_parse_error("symbol expr must contain identifiers, ?, integers, +, -, *, floordiv, ceildiv, mod, min(lhs, rhs), max(lhs, rhs) or iter<start,end,step>")

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
        - 标识符表示具名 symbol value。

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
            if token.kind == "ident" and token.text not in {"floordiv", "ceildiv", "mod", "min", "max", "iter"}:
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
            _raise_verify_error("symbol expr contains unsupported token")
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
            _raise_verify_error("symbol expr contains unsupported token")
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

    if _SYMBOL_EXPR_NAME_PATTERN.fullmatch(value) is None:
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


def _contains_symbol_expr_unknown(node: _SymbolExprNode) -> bool:
    """判断表达树是否包含 unknown。

    功能说明:
    - 识别 `iter<start,end,step>` 子表达中的 `?`，供算术结果保守传播。

    使用示例:
    - _contains_symbol_expr_unknown(node)
    """

    return _is_symbol_expr_unknown(node) or any(_contains_symbol_expr_unknown(arg) for arg in node.args)


def _contains_symbol_expr_iter(node: _SymbolExprNode) -> bool:
    """判断表达树是否包含 iter token。

    功能说明:
    - 含 iter token 的 `min/max` 需要保留调用顺序，避免 tail 表达式被重排。

    使用示例:
    - has_iter = _contains_symbol_expr_iter(node)
    """

    return node.kind == "iter" or any(_contains_symbol_expr_iter(arg) for arg in node.args)


def _make_symbol_expr_iter(start: _SymbolExprNode, end: _SymbolExprNode, step: _SymbolExprNode) -> _SymbolExprNode:
    """构造 `iter<start,end,step>` token 表达节点。

    功能说明:
    - 该节点表示 `SymbolIterType` 的值语义 token，不从 SSA 名称或 dump 文本派生。
    - start/end/step 已在子表达 parser 中完成 canonicalize。

    使用示例:
    - _make_symbol_expr_iter(start, end, step)
    """

    return _SymbolExprNode("iter", args=(start, end, step))


def _get_symbol_expr_const(node: _SymbolExprNode) -> int | None:
    """提取常量节点的整数值。

    功能说明:
    - 非常量返回 `None`。

    使用示例:
    - _get_symbol_expr_const(node)
    """

    return int(node.value) if node.kind == "const" and isinstance(node.value, int) else None


def _get_concrete_symbol_expr_node_value(node: _SymbolExprNode) -> int | None:
    """计算纯静态整数表达节点。

    功能说明:
    - 只处理由常量和整数算术构成的表达节点。
    - 遇到具名 symbol、`?`、`iter<...>`、`min/max` 或除零时返回 `None`，由调用方保守拒绝。

    使用示例:
    - value = _get_concrete_symbol_expr_node_value(_parse_symbol_expr_from_text("8 + 4"))
    """

    const = _get_symbol_expr_const(node)
    if const is not None:
        return const
    if node.kind == "neg":
        value = _get_concrete_symbol_expr_node_value(node.args[0])
        return -value if value is not None else None
    if node.kind == "add":
        values = [_get_concrete_symbol_expr_node_value(arg) for arg in node.args]
        if any(value is None for value in values):
            return None
        return sum(value for value in values if value is not None)
    if node.kind == "sub":
        lhs = _get_concrete_symbol_expr_node_value(node.args[0])
        rhs = _get_concrete_symbol_expr_node_value(node.args[1])
        return lhs - rhs if lhs is not None and rhs is not None else None
    if node.kind == "mul":
        values = [_get_concrete_symbol_expr_node_value(arg) for arg in node.args]
        if any(value is None for value in values):
            return None
        product = 1
        for value in values:
            if value is not None:
                product *= value
        return product
    if node.kind in {"floordiv", "ceildiv", "mod"}:
        lhs = _get_concrete_symbol_expr_node_value(node.args[0])
        rhs = _get_concrete_symbol_expr_node_value(node.args[1])
        if lhs is None or rhs is None or rhs == 0:
            return None
        if node.kind == "floordiv":
            return lhs // rhs
        if node.kind == "ceildiv":
            return -(-lhs // rhs)
        return lhs % rhs
    return None


def _linear_symbol_expr_terms(node: _SymbolExprNode) -> tuple[dict[str, int], int] | None:
    """提取一阶 symbol 表达式的系数表。

    功能说明:
    - 仅处理常量、具名 symbol、加减和常量乘一阶表达式。
    - 遇到 `?`、`iter<...>`、`min/max` 或非线性乘法时返回 `None`，调用方保守拒绝。

    使用示例:
    - linear = _linear_symbol_expr_terms(_parse_symbol_expr_from_text("B + 24"))
    """

    const = _get_symbol_expr_const(node)
    if const is not None:
        return ({}, const)
    if node.kind == "symbol":
        return ({str(node.value): 1}, 0)
    if node.kind == "neg":
        operand = _linear_symbol_expr_terms(node.args[0])
        if operand is None:
            return None
        terms, offset = operand
        return ({name: -coeff for name, coeff in terms.items()}, -offset)
    if node.kind == "add":
        combined: dict[str, int] = {}
        offset = 0
        for arg in node.args:
            parsed = _linear_symbol_expr_terms(arg)
            if parsed is None:
                return None
            terms, arg_offset = parsed
            offset += arg_offset
            for name, coeff in terms.items():
                combined[name] = combined.get(name, 0) + coeff
        return ({name: coeff for name, coeff in combined.items() if coeff != 0}, offset)
    if node.kind == "sub":
        lhs = _linear_symbol_expr_terms(node.args[0])
        rhs = _linear_symbol_expr_terms(node.args[1])
        if lhs is None or rhs is None:
            return None
        lhs_terms, lhs_offset = lhs
        rhs_terms, rhs_offset = rhs
        combined = dict(lhs_terms)
        for name, coeff in rhs_terms.items():
            combined[name] = combined.get(name, 0) - coeff
        return ({name: coeff for name, coeff in combined.items() if coeff != 0}, lhs_offset - rhs_offset)
    if node.kind == "mul":
        linear: tuple[dict[str, int], int] | None = None
        const_product = 1
        for arg in node.args:
            arg_const = _get_symbol_expr_const(arg)
            if arg_const is not None:
                const_product *= arg_const
                continue
            if linear is not None:
                return None
            linear = _linear_symbol_expr_terms(arg)
            if linear is None:
                return None
        if linear is None:
            return ({}, const_product)
        terms, offset = linear
        return ({name: coeff * const_product for name, coeff in terms.items()}, offset * const_product)
    return None


def _make_symbol_expr_neg(node: _SymbolExprNode) -> _SymbolExprNode:
    """构造一元负号表达。

    功能说明:
    - 常量直接折叠；unknown 继续传播。

    使用示例:
    - _make_symbol_expr_neg(_make_symbol_expr_symbol("N"))
    """

    if _contains_symbol_expr_unknown(node):
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

    if _contains_symbol_expr_unknown(lhs) or _contains_symbol_expr_unknown(rhs):
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

    if _contains_symbol_expr_unknown(lhs) or _contains_symbol_expr_unknown(rhs):
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

    if _contains_symbol_expr_unknown(lhs) or _contains_symbol_expr_unknown(rhs):
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

    if _contains_symbol_expr_unknown(lhs) or _contains_symbol_expr_unknown(rhs):
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
    - 支持二元 min、常量折叠、交换律排序、iter token 稳定排序与 `?` 传播。

    使用示例:
    - _make_symbol_expr_min(lhs, rhs)
    """

    if _contains_symbol_expr_unknown(lhs) or _contains_symbol_expr_unknown(rhs):
        return _make_symbol_expr_unknown()
    lhs_const = _get_symbol_expr_const(lhs)
    rhs_const = _get_symbol_expr_const(rhs)
    if lhs_const is not None and rhs_const is not None:
        return _make_symbol_expr_const(min(lhs_const, rhs_const))
    if lhs == rhs:
        return lhs
    lhs_has_iter = _contains_symbol_expr_iter(lhs)
    rhs_has_iter = _contains_symbol_expr_iter(rhs)
    if lhs_has_iter != rhs_has_iter:
        ordered = (rhs, lhs) if lhs_has_iter else (lhs, rhs)
        return _SymbolExprNode("min", args=ordered)
    if lhs_has_iter and rhs_has_iter:
        return _SymbolExprNode("min", args=(lhs, rhs))
    ordered = tuple(sorted((lhs, rhs), key=_format_symbol_expr_node))
    return _SymbolExprNode("min", args=ordered)


def _make_symbol_expr_max(lhs: _SymbolExprNode, rhs: _SymbolExprNode) -> _SymbolExprNode:
    """构造 canonical `max(lhs, rhs)` 表达。

    功能说明:
    - 支持二元 max、常量折叠、交换律排序、iter token 稳定排序与 `?` 传播。

    使用示例:
    - _make_symbol_expr_max(lhs, rhs)
    """

    if _contains_symbol_expr_unknown(lhs) or _contains_symbol_expr_unknown(rhs):
        return _make_symbol_expr_unknown()
    lhs_const = _get_symbol_expr_const(lhs)
    rhs_const = _get_symbol_expr_const(rhs)
    if lhs_const is not None and rhs_const is not None:
        return _make_symbol_expr_const(max(lhs_const, rhs_const))
    if lhs == rhs:
        return lhs
    lhs_has_iter = _contains_symbol_expr_iter(lhs)
    rhs_has_iter = _contains_symbol_expr_iter(rhs)
    if lhs_has_iter != rhs_has_iter:
        ordered = (rhs, lhs) if lhs_has_iter else (lhs, rhs)
        return _SymbolExprNode("max", args=ordered)
    if lhs_has_iter and rhs_has_iter:
        return _SymbolExprNode("max", args=(lhs, rhs))
    ordered = tuple(sorted((lhs, rhs), key=_format_symbol_expr_node))
    return _SymbolExprNode("max", args=ordered)


def _symbol_expr_precedence(node: _SymbolExprNode) -> int:
    """返回表达节点打印优先级。

    功能说明:
    - 用于生成可稳定重新解析的 canonical 文本。

    使用示例:
    - _symbol_expr_precedence(node)
    """

    if node.kind in {"const", "symbol", "unknown", "iter", "min", "max"}:
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
    elif node.kind == "iter":
        start, end, step = node.args
        text = f"iter<{_format_symbol_expr_node(start)},{_format_symbol_expr_node(end)},{_format_symbol_expr_node(step)}>"
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
        _raise_verify_error("symbol expr contains unsupported token")
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
    - 仅服务解析器内部对 `#symbol.expr<...>` 文本片段的规范化。
    - 不把裸 `StringAttr("N")` 或 `IntAttr(1)` 解释为公开 memory shape/stride 输入。

    使用示例:
    - _unwrap_symbol_expr_attr_text("#symbol.expr<N>")
    """

    stripped = expr.strip()
    prefix = "#symbol.expr<"
    if stripped.startswith(prefix) and stripped.endswith(">"):
        return stripped[len(prefix) : -1].strip()
    return stripped
