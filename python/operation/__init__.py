"""Operation API 入口。

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 暴露 nn 逐元素算术与比较运算 API。

使用示例:
- from python.operation import add, eq

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/test_operation_nn.py
- 功能实现: python/operation/nn.py
"""

from .nn import add, eq, ge, gt, le, lt, mul, ne, sub, truediv

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
