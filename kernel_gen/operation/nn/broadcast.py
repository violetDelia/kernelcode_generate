"""NN operation broadcast family.


功能说明:
- 提供显式 broadcast 与 broadcast_to family 实现

API 列表:
- `broadcast(value: Memory, target: Memory) -> Memory`
- `broadcast_to(source: Memory, target_shape: ShapeInput, space: MemorySpace) -> Memory`

使用示例:
- from kernel_gen.operation.nn import add, broadcast, broadcast_to

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/nn/test_broadcast.py
- 功能实现: kernel_gen/operation/nn/broadcast.py
"""

from __future__ import annotations

from collections.abc import Sequence

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
from kernel_gen.symbol_variable.type import Farmat

ShapeInput = Sequence[int | str | SymbolDim] | SymbolShape


def broadcast(value: Memory, target: Memory) -> Memory:
    """显式广播 Memory 到目标描述。


    功能说明:
    - 按尾维对齐规则扩张 singleton dim。
    - 返回结果在 shape/dtype/space/stride/format 上与 target 完全一致。

    使用示例:
    - broadcast(Memory([1, "N"], NumericType.Float32), Memory(["M", "N"], NumericType.Float32))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_broadcast.py
    - 功能实现: kernel_gen/operation/nn/broadcast.py
    """
    if not isinstance(value, Memory):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.broadcast 参数校验",
                expected="broadcast value must be Memory",
                actual=type(value).__name__,
                action=ERROR_ACTION,
            )
        )
    if not isinstance(target, Memory):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.broadcast 参数校验",
                expected="broadcast target must be Memory",
                actual=type(target).__name__,
                action=ERROR_ACTION,
            )
        )
    if value.dtype != target.dtype:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.broadcast 参数校验",
                expected="broadcast dtype must match target dtype",
                actual=f"input_dtype={value.dtype} target_dtype={target.dtype}",
                action=ERROR_ACTION,
            )
        )
    input_values = value.shape.get_values()
    target_values = target.shape.get_values()

    if len(target_values) < len(input_values):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.broadcast 参数校验",
                expected="broadcast target rank must be >= input rank",
                actual=f"input_rank={len(input_values)} target_rank={len(target_values)}",
                action=ERROR_ACTION,
            )
        )

    for input_dim, target_dim in zip(reversed(input_values), reversed(target_values), strict=False):
        if input_dim == target_dim:
            continue
        if input_dim == 1:
            continue
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.broadcast 参数校验",
                expected="broadcast dimension mismatch",
                actual=f"input={input_dim} target={target_dim}",
                action=ERROR_ACTION,
            )
        )

    return Memory(
        target.shape,
        target.dtype,
        space=target.space,
        stride=target.stride,
        format=target.format,
    )


def broadcast_to(source: Memory, target_shape: ShapeInput, space: MemorySpace) -> Memory:
    """显式广播 Memory 到目标 shape + space。


    功能说明:
    - 复用 broadcast 的维度对齐规则。
    - 仅提供目标 shape 列表与空间，不再要求传入 Memory 目标。

    使用示例:
    - broadcast_to(mem, ["M", "N"], MemorySpace.GM)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_broadcast.py
    - 功能实现: kernel_gen/operation/nn/broadcast.py
    """
    if not isinstance(source, Memory):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.broadcast_to 参数校验",
                expected="broadcast_to source must be Memory",
                actual=type(source).__name__,
                action=ERROR_ACTION,
            )
        )
    if not isinstance(space, MemorySpace):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.broadcast_to 参数校验",
                expected="broadcast_to space must be MemorySpace",
                actual=type(space).__name__,
                action=ERROR_ACTION,
            )
        )
    if isinstance(target_shape, SymbolShape):
        normalized_shape = target_shape
    elif isinstance(target_shape, Sequence) and not isinstance(target_shape, (str, bytes)):
        normalized_shape = SymbolShape(list(target_shape))
    else:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.broadcast_to 参数校验",
                expected="broadcast_to target_shape must be iterable shape",
                actual=type(target_shape).__name__,
                action=ERROR_ACTION,
            )
        )

    input_values = source.shape.get_values()
    target_values = normalized_shape.get_values()

    if len(target_values) < len(input_values):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.broadcast_to 参数校验",
                expected="broadcast_to target rank must be >= input rank",
                actual=f"input_rank={len(input_values)} target_rank={len(target_values)}",
                action=ERROR_ACTION,
            )
        )

    for input_dim, target_dim in zip(reversed(input_values), reversed(target_values), strict=False):
        if input_dim == target_dim:
            continue
        if input_dim == 1:
            continue
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.broadcast_to 参数校验",
                expected="broadcast_to dimension mismatch",
                actual=f"input={input_dim} target={target_dim}",
                action=ERROR_ACTION,
            )
        )

    return Memory(
        normalized_shape,
        source.dtype,
        space=space,
        format=Farmat.Norm,
    )

__all__ = ["broadcast", "broadcast_to"]
