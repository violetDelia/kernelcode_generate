"""DMA dialect definitions.


功能说明:
- 定义 dma dialect 的 alloc/fill/copy/load/store/slice/deslice/subview/view/reshape/cast/broadcast op 与 verifier 规则。
- 复用 nn dialect 的 NnMemoryType 与 NnMemorySpaceAttr。

API 列表:
- `class DmaAllocOp(dynamic_shape: Sequence[SSAValue], result_type: NnMemoryType)`
- `class DmaFillOp(target: SSAValue | Operation, value: SSAValue | Operation)`
- `class DmaFreeOp(source: SSAValue | Operation)`
- `class DmaCopyOp(target: SSAValue | Operation, source: SSAValue | Operation)`
- `class DmaBroadcastOp(target: SSAValue | Operation, source: SSAValue | Operation)`
- `class DmaTransposeOp(target: SSAValue | Operation, source: SSAValue | Operation, perm: Sequence[int] | ArrayAttr)`
- `class DmaLoadOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue])`
- `class DmaStoreOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue])`
- `class DmaSliceOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue])`
- `class DmaDesliceOp(target: SSAValue | Operation, source: SSAValue | Operation, offsets: Sequence[SSAValue], sizes: Sequence[SSAValue], strides: Sequence[SSAValue], result_type: NnMemoryType)`
- `class DmaSubviewOp(source: SSAValue | Operation, offset: SSAValue | Operation, size: SSAValue | Operation, stride: SSAValue | Operation, result_type: NnMemoryType)`
- `class DmaViewOp(source: SSAValue | Operation, offsets: Sequence[SSAValue], shape: Sequence[SSAValue], stride: Sequence[SSAValue], result_type: NnMemoryType)`
- `class DmaReshapeOp(source: SSAValue | Operation, shape: Sequence[SSAValue], result_type: NnMemoryType)`
- `class DmaCastOp(target: SSAValue | Operation, source: SSAValue | Operation)`
- `Dma`

使用示例:
- from kernel_gen.dialect.dma import Dma, DmaCopyOp

关联文件:
- spec: spec/dialect/dma.md
- test: test/dialect/test_dma.py
- 功能实现: kernel_gen/dialect/dma.py
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
    i32,
)
from xdsl.ir import Attribute, Dialect, Operation, SSAValue
from xdsl.irdl import (
    AttrSizedOperandSegments,
    IRDLOperation,
    attr_def,
    irdl_op_definition,
    operand_def,
    result_def,
    var_operand_def,
)
from xdsl.utils.exceptions import VerifyException

from kernel_gen.core.contracts import (
    verify_memory_type as _common_verify_memory_type,
)
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr, SymbolIterType, SymbolValueType

def _verify_memory_type(value: Attribute, field_name: str) -> NnMemoryType:
    """校验并返回 nn.memory type。


    功能说明:
    - 确认类型为 nn.memory 并触发类型校验。

    使用示例:
    - _verify_memory_type(op.source.type, "source")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    return _common_verify_memory_type(value, field_name, scene="dialect.dma verifier")


def _verify_memory_operand(value: SSAValue, field_name: str) -> NnMemoryType:
    """校验 SSA operand 为 nn.memory type。


    功能说明:
    - 统一处理 SSA operand 的 nn.memory 类型校验与内部验证。

    使用示例:
    - _verify_memory_operand(op.source, "source")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    return _verify_memory_type(value.type, field_name)


def _verify_fill_value_operand(value: SSAValue, field_name: str) -> SSAValue:
    """校验 `dma.fill` 的整数标量 operand。


    功能说明:
    - 当前仅接受 builtin `i32` 或 `!symbol.int<#symbol.expr<expr>>`。
    - 若为 `!symbol.int<#symbol.expr<expr>>`，同步触发其类型校验。

    使用示例:
    - _verify_fill_value_operand(op.value, "value")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if value.type == i32:
        return value
    if isinstance(value.type, SymbolValueType):
        value.type.verify()
        return value
    raise VerifyException(f"{field_name} must be builtin i32 or !symbol.int")


def _operand_int_value(value: SSAValue) -> int | None:
    """尝试从 `!symbol.int<#symbol.expr<expr>>` SSA operand 恢复静态整型值。


    功能说明:
    - 仅识别字面量整数表达式，例如 `!symbol.int<#symbol.expr<4>>`。
    - `!symbol.iter<start = "...", end = "...", step = "...">` 视为运行期值，不参与静态比较。

    使用示例:
    - _operand_int_value(op.sizes[0])

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
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


def _verify_symbol_int_operands(
    values: Sequence[SSAValue], field_name: str, *, min_value: int
) -> Sequence[SSAValue]:
    """校验 `!symbol.int<#symbol.expr<expr>>` operand 列表。


    功能说明:
    - 确保所有 operand 类型为 `!symbol.int<#symbol.expr<expr>>`。
    - 若 operand 可静态恢复为整型常量，则施加最小值约束。

    使用示例:
    - _verify_symbol_int_operands(op.sizes, "sizes", min_value=1)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    for value in values:
        if not isinstance(value.type, SymbolValueType):
            raise VerifyException(f"{field_name} entries must be !symbol.int")
        value.type.verify()
        static_value = _operand_int_value(value)
        if static_value is not None and static_value < min_value:
            raise VerifyException(f"{field_name} entries must be >= {min_value}")
    return values


def _verify_symbol_index_operands(
    values: Sequence[SSAValue], field_name: str, *, min_value: int
) -> Sequence[SSAValue]:
    """校验 `!symbol.int` / `!symbol.iter` operand 列表。


    功能说明:
    - 确保 operand 类型为 `!symbol.int` 或 `!symbol.iter`。
    - 若 operand 可静态恢复为整型常量，则施加最小值约束。

    使用示例:
    - _verify_symbol_index_operands(op.offsets, "offsets", min_value=0)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    for value in values:
        if not isinstance(value.type, (SymbolValueType, SymbolIterType)):
            raise VerifyException(f"{field_name} entries must be !symbol.int or !symbol.iter")
        value.type.verify()
        static_value = _operand_int_value(value)
        if static_value is not None and static_value < min_value:
            raise VerifyException(f"{field_name} entries must be >= {min_value}")
    return values


def _verify_rank_match(values: Sequence[SSAValue], rank: int, field_name: str) -> None:
    """校验标量 operand 列表长度与 rank 一致。


    功能说明:
    - 用于验证切片大小与 shape 的对应关系。

    使用示例:
    - _verify_rank_match(offsets, rank, "offsets")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if len(values) != rank:
        raise VerifyException(f"{field_name} length must match rank")


def _symbol_expr_attr_from_expr(expr: str) -> SymbolExprAttr:
    """构造公开 SymbolExprAttr。

    功能说明:
    - 统一 dma dialect 内部 shape/stride 推导的结构化表达构造。

    使用示例:
    - _symbol_expr_attr_from_expr("N")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    return SymbolExprAttr.from_expr(expr)


def _dim_expr_text(dim: Attribute) -> str:
    """读取 memory shape/stride 的 SymbolExprAttr 文本。

    功能说明:
    - 拒绝旧 IntAttr/StringAttr shape/stride 入口。

    使用示例:
    - _dim_expr_text(SymbolExprAttr.from_expr("N"))

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if not isinstance(dim, SymbolExprAttr):
        raise VerifyException("memory layout entries must be SymbolExprAttr")
    dim.verify()
    return dim.expr.data


def _static_int_from_expr_text(expr: str) -> int | None:
    """尝试从 SymbolExprAttr 文本提取静态整数。

    功能说明:
    - 仅识别十进制整数字面量；动态表达式返回 None。

    使用示例:
    - _static_int_from_expr_text("4")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    signless = expr[1:] if expr.startswith("-") else expr
    if signless.isdecimal():
        return int(expr)
    return None


def _static_int_from_dim(dim: Attribute) -> int | None:
    """尝试从 SymbolExprAttr 维度提取静态整数。

    功能说明:
    - 对 `#symbol.expr<4>` 返回 4；动态维度返回 None。

    使用示例:
    - _static_int_from_dim(SymbolExprAttr.from_expr("4"))

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    return _static_int_from_expr_text(_dim_expr_text(dim))


def _verify_operands_match_layout(
    values: Sequence[SSAValue],
    layout: ArrayAttr[Attribute],
    mismatch_message: str,
) -> None:
    """校验 operand 列表与类型中可静态判定的布局一致。


    功能说明:
    - 若布局维度为静态 `SymbolExprAttr`，对应 operand 必须是相同值的 `!symbol.int<#symbol.expr<n>>`。
    - 若布局维度为符号表达式，则 operand 的公开表达式必须一致。
    - `?` 类型值只能匹配 `#symbol.expr<?>` 布局，不能通过 SSA 名称伪造具名维度。

    使用示例:
    - _verify_operands_match_layout(op.sizes, result_type.shape, "shape must match sizes")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    for value, expected in zip(values, layout.data, strict=True):
        expected_int = _static_int_from_dim(expected)
        if expected_int is not None:
            static_value = _operand_int_value(value)
            if static_value != expected_int:
                raise VerifyException(mismatch_message)
            continue
        expected_expr = _dim_expr_text(expected)
        if expected_expr == "?":
            if not isinstance(value.type, SymbolValueType) or value.type.get_value() != "?":
                raise VerifyException(mismatch_message)
            continue
        if not isinstance(value.type, SymbolValueType) or value.type.get_value() != expected_expr:
            raise VerifyException(mismatch_message)


def _parse_symbolic_expr_text(text: str) -> sp.Basic | None:
    """解析符号整数表达式文本。


    功能说明:
    - 将整数、符号乘法、`floor(...)` 与 `min(...)` 文本解析为 sympy 表达式。
    - 无法解析或未知动态维度时返回 `None`，由调用方决定是否跳过静态比较。

    使用示例:
    - _parse_symbolic_expr_text("TILE_H*4")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
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


def _verify_dynamic_shape_matches_result(
    dynamic_shape: Sequence[SSAValue],
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
    - _verify_dynamic_shape_matches_result(dynamic_shape, result_type.shape, "dynamic_shape")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    rank = len(result_shape.data)
    if len(dynamic_shape) == rank:
        _verify_rank_match(dynamic_shape, rank, field_name)
        _verify_operands_match_layout(dynamic_shape, result_shape, f"{field_name} must match result shape")
        return

    dynamic_dims: list[Attribute] = []
    for dim in result_shape.data:
        if _static_int_from_dim(dim) is not None:
            continue
        dynamic_dims.append(dim)

    if len(dynamic_shape) != len(dynamic_dims):
        raise VerifyException(f"{field_name} length must match symbol rank")

    _verify_operands_match_layout(
        dynamic_shape,
        ArrayAttr(dynamic_dims),
        f"{field_name} symbol must match result shape",
    )


def _verify_broadcast_compat(
    source_shape: ArrayAttr[Attribute],
    target_shape: ArrayAttr[Attribute],
) -> None:
    """校验 dma.broadcast 的 shape 兼容性。


    功能说明:
    - 按尾维对齐规则检查 source/target shape。
    - 仅在静态整数维度冲突时失败，符号维度不做数值求解。

    使用示例:
    - _verify_broadcast_compat(source_type.shape, target_type.shape)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    source_dims = source_shape.data
    target_dims = target_shape.data
    if len(source_dims) > len(target_dims):
        raise VerifyException("dma.broadcast source rank must be <= target rank")

    for offset in range(1, len(target_dims) + 1):
        target_dim = target_dims[-offset]
        source_dim = source_dims[-offset] if offset <= len(source_dims) else _symbol_expr_attr_from_expr("1")
        source_value = _static_int_from_dim(source_dim)
        target_value = _static_int_from_dim(target_dim)
        if source_value is not None and target_value is not None:
            if source_value != target_value and source_value != 1 and target_value != 1:
                raise VerifyException("dma.broadcast shape mismatch")


def _dims_equal(lhs: Attribute, rhs: Attribute) -> bool:
    """判断 shape/stride 维度是否一致。


    功能说明:
    - 支持 SymbolExprAttr 的 canonical 文本一致性判断。

    使用示例:
    - _dims_equal(SymbolExprAttr.from_expr("N"), SymbolExprAttr.from_expr("N"))

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if isinstance(lhs, SymbolExprAttr) and isinstance(rhs, SymbolExprAttr):
        return lhs.expr.data == rhs.expr.data
    return False


def _verify_transpose_perm(perm: ArrayAttr, rank: int) -> list[int]:
    """校验 dma.transpose 的 perm 合法性并返回序列。


    功能说明:
    - 校验 perm 长度与 rank 一致。
    - 校验 perm 为 0..rank-1 的排列。

    使用示例:
    - _verify_transpose_perm(ArrayAttr([IntAttr(1), IntAttr(0)]), rank=2)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
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


def _verify_transpose_layout(
    source_type: NnMemoryType,
    target_type: NnMemoryType,
    perm_values: Sequence[int],
) -> None:
    """校验 dma.transpose 的目标 shape 与连续 stride。


    功能说明:
    - 按 perm 重排 source shape，并与 target shape 对齐校验。
    - target stride 必须是 target shape 的默认连续 stride；匿名动态 shape 的高维 stride 可保留调用点动态语义表达。

    使用示例:
    - _verify_transpose_layout(source_type, target_type, [1, 0])

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if len(target_type.shape.data) != len(perm_values):
        raise VerifyException("dma.transpose target rank mismatch")
    expected_shape = [source_type.shape.data[index] for index in perm_values]
    for expected_dim, actual_dim in zip(expected_shape, target_type.shape.data, strict=True):
        if not _dims_equal(expected_dim, actual_dim):
            raise VerifyException("dma.transpose target shape mismatch")

    expected_stride = _default_contiguous_stride(target_type.shape)
    for expected_dim, actual_dim in zip(expected_stride, target_type.stride.data, strict=True):
        if not _stride_attrs_equal(expected_dim, actual_dim):
            if _dim_expr_text(expected_dim) == "?" and _static_int_from_dim(actual_dim) is None:
                continue
            raise VerifyException("dma.transpose target stride mismatch")


def _verify_unit_stride_operands(strides: Sequence[SSAValue]) -> None:
    """校验 stride operand 是否全为常量 1。


    功能说明:
    - 当前阶段仅支持单位步长语义。
    - 每个 operand 都必须是值为 `1` 的 `!symbol.int<#symbol.expr<1>>`。

    使用示例:
    - _verify_unit_stride_operands(op.strides)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    for value in strides:
        if _operand_int_value(value) != 1:
            raise VerifyException("dma stride must be 1 in current implementation")


def _element_byte_size(element_type: Attribute) -> int | None:
    """解析 element_type 的字节大小。


    功能说明:
    - 支持 i1/i8/i16/i32/i64 与 f16/bf16/f32/f64。

    使用示例:
    - size = _element_byte_size(Float32Type())

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
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


def _is_i8_byte_pool(memory_type: NnMemoryType) -> bool:
    """判断是否为 i8 一维 byte pool。


    功能说明:
    - 要求 element_type 为 i8，且 rank 为 1。

    使用示例:
    - if _is_i8_byte_pool(mem_type): ...

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if len(memory_type.shape.data) != 1:
        return False
    element_type = memory_type.element_type
    return isinstance(element_type, IntegerType) and int(element_type.width.data) == 8


def _linear_max_index(
    offsets: Sequence[SSAValue],
    shape: Sequence[SSAValue],
    stride: Sequence[SSAValue],
) -> int | None:
    """计算 view 的静态最大线性索引（元素单位）。


    功能说明:
    - 当 offsets/shape/stride 都可静态还原时，返回最大线性索引。
    - 任一值无法静态还原则返回 None。

    使用示例:
    - max_index = _linear_max_index(op.offsets, op.shape, op.stride)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    total = 0
    for offset_value, size_value, stride_value in zip(offsets, shape, stride, strict=True):
        offset_int = _operand_int_value(offset_value)
        size_int = _operand_int_value(size_value)
        stride_int = _operand_int_value(stride_value)
        if offset_int is None or size_int is None or stride_int is None:
            return None
        total += offset_int + (size_int - 1) * stride_int
    return total

def _maybe_numel(shape: ArrayAttr[Attribute]) -> int | None:
    """尝试计算 shape 的元素总数。


    功能说明:
    - 仅在全部维度为静态整数 SymbolExprAttr 时返回乘积。

    使用示例:
    - _maybe_numel(ArrayAttr([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("4")]))

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    numel = 1
    for dim in shape.data:
        value = _static_int_from_dim(dim)
        if value is None:
            return None
        numel *= value
    return numel


def _verify_static_view_bounds(
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
    - _verify_static_view_bounds(source_type.shape, source_type.stride, op.offsets, op.shape, op.stride)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    source_numel = _maybe_numel(source_shape)
    if source_numel is None:
        return
    linear_start = 0
    linear_extent = 0
    for source_step_attr, offset_value, size_value, stride_value in zip(
        source_stride.data, offsets, shape, stride, strict=True
    ):
        source_step = _static_int_from_dim(source_step_attr)
        if source_step is None:
            return
        offset_int = _operand_int_value(offset_value)
        size_int = _operand_int_value(size_value)
        stride_int = _operand_int_value(stride_value)
        if offset_int is None or size_int is None or stride_int is None:
            return
        linear_start += offset_int * source_step
        linear_extent += (size_int - 1) * stride_int * source_step
    if linear_start + linear_extent >= source_numel:
        raise VerifyException("dma.view bounds mismatch")


def _parenthesize_symbol_expr(expr: str) -> str:
    """为乘法组合准备符号表达式文本。

    功能说明:
    - 简单标识符和整数保持原文。
    - 复合表达式加括号，避免 `floordiv`、加减法参与 stride 乘积时改变语义。

    使用示例:
    - text = _parenthesize_symbol_expr("M + 1")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if expr == "?" or expr.replace("_", "").isalnum() or expr.lstrip("-").isdigit():
        return expr
    return f"({expr})"


def _symbol_expr_product(lhs: str, rhs: str) -> str:
    """组合两个 symbol 表达式乘积。

    功能说明:
    - 消除乘以 1 的冗余文本。
    - 对复合表达式加括号，保持默认连续 stride 的符号计算语义。

    使用示例:
    - expr = _symbol_expr_product("M + 1", "N")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if lhs == "1":
        return rhs
    if rhs == "1":
        return lhs
    return f"{_parenthesize_symbol_expr(lhs)}*{_parenthesize_symbol_expr(rhs)}"


def _default_contiguous_stride(shape: ArrayAttr[Attribute]) -> list[Attribute]:
    """按默认连续布局生成行主序 stride。


    功能说明:
    - 静态维度返回 `#symbol.expr<整数>`。
    - 符号维度返回 canonical `#symbol.expr<乘积>`。
    - `#symbol.expr<?>` 维度会把更高维 stride 退化为 `#symbol.expr<?>`。

    使用示例:
    - _default_contiguous_stride(ArrayAttr([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("4")]))

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    stride: list[Attribute] = []
    running: str | None = "1"
    for dim in reversed(shape.data):
        if running is None:
            stride.append(_symbol_expr_attr_from_expr("?"))
        else:
            stride.append(_symbol_expr_attr_from_expr(running))
        if running is None:
            continue
        dim_expr = _dim_expr_text(dim)
        if dim_expr == "?":
            running = None
        elif dim_expr == "1":
            continue
        elif running == "1":
            running = dim_expr
        else:
            running = _dim_expr_text(_symbol_expr_attr_from_expr(_symbol_expr_product(dim_expr, running)))
    stride.reverse()
    return stride


def _parse_symbolic_dim_attr(value: Attribute) -> sp.Basic | None:
    """解析 stride 维度 attribute 为 sympy 表达式。


    功能说明:
    - `SymbolExprAttr` 解析为符号表达式，并为所有标识符创建同名整数符号。
    - `min(...)` 按 `sympy.Min` 解析，用于判定动态尾块连续 stride。
    - 无法解析或未知动态维度时返回 `None`。

    使用示例:
    - _parse_symbolic_dim_attr(SymbolExprAttr.from_expr("KH*KW*TC"))

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if not isinstance(value, SymbolExprAttr):
        return None
    return _parse_symbolic_expr_text(value.expr.data)


def _parse_symbol_value_expr(value: SSAValue) -> sp.Basic | None:
    """解析 `!symbol.int<#symbol.expr<expr>>` operand 为 sympy 表达式。


    功能说明:
    - 仅解析 `SymbolValueType` 的公开表达式文本。
    - 无法解析或未知动态值时返回 `None`，由调用方跳过静态比较。

    使用示例:
    - _parse_symbol_value_expr(op.stride[0])

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if not isinstance(value.type, SymbolValueType):
        return None
    return _parse_symbolic_expr_text(value.type.expr.expr.data)


def _stride_attrs_equal(lhs: Attribute, rhs: Attribute) -> bool:
    """判断两个 stride 维度是否等价。


    功能说明:
    - 优先复用公共维度比较。
    - 当文本不同但表达式等价时，使用 sympy 简化差值判断。

    使用示例:
    - _stride_attrs_equal(SymbolExprAttr.from_expr("TC*KH*KW"), SymbolExprAttr.from_expr("KH*KW*TC"))

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if _dims_equal(lhs, rhs):
        return True
    lhs_expr = _parse_symbolic_dim_attr(lhs)
    rhs_expr = _parse_symbolic_dim_attr(rhs)
    if lhs_expr is None or rhs_expr is None:
        return False
    return sp.simplify(lhs_expr - rhs_expr) == 0


def _verify_view_result_stride(
    source_stride: ArrayAttr[Attribute],
    stride_operands: Sequence[SSAValue],
    result_stride: ArrayAttr[Attribute],
) -> None:
    """校验 dma.view 结果 stride 来自源物理 stride 与逻辑 stride 的乘积。


    功能说明:
    - 对可解析维度执行 `result_stride == source_stride * stride_operand` 比较。
    - 含未知 `?` 或不可解析符号时跳过该维静态比较，保留动态 IR 表达能力。

    使用示例:
    - _verify_view_result_stride(source_type.stride, op.stride, result_type.stride)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    for source_attr, stride_value, result_attr in zip(source_stride.data, stride_operands, result_stride.data, strict=True):
        source_expr = _parse_symbolic_dim_attr(source_attr)
        stride_expr = _parse_symbol_value_expr(stride_value)
        result_expr = _parse_symbolic_dim_attr(result_attr)
        if source_expr is None or stride_expr is None or result_expr is None:
            continue
        if sp.simplify(result_expr - (source_expr * stride_expr)) != 0:
            raise VerifyException("stride must match source physical stride * view stride")


def _is_contiguous(memory_type: NnMemoryType) -> bool:
    """检查 memory type 是否连续行主序。


    功能说明:
    - 静态 stride 直接比较整数。
    - 符号 stride 使用表达式等价判断，允许乘法因子顺序不同。
    - 由匿名动态 shape 推导出的未知高维 stride 接受动态语义表达，保留调用点变量名。

    使用示例:
    - _is_contiguous(memory_type)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    expected = _default_contiguous_stride(memory_type.shape)
    if len(expected) != len(memory_type.stride.data):
        return False
    for expected_dim, stride_dim in zip(expected, memory_type.stride.data, strict=True):
        if not _stride_attrs_equal(expected_dim, stride_dim):
            if _dim_expr_text(expected_dim) == "?" and _static_int_from_dim(stride_dim) is None:
                continue
            return False
    return True


def _verify_default_contiguous_stride(memory_type: NnMemoryType, message: str) -> None:
    """校验 memory type 的 stride 是否匹配默认连续布局。


    功能说明:
    - 根据 `shape` 生成默认连续布局。
    - 要求 `stride` 与默认布局完全一致。

    使用示例:
    - _verify_default_contiguous_stride(result_type, "dma.alloc requires contiguous result stride")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if not _is_contiguous(memory_type):
        raise VerifyException(message)


@irdl_op_definition
class DmaAllocOp(IRDLOperation):
    """dma.alloc。"""

    name = "dma.alloc"

    dynamic_shape = var_operand_def(SymbolValueType)
    result = result_def(NnMemoryType)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        dynamic_shape: Sequence[SSAValue],
        result_type: NnMemoryType,
    ) -> None:
        """初始化 dma.alloc。


        功能说明:
        - 设置动态 shape operand 与结果类型。

        使用示例:
        - DmaAllocOp(dynamic_shape, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[dynamic_shape], result_types=[result_type])

    def verify_(self) -> None:
        """校验 dma.alloc。


        功能说明:
        - 结果类型必须为 nn.memory。
        - dynamic_shape 支持空列表（全静态 shape）、全量 rank 列表或仅符号维度列表。
        - stride 按结果类型显式指定，不再额外限制布局。

        使用示例:
        - DmaAllocOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        result_type = _verify_memory_type(self.result.type, "result")
        dynamic_shape = _verify_symbol_int_operands(self.dynamic_shape, "dynamic_shape", min_value=0)
        _verify_dynamic_shape_matches_result(dynamic_shape, result_type.shape, "dynamic_shape")


@irdl_op_definition
class DmaFillOp(IRDLOperation):
    """dma.fill。"""

    name = "dma.fill"

    target = operand_def(NnMemoryType)
    value = operand_def(Attribute)

    def __init__(self, target: SSAValue | Operation, value: SSAValue | Operation) -> None:
        """初始化 dma.fill。


        功能说明:
        - 设置被写入的 `target` memory 与标量 `value` operand。

        使用示例:
        - DmaFillOp(target, value)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[target, value])

    def verify_(self) -> None:
        """校验 dma.fill。


        功能说明:
        - `target` 必须为 `!nn.memory<..., i32, ...>`。
        - `value` 当前仅允许 builtin `i32` 或 `!symbol.int<#symbol.expr<expr>>`。

        使用示例:
        - DmaFillOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        target_type = _verify_memory_operand(self.target, "target")
        if target_type.element_type != i32:
            raise VerifyException("dma.fill target element_type must be i32")
        _verify_fill_value_operand(self.value, "value")


@irdl_op_definition
class DmaFreeOp(IRDLOperation):
    """dma.free。"""

    name = "dma.free"

    source = operand_def(NnMemoryType)

    def __init__(self, source: SSAValue | Operation) -> None:
        """初始化 dma.free。


        功能说明:
        - 设置待释放的 source operand。

        使用示例:
        - DmaFreeOp(source)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[source])

    def verify_(self) -> None:
        """校验 dma.free。


        功能说明:
        - source 必须为 nn.memory。

        使用示例:
        - DmaFreeOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        _verify_memory_operand(self.source, "source")


@irdl_op_definition
class DmaCopyOp(IRDLOperation):
    """dma.copy。"""

    name = "dma.copy"

    target = operand_def(NnMemoryType)
    source = operand_def(NnMemoryType)

    def __init__(self, target: SSAValue | Operation, source: SSAValue | Operation) -> None:
        """初始化 dma.copy。


        功能说明:
        - 设置 target 与 source operand。

        使用示例:
        - DmaCopyOp(target, source)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[target, source])

    def verify_(self) -> None:
        """校验 dma.copy。


        功能说明:
        - source/target 的 shape/stride/element_type 必须一致。

        使用示例:
        - DmaCopyOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        source_type = _verify_memory_type(self.source.type, "source")
        target_type = _verify_memory_type(self.target.type, "target")
        if source_type.shape != target_type.shape:
            raise VerifyException("dma.copy source/target shape mismatch")
        if source_type.stride != target_type.stride:
            raise VerifyException("dma.copy source/target stride mismatch")
        if source_type.element_type != target_type.element_type:
            raise VerifyException("dma.copy source/target element_type mismatch")


@irdl_op_definition
class DmaBroadcastOp(IRDLOperation):
    """dma.broadcast。"""

    name = "dma.broadcast"

    target = operand_def(NnMemoryType)
    source = operand_def(Attribute)

    def __init__(self, target: SSAValue | Operation, source: SSAValue | Operation) -> None:
        """初始化 dma.broadcast。


        功能说明:
        - 设置 target 与 source operand。

        使用示例:
        - DmaBroadcastOp(target, source)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[target, source])

    def verify_(self) -> None:
        """校验 dma.broadcast。


        功能说明:
        - target 必须为 nn.memory。
        - memory source 需满足 element_type/space 与 broadcast 规则。
        - scalar source 必须与 target.element_type 类型一致，或为整数场景的 symbol.int。

        使用示例:
        - DmaBroadcastOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        target_type = _verify_memory_type(self.target.type, "target")
        source_value = SSAValue.get(self.source)
        source_type = source_value.type

        if isinstance(source_type, NnMemoryType):
            source_type = _verify_memory_type(source_type, "source")
            if source_type.element_type != target_type.element_type:
                raise VerifyException("dma.broadcast element_type mismatch")
            if source_type.space.space.data != target_type.space.space.data:
                raise VerifyException("dma.broadcast space mismatch")
            _verify_broadcast_compat(source_type.shape, target_type.shape)
            return

        if isinstance(source_type, SymbolValueType):
            if not isinstance(target_type.element_type, IntegerType):
                raise VerifyException("dma.broadcast symbol.int target must be integer element_type")
            return

        if source_type != target_type.element_type:
            raise VerifyException("dma.broadcast scalar type mismatch")


@irdl_op_definition
class DmaTransposeOp(IRDLOperation):
    """dma.transpose。"""

    name = "dma.transpose"

    target = operand_def(NnMemoryType)
    source = operand_def(NnMemoryType)
    perm = attr_def(ArrayAttr)

    def __init__(
        self,
        target: SSAValue | Operation,
        source: SSAValue | Operation,
        perm: Sequence[int] | ArrayAttr,
    ) -> None:
        """初始化 dma.transpose。


        功能说明:
        - 设置 target/source operand 与 perm 属性。

        使用示例:
        - DmaTransposeOp(target, source, perm=[1, 0])

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        perm_attr = perm if isinstance(perm, ArrayAttr) else ArrayAttr([IntAttr(value) for value in perm])
        super().__init__(operands=[target, source], attributes={"perm": perm_attr})

    def verify_(self) -> None:
        """校验 dma.transpose。


        功能说明:
        - target/source 必须为 nn.memory。
        - element_type 与 space 必须一致。
        - perm 必须是 0..rank-1 的排列，target shape 为 source 的重排。
        - target stride 必须是 target shape 的默认连续 stride。

        使用示例:
        - DmaTransposeOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        target_type = _verify_memory_type(self.target.type, "target")
        source_type = _verify_memory_type(self.source.type, "source")
        if target_type.element_type != source_type.element_type:
            raise VerifyException("dma.transpose element_type mismatch")
        if target_type.space.space.data != source_type.space.space.data:
            raise VerifyException("dma.transpose space mismatch")
        perm_values = _verify_transpose_perm(self.perm, len(source_type.shape.data))
        _verify_transpose_layout(source_type, target_type, perm_values)


@irdl_op_definition
class DmaLoadOp(IRDLOperation):
    """dma.load。"""

    name = "dma.load"

    target = operand_def(NnMemoryType)
    source = operand_def(NnMemoryType)
    offsets = var_operand_def(Attribute)
    sizes = var_operand_def(SymbolValueType)
    strides = var_operand_def(SymbolValueType)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        target: SSAValue | Operation,
        source: SSAValue | Operation,
        offsets: Sequence[SSAValue],
        sizes: Sequence[SSAValue],
        strides: Sequence[SSAValue],
    ) -> None:
        """初始化 dma.load。


        功能说明:
        - 设置 target/source 与 offsets/sizes/strides。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaLoadOp(target, source, offsets, sizes, strides)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(
            operands=[target, source, offsets, sizes, strides],
        )

    def verify_(self) -> None:
        """校验 dma.load。


        功能说明:
        - offsets/sizes/strides 长度与 source rank 一致。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。
        - target.shape == sizes 且 element_type 一致。

        使用示例:
        - DmaLoadOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        target_type = _verify_memory_type(self.target.type, "target")
        source_type = _verify_memory_type(self.source.type, "source")
        offsets = _verify_symbol_index_operands(self.offsets, "offsets", min_value=0)
        sizes = _verify_symbol_int_operands(self.sizes, "sizes", min_value=1)
        strides = _verify_symbol_int_operands(self.strides, "strides", min_value=1)
        rank = len(source_type.shape.data)
        if len(target_type.shape.data) != rank:
            raise VerifyException("dma.load target rank must match source rank")
        _verify_rank_match(offsets, rank, "offsets")
        _verify_rank_match(sizes, rank, "sizes")
        _verify_rank_match(strides, rank, "strides")
        _verify_unit_stride_operands(strides)
        _verify_operands_match_layout(sizes, target_type.shape, "target shape must match sizes")
        if source_type.element_type != target_type.element_type:
            raise VerifyException("dma.load element_type mismatch")


@irdl_op_definition
class DmaStoreOp(IRDLOperation):
    """dma.store。"""

    name = "dma.store"

    target = operand_def(NnMemoryType)
    source = operand_def(NnMemoryType)
    offsets = var_operand_def(Attribute)
    sizes = var_operand_def(SymbolValueType)
    strides = var_operand_def(SymbolValueType)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        target: SSAValue | Operation,
        source: SSAValue | Operation,
        offsets: Sequence[SSAValue],
        sizes: Sequence[SSAValue],
        strides: Sequence[SSAValue],
    ) -> None:
        """初始化 dma.store。


        功能说明:
        - 设置 target/source 与 offsets/sizes/strides。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaStoreOp(target, source, offsets, sizes, strides)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[target, source, offsets, sizes, strides])

    def verify_(self) -> None:
        """校验 dma.store。


        功能说明:
        - source.shape 必须与 sizes 对齐。
        - offsets/sizes/strides 长度与 target rank 一致。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaStoreOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        source_type = _verify_memory_type(self.source.type, "source")
        target_type = _verify_memory_type(self.target.type, "target")
        offsets = _verify_symbol_index_operands(self.offsets, "offsets", min_value=0)
        sizes = _verify_symbol_int_operands(self.sizes, "sizes", min_value=1)
        strides = _verify_symbol_int_operands(self.strides, "strides", min_value=1)
        rank = len(target_type.shape.data)
        _verify_rank_match(offsets, rank, "offsets")
        _verify_rank_match(sizes, rank, "sizes")
        _verify_rank_match(strides, rank, "strides")
        _verify_unit_stride_operands(strides)
        _verify_operands_match_layout(sizes, source_type.shape, "source shape must match sizes")
        if source_type.element_type != target_type.element_type:
            raise VerifyException("dma.store element_type mismatch")


@irdl_op_definition
class DmaSliceOp(IRDLOperation):
    """dma.slice。"""

    name = "dma.slice"

    target = operand_def(NnMemoryType)
    source = operand_def(NnMemoryType)
    offsets = var_operand_def(Attribute)
    sizes = var_operand_def(SymbolValueType)
    strides = var_operand_def(SymbolValueType)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        target: SSAValue | Operation,
        source: SSAValue | Operation,
        offsets: Sequence[SSAValue],
        sizes: Sequence[SSAValue],
        strides: Sequence[SSAValue],
    ) -> None:
        """初始化 dma.slice。


        功能说明:
        - 设置 target/source 与 offsets/sizes/strides。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaSliceOp(target, source, offsets, sizes, strides)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[target, source, offsets, sizes, strides])

    def verify_(self) -> None:
        """校验 dma.slice。


        功能说明:
        - offsets/sizes/strides 长度与 source rank 一致。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。
        - target.shape == sizes 且 target/source element_type 一致。
        - 当前阶段 stride 必须为 1。

        使用示例:
        - DmaSliceOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        target_type = _verify_memory_type(self.target.type, "target")
        source_type = _verify_memory_type(self.source.type, "source")
        offsets = _verify_symbol_index_operands(self.offsets, "offsets", min_value=0)
        sizes = _verify_symbol_int_operands(self.sizes, "sizes", min_value=1)
        strides = _verify_symbol_int_operands(self.strides, "strides", min_value=1)
        rank = len(source_type.shape.data)
        if len(target_type.shape.data) != rank:
            raise VerifyException("dma.slice target rank must match source rank")
        _verify_rank_match(offsets, rank, "offsets")
        _verify_rank_match(sizes, rank, "sizes")
        _verify_rank_match(strides, rank, "strides")
        _verify_unit_stride_operands(strides)
        _verify_operands_match_layout(sizes, target_type.shape, "shape must match sizes")
        if source_type.element_type != target_type.element_type:
            raise VerifyException("dma.slice element_type mismatch")


@irdl_op_definition
class DmaDesliceOp(IRDLOperation):
    """dma.deslice。"""

    name = "dma.deslice"

    target = operand_def(NnMemoryType)
    source = operand_def(NnMemoryType)
    offsets = var_operand_def(Attribute)
    sizes = var_operand_def(SymbolValueType)
    strides = var_operand_def(SymbolValueType)
    result = result_def(NnMemoryType)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        target: SSAValue | Operation,
        source: SSAValue | Operation,
        offsets: Sequence[SSAValue],
        sizes: Sequence[SSAValue],
        strides: Sequence[SSAValue],
        result_type: NnMemoryType,
    ) -> None:
        """初始化 dma.deslice。


        功能说明:
        - 设置 target/source、offsets/sizes/strides 与结果类型。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaDesliceOp(target, source, offsets, sizes, strides, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(
            operands=[target, source, offsets, sizes, strides],
            result_types=[result_type],
        )

    def verify_(self) -> None:
        """校验 dma.deslice。


        功能说明:
        - source.shape 必须与 sizes 对齐。
        - offsets/sizes/strides 长度与 target rank 一致。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。
        - result type 必须与 target type 一致。

        使用示例:
        - DmaDesliceOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        source_type = _verify_memory_type(self.source.type, "source")
        target_type = _verify_memory_type(self.target.type, "target")
        result_type = _verify_memory_type(self.result.type, "result")
        offsets = _verify_symbol_index_operands(self.offsets, "offsets", min_value=0)
        sizes = _verify_symbol_int_operands(self.sizes, "sizes", min_value=1)
        strides = _verify_symbol_int_operands(self.strides, "strides", min_value=1)
        rank = len(target_type.shape.data)
        _verify_rank_match(offsets, rank, "offsets")
        _verify_rank_match(sizes, rank, "sizes")
        _verify_rank_match(strides, rank, "strides")
        _verify_unit_stride_operands(strides)
        _verify_operands_match_layout(sizes, source_type.shape, "source shape must match sizes")
        if source_type.element_type != target_type.element_type:
            raise VerifyException("dma.deslice element_type mismatch")
        if result_type != target_type:
            raise VerifyException("dma.deslice result must match target type")


@irdl_op_definition
class DmaViewOp(IRDLOperation):
    """dma.view。"""

    name = "dma.view"

    source = operand_def(NnMemoryType)
    offsets = var_operand_def(Attribute)
    shape = var_operand_def(SymbolValueType)
    stride = var_operand_def(SymbolValueType)
    result = result_def(NnMemoryType)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        source: SSAValue | Operation,
        offsets: Sequence[SSAValue],
        shape: Sequence[SSAValue],
        stride: Sequence[SSAValue],
        result_type: NnMemoryType,
    ) -> None:
        """初始化 dma.view。


        功能说明:
        - 设置 source、动态 offsets/shape/stride operand 与结果类型。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaViewOp(source, offsets, shape, stride, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        if not isinstance(result_type, NnMemoryType):
            raise TypeError("result_type must be nn.memory")

        super().__init__(operands=[source, offsets, shape, stride], result_types=[result_type])

    def verify_(self) -> None:
        """校验 dma.view。


        功能说明:
        - `space` 必须一致；`element_type` 必须一致（i8 byte pool 允许不同 element_type）。
        - 非 byte pool 场景下 source/result rank 必须一致；byte pool 允许 rank 不一致。
        - `offsets` 允许 `!symbol.int` 与 `!symbol.iter`，`shape`/`stride` 仍需 `!symbol.int`。
        - `offsets`/`shape`/`stride` 长度与结果 rank 一致。
        - 非 byte pool 场景下，结果 stride 必须等于 source physical stride 与 view logical stride 的逐维乘积。
        - 当边界可静态判定时，必须满足 `offset + (size - 1) * stride < dim`。
        - 非 byte pool 场景下可判定 numel 不一致必须报错；byte pool 需满足 typed 子区间字节边界可达。

        使用示例:
        - DmaViewOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        source_type = _verify_memory_type(self.source.type, "source")
        result_type = _verify_memory_type(self.result.type, "result")
        offsets = _verify_symbol_index_operands(self.offsets, "offsets", min_value=0)
        shape = _verify_symbol_int_operands(self.shape, "shape", min_value=1)
        stride = _verify_symbol_int_operands(self.stride, "stride", min_value=1)
        rank = len(result_type.shape.data)
        if len(source_type.shape.data) != rank and not _is_i8_byte_pool(source_type):
            raise VerifyException("dma.view source/result rank mismatch")
        _verify_rank_match(offsets, rank, "offsets")
        _verify_rank_match(shape, rank, "shape")
        _verify_rank_match(stride, rank, "stride")
        _verify_operands_match_layout(shape, result_type.shape, "shape must match result shape")
        if source_type.space.space.data != result_type.space.space.data:
            raise VerifyException("dma.view space mismatch")

        source_numel = _maybe_numel(source_type.shape)
        result_numel = _maybe_numel(result_type.shape)
        if _is_i8_byte_pool(source_type):
            _verify_operands_match_layout(stride, result_type.stride, "stride must match result stride")
            result_elem_size = _element_byte_size(result_type.element_type)
            if result_elem_size is None:
                raise VerifyException("dma.view element_type unsupported for byte pool")
            max_index = _linear_max_index(offsets, shape, stride)
            if max_index is not None and source_numel is not None:
                byte_end = (max_index + 1) * result_elem_size
                if byte_end > source_numel:
                    raise VerifyException("dma.view byte bounds mismatch")
        else:
            _verify_view_result_stride(source_type.stride, stride, result_type.stride)
            if source_type.element_type != result_type.element_type:
                raise VerifyException("dma.view element_type mismatch")
            if source_numel is not None and result_numel is not None and source_numel != result_numel:
                raise VerifyException("dma.view numel mismatch")
            _verify_static_view_bounds(source_type.shape, source_type.stride, offsets, shape, stride)


@irdl_op_definition
class DmaSubviewOp(IRDLOperation):
    """dma.subview。"""

    name = "dma.subview"

    source = var_operand_def(NnMemoryType)
    offset = var_operand_def(SymbolValueType)
    size = var_operand_def(SymbolValueType)
    stride = var_operand_def(SymbolValueType)
    result = result_def(NnMemoryType)

    irdl_options = (AttrSizedOperandSegments(as_property=True),)

    def __init__(
        self,
        source: SSAValue | Operation,
        offset: SSAValue | Operation,
        size: SSAValue | Operation,
        stride: SSAValue | Operation,
        result_type: NnMemoryType,
    ) -> None:
        """初始化 dma.subview。


        功能说明:
        - 设置一维 i8 backing memory、元素单位 offset/size/stride 与一维 typed result。
        - `offset/size/stride` 均为单个 `!symbol.int<#symbol.expr<expr>>` operand。

        使用示例:
        - DmaSubviewOp(pool, offset, size, stride, flat_result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        if not isinstance(result_type, NnMemoryType):
            raise TypeError("result_type must be nn.memory")

        super().__init__(
            operands=[[source], [offset], [size], [stride]],
            result_types=[result_type],
        )

    def verify_(self) -> None:
        """校验 dma.subview。


        功能说明:
        - source 必须是一维 i8 backing memory。
        - result 必须是一维 contiguous typed memory，且 space 与 source 一致。
        - offset/size/stride 都必须是单个 `!symbol.int<#symbol.expr<expr>>`；size 必须匹配 result flat shape。

        使用示例:
        - DmaSubviewOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        if len(self.source) != 1 or len(self.offset) != 1 or len(self.size) != 1 or len(self.stride) != 1:
            raise VerifyException("dma.subview requires one source, offset, size and stride")

        source_type = _verify_memory_type(self.source[0].type, "source")
        result_type = _verify_memory_type(self.result.type, "result")
        offset = _verify_symbol_int_operands(self.offset, "offset", min_value=0)[0]
        size = _verify_symbol_int_operands(self.size, "size", min_value=1)[0]
        stride = _verify_symbol_int_operands(self.stride, "stride", min_value=1)[0]

        if not _is_i8_byte_pool(source_type):
            raise VerifyException("dma.subview source must be one-dimensional i8 memory")
        if len(result_type.shape.data) != 1:
            raise VerifyException("dma.subview result must be one-dimensional")
        if len(result_type.stride.data) != 1:
            raise VerifyException("dma.subview result stride rank must be one")
        if source_type.space.space.data != result_type.space.space.data:
            raise VerifyException("dma.subview space mismatch")

        _verify_default_contiguous_stride(result_type, "dma.subview result must be contiguous")
        _verify_operands_match_layout([size], result_type.shape, "dma.subview size must match result shape")

        source_numel = _maybe_numel(source_type.shape)
        result_numel = _maybe_numel(result_type.shape)
        result_elem_size = _element_byte_size(result_type.element_type)
        if result_elem_size is None:
            raise VerifyException("dma.subview result element_type unsupported")
        offset_int = _operand_int_value(offset)
        size_int = _operand_int_value(size)
        stride_int = _operand_int_value(stride)
        if (
            source_numel is not None
            and result_numel is not None
            and offset_int is not None
            and size_int is not None
            and stride_int is not None
        ):
            byte_end = (offset_int + (size_int - 1) * stride_int + 1) * result_elem_size
            if byte_end > source_numel:
                raise VerifyException("dma.subview byte bounds mismatch")


@irdl_op_definition
class DmaReshapeOp(IRDLOperation):
    """dma.reshape。"""

    name = "dma.reshape"

    source = operand_def(NnMemoryType)
    shape = var_operand_def(SymbolValueType)
    result = result_def(NnMemoryType)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        source: SSAValue | Operation,
        shape: Sequence[SSAValue],
        result_type: NnMemoryType,
    ) -> None:
        """初始化 dma.reshape。


        功能说明:
        - 设置 source、动态 shape operand 与结果类型。

        使用示例:
        - DmaReshapeOp(source, shape, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[source, shape], result_types=[result_type])

    def verify_(self) -> None:
        """校验 dma.reshape。


        功能说明:
        - element_type/space 必须一致。
        - source 必须连续，result.stride 必须为连续行主序。
        - 可判定 numel 不一致必须报错。

        使用示例:
        - DmaReshapeOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        source_type = _verify_memory_type(self.source.type, "source")
        result_type = _verify_memory_type(self.result.type, "result")
        shape = _verify_symbol_int_operands(self.shape, "shape", min_value=1)
        _verify_rank_match(shape, len(result_type.shape.data), "shape")
        _verify_operands_match_layout(shape, result_type.shape, "shape must match result shape")
        if source_type.element_type != result_type.element_type:
            raise VerifyException("dma.reshape element_type mismatch")
        if source_type.space.space.data != result_type.space.space.data:
            raise VerifyException("dma.reshape space mismatch")

        source_numel = _maybe_numel(source_type.shape)
        result_numel = _maybe_numel(result_type.shape)
        if source_numel is not None and result_numel is not None and source_numel != result_numel:
            raise VerifyException("dma.reshape numel mismatch")

        if not _is_contiguous(source_type):
            raise VerifyException("dma.reshape requires contiguous source")

        _verify_default_contiguous_stride(result_type, "dma.reshape requires contiguous result stride")


@irdl_op_definition
class DmaCastOp(IRDLOperation):
    """dma.cast。"""

    name = "dma.cast"

    target = operand_def(NnMemoryType)
    source = operand_def(NnMemoryType)

    def __init__(self, target: SSAValue | Operation, source: SSAValue | Operation) -> None:
        """初始化 dma.cast。


        功能说明:
        - 设置 target 与 source。

        使用示例:
        - DmaCastOp(target, source)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[target, source])

    def verify_(self) -> None:
        """校验 dma.cast。


        功能说明:
        - target/source 的 shape/stride/space 必须一致，仅 element_type 可变化。

        使用示例:
        - DmaCastOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        target_type = _verify_memory_type(self.target.type, "target")
        source_type = _verify_memory_type(self.source.type, "source")
        if source_type.shape != target_type.shape:
            raise VerifyException("dma.cast shape mismatch")
        if source_type.stride != target_type.stride:
            raise VerifyException("dma.cast stride mismatch")
        if source_type.space.space.data != target_type.space.space.data:
            raise VerifyException("dma.cast space mismatch")


class Dma(Dialect):
    """DMA dialect 入口。


    功能说明:
    - 注册 dma dialect 的 op 定义。

    使用示例:
    - ctx.load_dialect(Dma)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    name = "dma"
    operations = [
        DmaAllocOp,
        DmaFillOp,
        DmaFreeOp,
        DmaCopyOp,
        DmaBroadcastOp,
        DmaTransposeOp,
        DmaLoadOp,
        DmaStoreOp,
        DmaSliceOp,
        DmaDesliceOp,
        DmaSubviewOp,
        DmaViewOp,
        DmaReshapeOp,
        DmaCastOp,
    ]
    attributes = []


__all__ = [
    "Dma",
    "DmaAllocOp",
    "DmaFillOp",
    "DmaFreeOp",
    "DmaCopyOp",
    "DmaBroadcastOp",
    "DmaTransposeOp",
    "DmaLoadOp",
    "DmaStoreOp",
    "DmaSliceOp",
    "DmaDesliceOp",
    "DmaSubviewOp",
    "DmaViewOp",
    "DmaReshapeOp",
    "DmaCastOp",
]
