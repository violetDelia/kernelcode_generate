"""NN operation matmul helper.


功能说明:
- 提供二维矩阵乘运算。

API 列表:
- `matmul(lhs: Memory, rhs: Memory, memoryspace: MemorySpace | None = None) -> Memory`

使用示例:
- from kernel_gen.operation.nn.matmul import matmul

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/nn/test_structured.py
- 功能实现: kernel_gen/operation/nn/matmul.py
"""

from __future__ import annotations

from kernel_gen.core.contracts import default_stride
from kernel_gen.core.error import (
    ERROR_ACTION,
    ERROR_TEMPLATE,
    ErrorKind,
    ErrorModule,
    kernel_code_error,
)
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_shape import SymbolShape
from kernel_gen.symbol_variable.type import Farmat, NumericType



def _resolve_add_dtype(lhs: NumericType, rhs: NumericType) -> NumericType:
    """按公开 `Memory` 算术语义推导 nn 结构化算子的结果 dtype。


    功能说明:
    - 复用 `Memory` 的公开加法路径推导 dtype。
    - 当 dtype 组合不受支持时，转为 `nn.matmul` 的稳定错误消息。

    使用示例:
    - _resolve_add_dtype(NumericType.Int32, NumericType.Float32)
    """

    try:
        return (Memory([1], lhs) + Memory([1], rhs)).get_type()
    except TypeError as exc:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.matmul 参数校验",
                expected="Unsupported dtype for nn.matmul",
                actual=f"lhs={lhs} rhs={rhs}",
                action=ERROR_ACTION,
            )
        ) from exc

def matmul(lhs: Memory, rhs: Memory, memoryspace: MemorySpace | None = None) -> Memory:
    """二维矩阵乘。


    功能说明:
    - 仅接受二维 Memory x Memory。
    - 校验 contracting dim 与 space 一致性。
    - dtype 按固定优先级决议。

    使用示例:
    - matmul(Memory(["M", "K"], NumericType.Float32), Memory(["K", "N"], NumericType.Float32))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/nn/test_structured.py
    - 功能实现: kernel_gen/operation/nn/matmul.py
    """
    if not isinstance(lhs, Memory) or not isinstance(rhs, Memory):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.matmul 参数校验",
                expected="matmul operands must be Memory",
                actual=f"lhs={type(lhs).__name__} rhs={type(rhs).__name__}",
                action=ERROR_ACTION,
            )
        )
    lhs_values = lhs.shape.get_values()
    rhs_values = rhs.shape.get_values()
    if len(lhs_values) != 2 or len(rhs_values) != 2:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.matmul 参数校验",
                expected="matmul operands must be rank-2 Memory",
                actual=f"lhs_rank={len(lhs_values)} rhs_rank={len(rhs_values)}",
                action=ERROR_ACTION,
            )
        )
    if lhs_values[1] != rhs_values[0]:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.matmul 参数校验",
                expected="matmul contracting dimension mismatch",
                actual=f"lhs_k={lhs_values[1]} rhs_k={rhs_values[0]}",
                action=ERROR_ACTION,
            )
        )
    if lhs.space is not rhs.space:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="nn.matmul 参数校验",
                expected="matmul space mismatch",
                actual=f"lhs={lhs.space} rhs={rhs.space}",
                action=ERROR_ACTION,
            )
        )
    result_dtype = _resolve_add_dtype(lhs.dtype, rhs.dtype)
    result_space = lhs.space if memoryspace is None else memoryspace
    return Memory(
        [lhs_values[0], rhs_values[1]],
        result_dtype,
        space=result_space,
        stride=default_stride(SymbolShape([lhs_values[0], rhs_values[1]])),
        format=Farmat.Norm,
    )

__all__ = ["matmul"]
