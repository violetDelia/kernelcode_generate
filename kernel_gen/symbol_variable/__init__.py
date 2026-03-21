"""Symbol variable package.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 提供符号维度、形状、内存与类型枚举的统一导入入口。

使用示例:
- from kernel_gen.symbol_variable import SymbolDim, SymbolShape, SymbolList, Memory, MemorySpace, NumericType, Farmat

关联文件:
- spec: spec/symbol_variable/package_api.md
- test: test/symbol_variable/test_package_api.py
- 功能实现: kernel_gen/symbol_variable/__init__.py
- 功能实现: kernel_gen/symbol_variable/symbol_dim.py
- 功能实现: kernel_gen/symbol_variable/symbol_shape.py
- 功能实现: kernel_gen/symbol_variable/memory.py
- 功能实现: kernel_gen/symbol_variable/type.py
"""

from __future__ import annotations

from .memory import LocalSpaceMeta, Memory, MemorySpace
from .symbol_dim import SymbolDim
from .symbol_shape import SymbolList, SymbolShape
from .type import Farmat, NumericType

__all__ = [
    "Farmat",
    "LocalSpaceMeta",
    "Memory",
    "MemorySpace",
    "NumericType",
    "SymbolDim",
    "SymbolList",
    "SymbolShape",
]
