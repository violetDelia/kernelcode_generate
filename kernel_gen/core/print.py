"""Core IR print helpers.

功能说明:
- 提供仓库统一的 MLIR-like alias IR 打印入口。
- 仅负责把完整 xDSL operation 打印成带顶层 alias 定义的诊断文本，不修改输入 IR。
- alias 状态只在单次调用内生效，不影响 xDSL 原生 `Printer`、`str(op)` 或 raw attr/type 打印。

API 列表:
- `print_operation_with_aliases(operation: Operation | ModuleOp) -> str`

使用示例:
- from kernel_gen.core.print import print_operation_with_aliases
- text = print_operation_with_aliases(module)
- assert "builtin.module" in text

关联文件:
- spec: [spec/core/print.md](../../spec/core/print.md)
- test: [test/core/test_print.py](../../test/core/test_print.py)
- 功能实现: [kernel_gen/core/print.py](../../kernel_gen/core/print.py)
"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
import re

from xdsl.dialects.builtin import ArrayAttr, ModuleOp
from xdsl.ir import Attribute, Operation, ParametrizedAttribute
from xdsl.printer import Printer

from kernel_gen.dialect.symbol import SymbolExprAttr, SymbolIterAttr, SymbolIterType

_SYMBOL_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_INTEGER_PATTERN = re.compile(r"^-?[0-9]+$")


@dataclass(frozen=True)
class _ExprAlias:
    """单个 symbol expr alias 记录。"""

    expr_text: str
    raw_text: str
    alias: str
    group: str


@dataclass(frozen=True)
class _IterAlias:
    """单个 symbol.iter alias 记录。"""

    key: tuple[str, str, str]
    raw_text: str
    alias: str


class _AliasTable:
    """当前文件内的单次打印 alias 状态。"""

    def __init__(self: "_AliasTable") -> None:
        """初始化空 alias 表。

        功能说明:
        - 分别保存 symbol expr 与 symbol.iter 的去重映射和首次出现顺序。

        使用示例:
        - table = _AliasTable()
        """

        self._expr_by_text: dict[str, _ExprAlias] = {}
        self._expr_order: list[_ExprAlias] = []
        self._iter_by_key: dict[tuple[str, str, str], _IterAlias] = {}
        self._iter_order: list[_IterAlias] = []
        self._complex_count = 0
        self._iter_count = 0

    def add_expr(self: "_AliasTable", attr: SymbolExprAttr) -> None:
        """收集一个 symbol expr alias。

        功能说明:
        - 按表达式文本去重，保留首次出现顺序。
        - 常量、单符号、unknown 与复杂表达式分别分配稳定 alias 名。

        使用示例:
        - table.add_expr(SymbolExprAttr.from_expr("N"))
        """

        expr_text = attr.expr.data
        if expr_text in self._expr_by_text:
            return
        raw_text = _print_attribute_text(attr)
        group = _expr_alias_group(expr_text)
        alias = _expr_alias_name(expr_text, group, self._complex_count + 1)
        if group == "complex":
            self._complex_count += 1
        record = _ExprAlias(expr_text=expr_text, raw_text=raw_text, alias=alias, group=group)
        self._expr_by_text[expr_text] = record
        self._expr_order.append(record)

    def add_iter(self: "_AliasTable", attr: SymbolIterAttr) -> None:
        """收集一个 symbol.iter alias。

        功能说明:
        - 先收集 start/end/step 的 symbol expr alias，再按三元组去重 iter alias。

        使用示例:
        - table.add_iter(SymbolIterAttr.from_bounds("0", "N", "1"))
        """

        self.add_expr(attr.start)
        self.add_expr(attr.end)
        self.add_expr(attr.step)
        key = (attr.start.expr.data, attr.end.expr.data, attr.step.expr.data)
        if key in self._iter_by_key:
            return
        self._iter_count += 1
        record = _IterAlias(key=key, raw_text=_print_attribute_text(attr), alias=f"#It{self._iter_count}")
        self._iter_by_key[key] = record
        self._iter_order.append(record)

    def expr_aliases(self: "_AliasTable") -> list[_ExprAlias]:
        """按声明顺序返回 symbol expr alias。

        功能说明:
        - 声明顺序固定为常量、单符号、unknown、复杂表达式，各组内保持首次出现顺序。

        使用示例:
        - aliases = table.expr_aliases()
        """

        ordered: list[_ExprAlias] = []
        for group in ("const", "symbol", "unknown", "complex"):
            ordered.extend(record for record in self._expr_order if record.group == group)
        return ordered

    def iter_aliases(self: "_AliasTable") -> list[_IterAlias]:
        """返回 symbol.iter alias。

        功能说明:
        - iter alias 按首次出现顺序声明。

        使用示例:
        - aliases = table.iter_aliases()
        """

        return list(self._iter_order)

    def alias_for_expr_text(self: "_AliasTable", expr_text: str) -> str:
        """查询 symbol expr 文本对应 alias。

        功能说明:
        - 只查询当前表中已收集的 alias。

        使用示例:
        - table.alias_for_expr_text("N")
        """

        return self._expr_by_text[expr_text].alias


def print_operation_with_aliases(operation: Operation | ModuleOp) -> str:
    """打印带顶层 symbol alias 的 operation IR。

    功能说明:
    - 使用 xDSL 公开 `Printer` 生成 operation 文本，再用本文件内收集到的 symbol alias 替换正文引用。
    - 顶层声明 `#C*`、`#S_*`、`#S1` 与 `#It1` 等 alias，输出可由默认上下文重新解析。

    使用示例:
    - text = print_operation_with_aliases(module)
    - assert text.startswith("#") or text.startswith("builtin.module")
    """

    if not isinstance(operation, Operation):
        raise TypeError("operation must be xdsl Operation")
    aliases = _AliasTable()
    _collect_operation_aliases(operation, aliases)
    body_text = _replace_body_aliases(_print_operation_text(operation), aliases)
    alias_text = _format_alias_definitions(aliases)
    if alias_text:
        return _ensure_trailing_newline(f"{alias_text}\n\n{body_text}")
    return _ensure_trailing_newline(body_text)


def _collect_operation_aliases(operation: Operation, aliases: _AliasTable) -> None:
    """从 operation 树收集 symbol alias。

    功能说明:
    - 遍历 operation 属性、properties、结果类型和 block argument 类型。

    使用示例:
    - _collect_operation_aliases(module, aliases)
    """

    for op in operation.walk():
        for attr in op.properties.values():
            _collect_attribute_aliases(attr, aliases)
        for attr in op.attributes.values():
            _collect_attribute_aliases(attr, aliases)
        for result in op.results:
            _collect_attribute_aliases(result.type, aliases)
        for region in op.regions:
            for block in region.blocks:
                for arg in block.args:
                    _collect_attribute_aliases(arg.type, aliases)


def _collect_attribute_aliases(attr: Attribute, aliases: _AliasTable) -> None:
    """从 attribute/type 中递归收集 symbol alias。

    功能说明:
    - 识别 `SymbolExprAttr`、`SymbolIterAttr` 与 `SymbolIterType`。
    - 对其它 xDSL attribute 只递归公开参数或 array 元素，不做语义猜测。

    使用示例:
    - _collect_attribute_aliases(SymbolExprAttr.from_expr("N"), aliases)
    """

    if isinstance(attr, SymbolIterAttr):
        aliases.add_iter(attr)
        return
    if isinstance(attr, SymbolIterType):
        aliases.add_expr(attr.start)
        aliases.add_expr(attr.end)
        aliases.add_expr(attr.step)
        return
    if isinstance(attr, SymbolExprAttr):
        aliases.add_expr(attr)
        return
    if isinstance(attr, ArrayAttr):
        for item in attr.data:
            _collect_attribute_aliases(item, aliases)
        return
    if isinstance(attr, ParametrizedAttribute):
        for param in attr.parameters:
            if isinstance(param, Attribute):
                _collect_attribute_aliases(param, aliases)


def _expr_alias_group(expr_text: str) -> str:
    """计算 symbol expr alias 分组。

    功能说明:
    - 分组决定 alias 命名和声明顺序。

    使用示例:
    - _expr_alias_group("N") == "symbol"
    """

    if _INTEGER_PATTERN.fullmatch(expr_text):
        return "const"
    if expr_text == "?":
        return "unknown"
    if _SYMBOL_NAME_PATTERN.fullmatch(expr_text):
        return "symbol"
    return "complex"


def _expr_alias_name(expr_text: str, group: str, complex_index: int) -> str:
    """生成 symbol expr alias 名。

    功能说明:
    - 常量使用 `#C*`，单符号使用 `#S_*`，unknown 使用 `#S_Q`，复杂表达式使用 `#S<index>`。

    使用示例:
    - _expr_alias_name("-3", "const", 1) == "#C_NEG3"
    """

    if group == "const":
        value = int(expr_text)
        if value < 0:
            return f"#C_NEG{abs(value)}"
        return f"#C{value}"
    if group == "symbol":
        return f"#S_{expr_text}"
    if group == "unknown":
        return "#S_Q"
    return f"#S{complex_index}"


def _format_alias_definitions(aliases: _AliasTable) -> str:
    """格式化顶层 alias 定义。

    功能说明:
    - 先输出 expr alias，再输出 iter alias。
    - iter 定义内的 start/end/step 会引用已声明 expr alias。

    使用示例:
    - text = _format_alias_definitions(aliases)
    """

    lines: list[str] = []
    for record in aliases.expr_aliases():
        lines.append(f"{record.alias} = {record.raw_text}")
    for record in aliases.iter_aliases():
        lines.append(f"{record.alias} = {_replace_expr_aliases(record.raw_text, aliases)}")
    return "\n".join(lines)


def _replace_body_aliases(body_text: str, aliases: _AliasTable) -> str:
    """替换 operation 正文中的 alias 引用。

    功能说明:
    - 先替换完整 iter attr，再替换 expr attr，避免 iter 内部 expr 替换后失去完整 iter 匹配。

    使用示例:
    - text = _replace_body_aliases(raw_ir, aliases)
    """

    text = body_text
    for record in aliases.iter_aliases():
        text = text.replace(record.raw_text, record.alias)
    return _replace_expr_aliases(text, aliases)


def _replace_expr_aliases(text: str, aliases: _AliasTable) -> str:
    """替换文本中的 symbol expr attr 为 alias。

    功能说明:
    - 使用已收集的精确 raw attr 文本替换，不按未解析正则猜测 IR 结构。

    使用示例:
    - text = _replace_expr_aliases("!symbol.int<#symbol.expr<N>>", aliases)
    """

    result = text
    records = sorted(aliases.expr_aliases(), key=lambda record: len(record.raw_text), reverse=True)
    for record in records:
        result = result.replace(record.raw_text, record.alias)
    return result


def _print_operation_text(operation: Operation) -> str:
    """使用 xDSL 公开 Printer 打印 operation。

    功能说明:
    - 不修改 xDSL printer 全局行为，只读取本次 operation 文本。

    使用示例:
    - text = _print_operation_text(module)
    """

    stream = StringIO()
    Printer(stream=stream).print_op(operation)
    return stream.getvalue().rstrip()


def _print_attribute_text(attr: Attribute) -> str:
    """使用 xDSL 公开 Printer 打印 attribute/type。

    功能说明:
    - 用于获得 alias 定义和正文替换的精确 raw attr 文本。

    使用示例:
    - text = _print_attribute_text(SymbolExprAttr.from_expr("N"))
    """

    stream = StringIO()
    Printer(stream=stream).print_attribute(attr)
    return stream.getvalue()


def _ensure_trailing_newline(text: str) -> str:
    """保证输出文本以换行结尾。

    功能说明:
    - 统一 dump 文件和 expectation 文本比较的末尾换行口径。

    使用示例:
    - _ensure_trailing_newline("builtin.module {}")
    """

    if text.endswith("\n"):
        return text
    return f"{text}\n"


__all__ = ["print_operation_with_aliases"]
