"""core package.


功能说明:
- 承载 `kernel_gen` 级别的核心公共设施子模块。
- 当前阶段仅提供子模块路径本身，不在包根额外转发公开 API。

API 列表:
- 无公开 API

使用示例:
- from kernel_gen.core.error import KernelCodeError

关联文件:
- spec: [spec/core/error.md](../../spec/core/error.md)
- spec: [spec/core/context.md](../../spec/core/context.md)
- spec: [spec/core/contracts.md](../../spec/core/contracts.md)
- test: [test/core/test_error.py](../../test/core/test_error.py)
- test: [test/core/test_contracts.py](../../test/core/test_contracts.py)
- 功能实现: [kernel_gen/core/__init__.py](../../kernel_gen/core/__init__.py)
- 功能实现: [kernel_gen/core/error.py](../../kernel_gen/core/error.py)
- 功能实现: [kernel_gen/core/context.py](../../kernel_gen/core/context.py)
- 功能实现: [kernel_gen/core/contracts.py](../../kernel_gen/core/contracts.py)
"""

from __future__ import annotations

__all__: list[str] = []
