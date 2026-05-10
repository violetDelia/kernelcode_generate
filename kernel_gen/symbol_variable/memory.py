"""Memory implementation.


功能说明:
- 定义内存空间枚举与 Memory 对象，描述 shape/dtype/stride/format/space 元信息。
- 当前文件私有 helper 仅服务 `Memory` 内部规整、复制和算术实现，不作为跨文件复用入口。

API 列表:
- `class LocalSpaceMeta(name: str, max_size: int | None, align: int)`
- `class MemorySpace(Enum)`
- `class Memory(shape: ShapeLike, dtype: NumericType | None = None, space: MemorySpace = MemorySpace.GM, stride: ShapeLike | None = None, format: Farmat = Farmat.Norm)`
- `Memory.get_shape(self) -> list[SymbolDim]`
- `Memory.get_stride(self) -> list[int | SymbolDim] | None`
- `Memory.get_type(self) -> NumericType`
- `Memory.get_space(self) -> MemorySpace`
- `Memory.get_format(self) -> Farmat`
- `Memory.clone(self, dtype: NumericType | None = None, space: MemorySpace | None = None) -> Memory`

使用示例:
- from kernel_gen.symbol_variable.memory import Memory, MemorySpace
- Memory([1, 2], NumericType.Float32, space=MemorySpace.GM)

关联文件:
- spec: spec/symbol_variable/memory.md
- test: test/symbol_variable/test_memory.py
- test: test/symbol_variable/test_memory_operation.py
- 功能实现: kernel_gen/symbol_variable/memory.py
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

import sympy as sp

from kernel_gen.core.contracts import default_stride as _common_default_stride
from .symbol_dim import SymbolDim
from .symbol_shape import SymbolShape
from .type import ARITHMETIC_DTYPE_RANK, Farmat, NumericType

ShapeLike = SymbolShape | Sequence[SymbolDim | int | str]
ScalarInput = int | bool


@dataclass(frozen=True)
class LocalSpaceMeta:
    """空间元信息描述。


    功能说明:
    - 描述空间名称、最大容量与对齐要求。

    使用示例:
    - LocalSpaceMeta(name="GM", max_size=None, align=1024)

    关联文件:
    - spec: spec/symbol_variable/memory.md
    - test: test/symbol_variable/test_memory.py
    - test: test/symbol_variable/test_memory_operation.py
    - 功能实现: kernel_gen/symbol_variable/memory.py
    """

    name: str
    max_size: int | None
    align: int


class MemorySpace(Enum):
    """内存空间枚举。


    功能说明:
    - 定义 GM/SM/LM/TSM/TLM1/TLM2/TLM3 等空间枚举项。

    使用示例:
    - MemorySpace.GM.value.align

    关联文件:
    - spec: spec/symbol_variable/memory.md
    - test: test/symbol_variable/test_memory.py
    - test: test/symbol_variable/test_memory_operation.py
    - 功能实现: kernel_gen/symbol_variable/memory.py
    """

    GM = LocalSpaceMeta(name="GM", max_size=None, align=1024)
    SM = LocalSpaceMeta(name="SM", max_size=None, align=1024)
    LM = LocalSpaceMeta(name="LM", max_size=None, align=1024)
    TSM = LocalSpaceMeta(name="TSM", max_size=None, align=1024)
    TLM1 = LocalSpaceMeta(name="TLM1", max_size=None, align=1024)
    TLM2 = LocalSpaceMeta(name="TLM2", max_size=None, align=1024)
    TLM3 = LocalSpaceMeta(name="TLM3", max_size=None, align=1024)


class Memory:
    """内存对象，独立描述形状与空间信息。


    功能说明:
    - 记录所在空间，并保存 shape/dtype/stride/format 元信息。

    使用示例:
    - Memory([1, 2], NumericType.Float32)

    关联文件:
    - spec: spec/symbol_variable/memory.md
    - test: test/symbol_variable/test_memory.py
    - test: test/symbol_variable/test_memory_operation.py
    - 功能实现: kernel_gen/symbol_variable/memory.py
    """

    def __init__(
        self: "Memory",
        shape: ShapeLike,
        dtype: NumericType | None = None,
        space: MemorySpace = MemorySpace.GM,
        stride: ShapeLike | None = None,
        format: Farmat = Farmat.Norm,
    ) -> None:
        """初始化 Memory。


        功能说明:
        - 规范化 shape/stride，并记录 space/format/dtype。
        - dtype 省略时默认使用 NumericType.Float32。

        使用示例:
        - Memory([1, 2], NumericType.Float32, space=MemorySpace.LM)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory.py
        - test: test/symbol_variable/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        self.shape = self._normalize_shape(shape)
        self.dtype = dtype or NumericType.Float32
        self.stride = self._default_stride(self.shape) if stride is None else self._normalize_stride(stride)
        self.format = format
        self.space = space

    @staticmethod
    def _normalize_shape(value: ShapeLike) -> SymbolShape:
        """规范化 shape/stride 输入为 SymbolShape。


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

    def _normalize_stride(self: "Memory", value: ShapeLike) -> SymbolShape:
        """规范化 stride 并校验 rank 一致性。


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
    def _promote_ranked_dtype(lhs: NumericType, rhs: NumericType) -> NumericType:
        """按固定优先级选择顺序更靠后的 dtype。"""
        if lhs not in ARITHMETIC_DTYPE_RANK or rhs not in ARITHMETIC_DTYPE_RANK:
            raise TypeError("Memory dtype mismatch")
        return lhs if ARITHMETIC_DTYPE_RANK[lhs] >= ARITHMETIC_DTYPE_RANK[rhs] else rhs

    @staticmethod
    def _clone_shape_like(value: SymbolShape | None) -> SymbolShape | None:
        """克隆 SymbolShape，避免元数据别名共享。


        功能说明:
        - 逐维复制 SymbolDim，保留 sympy 表达式结构。
        - 返回新的 SymbolShape 实例避免共享。

        使用示例:
        - Memory._clone_shape_like(SymbolShape([SymbolDim(\"N\") * 4, 1]))

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        if value is None:
            return None
        return SymbolShape([SymbolDim(dim.get_symbol()) for dim in value.get_shape()])

    def _tensor_repr(self: "Memory") -> str:
        """统一生成 Tensor(...) 文本片段。"""
        return (
            "Tensor("
            f"shape={self.shape}, "
            f"dtype={self.dtype}, "
            f"stride={self.stride}, "
            f"format={self.format}"
            ")"
        )

    @staticmethod
    def _default_stride(shape: SymbolShape) -> SymbolShape:
        """按连续行主序生成默认 stride。


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
        return _common_default_stride(shape)

    def get_shape(self: "Memory") -> list[SymbolDim]:
        """返回 shape 的 SymbolDim 列表。


        功能说明:
        - 返回每个维度的 `SymbolDim` 对象，支持解包与索引。
        - 调用方需要 int/str 公开文本时可对元素调用 `get_value()` 或 `str(...)`。

        使用示例:
        - m_size, n_size = Memory(["M", "N"]).get_shape()
        - first = Memory([32, 16]).get_shape()[0]

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self.shape.get_shape()

    def get_stride(self: "Memory") -> list[int | SymbolDim]:
        """返回 stride 列表，动态分量保留 SymbolDim。


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
        return [dim if dim.is_dynamic() else int(dim.get_symbol()) for dim in self.stride.get_shape()]

    def get_type(self: "Memory") -> NumericType:
        """返回 Memory 的 dtype。


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

    def get_space(self: "Memory") -> MemorySpace:
        """返回 Memory 的空间枚举。


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

    def get_format(self: "Memory") -> Farmat:
        """返回 Memory 的格式枚举。


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

    def clone(
        self: "Memory",
        dtype: NumericType | None = None,
        space: MemorySpace | None = None,
    ) -> "Memory":
        """按公开元信息克隆 `Memory`。


        功能说明:
        - 默认继承当前对象的 `shape/stride/dtype/space/format`。
        - `dtype` 或 `space` 显式传入时，只覆写对应公开元信息。
        - 返回新的 `Memory`，避免与原对象共享 `shape/stride` 容器。

        使用示例:
        - Memory(["M", "N"], NumericType.Float32).clone(dtype=NumericType.Int32)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        resolved_dtype = self.dtype if dtype is None else dtype
        if not isinstance(resolved_dtype, NumericType):
            raise TypeError("Memory.clone dtype must be NumericType or None")

        resolved_space = self.space if space is None else space
        if not isinstance(resolved_space, MemorySpace):
            raise TypeError("Memory.clone space must be MemorySpace or None")

        shape = self._clone_shape_like(self.shape)
        stride = self._clone_shape_like(self.stride)
        return Memory(shape, resolved_dtype, space=resolved_space, stride=stride, format=self.format)

    def __repr__(self: "Memory") -> str:
        """返回 Memory 的字符串表示。


        功能说明:
        - 返回 Memory(<space name>,Tensor(shape=..., dtype=..., stride=..., format=...))。

        使用示例:
        - repr(Memory([1, 2], NumericType.Float32))

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return f"Memory({self.space.name},{self._tensor_repr()})"

    def __str__(self: "Memory") -> str:
        """返回 Memory 的字符串表示。


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

    @staticmethod
    def _same_public_dim(lhs: SymbolDim, rhs: SymbolDim) -> bool:
        """判断两个维度是否语义等价。"""
        if lhs.get_value() == rhs.get_value():
            return True
        return sp.simplify(lhs.get_symbol() - rhs.get_symbol()) == 0

    @classmethod
    def _same_public_shape(cls, lhs: SymbolShape, rhs: SymbolShape) -> bool:
        """判断两个 shape 是否在公开语义上等价。"""
        if len(lhs) != len(rhs):
            return False
        return all(cls._same_public_dim(lhs_dim, rhs_dim) for lhs_dim, rhs_dim in zip(lhs, rhs, strict=True))

    def _ensure_same_shape(self: "Memory", other: "Memory") -> None:
        """校验 Memory 形状一致。


        功能说明:
        - 按静态值或符号语义比较 shape，不支持广播。

        使用示例:
        - mem._ensure_same_shape(other)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        if not self._same_public_shape(self.shape, other.shape):
            raise ValueError("Memory shape mismatch")

    def _ensure_same_dtype(self: "Memory", other: "Memory") -> None:
        """校验 Memory 数据类型兼容性。


        功能说明:
        - 比较运算要求 dtype 完全一致。

        使用示例:
        - mem._ensure_same_dtype(other)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        if self.dtype is not other.dtype:
            raise TypeError("Memory dtype mismatch")

    def _ensure_scalar_compatible(self: "Memory", value: ScalarInput) -> None:
        """校验标量输入兼容性。


        功能说明:
        - 支持 int/bool 标量，bool 视作 int，且需与 dtype 兼容。

        使用示例:
        - mem._ensure_scalar_compatible(1)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        self._normalize_scalar(value)
        if self.dtype not in ARITHMETIC_DTYPE_RANK:
            raise TypeError("Scalar incompatible with Memory dtype")

    @staticmethod
    def _normalize_scalar(value: ScalarInput) -> int:
        """统一校验并规整标量输入。


        功能说明:
        - 接受 int/bool，bool 视作 int。
        - 其他类型统一抛同一条 TypeError，避免多处重复定义标量边界。

        使用示例:
        - Memory._normalize_scalar(True)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        raise TypeError("Unsupported scalar type for Memory operation")

    @staticmethod
    def _scalar_dtype(value: ScalarInput) -> NumericType:
        """返回标量输入对应的 NumericType。


        功能说明:
        - 复用 `_normalize_scalar(...)` 的输入边界。
        - 当前所有合法标量统一映射为 `NumericType.Int32`。

        使用示例:
        - Memory._scalar_dtype(1)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        Memory._normalize_scalar(value)
        return NumericType.Int32

    def _clone_with_dtype(self: "Memory", dtype: NumericType) -> "Memory":
        """按指定 dtype 克隆 Memory。


        功能说明:
        - 继承 shape/stride/format/space，替换 dtype，并避免元数据别名复用。

        使用示例:
        - mem._clone_with_dtype(NumericType.Int32)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        return self.clone(dtype=dtype)

    def _binary_arithmetic(self: "Memory", other: MemoryBinaryOperand) -> "Memory":
        """逐元素算术运算入口。


        功能说明:
        - 支持 Memory/Memory 与 Memory/int/bool，bool 视作 int，返回 Memory。

        使用示例:
        - mem._binary_arithmetic(other)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        if isinstance(other, Memory):
            self._ensure_same_shape(other)
            result_dtype = self._promote_ranked_dtype(self.dtype, other.dtype)
            return self._clone_with_dtype(result_dtype)
        self._ensure_scalar_compatible(other)
        scalar_dtype = self._scalar_dtype(other)
        result_dtype = self._promote_ranked_dtype(self.dtype, scalar_dtype)
        return self._clone_with_dtype(result_dtype)

    def _binary_compare(self: "Memory", other: MemoryBinaryOperand) -> "Memory":
        """逐元素比较运算入口。


        功能说明:
        - 支持 Memory/Memory 与 Memory/int，返回 predicate dtype（Bool）。

        使用示例:
        - mem._binary_compare(other)

        关联文件:
        - spec: spec/symbol_variable/memory.md
        - test: test/symbol_variable/test_memory_operation.py
        - 功能实现: kernel_gen/symbol_variable/memory.py
        """
        if isinstance(other, Memory):
            self._ensure_same_shape(other)
            self._ensure_same_dtype(other)
            return self._clone_with_dtype(NumericType.Bool)
        self._ensure_scalar_compatible(other)
        return self._clone_with_dtype(NumericType.Bool)


MemoryBinaryOperand = Memory | ScalarInput


def _memory_binary_arithmetic_method(self: Memory, other: MemoryBinaryOperand) -> Memory:
    """Memory 逐元素算术 dunder 共享实现。


    功能说明:
    - 供 `__add__`、`__sub__`、`__mul__`、`__truediv__`、`__floordiv__` 及其反向方法复用。

    使用示例:
    - _memory_binary_arithmetic_method(mem, 1)

    关联文件:
    - spec: spec/symbol_variable/memory.md
    - test: test/symbol_variable/test_memory_operation.py
    - 功能实现: kernel_gen/symbol_variable/memory.py
    """

    return self._binary_arithmetic(other)


def _memory_binary_compare_method(self: Memory, other: MemoryBinaryOperand) -> Memory:
    """Memory 逐元素比较 dunder 共享实现。


    功能说明:
    - 供 `__eq__`、`__ne__`、`__lt__`、`__le__`、`__gt__`、`__ge__` 复用。

    使用示例:
    - _memory_binary_compare_method(mem, other)

    关联文件:
    - spec: spec/symbol_variable/memory.md
    - test: test/symbol_variable/test_memory_operation.py
    - 功能实现: kernel_gen/symbol_variable/memory.py
    """

    return self._binary_compare(other)


for _name in (
    "__add__",
    "__radd__",
    "__sub__",
    "__rsub__",
    "__mul__",
    "__rmul__",
    "__truediv__",
    "__rtruediv__",
    "__floordiv__",
    "__rfloordiv__",
):
    setattr(Memory, _name, _memory_binary_arithmetic_method)

for _name in ("__eq__", "__ne__", "__lt__", "__le__", "__gt__", "__ge__"):
    setattr(Memory, _name, _memory_binary_compare_method)
