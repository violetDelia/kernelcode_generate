"""symbol expression package.

功能说明:
- 聚合 symbol expression 内部 helper。

API 列表:
- 包内实现模块，无 root 公开 API。

使用示例:
- `from kernel_gen.dialect.symbol.expr import ...`

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/symbol/
- 功能实现: kernel_gen/dialect/symbol/expr/__init__.py
"""

from __future__ import annotations

from .parser import (
    _SymbolExprAttrParser,
    _SymbolExprNode,
    _SymbolExprParserBase,
    _SymbolExprTextParser,
    _SymbolExprToken,
    _canonicalize_symbolic_expr,
    _contains_symbol_expr_iter,
    _contains_symbol_expr_unknown,
    _evaluate_concrete_expr,
    _format_symbol_expr_add,
    _format_symbol_expr_node,
    _get_concrete_symbol_expr_node_value,
    _get_symbol_expr_const,
    _is_supported_symbol_expr,
    _is_symbol_expr_unknown,
    _linear_symbol_expr_terms,
    _make_symbol_expr_add,
    _make_symbol_expr_const,
    _make_symbol_expr_iter,
    _make_symbol_expr_keyword_binary,
    _make_symbol_expr_max,
    _make_symbol_expr_min,
    _make_symbol_expr_mul,
    _make_symbol_expr_neg,
    _make_symbol_expr_sub,
    _make_symbol_expr_symbol,
    _make_symbol_expr_unknown,
    _normalize_expr,
    _parse_symbol_expr_from_attr_parser,
    _parse_symbol_expr_from_text,
    _symbol_expr_precedence,
    _tokenize_symbol_expr,
)

__all__ = [
    "_SymbolExprAttrParser",
    "_SymbolExprNode",
    "_SymbolExprParserBase",
    "_SymbolExprTextParser",
    "_SymbolExprToken",
    "_canonicalize_symbolic_expr",
    "_contains_symbol_expr_iter",
    "_contains_symbol_expr_unknown",
    "_evaluate_concrete_expr",
    "_format_symbol_expr_add",
    "_format_symbol_expr_node",
    "_get_concrete_symbol_expr_node_value",
    "_get_symbol_expr_const",
    "_is_supported_symbol_expr",
    "_is_symbol_expr_unknown",
    "_linear_symbol_expr_terms",
    "_make_symbol_expr_add",
    "_make_symbol_expr_const",
    "_make_symbol_expr_iter",
    "_make_symbol_expr_keyword_binary",
    "_make_symbol_expr_max",
    "_make_symbol_expr_min",
    "_make_symbol_expr_mul",
    "_make_symbol_expr_neg",
    "_make_symbol_expr_sub",
    "_make_symbol_expr_symbol",
    "_make_symbol_expr_unknown",
    "_normalize_expr",
    "_parse_symbol_expr_from_attr_parser",
    "_parse_symbol_expr_from_text",
    "_symbol_expr_precedence",
    "_tokenize_symbol_expr",
]
