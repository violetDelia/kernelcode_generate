"""Kernel dialect definitions.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 定义 kernel dialect 的逐元素算术、比较、选择、指数、归约与类型转换 op。
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
    StringAttr,
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


def _collect_int_dims(dims: Sequence[Attribute]) -> list[int] | None:
    """提取静态整数维度列表。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 当所有维度均为 `IntAttr` 时返回整数列表。
    - 任一维度非静态整数时返回 `None`，交由后续阶段处理。

    使用示例:
    - _collect_int_dims(memory_type.shape.data)

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
    """根据静态 shape 构造连续布局 stride。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 采用行主序布局，从尾轴向前累计 stride。
    - 用于 `kernel.img2col2d` 输出布局校验。

    使用示例:
    - _build_contiguous_stride([1, 3, 3, 3, 3, 3])

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    running = 1
    strides: list[int] = []
    for dim in reversed(shape):
        strides.append(running)
        running *= dim
    strides.reverse()
    return strides


def _img2col_output_dim(size: int, kernel: int, stride: int, dilation: int, pad_before: int, pad_after: int) -> int:
    """根据 img2col 参数计算单轴输出尺寸。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 计算 `floor((size + pad_before + pad_after - dilation * (kernel - 1) - 1) / stride) + 1`。
    - 由 `kernel.img2col2d` 的 verifier 复用。

    使用示例:
    - _img2col_output_dim(5, 3, 1, 1, 0, 0)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    return ((size + pad_before + pad_after - dilation * (kernel - 1) - 1) // stride) + 1


def _normalize_bool_attr(value: bool | int | IntegerAttr | IntAttr, field_name: str) -> IntegerAttr:
    """将布尔语义规整为 i1 IntegerAttr。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 bool/int/IntAttr/IntegerAttr 输入，统一为 i1 IntegerAttr。
    - 用于 kernel.reduce_min keepdim 等属性构造入口。

    使用示例:
    - _normalize_bool_attr(True, "keepdim")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
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

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 要求类型为 i1 IntegerAttr。
    - 要求取值为 0/1，接受 i1 语义下的 -1(true)。

    使用示例:
    - keepdim = _verify_bool_attr(op.keepdim, "keepdim")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    if not isinstance(attr.type, IntegerType):
        raise VerifyException(
            _ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{field_name} must be i1",
                actual=_ERROR_ACTUAL,
                action=_ERROR_ACTION,
            )
        )
    width_attr = attr.type.width
    width_value = width_attr.data if isinstance(width_attr, IntAttr) else width_attr
    if width_value != 1:
        raise VerifyException(
            _ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{field_name} must be i1",
                actual=_ERROR_ACTUAL,
                action=_ERROR_ACTION,
            )
        )
    value = attr.value.data
    if value == -1:
        return True
    if value not in (0, 1):
        raise VerifyException(
            _ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{field_name} must be bool",
                actual=_ERROR_ACTUAL,
                action=_ERROR_ACTION,
            )
        )
    return value == 1


def _dims_equal(lhs: Attribute, rhs: Attribute) -> bool:
    """判断两个维度是否语义一致。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅在同类型且内容相等时认为一致。

    使用示例:
    - _dims_equal(IntAttr(1), IntAttr(1))

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    if isinstance(lhs, IntAttr) and isinstance(rhs, IntAttr):
        return lhs.data == rhs.data
    if isinstance(lhs, StringAttr) and isinstance(rhs, StringAttr):
        return lhs.data == rhs.data
    return False


def _build_reduce_result_shape(
    input_dims: Sequence[Attribute],
    axis: int,
    keepdim: bool,
) -> list[Attribute]:
    """构造 reduce 结果的 shape 维度列表。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - keepdim=true 时将归约轴替换为 1。
    - keepdim=false 时移除归约轴；若结果 rank 为 0 则规范为 [1]。

    使用示例:
    - _build_reduce_result_shape([IntAttr(2), IntAttr(3)], axis=0, keepdim=False)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    if keepdim:
        return [IntAttr(1) if index == axis else dim for index, dim in enumerate(input_dims)]

    result_dims = [dim for index, dim in enumerate(input_dims) if index != axis]
    if not result_dims:
        return [IntAttr(1)]
    return result_dims


def _verify_reduce_result_shape(
    result_type: NnMemoryType,
    expected_shape: Sequence[Attribute],
    op_name: str,
) -> None:
    """校验 reduce 结果 shape 合同。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 比较结果 shape 与期望 shape 的长度与逐维一致性。

    使用示例:
    - _verify_reduce_result_shape(out_type, expected_shape, "kernel.reduce_min")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    if len(result_type.shape.data) != len(expected_shape):
        raise VerifyException(
            _ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=f"{op_name} out shape must match reduce contract",
                actual=_ERROR_ACTUAL,
                action=_ERROR_ACTION,
            )
        )

    for expected_dim, actual_dim in zip(expected_shape, result_type.shape.data, strict=True):
        if not _dims_equal(expected_dim, actual_dim):
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected=f"{op_name} out shape must match reduce contract",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )


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
class KernelImg2col2dOp(IRDLOperation):
    """kernel.img2col2d。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 定义二维 img2col 的 kernel 目标 op。
    - verifier 校验输入输出 rank、窗口属性、结构化结果 shape/stride 与空间一致性。

    使用示例:
    - KernelImg2col2dOp(inp, out, kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0, space=_make_space("global"))

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    name = "kernel.img2col2d"

    input = operand_def(NnMemoryType)
    out = operand_def(NnMemoryType)
    kh = attr_def(IntegerAttr)
    kw = attr_def(IntegerAttr)
    sh = attr_def(IntegerAttr)
    sw = attr_def(IntegerAttr)
    dh = attr_def(IntegerAttr)
    dw = attr_def(IntegerAttr)
    ph = attr_def(IntegerAttr)
    pw = attr_def(IntegerAttr)
    pl = attr_def(IntegerAttr)
    pr = attr_def(IntegerAttr)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        out: SSAValue | Operation,
        kh: int | IntegerAttr | IntAttr,
        kw: int | IntegerAttr | IntAttr,
        sh: int | IntegerAttr | IntAttr,
        sw: int | IntegerAttr | IntAttr,
        dh: int | IntegerAttr | IntAttr,
        dw: int | IntegerAttr | IntAttr,
        ph: int | IntegerAttr | IntAttr,
        pw: int | IntegerAttr | IntAttr,
        pl: int | IntegerAttr | IntAttr,
        pr: int | IntegerAttr | IntAttr,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 img2col2d op。

        创建者: 朽木露琪亚
        最后一次更改: 朽木露琪亚

        功能说明:
        - 绑定输入/输出 operand。
        - 统一规整窗口参数为 i64 IntegerAttr。

        使用示例:
        - KernelImg2col2dOp(inp, out, 3, 3, 1, 1, 1, 1, 0, 0, 0, 0, _make_space("global"))

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/test_kernel_dialect.py
        - 功能实现: kernel_gen/dialect/kernel.py
        """

        super().__init__(
            operands=[input_value, out],
            attributes={
                "kh": _normalize_i64_attr(kh, "kh"),
                "kw": _normalize_i64_attr(kw, "kw"),
                "sh": _normalize_i64_attr(sh, "sh"),
                "sw": _normalize_i64_attr(sw, "sw"),
                "dh": _normalize_i64_attr(dh, "dh"),
                "dw": _normalize_i64_attr(dw, "dw"),
                "ph": _normalize_i64_attr(ph, "ph"),
                "pw": _normalize_i64_attr(pw, "pw"),
                "pl": _normalize_i64_attr(pl, "pl"),
                "pr": _normalize_i64_attr(pr, "pr"),
                "space": space,
            },
        )

    def verify_(self) -> None:
        """校验 kernel.img2col2d 合同。

        创建者: 朽木露琪亚
        最后一次更改: 朽木露琪亚

        功能说明:
        - 校验输入输出 rank、元素类型、空间、窗口参数与结构化结果布局。

        使用示例:
        - KernelImg2col2dOp(...).verify_()

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/test_kernel_dialect.py
        - 功能实现: kernel_gen/dialect/kernel.py
        """

        input_type = _verify_memory_type(self.input.type, "input")
        out_type = _verify_memory_type(self.out.type, "out")
        self.space.verify()

        if len(input_type.shape.data) != 4:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col2d requires rank-4 input",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
        if len(out_type.shape.data) != 6:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col2d requires rank-6 result",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
        if input_type.space.space.data != self.space.space.data:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col2d attribute space must match input space",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
        if out_type.space.space.data != self.space.space.data:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col2d attribute space must match result space",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
        if out_type.element_type != input_type.element_type:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col2d result element_type must match input",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )

        kh_value = _verify_i64_attr_range(self.kh, "kh", min_value=1, max_value=2**63 - 1)
        kw_value = _verify_i64_attr_range(self.kw, "kw", min_value=1, max_value=2**63 - 1)
        sh_value = _verify_i64_attr_range(self.sh, "sh", min_value=1, max_value=2**63 - 1)
        sw_value = _verify_i64_attr_range(self.sw, "sw", min_value=1, max_value=2**63 - 1)
        dh_value = _verify_i64_attr_range(self.dh, "dh", min_value=1, max_value=2**63 - 1)
        dw_value = _verify_i64_attr_range(self.dw, "dw", min_value=1, max_value=2**63 - 1)
        ph_value = _verify_i64_attr_range(self.ph, "ph", min_value=0, max_value=2**63 - 1)
        pw_value = _verify_i64_attr_range(self.pw, "pw", min_value=0, max_value=2**63 - 1)
        pl_value = _verify_i64_attr_range(self.pl, "pl", min_value=0, max_value=2**63 - 1)
        pr_value = _verify_i64_attr_range(self.pr, "pr", min_value=0, max_value=2**63 - 1)

        input_shape = list(input_type.shape.data)
        out_shape = list(out_type.shape.data)
        if not isinstance(out_shape[2], IntAttr) or out_shape[2].data != kh_value:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col2d result shape/stride must match img2col2d contract",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
        if not isinstance(out_shape[3], IntAttr) or out_shape[3].data != kw_value:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col2d result shape/stride must match img2col2d contract",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )

        input_dims = _collect_int_dims(input_shape)
        input_strides = _collect_int_dims(input_type.stride.data)
        if input_dims is not None and input_strides is not None:
            if input_strides != _build_contiguous_stride(input_dims):
                raise VerifyException(
                    _ERROR_TEMPLATE.format(
                        scene=_ERROR_SCENE,
                        expected="kernel.img2col2d input layout must be contiguous",
                        actual=_ERROR_ACTUAL,
                        action=_ERROR_ACTION,
                    )
                )

        out_dims = _collect_int_dims(out_shape)
        out_strides = _collect_int_dims(out_type.stride.data)
        if input_dims is None or out_dims is None or out_strides is None:
            return

        n_dim, c_dim, h_dim, w_dim = input_dims
        oh_dim = _img2col_output_dim(h_dim, kh_value, sh_value, dh_value, ph_value, pw_value)
        ow_dim = _img2col_output_dim(w_dim, kw_value, sw_value, dw_value, pl_value, pr_value)
        expected_shape = [n_dim, c_dim, kh_value, kw_value, oh_dim, ow_dim]
        expected_stride = _build_contiguous_stride(expected_shape)
        if oh_dim < 1 or ow_dim < 1 or out_dims != expected_shape or out_strides != expected_stride:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col2d result shape/stride must match img2col2d contract",
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


@irdl_op_definition
class KernelReduceMinOp(IRDLOperation):
    """kernel.reduce_min。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 定义 kernel.reduce_min op 与 verifier 约束。

    使用示例:
    - KernelReduceMinOp(inp, out, axis=1, keepdim=False, space=NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    name = "kernel.reduce_min"

    input = operand_def(NnMemoryType)
    out = operand_def(NnMemoryType)
    axis = attr_def(IntegerAttr)
    keepdim = attr_def(IntegerAttr)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        out: SSAValue | Operation,
        axis: int | IntegerAttr | IntAttr,
        keepdim: bool | int | IntegerAttr | IntAttr,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 reduce_min op。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 绑定输入/输出 operand。
        - axis 规整为 i64 IntegerAttr，keepdim 规整为 i1。

        使用示例:
        - KernelReduceMinOp(inp, out, axis=1, keepdim=False, space=NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/test_kernel_dialect.py
        - 功能实现: kernel_gen/dialect/kernel.py
        """

        axis_attr = _normalize_i64_attr(axis, "axis")
        keepdim_attr = _normalize_bool_attr(keepdim, "keepdim")
        super().__init__(
            operands=[input_value, out],
            attributes={"axis": axis_attr, "keepdim": keepdim_attr, "space": space},
        )

    def verify_(self) -> None:
        """校验 kernel.reduce_min 的 verifier 合同。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 校验 axis/keepdim/out.shape 约束。
        - 校验 element_type 与 space 一致性。

        使用示例:
        - KernelReduceMinOp(inp, out, axis=1, keepdim=False, space=NnMemorySpaceAttr.from_name("global")).verify_()

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/test_kernel_dialect.py
        - 功能实现: kernel_gen/dialect/kernel.py
        """

        input_type = _verify_memory_type(self.input.type, "input")
        out_type = _verify_memory_type(self.out.type, "out")
        axis_value = _verify_i64_attr_range(
            self.axis, "axis", min_value=0, max_value=len(input_type.shape.data) - 1
        )
        keepdim_value = _verify_bool_attr(self.keepdim, "keepdim")
        if input_type.element_type != out_type.element_type:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.reduce_min element_type must match across operands",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
        self.space.verify()
        if input_type.space.space.data != out_type.space.space.data:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.reduce_min out space must match input",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
        if input_type.space.space.data != self.space.space.data:
            raise VerifyException(
                _ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.reduce_min attribute space must match input",
                    actual=_ERROR_ACTUAL,
                    action=_ERROR_ACTION,
                )
            )
        expected_shape = _build_reduce_result_shape(
            list(input_type.shape.data), axis_value, keepdim_value
        )
        _verify_reduce_result_shape(out_type, expected_shape, "kernel.reduce_min")


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
        KernelImg2col2dOp,
        KernelSelectOp,
        KernelCastOp,
        KernelExpOp,
        KernelSoftmaxOp,
        KernelReduceMinOp,
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
    "KernelImg2col2dOp",
    "KernelSelectOp",
    "KernelCastOp",
    "KernelExpOp",
    "KernelSoftmaxOp",
    "KernelReduceMinOp",
]
