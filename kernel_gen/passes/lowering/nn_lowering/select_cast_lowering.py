"""select/cast/exp lowering 实现。

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- nn.select -> dma.alloc + kernel.select
- nn.cast -> dma.alloc + dma.cast
- nn.exp -> dma.alloc + kernel.exp
- 既保留 block 级兼容 helper，也提供按具体 nn op 类型匹配的单 op RewritePattern 集合。

使用示例:
- from kernel_gen.passes.lowering.nn_lowering.select_cast_lowering import lower_select_cast_family
- lower_select_cast_family(block, op)
- from kernel_gen.passes.lowering.nn_lowering.select_cast_lowering import select_cast_patterns
- patterns = select_cast_patterns()

关联文件:
- spec: spec/pass/lowering/nn_lowering.md
- test: test/pass/nn_lowering/select.py
- test: test/pass/nn_lowering/cast.py
- test: test/pass/nn_lowering/exp.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
"""

from __future__ import annotations

from xdsl.dialects.builtin import IntAttr, StringAttr
from xdsl.dialects.builtin import IntegerType
from xdsl.dialects.builtin import (
    BFloat16Type,
    Float16Type,
    Float32Type,
    Float64Type,
)
from xdsl.ir import Block, Operation, SSAValue
from xdsl.pattern_rewriter import PatternRewriter, RewritePattern, op_type_rewrite_pattern
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.dma import DmaAllocOp, DmaCastOp
from kernel_gen.dialect.kernel import KernelExpOp, KernelSelectOp
from kernel_gen.dialect.nn import NnCastOp, NnExpOp, NnMemoryType, NnSelectOp
from kernel_gen.dialect.symbol import SymbolGetDimOp, SymbolValueType
from .nn_lowering_utility import (
    NnLoweringError,
    ensure_expected_op_name,
    ensure_operand_count,
    ensure_single_result,
    ensure_space_attr,
)


def _build_alloc_dynamic_shape_from_source(
    source: SSAValue,
    result_type: NnMemoryType,
) -> tuple[list[Operation], list[SSAValue]]:
    """基于 memory operand 构造 dma.alloc 的 dynamic_shape。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅对符号维度使用 symbol.get_dim 读取 shape 对应维度。
    - 全静态 shape 时返回空的 dynamic_shape。
    - 禁止结果 shape 包含匿名维度 '?'。
    - source 与 result rank 不一致时抛出 NnLoweringError。

    使用示例:
    - ops, dynamic_shape = _build_alloc_dynamic_shape_from_source(source, result_type)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/select.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
    """

    source_type = source.type
    if not isinstance(source_type, NnMemoryType):
        raise NnLoweringError("dynamic_shape source must be nn.memory")
    if len(source_type.shape.data) != len(result_type.shape.data):
        raise NnLoweringError("nn select/cast operand/result rank mismatch")

    ops: list[Operation] = []
    operands: list[SSAValue] = []
    for axis, dim in enumerate(result_type.shape.data):
        if isinstance(dim, IntAttr):
            continue
        if isinstance(dim, StringAttr):
            if dim.data == "?":
                raise NnLoweringError("nn select/cast result shape must not contain '?'")
            get_dim = SymbolGetDimOp(source, IntAttr(axis))
            ops.append(get_dim)
            operands.append(get_dim.result)
            continue
        raise NnLoweringError("nn select/cast result shape must be int or symbol")
    return ops, operands


def _lower_select_op(op: Operation, block: Block) -> None:
    """对 nn.select 执行 lowering。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 输出 memory 通过 dma.alloc 创建。
    - 使用 kernel.select 完成写入。

    使用示例:
    - _lower_select_op(op, block)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/select.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
    """

    ensure_operand_count(op, 3)
    result_type = ensure_single_result(op)
    space = ensure_space_attr(op)

    cond_value = SSAValue.get(op.operands[0])
    lhs_value = SSAValue.get(op.operands[1])
    rhs_value = SSAValue.get(op.operands[2])
    if not isinstance(cond_value.type, NnMemoryType):
        raise NnLoweringError("nn.select cond must be nn.memory")
    if not isinstance(lhs_value.type, NnMemoryType):
        raise NnLoweringError("nn.select lhs must be nn.memory")
    if not isinstance(rhs_value.type, NnMemoryType):
        raise NnLoweringError("nn.select rhs must be nn.memory")

    shape_ops, dynamic_shape = _build_alloc_dynamic_shape_from_source(lhs_value, result_type)
    alloc = DmaAllocOp(dynamic_shape, result_type)
    kernel_op = KernelSelectOp(alloc.result, cond_value, lhs_value, rhs_value, space)

    try:
        alloc.verify()
        kernel_op.verify()
    except VerifyException as exc:
        raise NnLoweringError(str(exc)) from exc

    block.insert_ops_before([*shape_ops, alloc, kernel_op], op)
    op.results[0].replace_all_uses_with(alloc.result)
    block.erase_op(op)


def _lower_cast_op(op: Operation, block: Block) -> None:
    """对 nn.cast 执行 lowering。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 输出 memory 通过 dma.alloc 创建。
    - 使用 dma.cast 完成写入。

    使用示例:
    - _lower_cast_op(op, block)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/cast.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
    """

    if len(op.operands) == 2:
        _ensure_symbol_or_int(op, op.operands[1])
    else:
        ensure_operand_count(op, 1)
    result_type = ensure_single_result(op)

    input_value = SSAValue.get(op.operands[0])
    if not isinstance(input_value.type, NnMemoryType):
        raise NnLoweringError("nn.cast input must be nn.memory")
    for elem_type in (input_value.type.element_type, result_type.element_type):
        if isinstance(elem_type, IntegerType):
            if elem_type.width.data == 1:
                raise NnLoweringError("nn.cast element_type must be integer or float and not i1")
            continue
        if not isinstance(elem_type, (Float16Type, Float32Type, Float64Type, BFloat16Type)):
            raise NnLoweringError("nn.cast element_type must be integer or float and not i1")

    shape_ops, dynamic_shape = _build_alloc_dynamic_shape_from_source(input_value, result_type)
    alloc = DmaAllocOp(dynamic_shape, result_type)
    dma_cast_op = DmaCastOp(alloc.result, input_value)

    try:
        dma_cast_op.verify_()
        alloc.verify()
    except VerifyException as exc:
        raise NnLoweringError(str(exc)) from exc

    block.insert_ops_before([*shape_ops, alloc, dma_cast_op], op)
    op.results[0].replace_all_uses_with(alloc.result)
    block.erase_op(op)


def _lower_exp_op(op: Operation, block: Block) -> None:
    """对 nn.exp 执行 lowering。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 输出 memory 通过 dma.alloc 创建。
    - 使用 kernel.exp 完成写入。

    使用示例:
    - _lower_exp_op(op, block)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/exp.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
    """

    ensure_operand_count(op, 1)
    result_type = ensure_single_result(op)

    operand = SSAValue.get(op.operands[0])
    if not isinstance(operand.type, NnMemoryType):
        raise NnLoweringError("nn.exp operand must be nn.memory")
    if operand.type.shape != result_type.shape or operand.type.stride != result_type.stride:
        raise NnLoweringError("nn.exp result shape must match operand")

    shape_ops, dynamic_shape = _build_alloc_dynamic_shape_from_source(operand, result_type)
    alloc = DmaAllocOp(dynamic_shape, result_type)
    lowered = KernelExpOp(alloc.result, operand, ensure_space_attr(op))

    try:
        alloc.verify()
    except VerifyException as exc:
        raise NnLoweringError(str(exc)) from exc

    block.insert_ops_before([*shape_ops, alloc, lowered], op)
    op.results[0].replace_all_uses_with(alloc.result)
    block.erase_op(op)


def _ensure_symbol_or_int(op: Operation, operand: SSAValue | Operation) -> SSAValue:
    """确保 operand 为 symbol.int 或整数类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 symbol.int 或 IntegerType。

    使用示例:
    - value = _ensure_symbol_or_int(op, operand)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/cast.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
    """

    if isinstance(operand, Operation):
        operand = operand.results[0]
    if isinstance(operand.type, SymbolValueType):
        return operand
    if isinstance(operand.type, IntegerType):
        return operand
    raise NnLoweringError("nn.cast optional operand must be int or symbol")


class _LowerSelectPattern(RewritePattern):
    """将单个 nn.select lowering 为 kernel.select。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 通过 `@op_type_rewrite_pattern` 直接匹配 `NnSelectOp`。
    - 复用 `_lower_select_op(...)`，保持现有 IR 输出不变。

    使用示例:
    - pattern = _LowerSelectPattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/select_cast_lowering.md
    - test: test/pass/nn_lowering/select.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnSelectOp, rewriter: PatternRewriter, /) -> None:
        block = op.parent_block()
        if block is None:
            raise NnLoweringError("nn op must be inside a block")
        ensure_expected_op_name(op, "nn.select")
        _lower_select_op(op, block)
        rewriter.has_done_action = True


class _LowerCastPattern(RewritePattern):
    """将单个 nn.cast lowering 为 dma.cast。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 通过 `@op_type_rewrite_pattern` 直接匹配 `NnCastOp`。
    - 复用 `_lower_cast_op(...)`，保持现有 IR 输出与错误短语不变。

    使用示例:
    - pattern = _LowerCastPattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/select_cast_lowering.md
    - test: test/pass/nn_lowering/cast.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnCastOp, rewriter: PatternRewriter, /) -> None:
        block = op.parent_block()
        if block is None:
            raise NnLoweringError("nn op must be inside a block")
        ensure_expected_op_name(op, "nn.cast")
        _lower_cast_op(op, block)
        rewriter.has_done_action = True


class _LowerExpPattern(RewritePattern):
    """将单个 nn.exp lowering 为 kernel.exp。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 通过 `@op_type_rewrite_pattern` 直接匹配 `NnExpOp`。
    - 保持既有注册位置与 lowering 输出不变；reduce/softmax family 后续阶段可继续收口边界。

    使用示例:
    - pattern = _LowerExpPattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/select_cast_lowering.md
    - test: test/pass/nn_lowering/exp.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnExpOp, rewriter: PatternRewriter, /) -> None:
        block = op.parent_block()
        if block is None:
            raise NnLoweringError("nn op must be inside a block")
        ensure_expected_op_name(op, "nn.exp")
        _lower_exp_op(op, block)
        rewriter.has_done_action = True


def select_cast_patterns() -> list[RewritePattern]:
    """返回 select/cast/exp 的 rewrite pattern 集合。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 以单 op pattern 方式承载 nn.select / nn.cast / nn.exp lowering。
    - 供 nn_lowering 主 orchestrator 组装使用。

    使用示例:
    - patterns = select_cast_patterns()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/select_cast_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
    """

    return [_LowerSelectPattern(), _LowerCastPattern(), _LowerExpPattern()]


def lower_select_cast_family(block: Block, op: Operation) -> bool:
    """执行 select/cast family lowering。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 处理 nn.select、nn.cast 与 nn.exp。
    - 成功处理返回 True；非本 family op 返回 False。

    使用示例:
    - handled = lower_select_cast_family(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/select.py
    - test: test/pass/nn_lowering/cast.py
    - test: test/pass/nn_lowering/exp.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
    """

    if isinstance(op, NnSelectOp):
        ensure_expected_op_name(op, "nn.select")
        _lower_select_op(op, block)
        return True
    if isinstance(op, NnCastOp):
        ensure_expected_op_name(op, "nn.cast")
        _lower_cast_op(op, block)
        return True
    if isinstance(op, NnExpOp):
        ensure_expected_op_name(op, "nn.exp")
        _lower_exp_op(op, block)
        return True
    return False


__all__ = ["lower_select_cast_family", "select_cast_patterns"]
