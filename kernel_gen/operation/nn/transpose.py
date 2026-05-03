"""NN operation transpose helper.


功能说明:
- 提供 transpose 运算与 perm 规范化 helper。

API 列表:
- `transpose(value: Memory, perm: Sequence[int]) -> Memory`

使用示例:
- from kernel_gen.operation.nn.transpose import transpose

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/nn/test_structured.py
- 功能实现: kernel_gen/operation/nn/transpose.py
"""

from __future__ import annotations

from collections.abc import Sequence

from kernel_gen.core.contracts import default_stride
from kernel_gen.core.error import (
    ERROR_ACTION,
    ERROR_TEMPLATE,
    ErrorKind,
    ErrorModule,
    kernel_code_error,
)
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_shape import SymbolShape


def _normalize_transpose_perm(perm: Sequence[int], rank: int) -> list[int]:
    """规范化 transpose 的 perm 参数。


    功能说明:
    - 要求 perm 为非字符串序列，且元素必须是 int 但不能是 bool。
    - 要求 perm 长度与输入 rank 一致，并且是 `0..rank-1` 的排列。

    使用示例:
    - _normalize_transpose_perm([1, 0], rank=2)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_structured.py
    - 功能实现: kernel_gen/operation/nn/transpose.py
    """
    if isinstance(perm, (str, bytes)) or not isinstance(perm, Sequence):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.transpose 参数校验",
                expected="transpose perm must be a sequence of int",
                actual=type(perm).__name__,
                action=ERROR_ACTION,
            )
        )

    normalized_perm = list(perm)
    if len(normalized_perm) != rank:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.transpose 参数校验",
                expected="transpose perm length must equal input rank",
                actual=f"perm_len={len(normalized_perm)} rank={rank}",
                action=ERROR_ACTION,
            )
        )

    for index, axis in enumerate(normalized_perm):
        if isinstance(axis, bool) or not isinstance(axis, int):
            raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
                ERROR_TEMPLATE.format(
                    scene="nn.transpose 参数校验",
                    expected="transpose perm element must be int",
                    actual=f"index={index} type={type(axis).__name__}",
                    action=ERROR_ACTION,
                )
            )

    if sorted(normalized_perm) != list(range(rank)):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.transpose 参数校验",
                expected="transpose perm must be a permutation of input axes",
                actual=f"perm={normalized_perm} rank={rank}",
                action=ERROR_ACTION,
            )
        )

    return normalized_perm

def transpose(value: Memory, perm: Sequence[int]) -> Memory:
    """按指定 perm 物化转置 Memory 的轴顺序。


    功能说明:
    - 仅接受 Memory 输入，输出保留输入的 dtype/space/format。
    - 按 perm 重排 shape，并为转置后的目标 memory 生成默认连续 stride。
    - 对非法 perm 长度、元素类型或非排列情形直接报错。

    使用示例:
    - transpose(Memory([2, 3], NumericType.Float32), perm=[1, 0])

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_structured.py
    - 功能实现: kernel_gen/operation/nn/transpose.py
    """
    if not isinstance(value, Memory):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.transpose 参数校验",
                expected="transpose value must be Memory",
                actual=type(value).__name__,
                action=ERROR_ACTION,
            )
        )

    perm_values = _normalize_transpose_perm(perm, rank=len(value.shape))
    shape_dims = value.shape.get_shape()
    transposed_shape = SymbolShape([shape_dims[index] for index in perm_values])
    transposed_stride = default_stride(transposed_shape)
    return Memory(
        transposed_shape,
        value.dtype,
        space=value.space,
        stride=transposed_stride,
        format=value.format,
    )

__all__ = ["transpose"]
