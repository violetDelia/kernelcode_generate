"""npu target package.

创建者: 大哥大
最后一次更改: 大哥大

功能说明:
- 导出 npu info。

使用示例:
- from target.npu import info

关联文件:
- spec: spec/target/npu.md
- test: test/target/test_npu_info.py
- 功能实现: target/npu/__init__.py
"""

from . import info

__all__ = ["info"]
