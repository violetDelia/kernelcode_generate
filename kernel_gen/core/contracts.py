"""Core reusable contracts.


功能说明:
- 提供 kernel_gen 内部可复用的类型、shape、dtype 与 verifier 辅助逻辑。
- 错误模板文字统一从 `kernel_gen.core.error` 读取。
- 该模块仅承载公共实现，不改变 dialect/operation/symbol_variable 的对外合同。

API 列表:
- `raise_verify_error(scene: str, expected: str, *, actual: str = ERROR_ACTUAL, action: str = ERROR_ACTION) -> None`
- `verify_memory_type(value: Attribute, field_name: str, *, scene: str) -> NnMemoryType`
- `verify_i64_attr(attr: IntegerAttr, field_name: str, *, scene: str) -> int`
- `verify_i64_attr_range(attr: IntegerAttr, field_name: str, *, min_value: int, max_value: int, scene: str) -> int`
- `verify_i64_attr_value(attr: IntegerAttr, field_name: str, *, allow_zero: bool, scene: str) -> int`
- `verify_i64_attr_group(attrs: Sequence[IntegerAttr], *, allow_zero: bool, error_phrase: str, scene: str) -> list[int]`
- `collect_int_dims(dims: Sequence[Attribute]) -> list[int] | None`
- `build_contiguous_stride(shape: Sequence[int]) -> list[int]`
- `dims_equal(lhs: Attribute, rhs: Attribute) -> bool`
- `public_dim_values(shape: SymbolShape) -> list[int | str]`
- `default_stride(shape: SymbolShape) -> SymbolShape`
- `shape_numel(shape: SymbolShape) -> SymbolDim`

使用示例:
- from kernel_gen.core.contracts import verify_memory_type, default_stride
- memory_type = verify_memory_type(value, "lhs", scene="dialect.kernel verifier")
- stride = default_stride(SymbolShape(["M", "K", "N"]))

关联文件:
- spec: spec/core/contracts.md
- test: test/core/test_contracts.py
- 功能实现: kernel_gen/core/contracts.py
"""

from __future__ import annotations

from collections.abc import Sequence

from xdsl.dialects.builtin import IntAttr, IntegerAttr, IntegerType
from xdsl.ir import Attribute
from xdsl.utils.exceptions import VerifyException

from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE

__all__ = [
    "build_contiguous_stride",
    "collect_int_dims",
    "default_stride",
    "dims_equal",
    "public_dim_values",
    "raise_verify_error",
    "shape_numel",
    "verify_i64_attr",
    "verify_i64_attr_group",
    "verify_i64_attr_range",
    "verify_i64_attr_value",
    "verify_memory_type",
]


def _is_symbol_expr_attr(attr: Attribute) -> bool:
    """判断 attribute 是否为公开 SymbolExprAttr。

    功能说明:
    - 延迟导入公开 `SymbolExprAttr`，避免 core/contracts 与 dialect 初始化形成循环依赖。

    使用示例:
    - _is_symbol_expr_attr(dim)
    """

    from kernel_gen.dialect.symbol import SymbolExprAttr

    return isinstance(attr, SymbolExprAttr)


def raise_verify_error(
    scene: str,
    expected: str,
    *,
    actual: str = ERROR_ACTUAL,
    action: str = ERROR_ACTION,
) -> None:
    """统一抛出 verifier 错误。


    功能说明:
    - 统一 kernel_gen 内部 verifier 的错误模板拼接。
    - 调用方通过 scene / expected 保持各自领域的错误语义。

    使用示例:
    - raise_verify_error("dialect.kernel verifier", "lhs must be nn.memory")

    关联文件:
    - spec: spec/core/contracts.md
    - test: test/core/test_contracts.py
    - 功能实现: kernel_gen/core/contracts.py
    """

    raise VerifyException(
        ERROR_TEMPLATE.format(
            scene=scene,
            expected=expected,
            actual=actual,
            action=action,
        )
    )


def verify_memory_type(value: Attribute, field_name: str, *, scene: str) -> "NnMemoryType":
    """校验并返回 nn.memory type。


    功能说明:
    - 确认输入为 `NnMemoryType`。
    - 触发 `value.verify()` 保持 dialect verifier 的既有约束。

    使用示例:
    - verify_memory_type(op.lhs.type, "lhs", scene="dialect.kernel verifier")

    关联文件:
    - spec: spec/core/contracts.md
    - test: test/core/test_contracts.py
    - 功能实现: kernel_gen/core/contracts.py
    """

    from kernel_gen.dialect.nn import NnMemoryType

    if not isinstance(value, NnMemoryType):
        raise_verify_error(scene, f"{field_name} must be nn.memory")
    value.verify()
    return value


def verify_i64_attr(attr: IntegerAttr, field_name: str, *, scene: str) -> int:
    """校验 i64 属性并返回整数值。


    功能说明:
    - 校验属性类型为 i64。
    - 返回属性中的整数值，交由调用方继续施加边界约束。

    使用示例:
    - axis = verify_i64_attr(axis_attr, "axis", scene="dialect.nn verifier")

    关联文件:
    - spec: spec/core/contracts.md
    - test: test/core/test_contracts.py
    - 功能实现: kernel_gen/core/contracts.py
    """

    if not isinstance(attr.type, IntegerType):
        raise_verify_error(scene, f"{field_name} must be i64")
    width_attr = attr.type.width
    width_value = width_attr.data if isinstance(width_attr, IntAttr) else width_attr
    if width_value != 64:
        raise_verify_error(scene, f"{field_name} must be i64")
    return attr.value.data


def verify_i64_attr_range(
    attr: IntegerAttr,
    field_name: str,
    *,
    min_value: int,
    max_value: int,
    scene: str,
) -> int:
    """校验 i64 属性并限制在闭区间。


    功能说明:
    - 先要求属性为 i64。
    - 再校验数值位于指定闭区间内。

    使用示例:
    - verify_i64_attr_range(attr, "axis", min_value=-2, max_value=1, scene="dialect.kernel verifier")

    关联文件:
    - spec: spec/core/contracts.md
    - test: test/core/test_contracts.py
    - 功能实现: kernel_gen/core/contracts.py
    """

    value = verify_i64_attr(attr, field_name, scene=scene)
    if value < min_value or value > max_value:
        raise_verify_error(
            scene,
            f"{field_name} must be within [{min_value}, {max_value}]",
        )
    return value


def verify_i64_attr_value(attr: IntegerAttr, field_name: str, *, allow_zero: bool, scene: str) -> int:
    """校验 i64 属性并施加正负数约束。


    功能说明:
    - 先要求属性为 i64。
    - `allow_zero=True` 时要求非负；否则要求正数。

    使用示例:
    - verify_i64_attr_value(attr, "kw", allow_zero=False, scene="dialect.nn verifier")

    关联文件:
    - spec: spec/core/contracts.md
    - test: test/core/test_contracts.py
    - 功能实现: kernel_gen/core/contracts.py
    """

    value = verify_i64_attr(attr, field_name, scene=scene)
    if allow_zero:
        if value < 0:
            raise_verify_error(scene, f"{field_name} must be non-negative")
    elif value <= 0:
        raise_verify_error(scene, f"{field_name} must be positive")
    return value


def verify_i64_attr_group(
    attrs: Sequence[IntegerAttr],
    *,
    allow_zero: bool,
    error_phrase: str,
    scene: str,
) -> list[int]:
    """校验一组 i64 属性并返回整数列表。


    功能说明:
    - 统一校验属性类型为 i64。
    - 根据 `allow_zero` 控制非负或正数约束。
    - 任一属性不满足时抛出统一的 error phrase。

    使用示例:
    - verify_i64_attr_group([kw, sw, dw], allow_zero=False, error_phrase="kw-sw-dw must be positive", scene="dialect.nn verifier")

    关联文件:
    - spec: spec/core/contracts.md
    - test: test/core/test_contracts.py
    - 功能实现: kernel_gen/core/contracts.py
    """

    values: list[int] = []
    for attr in attrs:
        if not isinstance(attr.type, IntegerType):
            raise_verify_error(scene, error_phrase)
        width_attr = attr.type.width
        width_value = width_attr.data if isinstance(width_attr, IntAttr) else width_attr
        if width_value != 64:
            raise_verify_error(scene, error_phrase)
        value = attr.value.data
        if allow_zero:
            if value < 0:
                raise_verify_error(scene, error_phrase)
        elif value <= 0:
            raise_verify_error(scene, error_phrase)
        values.append(value)
    return values


def collect_int_dims(dims: Sequence[Attribute]) -> list[int] | None:
    """提取静态整数维度列表。


    功能说明:
    - 当所有维度均为静态整数 `SymbolExprAttr` 时返回整数列表。
    - 任一维度非静态整数时返回 `None`。

    使用示例:
    - collect_int_dims([SymbolExprAttr.from_expr("1"), SymbolExprAttr.from_expr("2")])

    关联文件:
    - spec: spec/core/contracts.md
    - test: test/core/test_contracts.py
    - 功能实现: kernel_gen/core/contracts.py
    """

    values: list[int] = []
    for dim in dims:
        if not _is_symbol_expr_attr(dim):
            return None
        expr = dim.expr.data
        if not expr.lstrip("-").isdigit():
            return None
        values.append(int(expr))
    return values


def build_contiguous_stride(shape: Sequence[int]) -> list[int]:
    """根据静态 shape 构造连续布局 stride。


    功能说明:
    - 采用行主序布局，从尾轴向前累计 stride。

    使用示例:
    - build_contiguous_stride([1, 3, 3, 3])

    关联文件:
    - spec: spec/core/contracts.md
    - test: test/core/test_contracts.py
    - 功能实现: kernel_gen/core/contracts.py
    """

    running = 1
    strides: list[int] = []
    for dim in reversed(shape):
        strides.append(running)
        running *= dim
    strides.reverse()
    return strides


def dims_equal(lhs: Attribute, rhs: Attribute) -> bool:
    """判断两个维度是否语义一致。


    功能说明:
    - 支持 `SymbolExprAttr` canonical 文本一致性判断。
    - 其他类型统一视为不一致。

    使用示例:
    - dims_equal(SymbolExprAttr.from_expr("N"), SymbolExprAttr.from_expr("N"))

    关联文件:
    - spec: spec/core/contracts.md
    - test: test/core/test_contracts.py
    - 功能实现: kernel_gen/core/contracts.py
    """

    if _is_symbol_expr_attr(lhs) and _is_symbol_expr_attr(rhs):
        return lhs.expr.data == rhs.expr.data
    return False


def public_dim_values(shape: SymbolShape) -> list[int | str]:
    """按 SymbolDim.get_value() 生成公开比较值序列。


    功能说明:
    - 静态分量返回整数，动态分量返回稳定字符串。
    - 用于 `Memory` 层的公开比较口径。

    使用示例:
    - public_dim_values(SymbolShape([SymbolDim("M"), SymbolDim("K")]))

    关联文件:
    - spec: spec/core/contracts.md
    - test: test/core/test_contracts.py
    - 功能实现: kernel_gen/core/contracts.py
    """

    values: list[int | str] = []
    for dim in shape.get_shape():
        public_value = dim.get_value()
        if isinstance(public_value, str):
            values.append(public_value)
        else:
            values.append(int(public_value))
    return values


def default_stride(shape: SymbolShape) -> SymbolShape:
    """按连续行主序生成默认 stride。


    功能说明:
    - 最后一维默认 stride 为 1。
    - 其余维度为后续维度长度的乘积。
    - 动态维度保持 `SymbolDim` 表达式语义。

    使用示例:
    - default_stride(SymbolShape(["M", "K", "N"]))

    关联文件:
    - spec: spec/core/contracts.md
    - test: test/core/test_contracts.py
    - 功能实现: kernel_gen/core/contracts.py
    """

    from kernel_gen.symbol_variable.symbol_dim import SymbolDim
    from kernel_gen.symbol_variable.symbol_shape import SymbolShape

    stride_values: list[SymbolDim] = []
    running = SymbolDim(1)
    for dim in reversed(shape.get_shape()):
        stride_values.append(running)
        running = dim * running
    stride_values.reverse()
    return SymbolShape(stride_values)


def shape_numel(shape: SymbolShape) -> SymbolDim:
    """计算 shape 的元素总数表达式。


    功能说明:
    - 静态维度返回静态乘积。
    - 动态维度返回由 `SymbolDim` 串接的表达式。

    使用示例:
    - shape_numel(SymbolShape([2, 3, 4]))

    关联文件:
    - spec: spec/core/contracts.md
    - test: test/core/test_contracts.py
    - 功能实现: kernel_gen/core/contracts.py
    """

    from kernel_gen.symbol_variable.symbol_dim import SymbolDim

    total = SymbolDim(1)
    for dim in shape.get_shape():
        total = total * dim
    return total
