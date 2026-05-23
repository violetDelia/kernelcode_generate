"""kernel package-internal helpers.

功能说明:
- 承载 kernel package 内 MemoryEffect trait、layout/type/kind verifier 和共享 helper。

API 列表:
- 包内实现模块，无 root 公开 API。

使用示例:
- `from kernel_gen.dialect.kernel import ...`

关联文件:
- spec: spec/dialect/kernel.md
- test: test/dialect/kernel/
- 功能实现: kernel_gen/dialect/kernel/common.py
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from kernel_gen.core.contracts import (
    build_contiguous_stride as _common_build_contiguous_stride,
    verify_i64_attr_range as _common_verify_i64_attr_range,
    verify_memory_type as _common_verify_memory_type,
)
from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE
from xdsl.dialects.arith import ConstantOp
from xdsl.dialects.builtin import (
    BFloat16Type,
    Float16Type,
    Float32Type,
    Float64Type,
    IntAttr,
    IntegerAttr,
    IntegerType,
    StringAttr,
    i1,
)
from xdsl.ir import Attribute, Dialect, Operation, SSAValue
from xdsl.irdl import IRDLOperation, attr_def, irdl_op_definition, operand_def, traits_def
from xdsl.traits import EffectInstance, MemoryEffect, MemoryEffectKind
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr, SymbolValueType


_ERROR_SCENE = "dialect.kernel verifier"
_BINARY_ELEWISE_ARITH_KINDS = {"add", "sub", "mul", "div", "truediv"}
_BINARY_ELEWISE_COMPARE_KINDS = {"eq", "ne", "lt", "le", "gt", "ge"}
_BINARY_ELEWISE_KINDS = _BINARY_ELEWISE_ARITH_KINDS | _BINARY_ELEWISE_COMPARE_KINDS
_REDUCE_KINDS = {"sum", "min", "max"}


def _effect(kind: MemoryEffectKind, value: SSAValue) -> EffectInstance:
    """构造作用到具体 SSA memory value 的 MemoryEffect。


    功能说明:
    - 将 kernel 方言 outs/ins 读写语义绑定到具体 SSA value。
    - 仅供当前文件私有 trait 类复用，不作为跨文件公开 API。

    使用示例:
    - _effect(MemoryEffectKind.WRITE, out)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    return EffectInstance(kind, SSAValue.get(value))


class _KernelBinaryMemoryEffect(MemoryEffect):
    """二元 kernel op 的 out 写与 lhs/rhs 读 effect trait。"""

    @classmethod
    def get_effects(cls, op: Operation) -> set[EffectInstance]:
        """返回二元 kernel op 的 MemoryEffect 集合。


        功能说明:
        - 使用 IRDL 命名字段绑定 effect value，避免构造函数参数顺序变化导致读写误绑。
        - `out` 产生 WRITE effect，`lhs/rhs` 产生 READ effect。

        使用示例:
        - effects = _KernelBinaryMemoryEffect.get_effects(op)

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        return {
            _effect(MemoryEffectKind.WRITE, op.out),  # type: ignore[attr-defined]
            _effect(MemoryEffectKind.READ, op.lhs),  # type: ignore[attr-defined]
            _effect(MemoryEffectKind.READ, op.rhs),  # type: ignore[attr-defined]
        }


class _KernelUnaryMemoryEffect(MemoryEffect):
    """一输入一输出 kernel op 的 out 写与 input 读 effect trait。"""

    @classmethod
    def get_effects(cls, op: Operation) -> set[EffectInstance]:
        """返回一输入一输出 kernel op 的 MemoryEffect 集合。


        功能说明:
        - 使用 IRDL 命名字段绑定 effect value，避免 `KernelExpOp(input_value, out, ...)`
          等构造函数参数顺序与 op 字段顺序不一致时读写误绑。
        - `out` 产生 WRITE effect，`input` 产生 READ effect。

        使用示例:
        - effects = _KernelUnaryMemoryEffect.get_effects(op)

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        return {
            _effect(MemoryEffectKind.WRITE, op.out),  # type: ignore[attr-defined]
            _effect(MemoryEffectKind.READ, op.input),  # type: ignore[attr-defined]
        }


class _KernelSelectMemoryEffect(MemoryEffect):
    """`kernel.select` 的 out 写与 cond/lhs/rhs 读 effect trait。"""

    @classmethod
    def get_effects(cls, op: Operation) -> set[EffectInstance]:
        """返回 `kernel.select` 的 MemoryEffect 集合。


        功能说明:
        - 使用 IRDL 命名字段绑定 effect value。
        - `out` 被写入；`cond/lhs/rhs` 被读取。

        使用示例:
        - effects = _KernelSelectMemoryEffect.get_effects(op)

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        return {
            _effect(MemoryEffectKind.WRITE, op.out),  # type: ignore[attr-defined]
            _effect(MemoryEffectKind.READ, op.cond),  # type: ignore[attr-defined]
            _effect(MemoryEffectKind.READ, op.lhs),  # type: ignore[attr-defined]
            _effect(MemoryEffectKind.READ, op.rhs),  # type: ignore[attr-defined]
        }


def _is_compare_output_element_type(value: Attribute) -> bool:
    """判断 compare 输出元素类型是否可接受。


    功能说明:
    - compare 输出只接受 builtin `i1`。

    使用示例:
    - assert _is_compare_output_element_type(i1)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    return value == i1


def _normalize_kind_attr(
    kind: str | StringAttr,
    *,
    op_name: str,
    field_name: str,
    allowed: set[str],
) -> StringAttr:
    """规范化并校验 kind attribute。


    功能说明:
    - 支持 str 与 StringAttr 作为 kind 输入。
    - 校验 kind 是否属于允许集合。

    使用示例:
    - kind_attr = _normalize_kind_attr("add", op_name="kernel.binary_elewise", field_name="kind", allowed=_BINARY_ELEWISE_KINDS)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    if isinstance(kind, StringAttr):
        kind_attr = kind
    elif isinstance(kind, str):
        kind_attr = StringAttr(kind)
    else:
        raise VerifyException(
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{op_name} {field_name} must be string",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )
    if kind_attr.data not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        raise VerifyException(
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{op_name} {field_name} must be one of [{allowed_text}]",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )
    return kind_attr

def _verify_memory_type(value: Attribute, field_name: str) -> NnMemoryType:
    """校验并返回 nn.memory type。


    功能说明:
    - 确认类型为 nn.memory 并触发类型校验。

    使用示例:
    - _verify_memory_type(op.lhs.type, "lhs")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    return _common_verify_memory_type(value, field_name, scene=_ERROR_SCENE)


def _verify_same_layout(types: Iterable[NnMemoryType], op_space: NnMemorySpaceAttr) -> None:
    """校验多 operand 的 shape/stride/space 一致性。


    功能说明:
    - 要求 shape/stride/space 全部一致。
    - op space 属性必须匹配 operand space。

    使用示例:
    - _verify_same_layout([lhs_type, rhs_type, out_type], space)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    types = list(types)
    if not types:
        return
    op_space.verify()
    base = types[0]
    for other in types[1:]:
        if other.space.space.data != base.space.space.data:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel op operands must use the same space",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if other.shape != base.shape:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel op shape must match across operands",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if other.stride != base.stride:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel op stride must match across operands",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
    if base.space.space.data != op_space.space.data:
        raise VerifyException(
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected="kernel op attribute space must match operand space",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )


def _verify_element_type_match(types: Iterable[NnMemoryType], message: str) -> None:
    """校验 element_type 一致性。


    功能说明:
    - 要求所有类型的 element_type 相同。

    使用示例:
    - _verify_element_type_match([lhs_type, rhs_type, out_type], "...")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    types = list(types)
    if not types:
        return
    base_type = types[0].element_type
    for other in types[1:]:
        if other.element_type != base_type:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected=message,
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )


def _verify_matmul_shape(
    lhs_shape: Sequence[Attribute],
    rhs_shape: Sequence[Attribute],
    out_shape: Sequence[Attribute],
) -> None:
    """校验 kernel.matmul 的形状约束。


    功能说明:
    - 要求 lhs/rhs/out 皆为 rank-2。
    - 要求 `lhs=[M, K]`、`rhs=[K, N]`、`out=[M, N]` 机械一致。

    使用示例:
    - _verify_matmul_shape(lhs.shape.data, rhs.shape.data, out.shape.data)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    lhs_shape = list(lhs_shape)
    rhs_shape = list(rhs_shape)
    out_shape = list(out_shape)
    if len(lhs_shape) != 2 or len(rhs_shape) != 2 or len(out_shape) != 2:
        raise VerifyException(
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected="kernel.matmul requires rank-2 memory types",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )
    if lhs_shape[1] != rhs_shape[0]:
        raise VerifyException(
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected="kernel.matmul contracting dimensions must match",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )
    if out_shape[0] != lhs_shape[0] or out_shape[1] != rhs_shape[1]:
        raise VerifyException(
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected="kernel.matmul result shape must match lhs/rhs",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )


def _normalize_i64_attr(value: int | IntegerAttr | IntAttr, field_name: str) -> IntegerAttr:
    """将数值规整为 i64 IntegerAttr。


    功能说明:
    - 支持传入 int/IntAttr/IntegerAttr，统一为 i64 IntegerAttr。
    - 用于 axis、tile 因子等整型属性构造入口。

    使用示例:
    - _normalize_i64_attr(1, "axis")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    if isinstance(value, IntegerAttr):
        attr = value
    elif isinstance(value, IntAttr):
        attr = IntegerAttr(value.data, IntegerType(64))
    else:
        attr = IntegerAttr(int(value), IntegerType(64))
    return attr


def _verify_i64_attr_range(attr: IntegerAttr, field_name: str, *, min_value: int, max_value: int) -> int:
    """校验 i64 属性并返回整数值。


    功能说明:
    - 校验属性类型为 i64。
    - 校验数值落在指定闭区间。

    使用示例:
    - axis = _verify_i64_attr_range(attr, "axis", min_value=-2, max_value=1)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    return _common_verify_i64_attr_range(
        attr,
        field_name,
        min_value=min_value,
        max_value=max_value,
        scene=_ERROR_SCENE,
    )


def _is_symbol_int_type(attr: Attribute) -> bool:
    """判断类型是否为 symbol.int。


    功能说明:
    - 仅通过 name 字段判断是否为 symbol.int，避免 kernel/symbol 循环依赖。

    使用示例:
    - _is_symbol_int_type(SymbolValueType.from_expr("K"))

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    return isinstance(attr, SymbolValueType)


def _is_int_or_symbol_type(attr: Attribute) -> bool:
    """判断类型是否为整数或 symbol.int。


    功能说明:
    - 允许任意位宽的 IntegerType。
    - 允许 symbol.int，复用 `_is_symbol_int_type` 规避循环依赖。

    使用示例:
    - _is_int_or_symbol_type(i32)
    - _is_int_or_symbol_type(SymbolValueType.from_expr("K"))

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    return _is_symbol_int_type(attr) or isinstance(attr, IntegerType)


def _static_int_from_operand(operand: SSAValue) -> int | None:
    """尝试从 operand 提取静态整数值。


    功能说明:
    - 支持 `arith.constant`/`symbol.const` 以及单层 `builtin.unrealized_conversion_cast`。
    - block argument 没有定义 op，直接返回 None。
    - 无法解析时返回 None。

    使用示例:
    - value = _static_int_from_operand(op.k)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    owner = operand.owner
    if owner is None or not isinstance(owner, Operation):
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
            return _static_int_from_operand(owner.operands[0])
    return None


def _verify_img2col_param_operands(
    operands: Sequence[SSAValue],
    *,
    allow_zero: bool,
    type_error_phrase: str,
    value_error_phrase: str,
) -> list[int | None]:
    """校验 img2col 参数 operand 类型并提取静态值。


    功能说明:
    - 要求每个 operand 为 IntegerType 或 symbol.int。
    - 若可解析出静态整数值，则校验正数/非负数约束。
    - 解析失败则返回 None，供上层决定是否跳过形状合同校验。

    使用示例:
    - values = _verify_img2col_param_operands([op.k, op.s], allow_zero=False, type_error_phrase="kernel.img2col1d k/s must be integer or symbol", value_error_phrase="kernel.img2col1d k/s must be positive")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    values: list[int | None] = []
    for operand in operands:
        if not _is_int_or_symbol_type(operand.type):
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected=type_error_phrase,
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        static_value = _static_int_from_operand(operand)
        if static_value is not None:
            if allow_zero:
                if static_value < 0:
                    raise VerifyException(
                        ERROR_TEMPLATE.format(
                            scene=_ERROR_SCENE,
                            expected=value_error_phrase,
                            actual=ERROR_ACTUAL,
                            action=ERROR_ACTION,
                        )
                    )
            elif static_value <= 0:
                raise VerifyException(
                    ERROR_TEMPLATE.format(
                        scene=_ERROR_SCENE,
                        expected=value_error_phrase,
                        actual=ERROR_ACTUAL,
                        action=ERROR_ACTION,
                    )
                )
        values.append(static_value)
    return values


def _collect_int_dims(dims: Sequence[Attribute]) -> list[int] | None:
    """提取静态整数维度列表。


    功能说明:
    - 当所有维度均为静态 `SymbolExprAttr` 整数表达时返回整数列表。
    - 任一维度非静态整数时返回 `None`，交由后续阶段处理。

    使用示例:
    - _collect_int_dims(memory_type.shape.data)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    values: list[int] = []
    for dim in dims:
        static_value = _static_int_from_dim(dim)
        if static_value is None:
            return None
        values.append(static_value)
    return values


def _build_contiguous_stride(shape: Sequence[int]) -> list[int]:
    """根据静态 shape 构造连续布局 stride。


    功能说明:
    - 采用行主序布局，从尾轴向前累计 stride。
    - 用于 `kernel.img2col2d` 输出布局校验。

    使用示例:
    - _build_contiguous_stride([1, 3, 3, 3, 3, 3])

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    return _common_build_contiguous_stride(shape)


def _img2col_output_dim(size: int, kernel: int, stride: int, dilation: int, pad_before: int, pad_after: int) -> int:
    """根据 img2col 参数计算单轴输出尺寸。


    功能说明:
    - 计算 `floor((size + pad_before + pad_after - dilation * (kernel - 1) - 1) / stride) + 1`。
    - 由 `kernel.img2col1d/img2col2d` 的 verifier 复用。

    使用示例:
    - _img2col_output_dim(5, 3, 1, 1, 0, 0)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    return ((size + pad_before + pad_after - dilation * (kernel - 1) - 1) // stride) + 1


def _normalize_bool_attr(value: bool | int | IntegerAttr | IntAttr, field_name: str) -> IntegerAttr:
    """将布尔语义规整为 i1 IntegerAttr。


    功能说明:
    - 支持 bool/int/IntAttr/IntegerAttr 输入，统一为 i1 IntegerAttr。
    - 用于 kernel.reduce_min keepdim 等属性构造入口。

    使用示例:
    - _normalize_bool_attr(True, "keepdim")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    if isinstance(value, IntegerAttr):
        return value
    if isinstance(value, IntAttr):
        value = value.data
    if isinstance(value, bool):
        value = 1 if value else 0
    return IntegerAttr(int(value), IntegerType(1))


def _verify_bool_attr(attr: IntegerAttr, field_name: str) -> bool:
    """校验 i1 bool attr 并返回布尔值。


    功能说明:
    - 要求类型为 i1 IntegerAttr。
    - 要求取值为 0/1，接受 i1 语义下的 -1(true)。

    使用示例:
    - keepdim = _verify_bool_attr(op.keepdim, "keepdim")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    if not isinstance(attr.type, IntegerType):
        raise VerifyException(
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{field_name} must be i1",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )
    width_attr = attr.type.width
    width_value = width_attr.data if isinstance(width_attr, IntAttr) else width_attr
    if width_value != 1:
        raise VerifyException(
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{field_name} must be i1",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )
    value = attr.value.data
    if value == -1:
        return True
    if value not in (0, 1):
        raise VerifyException(
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{field_name} must be bool",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )
    return value == 1


def _dims_equal(lhs: Attribute, rhs: Attribute) -> bool:
    """判断两个维度是否语义一致。


    功能说明:
    - 对 `SymbolExprAttr` 比较 canonical 文本。
    - 其它 attribute 统一视为不一致，避免旧 bare layout 条目继续参与 verifier。

    使用示例:
    - _dims_equal(SymbolExprAttr.from_expr("1"), SymbolExprAttr.from_expr("1"))

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    if isinstance(lhs, SymbolExprAttr) and isinstance(rhs, SymbolExprAttr):
        return lhs.expr.data == rhs.expr.data
    return False


def _static_int_from_dim(dim: Attribute) -> int | None:
    """从结构化维度提取静态整数。


    功能说明:
    - 仅接受 `SymbolExprAttr` 表达的静态整数。
    - 动态符号、`?` 或非结构化属性返回 None。

    使用示例:
    - _static_int_from_dim(SymbolExprAttr.from_expr("4"))

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    if not isinstance(dim, SymbolExprAttr):
        return None
    try:
        return int(dim.expr.data)
    except ValueError:
        return None


def _build_reduce_result_shape(
    input_dims: Sequence[Attribute],
    axis: int,
    keepdim: bool,
) -> list[Attribute]:
    """构造 reduce 结果的 shape 维度列表。


    功能说明:
    - keepdim=true 时将归约轴替换为 1。
    - keepdim=false 时移除归约轴；若结果 rank 为 0 则规范为 [1]。

    使用示例:
    - _build_reduce_result_shape([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("3")], axis=0, keepdim=False)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    if keepdim:
        return [SymbolExprAttr.from_expr("1") if index == axis else dim for index, dim in enumerate(input_dims)]

    result_dims = [dim for index, dim in enumerate(input_dims) if index != axis]
    if not result_dims:
        return [SymbolExprAttr.from_expr("1")]
    return result_dims


def _verify_reduce_result_shape(
    result_type: NnMemoryType,
    expected_shape: Sequence[Attribute],
    op_name: str,
) -> None:
    """校验 reduce 结果 shape 合同。


    功能说明:
    - 比较结果 shape 与期望 shape 的长度与逐维一致性。

    使用示例:
    - _verify_reduce_result_shape(out_type, expected_shape, "kernel.reduce_min")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    if len(result_type.shape.data) != len(expected_shape):
        raise VerifyException(
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{op_name} out shape must match reduce contract",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )

    for expected_dim, actual_dim in zip(expected_shape, result_type.shape.data, strict=True):
        if not _dims_equal(expected_dim, actual_dim):
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected=f"{op_name} out shape must match reduce contract",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )


class _BaseKernelBinaryOp(IRDLOperation):
    """内部兼容用的旧二元 op 基类。"""

    out = operand_def(NnMemoryType)
    lhs = operand_def(NnMemoryType)
    rhs = operand_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        out: SSAValue | Operation,
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化二元 op。

        功能说明:
        - 按旧二元 kernel op 的 operand 顺序保存 out/lhs/rhs 与 space 属性。

        使用示例:
        - _BaseKernelBinaryOp(out, lhs, rhs, space)
        """

        super().__init__(operands=[out, lhs, rhs], attributes={"space": space})

__all__ = [
    "_effect",
    "_KernelBinaryMemoryEffect",
    "_KernelUnaryMemoryEffect",
    "_KernelSelectMemoryEffect",
    "_is_compare_output_element_type",
    "_normalize_kind_attr",
    "_verify_memory_type",
    "_verify_same_layout",
    "_verify_element_type_match",
    "_verify_matmul_shape",
    "_normalize_i64_attr",
    "_verify_i64_attr_range",
    "_is_symbol_int_type",
    "_is_int_or_symbol_type",
    "_static_int_from_operand",
    "_verify_img2col_param_operands",
    "_collect_int_dims",
    "_build_contiguous_stride",
    "_img2col_output_dim",
    "_normalize_bool_attr",
    "_verify_bool_attr",
    "_dims_equal",
    "_static_int_from_dim",
    "_build_reduce_result_shape",
    "_verify_reduce_result_shape",
    "_BaseKernelBinaryOp",
]
