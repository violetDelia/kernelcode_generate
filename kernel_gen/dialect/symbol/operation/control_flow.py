"""symbol control-flow operations.

功能说明:
- 定义 symbol.yield 与 symbol.for op。

API 列表:
- `class SymbolYieldOp(value: SSAValue | Operation)`
- `class SymbolForOp(start: SSAValue | Operation, end: SSAValue | Operation, step: SSAValue | Operation, body: Region | Block | Sequence[Operation] | Sequence[Block], iter_attr: SymbolIterAttr | None = None, init: SSAValue | Operation | None = None, result_type: Attribute | None = None)`

使用示例:
- `from kernel_gen.dialect.symbol.operation import ...`

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/symbol/
- 功能实现: kernel_gen/dialect/symbol/operation/control_flow.py
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE, ErrorKind, ErrorModule, kernel_code_error, KernelCodeError
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

_SYMBOL_EXPR_TOKEN_PATTERN = re.compile(
    r"\s*(?:(?P<int>[0-9]+)|(?P<ident>[A-Za-z_][A-Za-z0-9_]*)|(?P<punct>[()+\-*,?<>])|(?P<invalid>.))",
    re.DOTALL,
)

_SYMBOL_EXPR_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

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
                node = _SYMBOL_EXPR.make_add(node, self.parse_term())
            elif self.consume_punctuation("-"):
                node = _SYMBOL_EXPR.make_sub(node, self.parse_term())
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
                node = _SYMBOL_EXPR.make_mul(node, self.parse_primary())
            elif self.consume_keyword("floordiv"):
                node = _SYMBOL_EXPR.make_keyword_binary("floordiv", node, self.parse_primary())
            elif self.consume_keyword("ceildiv"):
                node = _SYMBOL_EXPR.make_keyword_binary("ceildiv", node, self.parse_primary())
            elif self.consume_keyword("mod"):
                node = _SYMBOL_EXPR.make_keyword_binary("mod", node, self.parse_primary())
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
            return _SYMBOL_EXPR.make_neg(self.parse_primary())
        if self.consume_punctuation("?"):
            return _SYMBOL_EXPR.make_unknown()
        integer = self.consume_integer()
        if integer is not None:
            return _SYMBOL_EXPR.make_const(integer)
        if self.consume_keyword("min"):
            self.expect_punctuation("(")
            lhs = self.parse_expression()
            self.expect_punctuation(",")
            rhs = self.parse_expression()
            self.expect_punctuation(")")
            return _SYMBOL_EXPR.make_min(lhs, rhs)
        if self.consume_keyword("max"):
            self.expect_punctuation("(")
            lhs = self.parse_expression()
            self.expect_punctuation(",")
            rhs = self.parse_expression()
            self.expect_punctuation(")")
            return _SYMBOL_EXPR.make_max(lhs, rhs)
        if self.consume_keyword("iter"):
            self.expect_punctuation("<")
            start = self.parse_expression()
            self.expect_punctuation(",")
            end = self.parse_expression()
            self.expect_punctuation(",")
            step = self.parse_expression()
            self.expect_punctuation(">")
            return _SYMBOL_EXPR.make_iter(start, end, step)
        identifier = self.consume_identifier()
        if identifier is not None:
            return _SYMBOL_EXPR.make_symbol(identifier)
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
        - 字符串 parser 转为 `KernelCodeError`，xDSL parser 转为 `ParseError`。

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

        self.tokens = _SYMBOL_EXPR.tokenize(expr)
        self.index = 0

    def parse_all(self: "_SymbolExprTextParser") -> _SymbolExprNode:
        """解析完整字符串表达式。

        功能说明:
        - 要求表达式非空且所有 token 被消费。

        使用示例:
        - _SymbolExprTextParser("N + 1").parse_all()
        """

        if not self.tokens:
            raise_verify_error(_ERROR_SCENE, "symbol expr must not be empty")
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
        - 缺失时抛出 `KernelCodeError`。

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

        raise_verify_error(_ERROR_SCENE, message)

class _SymbolExprOps:
    """当前文件内 symbol expression 操作集合。

    功能说明:
    - 将本文件需要的表达式 builder、parser glue 与格式化逻辑合并到一个私有实现容器。
    - 该容器只服务当前文件公开 API，避免跨文件私有 helper 复用和私有函数链。

    使用示例:
    - _SYMBOL_EXPR.normalize("N + 1")
    """

    @staticmethod
    def tokenize(expr: str) -> list[_SymbolExprToken]:
        """把公开 symbol 表达式字符串转换为 token。

        功能说明:
        - 接受标识符、整数与受支持标点。
        - 裸 `/`、`//`、引号和其它字符直接报错。

        使用示例:
        - _SYMBOL_EXPR.tokenize("N floordiv 2")
        """

        tokens: list[_SymbolExprToken] = []
        position = 0
        while position < len(expr):
            if expr[position:].strip() == "":
                break
            match = _SYMBOL_EXPR_TOKEN_PATTERN.match(expr, position)
            if match is None:
                raise_verify_error(_ERROR_SCENE, "symbol expr contains unsupported token")
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
                    raise_verify_error(_ERROR_SCENE, "symbol expr does not support quoted string, bare / or //; use floordiv, ceildiv or mod")
                raise_verify_error(_ERROR_SCENE, "symbol expr contains unsupported token")
        return tokens

    @staticmethod
    def make_const(value: int) -> _SymbolExprNode:
        """构造常量表达节点。

        功能说明:
        - 统一保存整数常量。

        使用示例:
        - _SYMBOL_EXPR.make_const(4)
        """

        return _SymbolExprNode("const", value=value)

    @staticmethod
    def make_symbol(value: str) -> _SymbolExprNode:
        """构造具名 symbol 表达节点。

        功能说明:
        - 校验名称满足公开标识符规则。

        使用示例:
        - _SYMBOL_EXPR.make_symbol("N")
        """

        if _SYMBOL_EXPR_NAME_PATTERN.fullmatch(value) is None:
            raise_verify_error(_ERROR_SCENE, "symbol expr name must match [A-Za-z_][A-Za-z0-9_]*")
        return _SymbolExprNode("symbol", value=value)

    @staticmethod
    def make_unknown() -> _SymbolExprNode:
        """构造 unknown 表达节点。

        功能说明:
        - unknown 公开文本固定为 `?`。

        使用示例:
        - _SYMBOL_EXPR.make_unknown()
        """

        return _SymbolExprNode("unknown")

    @staticmethod
    def is_unknown(node: _SymbolExprNode) -> bool:
        """判断表达节点是否为 unknown。

        功能说明:
        - 服务 `?` 传播规则。

        使用示例:
        - _SYMBOL_EXPR.is_unknown(node)
        """

        return node.kind == "unknown"

    @staticmethod
    def contains_unknown(node: _SymbolExprNode) -> bool:
        """判断表达树是否包含 unknown。

        功能说明:
        - 识别 `iter<start,end,step>` 子表达中的 `?`，供算术结果保守传播。

        使用示例:
        - _SYMBOL_EXPR.contains_unknown(node)
        """

        return _SYMBOL_EXPR.is_unknown(node) or any(_SYMBOL_EXPR.contains_unknown(arg) for arg in node.args)

    @staticmethod
    def contains_iter(node: _SymbolExprNode) -> bool:
        """判断表达树是否包含 iter token。

        功能说明:
        - 含 iter token 的 `min/max` 需要保留调用顺序，避免 tail 表达式被重排。

        使用示例:
        - has_iter = _SYMBOL_EXPR.contains_iter(node)
        """

        return node.kind == "iter" or any(_SYMBOL_EXPR.contains_iter(arg) for arg in node.args)

    @staticmethod
    def make_iter(start: _SymbolExprNode, end: _SymbolExprNode, step: _SymbolExprNode) -> _SymbolExprNode:
        """构造 `iter<start,end,step>` token 表达节点。

        功能说明:
        - 该节点表示 `SymbolIterType` 的值语义 token，不从 SSA 名称或 dump 文本派生。
        - start/end/step 已在子表达 parser 中完成 canonicalize。

        使用示例:
        - _SYMBOL_EXPR.make_iter(start, end, step)
        """

        return _SymbolExprNode("iter", args=(start, end, step))

    @staticmethod
    def const_value(node: _SymbolExprNode) -> int | None:
        """提取常量节点的整数值。

        功能说明:
        - 非常量返回 `None`。

        使用示例:
        - _SYMBOL_EXPR.const_value(node)
        """

        return int(node.value) if node.kind == "const" and isinstance(node.value, int) else None

    @staticmethod
    def make_neg(node: _SymbolExprNode) -> _SymbolExprNode:
        """构造一元负号表达。

        功能说明:
        - 常量直接折叠；unknown 继续传播。

        使用示例:
        - _SYMBOL_EXPR.make_neg(_SYMBOL_EXPR.make_symbol("N"))
        """

        if _SYMBOL_EXPR.contains_unknown(node):
            return _SYMBOL_EXPR.make_unknown()
        const = _SYMBOL_EXPR.const_value(node)
        if const is not None:
            return _SYMBOL_EXPR.make_const(-const)
        if node.kind == "neg":
            return node.args[0]
        return _SymbolExprNode("neg", args=(node,))

    @staticmethod
    def make_add(lhs: _SymbolExprNode, rhs: _SymbolExprNode) -> _SymbolExprNode:
        """构造 canonical 加法表达。

        功能说明:
        - 常量折叠、零 identity、交换律排序与 `?` 传播。

        使用示例:
        - _SYMBOL_EXPR.make_add(_SYMBOL_EXPR.make_symbol("N"), _SYMBOL_EXPR.make_const(1))
        """

        if _SYMBOL_EXPR.contains_unknown(lhs) or _SYMBOL_EXPR.contains_unknown(rhs):
            return _SYMBOL_EXPR.make_unknown()
        lhs_const = _SYMBOL_EXPR.const_value(lhs)
        rhs_const = _SYMBOL_EXPR.const_value(rhs)
        if lhs_const is not None and rhs_const is not None:
            return _SYMBOL_EXPR.make_const(lhs_const + rhs_const)
        terms: list[_SymbolExprNode] = []
        const_sum = 0
        for node in (lhs, rhs):
            if node.kind == "add":
                source = node.args
            else:
                source = (node,)
            for term in source:
                term_const = _SYMBOL_EXPR.const_value(term)
                if term_const is None:
                    terms.append(term)
                else:
                    const_sum += term_const
        terms.sort(key=_SYMBOL_EXPR.format_node)
        if const_sum != 0:
            terms.append(_SYMBOL_EXPR.make_const(const_sum))
        if not terms:
            return _SYMBOL_EXPR.make_const(0)
        if len(terms) == 1:
            return terms[0]
        return _SymbolExprNode("add", args=tuple(terms))

    @staticmethod
    def make_sub(lhs: _SymbolExprNode, rhs: _SymbolExprNode) -> _SymbolExprNode:
        """构造 canonical 减法表达。

        功能说明:
        - 常量折叠、减零 identity 与 `?` 传播。

        使用示例:
        - _SYMBOL_EXPR.make_sub(_SYMBOL_EXPR.make_symbol("N"), _SYMBOL_EXPR.make_const(1))
        """

        if _SYMBOL_EXPR.contains_unknown(lhs) or _SYMBOL_EXPR.contains_unknown(rhs):
            return _SYMBOL_EXPR.make_unknown()
        lhs_const = _SYMBOL_EXPR.const_value(lhs)
        rhs_const = _SYMBOL_EXPR.const_value(rhs)
        if lhs_const is not None and rhs_const is not None:
            return _SYMBOL_EXPR.make_const(lhs_const - rhs_const)
        if rhs_const == 0:
            return lhs
        if rhs_const is not None:
            return _SYMBOL_EXPR.make_add(lhs, _SYMBOL_EXPR.make_const(-rhs_const))
        if lhs_const == 0:
            return _SYMBOL_EXPR.make_neg(rhs)
        if lhs == rhs:
            return _SYMBOL_EXPR.make_const(0)
        return _SymbolExprNode("sub", args=(lhs, rhs))

    @staticmethod
    def make_mul(lhs: _SymbolExprNode, rhs: _SymbolExprNode) -> _SymbolExprNode:
        """构造 canonical 乘法表达。

        功能说明:
        - 常量折叠、零/一规则、交换律排序与 `?` 传播。

        使用示例:
        - _SYMBOL_EXPR.make_mul(_SYMBOL_EXPR.make_symbol("N"), _SYMBOL_EXPR.make_const(2))
        """

        if _SYMBOL_EXPR.contains_unknown(lhs) or _SYMBOL_EXPR.contains_unknown(rhs):
            return _SYMBOL_EXPR.make_unknown()
        lhs_const = _SYMBOL_EXPR.const_value(lhs)
        rhs_const = _SYMBOL_EXPR.const_value(rhs)
        if lhs_const is not None and rhs_const is not None:
            return _SYMBOL_EXPR.make_const(lhs_const * rhs_const)
        terms: list[_SymbolExprNode] = []
        const_product = 1
        for node in (lhs, rhs):
            if node.kind == "mul":
                source = node.args
            else:
                source = (node,)
            for term in source:
                term_const = _SYMBOL_EXPR.const_value(term)
                if term_const is None:
                    terms.append(term)
                else:
                    const_product *= term_const
        if const_product == 0:
            return _SYMBOL_EXPR.make_const(0)
        terms.sort(key=_SYMBOL_EXPR.format_node)
        if const_product != 1 or not terms:
            terms.insert(0, _SYMBOL_EXPR.make_const(const_product))
        if len(terms) == 1:
            return terms[0]
        return _SymbolExprNode("mul", args=tuple(terms))

    @staticmethod
    def make_keyword_binary(op: str, lhs: _SymbolExprNode, rhs: _SymbolExprNode) -> _SymbolExprNode:
        """构造 affine 风格关键字二元表达。

        功能说明:
        - 支持 `floordiv`、`ceildiv` 与 `mod`。
        - 常量场景直接折叠，除零稳定报错。

        使用示例:
        - _SYMBOL_EXPR.make_keyword_binary("floordiv", lhs, rhs)
        """

        if _SYMBOL_EXPR.contains_unknown(lhs) or _SYMBOL_EXPR.contains_unknown(rhs):
            return _SYMBOL_EXPR.make_unknown()
        lhs_const = _SYMBOL_EXPR.const_value(lhs)
        rhs_const = _SYMBOL_EXPR.const_value(rhs)
        if rhs_const == 0:
            raise_verify_error(_ERROR_SCENE, "symbol expr division by zero is not supported")
        if lhs_const is not None and rhs_const is not None:
            if op == "floordiv":
                return _SYMBOL_EXPR.make_const(lhs_const // rhs_const)
            if op == "ceildiv":
                return _SYMBOL_EXPR.make_const(-(-lhs_const // rhs_const))
            if op == "mod":
                return _SYMBOL_EXPR.make_const(lhs_const % rhs_const)
        if rhs_const == 1:
            if op in {"floordiv", "ceildiv"}:
                return lhs
            if op == "mod":
                return _SYMBOL_EXPR.make_const(0)
        return _SymbolExprNode(op, args=(lhs, rhs))

    @staticmethod
    def make_min(lhs: _SymbolExprNode, rhs: _SymbolExprNode) -> _SymbolExprNode:
        """构造 canonical `min(lhs, rhs)` 表达。

        功能说明:
        - 支持二元 min、常量折叠、交换律排序、iter token 稳定排序与 `?` 传播。

        使用示例:
        - _SYMBOL_EXPR.make_min(lhs, rhs)
        """

        if _SYMBOL_EXPR.contains_unknown(lhs) or _SYMBOL_EXPR.contains_unknown(rhs):
            return _SYMBOL_EXPR.make_unknown()
        lhs_const = _SYMBOL_EXPR.const_value(lhs)
        rhs_const = _SYMBOL_EXPR.const_value(rhs)
        if lhs_const is not None and rhs_const is not None:
            return _SYMBOL_EXPR.make_const(min(lhs_const, rhs_const))
        if lhs == rhs:
            return lhs
        lhs_has_iter = _SYMBOL_EXPR.contains_iter(lhs)
        rhs_has_iter = _SYMBOL_EXPR.contains_iter(rhs)
        if lhs_has_iter != rhs_has_iter:
            ordered = (rhs, lhs) if lhs_has_iter else (lhs, rhs)
            return _SymbolExprNode("min", args=ordered)
        if lhs_has_iter and rhs_has_iter:
            return _SymbolExprNode("min", args=(lhs, rhs))
        ordered = tuple(sorted((lhs, rhs), key=_SYMBOL_EXPR.format_node))
        return _SymbolExprNode("min", args=ordered)

    @staticmethod
    def make_max(lhs: _SymbolExprNode, rhs: _SymbolExprNode) -> _SymbolExprNode:
        """构造 canonical `max(lhs, rhs)` 表达。

        功能说明:
        - 支持二元 max、常量折叠、交换律排序、iter token 稳定排序与 `?` 传播。

        使用示例:
        - _SYMBOL_EXPR.make_max(lhs, rhs)
        """

        if _SYMBOL_EXPR.contains_unknown(lhs) or _SYMBOL_EXPR.contains_unknown(rhs):
            return _SYMBOL_EXPR.make_unknown()
        lhs_const = _SYMBOL_EXPR.const_value(lhs)
        rhs_const = _SYMBOL_EXPR.const_value(rhs)
        if lhs_const is not None and rhs_const is not None:
            return _SYMBOL_EXPR.make_const(max(lhs_const, rhs_const))
        if lhs == rhs:
            return lhs
        lhs_has_iter = _SYMBOL_EXPR.contains_iter(lhs)
        rhs_has_iter = _SYMBOL_EXPR.contains_iter(rhs)
        if lhs_has_iter != rhs_has_iter:
            ordered = (rhs, lhs) if lhs_has_iter else (lhs, rhs)
            return _SymbolExprNode("max", args=ordered)
        if lhs_has_iter and rhs_has_iter:
            return _SymbolExprNode("max", args=(lhs, rhs))
        ordered = tuple(sorted((lhs, rhs), key=_SYMBOL_EXPR.format_node))
        return _SymbolExprNode("max", args=ordered)

    @staticmethod
    def precedence(node: _SymbolExprNode) -> int:
        """返回表达节点打印优先级。

        功能说明:
        - 用于生成可稳定重新解析的 canonical 文本。

        使用示例:
        - _SYMBOL_EXPR.precedence(node)
        """

        if node.kind in {"const", "symbol", "unknown", "iter", "min", "max"}:
            return _SYMBOL_EXPR_ATOM_PRECEDENCE
        if node.kind == "neg":
            return _SYMBOL_EXPR_UNARY_PRECEDENCE
        if node.kind in {"mul", "floordiv", "ceildiv", "mod"}:
            return _SYMBOL_EXPR_TERM_PRECEDENCE
        return _SYMBOL_EXPR_EXPR_PRECEDENCE

    @staticmethod
    def format_node(node: _SymbolExprNode, parent_precedence: int = 0) -> str:
        """打印 canonical symbol 表达式节点。

        功能说明:
        - 生成 `SymbolExprAttr.expr.data` 的稳定文本。
        - 只在必要时添加括号。

        使用示例:
        - _SYMBOL_EXPR.format_node(node)
        """

        if node.kind == "const":
            text = str(node.value)
        elif node.kind == "symbol":
            text = str(node.value)
        elif node.kind == "unknown":
            text = _UNKNOWN_SYMBOL_EXPR
        elif node.kind == "iter":
            start, end, step = node.args
            text = f"iter<{_SYMBOL_EXPR.format_node(start)},{_SYMBOL_EXPR.format_node(end)},{_SYMBOL_EXPR.format_node(step)}>"
        elif node.kind == "neg":
            text = "-" + _SYMBOL_EXPR.format_node(node.args[0], _SYMBOL_EXPR_UNARY_PRECEDENCE)
        elif node.kind == "add":
            text = _SYMBOL_EXPR.format_add(node)
        elif node.kind == "sub":
            lhs, rhs = node.args
            text = (
                f"{_SYMBOL_EXPR.format_node(lhs, _SYMBOL_EXPR_EXPR_PRECEDENCE)} - "
                f"{_SYMBOL_EXPR.format_node(rhs, _SYMBOL_EXPR_EXPR_PRECEDENCE + 1)}"
            )
        elif node.kind == "mul":
            text = "*".join(_SYMBOL_EXPR.format_node(arg, _SYMBOL_EXPR_TERM_PRECEDENCE) for arg in node.args)
        elif node.kind in {"floordiv", "ceildiv", "mod"}:
            lhs, rhs = node.args
            text = (
                f"{_SYMBOL_EXPR.format_node(lhs, _SYMBOL_EXPR_TERM_PRECEDENCE)} {node.kind} "
                f"{_SYMBOL_EXPR.format_node(rhs, _SYMBOL_EXPR_TERM_PRECEDENCE + 1)}"
            )
        elif node.kind == "min":
            text = f"min({_SYMBOL_EXPR.format_node(node.args[0])}, {_SYMBOL_EXPR.format_node(node.args[1])})"
        elif node.kind == "max":
            text = f"max({_SYMBOL_EXPR.format_node(node.args[0])}, {_SYMBOL_EXPR.format_node(node.args[1])})"
        else:
            raise_verify_error(_ERROR_SCENE, "symbol expr contains unsupported token")
        if _SYMBOL_EXPR.precedence(node) < parent_precedence:
            return f"({text})"
        return text

    @staticmethod
    def format_add(node: _SymbolExprNode) -> str:
        """打印 canonical 加法表达式。

        功能说明:
        - 把负常量和一元负号打印为 `lhs - rhs` 形式。

        使用示例:
        - _SYMBOL_EXPR.format_add(node)
        """

        pieces: list[str] = []
        for term in node.args:
            const = _SYMBOL_EXPR.const_value(term)
            if const is not None and const < 0:
                if not pieces:
                    pieces.append(str(const))
                else:
                    pieces.append(f"- {abs(const)}")
                continue
            if term.kind == "neg":
                text = _SYMBOL_EXPR.format_node(term.args[0], _SYMBOL_EXPR_EXPR_PRECEDENCE + 1)
                pieces.append(f"- {text}" if pieces else f"-{text}")
                continue
            text = _SYMBOL_EXPR.format_node(term, _SYMBOL_EXPR_EXPR_PRECEDENCE)
            pieces.append(text if not pieces else f"+ {text}")
        return " ".join(pieces)

    @staticmethod
    def parse_text(expr: str) -> _SymbolExprNode:
        """解析字符串为 canonical symbol 表达节点。

        功能说明:
        - 统一 `from_expr`、verifier 与内部 result 推导路径。

        使用示例:
        - _SYMBOL_EXPR.parse_text("N + 1")
        """

        return _SymbolExprTextParser(expr).parse_all()

    @staticmethod
    def normalize(expr: str) -> str:
        """标准化符号表达字符串。

        功能说明:
        - 解析公开 symbol 表达并输出 canonical 文本。
        - 裸 `/`、`//`、quoted string 和非法字符均被拒绝。

        使用示例:
        - _SYMBOL_EXPR.normalize("1 + N")
        """

        return _SYMBOL_EXPR.format_node(_SYMBOL_EXPR.parse_text(expr.strip()))

    @staticmethod
    def is_symbol_int_type(attr: Attribute) -> bool:
        """判断 attribute 是否为 symbol.int 类型。


        功能说明:
        - 为 `symbol.for` 与 `symbol.get_*` verifier 复用统一的 symbol 类型判断。

        使用示例:
        - _SYMBOL_EXPR.is_symbol_int_type(SymbolValueType.from_expr("N"))

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        return isinstance(attr, SymbolValueType)

_SYMBOL_EXPR = _SymbolExprOps()


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
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
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
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        if not _SYMBOL_EXPR.is_symbol_int_type(SSAValue.get(self.value).type):
            raise_verify_error(_ERROR_SCENE, f"{self.name} value must have type !symbol.int<#symbol.expr<expr>>")

        parent_op = self.parent_op()
        if not isinstance(parent_op, SymbolForOp):
            raise_verify_error(_ERROR_SCENE, f"{self.name} must appear inside symbol.for")
        if parent_op.init is None or parent_op.result is None:
            raise_verify_error(_ERROR_SCENE, f"{self.name} requires symbol.for loop-carried !symbol.int<#symbol.expr<expr>>")

        parent_block = self.parent_block()
        if parent_block is None or parent_block.last_op is not self:
            raise_verify_error(_ERROR_SCENE, f"{self.name} must terminate symbol.for body")

    def print(self: "SymbolYieldOp", printer: Printer) -> None:
        """打印 symbol.yield 自定义文本语法。


        功能说明:
        - 输出 `symbol.yield %value : !symbol.int<#symbol.expr<...>>` 形式文本。

        使用示例:
        - SymbolYieldOp(value).print(printer)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
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
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
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
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
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
                    _SYMBOL_EXPR.normalize(start_type.expr.expr.data),
                    _SYMBOL_EXPR.normalize(end_type.expr.expr.data),
                    _SYMBOL_EXPR.normalize(step_type.expr.expr.data),
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
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        start_value = SSAValue.get(self.start)
        end_value = SSAValue.get(self.end)
        step_value = SSAValue.get(self.step)
        for operand_name, operand in (("start", start_value), ("end", end_value), ("step", step_value)):
            if not _SYMBOL_EXPR.is_symbol_int_type(operand.type):
                raise_verify_error(_ERROR_SCENE, f"{self.name} {operand_name} must have type !symbol.int<#symbol.expr<expr>>")

        step_type = step_value.type
        assert isinstance(step_type, SymbolValueType)
        step_expr = _SYMBOL_EXPR.normalize(step_type.expr.expr.data)
        if step_expr == "0":
            raise_verify_error(_ERROR_SCENE, f"{self.name} step must not be zero")

        blocks = list(self.body.blocks)
        if len(blocks) != 1:
            raise_verify_error(_ERROR_SCENE, f"{self.name} only supports single-block regions")
        block = blocks[0]
        carried_init = self.init
        carried_result = self.result
        has_carried = carried_init is not None or carried_result is not None
        if carried_init is None and carried_result is not None:
            raise_verify_error(_ERROR_SCENE, f"{self.name} loop-carried !symbol.int<#symbol.expr<expr>> requires init operand")
        if carried_init is not None and carried_result is None:
            raise_verify_error(_ERROR_SCENE, f"{self.name} loop-carried !symbol.int<#symbol.expr<expr>> requires single symbol.int result")
        expected_block_args = 2 if has_carried else 1
        if len(block.args) != expected_block_args:
            if has_carried:
                raise_verify_error(_ERROR_SCENE, f"{self.name} loop-carried !symbol.int<#symbol.expr<expr>> requires exactly two block arguments")
            raise_verify_error(_ERROR_SCENE, f"{self.name} body must have exactly one block argument")
        iter_arg = block.args[0]
        if not isinstance(iter_arg.type, SymbolIterType):
            raise_verify_error(_ERROR_SCENE, f"{self.name} it must have type !symbol.iter<...>")
        iter_attr = self.iter_attr
        if not isinstance(iter_attr, SymbolIterAttr):
            raise_verify_error(_ERROR_SCENE, f"{self.name} iter attribute must be #symbol.iter<...>")
        start_expr = _SYMBOL_EXPR.normalize(start_value.type.expr.expr.data)
        end_expr = _SYMBOL_EXPR.normalize(end_value.type.expr.expr.data)
        if _SYMBOL_EXPR.normalize(iter_attr.start.expr.data) != start_expr:
            raise_verify_error(_ERROR_SCENE, f"{self.name} iter.start must match start operand")
        if _SYMBOL_EXPR.normalize(iter_attr.end.expr.data) != end_expr:
            raise_verify_error(_ERROR_SCENE, f"{self.name} iter.end must match end operand")
        if _SYMBOL_EXPR.normalize(iter_attr.step.expr.data) != step_expr:
            raise_verify_error(_ERROR_SCENE, f"{self.name} iter.step must match step operand")
        expected_iter_type = SymbolIterType.from_attr(iter_attr)
        if iter_arg.type != expected_iter_type:
            raise_verify_error(_ERROR_SCENE, f"{self.name} it must have type {expected_iter_type}")
        if not has_carried:
            return

        if not _SYMBOL_EXPR.is_symbol_int_type(carried_init.type):
            raise_verify_error(_ERROR_SCENE, f"{self.name} loop-carried init must have type !symbol.int<#symbol.expr<expr>>")
        if not _SYMBOL_EXPR.is_symbol_int_type(block.args[1].type):
            raise_verify_error(_ERROR_SCENE, f"{self.name} loop-carried acc must have type !symbol.int<#symbol.expr<expr>>")
        if not _SYMBOL_EXPR.is_symbol_int_type(carried_result.type):
            raise_verify_error(_ERROR_SCENE, f"{self.name} loop-carried result must have type !symbol.int<#symbol.expr<expr>>")

        terminator = block.last_op
        if not isinstance(terminator, SymbolYieldOp):
            raise_verify_error(_ERROR_SCENE, f"{self.name} loop-carried body must terminate with symbol.yield")
        if not _SYMBOL_EXPR.is_symbol_int_type(SSAValue.get(terminator.value).type):
            raise_verify_error(_ERROR_SCENE, f"{self.name} loop-carried yield must have type !symbol.int<#symbol.expr<expr>>")

    def print(self: "SymbolForOp", printer: Printer) -> None:
        """打印 symbol.for 自定义文本语法。


        功能说明:
        - 无 carried-value 时输出旧文本语法。
        - 带 carried-value 时输出 `iter_args(%acc = %init) {iter = ...} -> !symbol.int<#symbol.expr<...>> { ... }`，与 parser 使用同一公开顺序。

        使用示例:
        - SymbolForOp(start, end, step, body, init=zero).print(printer)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
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
        printer.print_string(" ")
        printer.print_attr_dict(self.attributes)
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
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
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
        attrs = dict(parser.parse_optional_attr_dict() or {})
        iter_attr = attrs.get("iter")
        if not isinstance(iter_attr, SymbolIterAttr):
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT, _format_error("symbol.for iter attribute must be #symbol.iter<...>"))
        iter_arg = unresolved_iter.resolve(SymbolIterType.from_attr(iter_attr))
        result_type = None
        if parser.parse_optional_characters("->") is not None:
            result_type = parser.parse_type()
        if init_value is None and result_type is not None:
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT, _format_error("symbol.for result type requires loop-carried !symbol.int<#symbol.expr<expr>>"))
        if init_value is not None:
            if not isinstance(result_type, SymbolValueType):
                raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT, _format_error("symbol.for loop-carried result must be !symbol.int<#symbol.expr<expr>>"))
            acc_arg = unresolved_acc.resolve(result_type)
        block_args = (iter_arg,) if acc_arg is None else (iter_arg, acc_arg)
        body = parser.parse_region(block_args)
        op = cls(start_value, end_value, step_value, body, iter_attr, init=init_value, result_type=result_type)
        op.attributes = attrs
        return op

__all__ = ["SymbolYieldOp", "SymbolForOp"]
