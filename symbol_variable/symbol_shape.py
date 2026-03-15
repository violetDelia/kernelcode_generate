"""SymbolShape implementation.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 提供符号形状列表的保存、访问与序列化能力。

使用示例:
- from symbol_variable.symbol_shape import SymbolShape
- SymbolShape(["N", 32])

关联文件:
- spec: spec/symbol_variable/symbol_shape.md
- test: test/symbol_variable/test_symbol_shape.py
- 功能实现: symbol_variable/symbol_shape.py
"""

from __future__ import annotations

from typing import Iterable, Iterator, List

from symbol_variable.symbol_dim import SymbolDim


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
    - 功能实现: symbol_variable/symbol_shape.py
    """

    def __init__(self, shapes: List[SymbolDim | int]) -> None:
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
        - 功能实现: symbol_variable/symbol_shape.py
        """
        self.shape: List[SymbolDim] = []
        for value in shapes:
            self.shape.append(self._normalize_value(value))

    @staticmethod
    def _normalize_value(value: SymbolDim | int) -> SymbolDim:
        """将输入值规范化为 SymbolDim。"""
        if isinstance(value, SymbolDim):
            return value
        return SymbolDim(value)

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
        - 功能实现: symbol_variable/symbol_shape.py
        """
        return f"List({', '.join(str(item.get_symbol()) for item in self.shape)})"

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
        - 功能实现: symbol_variable/symbol_shape.py
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
        - 功能实现: symbol_variable/symbol_shape.py
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
        - 功能实现: symbol_variable/symbol_shape.py
        """
        return reversed(self.shape)

    def __getitem__(self, key):
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
        - 功能实现: symbol_variable/symbol_shape.py
        """
        if isinstance(key, int):
            if key < -len(self.shape) or key >= len(self.shape):
                raise IndexError("下标超出范围")
            return self.shape[key]
        if isinstance(key, slice):
            return self.shape[key]
        raise TypeError("索引类型错误")

    def __setitem__(self, key, value) -> None:
        """索引赋值。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - int 索引赋值时转换为 SymbolDim。
        - int 索引越界抛 IndexError(\"下标超出范围\")。
        - 其他索引遵循 Python 列表语义。

        使用示例:
        - shape[0] = 64

        关联文件:
        - spec: spec/symbol_variable/symbol_shape.md
        - test: test/symbol_variable/test_symbol_shape.py
        - 功能实现: symbol_variable/symbol_shape.py
        """
        if isinstance(key, int):
            if key < -len(self.shape) or key >= len(self.shape):
                raise IndexError("下标超出范围")
            self.shape[key] = self._normalize_value(value)
            return
        if isinstance(key, slice):
            if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
                raise TypeError("切片赋值必须为可迭代对象")
            normalized: List[SymbolDim] = []
            for item in value:
                try:
                    normalized.append(self._normalize_value(item))
                except (TypeError, ValueError) as exc:
                    raise TypeError("切片赋值元素无法转换为 SymbolDim") from exc
            self.shape[key] = normalized
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
        - 功能实现: symbol_variable/symbol_shape.py
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
        - 功能实现: symbol_variable/symbol_shape.py
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
    - 提供列表转换与序列化能力。

    使用示例:
    - SymbolList([1, 2]).to_symbols()

    关联文件:
    - spec: spec/symbol_variable/symbol_shape.md
    - test: test/symbol_variable/test_symbol_shape.py
    - 功能实现: symbol_variable/symbol_shape.py
    """

    @staticmethod
    def convert_from_list(shapes: Iterable[SymbolDim | int] | "SymbolShape") -> "SymbolShape":
        """将列表或 SymbolShape 转换为 SymbolShape。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 输入为 SymbolShape 时直接返回。
        - 其他输入构造新的 SymbolShape。

        使用示例:
        - SymbolList.convert_from_list([1, 2])

        关联文件:
        - spec: spec/symbol_variable/symbol_shape.md
        - test: test/symbol_variable/test_symbol_shape.py
        - 功能实现: symbol_variable/symbol_shape.py
        """
        if isinstance(shapes, SymbolShape):
            return shapes
        return SymbolShape(list(shapes))

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
        - 功能实现: symbol_variable/symbol_shape.py
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
    - 功能实现: symbol_variable/symbol_shape.py
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
        - 功能实现: symbol_variable/symbol_shape.py
        """
        return f"Shape({', '.join(str(item.get_symbol()) for item in self.shape)})"
