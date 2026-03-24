"""Memory implementation.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 定义内存空间枚举与 Memory 对象，描述 shape/dtype/stride/format/space 元信息。

使用示例:
- from kernel_gen.symbol_variable.memory import Memory, MemorySpace
- Memory([1, 2], NumericType.Float32, space=MemorySpace.GM)

关联文件:
- spec: spec/symbol_variable/memory.md
- test: test/symbol_variable/test_memory.py
- test: test/operation/test_memory_operation.py
- 功能实现: kernel_gen/symbol_variable/memory.py
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .symbol_dim import SymbolDim
from .symbol_shape import SymbolShape
from .type import Farmat, NumericType

_NUMERIC_TYPE_ORDER = [
    NumericType.Bool,
    NumericType.Int8,
    NumericType.Uint8,
    NumericType.Int16,
    NumericType.Uint16,
    NumericType.Int32,
    NumericType.Uint32,
    NumericType.Int64,
    NumericType.Uint64,
    NumericType.Float16,
    NumericType.BFloat16,
    NumericType.Float32,
    NumericType.Float64,
]
_NUMERIC_TYPE_RANK = {dtype: index for index, dtype in enumerate(_NUMERIC_TYPE_ORDER)}


def _promote_dtype(lhs: NumericType, rhs: NumericType) -> NumericType:
    """选择更高精度的 NumericType。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 按公开顺序返回精度更高的 NumericType。

    使用示例:
    - _promote_dtype(NumericType.Int16, NumericType.Float32)

    关联文件:
    - spec: spec/symbol_variable/memory.md
    - test: test/symbol_variable/test_memory.py
    - test: test/operation/test_memory_operation.py
    - 功能实现: kernel_gen/symbol_variable/memory.py
    """
    if lhs not in _NUMERIC_TYPE_RANK or rhs not in _NUMERIC_TYPE_RANK:
        raise TypeError("Unsupported NumericType for Memory operation")
    return lhs if _NUMERIC_TYPE_RANK[lhs] >= _NUMERIC_TYPE_RANK[rhs] else rhs


def _scalar_to_dtype(value: object) -> NumericType:
    """将 Python 标量映射到公开 NumericType。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - bool -> NumericType.Bool
    - int -> NumericType.Int32
    - float -> NumericType.Float32

    使用示例:
    - _scalar_to_dtype(1.5)

    关联文件:
    - spec: spec/symbol_variable/memory.md
    - test: test/symbol_variable/test_memory.py
    - test: test/operation/test_memory_operation.py
    - 功能实现: kernel_gen/symbol_variable/memory.py
    """
    if isinstance(value, bool):
        return NumericType.Bool
    if isinstance(value, int):
        return NumericType.Int32
    if isinstance(value, float):
        return NumericType.Float32
    raise TypeError("Unsupported scalar type for Memory operation")


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
    - test: test/operation/test_memory_operation.py
    - 功能实现: kernel_gen/symbol_variable/memory.py
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
    - test: test/operation/test_memory_operation.py
    - 功能实现: kernel_gen/symbol_variable/memory.py
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
    - 记录所在空间，并保存 shape/dtype/stride/format 元信息。

    使用示例:
    - Memory([1, 2], NumericType.Float32)

    关联文件:
    - spec: spec/symbol_variable/memory.md
    - test: test/symbol_variable/test_memory.py
    - test: test/operation/test_memory_operation.py
    - 功能实现: kernel_gen/symbol_variable/memory.py
    """

    def __init__(
        self,
        shape,
        dtype: NumericType | None = None,
        space: MemorySpace = MemorySpace.GM,
        stride=None,
        format: Farmat = Farmat.Norm,
    ) -> None:
        """初始化 Memory。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 规范化 shape/stride，并记录 space/format/dtype。
        - dtype 省略时默认使用 NumericType.Float32。

        使用示例:
        - Memory([1, 2], NumericType.Float32, space=MemorySpace.LM)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory.py
        - test: test/operation/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        self.shape = self._normalize_shape(shape)
        self.dtype = dtype or NumericType.Float32
        self.stride = self._default_stride(self.shape) if stride is None else self._normalize_stride(stride)
        self.format = format
        self.space = space

    @staticmethod
    def _normalize_shape(value):
        """规范化 shape/stride 输入为 SymbolShape。

        创建者: 金铲铲大作战
        最后一次更改: 小李飞刀

        功能说明:
        - 若已为 SymbolShape，直接返回。
        - 否则通过 SymbolShape 构造规整输入。

        使用示例:
        - Memory._normalize_shape([1, 2])

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        if isinstance(value, SymbolShape):
            return value
        return SymbolShape(value)

    def _normalize_stride(self, value) -> SymbolShape:
        """规范化 stride 并校验 rank 一致性。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 将 stride 规整为 SymbolShape。
        - 校验 stride 与 shape 的 rank 一致。

        使用示例:
        - Memory([1, 2], NumericType.Float32, stride=[2, 1])

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        normalized = self._normalize_shape(value)
        if len(normalized) != len(self.shape):
            raise ValueError("Stride rank mismatch with shape")
        return normalized

    @staticmethod
    def _default_stride(shape: SymbolShape) -> SymbolShape:
        """按连续行主序生成默认 stride。

        创建者: OpenAI
        最后一次更改: OpenAI

        功能说明:
        - 最后一维默认 stride 为 1。
        - 其余维度为后续维度长度的乘积。
        - 动态维度使用无空格 `*` 的 SymbolDim 乘法表达式。

        使用示例:
        - Memory._default_stride(SymbolShape(["M", "K", "N"]))

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        stride_values: list[SymbolDim] = []
        running = SymbolDim(1)
        for dim in reversed(shape.get_shape()):
            stride_values.append(running)
            running = dim * running
        stride_values.reverse()
        return SymbolShape(stride_values)

    def get_shape(self) -> list[int | str]:
        """返回序列化后的 shape 列表。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 动态维度以字符串返回，静态维度以整数返回。

        使用示例:
        - Memory(["N", 32]).get_shape()

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self.shape.get_values()

    def get_stride(self) -> list[int | SymbolDim]:
        """返回 stride 列表，动态分量保留 SymbolDim。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 静态分量返回整数。
        - 动态分量返回 SymbolDim 表达式。

        使用示例:
        - Memory(["M", "N"], NumericType.Float32).get_stride()

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        values: list[int | SymbolDim] = []
        for dim in self.stride.get_shape():
            values.append(dim if dim.is_dynamic() else int(dim.get_symbol()))
        return values

    def get_type(self) -> NumericType:
        """返回 Memory 的 dtype。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 对外暴露 dtype 元信息。

        使用示例:
        - Memory([1], NumericType.Float32).get_type()

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self.dtype

    def get_space(self) -> MemorySpace:
        """返回 Memory 的空间枚举。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 对外暴露 space 元信息。

        使用示例:
        - Memory([1], NumericType.Float32).get_space()

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self.space

    def get_format(self) -> Farmat:
        """返回 Memory 的格式枚举。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 对外暴露 format 元信息。

        使用示例:
        - Memory([1], NumericType.Float32).get_format()

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self.format

    def __repr__(self) -> str:
        """返回 Memory 的字符串表示。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 返回 Memory(<space name>,Tensor(shape=..., dtype=..., stride=..., format=...))。

        使用示例:
        - repr(Memory([1, 2], NumericType.Float32))

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
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

    def __str__(self) -> str:
        """返回 Memory 的字符串表示。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 直接复用 __repr__ 的输出格式。

        使用示例:
        - str(Memory([1, 2], NumericType.Float32))

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self.__repr__()
 
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
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        if self.shape.get_values() != other.shape.get_values():
            raise ValueError("Memory shape mismatch")

    def _clone_symbol_list(self, value) -> "SymbolShape | None":
        """克隆符号列表对象。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 复制 SymbolShape 容器，避免别名共享。

        使用示例:
        - mem._clone_symbol_list(mem.shape)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
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
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        shape = self._clone_symbol_list(self.shape)
        stride = self._clone_symbol_list(self.stride)
        return Memory(shape, dtype, space=self.space, stride=stride, format=self.format)

    def _binary_arithmetic(self, other: object) -> "Memory":
        """逐元素算术运算入口。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/bool|int|float，返回 Memory。
        - Memory/Memory 与 Memory/标量都按公开 NumericType 顺序提升结果 dtype。

        使用示例:
        - mem._binary_arithmetic(other)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        if isinstance(other, Memory):
            self._ensure_same_shape(other)
            promoted = _promote_dtype(self.dtype, other.dtype)
            return self._clone_with_dtype(promoted)
        scalar_dtype = _scalar_to_dtype(other)
        promoted = _promote_dtype(self.dtype, scalar_dtype)
        return self._clone_with_dtype(promoted)

    def _binary_compare(self, other: object) -> "Memory":
        """逐元素比较运算入口。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/bool|int|float，返回 predicate dtype。
        - Memory/Memory 需保持 shape 一致；标量输入需能映射到公开 NumericType。

        使用示例:
        - mem._binary_compare(other)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        if isinstance(other, Memory):
            self._ensure_same_shape(other)
            return self._clone_with_dtype(NumericType.Int32)
        _scalar_to_dtype(other)
        return self._clone_with_dtype(NumericType.Int32)

    def __add__(self, other: object) -> "Memory":
        """逐元素加法。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/bool|int|float。
        - 标量输入先映射到公开 NumericType，再按同一提升规则参与运算。

        使用示例:
        - mem + 1

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self._binary_arithmetic(other)

    def __radd__(self, other: object) -> "Memory":
        """逐元素反向加法。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 bool|int|float + Memory。
        - reflected 路径与正向加法使用相同的 dtype 提升规则。

        使用示例:
        - 1 + mem

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self._binary_arithmetic(other)

    def __sub__(self, other: object) -> "Memory":
        """逐元素减法。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/bool|int|float。
        - 标量输入先映射到公开 NumericType，再按同一提升规则参与运算。

        使用示例:
        - mem - 1

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self._binary_arithmetic(other)

    def __rsub__(self, other: object) -> "Memory":
        """逐元素反向减法。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 bool|int|float - Memory。
        - reflected 路径与正向减法使用相同的 dtype 提升规则。

        使用示例:
        - 1 - mem

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self._binary_arithmetic(other)

    def __mul__(self, other: object) -> "Memory":
        """逐元素乘法。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/bool|int|float。
        - 标量输入先映射到公开 NumericType，再按同一提升规则参与运算。

        使用示例:
        - mem * 2

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self._binary_arithmetic(other)

    def __rmul__(self, other: object) -> "Memory":
        """逐元素反向乘法。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 bool|int|float * Memory。
        - reflected 路径与正向乘法使用相同的 dtype 提升规则。

        使用示例:
        - 2 * mem

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self._binary_arithmetic(other)

    def __truediv__(self, other: object) -> "Memory":
        """逐元素除法。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/bool|int|float。
        - 标量输入先映射到公开 NumericType，再按同一提升规则参与运算。

        使用示例:
        - mem / 2

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self._binary_arithmetic(other)

    def __rtruediv__(self, other: object) -> "Memory":
        """逐元素反向除法。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 bool|int|float / Memory。
        - reflected 路径与正向除法使用相同的 dtype 提升规则。

        使用示例:
        - 2 / mem

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self._binary_arithmetic(other)

    def __floordiv__(self, other: object) -> "Memory":
        """逐元素整除。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/bool|int|float。
        - 标量输入先映射到公开 NumericType，再按同一提升规则参与运算。

        使用示例:
        - mem // 2

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self._binary_arithmetic(other)

    def __rfloordiv__(self, other: object) -> "Memory":
        """逐元素反向整除。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 bool|int|float // Memory。
        - reflected 路径与正向整除使用相同的 dtype 提升规则。

        使用示例:
        - 2 // mem

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self._binary_arithmetic(other)

    def __eq__(self, other: object) -> "Memory":
        """逐元素相等比较。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/bool|int|float，返回 predicate dtype。
        - 标量输入需能映射到公开 NumericType；结果 dtype 固定为 NumericType.Int32。

        使用示例:
        - mem == other

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self._binary_compare(other)

    def __ne__(self, other: object) -> "Memory":
        """逐元素不等比较。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/bool|int|float，返回 predicate dtype。
        - 标量输入需能映射到公开 NumericType；结果 dtype 固定为 NumericType.Int32。

        使用示例:
        - mem != other

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self._binary_compare(other)

    def __lt__(self, other: object) -> "Memory":
        """逐元素小于比较。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/bool|int|float，返回 predicate dtype。
        - 标量输入需能映射到公开 NumericType；结果 dtype 固定为 NumericType.Int32。

        使用示例:
        - mem < other

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self._binary_compare(other)

    def __le__(self, other: object) -> "Memory":
        """逐元素小于等于比较。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/bool|int|float，返回 predicate dtype。
        - 标量输入需能映射到公开 NumericType；结果 dtype 固定为 NumericType.Int32。

        使用示例:
        - mem <= other

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self._binary_compare(other)

    def __gt__(self, other: object) -> "Memory":
        """逐元素大于比较。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/bool|int|float，返回 predicate dtype。
        - 标量输入需能映射到公开 NumericType；结果 dtype 固定为 NumericType.Int32。

        使用示例:
        - mem > other

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self._binary_compare(other)

    def __ge__(self, other: object) -> "Memory":
        """逐元素大于等于比较。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 Memory/Memory 与 Memory/bool|int|float，返回 predicate dtype。
        - 标量输入需能映射到公开 NumericType；结果 dtype 固定为 NumericType.Int32。

        使用示例:
        - mem >= other

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/operation/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self._binary_compare(other)
