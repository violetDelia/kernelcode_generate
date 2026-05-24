"""tuner param operation.

功能说明:
- 定义 tuner.param op。

API 列表:
- `class TunerParamOp(result_type: Attribute)`

使用示例:
- `from kernel_gen.dialect.tuner.operation import ...`

关联文件:
- spec: spec/dialect/tuner.md
- test: test/dialect/tuner/
- 功能实现: kernel_gen/dialect/tuner/operation/param.py
"""

from __future__ import annotations

from collections.abc import Sequence
import re

from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE, ErrorKind, ErrorModule, kernel_code_error
from xdsl.dialects.builtin import ArrayAttr, StringAttr, SymbolRefAttr
from xdsl.ir import Attribute, Dialect, Operation, SSAValue
from xdsl.irdl import IRDLOperation, attr_def, irdl_op_definition, opt_attr_def, result_def, var_operand_def
from xdsl.parser import AttrParser
from xdsl.printer import Printer

from kernel_gen.dialect.symbol import SymbolValueType

# Localized helpers from retired package-internal modules.

_ERROR_SCENE = "dialect.tuner verifier"

_TUNER_PARAM_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

def _verify_symbol_value_result_type(result_type: Attribute, op_name: str) -> SymbolValueType:
    """校验 tuner.param 的结果类型。


    功能说明:
    - 要求结果类型必须为 `!symbol.int<#symbol.expr<name>>` 并通过自身校验。
    - 要求表达式为单个公开名称，避免 tuner 参数退化为常量或复合表达式。

    使用示例:
    - _verify_symbol_value_result_type(SymbolValueType.from_expr("BLOCK_M"), "tuner.param")

    关联文件:
    - spec: spec/dialect/tuner.md
    - test: test/dialect/tuner/test_tuner.py
    - 功能实现: kernel_gen/dialect/tuner/
    """

    if not isinstance(result_type, SymbolValueType):
        raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{op_name} result type must be !symbol.int<#symbol.expr<name>>",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )
    result_type.verify()
    value = result_type.get_value()
    if not isinstance(value, str) or _TUNER_PARAM_NAME_PATTERN.fullmatch(value) is None:
        raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{op_name} result symbol name must match [A-Za-z_][A-Za-z0-9_]*",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )
    return result_type



@irdl_op_definition
class TunerParamOp(IRDLOperation):
    """声明超参数并返回符号值标量。"""

    name = "tuner.param"

    result = result_def(Attribute)

    def __init__(self: "TunerParamOp", result_type: Attribute) -> None:
        """初始化 tuner.param 操作。


        功能说明:
        - 构造仅含结果类型的 tuner.param op。

        使用示例:
        - TunerParamOp(SymbolValueType.from_expr("BLOCK_M"))

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        super().__init__(result_types=[result_type])

    def verify_(self: "TunerParamOp") -> None:
        """校验 tuner.param 的结果类型。


        功能说明:
        - 要求结果类型为 `!symbol.int<#symbol.expr<name>>`。

        使用示例:
        - TunerParamOp(SymbolValueType.from_expr("BLOCK_M")).verify()

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        _verify_symbol_value_result_type(self.result.type, self.name)

    def print(self: "TunerParamOp", printer: Printer) -> None:
        """打印 tuner.param 自定义文本语法。


        功能说明:
        - 输出 `tuner.param : !symbol.int<#symbol.expr<name>>`。

        使用示例:
        - TunerParamOp(SymbolValueType.from_expr("BLOCK_M")).print(printer)

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        printer.print_string(" : ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls: type["TunerParamOp"], parser: AttrParser) -> "TunerParamOp":
        """解析 tuner.param 自定义文本语法。


        功能说明:
        - 解析 `tuner.param : !symbol.int<#symbol.expr<name>>` 格式。

        使用示例:
        - TunerParamOp.parse(parser)

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/tuner/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner/
        """

        parser.parse_characters(":", f" in {cls.name}")
        return cls(parser.parse_type())

__all__ = [
    "TunerParamOp",
]
