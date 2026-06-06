"""symbol-buffer-hoist pass.


功能说明:
- 定义 `symbol-buffer-hoist` 的公开 pass、公开 pattern 与公开 pattern getter。
- 只在 `symbol.for` 单 block 循环体内识别 `dma.alloc`，并在 shape 明确不依赖 loop 内 SSA、
  直接 use 仅属于输入 staging / output scratch、公开 `MemoryEffect` 读写、`dma.broadcast`
  或受支持 alias producer，且存在唯一匹配 `dma.free` 时，将其与 `dma.free` 成对外提一层。
- 当同一 `symbol.for` 直接 body 内存在唯一匹配 `dma.free` 且该 free 晚于所有 data use 时，
  外提 `dma.alloc` 的同时把对应 `dma.free` 移到同一 `symbol.for` 之后。
- 对 source、offset/shape/stride 等 operand 均支配当前 `symbol.for` 的 `dma.view`、`dma.reshape`、
  `dma.subview` 和 `dma.reinterpret`，作为独立 alias op 单次外提一层；`dma.reinterpret`
  也参与 alias use chain 与 full-cover 生命周期证明；fixed-point 驱动允许同一 alias op 跨 nested loop
  逐层外提到最近安全位置。
- `symbol.get_dim` / `symbol.get_stride` 是 Pure metadata query，只读取 alias 或 memory 的 shape / stride
  信息，不参与生命周期数据 use，也不能单独证明 reset/write。
- `dma.alloc/free` 外提通过 `MemoryEffect` 证明生命周期：首次 read 前必须已有同一 region block 内的
  full reset/write；nested `symbol.for` 内 data use 不再一律 no-op，只要每个 read 均被支配它的 full write
  覆盖，alloc/free 就可以通过 fixed-point 逐层外提。`READ+WRITE` 的同值 use 不能自证 reset/write，
  但 `kernel.matmul` 动态 acc 形如 `iter != start` 时可证明首轮覆盖写；unknown effect、读先于写、多 free
  或 nested free 均保持 no-op。
- `dma.reinterpret` logical alias 的 partial write 只证明同一 logical scope 后续 read；`offset=0`、同 backing、
  同元素数且 contiguous 的等价 logical alias 可共享 reset proof，但不会升级为 backing root full reset。
- 失败边界统一复用 `KernelCodeError(module="pass")`；不新增专题专属错误类型，也不承诺额外 compat path。

API 列表:
- `class DmaAllocWithMatmulFirstUseHoistPattern()`
- `DmaAllocWithMatmulFirstUseHoistPattern.match_and_rewrite(op: DmaAllocOp, rewriter: PatternRewriter) -> None`
- `class DmaAllocInSymbolForHoistPattern()`
- `DmaAllocInSymbolForHoistPattern.match_and_rewrite(op: DmaAllocOp, rewriter: PatternRewriter) -> None`
- `class DmaViewInSymbolForHoistPattern()`
- `DmaViewInSymbolForHoistPattern.match_and_rewrite(op: DmaViewOp, rewriter: PatternRewriter) -> None`
- `class DmaReshapeInSymbolForHoistPattern()`
- `DmaReshapeInSymbolForHoistPattern.match_and_rewrite(op: DmaReshapeOp, rewriter: PatternRewriter) -> None`
- `class DmaSubviewInSymbolForHoistPattern()`
- `DmaSubviewInSymbolForHoistPattern.match_and_rewrite(op: DmaSubviewOp, rewriter: PatternRewriter) -> None`
- `class DmaReinterpretInSymbolForHoistPattern()`
- `DmaReinterpretInSymbolForHoistPattern.match_and_rewrite(op: DmaReinterpretOp, rewriter: PatternRewriter) -> None`
- `get_symbol_buffer_hoist_patterns() -> list[RewritePattern]`
- `class SymbolBufferHoistPass(fold: bool = True)`
- `SymbolBufferHoistPass.name: str`
- `SymbolBufferHoistPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from xdsl.context import Context
- from xdsl.dialects.builtin import ModuleOp
- from kernel_gen.passes.hoist.symbol_buffer_hoist import SymbolBufferHoistPass
- module = ModuleOp([])
- SymbolBufferHoistPass().apply(Context(), module)

关联文件:
- spec: spec/pass/symbol_buffer_hoist.md
- test: test/passes/test_symbol_buffer_hoist.py
- test: test/passes/test_registry.py
- 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
"""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import BlockArgument, Operation, SSAValue, Use
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
    DmaReinterpretOp,
    DmaReshapeOp,
    DmaSliceOp,
    DmaSubviewOp,
    DmaViewOp,
)
from kernel_gen.dialect.kernel import KernelMatmulOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import Symbol, SymbolExprAttr, SymbolForOp, SymbolValueType
from kernel_gen.passes.common import ensure_builtin_module
from kernel_gen.passes.pass_manager import Pass


@dataclass(frozen=True)
class _MemoryEvent:
    """alloc lifecycle proof 中的单次 memory event。


    功能说明:
    - 固定表示一次 READ/WRITE use 及其 logical access scope。
    - 用结构化字段替代无类型字符串 key dict，避免两个 alloc pattern 维护同一组字段名。
    - 该模型只在当前文件内部使用，不进入公开 API。

    使用示例:
    - event = _MemoryEvent(use=use, effects=frozenset(kinds), access_scope=scope, full_write=True, full_write_scope=None, self_reset=False)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    use: Use
    effects: frozenset[MemoryEffectKind]
    access_scope: SSAValue | tuple[SSAValue, str]
    full_write: bool
    full_write_scope: SSAValue | tuple[SSAValue, str] | None
    self_reset: bool


def _value_dominates_symbol_for(value: SSAValue, symbol_for: SymbolForOp) -> bool:
    """判断 SSA 值是否在当前 `symbol.for` 前可见。


    功能说明:
    - 只接受定义在当前 loop body 外、且支配当前 `symbol.for` 的 SSA 值。
    - 当前 loop body、nested region 或 sibling block 内定义的值都保守视为不可外提。
    - 外层 loop body 中位于当前 `symbol.for` 前的值允许作为“当前层” invariant。

    使用示例:
    - if not _value_dominates_symbol_for(shape_value, symbol_for): return

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    owner_loop_block = symbol_for.body.blocks[0]
    if isinstance(value, BlockArgument):
        return value.owner is not owner_loop_block and value.owner.is_ancestor(symbol_for)
    owner = value.owner
    if not isinstance(owner, Operation):
        return True
    owner_block = owner.parent_block()
    if owner_block is None:
        return True
    if owner_block is owner_loop_block or owner_loop_block.is_ancestor(owner):
        return False
    if owner_block is symbol_for.parent_block():
        return owner.is_before_in_block(symbol_for)
    ancestor = owner_block.find_ancestor_op_in_block(symbol_for)
    return ancestor is not None and owner is not ancestor and owner.is_before_in_block(ancestor)


def _hoist_alias_op_if_safe(op: Operation, rewriter: PatternRewriter) -> None:
    """在满足公开边界时把单个 alias op 外提一层。


    功能说明:
    - 仅处理当前 `symbol.for` 直接 body 内的 `dma.view/reshape/subview/reinterpret` alias op。
    - source 与布局 operand 必须全部支配当前 `symbol.for`。
    - result use 必须留在当前 loop body 或 descendant region 内，并落在公开白名单中。
    - 外提后复用原 op/result，不新增 loop argument。

    使用示例:
    - _hoist_alias_op_if_safe(view_op, rewriter)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    loop_block = op.parent_block()
    if loop_block is None:
        return
    symbol_for = loop_block.parent_op()
    if not isinstance(symbol_for, SymbolForOp):
        return
    if isinstance(op, DmaViewOp):
        operands = (SSAValue.get(op.source), *tuple(op.offsets), *tuple(op.shape), *tuple(op.stride))
    elif isinstance(op, DmaReshapeOp):
        operands = (SSAValue.get(op.source), *tuple(op.shape))
    elif isinstance(op, DmaSubviewOp):
        operands = (*tuple(op.source), *tuple(op.offset), *tuple(op.size), *tuple(op.stride))
    elif isinstance(op, DmaReinterpretOp):
        operands = (SSAValue.get(op.source), SSAValue.get(op.offset), *tuple(op.shape), *tuple(op.stride))
    else:
        return
    owner_loop_block = symbol_for.body.blocks[0]
    for operand in operands:
        operand_value = SSAValue.get(operand)
        if isinstance(operand_value, BlockArgument):
            if operand_value.owner is owner_loop_block or not operand_value.owner.is_ancestor(symbol_for):
                return
            continue
        owner = operand_value.owner
        if not isinstance(owner, Operation):
            continue
        owner_block = owner.parent_block()
        if owner_block is None:
            continue
        if owner_block is owner_loop_block or owner_loop_block.is_ancestor(owner):
            return
        if owner_block is symbol_for.parent_block():
            if not owner.is_before_in_block(symbol_for):
                return
            continue
        ancestor = owner_block.find_ancestor_op_in_block(symbol_for)
        if ancestor is None or owner is ancestor or not owner.is_before_in_block(ancestor):
            return
    if len(op.results) != 1:
        return
    result_uses = tuple(op.results[0].uses)
    if not result_uses:
        return
    for use in result_uses:
        user = use.operation
        user_block = user.parent_block()
        if user_block is None or not (user_block is loop_block or loop_block.is_ancestor(user)):
            return
        if use.index == 0 and user.name in {"symbol.get_dim", "symbol.get_stride"}:
            continue
        supported_use = (
            isinstance(user, DmaSliceOp)
            and use.index == 0
            or isinstance(user, DmaDesliceOp)
            and use.index in (0, 1)
            or isinstance(user, DmaFillOp)
            and use.index == 0
            or isinstance(user, DmaCopyOp)
            and use.index in (0, 1)
            or isinstance(user, DmaBroadcastOp)
            and use.index in (0, 1)
        )
        if not supported_use and user.name.startswith("kernel."):
            effects = get_effects(user)
            if effects is not None:
                used_value = SSAValue.get(user.operands[use.index])
                kinds = {effect.kind for effect in effects if effect.value is used_value}
                supported_use = bool(kinds) and kinds <= {MemoryEffectKind.READ, MemoryEffectKind.WRITE}
        if supported_use:
            continue
        if use.index == 0 and isinstance(user, (DmaViewOp, DmaReshapeOp, DmaSubviewOp, DmaReinterpretOp)):
            continue
        return
    op.detach()
    rewriter.insert_op(op, InsertPoint.before(symbol_for))
    rewriter.notify_op_modified(symbol_for)


def _alias_op_covers_source(alias_op: Operation) -> bool:
    """判断 alias op 是否逻辑覆盖其 source。


    功能说明:
    - 统一 `dma.reshape/view/subview/reinterpret` 的 full-cover 证明，供 alloc lifecycle proof 复用。
    - 返回 `False` 表示 alias 结果只能作为局部 logical scope，不能升级成 backing root full write。
    - 不修改 IR，也不访问当前文件外的非公开 API。

    使用示例:
    - if _alias_op_covers_source(alias_op): ...

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    if isinstance(alias_op, DmaReshapeOp):
        lhs_type = SSAValue.get(alias_op.source).type
        rhs_type = alias_op.result.type
        return (
            isinstance(lhs_type, NnMemoryType)
            and isinstance(rhs_type, NnMemoryType)
            and lhs_type.space == rhs_type.space
            and lhs_type.shape == rhs_type.shape
            and lhs_type.stride == rhs_type.stride
            and lhs_type.element_type == rhs_type.element_type
        )
    if isinstance(alias_op, DmaViewOp):
        lhs_type = SSAValue.get(alias_op.source).type
        rhs_type = alias_op.result.type
        offsets_are_zero = True
        for offset_value in alias_op.offsets:
            offset_type = SSAValue.get(offset_value).type
            if not isinstance(offset_type, SymbolValueType) or str(offset_type.get_value()) != "0":
                offsets_are_zero = False
                break
        strides_are_one = True
        for stride_value in alias_op.stride:
            stride_type = SSAValue.get(stride_value).type
            if not isinstance(stride_type, SymbolValueType) or str(stride_type.get_value()) != "1":
                strides_are_one = False
                break
        return (
            isinstance(lhs_type, NnMemoryType)
            and isinstance(rhs_type, NnMemoryType)
            and lhs_type.space == rhs_type.space
            and lhs_type.shape == rhs_type.shape
            and lhs_type.stride == rhs_type.stride
            and lhs_type.element_type == rhs_type.element_type
            and offsets_are_zero
            and strides_are_one
        )
    if isinstance(alias_op, DmaSubviewOp):
        source_value = SSAValue.get(alias_op.source[0])
        source_type = source_value.type
        result_type = alias_op.result.type
        offsets_are_zero = True
        for offset_value in alias_op.offset:
            offset_type = SSAValue.get(offset_value).type
            if not isinstance(offset_type, SymbolValueType) or str(offset_type.get_value()) != "0":
                offsets_are_zero = False
                break
        strides_are_one = True
        for stride_value in alias_op.stride:
            stride_type = SSAValue.get(stride_value).type
            if not isinstance(stride_type, SymbolValueType) or str(stride_type.get_value()) != "1":
                strides_are_one = False
                break
        size_texts = []
        for size_value in alias_op.size:
            size_type = SSAValue.get(size_value).type
            size_texts.append(str(size_type.get_value()) if isinstance(size_type, SymbolValueType) else None)
        shape_texts = []
        if isinstance(source_type, NnMemoryType):
            for shape_item in source_type.shape.data:
                shape_texts.append(shape_item.expr.data if isinstance(shape_item, SymbolExprAttr) else str(shape_item))
        return (
            isinstance(source_type, NnMemoryType)
            and isinstance(result_type, NnMemoryType)
            and source_type.space == result_type.space
            and source_type.shape == result_type.shape
            and source_type.stride == result_type.stride
            and source_type.element_type == result_type.element_type
            and offsets_are_zero
            and strides_are_one
            and len(size_texts) == len(shape_texts)
            and all(size == shape for size, shape in zip(size_texts, shape_texts))
        )
    if isinstance(alias_op, DmaReinterpretOp):
        source_type = SSAValue.get(alias_op.source).type
        result_type = alias_op.result.type
        source_numel = None
        result_numel = None
        if isinstance(source_type, NnMemoryType):
            factors = []
            unknown_dim = False
            for dim in source_type.shape.data:
                dim_text = dim.expr.data if isinstance(dim, SymbolExprAttr) else str(dim)
                if dim_text == "?":
                    unknown_dim = True
                    break
                if dim_text != "1":
                    factors.append(dim_text)
            if not unknown_dim:
                source_numel = "*".join(factors) if factors else "1"
        if isinstance(result_type, NnMemoryType):
            factors = []
            unknown_dim = False
            for dim in result_type.shape.data:
                dim_text = dim.expr.data if isinstance(dim, SymbolExprAttr) else str(dim)
                if dim_text == "?":
                    unknown_dim = True
                    break
                if dim_text != "1":
                    factors.append(dim_text)
            if not unknown_dim:
                result_numel = "*".join(factors) if factors else "1"
        expected_strides = None
        if isinstance(result_type, NnMemoryType):
            expected = []
            running = "1"
            unknown_dim = False
            for dim in reversed(result_type.shape.data):
                expected.append(running)
                dim_text = dim.expr.data if isinstance(dim, SymbolExprAttr) else str(dim)
                if dim_text == "?":
                    unknown_dim = True
                    break
                if dim_text != "1":
                    running = dim_text if running == "1" else f"{dim_text}*{running}"
            if not unknown_dim:
                expected.reverse()
                expected_strides = tuple(expected)
        actual_strides = None
        if isinstance(result_type, NnMemoryType):
            actual_strides = tuple(
                stride.expr.data if isinstance(stride, SymbolExprAttr) else str(stride)
                for stride in result_type.stride.data
            )
        offset_type = SSAValue.get(alias_op.offset).type
        return (
            isinstance(source_type, NnMemoryType)
            and isinstance(result_type, NnMemoryType)
            and source_type.element_type == result_type.element_type
            and source_type.space.space.data == result_type.space.space.data
            and isinstance(offset_type, SymbolValueType)
            and str(offset_type.get_value()) == "0"
            and source_numel is not None
            and source_numel == result_numel
            and expected_strides is not None
            and actual_strides == expected_strides
        )
    return False


def _reinterpret_logical_access_scope(access_value: SSAValue) -> SSAValue | tuple[SSAValue, str]:
    """返回 READ/WRITE event 使用的 logical access scope。


    功能说明:
    - 对普通 value 返回自身，维持 root-scope 证明。
    - 对 contiguous zero-offset `dma.reinterpret` 返回 `(source, result_numel)`，允许同一 logical scope 内证明 reset。
    - 该 helper 只产生 proof key，不改变 alias op 的 IR 位置或结果。

    使用示例:
    - access_scope = _reinterpret_logical_access_scope(access_value)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    access_owner = access_value.owner
    if not isinstance(access_owner, DmaReinterpretOp):
        return access_value
    source_type = SSAValue.get(access_owner.source).type
    result_type = access_owner.result.type
    result_numel = None
    if isinstance(result_type, NnMemoryType):
        factors = []
        unknown_dim = False
        for dim in result_type.shape.data:
            dim_text = dim.expr.data if isinstance(dim, SymbolExprAttr) else str(dim)
            if dim_text == "?":
                unknown_dim = True
                break
            if dim_text != "1":
                factors.append(dim_text)
        if not unknown_dim:
            result_numel = "*".join(factors) if factors else "1"
    expected_strides = None
    if isinstance(result_type, NnMemoryType):
        expected = []
        running = "1"
        unknown_dim = False
        for dim in reversed(result_type.shape.data):
            expected.append(running)
            dim_text = dim.expr.data if isinstance(dim, SymbolExprAttr) else str(dim)
            if dim_text == "?":
                unknown_dim = True
                break
            if dim_text != "1":
                running = dim_text if running == "1" else f"{dim_text}*{running}"
        if not unknown_dim:
            expected.reverse()
            expected_strides = tuple(expected)
    actual_strides = None
    if isinstance(result_type, NnMemoryType):
        actual_strides = tuple(
            stride.expr.data if isinstance(stride, SymbolExprAttr) else str(stride)
            for stride in result_type.stride.data
        )
    offset_type = SSAValue.get(access_owner.offset).type
    if (
        isinstance(source_type, NnMemoryType)
        and isinstance(result_type, NnMemoryType)
        and result_numel is not None
        and source_type.element_type == result_type.element_type
        and source_type.space.space.data == result_type.space.space.data
        and isinstance(offset_type, SymbolValueType)
        and str(offset_type.get_value()) == "0"
        and expected_strides is not None
        and actual_strides == expected_strides
    ):
        return (SSAValue.get(access_owner.source), result_numel)
    return access_value


def _write_covers_access_value(event_user: Operation, event_use_index: int) -> bool:
    """判断一次 WRITE 是否覆盖该 use 代表的完整访问值。


    功能说明:
    - 把 fill/broadcast/slice/copy/deslice/kernel 的 full-write 规则收口成单一 predicate。
    - 返回值只说明当前 access value 是否被完整写入，是否覆盖 root 由 caller 的 alias proof 决定。
    - 不允许在该 helper 内放宽 READ 初始化证明。

    使用示例:
    - write_covers_value = _write_covers_access_value(event_user, event_use.index)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    if isinstance(event_user, (DmaFillOp, DmaBroadcastOp, DmaSliceOp)) and event_use_index == 0:
        return True
    if isinstance(event_user, DmaCopyOp) and event_use_index == 0:
        target_type = SSAValue.get(event_user.target).type
        source_type = SSAValue.get(event_user.source).type
        return (
            isinstance(target_type, NnMemoryType)
            and isinstance(source_type, NnMemoryType)
            and target_type.shape == source_type.shape
            and target_type.stride == source_type.stride
            and target_type.element_type == source_type.element_type
        )
    if isinstance(event_user, DmaDesliceOp) and event_use_index == 0:
        target_type = SSAValue.get(event_user.target).type
        offsets_are_zero = True
        for offset_value in event_user.offsets:
            offset_type = SSAValue.get(offset_value).type
            if not isinstance(offset_type, SymbolValueType) or str(offset_type.get_value()) != "0":
                offsets_are_zero = False
                break
        strides_are_one = True
        for stride_value in event_user.strides:
            stride_type = SSAValue.get(stride_value).type
            if not isinstance(stride_type, SymbolValueType) or str(stride_type.get_value()) != "1":
                strides_are_one = False
                break
        size_texts = []
        for size_value in event_user.sizes:
            size_type = SSAValue.get(size_value).type
            size_texts.append(str(size_type.get_value()) if isinstance(size_type, SymbolValueType) else None)
        shape_texts = []
        if isinstance(target_type, NnMemoryType):
            for shape_item in target_type.shape.data:
                shape_texts.append(shape_item.expr.data if isinstance(shape_item, SymbolExprAttr) else str(shape_item))
        return (
            isinstance(target_type, NnMemoryType)
            and offsets_are_zero
            and strides_are_one
            and len(size_texts) == len(shape_texts)
            and all(size == shape for size, shape in zip(size_texts, shape_texts))
        )
    return event_user.name.startswith("kernel.")


class DmaAllocWithMatmulFirstUseHoistPattern(RewritePattern):
    """`kernel.matmul` 首次使用自 reset 的 `dma.alloc` 外提 pattern。


    功能说明:
    - 只匹配需要 dynamic acc matmul READ+WRITE 自初始化证明的 loop-local `dma.alloc/free`。
    - 普通 fill/copy/deslice 等已 reset 的 alloc 仍由 `DmaAllocInSymbolForHoistPattern` 处理。
    - 该 pattern 放在普通 alloc pattern 前，避免 self-reset 例外散落在 generic rewrite 责任中。
    - IR before:
      ```mlir
      symbol.for %k = %start to %end step %tile {
        %out = "dma.alloc"(%tm, %tn) : (...) -> !nn.memory<...>
        %acc = symbol.ne %k, %start : !symbol.iter<...>, !symbol.int<...> -> i1
        "kernel.matmul"(%out, %lhs, %rhs, %acc) : (...) -> ()
        "dma.free"(%out) : (!nn.memory<...>) -> ()
      }
      ```
    - IR after:
      ```mlir
      %out = "dma.alloc"(%tm, %tn) : (...) -> !nn.memory<...>
      symbol.for %k = %start to %end step %tile {
        %acc = symbol.ne %k, %start : !symbol.iter<...>, !symbol.int<...> -> i1
        "kernel.matmul"(%out, %lhs, %rhs, %acc) : (...) -> ()
      }
      "dma.free"(%out) : (!nn.memory<...>) -> ()
      ```

    使用示例:
    - pattern = DmaAllocWithMatmulFirstUseHoistPattern()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: DmaAllocOp, rewriter: PatternRewriter, /) -> None:
        """对 dynamic acc matmul 首次覆盖写的 alloc 执行外提。


        功能说明:
        - 仅当 alloc 位于 `symbol.for` 直接 body block 内、shape loop-invariant 且存在唯一 matching free 时继续。
        - 生命周期证明允许 dynamic acc `kernel.matmul` out operand 自证首轮覆盖写。
        - 若 use plan 不包含 self-reset read，则保持 no-op，交由普通 alloc pattern 处理。

        使用示例:
        - DmaAllocWithMatmulFirstUseHoistPattern().match_and_rewrite(op, rewriter)

        关联文件:
        - spec: spec/pass/symbol_buffer_hoist.md
        - test: test/passes/test_symbol_buffer_hoist.py
        - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
        """

        loop_block = op.parent_block()
        if loop_block is None:
            return
        symbol_for = loop_block.parent_op()
        if not isinstance(symbol_for, SymbolForOp):
            return

        for shape_value in op.dynamic_shape:
            if not _value_dominates_symbol_for(SSAValue.get(shape_value), symbol_for):
                return

        pending_event_uses = []
        free_ops: list[DmaFreeOp] = []
        failed = False
        for use in tuple(op.result.uses):
            user = use.operation
            user_block = user.parent_block()
            if user_block is None or not (user_block is loop_block or loop_block.is_ancestor(user)):
                return
            if use.index == 0 and user.name in {"symbol.get_dim", "symbol.get_stride"}:
                continue

            effects = get_effects(user)
            if effects is not None:
                used_value = SSAValue.get(user.operands[use.index])
                kinds = {effect.kind for effect in effects if effect.value is used_value}
                if kinds and kinds <= {MemoryEffectKind.READ, MemoryEffectKind.WRITE}:
                    pending_event_uses.append((use, True))
                    continue

            if use.index == 0 and isinstance(user, (DmaViewOp, DmaReshapeOp, DmaSubviewOp, DmaReinterpretOp)):
                alias_stack = [(user, True)]
                visited_alias_ops: set[Operation] = set()
                while alias_stack and not failed:
                    alias_op, alias_covers_root = alias_stack.pop()
                    if alias_op in visited_alias_ops:
                        failed = True
                        break
                    visited_alias_ops.add(alias_op)
                    alias_block = alias_op.parent_block()
                    if alias_block is None or not (alias_block is loop_block or loop_block.is_ancestor(alias_op)):
                        failed = True
                        break
                    if len(alias_op.results) != 1:
                        failed = True
                        break
                    result_uses = tuple(alias_op.results[0].uses)
                    if not result_uses:
                        failed = True
                        break

                    alias_op_covers_source = _alias_op_covers_source(alias_op)

                    next_alias_covers_root = alias_covers_root and alias_op_covers_source
                    for result_use in result_uses:
                        result_user = result_use.operation
                        result_user_block = result_user.parent_block()
                        if result_user_block is None or not (
                            result_user_block is loop_block or loop_block.is_ancestor(result_user)
                        ):
                            failed = True
                            break
                        if result_use.index == 0 and result_user.name in {"symbol.get_dim", "symbol.get_stride"}:
                            continue
                        supported_result_use = (
                            isinstance(result_user, DmaSliceOp)
                            and result_use.index == 0
                            or isinstance(result_user, DmaDesliceOp)
                            and result_use.index in (0, 1)
                            or isinstance(result_user, DmaFillOp)
                            and result_use.index == 0
                            or isinstance(result_user, DmaCopyOp)
                            and result_use.index in (0, 1)
                            or isinstance(result_user, DmaBroadcastOp)
                            and result_use.index in (0, 1)
                        )
                        if not supported_result_use and result_user.name.startswith("kernel."):
                            result_effects = get_effects(result_user)
                            if result_effects is not None:
                                result_value = SSAValue.get(result_user.operands[result_use.index])
                                result_kinds = {effect.kind for effect in result_effects if effect.value is result_value}
                                supported_result_use = (
                                    bool(result_kinds)
                                    and result_kinds <= {MemoryEffectKind.READ, MemoryEffectKind.WRITE}
                                )
                        if supported_result_use:
                            pending_event_uses.append((result_use, next_alias_covers_root))
                            continue
                        if result_use.index == 0 and isinstance(
                            result_user, (DmaViewOp, DmaReshapeOp, DmaSubviewOp, DmaReinterpretOp)
                        ):
                            alias_stack.append((result_user, next_alias_covers_root))
                            continue
                        failed = True
                        break
                if failed:
                    return
                continue

            if isinstance(user, DmaFreeOp) and use.index == 0 and user.parent_block() is loop_block:
                free_ops.append(user)
                continue
            return

        if failed or not pending_event_uses or len(free_ops) != 1:
            return

        data_events = []
        for event_use, alias_covers_root in pending_event_uses:
            event_user = event_use.operation
            access_value = SSAValue.get(event_user.operands[event_use.index])
            access_scope = _reinterpret_logical_access_scope(access_value)

            if isinstance(event_user, DmaDesliceOp) and event_use.index == 1 and event_user.parent_block() is loop_block:
                data_events.append(
                    _MemoryEvent(
                        use=event_use,
                        effects=frozenset({MemoryEffectKind.WRITE}),
                        access_scope=access_scope,
                        full_write=False,
                        full_write_scope=None,
                        self_reset=False,
                    )
                )
                continue

            effects = get_effects(event_user)
            if effects is None:
                return
            effect_value = SSAValue.get(event_user.operands[event_use.index])
            kinds = {effect.kind for effect in effects if effect.value is effect_value}
            if not kinds or not kinds <= {MemoryEffectKind.READ, MemoryEffectKind.WRITE}:
                return

            self_resets = False
            if isinstance(event_user, KernelMatmulOp) and event_use.index == 0 and event_user.dynamic_acc is not None:
                matmul_block = event_user.parent_block()
                acc_value = SSAValue.get(event_user.dynamic_acc)
                acc_op = acc_value.owner
                if matmul_block is not None and isinstance(acc_op, Operation):
                    if acc_op.name == "symbol.ne" and acc_op.parent_block() is matmul_block and acc_op.is_before_in_block(event_user):
                        innermost_for = matmul_block.parent_op()
                        if isinstance(innermost_for, SymbolForOp):
                            iter_arg = innermost_for.body.blocks[0].args[0]
                            start_value = SSAValue.get(innermost_for.start)
                            operands = tuple(SSAValue.get(operand) for operand in acc_op.operands)
                            self_resets = operands in ((iter_arg, start_value), (start_value, iter_arg))

            write_covers_value = False
            if MemoryEffectKind.WRITE in kinds:
                write_covers_value = _write_covers_access_value(event_user, event_use.index)

            root_full_write = alias_covers_root and write_covers_value
            scoped_full_write = (
                write_covers_value
                and not root_full_write
                and (MemoryEffectKind.READ not in kinds or self_resets)
            )
            data_events.append(
                _MemoryEvent(
                    use=event_use,
                    effects=frozenset(kinds),
                    access_scope=access_scope,
                    full_write=root_full_write or scoped_full_write,
                    full_write_scope=None if root_full_write else access_scope,
                    self_reset=MemoryEffectKind.READ in kinds and scoped_full_write and self_resets,
                )
            )

        if not data_events:
            return
        events_by_op: dict[Operation, list[_MemoryEvent]] = {}
        for event in data_events:
            event_op = event.use.operation
            event_block = event_op.parent_block()
            if event_block is None or not (event_block is loop_block or loop_block.is_ancestor(event_op)):
                return
            events_by_op.setdefault(event_op, []).append(event)

        proof_failed = False
        proof_stack = [(loop_block, ())]
        while proof_stack and not proof_failed:
            scan_block, entering_scopes = proof_stack.pop()
            initialized_scopes = list(entering_scopes)
            for scan_op in scan_block.ops:
                op_events = events_by_op.get(scan_op, ())
                for event in op_events:
                    if MemoryEffectKind.READ not in event.effects:
                        continue
                    if (
                        event.self_reset
                        and (event.full_write_scope is None or event.full_write_scope == event.access_scope)
                    ):
                        continue
                    if not any(scope is None or scope == event.access_scope for scope in initialized_scopes):
                        proof_failed = True
                        break
                if proof_failed:
                    break
                for event in op_events:
                    if event.full_write:
                        initialized_scopes.append(event.full_write_scope)
                for region in scan_op.regions:
                    for child_block in region.blocks:
                        proof_stack.append((child_block, tuple(initialized_scopes)))
        if proof_failed:
            return

        free_op = free_ops[0]
        indexes = {item: index for index, item in enumerate(loop_block.ops)}
        if free_op not in indexes:
            return
        data_indexes: list[int] = []
        for event in data_events:
            current_op = event.use.operation
            current_block = current_op.parent_block()
            direct_use_op = None
            while current_block is not None:
                if current_block is loop_block:
                    direct_use_op = current_op
                    break
                parent_op = current_block.parent_op()
                if parent_op is None:
                    break
                current_op = parent_op
                current_block = current_op.parent_block()
            if direct_use_op not in indexes:
                return
            data_indexes.append(indexes[direct_use_op])
        if not data_indexes or indexes[free_op] <= max(data_indexes):
            return
        if not any(event.self_reset and MemoryEffectKind.READ in event.effects for event in data_events):
            return

        op.detach()
        rewriter.insert_op(op, InsertPoint.before(symbol_for))
        free_op.detach()
        rewriter.insert_op(free_op, InsertPoint.after(symbol_for))
        rewriter.notify_op_modified(symbol_for)


class DmaAllocInSymbolForHoistPattern(RewritePattern):
    """`symbol.for` 内普通 `dma.alloc` 外提 pattern。


    功能说明:
    - 只匹配当前 `symbol.for` body block 顶层的 `dma.alloc`。
    - 满足 shape invariant、direct use 白名单与唯一匹配 free 时，把 alloc 外提到所属 `symbol.for` 之前。
    - 若存在合法匹配 free，同步把 free 移到所属 `symbol.for` 之后，保持生命周期成对外提。
    - 不启用 READ+WRITE 自初始化例外；dynamic acc matmul 首次覆盖写由专用 pattern 处理。
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
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: DmaAllocOp, rewriter: PatternRewriter, /) -> None:
        """对满足普通 reset 条件的 loop 内 `dma.alloc` 执行外提。


        功能说明:
        - 仅当 alloc 位于 `symbol.for` 直接 body block 内时继续。
        - shape 或 direct use 任一条件不满足时保持 no-op。
        - 外提后复用原 op/result，不新建等价 alloc；合法 free 也复用原 op。
        - 不允许 dynamic acc matmul 自证 reset，避免与专用 pattern 重叠。

        使用示例:
        - DmaAllocInSymbolForHoistPattern().match_and_rewrite(op, rewriter)

        关联文件:
        - spec: spec/pass/symbol_buffer_hoist.md
        - test: test/passes/test_symbol_buffer_hoist.py
        - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
        """

        loop_block = op.parent_block()
        if loop_block is None:
            return
        symbol_for = loop_block.parent_op()
        if not isinstance(symbol_for, SymbolForOp):
            return

        for shape_value in op.dynamic_shape:
            if not _value_dominates_symbol_for(SSAValue.get(shape_value), symbol_for):
                return

        pending_event_uses = []
        free_ops: list[DmaFreeOp] = []
        failed = False
        for use in tuple(op.result.uses):
            user = use.operation
            user_block = user.parent_block()
            if user_block is None or not (user_block is loop_block or loop_block.is_ancestor(user)):
                return
            if use.index == 0 and user.name in {"symbol.get_dim", "symbol.get_stride"}:
                continue

            effects = get_effects(user)
            if effects is not None:
                used_value = SSAValue.get(user.operands[use.index])
                kinds = {effect.kind for effect in effects if effect.value is used_value}
                if kinds and kinds <= {MemoryEffectKind.READ, MemoryEffectKind.WRITE}:
                    pending_event_uses.append((use, True))
                    continue

            if use.index == 0 and isinstance(user, (DmaViewOp, DmaReshapeOp, DmaSubviewOp, DmaReinterpretOp)):
                alias_stack = [(user, True)]
                visited_alias_ops: set[Operation] = set()
                while alias_stack and not failed:
                    alias_op, alias_covers_root = alias_stack.pop()
                    if alias_op in visited_alias_ops:
                        failed = True
                        break
                    visited_alias_ops.add(alias_op)
                    alias_block = alias_op.parent_block()
                    if alias_block is None or not (alias_block is loop_block or loop_block.is_ancestor(alias_op)):
                        failed = True
                        break
                    if len(alias_op.results) != 1:
                        failed = True
                        break
                    result_uses = tuple(alias_op.results[0].uses)
                    if not result_uses:
                        failed = True
                        break

                    alias_op_covers_source = _alias_op_covers_source(alias_op)

                    next_alias_covers_root = alias_covers_root and alias_op_covers_source
                    for result_use in result_uses:
                        result_user = result_use.operation
                        result_user_block = result_user.parent_block()
                        if result_user_block is None or not (
                            result_user_block is loop_block or loop_block.is_ancestor(result_user)
                        ):
                            failed = True
                            break
                        if result_use.index == 0 and result_user.name in {"symbol.get_dim", "symbol.get_stride"}:
                            continue
                        supported_result_use = (
                            isinstance(result_user, DmaSliceOp)
                            and result_use.index == 0
                            or isinstance(result_user, DmaDesliceOp)
                            and result_use.index in (0, 1)
                            or isinstance(result_user, DmaFillOp)
                            and result_use.index == 0
                            or isinstance(result_user, DmaCopyOp)
                            and result_use.index in (0, 1)
                            or isinstance(result_user, DmaBroadcastOp)
                            and result_use.index in (0, 1)
                        )
                        if not supported_result_use and result_user.name.startswith("kernel."):
                            result_effects = get_effects(result_user)
                            if result_effects is not None:
                                result_value = SSAValue.get(result_user.operands[result_use.index])
                                result_kinds = {effect.kind for effect in result_effects if effect.value is result_value}
                                supported_result_use = (
                                    bool(result_kinds)
                                    and result_kinds <= {MemoryEffectKind.READ, MemoryEffectKind.WRITE}
                                )
                        if supported_result_use:
                            pending_event_uses.append((result_use, next_alias_covers_root))
                            continue
                        if result_use.index == 0 and isinstance(
                            result_user, (DmaViewOp, DmaReshapeOp, DmaSubviewOp, DmaReinterpretOp)
                        ):
                            alias_stack.append((result_user, next_alias_covers_root))
                            continue
                        failed = True
                        break
                if failed:
                    return
                continue

            if isinstance(user, DmaFreeOp) and use.index == 0 and user.parent_block() is loop_block:
                free_ops.append(user)
                continue
            return

        if failed or not pending_event_uses or len(free_ops) != 1:
            return

        data_events = []
        for event_use, alias_covers_root in pending_event_uses:
            event_user = event_use.operation
            access_value = SSAValue.get(event_user.operands[event_use.index])
            access_scope = _reinterpret_logical_access_scope(access_value)

            if isinstance(event_user, DmaDesliceOp) and event_use.index == 1 and event_user.parent_block() is loop_block:
                data_events.append(
                    _MemoryEvent(
                        use=event_use,
                        effects=frozenset({MemoryEffectKind.WRITE}),
                        access_scope=access_scope,
                        full_write=False,
                        full_write_scope=None,
                        self_reset=False,
                    )
                )
                continue

            effects = get_effects(event_user)
            if effects is None:
                return
            effect_value = SSAValue.get(event_user.operands[event_use.index])
            kinds = {effect.kind for effect in effects if effect.value is effect_value}
            if not kinds or not kinds <= {MemoryEffectKind.READ, MemoryEffectKind.WRITE}:
                return

            self_resets = False
            if isinstance(event_user, KernelMatmulOp) and event_use.index == 0 and event_user.dynamic_acc is not None:
                matmul_block = event_user.parent_block()
                acc_value = SSAValue.get(event_user.dynamic_acc)
                acc_op = acc_value.owner
                if matmul_block is not None and isinstance(acc_op, Operation):
                    if acc_op.name == "symbol.ne" and acc_op.parent_block() is matmul_block and acc_op.is_before_in_block(event_user):
                        innermost_for = matmul_block.parent_op()
                        if isinstance(innermost_for, SymbolForOp):
                            iter_arg = innermost_for.body.blocks[0].args[0]
                            start_value = SSAValue.get(innermost_for.start)
                            operands = tuple(SSAValue.get(operand) for operand in acc_op.operands)
                            self_resets = operands in ((iter_arg, start_value), (start_value, iter_arg))

            write_covers_value = False
            if MemoryEffectKind.WRITE in kinds:
                write_covers_value = _write_covers_access_value(event_user, event_use.index)

            root_full_write = alias_covers_root and write_covers_value
            scoped_full_write = write_covers_value and not root_full_write and MemoryEffectKind.READ not in kinds
            data_events.append(
                _MemoryEvent(
                    use=event_use,
                    effects=frozenset(kinds),
                    access_scope=access_scope,
                    full_write=root_full_write or scoped_full_write,
                    full_write_scope=None if root_full_write else access_scope,
                    self_reset=False,
                )
            )

        if not data_events:
            return
        events_by_op: dict[Operation, list[_MemoryEvent]] = {}
        for event in data_events:
            event_op = event.use.operation
            event_block = event_op.parent_block()
            if event_block is None or not (event_block is loop_block or loop_block.is_ancestor(event_op)):
                return
            events_by_op.setdefault(event_op, []).append(event)

        proof_failed = False
        proof_stack = [(loop_block, ())]
        while proof_stack and not proof_failed:
            scan_block, entering_scopes = proof_stack.pop()
            initialized_scopes = list(entering_scopes)
            for scan_op in scan_block.ops:
                op_events = events_by_op.get(scan_op, ())
                for event in op_events:
                    if MemoryEffectKind.READ not in event.effects:
                        continue
                    if not any(scope is None or scope == event.access_scope for scope in initialized_scopes):
                        proof_failed = True
                        break
                if proof_failed:
                    break
                for event in op_events:
                    if event.full_write:
                        initialized_scopes.append(event.full_write_scope)
                for region in scan_op.regions:
                    for child_block in region.blocks:
                        proof_stack.append((child_block, tuple(initialized_scopes)))
        if proof_failed:
            return

        free_op = free_ops[0]
        indexes = {item: index for index, item in enumerate(loop_block.ops)}
        if free_op not in indexes:
            return
        data_indexes: list[int] = []
        for event in data_events:
            current_op = event.use.operation
            current_block = current_op.parent_block()
            direct_use_op = None
            while current_block is not None:
                if current_block is loop_block:
                    direct_use_op = current_op
                    break
                parent_op = current_block.parent_op()
                if parent_op is None:
                    break
                current_op = parent_op
                current_block = current_op.parent_block()
            if direct_use_op not in indexes:
                return
            data_indexes.append(indexes[direct_use_op])
        if not data_indexes or indexes[free_op] <= max(data_indexes):
            return

        op.detach()
        rewriter.insert_op(op, InsertPoint.before(symbol_for))
        free_op.detach()
        rewriter.insert_op(free_op, InsertPoint.after(symbol_for))
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
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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
        - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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
        - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
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
        - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
        """

        _hoist_alias_op_if_safe(op, rewriter)


class DmaReinterpretInSymbolForHoistPattern(RewritePattern):
    """`symbol.for` 内 `dma.reinterpret` 单 op 外提 pattern。


    功能说明:
    - 只在 source、offset、shape、stride 均对当前 loop invariant 时外提一层。
    - IR 变换：`symbol.for { %r = dma.reinterpret(...); use(%r) }` 变为 `%r = dma.reinterpret(...); symbol.for { use(%r) }`。
    - no-op：offset/shape/stride 来自当前 loop body 时保持原 IR。
    - IR before:
      ```mlir
      symbol.for %i = %c0 to %n step %c1 {
        %r = "dma.reinterpret"(%src, %off, %m, %n, %stride_m, %stride_n) : (...) -> !nn.memory<value>
        "kernel.use"(%r) : (value) -> ()
      }
      ```
    - IR after:
      ```mlir
      %r = "dma.reinterpret"(%src, %off, %m, %n, %stride_m, %stride_n) : (...) -> !nn.memory<value>
      symbol.for %i = %c0 to %n step %c1 {
        "kernel.use"(%r) : (value) -> ()
      }
      ```

    使用示例:
    - pattern = DmaReinterpretInSymbolForHoistPattern()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: DmaReinterpretOp, rewriter: PatternRewriter, /) -> None:
        """对满足条件的 `dma.reinterpret` 执行单层外提。


        功能说明:
        - 不新增 loop argument；loop body 直接捕获外提后的 SSA result。
        - 任一 operand 不支配当前 loop 或 result use 不在白名单时保持 no-op。

        使用示例:
        - DmaReinterpretInSymbolForHoistPattern().match_and_rewrite(op, rewriter)

        关联文件:
        - spec: spec/pass/symbol_buffer_hoist.md
        - test: test/passes/test_symbol_buffer_hoist.py
        - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
        """

        _hoist_alias_op_if_safe(op, rewriter)


def get_symbol_buffer_hoist_patterns() -> list[RewritePattern]:
    """返回 `symbol-buffer-hoist` 公开 pattern 列表。


    功能说明:
    - 公开返回 matmul-first alloc、普通 `dma.alloc/free` pattern 与 alias op pattern 实例。
    - 返回值顺序固定为 matmul-first alloc、普通 alloc/free、view、reshape、subview、reinterpret，
      便于 greedy walker 逐层收敛。

    使用示例:
    - patterns = get_symbol_buffer_hoist_patterns()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    return [
        DmaAllocWithMatmulFirstUseHoistPattern(),
        DmaAllocInSymbolForHoistPattern(),
        DmaViewInSymbolForHoistPattern(),
        DmaReshapeInSymbolForHoistPattern(),
        DmaSubviewInSymbolForHoistPattern(),
        DmaReinterpretInSymbolForHoistPattern(),
    ]


class SymbolBufferHoistPass(Pass):
    """`symbol-buffer-hoist` pass。


    功能说明:
    - 通过直接 pattern walker 处理 module 中满足公开条件的 `dma.alloc/free` 与 alias op 外提。
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
    - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
    """

    name = "symbol-buffer-hoist"

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 `symbol-buffer-hoist` ModulePass。


        功能说明:
        - 只处理 `builtin.module`。
        - 用 greedy pattern walker 把 `symbol.for` 内可安全外提的 alloc/alias op 外提一层。
        - 最终统一做一次 `module.verify()`，保持公开失败前缀稳定。

        使用示例:
        - SymbolBufferHoistPass().apply(Context(), module)

        关联文件:
        - spec: spec/pass/symbol_buffer_hoist.md
        - test: test/passes/test_symbol_buffer_hoist.py
        - test: test/passes/test_registry.py
        - 功能实现: kernel_gen/passes/hoist/symbol_buffer_hoist.py
        """

        module = ensure_builtin_module(module)
        if ctx.get_optional_dialect(Symbol.name) is None:
            ctx.load_dialect(Symbol)
        PatternRewriteWalker(
            GreedyRewritePatternApplier(
                [
                    *get_symbol_buffer_hoist_patterns(),
                ],
                ctx=ctx,
                folding_enabled=self.fold,
                dce_enabled=False,
            )
        ).rewrite_module(module)
        try:
            module.verify()
        except VerifyException as exc:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"SymbolBufferHoistVerifierError: {exc}") from exc
        except KernelCodeError as exc:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"SymbolBufferHoistVerifierError: {exc}") from exc


__all__ = [
    "DmaAllocWithMatmulFirstUseHoistPattern",
    "DmaAllocInSymbolForHoistPattern",
    "DmaViewInSymbolForHoistPattern",
    "DmaReshapeInSymbolForHoistPattern",
    "DmaSubviewInSymbolForHoistPattern",
    "DmaReinterpretInSymbolForHoistPattern",
    "get_symbol_buffer_hoist_patterns",
    "SymbolBufferHoistPass",
]
