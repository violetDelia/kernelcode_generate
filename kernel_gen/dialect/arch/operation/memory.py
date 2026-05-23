"""arch dynamic memory operation.

功能说明:
- 定义 arch.get_dynamic_memory op。

API 列表:
- `class ArchGetDynamicMemoryOp(memory_space: NnMemorySpaceAttr, result_type: Attribute | None = None)`

使用示例:
- `from kernel_gen.dialect.arch.operation import ...`

关联文件:
- spec: spec/dialect/arch.md
- test: test/dialect/arch/
- 功能实现: kernel_gen/dialect/arch/operation/memory.py
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar

from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE
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
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr, SymbolValueType
from kernel_gen.target import registry

from ..common import (
    _dynamic_memory_result_type,
    _is_positive_static_capacity,
    _raise_verify_error,
    _verify_symbol_int_operand,
    _verify_target_registry_support,
)

_DYNAMIC_MEMORY_SPACES = {"shared", "local", "tsm", "tlm1", "tlm2", "tlm3"}
_DYNAMIC_MEMORY_CAPACITY_SYMBOLS = {
    "shared": "SM_SIZE",
    "local": "LM_SIZE",
    "tsm": "TSM_SIZE",
    "tlm1": "TLM1_SIZE",
    "tlm2": "TLM2_SIZE",
    "tlm3": "TLM3_SIZE",
}
_DYNAMIC_MEMORY_STATIC_CAPACITY_SPACES = {"tsm", "tlm1", "tlm2", "tlm3"}
_ERROR_SCENE = "dialect.arch verifier"

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
        - test: test/dialect/arch/test_arch.py
        - 功能实现: kernel_gen/dialect/arch/
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
        - test: test/dialect/arch/test_arch.py
        - 功能实现: kernel_gen/dialect/arch/
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
        expected_capacity = _DYNAMIC_MEMORY_CAPACITY_SYMBOLS[space_name]
        result_shape = result_type.shape.data[0]
        is_named_capacity = result_shape == SymbolExprAttr.from_expr(expected_capacity)
        is_static_capacity = space_name in _DYNAMIC_MEMORY_STATIC_CAPACITY_SPACES and _is_positive_static_capacity(result_shape)
        if not is_named_capacity and not is_static_capacity:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected=(
                        "arch.get_dynamic_memory result shape must be "
                        f"[#symbol.expr<{expected_capacity}>] or positive static capacity"
                    ),
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if result_type.stride.data[0] != SymbolExprAttr.from_expr("1"):
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="arch.get_dynamic_memory result stride must be [#symbol.expr<1>]",
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
        """打印 arch.get_dynamic_memory 自定义文本语法。

        功能说明:
        - 输出 memory space 与推导出的 dynamic memory result type。

        使用示例:
        - ArchGetDynamicMemoryOp(space).print(printer)
        """

        printer.print_string(" ")
        printer.print_attribute(self.memory_space)
        printer.print_string(" : ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls: type["ArchGetDynamicMemoryOp"], parser: AttrParser) -> "ArchGetDynamicMemoryOp":
        """解析 arch.get_dynamic_memory 自定义文本语法。

        功能说明:
        - 读取 memory space 和 result type 并构造 dynamic memory op。

        使用示例:
        - ArchGetDynamicMemoryOp.parse(parser)
        """

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

__all__ = ["ArchGetDynamicMemoryOp"]
