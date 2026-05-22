"""nn dialect package internal common helpers.

功能说明:
- 承载 nn dialect package 拆分后的 nn dialect package internal common helpers 实现。

API 列表:
- `raise_verify_error(expected: str, *, actual: str = ERROR_ACTUAL) -> None`
- `verify_memory_type(value: Attribute, field_name: str) -> NnMemoryType`
- `is_symbol_int_type(attr: Attribute) -> bool`
- `is_int_or_symbol_type(attr: Attribute) -> bool`
- `static_int_from_operand(operand: SSAValue) -> int | None`
- `verify_i64_attr(attr: IntegerAttr, field_name: str) -> int`
- `normalize_i64_attr(value: int | IntegerAttr | IntAttr, field_name: str) -> IntegerAttr`
- `normalize_axes_attr(axes: Sequence[int] | ArrayAttr) -> ArrayAttr`
- `normalize_bool_attr(value: bool | int | IntegerAttr | IntAttr, field_name: str) -> IntegerAttr`
- `is_float_element_type(attr: Attribute) -> bool`
- `dims_equal(lhs: Attribute, rhs: Attribute) -> bool`
- `build_contiguous_stride(shape: Sequence[int]) -> list[int]`

使用示例:
- from kernel_gen.dialect.nn.common import verify_memory_type

关联文件:
- spec: spec/dialect/nn.md
- test: test/dialect/nn/
- 功能实现: kernel_gen/dialect/nn/common.py
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from kernel_gen.core.contracts import (
    build_contiguous_stride as _common_build_contiguous_stride,
    verify_i64_attr as _common_verify_i64_attr,
    verify_memory_type as _common_verify_memory_type,
)
from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE
from xdsl.dialects.arith import ConstantOp
from xdsl.dialects.builtin import (
    ArrayAttr,
    BFloat16Type,
    Float16Type,
    Float32Type,
    Float64Type,
    IntAttr,
    IntegerAttr,
    IntegerType,
)
from xdsl.ir import Attribute, ParametrizedAttribute, SSAValue
from xdsl.utils.exceptions import VerifyException

if TYPE_CHECKING:
    from kernel_gen.dialect.nn.type.memory_type import NnMemoryType

_ERROR_SCENE = "dialect.nn verifier"

def _is_symbol_expr_attr(attr: Attribute) -> bool:
    """判断属性是否是公开 SymbolExprAttr。

    功能说明:
    - 通过延迟导入的公开 class 判断 memory shape/stride 条目。

    使用示例:
    - _is_symbol_expr_attr(SymbolExprAttr.from_expr("N"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    from kernel_gen.dialect.symbol import SymbolExprAttr

    return isinstance(attr, SymbolExprAttr)

def _dim_expr_text(dim: Attribute) -> str:
    """读取 SymbolExprAttr 的规范表达式文本。

    功能说明:
    - 统一 shape/stride 的比较、静态求值和 stride 推导入口。

    使用示例:
    - _dim_expr_text(SymbolExprAttr.from_expr("N + 1"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    if not _is_symbol_expr_attr(dim):
        raise_verify_error("dimension entries must be SymbolExprAttr")
    dim.verify()
    return dim.expr.data

def raise_verify_error(expected: str, *, actual: str = ERROR_ACTUAL) -> None:
    """统一抛出 nn dialect verifier 错误。

    功能说明:
    - 按 nn dialect 稳定错误模板组装 verifier 失败信息。
    - 供 nn package 内部 attr/type/op verifier 复用同一错误场景。

    使用示例:
    - raise_verify_error("operand-must-be-nn-memory")
    """

    raise VerifyException(
        ERROR_TEMPLATE.format(
            scene=_ERROR_SCENE,
            expected=expected,
            actual=actual,
            action=ERROR_ACTION,
        )
    )

def verify_memory_type(value: Attribute, field_name: str) -> "NnMemoryType":
    """校验并返回 memory type。

    功能说明:
    - 确认 `value` 是公开 `NnMemoryType`，并执行通用 memory type 校验。
    - `field_name` 用于在稳定错误文本中定位被校验字段。

    使用示例:
    - input_type = verify_memory_type(op.input.type, "input")
    """

    return _common_verify_memory_type(value, field_name, scene=_ERROR_SCENE)

def is_symbol_int_type(attr: Attribute) -> bool:
    """判断 attribute 是否为 symbol.int。


    功能说明:
    - 仅通过 `name` 字段判断是否为 `symbol.int` 类型，避免 nn/symbol 循环依赖。

    使用示例:
    - is_symbol_int_type(SymbolValueType.from_expr("K"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    return isinstance(attr, ParametrizedAttribute) and attr.name == "symbol.int"

def is_int_or_symbol_type(attr: Attribute) -> bool:
    """判断类型是否为整数或 symbol.int。


    功能说明:
    - 允许任意位宽的 IntegerType。
    - 允许 symbol.int，复用 `is_symbol_int_type` 规避循环依赖。

    使用示例:
    - is_int_or_symbol_type(i32)
    - is_int_or_symbol_type(SymbolValueType.from_expr("K"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    return is_symbol_int_type(attr) or isinstance(attr, IntegerType)

def static_int_from_operand(operand: SSAValue) -> int | None:
    """尝试从 operand 提取静态整数值。


    功能说明:
    - 支持 `arith.constant`/`symbol.const` 以及单层 `builtin.unrealized_conversion_cast`。
    - 无法解析时返回 None，交由上层决定是否跳过数值合同校验。

    使用示例:
    - value = static_int_from_operand(op.kw)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    owner = operand.owner
    if owner is None:
        return None
    owner_name = owner.name
    if owner_name == "arith.constant":
        value_attr = owner.value if isinstance(owner, ConstantOp) else owner.attributes.get("value")
        if isinstance(value_attr, IntegerAttr):
            return int(value_attr.value.data)
        if isinstance(value_attr, IntAttr):
            return int(value_attr.data)
        return None
    if owner_name == "symbol.const":
        value_attr = owner.attributes.get("value")
        if isinstance(value_attr, IntAttr):
            return int(value_attr.data)
        return None
    if owner_name == "builtin.unrealized_conversion_cast":
        if owner.operands:
            return static_int_from_operand(owner.operands[0])
    return None

def verify_i64_attr(attr: IntegerAttr, field_name: str) -> int:
    """校验 i64 属性并返回整数值。


    功能说明:
    - 校验属性类型为 i64，但不限制符号正负。
    - 用于需要允许负值的 axis 等字段。

    使用示例:
    - axis_value = verify_i64_attr(axis_attr, "axis")

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    return _common_verify_i64_attr(attr, field_name, scene=_ERROR_SCENE)

def normalize_i64_attr(value: int | IntegerAttr | IntAttr, field_name: str) -> IntegerAttr:
    """将数值规范化为 i64 IntegerAttr。


    功能说明:
    - 支持传入 int/IntAttr/IntegerAttr，统一为 i64 IntegerAttr。
    - 用于 nn.img2col1d/nn.img2col2d 属性构造入口。

    使用示例:
    - normalize_i64_attr(3, "kw")

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    if isinstance(value, IntegerAttr):
        return value
    if isinstance(value, IntAttr):
        value = value.data
    return IntegerAttr(value, IntegerType(64))

def normalize_axes_attr(axes: Sequence[int] | ArrayAttr) -> ArrayAttr:
    """将归约 axes 规范化为 i64 ArrayAttr。


    功能说明:
    - 支持传入轴序列或 ArrayAttr。
    - 统一输出元素为 i64 IntegerAttr 的 ArrayAttr。

    使用示例:
    - normalize_axes_attr([0, 2])

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    if isinstance(axes, ArrayAttr):
        return axes
    return ArrayAttr([IntegerAttr(int(axis), IntegerType(64)) for axis in axes])

def normalize_bool_attr(value: bool | int | IntegerAttr | IntAttr, field_name: str) -> IntegerAttr:
    """将布尔语义规范化为 i1 IntegerAttr。


    功能说明:
    - 支持 bool/int/IntAttr/IntegerAttr 输入，统一为 i1 IntegerAttr。
    - 具体合法性由 verifier 进一步校验。

    使用示例:
    - normalize_bool_attr(True, "keepdim")

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    if isinstance(value, IntegerAttr):
        return value
    if isinstance(value, IntAttr):
        value = value.data
    if isinstance(value, bool):
        value = 1 if value else 0
    if not isinstance(value, int):
        raise TypeError(
            ERROR_TEMPLATE.format(
                scene="dialect.nn 参数校验",
                expected=f"{field_name} must be bool/int or i1 attr",
                actual=type(value).__name__,
                action=ERROR_ACTION,
            )
        )
    return IntegerAttr(int(value), IntegerType(1))

def is_float_element_type(attr: Attribute) -> bool:
    """判断 element_type 是否为浮点类型。


    功能说明:
    - 允许 f16/bf16/f32/f64 四类浮点类型。

    使用示例:
    - is_float_element_type(Float32Type())

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    return isinstance(attr, (Float16Type, BFloat16Type, Float32Type, Float64Type))

def dims_equal(lhs: Attribute, rhs: Attribute) -> bool:
    """判断两个维度是否语义一致。


    功能说明:
    - SymbolExprAttr 按 canonical 表达式文本比较。

    使用示例:
    - dims_equal(SymbolExprAttr.from_expr("N + 1"), SymbolExprAttr.from_expr("1 + N"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """
    if _is_symbol_expr_attr(lhs) and _is_symbol_expr_attr(rhs):
        return _dim_expr_text(lhs) == _dim_expr_text(rhs)
    return False

def build_contiguous_stride(shape: Sequence[int]) -> list[int]:
    """按连续行主序构建 stride 列表。


    功能说明:
    - 以最后一维 stride=1 计算前序 stride。

    使用示例:
    - build_contiguous_stride([1, 4, 8])

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    return _common_build_contiguous_stride(shape)

__all__ = [
    "raise_verify_error",
    "verify_memory_type",
    "is_symbol_int_type",
    "is_int_or_symbol_type",
    "static_int_from_operand",
    "verify_i64_attr",
    "normalize_i64_attr",
    "normalize_axes_attr",
    "normalize_bool_attr",
    "is_float_element_type",
    "dims_equal",
    "build_contiguous_stride",
]
