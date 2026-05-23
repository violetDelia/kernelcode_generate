"""tuner cost operation.

功能说明:
- 定义 tuner.cost op。

API 列表:
- `class TunerCostOp(operands: list[SSAValue | Operation], *, cost_kind: Attribute, op_name: Attribute, extra_attrs: dict[str, Attribute] | None = None, result_type: Attribute = SymbolValueType.from_expr("COST"))`

使用示例:
- `from kernel_gen.dialect.tuner.operation import ...`

关联文件:
- spec: spec/dialect/tuner.md
- test: test/dialect/tuner/
- 功能实现: kernel_gen/dialect/tuner/operation/cost.py
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

from ..common import _raise_verify_error

@irdl_op_definition
class TunerCostOp(IRDLOperation):
    """记录单个原 op 的局部成本元信息。"""

    name = "tuner.cost"

    operands_ = var_operand_def(Attribute)
    cost_kind = attr_def(Attribute)
    op_name = attr_def(Attribute)
    result = result_def(Attribute)

    def __init__(
        self: "TunerCostOp",
        operands: list[SSAValue | Operation],
        *,
        cost_kind: Attribute,
        op_name: Attribute,
        extra_attrs: dict[str, Attribute] | None = None,
        result_type: Attribute = SymbolValueType.from_expr("COST"),
    ) -> None:
        """初始化 tuner.cost。


        功能说明:
        - 构造透传原 op operands 的 `tuner.cost(...)->!symbol.int<#symbol.expr<expr>>`。
        - 保留原 op attrs，并显式要求公开 metadata attrs `cost_kind/op_name`。

        使用示例:
        - TunerCostOp([value], cost_kind=StringAttr("latency"), op_name=StringAttr("dma.copy"))

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        attributes = dict(extra_attrs or {})
        attributes.update(
            {
                "cost_kind": cost_kind,
                "op_name": op_name,
            }
        )
        super().__init__(operands=[operands], result_types=[result_type], attributes=attributes)

    def verify_(self: "TunerCostOp") -> None:
        """校验 tuner.cost metadata 与整数结果。


        功能说明:
        - 要求结果类型固定为 `!symbol.int<#symbol.expr<expr>>`。
        - 要求 `cost_kind/op_name` 两个 metadata attr 满足公开合同。
        - 显式拒绝旧 `kind/device_func` attrs。

        使用示例:
        - TunerCostOp([value], cost_kind=StringAttr("latency"), op_name=StringAttr("dma.copy")).verify()

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        if not isinstance(self.result.type, SymbolValueType):
            _raise_verify_error("tuner.cost result type must be !symbol.int<#symbol.expr<expr>>")
        self.result.type.verify()

        for attr_name, attr_value in (("cost_kind", self.cost_kind), ("op_name", self.op_name)):
            if not isinstance(attr_value, StringAttr):
                _raise_verify_error(f"tuner.cost {attr_name} must be string attr")
        if "kind" in self.attributes:
            _raise_verify_error("tuner.cost kind attr is not part of public contract")
        if "device_func" in self.attributes:
            _raise_verify_error("tuner.cost device_func attr is not part of public contract")

        if not self.cost_kind.data.strip():
            _raise_verify_error("tuner.cost cost_kind must be non-empty string attr")
        if not self.op_name.data.strip():
            _raise_verify_error("tuner.cost op_name must not be empty")

    def print(self: "TunerCostOp", printer: Printer) -> None:
        """打印 tuner.cost 自定义文本语法。


        功能说明:
        - 输出 `tuner.cost(%args) {attrs} : (types) -> !symbol.int<#symbol.expr<expr>>` 形式文本。
        - 保持 operands、attrs、类型段顺序稳定，便于 round-trip。

        使用示例:
        - TunerCostOp([value], cost_kind=cost_kind, op_name=op_name).print(printer)

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        printer.print_string("(")
        for index, operand in enumerate(self.operands_):
            if index:
                printer.print_string(", ")
            printer.print_ssa_value(operand)
        printer.print_string(") ")
        printer.print_attr_dict(self.attributes)
        printer.print_string(" : (")
        for index, operand in enumerate(self.operands_):
            if index:
                printer.print_string(", ")
            printer.print_attribute(SSAValue.get(operand).type)
        printer.print_string(") -> ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls: type["TunerCostOp"], parser: AttrParser) -> "TunerCostOp":
        """解析 tuner.cost 自定义文本语法。


        功能说明:
        - 解析 `tuner.cost(%args) {attrs} : (types) -> !symbol.int<#symbol.expr<expr>>`。
        - 在解析阶段按类型段解析 unresolved operands，确保 print 后再 parse 可闭环。

        使用示例:
        - TunerCostOp.parse(parser)

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        operands = parser.parse_comma_separated_list(parser.Delimiter.PAREN, parser.parse_unresolved_operand, f" in {cls.name}")
        attrs = dict(parser.parse_optional_attr_dict() or {})
        parser.parse_characters(":", f" in {cls.name}")
        operand_types = parser.parse_comma_separated_list(parser.Delimiter.PAREN, parser.parse_type, f" in {cls.name}")
        parser.parse_characters("->", f" in {cls.name}")
        result_type = parser.parse_type()

        if len(operands) != len(operand_types):
            _raise_verify_error("tuner.cost operands and operand types must have same length")
        resolved_operands = [parser.resolve_operand(operand, operand_type) for operand, operand_type in zip(operands, operand_types, strict=True)]

        try:
            cost_kind = attrs.pop("cost_kind")
            op_name = attrs.pop("op_name")
        except KeyError as exc:
            _raise_verify_error(f"tuner.cost requires attribute {exc.args[0]}")

        return cls(
            resolved_operands,
            cost_kind=cost_kind,
            op_name=op_name,
            extra_attrs=attrs,
            result_type=result_type,
        )

__all__ = [
    "TunerCostOp",
]
