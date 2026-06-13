"""tuner select operation.

功能说明:
- 定义 tuner.select op。

API 列表:
- `class TunerSelectOp(patterns: Sequence[str | SymbolRefAttr], result_type: Attribute = SymbolValueType.from_expr("pattern_id"), *, args: Sequence[SSAValue | Operation] = (), tuner_args: Sequence[SSAValue | Operation] = ())`

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
from kernel_gen.core.contracts import raise_verify_error
from xdsl.dialects.builtin import ArrayAttr, StringAttr, SymbolRefAttr
from xdsl.ir import Attribute, Dialect, Operation, SSAValue
from xdsl.irdl import AttrSizedOperandSegments, IRDLOperation, attr_def, irdl_op_definition, opt_attr_def, result_def, var_operand_def
from xdsl.parser import AttrParser
from xdsl.printer import Printer

from kernel_gen.dialect.symbol import SymbolValueType

# Localized helpers from retired package-internal modules.

_ERROR_SCENE = "dialect.tuner verifier"

def _verify_pattern_id_result_type(result_type: Attribute, op_name: str) -> SymbolValueType:
    """校验 pattern 选择结果类型。

    功能说明:
    - 只接受 `!symbol.int<#symbol.expr<pattern_id>>`，避免 dispatcher 选择值被其它 symbol 语义替代。

    使用示例:
    - _verify_pattern_id_result_type(SymbolValueType.from_expr("pattern_id"), "tuner.select")

    关联文件:
    - spec: spec/dialect/tuner.md
    - test: test/dialect/tuner/test_tuner.py
    - 功能实现: kernel_gen/dialect/tuner/
    """

    if not isinstance(result_type, SymbolValueType):
        raise_verify_error(_ERROR_SCENE, f"{op_name} result type must be !symbol.int<#symbol.expr<pattern_id>>")
    result_type.verify()
    if result_type.get_value() != "pattern_id":
        raise_verify_error(_ERROR_SCENE, f"{op_name} result type must be !symbol.int<#symbol.expr<pattern_id>>")
    return result_type

def _pattern_symbol_attr(value: str | SymbolRefAttr, op_name: str) -> SymbolRefAttr:
    """把 pattern 名称规整为 SymbolRefAttr。

    功能说明:
    - 构造器接受字符串或已构造的 `SymbolRefAttr`，统一写入 `patterns` attr。
    - 非公开输入类型立即按对应 op 的公开 verifier 文本失败，不扩大 constructor 合同。

    使用示例:
    - attr = _pattern_symbol_attr("matmul_entry_pattern0", "tuner.select")

    关联文件:
    - spec: spec/dialect/tuner.md
    - test: test/dialect/tuner/test_tuner.py
    - 功能实现: kernel_gen/dialect/tuner/
    """

    if isinstance(value, str):
        return SymbolRefAttr(value)
    if isinstance(value, SymbolRefAttr):
        return value
    if op_name == "tuner.select":
        raise_verify_error(_ERROR_SCENE, "tuner.select patterns must be non-empty ArrayAttr[SymbolRefAttr]")
    raise_verify_error(_ERROR_SCENE, f"{op_name} callee must be SymbolRefAttr")



@irdl_op_definition
class TunerSelectOp(IRDLOperation):
    """选择当前 host dispatcher 使用的 pattern id。"""

    name = "tuner.select"

    args = var_operand_def(Attribute)
    tuner_args = var_operand_def(Attribute)
    patterns = attr_def(ArrayAttr[Attribute])
    _parse_diagnostic = opt_attr_def(StringAttr, attr_name="_tuner_select_parse_diagnostic")
    result = result_def(Attribute)

    irdl_options = (AttrSizedOperandSegments(as_property=True),)

    def __init__(
        self: "TunerSelectOp",
        patterns: Sequence[str | SymbolRefAttr],
        result_type: Attribute = SymbolValueType.from_expr("pattern_id"),
        *,
        args: Sequence[SSAValue | Operation] = (),
        tuner_args: Sequence[SSAValue | Operation] = (),
    ) -> None:
        """初始化 tuner.select。

        功能说明:
        - 将候选 pattern 符号列表写入 `patterns` attr。
        - `args` 透传给真实 pattern launch，`tuner_args` 标记 selector function 使用的 runtime state。
        - 结果类型固定为 `!symbol.int<#symbol.expr<pattern_id>>`。

        使用示例:
        - TunerSelectOp(["matmul_entry_pattern0", "matmul_entry_pattern1"])
        - TunerSelectOp(["p0"], args=(out,), tuner_args=())

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        super().__init__(
            operands=[list(args), list(tuner_args)],
            attributes={"patterns": ArrayAttr([_pattern_symbol_attr(pattern, self.name) for pattern in patterns])},
            result_types=[result_type],
        )

    @classmethod
    def _from_parsed(
        cls: type["TunerSelectOp"],
        patterns: ArrayAttr[Attribute],
        args: Sequence[SSAValue | Operation],
        tuner_args: Sequence[SSAValue | Operation],
        result_type: Attribute,
        parse_diagnostic: str | None,
    ) -> "TunerSelectOp":
        """从文本解析结果构造 tuner.select。

        功能说明:
        - 该内部入口只服务 parser，把非法 attr / type-list 内容延迟到 verifier 按公开错误语义报错。
        - 不出现在 spec/API 列表、公开 constructor 签名或测试公开调用形态中。

        使用示例:
        - op = TunerSelectOp._from_parsed(patterns, args, tuner_args, result_type, None)

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        attrs: dict[str, Attribute] = {"patterns": patterns}
        if parse_diagnostic is not None:
            attrs["_tuner_select_parse_diagnostic"] = StringAttr(parse_diagnostic)
        op = cls.__new__(cls)
        IRDLOperation.__init__(op, operands=[list(args), list(tuner_args)], attributes=attrs, result_types=[result_type])
        return op

    def verify_(self: "TunerSelectOp") -> None:
        """校验 tuner.select patterns、operand groups 与 result type。

        功能说明:
        - `patterns` 必须是非空 `ArrayAttr[SymbolRefAttr]`。
        - `args` 与 `tuner_args` 是两组独立 variadic operands，由 IRDL segment sizes 维护。
        - result 必须固定为 `!symbol.int<#symbol.expr<pattern_id>>`。

        使用示例:
        - TunerSelectOp(["pattern0"]).verify_()

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        if self._parse_diagnostic is not None:
            raise_verify_error(_ERROR_SCENE, self._parse_diagnostic.data)
        if not isinstance(self.patterns, ArrayAttr) or not self.patterns.data:
            raise_verify_error(_ERROR_SCENE, "tuner.select patterns must be non-empty ArrayAttr[SymbolRefAttr]")
        for pattern in self.patterns.data:
            if not isinstance(pattern, SymbolRefAttr):
                raise_verify_error(_ERROR_SCENE, "tuner.select patterns must be non-empty ArrayAttr[SymbolRefAttr]")
            if not pattern.root_reference.data or len(pattern.nested_references.data) != 0:
                raise_verify_error(_ERROR_SCENE, "tuner.select patterns must be non-empty ArrayAttr[SymbolRefAttr]")
        _verify_pattern_id_result_type(self.result.type, self.name)

    def print(self: "TunerSelectOp", printer: Printer) -> None:
        """打印 tuner.select 自定义文本语法。

        功能说明:
        - 两组 operands 都为空时输出旧式短语法。
        - 仅打印非空 `args(...)` / `tuner_args(...)` operand 组和对应 type list。

        使用示例:
        - TunerSelectOp(["p0"]).print(printer)
        - TunerSelectOp(["p0"], args=(arg,)).print(printer)

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        if self.args:
            printer.print_string(" args(")
            for index, arg in enumerate(self.args):
                if index:
                    printer.print_string(", ")
                printer.print_ssa_value(SSAValue.get(arg))
            printer.print_string(")")
        if self.tuner_args:
            printer.print_string(" tuner_args(")
            for index, arg in enumerate(self.tuner_args):
                if index:
                    printer.print_string(", ")
                printer.print_ssa_value(SSAValue.get(arg))
            printer.print_string(")")
        printer.print_string(" ")
        printer.print_attr_dict(
            {
                name: attr
                for name, attr in self.attributes.items()
                if name != "_tuner_select_parse_diagnostic"
            }
        )
        printer.print_string(" : ")
        if self.args:
            printer.print_string("args(")
            for index, arg in enumerate(self.args):
                if index:
                    printer.print_string(", ")
                printer.print_attribute(SSAValue.get(arg).type)
            printer.print_string(") ")
        if self.tuner_args:
            printer.print_string("tuner_args(")
            for index, arg in enumerate(self.tuner_args):
                if index:
                    printer.print_string(", ")
                printer.print_attribute(SSAValue.get(arg).type)
            printer.print_string(") ")
        if self.args or self.tuner_args:
            printer.print_string("-> ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls: type["TunerSelectOp"], parser: AttrParser) -> "TunerSelectOp":
        """解析 tuner.select 自定义文本语法。

        功能说明:
        - 解析旧式空 operand 语法与 `args(...)` / `tuner_args(...)` 显式 operand 语法。
        - 两组 type list 分别与实际 operands 数量和类型一致，否则按公开诊断失败。

        使用示例:
        - TunerSelectOp.parse(parser)

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        args: list[SSAValue] = []
        tuner_args: list[SSAValue] = []
        saw_args_group = parser.parse_optional_keyword("args") is not None
        if saw_args_group:
            parser.parse_punctuation("(", f"Expected '(' after args in {cls.name}.")
            if parser.parse_optional_punctuation(")") is None:
                args.append(parser.parse_operand("Expected tuner.select args operand."))
                while parser.parse_optional_punctuation(",") is not None:
                    args.append(parser.parse_operand("Expected tuner.select args operand."))
                parser.parse_punctuation(")", f"Expected ')' after args in {cls.name}.")
        saw_tuner_args_group = parser.parse_optional_keyword("tuner_args") is not None
        if saw_tuner_args_group:
            parser.parse_punctuation("(", f"Expected '(' after tuner_args in {cls.name}.")
            if parser.parse_optional_punctuation(")") is None:
                tuner_args.append(parser.parse_operand("Expected tuner.select tuner_args operand."))
                while parser.parse_optional_punctuation(",") is not None:
                    tuner_args.append(parser.parse_operand("Expected tuner.select tuner_args operand."))
                parser.parse_punctuation(")", f"Expected ')' after tuner_args in {cls.name}.")
        attrs = dict(parser.parse_optional_attr_dict() or {})
        parser.parse_punctuation(":", f"Expected ':' before type list in {cls.name}.")
        arg_types: list[Attribute] = []
        tuner_arg_types: list[Attribute] = []
        if saw_args_group or saw_tuner_args_group:
            if saw_args_group:
                parser.parse_keyword("args", f" in {cls.name}")
                arg_types = parser.parse_comma_separated_list(parser.Delimiter.PAREN, parser.parse_type)
            if saw_tuner_args_group:
                parser.parse_keyword("tuner_args", f" in {cls.name}")
                tuner_arg_types = parser.parse_comma_separated_list(parser.Delimiter.PAREN, parser.parse_type)
            parser.parse_punctuation("->", f"Expected '-> result_type' in {cls.name}.")
            result_type = parser.parse_type()
        else:
            result_type = parser.parse_type()
        patterns = attrs.pop("patterns", None)
        if patterns is None:
            raise_verify_error(_ERROR_SCENE, "tuner.select patterns must be non-empty ArrayAttr[SymbolRefAttr]")
        if attrs:
            raise_verify_error(_ERROR_SCENE, "tuner.select only accepts patterns attr")
        if not isinstance(patterns, ArrayAttr):
            raise_verify_error(_ERROR_SCENE, "tuner.select patterns must be non-empty ArrayAttr[SymbolRefAttr]")
        parse_diagnostic = None
        if not patterns.data or any(not isinstance(pattern, SymbolRefAttr) for pattern in patterns.data):
            parse_diagnostic = "tuner.select patterns must be non-empty ArrayAttr[SymbolRefAttr]"
        if saw_args_group:
            if len(arg_types) != len(args):
                parse_diagnostic = parse_diagnostic or "tuner.select args type list must match operands"
            else:
                for operand, operand_type in zip(args, arg_types, strict=True):
                    if SSAValue.get(operand).type != operand_type:
                        parse_diagnostic = parse_diagnostic or "tuner.select args type list must match operands"
        if saw_tuner_args_group:
            if len(tuner_arg_types) != len(tuner_args):
                parse_diagnostic = parse_diagnostic or "tuner.select tuner_args type list must match operands"
            else:
                for operand, operand_type in zip(tuner_args, tuner_arg_types, strict=True):
                    if SSAValue.get(operand).type != operand_type:
                        parse_diagnostic = parse_diagnostic or "tuner.select tuner_args type list must match operands"
        return cls._from_parsed(patterns, args, tuner_args, result_type, parse_diagnostic)

__all__ = [
    "TunerSelectOp",
]
