"""Python 层模块入口。

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 提供 operation 子模块的统一入口。

使用示例:
- from python.operation import add

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/test_operation_nn.py
- 功能实现: python/operation/nn.py
"""

from .operation import add, eq, ge, gt, le, lt, mul, ne, sub, truediv

__all__ = [
    "add",
    "sub",
    "mul",
    "truediv",
    "eq",
    "ne",
    "lt",
    "le",
    "gt",
    "ge",
]
