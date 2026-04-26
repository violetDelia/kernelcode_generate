"""Common utilities package.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 提供 kernel_gen 内部可复用的通用常量与工具入口。

API 列表:
- `_ERROR_TEMPLATE: str`

使用示例:
- from kernel_gen.common import _ERROR_TEMPLATE
- message = _ERROR_TEMPLATE.format(scene="x", expected="y", actual="z", action="act")

关联文件:
- spec: spec/common/errors.md
- test: test/common/test_errors.py
- 功能实现: kernel_gen/common/__init__.py
- 功能实现: kernel_gen/common/errors.py
"""

from __future__ import annotations

from .errors import _ERROR_TEMPLATE

__all__ = ["_ERROR_TEMPLATE"]
