"""arch package-internal helpers.

功能说明:
- 承载 arch package 内 verifier、动态 memory 与 target registry 共享 helper。

API 列表:
- 包内 API `_raise_verify_error(expected: str, *, actual: str = ERROR_ACTUAL) -> None`
- 包内 API `_verify_symbol_int_operand(value: SSAValue, field_name: str, op_name: str) -> SymbolValueType`
- 包内 API `_verify_positive_static_symbol(operand_type: SymbolValueType, field_name: str, op_name: str) -> None`
- 包内 API `_verify_non_negative_static_symbol(operand_type: SymbolValueType, field_name: str, op_name: str) -> None`
- 包内 API `_verify_launch_callee_attr(callee: Attribute) -> SymbolRefAttr`
- 包内 API `_verify_barrier_visibility_attr(visibility: Attribute) -> ArrayAttr[Attribute]`
- 包内 API `_normalize_token_id(token_id: str | StringAttr) -> StringAttr`
- 包内 API `_verify_token_id_text(token_id: str) -> None`
- 包内 API `_dynamic_memory_result_type(space: NnMemorySpaceAttr) -> NnMemoryType`
- 包内 API `_is_positive_static_capacity(attr: SymbolExprAttr) -> bool`
- 包内 API `_verify_target_registry_support(op_name: str) -> None`

使用示例:
- `from kernel_gen.dialect.arch import ...`

关联文件:
- spec: spec/dialect/arch.md
- test: test/dialect/arch/
- 功能实现: kernel_gen/dialect/arch/common.py
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
from kernel_gen.target import registry as target_registry


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
    - test: test/dialect/arch/test_arch.py
    - 功能实现: kernel_gen/dialect/arch/
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
        raise VerifyException(
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
    - test: test/dialect/arch/test_arch.py
    - 功能实现: kernel_gen/dialect/arch/
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
    - test: test/dialect/arch/test_arch.py
    - 功能实现: kernel_gen/dialect/arch/
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
    - test: test/dialect/arch/test_arch.py
    - 功能实现: kernel_gen/dialect/arch/
    """

    from .attr.visibility import ArchVisibilityAttr

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
    - 功能实现: kernel_gen/dialect/arch/common.py
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
    - 功能实现: kernel_gen/dialect/arch/common.py
    """

    if not token_id:
        _raise_verify_error("arch token id must not be empty")
    if not token_id.replace("_", "").isalnum() or token_id[0].isdigit():
        _raise_verify_error("arch token id must be an identifier")


def _dynamic_memory_result_type(space: NnMemorySpaceAttr) -> NnMemoryType:
    """构造动态 memory 入口的固定结果类型。


    功能说明:
    - 返回 `!nn.memory<[#symbol.expr<<SPACE>_SIZE>], [#symbol.expr<1>], i8, #nn.space<space>>`。

    使用示例:
    - _dynamic_memory_result_type(NnMemorySpaceAttr.from_name("shared"))

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/arch/test_arch.py
    - 功能实现: kernel_gen/dialect/arch/
    """

    return NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr(_DYNAMIC_MEMORY_CAPACITY_SYMBOLS.get(space.space.data, "?"))]),
        ArrayAttr([SymbolExprAttr.from_expr("1")]),
        i8,
        space,
    )


def _is_positive_static_capacity(attr: SymbolExprAttr) -> bool:
    """判断 dynamic memory shape 是否为正静态容量。

    功能说明:
    - 允许 attach-arch-information pass 将 named capacity 特化为静态字节数。
    - 仅接受正整数，避免把任意符号 shape 误当作 target 特化结果。

    使用示例:
    - if _is_positive_static_capacity(shape_attr): ...

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/arch/test_arch.py
    - 功能实现: kernel_gen/dialect/arch/
    """

    value = SymbolValueType(attr).get_value()
    return isinstance(value, int) and value > 0


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

__all__ = [
    "_raise_verify_error",
    "_verify_symbol_int_operand",
    "_verify_positive_static_symbol",
    "_verify_non_negative_static_symbol",
    "_verify_launch_callee_attr",
    "_verify_barrier_visibility_attr",
    "_normalize_token_id",
    "_verify_token_id_text",
    "_dynamic_memory_result_type",
    "_is_positive_static_capacity",
    "_verify_target_registry_support",
]
