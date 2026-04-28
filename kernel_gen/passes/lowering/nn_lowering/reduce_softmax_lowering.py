"""reduce/softmax boundary lowering 实现。

创建者: 小李飞刀
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 提供 nn.reduce_* 的单 op pattern lowering 入口。
- `nn.softmax` 不在本层直接 lowering，需先由上游完成分解。
- surviving 模块级接口为 `reduce_softmax_patterns()`。

API 列表:
- `reduce_softmax_patterns() -> list[RewritePattern]`

使用示例:
- from kernel_gen.passes.lowering.nn_lowering.reduce_softmax_lowering import reduce_softmax_patterns
- patterns = reduce_softmax_patterns()

关联文件:
- spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
- test: test/pass/nn_lowering/test_reduce_lowering.py
- test: test/pass/nn_lowering/public_name.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
"""

from __future__ import annotations
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

from xdsl.dialects.builtin import ArrayAttr, IntAttr, IntegerAttr, IntegerType, StringAttr
from xdsl.ir import Attribute, Block, Operation, SSAValue
from xdsl.pattern_rewriter import PatternRewriter, RewritePattern, op_type_rewrite_pattern

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.kernel import KernelReduceOp
from kernel_gen.dialect.nn import (
    NnMemorySpaceAttr,
    NnMemoryType,
    NnReduceMaxOp,
    NnReduceMinOp,
    NnReduceSumOp,
    NnSoftmaxOp,
)
from kernel_gen.dialect.symbol import SymbolGetDimOp, SymbolValueType
from .nn_lowering_utility import ensure_expected_op_name


def _ensure_space_attr(op: Operation) -> NnMemorySpaceAttr:
    """获取并校验 nn op 的 space attribute。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 在当前文件内保持 reduce/softmax family 所需的 `space` 校验逻辑。
    - 避免跨文件直连 `nn_lowering.py` 的下划线 helper。

    使用示例:
    - space = _ensure_space_attr(op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/test_reduce_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
    """

    space = op.attributes.get("space")
    if not isinstance(space, NnMemorySpaceAttr):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn op must define #nn.space attribute")
    return space


def _ensure_single_result(op: Operation) -> NnMemoryType:
    """获取并校验 op 的唯一输出类型。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 在当前文件内保持 `nn.memory` 单结果校验逻辑。
    - 避免跨文件直连 `nn_lowering.py` 的下划线 helper。

    使用示例:
    - result_type = _ensure_single_result(op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/test_reduce_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
    """

    if len(op.results) != 1:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn op must produce exactly one result")
    result_type = op.results[0].type
    if not isinstance(result_type, NnMemoryType):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn op result must be nn.memory")
    return result_type


def _ensure_symbol_or_int(op: Operation, operand: SSAValue | Operation) -> SSAValue:
    """确保 operand 为 symbol.int 或整数 SSAValue。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 在当前文件内保持 reduce family 第二操作数的最小校验逻辑。
    - 允许 `!symbol.int` 或整数 SSAValue。
    - 避免跨文件直连 `nn_lowering.py` 的下划线 helper。

    使用示例:
    - _ensure_symbol_or_int(op, op.operands[1])

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
    """

    if isinstance(operand, Operation):
        operand = operand.results[0]
    if isinstance(operand.type, SymbolValueType):
        return operand
    if isinstance(operand.type, IntegerType):
        return operand
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "broadcast scalar must be int or symbol")


def _ensure_reduce_axis(op_name: str, axes_attr: ArrayAttr) -> int:
    """校验 reduce 轴参数。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 确保 axes_attr 为 ArrayAttr 且仅包含一个 IntegerAttr。

    使用示例:
    - axis = _ensure_reduce_axis("nn.reduce_min", axes_attr)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/test_reduce_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
    """

    if not isinstance(axes_attr, ArrayAttr):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"{op_name} axes must be ArrayAttr")
    if len(axes_attr.data) == 0:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "reduce axes must be non-empty")
    if len(axes_attr.data) != 1:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "reduce axes must contain exactly one element")
    axis_attr = axes_attr.data[0]
    if isinstance(axis_attr, IntegerAttr):
        return axis_attr.value.data
    if isinstance(axis_attr, IntAttr):
        return axis_attr.data
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "reduce axis must be integer")


def _ensure_reduce_keepdim(op_name: str, keepdim_attr: Attribute) -> bool:
    """校验 reduce keepdim 参数。

    创建者: 金铲铲大作战
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - keepdim 支持 IntegerAttr/IntAttr 的 0 或 1。
    - DSL 生成的布尔属性会打印为 true/false，底层为 i1 IntegerAttr，也按布尔值处理。

    使用示例:
    - keepdim = _ensure_reduce_keepdim("nn.reduce_min", keepdim_attr)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/test_reduce_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
    """

    if isinstance(keepdim_attr, IntegerAttr):
        keepdim = keepdim_attr.value.data
        width = getattr(keepdim_attr.type, "width", None)
        if getattr(width, "data", None) == 1:
            if keepdim == 0 or keepdim is False:
                return False
            if keepdim == 1 or keepdim == -1 or keepdim is True:
                return True
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "keepdim must be 0 or 1")
    elif isinstance(keepdim_attr, IntAttr):
        keepdim = keepdim_attr.data
    else:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "keepdim must be integer")
    if keepdim in (0, 1):
        return bool(keepdim)
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "keepdim must be 0 or 1")


def _build_alloc_dynamic_shape_from_operand(
    block: Block,
    op: Operation,
    operand: Operation,
    result_type: NnMemoryType,
    axis_map: list[int],
) -> list[SSAValue]:
    """基于 operand 构造 dma.alloc 的 dynamic_shape。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 针对 result_type 的符号维度插入 symbol.get_dim。
    - 以 axis_map 指定 result 维度与 operand 维度的映射。

    使用示例:
    - dynamic_shape = _build_alloc_dynamic_shape_from_operand(block, op, operand, result_type, axis_map)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/test_reduce_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
    """

    if not isinstance(operand.type, NnMemoryType):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"{op.name} operand must be nn.memory")

    dynamic_shape: list[SSAValue] = []
    for result_axis, dim in enumerate(result_type.shape.data):
        if not isinstance(dim, StringAttr):
            continue
        operand_axis = axis_map[result_axis]
        symbol_op = SymbolGetDimOp(operand, IntAttr(operand_axis))
        block.insert_op_before(symbol_op, op)
        dynamic_shape.append(symbol_op.result)
    return dynamic_shape


def _lower_reduce(block: Block, op: Operation, *, kind: str) -> None:
    """lower reduce family。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 校验 axes / keepdim。
    - 先创建 dma.alloc，再调用 kernel.reduce(kind=...)。

    使用示例:
    - _lower_reduce(block, op, kind="min")

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/test_reduce_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
    """

    space = _ensure_space_attr(op)
    result_type = _ensure_single_result(op)
    if len(op.operands) == 2:
        _ensure_symbol_or_int(op, op.operands[1])
    elif len(op.operands) != 1:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"{op.name} must have 1 operands")
    operand = op.operands[0]
    if not isinstance(operand.type, NnMemoryType):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn.reduce operand must be nn.memory")
    axes_attr = op.attributes.get("axes")
    if axes_attr is None:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"{op.name} axes must be ArrayAttr")
    axis = _ensure_reduce_axis(op.name, axes_attr)
    keepdim_attr = op.attributes.get("keepdim")
    if keepdim_attr is None:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"{op.name} keepdim must be bool")
    keepdim = _ensure_reduce_keepdim(op.name, keepdim_attr)
    operand_rank = len(operand.type.shape.data)
    result_rank = len(result_type.shape.data)
    expected_rank = operand_rank if keepdim else operand_rank - 1
    if result_rank != expected_rank:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "reduce shape rank must match")
    operand_shape = operand.type.shape.data
    result_shape = result_type.shape.data
    if keepdim:
        for idx, operand_dim in enumerate(operand_shape):
            result_dim = result_shape[idx]
            if idx == axis:
                if isinstance(result_dim, StringAttr):
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "reduce keepdim dimension must be 1")
                if isinstance(result_dim, IntegerAttr):
                    dim_value = result_dim.value.data
                elif isinstance(result_dim, IntAttr):
                    dim_value = result_dim.data
                else:
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "reduce keepdim dimension must be 1")
                if dim_value != 1:
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "reduce keepdim dimension must be 1")
            else:
                if isinstance(result_dim, StringAttr) and isinstance(operand_dim, StringAttr):
                    if result_dim.data != operand_dim.data:
                        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "reduce shape mismatch")
                elif isinstance(result_dim, (IntegerAttr, IntAttr)) and isinstance(
                    operand_dim, (IntegerAttr, IntAttr)
                ):
                    result_value = result_dim.value.data if isinstance(result_dim, IntegerAttr) else result_dim.data
                    operand_value = (
                        operand_dim.value.data if isinstance(operand_dim, IntegerAttr) else operand_dim.data
                    )
                    if result_value != operand_value:
                        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "reduce shape mismatch")
                else:
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "reduce shape mismatch")
    if keepdim:
        axis_map = list(range(operand_rank))
    else:
        axis_map = []
        for result_axis in range(result_rank):
            operand_axis = result_axis if result_axis < axis else result_axis + 1
            axis_map.append(operand_axis)
        for result_axis, operand_axis in enumerate(axis_map):
            result_dim = result_shape[result_axis]
            operand_dim = operand_shape[operand_axis]
            if isinstance(result_dim, StringAttr) and isinstance(operand_dim, StringAttr):
                if result_dim.data != operand_dim.data:
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "reduce shape mismatch")
            elif isinstance(result_dim, (IntegerAttr, IntAttr)) and isinstance(
                operand_dim, (IntegerAttr, IntAttr)
            ):
                result_value = result_dim.value.data if isinstance(result_dim, IntegerAttr) else result_dim.data
                operand_value = operand_dim.value.data if isinstance(operand_dim, IntegerAttr) else operand_dim.data
                if result_value != operand_value:
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "reduce shape mismatch")
            else:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "reduce shape mismatch")
    dynamic_shape = _build_alloc_dynamic_shape_from_operand(block, op, operand, result_type, axis_map)
    alloc = DmaAllocOp(dynamic_shape, result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = KernelReduceOp(result, operand, kind=kind, axis=axis, keepdim=keepdim, space=space)
    lowered.attributes = {
        "axis": lowered.attributes["axis"],
        "keepdim": lowered.attributes["keepdim"],
        "kind": lowered.attributes["kind"],
        "space": lowered.attributes["space"],
    }
    block.insert_op_before(lowered, op)
    op.results[0].replace_all_uses_with(result)
    block.erase_op(op)
class _LowerNnReduceSumPattern(RewritePattern):
    """将单个 nn.reduce_sum lowering 为 kernel.reduce(kind=sum)。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 通过 `@op_type_rewrite_pattern` 直接匹配 `NnReduceSumOp`。
    - 复用 `_lower_reduce(..., kind="sum")`，保持既有 IR 输出不变。

    使用示例:
    - pattern = _LowerNnReduceSumPattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/public_name.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnReduceSumOp, rewriter: PatternRewriter, /) -> None:
        block = op.parent_block()
        if block is None:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn op must be inside a block")
        ensure_expected_op_name(op, "nn.reduce_sum")
        _lower_reduce(block, op, kind="sum")
        rewriter.has_done_action = True


class _LowerNnReduceMinPattern(RewritePattern):
    """将单个 nn.reduce_min lowering 为 kernel.reduce(kind=min)。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 通过 `@op_type_rewrite_pattern` 直接匹配 `NnReduceMinOp`。
    - 复用 `_lower_reduce(..., kind="min")`，保持既有 IR 输出不变。

    使用示例:
    - pattern = _LowerNnReduceMinPattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/public_name.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnReduceMinOp, rewriter: PatternRewriter, /) -> None:
        block = op.parent_block()
        if block is None:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn op must be inside a block")
        ensure_expected_op_name(op, "nn.reduce_min")
        _lower_reduce(block, op, kind="min")
        rewriter.has_done_action = True


class _LowerNnReduceMaxPattern(RewritePattern):
    """将单个 nn.reduce_max lowering 为 kernel.reduce(kind=max)。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 通过 `@op_type_rewrite_pattern` 直接匹配 `NnReduceMaxOp`。
    - 复用 `_lower_reduce(..., kind="max")`，保持既有 IR 输出不变。

    使用示例:
    - pattern = _LowerNnReduceMaxPattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/public_name.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnReduceMaxOp, rewriter: PatternRewriter, /) -> None:
        block = op.parent_block()
        if block is None:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn op must be inside a block")
        ensure_expected_op_name(op, "nn.reduce_max")
        _lower_reduce(block, op, kind="max")
        rewriter.has_done_action = True


class _RejectNnSoftmaxPattern(RewritePattern):
    """拒绝 direct nn.softmax lowering。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 通过 `@op_type_rewrite_pattern` 直接匹配 `NnSoftmaxOp`。
    - 维持当前公开错误短语：nn.softmax 必须先由上游分解。

    使用示例:
    - pattern = _RejectNnSoftmaxPattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/public_name.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnSoftmaxOp, rewriter: PatternRewriter, /) -> None:
        _ = rewriter
        ensure_expected_op_name(op, "nn.softmax")
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn.softmax must be decomposed before lower-nn")


def reduce_softmax_patterns() -> list[RewritePattern]:
    """返回 reduce/softmax 边界 rewrite pattern 集合。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 提供 nn_lowering 主 driver 的 reduce 单 op pattern 注册入口。
    - 保留 direct nn.softmax 的显式拒绝边界。

    使用示例:
    - patterns = reduce_softmax_patterns()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/public_name.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
    """

    return [
        _LowerNnReduceSumPattern(),
        _LowerNnReduceMinPattern(),
        _LowerNnReduceMaxPattern(),
        _RejectNnSoftmaxPattern(),
    ]


__all__ = ["reduce_softmax_patterns"]
