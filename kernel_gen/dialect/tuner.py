"""Tuner dialect definitions.

创建者: 我不是牛马
最后一次更改: 我不是牛马

功能说明:
- 定义 tuner dialect 的超参数声明 op，用于生成符号维度标量。

使用示例:
- from kernel_gen.dialect.tuner import Tuner, TunerParamOp

关联文件:
- spec: spec/dialect/tuner.md
- test: test/dialect/test_tuner_dialect.py
- 功能实现: kernel_gen/dialect/tuner.py
"""

from __future__ import annotations

from xdsl.ir import Attribute, Dialect
from xdsl.irdl import IRDLOperation, irdl_op_definition, result_def
from xdsl.parser import AttrParser
from xdsl.printer import Printer
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.symbol import SymbolDimType

_ERROR_TEMPLATE = "场景: {scene}; 期望: {expected}; 实际: {actual}; 建议动作: {action}"
_ERROR_ACTION = "请按接口约束传参"
_ERROR_ACTUAL = "不满足期望"
_ERROR_SCENE = "dialect.tuner verifier"

def _verify_symbol_dim_result_type(result_type: Attribute, op_name: str) -> SymbolDimType:
    """校验 tuner.param 的结果类型。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 要求结果类型必须为 `!symbol.dim<"name">` 并通过自身校验。

    使用示例:
    - _verify_symbol_dim_result_type(SymbolDimType.from_name("BLOCK_M"), "tuner.param")

    关联文件:
    - spec: spec/dialect/tuner.md
    - test: test/dialect/test_tuner_dialect.py
    - 功能实现: kernel_gen/dialect/tuner.py
    """

    if not isinstance(result_type, SymbolDimType):
        raise VerifyException(
            _ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{op_name} result type must be !symbol.dim<\"name\">",
                actual=_ERROR_ACTUAL,
                action=_ERROR_ACTION,
            )
        )
    result_type.verify()
    return result_type


@irdl_op_definition
class TunerParamOp(IRDLOperation):
    """声明超参数并返回符号维度标量。"""

    name = "tuner.param"

    result = result_def(SymbolDimType)

    def __init__(self: "TunerParamOp", result_type: Attribute) -> None:
        """初始化 tuner.param 操作。

        创建者: 我不是牛马
        最后一次更改: 我不是牛马

        功能说明:
        - 构造仅含结果类型的 tuner.param op。

        使用示例:
        - TunerParamOp(SymbolDimType.from_name("BLOCK_M"))

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner_dialect.py
        - 功能实现: kernel_gen/dialect/tuner.py
        """

        super().__init__(result_types=[result_type])

    def verify_(self: "TunerParamOp") -> None:
        """校验 tuner.param 的结果类型。

        创建者: 我不是牛马
        最后一次更改: 我不是牛马

        功能说明:
        - 要求结果类型为 `!symbol.dim<"name">`。

        使用示例:
        - TunerParamOp(SymbolDimType.from_name("BLOCK_M")).verify()

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner_dialect.py
        - 功能实现: kernel_gen/dialect/tuner.py
        """

        _verify_symbol_dim_result_type(self.result.type, self.name)

    def print(self: "TunerParamOp", printer: Printer) -> None:
        """打印 tuner.param 自定义文本语法。

        创建者: 我不是牛马
        最后一次更改: 我不是牛马

        功能说明:
        - 输出 `tuner.param : !symbol.dim<"name">`。

        使用示例:
        - TunerParamOp(SymbolDimType.from_name("BLOCK_M")).print(printer)

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner_dialect.py
        - 功能实现: kernel_gen/dialect/tuner.py
        """

        printer.print_string(" : ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls: type["TunerParamOp"], parser: AttrParser) -> "TunerParamOp":
        """解析 tuner.param 自定义文本语法。

        创建者: 我不是牛马
        最后一次更改: 我不是牛马

        功能说明:
        - 解析 `tuner.param : !symbol.dim<"name">` 格式。

        使用示例:
        - TunerParamOp.parse(parser)

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner_dialect.py
        - 功能实现: kernel_gen/dialect/tuner.py
        """

        parser.parse_characters(":", f" in {cls.name}")
        return cls(parser.parse_type())


Tuner = Dialect(
    "tuner",
    [TunerParamOp],
    [],
)

__all__ = [
    "Tuner",
    "TunerParamOp",
]
