"""symbol type package.

功能说明:
- 聚合 symbol package 内公开 type。

API 列表:
- `class SymbolValueType(expr: SymbolExprAttr)`
- `class SymbolIterType(start: SymbolExprAttr, end: SymbolExprAttr, step: SymbolExprAttr)`
- `class SymbolPtrType(dtype: Attribute, template_name: StringAttr | str | None = None)`

使用示例:
- `from kernel_gen.dialect.symbol.type import ...`

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/symbol/
- 功能实现: kernel_gen/dialect/symbol/type/__init__.py
"""

from __future__ import annotations

from .iter_type import SymbolIterType
from .ptr_type import SymbolPtrType
from .value_type import SymbolValueType

__all__ = ["SymbolValueType", "SymbolIterType", "SymbolPtrType"]
