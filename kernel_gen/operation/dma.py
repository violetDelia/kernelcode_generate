"""DMA operation API.

创建者: 金铲铲大作战
最后一次更改: 小李飞刀

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

from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.symbol_shape import SymbolShape
from kernel_gen.symbol_variable.type import NumericType

_FLOAT_DTYPES = {
    NumericType.Float16,
    NumericType.BFloat16,
    NumericType.Float32,
    NumericType.Float64,
}
_INT_DTYPES = {
    NumericType.Int8,
    NumericType.Int16,
    NumericType.Int32,
    NumericType.Int64,
    NumericType.Uint8,
    NumericType.Uint16,
    NumericType.Uint32,
    NumericType.Uint64,
}


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
        raise TypeError(f"{name} must be Memory")
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
        raise ValueError(f"{name} must be a dimension sequence")
    try:
        return SymbolShape(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a valid dimension sequence") from exc


def alloc(
    shape,
    dtype: NumericType,
    space: MemorySpace = MemorySpace.GM,
    stride=None,
) -> Memory:
    """分配新的 Memory 描述对象。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 返回包含 shape/dtype/space/stride 的 Memory 对象。

    使用示例:
    - buf = alloc([32, 32], NumericType.Float32, space=MemorySpace.SM, stride=[1, 1])

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    if not isinstance(dtype, NumericType):
        raise TypeError("alloc dtype must be NumericType")
    if not isinstance(space, MemorySpace):
        raise TypeError("alloc space must be MemorySpace")
    shape_value = _ensure_shape_value(shape, "shape")
    stride_value = None
    if stride is not None:
        stride_value = _ensure_shape_value(stride, "stride")
        if len(stride_value) != len(shape_value):
            raise ValueError("stride rank mismatch")
    return Memory(shape_value, dtype, space=space, stride=stride_value)


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
        raise ValueError("Index rank mismatch")
    if strides is not None and len(strides) != rank:
        raise ValueError("Index rank mismatch")


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
            raise ValueError("Invalid size")


def _ensure_unit_strides(strides: SymbolShape | None) -> None:
    """校验 stride 是否为全 1。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 当前阶段仅支持全 1 stride，其他情况显式报错。

    使用示例:
    - _ensure_unit_strides(SymbolShape([1, 1]))

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    if strides is None:
        return
    for dim in strides.get_values():
        if dim != 1:
            raise NotImplementedError("Non-unit stride is not supported")


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
    return SymbolShape(value.get_values())


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
        raise ValueError("View shape numel mismatch")


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
    if source in _FLOAT_DTYPES and target in _FLOAT_DTYPES:
        return True
    if source in _INT_DTYPES and target in _INT_DTYPES:
        return True
    return False


def copy(source: object, target: object) -> None:
    """整块拷贝。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - source/target 需 shape/stride/dtype 一致。

    使用示例:
    - copy(src, dst)

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    src = _ensure_memory(source, "source")
    dst = _ensure_memory(target, "target")
    if src.dtype is not dst.dtype:
        raise TypeError("Memory dtype mismatch")
    if src.shape.get_values() != dst.shape.get_values():
        raise ValueError("Memory shape mismatch")
    if (src.stride is None) != (dst.stride is None):
        raise ValueError("Memory stride mismatch")
    if src.stride is not None and dst.stride is not None:
        if src.stride.get_values() != dst.stride.get_values():
            raise ValueError("Memory stride mismatch")
    return None


def load(
    source: object,
    offsets,
    sizes,
    strides=None,
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
        raise TypeError("space must be MemorySpace")
    offsets_shape = _normalize_index_list(offsets, "offsets")
    sizes_shape = _normalize_index_list(sizes, "sizes")
    strides_shape = None if strides is None else _normalize_index_list(strides, "strides")
    _ensure_index_rank(src, offsets_shape, sizes_shape, strides_shape)
    _ensure_sizes_positive(sizes_shape)
    _ensure_unit_strides(strides_shape)
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
    offsets,
    sizes,
    strides=None,
) -> None:
    """把 source 块写回 target 区域。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

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
        raise TypeError("Memory dtype mismatch")
    offsets_shape = _normalize_index_list(offsets, "offsets")
    sizes_shape = _normalize_index_list(sizes, "sizes")
    strides_shape = None if strides is None else _normalize_index_list(strides, "strides")
    _ensure_index_rank(dst, offsets_shape, sizes_shape, strides_shape)
    _ensure_sizes_positive(sizes_shape)
    _ensure_unit_strides(strides_shape)
    if src.shape.get_values() != sizes_shape.get_values():
        raise ValueError("Store size mismatch")
    return None


def slice(
    source: object,
    offsets,
    sizes,
    strides=None,
    space: MemorySpace | None = None,
) -> Memory:
    """从 source 抽取切片块。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 返回新的 Memory 块，强调切片语义。

    使用示例:
    - sub = slice(src, offsets=[0, 0], sizes=[8, 8], space=MemorySpace.LM)

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    return load(source, offsets, sizes, strides=strides, space=space)


def deslice(
    source: object,
    target: object,
    offsets,
    sizes,
    strides=None,
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


def view(source: object, shape, stride=None) -> Memory:
    """返回 source 的视图变换结果。

    创建者: ChatGPT
    最后一次更改: ChatGPT

    功能说明:
    - 仅调整 `shape/stride` 元信息，不做数据搬运。
    - 未显式提供 stride 时，要求 source 为连续布局。

    使用示例:
    - view(Memory([2, 3, 4], NumericType.Float32), shape=[6, 4])

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    src = _ensure_memory(source, "source")
    shape_value = _ensure_shape_value(shape, "shape")
    _ensure_view_numel_compatible(src, shape_value)
    if stride is None:
        if not _is_contiguous(src):
            raise ValueError("View requires contiguous source when stride is omitted")
        stride_value = None
    else:
        stride_value = _ensure_shape_value(stride, "stride")
        if len(stride_value) != len(shape_value):
            raise ValueError("stride rank mismatch")
    return Memory(
        _clone_symbol_list(shape_value),
        src.dtype,
        space=src.space,
        stride=_clone_symbol_list(stride_value),
        format=src.format,
    )


def reshape(source: object, shape) -> Memory:
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
        raise ValueError("Reshape requires contiguous source")
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
        raise ValueError("Flatten requires contiguous source")
    flattened = _shape_numel(src.shape)
    return Memory(
        [flattened],
        src.dtype,
        space=src.space,
        stride=[1],
        format=src.format,
    )


def cast(source: object, dtype: NumericType) -> Memory:
    """显式转换 Memory dtype。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 返回 shape/stride/space 保持一致的新 Memory。

    使用示例:
    - cast(Memory([1, 2], NumericType.Float32), NumericType.Float16)

    关联文件:
    - spec: spec/operation/dma.md
    - test: test/operation/test_operation_dma.py
    - 功能实现: kernel_gen/operation/dma.py
    """
    src = _ensure_memory(source, "source")
    if not isinstance(dtype, NumericType):
        raise TypeError("cast dtype must be NumericType")
    if not _is_supported_cast(src.dtype, dtype):
        raise NotImplementedError("Unsupported cast conversion")
    return Memory(
        _clone_symbol_list(src.shape),
        dtype,
        space=src.space,
        stride=_clone_symbol_list(src.stride),
        format=src.format,
    )
