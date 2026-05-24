"""symbol expression implementation package.

功能说明:
- 保留 `symbol.expr` package 边界，不再跨文件 re-export 私有 parser helper。

API 列表:
- 包内实现 package，无公开 API。

使用示例:
- 通过 `SymbolExprAttr.from_expr(...)` 使用公开 symbol expression 能力。

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/symbol/
- 功能实现: kernel_gen/dialect/symbol/attr/expr_attr.py
"""

from __future__ import annotations

__all__: list[str] = []
