"""NN operation elementwise binary family.

创建者: 守护最好的爱莉希雅
最后一次更改: 金铲铲大作战

功能说明:
- 提供逐元素算术 family 与共享隐式 broadcast helper。

API 列表:
- `add(lhs: object, rhs: object) -> ArithmeticResult`
- `sub(lhs: object, rhs: object) -> ArithmeticResult`
- `mul(lhs: object, rhs: object) -> ArithmeticResult`
- `truediv(lhs: object, rhs: object) -> ArithmeticResult`
- `floordiv(lhs: object, rhs: object) -> ArithmeticResult`

使用示例:
- from kernel_gen.operation.nn.elementwise_binary import add, sub, mul

关联文件:
- spec: spec/operation/nn.md
- test: test/operation/test_operation_nn_elementwise.py
- 功能实现: kernel_gen/operation/nn/elementwise_binary.py
"""

from __future__ import annotations

from kernel_gen.common.contracts import default_stride
from kernel_gen.common.errors import _ERROR_TEMPLATE
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.symbol_shape import SymbolShape
from kernel_gen.symbol_variable.type import Farmat

ScalarArithmeticValue = int | float | SymbolDim
ArithmeticResult = Memory | ScalarArithmeticValue
_ERROR_ACTION = "请按接口约束传参"
_ERROR_SCENE = "nn operation 参数校验"


def _clone_shape(shape: SymbolShape | None) -> SymbolShape | None:
    """复制 `SymbolShape`，避免输出与输入共享符号实例。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 对 `Memory` 的 shape/stride 做逐维复制。
    - 保持符号表达式结构不变，同时断开实例别名。

    使用示例:
    - _clone_shape(SymbolShape(["M", "N"]))
    """

    if shape is None:
        return None
    return SymbolShape([SymbolDim(dim.get_symbol()) for dim in shape.get_shape()])


def _clone_memory_with_dtype(value: Memory, dtype: object) -> Memory:
    """按指定 dtype 复制 `Memory` 的公开元信息。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅通过公开 shape/stride/space/format 元信息构造结果。
    - 避免跨文件依赖 `Memory._clone_with_dtype(...)`。

    使用示例:
    - _clone_memory_with_dtype(Memory([1], NumericType.Float32), NumericType.Float32)
    """

    return Memory(
        _clone_shape(value.shape),
        dtype,
        space=value.space,
        stride=_clone_shape(value.stride),
        format=value.format,
    )


def _resolve_add_dtype(lhs: object, rhs: object) -> object:
    """按公开 `Memory` 算术语义推导 nn 算术结果 dtype。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 复用 `Memory` 的公开加法路径推导 dtype。
    - 当 dtype 组合不受支持时，转为 `nn.add` 的稳定错误消息。

    使用示例:
    - _resolve_add_dtype(NumericType.Int32, NumericType.Float32)
    """

    try:
        return (Memory([1], lhs) + Memory([1], rhs)).get_type()
    except TypeError as exc:
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="nn.add 参数校验",
                expected="Unsupported dtype for nn.add",
                actual=f"lhs={lhs} rhs={rhs}",
                action=_ERROR_ACTION,
            )
        ) from exc


def _resolve_scalar_dtype(memory_dtype: object) -> object:
    """解析 `Memory/标量` 路径的 dtype 决议。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 标量按 `Int32` 参与公开算术类型提升规则。

    使用示例:
    - _resolve_scalar_dtype(NumericType.Int8)
    """

    from kernel_gen.symbol_variable.type import NumericType

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
    """校验至少一侧为 `Memory`。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅允许 `Memory` 或与 `Memory` 组合的二元运算。

    使用示例:
    - _ensure_memory_operand(Memory([1], NumericType.Float32), 1)
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
    """校验公开标量输入类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅允许 `int/float/bool` 作为与 `Memory` 组合的公开标量。

    使用示例:
    - _ensure_scalar_value(1)
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

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 允许 `int/float/bool/SymbolDim` 参与纯标量算术。

    使用示例:
    - _ensure_scalar_arithmetic_value(SymbolDim("N"))
    """

    if isinstance(value, SymbolDim):
        return
    _ensure_scalar_value(value)

def _infer_implicit_broadcast_shape(lhs: Memory, rhs: Memory) -> SymbolShape:
    """推导逐元素隐式 broadcast 的共同目标 shape。

    创建者: 小李飞刀
    最后一次更改: jcc你莫辜负

    功能说明:
    - 按尾维对齐规则合并维度。
    - 对较小 rank 的一侧视为前置维补 1。

    使用示例:
    - _infer_implicit_broadcast_shape(lhs, rhs)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_binary.py
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
    最后一次更改: jcc你莫辜负

    功能说明:
    - 支持隐式 broadcast 推导目标 shape。
    - dtype 使用 nn 算术固定优先级决议。
    - 当 format/stride 不一致时回落默认布局。

    使用示例:
    - _binary_memory_result(lhs, rhs)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_binary.py
    """
    result_dtype = _resolve_add_dtype(lhs.dtype, rhs.dtype)
    lhs_values = lhs.shape.get_values()
    rhs_values = rhs.shape.get_values()
    if lhs_values == rhs_values:
        if lhs.format is rhs.format and lhs.stride.get_values() == rhs.stride.get_values():
            if lhs.dtype is rhs.dtype:
                return lhs + rhs
            return _clone_memory_with_dtype(lhs, result_dtype)
        return Memory(
            lhs.shape,
            result_dtype,
            space=lhs.space,
            stride=default_stride(lhs.shape),
            format=Farmat.Norm,
        )
    target_shape = _infer_implicit_broadcast_shape(lhs, rhs)
    return Memory(
        target_shape,
        result_dtype,
        space=lhs.space,
        stride=default_stride(target_shape),
        format=Farmat.Norm,
    )

def _binary_add_result(lhs: Memory, rhs: Memory) -> Memory:
    """逐元素加法 Memory/Memory 结果推导。

    创建者: 小李飞刀
    最后一次更改: jcc你莫辜负

    功能说明:
    - 支持隐式 broadcast 推导目标 shape。
    - dtype 使用 nn.add 固定优先级决议。
    - 当 format/stride 不一致时回落默认布局。

    使用示例:
    - _binary_add_result(lhs, rhs)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_binary.py
    """
    result_dtype = _resolve_add_dtype(lhs.dtype, rhs.dtype)
    lhs_values = lhs.shape.get_values()
    rhs_values = rhs.shape.get_values()
    if lhs_values == rhs_values:
        if lhs.format is rhs.format and lhs.stride.get_values() == rhs.stride.get_values():
            if lhs.dtype is rhs.dtype:
                return lhs + rhs
            return _clone_memory_with_dtype(lhs, result_dtype)
        return Memory(
            lhs.shape,
            result_dtype,
            space=lhs.space,
            stride=default_stride(lhs.shape),
            format=Farmat.Norm,
        )
    target_shape = _infer_implicit_broadcast_shape(lhs, rhs)
    return Memory(
        target_shape,
        result_dtype,
        space=lhs.space,
        stride=default_stride(target_shape),
        format=Farmat.Norm,
    )

def _apply_scalar_operator(lhs: object, rhs: object, op: str, rop: str) -> ScalarArithmeticValue:
    """执行纯标量算术并保持 Python 操作数顺序语义。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 优先尝试左操作数实现，失败后回退到右操作数反向实现。
    - 用于支持 symbol/int 混合的纯标量算术辅助路径。

    使用示例:
    - _apply_scalar_operator(SymbolDim("M"), 2, "__add__", "__radd__")

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_binary.py
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
    最后一次更改: jcc你莫辜负

    功能说明:
    - 当两侧都不是 Memory 时，直接返回 Python/SymbolDim 算术结果。
    - 当任一侧为 Memory 时返回 None，由 Memory 路径继续处理。

    使用示例:
    - _dispatch_scalar_binary(2, SymbolDim("N"), "__mul__", "__rmul__")

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_binary.py
    """
    if isinstance(lhs, Memory) or isinstance(rhs, Memory):
        return None
    return _apply_scalar_operator(lhs, rhs, op, rop)

def _dispatch_binary(lhs: object, rhs: object, op: str, rop: str) -> ArithmeticResult:
    """二元算术调度。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 根据 Memory 所在侧选择正向或反向运算。

    使用示例:
    - _dispatch_binary(mem, 1, "__add__", "__radd__")

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_binary.py
    """
    scalar_result = _dispatch_scalar_binary(lhs, rhs, op, rop)
    if scalar_result is not None:
        return scalar_result
    _ensure_memory_operand(lhs, rhs)
    if isinstance(lhs, Memory) and isinstance(rhs, Memory):
        return _binary_memory_result(lhs, rhs)
    if isinstance(lhs, Memory):
        _ensure_scalar_value(rhs)
        return _clone_memory_with_dtype(lhs, _resolve_scalar_dtype(lhs.dtype))
    _ensure_scalar_value(lhs)
    return _clone_memory_with_dtype(rhs, _resolve_scalar_dtype(rhs.dtype))

def add(lhs: object, rhs: object) -> ArithmeticResult:
    """逐元素加法。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 支持 Memory 与 Memory/标量的加法。
    - 当两侧都为纯标量时，复用 Python / SymbolDim 的加法结果。

    使用示例:
    - add(mem, 1)
    - add(SymbolDim("M"), 2)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_binary.py
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
        return _clone_memory_with_dtype(lhs, _resolve_scalar_dtype(lhs.dtype))
    _ensure_scalar_value(lhs)
    return _clone_memory_with_dtype(rhs, _resolve_scalar_dtype(rhs.dtype))

def sub(lhs: object, rhs: object) -> ArithmeticResult:
    """逐元素减法。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 支持 Memory 与 Memory/标量的减法。
    - 当两侧都为纯标量时，复用 Python / SymbolDim 的减法结果。

    使用示例:
    - sub(mem, 1)
    - sub(SymbolDim("M"), 2)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_binary.py
    返回与限制：

    - 当任一侧为 `Memory` 时，返回 `Memory`。
    - 当两侧都为纯标量时，返回 Python 标量或 `SymbolDim` 算术结果。
    """
    return _dispatch_binary(lhs, rhs, "__sub__", "__rsub__")

def mul(lhs: object, rhs: object) -> ArithmeticResult:
    """逐元素乘法。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 支持 Memory 与 Memory/标量的乘法。
    - 当两侧都为纯标量时，复用 Python / SymbolDim 的乘法结果。

    使用示例:
    - mul(mem, 2)
    - mul(2, SymbolDim("N"))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_binary.py
    返回与限制：

    - 当任一侧为 `Memory` 时，返回 `Memory`。
    - 当两侧都为纯标量时，返回 Python 标量或 `SymbolDim` 算术结果。
    """
    return _dispatch_binary(lhs, rhs, "__mul__", "__rmul__")

def truediv(lhs: object, rhs: object) -> ArithmeticResult:
    """逐元素除法。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 支持 Memory 与 Memory/标量的除法。
    - 当两侧都为纯标量时，复用 Python / SymbolDim 的除法结果。

    使用示例:
    - truediv(mem, 2)
    - truediv(SymbolDim("M"), 2)

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_binary.py
    返回与限制：

    - 当任一侧为 `Memory` 时，返回 `Memory`。
    - 当两侧都为纯标量时，返回 Python 标量或 `SymbolDim` 算术结果。
    """
    return _dispatch_binary(lhs, rhs, "__truediv__", "__rtruediv__")

def floordiv(lhs: object, rhs: object) -> ArithmeticResult:
    """逐元素整除。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 支持 Memory 与 Memory/标量的整除。
    - 当两侧都为纯标量时，复用 Python / SymbolDim 的整除结果。

    使用示例:
    - floordiv(mem, 2)
    - floordiv(7, SymbolDim("N"))

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/operation/test_operation_nn_elementwise.py
    - 功能实现: kernel_gen/operation/nn/elementwise_binary.py
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
        return _clone_memory_with_dtype(lhs, _resolve_scalar_dtype(lhs.dtype))
    _ensure_scalar_value(lhs)
    return _clone_memory_with_dtype(rhs, _resolve_scalar_dtype(rhs.dtype))

__all__ = [
    "add",
    "sub",
    "mul",
    "truediv",
    "floordiv",
]
