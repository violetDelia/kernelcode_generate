"""arch barrier operation.

功能说明:
- 定义 arch.barrier op。

API 列表:
- `class ArchBarrierOp(scope: ArchScopeAttr, visibility: ArrayAttr[Attribute])`

使用示例:
- `from kernel_gen.dialect.arch.operation import ...`

关联文件:
- spec: spec/dialect/arch.md
- test: test/dialect/arch/
- 功能实现: kernel_gen/dialect/arch/operation/barrier.py
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

from ..attr import ArchScopeAttr

from kernel_gen.target import registry as target_registry

# Localized helpers from retired package-internal modules.

_ERROR_SCENE = "dialect.arch verifier"

_BARRIER_VISIBLE_SPACES = {"tsm", "tlm"}

def _verify_barrier_visibility_attr(visibility: Attribute) -> ArrayAttr[Attribute]:
    """校验 barrier visibility 列表。


    功能说明:
    - visibility 必须是非空 `ArrayAttr`。
    - 元素必须唯一，且必须且只能包含 `#arch.visibility<tsm>` 与 `#arch.visibility<tlm>`。

    使用示例:
    - _verify_barrier_visibility_attr(ArrayAttr([...]))

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/arch/test_arch.py
    - 功能实现: kernel_gen/dialect/arch/
    """

    from ..attr.visibility import ArchVisibilityAttr

    if not isinstance(visibility, ArrayAttr):
        raise_verify_error(_ERROR_SCENE, "arch.barrier visibility must be ArrayAttr")
    if not visibility.data:
        raise_verify_error(_ERROR_SCENE, "arch.barrier visibility must not be empty")
    seen: set[str] = set()
    for entry in visibility.data:
        if not isinstance(entry, ArchVisibilityAttr):
            raise_verify_error(_ERROR_SCENE, "arch.barrier visibility items must be #arch.visibility<...>")
        space_name = entry.visibility.data
        if space_name in seen:
            raise_verify_error(_ERROR_SCENE, "arch.barrier visibility must not contain duplicates")
        seen.add(space_name)
        if space_name not in _BARRIER_VISIBLE_SPACES:
            raise_verify_error(_ERROR_SCENE, "arch.barrier visibility must contain only #arch.visibility<tsm>/#arch.visibility<tlm>")
    if seen != _BARRIER_VISIBLE_SPACES:
        raise_verify_error(_ERROR_SCENE, "arch.barrier visibility must contain both #arch.visibility<tsm> and #arch.visibility<tlm>")
    return visibility

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
        - test: test/dialect/arch/test_arch.py
        - 功能实现: kernel_gen/dialect/arch/
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
        - test: test/dialect/arch/test_arch.py
        - 功能实现: kernel_gen/dialect/arch/
        """

        _verify_target_registry_support(self.name)
        self.scope.verify()
        _verify_barrier_visibility_attr(self.visibility)

    def print(self: "ArchBarrierOp", printer: Printer) -> None:
        """打印 arch.barrier 自定义文本语法。

        功能说明:
        - 按 `{scope = ..., visibility = ...}` 格式输出 barrier 属性。

        使用示例:
        - ArchBarrierOp(scope, visibility).print(printer)
        """

        printer.print_string(" {scope = ")
        printer.print_attribute(self.scope)
        printer.print_string(", visibility = ")
        printer.print_attribute(self.visibility)
        printer.print_string("}")

    @classmethod
    def parse(cls: type["ArchBarrierOp"], parser: AttrParser) -> "ArchBarrierOp":
        """解析 arch.barrier 自定义文本语法。

        功能说明:
        - 读取 `scope` 与 `visibility` 属性并构造 `ArchBarrierOp`。

        使用示例:
        - ArchBarrierOp.parse(parser)
        """

        parser.parse_punctuation("{", "Expected '{' in arch.barrier.")
        if parser.parse_identifier("Expected `scope` in arch.barrier.") != "scope":
            raise_verify_error(_ERROR_SCENE, "arch.barrier must print scope before visibility")
        parser.parse_punctuation("=", "Expected '=' after scope.")
        scope = parser.parse_attribute()
        parser.parse_punctuation(",", "Expected ',' between scope and visibility.")
        if parser.parse_identifier("Expected `visibility` in arch.barrier.") != "visibility":
            raise_verify_error(_ERROR_SCENE, "arch.barrier must contain visibility attribute")
        parser.parse_punctuation("=", "Expected '=' after visibility.")
        visibility = parser.parse_attribute()
        parser.parse_punctuation("}", "Expected '}' at end of arch.barrier.")
        return cls(scope, visibility)

__all__ = ["ArchBarrierOp"]
