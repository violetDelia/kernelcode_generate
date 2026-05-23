"""symbol package-internal common helpers.

功能说明:
- 承载 symbol package 内错误格式化与 ptr template helper。

API 列表:
- 包内实现模块，无 root 公开 API。

使用示例:
- `from kernel_gen.dialect.symbol import ...`

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/symbol/
- 功能实现: kernel_gen/dialect/symbol/common.py
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE
from xdsl.dialects import arith
from xdsl.dialects.builtin import BFloat16Type, Float16Type, Float32Type, Float64Type, IntAttr, IntegerAttr, IntegerType, StringAttr, f32, f64, i1, i32
from xdsl.dialect_interfaces.constant_materialization import ConstantMaterializationInterface
from xdsl.ir import Attribute, Block, Dialect, Operation, ParametrizedAttribute, Region, SSAValue, TypeAttribute
from xdsl.irdl import (
    IRDLOperation,
    attr_def,
    irdl_attr_definition,
    irdl_op_definition,
    opt_operand_def,
    opt_result_def,
    operand_def,
    param_def,
    region_def,
    result_def,
    traits_def,
    var_operand_def,
)
from xdsl.interfaces import HasFolderInterface
from xdsl.parser import AttrParser
from xdsl.printer import Printer
from xdsl.traits import IsTerminator, NoTerminator, Pure
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import NnMemoryType


_SYMBOL_PTR_TEMPLATE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ERROR_SCENE = "dialect.symbol"


def _format_error(expected: str, actual: str = ERROR_ACTUAL) -> str:
    """格式化 symbol dialect 统一错误文本。

    功能说明:
    - 复用核心错误模板生成 verifier、value error 与 type error 的稳定文本。

    使用示例:
    - message = _format_error("symbol value type expected")
    """

    return ERROR_TEMPLATE.format(
        scene=_ERROR_SCENE,
        expected=expected,
        actual=actual,
        action=ERROR_ACTION,
    )


def _raise_verify_error(expected: str, *, actual: str = ERROR_ACTUAL) -> None:
    """统一抛出 symbol dialect verifier 错误。

    功能说明:
    - 将 symbol verifier 失败收敛为 `VerifyException` 和稳定错误模板。

    使用示例:
    - _raise_verify_error("symbol operand expected")
    """

    raise VerifyException(_format_error(expected, actual))


def _raise_value_error(expected: str, *, actual: str = ERROR_ACTUAL) -> None:
    """统一抛出 symbol dialect value error。

    功能说明:
    - 将 symbol 参数值错误收敛为 `ValueError` 和稳定错误模板。

    使用示例:
    - _raise_value_error("non-empty expression expected")
    """

    raise ValueError(_format_error(expected, actual))


def _raise_type_error(expected: str, *, actual: str = ERROR_ACTUAL) -> None:
    """统一抛出 symbol dialect type error。

    功能说明:
    - 将 symbol 参数类型错误收敛为 `TypeError` 和稳定错误模板。

    使用示例:
    - _raise_type_error("StringAttr expected")
    """

    raise TypeError(_format_error(expected, actual))


def _normalize_symbol_ptr_template_name(template_name: StringAttr | str | None) -> StringAttr:
    """规整 symbol.ptr template name 参数。

    功能说明:
    - 把公开构造参数 `str | StringAttr | None` 统一为 `StringAttr`。

    使用示例:
    - attr = _normalize_symbol_ptr_template_name("T")
    """

    if template_name is None:
        return StringAttr("")
    if isinstance(template_name, StringAttr):
        return template_name
    if isinstance(template_name, str):
        return StringAttr(template_name)
    _raise_type_error("symbol.ptr template_name must be str, StringAttr or None")


def _verify_symbol_ptr_template_name(template_name: str) -> None:
    """校验 symbol.ptr template name 文本。

    功能说明:
    - 空字符串表示未携带 template name。
    - 非空时必须是公开 identifier 文本。

    使用示例:
    - _verify_symbol_ptr_template_name("T")
    """

    if template_name == "":
        return
    if _SYMBOL_PTR_TEMPLATE_PATTERN.fullmatch(template_name) is None:
        _raise_verify_error("symbol.ptr template_name must be an identifier")

__all__ = ["_format_error", "_raise_verify_error", "_raise_value_error", "_raise_type_error", "_normalize_symbol_ptr_template_name", "_verify_symbol_ptr_template_name"]
