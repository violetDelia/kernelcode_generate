"""symbol arith operations.

功能说明:
- 定义 symbol 二元算术 op。

API 列表:
- `class SymbolAddOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- `class SymbolSubOp(...)`
- `class SymbolMulOp(...)`
- `class SymbolDivOp(...)`
- `class SymbolFloorDivOp(...)`
- `class SymbolMinOp(...)`
- `class SymbolMaxOp(...)`

使用示例:
- `from kernel_gen.dialect.symbol.operation import ...`

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/symbol/
- 功能实现: kernel_gen/dialect/symbol/operation/arith.py
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
    def concrete_value(node: _SymbolExprNode) -> int | None:
        """计算纯静态整数表达节点。

        功能说明:
        - 只处理由常量和整数算术构成的表达节点。
        - 遇到具名 symbol、`?`、`iter<...>`、`min/max` 或除零时返回 `None`，由调用方保守拒绝。

        使用示例:
        - value = _SYMBOL_EXPR.concrete_value(_SYMBOL_EXPR.parse_text("8 + 4"))
        """

        const = _SYMBOL_EXPR.const_value(node)
        if const is not None:
            return const
        if node.kind == "neg":
            value = _SYMBOL_EXPR.concrete_value(node.args[0])
            return -value if value is not None else None
        if node.kind == "add":
            values = [_SYMBOL_EXPR.concrete_value(arg) for arg in node.args]
            if any(value is None for value in values):
                return None
            return sum(value for value in values if value is not None)
        if node.kind == "sub":
            lhs = _SYMBOL_EXPR.concrete_value(node.args[0])
            rhs = _SYMBOL_EXPR.concrete_value(node.args[1])
            return lhs - rhs if lhs is not None and rhs is not None else None
        if node.kind == "mul":
            values = [_SYMBOL_EXPR.concrete_value(arg) for arg in node.args]
            if any(value is None for value in values):
                return None
            product = 1
            for value in values:
                if value is not None:
                    product *= value
            return product
        if node.kind in {"floordiv", "ceildiv", "mod"}:
            lhs = _SYMBOL_EXPR.concrete_value(node.args[0])
            rhs = _SYMBOL_EXPR.concrete_value(node.args[1])
            if lhs is None or rhs is None or rhs == 0:
                return None
            if node.kind == "floordiv":
                return lhs // rhs
            if node.kind == "ceildiv":
                return -(-lhs // rhs)
            return lhs % rhs
        return None

    @staticmethod
    def linear_terms(node: _SymbolExprNode) -> tuple[dict[str, int], int] | None:
        """提取一阶 symbol 表达式的系数表。

        功能说明:
        - 仅处理常量、具名 symbol、加减和常量乘一阶表达式。
        - 遇到 `?`、`iter<...>`、`min/max` 或非线性乘法时返回 `None`，调用方保守拒绝。

        使用示例:
        - linear = _SYMBOL_EXPR.linear_terms(_SYMBOL_EXPR.parse_text("B + 24"))
        """

        const = _SYMBOL_EXPR.const_value(node)
        if const is not None:
            return ({}, const)
        if node.kind == "symbol":
            return ({str(node.value): 1}, 0)
        if node.kind == "neg":
            operand = _SYMBOL_EXPR.linear_terms(node.args[0])
            if operand is None:
                return None
            terms, offset = operand
            return ({name: -coeff for name, coeff in terms.items()}, -offset)
        if node.kind == "add":
            combined: dict[str, int] = {}
            offset = 0
            for arg in node.args:
                parsed = _SYMBOL_EXPR.linear_terms(arg)
                if parsed is None:
                    return None
                terms, arg_offset = parsed
                offset += arg_offset
                for name, coeff in terms.items():
                    combined[name] = combined.get(name, 0) + coeff
            return ({name: coeff for name, coeff in combined.items() if coeff != 0}, offset)
        if node.kind == "sub":
            lhs = _SYMBOL_EXPR.linear_terms(node.args[0])
            rhs = _SYMBOL_EXPR.linear_terms(node.args[1])
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
                arg_const = _SYMBOL_EXPR.const_value(arg)
                if arg_const is not None:
                    const_product *= arg_const
                    continue
                if linear is not None:
                    return None
                linear = _SYMBOL_EXPR.linear_terms(arg)
                if linear is None:
                    return None
            if linear is None:
                return ({}, const_product)
            terms, offset = linear
            return ({name: coeff * const_product for name, coeff in terms.items()}, offset * const_product)
        return None

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

    _UNKNOWN_SYMBOL_EXPR = "?"

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

    @staticmethod
    def is_symbol_arith_operand_type(attr: Attribute) -> bool:
        """判断 attribute 是否可作为 symbol 算术/比较 operand。

        功能说明:
        - symbol 算术允许 `!symbol.int` 与 loop-carried `!symbol.iter`，供 tail `min(tile, dim - idx)` 使用。

        使用示例:
        - ok = _SYMBOL_EXPR.is_symbol_arith_operand_type(SymbolValueType.from_expr("N"))
        """

        return isinstance(attr, (SymbolValueType, SymbolIterType))

    @staticmethod
    def is_unknown_symbol_int_type(attr: Attribute) -> bool:
        """判断 `!symbol.int<#symbol.expr<??>>` unknown 类型。

        功能说明:
        - 只在 symbol dialect 当前文件内服务 verifier 与 fold 边界。
        - unknown 是保守值语义，不等同具名符号表达。

        使用示例:
        - _SYMBOL_EXPR.is_unknown_symbol_int_type(SymbolValueType.from_expr("?"))
        """

        return isinstance(attr, SymbolValueType) and attr.get_value() == _UNKNOWN_SYMBOL_EXPR

    @staticmethod
    def parse_symbol_binary_operand_types(parser: AttrParser, op_name: str) -> tuple[Attribute, Attribute]:
        """解析 symbol 二元 op 的 operand type 列表。

        功能说明:
        - 支持当前 printer 输出的 `lhs_type, rhs_type`。
        - 兼容 MLIR 常见的 parenthesized 形式 `(lhs_type, rhs_type)`。

        使用示例:
        - lhs_type, rhs_type = _SYMBOL_EXPR.parse_symbol_binary_operand_types(parser, "symbol.eq")
        """

        if parser.parse_optional_punctuation("(") is not None:
            lhs_type = parser.parse_type()
            parser.parse_characters(",", f" in {op_name} type list")
            rhs_type = parser.parse_type()
            parser.parse_punctuation(")", f" in {op_name} type list")
            return lhs_type, rhs_type
        lhs_type = parser.parse_type()
        parser.parse_characters(",", f" in {op_name} type list")
        rhs_type = parser.parse_type()
        return lhs_type, rhs_type

    @staticmethod
    def symbol_iter_type_expr_node(attr: SymbolIterType) -> _SymbolExprNode:
        """从 `SymbolIterType` 构造公开 `iter<start,end,step>` token。

        功能说明:
        - 只读取 `SymbolIterType` 的公开 start/end/step 参数。
        - 不依赖 SSA 名称、`name_hint`、block argument 或运行时 dump 文本。

        使用示例:
        - node = _SYMBOL_EXPR.symbol_iter_type_expr_node(SymbolIterType.from_bounds("0", "N", "TILE"))
        """

        return _SYMBOL_EXPR.make_iter(
            _SYMBOL_EXPR.parse_text(attr.start.expr.data),
            _SYMBOL_EXPR.parse_text(attr.end.expr.data),
            _SYMBOL_EXPR.parse_text(attr.step.expr.data),
        )

    @staticmethod
    def symbol_arith_operand_expr_node(attr: Attribute) -> _SymbolExprNode | None:
        """提取 symbol 算术 operand 的值语义表达节点。

        功能说明:
        - `SymbolValueType` 直接读取其 `SymbolExprAttr`。
        - `SymbolIterType` 转换为公开 `iter<start,end,step>` token。
        - 非 symbol 算术 operand 返回 `None`，由 verifier 负责报错。

        使用示例:
        - node = _SYMBOL_EXPR.symbol_arith_operand_expr_node(value.type)
        """

        if isinstance(attr, SymbolValueType):
            return _SYMBOL_EXPR.parse_text(attr.expr.expr.data)
        if isinstance(attr, SymbolIterType):
            return _SYMBOL_EXPR.symbol_iter_type_expr_node(attr)
        return None

    @staticmethod
    def symbol_arith_operand_contains_unknown(attr: Attribute) -> bool | None:
        """从公开类型文本快速判断 symbol 算术 operand 是否含 unknown。

        功能说明:
        - `verify_` 的 unknown 传播只需要判断 `?` 是否存在，不需要重建完整表达式 AST。
        - 避免大尺寸动态 kernel IR 在验证阶段重复解析同一 canonical 表达式。

        使用示例:
        - has_unknown = _SYMBOL_EXPR.symbol_arith_operand_contains_unknown(value.type)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        if isinstance(attr, SymbolValueType):
            return _UNKNOWN_SYMBOL_EXPR in attr.expr.expr.data
        if isinstance(attr, SymbolIterType):
            return any(
                _UNKNOWN_SYMBOL_EXPR in expr.expr.data
                for expr in (attr.start, attr.end, attr.step)
            )
        return None

    @staticmethod
    def bounds_are_full_tiles(start: _SymbolExprNode, end: _SymbolExprNode, step: _SymbolExprNode) -> bool:
        """判断 `start -> end step step` 是否静态可证为 full-tile。

        功能说明:
        - 对 `B -> B + 24 step 8` 与 `B -> B + 3*S step S` 这类一阶表达做当前文件内结构化证明。
        - `iter<...>`、`?`、`min/max` 或非线性表达一律保守返回 `False`，避免 full-tile fold 依赖外部化简器状态。

        使用示例:
        - if _SYMBOL_EXPR.bounds_are_full_tiles(start, end, step): ...

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        start_linear = _SYMBOL_EXPR.linear_terms(start)
        end_linear = _SYMBOL_EXPR.linear_terms(end)
        if start_linear is None or end_linear is None:
            return False
        start_terms, start_offset = start_linear
        end_terms, end_offset = end_linear
        diff_terms = dict(end_terms)
        for name, coeff in start_terms.items():
            diff_terms[name] = diff_terms.get(name, 0) - coeff
        distance = end_offset - start_offset
        step_value = _SYMBOL_EXPR.concrete_value(step)
        if step_value is not None:
            if step_value == 0 or any(coeff != 0 for coeff in diff_terms.values()):
                return False
            return distance > 0 and distance % step_value == 0

        step_linear = _SYMBOL_EXPR.linear_terms(step)
        if step_linear is None:
            return False
        step_terms, step_offset = step_linear
        return _SYMBOL_EXPR.linear_distance_is_positive_multiple(diff_terms, distance, step_terms, step_offset)

    @staticmethod
    def linear_distance_is_positive_multiple(
        diff_terms: dict[str, int],
        diff_offset: int,
        step_terms: dict[str, int],
        step_offset: int,
    ) -> bool:
        """判断线性距离是否为 step 线性表达的正整数倍。

        功能说明:
        - 为 full-tile `symbol.min` 提供 `B -> B + 3*S step S` 与 `0 -> 5*N step N`
          这类动态 step 的当前文件内结构化证明。
        - 只接受同一组 symbol coefficient 的正整数倍，不调用外部符号化简器。

        使用示例:
        - _SYMBOL_EXPR.linear_distance_is_positive_multiple({"S": 3}, 0, {"S": 1}, 0)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        if not step_terms and step_offset == 0:
            return False

        ratios: list[int] = []
        for name in set(diff_terms) | set(step_terms):
            step_coeff = step_terms.get(name, 0)
            diff_coeff = diff_terms.get(name, 0)
            if step_coeff == 0:
                if diff_coeff != 0:
                    return False
                continue
            quotient, remainder = divmod(diff_coeff, step_coeff)
            if remainder != 0:
                return False
            ratios.append(quotient)

        if step_offset != 0:
            quotient, remainder = divmod(diff_offset, step_offset)
            if remainder != 0:
                return False
            ratios.append(quotient)
        elif diff_offset != 0:
            return False

        if not ratios:
            return False
        first = ratios[0]
        return first > 0 and all(ratio == first for ratio in ratios)

    @staticmethod
    def full_tile_residual_step(residual: _SymbolExprNode) -> _SymbolExprNode | None:
        """匹配 full-tile tail residual 的 step 表达。

        功能说明:
        - 匹配 `end - iter<start,end,step>`。
        - 只有 `(end-start)` 可证为 `step` 的正整数倍时返回 `step`。

        使用示例:
        - step = _SYMBOL_EXPR.full_tile_residual_step(residual)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        if residual.kind != "sub":
            return None
        end_node, iter_node = residual.args
        if iter_node.kind != "iter":
            return None
        start, end, step = iter_node.args
        if end_node != end:
            return None
        if not _SYMBOL_EXPR.bounds_are_full_tiles(start, end, step):
            return None
        return step

    @staticmethod
    def full_tile_min_step(lhs: _SymbolExprNode, rhs: _SymbolExprNode) -> _SymbolExprNode | None:
        """匹配 full-tile `symbol.min` 可折叠的 step 表达。

        功能说明:
        - 仅接受 `min(step, end - iter<start,end,step>)` 或交换 operand 的等价形式。
        - 非 full-tile、无法证明整除或 step 不一致时返回 `None`。

        使用示例:
        - step = _SYMBOL_EXPR.full_tile_min_step(lhs, rhs)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        rhs_step = _SYMBOL_EXPR.full_tile_residual_step(rhs)
        if rhs_step is not None and lhs == rhs_step:
            return lhs
        lhs_step = _SYMBOL_EXPR.full_tile_residual_step(lhs)
        if lhs_step is not None and rhs == lhs_step:
            return rhs
        return None

    @staticmethod
    def min_full_tile_step_value(lhs: SSAValue, rhs: SSAValue) -> SSAValue | None:
        """匹配 full-tile `symbol.min` 并返回应保留的 step SSA。

        功能说明:
        - 根据 operand type 的公开表达判断，不依赖 SSA 名称。
        - 仅供 `symbol.min` verifier / fold 共享 full-tile 识别。

        使用示例:
        - step_value = _SYMBOL_EXPR.min_full_tile_step_value(op.lhs, op.rhs)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        lhs_node = _SYMBOL_EXPR.symbol_arith_operand_expr_node(lhs.type)
        rhs_node = _SYMBOL_EXPR.symbol_arith_operand_expr_node(rhs.type)
        if lhs_node is None or rhs_node is None:
            return None
        rhs_step = _SYMBOL_EXPR.full_tile_residual_step(rhs_node)
        if rhs_step is not None and lhs_node == rhs_step:
            return lhs
        lhs_step = _SYMBOL_EXPR.full_tile_residual_step(lhs_node)
        if lhs_step is not None and rhs_node == lhs_step:
            return rhs
        return None

    @staticmethod
    def requires_unknown_arith_result(lhs_type: Attribute, rhs_type: Attribute) -> bool:
        """判断 symbol 算术结果是否必须为 unknown。

        功能说明:
        - 任一 operand 值语义包含 `?` 时，算术结果必须保守为 `!symbol.int<#symbol.expr<??>>`。
        - `!symbol.iter<...>` 自身不再强制 unknown，仅当 start/end/step 含 `?` 时传播 unknown。

        使用示例:
        - needs_unknown = _SYMBOL_EXPR.requires_unknown_arith_result(lhs.type, rhs.type)
        """

        lhs_contains_unknown = _SYMBOL_EXPR.symbol_arith_operand_contains_unknown(lhs_type)
        rhs_contains_unknown = _SYMBOL_EXPR.symbol_arith_operand_contains_unknown(rhs_type)
        return (
            lhs_contains_unknown is not None
            and rhs_contains_unknown is not None
            and (lhs_contains_unknown or rhs_contains_unknown)
        )

    @staticmethod
    def infer_arith_result_expr(op_name: str, lhs_type: Attribute, rhs_type: Attribute) -> str | None:
        """推导 symbol 二元算术的 canonical 结果表达。

        功能说明:
        - 对 `SymbolValueType` 与 `SymbolIterType` operand 复用 `SymbolExprAttr` canonical 逻辑。
        - `SymbolIterType` 会转换为 `iter<start,end,step>` token；`?` 场景由调用方使用 unknown 规则处理。
        - `symbol.min` 始终返回未折叠的 `min(lhs, rhs)` 表达；full-tile tail 的 `step` 是 fold 结果，不是 AST 发射必须提前写入的结果类型。

        使用示例:
        - _SYMBOL_EXPR.infer_arith_result_expr("symbol.add", lhs.type, rhs.type)
        """

        lhs = _SYMBOL_EXPR.symbol_arith_operand_expr_node(lhs_type)
        rhs = _SYMBOL_EXPR.symbol_arith_operand_expr_node(rhs_type)
        if lhs is None or rhs is None:
            return None
        if op_name == "symbol.add":
            return _SYMBOL_EXPR.format_node(_SYMBOL_EXPR.make_add(lhs, rhs))
        if op_name == "symbol.sub":
            return _SYMBOL_EXPR.format_node(_SYMBOL_EXPR.make_sub(lhs, rhs))
        if op_name == "symbol.mul":
            return _SYMBOL_EXPR.format_node(_SYMBOL_EXPR.make_mul(lhs, rhs))
        if op_name in {"symbol.div", "symbol.floordiv"}:
            return _SYMBOL_EXPR.format_node(_SYMBOL_EXPR.make_keyword_binary("floordiv", lhs, rhs))
        if op_name == "symbol.min":
            return _SYMBOL_EXPR.format_node(_SYMBOL_EXPR.make_min(lhs, rhs))
        if op_name == "symbol.max":
            return _SYMBOL_EXPR.format_node(_SYMBOL_EXPR.make_max(lhs, rhs))
        return None

    @staticmethod
    def alternate_arith_result_exprs(op_name: str, lhs_type: Attribute, rhs_type: Attribute) -> tuple[str, ...]:
        """返回 verifier 可接受但不要求 AST 提前生成的等价结果表达。

        功能说明:
        - 当前只为 `symbol.min` full-tile tail 提供已折叠 `step` 表达。
        - 允许 AST 先发射 `min(step, end - iter<...>)`，也允许后续 fold/pass 将其规约为 `step`。

        使用示例:
        - alternatives = _SYMBOL_EXPR.alternate_arith_result_exprs("symbol.min", lhs.type, rhs.type)
        """

        if op_name != "symbol.min":
            return ()
        lhs = _SYMBOL_EXPR.symbol_arith_operand_expr_node(lhs_type)
        rhs = _SYMBOL_EXPR.symbol_arith_operand_expr_node(rhs_type)
        if lhs is None or rhs is None:
            return ()
        full_tile_step = _SYMBOL_EXPR.full_tile_min_step(lhs, rhs)
        if full_tile_step is None:
            return ()
        return (_SYMBOL_EXPR.format_node(full_tile_step),)

    @staticmethod
    def concrete_symbol_int_value(attr: Attribute) -> int | None:
        """提取静态可求值的 `!symbol.int` 整数值。


        功能说明:
        - 仅当 `attr` 是静态整数 `SymbolValueType` 时返回具体整数。
        - 动态 symbol 表达返回 `None`，供 fold 逻辑保守拒绝。

        使用示例:
        - _SYMBOL_EXPR.concrete_symbol_int_value(SymbolValueType.from_expr("3"))

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        if not isinstance(attr, SymbolValueType):
            return None
        value = attr.get_value()
        return value if isinstance(value, int) else None

_SYMBOL_EXPR = _SymbolExprOps()


_UNKNOWN_SYMBOL_EXPR = "?"

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
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
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
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        for field_name, field_operand in (("lhs", self.lhs), ("rhs", self.rhs)):
            operand = SSAValue.get(field_operand)
            if not _SYMBOL_EXPR.is_symbol_arith_operand_type(operand.type):
                raise_verify_error(_ERROR_SCENE, f"{self.name} {field_name} must have type !symbol.int<#symbol.expr<expr>> or !symbol.iter<...>")
        if not _SYMBOL_EXPR.is_symbol_int_type(self.result.type):
            raise_verify_error(_ERROR_SCENE, f"{self.name} result type must be !symbol.int<#symbol.expr<expr>>")
        lhs_type = SSAValue.get(self.lhs).type
        rhs_type = SSAValue.get(self.rhs).type
        result_type = SSAValue.get(self.result).type
        if _SYMBOL_EXPR.requires_unknown_arith_result(lhs_type, rhs_type) and not _SYMBOL_EXPR.is_unknown_symbol_int_type(result_type):
            raise_verify_error(_ERROR_SCENE, f"{self.name} result type must be !symbol.int<#symbol.expr<?>> when operand value contains ?")
        if not _SYMBOL_EXPR.requires_unknown_arith_result(lhs_type, rhs_type) and isinstance(result_type, SymbolValueType):
            inferred_expr = _SYMBOL_EXPR.infer_arith_result_expr(self.name, lhs_type, rhs_type)
            if inferred_expr is not None and result_type.get_value() == _UNKNOWN_SYMBOL_EXPR:
                lhs_expr = _SYMBOL_EXPR.symbol_arith_operand_expr_node(lhs_type)
                rhs_expr = _SYMBOL_EXPR.symbol_arith_operand_expr_node(rhs_type)
                if (
                    lhs_expr is not None
                    and rhs_expr is not None
                    and (_SYMBOL_EXPR.contains_iter(lhs_expr) or _SYMBOL_EXPR.contains_iter(rhs_expr))
                ):
                    raise_verify_error(_ERROR_SCENE, f"{self.name} result type must match canonical symbol expression")
            if inferred_expr is not None and result_type.get_value() != _UNKNOWN_SYMBOL_EXPR:
                accepted_exprs = (inferred_expr, *_SYMBOL_EXPR.alternate_arith_result_exprs(self.name, lhs_type, rhs_type))
                expected_types = tuple(SymbolValueType.from_expr(expr) for expr in accepted_exprs)
                if result_type not in expected_types:
                    raise_verify_error(_ERROR_SCENE, f"{self.name} result type must match canonical symbol expression")

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
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        lhs_ssa = SSAValue.get(self.lhs)
        rhs_ssa = SSAValue.get(self.rhs)
        result_type = SSAValue.get(self.result).type
        if self.name == "symbol.min" and isinstance(result_type, SymbolValueType):
            step_value = _SYMBOL_EXPR.min_full_tile_step_value(lhs_ssa, rhs_ssa)
            if step_value is not None:
                step_static = _SYMBOL_EXPR.concrete_symbol_int_value(step_value.type)
                result_expr = result_type.get_value()
                if step_static is not None:
                    inferred_expr = _SYMBOL_EXPR.infer_arith_result_expr(self.name, lhs_ssa.type, rhs_ssa.type)
                    accepted_exprs: tuple[int | str, ...] = (
                        _UNKNOWN_SYMBOL_EXPR,
                        step_static,
                        *((inferred_expr,) if inferred_expr is not None else ()),
                    )
                    if result_expr in accepted_exprs:
                        if step_value.type != result_type:
                            return (step_value,)
                        return (IntAttr(step_static),)
                    return None
                if step_value.type == result_type:
                    return (step_value,)
                return None

        lhs_value = _SYMBOL_EXPR.concrete_symbol_int_value(lhs_ssa.type)
        rhs_value = _SYMBOL_EXPR.concrete_symbol_int_value(rhs_ssa.type)
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
        elif self.name == "symbol.max":
            result_value = max(lhs_value, rhs_value)
        else:
            return None

        result_expr = result_type.get_value()
        if result_expr != _UNKNOWN_SYMBOL_EXPR and result_expr != result_value:
            return None
        return (IntAttr(result_value),)

    def print(self: "_BaseSymbolBinaryArithOp", printer: Printer) -> None:
        """打印 symbol 二元整数算术 op 自定义文本语法。

        功能说明:
        - 输出 lhs/rhs operand、operand 类型与 result type。

        使用示例:
        - SymbolAddOp(lhs, rhs, result_type).print(printer)
        """

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
        """解析 symbol 二元整数算术 op 自定义文本语法。

        功能说明:
        - 读取两个 operand、operand 类型与 result type 并构造具体算术 op。

        使用示例:
        - SymbolAddOp.parse(parser)
        """

        unresolved_lhs = parser.parse_unresolved_operand()
        parser.parse_characters(",", f" in {cls.name}")
        unresolved_rhs = parser.parse_unresolved_operand()
        parser.parse_characters(":", f" in {cls.name}")
        lhs_type, rhs_type = _SYMBOL_EXPR.parse_symbol_binary_operand_types(parser, cls.name)
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
class SymbolMaxOp(_BaseSymbolBinaryArithOp):
    """两个 symbol.int 值的整数最大值。"""

    name = "symbol.max"

__all__ = ["SymbolAddOp", "SymbolSubOp", "SymbolMulOp", "SymbolDivOp", "SymbolFloorDivOp", "SymbolMinOp", "SymbolMaxOp"]
