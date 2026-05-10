"""SymbolDim implementation.


功能说明:
- 提供符号维度表达、基础算术运算与动态性判断。
- 字符串表达支持 `min(lhs, rhs)` 与 `max(lhs, rhs)`，用于 DSL tile 尾块表达。
- 匿名运行期未知维度 `?` 参与表达式时保守传播为 `?`，避免生成不可解析的派生文本。

API 列表:
- `class SymbolDim(sym: int | str | sp.Basic)`
- `SymbolDim.__init__(self, sym: int | str | sp.Basic) -> None`
- `SymbolDim.get_symbol(self) -> sp.Basic`
- `SymbolDim.get_value(self) -> int | float | str | sp.Basic`
- `SymbolDim.__repr__(self) -> str`
- `SymbolDim.__str__(self) -> str`
- `SymbolDim.__add__(self, other: int | str | sp.Basic | SymbolDim) -> SymbolDim`
- `SymbolDim.__radd__(self, other: int | str | sp.Basic | SymbolDim) -> SymbolDim`
- `SymbolDim.__sub__(self, other: int | str | sp.Basic | SymbolDim) -> SymbolDim`
- `SymbolDim.__rsub__(self, other: int | str | sp.Basic | SymbolDim) -> SymbolDim`
- `SymbolDim.__mul__(self, other: int | str | sp.Basic | SymbolDim) -> SymbolDim`
- `SymbolDim.__rmul__(self, other: int | str | sp.Basic | SymbolDim) -> SymbolDim`
- `SymbolDim.__truediv__(self, other: int | str | sp.Basic | SymbolDim) -> SymbolDim`
- `SymbolDim.__rtruediv__(self, other: int | str | sp.Basic | SymbolDim) -> SymbolDim`
- `SymbolDim.__floordiv__(self, other: int | str | sp.Basic | SymbolDim) -> SymbolDim`
- `SymbolDim.__rfloordiv__(self, other: int | str | sp.Basic | SymbolDim) -> SymbolDim`
- `SymbolDim.__eq__(self, other: int | str | sp.Basic | SymbolDim) -> bool`
- `SymbolDim.is_dynamic(self) -> bool`

使用示例:
- from kernel_gen.symbol_variable.symbol_dim import SymbolDim
- SymbolDim("N") + 1

关联文件:
- spec: spec/symbol_variable/symbol_dim.md
- test: test/symbol_variable/test_symbol_dim.py
- 功能实现: kernel_gen/symbol_variable/symbol_dim.py
"""

from __future__ import annotations

import ast
import contextlib
import io
import re
from typing import TypeAlias

import sympy as sp
from sympy.parsing.sympy_parser import parse_expr

SymbolDimOperand: TypeAlias = "int | str | sp.Basic | _SymbolDim"


class _SymbolDim:
    """符号维度基类，封装 sympy 表达式与基础运算。


    功能说明:
    - 统一保存与暴露 sympy 表达式，并提供算术与比较能力。

    使用示例:
    - d = SymbolDim("N")
    - d.get_symbol()

    关联文件:
    - spec: spec/symbol_variable/symbol_dim.md
    - test: test/symbol_variable/test_symbol_dim.py
    - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
    """

    _NUMERIC_LITERAL_RE = re.compile(
        r"^[+-]?(?:(?:\d(?:_?\d)*)(?:\.(?:\d(?:_?\d)*)?)?|\.(?:\d(?:_?\d)*))(?:[eE][+-]?\d(?:_?\d)*)?$"
    )
    _UNKNOWN_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_])\?(?![A-Za-z0-9_])")
    _UNKNOWN_PARSE_NAME = "__kg_unknown_dim__"

    @staticmethod
    def _unknown_symbol() -> sp.Symbol:
        """构造匿名未知维度符号。


        功能说明:
        - 统一使用 `?` 表示运行期无法在编译期命名的动态维度。

        使用示例:
        - unknown = _SymbolDim._unknown_symbol()

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """

        return sp.symbols("?", integer=True, real=True)

    @staticmethod
    def _contains_unknown_token(value: str) -> bool:
        """判断字符串表达式是否包含独立匿名未知 token。


        功能说明:
        - 仅识别独立 `?` token，避免把普通符号名中的字符误判为未知维度。

        使用示例:
        - _SymbolDim._contains_unknown_token("? - 2")

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """

        return _SymbolDim._UNKNOWN_TOKEN_RE.search(value) is not None

    @staticmethod
    def _replace_unknown_tokens_for_parse(value: str) -> str:
        """将匿名未知 token 替换成可被 Python/SymPy 解析的内部符号名。


        功能说明:
        - 仅替换独立 `?` token，保留其它文本用于后续语法校验。
        - 返回值只服务当前文件内部解析，不作为公开表达式输出。

        使用示例:
        - parsed_text = _SymbolDim._replace_unknown_tokens_for_parse("? - 2")

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """

        return _SymbolDim._UNKNOWN_TOKEN_RE.sub(_SymbolDim._UNKNOWN_PARSE_NAME, value)

    @staticmethod
    def _raise_invalid_expr() -> None:
        """抛出统一的 SymbolDim 表达式错误。


        功能说明:
        - 保持字符串表达式非法输入的公开错误消息稳定。

        使用示例:
        - _SymbolDim._raise_invalid_expr()

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """

        raise ValueError("SymbolDim expression string is invalid")

    @staticmethod
    def _validate_expr_ast_node(node: ast.AST) -> None:
        """递归校验 SymbolDim 表达式 AST 节点。


        功能说明:
        - 只允许整数常量、符号名、整数算术、一元正负号、`floor(arg)`、`min(lhs, rhs)` 和 `max(lhs, rhs)`。
        - 拒绝比较、布尔、条件、容器、属性、下标、幂运算和其它非公开表达式形态。

        使用示例:
        - _SymbolDim._validate_expr_ast_node(ast.parse("max(N, 4)", mode="eval"))

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """

        if isinstance(node, ast.Expression):
            _SymbolDim._validate_expr_ast_node(node.body)
            return
        if isinstance(node, ast.Name):
            return
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, int):
                _SymbolDim._raise_invalid_expr()
            return
        if isinstance(node, ast.UnaryOp):
            if not isinstance(node.op, (ast.UAdd, ast.USub)):
                _SymbolDim._raise_invalid_expr()
            _SymbolDim._validate_expr_ast_node(node.operand)
            return
        if isinstance(node, ast.BinOp):
            if not isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv)):
                _SymbolDim._raise_invalid_expr()
            _SymbolDim._validate_expr_ast_node(node.left)
            _SymbolDim._validate_expr_ast_node(node.right)
            return
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                _SymbolDim._raise_invalid_expr()
            expected_arity = {"floor": 1, "min": 2, "max": 2}.get(node.func.id)
            if expected_arity is None or node.keywords or len(node.args) != expected_arity:
                _SymbolDim._raise_invalid_expr()
            for arg in node.args:
                _SymbolDim._validate_expr_ast_node(arg)
            return
        _SymbolDim._raise_invalid_expr()

    @staticmethod
    def _validate_expr_ast(value: str) -> None:
        """校验 SymbolDim 表达式的公开语法范围。


        功能说明:
        - 在交给 SymPy 前先拒绝语法不完整或超出公开整数算术范围的表达式。
        - 仅允许整数算术、`floor(arg)`、`min(lhs, rhs)` 与 `max(lhs, rhs)` 三个公开函数形态。

        使用示例:
        - _SymbolDim._validate_expr_ast("max(N, 4)")

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """

        try:
            parsed_ast = ast.parse(value, mode="eval")
        except SyntaxError as exc:
            raise ValueError("SymbolDim expression string is invalid") from exc
        _SymbolDim._validate_expr_ast_node(parsed_ast)

    @staticmethod
    def _parse_expr_str(value: str) -> sp.Basic:
        """解析并校验公开 SymbolDim 表达式字符串。


        功能说明:
        - 统一处理函数白名单、函数参数数量、符号假设和 SymPy 解析错误。
        - 非法表达式稳定转换为 `ValueError("SymbolDim expression string is invalid")`。

        使用示例:
        - expr = _SymbolDim._parse_expr_str("max(N, 4)")

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """

        _SymbolDim._validate_expr_ast(value)
        symbol_names = {
            name
            for name in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", value)
            if name not in {"floor", "min", "max"}
        }
        local_symbols = {
            name: sp.symbols(name, integer=True, real=True)
            for name in symbol_names
        }
        local_symbols["floor"] = sp.floor
        local_symbols["min"] = sp.Min
        local_symbols["max"] = sp.Max
        try:
            parsed = parse_expr(value, local_dict=local_symbols, evaluate=True)
        except (sp.SympifyError, SyntaxError, TypeError, ValueError) as exc:
            raise ValueError("SymbolDim expression string is invalid") from exc
        if isinstance(parsed, tuple):
            raise ValueError("SymbolDim expression string is invalid")
        return _SymbolDim._normalize_symbol(parsed)

    @staticmethod
    def _is_unknown_expr(expr: sp.Basic) -> bool:
        """判断 sympy 表达式是否含匿名未知维度。


        功能说明:
        - 只要表达式自由符号中包含 `?`，该维度表达式对外折回匿名未知。

        使用示例:
        - _SymbolDim._is_unknown_expr(SymbolDim("?").get_symbol())

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """

        return any(symbol.name == "?" for symbol in expr.free_symbols)

    @staticmethod
    def _is_numeric_literal_str(value: str) -> bool:
        """判断字符串是否属于数值字面量。


        功能说明:
        - 识别整数、小数、科学计数法及带正负号的数值字面量字符串。
        - 仅用于字符串输入域校验，不负责解析 sympy 表达式。

        使用示例:
        - _SymbolDim._is_numeric_literal_str("12")
        - _SymbolDim._is_numeric_literal_str("1e3")

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        return bool(_SymbolDim._NUMERIC_LITERAL_RE.fullmatch(value))

    @staticmethod
    def _normalize_str(value: str) -> str:
        """统一规范化字符串输入并校验。


        功能说明:
        - 使用 strip() 去除首尾空白。
        - 空字符串或仅空白字符串抛 ValueError。
        - 数值字面量字符串抛 ValueError。

        使用示例:
        - _SymbolDim._normalize_str(" N ")

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        normalized = value.strip()
        if not normalized:
            raise ValueError("SymbolDim string must not be blank")
        if _SymbolDim._is_numeric_literal_str(normalized):
            raise ValueError("SymbolDim string must not be numeric")
        return normalized

    @staticmethod
    def _is_truediv_expr(expr: sp.Basic) -> bool:
        """判断表达式是否属于真除法链。


        功能说明:
        - 识别由 `__truediv__`/`__rtruediv__` 构造的嵌套 `Mul(..., Pow(..., -1))` 结构。
        - 仅用于生成对外公开值，不改变内部表达式对象。

        使用示例:
        - _SymbolDim._is_truediv_expr(SymbolDim("A").get_symbol() / SymbolDim("B").get_symbol())

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        return _SymbolDim._split_truediv_expr(expr) is not None

    @staticmethod
    def _split_truediv_expr(expr: sp.Basic) -> tuple[sp.Basic, list[sp.Basic]] | None:
        """拆解真除法链的分子与分母因子顺序。


        功能说明:
        - 将内部 `Mul(lhs, Pow(rhs, -1))` 结构拆为 `(numerator, [denominator...])`。
        - 分母因子按公开运算顺序保存，便于输出稳定且可区分的公开值。

        使用示例:
        - _SymbolDim._split_truediv_expr(SymbolDim("A").get_symbol() / SymbolDim("B").get_symbol())

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        if not isinstance(expr, sp.Mul) or len(expr.args) != 2:
            return None

        reciprocal = None
        numerator = None
        for arg in expr.args:
            if isinstance(arg, sp.Pow) and arg.exp == -1:
                reciprocal = arg.base
            else:
                numerator = arg

        if reciprocal is None or numerator is None:
            return None

        nested = _SymbolDim._split_truediv_expr(numerator)
        if nested is None:
            return numerator, [reciprocal]

        base_numerator, denominator_factors = nested
        return base_numerator, [reciprocal, *denominator_factors]

    @staticmethod
    def _format_public_expr(expr: sp.Basic) -> str:
        """格式化对外公开表达式片段。


        功能说明:
        - 对分子、分母因子进行最小必要的字符串格式化。
        - 对加法等低优先级表达式补括号，避免公开值歧义。

        使用示例:
        - _SymbolDim._format_public_expr(sp.Symbol("N") + 1)

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        formatted = str(_SymbolDim._simplify_quiet(expr))
        if expr.is_Add:
            return f"({formatted})"
        return formatted

    @staticmethod
    def _format_public_value_expr(expr: sp.Basic) -> str:
        """格式化公开值表达式，优先保留 `/` 与 `//` 语义文本。


        功能说明:
        - 对真除法链保留 `/` 文本与原始分母顺序。
        - 对由 `sp.floor(...)` 表达的整除链统一格式化为 `//`。
        - 其他表达式退回 `_format_public_expr(...)` 的最小必要括号规则。

        使用示例:
        - _SymbolDim._format_public_value_expr(sp.floor(sp.Symbol("N") / 2))

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        if expr.is_number:
            return str(_SymbolDim._simplify_quiet(expr))
        if _SymbolDim._is_unknown_expr(expr):
            return "?"
        if expr.is_Add:
            terms = expr.as_ordered_terms()
            formatted_terms: list[str] = []
            for index, term in enumerate(terms):
                if term.could_extract_minus_sign():
                    text = _SymbolDim._format_public_value_expr(-term)
                    formatted_terms.append(f"- {text}" if index > 0 else f"-{text}")
                else:
                    text = _SymbolDim._format_public_value_expr(term)
                    formatted_terms.append(f"+ {text}" if index > 0 else text)
            return " ".join(formatted_terms)
        if expr.is_Mul and not _SymbolDim._is_truediv_expr(expr):
            coeff, factors = expr.as_coeff_mul()
            formatted_factors: list[str] = []
            if coeff == -1:
                prefix = "-"
            elif coeff != 1:
                prefix = f"{coeff}*"
            else:
                prefix = ""
            for factor in factors:
                factor_text = _SymbolDim._format_public_value_expr(factor)
                if factor.is_Add:
                    factor_text = f"({factor_text})"
                formatted_factors.append(factor_text)
            if not formatted_factors:
                return str(coeff)
            joined = "*".join(formatted_factors)
            return f"{prefix}{joined}" if prefix else joined
        if _SymbolDim._is_truediv_expr(expr):
            split_expr = _SymbolDim._split_truediv_expr(expr)
            if split_expr is not None:
                numerator, denominator_factors = split_expr
                numerator_text = _SymbolDim._format_public_value_expr(numerator)
                denominator_parts = [
                    _SymbolDim._format_public_value_expr(factor)
                    for factor in denominator_factors
                    if _SymbolDim._simplify_quiet(factor) != 1
                ]
                if not denominator_parts:
                    return numerator_text
                if len(denominator_parts) == 1:
                    return f"{numerator_text}/{denominator_parts[0]}"
                return f"{numerator_text}/({'*'.join(denominator_parts)})"
        if expr.func == sp.floor and len(expr.args) == 1:
            floor_arg = expr.args[0]
            split_expr = _SymbolDim._split_truediv_expr(floor_arg)
            if split_expr is not None:
                numerator, denominator_factors = split_expr
                numerator_text = _SymbolDim._format_public_value_expr(numerator)
                if any(token in numerator_text for token in (" // ", "/", " + ", " - ")):
                    numerator_text = f"({numerator_text})"
                denominator_parts = [
                    _SymbolDim._format_public_value_expr(factor)
                    for factor in denominator_factors
                    if _SymbolDim._simplify_quiet(factor) != 1
                ]
                if not denominator_parts:
                    return numerator_text
                if len(denominator_parts) == 1:
                    return f"{numerator_text} // {denominator_parts[0]}"
                return f"{numerator_text} // ({'*'.join(denominator_parts)})"
        if expr.func == sp.Min and len(expr.args) == 2:
            lhs_text = _SymbolDim._format_public_value_expr(expr.args[0])
            rhs_text = _SymbolDim._format_public_value_expr(expr.args[1])
            return f"min({lhs_text}, {rhs_text})"
        if expr.func == sp.Max and len(expr.args) == 2:
            lhs_text = _SymbolDim._format_public_value_expr(expr.args[0])
            rhs_text = _SymbolDim._format_public_value_expr(expr.args[1])
            return f"max({lhs_text}, {rhs_text})"
        return _SymbolDim._format_public_expr(expr)

    @staticmethod
    def _public_value(expr: sp.Basic) -> int | float | str | sp.Basic:
        """生成稳定的公开比较值。


        功能说明:
        - 先按 SymPy 做最小必要简化，静态结果返回 Python 数值。
        - 对动态真除法链保留分母出现顺序，避免不同链式顺序对外公开值混同。
        - 其他动态表达式返回 SymPy 简化后的稳定字符串。

        使用示例:
        - _SymbolDim._public_value(SymbolDim("A").get_symbol())

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        if _SymbolDim._is_unknown_expr(expr):
            return "?"

        simplified = _SymbolDim._simplify_quiet(expr)
        if simplified.is_number:
            if simplified.is_integer:
                return int(simplified)
            return float(simplified)

        if _SymbolDim._is_unknown_expr(simplified):
            return "?"

        if expr.free_symbols:
            return _SymbolDim._format_public_value_expr(expr)
        return simplified

    @staticmethod
    def _should_use_simplified_quotient(expr: sp.Basic, simplified: sp.Basic) -> bool:
        """判断除法结果是否应采用简化表达式。


        功能说明:
        - 仅在简化结果明显收短表达式时采用 `sp.simplify(...)` 的结果。
        - 避免把链式除法的公开顺序信息一并抹平成同一个表达式。

        使用示例:
        - _SymbolDim._should_use_simplified_quotient(expr, sp.simplify(expr))

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        if simplified.is_number:
            return True
        return sp.count_ops(simplified) < sp.count_ops(expr)

    @staticmethod
    def _simplify_quiet(expr: sp.Basic) -> sp.Basic:
        """静默执行 SymPy 简化。


        功能说明:
        - 隔离 SymPy 在部分大写符号组合下导入 units 前缀时的 stdout 输出。
        - SymPy 内部失败时回退原表达式，避免公开字符串化因外部简化器状态污染失败。

        使用示例:
        - simplified = _SymbolDim._simplify_quiet(SymbolDim("N").get_symbol())

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """

        try:
            with contextlib.redirect_stdout(io.StringIO()):
                return sp.simplify(expr)
        except SystemError:
            return expr

    @staticmethod
    def _symbol_from_str(value: str) -> sp.Basic:
        """基于字符串创建带假设的符号。


        功能说明:
        - 统一使用 integer=True, real=True 的假设构造符号或符号表达式。
        - 表达式字符串仅放行 `floor(...)`、小写 `min(...)` 与小写 `max(...)` 函数。

        使用示例:
        - _SymbolDim._symbol_from_str("N")

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        normalized = _SymbolDim._normalize_str(value)
        if _SymbolDim._contains_unknown_token(normalized):
            parse_text = _SymbolDim._replace_unknown_tokens_for_parse(normalized)
            _SymbolDim._parse_expr_str(parse_text)
            return _SymbolDim._unknown_symbol()
        if re.search(r"//|[+\-*/()]", normalized):
            return _SymbolDim._parse_expr_str(normalized)
        symbol = sp.symbols(normalized, integer=True, real=True)
        if not isinstance(symbol, sp.Symbol):
            _SymbolDim._raise_invalid_expr()
        return symbol

    @staticmethod
    def _normalize_symbol(sym: sp.Basic) -> sp.Basic:
        """规范化 sympy.Symbol 的默认假设。


        功能说明:
        - 当 sym 为未显式指定 is_integer/is_real 的 Symbol 时，按名称重建为 integer=True, real=True。
        - 其他情况保持原样。

        使用示例:
        - _SymbolDim._normalize_symbol(sp.Symbol("N"))

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        if isinstance(sym, sp.Symbol) and sym.is_integer is None and sym.is_real is None:
            return _SymbolDim._symbol_from_str(sym.name)
        if isinstance(sym, sp.Basic) and sym.free_symbols:
            replacements = {
                symbol: _SymbolDim._symbol_from_str(symbol.name)
                for symbol in sym.free_symbols
                if symbol.is_integer is None and symbol.is_real is None
            }
            if replacements:
                return sym.xreplace(replacements)
        return sym

    @staticmethod
    def _coerce_symbol_expr(
        value: SymbolDimOperand | float,
        *,
        float_error: str,
        type_error_prefix: str,
    ) -> sp.Basic:
        """统一将输入规整为内部 sympy 表达式。


        功能说明:
        - 统一处理 `_SymbolDim`、`int`、`str`、`sympy.Basic` 的规整逻辑。
        - 通过参数保留构造路径与操作数路径各自的错误消息。
        - `sympy.Float` 与含浮点字面量的 `sympy.Basic` 表达式统一按浮点输入拒绝。

        使用示例:
        - _SymbolDim._coerce_symbol_expr("N", float_error="...", type_error_prefix="...")

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        if isinstance(value, _SymbolDim):
            return value.get_symbol()
        if isinstance(value, float):
            raise NotImplementedError(float_error)
        if isinstance(value, int):
            return sp.Integer(value)
        if isinstance(value, str):
            return _SymbolDim._symbol_from_str(value)
        if isinstance(value, sp.Basic):
            if value.has(sp.Float):
                raise NotImplementedError(float_error)
            return _SymbolDim._normalize_symbol(value)
        raise TypeError(f"{type_error_prefix}: {type(value)!r}")

    def __init__(self, sym: int | str | sp.Basic) -> None:
        """初始化符号维度。


        功能说明:
        - int 转为 sympy.Integer。
        - str 必须为非数值字面量且非空白字符串，转为 sympy.symbols(..., integer=True, real=True)。
        - sympy.Basic 默认直接保存；若为未设定假设的 Symbol，则统一为 integer=True, real=True。
        - 数值字面量字符串或空白字符串抛 ValueError。
        - 其他类型抛 TypeError。

        使用示例:
        - SymbolDim(16)
        - SymbolDim("N")
        - SymbolDim(sp.symbols("M"))

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        self.sym = self._coerce_symbol_expr(
            sym,
            float_error="Float input is not supported",
            type_error_prefix="Unsupported SymbolDim type",
        )

    @staticmethod
    def _normalize_operand(value: int | str | sp.Basic | "_SymbolDim") -> sp.Basic:
        """统一规范化操作数为 sympy 表达式。


        功能说明:
        - 支持 int/str/sympy.Basic/_SymbolDim，其他类型抛 TypeError。
        - str 与构造路径一致，空白/数值字面量字符串抛 ValueError。
        - sympy.Symbol 若无显式假设，统一规范化为 integer=True, real=True。

        使用示例:
        - _SymbolDim._normalize_operand(4)
        - _SymbolDim._normalize_operand("M")

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        return _SymbolDim._coerce_symbol_expr(
            value,
            float_error="Float operand is not supported",
            type_error_prefix="Unsupported operand type",
        )

    @staticmethod
    def _quotient_expr(numerator: sp.Basic, denominator: sp.Basic) -> sp.Basic:
        """构造保留顺序的除法表达式。


        功能说明:
        - 统一使用 `Mul(..., Pow(..., -1, evaluate=False))` 保存除法链顺序。
        - 供真除法与整除共用，避免重复定义除法底层结构。

        使用示例:
        - _SymbolDim._quotient_expr(sp.Symbol("N"), sp.Integer(2))

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        return sp.Mul(numerator, sp.Pow(denominator, -1, evaluate=False), evaluate=False)

    def _binary_symbol_op(
        self,
        other: int | str | sp.Basic | "_SymbolDim",
        operator,
        *,
        reverse: bool = False,
    ) -> "SymbolDim":
        """统一执行二元符号算术。


        功能说明:
        - 统一处理正向与反向的加减乘路径。
        - 先规整操作数，再按传入 operator 组装最终 sympy 表达式。

        使用示例:
        - SymbolDim("N")._binary_symbol_op(2, lambda lhs, rhs: lhs + rhs)

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        lhs = self._normalize_operand(other) if reverse else self.get_symbol()
        rhs = self.get_symbol() if reverse else self._normalize_operand(other)
        if self._is_unknown_expr(lhs) or self._is_unknown_expr(rhs):
            return SymbolDim(self._unknown_symbol())
        return SymbolDim(operator(lhs, rhs))

    def _quotient(
        self,
        other: int | str | sp.Basic | "_SymbolDim",
        *,
        reverse: bool = False,
        floordiv: bool = False,
    ) -> "SymbolDim":
        """统一执行真除法与整除。


        功能说明:
        - 共用同一套操作数规整、顺序保留与最小必要简化逻辑。
        - 静态整除直接返回整数结果；动态整除继续保留 `floor(...)` 结构。

        使用示例:
        - SymbolDim("N")._quotient(2)
        - SymbolDim("N")._quotient(2, floordiv=True)

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        lhs = self._normalize_operand(other) if reverse else self.get_symbol()
        rhs = self.get_symbol() if reverse else self._normalize_operand(other)
        if self._is_unknown_expr(lhs) or self._is_unknown_expr(rhs):
            return SymbolDim(self._unknown_symbol())
        if floordiv and not lhs.free_symbols and not rhs.free_symbols:
            return SymbolDim(sp.Integer(int(self._simplify_quiet(lhs)) // int(self._simplify_quiet(rhs))))

        expr = self._quotient_expr(lhs, rhs)
        expr = sp.floor(expr) if floordiv else expr
        simplified = self._simplify_quiet(expr)
        if self._should_use_simplified_quotient(expr, simplified):
            return SymbolDim(simplified)
        return SymbolDim(expr)

    def get_symbol(self) -> sp.Basic:
        """获取内部 sympy 表达式。


        功能说明:
        - 返回内部保存的 sympy 表达式对象。

        使用示例:
        - SymbolDim("N").get_symbol()

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        return self.sym

    def get_value(self):
        """获取对外可比较的数值/表达式。


        功能说明:
        - 静态整数/表达式返回 Python 数值。
        - 含符号表达式返回规整后的字符串表达。

        使用示例:
        - SymbolDim(8).get_value()
        - (SymbolDim(9) / SymbolDim(4)).get_value()

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        return self._public_value(self.get_symbol())

    def __repr__(self) -> str:
        """返回符号维度的字符串表示。


        功能说明:
        - 返回 str(get_symbol())。

        使用示例:
        - repr(SymbolDim("N"))

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        return str(self.get_symbol())

    def __str__(self) -> str:
        """返回符号维度的公开字符串表示。


        功能说明:
        - 复用 `get_value()` 的公开口径输出字符串。
        - 对外统一保留 `/` 与 `//` 文本，不暴露 `floor(...)` 形式。

        使用示例:
        - str(SymbolDim("N") // 2)

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        return str(self.get_value())

    def __add__(self, other: int | str | sp.Basic | "_SymbolDim") -> "SymbolDim":
        """符号维度加法。


        功能说明:
        - 支持 int/str/SymbolDim，加法结果返回 SymbolDim。

        使用示例:
        - SymbolDim("N") + 2

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        return self._binary_symbol_op(other, lambda lhs, rhs: lhs + rhs)

    def __radd__(self, other: int | str | sp.Basic | "_SymbolDim") -> "SymbolDim":
        """符号维度反向加法。


        功能说明:
        - 支持 int/str/SymbolDim，返回 SymbolDim。

        使用示例:
        - 3 + SymbolDim("N")

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        return self._binary_symbol_op(other, lambda lhs, rhs: lhs + rhs, reverse=True)

    def __sub__(self, other: int | str | sp.Basic | "_SymbolDim") -> "SymbolDim":
        """符号维度减法。


        功能说明:
        - 支持 int/str/SymbolDim，返回 SymbolDim。

        使用示例:
        - SymbolDim("N") - "M"

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        return self._binary_symbol_op(other, lambda lhs, rhs: lhs - rhs)

    def __rsub__(self, other: int | str | sp.Basic | "_SymbolDim") -> "SymbolDim":
        """符号维度反向减法。


        功能说明:
        - 支持 int/str/SymbolDim，返回 SymbolDim。

        使用示例:
        - 10 - SymbolDim("N")

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        return self._binary_symbol_op(other, lambda lhs, rhs: lhs - rhs, reverse=True)

    def __mul__(self, other: int | str | sp.Basic | "_SymbolDim") -> "SymbolDim":
        """符号维度乘法。


        功能说明:
        - 支持 int/str/SymbolDim，返回 SymbolDim。

        使用示例:
        - SymbolDim("N") * 2

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        return self._binary_symbol_op(other, lambda lhs, rhs: lhs * rhs)

    def __rmul__(self, other: int | str | sp.Basic | "_SymbolDim") -> "SymbolDim":
        """符号维度反向乘法。


        功能说明:
        - 支持 int/str/SymbolDim，返回 SymbolDim。

        使用示例:
        - 3 * SymbolDim("N")

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        return self._binary_symbol_op(other, lambda lhs, rhs: lhs * rhs, reverse=True)

    def __truediv__(self, other: int | str | sp.Basic | "_SymbolDim") -> "SymbolDim":
        """符号维度除法。


        功能说明:
        - 支持 int/str/SymbolDim，返回 SymbolDim。

        使用示例:
        - SymbolDim("N") / 2

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        return self._quotient(other)

    def __rtruediv__(self, other: int | str | sp.Basic | "_SymbolDim") -> "SymbolDim":
        """符号维度反向除法。


        功能说明:
        - 支持 int/str/SymbolDim，返回 SymbolDim。

        使用示例:
        - "K" / SymbolDim("N")

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        return self._quotient(other, reverse=True)

    def __floordiv__(self, other: int | str | sp.Basic | "_SymbolDim") -> "SymbolDim":
        """符号维度整除。


        功能说明:
        - 支持 int/str/SymbolDim，返回 SymbolDim。

        使用示例:
        - SymbolDim("N") // 2

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        return self._quotient(other, floordiv=True)

    def __rfloordiv__(self, other: int | str | sp.Basic | "_SymbolDim") -> "SymbolDim":
        """符号维度反向整除。


        功能说明:
        - 支持 int/str/SymbolDim，返回 SymbolDim。

        使用示例:
        - 3 // SymbolDim("N")

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        return self._quotient(other, reverse=True, floordiv=True)

    def __eq__(self, other: SymbolDimOperand) -> bool:
        """比较符号维度表达式等价性。


        功能说明:
        - 支持 int/str/sympy.Basic/SymbolDim，比较底层 sympy 表达式。
        - 其他类型抛 TypeError。

        使用示例:
        - SymbolDim("N") == "N"

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        if not isinstance(other, (_SymbolDim, int, str, sp.Basic)):
            raise TypeError(f"Unsupported comparison type: {type(other)!r}")
        return self.get_symbol() == self._normalize_operand(other)


class SymbolDim(_SymbolDim):
    """对外公开的符号维度类型。


    功能说明:
    - 提供动态性判断能力。

    使用示例:
    - SymbolDim("N").is_dynamic()

    关联文件:
    - spec: spec/symbol_variable/symbol_dim.md
    - test: test/symbol_variable/test_symbol_dim.py
    - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
    """

    def is_dynamic(self) -> bool:
        """判断符号维度是否为动态维度。


        功能说明:
        - 当内部表达式包含自由符号时返回 True。

        使用示例:
        - SymbolDim(8).is_dynamic()
        - SymbolDim("N").is_dynamic()

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: kernel_gen/symbol_variable/symbol_dim.py
        """
        return bool(self.get_symbol().free_symbols)
