"""target package exports.

创建者: 大哥大
最后一次更改: 大哥大

功能说明:
- 导出 Target 相关接口。

使用示例:
- from target import Target

关联文件:
- spec: spec/target/target.md
- test: test/target/test_target.py
- 功能实现: target/__init__.py
"""

from .target import Target, get_current_target, get_target, set_target

__all__ = ["Target", "get_target", "set_target", "get_current_target"]
