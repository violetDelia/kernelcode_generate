"""SymbolDim implementation.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 提供符号维度表达、基础算术运算与动态性判断。

使用示例:
- from symbol_variable.symbol_dim import SymbolDim
- SymbolDim("N") + 1

关联文件:
- spec: spec/symbol_variable/symbol_dim.md
- test: test/symbol_variable/test_symbol_dim.py
- 功能实现: symbol_variable/symbol_dim.py
"""

from __future__ import annotations

import sympy as sp


class _SymbolDim:
    """符号维度基类，封装 sympy 表达式与基础运算。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一保存与暴露 sympy 表达式，并提供算术与比较能力。

    使用示例:
    - d = SymbolDim("N")
    - d.get_symbol()

    关联文件:
    - spec: spec/symbol_variable/symbol_dim.md
    - test: test/symbol_variable/test_symbol_dim.py
    - 功能实现: symbol_variable/symbol_dim.py
    """

    @staticmethod
    def _normalize_str(value: str) -> str:
        """统一规范化字符串输入并校验。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 使用 strip() 去除首尾空白。
        - 空字符串或仅空白字符串抛 ValueError。
        - 纯数字字符串抛 ValueError。

        使用示例:
        - _SymbolDim._normalize_str(" N ")

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: symbol_variable/symbol_dim.py
        """
        normalized = value.strip()
        if not normalized:
            raise ValueError("SymbolDim string must not be blank")
        if normalized.isdigit():
            raise ValueError("SymbolDim string must not be numeric")
        return normalized

    @staticmethod
    def _symbol_from_str(value: str) -> sp.Symbol:
        """基于字符串创建带假设的符号。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 统一使用 integer=True, real=True 的假设构造符号。

        使用示例:
        - _SymbolDim._symbol_from_str("N")

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: symbol_variable/symbol_dim.py
        """
        return sp.symbols(_SymbolDim._normalize_str(value), integer=True, real=True)

    @staticmethod
    def _normalize_symbol(sym: sp.Basic) -> sp.Basic:
        """规范化 sympy.Symbol 的默认假设。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 当 sym 为未显式指定 is_integer/is_real 的 Symbol 时，按名称重建为 integer=True, real=True。
        - 其他情况保持原样。

        使用示例:
        - _SymbolDim._normalize_symbol(sp.Symbol("N"))

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: symbol_variable/symbol_dim.py
        """
        if isinstance(sym, sp.Symbol) and sym.is_integer is None and sym.is_real is None:
            return _SymbolDim._symbol_from_str(sym.name)
        return sym

    def __init__(self, sym: int | str | sp.Basic) -> None:
        """初始化符号维度。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - int 转为 sympy.Integer。
        - str 必须为非纯数字且非空白字符串，转为 sympy.symbols(..., integer=True, real=True)。
        - sympy.Basic 默认直接保存；若为未设定假设的 Symbol，则统一为 integer=True, real=True。
        - 纯数字字符串或空白字符串抛 ValueError。
        - 其他类型抛 TypeError。

        使用示例:
        - SymbolDim(16)
        - SymbolDim("N")
        - SymbolDim(sp.symbols("M"))

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: symbol_variable/symbol_dim.py
        """
        if isinstance(sym, int):
            self.sym = sp.Integer(sym)
        elif isinstance(sym, str):
            self.sym = self._symbol_from_str(sym)
        elif isinstance(sym, sp.Basic):
            self.sym = self._normalize_symbol(sym)
        else:
            raise TypeError(f"Unsupported SymbolDim type: {type(sym)!r}")

    @staticmethod
    def _normalize_operand(value: int | str | "_SymbolDim") -> sp.Basic:
        """统一规范化操作数为 sympy 表达式。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 支持 int/str/_SymbolDim，其他类型抛 TypeError。
        - str 与构造路径一致，空白/纯数字字符串抛 ValueError。

        使用示例:
        - _SymbolDim._normalize_operand(4)
        - _SymbolDim._normalize_operand("M")

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: symbol_variable/symbol_dim.py
        """
        if isinstance(value, _SymbolDim):
            return value.get_symbol()
        if isinstance(value, int):
            return sp.Integer(value)
        if isinstance(value, str):
            return _SymbolDim._symbol_from_str(value)
        raise TypeError(f"Unsupported operand type: {type(value)!r}")

    def get_symbol(self) -> sp.Basic:
        """获取内部 sympy 表达式。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 返回内部保存的 sympy 表达式对象。

        使用示例:
        - SymbolDim("N").get_symbol()

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: symbol_variable/symbol_dim.py
        """
        return self.sym

    def __repr__(self) -> str:
        """返回符号维度的字符串表示。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 返回 str(get_symbol())。

        使用示例:
        - repr(SymbolDim("N"))

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: symbol_variable/symbol_dim.py
        """
        return str(self.get_symbol())

    def __add__(self, other: int | str | "_SymbolDim") -> "SymbolDim":
        """符号维度加法。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 支持 int/str/SymbolDim，加法结果返回 SymbolDim。

        使用示例:
        - SymbolDim("N") + 2

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: symbol_variable/symbol_dim.py
        """
        return SymbolDim(self.get_symbol() + self._normalize_operand(other))

    def __radd__(self, other: int | str | "_SymbolDim") -> "SymbolDim":
        """符号维度反向加法。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 支持 int/str/SymbolDim，返回 SymbolDim。

        使用示例:
        - 3 + SymbolDim("N")

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: symbol_variable/symbol_dim.py
        """
        return SymbolDim(self._normalize_operand(other) + self.get_symbol())

    def __sub__(self, other: int | str | "_SymbolDim") -> "SymbolDim":
        """符号维度减法。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 支持 int/str/SymbolDim，返回 SymbolDim。

        使用示例:
        - SymbolDim("N") - "M"

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: symbol_variable/symbol_dim.py
        """
        return SymbolDim(self.get_symbol() - self._normalize_operand(other))

    def __rsub__(self, other: int | str | "_SymbolDim") -> "SymbolDim":
        """符号维度反向减法。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 支持 int/str/SymbolDim，返回 SymbolDim。

        使用示例:
        - 10 - SymbolDim("N")

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: symbol_variable/symbol_dim.py
        """
        return SymbolDim(self._normalize_operand(other) - self.get_symbol())

    def __mul__(self, other: int | str | "_SymbolDim") -> "SymbolDim":
        """符号维度乘法。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 支持 int/str/SymbolDim，返回 SymbolDim。

        使用示例:
        - SymbolDim("N") * 2

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: symbol_variable/symbol_dim.py
        """
        return SymbolDim(self.get_symbol() * self._normalize_operand(other))

    def __rmul__(self, other: int | str | "_SymbolDim") -> "SymbolDim":
        """符号维度反向乘法。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 支持 int/str/SymbolDim，返回 SymbolDim。

        使用示例:
        - 3 * SymbolDim("N")

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: symbol_variable/symbol_dim.py
        """
        return SymbolDim(self._normalize_operand(other) * self.get_symbol())

    def __truediv__(self, other: int | str | "_SymbolDim") -> "SymbolDim":
        """符号维度除法。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 支持 int/str/SymbolDim，返回 SymbolDim。

        使用示例:
        - SymbolDim("N") / 2

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: symbol_variable/symbol_dim.py
        """
        return SymbolDim(self.get_symbol() / self._normalize_operand(other))

    def __rtruediv__(self, other: int | str | "_SymbolDim") -> "SymbolDim":
        """符号维度反向除法。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 支持 int/str/SymbolDim，返回 SymbolDim。

        使用示例:
        - "K" / SymbolDim("N")

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: symbol_variable/symbol_dim.py
        """
        return SymbolDim(self._normalize_operand(other) / self.get_symbol())

    def __eq__(self, other: object) -> bool:
        """比较符号维度表达式等价性。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 支持 int/str/SymbolDim，比较底层 sympy 表达式。
        - 其他类型抛 TypeError。

        使用示例:
        - SymbolDim("N") == "N"

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: symbol_variable/symbol_dim.py
        """
        if not isinstance(other, (_SymbolDim, int, str)):
            raise TypeError(f"Unsupported comparison type: {type(other)!r}")
        return self.get_symbol() == self._normalize_operand(other)


class SymbolDim(_SymbolDim):
    """对外公开的符号维度类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 提供动态性判断与 int 转换入口。

    使用示例:
    - SymbolDim("N").is_dynamic()

    关联文件:
    - spec: spec/symbol_variable/symbol_dim.md
    - test: test/symbol_variable/test_symbol_dim.py
    - 功能实现: symbol_variable/symbol_dim.py
    """

    def is_dynamic(self) -> bool:
        """判断符号维度是否为动态维度。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 当内部表达式包含自由符号时返回 True。

        使用示例:
        - SymbolDim(8).is_dynamic()
        - SymbolDim("N").is_dynamic()

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: symbol_variable/symbol_dim.py
        """
        return bool(self.get_symbol().free_symbols)

    @staticmethod
    def convert_from_int(value: int) -> "SymbolDim":
        """将 int 转换为 SymbolDim。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 将 int 包装为 SymbolDim 并返回。

        使用示例:
        - SymbolDim.convert_from_int(32)

        关联文件:
        - spec: spec/symbol_variable/symbol_dim.md
        - test: test/symbol_variable/test_symbol_dim.py
        - 功能实现: symbol_variable/symbol_dim.py
        """
        return SymbolDim(value)
