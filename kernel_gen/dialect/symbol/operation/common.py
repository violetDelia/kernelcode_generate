"""symbol operation helpers.

功能说明:
- 承载 symbol operation package 内 verifier、fold 和 result inference helper。

API 列表:
- 包内实现模块，无 root 公开 API。

使用示例:
- `from kernel_gen.dialect.symbol.operation import ...`

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/symbol/
- 功能实现: kernel_gen/dialect/symbol/operation/common.py
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

from ..common import _format_error, _raise_verify_error
from ..expr.parser import (_SymbolExprNode, _SymbolExprToken, _SymbolExprParserBase, _SymbolExprTextParser, _SymbolExprAttrParser, _tokenize_symbol_expr, _make_symbol_expr_const, _make_symbol_expr_symbol, _make_symbol_expr_unknown, _is_symbol_expr_unknown, _contains_symbol_expr_unknown, _contains_symbol_expr_iter, _make_symbol_expr_iter, _get_symbol_expr_const, _get_concrete_symbol_expr_node_value, _linear_symbol_expr_terms, _make_symbol_expr_neg, _make_symbol_expr_add, _make_symbol_expr_sub, _make_symbol_expr_mul, _make_symbol_expr_keyword_binary, _make_symbol_expr_min, _make_symbol_expr_max, _symbol_expr_precedence, _format_symbol_expr_node, _format_symbol_expr_add, _parse_symbol_expr_from_text, _parse_symbol_expr_from_attr_parser, _normalize_expr, _evaluate_concrete_expr, _canonicalize_symbolic_expr, _is_supported_symbol_expr, _unwrap_symbol_expr_attr_text)
from ..attr import SymbolExprAttr
from ..type import SymbolIterType, SymbolValueType

_UNKNOWN_SYMBOL_EXPR = "?"

def _verify_axis(axis: Attribute, rank: int, op_name: str) -> int:
    """校验 axis attribute 并返回轴号。


    功能说明:
    - 统一校验 `symbol.get_dim/get_stride` 的静态整数轴号约束。

    使用示例:
    - _verify_axis(IntAttr(0), 2, "symbol.get_dim")

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/symbol/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol/
    """

    if not isinstance(axis, IntAttr):
        _raise_verify_error(f"{op_name} axis must be a static integer")
    if axis.data < 0 or axis.data >= rank:
        _raise_verify_error(f"{op_name} axis out of range")
    return axis.data


def _entry_to_expr(entry: Attribute, op_name: str, field_name: str) -> str:
    """将 memory 元信息条目转换为 symbol 表达。


    功能说明:
    - 将 `NnMemoryType` 中的 `shape/stride` 条目收敛为 `!symbol.int<#symbol.expr<...>>` 所需字符串。
    - 只接受当前 memory layout 合同中的 `SymbolExprAttr`。

    使用示例:
    - _entry_to_expr(SymbolExprAttr.from_expr("4"), "symbol.get_dim", "shape")

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/symbol/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol/
    """

    if isinstance(entry, SymbolExprAttr):
        return entry.expr.data
    _raise_verify_error(f"{op_name} {field_name} entry must be SymbolExprAttr")


def _infer_result_type(
    source: SSAValue | Operation,
    axis: Attribute,
    op_name: str,
    field_name: str,
) -> SymbolValueType:
    """根据 memory type 推导查询 op 的结果类型。


    功能说明:
    - 从 `NnMemoryType` 的 `shape/stride` 中读取真实条目，并推导 `SymbolValueType`。
    - 当 source/axis 非法时返回占位类型，交由 verifier 报出正式错误。

    使用示例:
    - _infer_result_type(source, IntAttr(0), "symbol.get_dim", "shape")

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/symbol/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol/
    """

    fallback = SymbolValueType.from_expr("0")
    source_value = SSAValue.get(source)
    if not isinstance(source_value.type, NnMemoryType):
        return fallback
    entries = source_value.type.shape.data if field_name == "shape" else source_value.type.stride.data
    if not isinstance(axis, IntAttr) or axis.data < 0 or axis.data >= len(entries):
        return fallback
    try:
        return SymbolValueType.from_expr(_entry_to_expr(entries[axis.data], op_name, field_name))
    except VerifyException:
        return fallback


def _is_symbol_int_type(attr: Attribute) -> bool:
    """判断 attribute 是否为 symbol.int 类型。


    功能说明:
    - 为 `symbol.for` 与 `symbol.get_*` verifier 复用统一的 symbol 类型判断。

    使用示例:
    - _is_symbol_int_type(SymbolValueType.from_expr("N"))

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/symbol/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol/
    """

    return isinstance(attr, SymbolValueType)


def _is_symbol_arith_operand_type(attr: Attribute) -> bool:
    """判断 attribute 是否可作为 symbol 算术/比较 operand。

    功能说明:
    - symbol 算术允许 `!symbol.int` 与 loop-carried `!symbol.iter`，供 tail `min(tile, dim - idx)` 使用。

    使用示例:
    - ok = _is_symbol_arith_operand_type(SymbolValueType.from_expr("N"))
    """

    return isinstance(attr, (SymbolValueType, SymbolIterType))


def _is_unknown_symbol_int_type(attr: Attribute) -> bool:
    """判断 `!symbol.int<#symbol.expr<??>>` unknown 类型。

    功能说明:
    - 只在 symbol dialect 当前文件内服务 verifier 与 fold 边界。
    - unknown 是保守值语义，不等同具名符号表达。

    使用示例:
    - _is_unknown_symbol_int_type(SymbolValueType.from_expr("?"))
    """

    return isinstance(attr, SymbolValueType) and attr.get_value() == _UNKNOWN_SYMBOL_EXPR


def _parse_symbol_binary_operand_types(parser: AttrParser, op_name: str) -> tuple[Attribute, Attribute]:
    """解析 symbol 二元 op 的 operand type 列表。

    功能说明:
    - 支持当前 printer 输出的 `lhs_type, rhs_type`。
    - 兼容 MLIR 常见的 parenthesized 形式 `(lhs_type, rhs_type)`。

    使用示例:
    - lhs_type, rhs_type = _parse_symbol_binary_operand_types(parser, "symbol.eq")
    """

    if parser.parse_optional_punctuation("(") is not None:
        lhs_type = parser.parse_type()
        parser.parse_characters(",", f" in {op_name} type list")
        rhs_type = parser.parse_type()
        parser.parse_punctuation(")", f" in {op_name} type list")
        return lhs_type, rhs_type
    lhs_type = parser.parse_type()
    parser.parse_characters(",", f" in {op_name} type list")
    rhs_type = parser.parse_type()
    return lhs_type, rhs_type


def _symbol_iter_type_expr_node(attr: SymbolIterType) -> _SymbolExprNode:
    """从 `SymbolIterType` 构造公开 `iter<start,end,step>` token。

    功能说明:
    - 只读取 `SymbolIterType` 的公开 start/end/step 参数。
    - 不依赖 SSA 名称、`name_hint`、block argument 或运行时 dump 文本。

    使用示例:
    - node = _symbol_iter_type_expr_node(SymbolIterType.from_bounds("0", "N", "TILE"))
    """

    return _make_symbol_expr_iter(
        _parse_symbol_expr_from_text(attr.start.expr.data),
        _parse_symbol_expr_from_text(attr.end.expr.data),
        _parse_symbol_expr_from_text(attr.step.expr.data),
    )


def _symbol_arith_operand_expr_node(attr: Attribute) -> _SymbolExprNode | None:
    """提取 symbol 算术 operand 的值语义表达节点。

    功能说明:
    - `SymbolValueType` 直接读取其 `SymbolExprAttr`。
    - `SymbolIterType` 转换为公开 `iter<start,end,step>` token。
    - 非 symbol 算术 operand 返回 `None`，由 verifier 负责报错。

    使用示例:
    - node = _symbol_arith_operand_expr_node(value.type)
    """

    if isinstance(attr, SymbolValueType):
        return _parse_symbol_expr_from_text(attr.expr.expr.data)
    if isinstance(attr, SymbolIterType):
        return _symbol_iter_type_expr_node(attr)
    return None


def _symbol_arith_operand_contains_unknown(attr: Attribute) -> bool | None:
    """从公开类型文本快速判断 symbol 算术 operand 是否含 unknown。

    功能说明:
    - `verify_` 的 unknown 传播只需要判断 `?` 是否存在，不需要重建完整表达式 AST。
    - 避免大尺寸动态 kernel IR 在验证阶段重复解析同一 canonical 表达式。

    使用示例:
    - has_unknown = _symbol_arith_operand_contains_unknown(value.type)

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/symbol/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol/
    """

    if isinstance(attr, SymbolValueType):
        return _UNKNOWN_SYMBOL_EXPR in attr.expr.expr.data
    if isinstance(attr, SymbolIterType):
        return any(
            _UNKNOWN_SYMBOL_EXPR in expr.expr.data
            for expr in (attr.start, attr.end, attr.step)
        )
    return None


def _symbol_expr_bounds_are_full_tiles(start: _SymbolExprNode, end: _SymbolExprNode, step: _SymbolExprNode) -> bool:
    """判断 `start -> end step step` 是否静态可证为 full-tile。

    功能说明:
    - 对 `B -> B + 24 step 8` 与 `B -> B + 3*S step S` 这类一阶表达做当前文件内结构化证明。
    - `iter<...>`、`?`、`min/max` 或非线性表达一律保守返回 `False`，避免 full-tile fold 依赖外部化简器状态。

    使用示例:
    - if _symbol_expr_bounds_are_full_tiles(start, end, step): ...

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/symbol/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol/
    """

    start_linear = _linear_symbol_expr_terms(start)
    end_linear = _linear_symbol_expr_terms(end)
    if start_linear is None or end_linear is None:
        return False
    start_terms, start_offset = start_linear
    end_terms, end_offset = end_linear
    diff_terms = dict(end_terms)
    for name, coeff in start_terms.items():
        diff_terms[name] = diff_terms.get(name, 0) - coeff
    distance = end_offset - start_offset
    step_value = _get_concrete_symbol_expr_node_value(step)
    if step_value is not None:
        if step_value == 0 or any(coeff != 0 for coeff in diff_terms.values()):
            return False
        return distance > 0 and distance % step_value == 0

    step_linear = _linear_symbol_expr_terms(step)
    if step_linear is None:
        return False
    step_terms, step_offset = step_linear
    return _linear_distance_is_positive_multiple(diff_terms, distance, step_terms, step_offset)


def _linear_distance_is_positive_multiple(
    diff_terms: dict[str, int],
    diff_offset: int,
    step_terms: dict[str, int],
    step_offset: int,
) -> bool:
    """判断线性距离是否为 step 线性表达的正整数倍。

    功能说明:
    - 为 full-tile `symbol.min` 提供 `B -> B + 3*S step S` 与 `0 -> 5*N step N`
      这类动态 step 的当前文件内结构化证明。
    - 只接受同一组 symbol coefficient 的正整数倍，不调用外部符号化简器。

    使用示例:
    - _linear_distance_is_positive_multiple({"S": 3}, 0, {"S": 1}, 0)

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/symbol/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol/
    """

    if not step_terms and step_offset == 0:
        return False

    ratios: list[int] = []
    for name in set(diff_terms) | set(step_terms):
        step_coeff = step_terms.get(name, 0)
        diff_coeff = diff_terms.get(name, 0)
        if step_coeff == 0:
            if diff_coeff != 0:
                return False
            continue
        quotient, remainder = divmod(diff_coeff, step_coeff)
        if remainder != 0:
            return False
        ratios.append(quotient)

    if step_offset != 0:
        quotient, remainder = divmod(diff_offset, step_offset)
        if remainder != 0:
            return False
        ratios.append(quotient)
    elif diff_offset != 0:
        return False

    if not ratios:
        return False
    first = ratios[0]
    return first > 0 and all(ratio == first for ratio in ratios)


def _symbol_expr_full_tile_residual_step(residual: _SymbolExprNode) -> _SymbolExprNode | None:
    """匹配 full-tile tail residual 的 step 表达。

    功能说明:
    - 匹配 `end - iter<start,end,step>`。
    - 只有 `(end-start)` 可证为 `step` 的正整数倍时返回 `step`。

    使用示例:
    - step = _symbol_expr_full_tile_residual_step(residual)

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/symbol/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol/
    """

    if residual.kind != "sub":
        return None
    end_node, iter_node = residual.args
    if iter_node.kind != "iter":
        return None
    start, end, step = iter_node.args
    if end_node != end:
        return None
    if not _symbol_expr_bounds_are_full_tiles(start, end, step):
        return None
    return step


def _symbol_expr_full_tile_min_step(lhs: _SymbolExprNode, rhs: _SymbolExprNode) -> _SymbolExprNode | None:
    """匹配 full-tile `symbol.min` 可折叠的 step 表达。

    功能说明:
    - 仅接受 `min(step, end - iter<start,end,step>)` 或交换 operand 的等价形式。
    - 非 full-tile、无法证明整除或 step 不一致时返回 `None`。

    使用示例:
    - step = _symbol_expr_full_tile_min_step(lhs, rhs)

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/symbol/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol/
    """

    rhs_step = _symbol_expr_full_tile_residual_step(rhs)
    if rhs_step is not None and lhs == rhs_step:
        return lhs
    lhs_step = _symbol_expr_full_tile_residual_step(lhs)
    if lhs_step is not None and rhs == lhs_step:
        return rhs
    return None


def _symbol_min_full_tile_step_value(lhs: SSAValue, rhs: SSAValue) -> SSAValue | None:
    """匹配 full-tile `symbol.min` 并返回应保留的 step SSA。

    功能说明:
    - 根据 operand type 的公开表达判断，不依赖 SSA 名称。
    - 仅供 `symbol.min` verifier / fold 共享 full-tile 识别。

    使用示例:
    - step_value = _symbol_min_full_tile_step_value(op.lhs, op.rhs)

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/symbol/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol/
    """

    lhs_node = _symbol_arith_operand_expr_node(lhs.type)
    rhs_node = _symbol_arith_operand_expr_node(rhs.type)
    if lhs_node is None or rhs_node is None:
        return None
    rhs_step = _symbol_expr_full_tile_residual_step(rhs_node)
    if rhs_step is not None and lhs_node == rhs_step:
        return lhs
    lhs_step = _symbol_expr_full_tile_residual_step(lhs_node)
    if lhs_step is not None and rhs_node == lhs_step:
        return rhs
    return None


def _requires_unknown_arith_result(lhs_type: Attribute, rhs_type: Attribute) -> bool:
    """判断 symbol 算术结果是否必须为 unknown。

    功能说明:
    - 任一 operand 值语义包含 `?` 时，算术结果必须保守为 `!symbol.int<#symbol.expr<??>>`。
    - `!symbol.iter<...>` 自身不再强制 unknown，仅当 start/end/step 含 `?` 时传播 unknown。

    使用示例:
    - needs_unknown = _requires_unknown_arith_result(lhs.type, rhs.type)
    """

    lhs_contains_unknown = _symbol_arith_operand_contains_unknown(lhs_type)
    rhs_contains_unknown = _symbol_arith_operand_contains_unknown(rhs_type)
    return (
        lhs_contains_unknown is not None
        and rhs_contains_unknown is not None
        and (lhs_contains_unknown or rhs_contains_unknown)
    )


def _infer_symbol_arith_result_expr(op_name: str, lhs_type: Attribute, rhs_type: Attribute) -> str | None:
    """推导 symbol 二元算术的 canonical 结果表达。

    功能说明:
    - 对 `SymbolValueType` 与 `SymbolIterType` operand 复用 `SymbolExprAttr` canonical 逻辑。
    - `SymbolIterType` 会转换为 `iter<start,end,step>` token；`?` 场景由调用方使用 unknown 规则处理。
    - `symbol.min` 始终返回未折叠的 `min(lhs, rhs)` 表达；full-tile tail 的 `step` 是 fold 结果，不是 AST 发射必须提前写入的结果类型。

    使用示例:
    - _infer_symbol_arith_result_expr("symbol.add", lhs.type, rhs.type)
    """

    lhs = _symbol_arith_operand_expr_node(lhs_type)
    rhs = _symbol_arith_operand_expr_node(rhs_type)
    if lhs is None or rhs is None:
        return None
    if op_name == "symbol.add":
        return _format_symbol_expr_node(_make_symbol_expr_add(lhs, rhs))
    if op_name == "symbol.sub":
        return _format_symbol_expr_node(_make_symbol_expr_sub(lhs, rhs))
    if op_name == "symbol.mul":
        return _format_symbol_expr_node(_make_symbol_expr_mul(lhs, rhs))
    if op_name in {"symbol.div", "symbol.floordiv"}:
        return _format_symbol_expr_node(_make_symbol_expr_keyword_binary("floordiv", lhs, rhs))
    if op_name == "symbol.min":
        return _format_symbol_expr_node(_make_symbol_expr_min(lhs, rhs))
    if op_name == "symbol.max":
        return _format_symbol_expr_node(_make_symbol_expr_max(lhs, rhs))
    return None


def _alternate_symbol_arith_result_exprs(op_name: str, lhs_type: Attribute, rhs_type: Attribute) -> tuple[str, ...]:
    """返回 verifier 可接受但不要求 AST 提前生成的等价结果表达。

    功能说明:
    - 当前只为 `symbol.min` full-tile tail 提供已折叠 `step` 表达。
    - 允许 AST 先发射 `min(step, end - iter<...>)`，也允许后续 fold/pass 将其规约为 `step`。

    使用示例:
    - alternatives = _alternate_symbol_arith_result_exprs("symbol.min", lhs.type, rhs.type)
    """

    if op_name != "symbol.min":
        return ()
    lhs = _symbol_arith_operand_expr_node(lhs_type)
    rhs = _symbol_arith_operand_expr_node(rhs_type)
    if lhs is None or rhs is None:
        return ()
    full_tile_step = _symbol_expr_full_tile_min_step(lhs, rhs)
    if full_tile_step is None:
        return ()
    return (_format_symbol_expr_node(full_tile_step),)


def _get_concrete_symbol_int_value(attr: Attribute) -> int | None:
    """提取静态可求值的 `!symbol.int` 整数值。


    功能说明:
    - 仅当 `attr` 是静态整数 `SymbolValueType` 时返回具体整数。
    - 动态 symbol 表达返回 `None`，供 fold 逻辑保守拒绝。

    使用示例:
    - _get_concrete_symbol_int_value(SymbolValueType.from_expr("3"))

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/symbol/test_symbol.py
    - 功能实现: kernel_gen/dialect/symbol/
    """

    if not isinstance(attr, SymbolValueType):
        return None
    value = attr.get_value()
    return value if isinstance(value, int) else None

__all__ = [
    "_verify_axis",
    "_entry_to_expr",
    "_infer_result_type",
    "_is_symbol_int_type",
    "_is_symbol_arith_operand_type",
    "_is_unknown_symbol_int_type",
    "_parse_symbol_binary_operand_types",
    "_symbol_iter_type_expr_node",
    "_symbol_arith_operand_expr_node",
    "_symbol_arith_operand_contains_unknown",
    "_symbol_expr_bounds_are_full_tiles",
    "_linear_distance_is_positive_multiple",
    "_symbol_expr_full_tile_residual_step",
    "_symbol_expr_full_tile_min_step",
    "_symbol_min_full_tile_step_value",
    "_requires_unknown_arith_result",
    "_infer_symbol_arith_result_expr",
    "_alternate_symbol_arith_result_exprs",
    "_get_concrete_symbol_int_value",
]
