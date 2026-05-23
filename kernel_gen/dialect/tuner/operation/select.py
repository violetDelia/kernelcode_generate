"""tuner select operation.

功能说明:
- 定义 tuner.select op。

API 列表:
- `class TunerSelectOp(patterns: Sequence[str | SymbolRefAttr], result_type: Attribute = SymbolValueType.from_expr("pattern_id"))`

使用示例:
- `from kernel_gen.dialect.tuner.operation import ...`

关联文件:
- spec: spec/dialect/tuner.md
- test: test/dialect/tuner/
- 功能实现: kernel_gen/dialect/tuner/operation/select.py
"""

from __future__ import annotations

from collections.abc import Sequence
import re

from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE
from xdsl.dialects.builtin import ArrayAttr, StringAttr, SymbolRefAttr
from xdsl.ir import Attribute, Dialect, Operation, SSAValue
from xdsl.irdl import IRDLOperation, attr_def, irdl_op_definition, opt_attr_def, result_def, var_operand_def
from xdsl.parser import AttrParser
from xdsl.printer import Printer
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.symbol import SymbolValueType

from ..common import _pattern_symbol_attr, _raise_verify_error, _verify_pattern_id_result_type

@irdl_op_definition
class TunerSelectOp(IRDLOperation):
    """选择当前 host dispatcher 使用的 pattern id。"""

    name = "tuner.select"

    patterns = attr_def(ArrayAttr[Attribute])
    _parse_diagnostic = opt_attr_def(StringAttr, attr_name="_tuner_select_parse_diagnostic")
    result = result_def(Attribute)

    def __init__(
        self: "TunerSelectOp",
        patterns: Sequence[str | SymbolRefAttr],
        result_type: Attribute = SymbolValueType.from_expr("pattern_id"),
    ) -> None:
        """初始化 tuner.select。

        功能说明:
        - 将候选 pattern 符号列表写入 `patterns` attr。
        - 结果类型固定为 `!symbol.int<#symbol.expr<pattern_id>>`。

        使用示例:
        - TunerSelectOp(["matmul_entry_pattern0", "matmul_entry_pattern1"])

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        super().__init__(
            attributes={"patterns": ArrayAttr([_pattern_symbol_attr(pattern, self.name) for pattern in patterns])},
            result_types=[result_type],
        )

    @classmethod
    def _from_parsed(
        cls: type["TunerSelectOp"],
        patterns: ArrayAttr[Attribute],
        result_type: Attribute,
        parse_diagnostic: str | None,
    ) -> "TunerSelectOp":
        """从文本解析结果构造 tuner.select。

        功能说明:
        - 该内部入口只服务 parser，把非法 attr 内容延迟到 verifier 按公开错误语义报错。
        - 不出现在 spec/API 列表、公开 constructor 签名或测试公开调用形态中。

        使用示例:
        - op = TunerSelectOp._from_parsed(patterns, result_type, "tuner.select patterns must be non-empty ArrayAttr[SymbolRefAttr]")

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        attrs: dict[str, Attribute] = {"patterns": patterns}
        if parse_diagnostic is not None:
            attrs["_tuner_select_parse_diagnostic"] = StringAttr(parse_diagnostic)
        op = cls.__new__(cls)
        IRDLOperation.__init__(op, attributes=attrs, result_types=[result_type])
        return op

    def verify_(self: "TunerSelectOp") -> None:
        """校验 tuner.select patterns 与 result type。

        功能说明:
        - `patterns` 必须是非空 `ArrayAttr[SymbolRefAttr]`。
        - result 必须固定为 `!symbol.int<#symbol.expr<pattern_id>>`。

        使用示例:
        - TunerSelectOp(["pattern0"]).verify_()

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        if self._parse_diagnostic is not None:
            _raise_verify_error(self._parse_diagnostic.data)
        if not isinstance(self.patterns, ArrayAttr) or not self.patterns.data:
            _raise_verify_error("tuner.select patterns must be non-empty ArrayAttr[SymbolRefAttr]")
        for pattern in self.patterns.data:
            if not isinstance(pattern, SymbolRefAttr):
                _raise_verify_error("tuner.select patterns must be non-empty ArrayAttr[SymbolRefAttr]")
            if not pattern.root_reference.data or len(pattern.nested_references.data) != 0:
                _raise_verify_error("tuner.select patterns must be non-empty ArrayAttr[SymbolRefAttr]")
        _verify_pattern_id_result_type(self.result.type, self.name)

    def print(self: "TunerSelectOp", printer: Printer) -> None:
        """打印 tuner.select 自定义文本语法。

        功能说明:
        - 输出 `tuner.select {patterns = [@p0, @p1]} : !symbol.int<#symbol.expr<pattern_id>>`。

        使用示例:
        - TunerSelectOp(["p0"]).print(printer)

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        printer.print_string(" ")
        printer.print_attr_dict(self.attributes)
        printer.print_string(" : ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls: type["TunerSelectOp"], parser: AttrParser) -> "TunerSelectOp":
        """解析 tuner.select 自定义文本语法。

        功能说明:
        - 解析 attr dict 与固定 result type。

        使用示例:
        - TunerSelectOp.parse(parser)

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        attrs = dict(parser.parse_optional_attr_dict() or {})
        parser.parse_characters(":", f" in {cls.name}")
        result_type = parser.parse_type()
        patterns = attrs.pop("patterns", None)
        if patterns is None:
            _raise_verify_error("tuner.select patterns must be non-empty ArrayAttr[SymbolRefAttr]")
        if attrs:
            _raise_verify_error("tuner.select only accepts patterns attr")
        if not isinstance(patterns, ArrayAttr):
            _raise_verify_error("tuner.select patterns must be non-empty ArrayAttr[SymbolRefAttr]")
        parse_diagnostic = None
        if not patterns.data or any(not isinstance(pattern, SymbolRefAttr) for pattern in patterns.data):
            parse_diagnostic = "tuner.select patterns must be non-empty ArrayAttr[SymbolRefAttr]"
        return cls._from_parsed(patterns, result_type, parse_diagnostic)

__all__ = [
    "TunerSelectOp",
]
