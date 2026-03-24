"""NN operation API.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 提供 Memory 的逐元素算术、比较与显式 broadcast 运算 API。

使用示例:
- from kernel_gen.operation.nn import add, broadcast, eq
- result = add(mem, 1)
- expanded = broadcast(mem, Memory(["M", "N"], NumericType.Float32))

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/test_operation_nn.py
- 功能实现: kernel_gen/operation/nn.py
"""

from __future__ import annotations

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
    - 按固定优先级选择更靠前的类型。
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
        raise TypeError("Unsupported dtype for nn.add") from exc
    return lhs if lhs_rank <= rhs_rank else rhs


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
        raise ValueError("Implicit broadcast dimension mismatch")
    if lhs_dim == rhs_dim:
        return lhs_dim
    if lhs_dim == 1:
        return rhs_dim
    if rhs_dim == 1:
        return lhs_dim
    raise ValueError("Implicit broadcast dimension mismatch")


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
        raise TypeError("Memory dtype mismatch")
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
        raise TypeError("At least one operand must be Memory")


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
        raise TypeError("Unsupported scalar type for nn operation")


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
    raise TypeError("Unsupported scalar type for nn operation")


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
    - 仅允许 singleton dim 扩张。

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
        raise ValueError("broadcast dimension mismatch")
    return SymbolShape(result)


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
        return lhs._clone_with_dtype(lhs.dtype)
    _ensure_scalar_value(lhs)
    return rhs._clone_with_dtype(rhs.dtype)


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
        return lhs._clone_with_dtype(lhs.dtype)
    _ensure_scalar_value(lhs)
    return rhs._clone_with_dtype(rhs.dtype)


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
        return lhs._clone_with_dtype(lhs.dtype)
    _ensure_scalar_value(lhs)
    return rhs._clone_with_dtype(rhs.dtype)


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
        raise TypeError("matmul operands must be Memory")
    lhs_values = lhs.shape.get_values()
    rhs_values = rhs.shape.get_values()
    if len(lhs_values) != 2 or len(rhs_values) != 2:
        raise ValueError("matmul operands must be rank-2 Memory")
    if lhs_values[1] != rhs_values[0]:
        raise ValueError("matmul contracting dimension mismatch")
    if lhs.space is not rhs.space:
        raise ValueError("matmul space mismatch")
    result_dtype = _resolve_add_dtype(lhs.dtype, rhs.dtype)
    result_space = lhs.space if memoryspace is None else memoryspace
    return Memory(
        [lhs_values[0], rhs_values[1]],
        result_dtype,
        space=result_space,
        stride=_build_add_stride(SymbolShape([lhs_values[0], rhs_values[1]])),
        format=Farmat.Norm,
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
        raise TypeError("broadcast value must be Memory")
    if not isinstance(target, Memory):
        raise TypeError("broadcast target must be Memory")
    input_values = value.shape.get_values()
    target_values = target.shape.get_values()

    if len(target_values) < len(input_values):
        raise ValueError("broadcast target rank must be >= input rank")

    for input_dim, target_dim in zip(reversed(input_values), reversed(target_values), strict=False):
        if input_dim == target_dim:
            continue
        if input_dim == 1:
            continue
        raise ValueError("broadcast dimension mismatch")

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
    "matmul",
    "broadcast",
    "broadcast_to",
]
