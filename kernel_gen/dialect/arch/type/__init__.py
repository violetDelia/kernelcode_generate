"""arch type package.

功能说明:
- 聚合 arch package 内公开 type。

API 列表:
- `class ArchTokenType(token_id: StringAttr)`

使用示例:
- `from kernel_gen.dialect.arch.type import ...`

关联文件:
- spec: spec/dialect/arch.md
- test: test/dialect/arch/
- 功能实现: kernel_gen/dialect/arch/type/__init__.py
"""

from __future__ import annotations

from .token import ArchTokenType

__all__ = ["ArchTokenType"]
