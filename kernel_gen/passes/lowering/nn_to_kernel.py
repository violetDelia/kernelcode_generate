"""nn -> kernel lowering pass.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 将 nn dialect 的逐元素 op lower 为 kernel dialect op。
- 当结果无法复用已有输出时，为结果插入 dma.alloc。
- `nn.softmax` lower 为 `kernel.softmax` 并保留 `axis`。

使用示例:
- from kernel_gen.passes.lowering.nn_to_kernel import LowerNnToKernelPass
- module = LowerNnToKernelPass().run(module)

关联文件:
- spec: spec/pass/lowering/nn_to_kernel.md
- test: test/pass/test_lowering_nn_to_kernel.py
- 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
"""

from __future__ import annotations

from collections.abc import Iterable

from xdsl.dialects import arith, func
from xdsl.dialects.builtin import (
    ArrayAttr,
    IntAttr,
    IntegerAttr,
    IntegerType,
    ModuleOp,
    StringAttr,
    UnrealizedConversionCastOp,
    i32,
)
from xdsl.ir import Block, Operation, Region, SSAValue
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp, DmaCopyOp, DmaFillOp, DmaTransposeOp
from kernel_gen.dialect.kernel import (
    KernelAddOp,
    KernelCastOp,
    KernelDivOp,
    KernelEqOp,
    KernelExpOp,
    KernelGeOp,
    KernelGtOp,
    KernelImg2col1dOp,
    KernelImg2col2dOp,
    KernelLeOp,
    KernelLtOp,
    KernelMatmulOp,
    KernelMulOp,
    KernelNeOp,
    KernelReduceMinOp,
    KernelSelectOp,
    KernelSoftmaxOp,
    KernelSubOp,
)
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolGetDimOp, SymbolValueType
from ..pass_manager import Pass


class LowerNnToKernelError(ValueError):
    """nn -> kernel lowering 过程的显式错误。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 用于在 lowering 阶段中断执行并返回明确错误信息。

    使用示例:
    - raise LowerNnToKernelError("Unsupported nn op")

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """


_SUPPORTED_BINARY = {
    "nn.add": KernelAddOp,
    "nn.sub": KernelSubOp,
    "nn.mul": KernelMulOp,
    "nn.div": KernelDivOp,
    "nn.truediv": KernelDivOp,
    "nn.eq": KernelEqOp,
    "nn.ne": KernelNeOp,
    "nn.lt": KernelLtOp,
    "nn.le": KernelLeOp,
    "nn.gt": KernelGtOp,
    "nn.ge": KernelGeOp,
    "nn.matmul": KernelMatmulOp,
}

_RESULT_TYPED_ALLOC_OPS = {"nn.matmul", "nn.img2col1d", "nn.img2col2d"}



def _ensure_space_attr(op: Operation) -> NnMemorySpaceAttr:
    """获取并校验 nn op 的 space attribute。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 确认 op.attributes["space"] 为 NnMemorySpaceAttr。

    使用示例:
    - space = _ensure_space_attr(op)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    space = op.attributes.get("space")
    if not isinstance(space, NnMemorySpaceAttr):
        raise LowerNnToKernelError("nn op must provide nn.space attribute")
    return space


def _ensure_single_result(op: Operation) -> NnMemoryType:
    """校验 nn op 仅有单个结果且类型为 nn.memory。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 要求结果数量为 1。
    - 要求结果类型为 NnMemoryType。

    使用示例:
    - result_type = _ensure_single_result(op)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if len(op.results) != 1:
        raise LowerNnToKernelError("nn op must have exactly one result")
    result_type = op.results[0].type
    if not isinstance(result_type, NnMemoryType):
        raise LowerNnToKernelError("nn op result must be nn.memory")
    return result_type


def _ensure_operand_count(op: Operation, expected: int) -> None:
    """校验 nn op 的 operand 数量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - operand 数量不匹配时直接抛错。

    使用示例:
    - _ensure_operand_count(op, 2)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if len(op.operands) != expected:
        raise LowerNnToKernelError(
            f"nn op {op.name} expects {expected} operands, got {len(op.operands)}"
        )


def _parse_transpose_perm_attr(attr: object, rank: int) -> ArrayAttr:
    """解析 nn.transpose 的 perm attribute。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 校验 perm 为 ArrayAttr。
    - 校验 perm 为 0..rank-1 的排列。

    使用示例:
    - perm_attr = _parse_transpose_perm_attr(op.attributes["perm"], rank=2)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if not isinstance(attr, ArrayAttr):
        raise LowerNnToKernelError("nn.transpose perm must be ArrayAttr")
    perm_values: list[int] = []
    for entry in attr.data:
        if isinstance(entry, IntAttr):
            perm_values.append(entry.data)
            continue
        if isinstance(entry, IntegerAttr) and isinstance(entry.value, IntAttr):
            perm_values.append(entry.value.data)
            continue
        raise LowerNnToKernelError("nn.transpose perm must be a permutation of 0..rank-1")
    if len(perm_values) != rank or sorted(perm_values) != list(range(rank)):
        raise LowerNnToKernelError("nn.transpose perm must be a permutation of 0..rank-1")
    return attr


def _parse_softmax_axis_attr(attr: object) -> IntegerAttr:
    """解析 nn.softmax 的 axis attribute。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 接收 IntegerAttr 或 IntAttr，并规整为 i64 IntegerAttr。
    - 统一校验 axis 的 i64 类型约束。

    使用示例:
    - axis_attr = _parse_softmax_axis_attr(op.attributes.get("axis"))

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if isinstance(attr, IntegerAttr):
        axis_attr = attr
    elif isinstance(attr, IntAttr):
        axis_attr = IntegerAttr(attr.data, IntegerType(64))
    else:
        raise LowerNnToKernelError("nn.softmax axis must be i64 IntegerAttr")

    if not isinstance(axis_attr.type, IntegerType):
        raise LowerNnToKernelError("nn.softmax axis must be i64 IntegerAttr")
    width_attr = axis_attr.type.width
    width_value = width_attr.data if isinstance(width_attr, IntAttr) else width_attr
    if width_value != 64:
        raise LowerNnToKernelError("nn.softmax axis must be i64 IntegerAttr")
    return axis_attr


def _parse_reduce_axis_attr(attr: object, op_name: str) -> IntegerAttr:
    """解析 nn.reduce_* 的 axes attribute。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验 axes 为 ArrayAttr 且仅包含单轴。
    - 统一输出 i64 IntegerAttr。

    使用示例:
    - axis_attr = _parse_reduce_axis_attr(op.attributes["axes"], "nn.reduce_min")

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if not isinstance(attr, ArrayAttr):
        raise LowerNnToKernelError(f"{op_name} axes must be ArrayAttr")
    if len(attr.data) != 1:
        raise LowerNnToKernelError(f"{op_name} axes must contain exactly one axis")
    entry = attr.data[0]
    if isinstance(entry, IntAttr):
        axis_attr = IntegerAttr(entry.data, IntegerType(64))
    elif isinstance(entry, IntegerAttr):
        axis_attr = entry
    else:
        raise LowerNnToKernelError(f"{op_name} axes must be i64 IntegerAttr")
    if not isinstance(axis_attr.type, IntegerType):
        raise LowerNnToKernelError(f"{op_name} axes must be i64 IntegerAttr")
    width_attr = axis_attr.type.width
    width_value = width_attr.data if isinstance(width_attr, IntAttr) else width_attr
    if width_value != 64:
        raise LowerNnToKernelError(f"{op_name} axes must be i64 IntegerAttr")
    return axis_attr


def _parse_reduce_keepdim_attr(attr: object, op_name: str) -> IntegerAttr:
    """解析 nn.reduce_* 的 keepdim attribute。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验 keepdim 为 i1 IntegerAttr。

    使用示例:
    - keepdim_attr = _parse_reduce_keepdim_attr(op.attributes["keepdim"], "nn.reduce_min")

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if isinstance(attr, IntAttr):
        attr = IntegerAttr(attr.data, IntegerType(1))
    if not isinstance(attr, IntegerAttr):
        raise LowerNnToKernelError(f"{op_name} keepdim must be i1 IntegerAttr")
    if not isinstance(attr.type, IntegerType):
        raise LowerNnToKernelError(f"{op_name} keepdim must be i1 IntegerAttr")
    width_attr = attr.type.width
    width_value = width_attr.data if isinstance(width_attr, IntAttr) else width_attr
    if width_value != 1:
        raise LowerNnToKernelError(f"{op_name} keepdim must be i1 IntegerAttr")
    raw_value = attr.value.data
    if raw_value in (0, 1):
        return IntegerAttr(raw_value, IntegerType(1))
    if raw_value == -1:
        return IntegerAttr(1, IntegerType(1))
    raise LowerNnToKernelError(f"{op_name} keepdim must be bool")


def _build_alloc_dynamic_shape(
    source: SSAValue,
    result_type: NnMemoryType,
) -> tuple[list[Operation], list[SSAValue]]:
    """构造 dma.alloc 的 dynamic_shape operands。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 通过 symbol.get_dim 读取结果 shape 对应的符号值。
    - 逐维生成 !symbol.int operands，确保长度与 rank 一致。

    使用示例:
    - ops, operands = _build_alloc_dynamic_shape(op.operands[0], result_type)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    ops: list[Operation] = []
    operands: list[SSAValue] = []
    for axis, dim in enumerate(result_type.shape.data):
        if isinstance(dim, StringAttr) and dim.data == "?":
            raise LowerNnToKernelError("nn op result shape must not contain '?'")
        op = SymbolGetDimOp(source, IntAttr(axis))
        ops.append(op)
        operands.append(op.result)
    return ops, operands


def _const_symbol_value(expr: str, literal: int) -> tuple[list[Operation], SSAValue]:
    """构造 !symbol.int<"expr"> SSA value。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 先创建 i32 常量，再通过 UnrealizedConversionCastOp 转为 symbol.int。
    - expr 用于约束 symbol.int 的公开表达式。

    使用示例:
    - ops, value = _const_symbol_value("N", 0)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    const = arith.ConstantOp(IntegerAttr(literal, i32))
    cast = UnrealizedConversionCastOp(
        operands=[const.result], result_types=[SymbolValueType.from_expr(expr)]
    )
    return [const, cast], cast.results[0]


def _build_alloc_dynamic_shape_from_result(
    result_type: NnMemoryType,
    *,
    include_static: bool = True,
) -> tuple[list[Operation], list[SSAValue]]:
    """基于结果类型构造 dma.alloc 的 dynamic_shape operands。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - include_static=True 时，静态整数维度使用对应数值的 symbol.int。
    - include_static=False 时仅输出符号维度。
    - 符号维度使用同名 symbol.int。
    - 匿名动态维度不允许。

    使用示例:
    - ops, operands = _build_alloc_dynamic_shape_from_result(result_type)
    - ops, operands = _build_alloc_dynamic_shape_from_result(result_type, include_static=False)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    ops: list[Operation] = []
    operands: list[SSAValue] = []
    for dim in result_type.shape.data:
        if isinstance(dim, IntAttr):
            if not include_static:
                continue
            new_ops, value = _const_symbol_value(str(dim.data), dim.data)
            ops.extend(new_ops)
            operands.append(value)
            continue
        if isinstance(dim, StringAttr):
            if dim.data == "?":
                raise LowerNnToKernelError("nn op result shape must not contain '?'")
            new_ops, value = _const_symbol_value(dim.data, 0)
            ops.extend(new_ops)
            operands.append(value)
            continue
        raise LowerNnToKernelError("nn op result shape entry must be IntAttr or StringAttr")
    return ops, operands


def _build_broadcast_alloc_dynamic_shape(
    source: SSAValue,
    result_type: NnMemoryType,
) -> tuple[list[Operation], list[SSAValue]]:
    """构造 nn.broadcast 结果 dma.alloc 的 dynamic_shape operands。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 按尾维对齐规则，将 result 的每一维映射回 source 对应维度。
    - 对于可从 source 直接读取的维度（逐维相等），使用 symbol.get_dim 获取实际维度。
    - 对于由 singleton 扩张得到的静态整数维度，使用常量 symbol.int。
    - 禁止把 singleton 扩张为符号维度，避免引入无法从 source 获得的符号维。

    使用示例:
    - ops, operands = _build_broadcast_alloc_dynamic_shape(op.operands[0], result_type)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    source_type = source.type
    if not isinstance(source_type, NnMemoryType):
        raise LowerNnToKernelError("nn.broadcast operand must be nn.memory")

    source_rank = len(source_type.shape.data)
    result_rank = len(result_type.shape.data)
    if result_rank < source_rank:
        raise LowerNnToKernelError("nn.broadcast result rank must be >= operand rank")
    prefix_rank = result_rank - source_rank

    ops: list[Operation] = []
    operands: list[SSAValue] = []
    for result_axis, result_dim in enumerate(result_type.shape.data):
        if isinstance(result_dim, StringAttr) and result_dim.data == "?":
            raise LowerNnToKernelError("nn op result shape must not contain '?'")

        source_axis = result_axis - prefix_rank
        if source_axis < 0:
            if isinstance(result_dim, IntAttr):
                new_ops, value = _const_symbol_value(str(result_dim.data), result_dim.data)
                ops.extend(new_ops)
                operands.append(value)
                continue
            if isinstance(result_dim, StringAttr):
                raise LowerNnToKernelError(
                    "LowerNnToKernelBroadcastSymbolDimNotFromSource: "
                    f"nn.broadcast cannot expand implicit singleton dim to symbol dim '{result_dim.data}'"
                )
            raise LowerNnToKernelError("nn op result shape entry must be IntAttr or StringAttr")

        source_dim = source_type.shape.data[source_axis]

        if isinstance(source_dim, IntAttr) and isinstance(result_dim, IntAttr):
            if source_dim.data == result_dim.data:
                get_dim = SymbolGetDimOp(source, IntAttr(source_axis))
                ops.append(get_dim)
                operands.append(get_dim.result)
                continue
            if source_dim.data == 1:
                new_ops, value = _const_symbol_value(str(result_dim.data), result_dim.data)
                ops.extend(new_ops)
                operands.append(value)
                continue
            raise LowerNnToKernelError("nn.broadcast result shape is not compatible with operand shape")

        if isinstance(source_dim, StringAttr) and isinstance(result_dim, StringAttr):
            if source_dim.data == "?":
                raise LowerNnToKernelError("nn.broadcast operand shape must not contain '?'")
            if source_dim.data == result_dim.data:
                get_dim = SymbolGetDimOp(source, IntAttr(source_axis))
                ops.append(get_dim)
                operands.append(get_dim.result)
                continue
            raise LowerNnToKernelError("nn.broadcast result shape is not compatible with operand shape")

        if isinstance(source_dim, IntAttr) and source_dim.data == 1 and isinstance(result_dim, StringAttr):
            raise LowerNnToKernelError(
                "LowerNnToKernelBroadcastSymbolDimNotFromSource: "
                f"nn.broadcast cannot expand singleton dim to symbol dim '{result_dim.data}'"
            )

        raise LowerNnToKernelError("nn.broadcast result shape is not compatible with operand shape")

    return ops, operands


def _ensure_contiguous_result_stride(result_type: NnMemoryType) -> None:
    """校验结果 stride 在静态形状下满足连续布局。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅在 shape/stride 均为静态整数时进行连续性校验。
    - 若 stride 不满足行主序连续布局，抛出明确错误。

    使用示例:
    - _ensure_contiguous_result_stride(result_type)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    shape_dims: list[int] = []
    for dim in result_type.shape.data:
        if not isinstance(dim, IntAttr):
            return
        shape_dims.append(dim.data)

    stride_dims: list[int] = []
    for dim in result_type.stride.data:
        if not isinstance(dim, IntAttr):
            return
        stride_dims.append(dim.data)

    expected: list[int] = []
    running = 1
    for dim in reversed(shape_dims):
        expected.append(running)
        running *= dim
    expected.reverse()

    if stride_dims != expected:
        raise LowerNnToKernelError("dma.alloc requires contiguous result stride")


def _is_static_shape(result_type: NnMemoryType) -> bool:
    """判断结果 shape 是否全为静态整数维度。"""

    return all(isinstance(dim, IntAttr) for dim in result_type.shape.data)


def _select_shape_source(op: Operation) -> SSAValue:
    """选择用于生成 dynamic_shape 的 memory operand。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 优先返回第一个 `nn.memory` operand。
    - 为 mixed add 这类包含标量 operand 的路径提供统一 shape 来源。

    使用示例:
    - shape_source = _select_shape_source(op)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    for operand in op.operands:
        operand_value = SSAValue.get(operand)
        if isinstance(operand_value.type, NnMemoryType):
            return operand_value
    raise LowerNnToKernelError("nn op must provide at least one nn.memory operand")


def _maybe_materialize_mixed_add_rhs(
    op: Operation,
    result_type: NnMemoryType,
    dynamic_shape: list[SSAValue],
) -> tuple[list[Operation], SSAValue]:
    """按需把 mixed `nn.add` 的 rhs 标量物化为 temporary memory。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅处理 `nn.add(memory[i32], i32|!symbol.int)`。
    - 通过 `dma.alloc + dma.fill` 生成可被 `kernel.add` 消费的 rhs memory。

    使用示例:
    - extra_ops, rhs_value = _maybe_materialize_mixed_add_rhs(op, result_type, dynamic_shape)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if op.name != "nn.add":
        if len(op.operands) < 2:
            return [], SSAValue.get(op.operands[0])
        return [], SSAValue.get(op.operands[1])

    _ensure_operand_count(op, 2)
    lhs_value = SSAValue.get(op.operands[0])
    rhs_value = SSAValue.get(op.operands[1])
    lhs_type = lhs_value.type
    rhs_type = rhs_value.type

    if not isinstance(lhs_type, NnMemoryType):
        return [], rhs_value
    if isinstance(rhs_type, NnMemoryType):
        return [], rhs_value
    if rhs_type != i32 and not isinstance(rhs_type, SymbolValueType):
        return [], rhs_value
    if lhs_type.element_type != i32 or result_type.element_type != i32:
        raise LowerNnToKernelError("mixed nn.add lowering currently requires i32 memory/result")

    rhs_alloc = DmaAllocOp(dynamic_shape, result_type)
    rhs_fill = DmaFillOp(rhs_alloc.result, rhs_value)
    return [rhs_alloc, rhs_fill], rhs_alloc.result


def _build_kernel_op(
    op: Operation,
    out_value: SSAValue,
    space: NnMemorySpaceAttr,
    *,
    lhs_value: SSAValue | None = None,
    rhs_value: SSAValue | None = None,
) -> Operation:
    """构造 kernel dialect op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 根据 nn op 名称映射 kernel op。
    - 处理二元/选择/类型转换/单 operand 结构化 op。

    使用示例:
    - kernel_op = _build_kernel_op(op, alloc.results[0], space)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if op.name in _SUPPORTED_BINARY:
        _ensure_operand_count(op, 2)
        kernel_cls = _SUPPORTED_BINARY[op.name]
        lowered_lhs = lhs_value if lhs_value is not None else SSAValue.get(op.operands[0])
        lowered_rhs = rhs_value if rhs_value is not None else SSAValue.get(op.operands[1])
        return kernel_cls(lowered_lhs, lowered_rhs, out_value, space)

    if op.name == "nn.select":
        _ensure_operand_count(op, 3)
        return KernelSelectOp(op.operands[0], op.operands[1], op.operands[2], out_value, space)

    if op.name == "nn.cast":
        _ensure_operand_count(op, 1)
        return KernelCastOp(op.operands[0], out_value, space)

    if op.name == "nn.exp":
        _ensure_operand_count(op, 1)
        return KernelExpOp(op.operands[0], out_value, space)

    if op.name == "nn.softmax":
        _ensure_operand_count(op, 1)
        axis_attr = _parse_softmax_axis_attr(op.attributes.get("axis"))
        return KernelSoftmaxOp(op.operands[0], out_value, axis_attr, space)

    if op.name == "nn.img2col1d":
        _ensure_operand_count(op, 6)
        return KernelImg2col1dOp(
            op.operands[0],
            out_value,
            op.operands[1],
            op.operands[2],
            op.operands[3],
            op.operands[4],
            op.operands[5],
            space=space,
        )

    if op.name == "nn.img2col2d":
        _ensure_operand_count(op, 11)
        return KernelImg2col2dOp(
            op.operands[0],
            out_value,
            op.operands[1],
            op.operands[2],
            op.operands[3],
            op.operands[4],
            op.operands[5],
            op.operands[6],
            op.operands[7],
            op.operands[8],
            op.operands[9],
            op.operands[10],
            space=space,
        )

    if op.name == "nn.reduce_min":
        _ensure_operand_count(op, 1)
        axis_attr = _parse_reduce_axis_attr(op.attributes.get("axes"), "nn.reduce_min")
        keepdim_attr = _parse_reduce_keepdim_attr(op.attributes.get("keepdim"), "nn.reduce_min")
        return KernelReduceMinOp(op.operands[0], out_value, axis_attr, keepdim_attr, space)

    raise LowerNnToKernelError(f"Unsupported nn op: {op.name}")


def _lower_nn_op(op: Operation, block: Block) -> None:
    """将单个 nn op lower 为 kernel op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 为结果插入 dma.alloc。
    - 用 kernel op 替换 nn op，并替换所有使用者。
    - nn.broadcast 在 source/结果空间不一致时先插入 dma.alloc + dma.copy。
    - nn.transpose lower 为 dma.transpose。

    使用示例:
    - _lower_nn_op(op, block)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if op.name == "nn.transpose":
        _ensure_operand_count(op, 1)
        result_type = _ensure_single_result(op)
        _ensure_space_attr(op)
        source = SSAValue.get(op.operands[0])
        source_type = source.type
        if not isinstance(source_type, NnMemoryType):
            raise LowerNnToKernelError("nn.transpose operand must be nn.memory")
        perm_attr = _parse_transpose_perm_attr(op.attributes.get("perm"), len(source_type.shape.data))
        if _is_static_shape(result_type):
            shape_ops = []
            dynamic_shape = []
        else:
            shape_ops, dynamic_shape = _build_alloc_dynamic_shape_from_result(result_type)
        alloc = DmaAllocOp(dynamic_shape, result_type)
        transpose = DmaTransposeOp(alloc.result, source, perm_attr)

        try:
            alloc.verify()
            transpose.verify()
        except VerifyException as exc:
            raise LowerNnToKernelError(str(exc)) from exc

        block.insert_ops_before([*shape_ops, alloc, transpose], op)
        op.results[0].replace_by(alloc.result)
        block.erase_op(op)
        return

    if op.name == "nn.broadcast":
        _ensure_operand_count(op, 1)
        result_type = _ensure_single_result(op)
        _ensure_space_attr(op)
        source = SSAValue.get(op.operands[0])
        source_type = source.type
        if not isinstance(source_type, NnMemoryType):
            raise LowerNnToKernelError("nn.broadcast operand must be nn.memory")

        if _is_static_shape(result_type):
            shape_ops = []
            dynamic_shape = []
        else:
            shape_ops, dynamic_shape = _build_broadcast_alloc_dynamic_shape(source, result_type)
        alloc = DmaAllocOp(dynamic_shape, result_type)
        broadcast_source = source
        extra_ops: list[Operation] = []
        extra_alloc: DmaAllocOp | None = None
        extra_copy: DmaCopyOp | None = None
        if source_type.space.space.data != result_type.space.space.data:
            temp_type = NnMemoryType(
                source_type.shape,
                source_type.stride,
                source_type.element_type,
                result_type.space,
            )
            if _is_static_shape(temp_type):
                temp_shape_ops = []
                temp_dynamic_shape = []
            else:
                temp_shape_ops, temp_dynamic_shape = _build_alloc_dynamic_shape(source, temp_type)
            extra_alloc = DmaAllocOp(temp_dynamic_shape, temp_type)
            extra_copy = DmaCopyOp(source, extra_alloc.result)
            extra_ops.extend(temp_shape_ops)
            extra_ops.extend([extra_alloc, extra_copy])
            broadcast_source = extra_alloc.result

        broadcast = DmaBroadcastOp(alloc.result, broadcast_source)

        try:
            alloc.verify()
            if extra_alloc is not None and extra_copy is not None:
                extra_alloc.verify()
                extra_copy.verify()
            broadcast.verify()
        except VerifyException as exc:
            raise LowerNnToKernelError(str(exc)) from exc

        ops_to_insert = [*shape_ops, *extra_ops, alloc, broadcast]
        block.insert_ops_before(ops_to_insert, op)
        op.results[0].replace_by(alloc.result)
        block.erase_op(op)
        return

    result_type = _ensure_single_result(op)
    space = _ensure_space_attr(op)

    _ensure_contiguous_result_stride(result_type)
    if _is_static_shape(result_type):
        shape_ops: list[Operation] = []
        dynamic_shape: list[SSAValue] = []
    elif op.name == "nn.reduce_min":
        shape_ops, dynamic_shape = _build_alloc_dynamic_shape_from_result(
            result_type,
            include_static=False,
        )
    elif op.name in _RESULT_TYPED_ALLOC_OPS:
        shape_ops, dynamic_shape = _build_alloc_dynamic_shape_from_result(result_type)
    else:
        shape_source = _select_shape_source(op)
        shape_ops, dynamic_shape = _build_alloc_dynamic_shape(shape_source, result_type)
    alloc = DmaAllocOp(dynamic_shape, result_type)
    rhs_ops, lowered_rhs = _maybe_materialize_mixed_add_rhs(op, result_type, dynamic_shape)
    kernel_op = _build_kernel_op(op, alloc.result, space, rhs_value=lowered_rhs)

    try:
        alloc.verify()
        for rhs_op in rhs_ops:
            rhs_op.verify()
        kernel_op.verify()
    except VerifyException as exc:
        raise LowerNnToKernelError(str(exc)) from exc

    block.insert_ops_before([*shape_ops, alloc, *rhs_ops, kernel_op], op)
    op.results[0].replace_by(alloc.result)
    block.erase_op(op)


def _lower_block(block: Block) -> None:
    """对单个 block 执行 nn -> kernel lowering。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 按顺序 lower block 内出现的 nn op。

    使用示例:
    - _lower_block(block)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    ops = list(block.ops)
    for op in ops:
        for region in op.regions:
            _lower_region(region)
        if op.name.startswith("nn."):
            _lower_nn_op(op, block)


def _lower_region(region: Region) -> None:
    """对 region 内的所有 block 执行 lowering。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 遍历 region 的每个 block 并执行 lowering。

    使用示例:
    - _lower_region(region)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    for block in region.blocks:
        _lower_block(block)


def _lower_module(module: Operation) -> None:
    """在 module 中执行 nn -> kernel lowering。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅对 func.func 进行 lowering。

    使用示例:
    - _lower_module(module)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    for op in module.ops:
        if isinstance(op, func.FuncOp):
            _lower_region(op.body)


def _iter_ops(module: Operation) -> Iterable[Operation]:
    """遍历 module 内全部 op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 递归遍历 module 内所有 op。

    使用示例:
    - for op in _iter_ops(module):
          ...

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    stack: list[Operation] = list(module.ops)
    while stack:
        op = stack.pop()
        yield op
        for region in op.regions:
            for block in region.blocks:
                stack.extend(reversed(list(block.ops)))


def _ensure_no_nn_ops(module: Operation) -> None:
    """确保 module 内不残留 nn op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 遍历 module，若发现 nn op 则抛错。

    使用示例:
    - _ensure_no_nn_ops(module)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    for op in _iter_ops(module):
        if op.name.startswith("nn."):
            raise LowerNnToKernelError(f"nn op remains after lowering: {op.name}")


class LowerNnToKernelPass(Pass):
    """nn -> kernel lowering pass。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 执行 nn dialect 到 kernel dialect 的 lowering。

    使用示例:
    - module = LowerNnToKernelPass().run(module)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    name = "lower-nn-to-kernel"

    def run(self: "LowerNnToKernelPass", module: Operation) -> Operation:
        """执行 pass。

        创建者: 金铲铲大作战
        最后一次更改: 小李飞刀

        功能说明:
        - 将 module 内 nn op lower 为 kernel op。

        使用示例:
        - LowerNnToKernelPass().run(module)

        关联文件:
        - spec: spec/pass/lowering/nn_to_kernel.md
        - test: test/pass/test_lowering_nn_to_kernel.py
        - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
        """

        if not isinstance(module, ModuleOp):
            raise LowerNnToKernelError("module must be builtin.module")
        try:
            iter(module.ops)
        except TypeError as exc:
            raise LowerNnToKernelError("module ops must be iterable") from exc

        _lower_module(module)
        _ensure_no_nn_ops(module)
        return module


__all__ = ["LowerNnToKernelPass", "LowerNnToKernelError"]
