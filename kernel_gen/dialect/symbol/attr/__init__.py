"""symbol attr package.

功能说明:
- 聚合 symbol package 内公开 attr。

API 列表:
- `class SymbolExprAttr(expr: StringAttr)`
- `class SymbolIterAttr(start: SymbolExprAttr, end: SymbolExprAttr, step: SymbolExprAttr)`

使用示例:
- `from kernel_gen.dialect.symbol.attr import ...`

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/symbol/
- 功能实现: kernel_gen/dialect/symbol/attr/__init__.py
"""

from __future__ import annotations

from .expr_attr import SymbolExprAttr
from .iter_attr import SymbolIterAttr

__all__ = ["SymbolExprAttr", "SymbolIterAttr"]
