"""nn.softmax decompose pass。

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 将 `func.func` 内的 `nn.softmax` 固定展开为 `nn.reduce_max -> nn.broadcast -> nn.sub -> nn.exp -> nn.reduce_sum -> nn.broadcast -> nn.truediv`。
- 在 pass 内把 `axis` 规整为非负下标，并显式拒绝越界 axis。
- 仅停留在 `nn` 方言层，不承担 `nn -> kernel` lowering。

使用示例:
- from kernel_gen.passes.lowering.decompose_nn_softmax import DecomposeNnSoftmaxPass
- module = DecomposeNnSoftmaxPass().run(module)

关联文件:
- spec: spec/pass/lowering/decompose_nn_softmax.md
- test: test/pass/test_decompose_nn_softmax.py
- 功能实现: kernel_gen/passes/lowering/decompose_nn_softmax.py
"""

from __future__ import annotations

from collections.abc import Sequence

from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, IntAttr, ModuleOp, StringAttr
from xdsl.ir import Attribute, Block, Operation, Region, SSAValue
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import (
    NnBroadcastOp,
    NnExpOp,
    NnMemoryType,
    NnReduceMaxOp,
    NnReduceSumOp,
    NnSoftmaxOp,
    NnSubOp,
    NnTrueDivOp,
)
from ..pass_manager import Pass


class DecomposeNnSoftmaxError(ValueError):
    """`decompose-nn-softmax` pass 的显式错误。"""


def _attr_product(factors: Sequence[Attribute]) -> Attribute:
    """把一组 shape 因子规整为 stride attribute。"""

    int_product = 1
    expr_parts: list[str] = []
    for factor in factors:
        if isinstance(factor, IntAttr):
            int_product *= factor.data
            continue
        if isinstance(factor, StringAttr):
            expr_parts.append(factor.data)
            continue
        raise DecomposeNnSoftmaxError(
            "DecomposeNnSoftmaxError: shape entries must be IntAttr or StringAttr"
        )

    if not expr_parts:
        return IntAttr(int_product)

    parts: list[str] = []
    if int_product != 1:
        parts.append(str(int_product))
    parts.extend(part for part in expr_parts if part != "1")
    if not parts:
        return IntAttr(1)
    return StringAttr("*".join(parts))


def _build_contiguous_stride(shape: Sequence[Attribute]) -> ArrayAttr[Attribute]:
    """按 shape 生成连续布局 stride。"""

    suffix_factors: list[Attribute] = []
    strides: list[Attribute] = []
    for dim in reversed(shape):
        strides.append(_attr_product(suffix_factors))
        suffix_factors.insert(0, dim)
    strides.reverse()
    return ArrayAttr(strides)


def _build_reduce_result_type(input_type: NnMemoryType, axis: int) -> NnMemoryType:
    """构造 keepdim=true 的 reduce 结果类型。"""

    result_shape = list(input_type.shape.data)
    result_shape[axis] = IntAttr(1)
    return NnMemoryType(
        ArrayAttr(result_shape),
        _build_contiguous_stride(result_shape),
        input_type.element_type,
        input_type.space,
    )


def _normalize_axis(axis: int, rank: int) -> int:
    """把 softmax axis 规整为非负下标。"""

    normalized = axis if axis >= 0 else rank + axis
    if normalized < 0 or normalized >= rank:
        raise DecomposeNnSoftmaxError("DecomposeNnSoftmaxError: normalized axis out of range")
    return normalized


def _ensure_operand_and_result_types(op: NnSoftmaxOp) -> tuple[NnMemoryType, NnMemoryType]:
    """校验 softmax operand/result 基础类型。"""

    input_type = op.input.type
    result_type = op.result.type
    if not isinstance(input_type, NnMemoryType) or not isinstance(result_type, NnMemoryType):
        raise DecomposeNnSoftmaxError(
            "DecomposeNnSoftmaxError: operand and result must be nn.memory"
        )
    return input_type, result_type


def _ensure_softmax_result_matches_input(op: NnSoftmaxOp) -> tuple[NnMemoryType, NnMemoryType]:
    """校验 softmax 结果类型与输入 shape/stride 一致。"""

    input_type, result_type = _ensure_operand_and_result_types(op)
    if input_type.shape != result_type.shape or input_type.stride != result_type.stride:
        raise DecomposeNnSoftmaxError(
            "DecomposeNnSoftmaxError: result type must match input shape and stride"
        )
    return input_type, result_type


def _verify_new_ops(ops: Sequence[Operation]) -> None:
    """逐个验证新生成的分解 op。"""

    for op in ops:
        try:
            op.verify()
        except VerifyException as exc:
            raise DecomposeNnSoftmaxError(f"DecomposeNnSoftmaxError: {exc}") from exc


def _decompose_softmax_op(op: NnSoftmaxOp, block: Block) -> None:
    """把单个 `nn.softmax` 展开为固定 7 段链。"""

    input_type, result_type = _ensure_softmax_result_matches_input(op)
    rank = len(input_type.shape.data)
    normalized_axis = _normalize_axis(op.axis.value.data, rank)
    reduce_type = _build_reduce_result_type(input_type, normalized_axis)

    max_op = NnReduceMaxOp(op.input, reduce_type, axes=[normalized_axis], keepdim=True, space=op.space)
    max_broadcast = NnBroadcastOp(max_op.result, result_type, op.space)
    sub_op = NnSubOp(op.input, max_broadcast.result, result_type, op.space)
    exp_op = NnExpOp(sub_op.result, result_type, op.space)
    sum_op = NnReduceSumOp(exp_op.result, reduce_type, axes=[normalized_axis], keepdim=True, space=op.space)
    sum_broadcast = NnBroadcastOp(sum_op.result, result_type, op.space)
    div_op = NnTrueDivOp(exp_op.result, sum_broadcast.result, result_type, op.space)
    new_ops = [max_op, max_broadcast, sub_op, exp_op, sum_op, sum_broadcast, div_op]

    _verify_new_ops(new_ops)
    block.insert_ops_before(new_ops, op)
    op.result.replace_by(div_op.result)
    block.erase_op(op)


def _decompose_block(block: Block) -> None:
    """递归处理 block 内部全部 softmax。"""

    for op in list(block.ops):
        for region in op.regions:
            _decompose_region(region)
        if isinstance(op, NnSoftmaxOp):
            _decompose_softmax_op(op, block)


def _decompose_region(region: Region) -> None:
    """递归处理 region。"""

    for block in region.blocks:
        _decompose_block(block)


def _decompose_module(module: ModuleOp) -> None:
    """仅在 `func.func` 内执行 softmax 分解。"""

    for op in module.ops:
        if isinstance(op, func.FuncOp):
            _decompose_region(op.body)


class DecomposeNnSoftmaxPass(Pass):
    """把 `nn.softmax` 分解为固定 7 段 `nn` 方言链。"""

    name = "decompose-nn-softmax"

    def run(self: "DecomposeNnSoftmaxPass", module: Operation) -> Operation:
        """执行 `decompose-nn-softmax` pass。"""

        if not isinstance(module, ModuleOp):
            raise DecomposeNnSoftmaxError("DecomposeNnSoftmaxError: module must be builtin.module")
        _decompose_module(module)
        return module


__all__ = ["DecomposeNnSoftmaxPass", "DecomposeNnSoftmaxError"]
