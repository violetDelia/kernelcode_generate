"""DMA dialect package-internal verifier helpers.

功能说明:
- 承载 dma package 内 op/type verifier 共享的结构化检查与符号表达工具。
- 这些 helper 只服务 `kernel_gen.dialect.dma` 包内部实现，不从 package root re-export。

API 列表:
- `verify_symbol_expr_attr(value: Attribute, field_name: str) -> SymbolExprAttr`
- `verify_memory_type(value: Attribute, field_name: str) -> NnMemoryType`
- `verify_memory_operand(value: SSAValue, field_name: str) -> NnMemoryType`
- `verify_fill_value_operand(value: SSAValue, field_name: str) -> SSAValue`
- `verify_fill_target_element_type(element_type: Attribute) -> None`
- `verify_fill_value_matches_target(value_type: Attribute, target_element_type: Attribute) -> None`
- `operand_int_value(value: SSAValue) -> int | None`
- `verify_symbol_int_operands(values: Sequence[SSAValue], field_name: str, *, min_value: int) -> Sequence[SSAValue]`
- `verify_symbol_index_operands(values: Sequence[SSAValue], field_name: str, *, min_value: int) -> Sequence[SSAValue]`
- `verify_rank_match(values: Sequence[SSAValue], rank: int, field_name: str) -> None`
- `symbol_expr_attr_from_expr(expr: str) -> SymbolExprAttr`
- `dim_expr_text(dim: Attribute) -> str`
- `static_int_from_expr_text(expr: str) -> int | None`
- `static_int_from_dim(dim: Attribute) -> int | None`
- `verify_operands_match_layout(values: Sequence[SSAValue], layout: ArrayAttr[Attribute], message: str) -> None`
- `parse_symbolic_expr_text(text: str) -> sp.Basic | None`
- `verify_dynamic_shape_matches_result(values: Sequence[SSAValue], result_shape: ArrayAttr[Attribute], field_name: str) -> None`
- `verify_broadcast_compat(source_shape: ArrayAttr[Attribute], target_shape: ArrayAttr[Attribute]) -> None`
- `dims_equal(lhs: Attribute, rhs: Attribute) -> bool`
- `verify_transpose_perm(perm: ArrayAttr, rank: int) -> list[int]`
- `verify_transpose_layout(source_type: NnMemoryType, target_type: NnMemoryType, perm_values: Sequence[int]) -> None`
- `verify_unit_stride_operands(strides: Sequence[SSAValue]) -> None`
- `element_byte_size(element_type: Attribute) -> int | None`
- `is_i8_byte_pool(memory_type: NnMemoryType) -> bool`
- `linear_max_index(offsets: Sequence[SSAValue], shape: Sequence[SSAValue], stride: Sequence[SSAValue]) -> int | None`
- `maybe_numel(shape: ArrayAttr[Attribute]) -> int | None`
- `verify_static_view_bounds(source_shape: ArrayAttr[Attribute], source_stride: ArrayAttr[Attribute], offsets: Sequence[SSAValue], shape: Sequence[SSAValue], stride: Sequence[SSAValue]) -> None`
- `parenthesize_symbol_expr(expr: str) -> str`
- `symbol_expr_product(lhs: str, rhs: str) -> str`
- `default_contiguous_stride(shape: ArrayAttr[Attribute]) -> list[Attribute]`
- `parse_symbolic_dim_attr(value: Attribute) -> sp.Basic | None`
- `parse_symbol_value_expr(value: SSAValue) -> sp.Basic | None`
- `stride_attrs_equal(lhs: Attribute, rhs: Attribute) -> bool`
- `verify_view_result_stride(source_stride: ArrayAttr[Attribute], stride: Sequence[SSAValue], result_stride: ArrayAttr[Attribute]) -> None`
- `is_contiguous(memory_type: NnMemoryType) -> bool`
- `verify_default_contiguous_stride(memory_type: NnMemoryType, message: str) -> None`
- `symbol_int_expr_text(value: SSAValue, field_name: str) -> str`
- `verify_positive_static_operand(value: SSAValue, field_name: str) -> int | None`

使用示例:
- `verify_memory_operand(source, "source")`

关联文件:
- spec: spec/dialect/dma.md
- test: test/dialect/dma/
- 功能实现: kernel_gen/dialect/dma/common.py
"""

from __future__ import annotations

import re
from collections.abc import Sequence

import sympy as sp
from xdsl.dialects.builtin import (
    ArrayAttr,
    BFloat16Type,
    Float16Type,
    Float32Type,
    Float64Type,
    IntAttr,
    IntegerAttr,
    IntegerType,
    i8,
    i32,
)
from xdsl.ir import Attribute, SSAValue
from xdsl.utils.exceptions import VerifyException

from kernel_gen.core.contracts import verify_memory_type as common_verify_memory_type
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr, SymbolIterType, SymbolValueType

def verify_symbol_expr_attr(value: Attribute, field_name: str) -> SymbolExprAttr:
    """校验属性为公开 SymbolExprAttr。

    功能说明:
    - 用于 dma ring type 的 offset 参数校验。

    使用示例:
    - offset = verify_symbol_expr_attr(attr, "offset")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if not isinstance(value, SymbolExprAttr):
        raise VerifyException(f"{field_name} must be SymbolExprAttr")
    value.verify()
    return value

def verify_memory_type(value: Attribute, field_name: str) -> NnMemoryType:
    """校验并返回 nn.memory type。


    功能说明:
    - 确认类型为 nn.memory 并触发类型校验。

    使用示例:
    - verify_memory_type(op.source.type, "source")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    return common_verify_memory_type(value, field_name, scene="dialect.dma verifier")


def verify_memory_operand(value: SSAValue, field_name: str) -> NnMemoryType:
    """校验 SSA operand 为 nn.memory type。


    功能说明:
    - 统一处理 SSA operand 的 nn.memory 类型校验与内部验证。

    使用示例:
    - verify_memory_operand(op.source, "source")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    return verify_memory_type(value.type, field_name)


def verify_fill_value_operand(value: SSAValue, field_name: str) -> SSAValue:
    """校验 `dma.fill` 的数值标量 operand。


    功能说明:
    - 当前接受 builtin 整型、builtin 浮点或 `!symbol.int<#symbol.expr<expr>>`。
    - builtin `i1` 视为 bool，不属于 `dma.fill` 数值标量。
    - 若为 `!symbol.int<#symbol.expr<expr>>`，同步触发其类型校验。

    使用示例:
    - verify_fill_value_operand(op.value, "value")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if isinstance(value.type, IntegerType) and int(value.type.width.data) != 1:
        return value
    if isinstance(value.type, (Float16Type, BFloat16Type, Float32Type, Float64Type)):
        return value
    if isinstance(value.type, SymbolValueType):
        value.type.verify()
        return value
    raise VerifyException(f"{field_name} must be builtin integer, builtin float or !symbol.int")


def verify_fill_target_element_type(element_type: Attribute) -> None:
    """校验 `dma.fill` 目标 memory element type。


    功能说明:
    - 允许公开数值 memory dtype，拒绝 bool 与非数值类型。

    使用示例:
    - verify_fill_target_element_type(target_type.element_type)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if isinstance(element_type, IntegerType):
        if int(element_type.width.data) == 1:
            raise VerifyException("dma.fill target element_type must be numeric and not bool")
        return
    if isinstance(element_type, (Float16Type, BFloat16Type, Float32Type, Float64Type)):
        return
    raise VerifyException("dma.fill target element_type must be numeric and not bool")


def verify_fill_value_matches_target(value_type: Attribute, target_element_type: Attribute) -> None:
    """校验 `dma.fill` value 与 target dtype 的公开兼容性。


    功能说明:
    - `!symbol.int` 可填充非 bool 数值 memory。
    - builtin 整数只能填充整数 memory，builtin 浮点只能填充浮点 memory。

    使用示例:
    - verify_fill_value_matches_target(op.value.type, target_type.element_type)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if isinstance(value_type, SymbolValueType):
        return
    if isinstance(value_type, IntegerType) and isinstance(target_element_type, IntegerType):
        return
    if isinstance(value_type, (Float16Type, BFloat16Type, Float32Type, Float64Type)) and isinstance(
        target_element_type,
        (Float16Type, BFloat16Type, Float32Type, Float64Type),
    ):
        return
    raise VerifyException("dma.fill value type must match target element_type")


def operand_int_value(value: SSAValue) -> int | None:
    """尝试从 `!symbol.int<#symbol.expr<expr>>` SSA operand 恢复静态整型值。


    功能说明:
    - 仅识别字面量整数表达式，例如 `!symbol.int<#symbol.expr<4>>`。
    - `!symbol.iter<start = "...", end = "...", step = "...">` 视为运行期值，不参与静态比较。

    使用示例:
    - operand_int_value(op.sizes[0])

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if isinstance(value.type, SymbolIterType):
        return None
    if not isinstance(value.type, SymbolValueType):
        return None
    expr = value.type.expr.expr.data.strip()
    try:
        return int(expr)
    except ValueError:
        return None


def verify_symbol_int_operands(
    values: Sequence[SSAValue], field_name: str, *, min_value: int
) -> Sequence[SSAValue]:
    """校验 `!symbol.int<#symbol.expr<expr>>` operand 列表。


    功能说明:
    - 确保所有 operand 类型为 `!symbol.int<#symbol.expr<expr>>`。
    - 若 operand 可静态恢复为整型常量，则施加最小值约束。

    使用示例:
    - verify_symbol_int_operands(op.sizes, "sizes", min_value=1)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    for value in values:
        if not isinstance(value.type, SymbolValueType):
            raise VerifyException(f"{field_name} entries must be !symbol.int")
        value.type.verify()
        static_value = operand_int_value(value)
        if static_value is not None and static_value < min_value:
            raise VerifyException(f"{field_name} entries must be >= {min_value}")
    return values


def verify_symbol_index_operands(
    values: Sequence[SSAValue], field_name: str, *, min_value: int
) -> Sequence[SSAValue]:
    """校验 `!symbol.int` / `!symbol.iter` operand 列表。


    功能说明:
    - 确保 operand 类型为 `!symbol.int` 或 `!symbol.iter`。
    - 若 operand 可静态恢复为整型常量，则施加最小值约束。

    使用示例:
    - verify_symbol_index_operands(op.offsets, "offsets", min_value=0)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    for value in values:
        if not isinstance(value.type, (SymbolValueType, SymbolIterType)):
            raise VerifyException(f"{field_name} entries must be !symbol.int or !symbol.iter")
        value.type.verify()
        static_value = operand_int_value(value)
        if static_value is not None and static_value < min_value:
            raise VerifyException(f"{field_name} entries must be >= {min_value}")
    return values


def verify_rank_match(values: Sequence[SSAValue], rank: int, field_name: str) -> None:
    """校验标量 operand 列表长度与 rank 一致。


    功能说明:
    - 用于验证切片大小与 shape 的对应关系。

    使用示例:
    - verify_rank_match(offsets, rank, "offsets")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if len(values) != rank:
        raise VerifyException(f"{field_name} length must match rank")


def symbol_expr_attr_from_expr(expr: str) -> SymbolExprAttr:
    """构造公开 SymbolExprAttr。

    功能说明:
    - 统一 dma dialect 内部 shape/stride 推导的结构化表达构造。

    使用示例:
    - symbol_expr_attr_from_expr("N")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    return SymbolExprAttr.from_expr(expr)


def dim_expr_text(dim: Attribute) -> str:
    """读取 memory shape/stride 的 SymbolExprAttr 文本。

    功能说明:
    - 拒绝旧 IntAttr/StringAttr shape/stride 入口。

    使用示例:
    - dim_expr_text(SymbolExprAttr.from_expr("N"))

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if not isinstance(dim, SymbolExprAttr):
        raise VerifyException("memory layout entries must be SymbolExprAttr")
    dim.verify()
    return dim.expr.data


def static_int_from_expr_text(expr: str) -> int | None:
    """尝试从 SymbolExprAttr 文本提取静态整数。

    功能说明:
    - 仅识别十进制整数字面量；动态表达式返回 None。

    使用示例:
    - static_int_from_expr_text("4")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    signless = expr[1:] if expr.startswith("-") else expr
    if signless.isdecimal():
        return int(expr)
    return None


def static_int_from_dim(dim: Attribute) -> int | None:
    """尝试从 SymbolExprAttr 维度提取静态整数。

    功能说明:
    - 对 `#symbol.expr<4>` 返回 4；动态维度返回 None。

    使用示例:
    - static_int_from_dim(SymbolExprAttr.from_expr("4"))

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    return static_int_from_expr_text(dim_expr_text(dim))


def verify_operands_match_layout(
    values: Sequence[SSAValue],
    layout: ArrayAttr[Attribute],
    message: str,
) -> None:
    """校验 operand 列表与类型中可静态判定的布局一致。


    功能说明:
    - 若布局维度为静态 `SymbolExprAttr`，对应 operand 必须是相同值的 `!symbol.int<#symbol.expr<n>>`。
    - 若布局维度为符号表达式，则 operand 的公开表达式必须一致。
    - `?` 类型值只能匹配 `#symbol.expr<?>` 布局，不能通过 SSA 名称伪造具名维度。

    使用示例:
    - verify_operands_match_layout(op.sizes, result_type.shape, "shape must match sizes")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    for value, expected in zip(values, layout.data, strict=True):
        expected_int = static_int_from_dim(expected)
        if expected_int is not None:
            static_value = operand_int_value(value)
            if static_value != expected_int:
                raise VerifyException(message)
            continue
        expected_expr = dim_expr_text(expected)
        if expected_expr == "?":
            if not isinstance(value.type, SymbolValueType) or value.type.get_value() != "?":
                raise VerifyException(message)
            continue
        if not isinstance(value.type, SymbolValueType) or value.type.get_value() != expected_expr:
            raise VerifyException(message)


def parse_symbolic_expr_text(text: str) -> sp.Basic | None:
    """解析符号整数表达式文本。


    功能说明:
    - 将整数、符号乘法、`floor(...)` 与 `min(...)` 文本解析为 sympy 表达式。
    - 无法解析或未知动态维度时返回 `None`，由调用方决定是否跳过静态比较。

    使用示例:
    - parse_symbolic_expr_text("TILE_H*4")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    stripped = text.strip().replace(" floordiv ", " // ")
    if stripped == "?":
        return None
    names = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", stripped))
    function_names = {"floor", "min"}
    local_dict = {name: sp.Symbol(name, integer=True, real=True) for name in names if name not in function_names}
    local_dict.update({"floor": sp.floor, "min": sp.Min})
    try:
        return sp.sympify(stripped, locals=local_dict)
    except (TypeError, ValueError, SyntaxError, sp.SympifyError):
        return None


def verify_dynamic_shape_matches_result(
    values: Sequence[SSAValue],
    result_shape: ArrayAttr[Attribute],
    field_name: str,
) -> None:
    """校验 dma.alloc 的 dynamic_shape 与结果 shape 的一致性。


    功能说明:
    - 支持两种形态：
      1) dynamic_shape 与结果 rank 等长，逐维对齐；
      2) dynamic_shape 仅包含非静态维度，按出现顺序对齐。
    - 匿名维度 `?` 必须由 `!symbol.int<?>` 承接，不能与具名维互相伪装。

    使用示例:
    - verify_dynamic_shape_matches_result(dynamic_shape, result_type.shape, "dynamic_shape")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    rank = len(result_shape.data)
    if len(values) == rank:
        verify_rank_match(values, rank, field_name)
        verify_operands_match_layout(values, result_shape, f"{field_name} must match result shape")
        return

    dynamic_dims: list[Attribute] = []
    for dim in result_shape.data:
        if static_int_from_dim(dim) is not None:
            continue
        dynamic_dims.append(dim)

    if len(values) != len(dynamic_dims):
        raise VerifyException(f"{field_name} length must match symbol rank")

    verify_operands_match_layout(
        values,
        ArrayAttr(dynamic_dims),
        f"{field_name} symbol must match result shape",
    )


def verify_broadcast_compat(
    source_shape: ArrayAttr[Attribute],
    target_shape: ArrayAttr[Attribute],
) -> None:
    """校验 dma.broadcast 的 shape 兼容性。


    功能说明:
    - 按尾维对齐规则检查 source/target shape。
    - 仅在静态整数维度冲突时失败，符号维度不做数值求解。

    使用示例:
    - verify_broadcast_compat(source_type.shape, target_type.shape)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    source_dims = source_shape.data
    target_dims = target_shape.data
    if len(source_dims) > len(target_dims):
        raise VerifyException("dma.broadcast source rank must be <= target rank")

    for offset in range(1, len(target_dims) + 1):
        target_dim = target_dims[-offset]
        source_dim = source_dims[-offset] if offset <= len(source_dims) else symbol_expr_attr_from_expr("1")
        source_value = static_int_from_dim(source_dim)
        target_value = static_int_from_dim(target_dim)
        if source_value is not None and target_value is not None:
            if source_value != target_value and source_value != 1 and target_value != 1:
                raise VerifyException("dma.broadcast shape mismatch")


def dims_equal(lhs: Attribute, rhs: Attribute) -> bool:
    """判断 shape/stride 维度是否一致。


    功能说明:
    - 支持 SymbolExprAttr 的 canonical 文本一致性判断。

    使用示例:
    - dims_equal(SymbolExprAttr.from_expr("N"), SymbolExprAttr.from_expr("N"))

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if isinstance(lhs, SymbolExprAttr) and isinstance(rhs, SymbolExprAttr):
        return lhs.expr.data == rhs.expr.data
    return False


def verify_transpose_perm(perm: ArrayAttr, rank: int) -> list[int]:
    """校验 dma.transpose 的 perm 合法性并返回序列。


    功能说明:
    - 校验 perm 长度与 rank 一致。
    - 校验 perm 为 0..rank-1 的排列。

    使用示例:
    - verify_transpose_perm(ArrayAttr([IntAttr(1), IntAttr(0)]), rank=2)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if len(perm.data) != rank:
        raise VerifyException("dma.transpose perm must match source rank")
    perm_values: list[int] = []
    for entry in perm.data:
        if isinstance(entry, IntAttr):
            perm_values.append(entry.data)
            continue
        if isinstance(entry, IntegerAttr) and isinstance(entry.value, IntAttr):
            perm_values.append(entry.value.data)
            continue
        raise VerifyException("dma.transpose perm must be a permutation of 0..rank-1")
    if sorted(perm_values) != list(range(rank)):
        raise VerifyException("dma.transpose perm must be a permutation of 0..rank-1")
    return perm_values


def verify_transpose_layout(
    source_type: NnMemoryType,
    target_type: NnMemoryType,
    perm_values: Sequence[int],
) -> None:
    """校验 dma.transpose 的目标 shape 与连续 stride。


    功能说明:
    - 按 perm 重排 source shape，并与 target shape 对齐校验。
    - target stride 必须是 target shape 的默认连续 stride；匿名动态 shape 的高维 stride 可保留调用点动态语义表达。

    使用示例:
    - verify_transpose_layout(source_type, target_type, [1, 0])

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if len(target_type.shape.data) != len(perm_values):
        raise VerifyException("dma.transpose target rank mismatch")
    expected_shape = [source_type.shape.data[index] for index in perm_values]
    for expected_dim, actual_dim in zip(expected_shape, target_type.shape.data, strict=True):
        if not dims_equal(expected_dim, actual_dim):
            raise VerifyException("dma.transpose target shape mismatch")

    expected_stride = default_contiguous_stride(target_type.shape)
    for expected_dim, actual_dim in zip(expected_stride, target_type.stride.data, strict=True):
        if not stride_attrs_equal(expected_dim, actual_dim):
            if dim_expr_text(expected_dim) == "?" and static_int_from_dim(actual_dim) is None:
                continue
            raise VerifyException("dma.transpose target stride mismatch")


def verify_unit_stride_operands(strides: Sequence[SSAValue]) -> None:
    """校验 stride operand 是否全为常量 1。


    功能说明:
    - 当前阶段仅支持单位步长语义。
    - 每个 operand 都必须是值为 `1` 的 `!symbol.int<#symbol.expr<1>>`。

    使用示例:
    - verify_unit_stride_operands(op.strides)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    for value in strides:
        if operand_int_value(value) != 1:
            raise VerifyException("dma stride must be 1 in current implementation")


def element_byte_size(element_type: Attribute) -> int | None:
    """解析 element_type 的字节大小。


    功能说明:
    - 支持 i1/i8/i16/i32/i64 与 f16/bf16/f32/f64。

    使用示例:
    - size = element_byte_size(Float32Type())

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if isinstance(element_type, IntegerType):
        width = int(element_type.width.data)
        if width in {1, 8}:
            return 1
        if width == 16:
            return 2
        if width == 32:
            return 4
        if width == 64:
            return 8
        return None
    if isinstance(element_type, (Float16Type, BFloat16Type)):
        return 2
    if isinstance(element_type, Float32Type):
        return 4
    if isinstance(element_type, Float64Type):
        return 8
    return None


def is_i8_byte_pool(memory_type: NnMemoryType) -> bool:
    """判断是否为 i8 一维 byte pool。


    功能说明:
    - 要求 element_type 为 i8，且 rank 为 1。

    使用示例:
    - if is_i8_byte_pool(mem_type): ...

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if len(memory_type.shape.data) != 1:
        return False
    element_type = memory_type.element_type
    return isinstance(element_type, IntegerType) and int(element_type.width.data) == 8


def linear_max_index(
    offsets: Sequence[SSAValue],
    shape: Sequence[SSAValue],
    stride: Sequence[SSAValue],
) -> int | None:
    """计算 view 的静态最大线性索引（元素单位）。


    功能说明:
    - 当 offsets/shape/stride 都可静态还原时，返回最大线性索引。
    - 任一值无法静态还原则返回 None。

    使用示例:
    - max_index = linear_max_index(op.offsets, op.shape, op.stride)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    total = 0
    for offset_value, size_value, stride_value in zip(offsets, shape, stride, strict=True):
        offset_int = operand_int_value(offset_value)
        size_int = operand_int_value(size_value)
        stride_int = operand_int_value(stride_value)
        if offset_int is None or size_int is None or stride_int is None:
            return None
        total += offset_int + (size_int - 1) * stride_int
    return total

def maybe_numel(shape: ArrayAttr[Attribute]) -> int | None:
    """尝试计算 shape 的元素总数。


    功能说明:
    - 仅在全部维度为静态整数 SymbolExprAttr 时返回乘积。

    使用示例:
    - maybe_numel(ArrayAttr([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("4")]))

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    numel = 1
    for dim in shape.data:
        value = static_int_from_dim(dim)
        if value is None:
            return None
        numel *= value
    return numel


def verify_static_view_bounds(
    source_shape: ArrayAttr[Attribute],
    source_stride: ArrayAttr[Attribute],
    offsets: Sequence[SSAValue],
    shape: Sequence[SSAValue],
    stride: Sequence[SSAValue],
) -> None:
    """校验 dma.view 可静态判定的边界约束。


    功能说明:
    - 当 `source.shape/source.stride` 与 `offsets/shape/stride` 都可静态恢复时，
      以源内存线性起点和结果线性覆盖范围执行静态边界检查。

    使用示例:
    - verify_static_view_bounds(source_type.shape, source_type.stride, op.offsets, op.shape, op.stride)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    source_numel = maybe_numel(source_shape)
    if source_numel is None:
        return
    linear_start = 0
    linear_extent = 0
    for source_step_attr, offset_value, size_value, stride_value in zip(
        source_stride.data, offsets, shape, stride, strict=True
    ):
        source_step = static_int_from_dim(source_step_attr)
        if source_step is None:
            return
        offset_int = operand_int_value(offset_value)
        size_int = operand_int_value(size_value)
        stride_int = operand_int_value(stride_value)
        if offset_int is None or size_int is None or stride_int is None:
            return
        linear_start += offset_int * source_step
        linear_extent += (size_int - 1) * stride_int * source_step
    if linear_start + linear_extent >= source_numel:
        raise VerifyException("dma.view bounds mismatch")


def parenthesize_symbol_expr(expr: str) -> str:
    """为乘法组合准备符号表达式文本。

    功能说明:
    - 简单标识符和整数保持原文。
    - 复合表达式加括号，避免 `floordiv`、加减法参与 stride 乘积时改变语义。

    使用示例:
    - text = parenthesize_symbol_expr("M + 1")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if expr == "?" or expr.replace("_", "").isalnum() or expr.lstrip("-").isdigit():
        return expr
    return f"({expr})"


def symbol_expr_product(lhs: str, rhs: str) -> str:
    """组合两个 symbol 表达式乘积。

    功能说明:
    - 消除乘以 1 的冗余文本。
    - 对复合表达式加括号，保持默认连续 stride 的符号计算语义。

    使用示例:
    - expr = symbol_expr_product("M + 1", "N")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if lhs == "1":
        return rhs
    if rhs == "1":
        return lhs
    return f"{parenthesize_symbol_expr(lhs)}*{parenthesize_symbol_expr(rhs)}"


def default_contiguous_stride(shape: ArrayAttr[Attribute]) -> list[Attribute]:
    """按默认连续布局生成行主序 stride。


    功能说明:
    - 静态维度返回 `#symbol.expr<整数>`。
    - 符号维度返回 canonical `#symbol.expr<乘积>`。
    - `#symbol.expr<?>` 维度会把更高维 stride 退化为 `#symbol.expr<?>`。

    使用示例:
    - default_contiguous_stride(ArrayAttr([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("4")]))

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    stride: list[Attribute] = []
    running: str | None = "1"
    for dim in reversed(shape.data):
        if running is None:
            stride.append(symbol_expr_attr_from_expr("?"))
        else:
            stride.append(symbol_expr_attr_from_expr(running))
        if running is None:
            continue
        dim_expr = dim_expr_text(dim)
        if dim_expr == "?":
            running = None
        elif dim_expr == "1":
            continue
        elif running == "1":
            running = dim_expr
        else:
            running = dim_expr_text(symbol_expr_attr_from_expr(symbol_expr_product(dim_expr, running)))
    stride.reverse()
    return stride


def parse_symbolic_dim_attr(value: Attribute) -> sp.Basic | None:
    """解析 stride 维度 attribute 为 sympy 表达式。


    功能说明:
    - `SymbolExprAttr` 解析为符号表达式，并为所有标识符创建同名整数符号。
    - `min(...)` 按 `sympy.Min` 解析，用于判定动态尾块连续 stride。
    - 无法解析或未知动态维度时返回 `None`。

    使用示例:
    - parse_symbolic_dim_attr(SymbolExprAttr.from_expr("KH*KW*TC"))

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if not isinstance(value, SymbolExprAttr):
        return None
    return parse_symbolic_expr_text(value.expr.data)


def parse_symbol_value_expr(value: SSAValue) -> sp.Basic | None:
    """解析 `!symbol.int<#symbol.expr<expr>>` operand 为 sympy 表达式。


    功能说明:
    - 仅解析 `SymbolValueType` 的公开表达式文本。
    - 无法解析或未知动态值时返回 `None`，由调用方跳过静态比较。

    使用示例:
    - parse_symbol_value_expr(op.stride[0])

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if not isinstance(value.type, SymbolValueType):
        return None
    return parse_symbolic_expr_text(value.type.expr.expr.data)


def stride_attrs_equal(lhs: Attribute, rhs: Attribute) -> bool:
    """判断两个 stride 维度是否等价。


    功能说明:
    - 优先复用公共维度比较。
    - 当文本不同但表达式等价时，使用 sympy 简化差值判断。

    使用示例:
    - stride_attrs_equal(SymbolExprAttr.from_expr("TC*KH*KW"), SymbolExprAttr.from_expr("KH*KW*TC"))

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if dims_equal(lhs, rhs):
        return True
    lhs_expr = parse_symbolic_dim_attr(lhs)
    rhs_expr = parse_symbolic_dim_attr(rhs)
    if lhs_expr is None or rhs_expr is None:
        return False
    return sp.simplify(lhs_expr - rhs_expr) == 0


def verify_view_result_stride(
    source_stride: ArrayAttr[Attribute],
    stride: Sequence[SSAValue],
    result_stride: ArrayAttr[Attribute],
) -> None:
    """校验 dma.view 结果 stride 来自源物理 stride 与逻辑 stride 的乘积。


    功能说明:
    - 对可解析维度执行 `result_stride == source_stride * stride_operand` 比较。
    - 含未知 `?` 或不可解析符号时跳过该维静态比较，保留动态 IR 表达能力。

    使用示例:
    - verify_view_result_stride(source_type.stride, op.stride, result_type.stride)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    for source_attr, stride_value, result_attr in zip(source_stride.data, stride, result_stride.data, strict=True):
        source_expr = parse_symbolic_dim_attr(source_attr)
        stride_expr = parse_symbol_value_expr(stride_value)
        result_expr = parse_symbolic_dim_attr(result_attr)
        if source_expr is None or stride_expr is None or result_expr is None:
            continue
        if sp.simplify(result_expr - (source_expr * stride_expr)) != 0:
            raise VerifyException("stride must match source physical stride * view stride")


def is_contiguous(memory_type: NnMemoryType) -> bool:
    """检查 memory type 是否连续行主序。


    功能说明:
    - 静态 stride 直接比较整数。
    - 符号 stride 使用表达式等价判断，允许乘法因子顺序不同。
    - 由匿名动态 shape 推导出的未知高维 stride 接受动态语义表达，保留调用点变量名。

    使用示例:
    - is_contiguous(memory_type)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    expected = default_contiguous_stride(memory_type.shape)
    if len(expected) != len(memory_type.stride.data):
        return False
    for expected_dim, stride_dim in zip(expected, memory_type.stride.data, strict=True):
        if not stride_attrs_equal(expected_dim, stride_dim):
            if dim_expr_text(expected_dim) == "?" and static_int_from_dim(stride_dim) is None:
                continue
            return False
    return True


def verify_default_contiguous_stride(memory_type: NnMemoryType, message: str) -> None:
    """校验 memory type 的 stride 是否匹配默认连续布局。


    功能说明:
    - 根据 `shape` 生成默认连续布局。
    - 要求 `stride` 与默认布局完全一致。

    使用示例:
    - verify_default_contiguous_stride(result_type, "dma.alloc requires contiguous result stride")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if not is_contiguous(memory_type):
        raise VerifyException(message)


def symbol_int_expr_text(value: SSAValue, field_name: str) -> str:
    """读取 `!symbol.int` operand 的公开表达文本。

    功能说明:
    - 校验 operand 类型为 `SymbolValueType` 并返回其 `SymbolExprAttr` 文本。

    使用示例:
    - offset_expr = symbol_int_expr_text(op.offset, "offset")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if not isinstance(value.type, SymbolValueType):
        raise VerifyException(f"{field_name} must be !symbol.int")
    value.type.verify()
    return value.type.expr.expr.data


def verify_positive_static_operand(value: SSAValue, field_name: str) -> int | None:
    """校验可静态判定的 `!symbol.int` operand 为正数。

    功能说明:
    - 动态符号表达式仅校验类型，不做数值求解。

    使用示例:
    - count = verify_positive_static_operand(op.count, "count")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    symbol_int_expr_text(value, field_name)
    static_value = operand_int_value(value)
    if static_value is not None and static_value <= 0:
        raise VerifyException(f"{field_name} must be > 0")
    return static_value



__all__ = [
    "verify_symbol_expr_attr",
    "verify_memory_type",
    "verify_memory_operand",
    "verify_fill_value_operand",
    "verify_fill_target_element_type",
    "verify_fill_value_matches_target",
    "operand_int_value",
    "verify_symbol_int_operands",
    "verify_symbol_index_operands",
    "verify_rank_match",
    "symbol_expr_attr_from_expr",
    "dim_expr_text",
    "static_int_from_expr_text",
    "static_int_from_dim",
    "verify_operands_match_layout",
    "parse_symbolic_expr_text",
    "verify_dynamic_shape_matches_result",
    "verify_broadcast_compat",
    "dims_equal",
    "verify_transpose_perm",
    "verify_transpose_layout",
    "verify_unit_stride_operands",
    "element_byte_size",
    "is_i8_byte_pool",
    "linear_max_index",
    "maybe_numel",
    "verify_static_view_bounds",
    "parenthesize_symbol_expr",
    "symbol_expr_product",
    "default_contiguous_stride",
    "parse_symbolic_dim_attr",
    "parse_symbol_value_expr",
    "stride_attrs_equal",
    "verify_view_result_stride",
    "is_contiguous",
    "verify_default_contiguous_stride",
    "symbol_int_expr_text",
    "verify_positive_static_operand",
]
