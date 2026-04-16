"""NN operation common helpers.

创建者: 小李飞刀
最后一次更改: jcc你莫辜负

功能说明:
- 提供 nn family 共享类型、常量与参数校验 helper

使用示例:
- from kernel_gen.operation.nn import add, broadcast, matmul, reduce_sum

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/test_operation_nn_elementwise.py
- test: test/operation/test_operation_nn_broadcast.py
- test: test/operation/test_operation_nn_structured.py
- test: test/operation/test_operation_nn_reduction.py
- 功能实现: kernel_gen/operation/_nn_common.py
"""

from __future__ import annotations

from collections.abc import Sequence
import math

from kernel_gen.common.errors import _ERROR_TEMPLATE
from kernel_gen.symbol_variable.dtype_constants import NN_FLOAT_DTYPES
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.symbol_shape import SymbolShape
from kernel_gen.symbol_variable.type import Farmat, NumericType

ScalarArithmeticValue = int | float | SymbolDim
ArithmeticResult = Memory | ScalarArithmeticValue

_NN_ADD_PROMOTION_ORDER = (
    NumericType.Int8,
    NumericType.Uint8,
    NumericType.Int16,
    NumericType.Uint16,
    NumericType.Int32,
    NumericType.Uint32,
    NumericType.Int64,
    NumericType.Uint64,
    NumericType.Float16,
    NumericType.BFloat16,
    NumericType.Float32,
    NumericType.Float64,
)
_NN_ADD_PROMOTION_RANK = {dtype: index for index, dtype in enumerate(_NN_ADD_PROMOTION_ORDER)}
_ERROR_ACTION = "请按接口约束传参"
_ERROR_SCENE = "nn operation 参数校验"

class _AddStrideDim(SymbolDim):
    """nn.add 默认 stride 的符号维度包装。

    创建者: 小李飞刀
    最后一次更改: jcc你莫辜负

    功能说明:
    - 对含符号表达式的维度返回字符串形式，避免对外泄露 sympy 表达式。

    使用示例:
    - _AddStrideDim("N").get_value()

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/_nn_common.py
    """

    def get_value(self: "_AddStrideDim") -> int | str:
        expr = self.get_symbol()
        if expr.free_symbols:
            return str(expr)
        return super().get_value()


def _build_add_stride(shape: SymbolShape) -> SymbolShape:
    """构建 nn.add 默认 stride。

    创建者: 小李飞刀
    最后一次更改: jcc你莫辜负

    功能说明:
    - 按连续行主序生成 stride。
    - 动态维度返回可序列化为字符串的符号维度。

    使用示例:
    - _build_add_stride(SymbolShape(["M", "N"]))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/_nn_common.py
    """
    stride_values: list[SymbolDim] = []
    running = SymbolDim(1)
    for dim in reversed(shape.get_shape()):
        stride_values.append(_AddStrideDim(running.get_symbol()))
        running = dim * running
    stride_values.reverse()
    return SymbolShape(stride_values)


def _resolve_add_dtype(lhs: NumericType, rhs: NumericType) -> NumericType:
    """解析 nn 算术的 dtype 决议。

    创建者: 小李飞刀
    最后一次更改: jcc你莫辜负

    功能说明:
    - 按固定优先级选择顺序更靠后的类型。
    - 不支持的 dtype 触发 TypeError。

    使用示例:
    - _resolve_add_dtype(NumericType.Int32, NumericType.Float32)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/_nn_common.py
    """
    try:
        lhs_rank = _NN_ADD_PROMOTION_RANK[lhs]
        rhs_rank = _NN_ADD_PROMOTION_RANK[rhs]
    except KeyError as exc:
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.add 参数校验",
                expected="Unsupported dtype for nn.add",
                actual=f"lhs={lhs} rhs={rhs}",
                action=_ERROR_ACTION,
            )
        ) from exc
    return lhs if lhs_rank >= rhs_rank else rhs


def _resolve_scalar_dtype(memory_dtype: NumericType) -> NumericType:
    """解析 Memory/标量路径的 dtype 决议。

    创建者: 小李飞刀
    最后一次更改: jcc你莫辜负

    功能说明:
    - 标量按 Int32 参与类型提升规则。

    使用示例:
    - _resolve_scalar_dtype(NumericType.Int8)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/_nn_common.py
    """
    return _resolve_add_dtype(memory_dtype, NumericType.Int32)


def _merge_broadcast_dim(lhs_dim: int | str, rhs_dim: int | str) -> int | str:
    """合并两个维度为隐式 broadcast 目标维度。

    创建者: 小李飞刀
    最后一次更改: jcc你莫辜负

    功能说明:
    - 维度相等时返回该维度。
    - 任一侧为静态 1 时返回另一侧。
    - 其他情况视为不兼容。

    使用示例:
    - _merge_broadcast_dim(1, "N")

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_broadcast.py
    - 功能实现: kernel_gen/operation/_nn_common.py
    """
    if lhs_dim == "?" or rhs_dim == "?":
        if lhs_dim == rhs_dim:
            return lhs_dim
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.add 参数校验",
                expected="Implicit broadcast dimension mismatch",
                actual=f"lhs={lhs_dim} rhs={rhs_dim}",
                action=_ERROR_ACTION,
            )
        )
    if lhs_dim == rhs_dim:
        return lhs_dim
    if lhs_dim == 1:
        return rhs_dim
    if rhs_dim == 1:
        return lhs_dim
    raise ValueError(
        _ERROR_TEMPLATE.format(
            scene="nn.add 参数校验",
            expected="Implicit broadcast dimension mismatch",
            actual=f"lhs={lhs_dim} rhs={rhs_dim}",
            action=_ERROR_ACTION,
        )
    )


def _ensure_memory_operand(lhs: object, rhs: object) -> None:
    """校验至少一侧为 Memory。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 仅允许 Memory 或与 Memory 组合的二元运算。

    使用示例:
    - _ensure_memory_operand(mem, 1)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/_nn_common.py
    """
    if not isinstance(lhs, Memory) and not isinstance(rhs, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected="At least one operand must be Memory",
                actual=f"lhs={type(lhs).__name__} rhs={type(rhs).__name__}",
                action=_ERROR_ACTION,
            )
        )


def _ensure_scalar_value(value: object) -> None:
    """校验标量输入类型。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 仅允许 int/float/bool 标量。

    使用示例:
    - _ensure_scalar_value(1)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/_nn_common.py
    """
    if isinstance(value, bool):
        return
    if not isinstance(value, (int, float)):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected="Unsupported scalar type for nn operation",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )


def _ensure_scalar_arithmetic_value(value: object) -> None:
    """校验纯标量算术输入类型。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 允许 int/float/bool/SymbolDim 参与纯标量算术。

    使用示例:
    - _ensure_scalar_arithmetic_value(SymbolDim("N"))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/_nn_common.py
    """
    if isinstance(value, SymbolDim):
        return
    _ensure_scalar_value(value)


def _ensure_float_memory(value: object, op_name: str) -> Memory:
    """校验激活函数的 Memory 与浮点 dtype 输入。

    创建者: 我不是牛马
    最后一次更改: jcc你莫辜负

    功能说明:
    - 仅接受 Memory 输入。
    - dtype 必须为浮点类型。

    使用示例:
    - _ensure_float_memory(mem, "relu")

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/_nn_common.py
    """
    if not isinstance(value, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene=f"nn.{op_name} 参数校验",
                expected=f"{op_name} value must be Memory",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if value.dtype not in NN_FLOAT_DTYPES:
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene=f"nn.{op_name} 参数校验",
                expected=f"{op_name} value dtype must be float",
                actual=str(value.dtype),
                action=_ERROR_ACTION,
            )
        )
    return value


def _ensure_activation_scalar(name: str, value: object) -> None:
    """校验激活函数数值参数。

    创建者: 我不是牛马
    最后一次更改: jcc你莫辜负

    功能说明:
    - 仅接受 int/float，不接受 bool 或 SymbolDim。
    - 拒绝 NaN/Inf 数值。

    使用示例:
    - _ensure_activation_scalar("alpha", 0.2)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/_nn_common.py
    """
    if isinstance(value, bool) or isinstance(value, SymbolDim):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.activation 参数校验",
                expected=f"{name} must be int or float",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if not isinstance(value, (int, float)):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.activation 参数校验",
                expected=f"{name} must be int or float",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if not math.isfinite(value):
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.activation 参数校验",
                expected=f"{name} must be finite",
                actual=str(value),
                action=_ERROR_ACTION,
            )
        )

__all__ = [
    "ArithmeticResult",
    "Farmat",
    "Memory",
    "MemorySpace",
    "NN_FLOAT_DTYPES",
    "NumericType",
    "ScalarArithmeticValue",
    "Sequence",
    "SymbolDim",
    "SymbolShape",
    "_AddStrideDim",
    "_ERROR_ACTION",
    "_ERROR_SCENE",
    "_ERROR_TEMPLATE",
    "_build_add_stride",
    "_ensure_activation_scalar",
    "_ensure_float_memory",
    "_ensure_memory_operand",
    "_ensure_scalar_arithmetic_value",
    "_ensure_scalar_value",
    "_merge_broadcast_dim",
    "_resolve_add_dtype",
    "_resolve_scalar_dtype",
    "math",
]
