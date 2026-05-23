"""arch attr package.

功能说明:
- 聚合 arch package 内公开 attr。

API 列表:
- `class ArchScopeAttr(scope: StringAttr)`
- `class ArchVisibilityAttr(visibility: StringAttr)`

使用示例:
- `from kernel_gen.dialect.arch.attr import ...`

关联文件:
- spec: spec/dialect/arch.md
- test: test/dialect/arch/
- 功能实现: kernel_gen/dialect/arch/attr/__init__.py
"""

from __future__ import annotations

from .scope import ArchScopeAttr
from .visibility import ArchVisibilityAttr

__all__ = ["ArchScopeAttr", "ArchVisibilityAttr"]
