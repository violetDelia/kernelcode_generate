"""DMA operation API.


功能说明:
- 提供 Memory 的数据搬运、显式广播、视图变换、整块初始化与显式转换 API，包括 alloc/free/fill/copy/broadcast/load/store/slice/deslice/view/reshape/flatten/cast。

API 列表:
- `alloc(shape: ShapeInput, dtype: NumericType, space: MemorySpace = MemorySpace.GM, stride: ShapeInput | None = None, format: Farmat = Farmat.Norm) -> Memory`
- `free(memory: Memory) -> None`
- `fill(target: Memory, value: FillValue) -> None`
- `copy(source: Memory, space: MemorySpace) -> Memory`
- `broadcast(target: Memory, source: Memory) -> None`
- `load(source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None, space: MemorySpace | None = None) -> Memory`
- `store(target: Memory, source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None) -> None`
- `slice(source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None, space: MemorySpace | None = None) -> Memory`
- `deslice(target: Memory, source: Memory, offsets: ShapeInput, sizes: ShapeInput, strides: ShapeInput | None = None) -> None`
- `view(source: Memory, offset: ShapeInput, size: ShapeInput, stride: ShapeInput) -> Memory`
- `reshape(source: Memory, shape: ShapeInput) -> Memory`
- `flatten(source: Memory) -> Memory`
- `cast(source: Memory, dtype: NumericType, memoryspace: MemorySpace | None = None) -> Memory`

使用示例:
- from kernel_gen.operation.dma import copy, cast, fill, view, flatten
- copy(src, dst)
- broadcast(target, source)
- fill(dst, 0)
- cast(src, NumericType.Float16)

关联文件:
- spec: spec/operation/dma.md
- test: test/operation/test_dma.py
- 功能实现: kernel_gen/operation/dma.py
"""

from __future__ import annotations

from collections.abc import Sequence

from kernel_gen.core.contracts import default_stride as _common_default_stride
from kernel_gen.core.contracts import shape_numel as _common_shape_numel
from kernel_gen.core.error import (
    ERROR_ACTION,
    ERROR_TEMPLATE,
    ErrorKind,
    ErrorModule,
    kernel_code_error,
)
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.symbol_shape import SymbolShape
from kernel_gen.symbol_variable.type import FLOAT_DTYPES, INT_DTYPES, Farmat, NumericType

_ERROR_SCENE = "dma operation 参数校验"
_ALLOWED_FILL_STRING_LITERALS = frozenset({"inf", "-inf"})

DimInput = int | str | SymbolDim
ShapeInput = Sequence[DimInput] | SymbolShape
FillValue = int | float | str | SymbolDim


class _RequiredSpaceSentinel:
    """标记 `space` 参数没有默认值。"""


_REQUIRED_SPACE = _RequiredSpaceSentinel()


def _ensure_memory(value: Memory, name: str) -> Memory:
    """确保输入为 Memory。


    功能说明:
    - 非 Memory 输入抛 KernelCodeError。

    使用示例:
    - _ensure_memory(mem, "source")

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    if not isinstance(value, Memory):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{name} must be Memory",
                actual=type(value).__name__,
                action=ERROR_ACTION,
            )
        )
    return value


def _ensure_shape_value(value: ShapeInput, name: str) -> SymbolShape:
    """校验并规范化 alloc 的 shape/stride。


    功能说明:
    - 字符串或字节串视为非法输入并报错。
    - 返回规范化后的 SymbolShape。

    使用示例:
    - _ensure_shape_value([1, 2], "shape")

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    if isinstance(value, (str, bytes)):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="dma.alloc 参数校验",
                expected=f"{name} must be a dimension sequence",
                actual=type(value).__name__,
                action=ERROR_ACTION,
            )
        )
    try:
        return SymbolShape(value)
    except (TypeError, ValueError) as exc:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="dma.alloc 参数校验",
                expected=f"{name} must be a valid dimension sequence",
                actual=type(value).__name__,
                action=ERROR_ACTION,
            )
        ) from exc


def alloc(
    shape: ShapeInput,
    dtype: NumericType,
    space: MemorySpace = MemorySpace.GM,
    stride: ShapeInput | None = None,
    format: Farmat = Farmat.Norm,
) -> Memory:
    """分配新的 Memory 描述对象。


    功能说明:
    - 返回包含 shape/dtype/space/stride/format 的 Memory 对象。

    使用示例:
    - buf = alloc([32, 32], NumericType.Float32, space=MemorySpace.SM, stride=[1, 1], format=Farmat.CLast)

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    if not isinstance(dtype, NumericType):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="dma.alloc 参数校验",
                expected="alloc dtype must be NumericType",
                actual=type(dtype).__name__,
                action=ERROR_ACTION,
            )
        )
    if not isinstance(space, MemorySpace):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="dma.alloc 参数校验",
                expected="alloc space must be MemorySpace",
                actual=type(space).__name__,
                action=ERROR_ACTION,
            )
        )
    if not isinstance(format, Farmat):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="dma.alloc 参数校验",
                expected="alloc format must be Farmat",
                actual=type(format).__name__,
                action=ERROR_ACTION,
            )
        )
    shape_value = _ensure_shape_value(shape, "shape")
    stride_value = None
    if stride is not None:
        stride_value = _ensure_shape_value(stride, "stride")
        if len(stride_value) != len(shape_value):
            raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
                ERROR_TEMPLATE.format(
                    scene="dma.alloc 参数校验",
                    expected="stride rank mismatch",
                    actual=f"shape_rank={len(shape_value)} stride_rank={len(stride_value)}",
                    action=ERROR_ACTION,
                )
            )
    return Memory(shape_value, dtype, space=space, stride=stride_value, format=format)


def free(value: Memory) -> None:
    """释放 Memory 生命周期。


    功能说明:
    - 仅接受 Memory 输入并返回 None。

    使用示例:
    - free(buf)

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    _ensure_memory(value, "value")
    return None


def _validate_fill_value(value: FillValue) -> FillValue:
    """校验 `dma.fill` 的公开 value 合同。


    功能说明:
    - 接受 `int`、`float`、`SymbolDim` 与 `"inf"/"-inf"`。
    - 其他字符串抛 `KernelCodeError`，其他类型抛 `KernelCodeError`。

    使用示例:
    - _validate_fill_value(0)
    - _validate_fill_value("-inf")

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    if isinstance(value, bool):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="dma.fill 参数校验",
                expected="fill value must be int/float/SymbolDim/'inf'/'-inf'",
                actual=type(value).__name__,
                action=ERROR_ACTION,
            )
        )
    if isinstance(value, str):
        if value not in _ALLOWED_FILL_STRING_LITERALS:
            raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
                ERROR_TEMPLATE.format(
                    scene="dma.fill 参数校验",
                    expected='fill string literal must be "inf" or "-inf"',
                    actual=value,
                    action=ERROR_ACTION,
                )
            )
        return value
    if isinstance(value, (int, float, SymbolDim)):
        return value
    raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
        ERROR_TEMPLATE.format(
            scene="dma.fill 参数校验",
            expected="fill value must be int/float/SymbolDim/'inf'/'-inf'",
            actual=type(value).__name__,
            action=ERROR_ACTION,
        )
    )


def fill(target: Memory, value: FillValue) -> None:
    """表达对整块 memory 的公开填充语义。


    功能说明:
    - 只校验公开 helper 合同，不分配新 buffer。
    - 返回 `None`，保持 `target` 的 shape/stride/space/format 不变。

    使用示例:
    - fill(buf, 0)
    - fill(buf, "-inf")

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    _ensure_memory(target, "target")
    _validate_fill_value(value)
    return None


def _normalize_index_list(value: ShapeInput, name: str) -> SymbolShape:
    """规范化索引列表。


    功能说明:
    - 接收 SymbolShape 或可迭代对象，并规范化为 SymbolShape。

    使用示例:
    - _normalize_index_list([0, 1], "offsets")

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    if isinstance(value, SymbolShape):
        return value
    return SymbolShape(value)


def _resolve_memory_space(
    space: MemorySpace | None,
    *,
    scene: str,
    default: MemorySpace | _RequiredSpaceSentinel = _REQUIRED_SPACE,
) -> MemorySpace:
    """统一解析 `MemorySpace` 参数。


    功能说明:
    - 统一处理 `copy/load/slice` 的 `space` 参数校验。
    - `default` 非哨兵时允许 `space=None` 回落到默认值。
    - 非 `MemorySpace` 输入保持原有 `KernelCodeError` 文案。

    使用示例:
    - _resolve_memory_space(MemorySpace.SM, scene="dma.copy 参数校验")
    - _resolve_memory_space(None, scene="dma.load 参数校验", default=MemorySpace.GM)

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    if space is None and default is not _REQUIRED_SPACE:
        return default
    if not isinstance(space, MemorySpace):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene=scene,
                expected="space must be MemorySpace",
                actual=type(space).__name__,
                action=ERROR_ACTION,
            )
        )
    return space


def _ensure_index_rank(memory: Memory, offsets: SymbolShape, sizes: SymbolShape, strides: SymbolShape | None) -> None:
    """校验索引列表长度与 rank 一致。


    功能说明:
    - offsets/sizes/strides 长度必须与 memory.rank 一致。

    使用示例:
    - _ensure_index_rank(mem, offsets, sizes, strides)

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    rank = len(memory.shape)
    if len(offsets) != rank or len(sizes) != rank:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected="Index rank mismatch",
                actual=f"rank={rank} offsets={len(offsets)} sizes={len(sizes)}",
                action=ERROR_ACTION,
            )
        )
    if strides is not None and len(strides) != rank:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected="Index rank mismatch",
                actual=f"rank={rank} strides={len(strides)}",
                action=ERROR_ACTION,
            )
        )


def _ensure_sizes_positive(sizes: SymbolShape) -> None:
    """校验 sizes 正长度约束。


    功能说明:
    - 静态长度必须大于 0，动态长度保持不变。

    使用示例:
    - _ensure_sizes_positive(SymbolShape([1, 2]))

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    for dim in sizes.get_values():
        if isinstance(dim, int) and dim <= 0:
            raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="Invalid size",
                    actual=str(dim),
                    action=ERROR_ACTION,
                )
            )


def _ensure_offsets_non_negative(offsets: SymbolShape) -> None:
    """校验 offsets 静态值非负。


    功能说明:
    - 静态 offset 必须为非负整数。

    使用示例:
    - _ensure_offsets_non_negative(SymbolShape([0, 4]))

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    for dim in offsets.get_values():
        if isinstance(dim, int) and dim < 0:
            raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="Invalid offset",
                    actual=str(dim),
                    action=ERROR_ACTION,
                )
            )


def _ensure_strides_positive(strides: SymbolShape | None) -> None:
    """校验 strides 静态值为正。


    功能说明:
    - 静态 stride 必须为正整数。

    使用示例:
    - _ensure_strides_positive(SymbolShape([1, 2]))

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    if strides is None:
        return
    for dim in strides.get_values():
        if isinstance(dim, int) and dim <= 0:
            raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="Invalid stride",
                    actual=str(dim),
                    action=ERROR_ACTION,
                )
            )


def _clone_symbol_list(value: SymbolShape | None) -> SymbolShape | None:
    """克隆符号列表对象。


    功能说明:
    - 复制 SymbolShape 容器，避免别名共享。

    使用示例:
    - _clone_symbol_list(SymbolShape([1, 2]))

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    if value is None:
        return None
    return SymbolShape(value.get_shape())


def _normalize_and_validate_access_region(
    memory: Memory,
    *,
    offsets: ShapeInput,
    sizes: ShapeInput,
    strides: ShapeInput | None = None,
    offset_name: str = "offsets",
    size_name: str = "sizes",
    stride_name: str = "strides",
    offset_normalizer=_normalize_index_list,
    size_normalizer=_normalize_index_list,
    stride_normalizer=_normalize_index_list,
) -> tuple[SymbolShape, SymbolShape, SymbolShape | None]:
    """统一规整并校验访问区域参数。


    功能说明:
    - 统一复用 offsets/sizes/strides 的规范化、rank 校验、正值校验与静态越界校验。
    - 允许调用方按 API 语义切换单个参数的规整函数，例如 `view` 继续复用 shape 风格校验。

    使用示例:
    - _normalize_and_validate_access_region(mem, offsets=[0, 0], sizes=[8, 8], strides=[1, 1])

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    offsets_shape = offset_normalizer(offsets, offset_name)
    sizes_shape = size_normalizer(sizes, size_name)
    strides_shape = None if strides is None else stride_normalizer(strides, stride_name)
    _ensure_index_rank(memory, offsets_shape, sizes_shape, strides_shape)
    _ensure_sizes_positive(sizes_shape)
    _ensure_offsets_non_negative(offsets_shape)
    _ensure_strides_positive(strides_shape)
    _ensure_bounds(memory, offsets_shape, sizes_shape, strides_shape)
    return offsets_shape, sizes_shape, strides_shape


def _ensure_bounds(
    memory: Memory,
    offsets: SymbolShape,
    sizes: SymbolShape,
    strides: SymbolShape | None,
) -> None:
    """在可静态判定时校验切片边界。


    功能说明:
    - offsets/sizes/strides 与 memory.shape 全为静态时检查越界。
    - 动态维度无法判定时跳过该维度校验。

    使用示例:
    - _ensure_bounds(mem, SymbolShape([0, 0]), SymbolShape([2, 2]), SymbolShape([1, 1]))

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    shape_values = memory.shape.get_values()
    offset_values = offsets.get_values()
    size_values = sizes.get_values()
    if strides is None:
        stride_values = [1 for _ in offset_values]
    else:
        stride_values = strides.get_values()
    for dim, offset, size, stride in zip(shape_values, offset_values, size_values, stride_values):
        if isinstance(offset, int) and offset < 0:
            raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="Invalid offset",
                    actual=str(offset),
                    action=ERROR_ACTION,
                )
            )
        if isinstance(size, int) and size <= 0:
            raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="Invalid size",
                    actual=str(size),
                    action=ERROR_ACTION,
                )
            )
        if isinstance(stride, int) and stride <= 0:
            raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="Invalid stride",
                    actual=str(stride),
                    action=ERROR_ACTION,
                )
            )
        if not all(isinstance(value, int) for value in (dim, offset, size, stride)):
            continue
        last_index = offset + (size - 1) * stride
        if last_index >= dim:
            raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="Index out of bounds",
                    actual=f"dim={dim} offset={offset} size={size} stride={stride}",
                    action=ERROR_ACTION,
                )
            )


def _is_contiguous(memory: Memory) -> bool:
    """判断 Memory 是否为连续行主序布局。


    功能说明:
    - 将当前 stride 与默认连续 stride 比较。

    使用示例:
    - _is_contiguous(Memory([2, 3], NumericType.Float32))

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    if memory.stride is None:
        return False
    default_stride = _common_default_stride(memory.shape)
    current = memory.stride.get_shape()
    expected = default_stride.get_shape()
    return len(current) == len(expected) and all(lhs == rhs for lhs, rhs in zip(current, expected))


def _shape_numel(shape: SymbolShape) -> SymbolDim:
    """计算 shape 的元素总数表达式。


    功能说明:
    - 静态维度返回静态乘积。
    - 动态维度返回无空格 `*` 的符号乘法表达式。

    使用示例:
    - _shape_numel(SymbolShape([2, 3, 4]))

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    return _common_shape_numel(shape)


def _ensure_view_numel_compatible(source: Memory, shape: SymbolShape) -> None:
    """在可判定时校验 view 前后元素总数一致。


    功能说明:
    - 若乘积表达式可化简为确定不相等，则抛 KernelCodeError。
    - 动态情况下无法判定时，保持由调用方保证。

    使用示例:
    - _ensure_view_numel_compatible(src, SymbolShape([6, 4]))

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    source_numel = _shape_numel(source.shape).get_symbol()
    target_numel = _shape_numel(shape).get_symbol()
    diff = source_numel - target_numel
    if diff == 0:
        return
    if not diff.free_symbols:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="dma.view 参数校验",
                expected="View shape numel mismatch",
                actual=f"source={source_numel} target={target_numel}",
                action=ERROR_ACTION,
            )
        )


def _combine_view_stride(source_stride: SymbolShape, view_stride: SymbolShape) -> SymbolShape:
    """组合 source 物理 stride 与 view 逻辑 stride。


    功能说明:
    - `dma.view` 的 stride 表示在 source 既有物理 stride 基础上的额外步长。
    - 逐维返回 `source_stride[i] * view_stride[i]`，静态维度由 SymbolDim 自动规整为整数。

    使用示例:
    - _combine_view_stride(SymbolShape(["LD", 1]), SymbolShape(["STEP", 1]))

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    combined = [
        source_dim * view_dim
        for source_dim, view_dim in zip(source_stride.get_shape(), view_stride.get_shape())
    ]
    return SymbolShape(combined)


def _is_supported_cast(source: NumericType, target: NumericType) -> bool:
    """判断是否支持 dtype 转换。


    功能说明:
    - 当前支持 float/int 数值类型之间的显式转换。

    使用示例:
    - _is_supported_cast(NumericType.Float32, NumericType.Float16)

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    if source is target:
        return True
    numeric_dtypes = FLOAT_DTYPES | INT_DTYPES
    if source in numeric_dtypes and target in numeric_dtypes:
        return True
    return False


def copy(source: Memory, space: MemorySpace) -> Memory:
    """整块拷贝。


    功能说明:
    - 返回新的 Memory 描述，仅覆盖目标 space。

    使用示例:
    - copy(src, MemorySpace.SM)

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    src = _ensure_memory(source, "source")
    target_space = _resolve_memory_space(space, scene="dma.copy 参数校验")
    return src.clone(space=target_space)


def _public_dim_value(dim: SymbolDim) -> int | str:
    """读取公开维度值。

    功能说明:
    - 将 SymbolDim 的公开值规整为 int 或 str。
    - 只在当前文件内服务 broadcast 合同校验。

    使用示例:
    - value = _public_dim_value(SymbolDim("N"))
    """

    value = dim.get_value()
    return value if isinstance(value, int) else str(value)


def _broadcast_dim_compatible(source_dim: SymbolDim, target_dim: SymbolDim) -> bool:
    """判断单个维度是否满足 broadcast 兼容。

    功能说明:
    - 静态维度按 `same or one` 规则检查。
    - 动态符号维度只在可机械判定冲突时失败，保持与 dma dialect verifier 一致。

    使用示例:
    - _broadcast_dim_compatible(SymbolDim(1), SymbolDim("N"))
    """

    if source_dim == target_dim:
        return True
    source_value = _public_dim_value(source_dim)
    target_value = _public_dim_value(target_dim)
    if source_value == 1 or target_value == 1:
        return True
    if isinstance(source_value, int) and isinstance(target_value, int):
        return False
    return True


def _ensure_broadcast_compatible(target: Memory, source: Memory) -> None:
    """校验 source 可广播写入 target。

    功能说明:
    - 按尾维对齐规则校验 rank、dtype、space 与静态 shape。
    - 不创建新 Memory，成功只表示 `dma.broadcast(target, source)` 合同成立。

    使用示例:
    - _ensure_broadcast_compatible(target, source)
    """

    if source.get_type() is not target.get_type():
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="dma.broadcast 参数校验",
                expected="broadcast dtype must match target dtype",
                actual=f"source={source.get_type()} target={target.get_type()}",
                action=ERROR_ACTION,
            )
        )
    if source.get_space() is not target.get_space():
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="dma.broadcast 参数校验",
                expected="broadcast source/target space must match",
                actual=f"source={source.get_space()} target={target.get_space()}",
                action=ERROR_ACTION,
            )
        )
    source_shape = source.get_shape()
    target_shape = target.get_shape()
    if len(source_shape) > len(target_shape):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="dma.broadcast 参数校验",
                expected="broadcast source rank must be <= target rank",
                actual=f"source_rank={len(source_shape)} target_rank={len(target_shape)}",
                action=ERROR_ACTION,
            )
        )
    for offset in range(1, len(target_shape) + 1):
        target_dim = target_shape[-offset]
        source_dim = source_shape[-offset] if offset <= len(source_shape) else SymbolDim(1)
        if not _broadcast_dim_compatible(source_dim, target_dim):
            raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
                ERROR_TEMPLATE.format(
                    scene="dma.broadcast 参数校验",
                    expected="broadcast shape must be compatible",
                    actual=f"source={source_shape} target={target_shape}",
                    action=ERROR_ACTION,
                )
            )


def broadcast(target: Memory, source: Memory) -> None:
    """显式广播 source 到 target。

    功能说明:
    - target-first 写回语义，`target` 是被写入的 memory operand。
    - `source` 必须是 memory，且按尾维对齐规则可广播到 `target`。
    - 返回 `None`，不创建新 Memory。

    使用示例:
    - broadcast(target, source)

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """

    dst = _ensure_memory(target, "target")
    src = _ensure_memory(source, "source")
    _ensure_broadcast_compatible(dst, src)
    return None


def load(
    source: Memory,
    offsets: ShapeInput,
    sizes: ShapeInput,
    strides: ShapeInput | None = None,
    space: MemorySpace | None = None,
) -> Memory:
    """从 source 读取切片块。


    功能说明:
    - 返回新的 Memory 块。

    使用示例:
    - tile = load(src, offsets=[0, 0], sizes=[32, 32], strides=[1, 1], space=MemorySpace.SM)

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    src = _ensure_memory(source, "source")
    offsets_shape, sizes_shape, strides_shape = _normalize_and_validate_access_region(
        src,
        offsets=offsets,
        sizes=sizes,
        strides=strides,
    )
    target_space = _resolve_memory_space(space, scene="dma.load 参数校验", default=src.space)
    return Memory(
        _clone_symbol_list(sizes_shape),
        src.dtype,
        space=target_space,
        stride=None,
        format=src.format,
    )


def store(
    target: Memory,
    source: Memory,
    offsets: ShapeInput,
    sizes: ShapeInput,
    strides: ShapeInput | None = None,
) -> None:
    """把 source 块写回 target 区域。


    功能说明:
    - target-first：第一个参数固定为写回目标。
    - source.shape 必须与 sizes 一致。

    使用示例:
    - store(dst, tile, offsets=[0, 0], sizes=[32, 32])

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    dst = _ensure_memory(target, "target")
    src = _ensure_memory(source, "source")
    if src.dtype is not dst.dtype:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="dma.store 参数校验",
                expected="Memory dtype mismatch",
                actual=f"source={src.dtype} target={dst.dtype}",
                action=ERROR_ACTION,
            )
        )
    offsets_shape, sizes_shape, strides_shape = _normalize_and_validate_access_region(
        dst,
        offsets=offsets,
        sizes=sizes,
        strides=strides,
    )
    if src.shape.get_values() != sizes_shape.get_values():
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="dma.store 参数校验",
                expected="Store size mismatch",
                actual=f"source={src.shape.get_values()} sizes={sizes_shape.get_values()}",
                action=ERROR_ACTION,
            )
        )
    return None


def slice(
    source: Memory,
    offsets: ShapeInput,
    sizes: ShapeInput,
    strides: ShapeInput | None = None,
    space: MemorySpace | None = None,
) -> Memory:
    """从 source 抽取切片块。


    功能说明:
    - 返回新的 Memory 块，强调切片语义。
    - lowering 会桥接为 `alloc + dma.slice(target, source, offsets, sizes, strides)`，返回值对应自动分配的 target。

    使用示例:
    - sub = slice(src, offsets=[0, 0], sizes=[8, 8], space=MemorySpace.LM)

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    src = _ensure_memory(source, "source")
    offsets_shape, sizes_shape, strides_shape = _normalize_and_validate_access_region(
        src,
        offsets=offsets,
        sizes=sizes,
        strides=strides,
    )
    target_space = _resolve_memory_space(space, scene="dma.slice 参数校验", default=src.space)
    return alloc(_clone_symbol_list(sizes_shape), src.dtype, space=target_space, format=src.format)


def deslice(
    target: Memory,
    source: Memory,
    offsets: ShapeInput,
    sizes: ShapeInput,
    strides: ShapeInput | None = None,
) -> None:
    """把切片块写回 target 区域。


    功能说明:
    - target 为写回目标，source.shape 必须与 sizes 一致。

    使用示例:
    - deslice(dst, sub, offsets=[0, 0], sizes=[8, 8])

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    return store(target, source, offsets, sizes, strides=strides)


def view(
    source: Memory,
    offset: ShapeInput,
    size: ShapeInput,
    stride: ShapeInput,
) -> Memory:
    """返回 source 的子视图结果。


    功能说明:
    - 仅保留 `offset/size/stride` 子视图参数，不做数据搬运。
    - 返回结果的 `shape` 固定等于 `size`，默认继承 `source` 的 `dtype/space/format`。
    - 返回结果 stride 由 source 物理 stride 与 view 逻辑 stride 逐维组合。

    使用示例:
    - view(Memory(["M", "K"], NumericType.Float32), offset=["M_t", "K_t"], size=[2, 2], stride=["stride", 1])

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    src = _ensure_memory(source, "source")
    offset_value, size_value, stride_value = _normalize_and_validate_access_region(
        src,
        offsets=offset,
        sizes=size,
        strides=stride,
        offset_name="offset",
        size_name="size",
        stride_name="stride",
        offset_normalizer=_ensure_shape_value,
        size_normalizer=_ensure_shape_value,
        stride_normalizer=_ensure_shape_value,
    )
    return Memory(
        _clone_symbol_list(size_value),
        src.dtype,
        space=src.space,
        stride=_combine_view_stride(src.stride, stride_value),
        format=src.format,
    )


def reshape(source: Memory, shape: ShapeInput) -> Memory:
    """返回 source 的形状重塑结果。


    功能说明:
    - 仅调整 `shape/stride` 元信息，不做数据搬运。
    - 仅允许连续布局的 source。

    使用示例:
    - reshape(Memory([2, 3, 4], NumericType.Float32), shape=[6, 4])

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    src = _ensure_memory(source, "source")
    shape_value = _ensure_shape_value(shape, "shape")
    _ensure_view_numel_compatible(src, shape_value)
    if not _is_contiguous(src):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="dma.reshape 参数校验",
                expected="Reshape requires contiguous source",
                actual="non-contiguous",
                action=ERROR_ACTION,
            )
        )
    return Memory(
        _clone_symbol_list(shape_value),
        src.dtype,
        space=src.space,
        stride=None,
        format=src.format,
    )


def flatten(source: Memory) -> Memory:
    """将 source 展平成一维视图。


    功能说明:
    - 要求 source 为连续布局。
    - 返回 `shape=[prod(shape)]`、`stride=[1]` 的新 Memory。

    使用示例:
    - flatten(Memory([2, 3, 4], NumericType.Float32))

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    src = _ensure_memory(source, "source")
    if not _is_contiguous(src):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="dma.flatten 参数校验",
                expected="Flatten requires contiguous source",
                actual="non-contiguous",
                action=ERROR_ACTION,
            )
        )
    flattened = _shape_numel(src.shape)
    return Memory(
        [flattened],
        src.dtype,
        space=src.space,
        stride=[1],
        format=src.format,
    )


def cast(source: Memory, dtype: NumericType, memoryspace: MemorySpace | None = None) -> Memory:
    """显式转换 Memory dtype。


    功能说明:
    - 返回 shape/stride/format 保持一致的新 Memory，space 可选覆盖。

    使用示例:
    - cast(Memory([1, 2], NumericType.Float32), NumericType.Float16, memoryspace=MemorySpace.GM)

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    src = _ensure_memory(source, "source")
    if not isinstance(dtype, NumericType):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="dma.cast 参数校验",
                expected="cast dtype must be NumericType",
                actual=type(dtype).__name__,
                action=ERROR_ACTION,
            )
        )
    if memoryspace is not None and not isinstance(memoryspace, MemorySpace):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="dma.cast 参数校验",
                expected="cast memoryspace must be MemorySpace",
                actual=type(memoryspace).__name__,
                action=ERROR_ACTION,
            )
        )
    if not _is_supported_cast(src.dtype, dtype):
        raise kernel_code_error(
            ErrorKind.UNIMPLEMENTED,
            ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="dma.cast 参数校验",
                expected="Unsupported cast conversion",
                actual=f"{src.dtype}->{dtype}",
                action=ERROR_ACTION,
            )
        )
    target_space = src.space if memoryspace is None else memoryspace
    return src.clone(dtype=dtype, space=target_space)
