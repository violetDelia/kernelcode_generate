"""Tuner dialect definitions.

创建者: 我不是牛马
最后一次更改: 金铲铲大作战

功能说明:
- 定义 tuner dialect 的超参数声明与局部成本节点接口。
- `tuner.param` 返回 `!symbol.dim<"name">` 超参数标量，`tuner.cost` 透传原 op operands 与公开 metadata，并固定返回 `!symbol.int<"expr">` 局部成本。
- `tuner.cost.cost_kind` 接受任意非空字符串 attr。

使用示例:
- from kernel_gen.dialect.tuner import Tuner, TunerParamOp, TunerCostOp

关联文件:
- spec: spec/dialect/tuner.md
- test: test/dialect/test_tuner_dialect.py
- 功能实现: kernel_gen/dialect/tuner.py
"""

from __future__ import annotations

from kernel_gen.core.contracts import _ERROR_TEMPLATE
from xdsl.dialects.builtin import StringAttr
from xdsl.ir import Attribute, Dialect, Operation, SSAValue
from xdsl.irdl import IRDLOperation, attr_def, irdl_op_definition, result_def, var_operand_def
from xdsl.parser import AttrParser
from xdsl.printer import Printer
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.symbol import SymbolDimType, SymbolValueType

_ERROR_ACTION = "请按接口约束传参"
_ERROR_ACTUAL = "不满足期望"
_ERROR_SCENE = "dialect.tuner verifier"
def _raise_verify_error(expected: str) -> None:
    """统一抛出 tuner verifier 错误。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 复用 tuner dialect 统一错误模板，生成带固定 scene/action/actual 的 `VerifyException`。
    - 供 `tuner.param`、`tuner.cost` 等 verifier 与 parser 共享错误格式，保持报错文本一致。

    使用示例:
    - _raise_verify_error('tuner.cost result type must be !symbol.int<"expr">')

    关联文件:
    - spec: spec/dialect/tuner.md
    - test: test/dialect/test_tuner_dialect.py
    - 功能实现: kernel_gen/dialect/tuner.py
    """

    raise VerifyException(
        _ERROR_TEMPLATE.format(
            scene=_ERROR_SCENE,
            expected=expected,
            actual=_ERROR_ACTUAL,
            action=_ERROR_ACTION,
        )
    )
def _verify_symbol_dim_result_type(result_type: Attribute, op_name: str) -> SymbolDimType:
    """校验 tuner.param 的结果类型。

    创建者: 我不是牛马
    最后一次更改: 小李飞刀

    功能说明:
    - 要求结果类型必须为 `!symbol.dim<"name">` 并通过自身校验。
    - 使用 `SymbolDimType` 的命名校验确保 name 合法。

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

    result = result_def(Attribute)

    def __init__(self: "TunerParamOp", result_type: Attribute) -> None:
        """初始化 tuner.param 操作。

        创建者: 我不是牛马
        最后一次更改: 小李飞刀

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
        最后一次更改: 小李飞刀

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
        最后一次更改: 小李飞刀

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
        最后一次更改: 小李飞刀

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

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 构造透传原 op operands 的 `tuner.cost(...)->!symbol.int<"...">`。
        - 保留原 op attrs，并显式要求公开 metadata attrs `cost_kind/op_name`。

        使用示例:
        - TunerCostOp([value], cost_kind=StringAttr("latency"), op_name=StringAttr("dma.copy"))

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner_dialect.py
        - 功能实现: kernel_gen/dialect/tuner.py
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

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 要求结果类型固定为 `!symbol.int<"expr">`。
        - 要求 `cost_kind/op_name` 两个 metadata attr 满足公开合同。
        - 显式拒绝旧 `kind/device_func` attrs。

        使用示例:
        - TunerCostOp([value], cost_kind=StringAttr("latency"), op_name=StringAttr("dma.copy")).verify()

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner_dialect.py
        - 功能实现: kernel_gen/dialect/tuner.py
        """

        if not isinstance(self.result.type, SymbolValueType):
            _raise_verify_error('tuner.cost result type must be !symbol.int<"expr">')
        self.result.type.verify()

        for attr_name in ("cost_kind", "op_name"):
            attr_value = getattr(self, attr_name)
            if not hasattr(attr_value, "data") or not isinstance(attr_value.data, str):
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

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 输出 `tuner.cost(%args) {attrs} : (types) -> !symbol.int<"...">` 形式文本。
        - 保持 operands、attrs、类型段顺序稳定，便于 round-trip。

        使用示例:
        - TunerCostOp([value], cost_kind=cost_kind, op_name=op_name).print(printer)

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner_dialect.py
        - 功能实现: kernel_gen/dialect/tuner.py
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

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 解析 `tuner.cost(%args) {attrs} : (types) -> !symbol.int<"...">`。
        - 在解析阶段按类型段解析 unresolved operands，确保 print 后再 parse 可闭环。

        使用示例:
        - TunerCostOp.parse(parser)

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner_dialect.py
        - 功能实现: kernel_gen/dialect/tuner.py
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


Tuner = Dialect(
    "tuner",
    [TunerParamOp, TunerCostOp],
    [],
)

__all__ = [
    "Tuner",
    "TunerCostOp",
    "TunerParamOp",
]
