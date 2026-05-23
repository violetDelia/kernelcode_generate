"""symbol-buffer-hoist pass.


功能说明:
- 定义 `symbol-buffer-hoist` 的公开 pass、公开 pattern 与公开 pattern getter。
- 只在 `symbol.for` 单 block 循环体内识别 `dma.alloc`，并在 shape 明确不依赖 loop 内 SSA、
  直接 use 仅属于输入 staging / output scratch、公开 `MemoryEffect` 读写、`dma.broadcast`
  或受支持 alias producer，且存在唯一匹配 `dma.free` 时，将其与 `dma.free` 成对外提一层。
- 当同一 `symbol.for` 直接 body 内存在唯一匹配 `dma.free` 且该 free 晚于所有 data use 时，
  外提 `dma.alloc` 的同时把对应 `dma.free` 移到同一 `symbol.for` 之后。
- 对 source、offset/shape/stride 等 operand 均支配当前 `symbol.for` 的 `dma.view`、`dma.reshape`
  和 `dma.subview`，作为独立 alias op 单次外提一层；fixed-point 驱动允许同一 alias op 跨 nested loop
  逐层外提到最近安全位置。
- `symbol.get_dim` / `symbol.get_stride` 是 Pure metadata query，只读取 alias 或 memory 的 shape / stride
  信息，不参与生命周期数据 use，也不能单独证明 reset/write。
- `dma.alloc/free` 外提通过 `MemoryEffect` 证明生命周期：首次 read 前必须已有同一 region block 内的
  full reset/write；nested `symbol.for` 内 data use 不再一律 no-op，只要每个 read 均被支配它的 full write
  覆盖，alloc/free 就可以通过 fixed-point 逐层外提。`READ+WRITE` 的同值 use 不能自证 reset/write，
  unknown effect、读先于写、多 free 或 nested free 均保持 no-op。
- 失败边界统一复用 `KernelCodeError(module="pass")`；不新增专题专属错误类型，也不承诺额外 compat path。

API 列表:
- `class DmaAllocInSymbolForHoistPattern()`
- `DmaAllocInSymbolForHoistPattern.match_and_rewrite(op: DmaAllocOp, rewriter: PatternRewriter) -> None`
- `class DmaViewInSymbolForHoistPattern()`
- `DmaViewInSymbolForHoistPattern.match_and_rewrite(op: DmaViewOp, rewriter: PatternRewriter) -> None`
- `class DmaReshapeInSymbolForHoistPattern()`
- `DmaReshapeInSymbolForHoistPattern.match_and_rewrite(op: DmaReshapeOp, rewriter: PatternRewriter) -> None`
- `class DmaSubviewInSymbolForHoistPattern()`
- `DmaSubviewInSymbolForHoistPattern.match_and_rewrite(op: DmaSubviewOp, rewriter: PatternRewriter) -> None`
- `get_symbol_buffer_hoist_patterns() -> list[RewritePattern]`
- `class SymbolBufferHoistPass(fold: bool = True)`
- `SymbolBufferHoistPass.name: str`
- `SymbolBufferHoistPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from xdsl.context import Context
- from xdsl.dialects.builtin import ModuleOp
- from kernel_gen.passes.symbol_buffer_hoist import SymbolBufferHoistPass
- module = ModuleOp([])
- SymbolBufferHoistPass().apply(Context(), module)

关联文件:
- spec: spec/pass/symbol_buffer_hoist.md
- test: test/passes/test_symbol_buffer_hoist.py
- test: test/passes/test_registry.py
- 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Attribute, Block, BlockArgument, Operation, SSAValue, Use
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)
from xdsl.rewriter import InsertPoint
from xdsl.traits import MemoryEffectKind, get_effects
from xdsl.utils.exceptions import VerifyException

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.dma import (
    DmaAllocOp,
    DmaBroadcastOp,
    DmaCopyOp,
    DmaDesliceOp,
    DmaFillOp,
    DmaFreeOp,
    DmaReshapeOp,
    DmaSliceOp,
    DmaSubviewOp,
    DmaViewOp,
)
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import Symbol, SymbolExprAttr, SymbolForOp, SymbolValueType
from kernel_gen.passes.common import ensure_builtin_module
from kernel_gen.passes.pass_manager import Pass


@dataclass(frozen=True)
class _HoistUsePlan:
    """记录一次 alloc 外提可接受的生命周期事件分类。


    功能说明:
    - `data_events` 保存同一 owner loop body 或 descendant region 内可证明的 data lifecycle event。
    - `free_op` 表示可随 alloc 成对外提的唯一 `dma.free`。

    使用示例:
    - plan = _HoistUsePlan(data_events=(event,), free_op=free_op)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    data_events: tuple["_MemoryEvent", ...]
    free_op: DmaFreeOp | None


@dataclass(frozen=True)
class _MemoryEvent:
    """记录某个 memory use 对 alloc root 的生命周期影响。


    功能说明:
    - `effects` 只承接公开 `MemoryEffectKind.READ/WRITE`。
    - `full_write` 表示该 WRITE 覆盖 alloc root 的完整可读内容，可作为后续 READ 的 reset proof。
    - alias result 上的 partial write 不会被升级为 alloc root 的 full write。

    使用示例:
    - event = _MemoryEvent(use=use, effects=frozenset({MemoryEffectKind.WRITE}), full_write=True)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    use: Use
    effects: frozenset[MemoryEffectKind]
    full_write: bool


def _value_dominates_symbol_for(value: SSAValue, symbol_for: SymbolForOp) -> bool:
    """判断 SSA 值是否在当前 `symbol.for` 前可见。


    功能说明:
    - 只接受定义在当前 loop body 外、且支配当前 `symbol.for` 的 SSA 值。
    - 当前 loop body、nested region 或 sibling block 内定义的值都保守视为不可外提。
    - 外层 loop body 中位于当前 `symbol.for` 前的值允许作为“当前层” invariant。

    使用示例:
    - _value_dominates_symbol_for(symbol_dim, symbol_for)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    loop_block = symbol_for.body.blocks[0]
    if isinstance(value, BlockArgument):
        return value.owner is not loop_block and value.owner.is_ancestor(symbol_for)
    owner = value.owner
    if not isinstance(owner, Operation):
        return True
    owner_block = owner.parent_block()
    if owner_block is None:
        return True
    if owner_block is loop_block or loop_block.is_ancestor(owner):
        return False
    if owner_block is symbol_for.parent_block():
        return owner.is_before_in_block(symbol_for)
    ancestor = owner_block.find_ancestor_op_in_block(symbol_for)
    if ancestor is None or owner is ancestor:
        return False
    return owner.is_before_in_block(ancestor)


def _shape_is_loop_invariant(op: DmaAllocOp, symbol_for: SymbolForOp) -> bool:
    """判断 `dma.alloc` 的 dynamic_shape 是否全部来自 loop 外。


    功能说明:
    - 空 `dynamic_shape` 视为满足 invariant。
    - 只要任一 shape operand 来自当前 loop body 或 loop-carried block argument，就保持 no-op。

    使用示例:
    - _shape_is_loop_invariant(alloc_op, symbol_for)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    return all(_value_dominates_symbol_for(SSAValue.get(value), symbol_for) for value in op.dynamic_shape)


def _is_supported_data_use(use: Use) -> bool:
    """判断 `dma.alloc` 的单个 direct data use 是否属于公开白名单。


    功能说明:
    - 输入 staging buffer：仅接受 `dma.slice` 的 `target` operand。
    - output scratch buffer：仅接受 `dma.deslice` 的 `source` operand。
    - `dma.free` 属于 lifecycle use，由独立规则处理。
    - 其他 direct use 一律视为未承接的逃逸形态。

    使用示例:
    - all(_is_supported_data_use(use) for use in alloc_op.result.uses)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    user = use.operation
    return (isinstance(user, DmaSliceOp) and use.index == 0) or (
        isinstance(user, DmaDesliceOp) and use.index == 1
    )


def _is_metadata_query_use(use: Use) -> bool:
    """判断 use 是否为 Pure memory metadata query。


    功能说明:
    - `symbol.get_dim` / `symbol.get_stride` 只读取 memory type 元信息，不参与 data lifecycle。
    - 该 helper 仅用于当前文件内 pass 判定，不作为公开 API。

    使用示例:
    - if _is_metadata_query_use(use): ...

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    return use.index == 0 and use.operation.name in {"symbol.get_dim", "symbol.get_stride"}


def _is_supported_alias_result_use(use: Use) -> bool:
    """判断 alias result 的 direct use 是否属于可捕获白名单。


    功能说明:
    - 允许 `dma.slice target`、`dma.deslice source`、`dma.fill target`、`dma.copy target/source`。
    - 允许 `symbol.get_dim` / `symbol.get_stride` 读取 alias memory 的 shape / stride 信息；它们不移动 memory 生命周期。
    - 允许带公开 MemoryEffect 的 `kernel.*` memory operand 捕获 alias result。
    - 其它 direct use 保持 no-op，避免把未知副作用或逃逸形态做宽。

    使用示例:
    - if _is_supported_alias_result_use(use): ...

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    user = use.operation
    if _is_supported_data_use(use):
        return True
    if isinstance(user, DmaFillOp) and use.index == 0:
        return True
    if isinstance(user, DmaCopyOp) and use.index in (0, 1):
        return True
    if _is_metadata_query_use(use):
        return True
    if _is_kernel_memory_use(use):
        return True
    return False


def _is_supported_alias_source_use(use: Use) -> bool:
    """判断 direct use 是否为受支持 alias op 的 source operand。


    功能说明:
    - 只允许 `dma.view`、`dma.reshape`、`dma.subview` 的 source use。
    - 该 helper 仅服务当前文件内 alloc/free 与 alias op 外提判定，不构成公开 API。

    使用示例:
    - if _is_supported_alias_source_use(use): ...

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    user = use.operation
    return use.index == 0 and isinstance(user, (DmaViewOp, DmaReshapeOp, DmaSubviewOp))


def _collect_direct_uses(result: SSAValue) -> tuple[Use, ...]:
    """收集 alloc 结果的直接 use 列表。


    功能说明:
    - 把 xdsl use 链转成稳定 tuple，便于重复遍历与空 use 判定。

    使用示例:
    - uses = _collect_direct_uses(alloc_op.result)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    return tuple(cast_use for cast_use in result.uses)


def _operation_parent_block(op: Operation) -> Block | None:
    """返回 operation 的 parent block。


    功能说明:
    - 收口 xDSL parent block 读取，供 direct use 分类复用。

    使用示例:
    - block = _operation_parent_block(use.operation)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    return op.parent_block()


def _operation_is_in_block_or_descendant(op: Operation, owner_block: Block) -> bool:
    """判断 operation 是否位于指定 block 或其 descendant region。


    功能说明:
    - alias fixed-point 外提允许 result use 留在 owner loop 的 nested loop 内。
    - sibling block 或 owner loop 外 use 仍视为逃逸。

    使用示例:
    - _operation_is_in_block_or_descendant(use.operation, loop_block)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    op_block = _operation_parent_block(op)
    if op_block is None:
        return False
    return op_block is owner_block or owner_block.is_ancestor(op)


def _direct_operation_in_block(op: Operation, owner_block: Block) -> Operation | None:
    """返回代表该 op 在 owner block 顺序中的直接 operation。


    功能说明:
    - 若 op 直接位于 owner block，返回 op。
    - 若 op 位于 owner block 的 descendant region，返回 owner block 中包住它的直接 child op。
    - 用于比较 nested data use 与 direct `dma.free` 的相对顺序。

    使用示例:
    - direct = _direct_operation_in_block(use.operation, loop_block)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    current = op
    current_block = _operation_parent_block(current)
    while current_block is not None:
        if current_block is owner_block:
            return current
        parent_op = current_block.parent_op()
        if parent_op is None:
            return None
        current = parent_op
        current_block = _operation_parent_block(current)
    return None


def _block_index_map(block: Block) -> dict[Operation, int]:
    """构造 block 内 operation 到顺序索引的映射。


    功能说明:
    - 用于判断 `dma.free` 是否晚于所有 data use。

    使用示例:
    - indexes = _block_index_map(loop_block)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    return {item: index for index, item in enumerate(block.ops)}


def _op_dominates_op(producer: Operation, consumer: Operation) -> bool:
    """判断 producer 是否在当前单 block / parent-chain 模型下支配 consumer。


    功能说明:
    - 同 block 时要求 producer 文本顺序早于 consumer。
    - producer 位于 ancestor block 时，要求 producer 早于该 block 中包住 consumer 的直接 child op。
    - sibling region、descendant 反向 use 与不可定位 parent chain 均保守返回 False。

    使用示例:
    - if _op_dominates_op(fill_op, matmul_op): ...

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    producer_block = _operation_parent_block(producer)
    consumer_block = _operation_parent_block(consumer)
    if producer_block is None or consumer_block is None:
        return False
    if producer_block is consumer_block:
        return producer.is_before_in_block(consumer)
    consumer_direct = _direct_operation_in_block(consumer, producer_block)
    if consumer_direct is None or consumer_direct is producer:
        return False
    return producer.is_before_in_block(consumer_direct)


def _free_follows_data_events(free_op: DmaFreeOp, data_events: tuple[_MemoryEvent, ...], loop_block: Block) -> bool:
    """判断唯一 free 是否位于所有 data event 之后。


    功能说明:
    - free 必须位于 owner loop 直接 body 内。
    - data event 可位于 owner loop body 或 descendant region 内，顺序比较映射到 owner block 中的直接 child op。
    - 任一 operation 不在 block 顺序表内时保守 no-op。

    使用示例:
    - if _free_follows_data_events(free_op, events, loop_block): ...

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    if not data_events:
        return False
    indexes = _block_index_map(loop_block)
    if free_op not in indexes:
        return False
    data_indexes: list[int] = []
    for event in data_events:
        direct_use_op = _direct_operation_in_block(event.use.operation, loop_block)
        if direct_use_op not in indexes:
            return False
        data_indexes.append(indexes[direct_use_op])
    return indexes[free_op] > max(data_indexes)


def _effect_kinds_for_use(use: Use) -> set[MemoryEffectKind] | None:
    """读取某个 use 所在 operation 对该 SSA value 的 MemoryEffect。


    功能说明:
    - `None` 表示 operation 没有公开 MemoryEffect 或 effect 不可判定。
    - 空集合表示 operation 有公开 effect，但不作用于当前 use 的 SSA value。

    使用示例:
    - kinds = _effect_kinds_for_use(use)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    effects = get_effects(use.operation)
    if effects is None:
        return None
    value = SSAValue.get(use.operation.operands[use.index])
    return {effect.kind for effect in effects if effect.value is value}


def _is_kernel_memory_use(use: Use) -> bool:
    """判断 use 是否是带公开 MemoryEffect 的 kernel memory operand。


    功能说明:
    - 仅当 `kernel.*` op 对该 operand 暴露 READ/WRITE effect 时返回 true。
    - 未挂 MemoryEffect 的 kernel op 保守视为未知逃逸。

    使用示例:
    - if _is_kernel_memory_use(use): ...

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    if not use.operation.name.startswith("kernel."):
        return False
    kinds = _effect_kinds_for_use(use)
    return kinds is not None and bool(kinds) and kinds <= {MemoryEffectKind.READ, MemoryEffectKind.WRITE}


def _is_supported_lifecycle_data_use(use: Use) -> bool:
    """判断 alloc result direct use 是否可纳入生命周期证明。


    功能说明:
    - 以公开 `MemoryEffect` 的 `READ/WRITE` 语义为主轴，不再依赖 op 名称白名单作为主判定。
    - `dma.slice target` 与 `dma.deslice source` 仍作为旧兼容边界存在，但也通过公开 effect 参与证明。
    - 接受公开 `MemoryEffect` 可判定的 `dma.fill/copy/load/store/slice/deslice/broadcast` 与 `kernel.*`
      read/write use。
    - 不接受 unknown effect、alloc/free effect、Pure metadata query 或未列入当前计划的 DMA op。

    使用示例:
    - if _is_supported_lifecycle_data_use(use): ...

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    kinds = _effect_kinds_for_use(use)
    return kinds is not None and bool(kinds) and kinds <= {MemoryEffectKind.READ, MemoryEffectKind.WRITE}


def _symbol_value_text(value: SSAValue) -> str | None:
    """返回公开 symbol.int 值文本。


    功能说明:
    - 只读取 `SymbolValueType` 的公开 `get_value()`。
    - 非 symbol.int operand 返回 None，由调用方保守处理。

    使用示例:
    - if _symbol_value_text(size) == "16": ...

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    value_type = SSAValue.get(value).type
    if not isinstance(value_type, SymbolValueType):
        return None
    return str(value_type.get_value())


def _symbol_expr_text(value: Attribute) -> str:
    """返回 symbol expr attr 的稳定文本。


    功能说明:
    - 仅在当前文件内比较 `NnMemoryType.shape/stride` 与 symbol operand 类型。
    - 非预期 attribute 走 `str(...)`，避免扩大公开 API 依赖。

    使用示例:
    - text = _symbol_expr_text(memory_type.shape.data[0])

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    if isinstance(value, SymbolExprAttr):
        return value.expr.data
    return str(value)


def _memory_type_of(value: SSAValue) -> NnMemoryType | None:
    """返回 SSA value 的 nn.memory type。


    功能说明:
    - 只在当前文件内判断 full-write 覆盖关系。
    - 非 memory value 返回 None，调用方保守拒绝 full reset。

    使用示例:
    - memory_type = _memory_type_of(use.operation.operands[0])

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    value_type = SSAValue.get(value).type
    return value_type if isinstance(value_type, NnMemoryType) else None


def _memory_types_match(lhs: SSAValue, rhs: SSAValue) -> bool:
    """判断两个 memory value 是否拥有相同公开类型文本。


    功能说明:
    - 用于 `dma.copy` 这类整块复制的 full-write 判定。
    - 类型文本不一致时保守视为非完整 root write。

    使用示例:
    - if _memory_types_match(target, source): ...

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    lhs_type = _memory_type_of(lhs)
    rhs_type = _memory_type_of(rhs)
    return lhs_type is not None and rhs_type is not None and str(lhs_type) == str(rhs_type)


def _sizes_cover_memory_shape(sizes: Iterable[SSAValue], memory_type: NnMemoryType) -> bool:
    """判断 size operands 是否覆盖 memory type 的完整 shape。


    功能说明:
    - 只比较公开 symbol.int 类型值与 `NnMemoryType.shape` 条目文本。
    - 任一维无法机械匹配时返回 False。

    使用示例:
    - if _sizes_cover_memory_shape(op.sizes, target_type): ...

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    size_texts = tuple(_symbol_value_text(SSAValue.get(size)) for size in sizes)
    shape_texts = tuple(_symbol_expr_text(item) for item in memory_type.shape.data)
    return len(size_texts) == len(shape_texts) and all(size == shape for size, shape in zip(size_texts, shape_texts))


def _values_are_symbol_constants(values: Iterable[SSAValue], expected: str) -> bool:
    """判断一组 symbol.int operand 是否都等于指定常量文本。


    功能说明:
    - 用于 full-region `dma.deslice/view/subview` 的 offset/stride 判定。
    - 动态、iter 或非 symbol.int operand 均保守返回 False。

    使用示例:
    - if _values_are_symbol_constants(op.strides, "1"): ...

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    return all(_symbol_value_text(SSAValue.get(value)) == expected for value in values)


def _deslice_writes_full_target(op: DmaDesliceOp) -> bool:
    """判断 `dma.deslice` 是否完整覆盖 target root。


    功能说明:
    - offsets 必须全 0，strides 必须全 1，sizes 必须等于 target shape。
    - 无法机械证明时不把 `dma.deslice` 作为 full reset。

    使用示例:
    - if _deslice_writes_full_target(deslice_op): ...

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    target_type = _memory_type_of(SSAValue.get(op.target))
    if target_type is None:
        return False
    return (
        _values_are_symbol_constants(tuple(SSAValue.get(value) for value in op.offsets), "0")
        and _values_are_symbol_constants(tuple(SSAValue.get(value) for value in op.strides), "1")
        and _sizes_cover_memory_shape(tuple(SSAValue.get(value) for value in op.sizes), target_type)
    )


def _alias_op_covers_source(op: Operation) -> bool:
    """判断 alias result 是否覆盖 source root 的完整可读内容。


    功能说明:
    - `dma.reshape` 视为整块重解释，写入 result 可覆盖 source root。
    - `dma.view` 只有在 result/source 类型一致、offset 全 0 且 stride 全 1 时视为整块覆盖。
    - `dma.subview` 默认是 byte pool 的局部 typed view；只有 source/result 类型一致且范围完整时才视为整块覆盖。

    使用示例:
    - covers_root = _alias_op_covers_source(view_op)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    if isinstance(op, DmaReshapeOp):
        return _memory_types_match(SSAValue.get(op.source), op.result)
    if isinstance(op, DmaViewOp):
        return (
            _memory_types_match(SSAValue.get(op.source), op.result)
            and _values_are_symbol_constants(tuple(SSAValue.get(value) for value in op.offsets), "0")
            and _values_are_symbol_constants(tuple(SSAValue.get(value) for value in op.stride), "1")
        )
    if isinstance(op, DmaSubviewOp):
        source_value = SSAValue.get(op.source[0])
        source_type = _memory_type_of(source_value)
        return (
            source_type is not None
            and _memory_types_match(source_value, op.result)
            and _values_are_symbol_constants(tuple(SSAValue.get(value) for value in op.offset), "0")
            and _values_are_symbol_constants(tuple(SSAValue.get(value) for value in op.stride), "1")
            and _sizes_cover_memory_shape(tuple(SSAValue.get(value) for value in op.size), source_type)
        )
    return False


def _write_use_covers_root(use: Use, *, alias_covers_root: bool) -> bool:
    """判断 WRITE use 是否可作为 alloc root 的 full reset。


    功能说明:
    - alias result 只有覆盖 source root 时，写入 alias 才能证明 root 被完整 reset。
    - `dma.fill`、`dma.broadcast` target、`dma.slice` target 与 `kernel.*` out 视为完整写入当前 memory value。
    - `dma.copy` / `dma.deslice` 需要额外证明整块覆盖；partial write 不能证明后续 root read。

    使用示例:
    - full_write = _write_use_covers_root(use, alias_covers_root=True)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    if not alias_covers_root:
        return False
    user = use.operation
    if isinstance(user, (DmaFillOp, DmaBroadcastOp, DmaSliceOp)) and use.index == 0:
        return True
    if isinstance(user, DmaCopyOp) and use.index == 0:
        return _memory_types_match(SSAValue.get(user.target), SSAValue.get(user.source))
    if isinstance(user, DmaDesliceOp) and use.index == 0:
        return _deslice_writes_full_target(user)
    return user.name.startswith("kernel.") and MemoryEffectKind.WRITE in (_effect_kinds_for_use(use) or set())


def _is_direct_legacy_output_scratch_use(use: Use, loop_block: Block) -> bool:
    """判断 use 是否为同 owner body 内 legacy output scratch 搬出。


    功能说明:
    - 仅允许 `dma.deslice(..., source=buf, ...)` 直接位于当前 owner `symbol.for` body。
    - descendant region 内的 `dma.deslice source` 必须按公开 MemoryEffect READ 进入 lifecycle proof。

    使用示例:
    - if _is_direct_legacy_output_scratch_use(use, loop_block): ...

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    return isinstance(use.operation, DmaDesliceOp) and use.index == 1 and _operation_parent_block(use.operation) is loop_block


def _memory_event_from_use(use: Use, *, alias_covers_root: bool, loop_block: Block) -> _MemoryEvent | None:
    """把公开 MemoryEffect use 转成生命周期事件。


    功能说明:
    - 只接受 READ/WRITE effect；unknown、ALLOC/FREE 或空 effect 均返回 None。
    - `full_write` 单独记录，供 nested loop read proof 使用。
    - 同 owner body 直接 `dma.deslice source` 保留旧 output scratch 例外，不参与 nested reset proof。
    - descendant region 内 `dma.deslice source` 仍按公开 READ effect 强制要求此前 full reset/write。

    使用示例:
    - event = _memory_event_from_use(use, alias_covers_root=True, loop_block=loop_block)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    if _is_direct_legacy_output_scratch_use(use, loop_block):
        return _MemoryEvent(use=use, effects=frozenset({MemoryEffectKind.WRITE}), full_write=False)
    kinds = _effect_kinds_for_use(use)
    if kinds is None or not kinds or not kinds <= {MemoryEffectKind.READ, MemoryEffectKind.WRITE}:
        return None
    full_write = (
        MemoryEffectKind.WRITE in kinds
        and MemoryEffectKind.READ not in kinds
        and _write_use_covers_root(use, alias_covers_root=alias_covers_root)
    )
    return _MemoryEvent(use=use, effects=frozenset(kinds), full_write=full_write)


def _data_events_are_reset_before_read(data_events: tuple[_MemoryEvent, ...], loop_block: Block) -> bool:
    """校验生命周期 data event 中每个 read 前已有支配它的 full reset/write。


    功能说明:
    - 只对公开 `MemoryEffect` 可判定的 use 强制顺序证明。
    - full write 可位于同 block read 前，也可位于包住 read 的 nested op 前。
    - nested loop 内 write 不证明 loop 后 read；sibling region write 不证明 merge read。
    - `READ+WRITE` 的同值 use 不得自证 reset/write；只有同一 block 中此前已有独立 `WRITE` 时才允许继续。
    - 任一 read 出现在对应 block 的 reset/write 前时拒绝外提。

    使用示例:
    - _data_events_are_reset_before_read(events, loop_block)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    for event in data_events:
        user = event.use.operation
        if not _operation_is_in_block_or_descendant(user, loop_block):
            return False

    full_writes = tuple(event for event in data_events if event.full_write)
    for event in data_events:
        if MemoryEffectKind.READ not in event.effects:
            continue
        if not any(_op_dominates_op(write_event.use.operation, event.use.operation) for write_event in full_writes):
                return False
    return True


def _collect_alias_data_events(
    alias_op: Operation,
    loop_block: Block,
    visited: frozenset[Operation],
    *,
    alias_covers_root: bool,
) -> tuple[_MemoryEvent, ...] | None:
    """收集 alias result 最终承接的可捕获 lifecycle event。


    功能说明:
    - `dma.view`、`dma.reshape`、`dma.subview` result 只能被同一 owner loop body 或其 descendant
      region 内的可捕获 memory use 或下一层受支持 alias op 使用。
    - owner loop 外、sibling region、`symbol.yield`、`func.return` 或未知 direct use 一律让外提 no-op。
    - 返回的 event 用于证明 matching free 晚于 alias 链真实消费，且 partial alias write 不被当作 root reset。

    使用示例:
    - events = _collect_alias_data_events(view_op, loop_block, frozenset(), alias_covers_root=True)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    if alias_op in visited:
        return None
    if not _operation_is_in_block_or_descendant(alias_op, loop_block):
        return None
    if len(alias_op.results) != 1:
        return None
    result_uses = _collect_direct_uses(alias_op.results[0])
    if not result_uses:
        return None

    next_visited = visited | frozenset((alias_op,))
    data_events: list[_MemoryEvent] = []
    next_alias_covers_root = alias_covers_root and _alias_op_covers_source(alias_op)
    for use in result_uses:
        if not _operation_is_in_block_or_descendant(use.operation, loop_block):
            return None
        if _is_metadata_query_use(use):
            continue
        if _is_supported_alias_result_use(use):
            event = _memory_event_from_use(use, alias_covers_root=next_alias_covers_root, loop_block=loop_block)
            if event is None:
                return None
            data_events.append(event)
            continue
        if _is_supported_alias_source_use(use):
            nested_data_events = _collect_alias_data_events(
                use.operation,
                loop_block,
                next_visited,
                alias_covers_root=next_alias_covers_root,
            )
            if nested_data_events is None:
                return None
            data_events.extend(nested_data_events)
            continue
        return None
    return tuple(data_events)


def _build_hoist_use_plan(uses: Iterable[Use], loop_block: Block) -> _HoistUsePlan | None:
    """判断 alloc 结果的 direct use 集合是否满足当前公开外提条件。


    功能说明:
    - 当前公开语义要求 alloc 至少存在一个 data use。
    - data use 必须位于同一 loop body 或其非 `symbol.for` descendant region 内，且属于公开 MemoryEffect
      可判定的 read/write use，或受支持 alias 链最终导向的可捕获 use。
    - lifecycle use 必须存在同一 loop body 内唯一 `dma.free`，且必须晚于所有 data use。
    - 多个 free、nested free、跨 loop free 或未知 direct use 均保持 no-op。

    使用示例:
    - plan = _build_hoist_use_plan(_collect_direct_uses(alloc_op.result), loop_block)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    collected_uses = tuple(uses)
    if not collected_uses:
        return None

    data_events: list[_MemoryEvent] = []
    free_ops: list[DmaFreeOp] = []
    for use in collected_uses:
        user = use.operation
        if not _operation_is_in_block_or_descendant(user, loop_block):
            return None
        if _is_metadata_query_use(use):
            continue
        if _is_supported_lifecycle_data_use(use):
            event = _memory_event_from_use(use, alias_covers_root=True, loop_block=loop_block)
            if event is None:
                return None
            data_events.append(event)
            continue
        if _is_supported_alias_source_use(use):
            alias_data_events = _collect_alias_data_events(
                user,
                loop_block,
                frozenset(),
                alias_covers_root=True,
            )
            if alias_data_events is None:
                return None
            data_events.extend(alias_data_events)
            continue
        if isinstance(user, DmaFreeOp) and use.index == 0 and _operation_parent_block(user) is loop_block:
            free_ops.append(user)
            continue
        return None

    if not data_events or len(free_ops) != 1:
        return None
    free_op = free_ops[0]
    data_event_tuple = tuple(data_events)
    if not _data_events_are_reset_before_read(data_event_tuple, loop_block):
        return None
    if not _free_follows_data_events(free_op, data_event_tuple, loop_block):
        return None
    return _HoistUsePlan(data_events=data_event_tuple, free_op=free_op)


class DmaAllocInSymbolForHoistPattern(RewritePattern):
    """`symbol.for` 内 `dma.alloc` 外提 pattern。


    功能说明:
    - 只匹配当前 `symbol.for` body block 顶层的 `dma.alloc`。
    - 满足 shape invariant、direct use 白名单与唯一匹配 free 时，把 alloc 外提到所属 `symbol.for` 之前。
    - 若存在合法匹配 free，同步把 free 移到所属 `symbol.for` 之后，保持生命周期成对外提。
    - IR before:
      ```mlir
      symbol.for %i = %c0 to %n step %c1 {
        %buf = "dma.alloc"() : () -> !nn.memory<value>
        "dma.fill"(%buf, %zero) : (value, f32) -> ()
        "dma.free"(%buf) : (value) -> ()
      }
      ```
    - IR after:
      ```mlir
      %buf = "dma.alloc"() : () -> !nn.memory<value>
      symbol.for %i = %c0 to %n step %c1 {
        "dma.fill"(%buf, %zero) : (value, f32) -> ()
      }
      "dma.free"(%buf) : (value) -> ()
      ```
    - no-op unchanged after：shape 依赖 loop-carried 值、缺少唯一 `dma.free` 或首次 data use 不安全时，上述 before IR 保持不变。

    使用示例:
    - pattern = DmaAllocInSymbolForHoistPattern()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: DmaAllocOp, rewriter: PatternRewriter, /) -> None:
        """对满足公开条件的 loop 内 `dma.alloc` 执行外提。


        功能说明:
        - 仅当 alloc 位于 `symbol.for` 直接 body block 内时继续。
        - shape 或 direct use 任一条件不满足时保持 no-op。
        - 外提后复用原 op/result，不新建等价 alloc；合法 free 也复用原 op。

        使用示例:
        - DmaAllocInSymbolForHoistPattern().match_and_rewrite(op, rewriter)

        关联文件:
        - spec: spec/pass/symbol_buffer_hoist.md
        - test: test/passes/test_symbol_buffer_hoist.py
        - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
        """

        loop_block = op.parent_block()
        if loop_block is None:
            return
        symbol_for = loop_block.parent_op()
        if not isinstance(symbol_for, SymbolForOp):
            return
        if not _shape_is_loop_invariant(op, symbol_for):
            return
        use_plan = _build_hoist_use_plan(_collect_direct_uses(op.result), loop_block)
        if use_plan is None:
            return
        op.detach()
        rewriter.insert_op(op, InsertPoint.before(symbol_for))
        if use_plan.free_op is not None:
            use_plan.free_op.detach()
            rewriter.insert_op(use_plan.free_op, InsertPoint.after(symbol_for))
        rewriter.notify_op_modified(symbol_for)


def _alias_operands(op: Operation) -> tuple[SSAValue, ...]:
    """返回 alias op 外提所需检查的全部 operand。


    功能说明:
    - `dma.view` 检查 source、offsets、shape、stride。
    - `dma.reshape` 检查 source 与 shape。
    - `dma.subview` 检查 source、offset、size、stride。

    使用示例:
    - operands = _alias_operands(view_op)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    if isinstance(op, DmaViewOp):
        return (SSAValue.get(op.source), *tuple(op.offsets), *tuple(op.shape), *tuple(op.stride))
    if isinstance(op, DmaReshapeOp):
        return (SSAValue.get(op.source), *tuple(op.shape))
    if isinstance(op, DmaSubviewOp):
        return (*tuple(op.source), *tuple(op.offset), *tuple(op.size), *tuple(op.stride))
    return ()


def _alias_result_uses_are_supported(op: Operation, loop_block: Block) -> bool:
    """判断 alias op result 是否只流向当前 loop 直接 body 内的白名单 use。


    功能说明:
    - 至少需要一个 direct use，避免外提无用或逃逸 alias。
    - 支持 alias result 继续喂给 `dma.view`、`dma.reshape`、`dma.subview`，后续 pattern 会继续单 op 外提。
    - 支持 alias result 被同一 loop body 或 descendant region 内的公开 MemoryEffect consumer 捕获。
    - `kernel.*` consumer 只有在公开 MemoryEffect 能判定 alias result 作为读/写 operand 时才允许。
    - 未知 use、逃逸 use 或无 MemoryEffect 的 consumer 保守 no-op，避免把副作用规则做宽。

    使用示例:
    - if _alias_result_uses_are_supported(view_op, loop_block): ...

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    if len(op.results) != 1:
        return False
    result_uses = _collect_direct_uses(op.results[0])
    if not result_uses:
        return False
    for use in result_uses:
        if not _operation_is_in_block_or_descendant(use.operation, loop_block):
            return False
        if _is_supported_alias_result_use(use):
            continue
        if _is_supported_alias_source_use(use):
            continue
        return False
    return True


def _hoist_alias_op_if_safe(op: Operation, rewriter: PatternRewriter) -> None:
    """在满足公开边界时把单个 alias op 外提一层。


    功能说明:
    - 仅处理当前 `symbol.for` 直接 body 内的 alias op。
    - source 与布局 operand 必须全部支配当前 `symbol.for`。
    - result use 必须留在当前 loop 直接 body 的公开白名单内。

    使用示例:
    - _hoist_alias_op_if_safe(view_op, rewriter)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    loop_block = op.parent_block()
    if loop_block is None:
        return
    symbol_for = loop_block.parent_op()
    if not isinstance(symbol_for, SymbolForOp):
        return
    if not all(_value_dominates_symbol_for(operand, symbol_for) for operand in _alias_operands(op)):
        return
    if not _alias_result_uses_are_supported(op, loop_block):
        return
    op.detach()
    rewriter.insert_op(op, InsertPoint.before(symbol_for))
    rewriter.notify_op_modified(symbol_for)


class DmaViewInSymbolForHoistPattern(RewritePattern):
    """`symbol.for` 内 `dma.view` 单 op 外提 pattern。


    功能说明:
    - 只在 source 与 offset/shape/stride 均对当前 loop invariant 时外提一层。
    - IR 变换：`symbol.for { %v = dma.view(...); use(%v) }` 变为 `%v = dma.view(...); symbol.for { use(%v) }`。
    - no-op：operand 不支配当前 loop 或 result use 不在白名单时保持原 IR。
    - IR before:
      ```mlir
      symbol.for %i = %c0 to %n step %c1 {
        %v = "dma.view"(%src, %off, %size, %stride) : (...) -> !nn.memory<value>
        "kernel.use"(%v) : (value) -> ()
      }
      ```
    - IR after:
      ```mlir
      %v = "dma.view"(%src, %off, %size, %stride) : (...) -> !nn.memory<value>
      symbol.for %i = %c0 to %n step %c1 {
        "kernel.use"(%v) : (value) -> ()
      }
      ```
    - no-op unchanged after：offset/shape/stride 依赖当前 loop 或 result use 逃逸时，上述 before IR 保持不变。

    使用示例:
    - pattern = DmaViewInSymbolForHoistPattern()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: DmaViewOp, rewriter: PatternRewriter, /) -> None:
        """对满足条件的 `dma.view` 执行单层外提。


        功能说明:
        - 不新增 loop argument；loop body 直接捕获外提后的 SSA result。
        - 任一 operand 不支配当前 loop 或 result use 不在白名单时保持 no-op。

        使用示例:
        - DmaViewInSymbolForHoistPattern().match_and_rewrite(op, rewriter)

        关联文件:
        - spec: spec/pass/symbol_buffer_hoist.md
        - test: test/passes/test_symbol_buffer_hoist.py
        - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
        """

        _hoist_alias_op_if_safe(op, rewriter)


class DmaReshapeInSymbolForHoistPattern(RewritePattern):
    """`symbol.for` 内 `dma.reshape` 单 op 外提 pattern。


    功能说明:
    - 只在 source 与 shape 均对当前 loop invariant 时外提一层。
    - IR 变换：`symbol.for { %r = dma.reshape(...); use(%r) }` 变为 `%r = dma.reshape(...); symbol.for { use(%r) }`。
    - no-op：shape 来自当前 loop body、loop iterator 或 loop-carried 值时保持原 IR。
    - IR before:
      ```mlir
      symbol.for %i = %c0 to %n step %c1 {
        %r = "dma.reshape"(%src, %m, %k) : (...) -> !nn.memory<value>
        "kernel.use"(%r) : (value) -> ()
      }
      ```
    - IR after:
      ```mlir
      %r = "dma.reshape"(%src, %m, %k) : (...) -> !nn.memory<value>
      symbol.for %i = %c0 to %n step %c1 {
        "kernel.use"(%r) : (value) -> ()
      }
      ```
    - no-op unchanged after：shape 依赖当前 loop 时，上述 before IR 保持不变。

    使用示例:
    - pattern = DmaReshapeInSymbolForHoistPattern()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: DmaReshapeOp, rewriter: PatternRewriter, /) -> None:
        """对满足条件的 `dma.reshape` 执行单层外提。


        功能说明:
        - 不新增 loop argument；loop body 直接捕获外提后的 SSA result。
        - shape 来自当前 loop body、loop iterator 或 loop-carried 值时保持 no-op。

        使用示例:
        - DmaReshapeInSymbolForHoistPattern().match_and_rewrite(op, rewriter)

        关联文件:
        - spec: spec/pass/symbol_buffer_hoist.md
        - test: test/passes/test_symbol_buffer_hoist.py
        - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
        """

        _hoist_alias_op_if_safe(op, rewriter)


class DmaSubviewInSymbolForHoistPattern(RewritePattern):
    """`symbol.for` 内 `dma.subview` 单 op 外提 pattern。


    功能说明:
    - 只在 source、offset、size、stride 均对当前 loop invariant 时外提一层。
    - IR 变换：`symbol.for { %s = dma.subview(...); use(%s) }` 变为 `%s = dma.subview(...); symbol.for { use(%s) }`。
    - no-op：offset/size/stride 来自当前 loop body 时保持原 IR。
    - IR before:
      ```mlir
      symbol.for %i = %c0 to %n step %c1 {
        %s = "dma.subview"(%src, %off, %size, %stride) : (...) -> !nn.memory<value>
        "kernel.use"(%s) : (value) -> ()
      }
      ```
    - IR after:
      ```mlir
      %s = "dma.subview"(%src, %off, %size, %stride) : (...) -> !nn.memory<value>
      symbol.for %i = %c0 to %n step %c1 {
        "kernel.use"(%s) : (value) -> ()
      }
      ```
    - no-op unchanged after：offset/size/stride 依赖当前 loop 时，上述 before IR 保持不变。

    使用示例:
    - pattern = DmaSubviewInSymbolForHoistPattern()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: DmaSubviewOp, rewriter: PatternRewriter, /) -> None:
        """对满足条件的 `dma.subview` 执行单层外提。


        功能说明:
        - 不新增 loop argument；loop body 直接捕获外提后的 SSA result。
        - offset/size/stride 来自当前 loop body 时保持 no-op。

        使用示例:
        - DmaSubviewInSymbolForHoistPattern().match_and_rewrite(op, rewriter)

        关联文件:
        - spec: spec/pass/symbol_buffer_hoist.md
        - test: test/passes/test_symbol_buffer_hoist.py
        - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
        """

        _hoist_alias_op_if_safe(op, rewriter)


def get_symbol_buffer_hoist_patterns() -> list[RewritePattern]:
    """返回 `symbol-buffer-hoist` 公开 pattern 列表。


    功能说明:
    - 公开返回 `dma.alloc/free` pattern 与 alias op pattern 实例。
    - 返回值顺序固定为 alloc/free、view、reshape、subview，便于 greedy walker 逐层收敛。

    使用示例:
    - patterns = get_symbol_buffer_hoist_patterns()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    return [
        DmaAllocInSymbolForHoistPattern(),
        DmaViewInSymbolForHoistPattern(),
        DmaReshapeInSymbolForHoistPattern(),
        DmaSubviewInSymbolForHoistPattern(),
    ]


def _rewrite_module_once(ctx: Context, module: ModuleOp, *, fold: bool) -> None:
    """对 module 执行一轮 `symbol-buffer-hoist` pattern walker。


    功能说明:
    - 当前文件内部 helper；保持公开 pass API 不变。
    - 单轮 walker 仍遵守每个 pattern 只移动一个 op、一层 loop 的边界。

    使用示例:
    - _rewrite_module_once(ctx, module, fold=True)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    PatternRewriteWalker(
        GreedyRewritePatternApplier(
            get_symbol_buffer_hoist_patterns(),
            ctx=ctx,
            folding_enabled=fold,
            dce_enabled=False,
        )
    ).rewrite_module(module)


def _rewrite_module_to_fixed_point(ctx: Context, module: ModuleOp, *, fold: bool) -> None:
    """重复执行 walker，直到 alias op 外提达到稳定态。


    功能说明:
    - `dma.view` 外提后，依赖该 view 的 `dma.reshape` 可能才满足支配条件。
    - 通过模块文本稳定性检测追加有限轮收敛，避免单轮遍历漏掉后继 alias op。
    - 每轮仍复用公开 pattern 列表，不引入跨文件私有 API 或新公开入口。

    使用示例:
    - _rewrite_module_to_fixed_point(ctx, module, fold=True)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    for _iteration in range(8):
        before = str(module)
        _rewrite_module_once(ctx, module, fold=fold)
        if str(module) == before:
            return


class SymbolBufferHoistPass(Pass):
    """`symbol-buffer-hoist` pass。


    功能说明:
    - 通过 pattern walker fixed point 处理 module 中满足公开条件的 `dma.alloc/free` 与 alias op 外提。
    - 非 `builtin.module` 输入直接复用共享 `KernelCodeError("module must be builtin.module")`。
    - 最终 verifier 失败统一转成 `KernelCodeError("SymbolBufferHoistVerifierError: ...")`。

    使用示例:
    - from xdsl.context import Context
    - from xdsl.dialects.builtin import ModuleOp
    - module = ModuleOp([])
    - SymbolBufferHoistPass().apply(Context(), module)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - test: test/passes/test_registry.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    name = "symbol-buffer-hoist"

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 `symbol-buffer-hoist` ModulePass。


        功能说明:
        - 只处理 `builtin.module`。
        - 用 greedy pattern walker 把 `symbol.for` 内可安全外提的 alloc/alias op 推进到稳定态。
        - 最终统一做一次 `module.verify()`，保持公开失败前缀稳定。

        使用示例:
        - SymbolBufferHoistPass().apply(Context(), module)

        关联文件:
        - spec: spec/pass/symbol_buffer_hoist.md
        - test: test/passes/test_symbol_buffer_hoist.py
        - test: test/passes/test_registry.py
        - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
        """

        module = ensure_builtin_module(module)
        if ctx.get_optional_dialect(Symbol.name) is None:
            ctx.load_dialect(Symbol)
        _rewrite_module_to_fixed_point(ctx, module, fold=self.fold)
        try:
            module.verify()
        except VerifyException as exc:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"SymbolBufferHoistVerifierError: {exc}") from exc

__all__ = [
    "DmaAllocInSymbolForHoistPattern",
    "DmaViewInSymbolForHoistPattern",
    "DmaReshapeInSymbolForHoistPattern",
    "DmaSubviewInSymbolForHoistPattern",
    "get_symbol_buffer_hoist_patterns",
    "SymbolBufferHoistPass",
]
