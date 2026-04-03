"""SymbolShape implementation.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 提供符号形状列表的保存、访问与序列化能力。

使用示例:
- from kernel_gen.symbol_variable.symbol_shape import SymbolShape
- SymbolShape(["N", 32])

关联文件:
- spec: spec/symbol_variable/symbol_shape.md
- test: test/symbol_variable/test_symbol_shape.py
- 功能实现: kernel_gen/symbol_variable/symbol_shape.py
"""

from __future__ import annotations

from typing import Iterable, Iterator, List

from .symbol_dim import SymbolDim


class _SymbolList:
    """符号形状列表基类。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 负责保存 SymbolDim 列表，并提供序列化与索引行为。

    使用示例:
    - SymbolShape(["N", 32])

    关联文件:
    - spec: spec/symbol_variable/symbol_shape.md
    - test: test/symbol_variable/test_symbol_shape.py
    - 功能实现: kernel_gen/symbol_variable/symbol_shape.py
    """

    def __init__(self, shapes: Iterable[object]) -> None:
        """初始化符号形状列表。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 遍历输入并将非 SymbolDim 元素转换为 SymbolDim。

        使用示例:
        - SymbolShape([SymbolDim("N"), 32])

        关联文件:
        - spec: spec/symbol_variable/symbol_shape.md
        - test: test/symbol_variable/test_symbol_shape.py
        - 功能实现: kernel_gen/symbol_variable/symbol_shape.py
        """
        self.shape: List[SymbolDim] = []
        for value in shapes:
            self.shape.append(self._normalize_value(value))

    @staticmethod
    def _normalize_value(value: object) -> SymbolDim:
        """将输入值规范化为 SymbolDim。"""
        if isinstance(value, SymbolDim):
            return value
        if isinstance(value, str):
            normalized = value.strip()
            if normalized.isdigit():
                return SymbolDim(int(normalized))
        return SymbolDim(value)

    @staticmethod
    def _render_items(items: Iterable[SymbolDim]) -> str:
        """统一渲染 SymbolDim 序列。"""
        return ", ".join(str(item.get_symbol()) for item in items)

    def _normalize_slice_values(self, value: object) -> List[SymbolDim]:
        """规范化切片赋值输入。

        创建者: 大闸蟹
        最后一次更改: 大闸蟹

        功能说明:
        - 校验切片赋值必须为可迭代对象。
        - 逐项规整为 SymbolDim。
        - `TypeError/ValueError` 统一收敛为切片赋值错误；`NotImplementedError` 继续透传。

        使用示例:
        - shape._normalize_slice_values([1, "N"])

        关联文件:
        - spec: spec/symbol_variable/symbol_shape.md
        - test: test/symbol_variable/test_symbol_shape.py
        - 功能实现: kernel_gen/symbol_variable/symbol_shape.py
        """
        if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
            raise TypeError("切片赋值必须为可迭代对象")
        normalized: List[SymbolDim] = []
        for item in value:
            try:
                normalized.append(self._normalize_value(item))
            except (TypeError, ValueError) as exc:
                raise TypeError("切片赋值元素无法转换为 SymbolDim") from exc
        return normalized

    def _validate_int_index(self, key: int) -> None:
        """统一校验 int 索引范围。"""
        if key < -len(self.shape) or key >= len(self.shape):
            raise IndexError("下标超出范围")

    def __repr__(self) -> str:
        """返回列表字符串表示。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 以 List(d0, d1, ...) 格式返回。

        使用示例:
        - repr(SymbolShape([1, 2]))

        关联文件:
        - spec: spec/symbol_variable/symbol_shape.md
        - test: test/symbol_variable/test_symbol_shape.py
        - 功能实现: kernel_gen/symbol_variable/symbol_shape.py
        """
        return f"List({self._render_items(self.shape)})"

    def __len__(self) -> int:
        """返回维度数量。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 返回维度列表长度。

        使用示例:
        - len(SymbolShape([1, 2]))

        关联文件:
        - spec: spec/symbol_variable/symbol_shape.md
        - test: test/symbol_variable/test_symbol_shape.py
        - 功能实现: kernel_gen/symbol_variable/symbol_shape.py
        """
        return len(self.shape)

    def __iter__(self) -> Iterator[SymbolDim]:
        """迭代维度元素。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 返回内部 shape 的迭代器。

        使用示例:
        - [dim for dim in SymbolShape([1, 2])]

        关联文件:
        - spec: spec/symbol_variable/symbol_shape.md
        - test: test/symbol_variable/test_symbol_shape.py
        - 功能实现: kernel_gen/symbol_variable/symbol_shape.py
        """
        return iter(self.shape)

    def __reversed__(self) -> Iterator[SymbolDim]:
        """反向迭代维度元素。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 返回反向迭代器。

        使用示例:
        - list(reversed(SymbolShape([1, 2])))

        关联文件:
        - spec: spec/symbol_variable/symbol_shape.md
        - test: test/symbol_variable/test_symbol_shape.py
        - 功能实现: kernel_gen/symbol_variable/symbol_shape.py
        """
        return reversed(self.shape)

    def __getitem__(self, key: int | slice) -> SymbolDim | List[SymbolDim]:
        """索引访问维度元素。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - int 索引越界抛 IndexError(\"下标超出范围\")。
        - slice 返回 List[SymbolDim]。

        使用示例:
        - SymbolShape([1, 2])[0]
        - SymbolShape([1, 2])[0:1]

        关联文件:
        - spec: spec/symbol_variable/symbol_shape.md
        - test: test/symbol_variable/test_symbol_shape.py
        - 功能实现: kernel_gen/symbol_variable/symbol_shape.py
        """
        if isinstance(key, int):
            self._validate_int_index(key)
            return self.shape[key]
        if isinstance(key, slice):
            return self.shape[key]
        raise TypeError("索引类型错误")

    def __setitem__(self, key: int | slice, value: object) -> None:
        """索引赋值。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - int 索引赋值时转换为 SymbolDim。
        - int 索引越界抛 IndexError(\"下标超出范围\")。
        - slice 赋值需传入可迭代对象，并逐项转换为 SymbolDim。
        - 非 int/slice 索引抛 TypeError。

        使用示例:
        - shape[0] = 64

        关联文件:
        - spec: spec/symbol_variable/symbol_shape.md
        - test: test/symbol_variable/test_symbol_shape.py
        - 功能实现: kernel_gen/symbol_variable/symbol_shape.py
        """
        if isinstance(key, int):
            self._validate_int_index(key)
            self.shape[key] = self._normalize_value(value)
            return
        if isinstance(key, slice):
            self.shape[key] = self._normalize_slice_values(value)
            return
        raise TypeError("索引类型错误")

    def get_shape(self) -> List[SymbolDim]:
        """返回内部形状列表。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 返回内部保存的 SymbolDim 列表。

        使用示例:
        - SymbolShape([1, 2]).get_shape()

        关联文件:
        - spec: spec/symbol_variable/symbol_shape.md
        - test: test/symbol_variable/test_symbol_shape.py
        - 功能实现: kernel_gen/symbol_variable/symbol_shape.py
        """
        return list(self.shape)

    def get_values(self) -> List[int | str]:
        """序列化为 int/str 列表。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 动态维度输出字符串，静态维度输出整数。

        使用示例:
        - SymbolShape([\"N\", 32]).get_values()

        关联文件:
        - spec: spec/symbol_variable/symbol_shape.md
        - test: test/symbol_variable/test_symbol_shape.py
        - 功能实现: kernel_gen/symbol_variable/symbol_shape.py
        """
        values: List[int | str] = []
        for dim in self.shape:
            if dim.is_dynamic():
                values.append(str(dim.get_symbol()))
            else:
                values.append(int(dim.get_symbol()))
        return values


class SymbolList(_SymbolList):
    """对外公开的形状列表类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 提供序列化能力。

    使用示例:
    - SymbolList([1, 2]).to_symbols()

    关联文件:
    - spec: spec/symbol_variable/symbol_shape.md
    - test: test/symbol_variable/test_symbol_shape.py
    - 功能实现: kernel_gen/symbol_variable/symbol_shape.py
    """

    def to_symbols(self) -> List[int | str]:
        """序列化为 int/str 列表。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 与 get_values() 相同的序列化规则。

        使用示例:
        - SymbolList([1, 2]).to_symbols()

        关联文件:
        - spec: spec/symbol_variable/symbol_shape.md
        - test: test/symbol_variable/test_symbol_shape.py
        - 功能实现: kernel_gen/symbol_variable/symbol_shape.py
        """
        return self.get_values()


class SymbolShape(SymbolList):
    """具体形状类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 作为具体形状容器对外使用。

    使用示例:
    - SymbolShape([1, 2])

    关联文件:
    - spec: spec/symbol_variable/symbol_shape.md
    - test: test/symbol_variable/test_symbol_shape.py
    - 功能实现: kernel_gen/symbol_variable/symbol_shape.py
    """

    def __repr__(self) -> str:
        """返回 Shape(d0, d1, ...) 格式字符串。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 以 Shape(d0, d1, ...) 格式输出。

        使用示例:
        - repr(SymbolShape([1, 2]))

        关联文件:
        - spec: spec/symbol_variable/symbol_shape.md
        - test: test/symbol_variable/test_symbol_shape.py
        - 功能实现: kernel_gen/symbol_variable/symbol_shape.py
        """
        return f"Shape({self._render_items(self.shape)})"
