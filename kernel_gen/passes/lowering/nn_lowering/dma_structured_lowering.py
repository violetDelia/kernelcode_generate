"""dma_structured lowering 实现。

创建者: 小李飞刀
最后一次更改: jcc你莫辜负

功能说明:
- 负责 nn.broadcast / nn.transpose 的 lowering。
- 输出 memory 通过 dma.alloc 创建，并由 dma.* op 写入。

使用示例:
- from kernel_gen.passes.lowering.nn_lowering.dma_structured_lowering import lower_dma_structured_family
- lower_dma_structured_family(block, op)

关联文件:
- spec: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
- test: test/pass/nn_lowering/test_lowering_nn_lowering.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
"""

from __future__ import annotations

from xdsl.dialects.builtin import ArrayAttr, IntAttr, IntegerAttr, IntegerType, StringAttr
from xdsl.ir import Attribute, Block, Operation, SSAValue
from xdsl.pattern_rewriter import PatternRewriter, RewritePattern, op_type_rewrite_pattern

from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp, DmaTransposeOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolGetDimOp, SymbolValueType
from .nn_lowering_utility import NnLoweringError, ensure_single_result


_DMA_STRUCTURED_OP_NAMES = {"nn.broadcast", "nn.transpose"}


def _ensure_symbol_or_int(op: Operation, operand: SSAValue | Operation) -> SSAValue:
    """确保 operand 为 symbol.int 或 IntegerType。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 symbol.int 或 IntegerType。

    使用示例:
    - value = _ensure_symbol_or_int(op, operand)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
    """

    if isinstance(operand, Operation):
        operand = operand.results[0]
    if isinstance(operand.type, SymbolValueType):
        return operand
    if isinstance(operand.type, IntegerType):
        return operand
    raise NnLoweringError("broadcast scalar must be int or symbol")


def _get_symbol_dim_from_source(
    block: Block,
    op: Operation,
    axis: int,
    result_shape: list[int | str],
    operand: SSAValue,
    operand_shape: list[int | str],
) -> SymbolGetDimOp:
    """从 operand 的 symbol dim 提取维度。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 使用 SymbolGetDimOp 从 operand 上读取动态维度。
    - 支持 result 维度与 source 维度直接匹配或通过 result dim 在 operand_shape 中索引。
    - 匹配失败时抛出稳定错误短语。

    使用示例:
    - _get_symbol_dim_from_source(block, op, idx, result_shape, operand, operand_shape)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
    """

    axis_offset = len(result_shape) - len(operand_shape)
    source_axis = axis - axis_offset
    if source_axis < 0 or source_axis >= len(operand_shape):
        raise NnLoweringError("NnLoweringBroadcastSymbolDimNotFromSource: axis out of range")
    source_dim = operand_shape[source_axis]
    result_dim = result_shape[axis]
    if isinstance(source_dim, str) and source_dim == result_dim:
        symbol_op = SymbolGetDimOp(operand, IntAttr(source_axis))
        block.insert_op_before(symbol_op, op)
        return symbol_op
    if isinstance(result_dim, str) and result_dim in operand_shape:
        source_axis = operand_shape.index(result_dim)
        symbol_op = SymbolGetDimOp(operand, IntAttr(source_axis))
        block.insert_op_before(symbol_op, op)
        return symbol_op
    if not isinstance(source_dim, str):
        raise NnLoweringError("NnLoweringBroadcastSymbolDimNotFromSource: source dim is not symbolic")
    raise NnLoweringError("NnLoweringBroadcastSymbolDimNotFromSource: symbol mismatch")


def _ensure_broadcast_shape(
    op: Operation,
    result_type: NnMemoryType,
    operand_type: NnMemoryType,
) -> tuple[list[int | str], list[int | str]]:
    """校验 nn.broadcast 的 shape 合法性。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 校验 operand 与 result shape 兼容。

    使用示例:
    - result_shape, operand_shape = _ensure_broadcast_shape(op, result_type, operand_type)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
    """

    if not isinstance(result_type, NnMemoryType):
        raise NnLoweringError("nn.broadcast result must be nn.memory")
    if not isinstance(operand_type, NnMemoryType):
        raise NnLoweringError("nn.broadcast operand must be nn.memory")

    def _shape_value(dim: Attribute) -> int | str:
        if isinstance(dim, StringAttr):
            return dim.data
        if isinstance(dim, IntAttr):
            return dim.data
        if isinstance(dim, IntegerAttr):
            return dim.value.data
        raise NnLoweringError("nn.broadcast shape must be IntAttr or StringAttr")

    result_shape = [_shape_value(dim) for dim in result_type.shape.data]
    operand_shape = [_shape_value(dim) for dim in operand_type.shape.data]

    if len(result_shape) < len(operand_shape):
        raise NnLoweringError("nn.broadcast result rank must be >= operand rank")

    for dim in operand_shape:
        if isinstance(dim, str) and dim == "?":
            raise NnLoweringError("nn.broadcast operand shape must not contain '?'")

    return result_shape, operand_shape


def _ensure_broadcast_compat(result_shape: list[int | str], operand_shape: list[int | str]) -> None:
    """校验 nn.broadcast 的 shape 兼容性。

    创建者: 小李飞刀
    最后一次更改: jcc你莫辜负

    功能说明:
    - 按尾维对齐规则检查 operand/result 维度。
    - 对静态数值不匹配报错，对非法符号扩张报错。
    - 允许 operand_dim=1 且 result_dim 为 operand_shape 中的符号维。

    使用示例:
    - _ensure_broadcast_compat(result_shape, operand_shape)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
    """

    axis_offset = len(result_shape) - len(operand_shape)
    for idx in range(axis_offset):
        dim = result_shape[idx]
        if isinstance(dim, str):
            raise NnLoweringError("NnLoweringBroadcastSymbolDimNotFromSource: new symbol dim")
    for idx, operand_dim in enumerate(operand_shape):
        result_dim = result_shape[idx + axis_offset]
        if isinstance(operand_dim, int):
            if isinstance(result_dim, int):
                if operand_dim != 1 and operand_dim != result_dim:
                    raise NnLoweringError("invalid broadcast target shape")
                continue
            if operand_dim == 1 and isinstance(result_dim, str) and result_dim in operand_shape:
                continue
            raise NnLoweringError("NnLoweringBroadcastSymbolDimNotFromSource: result dim not in source")
        if isinstance(result_dim, str):
            if operand_dim != result_dim:
                raise NnLoweringError("NnLoweringBroadcastSymbolDimNotFromSource: symbol mismatch")
            continue
        raise NnLoweringError("invalid broadcast target shape")


def _lower_broadcast(block: Block, op: Operation) -> None:
    """lower nn.broadcast。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 允许动态 shape，并使用 symbol.get_dim。
    - 对重复符号维度进行缓存，避免重复生成 symbol.get_dim。
    - 先创建 dma.alloc，再调用 dma.broadcast。

    使用示例:
    - _lower_broadcast(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
    """

    result_type = ensure_single_result(op)
    if len(op.operands) == 2:
        _ensure_symbol_or_int(op, op.operands[1])
    elif len(op.operands) != 1:
        raise NnLoweringError(f"{op.name} must have 1 operands")
    operand = op.operands[0]
    if not isinstance(operand.type, NnMemoryType):
        raise NnLoweringError("nn.broadcast operand must be nn.memory")

    result_shape, operand_shape = _ensure_broadcast_shape(op, result_type, operand.type)
    _ensure_broadcast_compat(result_shape, operand_shape)
    if any(isinstance(dim, str) for dim in result_shape):
        symbol_dims: list[SSAValue] = []
        cached_symbols: dict[str, SSAValue] = {}
        for idx, dim in enumerate(result_shape):
            if isinstance(dim, str):
                cached = cached_symbols.get(dim)
                if cached is None:
                    symbol_op = _get_symbol_dim_from_source(
                        block,
                        op,
                        idx,
                        result_shape,
                        operand,
                        operand_shape,
                    )
                    cached = symbol_op.result
                    cached_symbols[dim] = cached
                symbol_dims.append(cached)
        alloc = DmaAllocOp(symbol_dims, result_type)
    else:
        alloc = DmaAllocOp([], result_type)

    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = DmaBroadcastOp(result, operand)
    block.insert_op_before(lowered, op)
    op.results[0].replace_by(result)
    block.erase_op(op)


def _lower_transpose(block: Block, op: Operation) -> None:
    """lower nn.transpose。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 校验 perm / shape / stride。
    - 若含符号维度，使用 symbol.get_dim 生成 dma.alloc 的 dynamic_shape。
    - 先创建 dma.alloc，再调用 dma.transpose。

    使用示例:
    - _lower_transpose(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
    """

    result_type = ensure_single_result(op)
    operand = op.operands[0]
    if not isinstance(operand.type, NnMemoryType):
        raise NnLoweringError("nn.transpose operand must be nn.memory")
    perm_attr = op.attributes.get("perm")
    if not isinstance(perm_attr, ArrayAttr):
        raise NnLoweringError("nn.transpose perm must be ArrayAttr")
    perm = perm_attr.data
    if len(perm) != len(result_type.shape.data):
        raise NnLoweringError("nn.transpose perm rank mismatch")
    symbol_dims: list[SSAValue] = []
    symbol_map: dict[str, SSAValue] = {}
    for axis, dim in enumerate(operand.type.shape.data):
        if isinstance(dim, StringAttr):
            if dim.data == "?":
                raise NnLoweringError("nn.transpose operand shape must not contain '?'")
            symbol_op = SymbolGetDimOp(operand, IntAttr(axis))
            block.insert_op_before(symbol_op, op)
            symbol_map[dim.data] = symbol_op.result
    for dim in result_type.shape.data:
        if isinstance(dim, StringAttr):
            symbol_value = symbol_map.get(dim.data)
            if symbol_value is None:
                raise NnLoweringError("nn.transpose result dim not in source")
            symbol_dims.append(symbol_value)
    alloc = DmaAllocOp(symbol_dims, result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = DmaTransposeOp(result, operand, perm_attr)
    block.insert_op_before(lowered, op)
    op.results[0].replace_by(result)
    block.erase_op(op)


def lower_dma_structured_family(block: Block, op: Operation) -> bool:
    """执行 dma_structured family lowering。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅处理 nn.broadcast / nn.transpose。
    - 成功处理返回 True；非本 family op 返回 False。

    使用示例:
    - handled = lower_dma_structured_family(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
    """

    if op.name == "nn.broadcast":
        _lower_broadcast(block, op)
        return True
    if op.name == "nn.transpose":
        _lower_transpose(block, op)
        return True
    return False


class _LowerDmaStructuredFamilyPattern(RewritePattern):
    """将 dma structured family 交给当前 family helper 改写。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 作为 S1 pattern driver 的 dma structured family 入口。
    - 仅处理 nn.broadcast / nn.transpose，保持既有输出不变。

    使用示例:
    - pattern = _LowerDmaStructuredFamilyPattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
    - test: test/pass/nn_lowering/public_name.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter) -> None:
        if op.name not in _DMA_STRUCTURED_OP_NAMES:
            return
        block = op.parent_block()
        if block is None:
            raise NnLoweringError("nn op must be inside a block")
        lower_dma_structured_family(block, op)
        rewriter.has_done_action = True


def dma_structured_patterns() -> list[RewritePattern]:
    """返回 dma structured rewrite pattern 集合。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 提供 nn_lowering 主 driver 的 family pattern 注册入口。
    - S1 阶段保持 family helper 复用，后续阶段可替换为单 op pattern。

    使用示例:
    - patterns = dma_structured_patterns()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
    - test: test/pass/nn_lowering/public_name.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
    """

    return [_LowerDmaStructuredFamilyPattern()]


__all__ = ["dma_structured_patterns", "lower_dma_structured_family"]
