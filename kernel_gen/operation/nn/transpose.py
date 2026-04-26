"""NN operation transpose helper.

创建者: 守护最好的爱莉希雅
最后一次更改: 金铲铲大作战

功能说明:
- 提供 transpose 运算与 perm 规范化 helper。

API 列表:
- `transpose(value: object, perm: object) -> Memory`

使用示例:
- from kernel_gen.operation.nn.transpose import transpose

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/test_operation_nn_structured.py
- 功能实现: kernel_gen/operation/nn/transpose.py
"""

from __future__ import annotations

from collections.abc import Sequence

from kernel_gen.common.errors import _ERROR_TEMPLATE
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_shape import SymbolShape

_ERROR_ACTION = "请按接口约束传参"

def _normalize_transpose_perm(perm: object, rank: int) -> list[int]:
    """规范化 transpose 的 perm 参数。

    创建者: 小李飞刀
    最后一次更改: jcc你莫辜负

    功能说明:
    - 要求 perm 为非字符串序列，且元素必须是 int 但不能是 bool。
    - 要求 perm 长度与输入 rank 一致，并且是 `0..rank-1` 的排列。

    使用示例:
    - _normalize_transpose_perm([1, 0], rank=2)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_structured.py
    - 功能实现: kernel_gen/operation/nn/transpose.py
    """
    if isinstance(perm, (str, bytes)) or not isinstance(perm, Sequence):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.transpose 参数校验",
                expected="transpose perm must be a sequence of int",
                actual=type(perm).__name__,
                action=_ERROR_ACTION,
            )
        )

    normalized_perm = list(perm)
    if len(normalized_perm) != rank:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.transpose 参数校验",
                expected="transpose perm length must equal input rank",
                actual=f"perm_len={len(normalized_perm)} rank={rank}",
                action=_ERROR_ACTION,
            )
        )

    for index, axis in enumerate(normalized_perm):
        if isinstance(axis, bool) or not isinstance(axis, int):
            raise TypeError(
                _ERROR_TEMPLATE.format(
                    scene="nn.transpose 参数校验",
                    expected="transpose perm element must be int",
                    actual=f"index={index} type={type(axis).__name__}",
                    action=_ERROR_ACTION,
                )
            )

    if sorted(normalized_perm) != list(range(rank)):
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.transpose 参数校验",
                expected="transpose perm must be a permutation of input axes",
                actual=f"perm={normalized_perm} rank={rank}",
                action=_ERROR_ACTION,
            )
        )

    return normalized_perm

def transpose(value: object, perm: object) -> Memory:
    """按指定 perm 重排 Memory 的轴顺序。

    创建者: 小李飞刀
    最后一次更改: jcc你莫辜负

    功能说明:
    - 仅接受 Memory 输入，输出保留输入的 dtype/space/format。
    - 按 perm 同步重排 shape 与 stride。
    - 对非法 perm 长度、元素类型或非排列情形直接报错。

    使用示例:
    - transpose(Memory([2, 3], NumericType.Float32), perm=[1, 0])

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_structured.py
    - 功能实现: kernel_gen/operation/nn/transpose.py
    """
    if not isinstance(value, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.transpose 参数校验",
                expected="transpose value must be Memory",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )

    perm_values = _normalize_transpose_perm(perm, rank=len(value.shape))
    shape_dims = value.shape.get_shape()
    stride_dims = value.stride.get_shape()
    transposed_shape = SymbolShape([shape_dims[index] for index in perm_values])
    transposed_stride = SymbolShape([stride_dims[index] for index in perm_values])
    return Memory(
        transposed_shape,
        value.dtype,
        space=value.space,
        stride=transposed_stride,
        format=value.format,
    )

__all__ = ["transpose"]
