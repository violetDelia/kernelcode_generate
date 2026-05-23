"""Tuner dialect definitions.


功能说明:
- 定义 tuner dialect 的超参数声明、局部成本节点、pattern 选择与 pattern launch 接口。
- `tuner.param` 返回 `!symbol.int<#symbol.expr<name>>` 超参数标量，`tuner.cost` 透传原 op operands 与公开 metadata，并固定返回 `!symbol.int<#symbol.expr<expr>>` 局部成本。
- `tuner.cost.cost_kind` 接受任意非空字符串 attr。
- `tuner.select` 返回固定 `!symbol.int<#symbol.expr<pattern_id>>`，第一版由后端默认选择 pattern0。
- `tuner.launch` 表示 host dispatcher 对 pattern 函数的直接启动请求，后续必须由 `outline-device-kernel` 降成 `arch.launch`。

API 列表:
- `class TunerParamOp(result_type: Attribute)`
- `class TunerCostOp(operands: list[SSAValue | Operation], *, cost_kind: Attribute, op_name: Attribute, extra_attrs: dict[str, Attribute] | None = None, result_type: Attribute = SymbolValueType.from_expr("COST"))`
- `class TunerSelectOp(patterns: Sequence[str | SymbolRefAttr], result_type: Attribute = SymbolValueType.from_expr("pattern_id"))`
- `class TunerLaunchOp(callee: str | SymbolRefAttr, args: Sequence[SSAValue | Operation] = ())`
- `Tuner`

使用示例:
- from kernel_gen.dialect.tuner import Tuner, TunerParamOp, TunerCostOp

关联文件:
- spec: spec/dialect/tuner.md
- test: test/dialect/test_tuner.py
- 功能实现: kernel_gen/dialect/tuner.py
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

_ERROR_SCENE = "dialect.tuner verifier"
_TUNER_PARAM_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _raise_verify_error(expected: str) -> None:
    """统一抛出 tuner verifier 错误。


    功能说明:
    - 复用 tuner dialect 统一错误模板，生成带固定 scene/action/actual 的 `VerifyException`。
    - 供 `tuner.param`、`tuner.cost` 等 verifier 与 parser 共享错误格式，保持报错文本一致。

    使用示例:
    - _raise_verify_error("tuner.cost result type must be !symbol.int<#symbol.expr<expr>>")

    关联文件:
    - spec: spec/dialect/tuner.md
    - test: test/dialect/test_tuner.py
    - 功能实现: kernel_gen/dialect/tuner.py
    """

    raise VerifyException(
        ERROR_TEMPLATE.format(
            scene=_ERROR_SCENE,
            expected=expected,
            actual=ERROR_ACTUAL,
            action=ERROR_ACTION,
        )
    )
def _verify_symbol_value_result_type(result_type: Attribute, op_name: str) -> SymbolValueType:
    """校验 tuner.param 的结果类型。


    功能说明:
    - 要求结果类型必须为 `!symbol.int<#symbol.expr<name>>` 并通过自身校验。
    - 要求表达式为单个公开名称，避免 tuner 参数退化为常量或复合表达式。

    使用示例:
    - _verify_symbol_value_result_type(SymbolValueType.from_expr("BLOCK_M"), "tuner.param")

    关联文件:
    - spec: spec/dialect/tuner.md
    - test: test/dialect/test_tuner.py
    - 功能实现: kernel_gen/dialect/tuner.py
    """

    if not isinstance(result_type, SymbolValueType):
        raise VerifyException(
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
        raise VerifyException(
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{op_name} result symbol name must match [A-Za-z_][A-Za-z0-9_]*",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )
    return result_type


def _verify_pattern_id_result_type(result_type: Attribute, op_name: str) -> SymbolValueType:
    """校验 pattern 选择结果类型。

    功能说明:
    - 只接受 `!symbol.int<#symbol.expr<pattern_id>>`，避免 dispatcher 选择值被其它 symbol 语义替代。

    使用示例:
    - _verify_pattern_id_result_type(SymbolValueType.from_expr("pattern_id"), "tuner.select")

    关联文件:
    - spec: spec/dialect/tuner.md
    - test: test/dialect/test_tuner.py
    - 功能实现: kernel_gen/dialect/tuner.py
    """

    if not isinstance(result_type, SymbolValueType):
        _raise_verify_error(f"{op_name} result type must be !symbol.int<#symbol.expr<pattern_id>>")
    result_type.verify()
    if result_type.get_value() != "pattern_id":
        _raise_verify_error(f"{op_name} result type must be !symbol.int<#symbol.expr<pattern_id>>")
    return result_type


def _verify_symbol_ref_attr(attr: Attribute, op_name: str) -> SymbolRefAttr:
    """校验 callee / pattern 属性为 flat SymbolRefAttr。

    功能说明:
    - `tuner.select` 与 `tuner.launch` 都只接受直接 `@symbol`。
    - 嵌套引用或空 symbol 稳定失败，避免 dispatcher 指向不明确目标。

    使用示例:
    - callee = _verify_symbol_ref_attr(SymbolRefAttr("pattern0"), "tuner.launch")

    关联文件:
    - spec: spec/dialect/tuner.md
    - test: test/dialect/test_tuner.py
    - 功能实现: kernel_gen/dialect/tuner.py
    """

    if not isinstance(attr, SymbolRefAttr):
        _raise_verify_error(f"{op_name} callee must be SymbolRefAttr")
    if not attr.root_reference.data or len(attr.nested_references.data) != 0:
        _raise_verify_error(f"{op_name} callee must be SymbolRefAttr")
    return attr


def _pattern_symbol_attr(value: str | SymbolRefAttr, op_name: str) -> SymbolRefAttr:
    """把 pattern 名称规整为 SymbolRefAttr。

    功能说明:
    - 构造器接受字符串或已构造的 `SymbolRefAttr`，统一写入 `patterns` attr。
    - 非公开输入类型立即按对应 op 的公开 verifier 文本失败，不扩大 constructor 合同。

    使用示例:
    - attr = _pattern_symbol_attr("matmul_entry_pattern0", "tuner.select")

    关联文件:
    - spec: spec/dialect/tuner.md
    - test: test/dialect/test_tuner.py
    - 功能实现: kernel_gen/dialect/tuner.py
    """

    if isinstance(value, str):
        return SymbolRefAttr(value)
    if isinstance(value, SymbolRefAttr):
        return value
    if op_name == "tuner.select":
        _raise_verify_error("tuner.select patterns must be non-empty ArrayAttr[SymbolRefAttr]")
    _raise_verify_error(f"{op_name} callee must be SymbolRefAttr")


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
        - test: test/dialect/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner.py
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
        - test: test/dialect/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner.py
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
        - test: test/dialect/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner.py
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
        - test: test/dialect/test_tuner.py
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


        功能说明:
        - 构造透传原 op operands 的 `tuner.cost(...)->!symbol.int<#symbol.expr<expr>>`。
        - 保留原 op attrs，并显式要求公开 metadata attrs `cost_kind/op_name`。

        使用示例:
        - TunerCostOp([value], cost_kind=StringAttr("latency"), op_name=StringAttr("dma.copy"))

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner.py
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


        功能说明:
        - 要求结果类型固定为 `!symbol.int<#symbol.expr<expr>>`。
        - 要求 `cost_kind/op_name` 两个 metadata attr 满足公开合同。
        - 显式拒绝旧 `kind/device_func` attrs。

        使用示例:
        - TunerCostOp([value], cost_kind=StringAttr("latency"), op_name=StringAttr("dma.copy")).verify()

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner.py
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
        - test: test/dialect/test_tuner.py
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


        功能说明:
        - 解析 `tuner.cost(%args) {attrs} : (types) -> !symbol.int<#symbol.expr<expr>>`。
        - 在解析阶段按类型段解析 unresolved operands，确保 print 后再 parse 可闭环。

        使用示例:
        - TunerCostOp.parse(parser)

        关联文件:
        - spec: spec/dialect/tuner.md
        - test: test/dialect/test_tuner.py
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
        - test: test/dialect/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner.py
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
        - test: test/dialect/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner.py
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
        - test: test/dialect/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner.py
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
        - test: test/dialect/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner.py
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
        - test: test/dialect/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner.py
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
        - test: test/dialect/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner.py
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
        - test: test/dialect/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner.py
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
        - test: test/dialect/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner.py
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
        - test: test/dialect/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner.py
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
        - test: test/dialect/test_tuner.py
        - 功能实现: kernel_gen/dialect/tuner.py
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


Tuner = Dialect(
    "tuner",
    [TunerParamOp, TunerCostOp, TunerSelectOp, TunerLaunchOp],
    [],
)

__all__ = [
    "Tuner",
    "TunerCostOp",
    "TunerLaunchOp",
    "TunerParamOp",
    "TunerSelectOp",
]
