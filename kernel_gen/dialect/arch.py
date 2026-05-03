"""Arch dialect definitions.


功能说明:
- 定义 arch dialect 的执行维度查询、动态片上内存入口、barrier 与 launch op。
- 复用 symbol dialect 的 `!symbol.int<"expr">` 与 nn dialect 的 `nn.memory/#nn.space`。

API 列表:
- `class ArchScopeAttr(scope: StringAttr)`
- `ArchScopeAttr.from_name(name: str) -> ArchScopeAttr`
- `class ArchVisibilityAttr(visibility: StringAttr)`
- `ArchVisibilityAttr.from_name(name: str) -> ArchVisibilityAttr`
- `class ArchGetBlockIdOp(result_type: Attribute | None = None)`
- `class ArchGetBlockNumOp(result_type: Attribute | None = None)`
- `class ArchGetThreadIdOp(result_type: Attribute | None = None)`
- `class ArchGetThreadNumOp(result_type: Attribute | None = None)`
- `class ArchGetSubthreadIdOp(result_type: Attribute | None = None)`
- `class ArchGetSubthreadNumOp(result_type: Attribute | None = None)`
- `class ArchGetDynamicMemoryOp(memory_space: NnMemorySpaceAttr, result_type: Attribute | None = None)`
- `class ArchBarrierOp(scope: ArchScopeAttr, visibility: ArrayAttr[Attribute])`
- `class ArchLaunchOp(callee: str | Attribute, block: SSAValue | Operation, thread: SSAValue | Operation, subthread: SSAValue | Operation, shared_memory_size: SSAValue | Operation, args: Sequence[SSAValue | Operation] = ())`
- `ArchLaunchKernelOp = ArchLaunchOp`
- `Arch`

使用示例:
- from kernel_gen.dialect.arch import Arch, ArchBarrierOp, ArchGetBlockIdOp, ArchLaunchOp

关联文件:
- spec: spec/dialect/arch.md
- test: test/dialect/test_arch.py
- 功能实现: kernel_gen/dialect/arch.py
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar

from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE
from xdsl.dialects.builtin import ArrayAttr, IntAttr, StringAttr, SymbolRefAttr, i8
from xdsl.ir import Attribute, Dialect, Operation, ParametrizedAttribute, SSAValue
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
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.target import registry as target_registry

_DYNAMIC_MEMORY_SPACES = {"shared", "local", "tsm", "tlm1", "tlm2", "tlm3"}
_ERROR_SCENE = "dialect.arch verifier"
_BARRIER_SCOPE_VALUES = {"block", "thread", "subthread", "global"}
_BARRIER_VISIBLE_SPACES = {"tsm", "tlm"}


def _raise_verify_error(expected: str, *, actual: str = ERROR_ACTUAL) -> None:
    """统一抛出 arch dialect verifier 错误。


    功能说明:
    - 复用统一错误模板，保持 barrier/launch 边界短语稳定。

    使用示例:
    - _raise_verify_error("arch.launch callee must be @symbol")

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/test_arch.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    raise VerifyException(
        ERROR_TEMPLATE.format(
            scene=_ERROR_SCENE,
            expected=expected,
            actual=actual,
            action=ERROR_ACTION,
        )
    )


def _verify_symbol_int_operand(value: SSAValue, field_name: str, op_name: str) -> SymbolValueType:
    """校验单个启动维度 operand 为 `!symbol.int<\"expr\">`。


    功能说明:
    - 统一校验 `arch.launch` 的维度输入类型。

    使用示例:
    - _verify_symbol_int_operand(op.block, "block", "arch.launch")

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/test_arch.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    if not isinstance(value.type, SymbolValueType):
        raise VerifyException(
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{op_name} {field_name} must have type !symbol.int<\"expr\">",
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
    - test: test/dialect/test_arch.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    static_value = operand_type.get_value()
    if isinstance(static_value, int) and static_value <= 0:
        raise VerifyException(
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
    - test: test/dialect/test_arch.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    static_value = operand_type.get_value()
    if isinstance(static_value, int) and static_value < 0:
        raise VerifyException(
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
    - test: test/dialect/test_arch.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    if not isinstance(callee, SymbolRefAttr):
        _raise_verify_error("arch.launch callee must be @symbol")
    if not callee.root_reference.data:
        _raise_verify_error("arch.launch callee must not be empty")
    if len(callee.nested_references.data) != 0:
        _raise_verify_error("arch.launch callee must be flat @symbol")
    return callee


def _verify_barrier_visibility_attr(visibility: Attribute) -> ArrayAttr[Attribute]:
    """校验 barrier visibility 列表。


    功能说明:
    - visibility 必须是非空 `ArrayAttr`。
    - 元素必须唯一，且必须且只能包含 `#arch.visibility<tsm>` 与 `#arch.visibility<tlm>`。

    使用示例:
    - _verify_barrier_visibility_attr(ArrayAttr([...]))

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/test_arch.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    if not isinstance(visibility, ArrayAttr):
        _raise_verify_error("arch.barrier visibility must be ArrayAttr")
    if not visibility.data:
        _raise_verify_error("arch.barrier visibility must not be empty")
    seen: set[str] = set()
    for entry in visibility.data:
        if not isinstance(entry, ArchVisibilityAttr):
            _raise_verify_error("arch.barrier visibility items must be #arch.visibility<...>")
        space_name = entry.visibility.data
        if space_name in seen:
            _raise_verify_error("arch.barrier visibility must not contain duplicates")
        seen.add(space_name)
        if space_name not in _BARRIER_VISIBLE_SPACES:
            _raise_verify_error("arch.barrier visibility must contain only #arch.visibility<tsm>/#arch.visibility<tlm>")
    if seen != _BARRIER_VISIBLE_SPACES:
        _raise_verify_error("arch.barrier visibility must contain both #arch.visibility<tsm> and #arch.visibility<tlm>")
    return visibility


@irdl_attr_definition
class ArchVisibilityAttr(ParametrizedAttribute):
    """表示 `arch.barrier` 的聚合可见域属性。"""

    name = "arch.visibility"

    visibility: StringAttr = param_def(StringAttr)

    @classmethod
    def parse_parameters(cls: type["ArchVisibilityAttr"], parser: AttrParser) -> Sequence[Attribute]:
        """解析 arch.visibility 参数。


        功能说明:
        - 支持 `#arch.visibility<tsm>` 与 `#arch.visibility<tlm>` 的文本。

        使用示例:
        - ArchVisibilityAttr.parse_parameters(parser)

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/test_arch.py
        - 功能实现: kernel_gen/dialect/arch.py
        """

        parser.parse_punctuation("<", "Expected '<' for arch.visibility.")
        visibility_name = parser.parse_identifier("Expected arch visibility name.")
        parser.parse_punctuation(">", "Expected '>' for arch.visibility.")
        return (StringAttr(visibility_name),)

    def print_parameters(self: "ArchVisibilityAttr", printer: Printer) -> None:
        """打印 arch.visibility 参数。"""

        printer.print_string("<")
        printer.print_string(self.visibility.data)
        printer.print_string(">")

    def verify(self: "ArchVisibilityAttr") -> None:
        """校验 arch.visibility 参数。"""

        if self.visibility.data not in _BARRIER_VISIBLE_SPACES:
            _raise_verify_error("arch.visibility must be tsm/tlm")

    @classmethod
    def from_name(cls: type["ArchVisibilityAttr"], name: str) -> "ArchVisibilityAttr":
        """按名称构造 arch.visibility 属性。


        功能说明:
        - 为测试与实现提供统一的 barrier 可见域构造入口。

        使用示例:
        - ArchVisibilityAttr.from_name("tsm")

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/test_arch.py
        - 功能实现: kernel_gen/dialect/arch.py
        """

        return cls(StringAttr(name))


@irdl_attr_definition
class ArchScopeAttr(ParametrizedAttribute):
    """表示 `arch.barrier` 的 scope 属性。"""

    name = "arch.scope"

    scope: StringAttr = param_def(StringAttr)

    @classmethod
    def parse_parameters(cls: type["ArchScopeAttr"], parser: AttrParser) -> Sequence[Attribute]:
        """解析 arch.scope 参数。


        功能说明:
        - 支持 `#arch.scope<block>` / `thread` / `subthread` / `global>` 的文本。

        使用示例:
        - ArchScopeAttr.parse_parameters(parser)

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/test_arch.py
        - 功能实现: kernel_gen/dialect/arch.py
        """

        parser.parse_punctuation("<", "Expected '<' for arch.scope.")
        scope_name = parser.parse_identifier("Expected arch scope name.")
        parser.parse_punctuation(">", "Expected '>' for arch.scope.")
        return (StringAttr(scope_name),)

    def print_parameters(self: "ArchScopeAttr", printer: Printer) -> None:
        """打印 arch.scope 参数。"""

        printer.print_string("<")
        printer.print_string(self.scope.data)
        printer.print_string(">")

    def verify(self: "ArchScopeAttr") -> None:
        """校验 arch.scope 参数。"""

        if self.scope.data not in _BARRIER_SCOPE_VALUES:
            _raise_verify_error("arch.scope must be block/thread/subthread/global")

    @classmethod
    def from_name(cls: type["ArchScopeAttr"], name: str) -> "ArchScopeAttr":
        """按名称构造 arch.scope 属性。


        功能说明:
        - 为测试与实现提供统一的构造入口。

        使用示例:
        - ArchScopeAttr.from_name("block")

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/test_arch.py
        - 功能实现: kernel_gen/dialect/arch.py
        """

        return cls(StringAttr(name))


def _dynamic_memory_result_type(space: NnMemorySpaceAttr) -> NnMemoryType:
    """构造动态 memory 入口的固定结果类型。


    功能说明:
    - 返回 `!nn.memory<[?], [1], i8, #nn.space<space>>`。

    使用示例:
    - _dynamic_memory_result_type(NnMemorySpaceAttr.from_name("shared"))

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/test_arch.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    return NnMemoryType(
        ArrayAttr([StringAttr("?")]),
        ArrayAttr([IntAttr(1)]),
        i8,
        space,
    )


def _verify_target_registry_support(op_name: str) -> None:
    """按当前 target registry 配置校验 arch op 支持性。


    功能说明:
    - 在启用 target registry 校验时，检查 arch op 是否被当前 target 支持。

    使用示例:
    - _verify_target_registry_support("arch.get_thread_id")

    关联文件:
    - spec: spec/target/registry.md
    - test: test/dialect/test_arch.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    current_target = target_registry.get_current_target()
    if current_target is None:
        return
    try:
        if not target_registry.is_arch_op_supported(current_target, op_name):
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected=f"{op_name} is not supported by target {current_target}",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
    except ValueError as exc:
        raise VerifyException(
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=str(exc),
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        ) from exc


class _BaseArchIndexQueryOp(IRDLOperation):
    """固定返回指定 symbol.int 类型的 arch 查询 op 基类。"""

    result = result_def(SymbolValueType)

    RESULT_EXPR: ClassVar[str]

    def __init__(
        self: "_BaseArchIndexQueryOp",
        result_type: Attribute | None = None,
    ) -> None:
        """初始化固定结果类型的 arch 查询 op。


        功能说明:
        - 支持默认构造固定结果类型，也支持 parser 注入显式结果类型后由 verifier 校验。

        使用示例:
        - ArchGetBlockIdOp()

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/test_arch.py
        - 功能实现: kernel_gen/dialect/arch.py
        """

        super().__init__(result_types=[result_type or SymbolValueType.from_expr(self.RESULT_EXPR)])

    def verify_(self: "_BaseArchIndexQueryOp") -> None:
        """校验固定结果类型查询 op。


        功能说明:
        - 校验固定结果类型并在启用 target registry 时执行支持性检查。

        使用示例:
        - ArchGetBlockIdOp().verify()

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/test_arch.py
        - 功能实现: kernel_gen/dialect/arch.py
        """

        expected = SymbolValueType.from_expr(self.RESULT_EXPR)
        if self.result.type != expected:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected=f"{self.name} result type must be !symbol.int<\"{self.RESULT_EXPR}\">",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        _verify_target_registry_support(self.name)

    def print(self: "_BaseArchIndexQueryOp", printer: Printer) -> None:
        """打印固定结果类型查询 op 自定义文本语法。"""

        printer.print_string(" : ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls: type["_BaseArchIndexQueryOp"], parser: AttrParser) -> "_BaseArchIndexQueryOp":
        """解析固定结果类型查询 op 自定义文本语法。"""

        parser.parse_characters(":", f" in {cls.name}")
        return cls(parser.parse_type())


@irdl_op_definition
class ArchGetBlockIdOp(_BaseArchIndexQueryOp):
    """返回当前 block 的执行索引。"""

    name = "arch.get_block_id"
    RESULT_EXPR: ClassVar[str] = "block_id"


@irdl_op_definition
class ArchGetBlockNumOp(_BaseArchIndexQueryOp):
    """返回当前 launch 的 block 数量。"""

    name = "arch.get_block_num"
    RESULT_EXPR: ClassVar[str] = "block_num"


@irdl_op_definition
class ArchGetThreadIdOp(_BaseArchIndexQueryOp):
    """返回当前 block 内 thread 执行索引。"""

    name = "arch.get_thread_id"
    RESULT_EXPR: ClassVar[str] = "thread_id"


@irdl_op_definition
class ArchGetThreadNumOp(_BaseArchIndexQueryOp):
    """返回当前 block 内 thread 数量。"""

    name = "arch.get_thread_num"
    RESULT_EXPR: ClassVar[str] = "thread_num"


@irdl_op_definition
class ArchGetSubthreadIdOp(_BaseArchIndexQueryOp):
    """返回当前 thread 内 subthread 执行索引。"""

    name = "arch.get_subthread_id"
    RESULT_EXPR: ClassVar[str] = "subthread_id"


@irdl_op_definition
class ArchGetSubthreadNumOp(_BaseArchIndexQueryOp):
    """返回当前 thread 内 subthread 数量。"""

    name = "arch.get_subthread_num"
    RESULT_EXPR: ClassVar[str] = "subthread_num"


@irdl_op_definition
class ArchGetDynamicMemoryOp(IRDLOperation):
    """获取指定片上 memory space 的动态字节缓冲入口。"""

    name = "arch.get_dynamic_memory"

    memory_space = attr_def(NnMemorySpaceAttr)
    result = result_def(NnMemoryType)

    def __init__(
        self: "ArchGetDynamicMemoryOp",
        memory_space: NnMemorySpaceAttr,
        result_type: Attribute | None = None,
    ) -> None:
        """初始化 arch.get_dynamic_memory。


        功能说明:
        - 记录 memory space，并默认推导固定结果类型。

        使用示例:
        - ArchGetDynamicMemoryOp(NnMemorySpaceAttr.from_name("shared"))

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/test_arch.py
        - 功能实现: kernel_gen/dialect/arch.py
        """

        super().__init__(
            result_types=[result_type or _dynamic_memory_result_type(memory_space)],
            attributes={"memory_space": memory_space},
        )

    def verify_(self: "ArchGetDynamicMemoryOp") -> None:
        """校验动态 memory 入口 op。


        功能说明:
        - 校验 memory_space 与结果类型，并在启用 target registry 时执行支持性检查。

        使用示例:
        - ArchGetDynamicMemoryOp(NnMemorySpaceAttr.from_name("shared")).verify()

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/test_arch.py
        - 功能实现: kernel_gen/dialect/arch.py
        """

        _verify_target_registry_support(self.name)
        self.memory_space.verify()
        space_name = self.memory_space.space.data
        if space_name not in _DYNAMIC_MEMORY_SPACES:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="arch.get_dynamic_memory memory_space must be shared/local/tsm/tlm1/tlm2/tlm3",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )

        if not isinstance(self.result.type, NnMemoryType):
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="arch.get_dynamic_memory result type must be nn.memory",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )

        result_type = self.result.type
        result_type.verify()

        if len(result_type.shape.data) != 1:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="arch.get_dynamic_memory result must be 1-D",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if len(result_type.stride.data) != 1:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="arch.get_dynamic_memory result stride rank must be 1",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if result_type.shape.data[0] != StringAttr("?"):
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="arch.get_dynamic_memory result shape must be [?]",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if result_type.stride.data[0] != IntAttr(1):
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="arch.get_dynamic_memory result stride must be [1]",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if result_type.element_type != i8:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="arch.get_dynamic_memory result element type must be i8",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if result_type.space != self.memory_space:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="arch.get_dynamic_memory result space must match memory_space",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )

    def print(self: "ArchGetDynamicMemoryOp", printer: Printer) -> None:
        """打印 arch.get_dynamic_memory 自定义文本语法。"""

        printer.print_string(" ")
        printer.print_attribute(self.memory_space)
        printer.print_string(" : ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls: type["ArchGetDynamicMemoryOp"], parser: AttrParser) -> "ArchGetDynamicMemoryOp":
        """解析 arch.get_dynamic_memory 自定义文本语法。"""

        memory_space = parser.parse_attribute()
        if not isinstance(memory_space, NnMemorySpaceAttr):
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="arch.get_dynamic_memory memory_space must be #nn.space<...>",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        parser.parse_characters(":", f" in {cls.name}")
        return cls(memory_space, parser.parse_type())


@irdl_op_definition
class ArchBarrierOp(IRDLOperation):
    """描述一次 block 级 barrier。"""

    name = "arch.barrier"

    scope = attr_def(ArchScopeAttr)
    visibility = attr_def(ArrayAttr)

    def __init__(
        self: "ArchBarrierOp",
        scope: ArchScopeAttr,
        visibility: ArrayAttr[Attribute],
    ) -> None:
        """初始化 arch.barrier。


        功能说明:
        - 记录 barrier 的 scope 与 visibility。

        使用示例:
        - ArchBarrierOp(ArchScopeAttr.from_name("block"), ArrayAttr([...]))

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/test_arch.py
        - 功能实现: kernel_gen/dialect/arch.py
        """

        super().__init__(attributes={"scope": scope, "visibility": visibility})

    def verify_(self: "ArchBarrierOp") -> None:
        """校验 arch.barrier 输入约束。


        功能说明:
        - 校验 scope 必须是公开 `#arch.scope<...>` 成员之一。
        - 校验 visibility 为唯一且完整的 `[tsm, tlm]` 聚合可见域。

        使用示例:
        - ArchBarrierOp(...).verify()

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/test_arch.py
        - 功能实现: kernel_gen/dialect/arch.py
        """

        _verify_target_registry_support(self.name)
        self.scope.verify()
        _verify_barrier_visibility_attr(self.visibility)

    def print(self: "ArchBarrierOp", printer: Printer) -> None:
        """打印 arch.barrier 自定义文本语法。"""

        printer.print_string(" {scope = ")
        printer.print_attribute(self.scope)
        printer.print_string(", visibility = ")
        printer.print_attribute(self.visibility)
        printer.print_string("}")

    @classmethod
    def parse(cls: type["ArchBarrierOp"], parser: AttrParser) -> "ArchBarrierOp":
        """解析 arch.barrier 自定义文本语法。"""

        parser.parse_punctuation("{", "Expected '{' in arch.barrier.")
        if parser.parse_identifier("Expected `scope` in arch.barrier.") != "scope":
            _raise_verify_error("arch.barrier must print scope before visibility")
        parser.parse_punctuation("=", "Expected '=' after scope.")
        scope = parser.parse_attribute()
        parser.parse_punctuation(",", "Expected ',' between scope and visibility.")
        if parser.parse_identifier("Expected `visibility` in arch.barrier.") != "visibility":
            _raise_verify_error("arch.barrier must contain visibility attribute")
        parser.parse_punctuation("=", "Expected '=' after visibility.")
        visibility = parser.parse_attribute()
        parser.parse_punctuation("}", "Expected '}' at end of arch.barrier.")
        return cls(scope, visibility)


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
        - test: test/dialect/test_arch.py
        - 功能实现: kernel_gen/dialect/arch.py
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
        - test: test/dialect/test_arch.py
        - 功能实现: kernel_gen/dialect/arch.py
        """

        _verify_target_registry_support(self.name)
        _verify_launch_callee_attr(self.callee)

        for field_name in ("block", "thread", "subthread"):
            operand_value = SSAValue.get(getattr(self, field_name))
            operand_type = _verify_symbol_int_operand(operand_value, field_name, self.name)
            _verify_positive_static_symbol(operand_type, field_name, self.name)
        shared_memory_size = SSAValue.get(self.shared_memory_size)
        shared_memory_size_type = _verify_symbol_int_operand(shared_memory_size, "shared_memory_size", self.name)
        _verify_non_negative_static_symbol(shared_memory_size_type, "shared_memory_size", self.name)

    def print(self: "ArchLaunchOp", printer: Printer) -> None:
        """打印 arch.launch 自定义文本语法。"""

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
        """解析 arch.launch 自定义文本语法。"""

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
            _raise_verify_error("arch.launch result types must be ()")
        if len(arg_types) != len(args):
            _raise_verify_error("arch.launch arg type list must match operand count")
        for operand, operand_type in zip(args, arg_types, strict=True):
            if SSAValue.get(operand).type != operand_type:
                _raise_verify_error("arch.launch arg types must match operand types")
        return cls(callee, block, thread, subthread, shared_memory_size, args)


ArchLaunchKernelOp = ArchLaunchOp


Arch = Dialect(
    "arch",
    [
        ArchGetBlockIdOp,
        ArchGetBlockNumOp,
        ArchGetThreadIdOp,
        ArchGetThreadNumOp,
        ArchGetSubthreadIdOp,
        ArchGetSubthreadNumOp,
        ArchGetDynamicMemoryOp,
        ArchBarrierOp,
        ArchLaunchOp,
    ],
    [ArchScopeAttr, ArchVisibilityAttr],
)

__all__ = [
    "Arch",
    "ArchScopeAttr",
    "ArchVisibilityAttr",
    "ArchGetBlockIdOp",
    "ArchGetBlockNumOp",
    "ArchGetThreadIdOp",
    "ArchGetThreadNumOp",
    "ArchGetSubthreadIdOp",
    "ArchGetSubthreadNumOp",
    "ArchGetDynamicMemoryOp",
    "ArchBarrierOp",
    "ArchLaunchOp",
    "ArchLaunchKernelOp",
]
