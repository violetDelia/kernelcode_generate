"""DMA operation API.

创建者: 金铲铲大作战
最后一次更改: 朽木露琪亚

功能说明:
- 提供 Memory 的数据搬运、视图变换与显式转换 API，包括 alloc/free/copy/load/store/slice/deslice/view/reshape/flatten/cast。

使用示例:
- from kernel_gen.operation.dma import copy, cast, view, flatten
- copy(src, dst)
- cast(src, NumericType.Float16)

关联文件:
- spec: spec/operation/dma.md
- test: test/operation/test_operation_dma.py
- 功能实现: kernel_gen/operation/dma.py
"""

from __future__ import annotations

from collections.abc import Sequence

from kernel_gen.common.errors import _ERROR_TEMPLATE
from kernel_gen.symbol_variable.dtype_constants import FLOAT_DTYPES, INT_DTYPES
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.symbol_shape import SymbolShape
from kernel_gen.symbol_variable.type import Farmat, NumericType

_ERROR_ACTION = "请按接口约束传参"
_ERROR_SCENE = "dma operation 参数校验"


def _ensure_memory(value: object, name: str) -> Memory:
    """确保输入为 Memory。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 非 Memory 输入抛 TypeError。

    使用示例:
    - _ensure_memory(mem, "source")

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    if not isinstance(value, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{name} must be Memory",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    return value


def _ensure_shape_value(value: object, name: str) -> SymbolShape:
    """校验并规范化 alloc 的 shape/stride。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 字符串或字节串视为非法输入并报错。
    - 返回规范化后的 SymbolShape。

    使用示例:
    - _ensure_shape_value([1, 2], "shape")

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    if isinstance(value, (str, bytes)):
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="dma.alloc 参数校验",
                expected=f"{name} must be a dimension sequence",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    try:
        return SymbolShape(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="dma.alloc 参数校验",
                expected=f"{name} must be a valid dimension sequence",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        ) from exc


def alloc(
    shape: Sequence[int | str] | SymbolShape,
    dtype: NumericType,
    space: MemorySpace = MemorySpace.GM,
    stride: Sequence[int | str] | SymbolShape | None = None,
    format: Farmat = Farmat.Norm,
) -> Memory:
    """分配新的 Memory 描述对象。

    创建者: 金铲铲大作战
    最后一次更改: 朽木露琪亚

    功能说明:
    - 返回包含 shape/dtype/space/stride/format 的 Memory 对象。

    使用示例:
    - buf = alloc([32, 32], NumericType.Float32, space=MemorySpace.SM, stride=[1, 1], format=Farmat.CLast)

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    if not isinstance(dtype, NumericType):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="dma.alloc 参数校验",
                expected="alloc dtype must be NumericType",
                actual=type(dtype).__name__,
                action=_ERROR_ACTION,
            )
        )
    if not isinstance(space, MemorySpace):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="dma.alloc 参数校验",
                expected="alloc space must be MemorySpace",
                actual=type(space).__name__,
                action=_ERROR_ACTION,
            )
        )
    if not isinstance(format, Farmat):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="dma.alloc 参数校验",
                expected="alloc format must be Farmat",
                actual=type(format).__name__,
                action=_ERROR_ACTION,
            )
        )
    shape_value = _ensure_shape_value(shape, "shape")
    stride_value = None
    if stride is not None:
        stride_value = _ensure_shape_value(stride, "stride")
        if len(stride_value) != len(shape_value):
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene="dma.alloc 参数校验",
                    expected="stride rank mismatch",
                    actual=f"shape_rank={len(shape_value)} stride_rank={len(stride_value)}",
                    action=_ERROR_ACTION,
                )
            )
    return Memory(shape_value, dtype, space=space, stride=stride_value, format=format)


def free(value: object) -> None:
    """释放 Memory 生命周期。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅接受 Memory 输入并返回 None。

    使用示例:
    - free(buf)

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    _ensure_memory(value, "value")
    return None


def _normalize_index_list(value: object, name: str) -> SymbolShape:
    """规范化索引列表。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 接收 SymbolShape 或可迭代对象，并规范化为 SymbolShape。

    使用示例:
    - _normalize_index_list([0, 1], "offsets")

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    if isinstance(value, SymbolShape):
        return value
    return SymbolShape(value)


def _ensure_index_rank(memory: Memory, offsets: SymbolShape, sizes: SymbolShape, strides: SymbolShape | None) -> None:
    """校验索引列表长度与 rank 一致。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - offsets/sizes/strides 长度必须与 memory.rank 一致。

    使用示例:
    - _ensure_index_rank(mem, offsets, sizes, strides)

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    rank = len(memory.shape)
    if len(offsets) != rank or len(sizes) != rank:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected="Index rank mismatch",
                actual=f"rank={rank} offsets={len(offsets)} sizes={len(sizes)}",
                action=_ERROR_ACTION,
            )
        )
    if strides is not None and len(strides) != rank:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected="Index rank mismatch",
                actual=f"rank={rank} strides={len(strides)}",
                action=_ERROR_ACTION,
            )
        )


def _ensure_sizes_positive(sizes: SymbolShape) -> None:
    """校验 sizes 正长度约束。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 静态长度必须大于 0，动态长度保持不变。

    使用示例:
    - _ensure_sizes_positive(SymbolShape([1, 2]))

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    for dim in sizes.get_values():
        if isinstance(dim, int) and dim <= 0:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="Invalid size",
                    actual=str(dim),
                    action=_ERROR_ACTION,
                )
            )


def _ensure_offsets_non_negative(offsets: SymbolShape) -> None:
    """校验 offsets 静态值非负。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 静态 offset 必须为非负整数。

    使用示例:
    - _ensure_offsets_non_negative(SymbolShape([0, 4]))

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    for dim in offsets.get_values():
        if isinstance(dim, int) and dim < 0:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="Invalid offset",
                    actual=str(dim),
                    action=_ERROR_ACTION,
                )
            )


def _ensure_strides_positive(strides: SymbolShape | None) -> None:
    """校验 strides 静态值为正。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 静态 stride 必须为正整数。

    使用示例:
    - _ensure_strides_positive(SymbolShape([1, 2]))

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    if strides is None:
        return
    for dim in strides.get_values():
        if isinstance(dim, int) and dim <= 0:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="Invalid stride",
                    actual=str(dim),
                    action=_ERROR_ACTION,
                )
            )


def _clone_symbol_list(value: SymbolShape | None) -> SymbolShape | None:
    """克隆符号列表对象。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 复制 SymbolShape 容器，避免别名共享。

    使用示例:
    - _clone_symbol_list(SymbolShape([1, 2]))

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    if value is None:
        return None
    return SymbolShape(value.get_shape())


def _ensure_bounds(
    memory: Memory,
    offsets: SymbolShape,
    sizes: SymbolShape,
    strides: SymbolShape | None,
) -> None:
    """在可静态判定时校验切片边界。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - offsets/sizes/strides 与 memory.shape 全为静态时检查越界。
    - 动态维度无法判定时跳过该维度校验。

    使用示例:
    - _ensure_bounds(mem, SymbolShape([0, 0]), SymbolShape([2, 2]), SymbolShape([1, 1]))

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
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
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="Invalid offset",
                    actual=str(offset),
                    action=_ERROR_ACTION,
                )
            )
        if isinstance(size, int) and size <= 0:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="Invalid size",
                    actual=str(size),
                    action=_ERROR_ACTION,
                )
            )
        if isinstance(stride, int) and stride <= 0:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="Invalid stride",
                    actual=str(stride),
                    action=_ERROR_ACTION,
                )
            )
        if not all(isinstance(value, int) for value in (dim, offset, size, stride)):
            continue
        last_index = offset + (size - 1) * stride
        if last_index >= dim:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="Index out of bounds",
                    actual=f"dim={dim} offset={offset} size={size} stride={stride}",
                    action=_ERROR_ACTION,
                )
            )


def _is_contiguous(memory: Memory) -> bool:
    """判断 Memory 是否为连续行主序布局。

    创建者: ChatGPT
    最后一次更改: ChatGPT

    功能说明:
    - 将当前 stride 与默认连续 stride 比较。

    使用示例:
    - _is_contiguous(Memory([2, 3], NumericType.Float32))

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    if memory.stride is None:
        return False
    default_stride = Memory._default_stride(memory.shape)
    current = memory.stride.get_shape()
    expected = default_stride.get_shape()
    return len(current) == len(expected) and all(lhs == rhs for lhs, rhs in zip(current, expected))


def _shape_numel(shape: SymbolShape) -> SymbolDim:
    """计算 shape 的元素总数表达式。

    创建者: ChatGPT
    最后一次更改: ChatGPT

    功能说明:
    - 静态维度返回静态乘积。
    - 动态维度返回无空格 `*` 的符号乘法表达式。

    使用示例:
    - _shape_numel(SymbolShape([2, 3, 4]))

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    total = SymbolDim(1)
    for dim in shape.get_shape():
        total = total * dim
    return total


def _ensure_view_numel_compatible(source: Memory, shape: SymbolShape) -> None:
    """在可判定时校验 view 前后元素总数一致。

    创建者: ChatGPT
    最后一次更改: ChatGPT

    功能说明:
    - 若乘积表达式可化简为确定不相等，则抛 ValueError。
    - 动态情况下无法判定时，保持由调用方保证。

    使用示例:
    - _ensure_view_numel_compatible(src, SymbolShape([6, 4]))

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    source_numel = _shape_numel(source.shape).get_symbol()
    target_numel = _shape_numel(shape).get_symbol()
    diff = source_numel - target_numel
    if diff == 0:
        return
    if not diff.free_symbols:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="dma.view 参数校验",
                expected="View shape numel mismatch",
                actual=f"source={source_numel} target={target_numel}",
                action=_ERROR_ACTION,
            )
        )


def _is_supported_cast(source: NumericType, target: NumericType) -> bool:
    """判断是否支持 dtype 转换。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 当前仅支持同类数值类型间的显式转换。

    使用示例:
    - _is_supported_cast(NumericType.Float32, NumericType.Float16)

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    if source is target:
        return True
    if source in FLOAT_DTYPES and target in FLOAT_DTYPES:
        return True
    if source in INT_DTYPES and target in INT_DTYPES:
        return True
    return False


def copy(source: object, space: object) -> Memory:
    """整块拷贝。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 返回新的 Memory 描述，仅覆盖目标 space。

    使用示例:
    - copy(src, MemorySpace.SM)

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    src = _ensure_memory(source, "source")
    if not isinstance(space, MemorySpace):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="dma.copy 参数校验",
                expected="space must be MemorySpace",
                actual=type(space).__name__,
                action=_ERROR_ACTION,
            )
        )
    return Memory(
        _clone_symbol_list(src.shape),
        src.dtype,
        space=space,
        stride=_clone_symbol_list(src.stride),
        format=src.format,
    )


def load(
    source: object,
    offsets: Sequence[int | str] | SymbolShape,
    sizes: Sequence[int | str] | SymbolShape,
    strides: Sequence[int | str] | SymbolShape | None = None,
    space: MemorySpace | None = None,
) -> Memory:
    """从 source 读取切片块。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 返回新的 Memory 块。

    使用示例:
    - tile = load(src, offsets=[0, 0], sizes=[32, 32], strides=[1, 1], space=MemorySpace.SM)

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    src = _ensure_memory(source, "source")
    if space is not None and not isinstance(space, MemorySpace):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="dma.load 参数校验",
                expected="space must be MemorySpace",
                actual=type(space).__name__,
                action=_ERROR_ACTION,
            )
        )
    offsets_shape = _normalize_index_list(offsets, "offsets")
    sizes_shape = _normalize_index_list(sizes, "sizes")
    strides_shape = None if strides is None else _normalize_index_list(strides, "strides")
    _ensure_index_rank(src, offsets_shape, sizes_shape, strides_shape)
    _ensure_sizes_positive(sizes_shape)
    _ensure_offsets_non_negative(offsets_shape)
    _ensure_strides_positive(strides_shape)
    _ensure_bounds(src, offsets_shape, sizes_shape, strides_shape)
    target_space = src.space if space is None else space
    return Memory(
        _clone_symbol_list(sizes_shape),
        src.dtype,
        space=target_space,
        stride=None,
        format=src.format,
    )


def store(
    source: object,
    target: object,
    offsets: Sequence[int | str] | SymbolShape,
    sizes: Sequence[int | str] | SymbolShape,
    strides: Sequence[int | str] | SymbolShape | None = None,
) -> None:
    """把 source 块写回 target 区域。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - source.shape 必须与 sizes 一致。

    使用示例:
    - store(tile, dst, offsets=[0, 0], sizes=[32, 32])

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    src = _ensure_memory(source, "source")
    dst = _ensure_memory(target, "target")
    if src.dtype is not dst.dtype:
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="dma.store 参数校验",
                expected="Memory dtype mismatch",
                actual=f"source={src.dtype} target={dst.dtype}",
                action=_ERROR_ACTION,
            )
        )
    offsets_shape = _normalize_index_list(offsets, "offsets")
    sizes_shape = _normalize_index_list(sizes, "sizes")
    strides_shape = None if strides is None else _normalize_index_list(strides, "strides")
    _ensure_index_rank(dst, offsets_shape, sizes_shape, strides_shape)
    _ensure_sizes_positive(sizes_shape)
    _ensure_offsets_non_negative(offsets_shape)
    _ensure_strides_positive(strides_shape)
    _ensure_bounds(dst, offsets_shape, sizes_shape, strides_shape)
    if src.shape.get_values() != sizes_shape.get_values():
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="dma.store 参数校验",
                expected="Store size mismatch",
                actual=f"source={src.shape.get_values()} sizes={sizes_shape.get_values()}",
                action=_ERROR_ACTION,
            )
        )
    return None


def slice(
    source: object,
    offsets: Sequence[int | str] | SymbolShape,
    sizes: Sequence[int | str] | SymbolShape,
    strides: Sequence[int | str] | SymbolShape | None = None,
    space: MemorySpace | None = None,
) -> Memory:
    """从 source 抽取切片块。

    创建者: 金铲铲大作战
    最后一次更改: 朽木露琪亚

    功能说明:
    - 返回新的 Memory 块，强调切片语义。
    - lowering 会桥接为 `alloc + dma.slice(target, source, offsets, sizes, strides)`，返回值对应自动分配的 target。

    使用示例:
    - sub = slice(src, offsets=[0, 0], sizes=[8, 8], space=MemorySpace.LM)

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    src = _ensure_memory(source, "source")
    if space is not None and not isinstance(space, MemorySpace):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="dma.slice 参数校验",
                expected="space must be MemorySpace",
                actual=type(space).__name__,
                action=_ERROR_ACTION,
            )
        )
    offsets_shape = _normalize_index_list(offsets, "offsets")
    sizes_shape = _normalize_index_list(sizes, "sizes")
    strides_shape = None if strides is None else _normalize_index_list(strides, "strides")
    _ensure_index_rank(src, offsets_shape, sizes_shape, strides_shape)
    _ensure_sizes_positive(sizes_shape)
    _ensure_offsets_non_negative(offsets_shape)
    _ensure_strides_positive(strides_shape)
    _ensure_bounds(src, offsets_shape, sizes_shape, strides_shape)
    target_space = src.space if space is None else space
    return alloc(_clone_symbol_list(sizes_shape), src.dtype, space=target_space, format=src.format)


def deslice(
    source: object,
    target: object,
    offsets: Sequence[int | str] | SymbolShape,
    sizes: Sequence[int | str] | SymbolShape,
    strides: Sequence[int | str] | SymbolShape | None = None,
) -> None:
    """把切片块写回 target 区域。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - source.shape 必须与 sizes 一致。

    使用示例:
    - deslice(sub, dst, offsets=[0, 0], sizes=[8, 8])

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    return store(source, target, offsets, sizes, strides=strides)


def view(
    source: object,
    offset: Sequence[int | str] | SymbolShape,
    size: Sequence[int | str] | SymbolShape,
    stride: Sequence[int | str] | SymbolShape,
) -> Memory:
    """返回 source 的子视图结果。

    创建者: ChatGPT
    最后一次更改: 小李飞刀

    功能说明:
    - 仅保留 `offset/size/stride` 子视图参数，不做数据搬运。
    - 返回结果的 `shape` 固定等于 `size`，默认继承 `source` 的 `dtype/space/format`。
    - 返回结果继承 `source` 的规格，仅替换 `shape`。

    使用示例:
    - view(Memory(["M", "K"], NumericType.Float32), offset=["M_t", "K_t"], size=[2, 2], stride=["stride", 1])

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    src = _ensure_memory(source, "source")
    offset_value = _ensure_shape_value(offset, "offset")
    size_value = _ensure_shape_value(size, "size")
    stride_value = _ensure_shape_value(stride, "stride")
    _ensure_index_rank(src, offset_value, size_value, stride_value)
    _ensure_sizes_positive(size_value)
    _ensure_offsets_non_negative(offset_value)
    _ensure_strides_positive(stride_value)
    _ensure_bounds(src, offset_value, size_value, stride_value)
    return Memory(
        _clone_symbol_list(size_value),
        src.dtype,
        space=src.space,
        stride=_clone_symbol_list(src.stride),
        format=src.format,
    )


def reshape(source: object, shape: Sequence[int | str] | SymbolShape) -> Memory:
    """返回 source 的形状重塑结果。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅调整 `shape/stride` 元信息，不做数据搬运。
    - 仅允许连续布局的 source。

    使用示例:
    - reshape(Memory([2, 3, 4], NumericType.Float32), shape=[6, 4])

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    src = _ensure_memory(source, "source")
    shape_value = _ensure_shape_value(shape, "shape")
    _ensure_view_numel_compatible(src, shape_value)
    if not _is_contiguous(src):
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="dma.reshape 参数校验",
                expected="Reshape requires contiguous source",
                actual="non-contiguous",
                action=_ERROR_ACTION,
            )
        )
    return Memory(
        _clone_symbol_list(shape_value),
        src.dtype,
        space=src.space,
        stride=None,
        format=src.format,
    )


def flatten(source: object) -> Memory:
    """将 source 展平成一维视图。

    创建者: ChatGPT
    最后一次更改: ChatGPT

    功能说明:
    - 要求 source 为连续布局。
    - 返回 `shape=[prod(shape)]`、`stride=[1]` 的新 Memory。

    使用示例:
    - flatten(Memory([2, 3, 4], NumericType.Float32))

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    src = _ensure_memory(source, "source")
    if not _is_contiguous(src):
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="dma.flatten 参数校验",
                expected="Flatten requires contiguous source",
                actual="non-contiguous",
                action=_ERROR_ACTION,
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


def cast(source: object, dtype: NumericType, memoryspace: MemorySpace | None = None) -> Memory:
    """显式转换 Memory dtype。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 返回 shape/stride/format 保持一致的新 Memory，space 可选覆盖。

    使用示例:
    - cast(Memory([1, 2], NumericType.Float32), NumericType.Float16, memoryspace=MemorySpace.GM)

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    src = _ensure_memory(source, "source")
    if not isinstance(dtype, NumericType):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="dma.cast 参数校验",
                expected="cast dtype must be NumericType",
                actual=type(dtype).__name__,
                action=_ERROR_ACTION,
            )
        )
    if memoryspace is not None and not isinstance(memoryspace, MemorySpace):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="dma.cast 参数校验",
                expected="cast memoryspace must be MemorySpace",
                actual=type(memoryspace).__name__,
                action=_ERROR_ACTION,
            )
        )
    if not _is_supported_cast(src.dtype, dtype):
        raise NotImplementedError(
            _ERROR_TEMPLATE.format(
                scene="dma.cast 参数校验",
                expected="Unsupported cast conversion",
                actual=f"{src.dtype}->{dtype}",
                action=_ERROR_ACTION,
            )
        )
    target_space = src.space if memoryspace is None else memoryspace
    return Memory(
        _clone_symbol_list(src.shape),
        dtype,
        space=target_space,
        stride=_clone_symbol_list(src.stride),
        format=src.format,
    )
