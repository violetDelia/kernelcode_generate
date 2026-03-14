"""Symbol variable package.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 提供符号维度相关类型的统一导入入口。

使用示例:
- from symbol_variable import SymbolDim

关联文件:
- spec: spec/symbol_variable/symbol_dim.md
- test: test/symbol_variable/test_symbol_dim.py
- 功能实现: symbol_variable/symbol_dim.py
"""

from __future__ import annotations

from .symbol_dim import SymbolDim

__all__ = ["SymbolDim"]
