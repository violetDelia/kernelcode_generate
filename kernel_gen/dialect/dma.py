"""DMA dialect definitions.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 定义 dma dialect 的 alloc/fill/copy/load/store/slice/deslice/view/reshape/cast/broadcast op 与 verifier 规则。
- 复用 nn dialect 的 NnMemoryType 与 NnMemorySpaceAttr。

使用示例:
- from kernel_gen.dialect.dma import Dma, DmaCopyOp

关联文件:
- spec: spec/dialect/dma.md
- test: test/dialect/test_dma_dialect.py
- 功能实现: kernel_gen/dialect/dma.py
"""

from __future__ import annotations

from collections.abc import Sequence

from xdsl.dialects.builtin import (
    ArrayAttr,
    BFloat16Type,
    Float16Type,
    Float32Type,
    Float64Type,
    IntAttr,
    IntegerAttr,
    IntegerType,
    StringAttr,
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

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolIterType, SymbolValueType


def _verify_memory_type(value: Attribute, field_name: str) -> NnMemoryType:
    """校验并返回 nn.memory type。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 确认类型为 nn.memory 并触发类型校验。

    使用示例:
    - _verify_memory_type(op.source.type, "source")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if not isinstance(value, NnMemoryType):
        raise VerifyException(f"{field_name} must be nn.memory")
    value.verify()
    return value


def _verify_memory_operand(value: SSAValue, field_name: str) -> NnMemoryType:
    """校验 SSA operand 为 nn.memory type。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一处理 SSA operand 的 nn.memory 类型校验与内部验证。

    使用示例:
    - _verify_memory_operand(op.source, "source")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    return _verify_memory_type(value.type, field_name)


def _verify_fill_value_operand(value: SSAValue, field_name: str) -> SSAValue:
    """校验 `dma.fill` 的整数标量 operand。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 当前仅接受 builtin `i32` 或 `!symbol.int<"expr">`。
    - 若为 `!symbol.int<"expr">`，同步触发其类型校验。

    使用示例:
    - _verify_fill_value_operand(op.value, "value")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if value.type == i32:
        return value
    if isinstance(value.type, SymbolValueType):
        value.type.verify()
        return value
    raise VerifyException(f"{field_name} must be builtin i32 or !symbol.int")


def _operand_int_value(value: SSAValue) -> int | None:
    """尝试从 `!symbol.int<"expr">` SSA operand 恢复静态整型值。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅识别字面量整数表达式，例如 `!symbol.int<"4">`。
    - `!symbol.iter<start = "...", end = "...", step = "...">` 视为运行期值，不参与静态比较。

    使用示例:
    - _operand_int_value(op.sizes[0])

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
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
    """校验 `!symbol.int<"expr">` operand 列表。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 确保所有 operand 类型为 `!symbol.int<"expr">`。
    - 若 operand 可静态恢复为整型常量，则施加最小值约束。

    使用示例:
    - _verify_symbol_int_operands(op.sizes, "sizes", min_value=1)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
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

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 确保 operand 类型为 `!symbol.int` 或 `!symbol.iter`。
    - 若 operand 可静态恢复为整型常量，则施加最小值约束。

    使用示例:
    - _verify_symbol_index_operands(op.offsets, "offsets", min_value=0)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
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

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 用于验证切片大小与 shape 的对应关系。

    使用示例:
    - _verify_rank_match(offsets, rank, "offsets")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if len(values) != rank:
        raise VerifyException(f"{field_name} length must match rank")


def _verify_operands_match_layout(
    values: Sequence[SSAValue],
    layout: ArrayAttr[Attribute],
    mismatch_message: str,
) -> None:
    """校验 operand 列表与类型中可静态判定的布局一致。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 若布局维度为 `IntAttr`，对应 operand 必须是相同值的 `!symbol.int<"n">`。
    - 若布局维度为符号属性，则只要求存在 `!symbol.int<"expr">` SSA operand。

    使用示例:
    - _verify_operands_match_layout(op.sizes, result_type.shape, "shape must match sizes")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    for value, expected in zip(values, layout.data, strict=True):
        if isinstance(expected, IntAttr):
            static_value = _operand_int_value(value)
            if static_value != expected.data:
                raise VerifyException(mismatch_message)


def _verify_dynamic_shape_matches_result(
    dynamic_shape: Sequence[SSAValue],
    result_shape: ArrayAttr[Attribute],
    field_name: str,
) -> None:
    """校验 dma.alloc 的 dynamic_shape 与结果 shape 的一致性。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持两种形态：
      1) dynamic_shape 与结果 rank 等长，逐维对齐；
      2) dynamic_shape 仅包含符号维度，按出现顺序对齐。
    - 匿名维度 `?` 仍不允许出现在结果 shape。

    使用示例:
    - _verify_dynamic_shape_matches_result(dynamic_shape, result_type.shape, "dynamic_shape")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    rank = len(result_shape.data)
    if len(dynamic_shape) == rank:
        _verify_rank_match(dynamic_shape, rank, field_name)
        _verify_operands_match_layout(dynamic_shape, result_shape, f"{field_name} must match result shape")
        return

    symbol_dims: list[str] = []
    for dim in result_shape.data:
        if isinstance(dim, IntAttr):
            continue
        if isinstance(dim, StringAttr):
            if dim.data == "?":
                raise VerifyException(f"{field_name} must not contain '?'")
            symbol_dims.append(dim.data)
            continue
        raise VerifyException(f"{field_name} entries must be IntAttr or StringAttr")

    if len(dynamic_shape) != len(symbol_dims):
        raise VerifyException(f"{field_name} length must match symbol rank")

    for value, expected in zip(dynamic_shape, symbol_dims, strict=True):
        if not isinstance(value.type, SymbolValueType):
            raise VerifyException(f"{field_name} entries must be !symbol.int")
        if value.type.get_value() != expected:
            raise VerifyException(f"{field_name} symbol must match result shape")


def _verify_broadcast_compat(
    source_shape: ArrayAttr[Attribute],
    target_shape: ArrayAttr[Attribute],
) -> None:
    """校验 dma.broadcast 的 shape 兼容性。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 按尾维对齐规则检查 source/target shape。
    - 仅在静态整数维度冲突时失败，符号维度不做数值求解。

    使用示例:
    - _verify_broadcast_compat(source_type.shape, target_type.shape)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    source_dims = source_shape.data
    target_dims = target_shape.data
    if len(source_dims) > len(target_dims):
        raise VerifyException("dma.broadcast source rank must be <= target rank")

    for offset in range(1, len(target_dims) + 1):
        target_dim = target_dims[-offset]
        source_dim = source_dims[-offset] if offset <= len(source_dims) else IntAttr(1)
        if isinstance(source_dim, IntAttr) and isinstance(target_dim, IntAttr):
            if (
                source_dim.data != target_dim.data
                and source_dim.data != 1
                and target_dim.data != 1
            ):
                raise VerifyException("dma.broadcast shape mismatch")


def _dims_equal(lhs: Attribute, rhs: Attribute) -> bool:
    """判断 shape/stride 维度是否一致。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 IntAttr 与 StringAttr 的值一致性判断。
    - 其他类型统一视为不一致。

    使用示例:
    - _dims_equal(IntAttr(2), IntAttr(2))

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if isinstance(lhs, IntAttr) and isinstance(rhs, IntAttr):
        return lhs.data == rhs.data
    if isinstance(lhs, StringAttr) and isinstance(rhs, StringAttr):
        return lhs.data == rhs.data
    return False


def _verify_transpose_perm(perm: ArrayAttr, rank: int) -> list[int]:
    """校验 dma.transpose 的 perm 合法性并返回序列。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 校验 perm 长度与 rank 一致。
    - 校验 perm 为 0..rank-1 的排列。

    使用示例:
    - _verify_transpose_perm(ArrayAttr([IntAttr(1), IntAttr(0)]), rank=2)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
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
    """校验 dma.transpose 的 shape/stride 是否按 perm 重排。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 按 perm 重排 source shape/stride，并与 target 对齐校验。

    使用示例:
    - _verify_transpose_layout(source_type, target_type, [1, 0])

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if len(target_type.shape.data) != len(perm_values):
        raise VerifyException("dma.transpose target rank mismatch")
    expected_shape = [source_type.shape.data[index] for index in perm_values]
    for expected_dim, actual_dim in zip(expected_shape, target_type.shape.data, strict=True):
        if not _dims_equal(expected_dim, actual_dim):
            raise VerifyException("dma.transpose target shape mismatch")

    expected_stride = [source_type.stride.data[index] for index in perm_values]
    for expected_dim, actual_dim in zip(expected_stride, target_type.stride.data, strict=True):
        if not _dims_equal(expected_dim, actual_dim):
            raise VerifyException("dma.transpose target stride mismatch")


def _verify_unit_stride_operands(strides: Sequence[SSAValue]) -> None:
    """校验 stride operand 是否全为常量 1。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 当前阶段仅支持单位步长语义。
    - 每个 operand 都必须是值为 `1` 的 `!symbol.int<"1">`。

    使用示例:
    - _verify_unit_stride_operands(op.strides)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    for value in strides:
        if _operand_int_value(value) != 1:
            raise VerifyException("dma stride must be 1 in current implementation")


def _element_byte_size(element_type: Attribute) -> int | None:
    """解析 element_type 的字节大小。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 i1/i8/i16/i32/i64 与 f16/bf16/f32/f64。

    使用示例:
    - size = _element_byte_size(Float32Type())

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
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

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 要求 element_type 为 i8，且 rank 为 1。

    使用示例:
    - if _is_i8_byte_pool(mem_type): ...

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
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

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 当 offsets/shape/stride 都可静态还原时，返回最大线性索引。
    - 任一值无法静态还原则返回 None。

    使用示例:
    - max_index = _linear_max_index(op.offsets, op.shape, op.stride)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    total = 0
    for offset_value, size_value, stride_value in zip(offsets, shape, stride, strict=True):
        offset_int = _operand_int_value(offset_value)
        size_int = _operand_int_value(size_value)
        stride_int = _operand_int_value(stride_value)
        if offset_int is None or size_int is None or stride_int is None:
            return None
        total += (offset_int + size_int - 1) * stride_int
    return total

def _maybe_numel(shape: ArrayAttr[Attribute]) -> int | None:
    """尝试计算 shape 的元素总数。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅在全部维度为 IntAttr 时返回乘积。

    使用示例:
    - _maybe_numel(ArrayAttr([IntAttr(2), IntAttr(4)]))

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    numel = 1
    for dim in shape.data:
        if not isinstance(dim, IntAttr):
            return None
        numel *= dim.data
    return numel


def _verify_static_view_bounds(
    source_shape: ArrayAttr[Attribute],
    source_stride: ArrayAttr[Attribute],
    offsets: Sequence[SSAValue],
    shape: Sequence[SSAValue],
    stride: Sequence[SSAValue],
) -> None:
    """校验 dma.view 可静态判定的边界约束。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 当 `source.shape/source.stride` 与 `offsets/shape/stride` 都可静态恢复时，
      以源内存线性起点和结果线性覆盖范围执行静态边界检查。

    使用示例:
    - _verify_static_view_bounds(source_type.shape, source_type.stride, op.offsets, op.shape, op.stride)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
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
        if not isinstance(source_step_attr, IntAttr):
            return
        offset_int = _operand_int_value(offset_value)
        size_int = _operand_int_value(size_value)
        stride_int = _operand_int_value(stride_value)
        if offset_int is None or size_int is None or stride_int is None:
            return
        linear_start += offset_int * source_step_attr.data
        linear_extent += (size_int - 1) * stride_int
    if linear_start + linear_extent >= source_numel:
        raise VerifyException("dma.view bounds mismatch")


def _default_contiguous_stride(shape: ArrayAttr[Attribute]) -> list[Attribute]:
    """按默认连续布局生成行主序 stride。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 静态维度返回 `IntAttr` 乘积。
    - 符号维度返回无空格 `*` 连接的乘法表达式。
    - `?` 维度会把更高维 stride 退化为 `?`。

    使用示例:
    - _default_contiguous_stride(ArrayAttr([IntAttr(2), IntAttr(4)]))

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    stride: list[Attribute] = []
    running: int | str | None = 1
    for dim in reversed(shape.data):
        if running is None:
            stride.append(StringAttr("?"))
        elif isinstance(running, int):
            stride.append(IntAttr(running))
        else:
            stride.append(StringAttr(running))
        if running is None:
            continue
        if isinstance(dim, IntAttr):
            if dim.data == 1:
                continue
            if isinstance(running, int):
                running *= dim.data
            else:
                running = f"{dim.data}*{running}"
            continue
        if isinstance(dim, StringAttr):
            if dim.data == "?":
                running = None
            elif running == 1:
                running = dim.data
            else:
                running = f"{dim.data}*{running}"
            continue
        if running is not None:
            running = None
    stride.reverse()
    return stride


def _is_contiguous(memory_type: NnMemoryType) -> bool:
    """检查 memory type 是否连续行主序。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅在 stride 为 IntAttr 且匹配连续行主序时返回 True。

    使用示例:
    - _is_contiguous(memory_type)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    expected = _default_contiguous_stride(memory_type.shape)
    if len(expected) != len(memory_type.stride.data):
        return False
    for expected_dim, stride_dim in zip(expected, memory_type.stride.data, strict=True):
        if isinstance(expected_dim, IntAttr):
            if not isinstance(stride_dim, IntAttr) or stride_dim.data != expected_dim.data:
                return False
            continue
        if isinstance(expected_dim, StringAttr):
            if not isinstance(stride_dim, StringAttr) or stride_dim.data != expected_dim.data:
                return False
            continue
        return False
    return True


def _verify_default_contiguous_stride(memory_type: NnMemoryType, message: str) -> None:
    """校验 memory type 的 stride 是否匹配默认连续布局。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 根据 `shape` 生成默认连续布局。
    - 要求 `stride` 与默认布局完全一致。

    使用示例:
    - _verify_default_contiguous_stride(result_type, "dma.alloc requires contiguous result stride")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
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

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 设置动态 shape operand 与结果类型。

        使用示例:
        - DmaAllocOp(dynamic_shape, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[dynamic_shape], result_types=[result_type])

    def verify_(self) -> None:
        """校验 dma.alloc。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 结果类型必须为 nn.memory。
        - dynamic_shape 支持空列表（全静态 shape）、全量 rank 列表或仅符号维度列表。
        - stride 按结果类型显式指定，不再额外限制布局。

        使用示例:
        - DmaAllocOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
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

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 设置被写入的 `target` memory 与标量 `value` operand。

        使用示例:
        - DmaFillOp(target, value)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[target, value])

    def verify_(self) -> None:
        """校验 dma.fill。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - `target` 必须为 `!nn.memory<..., i32, ...>`。
        - `value` 当前仅允许 builtin `i32` 或 `!symbol.int<"expr">`。

        使用示例:
        - DmaFillOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
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

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 设置待释放的 source operand。

        使用示例:
        - DmaFreeOp(source)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[source])

    def verify_(self) -> None:
        """校验 dma.free。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - source 必须为 nn.memory。

        使用示例:
        - DmaFreeOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        _verify_memory_operand(self.source, "source")


@irdl_op_definition
class DmaCopyOp(IRDLOperation):
    """dma.copy。"""

    name = "dma.copy"

    source = operand_def(NnMemoryType)
    target = operand_def(NnMemoryType)

    def __init__(self, source: SSAValue | Operation, target: SSAValue | Operation) -> None:
        """初始化 dma.copy。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 设置 source 与 target operand。

        使用示例:
        - DmaCopyOp(source, target)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[source, target])

    def verify_(self) -> None:
        """校验 dma.copy。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - source/target 的 shape/stride/element_type 必须一致。

        使用示例:
        - DmaCopyOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
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

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 设置 target 与 source operand。

        使用示例:
        - DmaBroadcastOp(target, source)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[target, source])

    def verify_(self) -> None:
        """校验 dma.broadcast。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - target 必须为 nn.memory。
        - memory source 需满足 element_type/space 与 broadcast 规则。
        - scalar source 必须与 target.element_type 类型一致，或为整数场景的 symbol.int。

        使用示例:
        - DmaBroadcastOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
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

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 设置 target/source operand 与 perm 属性。

        使用示例:
        - DmaTransposeOp(target, source, perm=[1, 0])

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        perm_attr = perm if isinstance(perm, ArrayAttr) else ArrayAttr([IntAttr(value) for value in perm])
        super().__init__(operands=[target, source], attributes={"perm": perm_attr})

    def verify_(self) -> None:
        """校验 dma.transpose。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - target/source 必须为 nn.memory。
        - element_type 与 space 必须一致。
        - perm 必须是 0..rank-1 的排列，且 target shape/stride 为 source 的重排。

        使用示例:
        - DmaTransposeOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
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

    source = operand_def(NnMemoryType)
    offsets = var_operand_def(Attribute)
    sizes = var_operand_def(SymbolValueType)
    strides = var_operand_def(SymbolValueType)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        source: SSAValue | Operation,
        offsets: Sequence[SSAValue],
        sizes: Sequence[SSAValue],
        strides: Sequence[SSAValue],
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 dma.load。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 设置 source、offsets/sizes/strides、结果类型与 space attribute。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaLoadOp(source, offsets, sizes, strides, result_type, space)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(
            operands=[source, offsets, sizes, strides],
            result_types=[result_type],
            attributes={"space": space},
        )

    def verify_(self) -> None:
        """校验 dma.load。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - offsets/sizes/strides 长度与 source rank 一致。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。
        - result.shape == sizes 且 element_type/space 一致。

        使用示例:
        - DmaLoadOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        source_type = _verify_memory_type(self.source.type, "source")
        result_type = _verify_memory_type(self.result.type, "result")
        offsets = _verify_symbol_index_operands(self.offsets, "offsets", min_value=0)
        sizes = _verify_symbol_int_operands(self.sizes, "sizes", min_value=1)
        strides = _verify_symbol_int_operands(self.strides, "strides", min_value=1)
        rank = len(source_type.shape.data)
        _verify_rank_match(offsets, rank, "offsets")
        _verify_rank_match(sizes, rank, "sizes")
        _verify_rank_match(strides, rank, "strides")
        _verify_unit_stride_operands(strides)
        _verify_operands_match_layout(sizes, result_type.shape, "shape must match sizes")
        if source_type.element_type != result_type.element_type:
            raise VerifyException("dma.load element_type mismatch")
        self.space.verify()
        if result_type.space.space.data != self.space.space.data:
            raise VerifyException("dma.load space attribute must match result space")


@irdl_op_definition
class DmaStoreOp(IRDLOperation):
    """dma.store。"""

    name = "dma.store"

    source = operand_def(NnMemoryType)
    target = operand_def(NnMemoryType)
    offsets = var_operand_def(Attribute)
    sizes = var_operand_def(SymbolValueType)
    strides = var_operand_def(SymbolValueType)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        source: SSAValue | Operation,
        target: SSAValue | Operation,
        offsets: Sequence[SSAValue],
        sizes: Sequence[SSAValue],
        strides: Sequence[SSAValue],
    ) -> None:
        """初始化 dma.store。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 设置 source/target 与 offsets/sizes/strides。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaStoreOp(source, target, offsets, sizes, strides)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[source, target, offsets, sizes, strides])

    def verify_(self) -> None:
        """校验 dma.store。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - source.shape 必须与 sizes 对齐。
        - offsets/sizes/strides 长度与 target rank 一致。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaStoreOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
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

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 设置 target/source 与 offsets/sizes/strides。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaSliceOp(target, source, offsets, sizes, strides)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[target, source, offsets, sizes, strides])

    def verify_(self) -> None:
        """校验 dma.slice。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - offsets/sizes/strides 长度与 source rank 一致。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。
        - target.shape == sizes 且 target/source element_type 一致。
        - 当前阶段 stride 必须为 1。

        使用示例:
        - DmaSliceOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
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

    source = operand_def(NnMemoryType)
    target = operand_def(NnMemoryType)
    offsets = var_operand_def(Attribute)
    sizes = var_operand_def(SymbolValueType)
    strides = var_operand_def(SymbolValueType)
    result = result_def(NnMemoryType)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        source: SSAValue | Operation,
        target: SSAValue | Operation,
        offsets: Sequence[SSAValue],
        sizes: Sequence[SSAValue],
        strides: Sequence[SSAValue],
        result_type: NnMemoryType,
    ) -> None:
        """初始化 dma.deslice。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 设置 source/target、offsets/sizes/strides 与结果类型。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaDesliceOp(source, target, offsets, sizes, strides, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(
            operands=[source, target, offsets, sizes, strides],
            result_types=[result_type],
        )

    def verify_(self) -> None:
        """校验 dma.deslice。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - source.shape 必须与 sizes 对齐。
        - offsets/sizes/strides 长度与 target rank 一致。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。
        - result type 必须与 target type 一致。

        使用示例:
        - DmaDesliceOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
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

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 设置 source、动态 offsets/shape/stride operand 与结果类型。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaViewOp(source, offsets, shape, stride, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        if not isinstance(result_type, NnMemoryType):
            raise TypeError("result_type must be nn.memory")

        super().__init__(operands=[source, offsets, shape, stride], result_types=[result_type])

    def verify_(self) -> None:
        """校验 dma.view。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - `space` 必须一致；`element_type` 必须一致（i8 byte pool 允许不同 element_type）。
        - 非 byte pool 场景下 source/result rank 必须一致；byte pool 允许 rank 不一致。
        - `offsets` 允许 `!symbol.int` 与 `!symbol.iter`，`shape`/`stride` 仍需 `!symbol.int`。
        - `offsets`/`shape`/`stride` 长度与结果 rank 一致。
        - 当边界可静态判定时，必须满足 `offset + (size - 1) * stride < dim`。
        - 非 byte pool 场景下可判定 numel 不一致必须报错；byte pool 需满足字节数一致与字节边界可达。

        使用示例:
        - DmaViewOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
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
        _verify_operands_match_layout(stride, result_type.stride, "stride must match result stride")
        if source_type.space.space.data != result_type.space.space.data:
            raise VerifyException("dma.view space mismatch")

        source_numel = _maybe_numel(source_type.shape)
        result_numel = _maybe_numel(result_type.shape)
        if _is_i8_byte_pool(source_type):
            result_elem_size = _element_byte_size(result_type.element_type)
            if result_elem_size is None:
                raise VerifyException("dma.view element_type unsupported for byte pool")
            if source_numel is not None and result_numel is not None:
                if source_numel != result_numel * result_elem_size:
                    raise VerifyException("dma.view byte length mismatch")
            max_index = _linear_max_index(offsets, shape, stride)
            if max_index is not None and source_numel is not None:
                byte_end = (max_index + 1) * result_elem_size
                if byte_end > source_numel:
                    raise VerifyException("dma.view byte bounds mismatch")
        else:
            if source_type.element_type != result_type.element_type:
                raise VerifyException("dma.view element_type mismatch")
            if source_numel is not None and result_numel is not None and source_numel != result_numel:
                raise VerifyException("dma.view numel mismatch")
            _verify_static_view_bounds(source_type.shape, source_type.stride, offsets, shape, stride)


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

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 设置 source、动态 shape operand 与结果类型。

        使用示例:
        - DmaReshapeOp(source, shape, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[source, shape], result_types=[result_type])

    def verify_(self) -> None:
        """校验 dma.reshape。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - element_type/space 必须一致。
        - source 必须连续，result.stride 必须为连续行主序。
        - 可判定 numel 不一致必须报错。

        使用示例:
        - DmaReshapeOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
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

    source = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)

    def __init__(self, source: SSAValue | Operation, result_type: NnMemoryType) -> None:
        """初始化 dma.cast。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 设置 source 与结果类型。

        使用示例:
        - DmaCastOp(source, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[source], result_types=[result_type])

    def verify_(self) -> None:
        """校验 dma.cast。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - shape/stride/space 必须一致，仅 element_type 可变化。

        使用示例:
        - DmaCastOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        source_type = _verify_memory_type(self.source.type, "source")
        result_type = _verify_memory_type(self.result.type, "result")
        if source_type.shape != result_type.shape:
            raise VerifyException("dma.cast shape mismatch")
        if source_type.stride != result_type.stride:
            raise VerifyException("dma.cast stride mismatch")
        if source_type.space.space.data != result_type.space.space.data:
            raise VerifyException("dma.cast space mismatch")


class Dma(Dialect):
    """DMA dialect 入口。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 注册 dma dialect 的 op 定义。

    使用示例:
    - ctx.load_dialect(Dma)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
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
    "DmaViewOp",
    "DmaReshapeOp",
    "DmaCastOp",
]
