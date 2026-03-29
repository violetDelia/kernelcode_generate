"""NN operation API.

创建者: 金铲铲大作战
最后一次更改: 我不是牛马

功能说明:
- 提供 Memory 的逐元素算术、比较与显式 broadcast 运算 API。
- 提供常用激活函数（relu/leaky_relu/sigmoid/tanh/hard_sigmoid）API。

使用示例:
- from kernel_gen.operation.nn import add, broadcast, eq, relu
- result = add(mem, 1)
- activated = relu(mem)
- expanded = broadcast(mem, Memory(["M", "N"], NumericType.Float32))

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/test_operation_nn.py
- 功能实现: kernel_gen/operation/nn.py
"""

from __future__ import annotations

import math

from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_shape import SymbolShape
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
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
_NN_FLOAT_DTYPES = {
    NumericType.Float16,
    NumericType.BFloat16,
    NumericType.Float32,
    NumericType.Float64,
}
_ERROR_TEMPLATE = "场景: {scene}; 期望: {expected}; 实际: {actual}; 建议动作: {action}"
_ERROR_ACTION = "请按接口约束传参"
_ERROR_SCENE = "nn operation 参数校验"


class _AddStrideDim(SymbolDim):
    """nn.add 默认 stride 的符号维度包装。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 对含符号表达式的维度返回字符串形式，避免对外泄露 sympy 表达式。

    使用示例:
    - _AddStrideDim("N").get_value()

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """

    def get_value(self: "_AddStrideDim") -> int | str:
        expr = self.get_symbol()
        if expr.free_symbols:
            return str(expr)
        return super().get_value()


def _build_add_stride(shape: SymbolShape) -> SymbolShape:
    """构建 nn.add 默认 stride。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 按连续行主序生成 stride。
    - 动态维度返回可序列化为字符串的符号维度。

    使用示例:
    - _build_add_stride(SymbolShape(["M", "N"]))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
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
    最后一次更改: 小李飞刀

    功能说明:
    - 按固定优先级选择顺序更靠后的类型。
    - 不支持的 dtype 触发 TypeError。

    使用示例:
    - _resolve_add_dtype(NumericType.Int32, NumericType.Float32)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
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
    最后一次更改: 小李飞刀

    功能说明:
    - 标量按 Int32 参与类型提升规则。

    使用示例:
    - _resolve_scalar_dtype(NumericType.Int8)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    return _resolve_add_dtype(memory_dtype, NumericType.Int32)


def _merge_broadcast_dim(lhs_dim: int | str, rhs_dim: int | str) -> int | str:
    """合并两个维度为隐式 broadcast 目标维度。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 维度相等时返回该维度。
    - 任一侧为静态 1 时返回另一侧。
    - 其他情况视为不兼容。

    使用示例:
    - _merge_broadcast_dim(1, "N")

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
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


def _infer_implicit_broadcast_shape(lhs: Memory, rhs: Memory) -> SymbolShape:
    """推导逐元素隐式 broadcast 的共同目标 shape。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 按尾维对齐规则合并维度。
    - 对较小 rank 的一侧视为前置维补 1。

    使用示例:
    - _infer_implicit_broadcast_shape(lhs, rhs)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    lhs_values = lhs.shape.get_values()
    rhs_values = rhs.shape.get_values()
    lhs_rank = len(lhs_values)
    rhs_rank = len(rhs_values)
    max_rank = lhs_rank if lhs_rank >= rhs_rank else rhs_rank
    result_reversed: list[int | str] = []

    for idx in range(1, max_rank + 1):
        lhs_dim = lhs_values[-idx] if idx <= lhs_rank else 1
        rhs_dim = rhs_values[-idx] if idx <= rhs_rank else 1
        result_reversed.append(_merge_broadcast_dim(lhs_dim, rhs_dim))

    return SymbolShape(list(reversed(result_reversed)))


def _binary_memory_result(lhs: Memory, rhs: Memory) -> Memory:
    """逐元素算术 Memory/Memory 结果推导。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持隐式 broadcast 推导目标 shape。
    - dtype 使用 nn 算术固定优先级决议。
    - 当 format/stride 不一致时回落默认布局。

    使用示例:
    - _binary_memory_result(lhs, rhs)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    result_dtype = _resolve_add_dtype(lhs.dtype, rhs.dtype)
    lhs_values = lhs.shape.get_values()
    rhs_values = rhs.shape.get_values()
    if lhs_values == rhs_values:
        if lhs.format is rhs.format and lhs.stride.get_values() == rhs.stride.get_values():
            if lhs.dtype is rhs.dtype:
                return lhs + rhs
            return lhs._clone_with_dtype(result_dtype)
        return Memory(
            lhs.shape,
            result_dtype,
            space=lhs.space,
            stride=_build_add_stride(lhs.shape),
            format=Farmat.Norm,
        )
    target_shape = _infer_implicit_broadcast_shape(lhs, rhs)
    return Memory(
        target_shape,
        result_dtype,
        space=lhs.space,
        stride=_build_add_stride(target_shape),
        format=Farmat.Norm,
    )


def _binary_add_result(lhs: Memory, rhs: Memory) -> Memory:
    """逐元素加法 Memory/Memory 结果推导。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持隐式 broadcast 推导目标 shape。
    - dtype 使用 nn.add 固定优先级决议。
    - 当 format/stride 不一致时回落默认布局。

    使用示例:
    - _binary_add_result(lhs, rhs)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    result_dtype = _resolve_add_dtype(lhs.dtype, rhs.dtype)
    lhs_values = lhs.shape.get_values()
    rhs_values = rhs.shape.get_values()
    if lhs_values == rhs_values:
        if lhs.format is rhs.format and lhs.stride.get_values() == rhs.stride.get_values():
            if lhs.dtype is rhs.dtype:
                return lhs + rhs
            return lhs._clone_with_dtype(result_dtype)
        return Memory(
            lhs.shape,
            result_dtype,
            space=lhs.space,
            stride=_build_add_stride(lhs.shape),
            format=Farmat.Norm,
        )
    target_shape = _infer_implicit_broadcast_shape(lhs, rhs)
    return Memory(
        target_shape,
        result_dtype,
        space=lhs.space,
        stride=_build_add_stride(target_shape),
        format=Farmat.Norm,
    )


def _compare_memory_result(lhs: Memory, rhs: Memory) -> Memory:
    """逐元素比较 Memory/Memory 结果推导。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持隐式 broadcast 推导目标 shape。
    - 结果 dtype 固定为 Bool。

    使用示例:
    - _compare_memory_result(lhs, rhs)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    if lhs.dtype is not rhs.dtype:
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.compare 参数校验",
                expected="Memory dtype mismatch",
                actual=f"lhs={lhs.dtype} rhs={rhs.dtype}",
                action=_ERROR_ACTION,
            )
        )
    lhs_values = lhs.shape.get_values()
    rhs_values = rhs.shape.get_values()
    if lhs_values == rhs_values:
        return lhs._clone_with_dtype(NumericType.Bool)
    target_shape = _infer_implicit_broadcast_shape(lhs, rhs)
    return Memory(target_shape, NumericType.Bool, space=lhs.space, stride=None, format=lhs.format)


def _ensure_memory_operand(lhs: object, rhs: object) -> None:
    """校验至少一侧为 Memory。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅允许 Memory 或与 Memory 组合的二元运算。

    使用示例:
    - _ensure_memory_operand(mem, 1)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
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
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅允许 int/float/bool 标量。

    使用示例:
    - _ensure_scalar_value(1)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
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
    最后一次更改: 金铲铲大作战

    功能说明:
    - 允许 int/float/bool/SymbolDim 参与纯标量算术。

    使用示例:
    - _ensure_scalar_arithmetic_value(SymbolDim("N"))

    关联文件:
    - spec: spec/dsl/mlir_gen.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    if isinstance(value, SymbolDim):
        return
    _ensure_scalar_value(value)


def _ensure_float_memory(value: object, op_name: str) -> Memory:
    """校验激活函数的 Memory 与浮点 dtype 输入。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 仅接受 Memory 输入。
    - dtype 必须为浮点类型。

    使用示例:
    - _ensure_float_memory(mem, "relu")

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
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
    if value.dtype not in _NN_FLOAT_DTYPES:
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
    最后一次更改: 我不是牛马

    功能说明:
    - 仅接受 int/float，不接受 bool 或 SymbolDim。
    - 拒绝 NaN/Inf 数值。

    使用示例:
    - _ensure_activation_scalar("alpha", 0.2)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
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


def _apply_scalar_operator(lhs: object, rhs: object, op: str, rop: str) -> ScalarArithmeticValue:
    """执行纯标量算术并保持 Python 操作数顺序语义。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 优先尝试左操作数实现，失败后回退到右操作数反向实现。
    - 用于支持 symbol/int 混合的纯标量算术辅助路径。

    使用示例:
    - _apply_scalar_operator(SymbolDim("M"), 2, "__add__", "__radd__")

    关联文件:
    - spec: spec/dsl/mlir_gen.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/operation/nn.py
    """

    def _call_operator(target: object, method_name: str, operand: object) -> object:
        method = getattr(target, method_name, None)
        if method is None:
            return NotImplemented
        try:
            return method(operand)
        except TypeError:
            return NotImplemented

    _ensure_scalar_arithmetic_value(lhs)
    _ensure_scalar_arithmetic_value(rhs)

    direct_result = _call_operator(lhs, op, rhs)
    if direct_result is not NotImplemented:
        return direct_result
    reverse_result = _call_operator(rhs, rop, lhs)
    if reverse_result is not NotImplemented:
        return reverse_result
    raise TypeError(
        _ERROR_TEMPLATE.format(
            scene=_ERROR_SCENE,
            expected="Unsupported scalar type for nn operation",
            actual=f"lhs={type(lhs).__name__} rhs={type(rhs).__name__}",
            action=_ERROR_ACTION,
        )
    )


def _dispatch_scalar_binary(lhs: object, rhs: object, op: str, rop: str) -> ScalarArithmeticValue | None:
    """在无 Memory 参与时执行纯标量算术调度。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 当两侧都不是 Memory 时，直接返回 Python/SymbolDim 算术结果。
    - 当任一侧为 Memory 时返回 None，由 Memory 路径继续处理。

    使用示例:
    - _dispatch_scalar_binary(2, SymbolDim("N"), "__mul__", "__rmul__")

    关联文件:
    - spec: spec/dsl/mlir_gen.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    if isinstance(lhs, Memory) or isinstance(rhs, Memory):
        return None
    return _apply_scalar_operator(lhs, rhs, op, rop)


def _infer_broadcast_shape(lhs: SymbolShape, rhs: SymbolShape) -> SymbolShape:
    """推导逐元素隐式 broadcast 的目标 shape。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 按尾维对齐规则推导共同目标 shape。
    - 仅允许 singleton dim 扩张，"?" 仅与 "?" 兼容。

    使用示例:
    - _infer_broadcast_shape(SymbolShape([1, "B"]), SymbolShape(["A", "B"]))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    lhs_dims = lhs.get_values()
    rhs_dims = rhs.get_values()
    max_rank = max(len(lhs_dims), len(rhs_dims))
    result_reversed: list[int | str] = []
    for index in range(1, max_rank + 1):
        lhs_dim = lhs_dims[-index] if index <= len(lhs_dims) else 1
        rhs_dim = rhs_dims[-index] if index <= len(rhs_dims) else 1
        result_reversed.append(_merge_broadcast_dim(lhs_dim, rhs_dim))
    return SymbolShape(list(reversed(result_reversed)))


def _broadcast_memory_pair(lhs: Memory, rhs: Memory) -> tuple[Memory, Memory]:
    """为逐元素运算执行隐式 broadcast。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 若 shape 不一致但可广播，则显式扩张到共同目标 shape。

    使用示例:
    - lhs_b, rhs_b = _broadcast_memory_pair(lhs, rhs)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
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


def _dispatch_binary(lhs: object, rhs: object, op: str, rop: str) -> ArithmeticResult:
    """二元算术调度。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 根据 Memory 所在侧选择正向或反向运算。

    使用示例:
    - _dispatch_binary(mem, 1, "__add__", "__radd__")

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    scalar_result = _dispatch_scalar_binary(lhs, rhs, op, rop)
    if scalar_result is not None:
        return scalar_result
    _ensure_memory_operand(lhs, rhs)
    if isinstance(lhs, Memory) and isinstance(rhs, Memory):
        return _binary_memory_result(lhs, rhs)
    if isinstance(lhs, Memory):
        _ensure_scalar_value(rhs)
        return lhs._clone_with_dtype(_resolve_scalar_dtype(lhs.dtype))
    _ensure_scalar_value(lhs)
    return rhs._clone_with_dtype(_resolve_scalar_dtype(rhs.dtype))


def _dispatch_compare(lhs: object, rhs: object, op: str, rop: str) -> Memory:
    """二元比较调度。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 保持比较方向的调度规则。

    使用示例:
    - _dispatch_compare(mem, 1, "__lt__", "__gt__")

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    _ensure_memory_operand(lhs, rhs)
    if isinstance(lhs, Memory) and isinstance(rhs, Memory):
        return _compare_memory_result(lhs, rhs)
    if isinstance(lhs, Memory):
        _ensure_scalar_value(rhs)
        return lhs._clone_with_dtype(NumericType.Bool)
    _ensure_scalar_value(lhs)
    return rhs._clone_with_dtype(NumericType.Bool)


def add(lhs: object, rhs: object) -> ArithmeticResult:
    """逐元素加法。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 Memory 与 Memory/标量的加法。
    - 当两侧都为纯标量时，复用 Python / SymbolDim 的加法结果。

    使用示例:
    - add(mem, 1)
    - add(SymbolDim("M"), 2)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    返回与限制：

    - 当任一侧为 `Memory` 时，返回 `Memory`。
    - 当两侧都为纯标量时，返回 Python 标量或 `SymbolDim` 算术结果。
    """
    scalar_result = _dispatch_scalar_binary(lhs, rhs, "__add__", "__radd__")
    if scalar_result is not None:
        return scalar_result
    _ensure_memory_operand(lhs, rhs)
    if isinstance(lhs, Memory) and isinstance(rhs, Memory):
        return _binary_add_result(lhs, rhs)
    if isinstance(lhs, Memory):
        _ensure_scalar_value(rhs)
        return lhs._clone_with_dtype(_resolve_scalar_dtype(lhs.dtype))
    _ensure_scalar_value(lhs)
    return rhs._clone_with_dtype(_resolve_scalar_dtype(rhs.dtype))


def sub(lhs: object, rhs: object) -> ArithmeticResult:
    """逐元素减法。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 Memory 与 Memory/标量的减法。
    - 当两侧都为纯标量时，复用 Python / SymbolDim 的减法结果。

    使用示例:
    - sub(mem, 1)
    - sub(SymbolDim("M"), 2)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    返回与限制：

    - 当任一侧为 `Memory` 时，返回 `Memory`。
    - 当两侧都为纯标量时，返回 Python 标量或 `SymbolDim` 算术结果。
    """
    return _dispatch_binary(lhs, rhs, "__sub__", "__rsub__")


def mul(lhs: object, rhs: object) -> ArithmeticResult:
    """逐元素乘法。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 Memory 与 Memory/标量的乘法。
    - 当两侧都为纯标量时，复用 Python / SymbolDim 的乘法结果。

    使用示例:
    - mul(mem, 2)
    - mul(2, SymbolDim("N"))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    返回与限制：

    - 当任一侧为 `Memory` 时，返回 `Memory`。
    - 当两侧都为纯标量时，返回 Python 标量或 `SymbolDim` 算术结果。
    """
    return _dispatch_binary(lhs, rhs, "__mul__", "__rmul__")


def truediv(lhs: object, rhs: object) -> ArithmeticResult:
    """逐元素除法。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 Memory 与 Memory/标量的除法。
    - 当两侧都为纯标量时，复用 Python / SymbolDim 的除法结果。

    使用示例:
    - truediv(mem, 2)
    - truediv(SymbolDim("M"), 2)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    返回与限制：

    - 当任一侧为 `Memory` 时，返回 `Memory`。
    - 当两侧都为纯标量时，返回 Python 标量或 `SymbolDim` 算术结果。
    """
    return _dispatch_binary(lhs, rhs, "__truediv__", "__rtruediv__")


def floordiv(lhs: object, rhs: object) -> ArithmeticResult:
    """逐元素整除。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 Memory 与 Memory/标量的整除。
    - 当两侧都为纯标量时，复用 Python / SymbolDim 的整除结果。

    使用示例:
    - floordiv(mem, 2)
    - floordiv(7, SymbolDim("N"))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    返回与限制：

    - 当任一侧为 `Memory` 时，返回 `Memory`。
    - 当两侧都为纯标量时，返回 Python 标量或 `SymbolDim` 算术结果。
    """
    scalar_result = _dispatch_scalar_binary(lhs, rhs, "__floordiv__", "__rfloordiv__")
    if scalar_result is not None:
        return scalar_result
    _ensure_memory_operand(lhs, rhs)
    if isinstance(lhs, Memory) and isinstance(rhs, Memory):
        return _binary_memory_result(lhs, rhs)
    if isinstance(lhs, Memory):
        _ensure_scalar_value(rhs)
        return lhs._clone_with_dtype(_resolve_scalar_dtype(lhs.dtype))
    _ensure_scalar_value(lhs)
    return rhs._clone_with_dtype(_resolve_scalar_dtype(rhs.dtype))


def eq(lhs: object, rhs: object) -> Memory:
    """逐元素相等比较。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 Memory 与 Memory/标量的相等比较。

    使用示例:
    - eq(mem, other)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    return _dispatch_compare(lhs, rhs, "__eq__", "__eq__")


def ne(lhs: object, rhs: object) -> Memory:
    """逐元素不等比较。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 Memory 与 Memory/标量的不等比较。

    使用示例:
    - ne(mem, other)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    return _dispatch_compare(lhs, rhs, "__ne__", "__ne__")


def lt(lhs: object, rhs: object) -> Memory:
    """逐元素小于比较。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 Memory 与 Memory/标量的小于比较。

    使用示例:
    - lt(mem, 0)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    return _dispatch_compare(lhs, rhs, "__lt__", "__gt__")


def le(lhs: object, rhs: object) -> Memory:
    """逐元素小于等于比较。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 Memory 与 Memory/标量的小于等于比较。

    使用示例:
    - le(mem, 0)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    return _dispatch_compare(lhs, rhs, "__le__", "__ge__")


def gt(lhs: object, rhs: object) -> Memory:
    """逐元素大于比较。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 Memory 与 Memory/标量的大于比较。

    使用示例:
    - gt(mem, other)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    return _dispatch_compare(lhs, rhs, "__gt__", "__lt__")


def ge(lhs: object, rhs: object) -> Memory:
    """逐元素大于等于比较。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 Memory 与 Memory/标量的大于等于比较。

    使用示例:
    - ge(mem, other)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    return _dispatch_compare(lhs, rhs, "__ge__", "__le__")


def relu(value: object) -> Memory:
    """逐元素 ReLU 激活。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 仅接受 Memory 输入，dtype 需为浮点类型。
    - 输出继承输入的 shape/dtype/space/format/stride。

    使用示例:
    - relu(Memory(["M", "N"], NumericType.Float32))
    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    memory = _ensure_float_memory(value, "relu")
    return memory._clone_with_dtype(memory.dtype)


def leaky_relu(value: object, alpha: int | float = 0.01) -> Memory:
    """逐元素 Leaky ReLU 激活。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 仅接受 Memory 输入，dtype 需为浮点类型。
    - alpha 必须为有限的 int/float。
    - 输出继承输入的 shape/dtype/space/format/stride。

    使用示例:
    - leaky_relu(Memory(["M", "N"], NumericType.Float16), alpha=0.2)
    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    memory = _ensure_float_memory(value, "leaky_relu")
    _ensure_activation_scalar("alpha", alpha)
    return memory._clone_with_dtype(memory.dtype)


def sigmoid(value: object) -> Memory:
    """逐元素 Sigmoid 激活。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 仅接受 Memory 输入，dtype 需为浮点类型。
    - 输出继承输入的 shape/dtype/space/format/stride。

    使用示例:
    - sigmoid(Memory(["M", "N"], NumericType.Float32))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    memory = _ensure_float_memory(value, "sigmoid")
    return memory._clone_with_dtype(memory.dtype)


def tanh(value: object) -> Memory:
    """逐元素 Tanh 激活。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 仅接受 Memory 输入，dtype 需为浮点类型。
    - 输出继承输入的 shape/dtype/space/format/stride。

    使用示例:
    - tanh(Memory(["M", "N"], NumericType.Float32))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    memory = _ensure_float_memory(value, "tanh")
    return memory._clone_with_dtype(memory.dtype)


def hard_sigmoid(value: object, alpha: int | float = 0.2, beta: int | float = 0.5) -> Memory:
    """逐元素 Hard Sigmoid 激活。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 仅接受 Memory 输入，dtype 需为浮点类型。
    - alpha/beta 必须为有限的 int/float。
    - 输出继承输入的 shape/dtype/space/format/stride。

    使用示例:
    - hard_sigmoid(Memory(["M", "N"], NumericType.Float32), alpha=0.2, beta=0.5)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    memory = _ensure_float_memory(value, "hard_sigmoid")
    _ensure_activation_scalar("alpha", alpha)
    _ensure_activation_scalar("beta", beta)
    return memory._clone_with_dtype(memory.dtype)


def softmax(value: object, axis: int = -1) -> Memory:
    """沿指定轴执行 softmax 归一化。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅接受 Memory 输入，并校验 dtype 与 axis。
    - 数值稳定语义约束为 exp(x - max(x)) / sum(exp(x - max(x)))。
    - 输出 shape/dtype/space/format/stride 与输入保持一致。

    使用示例:
    - softmax(Memory(["M", "N"], NumericType.Float32))
    - softmax(Memory(["B", "C", "H", "W"], NumericType.Float32), axis=1)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    if not isinstance(value, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.softmax 参数校验",
                expected="softmax value must be Memory",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if value.dtype not in (
        NumericType.Float16,
        NumericType.BFloat16,
        NumericType.Float32,
        NumericType.Float64,
    ):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.softmax 参数校验",
                expected="softmax value dtype must be float",
                actual=str(value.dtype),
                action=_ERROR_ACTION,
            )
        )
    if isinstance(axis, bool) or not isinstance(axis, int):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.softmax 参数校验",
                expected="softmax axis must be int",
                actual=type(axis).__name__,
                action=_ERROR_ACTION,
            )
        )
    rank = len(value.shape)
    if axis < -rank or axis >= rank:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.softmax 参数校验",
                expected="softmax axis out of range",
                actual=f"axis={axis} rank={rank}",
                action=_ERROR_ACTION,
            )
        )
    _ = axis + rank if axis < 0 else axis
    return value._clone_with_dtype(value.dtype)


def fc(value: object, weight: object, bias: object | None = None) -> Memory:
    """全连接（fully connected）运算。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 Memory 的末维与权重输入特征维线性变换。
    - bias 可选，提供时需与输出特征维对齐。

    使用示例:
    - fc(Memory(["B", "K"], NumericType.Float32), Memory(["N", "K"], NumericType.Float32))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    if not isinstance(value, Memory) or not isinstance(weight, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.fc 参数校验",
                expected="fc operands must be Memory",
                actual=f"value={type(value).__name__} weight={type(weight).__name__}",
                action=_ERROR_ACTION,
            )
        )
    if bias is not None and not isinstance(bias, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.fc 参数校验",
                expected="fc bias must be Memory or None",
                actual=type(bias).__name__,
                action=_ERROR_ACTION,
            )
        )
    value_values = value.shape.get_values()
    weight_values = weight.shape.get_values()
    if len(value_values) < 2:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.fc 参数校验",
                expected="fc value rank must be >= 2",
                actual=f"rank={len(value_values)}",
                action=_ERROR_ACTION,
            )
        )
    if len(weight_values) != 2:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.fc 参数校验",
                expected="fc weight must be rank-2 Memory",
                actual=f"rank={len(weight_values)}",
                action=_ERROR_ACTION,
            )
        )
    if value_values[-1] != weight_values[1]:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.fc 参数校验",
                expected="fc input feature mismatch",
                actual=f"value={value_values[-1]} weight={weight_values[1]}",
                action=_ERROR_ACTION,
            )
        )
    if value.space is not weight.space:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.fc 参数校验",
                expected="fc space mismatch",
                actual=f"value={value.space} weight={weight.space}",
                action=_ERROR_ACTION,
            )
        )
    if bias is not None:
        bias_values = bias.shape.get_values()
        if len(bias_values) != 1 or bias_values[0] != weight_values[0]:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene="nn.fc 参数校验",
                    expected="fc bias shape mismatch",
                    actual=f"bias={bias_values} weight_out={weight_values[0]}",
                    action=_ERROR_ACTION,
                )
            )
        if bias.space is not value.space:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene="nn.fc 参数校验",
                    expected="fc space mismatch",
                    actual=f"bias={bias.space} value={value.space}",
                    action=_ERROR_ACTION,
                )
            )
    result_dtype = _resolve_add_dtype(value.dtype, weight.dtype)
    if bias is not None and _resolve_add_dtype(result_dtype, bias.dtype) is not result_dtype:
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.fc 参数校验",
                expected="fc bias dtype mismatch",
                actual=f"result={result_dtype} bias={bias.dtype}",
                action=_ERROR_ACTION,
            )
        )
    output_shape = [*value_values[:-1], weight_values[0]]
    return Memory(
        output_shape,
        result_dtype,
        space=value.space,
        stride=_build_add_stride(SymbolShape(output_shape)),
        format=Farmat.Norm,
    )


def matmul(lhs: object, rhs: object, memoryspace: MemorySpace | None = None) -> Memory:
    """二维矩阵乘。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅接受二维 Memory x Memory。
    - 校验 contracting dim 与 space 一致性。
    - dtype 按固定优先级决议。

    使用示例:
    - matmul(Memory(["M", "K"], NumericType.Float32), Memory(["K", "N"], NumericType.Float32))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    if not isinstance(lhs, Memory) or not isinstance(rhs, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.matmul 参数校验",
                expected="matmul operands must be Memory",
                actual=f"lhs={type(lhs).__name__} rhs={type(rhs).__name__}",
                action=_ERROR_ACTION,
            )
        )
    lhs_values = lhs.shape.get_values()
    rhs_values = rhs.shape.get_values()
    if len(lhs_values) != 2 or len(rhs_values) != 2:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.matmul 参数校验",
                expected="matmul operands must be rank-2 Memory",
                actual=f"lhs_rank={len(lhs_values)} rhs_rank={len(rhs_values)}",
                action=_ERROR_ACTION,
            )
        )
    if lhs_values[1] != rhs_values[0]:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.matmul 参数校验",
                expected="matmul contracting dimension mismatch",
                actual=f"lhs_k={lhs_values[1]} rhs_k={rhs_values[0]}",
                action=_ERROR_ACTION,
            )
        )
    if lhs.space is not rhs.space:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.matmul 参数校验",
                expected="matmul space mismatch",
                actual=f"lhs={lhs.space} rhs={rhs.space}",
                action=_ERROR_ACTION,
            )
        )
    result_dtype = _resolve_add_dtype(lhs.dtype, rhs.dtype)
    result_space = lhs.space if memoryspace is None else memoryspace
    return Memory(
        [lhs_values[0], rhs_values[1]],
        result_dtype,
        space=result_space,
        stride=_build_add_stride(SymbolShape([lhs_values[0], rhs_values[1]])),
        format=Farmat.Norm,
    )


def _normalize_img2col_param(name: str, value: int | SymbolDim, allow_zero: bool) -> SymbolDim:
    """规范化 img2col 参数为 SymbolDim。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅接受 int 或 SymbolDim。
    - 对静态可判定的值校验正数/非负约束。

    使用示例:
    - _normalize_img2col_param("kh", 3, allow_zero=False)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    if isinstance(value, bool):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.img2col 参数校验",
                expected=f"img2col {name} must be int or SymbolDim",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if isinstance(value, int):
        if allow_zero and value < 0:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene="nn.img2col 参数校验",
                    expected=f"img2col {name} must be >= 0",
                    actual=str(value),
                    action=_ERROR_ACTION,
                )
            )
        if not allow_zero and value <= 0:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene="nn.img2col 参数校验",
                    expected=f"img2col {name} must be > 0",
                    actual=str(value),
                    action=_ERROR_ACTION,
                )
            )
        return SymbolDim(value)
    if isinstance(value, SymbolDim):
        if not value.is_dynamic():
            resolved = value.get_value()
            if not isinstance(resolved, int):
                raise ValueError(
                    _ERROR_TEMPLATE.format(
                        scene="nn.img2col 参数校验",
                        expected=f"img2col {name} must be integer",
                        actual=str(resolved),
                        action=_ERROR_ACTION,
                    )
                )
            if allow_zero and resolved < 0:
                raise ValueError(
                    _ERROR_TEMPLATE.format(
                        scene="nn.img2col 参数校验",
                        expected=f"img2col {name} must be >= 0",
                        actual=str(resolved),
                        action=_ERROR_ACTION,
                    )
                )
            if not allow_zero and resolved <= 0:
                raise ValueError(
                    _ERROR_TEMPLATE.format(
                        scene="nn.img2col 参数校验",
                        expected=f"img2col {name} must be > 0",
                        actual=str(resolved),
                        action=_ERROR_ACTION,
                    )
                )
        return value
    raise TypeError(
        _ERROR_TEMPLATE.format(
            scene="nn.img2col 参数校验",
            expected=f"img2col {name} must be int or SymbolDim",
            actual=type(value).__name__,
            action=_ERROR_ACTION,
        )
    )


def _img2col_output_dim(
    size: SymbolDim,
    kernel: SymbolDim,
    stride: SymbolDim,
    dilation: SymbolDim,
    pad_low: SymbolDim,
    pad_high: SymbolDim,
) -> SymbolDim:
    """计算 img2col 的输出维度。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 按 floor((size + pad_low + pad_high - dilation*(kernel-1) - 1) / stride) + 1 计算。

    使用示例:
    - _img2col_output_dim(SymbolDim(5), SymbolDim(3), SymbolDim(1), SymbolDim(1), SymbolDim(1), SymbolDim(1))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    return ((size + pad_low + pad_high - dilation * (kernel - 1) - 1) // stride) + 1


def _normalize_conv_param(name: str, value: int | SymbolDim, allow_zero: bool) -> SymbolDim:
    """规范化 conv 参数为 SymbolDim。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅接受 int 或 SymbolDim。
    - 对静态可判定的值校验正数/非负约束。

    使用示例:
    - _normalize_conv_param("sh", 1, allow_zero=False)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    if isinstance(value, bool):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.conv 参数校验",
                expected=f"conv {name} must be int or SymbolDim",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if isinstance(value, int):
        if allow_zero and value < 0:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene="nn.conv 参数校验",
                    expected=f"conv {name} must be >= 0",
                    actual=str(value),
                    action=_ERROR_ACTION,
                )
            )
        if not allow_zero and value <= 0:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene="nn.conv 参数校验",
                    expected=f"conv {name} must be > 0",
                    actual=str(value),
                    action=_ERROR_ACTION,
                )
            )
        return SymbolDim(value)
    if isinstance(value, SymbolDim):
        if not value.is_dynamic():
            resolved = value.get_value()
            if not isinstance(resolved, int):
                raise ValueError(
                    _ERROR_TEMPLATE.format(
                        scene="nn.conv 参数校验",
                        expected=f"conv {name} must be integer",
                        actual=str(resolved),
                        action=_ERROR_ACTION,
                    )
                )
            if allow_zero and resolved < 0:
                raise ValueError(
                    _ERROR_TEMPLATE.format(
                        scene="nn.conv 参数校验",
                        expected=f"conv {name} must be >= 0",
                        actual=str(resolved),
                        action=_ERROR_ACTION,
                    )
                )
            if not allow_zero and resolved <= 0:
                raise ValueError(
                    _ERROR_TEMPLATE.format(
                        scene="nn.conv 参数校验",
                        expected=f"conv {name} must be > 0",
                        actual=str(resolved),
                        action=_ERROR_ACTION,
                    )
                )
        return value
    raise TypeError(
        _ERROR_TEMPLATE.format(
            scene="nn.conv 参数校验",
            expected=f"conv {name} must be int or SymbolDim",
            actual=type(value).__name__,
            action=_ERROR_ACTION,
        )
    )


def conv(
    value: object,
    weight: object,
    bias: object | None = None,
    sh: int | SymbolDim = 1,
    sw: int | SymbolDim = 1,
    dh: int | SymbolDim = 1,
    dw: int | SymbolDim = 1,
    ph: int | SymbolDim = 0,
    pw: int | SymbolDim = 0,
    pl: int | SymbolDim = 0,
    pr: int | SymbolDim = 0,
) -> Memory:
    """二维卷积（NCHW）语义推导。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验输入类型、rank、空间与 dtype 一致性。
    - 支持可选 bias 对齐 C_out。
    - 按公式推导输出高宽并保持 Memory 元信息约束。

    使用示例:
    - conv(Memory([1, 3, 32, 32], NumericType.Float32), Memory([8, 3, 3, 3], NumericType.Float32))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    if not isinstance(value, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.conv 参数校验",
                expected="conv value must be Memory",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if not isinstance(weight, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.conv 参数校验",
                expected="conv weight must be Memory",
                actual=type(weight).__name__,
                action=_ERROR_ACTION,
            )
        )
    if len(value.shape) != 4:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.conv 参数校验",
                expected="conv value must be rank-4 Memory",
                actual=f"rank={len(value.shape)}",
                action=_ERROR_ACTION,
            )
        )
    if len(weight.shape) != 4:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.conv 参数校验",
                expected="conv weight must be rank-4 Memory",
                actual=f"rank={len(weight.shape)}",
                action=_ERROR_ACTION,
            )
        )

    n_dim, c_in_dim, h_dim, w_dim = value.shape.get_shape()
    c_out_dim, c_in_weight_dim, kh_dim, kw_dim = weight.shape.get_shape()
    if c_in_dim != c_in_weight_dim:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.conv 参数校验",
                expected="conv input channel mismatch",
                actual=f"value={c_in_dim} weight={c_in_weight_dim}",
                action=_ERROR_ACTION,
            )
        )
    if value.dtype is not weight.dtype:
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.conv 参数校验",
                expected="conv dtype mismatch",
                actual=f"value={value.dtype} weight={weight.dtype}",
                action=_ERROR_ACTION,
            )
        )
    if value.space is not weight.space:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.conv 参数校验",
                expected="conv space mismatch",
                actual=f"value={value.space} weight={weight.space}",
                action=_ERROR_ACTION,
            )
        )

    if bias is not None:
        if not isinstance(bias, Memory):
            raise TypeError(
                _ERROR_TEMPLATE.format(
                    scene="nn.conv 参数校验",
                    expected="conv bias must be Memory",
                    actual=type(bias).__name__,
                    action=_ERROR_ACTION,
                )
            )
        if len(bias.shape) != 1:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene="nn.conv 参数校验",
                    expected="conv bias must be rank-1 Memory",
                    actual=f"rank={len(bias.shape)}",
                    action=_ERROR_ACTION,
                )
            )
        bias_dim = bias.shape.get_shape()[0]
        if bias_dim != c_out_dim:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene="nn.conv 参数校验",
                    expected="conv bias shape mismatch",
                    actual=f"bias={bias_dim} out={c_out_dim}",
                    action=_ERROR_ACTION,
                )
            )
        if bias.dtype is not value.dtype:
            raise TypeError(
                _ERROR_TEMPLATE.format(
                    scene="nn.conv 参数校验",
                    expected="conv bias dtype mismatch",
                    actual=f"bias={bias.dtype} value={value.dtype}",
                    action=_ERROR_ACTION,
                )
            )
        if bias.space is not value.space:
            raise ValueError(
                _ERROR_TEMPLATE.format(
                    scene="nn.conv 参数校验",
                    expected="conv bias space mismatch",
                    actual=f"bias={bias.space} value={value.space}",
                    action=_ERROR_ACTION,
                )
            )

    sh_dim = _normalize_conv_param("sh", sh, allow_zero=False)
    sw_dim = _normalize_conv_param("sw", sw, allow_zero=False)
    dh_dim = _normalize_conv_param("dh", dh, allow_zero=False)
    dw_dim = _normalize_conv_param("dw", dw, allow_zero=False)
    ph_dim = _normalize_conv_param("ph", ph, allow_zero=True)
    pw_dim = _normalize_conv_param("pw", pw, allow_zero=True)
    pl_dim = _normalize_conv_param("pl", pl, allow_zero=True)
    pr_dim = _normalize_conv_param("pr", pr, allow_zero=True)

    h_out = _img2col_output_dim(h_dim, kh_dim, sh_dim, dh_dim, ph_dim, pw_dim)
    w_out = _img2col_output_dim(w_dim, kw_dim, sw_dim, dw_dim, pl_dim, pr_dim)

    h_out_value = h_out.get_value()
    if isinstance(h_out_value, int) and h_out_value <= 0:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.conv 参数校验",
                expected="conv output height must be positive",
                actual=str(h_out_value),
                action=_ERROR_ACTION,
            )
        )
    w_out_value = w_out.get_value()
    if isinstance(w_out_value, int) and w_out_value <= 0:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.conv 参数校验",
                expected="conv output width must be positive",
                actual=str(w_out_value),
                action=_ERROR_ACTION,
            )
        )

    return Memory(
        SymbolShape([n_dim, c_out_dim, h_out, w_out]),
        value.dtype,
        space=value.space,
        format=Farmat.Norm,
    )


def img2col1d(
    value: object,
    kw: int | SymbolDim,
    sw: int | SymbolDim = 1,
    dw: int | SymbolDim = 1,
    pl: int | SymbolDim = 0,
    pr: int | SymbolDim = 0,
) -> Memory:
    """将三维输入按一维窗口展开为列矩阵。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验输入类型与 rank。
    - 校验 kw/sw/dw 与 padding 参数。
    - 返回 img2col1d 展开后的 Memory 描述。

    使用示例:
    - img2col1d(Memory([1, 3, 5], NumericType.Float32), kw=3, sw=1, dw=1, pl=1, pr=1)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    if not isinstance(value, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.img2col 参数校验",
                expected="img2col1d value must be Memory",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if len(value.shape) != 3:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.img2col 参数校验",
                expected="img2col1d value must be rank-3 Memory",
                actual=f"rank={len(value.shape)}",
                action=_ERROR_ACTION,
            )
        )

    kw_dim = _normalize_img2col_param("kw", kw, allow_zero=False)
    sw_dim = _normalize_img2col_param("sw", sw, allow_zero=False)
    dw_dim = _normalize_img2col_param("dw", dw, allow_zero=False)
    pl_dim = _normalize_img2col_param("pl", pl, allow_zero=True)
    pr_dim = _normalize_img2col_param("pr", pr, allow_zero=True)

    n_dim, c_dim, w_dim = value.shape.get_shape()
    w_out = _img2col_output_dim(w_dim, kw_dim, sw_dim, dw_dim, pl_dim, pr_dim)

    w_out_value = w_out.get_value()
    if isinstance(w_out_value, int) and w_out_value <= 0:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.img2col 参数校验",
                expected="img2col1d output width must be positive",
                actual=str(w_out_value),
                action=_ERROR_ACTION,
            )
        )

    out_shape = SymbolShape([n_dim, c_dim * kw_dim, w_out])
    return Memory(
        out_shape,
        value.dtype,
        space=value.space,
        stride=_build_add_stride(out_shape),
        format=Farmat.Norm,
    )


def img2col2d(
    value: object,
    kh: int | SymbolDim,
    kw: int | SymbolDim,
    sh: int | SymbolDim = 1,
    sw: int | SymbolDim = 1,
    dh: int | SymbolDim = 1,
    dw: int | SymbolDim = 1,
    ph: int | SymbolDim = 0,
    pw: int | SymbolDim = 0,
    pl: int | SymbolDim = 0,
    pr: int | SymbolDim = 0,
) -> Memory:
    """将四维输入按二维窗口展开为列矩阵。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验输入类型与 rank。
    - 校验 kernel/stride/dilation/padding 参数。
    - 返回 img2col2d 展开后的 Memory 描述。

    使用示例:
    - img2col2d(Memory([1, 3, 5, 5], NumericType.Float32), 3, 3, 1, 1, 1, 1, 1, 1, 1, 1)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    if not isinstance(value, Memory):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.img2col 参数校验",
                expected="img2col2d value must be Memory",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if len(value.shape) != 4:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.img2col 参数校验",
                expected="img2col2d value must be rank-4 Memory",
                actual=f"rank={len(value.shape)}",
                action=_ERROR_ACTION,
            )
        )

    kh_dim = _normalize_img2col_param("kh", kh, allow_zero=False)
    kw_dim = _normalize_img2col_param("kw", kw, allow_zero=False)
    sh_dim = _normalize_img2col_param("sh", sh, allow_zero=False)
    sw_dim = _normalize_img2col_param("sw", sw, allow_zero=False)
    dh_dim = _normalize_img2col_param("dh", dh, allow_zero=False)
    dw_dim = _normalize_img2col_param("dw", dw, allow_zero=False)
    ph_dim = _normalize_img2col_param("ph", ph, allow_zero=True)
    pw_dim = _normalize_img2col_param("pw", pw, allow_zero=True)
    pl_dim = _normalize_img2col_param("pl", pl, allow_zero=True)
    pr_dim = _normalize_img2col_param("pr", pr, allow_zero=True)

    n_dim, c_dim, h_dim, w_dim = value.shape.get_shape()
    h_out = _img2col_output_dim(h_dim, kh_dim, sh_dim, dh_dim, ph_dim, pw_dim)
    w_out = _img2col_output_dim(w_dim, kw_dim, sw_dim, dw_dim, pl_dim, pr_dim)

    h_out_value = h_out.get_value()
    if isinstance(h_out_value, int) and h_out_value <= 0:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.img2col 参数校验",
                expected="img2col2d output height must be positive",
                actual=str(h_out_value),
                action=_ERROR_ACTION,
            )
        )
    w_out_value = w_out.get_value()
    if isinstance(w_out_value, int) and w_out_value <= 0:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="nn.img2col 参数校验",
                expected="img2col2d output width must be positive",
                actual=str(w_out_value),
                action=_ERROR_ACTION,
            )
        )

    out_shape = SymbolShape([n_dim, c_dim * kh_dim * kw_dim, h_out * w_out])
    return Memory(
        out_shape,
        value.dtype,
        space=value.space,
        stride=_build_add_stride(out_shape),
        format=Farmat.Norm,
    )


def img2col(
    value: object,
    kh: int | SymbolDim,
    kw: int | SymbolDim,
    sh: int | SymbolDim,
    sw: int | SymbolDim,
    dh: int | SymbolDim,
    dw: int | SymbolDim,
    ph: int | SymbolDim,
    pw: int | SymbolDim,
    pl: int | SymbolDim,
    pr: int | SymbolDim,
) -> Memory:
    """禁用笼统 img2col 公开入口。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 禁止继续使用 img2col 作为公开入口。
    - 请改用 img2col1d 或 img2col2d。

    使用示例:
    - img2col(value, kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)  # 将抛出异常

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    raise ValueError(
        _ERROR_TEMPLATE.format(
            scene="nn.img2col 参数校验",
            expected="img2col is forbidden public name",
            actual="img2col called",
            action="请改用 img2col1d/img2col2d",
        )
    )


def broadcast(value: object, target: object) -> Memory:
    """显式广播 Memory 到目标描述。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 按尾维对齐规则扩张 singleton dim。
    - 返回结果在 shape/dtype/space/stride/format 上与 target 完全一致。

    使用示例:
    - broadcast(Memory([1, "N"], NumericType.Float32), Memory(["M", "N"], NumericType.Float32))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
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
            if target_dim == "?":
                raise ValueError(
                    _ERROR_TEMPLATE.format(
                        scene="nn.broadcast 参数校验",
                        expected="broadcast dimension mismatch",
                        actual=f"input={input_dim} target={target_dim}",
                        action=_ERROR_ACTION,
                    )
                )
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


def broadcast_to(value: object, target: object) -> Memory:
    """broadcast 的别名接口。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 复用 broadcast 语义。

    使用示例:
    - broadcast_to(mem, target)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn.py
    - 功能实现: kernel_gen/operation/nn.py
    """
    return broadcast(value, target)


__all__ = [
    "add",
    "sub",
    "mul",
    "truediv",
    "floordiv",
    "eq",
    "ne",
    "lt",
    "le",
    "gt",
    "ge",
    "relu",
    "leaky_relu",
    "sigmoid",
    "tanh",
    "hard_sigmoid",
    "matmul",
    "img2col1d",
    "img2col2d",
    "broadcast",
    "broadcast_to",
]
