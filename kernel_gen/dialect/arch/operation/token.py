"""arch token operations.

功能说明:
- 定义 arch.token、arch.sign 与 arch.wait op。

API 列表:
- `class ArchTokenOp(token_id: str | StringAttr, count: SSAValue | Operation)`
- `class ArchSignOp(event: SSAValue | Operation, count: SSAValue | Operation)`
- `class ArchWaitOp(event: SSAValue | Operation)`

使用示例:
- `from kernel_gen.dialect.arch.operation import ...`

关联文件:
- spec: spec/dialect/arch.md
- test: test/dialect/arch/
- 功能实现: kernel_gen/dialect/arch/operation/token.py
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
    _normalize_token_id,
    _raise_verify_error,
    _verify_non_negative_static_symbol,
    _verify_positive_static_symbol,
    _verify_symbol_int_operand,
    _verify_token_id_text,
)
from ..type import ArchTokenType


def _verify_token_operand(value: SSAValue, field_name: str) -> ArchTokenType:
    """校验 operand 为 `!arch.token<id>`。

    功能说明:
    - 返回已校验的 ArchTokenType。
    - 仅供当前 op 文件内 sign/wait verifier 复用，避免跨文件 import `arch.type.token` 私有 helper。

    使用示例:
    - token_type = _verify_token_operand(op.event, "event")

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/arch/test_arch.py
    - 功能实现: kernel_gen/dialect/arch/operation/token.py
    """

    if not isinstance(value.type, ArchTokenType):
        _raise_verify_error(f"arch token {field_name} must be !arch.token<id>")
    value.type.verify()
    return value.type

@irdl_op_definition
class ArchTokenOp(IRDLOperation):
    """创建 arch event token。"""

    name = "arch.token"

    count = operand_def(SymbolValueType)
    token_id = attr_def(StringAttr, attr_name="id")
    result = result_def(ArchTokenType)

    def __init__(self: "ArchTokenOp", token_id: str | StringAttr, count: SSAValue | Operation) -> None:
        """初始化 arch.token。

        功能说明:
        - 根据公开 token id 与初始 count 创建 event token。

        使用示例:
        - ArchTokenOp("event0", count)

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/arch/test_arch.py
        - 功能实现: kernel_gen/dialect/arch/
        """

        id_attr = _normalize_token_id(token_id)
        super().__init__(
            operands=[count],
            result_types=[ArchTokenType(id_attr)],
            attributes={"id": id_attr},
        )

    def verify_(self: "ArchTokenOp") -> None:
        """校验 arch.token。

        功能说明:
        - id attr 必须非空且与 result token id 一致。
        - count 必须是 `!symbol.int`，静态可判定时必须非负。

        使用示例:
        - ArchTokenOp("event0", count).verify_()

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/arch/test_arch.py
        - 功能实现: kernel_gen/dialect/arch/
        """

        _verify_token_id_text(self.token_id.data)
        count_type = _verify_symbol_int_operand(self.count, "count", self.name)
        _verify_non_negative_static_symbol(count_type, "count", self.name)
        if not isinstance(self.result.type, ArchTokenType):
            _raise_verify_error("arch.token result must be !arch.token<id>")
        self.result.type.verify()
        if self.result.type.token_id.data != self.token_id.data:
            _raise_verify_error("arch.token result token id must match id attr")


@irdl_op_definition
class ArchSignOp(IRDLOperation):
    """发送 arch event token 信号。"""

    name = "arch.sign"

    event = operand_def(ArchTokenType)
    count = operand_def(SymbolValueType)

    def __init__(self: "ArchSignOp", event: SSAValue | Operation, count: SSAValue | Operation) -> None:
        """初始化 arch.sign。

        功能说明:
        - 对 event token 发送指定 count 的信号。

        使用示例:
        - ArchSignOp(event, count)

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/arch/test_arch.py
        - 功能实现: kernel_gen/dialect/arch/
        """

        super().__init__(operands=[event, count])

    def verify_(self: "ArchSignOp") -> None:
        """校验 arch.sign。

        功能说明:
        - event 必须为 arch token；count 必须是 `!symbol.int`，静态可判定时必须为正。

        使用示例:
        - ArchSignOp(event, count).verify_()

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/arch/test_arch.py
        - 功能实现: kernel_gen/dialect/arch/
        """

        _verify_token_operand(self.event, "event")
        count_type = _verify_symbol_int_operand(self.count, "count", self.name)
        _verify_positive_static_symbol(count_type, "count", self.name)


@irdl_op_definition
class ArchWaitOp(IRDLOperation):
    """等待 arch event token。"""

    name = "arch.wait"

    event = operand_def(ArchTokenType)

    def __init__(self: "ArchWaitOp", event: SSAValue | Operation) -> None:
        """初始化 arch.wait。

        功能说明:
        - 等待 event token 达到可继续条件。

        使用示例:
        - ArchWaitOp(event)

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/arch/test_arch.py
        - 功能实现: kernel_gen/dialect/arch/
        """

        super().__init__(operands=[event])

    def verify_(self: "ArchWaitOp") -> None:
        """校验 arch.wait。

        功能说明:
        - event 必须为 arch token。

        使用示例:
        - ArchWaitOp(event).verify_()

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/arch/test_arch.py
        - 功能实现: kernel_gen/dialect/arch/
        """

        _verify_token_operand(self.event, "event")

__all__ = ["ArchTokenOp", "ArchSignOp", "ArchWaitOp"]
