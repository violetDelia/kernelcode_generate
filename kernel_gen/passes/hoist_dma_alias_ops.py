"""hoist-dma-alias-ops pass.

功能说明:
- 提供 `hoist-dma-alias-ops` pass。
- `DmaAliasThroughWriteNoReadPattern` 统一处理 alias 穿过 write-only / no-read writer，
  并把 writer target 改为 alias result。
- `DmaAliasHoistPattern` 统一处理 NoMemoryEffect alias descriptor 的纯外提；纯外提路径不改写 writer target。
- `DmaAliasHoistPattern` 同时在既有公开 pattern 框架内删除 broadcast source 的 leading-unit
  `dma.reinterpret`，并把相关 writer target / broadcast source 改回 flat source。
- 第一版 alias 范围为 `dma.reshape`、`dma.view` 与 `dma.reinterpret`。
- 不保留旧 `view + deslice` 连续维度分组，也不保留旧单 op pattern 兼容入口。

API 列表:
- `class DmaAliasThroughWriteNoReadPattern(module: ModuleOp)`
- `DmaAliasThroughWriteNoReadPattern.match_and_rewrite(op: Operation, rewriter: PatternRewriter) -> None`
- `class DmaAliasHoistPattern(module: ModuleOp)`
- `DmaAliasHoistPattern.match_and_rewrite(op: Operation, rewriter: PatternRewriter) -> None`
- `get_hoist_dma_alias_ops_pass_patterns(module: ModuleOp) -> list[RewritePattern]`
- `class HoistDmaAliasOpsPass(fold: bool = True)`
- `HoistDmaAliasOpsPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from xdsl.context import Context
- from kernel_gen.passes.hoist_dma_alias_ops import HoistDmaAliasOpsPass
- HoistDmaAliasOpsPass().apply(Context(), module)

关联文件:
- spec: [spec/pass/hoist_dma_alias_ops.md](spec/pass/hoist_dma_alias_ops.md)
- test: [test/passes/test_hoist_dma_alias_ops.py](test/passes/test_hoist_dma_alias_ops.py)
- 功能实现: [kernel_gen/passes/hoist_dma_alias_ops.py](kernel_gen/passes/hoist_dma_alias_ops.py)
"""

from __future__ import annotations

from collections.abc import Sequence

from xdsl.context import Context
from xdsl.dialects.builtin import ArrayAttr, IntegerType, ModuleOp
from xdsl.ir import Attribute, Block, BlockArgument, Operation, SSAValue
from xdsl.pattern_rewriter import GreedyRewritePatternApplier, PatternRewriter, PatternRewriteWalker, RewritePattern
from xdsl.rewriter import InsertPoint
from xdsl.traits import MemoryEffectKind, get_effects

from kernel_gen.dialect.dma import DmaBroadcastOp, DmaReinterpretOp, DmaReshapeOp, DmaViewOp
from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr, SymbolForOp, SymbolValueType
from kernel_gen.passes.common import ensure_builtin_module, verify_generated_ops
from kernel_gen.passes.pass_manager import Pass


def _same_value(candidate: SSAValue | Operation, value: SSAValue | Operation) -> bool:
    """判断两个 operand / result 是否指向同一个 SSA value。

    功能说明:
    - 统一处理 xDSL operand 可能传入 `Operation` 或 `SSAValue` 的形态。

    使用示例:
    - if _same_value(writer.operands[0], alias.source): ...
    """

    return SSAValue.get(candidate) is SSAValue.get(value)


def _value_dominates_op(value: SSAValue, op: Operation) -> bool:
    """判断 value 是否在 op 之前可见。

    功能说明:
    - 接受同 block 中位于 `op` 之前的 operation result。
    - 接受当前 block 或 ancestor block 的 block argument。
    - 对 sibling / descendant region 中的 value 保守返回 False。

    使用示例:
    - if all(_value_dominates_op(operand, writer) for operand in alias.operands): ...
    """

    op_block = op.parent_block()
    if op_block is None:
        return False
    if isinstance(value, BlockArgument):
        return value.owner is op_block or value.owner.is_ancestor(op)
    owner = value.owner
    if not isinstance(owner, Operation):
        return True
    owner_block = owner.parent_block()
    if owner_block is None:
        return True
    if owner_block is op_block:
        return owner.is_before_in_block(op)
    ancestor = owner_block.find_ancestor_op_in_block(op)
    if ancestor is None or owner is ancestor:
        return False
    return owner.is_before_in_block(ancestor)


def _memory_type_of(value: SSAValue | Operation) -> NnMemoryType | None:
    """读取 SSA value 的公开 `NnMemoryType`。

    功能说明:
    - 非 memory value 返回 `None`，供 pass 保守 no-op。

    使用示例:
    - source_type = _memory_type_of(alias.source)
    """

    value_type = SSAValue.get(value).type
    return value_type if isinstance(value_type, NnMemoryType) else None


def _symbol_expr_attrs(attrs: ArrayAttr[Attribute]) -> tuple[SymbolExprAttr, ...] | None:
    """把 ArrayAttr 规整为 `SymbolExprAttr` tuple。

    功能说明:
    - 当前 rewrite 只接受结构化 `SymbolExprAttr` 布局。
    - 任一元素不是 `SymbolExprAttr` 时返回 `None`，避免文本 fallback。

    使用示例:
    - shape_attrs = _symbol_expr_attrs(memory_type.shape)
    """

    result: list[SymbolExprAttr] = []
    for attr in attrs.data:
        if not isinstance(attr, SymbolExprAttr):
            return None
        result.append(attr)
    return tuple(result)


def _symbol_expr_text(attr: SymbolExprAttr) -> str:
    """返回结构化 SymbolExprAttr 的 canonical 表达式文本。

    功能说明:
    - 只读取 `SymbolExprAttr` 自身公开承载的 canonical 文本。

    使用示例:
    - expr = _symbol_expr_text(SymbolExprAttr.from_expr("N*K"))
    """

    return attr.expr.data


def _same_symbol_attrs(left: Sequence[SymbolExprAttr], right: Sequence[SymbolExprAttr]) -> bool:
    """判断两组 SymbolExprAttr 是否逐项 exact 相等。

    功能说明:
    - 结构化 equality 是本 pass 的唯一 layout 证明来源。
    - 不使用 name_hint、dump 文本或额外代数化简 fallback。

    使用示例:
    - if _same_symbol_attrs(source_shape, result_shape): ...
    """

    return len(left) == len(right) and all(left_item == right_item for left_item, right_item in zip(left, right, strict=True))


def _factor_expr(expr: str) -> str:
    """为乘法拼接准备单个表达式 factor。

    功能说明:
    - 对复杂表达式加括号，交给 `SymbolExprAttr.from_expr(...)` 做 canonical 化。

    使用示例:
    - factor = _factor_expr("N+1")
    """

    if expr.lstrip("-").isdigit() or expr.replace("_", "").isalnum() or expr == "?":
        return expr
    return f"({expr})"


def _product_expr_attr(attrs: Sequence[SymbolExprAttr]) -> SymbolExprAttr:
    """构造一组维度的乘积表达式属性。

    功能说明:
    - 乘积按维度顺序生成，最终由 `SymbolExprAttr` canonical 化。
    - 空乘积返回 `1`，用于 contiguous stride 推导。

    使用示例:
    - attr = _product_expr_attr((SymbolExprAttr.from_expr("M"), SymbolExprAttr.from_expr("N")))
    """

    if not attrs:
        return SymbolExprAttr.from_expr("1")
    expr = _symbol_expr_text(attrs[0])
    for attr in attrs[1:]:
        expr = f"{_factor_expr(expr)}*{_factor_expr(_symbol_expr_text(attr))}"
    return SymbolExprAttr.from_expr(expr)


def _contiguous_stride_attrs(shape_attrs: Sequence[SymbolExprAttr]) -> tuple[SymbolExprAttr, ...]:
    """根据 shape 构造行主序 contiguous stride。

    功能说明:
    - 与 `NnMemoryType` 的公开 contiguous 语义保持一致。

    使用示例:
    - strides = _contiguous_stride_attrs(shape_attrs)
    """

    return tuple(_product_expr_attr(shape_attrs[index + 1 :]) for index in range(len(shape_attrs)))


def _is_contiguous_memory_type(memory_type: NnMemoryType) -> bool:
    """判断 memory type 是否是行主序 contiguous。

    功能说明:
    - 只基于 `NnMemoryType.shape/stride` 的 `SymbolExprAttr` 结构化布局判断。

    使用示例:
    - if not _is_contiguous_memory_type(memory_type): return False
    """

    shape_attrs = _symbol_expr_attrs(memory_type.shape)
    stride_attrs = _symbol_expr_attrs(memory_type.stride)
    if shape_attrs is None or stride_attrs is None:
        return False
    return _same_symbol_attrs(stride_attrs, _contiguous_stride_attrs(shape_attrs))


def _is_i8_byte_pool_memory_type(memory_type: NnMemoryType) -> bool:
    """判断 memory type 是否是一维 i8 byte pool。

    功能说明:
    - P2 对 byte-pool dtype-changing reinterpret 保守 no-op。
    - 判定仅使用公开 `NnMemoryType` 字段，不调用 dma package 内部 helper。

    使用示例:
    - if _is_i8_byte_pool_memory_type(source_type): return False
    """

    shape_attrs = _symbol_expr_attrs(memory_type.shape)
    stride_attrs = _symbol_expr_attrs(memory_type.stride)
    element_type = memory_type.element_type
    return (
        shape_attrs is not None
        and stride_attrs == (SymbolExprAttr.from_expr("1"),)
        and len(shape_attrs) == 1
        and isinstance(element_type, IntegerType)
        and int(element_type.width.data) == 8
    )


def _symbol_value_expr_attr(value: SSAValue | Operation) -> SymbolExprAttr | None:
    """读取 symbol/int operand 的结构化表达式属性。

    功能说明:
    - 仅接受 `SymbolValueType`。
    - `symbol.iter` 或其它类型不参与 full-cover 证明，保持 no-op。

    使用示例:
    - expr_attr = _symbol_value_expr_attr(size)
    """

    value_type = SSAValue.get(value).type
    return value_type.expr if isinstance(value_type, SymbolValueType) else None


def _symbol_value_matches_attr(value: SSAValue | Operation, attr: SymbolExprAttr) -> bool:
    """判断 symbol operand 的类型表达式是否等于目标属性。

    功能说明:
    - 等价关系只来自公开 `SymbolValueType` 与 `SymbolExprAttr` 的结构化参数。

    使用示例:
    - if _symbol_value_matches_attr(size, result_shape_attr): ...
    """

    value_attr = _symbol_value_expr_attr(value)
    return value_attr == attr


def _symbol_value_is_expr(value: SSAValue | Operation, expr: str) -> bool:
    """判断 symbol operand 是否等于指定常量表达式。

    功能说明:
    - 用于校验 offset 为 0、stride 为 1 等公开整数边界。

    使用示例:
    - if _symbol_value_is_expr(offset, "0"): ...
    """

    return _symbol_value_matches_attr(value, SymbolExprAttr.from_expr(expr))


def _symbol_operands_match_attrs(values: Sequence[SSAValue], attrs: Sequence[SymbolExprAttr]) -> bool:
    """判断一组 symbol operands 是否逐项匹配目标表达式。

    功能说明:
    - 只做同长度逐项精确匹配。
    - 任一 operand 类型不是 `SymbolValueType` 时返回 False。

    使用示例:
    - if _symbol_operands_match_attrs(alias.shape, result_shape_attrs): ...
    """

    if len(values) != len(attrs):
        return False
    return all(_symbol_value_matches_attr(value, attr) for value, attr in zip(values, attrs, strict=True))


def _same_space_and_element_type(source_type: NnMemoryType, result_type: NnMemoryType) -> bool:
    """判断 alias source/result 是否保持同 space 与 element type。

    功能说明:
    - P2 through-write retarget 只允许物理 index set 等价的 alias。
    - byte-pool reinterpret 这类 dtype-changing 形态由调用方单独 no-op。

    使用示例:
    - if not _same_space_and_element_type(source_type, result_type): return False
    """

    return source_type.space.space.data == result_type.space.space.data and source_type.element_type == result_type.element_type


def _memory_numel_attr(memory_type: NnMemoryType) -> SymbolExprAttr | None:
    """返回 memory shape 的元素总数表达式。

    功能说明:
    - 返回 `None` 表示 shape 不是当前结构化 SymbolExprAttr layout。

    使用示例:
    - source_numel = _memory_numel_attr(source_type)
    """

    shape_attrs = _symbol_expr_attrs(memory_type.shape)
    if shape_attrs is None:
        return None
    return _product_expr_attr(shape_attrs)


def _alias_source(op: Operation) -> SSAValue | None:
    """返回 alias op 的 source operand。

    功能说明:
    - 当前只接受 `dma.reshape`、`dma.view` 与 `dma.reinterpret`。

    使用示例:
    - source = _alias_source(op)
    """

    if isinstance(op, (DmaReshapeOp, DmaViewOp, DmaReinterpretOp)):
        return op.operands[0]
    return None


def _alias_layout_operands(op: Operation) -> tuple[SSAValue, ...]:
    """返回 alias op 除 source 外的布局 operands。

    功能说明:
    - P1/P2 都要求这些 operands 支配候选插入点。

    使用示例:
    - if all(_value_dominates_op(value, writer) for value in _alias_layout_operands(alias)): ...
    """

    if isinstance(op, DmaReshapeOp):
        return tuple(op.shape)
    if isinstance(op, DmaViewOp):
        return tuple(op.offsets) + tuple(op.shape) + tuple(op.stride)
    if isinstance(op, DmaReinterpretOp):
        return (op.offset,) + tuple(op.shape) + tuple(op.stride)
    return ()


def _alias_operands(op: Operation) -> tuple[SSAValue, ...]:
    """返回 alias op 的全部 operands。

    功能说明:
    - 统一 P1 与 P2 的支配检查。

    使用示例:
    - operands = _alias_operands(alias)
    """

    return tuple(op.operands) if isinstance(op, (DmaReshapeOp, DmaViewOp, DmaReinterpretOp)) else ()


def _reshape_is_full_cover(alias: DmaReshapeOp) -> bool:
    """判断 `dma.reshape` 是否是 full-cover alias。

    功能说明:
    - source/result 必须同 space、同 element type。
    - source/result 必须都是 contiguous，且 numel exact 相等。
    - shape operands 必须 exact 匹配 result shape。

    使用示例:
    - if _reshape_is_full_cover(alias): ...
    """

    source_type = _memory_type_of(alias.source)
    result_type = _memory_type_of(alias.result)
    if source_type is None or result_type is None:
        return False
    result_shape = _symbol_expr_attrs(result_type.shape)
    if result_shape is None:
        return False
    source_numel = _memory_numel_attr(source_type)
    result_numel = _memory_numel_attr(result_type)
    return (
        _same_space_and_element_type(source_type, result_type)
        and _is_contiguous_memory_type(source_type)
        and _is_contiguous_memory_type(result_type)
        and source_numel is not None
        and source_numel == result_numel
        and _symbol_operands_match_attrs(alias.shape, result_shape)
    )


def _view_is_full_cover(alias: DmaViewOp) -> bool:
    """判断 `dma.view` 是否是 full-cover alias。

    功能说明:
    - offset 必须全 0、logical stride 必须全 1。
    - source/result shape 与 physical stride 必须 exact 相等，保证物理 index set 完整等价。

    使用示例:
    - if _view_is_full_cover(alias): ...
    """

    source_type = _memory_type_of(alias.source)
    result_type = _memory_type_of(alias.result)
    if source_type is None or result_type is None:
        return False
    source_shape = _symbol_expr_attrs(source_type.shape)
    source_stride = _symbol_expr_attrs(source_type.stride)
    result_shape = _symbol_expr_attrs(result_type.shape)
    result_stride = _symbol_expr_attrs(result_type.stride)
    if source_shape is None or source_stride is None or result_shape is None or result_stride is None:
        return False
    return (
        _same_space_and_element_type(source_type, result_type)
        and _same_symbol_attrs(source_shape, result_shape)
        and _same_symbol_attrs(source_stride, result_stride)
        and all(_symbol_value_is_expr(offset, "0") for offset in alias.offsets)
        and all(_symbol_value_is_expr(stride, "1") for stride in alias.stride)
        and _symbol_operands_match_attrs(alias.shape, result_shape)
    )


def _reinterpret_is_full_cover(alias: DmaReinterpretOp) -> bool:
    """判断 `dma.reinterpret` 是否是 full-cover alias。

    功能说明:
    - offset 必须为 0，source 不能是一维 i8 byte pool。
    - source/result 必须同 space、同 element type、都为 contiguous，且 numel exact 相等。
    - shape/stride operands 必须 exact 匹配 result layout。

    使用示例:
    - if _reinterpret_is_full_cover(alias): ...
    """

    source_type = _memory_type_of(alias.source)
    result_type = _memory_type_of(alias.result)
    if source_type is None or result_type is None:
        return False
    result_shape = _symbol_expr_attrs(result_type.shape)
    result_stride = _symbol_expr_attrs(result_type.stride)
    if result_shape is None or result_stride is None:
        return False
    source_numel = _memory_numel_attr(source_type)
    result_numel = _memory_numel_attr(result_type)
    return (
        _symbol_value_is_expr(alias.offset, "0")
        and not _is_i8_byte_pool_memory_type(source_type)
        and _same_space_and_element_type(source_type, result_type)
        and _is_contiguous_memory_type(source_type)
        and _is_contiguous_memory_type(result_type)
        and source_numel is not None
        and source_numel == result_numel
        and _symbol_operands_match_attrs(alias.shape, result_shape)
        and _symbol_operands_match_attrs(alias.stride, result_stride)
    )


def _alias_is_full_cover(op: Operation) -> bool:
    """判断 alias op 是否覆盖 source 的完整物理 index set。

    功能说明:
    - P2 retarget 只接受可证明 full-cover 的 alias。

    使用示例:
    - if _alias_is_full_cover(alias): ...
    """

    if isinstance(op, DmaReshapeOp):
        return _reshape_is_full_cover(op)
    if isinstance(op, DmaViewOp):
        return _view_is_full_cover(op)
    if isinstance(op, DmaReinterpretOp):
        return _reinterpret_is_full_cover(op)
    return False


def _writer_target_has_write_no_read_effect(writer: Operation, target: SSAValue) -> bool:
    """判断 writer 对 target 是否只有 WRITE、没有 READ。

    功能说明:
    - 只使用公开 `get_effects(writer)` 与 `MemoryEffectKind.WRITE/READ`。
    - 无 effect、unknown effect 或同 target 有 READ 时均保守 no-op。

    使用示例:
    - if _writer_target_has_write_no_read_effect(writer, writer.operands[0]): ...
    """

    effects = get_effects(writer)
    if effects is None:
        return False
    has_write = False
    has_read = False
    for effect in effects:
        effect_value = effect.value
        if effect_value is None or not _same_value(effect_value, target):
            continue
        if effect.kind is MemoryEffectKind.WRITE:
            has_write = True
        if effect.kind is MemoryEffectKind.READ:
            has_read = True
    return has_write and not has_read


def _alias_can_retarget_writer(alias: Operation, writer: Operation) -> bool:
    """判断 alias 是否可穿过当前 writer 并 retarget。

    功能说明:
    - 要求 writer 与 alias 同 block 紧邻、writer target 等于 alias source。
    - 要求 writer target 由 MemoryEffect 证明为 WRITE/no-READ。
    - 要求 alias 布局 operands 支配 writer，且 alias 是 full-cover。

    使用示例:
    - if _alias_can_retarget_writer(alias, writer): ...
    """

    block = alias.parent_block()
    source = _alias_source(alias)
    if block is None or writer.parent_block() is not block or source is None:
        return False
    if writer.next_op is not alias or not writer.operands:
        return False
    writer_target = writer.operands[0]
    return (
        _same_value(writer_target, source)
        and _writer_target_has_write_no_read_effect(writer, writer_target)
        and all(_value_dominates_op(operand, writer) for operand in _alias_layout_operands(alias))
        and _alias_is_full_cover(alias)
    )


def _op_effect_touches_value(op: Operation, value: SSAValue) -> bool:
    """判断 op 的公开 memory effect 是否触碰指定 value。

    功能说明:
    - `effects is None` 或 effect value 缺失表示无法证明安全，按触碰处理。
    - 只使用公开 `get_effects(op)` 结果，不按具体 op class 白名单判断。

    使用示例:
    - if _op_effect_touches_value(candidate, source): return False
    """

    effects = get_effects(op)
    if effects is None:
        return True
    for effect in effects:
        if effect.value is None or _same_value(effect.value, value):
            return True
    return False


def _same_block_hoist_crosses_source_effect(alias: Operation, insert_point: InsertPoint) -> bool:
    """判断同 block pure hoist 是否会跨过触碰 source 的 memory op。

    功能说明:
    - P1 可以跨过无关 writer，例如 `dma.fill(%dst); dma.view(%src)`。
    - P1 不跨过触碰 alias source 的 writer/reader，避免绕过 P2 的 write/no-read 条件。

    使用示例:
    - if _same_block_hoist_crosses_source_effect(alias, insert_point): return
    """

    source = _alias_source(alias)
    if source is None:
        return True
    current = insert_point.insert_before
    if current is None:
        return True
    while current is not None and current is not alias:
        if _op_effect_touches_value(current, source):
            return True
        current = current.next_op
    return current is not alias


def _restore_alias_after_failed_move(block: Block, alias: Operation, original_next: Operation | None) -> None:
    """把事务失败时的 alias op 放回原位置。

    功能说明:
    - 优先插到原 `next_op` 前；原尾部 op 时插回 block 末尾。

    使用示例:
    - _restore_alias_after_failed_move(block, alias, original_next)
    """

    alias.detach()
    if original_next is not None and original_next.parent_block() is block:
        block.insert_op_before(alias, original_next)
    else:
        block.add_op(alias)


class _HoistAliasMover:
    """当前文件内的局部 rewrite 规则容器。

    功能说明:
    - 将单个事务式 helper 收进对象方法，避免 private callable 调用 private callable。
    - 该容器只在当前文件使用，不作为跨文件公开 API。

    使用示例:
    - _HOIST_ALIAS_MOVER.move_alias_before_writer(...)
    """

    @staticmethod
    def move_alias_before_writer(module: ModuleOp, alias: Operation, writer: Operation, rewriter: PatternRewriter) -> bool:
        """执行一次 alias 穿过 writer 的事务式改写。

        功能说明:
        - 复用原 alias op/result，不新建 alias。
        - 先把 alias 插到 writer 前，再把 writer target 改为 alias result。
        - `module.verify()` 失败时撤回 alias 位置和 writer target，保证原 module 不被部分改写。

        使用示例:
        - changed = _HOIST_ALIAS_MOVER.move_alias_before_writer(module, alias, writer, rewriter)
        """

        block = alias.parent_block()
        if block is None or writer.parent_block() is not block or not alias.results or not writer.operands:
            return False
        original_next = alias.next_op
        original_target = writer.operands[0]
        alias.detach()
        rewriter.insert_op(alias, InsertPoint.before(writer))
        writer.operands[0] = alias.results[0]
        try:
            verify_generated_ops([module])
        except KernelCodeError:
            writer.operands[0] = original_target
            _restore_alias_after_failed_move(block, alias, original_next)
            return False
        rewriter.notify_op_modified(writer)
        return True

_HOIST_ALIAS_MOVER = _HoistAliasMover()


def _same_block_insert_point(alias: Operation) -> InsertPoint | None:
    """计算 alias 在当前 block 内的最早合法插入点。

    功能说明:
    - 插入点位于所有同 block operand 定义之后。
    - 任一 operand 定义在 alias 之后、sibling block 或 descendant region 时 no-op。

    使用示例:
    - insert_point = _same_block_insert_point(alias)
    """

    block = alias.parent_block()
    if block is None:
        return None
    latest_owner: Operation | None = None
    for operand in _alias_operands(alias):
        if isinstance(operand, BlockArgument):
            if operand.owner is block or operand.owner.is_ancestor(alias):
                continue
            return None
        owner = operand.owner
        if not isinstance(owner, Operation):
            continue
        owner_block = owner.parent_block()
        if owner_block is not block:
            ancestor = owner_block.find_ancestor_op_in_block(alias) if owner_block is not None else None
            if ancestor is None or owner is ancestor:
                return None
            owner = ancestor
        if owner is alias:
            return None
        if not owner.is_before_in_block(alias):
            return None
        if latest_owner is None or latest_owner.is_before_in_block(owner):
            latest_owner = owner
    if latest_owner is None:
        if alias.prev_op is None:
            return None
        return InsertPoint.at_start(block)
    if alias.prev_op is latest_owner:
        return None
    return InsertPoint.after(latest_owner)


def _direct_symbol_for_parent(block: Block) -> SymbolForOp | None:
    """返回 block 的直接 parent `symbol.for`。

    功能说明:
    - P1 只允许把 alias 从 `symbol.for` 直接 body 提到循环前。
    - 其它 region 形态全部 no-op。

    使用示例:
    - loop = _direct_symbol_for_parent(alias.parent_block())
    """

    parent_op = block.parent_op()
    return parent_op if isinstance(parent_op, SymbolForOp) and parent_op.body.block is block else None


def _loop_hoist_insert_point(alias: Operation) -> InsertPoint | None:
    """计算 alias 从 `symbol.for` body 外提一层的插入点。

    功能说明:
    - alias 所有 operands 必须支配该 `symbol.for`。
    - 依赖 loop iterator、loop-carried block argument 或 loop body 内 SSA 时 no-op。

    使用示例:
    - insert_point = _loop_hoist_insert_point(alias)
    """

    block = alias.parent_block()
    if block is None:
        return None
    loop = _direct_symbol_for_parent(block)
    if loop is None or loop.parent_block() is None:
        return None
    if not all(_value_dominates_op(operand, loop) for operand in _alias_operands(alias)):
        return None
    return InsertPoint.before(loop)


def _move_alias(module: ModuleOp, alias: Operation, insert_point: InsertPoint, rewriter: PatternRewriter) -> bool:
    """事务式移动 alias op。

    功能说明:
    - 用于 P1 pure hoist，不改 writer target。
    - P1 的安全性来自 `_same_block_insert_point(...)` 与 `_loop_hoist_insert_point(...)` 的支配证明。
    - 不运行全模块 verifier，避免已有 dma.view 子区间 verifier 旧口径阻断纯位置移动。

    使用示例:
    - changed = _move_alias(module, alias, insert_point, rewriter)
    """

    block = alias.parent_block()
    if block is None:
        return False
    alias.detach()
    rewriter.insert_op(alias, insert_point)
    _ = module
    return True


class DmaAliasThroughWriteNoReadPattern(RewritePattern):
    """通过公开 MemoryEffect 证明的 alias-through-write pattern。

    功能说明:
    - 匹配紧邻 `writer; alias`。
    - writer target 必须是 `writer.operands[0]`，且 `get_effects(writer)` 中该 target 有
      `MemoryEffectKind.WRITE`、没有 `MemoryEffectKind.READ`。
    - alias 必须是 full-cover `dma.reshape`、`dma.view` 或 `dma.reinterpret`。
    - writer 正例覆盖 `dma.fill` 与 scalar `dma.broadcast`；memory-source `dma.broadcast`
      读取同一 target 时保持 no-op。

    IR before:
    ```mlir
    "dma.fill"(%src, %zero) : (!nn.memory<...>, f32) -> ()
    %alias = "dma.reshape"(%src, %m, %n) : (...) -> !nn.memory<...>
    ```

    IR after:
    ```mlir
    %alias = "dma.reshape"(%src, %m, %n) : (...) -> !nn.memory<...>
    "dma.fill"(%alias, %zero) : (!nn.memory<...>, f32) -> ()
    ```

    使用示例:
    - pattern = DmaAliasThroughWriteNoReadPattern(module)
    """

    def __init__(self: "DmaAliasThroughWriteNoReadPattern", module: ModuleOp) -> None:
        """初始化 through-write pattern。

        功能说明:
        - 保存当前 ModuleOp，用于事务式 rewrite 后验证和 rollback。
        - 记录 verify 已拒绝的 alias，避免 greedy walker 对同一失败候选无限重试。

        使用示例:
        - pattern = DmaAliasThroughWriteNoReadPattern(module)
        """

        self.module = module
        self._rejected_alias_ids: set[int] = set()

    def match_and_rewrite(
        self: "DmaAliasThroughWriteNoReadPattern",
        op: Operation,
        rewriter: PatternRewriter,
        /,
    ) -> None:
        """执行单个 alias-through-write 候选改写。

        功能说明:
        - 仅处理 `dma.reshape`、`dma.view`、`dma.reinterpret`。
        - 失败边界均 no-op；verify 失败会回滚。

        使用示例:
        - DmaAliasThroughWriteNoReadPattern(module).match_and_rewrite(op, rewriter)
        """

        if not isinstance(op, (DmaReshapeOp, DmaViewOp, DmaReinterpretOp)):
            return
        if id(op) in self._rejected_alias_ids:
            return
        writer = op.prev_op
        if writer is None or not _alias_can_retarget_writer(op, writer):
            return
        if not _HOIST_ALIAS_MOVER.move_alias_before_writer(self.module, op, writer, rewriter):
            self._rejected_alias_ids.add(id(op))


class DmaAliasHoistPattern(RewritePattern):
    """NoMemoryEffect alias descriptor pure hoist pattern。

    功能说明:
    - 统一外提 `dma.view`、`dma.reshape` 与 `dma.reinterpret`。
    - 只移动 alias descriptor 到 operands 已支配的最早合法位置，不修改任何 writer target。
    - 允许 loop-invariant alias 从 `symbol.for` 直接 body 提到该 loop 前。
    - 对 broadcast source 上的 leading-unit `dma.reinterpret([N] -> [1,N])`，在 verifier
      成功时删除 alias，并把 writer target 与 `dma.broadcast` source 改回 flat source。

    IR before:
    ```mlir
    "dma.fill"(%dst, %zero) : (!nn.memory<...>, f32) -> ()
    %alias = "dma.view"(%src, %o0, %o1, %s0, %s1, %t0, %t1) : (...) -> !nn.memory<...>
    ```

    IR after:
    ```mlir
    %alias = "dma.view"(%src, %o0, %o1, %s0, %s1, %t0, %t1) : (...) -> !nn.memory<...>
    "dma.fill"(%dst, %zero) : (!nn.memory<...>, f32) -> ()
    ```

    IR before:
    ```mlir
    %alias = "dma.reinterpret"(%flat, %c0, %c1, %n, %n, %c1) : (...) -> !nn.memory<...>
    "dma.broadcast"(%dst, %alias) : (!nn.memory<...>, !nn.memory<...>) -> ()
    ```

    IR after:
    ```mlir
    "dma.broadcast"(%dst, %flat) : (!nn.memory<...>, !nn.memory<...>) -> ()
    ```

    使用示例:
    - pattern = DmaAliasHoistPattern(module)
    """

    def __init__(self: "DmaAliasHoistPattern", module: ModuleOp) -> None:
        """初始化 pure alias hoist pattern。

        功能说明:
        - 保存当前 ModuleOp，用于事务式 rewrite 后验证和 rollback。
        - 记录已处理 / 已拒绝 alias，保证 pure hoist 在 greedy walker 中收敛。

        使用示例:
        - pattern = DmaAliasHoistPattern(module)
        """

        self.module = module
        self._handled_alias_ids: set[int] = set()
        self._rejected_alias_ids: set[int] = set()

    def match_and_rewrite(self: "DmaAliasHoistPattern", op: Operation, rewriter: PatternRewriter, /) -> None:
        """执行单个 alias hoist / broadcast source 化简候选改写。

        功能说明:
        - 对同 block alias，移动到 operands 已支配后的最早合法位置。
        - 对 `symbol.for` 直接 body 内 loop-invariant alias，提到 loop 前。
        - 对 leading-unit `dma.reinterpret([N] -> [1,N])` 的 broadcast source，事务式删除 alias。
        - retarget 后任一 op/module verifier 失败时完整 rollback，非目标 rank 保持 no-op。

        使用示例:
        - DmaAliasHoistPattern(module).match_and_rewrite(op, rewriter)
        """

        if not isinstance(op, (DmaReshapeOp, DmaViewOp, DmaReinterpretOp)):
            return
        alias_id = id(op)
        if alias_id in self._handled_alias_ids or alias_id in self._rejected_alias_ids:
            return
        if isinstance(op, DmaReinterpretOp) and op.results:
            source_type = _memory_type_of(op.source)
            result_type = _memory_type_of(op.result)
            source_shape = _symbol_expr_attrs(source_type.shape) if source_type is not None else None
            source_stride = _symbol_expr_attrs(source_type.stride) if source_type is not None else None
            result_shape = _symbol_expr_attrs(result_type.shape) if result_type is not None else None
            result_stride = _symbol_expr_attrs(result_type.stride) if result_type is not None else None
            source_numel = _memory_numel_attr(source_type) if source_type is not None else None
            result_numel = _memory_numel_attr(result_type) if result_type is not None else None
            expected_shape: tuple[SymbolExprAttr, ...] = ()
            expected_stride: tuple[SymbolExprAttr, ...] = ()
            if source_shape is not None and len(source_shape) == 1:
                expected_shape = (SymbolExprAttr.from_expr("1"), source_shape[0])
                expected_stride = (source_shape[0], SymbolExprAttr.from_expr("1"))
            is_leading_unit_broadcast_source = (
                source_type is not None
                and result_type is not None
                and source_shape is not None
                and source_stride is not None
                and result_shape is not None
                and result_stride is not None
                and len(source_shape) == 1
                and len(result_shape) == 2
                and _symbol_value_is_expr(op.offset, "0")
                and not _is_i8_byte_pool_memory_type(source_type)
                and _same_space_and_element_type(source_type, result_type)
                and _is_contiguous_memory_type(source_type)
                and _is_contiguous_memory_type(result_type)
                and source_stride == (SymbolExprAttr.from_expr("1"),)
                and source_numel is not None
                and source_numel == result_numel
                and _same_symbol_attrs(result_shape, expected_shape)
                and _same_symbol_attrs(result_stride, expected_stride)
                and _symbol_operands_match_attrs(op.shape, result_shape)
                and _symbol_operands_match_attrs(op.stride, result_stride)
            )
            if is_leading_unit_broadcast_source:
                source = op.source
                alias_result = op.results[0]
                uses = list(alias_result.uses)
                has_broadcast_source_use = False
                originals: list[tuple[Operation, int, SSAValue]] = []
                for use in uses:
                    user = use.operation
                    operand_index = use.index
                    is_broadcast_source = isinstance(user, DmaBroadcastOp) and operand_index == 1
                    is_write_no_read_target = operand_index == 0 and _writer_target_has_write_no_read_effect(
                        user,
                        alias_result,
                    )
                    if is_broadcast_source:
                        has_broadcast_source_use = True
                    if not _value_dominates_op(source, user) or not (is_broadcast_source or is_write_no_read_target):
                        originals = []
                        break
                    originals.append((user, operand_index, user.operands[operand_index]))
                if has_broadcast_source_use and originals:
                    try:
                        verify_generated_ops([self.module])
                    except KernelCodeError:
                        module_was_valid = False
                    else:
                        module_was_valid = True
                    for user, operand_index, _original in originals:
                        user.operands[operand_index] = source
                    try:
                        for user, _operand_index, _original in originals:
                            verify_generated_ops([user])
                        if module_was_valid:
                            verify_generated_ops([self.module])
                    except KernelCodeError:
                        for user, operand_index, original in originals:
                            user.operands[operand_index] = original
                    else:
                        if list(alias_result.uses):
                            for user, operand_index, original in originals:
                                user.operands[operand_index] = original
                        else:
                            for user, _operand_index, _original in originals:
                                rewriter.notify_op_modified(user)
                            rewriter.erase_op(op)
                            self._handled_alias_ids.add(alias_id)
                            return
        insert_point = _loop_hoist_insert_point(op)
        is_loop_hoist = insert_point is not None
        if not is_loop_hoist:
            insert_point = _same_block_insert_point(op)
        if insert_point is None:
            return
        if not is_loop_hoist and _same_block_hoist_crosses_source_effect(op, insert_point):
            return
        if _move_alias(self.module, op, insert_point, rewriter):
            self._handled_alias_ids.add(alias_id)
        else:
            self._rejected_alias_ids.add(alias_id)


def get_hoist_dma_alias_ops_pass_patterns(module: ModuleOp) -> list[RewritePattern]:
    """返回 `hoist-dma-alias-ops` pass 的公开 pattern 列表。

    功能说明:
    - 返回顺序固定为 through-write/no-read pattern 在前、pure hoist pattern 在后。
    - 每次调用返回新 pattern 实例，避免跨运行共享状态。

    使用示例:
    - patterns = get_hoist_dma_alias_ops_pass_patterns(module)
    """

    return [DmaAliasThroughWriteNoReadPattern(module), DmaAliasHoistPattern(module)]


def _rewrite_module(module: ModuleOp) -> None:
    """对 ModuleOp 运行 hoist-dma-alias-ops rewrite walker。

    功能说明:
    - 只使用 xDSL `PatternRewriteWalker` 与 `GreedyRewritePatternApplier`。
    - 不在 pass 中实现手写整段 block 遍历。

    使用示例:
    - _rewrite_module(module)
    """

    PatternRewriteWalker(
        GreedyRewritePatternApplier(get_hoist_dma_alias_ops_pass_patterns(module)),
        apply_recursively=True,
    ).rewrite_module(module)


class HoistDmaAliasOpsPass(Pass):
    """`hoist-dma-alias-ops` pass 公开入口。

    功能说明:
    - 用 P2 through-write/no-read 与 P1 pure alias hoist 两个公开 pattern 驱动 rewrite。
    - 不新增 pass option；`fold` 仍只作为通用 pass 开关。

    使用示例:
    - HoistDmaAliasOpsPass().apply(Context(), module)
    """

    name = "hoist-dma-alias-ops"

    def apply(self: "HoistDmaAliasOpsPass", ctx: Context, module: ModuleOp) -> None:
        """执行 `hoist-dma-alias-ops` ModulePass。

        功能说明:
        - 校验输入是 builtin.module。
        - 运行公开 pattern 列表驱动的 greedy rewrite。

        使用示例:
        - HoistDmaAliasOpsPass(fold=False).apply(ctx, module)
        """

        target = ensure_builtin_module(module)
        _rewrite_module(target)


__all__ = [
    "DmaAliasHoistPattern",
    "DmaAliasThroughWriteNoReadPattern",
    "get_hoist_dma_alias_ops_pass_patterns",
    "HoistDmaAliasOpsPass",
]
