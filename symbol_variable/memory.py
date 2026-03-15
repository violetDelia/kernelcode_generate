"""Memory implementation.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 定义内存空间枚举与 Memory 对象，独立描述形状与类型信息。

使用示例:
- from symbol_variable.memory import Memory, MemorySpace
- Memory([1, 2], NumericType.Float32, space=MemorySpace.GM)

关联文件:
- spec: spec/symbol_variable/memory.md
- test: test/symbol_variable/test_memory.py
- 功能实现: symbol_variable/memory.py
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from symbol_variable.symbol_shape import SymbolList
from symbol_variable.type import Farmat, NumericType


@dataclass(frozen=True)
class LocalSpaceMeta:
    """空间元信息描述。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 描述空间名称、最大容量与对齐要求。

    使用示例:
    - LocalSpaceMeta(name="GM", max_size=None, align=1024)

    关联文件:
    - spec: spec/symbol_variable/memory.md
    - test: test/symbol_variable/test_memory.py
    - 功能实现: symbol_variable/memory.py
    """

    name: str
    max_size: int | None
    align: int


class MemorySpace(Enum):
    """内存空间枚举。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 定义 GM/SM/LM/TSM/TLM 等空间枚举项。

    使用示例:
    - MemorySpace.GM.value.align

    关联文件:
    - spec: spec/symbol_variable/memory.md
    - test: test/symbol_variable/test_memory.py
    - 功能实现: symbol_variable/memory.py
    """

    GM = LocalSpaceMeta(name="GM", max_size=None, align=1024)
    SM = LocalSpaceMeta(name="SM", max_size=None, align=1024)
    LM = LocalSpaceMeta(name="LM", max_size=None, align=1024)
    TSM = LocalSpaceMeta(name="TSM", max_size=None, align=1024)
    TLM = LocalSpaceMeta(name="TLM", max_size=None, align=1024)


class Memory:
    """内存对象，独立描述形状与空间信息。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 记录所在空间，并保存 shape/dtype/stride/format。

    使用示例:
    - Memory([1, 2], NumericType.Float32)

    关联文件:
    - spec: spec/symbol_variable/memory.md
    - test: test/symbol_variable/test_memory.py
    - 功能实现: symbol_variable/memory.py
    """

    def __init__(
        self,
        shape,
        dtype: NumericType,
        space: MemorySpace = MemorySpace.GM,
        stride=None,
        format: Farmat = Farmat.Norm,
    ) -> None:
        """初始化 Memory。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 规范化 shape/stride，并记录 space。

        使用示例:
        - Memory([1, 2], NumericType.Float32, space=MemorySpace.LM)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory.py
        - 功能实现: symbol_variable/memory.py
        """
        self.shape = SymbolList.convert_from_list(shape)
        self.dtype = dtype
        self.stride = None if stride is None else SymbolList.convert_from_list(stride)
        self.format = format
        self.space = space

    def __repr__(self) -> str:
        """返回 Memory 的字符串表示。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 返回 Memory(<space name>,shape=...,dtype=...,stride=...,format=...)。

        使用示例:
        - repr(Memory([1, 2], NumericType.Float32))

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory.py
        - 功能实现: symbol_variable/memory.py
        """
        tensor_repr = (
            "Tensor("
            f"shape={self.shape}, "
            f"dtype={self.dtype}, "
            f"stride={self.stride}, "
            f"format={self.format}"
            ")"
        )
        return f"Memory({self.space.name},{tensor_repr})"

    @staticmethod
    def convert_from_tensor(tensor) -> "Memory":
        """由类 Tensor 对象构造 Memory。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 复制 shape/dtype/stride/format，空间默认 GM。

        使用示例:
        - Memory.convert_from_tensor(obj)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory.py
        - 功能实现: symbol_variable/memory.py
        """
        return Memory(
            tensor.shape,
            tensor.dtype,
            stride=tensor.stride,
            format=tensor.format,
        )
