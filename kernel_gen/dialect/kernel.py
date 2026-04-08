"""Kernel dialect definitions.

创建者: 小李飞刀
最后一次更改: jcc你莫辜负

功能说明:
- 定义 kernel dialect 的逐元素算术、比较、选择、指数与类型转换 op。
- 复用 nn dialect 的 NnMemoryType 与 NnMemorySpaceAttr。
- 所有结果通过 outs(...) 写回，不产生 SSA result。

使用示例:
- from kernel_gen.dialect.kernel import Kernel, KernelAddOp

关联文件:
- spec: spec/dialect/kernel.md
- test: test/dialect/test_kernel_dialect.py
- 功能实现: kernel_gen/dialect/kernel.py
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from xdsl.dialects.builtin import (
    BFloat16Type,
    Float16Type,
    Float32Type,
    Float64Type,
    IntAttr,
    IntegerAttr,
    IntegerType,
    i1,
)
from xdsl.ir import Attribute, Dialect, Operation, SSAValue
from xdsl.irdl import IRDLOperation, attr_def, irdl_op_definition, operand_def
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType

_ERROR_TEMPLATE = "场景: {scene}; 期望: {expected}; 实际: {actual}; 建议动作: {action}"
_ERROR_ACTION = "请按接口约束传参"
_ERROR_ACTUAL = "不满足期望"
_ERROR_SCENE = "dialect.kernel verifier"

def _verify_memory_type(value: Attribute, field_name: str) -> NnMemoryType:
    """校验并返回 nn.memory type。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 确认类型为 nn.memory 并触发类型校验。

    使用示例:
    - _verify_memory_type(op.lhs.type, "lhs")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    if not isinstance(value, NnMemoryType):
        raise VerifyException(
            _ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{field_name} must be nn.memory",
                actual=_ERROR_ACTUAL,
                action=_ERROR_ACTION,
            )
        )
    value.verify()
    return value


def _verify_same_layout(types: Iterable[NnMemoryType], op_space: NnMemorySpaceAttr) -> None:
    """校验多 operand 的 shape/stride/space 一致性。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 要求 shape/stride/space 全部一致。
    - op space 属性必须匹配 operand space。

    使用示例:
    - _verify_same_layout([lhs_type, rhs_type, out_type], space)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    types = list(types)
    if not types:
        return
    op_space.verify()
    base = types[0]
    for other in types[1:]:
        if other.space.space.data != base.space.space.data:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel op operands must use the same space",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
        if other.shape != base.shape:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel op shape must match across operands",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
        if other.stride != base.stride:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel op stride must match across operands",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
    if base.space.space.data != op_space.space.data:
        raise VerifyException(
            _ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected="kernel op attribute space must match operand space",
                actual=_ERROR_ACTUAL,
                action=_ERROR_ACTION,
            )
        )


def _verify_element_type_match(types: Iterable[NnMemoryType], message: str) -> None:
    """校验 element_type 一致性。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 要求所有类型的 element_type 相同。

    使用示例:
    - _verify_element_type_match([lhs_type, rhs_type, out_type], "...")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    types = list(types)
    if not types:
        return
    base_type = types[0].element_type
    for other in types[1:]:
        if other.element_type != base_type:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected=message,
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )


def _verify_matmul_shape(
    lhs_shape: Sequence[Attribute],
    rhs_shape: Sequence[Attribute],
    out_shape: Sequence[Attribute],
) -> None:
    """校验 kernel.matmul 的形状约束。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 要求 lhs/rhs/out 皆为 rank-2。
    - 要求 `lhs=[M, K]`、`rhs=[K, N]`、`out=[M, N]` 机械一致。

    使用示例:
    - _verify_matmul_shape(lhs.shape.data, rhs.shape.data, out.shape.data)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    lhs_shape = list(lhs_shape)
    rhs_shape = list(rhs_shape)
    out_shape = list(out_shape)
    if len(lhs_shape) != 2 or len(rhs_shape) != 2 or len(out_shape) != 2:
        raise VerifyException(
            _ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected="kernel.matmul requires rank-2 memory types",
                actual=_ERROR_ACTUAL,
                action=_ERROR_ACTION,
            )
        )
    if lhs_shape[1] != rhs_shape[0]:
        raise VerifyException(
            _ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected="kernel.matmul contracting dimensions must match",
                actual=_ERROR_ACTUAL,
                action=_ERROR_ACTION,
            )
        )
    if out_shape[0] != lhs_shape[0] or out_shape[1] != rhs_shape[1]:
        raise VerifyException(
            _ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected="kernel.matmul result shape must match lhs/rhs",
                actual=_ERROR_ACTUAL,
                action=_ERROR_ACTION,
            )
        )


def _is_cast_element_type(value: Attribute) -> bool:
    """判断元素类型是否允许用于 kernel.cast。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持整数与浮点类型，但不允许 i1。

    使用示例:
    - _is_cast_element_type(i1)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    if isinstance(value, IntegerType):
        return value.width.data != 1
    return isinstance(value, (Float16Type, Float32Type, Float64Type))


def _normalize_i64_attr(value: int | IntegerAttr | IntAttr, field_name: str) -> IntegerAttr:
    """将数值规整为 i64 IntegerAttr。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持传入 int/IntAttr/IntegerAttr，统一为 i64 IntegerAttr。
    - 用于 kernel.softmax axis 等属性构造入口。

    使用示例:
    - _normalize_i64_attr(1, "axis")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
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

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验属性类型为 i64。
    - 校验数值落在指定闭区间。

    使用示例:
    - axis = _verify_i64_attr_range(attr, "axis", min_value=-2, max_value=1)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    if not isinstance(attr.type, IntegerType):
        raise VerifyException(
            _ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{field_name} must be i64",
                actual=_ERROR_ACTUAL,
                action=_ERROR_ACTION,
            )
        )
    width_attr = attr.type.width
    width_value = width_attr.data if isinstance(width_attr, IntAttr) else width_attr
    if width_value != 64:
        raise VerifyException(
            _ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{field_name} must be i64",
                actual=_ERROR_ACTUAL,
                action=_ERROR_ACTION,
            )
        )
    value = attr.value.data
    if value < min_value or value > max_value:
        raise VerifyException(
            _ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{field_name} must be within [{min_value}, {max_value}]",
                actual=_ERROR_ACTUAL,
                action=_ERROR_ACTION,
            )
        )
    return value


def _verify_i64_attr_value(attr: IntegerAttr, field_name: str, *, allow_zero: bool) -> int:
    """校验 i64 属性值并返回整数。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 校验属性类型为 i64。
    - 校验正数/非负数约束并返回值。

    使用示例:
    - _verify_i64_attr_value(_normalize_i64_attr(1, "k"), "k", allow_zero=False)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    if not isinstance(attr.type, IntegerType):
        raise VerifyException(
            _ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{field_name} must be i64",
                actual=_ERROR_ACTUAL,
                action=_ERROR_ACTION,
            )
        )
    width_attr = attr.type.width
    width_value = width_attr.data if isinstance(width_attr, IntAttr) else width_attr
    if width_value != 64:
        raise VerifyException(
            _ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{field_name} must be i64",
                actual=_ERROR_ACTUAL,
                action=_ERROR_ACTION,
            )
        )
    value = attr.value.data
    if allow_zero:
        if value < 0:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected=f"{field_name} must be non-negative",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
    elif value <= 0:
        raise VerifyException(
            _ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{field_name} must be positive",
                actual=_ERROR_ACTUAL,
                action=_ERROR_ACTION,
            )
        )
    return value


def _collect_int_dims(dims: Sequence[Attribute]) -> list[int] | None:
    """提取维度中的整数值列表。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 仅当所有维度均为 IntAttr 时返回整数列表。
    - 任何非 IntAttr 维度返回 None，表示无法进行数值合同校验。

    使用示例:
    - _collect_int_dims([IntAttr(1), IntAttr(2)])

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    values: list[int] = []
    for dim in dims:
        if not isinstance(dim, IntAttr):
            return None
        values.append(dim.data)
    return values


def _build_contiguous_stride(shape: Sequence[int]) -> list[int]:
    """按连续行主序构建 stride 列表。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 以最后一维 stride=1 计算前序 stride。

    使用示例:
    - _build_contiguous_stride([1, 4, 8])

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    stride: list[int] = []
    running = 1
    for dim in reversed(shape):
        stride.append(running)
        running *= dim
    stride.reverse()
    return stride


def _img2col_output_dim(
    input_dim: int,
    kernel: int,
    stride: int,
    dilation: int,
    pad_before: int,
    pad_after: int,
) -> int:
    """计算 img2col 输出维度。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 复用卷积输出维度公式并返回整数结果。

    使用示例:
    - _img2col_output_dim(8, 3, 1, 1, 1, 1)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    numerator = input_dim + pad_before + pad_after - dilation * (kernel - 1) - 1
    return numerator // stride + 1


class _BaseKernelBinaryOp(IRDLOperation):
    """kernel 二元 op 基类。"""

    lhs = operand_def(NnMemoryType)
    rhs = operand_def(NnMemoryType)
    out = operand_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        out: SSAValue | Operation,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化二元 op。"""

        super().__init__(operands=[lhs, rhs, out], attributes={"space": space})


@irdl_op_definition
class KernelAddOp(_BaseKernelBinaryOp):
    """kernel.add。"""

    name = "kernel.add"

    def verify_(self) -> None:
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([lhs_type, rhs_type, out_type], self.space)
        _verify_element_type_match(
            [lhs_type, rhs_type, out_type],
            "kernel arithmetic element_type must match across operands",
        )


@irdl_op_definition
class KernelSubOp(_BaseKernelBinaryOp):
    """kernel.sub。"""

    name = "kernel.sub"

    def verify_(self) -> None:
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([lhs_type, rhs_type, out_type], self.space)
        _verify_element_type_match(
            [lhs_type, rhs_type, out_type],
            "kernel arithmetic element_type must match across operands",
        )


@irdl_op_definition
class KernelMulOp(_BaseKernelBinaryOp):
    """kernel.mul。"""

    name = "kernel.mul"

    def verify_(self) -> None:
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([lhs_type, rhs_type, out_type], self.space)
        _verify_element_type_match(
            [lhs_type, rhs_type, out_type],
            "kernel arithmetic element_type must match across operands",
        )


@irdl_op_definition
class KernelDivOp(_BaseKernelBinaryOp):
    """kernel.div。"""

    name = "kernel.div"

    def verify_(self) -> None:
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([lhs_type, rhs_type, out_type], self.space)
        _verify_element_type_match(
            [lhs_type, rhs_type, out_type],
            "kernel arithmetic element_type must match across operands",
        )


@irdl_op_definition
class KernelEqOp(_BaseKernelBinaryOp):
    """kernel.eq。"""

    name = "kernel.eq"

    def verify_(self) -> None:
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([lhs_type, rhs_type, out_type], self.space)
        if out_type.element_type != i1:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel compare output element_type must be i1",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )


@irdl_op_definition
class KernelNeOp(_BaseKernelBinaryOp):
    """kernel.ne。"""

    name = "kernel.ne"

    def verify_(self) -> None:
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([lhs_type, rhs_type, out_type], self.space)
        if out_type.element_type != i1:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel compare output element_type must be i1",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )


@irdl_op_definition
class KernelLtOp(_BaseKernelBinaryOp):
    """kernel.lt。"""

    name = "kernel.lt"

    def verify_(self) -> None:
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([lhs_type, rhs_type, out_type], self.space)
        if out_type.element_type != i1:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel compare output element_type must be i1",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )


@irdl_op_definition
class KernelLeOp(_BaseKernelBinaryOp):
    """kernel.le。"""

    name = "kernel.le"

    def verify_(self) -> None:
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([lhs_type, rhs_type, out_type], self.space)
        if out_type.element_type != i1:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel compare output element_type must be i1",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )


@irdl_op_definition
class KernelGtOp(_BaseKernelBinaryOp):
    """kernel.gt。"""

    name = "kernel.gt"

    def verify_(self) -> None:
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([lhs_type, rhs_type, out_type], self.space)
        if out_type.element_type != i1:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel compare output element_type must be i1",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )


@irdl_op_definition
class KernelGeOp(_BaseKernelBinaryOp):
    """kernel.ge。"""

    name = "kernel.ge"

    def verify_(self) -> None:
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([lhs_type, rhs_type, out_type], self.space)
        if out_type.element_type != i1:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel compare output element_type must be i1",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )


@irdl_op_definition
class KernelMatmulOp(_BaseKernelBinaryOp):
    """kernel.matmul。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 结构化矩阵乘 op，输入输出均为 nn.memory。
    - verifier 强制二维输入、shape 机械一致及 element_type/space 对齐。

    使用示例:
    - KernelMatmulOp(lhs, rhs, out, _make_space("global"))

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    name = "kernel.matmul"

    def verify_(self) -> None:
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        self.space.verify()
        if lhs_type.space.space.data != rhs_type.space.space.data:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.matmul operands must use the same space",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
        if lhs_type.space.space.data != self.space.space.data:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.matmul attribute space must match operand space",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
        if out_type.space.space.data != self.space.space.data:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.matmul attribute space must match result space",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
        _verify_matmul_shape(lhs_type.shape.data, rhs_type.shape.data, out_type.shape.data)
        _verify_element_type_match(
            [lhs_type, rhs_type, out_type],
            "kernel.matmul element_type must match across operands",
        )


@irdl_op_definition
class KernelImg2col1dOp(IRDLOperation):
    """kernel.img2col1d。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 定义 kernel.img2col1d op 与 verifier 约束。

    使用示例:
    - KernelImg2col1dOp(inp, out, k=3, s=1, d=1, p_left=0, p_right=0, space=_make_space("global"))

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    name = "kernel.img2col1d"

    input = operand_def(NnMemoryType)
    out = operand_def(NnMemoryType)
    k = attr_def(IntegerAttr)
    s = attr_def(IntegerAttr)
    d = attr_def(IntegerAttr)
    p_left = attr_def(IntegerAttr)
    p_right = attr_def(IntegerAttr)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        out: SSAValue | Operation,
        k: int | IntegerAttr | IntAttr,
        s: int | IntegerAttr | IntAttr,
        d: int | IntegerAttr | IntAttr,
        p_left: int | IntegerAttr | IntAttr,
        p_right: int | IntegerAttr | IntAttr,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 img2col1d op。

        创建者: jcc你莫辜负
        最后一次更改: jcc你莫辜负

        功能说明:
        - 绑定输入/输出 operand 与结构化窗口属性。

        使用示例:
        - KernelImg2col1dOp(inp, out, k=3, s=1, d=1, p_left=0, p_right=0, space=_make_space("global"))

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/test_kernel_dialect.py
        - 功能实现: kernel_gen/dialect/kernel.py
        """

        super().__init__(
            operands=[input_value, out],
            attributes={
                "k": _normalize_i64_attr(k, "k"),
                "s": _normalize_i64_attr(s, "s"),
                "d": _normalize_i64_attr(d, "d"),
                "p_left": _normalize_i64_attr(p_left, "p_left"),
                "p_right": _normalize_i64_attr(p_right, "p_right"),
                "space": space,
            },
        )

    def verify_(self) -> None:
        """校验 kernel.img2col1d 的 verifier 合同。

        创建者: jcc你莫辜负
        最后一次更改: jcc你莫辜负

        功能说明:
        - 校验输入/输出 rank、属性合法性与结构化输出合同。

        使用示例:
        - KernelImg2col1dOp(inp, out, k=3, s=1, d=1, p_left=0, p_right=0, space=_make_space("global")).verify_()

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/test_kernel_dialect.py
        - 功能实现: kernel_gen/dialect/kernel.py
        """

        input_type = _verify_memory_type(self.input.type, "input")
        out_type = _verify_memory_type(self.out.type, "out")
        self.space.verify()
        if input_type.space.space.data != out_type.space.space.data:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col1d operands must use the same space",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
        if input_type.space.space.data != self.space.space.data:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col1d attribute space must match operand space",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
        if out_type.space.space.data != self.space.space.data:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col1d attribute space must match result space",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
        if len(input_type.shape.data) != 3:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col1d requires rank-3 input",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
        if len(out_type.shape.data) != 4:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col1d requires rank-4 output",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
        if input_type.element_type != out_type.element_type:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col1d element_type must match across operands",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )

        k_value = _verify_i64_attr_value(self.k, "kernel.img2col1d k", allow_zero=False)
        s_value = _verify_i64_attr_value(self.s, "kernel.img2col1d s", allow_zero=False)
        d_value = _verify_i64_attr_value(self.d, "kernel.img2col1d d", allow_zero=False)
        p_left_value = _verify_i64_attr_value(
            self.p_left, "kernel.img2col1d p_left", allow_zero=True
        )
        p_right_value = _verify_i64_attr_value(
            self.p_right, "kernel.img2col1d p_right", allow_zero=True
        )

        input_dims = _collect_int_dims(input_type.shape.data)
        out_dims = _collect_int_dims(out_type.shape.data)
        if input_dims is None or out_dims is None:
            return

        n_dim, c_dim, w_dim = input_dims
        w_out = _img2col_output_dim(w_dim, k_value, s_value, d_value, p_left_value, p_right_value)
        if w_out <= 0:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col1d output width must be positive",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )

        expected_shape = [n_dim, c_dim, k_value, w_out]
        if out_dims != expected_shape:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col1d output shape must match input and attrs",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )

        out_strides = _collect_int_dims(out_type.stride.data)
        if out_strides is None:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col1d output stride must be contiguous",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
        expected_stride = _build_contiguous_stride(expected_shape)
        if out_strides != expected_stride:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col1d output stride must be contiguous",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )


@irdl_op_definition
class KernelSelectOp(IRDLOperation):
    """kernel.select。"""

    name = "kernel.select"

    cond = operand_def(NnMemoryType)
    lhs = operand_def(NnMemoryType)
    rhs = operand_def(NnMemoryType)
    out = operand_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        cond: SSAValue | Operation,
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        out: SSAValue | Operation,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 select op。"""

        super().__init__(operands=[cond, lhs, rhs, out], attributes={"space": space})

    def verify_(self) -> None:
        cond_type = _verify_memory_type(self.cond.type, "cond")
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        out_type = _verify_memory_type(self.out.type, "out")
        if cond_type.element_type != i1:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.select cond element_type must be i1",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
        _verify_same_layout([cond_type, lhs_type, rhs_type, out_type], self.space)
        _verify_element_type_match(
            [lhs_type, rhs_type, out_type],
            "kernel.select operand element_type must match",
        )


@irdl_op_definition
class KernelCastOp(IRDLOperation):
    """kernel.cast。"""

    name = "kernel.cast"

    input = operand_def(NnMemoryType)
    out = operand_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        out: SSAValue | Operation,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 cast op。"""

        super().__init__(operands=[input_value, out], attributes={"space": space})

    def verify_(self) -> None:
        input_type = _verify_memory_type(self.input.type, "input")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([input_type, out_type], self.space)
        if not _is_cast_element_type(input_type.element_type) or not _is_cast_element_type(
            out_type.element_type
        ):
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.cast element_type must be integer or float and not i1",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )


@irdl_op_definition
class KernelExpOp(IRDLOperation):
    """kernel.exp。"""

    name = "kernel.exp"

    input = operand_def(NnMemoryType)
    out = operand_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        out: SSAValue | Operation,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 exp op。"""

        super().__init__(operands=[input_value, out], attributes={"space": space})

    def verify_(self) -> None:
        input_type = _verify_memory_type(self.input.type, "input")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([input_type, out_type], self.space)
        _verify_element_type_match(
            [input_type, out_type],
            "kernel.exp element_type must match across operands",
        )
        if not isinstance(input_type.element_type, (BFloat16Type, Float16Type, Float32Type, Float64Type)):
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.exp element_type must be float",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )


@irdl_op_definition
class KernelSoftmaxOp(IRDLOperation):
    """kernel.softmax。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 定义 kernel.softmax op 与 verifier 约束。

    使用示例:
    - KernelSoftmaxOp(inp, out, axis=1, space=NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    name = "kernel.softmax"

    input = operand_def(NnMemoryType)
    out = operand_def(NnMemoryType)
    axis = attr_def(IntegerAttr)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        out: SSAValue | Operation,
        axis: int | IntegerAttr | IntAttr,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 softmax op。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 绑定输入/输出 operand。
        - axis 规整为 i64 IntegerAttr 以便 verifier 校验。

        使用示例:
        - KernelSoftmaxOp(inp, out, axis=1, space=NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/test_kernel_dialect.py
        - 功能实现: kernel_gen/dialect/kernel.py
        """

        axis_attr = _normalize_i64_attr(axis, "axis")
        super().__init__(operands=[input_value, out], attributes={"axis": axis_attr, "space": space})

    def verify_(self) -> None:
        """校验 kernel.softmax 的 verifier 合同。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 校验 layout/element_type/axis 约束。

        使用示例:
        - KernelSoftmaxOp(inp, out, axis=1, space=NnMemorySpaceAttr.from_name("global")).verify_()

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/test_kernel_dialect.py
        - 功能实现: kernel_gen/dialect/kernel.py
        """

        input_type = _verify_memory_type(self.input.type, "input")
        out_type = _verify_memory_type(self.out.type, "out")
        _verify_same_layout([input_type, out_type], self.space)
        _verify_element_type_match(
            [input_type, out_type],
            "kernel.softmax element_type must match across operands",
        )
        if not isinstance(input_type.element_type, (BFloat16Type, Float16Type, Float32Type, Float64Type)):
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.softmax element_type must be float",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
        axis_attr = _normalize_i64_attr(self.axis, "axis")
        rank = len(input_type.shape.data)
        _verify_i64_attr_range(axis_attr, "axis", min_value=-rank, max_value=rank - 1)


Kernel = Dialect(
    "kernel",
    [
        KernelAddOp,
        KernelSubOp,
        KernelMulOp,
        KernelDivOp,
        KernelEqOp,
        KernelNeOp,
        KernelLtOp,
        KernelLeOp,
        KernelGtOp,
        KernelGeOp,
        KernelMatmulOp,
        KernelImg2col1dOp,
        KernelSelectOp,
        KernelCastOp,
        KernelExpOp,
        KernelSoftmaxOp,
    ],
    [],
)

__all__ = [
    "Kernel",
    "KernelAddOp",
    "KernelSubOp",
    "KernelMulOp",
    "KernelDivOp",
    "KernelEqOp",
    "KernelNeOp",
    "KernelLtOp",
    "KernelLeOp",
    "KernelGtOp",
    "KernelGeOp",
    "KernelMatmulOp",
    "KernelImg2col1dOp",
    "KernelSelectOp",
    "KernelCastOp",
    "KernelExpOp",
    "KernelSoftmaxOp",
]
