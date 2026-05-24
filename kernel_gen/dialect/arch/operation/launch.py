"""arch launch operation.

功能说明:
- 定义 arch.launch op 与 ArchLaunchKernelOp alias。

API 列表:
- `class ArchLaunchOp(callee: str | Attribute, block: SSAValue | Operation, thread: SSAValue | Operation, subthread: SSAValue | Operation, shared_memory_size: SSAValue | Operation, args: Sequence[SSAValue | Operation] = ())`

使用示例:
- `from kernel_gen.dialect.arch.operation import ...`

关联文件:
- spec: spec/dialect/arch.md
- test: test/dialect/arch/
- 功能实现: kernel_gen/dialect/arch/operation/launch.py
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar

from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE, ErrorKind, ErrorModule, kernel_code_error
from kernel_gen.core.contracts import raise_verify_error
from xdsl.dialects.builtin import ArrayAttr, IntAttr, StringAttr, SymbolRefAttr, i8
from xdsl.ir import Attribute, Dialect, Operation, ParametrizedAttribute, SSAValue, TypeAttribute
from xdsl.irdl import (
    AttrSizedOperandSegments,
    IRDLOperation,
    attr_def,
    irdl_attr_definition,
    irdl_op_definition,
    operand_def,
    param_def,
    result_def,
    var_operand_def,
)
from xdsl.parser import AttrParser
from xdsl.printer import Printer

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr, SymbolValueType
from kernel_gen.target import registry

from kernel_gen.target import registry as target_registry

# Localized helpers from retired package-internal modules.

_ERROR_SCENE = "dialect.arch verifier"

def _verify_symbol_int_operand(value: SSAValue, field_name: str, op_name: str) -> SymbolValueType:
    """校验单个启动维度 operand 为 `!symbol.int<#symbol.expr<expr>>`。


    功能说明:
    - 统一校验 `arch.launch` 的维度输入类型。

    使用示例:
    - _verify_symbol_int_operand(op.block, "block", "arch.launch")

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/arch/test_arch.py
    - 功能实现: kernel_gen/dialect/arch/
    """

    if not isinstance(value.type, SymbolValueType):
        raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{op_name} {field_name} must have type !symbol.int<#symbol.expr<expr>>",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )
    value.type.verify()
    return value.type

def _verify_positive_static_symbol(operand_type: SymbolValueType, field_name: str, op_name: str) -> None:
    """校验可静态求值的 symbol.int 启动维度为正整数。


    功能说明:
    - 对字面量整数表达式执行 `> 0` 约束。
    - 对无法静态求值的符号表达式保持放行。

    使用示例:
    - _verify_positive_static_symbol(SymbolValueType.from_expr("8"), "block", "arch.launch")

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/arch/test_arch.py
    - 功能实现: kernel_gen/dialect/arch/
    """

    static_value = operand_type.get_value()
    if isinstance(static_value, int) and static_value <= 0:
        raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{op_name} {field_name} must be > 0 when statically known",
                actual=str(static_value),
                action=ERROR_ACTION,
            )
        )

def _verify_non_negative_static_symbol(operand_type: SymbolValueType, field_name: str, op_name: str) -> None:
    """校验可静态求值的 symbol.int 启动规模为非负整数。


    功能说明:
    - 对字面量整数表达式执行 `>= 0` 约束。
    - 对无法静态求值的符号表达式保持放行。

    使用示例:
    - _verify_non_negative_static_symbol(SymbolValueType.from_expr("0"), "shared_memory_size", "arch.launch")

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/arch/test_arch.py
    - 功能实现: kernel_gen/dialect/arch/
    """

    static_value = operand_type.get_value()
    if isinstance(static_value, int) and static_value < 0:
        raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{op_name} {field_name} must be >= 0 when statically known",
                actual=str(static_value),
                action=ERROR_ACTION,
            )
        )

def _verify_launch_callee_attr(callee: Attribute) -> SymbolRefAttr:
    """校验 launch 的 `@callee` symbol ref 属性。


    功能说明:
    - 仅接受无嵌套的 `@callee` 形式 `SymbolRefAttr`。

    使用示例:
    - _verify_launch_callee_attr(SymbolRefAttr("kernel_body"))

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/arch/test_arch.py
    - 功能实现: kernel_gen/dialect/arch/
    """

    if not isinstance(callee, SymbolRefAttr):
        raise_verify_error(_ERROR_SCENE, "arch.launch callee must be @symbol")
    if not callee.root_reference.data:
        raise_verify_error(_ERROR_SCENE, "arch.launch callee must not be empty")
    if len(callee.nested_references.data) != 0:
        raise_verify_error(_ERROR_SCENE, "arch.launch callee must be flat @symbol")
    return callee

def _verify_target_registry_support(op_name: str) -> None:
    """按当前 target registry 配置校验 arch op 支持性。


    功能说明:
    - 在启用 target registry 校验时，检查 arch op 是否被当前 target 支持。

    使用示例:
    - _verify_target_registry_support("arch.get_thread_id")

    关联文件:
    - spec: spec/target/registry.md
    - test: test/dialect/arch/test_arch.py
    - 功能实现: kernel_gen/dialect/arch/
    """

    current_target = target_registry.get_current_target()
    if current_target is None:
        return
    try:
        if not target_registry.is_arch_op_supported(current_target, op_name):
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected=f"{op_name} is not supported by target {current_target}",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
    except ValueError as exc:
        raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=str(exc),
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        ) from exc



@irdl_op_definition
class ArchLaunchOp(IRDLOperation):
    """描述一次四层执行规模的 kernel 启动请求。"""

    name = "arch.launch"

    block = operand_def(Attribute)
    thread = operand_def(Attribute)
    subthread = operand_def(Attribute)
    shared_memory_size = operand_def(Attribute)
    args = var_operand_def(Attribute)
    callee = attr_def(SymbolRefAttr)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self: "ArchLaunchOp",
        callee: str | Attribute,
        block: SSAValue | Operation,
        thread: SSAValue | Operation,
        subthread: SSAValue | Operation,
        shared_memory_size: SSAValue | Operation,
        args: Sequence[SSAValue | Operation] = (),
    ) -> None:
        """初始化 arch.launch。


        功能说明:
        - 记录 `@callee`、block/thread/subthread/shared_memory_size 与尾部 args。

        使用示例:
        - ArchLaunchOp("my_kernel", block, thread, subthread, shared_memory_size, (lhs, rhs, out))

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/arch/test_arch.py
        - 功能实现: kernel_gen/dialect/arch/
        """

        callee_attr = SymbolRefAttr(callee) if isinstance(callee, str) else callee
        super().__init__(
            operands=[block, thread, subthread, shared_memory_size, list(args)],
            attributes={"callee": callee_attr},
        )

    def verify_(self: "ArchLaunchOp") -> None:
        """校验 arch.launch 输入约束。


        功能说明:
        - 校验 `@callee` 与四字段 extent。
        - 前三字段必须是 `!symbol.int<...>` 且静态已知时必须 `> 0`。
        - `shared_memory_size` 必须是 `!symbol.int<...>` 且静态已知时必须 `>= 0`。

        使用示例:
        - ArchLaunchOp("kernel", block, thread, subthread, shared_memory_size).verify()

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/arch/test_arch.py
        - 功能实现: kernel_gen/dialect/arch/
        """

        _verify_target_registry_support(self.name)
        _verify_launch_callee_attr(self.callee)

        for field_name, operand in (
            ("block", self.block),
            ("thread", self.thread),
            ("subthread", self.subthread),
        ):
            operand_value = SSAValue.get(operand)
            operand_type = _verify_symbol_int_operand(operand_value, field_name, self.name)
            _verify_positive_static_symbol(operand_type, field_name, self.name)
        shared_memory_size = SSAValue.get(self.shared_memory_size)
        shared_memory_size_type = _verify_symbol_int_operand(shared_memory_size, "shared_memory_size", self.name)
        _verify_non_negative_static_symbol(shared_memory_size_type, "shared_memory_size", self.name)

    def print(self: "ArchLaunchOp", printer: Printer) -> None:
        """打印 arch.launch 自定义文本语法。

        功能说明:
        - 输出 launch extent、callee、参数 operand 与函数类型。

        使用示例:
        - ArchLaunchOp(callee, block, thread, subthread, shared, args).print(printer)
        """

        printer.print_string("<")
        printer.print_ssa_value(self.block)
        printer.print_string(", ")
        printer.print_ssa_value(self.thread)
        printer.print_string(", ")
        printer.print_ssa_value(self.subthread)
        printer.print_string(", ")
        printer.print_ssa_value(self.shared_memory_size)
        printer.print_string(">(")
        printer.print_attribute(self.callee)
        for operand in self.args:
            printer.print_string(", ")
            printer.print_ssa_value(SSAValue.get(operand))
        printer.print_string(") : (")
        for index, operand in enumerate(self.args):
            if index:
                printer.print_string(", ")
            printer.print_attribute(SSAValue.get(operand).type)
        printer.print_string(") -> ()")

    @classmethod
    def parse(cls: type["ArchLaunchOp"], parser: AttrParser) -> "ArchLaunchOp":
        """解析 arch.launch 自定义文本语法。

        功能说明:
        - 读取 launch extent、callee、参数 operand 与类型列表并构造 op。

        使用示例:
        - ArchLaunchOp.parse(parser)
        """

        parser.parse_punctuation("<", f"Expected '<' in {cls.name}.")
        block = parser.parse_operand("Expected block extent operand.")
        parser.parse_punctuation(",", f"Expected ',' after block extent in {cls.name}.")
        thread = parser.parse_operand("Expected thread extent operand.")
        parser.parse_punctuation(",", f"Expected ',' after thread extent in {cls.name}.")
        subthread = parser.parse_operand("Expected subthread extent operand.")
        parser.parse_punctuation(",", f"Expected ',' after subthread extent in {cls.name}.")
        shared_memory_size = parser.parse_operand("Expected shared_memory_size extent operand.")
        parser.parse_punctuation(">", f"Expected '>' after extents in {cls.name}.")
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
        if result_types:
            raise_verify_error(_ERROR_SCENE, "arch.launch result types must be ()")
        if len(arg_types) != len(args):
            raise_verify_error(_ERROR_SCENE, "arch.launch arg type list must match operand count")
        for operand, operand_type in zip(args, arg_types, strict=True):
            if SSAValue.get(operand).type != operand_type:
                raise_verify_error(_ERROR_SCENE, "arch.launch arg types must match operand types")
        return cls(callee, block, thread, subthread, shared_memory_size, args)


ArchLaunchKernelOp = ArchLaunchOp

__all__ = ["ArchLaunchOp", "ArchLaunchKernelOp"]
