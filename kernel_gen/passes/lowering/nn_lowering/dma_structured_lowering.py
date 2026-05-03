"""dma_structured lowering 实现。


功能说明:
- 负责 nn.broadcast / nn.transpose 的 lowering。
- 输出 memory 通过 dma.alloc 创建，并由 dma.* op 写入。
- surviving 模块级接口为 `dma_structured_patterns()`。

API 列表:
- `dma_structured_patterns() -> list[RewritePattern]`

使用示例:
- from kernel_gen.passes.lowering.nn_lowering.dma_structured_lowering import dma_structured_patterns
- patterns = dma_structured_patterns()

关联文件:
- spec: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
- test: test/passes/lowering/nn_lowering/test_nn_lowering.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
"""

from __future__ import annotations
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

from xdsl.dialects.builtin import ArrayAttr, IntAttr, IntegerAttr, IntegerType, StringAttr
from xdsl.ir import Attribute, Block, Operation, SSAValue
from xdsl.pattern_rewriter import PatternRewriter, RewritePattern, op_type_rewrite_pattern

from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp, DmaTransposeOp
from kernel_gen.dialect.nn import NnBroadcastOp, NnMemoryType, NnTransposeOp
from kernel_gen.dialect.symbol import SymbolGetDimOp, SymbolValueType
from .nn_lowering_utility import ensure_single_result


def _find_block_symbol_dim(block: Block, dim: str, before_op: Operation | None = None) -> SSAValue | None:
    """查找当前 block 中可直接复用的 symbol 维度参数。


    功能说明:
    - 在 block 参数中查找公开值等于 `dim` 的 `!symbol.int<"...">`。
    - 在 `before_op` 之前查找同一 block 已生成的符号 SSA 值。
    - 用于支持 `[1, N] -> [M, N]` 这类复用已有动态维度的 broadcast。

    使用示例:
    - symbol_value = _find_block_symbol_dim(block, "M", before_op=op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/passes/lowering/nn_lowering/test_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
    """

    for arg in block.args:
        if isinstance(arg.type, SymbolValueType) and arg.type.get_value() == dim:
            return arg
    for item in block.ops:
        if before_op is not None and item is before_op:
            break
        for result in item.results:
            if isinstance(result.type, SymbolValueType) and result.type.get_value() == dim:
                return result
    return None


def _ensure_symbol_or_int(op: Operation, operand: SSAValue | Operation) -> SSAValue:
    """确保 operand 为 symbol.int 或 IntegerType。


    功能说明:
    - 支持 symbol.int 或 IntegerType。

    使用示例:
    - value = _ensure_symbol_or_int(op, operand)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
    - test: test/passes/lowering/nn_lowering/test_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
    """

    if isinstance(operand, Operation):
        operand = operand.results[0]
    if isinstance(operand.type, SymbolValueType):
        return operand
    if isinstance(operand.type, IntegerType):
        return operand
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "broadcast scalar must be int or symbol")


def _get_symbol_dim_from_source(
    block: Block,
    op: Operation,
    axis: int,
    result_shape: list[int | str],
    operand: SSAValue,
    operand_shape: list[int | str],
) -> SSAValue:
    """获取 broadcast 结果动态维度的 SSA 值。


    功能说明:
    - 使用 SymbolGetDimOp 从 operand 上读取来自 source 的动态维度。
    - 支持 result 维度与 source 维度直接匹配或通过 result dim 在 operand_shape 中索引。
    - 当 source 对齐维为 1 时，允许 result 新符号维来自当前 block 参数或当前 op 之前已生成的 symbol SSA 值。
    - 匹配失败时抛出稳定错误短语。

    使用示例:
    - _get_symbol_dim_from_source(block, op, idx, result_shape, operand, operand_shape)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
    - test: test/passes/lowering/nn_lowering/test_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
    """

    axis_offset = len(result_shape) - len(operand_shape)
    source_axis = axis - axis_offset
    result_dim = result_shape[axis]
    if not isinstance(result_dim, str):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "NnLoweringBroadcastSymbolDimNotFromSource: result dim is not symbolic")
    if source_axis < 0 or source_axis >= len(operand_shape):
        if result_dim in operand_shape:
            source_axis = operand_shape.index(result_dim)
            symbol_op = SymbolGetDimOp(operand, IntAttr(source_axis))
            block.insert_op_before(symbol_op, op)
            return symbol_op.result
        block_symbol = _find_block_symbol_dim(block, result_dim, before_op=op)
        if block_symbol is not None:
            return block_symbol
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "NnLoweringBroadcastSymbolDimNotFromSource: axis out of range")
    source_dim = operand_shape[source_axis]
    if isinstance(source_dim, str) and source_dim == result_dim:
        symbol_op = SymbolGetDimOp(operand, IntAttr(source_axis))
        block.insert_op_before(symbol_op, op)
        return symbol_op.result
    if result_dim in operand_shape:
        source_axis = operand_shape.index(result_dim)
        symbol_op = SymbolGetDimOp(operand, IntAttr(source_axis))
        block.insert_op_before(symbol_op, op)
        return symbol_op.result
    if source_dim == 1:
        block_symbol = _find_block_symbol_dim(block, result_dim, before_op=op)
        if block_symbol is not None:
            return block_symbol
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "NnLoweringBroadcastSymbolDimNotFromSource: result dim not in source")
    if not isinstance(source_dim, str):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "NnLoweringBroadcastSymbolDimNotFromSource: source dim is not symbolic")
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "NnLoweringBroadcastSymbolDimNotFromSource: symbol mismatch")


def _broadcast_shape_value(dim: Attribute) -> int | str:
    """读取 broadcast shape 维度值。


    功能说明:
    - 统一支持 `StringAttr`、`IntAttr` 与 `IntegerAttr`。

    使用示例:
    - _broadcast_shape_value(IntAttr(4))

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
    - test: test/passes/lowering/nn_lowering/test_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
    """

    if isinstance(dim, StringAttr):
        return dim.data
    if isinstance(dim, IntAttr):
        return dim.data
    if isinstance(dim, IntegerAttr):
        return dim.value.data
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn.broadcast shape must be IntAttr or StringAttr")


def _ensure_broadcast_shape(
    op: Operation,
    result_type: NnMemoryType,
    operand_type: NnMemoryType,
) -> tuple[list[int | str], list[int | str]]:
    """校验 nn.broadcast 的 shape 合法性。


    功能说明:
    - 校验 operand 与 result shape 兼容。

    使用示例:
    - result_shape, operand_shape = _ensure_broadcast_shape(op, result_type, operand_type)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
    - test: test/passes/lowering/nn_lowering/test_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
    """

    if not isinstance(result_type, NnMemoryType):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn.broadcast result must be nn.memory")
    if not isinstance(operand_type, NnMemoryType):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn.broadcast operand must be nn.memory")

    result_shape = [_broadcast_shape_value(dim) for dim in result_type.shape.data]
    operand_shape = [_broadcast_shape_value(dim) for dim in operand_type.shape.data]

    if len(result_shape) < len(operand_shape):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn.broadcast result rank must be >= operand rank")

    for dim in operand_shape:
        if isinstance(dim, str) and dim == "?":
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn.broadcast operand shape must not contain '?'")

    return result_shape, operand_shape


def _ensure_broadcast_compat(result_shape: list[int | str], operand_shape: list[int | str]) -> None:
    """校验 nn.broadcast 的 shape 兼容性。


    功能说明:
    - 按尾维对齐规则检查 operand/result 维度。
    - 对静态数值不匹配报错，对非法符号扩张由动态维度解析阶段报错。
    - 允许 operand_dim=1 且 result_dim 为符号维，后续会要求该符号来自 source 或 block 参数。

    使用示例:
    - _ensure_broadcast_compat(result_shape, operand_shape)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
    - test: test/passes/lowering/nn_lowering/test_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
    """

    axis_offset = len(result_shape) - len(operand_shape)
    for idx, operand_dim in enumerate(operand_shape):
        result_dim = result_shape[idx + axis_offset]
        if isinstance(operand_dim, int):
            if isinstance(result_dim, int):
                if operand_dim != 1 and operand_dim != result_dim:
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "invalid broadcast target shape")
                continue
            if operand_dim == 1 and isinstance(result_dim, str):
                continue
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "NnLoweringBroadcastSymbolDimNotFromSource: result dim not in source")
        if isinstance(result_dim, str):
            if operand_dim != result_dim:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "NnLoweringBroadcastSymbolDimNotFromSource: symbol mismatch")
            continue
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "invalid broadcast target shape")


def _lower_broadcast(block: Block, op: Operation) -> None:
    """lower nn.broadcast。


    功能说明:
    - 允许动态 shape，并使用 symbol.get_dim。
    - 对重复符号维度进行缓存，避免重复生成 symbol.get_dim。
    - 先创建 dma.alloc，再调用 dma.broadcast。

    使用示例:
    - _lower_broadcast(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
    - test: test/passes/lowering/nn_lowering/test_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
    """

    result_type = ensure_single_result(op)
    if len(op.operands) == 2:
        _ensure_symbol_or_int(op, op.operands[1])
    elif len(op.operands) != 1:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"{op.name} must have 1 operands")
    operand = op.operands[0]
    if not isinstance(operand.type, NnMemoryType):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn.broadcast operand must be nn.memory")

    result_shape, operand_shape = _ensure_broadcast_shape(op, result_type, operand.type)
    _ensure_broadcast_compat(result_shape, operand_shape)
    if any(isinstance(dim, str) for dim in result_shape):
        symbol_dims: list[SSAValue] = []
        cached_symbols: dict[str, SSAValue] = {}
        for idx, dim in enumerate(result_shape):
            if isinstance(dim, str):
                cached = cached_symbols.get(dim)
                if cached is None:
                    cached = _get_symbol_dim_from_source(
                        block,
                        op,
                        idx,
                        result_shape,
                        operand,
                        operand_shape,
                    )
                    cached_symbols[dim] = cached
                symbol_dims.append(cached)
        alloc = DmaAllocOp(symbol_dims, result_type)
    else:
        alloc = DmaAllocOp([], result_type)

    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = DmaBroadcastOp(result, operand)
    block.insert_op_before(lowered, op)
    op.results[0].replace_all_uses_with(result)
    block.erase_op(op)


def _lower_transpose(block: Block, op: Operation) -> None:
    """lower nn.transpose。


    功能说明:
    - 校验 perm / shape / stride。
    - 若含符号维度，使用 symbol.get_dim 生成 dma.alloc 的 dynamic_shape。
    - 先创建 dma.alloc，再调用 dma.transpose。

    使用示例:
    - _lower_transpose(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
    - test: test/passes/lowering/nn_lowering/test_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
    """

    result_type = ensure_single_result(op)
    operand = op.operands[0]
    if not isinstance(operand.type, NnMemoryType):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn.transpose operand must be nn.memory")
    perm_attr = op.attributes.get("perm")
    if not isinstance(perm_attr, ArrayAttr):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn.transpose perm must be ArrayAttr")
    perm = perm_attr.data
    if len(perm) != len(result_type.shape.data):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn.transpose perm rank mismatch")
    symbol_dims: list[SSAValue] = []
    symbol_map: dict[str, SSAValue] = {}
    for axis, dim in enumerate(operand.type.shape.data):
        if isinstance(dim, StringAttr):
            if dim.data == "?":
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn.transpose operand shape must not contain '?'")
            symbol_op = SymbolGetDimOp(operand, IntAttr(axis))
            block.insert_op_before(symbol_op, op)
            symbol_map[dim.data] = symbol_op.result
    for dim in result_type.shape.data:
        if isinstance(dim, StringAttr):
            symbol_value = symbol_map.get(dim.data)
            if symbol_value is None:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn.transpose result dim not in source")
            symbol_dims.append(symbol_value)
    alloc = DmaAllocOp(symbol_dims, result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = DmaTransposeOp(result, operand, perm_attr)
    block.insert_op_before(lowered, op)
    op.results[0].replace_all_uses_with(result)
    block.erase_op(op)
class _LowerNnBroadcastPattern(RewritePattern):
    """将单个 nn.broadcast lowering 为 dma.broadcast。


    功能说明:
    - 只匹配 NnBroadcastOp，避免 family 级 op.name 分派。
    - 复用现有 broadcast helper，保持 IR 输出与校验语义不变。

    使用示例:
    - pattern = _LowerNnBroadcastPattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
    - test: test/passes/lowering/nn_lowering/test_public_name.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnBroadcastOp, rewriter: PatternRewriter) -> None:
        block = op.parent_block()
        if block is None:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn op must be inside a block")
        _lower_broadcast(block, op)
        rewriter.has_done_action = True


class _LowerNnTransposePattern(RewritePattern):
    """将单个 nn.transpose lowering 为 dma.transpose。


    功能说明:
    - 只匹配 NnTransposeOp，避免 family 级 op.name 分派。
    - 复用现有 transpose helper，保持 IR 输出与校验语义不变。

    使用示例:
    - pattern = _LowerNnTransposePattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
    - test: test/passes/lowering/nn_lowering/test_public_name.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnTransposeOp, rewriter: PatternRewriter) -> None:
        block = op.parent_block()
        if block is None:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn op must be inside a block")
        _lower_transpose(block, op)
        rewriter.has_done_action = True


def dma_structured_patterns() -> list[RewritePattern]:
    """返回 dma structured rewrite pattern 集合。


    功能说明:
    - 提供 nn_lowering 主 driver 的单 op pattern 注册入口。
    - 每个 pattern 只匹配一个具体 nn op，不再保留 family pattern 名称分派。

    使用示例:
    - patterns = dma_structured_patterns()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
    - test: test/passes/lowering/nn_lowering/test_public_name.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
    """

    return [_LowerNnBroadcastPattern(), _LowerNnTransposePattern()]


__all__ = ["dma_structured_patterns"]
