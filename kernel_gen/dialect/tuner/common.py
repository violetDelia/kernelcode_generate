"""tuner package-internal helpers.

功能说明:
- 承载 tuner package 内 verifier 和 pattern attr helper。

API 列表:
- 包内实现模块，无 root 公开 API。

使用示例:
- `from kernel_gen.dialect.tuner import ...`

关联文件:
- spec: spec/dialect/tuner.md
- test: test/dialect/tuner/
- 功能实现: kernel_gen/dialect/tuner/common.py
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
    - test: test/dialect/tuner/test_tuner.py
    - 功能实现: kernel_gen/dialect/tuner/
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
    - test: test/dialect/tuner/test_tuner.py
    - 功能实现: kernel_gen/dialect/tuner/
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
    - test: test/dialect/tuner/test_tuner.py
    - 功能实现: kernel_gen/dialect/tuner/
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
    - test: test/dialect/tuner/test_tuner.py
    - 功能实现: kernel_gen/dialect/tuner/
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
    - test: test/dialect/tuner/test_tuner.py
    - 功能实现: kernel_gen/dialect/tuner/
    """

    if isinstance(value, str):
        return SymbolRefAttr(value)
    if isinstance(value, SymbolRefAttr):
        return value
    if op_name == "tuner.select":
        _raise_verify_error("tuner.select patterns must be non-empty ArrayAttr[SymbolRefAttr]")
    _raise_verify_error(f"{op_name} callee must be SymbolRefAttr")

__all__ = [
    "_raise_verify_error",
    "_verify_symbol_value_result_type",
    "_verify_pattern_id_result_type",
    "_verify_symbol_ref_attr",
    "_pattern_symbol_attr",
]
