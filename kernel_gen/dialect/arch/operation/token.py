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

from ..type import ArchTokenType

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

def _normalize_token_id(token_id: str | StringAttr) -> StringAttr:
    """规整 arch token id 参数。

    功能说明:
    - 将公开构造参数 `str | StringAttr` 统一为 `StringAttr`。
    - 作为 arch 包内 API 供 token type/op 共享，不从 `arch.type.token` 跨文件导入私有对象。

    使用示例:
    - attr = _normalize_token_id("event0")

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/arch/test_arch.py
    - 功能实现: kernel_gen/dialect/arch/operation/token.py
    """

    if isinstance(token_id, StringAttr):
        return token_id
    if isinstance(token_id, str):
        return StringAttr(token_id)
    raise TypeError("arch token id must be str or StringAttr")

def _verify_token_id_text(token_id: str) -> None:
    """校验 arch token id 文本。

    功能说明:
    - token id 必须是非空标识符，作为 `!arch.token<id>` 的稳定文本。
    - 作为 arch 包内 API 统一 token type/op 的错误语义。

    使用示例:
    - _verify_token_id_text("event0")

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/arch/test_arch.py
    - 功能实现: kernel_gen/dialect/arch/operation/token.py
    """

    has_text = bool(token_id)
    if not has_text:
        raise_verify_error(_ERROR_SCENE, "arch token id must not be empty")
    identifier_body = token_id.replace("_", "")
    starts_with_digit = token_id[0].isdigit()
    if not identifier_body.isalnum() or starts_with_digit:
        raise_verify_error(_ERROR_SCENE, "arch token id must be an identifier")



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

    token_type = value.type
    if not isinstance(token_type, ArchTokenType):
        raise_verify_error(_ERROR_SCENE, f"arch token {field_name} must be !arch.token<id>")
    token_type.verify()
    return token_type

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
            raise_verify_error(_ERROR_SCENE, "arch.token result must be !arch.token<id>")
        self.result.type.verify()
        if self.result.type.token_id.data != self.token_id.data:
            raise_verify_error(_ERROR_SCENE, "arch.token result token id must match id attr")


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
