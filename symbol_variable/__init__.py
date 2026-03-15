"""Symbol variable package.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 提供符号维度、形状与内存相关类型的统一导入入口。

使用示例:
- from symbol_variable import SymbolDim, SymbolShape, SymbolList, Memory, MemorySpace, NumericType, Farmat

关联文件:
- spec: spec/symbol_variable/symbol_dim.md
- spec: spec/symbol_variable/symbol_shape.md
- spec: spec/symbol_variable/memory.md
- spec: spec/symbol_variable/package_api.md
- test: test/symbol_variable/test_symbol_dim.py
- test: test/symbol_variable/test_symbol_shape.py
- test: test/symbol_variable/test_memory.py
- test: test/symbol_variable/test_package_api.py
- 功能实现: symbol_variable/symbol_dim.py
- 功能实现: symbol_variable/symbol_shape.py
- 功能实现: symbol_variable/memory.py
- 功能实现: symbol_variable/type.py
"""

from __future__ import annotations

from .memory import LocalSpaceMeta, Memory, MemorySpace
from .symbol_dim import SymbolDim
from .symbol_shape import SymbolList, SymbolShape
from .type import Farmat, NumericType

__all__ = [
    "LocalSpaceMeta",
    "Memory",
    "MemorySpace",
    "NumericType",
    "Farmat",
    "SymbolDim",
    "SymbolList",
    "SymbolShape",
]
