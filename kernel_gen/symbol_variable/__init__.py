"""Symbol variable package.


功能说明:
- 提供符号维度、形状、内存与类型枚举的统一导入入口。

API 列表:
- `SymbolDim(value: int | str | Expr | Symbol)`
- `SymbolList(shapes: list[int | str | SymbolDim])`
- `SymbolShape(shapes: list[int | str | SymbolDim])`
- `LocalSpaceMeta(name: str, max_size: int | None, align: int)`
- `Memory(shape: ShapeLike, dtype: NumericType | None = None, space: MemorySpace = MemorySpace.GM, stride: ShapeLike | None = None, format: Farmat = Farmat.Norm)`
- `MemorySpace`
- `NumericType`
- `Farmat`

使用示例:
- from kernel_gen.symbol_variable import SymbolDim, SymbolShape, SymbolList, Memory, MemorySpace, NumericType, Farmat

关联文件:
- spec: spec/symbol_variable/package_api.md
- test: test/symbol_variable/test_package.py
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
