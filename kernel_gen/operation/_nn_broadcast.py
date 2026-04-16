"""NN operation broadcast family.

创建者: 小李飞刀
最后一次更改: jcc你莫辜负

功能说明:
- 提供显式 broadcast 与 broadcast_to family 实现

使用示例:
- from kernel_gen.operation.nn import add, broadcast, broadcast_to

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/test_operation_nn_broadcast.py
- 功能实现: kernel_gen/operation/_nn_broadcast.py
"""

from __future__ import annotations

from ._nn_common import *


def _infer_broadcast_shape(lhs: SymbolShape, rhs: SymbolShape) -> SymbolShape:
    """推导逐元素隐式 broadcast 的目标 shape。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 按尾维对齐规则推导共同目标 shape。
    - 仅允许 singleton dim 扩张。

    使用示例:
    - _infer_broadcast_shape(SymbolShape([1, "B"]), SymbolShape(["A", "B"]))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_broadcast.py
    - 功能实现: kernel_gen/operation/_nn_broadcast.py
    """
    lhs_dims = lhs.get_values()
    rhs_dims = rhs.get_values()
    max_rank = max(len(lhs_dims), len(rhs_dims))
    result: list[object] = []
    for index in range(1, max_rank + 1):
        lhs_dim = lhs_dims[-index] if index <= len(lhs_dims) else None
        rhs_dim = rhs_dims[-index] if index <= len(rhs_dims) else None
        if lhs_dim is None:
            result.insert(0, rhs_dim)
            continue
        if rhs_dim is None:
            result.insert(0, lhs_dim)
            continue
        if lhs_dim == rhs_dim:
            result.insert(0, lhs_dim)
            continue
        if lhs_dim == 1:
            result.insert(0, rhs_dim)
            continue
        if rhs_dim == 1:
            result.insert(0, lhs_dim)
            continue
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.broadcast 参数校验",
                expected="broadcast dimension mismatch",
                actual=f"lhs={lhs_dim} rhs={rhs_dim}",
                action=_ERROR_ACTION,
            )
        )
    return SymbolShape(result)


def _broadcast_memory_pair(lhs: Memory, rhs: Memory) -> tuple[Memory, Memory]:
    """为逐元素运算执行隐式 broadcast。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 若 shape 不一致但可广播，则显式扩张到共同目标 shape。

    使用示例:
    - lhs_b, rhs_b = _broadcast_memory_pair(lhs, rhs)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_broadcast.py
    - 功能实现: kernel_gen/operation/_nn_broadcast.py
    """
    lhs_values = lhs.shape.get_values()
    rhs_values = rhs.shape.get_values()
    if lhs_values == rhs_values:
        return lhs, rhs
    target_shape = _infer_broadcast_shape(lhs.shape, rhs.shape)
    target_values = target_shape.get_values()
    if lhs_values == target_values:
        lhs_b = lhs
    else:
        lhs_target = Memory(target_shape, lhs.dtype, space=lhs.space, stride=lhs.stride, format=lhs.format)
        lhs_b = broadcast(lhs, lhs_target)
    if rhs_values == target_values:
        rhs_b = rhs
    else:
        rhs_target = Memory(target_shape, rhs.dtype, space=rhs.space, stride=rhs.stride, format=rhs.format)
        rhs_b = broadcast(rhs, rhs_target)
    return lhs_b, rhs_b


def broadcast(value: object, target: object) -> Memory:
    """显式广播 Memory 到目标描述。

    创建者: 小李飞刀
    最后一次更改: jcc你莫辜负

    功能说明:
    - 按尾维对齐规则扩张 singleton dim。
    - 返回结果在 shape/dtype/space/stride/format 上与 target 完全一致。

    使用示例:
    - broadcast(Memory([1, "N"], NumericType.Float32), Memory(["M", "N"], NumericType.Float32))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_broadcast.py
    - 功能实现: kernel_gen/operation/_nn_broadcast.py
    """
    if not isinstance(value, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.broadcast 参数校验",
                expected="broadcast value must be Memory",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if not isinstance(target, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.broadcast 参数校验",
                expected="broadcast target must be Memory",
                actual=type(target).__name__,
                action=_ERROR_ACTION,
            )
        )
    if value.dtype != target.dtype:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.broadcast 参数校验",
                expected="broadcast dtype must match target dtype",
                actual=f"input_dtype={value.dtype} target_dtype={target.dtype}",
                action=_ERROR_ACTION,
            )
        )
    input_values = value.shape.get_values()
    target_values = target.shape.get_values()

    if len(target_values) < len(input_values):
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.broadcast 参数校验",
                expected="broadcast target rank must be >= input rank",
                actual=f"input_rank={len(input_values)} target_rank={len(target_values)}",
                action=_ERROR_ACTION,
            )
        )

    for input_dim, target_dim in zip(reversed(input_values), reversed(target_values), strict=False):
        if input_dim == target_dim:
            continue
        if input_dim == 1:
            continue
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.broadcast 参数校验",
                expected="broadcast dimension mismatch",
                actual=f"input={input_dim} target={target_dim}",
                action=_ERROR_ACTION,
            )
        )

    return Memory(
        target.shape,
        target.dtype,
        space=target.space,
        stride=target.stride,
        format=target.format,
    )


def broadcast_to(source: object, target_shape: object, space: object) -> Memory:
    """显式广播 Memory 到目标 shape + space。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 复用 broadcast 的维度对齐规则。
    - 仅提供目标 shape 列表与空间，不再要求传入 Memory 目标。

    使用示例:
    - broadcast_to(mem, ["M", "N"], MemorySpace.GM)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_broadcast.py
    - 功能实现: kernel_gen/operation/_nn_broadcast.py
    """
    if not isinstance(source, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.broadcast_to 参数校验",
                expected="broadcast_to source must be Memory",
                actual=type(source).__name__,
                action=_ERROR_ACTION,
            )
        )
    if not isinstance(space, MemorySpace):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.broadcast_to 参数校验",
                expected="broadcast_to space must be MemorySpace",
                actual=type(space).__name__,
                action=_ERROR_ACTION,
            )
        )
    if isinstance(target_shape, SymbolShape):
        normalized_shape = target_shape
    elif isinstance(target_shape, Sequence) and not isinstance(target_shape, (str, bytes)):
        normalized_shape = SymbolShape(list(target_shape))
    else:
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.broadcast_to 参数校验",
                expected="broadcast_to target_shape must be iterable shape",
                actual=type(target_shape).__name__,
                action=_ERROR_ACTION,
            )
        )

    input_values = source.shape.get_values()
    target_values = normalized_shape.get_values()

    if len(target_values) < len(input_values):
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.broadcast_to 参数校验",
                expected="broadcast_to target rank must be >= input rank",
                actual=f"input_rank={len(input_values)} target_rank={len(target_values)}",
                action=_ERROR_ACTION,
            )
        )

    for input_dim, target_dim in zip(reversed(input_values), reversed(target_values), strict=False):
        if input_dim == target_dim:
            continue
        if input_dim == 1:
            continue
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.broadcast_to 参数校验",
                expected="broadcast_to dimension mismatch",
                actual=f"input={input_dim} target={target_dim}",
                action=_ERROR_ACTION,
            )
        )

    return Memory(
        normalized_shape,
        source.dtype,
        space=space,
        format=Farmat.Norm,
    )

__all__ = [
    "_infer_broadcast_shape",
    "_broadcast_memory_pair",
    "broadcast",
    "broadcast_to",
]
