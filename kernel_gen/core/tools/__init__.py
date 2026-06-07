"""core tools package.


功能说明:
- 承载 `kernel_gen.core` 下可复用的工具型公共子模块。
- 包根不转发子模块公开 API，调用方应从具体子模块导入所需入口。

API 列表:
- 无公开 API。

使用示例:
- from kernel_gen.core.tools.dump_dir import DumpDirWriter

关联文件:
- spec: [spec/core/tools/dump_dir.md](../../../spec/core/tools/dump_dir.md)
- test: [test/core/test_dump_dir_writer.py](../../../test/core/test_dump_dir_writer.py)
- 功能实现: [kernel_gen/core/tools/__init__.py](../../../kernel_gen/core/tools/__init__.py)
- 功能实现: [kernel_gen/core/tools/dump_dir/writer.py](dump_dir/writer.py)
"""

from __future__ import annotations

__all__: list[str] = []
