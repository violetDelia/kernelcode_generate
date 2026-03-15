"""Memory implementation.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 定义内存空间枚举与 Memory 对象，独立描述形状与类型信息。

使用示例:
- from python.symbol_variable.memory import Memory, MemorySpace
- Memory([1, 2], NumericType.Float32, space=MemorySpace.GM)

关联文件:
- spec: spec/symbol_variable/memory.md
- test: test/symbol_variable/test_memory.py
- 功能实现: python/symbol_variable/memory.py
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .symbol_shape import SymbolShape
from .type import Farmat, NumericType


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
    - 功能实现: python/symbol_variable/memory.py
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
    - 功能实现: python/symbol_variable/memory.py
    """

    GM = LocalSpaceMeta(name="GM", max_size=None, align=1024)
    SM = LocalSpaceMeta(name="SM", max_size=None, align=1024)
    LM = LocalSpaceMeta(name="LM", max_size=None, align=1024)
    TSM = LocalSpaceMeta(name="TSM", max_size=None, align=1024)
    TLM = LocalSpaceMeta(name="TLM", max_size=None, align=1024)


class Memory:
    """内存对象，独立描述形状与空间信息。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 记录所在空间，并保存 shape/dtype/stride/format。

    使用示例:
    - Memory([1, 2], NumericType.Float32)

    关联文件:
    - spec: spec/symbol_variable/memory.md
    - test: test/symbol_variable/test_memory.py
    - 功能实现: python/symbol_variable/memory.py
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
        最后一次更改: 金铲铲大作战

        功能说明:
        - 规范化 shape/stride，并记录 space。

        使用示例:
        - Memory([1, 2], NumericType.Float32, space=MemorySpace.LM)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory.py
        - 功能实现: python/symbol_variable/memory.py
        """
        self.shape = self._normalize_shape(shape)
        self.dtype = dtype
        self.stride = None if stride is None else self._normalize_shape(stride)
        self.format = format
        self.space = space

    @staticmethod
    def _normalize_shape(value):
        """规范化 shape/stride 输入为 SymbolShape。"""
        if isinstance(value, SymbolShape):
            return value
        return SymbolShape(value)

    def __repr__(self) -> str:
        """返回 Memory 的字符串表示。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 返回 Memory(<space name>,shape=...,dtype=...,stride=...,format=...)。

        使用示例:
        - repr(Memory([1, 2], NumericType.Float32))

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory.py
        - 功能实现: python/symbol_variable/memory.py
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
 
    def _ensure_same_shape(self, other: "Memory") -> None:
        """校验 Memory 形状一致。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 使用序列化结果判断形状是否完全一致，不支持广播。

        使用示例:
        - mem._ensure_same_shape(other)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: python/symbol_variable/memory.py
        """
        if self.shape.get_values() != other.shape.get_values():
            raise ValueError("Memory shape mismatch")

    def _ensure_same_dtype(self, other: "Memory") -> None:
        """校验 Memory 数据类型兼容性。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 当前实现仅允许 dtype 完全一致。

        使用示例:
        - mem._ensure_same_dtype(other)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: python/symbol_variable/memory.py
        """
        if self.dtype is not other.dtype:
            raise TypeError("Memory dtype mismatch")

    def _ensure_scalar_compatible(self, value: object) -> None:
        """校验标量输入兼容性。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 阶段一仅支持 int 标量，且需与 dtype 兼容。

        使用示例:
        - mem._ensure_scalar_compatible(1)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: python/symbol_variable/memory.py
        """
        if isinstance(value, bool):
            value = int(value)
        if not isinstance(value, int):
            raise TypeError("Unsupported scalar type for Memory operation")
        if self.dtype not in (NumericType.Int32, NumericType.Float32):
            raise TypeError("Scalar incompatible with Memory dtype")

    def _clone_symbol_list(self, value) -> "SymbolShape | None":
        """克隆符号列表对象。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 复制 SymbolShape/SymbolList 的容器，避免别名共享。

        使用示例:
        - mem._clone_symbol_list(mem.shape)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: python/symbol_variable/memory.py
        """
        if value is None:
            return None
        return SymbolShape(value.get_values())

    def _clone_with_dtype(self, dtype: NumericType) -> "Memory":
        """按指定 dtype 克隆 Memory。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 继承 shape/stride/format/space，替换 dtype，并避免元数据别名复用。

        使用示例:
        - mem._clone_with_dtype(NumericType.Int32)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: python/symbol_variable/memory.py
        """
        shape = self._clone_symbol_list(self.shape)
        stride = self._clone_symbol_list(self.stride)
        return Memory(shape, dtype, space=self.space, stride=stride, format=self.format)

    def _binary_arithmetic(self, other: object) -> "Memory":
        """逐元素算术运算入口。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/int，返回 Memory。

        使用示例:
        - mem._binary_arithmetic(other)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: python/symbol_variable/memory.py
        """
        if isinstance(other, Memory):
            self._ensure_same_shape(other)
            self._ensure_same_dtype(other)
            return self._clone_with_dtype(self.dtype)
        self._ensure_scalar_compatible(other)
        return self._clone_with_dtype(self.dtype)

    def _binary_compare(self, other: object) -> "Memory":
        """逐元素比较运算入口。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/int，返回 predicate dtype。

        使用示例:
        - mem._binary_compare(other)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: python/symbol_variable/memory.py
        """
        if isinstance(other, Memory):
            self._ensure_same_shape(other)
            self._ensure_same_dtype(other)
            return self._clone_with_dtype(NumericType.Int32)
        self._ensure_scalar_compatible(other)
        return self._clone_with_dtype(NumericType.Int32)

    def __add__(self, other: object) -> "Memory":
        """逐元素加法。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/int。

        使用示例:
        - mem + 1

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: python/symbol_variable/memory.py
        """
        return self._binary_arithmetic(other)

    def __radd__(self, other: object) -> "Memory":
        """逐元素反向加法。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 int + Memory。

        使用示例:
        - 1 + mem

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: python/symbol_variable/memory.py
        """
        return self._binary_arithmetic(other)

    def __sub__(self, other: object) -> "Memory":
        """逐元素减法。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/int。

        使用示例:
        - mem - 1

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: python/symbol_variable/memory.py
        """
        return self._binary_arithmetic(other)

    def __rsub__(self, other: object) -> "Memory":
        """逐元素反向减法。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 int - Memory。

        使用示例:
        - 1 - mem

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: python/symbol_variable/memory.py
        """
        return self._binary_arithmetic(other)

    def __mul__(self, other: object) -> "Memory":
        """逐元素乘法。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/int。

        使用示例:
        - mem * 2

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: python/symbol_variable/memory.py
        """
        return self._binary_arithmetic(other)

    def __rmul__(self, other: object) -> "Memory":
        """逐元素反向乘法。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 int * Memory。

        使用示例:
        - 2 * mem

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: python/symbol_variable/memory.py
        """
        return self._binary_arithmetic(other)

    def __truediv__(self, other: object) -> "Memory":
        """逐元素除法。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/int。

        使用示例:
        - mem / 2

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: python/symbol_variable/memory.py
        """
        return self._binary_arithmetic(other)

    def __rtruediv__(self, other: object) -> "Memory":
        """逐元素反向除法。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 int / Memory。

        使用示例:
        - 2 / mem

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: python/symbol_variable/memory.py
        """
        return self._binary_arithmetic(other)

    def __eq__(self, other: object) -> "Memory":
        """逐元素相等比较。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/int，返回 predicate dtype。

        使用示例:
        - mem == other

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: python/symbol_variable/memory.py
        """
        return self._binary_compare(other)

    def __ne__(self, other: object) -> "Memory":
        """逐元素不等比较。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/int，返回 predicate dtype。

        使用示例:
        - mem != other

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: python/symbol_variable/memory.py
        """
        return self._binary_compare(other)

    def __lt__(self, other: object) -> "Memory":
        """逐元素小于比较。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/int，返回 predicate dtype。

        使用示例:
        - mem < other

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: python/symbol_variable/memory.py
        """
        return self._binary_compare(other)

    def __le__(self, other: object) -> "Memory":
        """逐元素小于等于比较。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/int，返回 predicate dtype。

        使用示例:
        - mem <= other

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: python/symbol_variable/memory.py
        """
        return self._binary_compare(other)

    def __gt__(self, other: object) -> "Memory":
        """逐元素大于比较。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/int，返回 predicate dtype。

        使用示例:
        - mem > other

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: python/symbol_variable/memory.py
        """
        return self._binary_compare(other)

    def __ge__(self, other: object) -> "Memory":
        """逐元素大于等于比较。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/int，返回 predicate dtype。

        使用示例:
        - mem >= other

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: python/symbol_variable/memory.py
        """
        return self._binary_compare(other)
