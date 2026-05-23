"""tuner launch operation.

功能说明:
- 定义 tuner.launch op。

API 列表:
- `class TunerLaunchOp(callee: str | SymbolRefAttr, args: Sequence[SSAValue | Operation] = ())`

使用示例:
- `from kernel_gen.dialect.tuner.operation import ...`

关联文件:
- spec: spec/dialect/tuner.md
- test: test/dialect/tuner/
- 功能实现: kernel_gen/dialect/tuner/operation/launch.py
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

from ..common import _pattern_symbol_attr, _raise_verify_error, _verify_symbol_ref_attr

@irdl_op_definition
class TunerLaunchOp(IRDLOperation):
    """启动一个已选择的 pattern 函数。"""

    name = "tuner.launch"

    args = var_operand_def(Attribute)
    callee = attr_def(Attribute)
    _parse_diagnostic = opt_attr_def(StringAttr, attr_name="_tuner_launch_parse_diagnostic")

    def __init__(
        self: "TunerLaunchOp",
        callee: str | SymbolRefAttr,
        args: Sequence[SSAValue | Operation] = (),
    ) -> None:
        """初始化 tuner.launch。

        功能说明:
        - 记录直接 `@callee` 与透传 runtime args。
        - 不产生 result，必须在 outline 阶段改写为 `arch.launch`。

        使用示例:
        - TunerLaunchOp("matmul_entry_pattern0", (lhs, rhs, out))

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        super().__init__(
            operands=[list(args)],
            attributes={"callee": _pattern_symbol_attr(callee, self.name)},
        )

    @classmethod
    def _from_parsed(
        cls: type["TunerLaunchOp"],
        callee: Attribute,
        args: Sequence[SSAValue | Operation],
        parse_diagnostic: str | None,
    ) -> "TunerLaunchOp":
        """从文本解析结果构造 tuner.launch。

        功能说明:
        - 该内部入口只服务 parser，把非法文本输入延迟到 verifier 按公开错误语义报错。
        - 不出现在 spec/API 列表、公开 constructor 签名或测试公开调用形态中。

        使用示例:
        - op = TunerLaunchOp._from_parsed(callee, args, "tuner.launch callee must be SymbolRefAttr")

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        attrs: dict[str, Attribute] = {"callee": callee}
        if parse_diagnostic is not None:
            attrs["_tuner_launch_parse_diagnostic"] = StringAttr(parse_diagnostic)
        op = cls.__new__(cls)
        IRDLOperation.__init__(op, operands=[list(args)], attributes=attrs)
        return op

    def verify_(self: "TunerLaunchOp") -> None:
        """校验 tuner.launch callee。

        功能说明:
        - callee 必须为 flat `SymbolRefAttr`。
        - result 由 IRDL 固定为空。

        使用示例:
        - TunerLaunchOp("pattern0").verify_()

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        if self._parse_diagnostic is not None:
            _raise_verify_error(self._parse_diagnostic.data)
        _verify_symbol_ref_attr(self.callee, self.name)

    def print(self: "TunerLaunchOp", printer: Printer) -> None:
        """打印 tuner.launch 自定义文本语法。

        功能说明:
        - 输出 `tuner.launch(@callee, %arg0) : (arg_types) -> ()`。

        使用示例:
        - TunerLaunchOp("pattern0").print(printer)

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        printer.print_string("(")
        printer.print_attribute(self.callee)
        for arg in self.args:
            printer.print_string(", ")
            printer.print_ssa_value(SSAValue.get(arg))
        printer.print_string(") : (")
        for index, arg in enumerate(self.args):
            if index:
                printer.print_string(", ")
            printer.print_attribute(SSAValue.get(arg).type)
        printer.print_string(") -> ()")

    @classmethod
    def parse(cls: type["TunerLaunchOp"], parser: AttrParser) -> "TunerLaunchOp":
        """解析 tuner.launch 自定义文本语法。

        功能说明:
        - 解析 callee、runtime args、arg type list 与空 result type list。

        使用示例:
        - TunerLaunchOp.parse(parser)

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        parser.parse_punctuation("(", f"Expected '(' before callee in {cls.name}.")
        callee = parser.parse_attribute()
        args: list[SSAValue] = []
        if parser.parse_optional_punctuation(",") is not None:
            args.append(parser.parse_operand("Expected launch argument operand."))
            while parser.parse_optional_punctuation(",") is not None:
                args.append(parser.parse_operand("Expected launch argument operand."))
        parser.parse_punctuation(")", f"Expected ')' after callee/args in {cls.name}.")
        parser.parse_punctuation(":", f"Expected ':' before function type in {cls.name}.")
        arg_types = parser.parse_comma_separated_list(parser.Delimiter.PAREN, parser.parse_type)
        parser.parse_punctuation("->", f"Expected '-> ()' in {cls.name}.")
        result_types = parser.parse_comma_separated_list(parser.Delimiter.PAREN, parser.parse_type)
        parse_diagnostic: str | None = None
        if result_types:
            parse_diagnostic = "tuner.launch result types must be ()"
        if len(arg_types) != len(args):
            parse_diagnostic = parse_diagnostic or "tuner.launch arg type list must match operand count"
        if len(arg_types) == len(args):
            for operand, operand_type in zip(args, arg_types, strict=True):
                if SSAValue.get(operand).type != operand_type:
                    parse_diagnostic = parse_diagnostic or "tuner.launch arg types must match operand types"
        if not isinstance(callee, SymbolRefAttr):
            parse_diagnostic = parse_diagnostic or "tuner.launch callee must be SymbolRefAttr"
        return cls._from_parsed(callee, args, parse_diagnostic)

__all__ = [
    "TunerLaunchOp",
]
